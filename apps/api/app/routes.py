import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import Tournament, Team, Venue, TimeWindow, ScheduleRun
from .schemas import TournamentCreateIn, TournamentOut, GenerateOut, ScheduleRunOut

from .schemas import TournamentCreateIn, TournamentOut, GenerateOut, ScheduleRunOut, TournamentListItem

from datetime import datetime
from typing import Any, Dict, List


router = APIRouter()


def _stable_hash(obj) -> str:
    # Deterministic JSON hash so we can compare inputs across runs
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def _parse_dt(dt_str: str) -> datetime:
    # Convert ISO string to datetime (handles "...Z" by converting to "+00:00")
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    # Two intervals overlap if each starts before the other ends.
    return a_start < b_end and b_start < a_end


def _compute_integrity(games: List[Dict[str, Any]], team_name_by_id: Dict[str, str], venue_name_by_id: Dict[str, str]) -> Dict[str, Any]:
    """
    Invariant checks (must never be violated):
      - Team double-booking (same team in overlapping games)
      - Venue double-booking (same venue in overlapping games)

    Returns:
      {
        "status": "PASS" | "FAIL",
        "violations_total": int,
        "violations": [ ... ],
      }
    """

    violations: List[Dict[str, Any]] = []

    def team_name(team_id: str) -> str:
        return team_name_by_id.get(team_id, team_id)

    def venue_name(venue_id: str) -> str:
        return venue_name_by_id.get(venue_id, venue_id)

    def matchup_label(g: Dict[str, Any]) -> str:
        # "Barcelona vs Real Madrid"
        return f'{team_name(g["home_team_id"])} vs {team_name(g["away_team_id"])}'


    # Index games by team and by venue using parsed times, WITHOUT mutating the original dicts.
    games_by_team: Dict[str, List[Dict[str, Any]]] = {}
    games_by_venue: Dict[str, List[Dict[str, Any]]] = {}

    def record(g: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "game_no": g.get("game_no"),
            "home_team_id": g.get("home_team_id"),
            "away_team_id": g.get("away_team_id"),
            "venue_id": g.get("venue_id"),
            "start_ts": g.get("start_ts"),
            "end_ts": g.get("end_ts"),
            "start": _parse_dt(g["start_ts"]),
            "end": _parse_dt(g["end_ts"]),
        }

    # Build indexes
    records: List[Dict[str, Any]] = [record(g) for g in games]

    for r in records:
        # Teams
        for team_id in [r["home_team_id"], r["away_team_id"]]:
            games_by_team.setdefault(team_id, []).append(r)

        # Venue
        games_by_venue.setdefault(r["venue_id"], []).append(r)

    # Check 1: Team double-booking
    for team_id, tgames in games_by_team.items():
        tgames_sorted = sorted(tgames, key=lambda x: x["start"])

        for i in range(len(tgames_sorted)):
            for j in range(i + 1, len(tgames_sorted)):
                a = tgames_sorted[i]
                b = tgames_sorted[j]

                if b["start"] >= a["end"]:
                    break

                if _overlaps(a["start"], a["end"], b["start"], b["end"]):
                    violations.append({
                        "type": "TEAM_DOUBLE_BOOKING",
                        "severity": "HIGH",
                        "message": "A team is scheduled for overlapping games.",
                        "team_id": team_id,
                        "team_name": team_name_by_id.get(team_id, team_id),
                        "games": [
                            {
                                "game_no": a["game_no"],
                                "start_ts": a["start_ts"],
                                "end_ts": a["end_ts"],
                                "venue_id": a["venue_id"],
                                "venue_name": venue_name(a["venue_id"]),
                                # opponent relative to the violating team
                                "vs": team_name(a["away_team_id"]) if a["home_team_id"] == team_id else team_name(a["home_team_id"]),
                            },
                            {
                                "game_no": b["game_no"],
                                "start_ts": b["start_ts"],
                                "end_ts": b["end_ts"],
                                "venue_id": b["venue_id"],
                                "venue_name": venue_name(b["venue_id"]),
                                "vs": team_name(b["away_team_id"]) if b["home_team_id"] == team_id else team_name(b["home_team_id"]),
                            },
                        ],
                        "explain": "The same team appears in two games whose time ranges overlap."
                    })

    MIN_REST_MINUTES = 60

    for team_id, tgames in games_by_team.items():
        tgames_sorted = sorted(tgames, key=lambda x: x["start"])

        for i in range(len(tgames_sorted) - 1):
            a = tgames_sorted[i]
            b = tgames_sorted[i + 1]

            # Rest minutes between games
            rest_minutes = (b["start"] - a["end"]).total_seconds() / 60.0

            if rest_minutes < MIN_REST_MINUTES:
                violations.append({
                    "type": "REST_VIOLATION",
                    "severity": "MEDIUM",
                    "message": "A team does not have enough rest between games.",
                    "team_id": team_id,
                    "team_name": team_name(team_id),
                    "min_rest_minutes": MIN_REST_MINUTES,
                    "rest_minutes": round(rest_minutes, 1),
                    "games": [
                        {
                            "game_no": a["game_no"],
                            "start_ts": a["start_ts"],
                            "end_ts": a["end_ts"],
                            "venue_name": venue_name(a["venue_id"]),
                            "vs": team_name(a["away_team_id"]) if a["home_team_id"] == team_id else team_name(a["home_team_id"]),
                        },
                        {
                            "game_no": b["game_no"],
                            "start_ts": b["start_ts"],
                            "end_ts": b["end_ts"],
                            "venue_name": venue_name(b["venue_id"]),
                            "vs": team_name(b["away_team_id"]) if b["home_team_id"] == team_id else team_name(b["home_team_id"]),
                        },
                    ],
                    "explain": "Even if games don’t overlap, teams need buffer time for warm-up, travel, and recovery."
                })


    # Check 2: Venue double-booking
    for venue_id, vgames in games_by_venue.items():
        vgames_sorted = sorted(vgames, key=lambda x: x["start"])

        for i in range(len(vgames_sorted)):
            for j in range(i + 1, len(vgames_sorted)):
                a = vgames_sorted[i]
                b = vgames_sorted[j]

                if b["start"] >= a["end"]:
                    break

                if _overlaps(a["start"], a["end"], b["start"], b["end"]):
                    violations.append({
                        "type": "VENUE_DOUBLE_BOOKING",
                        "severity": "HIGH",
                        "message": "A venue is scheduled for overlapping games.",
                        "venue_id": venue_id,
                        "venue_name": venue_name_by_id.get(venue_id, venue_id),
                        "games": [
                            {
                                "game_no": a["game_no"],
                                "start_ts": a["start_ts"],
                                "end_ts": a["end_ts"],
                                "matchup": matchup_label(a),
                            },
                            {
                                "game_no": b["game_no"],
                                "start_ts": b["start_ts"],
                                "end_ts": b["end_ts"],
                                "matchup": matchup_label(b),
                            },
                        ],
                        "explain": "Two games are placed in the same venue during overlapping time windows."
                    })

    status = "PASS" if len(violations) == 0 else "FAIL"




    return {
        "status": status,
        "violations_total": len(violations),
        "violations": violations[:25],  # cap
    }

