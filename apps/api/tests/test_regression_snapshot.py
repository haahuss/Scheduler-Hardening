# apps/api/tests/test_regression_snapshot.py
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.routes import Slot, _generate_best_effort_schedule


FIX = Path(__file__).parent / "fixtures" / "tourney_small.json"
SNAP = Path(__file__).parent / "snapshots" / "tourney_small_draft.json"


def _parse_dt(dt_str: str) -> datetime:
    # handles "...Z"
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def _slots_from_time_windows(time_windows: list[dict]) -> list[Slot]:
    tw_sorted = sorted(time_windows, key=lambda w: w["start_ts"])
    slots: list[Slot] = []
    for i, tw in enumerate(tw_sorted):
        slots.append(
            Slot(idx=i, start=_parse_dt(tw["start_ts"]), end=_parse_dt(tw["end_ts"]))
        )
    return slots


def _round_robin_matchups(team_ids: list[str]) -> list[tuple[str, str]]:
    matchups: list[tuple[str, str]] = []
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            matchups.append((team_ids[i], team_ids[j]))
    return matchups


def test_scheduler_regression_snapshot():
    payload = json.loads(FIX.read_text())

    teams = [f"team-{i}" for i, _ in enumerate(payload["teams"])]
    venues = [f"venue-{i}" for i, _ in enumerate(payload["venues"])]

    matchups = _round_robin_matchups(teams)
    slots = _slots_from_time_windows(payload["time_windows"])

    games = _generate_best_effort_schedule(matchups, slots, venues)

    # stable-ish snapshot payload
    snap_obj = {
        "slots": [
            {
                **asdict(s),
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
            }
            for s in slots
        ],
        "venues": venues,
        "games": games,
    }

    if SNAP.exists() and not (Path.cwd() / ".update_snapshots").exists():
        expected = json.loads(SNAP.read_text())
        assert snap_obj == expected
    else:
        SNAP.parent.mkdir(parents=True, exist_ok=True)
        SNAP.write_text(json.dumps(snap_obj, indent=2, sort_keys=True))
        # If you hit this locally, commit the new snapshot file.
        assert True
