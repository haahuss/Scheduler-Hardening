import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from collections import Counter
from .models import Tournament, Team, Venue, TimeWindow, ScheduleRun
from .schemas import (
    TournamentCreateIn,
    TournamentOut,
    GenerateOut,
    ScheduleRunOut,
    TournamentListItem,
)

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .deps import get_db_rls
from .rls import require_user_id


router = APIRouter()


def _stable_hash(obj) -> str:
    # Deterministic JSON hash so we can compare inputs across runs
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _parse_dt(dt_str: str) -> datetime:
    # Convert ISO string to datetime (handles "...Z" by converting to "+00:00")
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def _overlaps(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    # Two intervals overlap if each starts before the other ends.
    return a_start < b_end and b_start < a_end


def _compute_integrity(
    games: List[Dict[str, Any]],
    team_name_by_id: Dict[str, str],
    venue_name_by_id: Dict[str, str],
) -> Dict[str, Any]:
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
        return f"{team_name(g['home_team_id'])} vs {team_name(g['away_team_id'])}"

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
                    violations.append(
                        {
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
                                    "vs": team_name(a["away_team_id"])
                                    if a["home_team_id"] == team_id
                                    else team_name(a["home_team_id"]),
                                },
                                {
                                    "game_no": b["game_no"],
                                    "start_ts": b["start_ts"],
                                    "end_ts": b["end_ts"],
                                    "venue_id": b["venue_id"],
                                    "venue_name": venue_name(b["venue_id"]),
                                    "vs": team_name(b["away_team_id"])
                                    if b["home_team_id"] == team_id
                                    else team_name(b["home_team_id"]),
                                },
                            ],
                            "explain": "The same team appears in two games whose time ranges overlap.",
                        }
                    )

    MIN_REST_MINUTES = 60

    for team_id, tgames in games_by_team.items():
        tgames_sorted = sorted(tgames, key=lambda x: x["start"])

        for i in range(len(tgames_sorted) - 1):
            a = tgames_sorted[i]
            b = tgames_sorted[i + 1]

            # Rest minutes between games
            rest_minutes = (b["start"] - a["end"]).total_seconds() / 60.0

            if rest_minutes < MIN_REST_MINUTES:
                violations.append(
                    {
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
                                "vs": team_name(a["away_team_id"])
                                if a["home_team_id"] == team_id
                                else team_name(a["home_team_id"]),
                            },
                            {
                                "game_no": b["game_no"],
                                "start_ts": b["start_ts"],
                                "end_ts": b["end_ts"],
                                "venue_name": venue_name(b["venue_id"]),
                                "vs": team_name(b["away_team_id"])
                                if b["home_team_id"] == team_id
                                else team_name(b["home_team_id"]),
                            },
                        ],
                        "explain": "Even if games don’t overlap, teams need buffer time for warm-up, travel, and recovery.",
                    }
                )

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
                    violations.append(
                        {
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
                            "explain": "Two games are placed in the same venue during overlapping time windows.",
                        }
                    )

    status = "PASS" if len(violations) == 0 else "FAIL"

    return {
        "status": status,
        "violations_total": len(violations),
        "violations": violations[:25],  # cap
    }


