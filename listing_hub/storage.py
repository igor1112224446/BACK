"""Хранилище: объекты и их публикации на площадках (SQLite, файл hub.db)."""
import json
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    data        TEXT NOT NULL,          -- JSON: поля объекта + тексты
    photos      TEXT DEFAULT '[]',      -- JSON: исходные фото
    photos_wm   TEXT DEFAULT '[]',      -- JSON: фото с логотипом и телефоном
    created_at  TEXT,
    updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS publications (
    listing_id  INTEGER,
    platform    TEXT,
    status      TEXT,   -- queued | working | waiting_you | published | error | skipped
    url         TEXT,
    error       TEXT,
    updated_at  TEXT,
    PRIMARY KEY (listing_id, platform)
);
CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url  TEXT UNIQUE,            -- ссылка на оригинальное объявление
    data        TEXT NOT NULL,          -- JSON: цена, площадь, комнаты, адрес, фото-превью…
    status      TEXT DEFAULT 'new',     -- new | called | agreed | not_interested | sold
    notes       TEXT DEFAULT '',
    created_at  TEXT,
    updated_at  TEXT,
    seen_at     TEXT                    -- когда объявление последний раз встречалось в выдаче
);
"""


def now():
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, path="hub.db"):
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.executescript(SCHEMA)

    # ---------- объекты ----------
    def create(self, data, photos, photos_wm):
        cur = self.c.execute(
            "INSERT INTO listings (data, photos, photos_wm, created_at, updated_at) VALUES (?,?,?,?,?)",
            (json.dumps(data, ensure_ascii=False), json.dumps(photos), json.dumps(photos_wm), now(), now()))
        self.c.commit()
        return cur.lastrowid

    def update_data(self, lid, data):
        self.c.execute("UPDATE listings SET data=?, updated_at=? WHERE id=?",
                       (json.dumps(data, ensure_ascii=False), now(), lid))
        self.c.commit()

    def set_all_photos(self, lid, photos, photos_wm):
        self.c.execute("UPDATE listings SET photos=?, photos_wm=?, updated_at=? WHERE id=?",
                       (json.dumps(photos), json.dumps(photos_wm), now(), lid))
        self.c.commit()

    def set_photos(self, lid, photos_wm):
        self.c.execute("UPDATE listings SET photos_wm=?, updated_at=? WHERE id=?", (json.dumps(photos_wm), now(), lid))
        self.c.commit()

    def get(self, lid):
        r = self.c.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
        return self._row(r) if r else None

    def all(self):
        return [self._row(r) for r in self.c.execute("SELECT * FROM listings ORDER BY id DESC")]

    def delete(self, lid):
        self.c.execute("DELETE FROM listings WHERE id=?", (lid,))
        self.c.execute("DELETE FROM publications WHERE listing_id=?", (lid,))
        self.c.commit()

    def _row(self, r):
        d = dict(r)
        d["data"] = json.loads(d["data"])
        d["photos"] = json.loads(d["photos"])
        d["photos_wm"] = json.loads(d["photos_wm"])
        d["publications"] = {p["platform"]: dict(p) for p in self.c.execute(
            "SELECT * FROM publications WHERE listing_id=?", (d["id"],))}
        return d

    # ---------- публикации ----------
    def set_pub(self, lid, platform, status, url=None, error=None):
        self.c.execute(
            "INSERT INTO publications (listing_id, platform, status, url, error, updated_at) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(listing_id, platform) DO UPDATE SET status=excluded.status, "
            "url=COALESCE(excluded.url, publications.url), error=excluded.error, updated_at=excluded.updated_at",
            (lid, platform, status, url, error, now()))
        self.c.commit()

    # ---------- лиды (CRM) ----------
    def upsert_lead(self, url, data):
        r = self.c.execute("SELECT id, data FROM leads WHERE source_url=?", (url,)).fetchone()
        if r:
            old = json.loads(r["data"])
            merged = {**old, **{k: v for k, v in data.items() if v not in (None, "", [])}}
            if old.get("price") and data.get("price") and float(old["price"]) != float(data["price"]):
                merged["price_prev"] = old["price"]          # цена изменилась — покажем в CRM
                merged["price_changed_at"] = now()
            self.c.execute("UPDATE leads SET data=?, updated_at=?, seen_at=? WHERE id=?",
                           (json.dumps(merged, ensure_ascii=False), now(), now(), r["id"]))
            self.c.commit()
            return "updated"
        self.c.execute("INSERT INTO leads (source_url, data, created_at, updated_at, seen_at) VALUES (?,?,?,?,?)",
                       (url, json.dumps(data, ensure_ascii=False), now(), now(), now()))
        self.c.commit()
        return "added"

    def leads(self):
        out = []
        for r in self.c.execute("SELECT * FROM leads ORDER BY created_at DESC, id DESC"):
            d = dict(r); d["data"] = json.loads(d["data"]); out.append(d)
        return out

    def update_lead(self, lid, **fields):
        cols = ", ".join(f"{k}=?" for k in fields)
        self.c.execute(f"UPDATE leads SET {cols}, updated_at=? WHERE id=?", (*fields.values(), now(), lid))
        self.c.commit()

    def delete_lead(self, lid):
        self.c.execute("DELETE FROM leads WHERE id=?", (lid,))
        self.c.commit()

    def next_job(self):
        r = self.c.execute(
            "SELECT listing_id, platform FROM publications WHERE status='queued' ORDER BY updated_at LIMIT 1").fetchone()
        return (r["listing_id"], r["platform"]) if r else None
