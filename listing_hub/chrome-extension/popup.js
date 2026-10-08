// Popup: берёт объекты из локального сервиса и отправляет выбранный в форму на странице.
const $ = s => document.querySelector(s);
const PLATFORM_BY_HOST = { "home.ss.ge": "ssge", "ss.ge": "ssge",
  "statements.myhome.ge": "myhome", "www.myhome.ge": "myhome", "myhome.ge": "myhome",
  "korter.ge": "korter", "www.korter.ge": "korter", "ecosystem.etagi.com": "etagi",
  "www.threads.com": "threads", "threads.com": "threads", "www.threads.net": "threads", "threads.net": "threads",
  "www.facebook.com": "facebook", "facebook.com": "facebook", "m.facebook.com": "facebook" };
const TITLES = { ssge: "SS.ge", myhome: "MyHome", korter: "Korter", etagi: "Этажи CRM", threads: "Threads", facebook: "Facebook Marketplace" };
let API = "http://localhost:8000", LIST = [], SELECTED = null, TAB = null, PLATFORM = null, CFG_AI = false, CONTACT = {}, RATE = 0;

const status = (t, err) => { $("#status").textContent = t; $("#status").className = err ? "err" : ""; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function api(path, opt) {
  const r = await fetch(API + path, opt);
  if (!r.ok) throw new Error(`Сервис ответил ${r.status}`);
  return r.json();
}

function render() {
  if (!LIST.length) { $("#list").innerHTML = `<p class="muted" style="padding:14px">В сервисе пока нет объектов.</p>`; return; }
  const host = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return "ссылка"; } };
  $("#list").innerHTML = LIST.map(it => {
    const d = it.data, pub = PLATFORM && it.publications[PLATFORM];
    const params = [d.rooms && `${d.rooms}-комн.`, d.area && `${d.area} м²`, d.district].filter(Boolean).join(", ");
    const cur = d.currency === "GEL" ? " ₾" : " $";
    return `<div class="obj-row">
      <button class="obj" data-id="${it.id}" aria-pressed="${SELECTED === it.id}">
        <img src="${it.photos_wm[0] ? API + "/" + it.photos_wm[0].replace(/\\/g, "/") : ""}" alt="">
        <span><span class="price">${d.price ? Number(d.price).toLocaleString("ru-RU") + cur : "Без цены"}</span><br>
        <span class="muted">${esc(params)}</span>
        ${d.address ? `<br><span class="muted">${esc(d.address)}</span>` : ""}
        ${pub?.status === "published" ? `<br><span class="done">Уже опубликован здесь</span>` : ""}</span>
      </button>
      ${d.source_url ? `<a class="src" href="${esc(d.source_url)}" data-url="${esc(d.source_url)}" title="${esc(d.source_url)}">Оригинал на ${esc(host(d.source_url))} ↗</a>` : ""}
    </div>`;
  }).join("");
  document.querySelectorAll(".obj").forEach(b => b.onclick = () => { SELECTED = +b.dataset.id; render(); updateButtons(); });
  // ссылка открывается в новой вкладке, popup при этом не мешает
  document.querySelectorAll("a.src").forEach(a => a.onclick = e => { e.preventDefault(); chrome.tabs.create({ url: a.dataset.url, active: true }); });
}

function updateButtons() {
  const onSite = !!PLATFORM;
  $("#fill").disabled = !(SELECTED && onSite);
  $("#mark").disabled = !(SELECTED && onSite);
  if (!onSite) status("Открой форму подачи объявления на MyHome, SS.ge, Korter или в CRM Этажей — кнопки станут активны.");
}

async function toDataURL(url) {
  const blob = await (await fetch(url)).blob();
  return await new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(blob); });
}

async function send(msg) {
  try { return await chrome.tabs.sendMessage(TAB.id, msg); }
  catch {
    // страница открыта до установки расширения — подключаем скрипт вручную
    await chrome.scripting.executeScript({ target: { tabId: TAB.id }, files: ["content.js"] });
    return await chrome.tabs.sendMessage(TAB.id, msg);
  }
}

