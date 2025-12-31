import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import Tournament, Team, Venue, TimeWindow, ScheduleRun
from .schemas import TournamentCreateIn, TournamentOut, GenerateOut, ScheduleRunOut

router = APIRouter()


def _stable_hash(obj) -> str:
    # Deterministic JSON hash so we can compare inputs across runs
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@router.post("/tournaments", response_model=TournamentOut)
async def create_tournament(payload: TournamentCreateIn, db: AsyncSession = Depends(get_db)):
    t = Tournament(name=payload.name)
    db.add(t)
    await db.flush()  # get t.id

    for team in payload.teams:
        db.add(Team(tournament_id=t.id, name=team.name))

    for venue in payload.venues:
        db.add(Venue(tournament_id=t.id, name=venue.name))

    # Need venue IDs if user wants to pin time windows to venues
    await db.flush()

    for tw in payload.time_windows:
        db.add(TimeWindow(
            tournament_id=t.id,
            start_ts=tw.start_ts,
            end_ts=tw.end_ts,
            venue_id=tw.venue_id,
        ))

    await db.commit()
    await db.refresh(t)
    return TournamentOut(id=t.id, name=t.name, created_at=t.created_at)


@router.post("/tournaments/{tournament_id}/generate", response_model=GenerateOut)
async def generate_schedule(tournament_id: UUID, db: AsyncSession = Depends(get_db)):
    # Load minimal inputs
    t = (await db.execute(select(Tournament).where(Tournament.id == tournament_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    teams = (await db.execute(select(Team).where(Team.tournament_id == tournament_id))).scalars().all()
    venues = (await db.execute(select(Venue).where(Venue.tournament_id == tournament_id))).scalars().all()
    time_windows = (await db.execute(select(TimeWindow).where(TimeWindow.tournament_id == tournament_id).order_by(TimeWindow.start_ts))).scalars().all()

    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams to generate a schedule")
    if len(time_windows) < 1:
        raise HTTPException(status_code=400, detail="Need at least 1 time window to generate a schedule")
    if len(venues) < 1:
        raise HTTPException(status_code=400, detail="Need at least 1 venue to generate a schedule")

    # Phase 0: simple pairing + sequential slot assignment
    team_ids = [str(x.id) for x in teams]
    venue_ids = [str(v.id) for v in venues]
    windows = [{"start_ts": tw.start_ts.isoformat(), "end_ts": tw.end_ts.isoformat(), "venue_id": str(tw.venue_id) if tw.venue_id else None} for tw in time_windows]

    input_obj = {"teams": team_ids, "venues": venue_ids, "time_windows": windows}
    input_hash = _stable_hash(input_obj)

    # Build simple games list (round-robin combinations)
    games = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            games.append({"home_team_id": str(teams[i].id), "away_team_id": str(teams[j].id)})

    schedule = []
    for idx, game in enumerate(games):
        tw = time_windows[idx % len(time_windows)]
        # If time window is pinned to a venue, use it; else rotate venues.
        venue_id = tw.venue_id or venues[idx % len(venues)].id

        schedule.append({
            "game_no": idx + 1,
            "home_team_id": game["home_team_id"],
            "away_team_id": game["away_team_id"],
            "start_ts": tw.start_ts.isoformat(),
            "end_ts": tw.end_ts.isoformat(),
            "venue_id": str(venue_id),
        })

    # Basic metrics for Phase 0 (placeholder)
    metrics = {
        "games_total": len(schedule),
        "teams_total": len(teams),
        "venues_total": len(venues),
        "time_windows_total": len(time_windows),
    }

    run = ScheduleRun(
        tournament_id=tournament_id,
        status="COMPLETE",
        input_hash=input_hash,
        schedule_json={"games": schedule},
        metrics_json=metrics,
        error_json=None,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return GenerateOut(run_id=run.id, status=run.status)


@router.get("/tournaments/{tournament_id}/latest-run", response_model=ScheduleRunOut)
async def latest_run(tournament_id: UUID, db: AsyncSession = Depends(get_db)):
    # Latest run by created_at
    result = await db.execute(
        select(ScheduleRun)
        .where(ScheduleRun.tournament_id == tournament_id)
        .order_by(ScheduleRun.created_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="No schedule runs yet")

    return ScheduleRunOut(
        id=run.id,
        tournament_id=run.tournament_id,
        created_at=run.created_at,
        status=run.status,
        input_hash=run.input_hash,
        schedule_json=run.schedule_json,
        metrics_json=run.metrics_json,
        error_json=run.error_json,
    )
