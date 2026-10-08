"""
Агент публикации. Берёт задания из очереди и заполняет формы площадок в браузере.

  python worker.py                  запустить агента (держи окно открытым)
  python worker.py login myhome     войти в аккаунт площадки (один раз для каждой)
  python worker.py record myhome    записать форму площадки через Playwright Codegen

Каждая площадка работает в своём профиле браузера (папка profiles/), логины сохраняются.
"""
import random
import subprocess
import sys
import time

import yaml
from playwright.sync_api import sync_playwright

from ai import georgian_labels
from storage import Store

import os
from pathlib import Path
BASE = Path(__file__).resolve().parent
CFG = yaml.safe_load(open(BASE / "config.yaml", encoding="utf-8"))
DATA_DIR = Path(os.environ.get("LISTING_HUB_DATA") or CFG.get("storage", {}).get("data_dir")
                or Path(os.environ.get("APPDATA") or Path.home()) / "ListingHub")


# Какой браузер использовать: "chrome" — твой установленный Google Chrome (сайты реже его блокируют),
# "" — встроенный браузер Playwright (Chrome for Testing).
CHANNEL = CFG.get("publishing", {}).get("browser_channel", "chrome")


def profile(platform):
    return f"profiles/{platform}" + (f"-{CHANNEL}" if CHANNEL else "")


def open_browser(p, platform):
    ctx = p.chromium.launch_persistent_context(
        profile(platform), channel=CHANNEL or None, headless=False, locale="ka-GE", no_viewport=True,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        ignore_default_args=["--enable-automation"])
    return ctx, (ctx.pages[0] if ctx.pages else ctx.new_page())


# ---------- служебные команды ----------
def login(platform):
    pc = CFG["platforms"][platform]
    with sync_playwright() as p:
        ctx, page = open_browser(p, platform)
        page.goto(pc["home_url"], wait_until="domcontentloaded", timeout=90000)
        input(f"Войди в {pc['title']} в открывшемся окне, затем нажми Enter здесь...")
        ctx.close()
    print("Сессия сохранена.")


def record(platform):
    pc = CFG["platforms"][platform]
    if not pc["add_url"]:
        sys.exit(f"Сначала впиши add_url для {platform} в config.yaml")
    print("Заполни форму руками тестовыми данными, НЕ публикуй. Затем скопируй код из окна Inspector.")
    cmd = [sys.executable, "-m", "playwright", "codegen", "--user-data-dir", profile(platform)]
    if CHANNEL:
        cmd += ["--channel", CHANNEL]
    subprocess.run(cmd + [pc["add_url"]])


# ---------- заполнение формы ----------
def render(tpl, d):
    safe = {k: ("" if v is None else ", ".join(v) if isinstance(v, list) else v) for k, v in d.items()}
    try:
        return str(tpl).format(**safe)
    except (KeyError, IndexError):
        return ""


def locate(page, f):
    by, key = f["by"], f["key"]
    if by == "label":
        return page.get_by_label(key, exact=False).first
    if by == "placeholder":
        return page.get_by_placeholder(key, exact=False).first
    if by == "text":
        return page.get_by_text(key, exact=True).first
    return page.locator(key).first


def fill_form(page, fields, d, photos):
    problems = []
    for f in fields:
        value = render(f.get("value", ""), d)
        try:
            t = f.get("type", "text")
            if t == "click_text":
                target = value or f["key"]
                if target:
                    page.get_by_text(target, exact=True).first.click(timeout=5000)
            elif t == "select":
                if value:
                    locate(page, f).select_option(label=value, timeout=5000)
            else:
                if not value:
                    continue
                el = locate(page, f)
                el.fill("", timeout=5000)
                el.type(value, delay=random.randint(15, 50))
            time.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            problems.append(f"{f.get('name', f['key'])}: {type(e).__name__}")
    if photos:
        try:
            page.locator("input[type=file]").first.set_input_files(photos, timeout=10000)
            page.wait_for_timeout(3000 + 800 * len(photos))
        except Exception as e:
            problems.append(f"фото: {type(e).__name__}")
    return problems


def wait_for_you(store, lid, platform, page, minutes=20):
    """assist-режим: ждём, пока ты нажмёшь «Опубликовано» или «Пропустить» в веб-интерфейсе."""
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        pub = store.get(lid)["publications"].get(platform, {})
        if pub.get("status") in ("published", "skipped"):
            return pub["status"]
        try:
            page.wait_for_timeout(2000)
        except Exception:        # окно браузера закрыли
            return "skipped"
    return "timeout"


def run_job(store, p, lid, platform):
    pc = CFG["platforms"][platform]
    item = store.get(lid)
    d = {**item["data"], **georgian_labels(item["data"])}
    if not pc["add_url"] or not pc["fields"]:
        store.set_pub(lid, platform, "error", error="Площадка не настроена: нужен add_url и поля формы (worker.py record)")
        return
    store.set_pub(lid, platform, "working")
    ctx, page = open_browser(p, platform)
    try:
        page.goto(pc["add_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        if any(w in page.url.lower() for w in ("login", "auth", "signin")):
            store.set_pub(lid, platform, "error", error=f"Не выполнен вход: python worker.py login {platform}")
            return
        problems = fill_form(page, pc["fields"], d, item["photos_wm"])
        note = ("Не заполнилось: " + "; ".join(problems)) if problems else None

        if CFG["publishing"]["mode"] == "auto" and not problems and pc.get("submit_text"):
            page.get_by_role("button", name=pc["submit_text"]).first.click()
            page.wait_for_timeout(6000)
            store.set_pub(lid, platform, "published", url=page.url)
        else:
            store.set_pub(lid, platform, "waiting_you", error=note)
            print(f"  ⏳ {pc['title']}: проверь форму в браузере, опубликуй и нажми «Опубликовано» в сервисе")
            result = wait_for_you(store, lid, platform, page)
            if result == "timeout":
                store.set_pub(lid, platform, "error", error="Не дождались подтверждения за 20 минут")
    except Exception as e:
        store.set_pub(lid, platform, "error", error=f"{type(e).__name__}: {e}"[:500])
    finally:
        ctx.close()


def main_loop():
    os.chdir(DATA_DIR)
    store = Store(str(DATA_DIR / "hub.db"))
    print("Агент публикации запущен. Ожидаю задания из сервиса... (Ctrl+C — выход)")
    with sync_playwright() as p:
        while True:
            job = store.next_job()
            if not job:
                time.sleep(3)
                continue
            lid, platform = job
            print(f"▶ Объект #{lid} → {platform}")
            run_job(store, p, lid, platform)
            lo, hi = CFG["publishing"]["pause_between_posts_sec"]
            time.sleep(random.uniform(lo, hi))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ("login", "record"):
        {"login": login, "record": record}[sys.argv[1]](sys.argv[2])
    else:
        main_loop()
