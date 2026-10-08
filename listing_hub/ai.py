"""ИИ-часть: разбор свободного текста в поля объекта и тексты объявления на 3 языках."""
import json
import os
import unicodedata

FIELDS = {
    "deal": "sale | rent | daily_rent",
    "property_type": "apartment | house | commercial | land",
    "price": "число, в USD",
    "area": "общая площадь, м²",
    "rooms": "комнат всего", "bedrooms": "спален",
    "floor": "этаж", "floors_total": "этажей в доме",
    "city": "город", "district": "район", "address": "улица и дом",
    "condition": "new_renovation | old_renovation | white_frame | black_frame | green_frame | needs_renovation",
    "building_status": "old_building | new_building | under_construction",
    "features": "список: balcony, parking, elevator, furniture, heating, gas, storage, pool, view ...",
    "cadastral_code": "кадастровый код, если есть",
}

DEAL_KA = {"sale": "იყიდება", "rent": "ქირავდება", "daily_rent": "ქირავდება დღიურად"}
PROPERTY_KA = {"apartment": "ბინა", "house": "სახლი", "commercial": "კომერციული ფართი", "land": "მიწა"}
CONDITION_KA = {"new_renovation": "ახალი რემონტი", "old_renovation": "ძველი რემონტი",
                "white_frame": "თეთრი კარკასი", "black_frame": "შავი კარკასი",
                "green_frame": "მწვანე კარკასი", "needs_renovation": "სარემონტო"}


import re as _re

LINK_RE = _re.compile(r"(https?://\S+|www\.\S+|\b[\w.-]+\.(?:ge|com|ru|net|org|io|app)(?:/\S*)?|\bID\s*:?\s*\d{5,}\b)", _re.I)


def strip_links(text):
    """Убирает из текста ссылки, адреса сайтов и ID объявлений."""
    t = LINK_RE.sub("", text or "")
    t = _re.sub(r"\s+([,.;:])", r"\1", t)          # «смотри , .» → «смотри,.»
    t = _re.sub(r"([,;:])(?:\s*[,;:.])+", ".", t)   # «,.» → «.»
    return _re.sub(r"[ \t]{2,}", " ", t).strip()


def enabled(cfg):
    return cfg["ai"].get("enabled") and os.getenv("ANTHROPIC_API_KEY")


def _ask(cfg, prompt, max_tokens=2000):
    import anthropic
    msg = anthropic.Anthropic().messages.create(
        model=cfg["ai"]["model"], max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def extract_fields(cfg, free_text, source="text"):
    """«3-комн., Ваке, 85 кв, 9/16, свежий ремонт, 185к» → структурированные поля.
    source="page" — текст целой веб-страницы объявления (с меню, рекламой и похожими объявлениями)."""
    intro = ("Это текст веб-страницы с объявлением о недвижимости в Грузии. На странице есть меню, реклама и блоки "
             "«похожие объявления» — бери данные ТОЛЬКО основного объявления (обычно заголовок и параметры вверху). "
             "Добавь поле \"description\" — исходное описание объекта из объявления как есть (без телефонов и имён). "
             if source == "page" else "Извлеки данные об объекте недвижимости в Грузии из текста риэлтора. ")
    prompt = (
        intro +
        "Не выдумывай: если поля нет в тексте — не включай его.\n"
        f"Поля и допустимые значения: {json.dumps(FIELDS, ensure_ascii=False)}\n"
        "«185к» = 185000. Если цена указана в лари, оставь число как есть и добавь \"currency\": \"GEL\" — сервис сам переведёт в доллары.\n"
        f"Текст:\n{free_text}\n\nВерни ТОЛЬКО JSON-объект."
    )
    return _ask(cfg, prompt, 2500 if source == "page" else 1000)


def write_descriptions(cfg, d):
    private = {"source_url", "ai_error", "wm_applied", "notes"}
    facts = {k: v for k, v in d.items() if not k.startswith(("description_", "title_")) and k not in private
             and v not in (None, "", [])}
    if d.get("notes"):   # исходный текст — только как источник признаков, без контактов и ссылок
        facts["особенности_из_исходного_текста"] = strip_links(d["notes"])[:1500]
    prompt = (
        "Напиши объявление о недвижимости для грузинских площадок (myhome.ge, ss.ge, korter.ge).\n"
        f"Факты (ничего сверх них не добавляй): {json.dumps(facts, ensure_ascii=False)}\n"
        f"Телефон: {cfg['agent']['phone']}.\n"
        "Нужно: title_ka / title_ru / title_en — до 70 символов; description_ka / description_ru / description_en — "
        "500–900 символов, живым языком, без капса, без восклицательных знаков подряд, с телефоном в конце. "
        "Грузинский текст — естественный, как пишут местные риэлторы.\n"
        "Пиши своими словами, не копируй исходный текст. НИКОГДА не указывай ссылки, сайты, ID объявлений, "
        "чужие телефоны и имена — только телефон выше.\n"
        "Верни ТОЛЬКО JSON с этими шестью ключами."
    )
    return _ask(cfg, prompt, 3000)


THREADS_CONTACTS = {"whatsapp": "+79146596272 (WhatsApp)", "telegram": "@Rentch_srb",
                    "channel": "https://t.me/rentch_serbia"}


CURRENCY_WORDS = {"EUR": "евро", "USD": "долларов", "RSD": "динаров", "GEL": "лари"}


def threads_post_text(cfg, district_ru, area, price=None, currency=None):
    """Пост для Threads по фиксированному шаблону: только район и площадь меняются, контакты — из config.yaml
    (раздел threads) или из значений по умолчанию."""
    c = {**THREADS_CONTACTS, **(cfg.get("threads") or {})}
    head = "Сдаётся квартира" + (f" в районе {district_ru}" if district_ru else "") + (f", {area} м²" if area else "") + "."
    lines = [head]
    if price:
        code = (currency or "").upper()
        lines.append(f"Цена {price} {CURRENCY_WORDS.get(code, code)}".rstrip())
    lines += [f"Записаться на просмотр: {c['whatsapp']} или в телеге: {c['telegram']}",
             f"Другие квартиры вы можете найти в нашем телеграм-канале: {c['channel']}"]
    post = "\n".join(lines)
    return post if len(post) <= 500 else post[:497] + "…"   # лимит Threads


def _fold(s):
    """Нижний регистр без диакритики: «Vračar» → «vracar», «Đorđe» → «djorde»."""
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch)).replace("đ", "dj")


