// Заполнение формы объявления на странице + сканер полей формы.
// Работает внутри твоего обычного браузера: для сайта это действия обычного пользователя.
if (!window.__listingHub) {
window.__listingHub = true;

const sleep = ms => new Promise(r => setTimeout(r, ms));
// «Цена *», «Этаж:», «Адрес ⓘ» → «цена», «этаж», «адрес»: звёздочки обязательных полей и двоеточия не мешают поиску
const norm = s => String(s || "").replace(/[*:\u2139\u24D8]/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden"; };

// ---------- профили площадок ----------
// Тексты кнопок и подписей полей на языках интерфейса (ru / ka / en).
const PROPERTY = {
  apartment: ["Квартира", "ბინა", "Apartment"],
  house: ["Дом", "Частный дом", "სახლი", "კერძო სახლი", "House"],
  commercial: ["Коммерческая недвижимость", "Коммерческая площадь", "კომერციული ფართი", "Commercial real estate", "Commercial"],
  land: ["Участок", "Земля", "მიწა", "მიწის ნაკვეთი", "Land"],
};
const CONDITION = {
  new_renovation: ["Новый ремонт", "Свежий ремонт", "Недавно отремонтированный", "ახალი რემონტი", "ახალი გარემონტებული", "Newly renovated"],
  old_renovation: ["Старый ремонт", "ძველი რემონტი", "ძველი გარემონტებული", "Old renovated"],
  white_frame: ["Белый каркас", "თეთრი კარკასი", "White frame"],
  black_frame: ["Черный каркас", "Чёрный каркас", "შავი კარკასი", "Black frame"],
  green_frame: ["Зеленый каркас", "Зелёный каркас", "მწვანე კარკასი", "Green frame"],
  needs_renovation: ["Требует ремонта", "Под ремонт", "სარემონტო", "Needs renovation"],
};
const BUILDING = {
  old_building: ["Старое строение", "Старый фонд", "Старая постройка", "ძველი აშენებული", "Old building"],
  new_building: ["Новое здание", "Новое строение", "Новостройка", "Новая постройка", "ახალი აშენებული", "New building"],
  under_construction: ["Строящийся", "Строится", "В процессе строительства", "მშენებარე", "Under construction"],
};
const FIELDS = [
  { key: "area", name: "Площадь", labels: ["Площадь", "Общая площадь", "Площадь (кв. м)", "Площадь, кв. м", "Квадратные метры", "Square meters", "Square feet", "Прямоугольность", "ფართი", "ფართობი", "საერთო ფართი", "Area", "Total area"] },
  { key: "rooms", name: "Комнаты", labels: ["Комнаты", "Комнат", "Кол-во комнат", "Число комнат", "Количество комнат", "Комнатность",
      "ოთახები", "ოთახი", "ოთახების რაოდენობა", "Rooms", "Number of rooms", "Room count"] },
  { key: "bedrooms", name: "Спальни", labels: ["Спальни", "Спальня", "Спален", "Количество спален", "Число спален", "Число спален",
      "საძინებელი", "საძინებლები", "საძინებლების რაოდენობა", "Bedrooms", "Bedroom", "Number of bedrooms"] },
  { key: "floor", name: "Этаж", labels: ["Этаж", "სართული", "Floor"], exact: true },
  { key: "floors_total", name: "Этажность", labels: ["Этажность", "Этажность дома", "Этажей всего", "Всего этажей", "Количество этажей", "Число этажей", "Этажей в здании", "სართულების რაოდენობა", "სულ სართული", "სართულები", "Floors in building", "Number of floors", "Building floors", "Этажей в доме", "Этажей", "სართულიანობა", "სართულები სულ", "Floors", "Total floors"] },
  { key: "price", name: "Цена", labels: ["Цена", "Полная цена", "Общая цена", "ფასი", "სრული ფასი", "Price", "Total price"] },
  { key: "cadastral_code", name: "Кадастровый код", labels: ["Кадастровый код", "საკადასტრო კოდი", "Cadastral code"] },
];
const PROFILES = {
  ssge: {
    title: "SS.ge",
    category: ["Недвижимость", "უძრავი ქონება", "Real estate"],
    deal: {
      sale: ["Купить", "Продажа", "Продается", "იყიდება", "Sale", "For sale"],
      rent: ["Снять", "Аренда", "ქირავდება", "Rent"],
      daily_rent: ["Посуточно", "დღიურად", "Daily"],
    },
  },
  facebook: {
    title: "Facebook Marketplace",
    category: null,
    noChipClick: true,          // на Facebook типы выбираются только из выпадающих списков
    noContact: true,            // имя и контакт берутся из профиля Facebook
    quietMissing: true,         // у Facebook нет полей «этаж», «комнаты» — не считаем это ошибкой
    categoryLabels: ["Категория", "Category"],
    categoryValues: ["Недвижимость", "Жильё", "Жилье", "Квартиры", "Property", "Property for sale", "Real estate", "Housing"],
    priceInGel: true,           // в Грузии Marketplace показывает цену в лари — переводим $ → ₾ по курсу
    cityLocation: { labels: ["Местоположение", "Location", "მდებარეობა"], queries: ["Тбилиси", "Tbilisi", "თბილისი"],
                    country: /грузи|georgia|საქართველო|tbilisi|тбилиси|თბილისი/i },
    expanders: ["Дополнительная информация", "Подробнее", "Дополнительные сведения", "More details", "Additional details", "დამატებითი ინფორმაცია"],
    addressLang: "ka",
    titleField: ["Заголовок", "Название", "Title"],
    propertyLabels: ["Тип недвижимости", "Тип жилья", "Тип объекта", "Property type", "Home type", "Rental type"],
    dealLabels: ["Тип объявления", "Продажа или аренда", "Listing type", "Sale or rent"],
    deal: {
      sale: ["Продажа", "На продажу", "Продается", "For sale", "Sale"],
      rent: ["Аренда", "Сдается", "For rent", "Rent"],
      daily_rent: ["Посуточно"],
    },
  },
  korter: {
    title: "Korter",
    category: null,
    deal: {
      sale: ["Продажа", "Продать", "Продается", "იყიდება", "გაყიდვა", "Sale", "Sell", "For sale"],
      rent: ["Аренда", "Сдать", "Сдается", "ქირავდება", "Rent", "For rent"],
      daily_rent: ["Посуточно", "დღიურად", "Daily"],
    },
  },
  etagi: {
    title: "Этажи CRM",
    category: null,
    crm: true,                 // в CRM поля «Имя/Фамилия» — это собственник, а не ты: контакт не подставляем
    structuredAddress: true,   // город / район / улица / дом — отдельными полями
    descLang: "ru",
    propertyLabels: ["Тип объекта", "Тип недвижимости", "Вид объекта", "Категория"],
    dealLabels: ["Тип сделки", "Сделка", "Операция", "Вид сделки"],
    deal: {
      sale: ["Продажа", "Продам", "Продается", "Продаётся", "Вторичка", "Вторичное жильё"],
      rent: ["Аренда", "Сдам"],
      daily_rent: ["Посуточно"],
    },
  },
  myhome: {
    title: "MyHome",
    category: null,
    // всегда выбираем, независимо от данных объекта
    alwaysCondition: "new_renovation",       // «Недавно отремонтированный»
    alwaysBuilding: "new_building",          // «Новое здание»
    projectType: { labels: ["Тип проекта", "Проект", "პროექტის ტიპი", "პროექტი", "Project type", "Project"],
                   values: ["Нестандартный", "Нестандартная", "Нестандартные", "არასტანდარტული", "Non-standard", "Nonstandard", "Non standard"] },
    deal: {
      sale: ["Продажа", "Продается", "იყიდება", "Sale", "For sale"],
      rent: ["Аренда", "Сдается", "ქირავდება", "Rent", "For rent"],
      daily_rent: ["Посуточно", "Посуточная аренда", "ქირავდება დღიურად", "დღიურად", "Daily rent"],
    },
  },
};

// Ссылки на оригинал, адреса сайтов и ID объявлений никогда не вставляются в публикуемый текст
function stripLinks(t) {
  return String(t || "").replace(/https?:\/\/\S+|www\.\S+|\b[\w.-]+\.(?:ge|com|ru|net|org|io|app)(?:\/\S*)?|\bID\s*:?\s*\d{5,}\b/gi, "")
    .replace(/[ \t]{2,}/g, " ").trim();
}

// Записать значение и убедиться, что форма его приняла. Если поле — «выбиралка» (открывает список),
// кликаем по нему и выбираем вариант с нужным текстом.
async function smartSet(el, value) {
  const v = String(value);
  setValue(el, v); await sleep(200);
  if (String(el.value).replace(/\s/g, "") === v.replace(/\s/g, "")) return true;
  if (!el.readOnly) { await typeSlow(el, v); el.dispatchEvent(new Event("blur", { bubbles: true })); await sleep(200);
    if (String(el.value).replace(/\s/g, "") === v.replace(/\s/g, "")) return true; }
  realClick(el); await sleep(500);
  const opt = [...document.querySelectorAll('[role="option"], [role="listbox"] *, li, button, [class*="option"], [class*="item"]')]
    .filter(o => visible(o) && o !== el && !o.closest("#lh-panel") && norm(o.innerText) === norm(v))
    .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
  if (opt) { realClick(opt); await sleep(300); return true; }
  return String(el.value).trim() !== "";
}

// ---------- Facebook Marketplace: город, раскрытие разделов ----------
async function openExpanders(names) {
  let opened = 0;
  for (const el of findByText(names, document, true)) {
    const btn = el.closest('[role="button"], button, [aria-expanded]') || el;
    if (btn.getAttribute("aria-expanded") === "true") continue;
    realClick(btn); opened++; await sleep(700);
  }
  return opened;
}

async function fillCity(cfg) {
  const el = findInputNear(cfg.labels);
  if (!el) return "none";
  if (cfg.country.test(el.value || "")) return "already";
  USED.add(el);
  for (const q of cfg.queries) {
    setValue(el, ""); await typeSlow(el, q);
    for (let i = 0; i < 10; i++) {           // ждём подсказки до 5 с и берём вариант именно в Грузии
      await sleep(500);
      const opt = [...document.querySelectorAll('[role="option"], [role="listbox"] li, li')]
        .find(o => visible(o) && !o.closest("#lh-panel") && cfg.country.test(o.innerText || "") && !/egypt|египет/i.test(o.innerText));
      if (opt) { realClick(opt); await sleep(600); return "selected"; }
    }
  }
  return "typed";
}

// ---------- низкоуровневые действия ----------
function setValue(el, value) {
  el.focus();
  const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value").set.call(el, String(value)); // работает с React-формами
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  el.dispatchEvent(new Event("blur", { bubbles: true }));
}

function realClick(el) {
  el.scrollIntoView({ block: "center" });
  for (const t of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
    el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window }));
  }
}

