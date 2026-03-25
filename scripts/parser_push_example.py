from __future__ import annotations

import os

import httpx


API_URL = os.getenv("COLIBRI_API_URL", "http://127.0.0.1:8000/api/ingest/offer")
API_KEY = os.getenv("COLIBRI_API_KEY", "change-me")

payload = {
    "role": "traveler",
    "source_name": "travelask_parser",
    "source_offer_id": "example-001",
    "from_city": "Belgrade",
    "to_city": "Vienna",
    "travel_date": "2026-03-28",
    "weight_kg": 5,
    "description": "Могу взять небольшую посылку до 5 кг",
    "handoff_time_text": "28.03.2026, 14:00–16:00",
    "handoff_location": "Белград, парковка у ТЦ Galerija",
    "payment_instructions": "Оплата производится в момент передачи посылки на карту **** 1234",
    "internal_contact_ref": "tg:@hidden_contact",
    "raw_payload": {"source_channel": "TravelAsk", "message_id": 12345},
    "is_active": True,
}

headers = {"Authorization": f"Bearer {API_KEY}"}
response = httpx.post(API_URL, json=payload, headers=headers, timeout=30)
print(response.status_code)
print(response.text)