# районы Белграда: как пишут в объявлениях (латиница без диакритики и кириллица) → по-русски
DISTRICTS = [
    ("savski venac", "Савский венац"), ("савски венац", "Савский венац"),
    ("novi beograd", "Новый Белград"), ("нови београд", "Новый Белград"),
    ("stari grad", "Старый город"), ("стари град", "Старый город"),
    ("zemun polje", "Земун Поле"), ("zemun", "Земун"), ("земун", "Земун"),
    ("vracar", "Врачар"), ("врачар", "Врачар"),
    ("cukarica", "Чукарица"), ("чукарица", "Чукарица"),
    ("vozdovac", "Вождовац"), ("вождовац", "Вождовац"),
    ("zvezdara", "Звездара"), ("звездара", "Звездара"),
    ("palilula", "Палилула"), ("палилула", "Палилула"),
    ("rakovica", "Раковица"), ("раковица", "Раковица"),
    ("banovo brdo", "Баново брдо"), ("баново брдо", "Баново брдо"),
    ("dorcol", "Дорчол"), ("дорћол", "Дорчол"),
    ("konjarnik", "Конярник"), ("коњарник", "Конярник"),
    ("senjak", "Сеньяк"), ("сењак", "Сеньяк"),
    ("dedinje", "Дединье"), ("дедиње", "Дединье"),
    ("karaburma", "Карабурма"), ("карабурма", "Карабурма"),
    ("mirijevo", "Мириево"), ("миријево", "Мириево"),
    ("vidikovac", "Видиковац"), ("видиковац", "Видиковац"),
    ("medakovic", "Медакович"), ("медаковић", "Медакович"),
    ("sremcica", "Сремчица"), ("сремчица", "Сремчица"),
    ("bezanijska kosa", "Бежанийская коса"), ("бежанијска коса", "Бежанийская коса"),
    ("cubura", "Чубура"), ("чубура", "Чубура"),
    ("banjica", "Баница"), ("бањица", "Баница"),
]
_AREA_RE = _re.compile(r"(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:m|м)\s*(?:²|2)", _re.I)
_PRICE_AFTER_RE = _re.compile(r"(\d{1,3}(?:[.,\s]\d{3})+|\d{3,7})\s*(?:€|EUR\b)", _re.I)
_PRICE_BEFORE_RE = _re.compile(r"€\s*(\d{1,3}(?:[.,\s]\d{3})+|\d{3,7})", _re.I)


def threads_fields(title, text):
    """Район, площадь и цена в евро из текста объявления. Без ИИ: только регулярные выражения и словарь районов."""
    raw = f"{title}\n{text}"
    folded = _fold(raw)
    district = next((ru for key, ru in sorted(DISTRICTS, key=lambda kv: -len(kv[0])) if key in folded), "")
    area = None
    m = _AREA_RE.search(raw)
    if m:
        value = float(m.group(1).replace(",", "."))
        area = int(value) if value.is_integer() else value
    price = None
    m = _PRICE_AFTER_RE.search(raw) or _PRICE_BEFORE_RE.search(raw)
    if m:
        price = int(_re.sub(r"\D", "", m.group(1)))
    return {"district_ru": district, "area_m2": area, "price": price, "currency": "EUR" if price else None}


def template_descriptions(cfg, d):
    """Без ИИ: объявление своими словами на 3 языках из фактов объекта (см. descriptions.py)."""
    from descriptions import generate
    a = cfg["agent"]
    return generate(d, a["phone"], a.get("name") or a.get("first_name", ""))


def georgian_labels(d):
    """Грузинские значения для форм площадок."""
    return {"deal_ka": DEAL_KA.get(d.get("deal"), ""),
            "property_ka": PROPERTY_KA.get(d.get("property_type"), ""),
            "condition_ka": CONDITION_KA.get(d.get("condition"), "")}