// Элементы, чей собственный текст совпадает с одной из подписей
function findByText(texts, root = document, exact = true) {
  const wanted = texts.map(norm);
  const nodes = root.querySelectorAll("button, label, span, div, p, a, li, b, strong, small, em, dt, dd, th, td, h1, h2, h3, h4, h5, h6, legend");
  const hits = [];
  for (const el of nodes) {
    if (!visible(el) || el.closest("#lh-panel")) continue;
    const own = norm(el.innerText);
    if (!own || own.length > 60) continue;
    if (wanted.some(w => exact ? own === w : own.startsWith(w))) hits.push(el);
  }
  // самый «глубокий» элемент — сама кнопка/подпись, а не её контейнер
  return hits.filter(h => !hits.some(o => o !== h && h.contains(o)));
}

async function clickText(texts, root) {
  const el = findByText(texts, root)[0];
  if (!el) return false;
  realClick(el.closest("button, label, [role=button], [role=radio], [role=tab], li, a") || el);
  await sleep(700);
  return true;
}

// Как может быть подписана кнопка для числа комнат/спален на разных сайтах
function chipVariants(value) {
  const v = String(value), n = parseInt(v, 10);
  const out = [v];
  if (!isNaN(n)) {
    out.push(`${n}к`, `${n}-к`, `${n} к`, `${n} комн.`, `${n}-комнатная`, `${n}-room`, `${n}-ოთახიანი`);
    for (let k = 3; k <= Math.min(n, 10); k++) out.push(`${k}+`, `${k}к+`, `${k} и более`);
    if (n === 1) out.push("Студия", "Studio", "სტუდიო");
  }
  return out;
}

// Валюта: перед вводом цены переключаем форму на доллары («$», «USD», «დოლარი»)
const USD_LABELS = ["$", "usd", "us$", "дол.", "долл.", "доллар", "доллары", "დოლარი", "dollar"];
const PRICE_LABELS = ["Цена", "Полная цена", "Общая цена", "Стоимость", "ფასი", "სრული ფასი", "Price", "Total price"];

async function selectUSD() {
  const labs = findByText(PRICE_LABELS, document, true);
  for (const lab of labs) {
    let box = lab;
    for (let i = 0; i < 5 && box; i++) {
      box = box.parentElement;
      if (!box) break;
      // <select> с валютой
      const sel = [...box.querySelectorAll("select")].find(x => visible(x) && [...x.options].some(o => USD_LABELS.includes(norm(o.text)) || /usd/i.test(o.value)));
      if (sel) {
        const o = [...sel.options].find(o => USD_LABELS.includes(norm(o.text)) || /usd/i.test(o.value));
        if (sel.value !== o.value) { sel.value = o.value; sel.dispatchEvent(new Event("change", { bubbles: true })); }
        return true;
      }
      // переключатель «₾ | $»
      const btn = [...box.querySelectorAll("button, label, span, div, li, a, [role=tab], [role=radio]")]
        .find(x => visible(x) && !x.children.length && USD_LABELS.includes(norm(x.innerText)) && !x.closest("#lh-panel"));
      if (btn) {
        const target = btn.closest("button, label, [role=tab], [role=radio], li, a") || btn;
        const active = target.getAttribute("aria-pressed") === "true" || target.getAttribute("aria-selected") === "true" ||
          target.getAttribute("aria-checked") === "true" || /(^|\s|-)(active|selected|checked)(\s|$|-)/i.test(target.className || "");
        if (!active) { realClick(target); await sleep(400); }
        return true;
      }
    }
  }
  return false;
}

// Заполнить поле рядом с подписью: поднимаемся от подписи по контейнерам и на каждом уровне
// ищем сначала кнопку-чип с нужным значением («Комнаты: 1 2 3»), потом поле ввода после подписи.
const USED = new Set(); // поля, которые уже заполнили в этом проходе
const INPUTS = "input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]), textarea";
const after = (a, b) => a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING;

async function fillNear(labels, value, exact) {
  // 1) placeholder / aria-label
  const L = labels.map(norm);
  for (const el of [...document.querySelectorAll(INPUTS)].filter(visible)) {
    if (USED.has(el) || el.closest("#lh-panel")) continue;
    const hint = norm(el.placeholder || el.getAttribute("aria-label") || "");
    if (hint && L.some(l => exact ? hint === l : hint.startsWith(l))) { USED.add(el); return smartSet(el, value); }
  }
  // 2) текстовая подпись
  const labs = findByText(labels, document, true);
  if (!labs.length && !exact) labs.push(...findByText(labels, document, false));
  for (const lab of labs) {
    if (lab.tagName === "LABEL" && lab.htmlFor) {
      const byFor = document.getElementById(lab.htmlFor);
      if (byFor && !USED.has(byFor)) { setValue(byFor, value); USED.add(byFor); return true; }
    }
    let box = lab;
    for (let i = 0; i < 4 && box; i++) {
      box = box.parentElement;
      if (!box) break;
      const variants = chipVariants(value);
      const chips = findByText(variants, box, true).filter(el => el !== lab && after(lab, el));
      // точное совпадение важнее «4+»: сортируем по порядку вариантов
      const vn = variants.map(norm), rank = el => { const i = vn.indexOf(norm(el.innerText)); return i < 0 ? 99 : i; };
      const chip = chips.sort((a, b) => rank(a) - rank(b))[0];
      if (chip) { realClick(chip.closest("button, label, [role=button], [role=radio], li") || chip); await sleep(300); return true; }
      const inp = [...box.querySelectorAll(INPUTS)].find(el => visible(el) && !USED.has(el) && after(lab, el));
      if (inp) { USED.add(inp); return smartSet(inp, value); }
      const sel = [...box.querySelectorAll("select")].find(el => visible(el) && !USED.has(el) && after(lab, el));
      if (sel) {
        const vv = chipVariants(value).map(norm);
        const opt = [...sel.options].find(o => norm(o.text) === norm(value) || norm(o.value) === norm(value))
          || [...sel.options].find(o => vv.includes(norm(o.text))) || [...sel.options].find(o => num(o.text) === num(value));
        if (opt) { sel.value = opt.value; USED.add(sel); sel.dispatchEvent(new Event("change", { bubbles: true })); return true; }
      }
    }
  }
  return false;
}

