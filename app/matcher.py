from __future__ import annotations

from datetime import date

from sqlalchemy import Select, asc, case, desc, func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Match, ParsedOffer, RecordStatus, RequestRole, UserRequest


TARGET_ROLE = {
    RequestRole.sender: RequestRole.traveler,
    RequestRole.traveler: RequestRole.sender,
}


def _city_priority(column, value: str):
    return case((func.lower(column) == value.lower(), 0), else_=1)


def _date_gap(column, value: date):
    # works in sqlite and postgres differently; julianday is sqlite specific, date subtraction is postgres.
    # For cross-db simplicity, just order by date itself after filtering.
    return asc(column)


def _weight_excess(column, value: float):
    return asc(column)


def build_offer_query(request: UserRequest) -> Select:
    stmt = (
        select(ParsedOffer)
        .where(ParsedOffer.is_active.is_(True))
        .where(ParsedOffer.role == TARGET_ROLE[request.role])
        .where(func.lower(ParsedOffer.from_city) == request.from_city.lower())
        .where(func.lower(ParsedOffer.to_city) == request.to_city.lower())
        .where(ParsedOffer.travel_date >= request.travel_date)
        .where(ParsedOffer.weight_kg >= request.weight_kg)
        .order_by(
            _city_priority(ParsedOffer.from_city, request.from_city),
            _city_priority(ParsedOffer.to_city, request.to_city),
            _date_gap(ParsedOffer.travel_date, request.travel_date),
            _weight_excess(ParsedOffer.weight_kg, request.weight_kg),
            desc(ParsedOffer.created_at),
        )
        .limit(settings.results_limit)
    )
    return stmt


def find_best_offer(session: Session, request: UserRequest) -> ParsedOffer | None:
    stmt = build_offer_query(request)
    return session.scalars(stmt).first()


def create_match_if_possible(session: Session, request: UserRequest) -> Match | None:
    offer = find_best_offer(session, request)
    if not offer:
        return None

    existing = session.scalar(
        select(Match).where(Match.request_id == request.id).where(Match.offer_id == offer.id)
    )
    if existing:
        return existing

    match = Match(request_id=request.id, offer_id=offer.id, status=RecordStatus.matched)
    request.status = RecordStatus.matched
    from datetime import datetime

    request.matched_at = datetime.utcnow()
    session.add(match)
    session.flush()
    session.refresh(match)
    return match