def _compute_fairness(games: List[Dict[str, Any]], team_name_by_id: Dict[str, str]) -> Dict[str, Any]:
    records = []
    for g in games:
        records.append({
            "game_no": g.get("game_no"),
            "home_team_id": g.get("home_team_id"),
            "away_team_id": g.get("away_team_id"),
            "start": _parse_dt(g["start_ts"]),
            "end": _parse_dt(g["end_ts"]),
        })

    # Build per-team timelines
    games_by_team: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        for team_id in [r["home_team_id"], r["away_team_id"]]:
            games_by_team.setdefault(team_id, []).append(r)

    MIN_REST_MINUTES = 60
    back_to_backs = []
    rest_stats = []

    for team_id, tgames in games_by_team.items():
        tgames_sorted = sorted(tgames, key=lambda x: x["start"])
        rests = []

        for i in range(len(tgames_sorted) - 1):
            a = tgames_sorted[i]
            b = tgames_sorted[i + 1]
            rest_minutes = (b["start"] - a["end"]).total_seconds() / 60.0
            rests.append(rest_minutes)

            if rest_minutes < MIN_REST_MINUTES:
                back_to_backs.append({
                    "team_id": team_id,
                    "team_name": team_name_by_id.get(team_id, team_id),
                    "rest_minutes": round(rest_minutes, 1),
                    "games": [a["game_no"], b["game_no"]],
                })

        if rests:
            rest_stats.append({
                "team_id": team_id,
                "team_name": team_name_by_id.get(team_id, team_id),
                "min_rest": round(min(rests), 1),
                "avg_rest": round(sum(rests) / len(rests), 1),
            })
        else:
            rest_stats.append({
                "team_id": team_id,
                "team_name": team_name_by_id.get(team_id, team_id),
                "min_rest": None,
                "avg_rest": None,
            })

    # Simple scoring: start at 100, subtract penalties for back-to-backs
    score = 100 - (10 * len(back_to_backs))
    score = max(0, score)

    # Top offenders (who has most back-to-backs)
    offender_counts: Dict[str, int] = {}
    for b2b in back_to_backs:
        offender_counts[b2b["team_name"]] = offender_counts.get(b2b["team_name"], 0) + 1

    top_offenders = sorted(offender_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "score": score,
        "back_to_back_total": len(back_to_backs),
        "top_offenders": [{"team_name": name, "count": cnt} for name, cnt in top_offenders],
        "rest_stats": rest_stats,
    }