// Выпадающий список рядом с подписью: обычный <select> или «самодельный» (клик → список вариантов)
async function chooseOption(labels, values) {
  const want = values.map(norm);
  const labs = findByText(labels, document, true);
  for (const lab of labs) {
    // подпись внутри самого выпадающего списка (Facebook: <label role="combobox"><span>Тип недвижимости</span>…)
    const own = lab.closest('[role="combobox"], [aria-haspopup="listbox"], [aria-haspopup="menu"]');
    if (own && !USED.has(own)) {
      if (want.some(w => norm(own.innerText).includes(w))) return true;
      realClick(own);
      for (let k = 0; k < 8; k++) {
        await sleep(250);
        const opt = [...document.querySelectorAll('[role="option"], [role="menuitem"], [role="menuitemradio"]')]
          .find(o => visible(o) && want.some(w => norm(o.innerText) === w || norm(o.innerText).startsWith(w)));
        if (opt) { realClick(opt); USED.add(own); await sleep(400); return true; }
      }
      document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    }
    let box = lab;
    for (let i = 0; i < 4 && box; i++) {
      box = box.parentElement;
      if (!box) break;
      const sel = [...box.querySelectorAll("select")].find(el => visible(el) && after(lab, el) && !USED.has(el));
      if (sel) {
        const opt = [...sel.options].find(o => want.includes(norm(o.text))) || [...sel.options].find(o => want.some(w => norm(o.text).startsWith(w)));
        if (!opt) return false;
        sel.value = opt.value; USED.add(sel);
        sel.dispatchEvent(new Event("input", { bubbles: true })); sel.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      }
      const trigger = [...box.querySelectorAll('[role="combobox"], [aria-haspopup="listbox"], [class*="select"], [class*="Select"], [class*="dropdown"], input[readonly]')]
        .find(el => visible(el) && after(lab, el) && !USED.has(el))
        || [...box.querySelectorAll("div, button, span")].find(el => visible(el) && after(lab, el) && !el.contains(lab) &&
             /выберите|აირჩიეთ|select|choose|не выбрано/i.test(el.innerText || "") && (el.innerText || "").length < 80);
      if (trigger) {
        if (want.some(w => norm(trigger.innerText).endsWith(w) || norm(trigger.value || "") === w)) return true;   // уже выбрано
        const findOpt = () => findByText(values, document, true)
          .concat(findByText(values, document, false))
          .find(o => visible(o) && !o.closest("#lh-panel") && o !== lab && !lab.contains(o) && !trigger.contains(o) && !o.closest("label"));
        const clickTargets = [trigger, trigger.querySelector("input"), trigger.parentElement].filter(Boolean);
        for (const t of clickTargets) {
          realClick(t);
          for (let k = 0; k < 6; k++) {          // варианты появляются не сразу — ждём до ~1,5 с
            await sleep(250);
            const opt = findOpt();
            if (opt) { realClick(opt.closest('[role="option"], li, button') || opt); USED.add(trigger); await sleep(400); return true; }
          }
        }
        // список с поиском: вводим название и жмём Enter
        const inp = trigger.matches("input") ? trigger : trigger.querySelector("input:not([type=hidden])");
        if (inp) {
          await typeSlow(inp, values[0]); await sleep(700);
          const opt = findOpt();
          if (opt) { realClick(opt.closest('[role="option"], li, button') || opt); await sleep(400); return true; }
          inp.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, bubbles: true }));
          await sleep(400);
          if (want.some(w => norm(trigger.innerText).includes(w) || norm(inp.value).includes(w))) return true;
        }
        document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        return false;
      }
    }
  }
  return false;
}

async function attachPhotos(dataUrls) {
  const input = document.querySelector("input[type=file]");
  if (!input) return false;
  const dt = new DataTransfer();
  for (let i = 0; i < dataUrls.length; i++) {
    const blob = await (await fetch(dataUrls[i])).blob();
    dt.items.add(new File([blob], `photo_${String(i + 1).padStart(2, "0")}.jpg`, { type: "image/jpeg" }));
  }
  input.files = dt.files;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(1500 + 400 * dataUrls.length);
  return true;
}

// ---------- заполнение ----------
// ---------- CRM «Этажи» (ecosystem.etagi.com) ----------
// Форма разбита на вкладки «О сделке / Об объекте / Характеристика объекта / Паспорт объекта».
// В CRM редактируются уже существующие объекты, поэтому заполняем ТОЛЬКО пустые поля и ничего не перезаписываем.
const ETAGI_TABS = ["О сделке", "Об объекте", "Характеристика объекта", "Паспорт объекта"];

function chipSelected(container) {
  return [...container.querySelectorAll("button, [role=button], [role=radio], label, li, div, span")].some(el =>
    visible(el) && (el.getAttribute("aria-pressed") === "true" || el.getAttribute("aria-checked") === "true" ||
      /(^|\s|-)(active|selected|checked|current)(\s|$|-)/i.test(el.className || "")));
}

async function etagiField(labels, value, kind) {
  // возвращает "filled" | "skipped" (уже заполнено) | "absent" (поля нет на этой вкладке)
  const lab = findByText(labels, document, true)[0];
  if (!lab) return "absent";
  let box = lab;
  for (let i = 0; i < 4 && box; i++) {
    box = box.parentElement;
    if (!box) break;
    if (kind === "chip") {
      const chip = findByText([String(value)], box, true).find(el => el !== lab && after(lab, el));
      if (chip) {
        if (chipSelected(box)) return "skipped";
        realClick(chip.closest("button, label, [role=button], [role=radio], li") || chip); await sleep(300);
        return "filled";
      }
      continue;
    }
    const el = [...box.querySelectorAll(INPUTS)].find(x => visible(x) && !USED.has(x) && after(lab, x));
    if (el) {
      USED.add(el);
      if (String(el.value || "").trim()) return "skipped";
      setValue(el, value); await sleep(200);
      if (String(el.value) !== String(value)) { await typeSlow(el, String(value)); await sleep(200); }
      return "filled";
    }
  }
  return "absent";
}

async function fillEtagi(d) {
  const ok = [], miss = [], done = new Set();
  USED.clear();
  const rooms = d.rooms ? (d.rooms >= 4 ? "4к+" : `${d.rooms}к`) : null;
  const addr = d.address_ru || d.address || "";
  const am = addr.match(/^(.*?)[,\s]+(\d+[а-яa-zა-ჰ]?(?:\/\d+)?)\s*$/i);
  const street = (am ? am[1] : addr).trim(), house = am ? am[2] : "";
  const fields = [
    ["price", "Цена", ["Цена"], d.price],
    ["area", "Общая площадь", ["Общая площадь"], d.area],
    ["floor", "Этаж", ["Этаж"], d.floor],
    ["rooms", "Количество комнат", ["Количество комнат", "Комнат"], rooms, "chip"],
    ["bedrooms", "Количество спален", ["Количество спален", "Спален"], d.bedrooms],
    ["floors_total", "Число этажей", ["Число этажей", "Этажность", "Этажей в доме"], d.floors_total],
    ["description", "Описание", ["Описание", "Описание объекта", "Рекламный текст", "Текст объявления", "Текст рекламы"], stripLinks(d.description_ru || "")],
  ].filter(f => f[3] !== null && f[3] !== undefined && f[3] !== "");

  const tabs = ETAGI_TABS.filter(t => findByText([t]).length);
  for (const tab of (tabs.length ? tabs : [null])) {
    if (tab) { realClick(findByText([tab])[0]); await sleep(1200); USED.clear(); }
    for (const [key, name, labels, value, kind] of fields) {
      if (done.has(key)) continue;
      const r = await etagiField(labels, value, kind);
      if (r === "filled") { ok.push(`${name}: ${value}`.slice(0, 60)); done.add(key); }
      else if (r === "skipped") { ok.push(`${name}: уже было заполнено — не трогал`); done.add(key); }
    }
    // адрес: одно поле с подсказками (формат Яндекс.Карт) + отдельное поле «д»
    if (!done.has("address") && street) {
      const el = findInputNear(["Адрес"]);
      if (el) {
        done.add("address");
        if (String(el.value || "").trim()) ok.push("Адрес: уже был указан — не трогал");
        else {
          USED.add(el);
          await typeSlow(el, `Тбилиси, ${street.replace(/^(ул\.|улица)\s*/i, "")}`);
          let picked = false;
          for (let i = 0; i < 8 && !picked; i++) {
            await sleep(500);
            const opts = suggestionsBelow(el);
            if (opts.length) { realClick(opts[0]); picked = true; await sleep(700); }
          }
          (picked ? ok : miss).push(picked ? "Адрес: выбрана подсказка — проверь" : "Адрес вписан — выбери вариант из подсказок");
          if (house) {
            const h = findInputNear(["д", "Дом", "№ дома", "Номер дома"]);
            if (h && !String(h.value || "").trim()) { setValue(h, house); ok.push(`Дом: ${house}`); }
          }
        }
      }
    }
  }
  for (const [key, name] of fields) if (!done.has(key)) miss.push(`${name}: поле не найдено`);
  if (!done.has("address") && street) miss.push(`Адрес: ${addr} — укажи вручную`);
  miss.push("Фото: загрузи во вкладке «Медиа»");
  return { ok, miss };
}

