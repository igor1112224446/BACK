from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from .models import RequestRole


class IngestOfferIn(BaseModel):
    role: RequestRole
    source_name: str = Field(..., max_length=100)
    source_offer_id: str = Field(..., max_length=255)
    from_city: str
    to_city: str
    travel_date: date
    weight_kg: float = Field(..., gt=0)
    description: str | None = None
    handoff_time_text: str | None = None
    handoff_location: str | None = None
    payment_instructions: str | None = None
    internal_contact_ref: str | None = None
    raw_payload: dict[str, Any] | None = None
    is_active: bool = True


class IngestOfferOut(BaseModel):
    ok: bool
    offer_id: int


class MatchView(BaseModel):
    match_id: int
    request_id: int
    offer_id: int
    role: RequestRole
    from_city: str
    to_city: str
    travel_date: date
    weight_kg: float
    description: str | None
    handoff_time_text: str | None
    handoff_location: str | None
    payment_instructions: str | None
    internal_contact_ref: str | None


class MatchResponse(BaseModel):
    ok: bool
    found: bool
    match: MatchView | None = None


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "colibri-dispatch-api"
