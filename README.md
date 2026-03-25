# Colibri Dispatch Bot

Рабочий каркас под твой новый сценарий:

- Telegram-бот собирает заявку от пользователя.
- Заявка сохраняется в отдельную базу.
- Парсер шлёт предложения в backend по HTTP.
- Backend ищет совпадение без score.
- Бот отправляет управляемое сообщение без передачи контактов.

## Что внутри

- `app/api.py` — FastAPI backend
- `app/bot.py` — Telegram-бот
- `app/models.py` — таблицы базы данных
- `app/matcher.py` — детерминированный matching без score
- `scripts/parser_push_example.py` — пример отправки данных из парсера/Colab
- `schema.sql` — SQL-схема
- `Dockerfile` — базовый контейнер для API

## Логика matching

Для заявок отправителя ищутся предложения попутчиков, а для заявок попутчиков — предложения посылок.

Фильтры жёсткие:

- тот же `from_city`
- тот же `to_city`
- `offer.travel_date >= request.travel_date`
- `offer.weight_kg >= request.weight_kg`
- только активные предложения

Порядок сортировки:

1. точный маршрут
2. ближайшая подходящая дата
3. минимальный лишний запас по весу
4. более свежая запись

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Заполни `.env`.

### Запуск API

```bash
uvicorn app.api:app --reload
```

### Запуск бота

Во втором окне терминала:

```bash
python -m app.bot
```

## Минимальные переменные `.env`

```env
DATABASE_URL=sqlite:///./colibri.db
TELEGRAM_BOT_TOKEN=...
BOT_API_KEY=change-me
```

Для Railway лучше использовать Postgres:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

## Как подключить парсер из Google Colab

Из Colab или любого скрипта отправляй POST на backend:

`POST /api/ingest/offer`

С заголовком:

```text
Authorization: Bearer <BOT_API_KEY>
```

Пример есть в `scripts/parser_push_example.py`.

## Как это деплоить на Railway

Нужны **2 сервиса** из одного репозитория:

### 1. API service
Стартовая команда:

```bash
uvicorn app.api:app --host 0.0.0.0 --port $PORT
```

### 2. Bot worker
Стартовая команда:

```bash
python -m app.bot
```

Оба сервиса должны использовать одну и ту же переменную `DATABASE_URL` и один и тот же `.env`-набор.

## Какой ответ получает пользователь

Когда match найден, бот не показывает контакты, а отправляет управляемый текст:

```text
Мы нашли для вас подходящего попутчика для вашей посылки.

Маршрут: Белград → Вена
Передача: 28.03.2026, 14:00–16:00
Место: Белград, парковка у ТЦ Galerija
Оплата: Оплата производится в момент передачи посылки на карту **** 1234
```

Текст берётся из шаблонов `.env` и данных matched-offer.

## Что тебе нужно сделать дальше

1. Создать Telegram-бота у `@BotFather`
2. Поставить токен в `.env`
3. Решить, где будет Postgres: Railway Postgres или отдельный провайдер
4. Развернуть API
5. Развернуть Bot worker
6. Переделать текущий парсер так, чтобы он слал данные на `/api/ingest/offer`

## Что я бы менял следующим шагом

- валидацию маршрутов и дат
- загрузку фото в S3 / Supabase Storage / Railway volume
- админку подтверждения match
- ручную установку места/времени передачи
- ручную установку реквизитов оплаты
- cron-задачу, которая повторно прогоняет pending-заявки