// ---------- Threads: заполняем окно нового поста (текст + фото), публикуешь сам ----------
async function fillThreads(d, photos, lang) {
  const ok = [], miss = [];
  // пост из перевода объявления (threads_post) — как есть, со ссылкой на канал; иначе — обычный текст объявления
  const text = d.threads_post ? d.threads_post.slice(0, 500)
    : stripLinks(d["social_" + lang] || d.social_ru || d["description_" + lang] || "").slice(0, 500);
  const editor = () => document.querySelector('[role="dialog"] [contenteditable="true"]')
    || document.querySelector('[contenteditable="true"][role="textbox"]') || document.querySelector('[contenteditable="true"]');
  let box = editor();
  if (!box) {   // окно поста не открыто — пробуем открыть
    const opener = findByText(["Что нового?", "Что у вас нового?", "What's new?", "Start a thread", "Создать ветку", "Новая ветка", "Начать ветку"])[0]
      || document.querySelector('[aria-label="Create"], [aria-label="Создать"], [aria-label="New thread"], [aria-label="Новая ветка"]');
    if (opener) { realClick(opener.closest("a, button, [role=button]") || opener); await sleep(1800); box = editor(); }
  }
  if (!box) return { ok, miss: ["Не нашёл окно нового поста — открой «Создать» в Threads и нажми «Заполнить» ещё раз"] };

  box.focus();
  document.execCommand("selectAll", false);
  document.execCommand("insertText", false, text);
  await sleep(400);
  if (!norm(box.innerText).includes(norm(text.slice(0, 20)))) {   // редактор не принял ввод — вставляем как из буфера обмена
    const dt = new DataTransfer(); dt.setData("text/plain", text);
    box.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(400);
  }
  (norm(box.innerText).includes(norm(text.slice(0, 20))) ? ok : miss).push(`Текст поста (${lang}, ${text.length} симв.)`);

  if (photos.length) {
    const scope = box.closest('[role="dialog"]') || document;
    const input = scope.querySelector('input[type=file][accept*="image"], input[type=file]');
    if (input) {
      const dt = new DataTransfer();
      for (let i = 0; i < Math.min(photos.length, 10); i++) {
        const blob = await (await fetch(photos[i])).blob();
        dt.items.add(new File([blob], `photo_${i + 1}.jpg`, { type: "image/jpeg" }));
      }
      input.files = dt.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      await sleep(1500 + 300 * dt.files.length);
      ok.push(`Фото: ${dt.files.length}`);
    } else miss.push("Фото: не нашёл кнопку добавления фото в окне поста");
  }
  miss.push("Проверь пост и нажми «Опубликовать» в Threads");
  return { ok, miss };
}

async function fillForm(platform, listing, photos, lang, contact, rate) {
  if (platform === "threads") return fillThreads(listing.data, photos, lang);
  if (platform === "etagi") return fillEtagi(listing.data);
  const P = PROFILES[platform] || PROFILES.ssge;
  const d = listing.data, ok = [], miss = [];
  USED.clear();
  const step = async (name, fn) => { try { (await fn()) ? ok.push(name) : miss.push(name); } catch (e) { miss.push(name); } };

  if (platform === "facebook" && /\/create\/rental/.test(location.pathname)) {
    return { ok, miss: ["Это форма АРЕНДЫ (цена «в месяц»). Объект на продажу так публиковать нельзя — " +
      "открой Marketplace → «Создать объявление» → «Недвижимость на продажу» и нажми «Заполнить форму» там."] };
  }
  if (P.category) await step("Категория", () => clickText(P.category));
  if (P.categoryLabels) await step("Категория: Недвижимость", () => chooseOption(P.categoryLabels, P.categoryValues));
  // всегда продажа квартиры
  const qstep = async (name, fn) => P.quietMissing ? ((await fn().catch(() => false)) && ok.push(name)) : step(name, fn);
  if (P.categoryLabels) await sleep(1000);   // после выбора категории появляются поля недвижимости
  await qstep("Тип недвижимости: квартира", async () => (!P.noChipClick && await clickText(PROPERTY.apartment)) ||
    (P.propertyLabels ? chooseOption(P.propertyLabels, PROPERTY.apartment) : false));
  await qstep("Тип сделки: продажа", async () => (!P.noChipClick && await clickText(P.deal.sale)) ||
    (P.dealLabels ? chooseOption(P.dealLabels, P.deal.sale) : false));
  // заголовок объявления (если у формы есть отдельное поле)
  if (P.titleField) {
    const t = stripLinks(d["title_" + lang] || d.title_ru || d.title_en || "");
    if (t) await step("Заголовок", () => fillNear(P.titleField, t, true));
  }
  await sleep(1200); // после выбора типа появляются остальные поля

  if (photos.length) await step(`Фото (${photos.length})`, () => attachPhotos(photos));

  for (const f of FIELDS) {
    const v = d[f.key];
    if (v === undefined || v === null || v === "") continue;
    if (f.key === "price") {
      if (P.priceInGel && rate) {
        const gel = Math.round(v * rate / 100) * 100;
        await step(`Цена: ${gel.toLocaleString("ru-RU")} ₾ (= ${Number(v).toLocaleString("ru-RU")} $ по курсу ${rate})`, () => fillNear(f.labels, gel, f.exact));
        continue;
      }
      if (await selectUSD()) ok.push("Валюта: $");   // если переключателя валюты нет — форма и так в одной валюте
      await step("Цена ($)", () => fillNear(f.labels, v, f.exact));
      continue;
    }
    if (P.quietMissing) { if (await fillNear(f.labels, v, f.exact)) ok.push(f.name); continue; }
    await step(f.name, () => fillNear(f.labels, v, f.exact));
  }
  const cond = P.alwaysCondition || d.condition, bld = P.alwaysBuilding || d.building_status;
  if (cond && CONDITION[cond]) await step(`Состояние: ${CONDITION[cond][0]}`, () => clickText(CONDITION[cond]));
  if (bld && BUILDING[bld]) await step(`Статус: ${BUILDING[bld][0]}`, () => clickText(BUILDING[bld]));
  if (P.projectType) await step(`Тип проекта: ${P.projectType.values[0]}`, () => chooseOption(P.projectType.labels, P.projectType.values));

  if (P.expanders) { await openExpanders(P.expanders); await sleep(500); }
  const ds = await fillDescriptions(d, P.descLang || lang);
  ok.push(...ds.ok); miss.push(...ds.miss);

  if (P.structuredAddress) {
    // CRM: город, район, улица и дом — отдельными полями
    const m = (d.address || "").match(/^(.*?)[,\s]+(\d+[а-яa-zა-ჰ]?(?:\/\d+)?)\s*$/i);
    const streetOnly = (m ? m[1] : d.address || "").replace(/^(ул\.|улица|ქ\.|ქუჩა)\s*/i, "").replace(/\s+(ქუჩა|ქ\.)$/, "").trim();
    const house = m ? m[2] : "";
    const parts = [["Город", ["Город", "Населённый пункт", "Населенный пункт"], d.city || "Тбилиси"],
                   ["Район", ["Район", "Микрорайон", "Округ"], d.district],
                   ["Улица", ["Улица", "Адрес"], streetOnly],
                   ["Дом", ["Дом", "Номер дома", "№ дома"], house]];
    for (const [name, labels, val] of parts) {
      if (!val) continue;
      await step(`${name}: ${val}`, async () => (await chooseOption(labels, [val])) || fillNear(labels, val, true));
    }
  } else if (P.cityLocation) {
    const r = await fillCity(P.cityLocation);
    if (r === "selected" || r === "already") ok.push("Местоположение: Тбилиси");
    else miss.push("Местоположение: выбери «Тбилиси, Грузия» из подсказок");
    const addrKa = d.address_ka || d.address || "";
    if (addrKa && findInputNear(["Адрес", "Адрес объекта", "Адрес недвижимости", "Property address", "Address", "მისამართი"])) {
      const res = await fillAddress(addrKa);
      (res === "selected" || res === "typed" ? ok : miss).push(`Адрес (по-грузински): ${addrKa}`);
    }
  } else {
    // адрес: вписываем улицу и выбираем первую подсказку
    const street = d.address || "";
    if (street) {
      const res = await fillAddress(street);
      if (res === "selected") ok.push("Адрес (проверь выбранную подсказку)");
      else if (res === "typed") miss.push("Адрес вписан — выбери подходящий вариант из подсказок");
      else miss.push(`Адрес: ${street} — укажи вручную`);
    } else miss.push("Адрес: не найден в объекте — укажи вручную");
  }

  // контакт: имя (блок контактов внизу формы и подгружается при прокрутке)
  const name = contact && (contact.contact_name || [contact.first_name, contact.last_name].filter(Boolean).join(" "));
  if (!P.crm && !P.noContact && name) {
    window.scrollTo(0, document.body.scrollHeight); await sleep(1200);
    const put = async (el, val) => {
      if (!el) return false;
      USED.add(el); el.scrollIntoView({ block: "center" });
      setValue(el, val); await sleep(200);
      if (el.value !== val) { await typeSlow(el, val); await sleep(200); }   // форма отбросила значение — вводим посимвольно
      el.dispatchEvent(new Event("blur", { bubbles: true }));
      return el.value === val;
    };
    const isPhone = el => el.type === "tel" || /телефон|ტელეფონ|phone|номер|ნომერ|код|კოდ|code/i.test(
      [el.placeholder, el.name, el.getAttribute("aria-label"), el.closest("label, div")?.innerText?.slice(0, 60)].join(" "));
    let nameEl = null;
    // 1) поле в разделе «Контактная информация» (не путаем с «Информацией о владельце»)
    const head = findByText(["Контактная информация", "Контакты", "საკონტაქტო ინფორმაცია", "კონტაქტი", "Contact information", "Contact details"], document, true)[0];
    if (head) {
      let box = head;
      for (let i = 0; i < 5 && box && !nameEl; i++) {
        box = box.parentElement;
        if (!box) break;
        nameEl = [...box.querySelectorAll("input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio])")]
          .filter(el => visible(el) && after(head, el) && !isPhone(el)
            && !/владел|მესაკუთრ|owner/i.test(el.closest("section, form > div, [class*=card], [class*=block]")?.innerText?.slice(0, 80) || ""))[0] || null;
      }
    }
    // 2) иначе — поле с подписью «Имя»
    if (!nameEl) nameEl = findInputNear(["Имя и фамилия", "Имя Фамилия", "Контактное лицо", "ФИО", "სახელი და გვარი", "სახელი, გვარი",
      "Full name", "Contact person", "Имя", "Ваше имя", "Контактное имя", "სახელი", "First name", "Name", "Your name"]);
    (await put(nameEl, name) ? ok : miss).push(nameEl ? `Имя: ${name}` : `Имя: не нашёл поле — впиши «${name}»`);
  }
  return { ok, miss };
}

