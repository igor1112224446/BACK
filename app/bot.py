from __future__ import annotations

import logging
from datetime import datetime

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import settings
from .db import get_session
from .models import RecordStatus, RequestRole
from .services import (
    build_dispatch_text,
    create_user_request,
    get_or_create_bot_user,
    get_or_create_open_conversation,
    init_db,
    save_bot_message,
    try_match_request,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROLE, FROM_CITY, TO_CITY, DATE, WEIGHT, DESCRIPTION, PHOTO = range(7)

ROLE_LABELS = {
    "Хочу отправить посылку": RequestRole.sender,
    "Я попутчик": RequestRole.traveler,
}


def _main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Хочу отправить посылку")], [KeyboardButton("Я попутчик")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user or not update.message:
        return ConversationHandler.END

    with get_session() as session:
        bot_user = get_or_create_bot_user(session, user.id, user.username, user.first_name, user.last_name)
        conversation = get_or_create_open_conversation(session, bot_user.id)
        save_bot_message(session, conversation.id, "in", "/start", update.message.message_id)

    text = (
        "Привет. Я бот Colibri.\n\n"
        "Я соберу данные по вашей заявке, сохраню их в систему и, если найду совпадение, пришлю готовую инструкцию без передачи чужих контактов.\n\n"
        "Выберите, что вам нужно:"
    )
    await update.message.reply_text(text, reply_markup=_main_keyboard())
    return ROLE


async def role_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return ConversationHandler.END
    choice = update.message.text.strip()
    if choice not in ROLE_LABELS:
        await update.message.reply_text("Нажмите одну из двух кнопок.", reply_markup=_main_keyboard())
        return ROLE

    context.user_data["role"] = ROLE_LABELS[choice].value
    prompt = (
        "Укажите город отправления посылки."
        if ROLE_LABELS[choice] == RequestRole.sender
        else "Укажите город, откуда вы поедете."
    )
    await update.message.reply_text(prompt)
    return FROM_CITY


async def from_city_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    context.user_data["from_city"] = update.message.text.strip()
    prompt = (
        "Укажите город назначения посылки."
        if context.user_data.get("role") == RequestRole.sender.value
        else "Укажите город, куда вы направляетесь."
    )
    await update.message.reply_text(prompt)
    return TO_CITY


async def to_city_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    context.user_data["to_city"] = update.message.text.strip()
    prompt = (
        "Напишите дату, когда посылка должна быть отправлена, в формате ДД.ММ.ГГГГ."
        if context.user_data.get("role") == RequestRole.sender.value
        else "Напишите дату вашей поездки в формате ДД.ММ.ГГГГ."
    )
    await update.message.reply_text(prompt)
    return DATE


async def date_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    raw = update.message.text.strip()
    try:
        travel_date = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text("Нужен формат даты ДД.ММ.ГГГГ. Например: 28.03.2026")
        return DATE

    context.user_data["travel_date"] = travel_date.isoformat()
    prompt = (
        "Укажите вес посылки в килограммах. Например: 2.5"
        if context.user_data.get("role") == RequestRole.sender.value
        else "Укажите, сколько килограммов вы можете взять. Например: 10"
    )
    await update.message.reply_text(prompt)
    return WEIGHT


async def weight_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    raw = update.message.text.replace(",", ".").strip()
    try:
        weight = float(raw)
        if weight <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите число больше нуля. Например: 3 или 4.5")
        return WEIGHT

    context.user_data["weight_kg"] = weight
    prompt = (
        "Кратко опишите посылку. Например: документы, одежда, электроника."
        if context.user_data.get("role") == RequestRole.sender.value
        else "Кратко опишите, что вы готовы взять или какие есть ограничения."
    )
    await update.message.reply_text(prompt)
    return DESCRIPTION


async def description_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    context.user_data["description"] = update.message.text.strip()

    if context.user_data.get("role") == RequestRole.sender.value:
        await update.message.reply_text(
            "Теперь отправьте фотографию посылки одним сообщением. Если фото нет, напишите: нет",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PHOTO

    context.user_data["photo_file_id"] = None
    context.user_data["photo_unique_id"] = None
    return await finalize_request(update, context)


async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END

    if update.message.text and update.message.text.strip().lower() == "нет":
        context.user_data["photo_file_id"] = None
        context.user_data["photo_unique_id"] = None
        return await finalize_request(update, context)

    if not update.message.photo:
        await update.message.reply_text("Пришлите фото посылки или напишите: нет")
        return PHOTO

    photo = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo.file_id
    context.user_data["photo_unique_id"] = photo.file_unique_id
    return await finalize_request(update, context)


async def finalize_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return ConversationHandler.END

    role = RequestRole(context.user_data["role"])
    from_city = context.user_data["from_city"]
    to_city = context.user_data["to_city"]
    travel_date = datetime.fromisoformat(context.user_data["travel_date"]).date()
    weight_kg = float(context.user_data["weight_kg"])
    description = context.user_data.get("description")
    photo_file_id = context.user_data.get("photo_file_id")
    photo_unique_id = context.user_data.get("photo_unique_id")

    with get_session() as session:
        bot_user = get_or_create_bot_user(
            session,
            update.effective_user.id,
            update.effective_user.username,
            update.effective_user.first_name,
            update.effective_user.last_name,
        )
        conversation = get_or_create_open_conversation(session, bot_user.id)
        save_bot_message(session, conversation.id, "in", str(context.user_data), update.message.message_id)
        request = create_user_request(
            session=session,
            bot_user_id=bot_user.id,
            role=role,
            from_city=from_city,
            to_city=to_city,
            travel_date=travel_date,
            weight_kg=weight_kg,
            description=description,
            photo_file_id=photo_file_id,
            photo_unique_id=photo_unique_id,
            raw_payload=dict(context.user_data),
        )
        match = try_match_request(session, request.id)
        if match:
            response_text = build_dispatch_text(match)
            match.message_sent = True
        else:
            response_text = (
                "Заявка сохранена. Мы приняли её в работу и начнём поиск подходящего варианта. "
                "Как только найдём совпадение, пришлём готовую инструкцию прямо сюда."
            )
            request.status = RecordStatus.active
        save_bot_message(session, conversation.id, "out", response_text)

    await update.message.reply_text(response_text, reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Диалог остановлен. Напишите /start, чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


def build_application() -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment")

    application = Application.builder().token(settings.telegram_bot_token).build()
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, role_step)],
            FROM_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_city_step)],
            TO_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, to_city_step)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_step)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_step)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_step)],
            PHOTO: [
                MessageHandler(filters.PHOTO, photo_step),
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_step),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("cancel", cancel))
    return application


def main() -> None:
    init_db()
    app = build_application()
    logger.info("Starting Colibri Telegram bot")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
