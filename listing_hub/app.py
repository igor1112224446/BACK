"""
Веб-сервис: добавляешь объект с фото → ИИ готовит тексты → ставишь в очередь на площадки.
Запуск:  python -m uvicorn app:app --port 8000   → открой http://localhost:8000
"""
import base64
import json
import urllib.request
import uuid
from pathlib import Path
from typing import List

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ai
from images import watermark
from storage import Store

import os
import shutil
from datetime import date

# ---------- где хранятся данные ----------
# Программа (C:\listing-hub) и данные (объекты, фото) разделены: данные лежат в папке пользователя
# %APPDATA%\ListingHub и не затрагиваются при обновлении/распаковке/переносе программы.
BASE = Path(__file__).resolve().parent
CFG = yaml.safe_load(open(BASE / "config.yaml", encoding="utf-8"))
DATA_DIR = Path(os.environ.get("LISTING_HUB_DATA") or CFG.get("storage", {}).get("data_dir")
                or Path(os.environ.get("APPDATA") or Path.home()) / "ListingHub")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# перенос данных из старого места (папка программы) — один раз
if not (DATA_DIR / "hub.db").exists() and (BASE / "hub.db").exists():
    shutil.copy2(BASE / "hub.db", DATA_DIR / "hub.db")
    if (BASE / "media").exists() and not (DATA_DIR / "media").exists():
        shutil.copytree(BASE / "media", DATA_DIR / "media")

# ежедневная резервная копия базы (хранятся последние 30)
_backups = DATA_DIR / "backups"
_backups.mkdir(exist_ok=True)
if (DATA_DIR / "hub.db").exists():
    _today = _backups / f"hub-{date.today().isoformat()}.db"
    if not _today.exists():
        shutil.copy2(DATA_DIR / "hub.db", _today)
    for old_copy in sorted(_backups.glob("hub-*.db"))[:-30]:
        old_copy.unlink(missing_ok=True)

os.chdir(DATA_DIR)          # пути к фото в базе хранятся относительно папки данных ("media/...")
MEDIA = Path("media")
MEDIA.mkdir(exist_ok=True)
if not Path(CFG["agent"].get("logo_path", "")).is_absolute():
    CFG["agent"]["logo_path"] = str(BASE / CFG["agent"].get("logo_path", "assets/logo.png"))

app = FastAPI(title="Listing Hub")
store = Store(str(DATA_DIR / "hub.db"))
WM_ON = bool(CFG["agent"].get("watermark", False))


def make_photo(src, dst):
    return watermark(src, dst, CFG["agent"]["logo_path"], CFG["agent"]["phone"],
                     CFG["agent"]["logo_width_ratio"], enabled=WM_ON)


def rebuild_photos():
    """Если настройка логотипа поменялась — переделываем фото уже сохранённых объектов из оригиналов."""
    for it in store.all():
        if bool(it["data"].get("wm_applied", True)) == WM_ON:
            continue
        for src, dst in zip(it["photos"], it["photos_wm"]):
            try:
                make_photo(src, dst)
            except Exception:
                pass
        store.update_data(it["id"], {**it["data"], "wm_applied": WM_ON})


rebuild_photos()


# ---------- цены только в долларах ----------
_RATE = {"value": None, "day": None}


