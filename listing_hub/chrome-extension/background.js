// Фоновый сбор объявлений со всех страниц выдачи MyHome.
// Работает, даже если окошко расширения закрыто. Ход работы — в chrome.storage.local ("collect").
const sleep = ms => new Promise(r => setTimeout(r, ms));
let STOP = false;

async function setState(patch) {
  const { collect = {} } = await chrome.storage.local.get("collect");
  await chrome.storage.local.set({ collect: { ...collect, ...patch, at: Date.now() } });
}

function waitLoaded(tabId, timeout = 40000) {
  return new Promise(resolve => {
    const done = () => { chrome.tabs.onUpdated.removeListener(fn); clearTimeout(t); resolve(); };
    const fn = (id, info) => { if (id === tabId && info.status === "complete") done(); };
    const t = setTimeout(done, timeout);
    chrome.tabs.onUpdated.addListener(fn);
  });
}

async function ask(tabId, msg) {
  try { return await chrome.tabs.sendMessage(tabId, msg); }
  catch {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
    return await chrome.tabs.sendMessage(tabId, msg);
  }
}

async function collectAll({ tabId, startUrl, maxPages, api }) {
  STOP = false;
  let added = 0, updated = 0, total = 0, prevIds = "";
  await setState({ running: true, page: 0, maxPages, added, updated, total, msg: "Начинаю…", error: null });
  const base = new URL(startUrl);
  const startPage = +(base.searchParams.get("page") || 1);
  for (let i = 0; i < maxPages && !STOP; i++) {
    const page = startPage + i;
    if (i > 0) {
      // пауза как у человека, чтобы не нагружать сайт и не попасть под ограничения
      const wait = 5000 + Math.random() * 4000;
      await setState({ msg: `Пауза ${Math.round(wait / 1000)} с перед страницей ${page}…` });
      await sleep(wait);
      if (STOP) break;
      base.searchParams.set("page", page);
      await chrome.tabs.update(tabId, { url: base.toString() });
      await waitLoaded(tabId);
      await sleep(1500);
    }
    await setState({ page: i + 1, msg: `Страница ${page}: прокручиваю и читаю карточки…` });
    await ask(tabId, { type: "scrollLoad" });
    const r = await ask(tabId, { type: "extractList" });
    const items = r?.list?.items || [];
    const ids = items.map(x => x.listing_id).sort().join(",");
    if (!items.length) { await setState({ msg: `На странице ${page} объявлений нет — это последняя страница.` }); break; }
    if (ids === prevIds) { await setState({ msg: `Страница ${page} совпадает с предыдущей — дальше страниц нет.` }); break; }
    prevIds = ids;
    const res = await fetch(api + "/api/leads/bulk", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(r.list) }).then(x => x.json());
    added += res.added; updated += res.updated; total = res.total;
    await setState({ added, updated, total, msg: `Страница ${page}: найдено ${items.length}, новых ${res.added}.` });
  }
  await setState({ running: false, msg: (STOP ? "Остановлено. " : "Готово. ") + `Новых: ${added}, обновлено: ${updated}. Всего в базе: ${total}.` });
}

chrome.runtime.onMessage.addListener((msg, _s, reply) => {
  if (msg.type === "collectAll") {
    collectAll(msg).catch(e => setState({ running: false, error: String(e.message || e), msg: "Ошибка: " + (e.message || e) }));
    reply({ ok: true });
  } else if (msg.type === "collectStop") { STOP = true; reply({ ok: true }); }
  return true;
});
