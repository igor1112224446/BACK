from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'colibri.db'}")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_api_key: str = os.getenv("BOT_API_KEY", "change-me")
    uploads_dir: str = os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads"))
    results_limit: int = int(os.getenv("RESULTS_LIMIT", "5"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    default_handoff_location: str = os.getenv(
        "DEFAULT_HANDOFF_LOCATION",
        "Точное место передачи уточнит оператор Colibri после подтверждения.",
    )
    default_payment_instructions: str = os.getenv(
        "DEFAULT_PAYMENT_INSTRUCTIONS",
        "Оплата производится в момент передачи посылки по реквизитам, которые направит Colibri.",
    )
    default_sender_success_template: str = os.getenv(
        "DEFAULT_SENDER_SUCCESS_TEMPLATE",
        (
            "Мы нашли для вас подходящего попутчика для вашей посылки.\n\n"
            "Маршрут: {from_city} → {to_city}\n"
            "Передача: {handoff_time}\n"
            "Место: {handoff_location}\n"
            "Оплата: {payment_instructions}"
        ),
    )
    default_traveler_success_template: str = os.getenv(
        "DEFAULT_TRAVELER_SUCCESS_TEMPLATE",
        (
            "Мы нашли для вас подходящую посылку для вашей поездки.\n\n"
            "Маршрут: {from_city} → {to_city}\n"
            "Передача: {handoff_time}\n"
            "Место: {handoff_location}\n"
            "Оплата: {payment_instructions}"
        ),
    )


settings = Settings()
Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)