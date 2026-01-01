from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class VenueIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TimeWindowIn(BaseModel):
    start_ts: datetime
    end_ts: datetime
    venue_id: Optional[UUID] = None


class TournamentCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    teams: List[TeamIn] = Field(default_factory=list)
    venues: List[VenueIn] = Field(default_factory=list)
    time_windows: List[TimeWindowIn] = Field(default_factory=list)


class TournamentOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class GenerateOut(BaseModel):
    run_id: UUID
    status: str


class ScheduleRunOut(BaseModel):
    id: UUID
    tournament_id: UUID
    created_at: datetime
    status: str
    input_hash: str
    schedule_json: Optional[Any] = None
    metrics_json: Optional[Dict[str, Any]] = None
    error_json: Optional[Dict[str, Any]] = None

class TournamentListItem(BaseModel):
    id: UUID
    name: str
    created_at: datetime