def _compute_fairness(
    games: List[Dict[str, Any]], team_name_by_id: Dict[str, str]
) -> Dict[str, Any]:
    records = []
    for g in games:
        records.append(
            {
                "game_no": g.get("game_no"),
                "home_team_id": g.get("home_team_id"),
                "away_team_id": g.get("away_team_id"),
                "start": _parse_dt(g["start_ts"]),
                "end": _parse_dt(g["end_ts"]),
            }
        )

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
                back_to_backs.append(
                    {
                        "team_id": team_id,
                        "team_name": team_name_by_id.get(team_id, team_id),
                        "rest_minutes": round(rest_minutes, 1),
                        "games": [a["game_no"], b["game_no"]],
                    }
                )

        if rests:
            rest_stats.append(
                {
                    "team_id": team_id,
                    "team_name": team_name_by_id.get(team_id, team_id),
                    "min_rest": round(min(rests), 1),
                    "avg_rest": round(sum(rests) / len(rests), 1),
                }
            )
        else:
            rest_stats.append(
                {
                    "team_id": team_id,
                    "team_name": team_name_by_id.get(team_id, team_id),
                    "min_rest": None,
                    "avg_rest": None,
                }
            )

    # Simple scoring: start at 100, subtract penalties for back-to-backs
    score = 100 - (10 * len(back_to_backs))
    score = max(0, score)

    # Top offenders (who has most back-to-backs)
    offender_counts: Dict[str, int] = {}
    for b2b in back_to_backs:
        offender_counts[b2b["team_name"]] = offender_counts.get(b2b["team_name"], 0) + 1

    top_offenders = sorted(offender_counts.items(), key=lambda x: x[1], reverse=True)[
        :3
    ]

    return {
        "score": score,
        "back_to_back_total": len(back_to_backs),
        "top_offenders": [
            {"team_name": name, "count": cnt} for name, cnt in top_offenders
        ],
        "rest_stats": rest_stats,
    }


def _dt_to_iso(dt: datetime) -> str:
    # Always serialize as ISO for JSON (preserve timezone if present).
    return dt.isoformat()


def _gap_minutes(a_end: datetime, b_start: datetime) -> float:
    return (b_start - a_end).total_seconds() / 60.0


@dataclass(frozen=True)
class Slot:
    # A discrete scheduling slot (one time window).
    idx: int
    start: datetime
    end: datetime


def _build_slots(time_windows: List[Any]) -> List[Slot]:
    # time_windows are ORM rows; we assume they have start_ts and end_ts datetime fields.
    tw_sorted = sorted(time_windows, key=lambda w: w.start_ts)
    return [
        Slot(idx=i, start=w.start_ts, end=w.end_ts) for i, w in enumerate(tw_sorted)
    ]


def _round_robin_matchups(team_ids: List[str]) -> List[Tuple[str, str]]:
    # Generates all pairings (n choose 2) deterministically.
    # (We don’t care about home/away semantics here; just return two IDs.)
    matchups = []
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            matchups.append((team_ids[i], team_ids[j]))
    return matchups