@router.get("/tournaments", response_model=list[TournamentListItem])
async def list_tournaments(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Tournament).order_by(Tournament.created_at.desc()).limit(50)
        )
    ).scalars().all()

    return [TournamentListItem(id=t.id, name=t.name, created_at=t.created_at) for t in rows]


@router.get("/tournaments/{tournament_id}", response_model=TournamentOut)
async def get_tournament(tournament_id: UUID, db: AsyncSession = Depends(get_db)):
    t = (
        await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    ).scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return TournamentOut(id=t.id, name=t.name, created_at=t.created_at)


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

    team_name_by_id = {str(x.id): x.name for x in teams}
    venue_name_by_id = {str(v.id): v.name for v in venues}
    integrity = _compute_integrity(schedule, team_name_by_id, venue_name_by_id)

    fairness = _compute_fairness(schedule, team_name_by_id)


    metrics = {
        "games_total": len(schedule),
        "teams_total": len(teams),
        "venues_total": len(venues),
        "time_windows_total": len(time_windows),

        # Phase 1 Core
        "integrity": integrity,

        # Phase 1 core
        "fairness": fairness,
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

    # Load teams + venues to build ID->name maps
    teams = (await db.execute(select(Team).where(Team.tournament_id == tournament_id))).scalars().all()
    venues = (await db.execute(select(Venue).where(Venue.tournament_id == tournament_id))).scalars().all()

    team_name_by_id = {str(t.id): t.name for t in teams}
    venue_name_by_id = {str(v.id): v.name for v in venues}

    # Decorate schedule_json for UI friendliness (do NOT mutate DB)
    schedule_json = run.schedule_json
    if schedule_json and isinstance(schedule_json, dict) and "games" in schedule_json:
        decorated_games = []
        for g in schedule_json.get("games", []):
            # g contains IDs; we add names
            home_id = g.get("home_team_id")
            away_id = g.get("away_team_id")
            venue_id = g.get("venue_id")

            decorated_games.append({
                **g,
                "home_team_name": team_name_by_id.get(home_id, home_id),
                "away_team_name": team_name_by_id.get(away_id, away_id),
                "venue_name": venue_name_by_id.get(venue_id, venue_id),
            })

        schedule_json = {**schedule_json, "games": decorated_games}

    return ScheduleRunOut(
        id=run.id,
        tournament_id=run.tournament_id,
        created_at=run.created_at,
        status=run.status,
        input_hash=run.input_hash,
        schedule_json=schedule_json,
        metrics_json=run.metrics_json,
        error_json=run.error_json,
    )
