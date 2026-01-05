from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime


def _dt_to_iso(dt: datetime) -> str:
    # Always serialize as ISO (timezone-preserving if tz-aware)
    return dt.isoformat()


def _generate_best_effort_schedule(
    matchups: List[Tuple[str, str]],
    slots: List[Slot],
    venue_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Deterministic draft schedule that may violate constraints.
    Used ONLY when the solver cannot find a PASS schedule.
    """
    if not slots or not venue_ids:
        return []

    games: List[Dict[str, Any]] = []
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