$("#fill").onclick = async () => {
  const it = LIST.find(x => x.id === SELECTED);
  $("#fill").disabled = true;
  try {
    status(`Готовлю фото…`);
    const photos = [];
    // для Korter — отдельный подготовленный набор фото, если он есть
    const set = PLATFORM === "korter" && it.data.photos_korter?.length ? it.data.photos_korter : it.photos_wm;
    for (const p of set) photos.push(await toDataURL(API + "/" + p.replace(/\\/g, "/")));
    status("Заполняю форму…");
    const res = await send({ type: "fill", platform: PLATFORM, listing: it, photos, lang: $("#lang").value, contact: CONTACT, rate: RATE });
    status(res?.ok ? `Готово: заполнено ${res.filled}, вручную — ${res.missed}. Проверь форму.` : (res?.error || "Не удалось заполнить"), !res?.ok);
  } catch (e) { status(e.message, true); }
  $("#fill").disabled = false;
};

$("#mark").onclick = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    await api(`/api/listings/${SELECTED}/publications/${PLATFORM}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "published", url: tab.url })
    });
    status("Отмечено в сервисе как опубликованное.");
    LIST = await api("/api/listings"); render();
  } catch (e) { status(e.message, true); }
};

$("#scan").onclick = async () => {
  try { const r = await send({ type: "scan" }); status(r?.ok ? `Сканер: найдено ${r.count} полей, файл сохранён в «Загрузки».` : "Сканер не сработал", !r?.ok); }
  catch (e) { status("Сканер работает только на странице формы MyHome, SS.ge, Korter или CRM Этажей", true); }
};

$("#grab").onclick = async () => {
  const b = $("#grab"), st = t => $("#grabStatus").textContent = t;
  b.disabled = true;
  try {
    if (!/^https?:/.test(TAB.url || "")) throw new Error("Открой страницу объявления на сайте");
    st("Читаю страницу…");
    const r = await send({ type: "extract" });
    if (!r?.ok) throw new Error("Не удалось прочитать страницу");
    const p = r.page;
    st(`Нашёл ${p.photo_urls.length} фото. Сохраняю${CFG_AI ? ", ИИ разбирает объявление" : ""}…`);
    const it = await api("/api/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) });
    const d = it.data;
    const has = (k, name) => (d[k] ? "✓" : "✗") + " " + name;
    const report = [has("price", "цена"), has("area", "площадь"), has("rooms", "комнаты"), has("floor", "этаж"),
      has("floors_total", "этажность"), has("notes", "описание")].join("  ");
    st(it.duplicate ? `Это объявление уже было в сервисе — параметры обновлены.\n${report}` :
      `Сохранено: ${d.price ? Number(d.price).toLocaleString("ru-RU") + (d.currency === "GEL" ? " ₾" : " $") : "без цены"}, ` +
      `фото: ${it.photos_wm.length}\n${report}`);
    LIST = await api("/api/listings"); SELECTED = it.id; render(); updateButtons();
  } catch (e) {
    let msg = e.message;
    if (/422/.test(msg)) msg = "Сайт не отдал фото. Пролистай галерею объявления, чтобы фото загрузились, и попробуй снова.";
    st(msg);
  }
  b.disabled = false;
};

// ---------- перевод объявления на русский + пост для Threads (любой сайт, в т.ч. halooglasi.com) ----------
$("#threads").onclick = async () => {
  const b = $("#threads"), st = t => $("#grabStatus").textContent = t;
  b.disabled = true; $("#threadsOut").hidden = true;
  try {
    if (!/^https?:/.test(TAB.url || "")) throw new Error("Открой страницу объявления на сайте");
    if (!CFG_AI) throw new Error("Перевод нужен ИИ: задай ANTHROPIC_API_KEY и ai.enabled: true в config.yaml");
    st("Читаю объявление…");
    const r = await send({ type: "extract" });
    if (!r?.ok) throw new Error("Не удалось прочитать страницу");
    st("Перевожу и пишу пост… это займёт до минуты");
    const res = await api("/api/threads-post", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_url: r.page.source_url, title: r.page.title, text: r.page.text }) });
    $("#threadsPost").value = res.threads_post;
    $("#threadsRu").value = res.ru_translation;
    $("#threadsOut").hidden = false;
    st(`Пост: ${res.threads_post.length} из 500 символов.`);
  } catch (e) {
    st(e.message);
  }
  b.disabled = false;
};
const copyText = (sel, btn) => navigator.clipboard.writeText($(sel).value)
  .then(() => { $(btn).textContent = "Скопировано ✓"; setTimeout(() => $(btn).textContent = btn === "#copyPost" ? "Копировать пост" : "Копировать перевод", 1500); });
$("#copyPost").onclick = () => copyText("#threadsPost", "#copyPost");
$("#copyRu").onclick = () => copyText("#threadsRu", "#copyRu");

// ---------- сбор всей выдачи в базу (работает в фоне, окошко можно закрыть) ----------
function showCollect(c) {
  if (!c || !c.msg) return;
  const running = c.running && Date.now() - (c.at || 0) < 120000;
  $("#grabStatus").innerHTML = esc(c.msg) + (c.maxPages ? `<br>Страница ${c.page || 0} из ${c.maxPages} · новых ${c.added || 0} · обновлено ${c.updated || 0}` : "") +
    `<br><a href="#" id="openCrm">Открыть базу объявлений</a>`;
  $("#openCrm").onclick = e => { e.preventDefault(); chrome.tabs.create({ url: API + "/crm" }); };
  $("#grabAll").disabled = running; $("#stopAll").hidden = !running;
}
chrome.storage.onChanged.addListener(ch => { if (ch.collect) showCollect(ch.collect.newValue); });

$("#grabAll").onclick = async () => {
  if (!/myhome\.ge/.test(TAB.url || "")) {
    $("#grabStatus").textContent = "Открой страницу выдачи MyHome (список объявлений) и нажми снова.";
    return;
  }
  const maxPages = +$("#pages").value;
  await chrome.runtime.sendMessage({ type: "collectAll", tabId: TAB.id, startUrl: TAB.url, maxPages, api: API });
  $("#grabAll").disabled = true; $("#stopAll").hidden = false;
};
$("#stopAll").onclick = () => chrome.runtime.sendMessage({ type: "collectStop" });
chrome.storage.local.get("collect").then(({ collect }) => showCollect(collect));

$("#saveApi").onclick = async () => {
  API = $("#api").value.trim().replace(/\/$/, "");
  await chrome.storage.local.set({ api: API });
  init();
};

async function init() {
  const s = await chrome.storage.local.get(["api", "lang"]);
  API = s.api || API; $("#api").value = API;
  if (s.lang) $("#lang").value = s.lang;
  $("#lang").onchange = () => chrome.storage.local.set({ lang: $("#lang").value });
  [TAB] = await chrome.tabs.query({ active: true, currentWindow: true });
  const host = TAB?.url ? new URL(TAB.url).hostname : "";
  PLATFORM = PLATFORM_BY_HOST[host] || null;
  $("#site").textContent = PLATFORM ? TITLES[PLATFORM] : "";
  if (PLATFORM === "threads") { $("#fill").textContent = "Заполнить пост в Threads"; $("label[for=lang]").textContent = "Пост на"; }
  try { const cfg = await api("/api/config"); CFG_AI = cfg.ai; CONTACT = cfg.agent || {}; RATE = cfg.gel_per_usd || 0; LIST = await api("/api/listings"); render(); updateButtons(); }
  catch {
    $("#list").innerHTML = `<p class="err" style="padding:14px">Сервис не отвечает на ${esc(API)}. Запусти start_service.bat.</p>`;
  }
}
init();