// ---------- описание на нескольких языках ----------
const LANG_TABS = {
  ka: ["ქართული", "ქარ", "ქართ", "Грузинский", "Груз", "Georgian", "Geo", "GE", "KA", "🇬🇪"],
  ru: ["Русский", "Рус", "Ру", "რუსული", "Russian", "Rus", "RU", "🇷🇺"],
  en: ["English", "Eng", "Английский", "Англ", "ინგლისური", "EN", "🇬🇧", "🇺🇸"],
};
const LANG_HINT = {
  ka: /(^|[^a-z])(ka|ge|geo)([^a-z]|$)|ქართ|груз|georg/i,
  ru: /(^|[^a-z])(ru|rus)([^a-z]|$)|русск|რუს|russ/i,
  en: /(^|[^a-z])(en|eng)([^a-z]|$)|англ|english|ინგლ/i,
};

function langOf(el) {
  let hints = [el.name, el.id, el.placeholder, el.getAttribute("aria-label"), el.getAttribute("lang"), el.dataset.lang].join(" ");
  if (el.id) hints += " " + (document.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.innerText || "");
  let box = el;
  for (let i = 0; i < 3 && box; i++) {   // подпись прямо над полем
    box = box.parentElement;
    const labs = box ? [...box.querySelectorAll("label, span, p, h4, h5, div")]
      .filter(x => !x.contains(el) && x.innerText && x.innerText.trim().length < 40 && after(x, el)) : [];
    if (labs.length) { hints += " " + labs[labs.length - 1].innerText; break; }   // ближайшая подпись над полем
  }
  for (const l of ["ka", "ru", "en"]) if (LANG_HINT[l].test(hints)) return l;
  return null;
}

async function fillDescriptions(d, fallbackLang) {
  const ok = [], miss = [];
  const textOf = l => stripLinks(d["description_" + l] || "");
  const areas = () => [...document.querySelectorAll("textarea")].filter(el => visible(el) && !el.closest("#lh-panel"));
  const tas = areas();
  if (!tas.length) return { ok, miss: ["Описание: поле не найдено"] };

  // 1) отдельное поле под каждый язык
  const byLang = {};
  for (const ta of tas) { const l = langOf(ta); if (l && !byLang[l]) byLang[l] = ta; }
  if (Object.keys(byLang).length >= 2) {
    for (const l of ["ka", "ru", "en"]) {
      if (!byLang[l]) continue;
      if (!textOf(l)) { miss.push(`Описание (${l}): нет текста — нажми в сервисе «Перевести»`); continue; }
      (await smartSet(byLang[l], textOf(l)) ? ok : miss).push(`Описание (${l})`);
    }
    return { ok, miss };
  }

  // 2) одно поле и переключатели языков РЯДОМ с ним (не трогаем переключатель языка всего сайта)
  const ta0 = tas[0];
  const taTop = ta0.getBoundingClientRect().top + scrollY;
  // вкладка языка должна быть рядом с полем (не дальше ~300px по вертикали) — так не заденем язык всего сайта в шапке
  const near = el => Math.abs(el.getBoundingClientRect().top + scrollY - taTop) < 300 && !el.closest("header");
  let box = ta0, tabs = {};
  for (let i = 0; i < 7 && box && Object.keys(tabs).length < 2; i++) {
    box = box.parentElement;
    if (!box) break;
    tabs = {};
    for (const l of ["ka", "ru", "en"]) {
      const t = findByText(LANG_TABS[l], box, true).find(near);
      if (t) tabs[l] = t;
    }
  }
  if (Object.keys(tabs).length >= 2) {
    for (const l of ["ka", "ru", "en"]) {
      if (!tabs[l]) continue;
      if (!textOf(l)) { miss.push(`Описание (${l}): нет текста — нажми в сервисе «Перевести»`); continue; }
      const tabEl = tabs[l].closest("button, [role=tab], li, a, label") || tabs[l];
      realClick(tabEl); await sleep(700);
      const ta = [...box.querySelectorAll("textarea")].find(el => visible(el)) || areas()[0];
      (ta && await smartSet(ta, textOf(l)) ? ok : miss).push(`Описание (${l})`);
      ta && ta.dispatchEvent(new Event("blur", { bubbles: true }));
      await sleep(300);
    }
    return { ok, miss };
  }

  // 3) одно поле без переключателей — один язык; берём поле с подписью «Описание», а не первое попавшееся
  const labeled = findInputNear(["Описание", "Описание объекта", "Description", "აღწერა"]);
  const target = labeled && labeled.tagName === "TEXTAREA" ? labeled : ta0;
  const l = textOf(fallbackLang) ? fallbackLang : ["ka", "ru", "en"].find(x => textOf(x));
  if (l) (await smartSet(target, textOf(l)) ? ok : miss).push(`Описание (${l})`);
  else miss.push("Описание: нет текста");
  return { ok, miss };
}

// ---------- адрес с подсказками ----------
const ADDRESS_LABELS = ["Адрес", "Улица", "Введите адрес", "Адрес объекта", "Местоположение", "Укажите адрес", "Адрес недвижимости",
  "Местоположение сдаваемого жилья", "Property address", "Location",
  "მისამართი", "ქუჩა", "შეიყვანეთ მისამართი", "Address", "Street", "Enter address"];

function findInputNear(labels) {
  const L = labels.map(norm);
  const inputs = [...document.querySelectorAll(INPUTS)].filter(el => visible(el) && !el.closest("#lh-panel"));
  const hintOf = el => norm(el.placeholder || el.getAttribute("aria-label") || el.name || "");
  for (const el of inputs) { const h = hintOf(el); if (h && L.includes(h) && !USED.has(el)) return el; }
  for (const el of inputs) { const h = hintOf(el); if (h && L.some(l => h.startsWith(l)) && !USED.has(el)) return el; }
  for (const lab of findByText(labels, document, true)) {
    let box = lab;
    for (let i = 0; i < 4 && box; i++) {
      box = box.parentElement;
      const inp = box && [...box.querySelectorAll(INPUTS)].find(el => visible(el) && after(lab, el));
      if (inp) return inp;
    }
  }
  return null;
}

async function typeSlow(el, text) {
  el.focus(); realClick(el);
  setValue(el, "");
  const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
  let cur = "";
  for (const ch of text) {
    cur += ch;
    el.dispatchEvent(new KeyboardEvent("keydown", { key: ch, bubbles: true }));
    setter.call(el, cur);
    el.dispatchEvent(new InputEvent("input", { bubbles: true, data: ch, inputType: "insertText" }));
    el.dispatchEvent(new KeyboardEvent("keyup", { key: ch, bubbles: true }));
    await sleep(45);
  }
}

