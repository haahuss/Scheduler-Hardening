# apps/api/tests/test_fuzz_scheduler.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings, strategies as st

from app.routes import Slot, _generate_best_effort_schedule


def _make_matchups(team_ids: list[str]) -> list[tuple[str, str]]:
    matchups: list[tuple[str, str]] = []
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            matchups.append((team_ids[i], team_ids[j]))
    return matchups


def _make_slots(slot_count: int) -> list[Slot]:
    base = datetime.now(timezone.utc) + timedelta(days=1)
    slots: list[Slot] = []
    for i in range(slot_count):
        start = base + timedelta(hours=i)
        end = start + timedelta(hours=1)
        slots.append(Slot(idx=i, start=start, end=end))
    return slots


@settings(max_examples=75, deadline=None)
@given(
    team_count=st.integers(min_value=2, max_value=8),
    venue_count=st.integers(min_value=1, max_value=4),
    slot_count=st.integers(min_value=1, max_value=12),
)
def test_generate_best_effort_never_crashes_and_obeys_basic_invariants(
    team_count: int,
    venue_count: int,
    slot_count: int,
):
    team_ids = [f"team-{i}" for i in range(team_count)]
    venue_ids = [f"venue-{i}" for i in range(venue_count)]
    matchups = _make_matchups(team_ids)
    slots = _make_slots(slot_count)

    games = _generate_best_effort_schedule(matchups, slots, venue_ids)

    # basic invariants: shape + required fields
    assert isinstance(games, list)
    for g in games:
        assert "home_team_id" in g and "away_team_id" in g
        assert "start_ts" in g and "end_ts" in g
        assert "venue_id" in g
        assert g["home_team_id"] != g["away_team_id"]
        assert g["venue_id"] in venue_ids

    # best-effort fills one entry per matchup (unless no slots/venues; but we always have >=1)
    assert len(games) == len(matchups)