def _upper_bound_capacity(num_teams: int, num_venues: int, num_slots: int) -> int:
    # In a single slot, you can’t schedule more games than:
    # - number of venues, and
    # - floor(num_teams / 2) (each game consumes 2 teams)
    per_slot = min(num_venues, num_teams // 2)
    return per_slot * num_slots


def _min_gap_between_slots(slots: List[Slot]) -> Optional[float]:
    if len(slots) < 2:
        return None
    gaps = []
    for i in range(len(slots) - 1):
        gaps.append(_gap_minutes(slots[i].end, slots[i + 1].start))
    return min(gaps) if gaps else None


def _solve_schedule_backtracking(
    matchups: List[Tuple[str, str]],
    slots: List[Slot],
    venue_ids: List[str],
    min_rest_minutes: int,
    max_nodes: int = 200_000,
) -> Optional[List[Dict[str, Any]]]:
    """
    Backtracking solver assigning each matchup to (slot, venue).
    Returns schedule list if solvable, else None.
    """

    # Track used venues per slot index.
    used_venues_by_slot: List[set[str]] = [set() for _ in slots]

    # Track which teams are already playing in each slot (quick overlap check).
    used_teams_by_slot: List[set[str]] = [set() for _ in slots]

    # Track assigned intervals per team to enforce rest rule.
    # team_id -> list of (start, end)
    team_intervals: Dict[str, List[Tuple[datetime, datetime]]] = {}

    # Current partial assignment: list of dicts for scheduled games
    assignment: List[Dict[str, Any]] = []

    # Node counter to avoid runaway search
    nodes = 0

    # Heuristic: schedule “harder” matchups first is usually better.
    # We’ll just keep deterministic ordering as given.
    def can_place(team_a: str, team_b: str, slot: Slot, venue_id: str) -> bool:
        # Venue already occupied in this slot?
        if venue_id in used_venues_by_slot[slot.idx]:
            return False

        # Either team already playing in this slot?
        if (
            team_a in used_teams_by_slot[slot.idx]
            or team_b in used_teams_by_slot[slot.idx]
        ):
            return False

        # Rest rule check vs existing intervals for team_a and team_b.
        for team_id in (team_a, team_b):
            for s, e in team_intervals.get(team_id, []):
                # Overlap is automatically invalid.
                if _overlaps(s, e, slot.start, slot.end):
                    return False

                # Rest gap invalid on either side.
                # If new slot after existing interval:
                if slot.start >= e and _gap_minutes(e, slot.start) < min_rest_minutes:
                    return False
                # If new slot before existing interval:
                if s >= slot.end and _gap_minutes(slot.end, s) < min_rest_minutes:
                    return False

        return True

    def place(team_a: str, team_b: str, slot: Slot, venue_id: str):
        used_venues_by_slot[slot.idx].add(venue_id)
        used_teams_by_slot[slot.idx].add(team_a)
        used_teams_by_slot[slot.idx].add(team_b)

        team_intervals.setdefault(team_a, []).append((slot.start, slot.end))
        team_intervals.setdefault(team_b, []).append((slot.start, slot.end))

        assignment.append(
            {
                "home_team_id": team_a,
                "away_team_id": team_b,
                "start_ts": _dt_to_iso(slot.start),
                "end_ts": _dt_to_iso(slot.end),
                "venue_id": venue_id,
            }
        )

    def unplace(team_a: str, team_b: str, slot: Slot, venue_id: str):
        used_venues_by_slot[slot.idx].remove(venue_id)
        used_teams_by_slot[slot.idx].remove(team_a)
        used_teams_by_slot[slot.idx].remove(team_b)

        team_intervals[team_a].remove((slot.start, slot.end))
        team_intervals[team_b].remove((slot.start, slot.end))

        assignment.pop()

    # Precompute all candidate placements (slot, venue) in deterministic order.
    candidates: List[Tuple[Slot, str]] = []
    for slot in slots:
        for v in venue_ids:
            candidates.append((slot, v))

    def backtrack(i: int) -> bool:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            return False

        if i == len(matchups):
            return True

        team_a, team_b = matchups[i]

        for slot, venue_id in candidates:
            if can_place(team_a, team_b, slot, venue_id):
                place(team_a, team_b, slot, venue_id)
                if backtrack(i + 1):
                    return True
                unplace(team_a, team_b, slot, venue_id)

        return False

    ok = backtrack(0)
    if not ok:
        return None

    # Assign game numbers deterministically
    # (Sort by start time, then venue to make output stable)
    assignment_sorted = sorted(
        assignment,
        key=lambda g: (
            g["start_ts"],
            g["venue_id"],
            g["home_team_id"],
            g["away_team_id"],
        ),
    )

    final_schedule = []
    for idx, g in enumerate(assignment_sorted, start=1):
        final_schedule.append({**g, "game_no": idx})

    return final_schedule


def _generate_best_effort_schedule(
    matchups: List[Tuple[str, str]],
    slots: List[Slot],
    venue_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Deterministic draft schedule that may violate constraints.
    This is used ONLY when the solver cannot find a PASS schedule.
    """
    if not slots or not venue_ids:
        return []

    games = []
    for i, (a, b) in enumerate(matchups):
        slot = slots[i % len(slots)]
        venue_id = venue_ids[i % len(venue_ids)]

        games.append(
            {
                "game_no": i + 1,
                "home_team_id": a,
                "away_team_id": b,
                "start_ts": _dt_to_iso(slot.start),
                "end_ts": _dt_to_iso(slot.end),
                "venue_id": venue_id,
            }
        )

    return games


def _build_guidance_error(
    num_teams, num_venues, time_windows, games_needed, min_rest_minutes
):
    # upper bound: per window you can schedule min(venues, floor(teams/2)) games
    per_window = max(1, min(num_venues, num_teams // 2))
    capacity = per_window * len(time_windows)

    guidance = []

    if capacity < games_needed:
        windows_needed = math.ceil(games_needed / per_window)
        extra = max(0, windows_needed - len(time_windows))
        guidance.append(
            f"Add at least {extra} more time window(s), or add venues, to reach capacity."
        )

    # min gap between consecutive windows
    if len(time_windows) >= 2:
        tw = sorted(time_windows, key=lambda w: w.start_ts)
        gaps = []
        for i in range(len(tw) - 1):
            gaps.append((tw[i + 1].start_ts - tw[i].end_ts).total_seconds() / 60.0)
        min_gap = min(gaps) if gaps else None
        if min_gap is not None and min_gap < min_rest_minutes:
            guidance.append(
                f"Your smallest gap between time windows is {int(min_gap)} min, but min rest is {min_rest_minutes} min. "
                "Add breaks between windows or reduce min rest."
            )

    if not guidance:
        guidance.append(
            "Add more time windows or venues, or relax constraints. No valid schedule was found."
        )

    return {
        "reason_code": "INFEASIBLE",
        "message": "Unable to generate a valid schedule with the current constraints.",
        "inputs": {
            "teams": num_teams,
            "venues": num_venues,
            "time_windows": len(time_windows),
            "games_needed": games_needed,
            "min_rest_minutes": min_rest_minutes,
        },
        "capacity": {"upper_bound_games_possible": capacity},
        "guidance": guidance,
    }


def _infeasible_explanation(
    num_teams: int,
    num_venues: int,
    slots: List[Slot],
    games_needed: int,
    min_rest_minutes: int,
) -> Dict[str, Any]:
    # Capacity upper bound
    capacity = _upper_bound_capacity(num_teams, num_venues, len(slots))
    min_gap = _min_gap_between_slots(slots)

    guidance = []

    if capacity < games_needed:
        # How many extra slots needed at minimum (upper bound math)
        per_slot = max(1, min(num_venues, num_teams // 2))
        slots_needed = math.ceil(games_needed / per_slot)
        extra_slots = max(0, slots_needed - len(slots))
        guidance.append(
            f"Add at least {extra_slots} more time window(s), or add venues, to reach capacity."
        )

    if min_gap is not None and min_gap < min_rest_minutes:
        guidance.append(
            f"Your time windows have a minimum gap of {int(min_gap)} minutes, but min rest is {min_rest_minutes}. "
            "Add breaks between windows or reduce the min-rest requirement."
        )

    if not guidance:
        guidance.append(
            "Try adding more time windows or venues, or relaxing constraints. The solver could not find a valid arrangement."
        )

    return {
        "reason_code": "INFEASIBLE",
        "message": "Unable to generate a valid schedule with the current constraints.",
        "inputs": {
            "teams": num_teams,
            "venues": num_venues,
            "time_windows": len(slots),
            "games_needed": games_needed,
            "min_rest_minutes": min_rest_minutes,
        },
        "capacity": {
            "upper_bound_games_possible": capacity,
        },
        "guidance": guidance,
    }


@router.get("/tournaments", response_model=list[TournamentListItem])
async def list_tournaments(db: AsyncSession = Depends(get_db_rls)):
    rows = (
        (
            await db.execute(
                select(Tournament).order_by(Tournament.created_at.desc()).limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [
        TournamentListItem(id=t.id, name=t.name, created_at=t.created_at) for t in rows
    ]


@router.get("/tournaments/{tournament_id}", response_model=TournamentOut)
async def get_tournament(tournament_id: UUID, db: AsyncSession = Depends(get_db_rls)):
    t = (
        await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    ).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return TournamentOut(id=t.id, name=t.name, created_at=t.created_at)


@router.post("/tournaments", response_model=TournamentOut)
async def create_tournament(
    payload: TournamentCreateIn,
    user_id: UUID = Depends(require_user_id),
    db: AsyncSession = Depends(get_db_rls),
):
    # --- Step 3D: backend validation for time windows ---
    if not payload.time_windows or len(payload.time_windows) < 1:
        raise HTTPException(status_code=422, detail="Add at least 1 time window.")

    now = datetime.now(timezone.utc)

    for i, tw in enumerate(payload.time_windows):
        if tw.start_ts is None or tw.end_ts is None:
            raise HTTPException(
                status_code=422,
                detail=f"Time window #{i + 1} must have start_ts and end_ts.",
            )

        # If datetimes come in naive, treat them as UTC (consistent enforcement)
        start = (
            tw.start_ts
            if tw.start_ts.tzinfo
            else tw.start_ts.replace(tzinfo=timezone.utc)
        )
        end = tw.end_ts if tw.end_ts.tzinfo else tw.end_ts.replace(tzinfo=timezone.utc)

        if start < now:
            raise HTTPException(
                status_code=422,
                detail=f"Time window #{i + 1} cannot start in the past.",
            )
        if end <= start:
            raise HTTPException(
                status_code=422,
                detail=f"Time window #{i + 1} end_ts must be after start_ts.",
            )

    # --- Resolve org_id from current user identity (set by get_db_rls / RLS identity) ---
    org_id = (
        await db.execute(
            text("select org_id from org_members where user_id = :uid limit 1"),
            {"uid": user_id},
        )
    ).scalar_one_or_none()

    val = (await db.execute(text("select current_setting('app.user_id', true)"))).scalar_one()
    print("DEBUG app.user_id =", repr(val))

    if not org_id:
        raise HTTPException(status_code=403, detail="User is not a member of any org.")


    # --- Create tournament ---
    t = Tournament(name=payload.name, org_id=org_id)
    db.add(t)
    await db.flush()  # get t.id

    for team in payload.teams:
        db.add(Team(tournament_id=t.id, name=team.name, org_id=org_id))

    for venue in payload.venues:
        db.add(Venue(tournament_id=t.id, name=venue.name, org_id=org_id))


    # Need venue IDs if user wants to pin time windows to venues
    await db.flush()

    for tw in payload.time_windows:
        db.add(
            TimeWindow(
                tournament_id=t.id,
                start_ts=tw.start_ts,
                end_ts=tw.end_ts,
                venue_id=tw.venue_id,
            )
        )

    await db.commit()
    await db.refresh(t)
    return TournamentOut(id=t.id, name=t.name, created_at=t.created_at)

def _norm(s: str) -> str:
        return " ".join(s.strip().lower().split())


@router.post("/tournaments/{tournament_id}/generate", response_model=GenerateOut)
async def generate_schedule(
    tournament_id: UUID, db: AsyncSession = Depends(get_db_rls)
):
    t = (
        await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    ).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    teams = (
        (await db.execute(select(Team).where(Team.tournament_id == tournament_id)))
        .scalars()
        .all()
    )
    venues = (
        (await db.execute(select(Venue).where(Venue.tournament_id == tournament_id)))
        .scalars()
        .all()
    )
    time_windows = (
        (
            await db.execute(
                select(TimeWindow)
                .where(TimeWindow.tournament_id == tournament_id)
                .order_by(TimeWindow.start_ts)
            )
        )
        .scalars()
        .all()
    )

    
    # Reject duplicate team names (case/whitespace-insensitive)
    counts = Counter(teams)
    dupes = sorted({name for name, c in counts.items() if c > 1})
    if dupes:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate team name(s) not allowed: {', '.join(dupes)}",
        )

    venue_names = [_norm(v.name) for v in venues if v.name and v.name.strip()]
    counts = Counter(venue_names)
    dupes = sorted({name for name, c in counts.items() if c > 1})
    if dupes:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate venue name(s) not allowed: {', '.join(dupes)}",
        )


    if len(teams) < 2:
        raise HTTPException(
            status_code=400, detail="Need at least 2 teams to generate a schedule"
        )
    if len(time_windows) < 1:
        raise HTTPException(
            status_code=400, detail="Need at least 1 time window to generate a schedule"
        )
    if len(venues) < 1:
        raise HTTPException(
            status_code=400, detail="Need at least 1 venue to generate a schedule"
        )

    team_ids = sorted([str(x.id) for x in teams])
    venue_ids = [str(v.id) for v in venues]
    windows = [
        {
            "start_ts": tw.start_ts.isoformat(),
            "end_ts": tw.end_ts.isoformat(),
            "venue_id": str(tw.venue_id) if tw.venue_id else None,
        }
        for tw in time_windows
    ]
    input_obj = {"teams": team_ids, "venues": venue_ids, "time_windows": windows}
    input_hash = _stable_hash(input_obj)

    # Build matchups
    matchups = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            matchups.append((str(teams[i].id), str(teams[j].id)))
    games_needed = len(matchups)

    team_name_by_id = {str(x.id): x.name for x in teams}
    venue_name_by_id = {str(v.id): v.name for v in venues}

    slots = _build_slots(time_windows)
    min_rest_minutes = 60

    # Guidance (used when failing)
    error_json = _build_guidance_error(
        num_teams=len(team_ids),
        num_venues=len(venue_ids),
        time_windows=time_windows,
        games_needed=games_needed,
        min_rest_minutes=min_rest_minutes,
    )

    # 1) Try to solve PASS schedule
    solved = _solve_schedule_backtracking(
        matchups=matchups,
        slots=slots,
        venue_ids=venue_ids,
        min_rest_minutes=min_rest_minutes,
    )

    if solved is not None:
        integrity_solved = _compute_integrity(solved, team_name_by_id, venue_name_by_id)
        fairness_solved = _compute_fairness(solved, team_name_by_id)

        metrics_solved = {
            "games_total": len(solved),
            "teams_total": len(teams),
            "venues_total": len(venues),
            "time_windows_total": len(time_windows),
            "integrity": integrity_solved,
            "fairness": fairness_solved,
        }

        if integrity_solved.get("status") == "PASS":
            org_id = (
                await db.execute(
                    text("select org_id from tournaments where id = :tid"),
                    {"tid": tournament_id},
                )
            ).scalar_one_or_none()
            run = ScheduleRun(
                tournament_id=tournament_id,
                status="SUCCESS",
                org_id=org_id,
                input_hash=input_hash,
                schedule_json={"games": solved},
                metrics_json=metrics_solved,
                error_json=None,
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
            return GenerateOut(run_id=run.id, status=run.status)

    # 2) Draft fallback (FAILED but still show schedule + reasons + guidance)
    draft = _generate_best_effort_schedule(matchups, slots, venue_ids)

    integrity = _compute_integrity(draft, team_name_by_id, venue_name_by_id)
    fairness = _compute_fairness(draft, team_name_by_id)

    metrics = {
        "games_total": len(draft),
        "teams_total": len(teams),
        "venues_total": len(venues),
        "time_windows_total": len(time_windows),
        "integrity": integrity,
        "fairness": fairness,
    }

    org_id = (
        await db.execute(
            text("select org_id from tournaments where id = :tid"),
            {"tid": tournament_id},
        )
    ).scalar_one()


    run = ScheduleRun(
        tournament_id=tournament_id,
        org_id=org_id,
        status="FAILED",
        input_hash=input_hash,
        schedule_json={"games": draft},
        metrics_json=metrics,
        error_json=error_json,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return GenerateOut(run_id=run.id, status=run.status)


@router.get("/tournaments/{tournament_id}/latest-run", response_model=ScheduleRunOut)
async def latest_run(tournament_id: UUID, db: AsyncSession = Depends(get_db_rls)):
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
    teams = (
        (await db.execute(select(Team).where(Team.tournament_id == tournament_id)))
        .scalars()
        .all()
    )
    venues = (
        (await db.execute(select(Venue).where(Venue.tournament_id == tournament_id)))
        .scalars()
        .all()
    )

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

            decorated_games.append(
                {
                    **g,
                    "home_team_name": team_name_by_id.get(home_id, home_id),
                    "away_team_name": team_name_by_id.get(away_id, away_id),
                    "venue_name": venue_name_by_id.get(venue_id, venue_id),
                }
            )

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