function suggestionsBelow(el) {
  const top = el.getBoundingClientRect().top;
  const sel = '[role="option"], [role="listbox"] li, .pac-item, [class*="suggest"] li, [class*="Suggest"] li, ' +
    '[class*="autocomplete"] li, [class*="Autocomplete"] li, [class*="option"], [class*="Option"], [class*="dropdown"] li, [class*="menu"] li';
  return [...document.querySelectorAll(sel)].filter(o => visible(o) && !o.closest("#lh-panel") && o !== el &&
    norm(o.innerText).length > 1 && o.getBoundingClientRect().top >= top - 5 && !o.querySelector("input"));
}

async function fillAddress(street) {
  const el = findInputNear(ADDRESS_LABELS);
  if (!el) return "none";
  USED.add(el);
  // для подсказок лучше вводить без «ул.» и номера дома — потом допишем номер, если поле позволяет
  const q = street.replace(/(^|\s)(ул\.|улица|ქ\.|ქუჩა|street|st\.)\s*/gi, " ").replace(/\s+/g, " ").trim();
  await typeSlow(el, q);
  for (let i = 0; i < 8; i++) {   // ждём подсказки до ~4 секунд
    await sleep(500);
    const opts = suggestionsBelow(el);
    if (opts.length) { realClick(opts[0]); await sleep(600); return "selected"; }
  }
  return "typed";
}

