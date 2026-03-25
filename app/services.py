from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .matcher import create_match_if_possible
from .models import (
    BotConversation,
    BotMessage,
    BotUser,
    Match,
    ParsedOffer,
    RecordStatus,
    RequestRole,
    UserRequest,
)
from .schemas import IngestOfferIn, MatchView


def init_db() -> None:
    from .db import engine
    from .models import Base

    Base.metadata.create_all(bind=engine)


def get_or_create_bot_user(
    session: Session,
    telegram_user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> BotUser:
    user = session.scalar(select(BotUser).where(BotUser.telegram_user_id == telegram_user_id))
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        session.flush()
        return user

    user = BotUser(
        telegram_user_id=telegram_user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    session.flush()
    return user


def get_or_create_open_conversation(session: Session, bot_user_id: int) -> BotConversation:
    conversation = session.scalar(
        select(BotConversation)
        .where(BotConversation.bot_user_id == bot_user_id)
        .where(BotConversation.is_open.is_(True))
        .order_by(BotConversation.created_at.desc())
    )
    if conversation:
        return conversation

    conversation = BotConversation(bot_user_id=bot_user_id, is_open=True)
    session.add(conversation)
    session.flush()
    return conversation


def save_bot_message(
    session: Session,
    conversation_id: int,
    direction: str,
    message_text: str | None,
    telegram_message_id: int | None = None,
) -> BotMessage:
    message = BotMessage(
        conversation_id=conversation_id,
        direction=direction,
        message_text=message_text,
        telegram_message_id=telegram_message_id,
    )
    session.add(message)
    session.flush()
    return message


def create_user_request(
    session: Session,
    bot_user_id: int,
    role: RequestRole,
    from_city: str,
    to_city: str,
    travel_date,
    weight_kg: float,
    description: str | None,
    photo_file_id: str | None,
    photo_unique_id: str | None,
    raw_payload: dict | None = None,
) -> UserRequest:
    request = UserRequest(
        bot_user_id=bot_user_id,
        role=role,
        from_city=from_city.strip(),
        to_city=to_city.strip(),
        travel_date=travel_date,
        weight_kg=weight_kg,
        description=description,
        photo_file_id=photo_file_id,
        photo_unique_id=photo_unique_id,
        raw_payload=json.dumps(raw_payload, ensure_ascii=False) if raw_payload else None,
        status=RecordStatus.pending,
    )
    session.add(request)
    session.flush()
    return request


def upsert_parsed_offer(session: Session, data: IngestOfferIn) -> ParsedOffer:
    offer = session.scalar(
        select(ParsedOffer)
        .where(ParsedOffer.source_name == data.source_name)
        .where(ParsedOffer.source_offer_id == data.source_offer_id)
    )
    if not offer:
        offer = ParsedOffer(source_name=data.source_name, source_offer_id=data.source_offer_id, role=data.role)
        session.add(offer)

    offer.role = data.role
    offer.from_city = data.from_city.strip()
    offer.to_city = data.to_city.strip()
    offer.travel_date = data.travel_date
    offer.weight_kg = data.weight_kg
    offer.description = data.description
    offer.handoff_time_text = data.handoff_time_text
    offer.handoff_location = data.handoff_location
    offer.payment_instructions = data.payment_instructions
    offer.internal_contact_ref = data.internal_contact_ref
    offer.raw_payload = json.dumps(data.raw_payload, ensure_ascii=False) if data.raw_payload else None
    offer.is_active = data.is_active
    offer.updated_at = datetime.utcnow()
    session.flush()
    return offer


def try_match_request(session: Session, request_id: int) -> Match | None:
    request = session.get(UserRequest, request_id)
    if not request:
        return None
    return create_match_if_possible(session, request)


def try_match_offer_against_pending_requests(session: Session, offer_id: int) -> list[Match]:
    offer = session.get(ParsedOffer, offer_id)
    if not offer:
        return []

    target_request_role = RequestRole.sender if offer.role == RequestRole.traveler else RequestRole.traveler
    pending_requests = session.scalars(
        select(UserRequest)
        .where(UserRequest.role == target_request_role)
        .where(UserRequest.status == RecordStatus.pending)
        .where(func.lower(UserRequest.from_city) == offer.from_city.lower())
    ).all()

    matched: list[Match] = []
    for request in pending_requests:
        if request.to_city.lower() != offer.to_city.lower():
            continue
        if request.travel_date > offer.travel_date:
            continue
        if request.weight_kg > offer.weight_kg:
            continue
        match = create_match_if_possible(session, request)
        if match:
            matched.append(match)
    return matched


def build_dispatch_text(match: Match) -> str:
    offer = match.offer
    request = match.request
    handoff_location = offer.handoff_location or settings.default_handoff_location
    handoff_time = offer.handoff_time_text or offer.travel_date.strftime("%d.%m.%Y")
    payment_instructions = offer.payment_instructions or settings.default_payment_instructions

    template = (
        settings.default_sender_success_template
        if request.role == RequestRole.sender
        else settings.default_traveler_success_template
    )
    return template.format(
        from_city=request.from_city,
        to_city=request.to_city,
        handoff_time=handoff_time,
        handoff_location=handoff_location,
        payment_instructions=payment_instructions,
    )


def to_match_view(match: Match) -> MatchView:
    offer = match.offer
    return MatchView(
        match_id=match.id,
        request_id=match.request_id,
        offer_id=match.offer_id,
        role=offer.role,
        from_city=offer.from_city,
        to_city=offer.to_city,
        travel_date=offer.travel_date,
        weight_kg=offer.weight_kg,
        description=offer.description,
        handoff_time_text=offer.handoff_time_text,
        handoff_location=offer.handoff_location,
        payment_instructions=offer.payment_instructions,
        internal_contact_ref=offer.internal_contact_ref,
    )
