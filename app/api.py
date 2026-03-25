from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .schemas import HealthResponse, IngestOfferIn, IngestOfferOut, MatchResponse
from .services import init_db, to_match_view, try_match_offer_against_pending_requests, try_match_request, upsert_parsed_offer


app = FastAPI(title="Colibri Dispatch API")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.bot_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/ingest/offer", response_model=IngestOfferOut, dependencies=[Depends(require_api_key)])
def ingest_offer(payload: IngestOfferIn, session: Session = Depends(db_session)) -> IngestOfferOut:
    offer = upsert_parsed_offer(session, payload)
    try_match_offer_against_pending_requests(session, offer.id)
    return IngestOfferOut(ok=True, offer_id=offer.id)


@app.post("/api/match/request/{request_id}", response_model=MatchResponse, dependencies=[Depends(require_api_key)])
def match_request(request_id: int, session: Session = Depends(db_session)) -> MatchResponse:
    match = try_match_request(session, request_id)
    if not match:
        return MatchResponse(ok=True, found=False, match=None)
    return MatchResponse(ok=True, found=True, match=to_match_view(match))