// ---------- панель с результатом ----------
function showPanel(title, ok, miss) {
  document.getElementById("lh-panel")?.remove();
  const p = document.createElement("div");
  p.id = "lh-panel";
  p.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:2147483647;width:300px;max-height:60vh;overflow:auto;" +
    "background:#fff;color:#1B2A33;border:1px solid #DCE2E6;border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.18);" +
    "font:13px/1.45 'Segoe UI',system-ui,sans-serif;padding:12px 14px";
  const li = (t, c, mark) => `<li style="list-style:none;margin:2px 0;color:${c}">${mark} ${t.replace(/</g, "&lt;")}</li>`;
  p.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <strong>${title}</strong><button id="lh-close" style="border:0;background:none;font-size:18px;cursor:pointer" aria-label="Закрыть">×</button></div>
    <ul style="padding:0;margin:0">${ok.map(t => li(t, "#2E7D4F", "✓")).join("")}${miss.map(t => li(t, "#B3261E", "✗")).join("")}</ul>
    <p style="margin:8px 0 0;color:#51616C">Проверь форму, дозаполни отмеченное ✗, опубликуй и нажми в расширении «Отметить опубликованным».</p>`;
  document.body.appendChild(p);
  p.querySelector("#lh-close").onclick = () => p.remove();
}

// ---------- сканер формы ----------
function scanForm() {
  const labelOf = el => {
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return l.innerText.trim(); }
    let box = el;
    for (let i = 0; i < 4 && box; i++) {
      box = box.parentElement;
      const t = box && [...box.querySelectorAll("label, span, p, div")].map(x => x.innerText?.trim()).find(t => t && t.length < 50);
      if (t) return t;
    }
    return "";
  };
  const fields = [...document.querySelectorAll("input, textarea, select")].filter(el => el.type !== "hidden").map(el => ({
    tag: el.tagName.toLowerCase(), type: el.type, name: el.name, id: el.id, placeholder: el.placeholder,
    aria: el.getAttribute("aria-label"), label: labelOf(el), visible: visible(el),
    options: el.tagName === "SELECT" ? [...el.options].map(o => o.text) : undefined,
  }));
  const clickables = [...document.querySelectorAll("button, [role=button], [role=radio], [role=tab], label")]
    .filter(visible).map(el => norm(el.innerText)).filter(t => t && t.length < 50);
  const headings = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6,legend,p,span")]
    .filter(visible).map(el => el.innerText?.trim()).filter(t => t && t.length < 60 && !t.includes("\n"));
  let extracted = null; try { const e = extractPage(); extracted = { guess: e.guess, photos: e.photo_urls.length, title: e.title, textStart: e.text.slice(0, 4000) }; } catch {}
  const data = { url: location.href, scannedAt: new Date().toISOString(), extracted, fields,
    clickables: [...new Set(clickables)], texts: [...new Set(headings)].slice(0, 400) };
  const blob = new Blob([JSON.stringify(data, null, 1)], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `${location.hostname.replace(/\W+/g, "-")}-form-scan.json` });
  document.body.appendChild(a); a.click(); a.remove();
  return fields.length;
}

// ---------- сохранение объявления со страницы ----------
function num(s) { const m = String(s).replace(/[\s\u00a0]/g, "").replace(",", ".").match(/\d+(\.\d+)?/); return m ? parseFloat(m[0]) : null; }

function guessFields(text) {
  const g = {};
  // цена: число с валютой на ОДНОЙ строке; из всех вариантов в начале страницы берём самый правдоподобный (крупный)
  const priceHead = text.slice(0, 4000);
  const cands = [];
  for (const mm of priceHead.matchAll(/(\d[\d \u00a0.,]{2,})[ \u00a0]*\n?[ \u00a0]*(\$|USD|₾|GEL|ლარი|лари)/gi)) cands.push([mm.index, mm[1], mm[2]]);
  for (const mm of priceHead.matchAll(/(\$|₾)[ \u00a0]*(\d[\d \u00a0.,]{2,})/g)) cands.push([mm.index, mm[2], mm[1]]);
  // по порядку на странице: первая цена — у основного объявления, похожие ниже
  const parsed = cands.sort((a, b) => a[0] - b[0]).map(([, a, c]) => [Math.round(num(a.replace(/[.,](?=\d{3}(\D|$))/g, ""))), c])
    .filter(([v]) => v >= 1000);
  let m;
  if (parsed.length) {
    // в долларах, если на странице есть цена в долларах
    const usd = parsed.find(([, c]) => /\$|USD/i.test(c));
    const [v, c] = usd || parsed[0];
    g.price = v;
    if (/₾|GEL|ლარი|лари/i.test(c)) g.currency = "GEL";
  }
  m = text.match(/(?:площадь|area|ფართი)\s*:?\s*(\d+[.,]?\d*)\s*(?:м²|м2|m²|m2|მ²|кв)/i)
    || text.match(/(?:^|\n|\s)(\d{2,4}[.,]?\d*)\s*(м²|м2|кв\.?\s*м|m²|m2|sq\.?\s*m|მ²|კვ\.?\s*მ)(?!\s*-)/i);
  if (m) g.area = num(m[1]);
  m = text.match(/(?:^|\n)\s*(?:комнат[а-яё]*|количество комнат|число комнат|rooms?|number of rooms|ოთახ[ა-ჰ]*)\s*:?\s*\n?\s*(\d{1,2})\s*(?:\n|$)/i)
    || text.match(/(\d+)\s*-?\s*(комн|room|ოთახ)/i);
  if (m) g.rooms = +m[1];
  else if (/студи|studio|სტუდიო/i.test(text.slice(0, 1500))) g.rooms = 1;
  m = text.match(/(?:^|\n)\s*(?:спал[а-яё]*|количество спален|число спален|bedrooms?|number of bedrooms|საძინებ[ა-ჰ]*)\s*:?\s*\n?\s*(\d{1,2})\s*(?:\n|$)/i)
    || text.match(/(\d+)\s*-?\s*(спал|bedroom|საძინებ)/i);
  if (m) g.bedrooms = +m[1];
  m = text.match(/(?:этаж|floor|სართული)\s*:?\s*(\d{1,3})\s*(?:\/|из|of)\s*(\d{1,3})(?!\d)/i)   // этаж 6 / 7
    || text.match(/(?:^|\n|\s)(\d{1,3})\s*(?:этаж|floor|სართული)\s*\/\s*(\d{1,3})(?!\d)/i)        // 15 этаж/23
    || text.match(/(\d{1,3})\s*(?:-?й|-?м)?\s*этаж[а-яё]*\s*из\s*(\d{1,3})/i)                        // 6-й этаж из 7
    || text.match(/(?:^|\n)\s*(\d{1,3})\s*\/\s*(\d{1,3})\s*\n+\s*(?:этаж|floor|სართული)/i)         // 6 / 7 ↵ этаж
    || text.match(/(\d{1,3})\s*\/\s*(\d{1,3})\s*(?:эт|floor|სართ)/i);                                     // 11/12 эт.
  if (m && +m[1] <= +m[2] + 1 && +m[2] < 80) { g.floor = +m[1]; g.floors_total = +m[2]; }
  else {
    m = text.match(/(?:^|\n)\s*(?:этаж|floor|სართული)\s*:?\s*\n?\s*(\d+)\b/i); if (m) g.floor = +m[1];
    m = text.match(/(?:этажность|всего этажей|этажей в доме|total floors|სართულიანობა)\s*:?\s*\n?\s*(\d+)/i); if (m) g.floors_total = +m[1];
  }
  if (!g.area) { m = text.match(/(?:площадь|area|ფართი)\s*:?\s*\n?\s*(\d+[.,]?\d*)/i); if (m) g.area = num(m[1]); }
  const head0 = text.slice(0, 4000);
  m = head0.match(/(?:^|\n)\s*([ა-ჰ][ა-ჰ.\- ]{1,40}\s(?:ქუჩა|ქ\.|გამზირი|გამზ\.|შესახვევი|შეს\.|ჩიხი|ხეივანი|მოედანი|დასახლება)(?:\s*\([^)\n]{1,30}\))?(?:\s*\d+[ა-ჰa-zа-я]?)?)\s*(?:\n|$)/)
    || head0.match(/(?:^|\n)\s*((?:ул\.|улица|пр\.|проспект|пер\.|переулок)\s*[^\n,]{2,50}(?:,?\s*\d+[а-яa-z]?)?)\s*(?:\n|$)/i)
    || head0.match(/(?:^|\n)\s*([A-Z][\w.\- ]{1,40}\s(?:Street|St\.|Avenue|Ave\.|Lane|Square|Highway)(?:\s*\d+[a-z]?)?)\s*(?:\n|$)/)
    || head0.match(/(?:адрес|address|მისამართი)\s*:?\s*\n?\s*([^\n]{3,60})/i);
  if (m) g.address = m[1].trim();
  const DISTRICTS = ["Ваке", "Сабуртало", "Ортачала", "Крцаниси", "Дигоми", "Дидубе", "Глдани", "Надзаладеви", "Исани", "Самгори",
    "Мтацминда", "Чугурети", "Старый Тбилиси", "Варкетили", "Сололаки", "Вера", "Авлабари", "Лиси", "Бахтриони",
    "ვაკე", "საბურთალო", "ორთაჭალა", "კრწანისი", "დიღომი", "დიდუბე", "გლდანი", "ნაძალადევი", "ისანი", "სამგორი",
    "მთაწმინდა", "ჩუღურეთი", "ძველი თბილისი", "ვარკეთილი", "სოლოლაკი", "ვერა", "ავლაბარი", "ლისი", "ბახტრიონი",
    "Vake", "Saburtalo", "Ortachala", "Krtsanisi", "Digomi", "Didube", "Gldani", "Nadzaladevi", "Isani", "Samgori", "Mtatsminda", "Old Tbilisi", "Vera"];
  const head = text.slice(0, 2500);
  const dist = DISTRICTS.map(x => [x, head.search(new RegExp("(^|[^\\wა-ჰ])" + x + "($|[^\\wა-ჰ])", "i"))]).filter(x => x[1] >= 0).sort((a, b) => a[1] - b[1])[0];
  if (dist) g.district = dist[0];
  return g;
}

function pagePhotos() {
  const urls = new Set();
  const add = u => { try { if (u && !u.startsWith("data:") && !/\.svg(\?|$)/i.test(u)) urls.add(new URL(u, location.href).href); } catch {} };
  document.querySelectorAll('meta[property="og:image"]').forEach(m => add(m.content));
  for (const img of document.images) {
    if (img.closest("header, footer, nav, #lh-panel")) continue;
    const src = img.currentSrc || img.src;
    if (/logo|icon|avatar|sprite|banner|flag|placeholder/i.test(src + " " + img.className + " " + img.alt)) continue;
    // берём самый крупный вариант из srcset
    const best = (img.srcset || "").split(",").map(x => x.trim().split(/\s+/)).filter(x => x[0])
      .sort((a, b) => (parseInt(b[1]) || 0) - (parseInt(a[1]) || 0))[0];
    if ((img.naturalWidth || img.width) >= 300 || best) add(best ? best[0] : src);
  }
  // фото, заданные фоном (часто в галереях)
  document.querySelectorAll("[style*='background-image']").forEach(el => {
    const m = el.style.backgroundImage.match(/url\(["']?(.*?)["']?\)/); if (m && el.offsetWidth >= 300) add(m[1]);
  });
  return [...urls].slice(0, 25);
}

// Структурированные данные страницы: многие сайты (MyHome, SS.ge и др.) кладут объявление целиком
// в JSON внутри страницы (__NEXT_DATA__ и т.п.). Ищем объект, больше всего похожий на объявление.
const KEY_HINTS = /^(roomsCount|roomCount|bedroomsCount|bedroomCount|totalFloors|floorsCount|floorNumber|totalArea|price|price_usd|total_price|area|total_area|square|floor|floors|total_floors|floors_total|floor_count|room|rooms|room_count|room_type_id|bedroom|bedrooms|bedroom_count|bedroom_type_id|comment|description|address|street|street_name|street_title|urban_name|district_name|city_name|lat|lng|images|photos|gallery)$/i;

function collectJson() {
  const out = [];
  document.querySelectorAll('script[type="application/json"], script#__NEXT_DATA__, script[type="application/ld+json"]').forEach(sc => {
    try { out.push(JSON.parse(sc.textContent)); } catch {}
  });
  return out;
}

function bestListingObject(roots) {
  const cands = []; let seen = 0;
  const walk = (o, depth) => {
    if (!o || typeof o !== "object" || depth > 16 || ++seen > 300000) return;
    if (!Array.isArray(o)) {
      const score = Object.keys(o).filter(k => KEY_HINTS.test(k)).length;
      if (score >= 3) cands.push({ o, score, depth });
    }
    for (const v of Object.values(o)) if (v && typeof v === "object") walk(v, depth + 1);
  };
  roots.forEach(r => walk(r, 0));
  if (!cands.length) return null;
  // 1) ID объявления из адреса страницы (на MyHome — 7–9 цифр)
  const ids = (location.pathname.match(/\d{6,}/g) || []);
  const byId = cands.filter(c => ["id", "statement_id", "uuid", "listing_id", "application_id", "product_id"]
    .some(k => c.o[k] != null && ids.includes(String(c.o[k]))));
  if (byId.length) return byId.sort((a, b) => b.score - a.score)[0].o;
  // 2) иначе — объект, чья площадь/комнаты совпадают с заголовком, а среди равных — самый «неглубокий»
  const title = (document.querySelector("h1")?.innerText || document.title).toLowerCase();
  const titleRooms = (title.match(/(\d+)\s*-?\s*(комн|room|ოთახ)/) || [])[1];
  const fit = c => (titleRooms && [c.o.room, c.o.rooms, c.o.room_count].map(String).includes(titleRooms) ? 2 : 0);
  return cands.sort((a, b) => (fit(b) - fit(a)) || (b.score - a.score) || (a.depth - b.depth))[0].o;
}

function fieldsFromObject(o) {
  const f = {}, photos = [];
  const n = v => (typeof v === "number" ? v : (typeof v === "string" && /^\s*[\d\s.,]+\s*$/.test(v) ? num(v) : null));
  const priceOf = v => {
    if (n(v)) return n(v);
    if (v && typeof v === "object") {
      // {usd: ..., gel: ...}
      for (const [k, x] of Object.entries(v)) if (/usd|dollar/i.test(k) && (n(x) || priceOf(x))) return n(x) || priceOf(x);
      // {"1": {price_total}, "2": {...}, "3": {...}} — цена в нескольких валютах (лари, доллары, евро).
      // Лари всегда самое большое число, евро чуть меньше доллара: при трёх валютах доллар — средний, при двух — меньший.
      const vals = Object.values(v).map(x => n(x) || (x && typeof x === "object" && (n(x.price_total) || n(x.price)))).filter(Boolean).sort((a, b) => a - b);
      if (vals.length >= 3) return vals[Math.floor(vals.length / 2)];
      if (vals.length) return vals[0];
    }
    return null;
  };
  for (const [k, v] of Object.entries(o)) {
    const key = k.replace(/([a-z])([A-Z])/g, "$1_$2").toLowerCase();   // roomsCount → rooms_count
    if (/^(price|price_usd|total_price|price_total)$/.test(key) && !f.price) { const p = priceOf(v); if (p) f.price = Math.round(p); }
    else if (/^(area|total_area|square|area_total|area_value|total_square)$/.test(key) && n(v)) f.area = n(v);
    else if (/^(floor|floor_number|flat_floor)$/.test(key) && n(v) !== null) f.floor = n(v);
    else if (/^(total_floors|floors_total|floors|building_floors|floor_count|total_floor|floors_count|number_of_floors|max_floor|house_floors)$/.test(key) && n(v)) f.floors_total = n(v);
    else if (/^(room|rooms|room_count|rooms_count|rooms_number|number_of_rooms|room_quantity)$/.test(key) && n(v)) f.rooms = n(v);
    else if (/^(bedroom|bedrooms|bedroom_count|bedrooms_count|number_of_bedrooms|bedroom_quantity)$/.test(key) && n(v)) f.bedrooms = n(v);
    else if (/^(comment|description|text)$/.test(key) && typeof v === "string" && v.length > 30) f.description = v;
    else if (/^(address|street|street_address|street_name|street_title|full_address|address_ka|address_ru)$/.test(key) && typeof v === "string" && v.trim() && !f.address)
      f.address = (v + (o.street_number || o.house_number ? " " + (o.street_number || o.house_number) : "")).trim();
    else if (/^(address|location)$/.test(key) && v && typeof v === "object" && !Array.isArray(v)) {
      const st = v.street || v.street_name || v.address || v.name, no = v.number || v.house || v.street_number;
      if (typeof st === "string" && !f.address) f.address = st + (no ? " " + no : "");
      for (const [kk, vv] of Object.entries(v)) if (/district|urban/i.test(kk) && typeof vv === "string" && !f.district) f.district = vv;
    }
    else if (/^(urban|urban_name|district|district_name|subdistrict|subdistrict_name|neighborhood)$/.test(key) && typeof v === "string" && !f.district) f.district = v;
    else if (/^(urban|district)$/.test(key) && v && typeof v === "object" && typeof v.name === "string" && !f.district) f.district = v.name;
    else if (/^(city|city_name)$/.test(key) && typeof v === "string") f.city = v;
    else if (key === "city" && v && typeof v === "object" && typeof v.name === "string") f.city = v.name;
    else if (/^(images|photos|gallery|pictures)$/.test(key) && Array.isArray(v)) {
      for (const im of v) {
        const u = typeof im === "string" ? im : im && (im.large || im.big || im.original || im.url || im.src || im.thumb);
        if (typeof u === "string" && /^(https?:\/\/|\/\/|\/)/.test(u) && !/\.svg(\?|$)/i.test(u)) {
          try { photos.push(new URL(u, location.href).href); } catch {}
        }
      }
    }
  }
  return { fields: f, photos };
}

// Текст страницы без «похожих объявлений», рекламы и подвала
function mainText() {
  let t = (document.body.innerText || "").replace(/\n{3,}/g, "\n\n");
  const stop = t.slice(400).search(/Похожие|Вам также|Рекомендуем|Similar|You may also|მსგავსი|ასევე დაგაინტერესებთ/i);
  if (stop > 0) t = t.slice(0, stop + 400);
  return t.slice(0, 15000);
}

function extractPage() {
  const title = (document.querySelector("h1")?.innerText || document.querySelector('meta[property="og:title"]')?.content || document.title).trim();
  const text = mainText();
  const guess = guessFields(title + "\n" + text);
  const obj = bestListingObject(collectJson());
  let photos = [];
  if (obj) {
    const { fields, photos: ph } = fieldsFromObject(obj);
    for (const [k, v] of Object.entries(fields)) {
      if (v === null || v === undefined || v === "") continue;
      if (k === "floor" && fields.floors_total && v > fields.floors_total + 1) continue;   // этаж выше этажности — мусор
      guess[k] = v;   // данные из JSON страницы точнее, чем разбор текста
    }
    if (guess.floor && guess.floors_total && guess.floor > guess.floors_total + 1) delete guess.floors_total;
    if (fields.price) delete guess.currency;  // цену из JSON берём в долларах
    photos = ph;
  }
  if (!guess.description) {
    const paras = [...document.querySelectorAll("p, div, span")].filter(el => !el.children.length || el.tagName === "P")
      .map(el => (el.innerText || "").trim()).filter(t => t.length > 80 && t.length < 5000 && text.includes(t.slice(0, 60)));
    if (paras.length) guess.description = paras.sort((a, b) => b.length - a.length)[0];
  }
  const all = [...new Set([...photos, ...pagePhotos()])].slice(0, 25);
  return { source_url: location.href.split("#")[0], title, text, guess, photo_urls: all };
}

// ---------- список объявлений со страницы выдачи (для CRM) ----------
// Читаем только то, что уже есть на открытой странице: никаких дополнительных запросов к сайту.
function listingId(href) {
  try { const m = new URL(href, location.href).pathname.match(/(\d{6,})/); return m ? m[1] : null; } catch { return null; }
}

function extractList() {
  // 1) ссылки на объявления
  const links = new Map();
  for (const a of document.querySelectorAll("a[href]")) {
    const id = listingId(a.href);
    if (!id || a.closest("header, footer, #lh-panel")) continue;
    if (id === listingId(location.href)) continue;
    if (!links.has(id)) links.set(id, a);
  }
  // 2) данные из JSON страницы по ID
  const byId = {}; let seen = 0;
  const walk = (o, depth) => {
    if (!o || typeof o !== "object" || depth > 16 || ++seen > 300000) return;
    if (!Array.isArray(o) && (o.id != null || o.statement_id != null)) {
      const score = Object.keys(o).filter(k => KEY_HINTS.test(k)).length;
      const id = String(o.id ?? o.statement_id);
      if (score >= 3 && (!byId[id] || byId[id].score < score)) byId[id] = { o, score };
    }
    for (const v of Object.values(o)) if (v && typeof v === "object") walk(v, depth + 1);
  };
  collectJson().forEach(r => walk(r, 0));

  const items = [];
  for (const [id, a] of links) {
    // карточка: поднимаемся, пока внутри нет ссылок на другие объявления
    let card = a;
    for (let i = 0; i < 8 && card.parentElement; i++) {
      const p = card.parentElement;
      const ids = new Set([...p.querySelectorAll("a[href]")].map(x => listingId(x.href)).filter(Boolean));
      if (ids.size > 1) break;
      card = p;
    }
    const text = (card.innerText || "").slice(0, 1500);
    const item = { source_url: new URL(a.href, location.href).href.split("#")[0], listing_id: id };
    const j = byId[id] ? fieldsFromObject(byId[id].o) : { fields: {}, photos: [] };
    Object.assign(item, guessFields(text), j.fields);
    // в карточке выдачи этаж часто записан просто «5/12», а адрес — «ქ. ვაჟა-ფშაველა 12»
    if (!item.floor) {
      const fm = text.match(/(?:^|\n)\s*(\d{1,2})\s*\/\s*(\d{1,2})\s*(?:\n|$)/);
      if (fm && +fm[1] <= +fm[2] + 1) { item.floor = +fm[1]; item.floors_total = +fm[2]; }
    }
    if (!item.address) {
      const am = text.match(/(?:^|\n)\s*((?:ქ\.|ქუჩა|გამზ\.|გამზირი)\s*[ა-ჰ][^\n]{2,50})\s*(?:\n|$)/);
      if (am) item.address = am[1].trim();
    }
    if (j.fields.price) delete item.currency;
    const img = card.querySelector("img");
    item.photo = j.photos[0] || (img && (img.currentSrc || img.src)) || "";
    item.title = (card.querySelector("h2, h3, h4, [class*=title]")?.innerText || a.innerText || "").trim().split("\n")[0].slice(0, 120);
    delete item.description;
    // кто продаёт: собственник или агентство
    const o = byId[id]?.o || {};
    const ownerFlag = [o.is_owner, o.owner, o.isOwner].find(v => typeof v === "boolean");
    const agentFlag = [o.is_agency, o.isAgency, o.is_agent, o.isAgent].find(v => typeof v === "boolean");
    if (ownerFlag === true || agentFlag === false || /собственник|მესაკუთრე|\bowner\b/i.test(text)) item.seller = "owner";
    else if (agentFlag === true || ownerFlag === false || /агент|агентств|სააგენტო|აგენტ|\bagen(t|cy)\b|девелопер|застройщик|დეველოპერ/i.test(text)) item.seller = "agent";
    if (item.price || item.area || item.rooms) items.push(item);
  }
  return { page_url: location.href, items };
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  (async () => {
    try {
      if (msg.type === "scan") return reply({ ok: true, count: scanForm() });
      if (msg.type === "extract") return reply({ ok: true, page: extractPage() });
      if (msg.type === "extractList") return reply({ ok: true, list: extractList() });
      if (msg.type === "scrollLoad") {   // карточки и фото подгружаются при прокрутке
        for (let y = 0; y < document.body.scrollHeight; y += Math.max(400, innerHeight * 0.8)) { scrollTo(0, y); await sleep(250); }
        await sleep(600); scrollTo(0, 0);
        return reply({ ok: true });
      }
      if (msg.type === "fill") {
        const { ok, miss } = await fillForm(msg.platform, msg.listing, msg.photos || [], msg.lang || "ka", msg.contact || {}, msg.rate || 0);
        showPanel("Listing Hub: форма заполнена", ok, miss);
        return reply({ ok: true, filled: ok.length, missed: miss.length });
      }
    } catch (e) { reply({ ok: false, error: String(e) }); }
  })();
  return true; // ответ асинхронный
});
}