def gel_per_usd():
    """Курс лари к доллару: официальный курс Нацбанка Грузии (раз в день), иначе — из config.yaml."""
    import datetime
    today = datetime.date.today().isoformat()
    if _RATE["day"] == today and _RATE["value"]:
        return _RATE["value"]
    rate = float(CFG.get("currency", {}).get("gel_per_usd_fallback", 2.7))
    try:
        req = urllib.request.Request("https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?currencies=USD",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        c = data[0]["currencies"][0]
        rate = float(c["rate"]) / float(c.get("quantity", 1) or 1)
    except Exception:
        pass
    _RATE.update(value=rate, day=today)
    return rate


def to_usd(d):
    """Если цена в лари — переводим в доллары (лари сохраняем отдельно для справки)."""
    if d.get("currency") == "GEL" and d.get("price"):
        rate = gel_per_usd()
        d["price_gel"] = d["price"]
        d["price"] = int(round(float(d["price"]) / rate, -2))   # до сотен долларов
        d["usd_rate"] = round(rate, 4)
    d["currency"] = "USD"
    return d


def migrate_prices():
    for it in store.all():
        if it["data"].get("currency") == "GEL":
            store.update_data(it["id"], to_usd(dict(it["data"])))


migrate_prices()

app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.get("/")
def index():
    return FileResponse(str(BASE / "static" / "index.html"))


@app.get("/crm")
def crm_page():
    return FileResponse(str(BASE / "static" / "crm.html"))


class LeadsBulk(BaseModel):
    page_url: str = ""
    items: List[dict]


@app.post("/api/leads/bulk")
def leads_bulk(req: LeadsBulk):
    """Объявления со страницы выдачи MyHome — одним запросом из расширения, без лишних обращений к сайту."""
    added = updated = 0
    for it in req.items:
        url = (it.get("source_url") or "").split("#")[0]
        if not url:
            continue
        d = {k: v for k, v in it.items() if k != "source_url"}
        if d.get("price"):
            to_usd(d)
        from descriptions import localize   # район и адрес в базе — по-русски, чтобы фильтр не двоился
        for k in ("district", "address"):
            if d.get(k):
                d[k + "_orig"] = d[k]
                d[k] = localize(d[k], "ru")
        d["from_page"] = req.page_url
        if store.upsert_lead(url, d) == "added":
            added += 1
        else:
            updated += 1
    return {"added": added, "updated": updated, "total": len(store.leads())}


@app.get("/api/leads")
def leads_list():
    import re
    have = {m.group(1) for it in store.all() for m in [re.search(r"(\d{6,})", it["data"].get("source_url") or "")] if m}
    out = store.leads()
    for l in out:
        m = re.search(r"(\d{6,})", l["source_url"])
        l["in_objects"] = bool(m and m.group(1) in have)
    return out


class LeadUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


@app.put("/api/leads/{lid}")
def lead_update(lid: int, body: LeadUpdate):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields.get("status") and fields["status"] not in ("new", "called", "agreed", "not_interested", "sold"):
        raise HTTPException(400, "Неизвестный статус")
    if fields:
        store.update_lead(lid, **fields)
    return {"ok": True}


@app.delete("/api/leads/{lid}")
def lead_delete(lid: int):
    store.delete_lead(lid)
    return {"ok": True}


@app.get("/api/config")
def config():
    return {"platforms": {k: {"title": v["title"], "method": v.get("method", "bot"),
                              "ready": v.get("method") == "extension" or bool(v["add_url"] and v["fields"])}
                          for k, v in CFG["platforms"].items() if v.get("enabled")},
            "ai": bool(ai.enabled(CFG)), "mode": CFG["publishing"]["mode"],
            "agent": {k: CFG["agent"].get(k, "") for k in ("contact_name", "first_name", "last_name", "phone")},
            "data_dir": str(DATA_DIR), "gel_per_usd": round(gel_per_usd(), 4)}


class FreeText(BaseModel):
    text: str


@app.post("/api/extract")
def extract(body: FreeText):
    if not ai.enabled(CFG):
        raise HTTPException(400, "ИИ не подключён: задай ANTHROPIC_API_KEY и ai.enabled: true")
    try:
        return ai.extract_fields(CFG, body.text)
    except Exception as e:
        raise HTTPException(502, f"ИИ не смог разобрать текст: {e}")


@app.get("/api/listings")
def listings():
    from descriptions import localize
    from descriptions import social
    a = CFG["agent"]
    items = store.all()
    for it in items:
        d = it["data"]
        if d.get("address") and not d.get("address_ru"):
            d["address_ru"] = localize(d["address"], "ru")
        if d.get("address") and not d.get("address_ka"):
            d["address_ka"] = localize(d["address"], "ka")
        if not d.get("social_ru"):   # для объектов, сохранённых до появления постов
            d.update({k: ai.strip_links(v) for k, v in social(d, a["phone"], a.get("name", "")).items()})
    return items


@app.post("/api/listings")
async def create_listing(data: str = Form(...), photos: List[UploadFile] = File(...)):
    d = to_usd(json.loads(data))
    if not photos:
        raise HTTPException(400, "Добавь хотя бы одно фото")
    folder = MEDIA / uuid.uuid4().hex[:10]
    raw, wm = [], []
    for i, ph in enumerate(photos):
        src = folder / "raw" / f"{i:02d}{Path(ph.filename).suffix.lower() or '.jpg'}"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(await ph.read())
        dst = folder / "wm" / f"{i:02d}.jpg"
        make_photo(src, dst)
        raw.append(str(src))
        wm.append(str(dst))

    add_texts(d)
    d["wm_applied"] = WM_ON
    lid = store.create(d, raw, wm)
    return store.get(lid)


def add_texts(d):
    """Тексты объявления: ИИ (если подключён) или шаблон. То, что уже заполнено руками, не трогаем."""
    texts = ai.template_descriptions(CFG, d)
    if ai.enabled(CFG):
        try:
            texts = ai.write_descriptions(CFG, d)
        except Exception as e:
            d["ai_error"] = str(e)[:200]
    for k, v in texts.items():
        if not d.get(k):
            d[k] = v
    from descriptions import social
    a = CFG["agent"]
    for k, v in social(d, a["phone"], a.get("name", "")).items():   # короткий пост для Threads
        if not d.get(k):
            d[k] = v
    from descriptions import localize
    if d.get("address"):
        d["address_ru"] = localize(d["address"], "ru")   # CRM Этажей ищет адрес по-русски (формат Яндекс.Карт)
        d["address_ka"] = localize(d["address"], "ka")   # Facebook и грузинские площадки — по-грузински
    if d.get("district"):
        d["district_ru"] = localize(d["district"], "ru")
    for k in list(d):   # ссылки на оригинал и любые адреса сайтов в публикуемый текст не попадают
        if k.startswith(("title_", "description_")) and isinstance(d[k], str):
            d[k] = ai.strip_links(d[k])


def save_photo_bytes(folder, i, content, ext=".jpg"):
    src = folder / "raw" / f"{i:02d}{ext}"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(content)
    dst = folder / "wm" / f"{i:02d}.jpg"
    make_photo(src, dst)
    return str(src), str(dst)


class PageImport(BaseModel):
    source_url: str
    title: str = ""
    text: str = ""
    guess: dict = {}
    photo_urls: List[str] = []
    photo_data: List[str] = []   # data:image/...;base64 — если сайт не отдаёт фото серверу


def _download(url, referer):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
        "Referer": referer, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


@app.post("/api/import")
def import_page(req: PageImport):
    """Сохранить объявление со страницы браузера (кнопка в расширении)."""
    for it in store.all():  # это объявление уже сохраняли — обновляем параметры, тексты и фото не трогаем
        if it["data"].get("source_url") == req.source_url:
            d = dict(it["data"])
            for k, v in req.guess.items():
                if v not in (None, "", []) and k not in ("description",):
                    d[k] = v
            d["deal"], d["property_type"] = "sale", "apartment"
            to_usd(d)
            store.update_data(it["id"], d)
            return {**store.get(it["id"]), "duplicate": True}

    d = {k: v for k, v in req.guess.items() if v not in (None, "", [])}
    if ai.enabled(CFG) and req.text:
        try:
            found = ai.extract_fields(CFG, f"{req.title}\n\n{req.text[:12000]}", source="page")
            d.update({k: v for k, v in found.items() if v not in (None, "", [])})
        except Exception as e:
            d["ai_error"] = f"Разбор страницы: {e}"[:200]
    if d.get("description"):
        d["notes"] = str(d.pop("description"))[:2000]  # исходный текст — материал для нового описания
    d["source_url"] = req.source_url
    # объявление из твоего аккаунта? (на странице стоит твоё имя или ID аккаунта MyHome)
    a = CFG["agent"]
    page = f"{req.title}\n{req.text}"
    name_ok = a.get("first_name") and a.get("last_name") and a["first_name"] in page and a["last_name"] in page
    id_ok = a.get("myhome_user_id") and str(a["myhome_user_id"]) in page
    d["own_listing"] = bool(name_ok or id_ok)
    d["deal"], d["property_type"] = "sale", "apartment"   # всегда продажа квартиры
    to_usd(d)
    d.setdefault("city", "Тбилиси")

    folder = MEDIA / uuid.uuid4().hex[:10]
    raw, wm, i = [], [], 0
    for url in req.photo_urls[:20]:
        try:
            content = _download(url, req.source_url)
            if len(content) < 15_000:   # превью и иконки
                continue
            r, w = save_photo_bytes(folder, i, content)
            raw.append(r); wm.append(w); i += 1
        except Exception:
            continue
    for data_url in req.photo_data[:20]:
        if i >= 20:
            break
        try:
            content = base64.b64decode(data_url.split(",", 1)[1])
            r, w = save_photo_bytes(folder, i, content)
            raw.append(r); wm.append(w); i += 1
        except Exception:
            continue
    if not wm:
        raise HTTPException(422, "Не удалось скачать ни одного фото с этой страницы")

    add_texts(d)
    d["wm_applied"] = WM_ON
    lid = store.create(d, raw, wm)
    return store.get(lid)


@app.put("/api/listings/{lid}")
def update_listing(lid: int, d: dict):
    item = store.get(lid)
    if not item:
        raise HTTPException(404)
    for k in list(d):
        if k.startswith(("title_", "description_")) and isinstance(d[k], str):
            d[k] = ai.strip_links(d[k])
    store.update_data(lid, {**item["data"], **d})
    return store.get(lid)


@app.post("/api/listings/{lid}/regenerate")
def regenerate(lid: int):
    """Написать заголовок и описание заново по текущим параметрам объекта."""
    item = store.get(lid)
    if not item:
        raise HTTPException(404)
    d = {k: v for k, v in item["data"].items() if not k.startswith(("title_", "description_"))}
    add_texts(d)
    store.update_data(lid, d)
    return store.get(lid)


@app.post("/api/listings/{lid}/remove_watermark")
def remove_watermark(lid: int):
    """Попробовать убрать водяной знак площадки — только для объявлений из твоего аккаунта."""
    item = store.get(lid)
    if not item:
        raise HTTPException(404)
    d = item["data"]
    if d.get("source_url") and not d.get("own_listing"):
        raise HTTPException(403, "Убрать водяной знак можно только на фото из объявлений твоего аккаунта. "
                                 "Если это твоё объявление — открой его на MyHome и сохрани заново кнопкой расширения.")
    import watermark_remove
    src = item["photos"] or item["photos_wm"]
    out_dir = Path(src[0]).parent.parent / "clean"
    cleaned, msg = watermark_remove.remove(src, out_dir)
    if not cleaned:
        raise HTTPException(422, msg)
    if not d.get("photos_before_clean"):
        d["photos_before_clean"] = item["photos_wm"]
    d["wm_removed"] = True
    store.update_data(lid, d)
    store.set_photos(lid, cleaned)
    return {**store.get(lid), "message": msg}


class KorterPrep(BaseModel):
    add_logo: bool = False
    remove_wm: bool = True


@app.post("/api/listings/{lid}/prepare_korter")
def prepare_korter(lid: int, req: KorterPrep):
    """Отдельный набор фото для Korter: без водяного знака MyHome, другая обложка, лёгкая обработка,
    по желанию — свой логотип. Только для объектов из твоего аккаунта (или добавленных вручную)."""
    item = store.get(lid)
    if not item:
        raise HTTPException(404)
    d = item["data"]
    if d.get("source_url") and not d.get("own_listing"):
        raise HTTPException(403, "Набор фото для Korter готовится только для объектов из твоего аккаунта MyHome. "
                                 "Если это твоё объявление — открой его на MyHome и сохрани заново кнопкой расширения.")
    import photo_variants
    import watermark_remove
    src = item["photos"] or item["photos_wm"]
    if not src:
        raise HTTPException(400, "У объекта нет фото")
    base = Path(src[0]).parent.parent
    msg_wm = ""
    if req.remove_wm:
        if d.get("wm_removed"):
            src = item["photos_wm"]                      # уже очищенные
        else:
            cleaned, msg_wm = watermark_remove.remove(src, base / "clean_korter")
            if cleaned:
                src = cleaned
    out = photo_variants.prepare(src, base / "korter", seed=f"{lid}-{d.get('source_url', '')}",
                                 logo_path=CFG["agent"]["logo_path"], phone=CFG["agent"]["phone"],
                                 add_logo=req.add_logo, logo_ratio=CFG["agent"]["logo_width_ratio"])
    d["photos_korter"] = out
    store.update_data(lid, d)
    note = "Водяной знак убран. " if (req.remove_wm and (d.get("wm_removed") or "убран" in msg_wm)) else \
           (msg_wm + " " if msg_wm else "")
    return {**store.get(lid), "message": f"{note}Набор для Korter готов: {len(out)} фото, обложка — другой кадр."}


@app.delete("/api/listings/{lid}/prepare_korter")
def reset_korter(lid: int):
    item = store.get(lid)
    if not item:
        raise HTTPException(404)
    d = item["data"]; d.pop("photos_korter", None)
    store.update_data(lid, d)
    return store.get(lid)


@app.post("/api/listings/{lid}/restore_photos")
def restore_photos(lid: int):
    item = store.get(lid)
    if not item or not item["data"].get("photos_before_clean"):
        raise HTTPException(400, "Нечего возвращать")
    d = item["data"]
    store.set_photos(lid, d.pop("photos_before_clean"))
    d["wm_removed"] = False
    store.update_data(lid, d)
    return store.get(lid)


@app.delete("/api/listings/{lid}")
def delete_listing(lid: int):
    store.delete(lid)
    return {"ok": True}


class PublishReq(BaseModel):
    platforms: List[str]


@app.post("/api/listings/{lid}/publish")
def publish(lid: int, req: PublishReq):
    if not store.get(lid):
        raise HTTPException(404, "Объект не найден")
    for p in req.platforms:
        if p in CFG["platforms"] and CFG["platforms"][p].get("method") != "extension":
            store.set_pub(lid, p, "queued")
    return store.get(lid)


class Confirm(BaseModel):
    status: str          # published | skipped
    url: str | None = None


@app.post("/api/listings/{lid}/publications/{platform}")
def confirm(lid: int, platform: str, body: Confirm):
    if body.status not in ("published", "skipped", "queued"):
        raise HTTPException(400)
    store.set_pub(lid, platform, body.status, url=body.url or None)
    return store.get(lid)
