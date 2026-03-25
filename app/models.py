from __future__ import annotations

from datetime import datetime, date
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RequestRole(str, Enum):
    sender = "sender"
    traveler = "traveler"


class RecordStatus(str, Enum):
    pending = "pending"
    active = "active"
    matched = "matched"
    closed = "closed"
    archived = "archived"


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations: Mapped[list[BotConversation]] = relationship(back_populates="user")
    requests: Mapped[list[UserRequest]] = relationship(back_populates="user")


class BotConversation(Base):
    __tablename__ = "bot_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id"), index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[BotUser] = relationship(back_populates="conversations")
    messages: Mapped[list[BotMessage]] = relationship(back_populates="conversation")


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("bot_conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20))
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped[BotConversation] = relationship(back_populates="messages")


class UserRequest(Base):
    __tablename__ = "user_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id"), index=True)
    role: Mapped[RequestRole] = mapped_column(SAEnum(RequestRole), index=True)
    from_city: Mapped[str] = mapped_column(String(255), index=True)
    to_city: Mapped[str] = mapped_column(String(255), index=True)
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_unique_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.pending, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[BotUser] = relationship(back_populates="requests")
    matches: Mapped[list[Match]] = relationship(back_populates="request")


class ParsedOffer(Base):
    __tablename__ = "parsed_offers"
    __table_args__ = (UniqueConstraint("source_name", "source_offer_id", name="uq_source_offer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[RequestRole] = mapped_column(SAEnum(RequestRole), index=True)
    source_name: Mapped[str] = mapped_column(String(100), index=True)
    source_offer_id: Mapped[str] = mapped_column(String(255), index=True)
    from_city: Mapped[str] = mapped_column(String(255), index=True)
    to_city: Mapped[str] = mapped_column(String(255), index=True)
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    handoff_time_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    handoff_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_contact_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    matches: Mapped[list[Match]] = relationship(back_populates="offer")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("user_requests.id"), index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("parsed_offers.id"), index=True)
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.matched, index=True)
    message_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped[UserRequest] = relationship(back_populates="matches")
    offer: Mapped[ParsedOffer] = relationship(back_populates="matches")
