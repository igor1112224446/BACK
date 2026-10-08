"""
Генератор объявлений без ИИ: пишет заголовок и описание своими словами на грузинском, русском
и английском — только из фактов объекта. Исходный текст объявления не копируется: из него берутся
лишь признаки (балкон, парковка, мебель, вид и т.п.).
Формулировки чередуются, чтобы объявления не были одинаковыми; для одного объекта текст стабилен.
"""
import hashlib
import re

# признак → (регулярка по исходному тексту, ru, ka, en)
FEATURES = [
    ("balcony", r"балкон|лоджи|აივან|ლოჯი|balcon", "балкон", "აივანი", "balcony"),
    ("terrace", r"террас|ტერას|terrace", "терраса", "ტერასა", "terrace"),
    ("parking", r"парков|паркинг|гараж|პარკინგ|ავტოსადგომ|გარაჟ|parking|garage", "парковка", "პარკინგი", "parking"),
    ("furniture", r"мебел|меблир|ავეჯ|furnish|furniture", "мебель", "ავეჯი", "furniture"),
    ("appliances", r"бытов\w* техник|техник[аиу]|ტექნიკ|appliance", "бытовая техника", "ტექნიკა", "appliances"),
    ("view", r"вид на|видом на|панорам|ხედ|view", "красивый вид из окон", "ლამაზი ხედი", "a beautiful view"),
    ("heating", r"центральн\w* отоплен|ცენტრალური გათბობ|central heating", "центральное отопление", "ცენტრალური გათბობა", "central heating"),
    ("elevator", r"лифт|ლიფტ|elevator|\blift\b", "лифт", "ლიფტი", "an elevator"),
    ("storage", r"кладов|სათავს|storage", "кладовая", "სათავსო", "a storage room"),
    ("pool", r"бассейн|აუზ|pool", "бассейн", "აუზი", "a swimming pool"),
    ("ac", r"кондиционер|კონდიციონ|air.?condition", "кондиционер", "კონდიციონერი", "air conditioning"),
    ("gas", r"\bгаз\b|ბუნებრივი აირ|natural gas", "газ", "ბუნებრივი აირი", "natural gas"),
]
NEARBY = [
    ("metro", r"метро|მეტრო|metro|subway", "метро", "მეტრო", "the metro"),
    ("park", r"(?<!\w)парк(а|е|ом|и|у)?(?!\w)|პარკ(ი|თან|ის|ში)(?![ა-ჰ])|\bparks?\b", "парк", "პარკი", "a park"),
    ("school", r"школ|სკოლ|school", "школа", "სკოლა", "a school"),
    ("kindergarten", r"детск\w* сад|საბავშვო ბაღ|kindergarten", "детский сад", "საბავშვო ბაღი", "a kindergarten"),
    ("shops", r"магазин|супермаркет|მაღაზი|სუპერმარკეტ|shop|supermarket", "магазины", "მაღაზიები", "shops"),
]

CONDITION = {  # ru (после «Квартира»), ka (готовое предложение), en
    "new_renovation": ("со свежим ремонтом", "ბინაში გაკეთებულია ახალი რემონტი.", "freshly renovated"),
    "old_renovation": ("с ремонтом", "ბინა გარემონტებულია.", "renovated"),
    "white_frame": ("в белом каркасе", "ბინა თეთრ კარკასშია.", "in white frame condition"),
    "black_frame": ("в чёрном каркасе", "ბინა შავ კარკასშია.", "in black frame condition"),
    "green_frame": ("в зелёном каркасе", "ბინა მწვანე კარკასშია.", "in green frame condition"),
    "needs_renovation": ("под ремонт", "ბინა საჭიროებს რემონტს.", "in need of renovation"),
}
BUILDING = {  # ru, ka (предложение), en
    "new_building": ("в новостройке", "სახლი ახალი აშენებულია.", "in a new building"),
    "old_building": ("в доме старой постройки", "სახლი ძველი აშენებულია.", "in an older building"),
    "under_construction": ("в строящемся доме", "სახლი მშენებარეა.", "in a building under construction"),
}

# (именительный, винительный) — «Продаётся светлая…» / «Предлагаем светлую…»
RU_ADJ = [("светлая", "светлую"), ("просторная", "просторную"), ("уютная", "уютную"), ("комфортная", "комфортную")]
# (именительный, дательный) — «იყიდება ნათელი…» / «გთავაზობთ ნათელ…»
KA_ADJ = [("ნათელი", "ნათელ"), ("ფართო", "ფართო"), ("მყუდრო", "მყუდრო"), ("კომფორტული", "კომფორტულ")]
EN_ADJ = ["bright", "spacious", "cozy", "comfortable"]


# ---------- названия мест на трёх языках ----------
PLACES = {  # ru: (ka, en)
    "Тбилиси": ("თბილისი", "Tbilisi"), "Батуми": ("ბათუმი", "Batumi"), "Кутаиси": ("ქუთაისი", "Kutaisi"),
    "Ваке": ("ვაკე", "Vake"), "Сабуртало": ("საბურთალო", "Saburtalo"), "Ортачала": ("ორთაჭალა", "Ortachala"),
    "Крцаниси": ("კრწანისი", "Krtsanisi"), "Дигоми": ("დიღომი", "Digomi"), "Диди Дигоми": ("დიდი დიღომი", "Didi Digomi"),
    "Дидубе": ("დიდუბე", "Didube"), "Глдани": ("გლდანი", "Gldani"), "Надзаладеви": ("ნაძალადევი", "Nadzaladevi"),
    "Исани": ("ისანი", "Isani"), "Самгори": ("სამგორი", "Samgori"), "Мтацминда": ("მთაწმინდა", "Mtatsminda"),
    "Чугурети": ("ჩუღურეთი", "Chughureti"), "Старый Тбилиси": ("ძველი თბილისი", "Old Tbilisi"),
    "Варкетили": ("ვარკეთილი", "Varketili"), "Сололаки": ("სოლოლაკი", "Sololaki"), "Вера": ("ვერა", "Vera"),
    "Ваке-Сабуртало": ("ვაკე-საბურთალო", "Vake-Saburtalo"), "Авлабари": ("ავლაბარი", "Avlabari"),
    "Ортачальский": ("ორთაჭალა", "Ortachala"), "Лиси": ("ლისი", "Lisi"), "Бахтриони": ("ბახტრიონი", "Bakhtrioni"),
}
RU_KA = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                 ["ა","ბ","ვ","გ","დ","ე","ე","ჟ","ზ","ი","ი","კ","ლ","მ","ნ","ო","პ","რ","ს","ტ","უ","ფ","ხ","ც","ჩ","შ","შ","","ი","","ე","იუ","ია"]))
RU_EN = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                 ["a","b","v","g","d","e","e","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","y","","e","yu","ya"]))
KA_RU = dict(zip("აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ",
                 ["а","б","г","д","е","в","з","т","и","к","л","м","н","о","п","ж","р","с","т","у","п","к","г","к","ш","ч","ц","дз","ц","ч","х","дж","х"]))
KA_EN = dict(zip("აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ",
                 ["a","b","g","d","e","v","z","t","i","k","l","m","n","o","p","zh","r","s","t","u","p","k","gh","q","sh","ch","ts","dz","ts","ch","kh","j","h"]))


def _tr(text, table):
    out = []
    for ch in text:
        low = ch.lower()
        if low in table:
            t = table[low]
            out.append(t.capitalize() if ch != low and t else t)
        else:
            out.append(ch)
    return "".join(out)


def localize(text, lang):
    """Район/адрес → нужный язык: словарь известных мест, иначе транслитерация."""
    if not text:
        return ""
    t = str(text).strip()
    was_georgian = bool(re.search(r"[ა-ჰ]", t))
    if lang != "ka":
        # грузинский порядок «მაღალაშვილის ქუჩა 5» → «ул. Магалашвили 5» / «Maghalashvili St. 5»
        kinds = {"ქუჩა": ("ул.", "St."), "ქ.": ("ул.", "St."), "გამზირი": ("пр.", "Ave."), "გამზ.": ("пр.", "Ave."),
                 "შესახვევი": ("пер.", "Lane"), "შეს.": ("пер.", "Lane"), "ჩიხი": ("тупик", "Dead End"), "მოედანი": ("пл.", "Sq.")}
        def reorder(m):
            name, kind, rest = m.group(1).strip(), m.group(2), (m.group(3) or "").strip()
            name = re.sub(r"([ა-ჰ]{2,})ის$", r"\1ი", name)   # родительный падеж → именительный
            ru, en = kinds[kind]
            return (f"{ru} {name} {rest}" if lang == "ru" else f"{name} {en} {rest}").strip()
        t = re.sub(r"([ა-ჰ][ა-ჰ.\- ]*?)\s+(ქუჩა|ქ\.|გამზირი|გამზ\.|შესახვევი|შეს\.|ჩიხი|მოედანი)(\s*\d+[ა-ჰa-z]?)?", reorder, t)
    segs = [(t, False)]  # (текст, уже переведён)

    def sub_free(pattern, repl, flags=0):
        nonlocal segs
        out = []
        for seg, done in segs:
            if done:
                out.append((seg, True)); continue
            pos = 0
            for m in re.finditer(pattern, seg, flags):
                out.append((seg[pos:m.start()], False)); out.append((repl, True)); pos = m.end()
            out.append((seg[pos:], False))
        segs = [x for x in out if x[0]]

    # сначала длинные названия, только целыми словами («Лиси» не должно ломать «Тбилиси»)
    for ru, (ka, en) in sorted(PLACES.items(), key=lambda kv: -len(kv[0])):
        dst = {"ru": ru, "ka": ka, "en": en}[lang]
        for src in (ru, ka, en):
            sub_free(r"(?<![\wა-ჰ])" + re.escape(src) + r"(?![\wა-ჰ])", dst, re.I)
    street = {"ka": "ქ. ", "en": "", "ru": "ул. "}[lang]
    sub_free(r"(?<!\w)(ул\.|улица)\s*", street, re.I)
    sub_free(r"(ქ\.|ქუჩა)\s*", street)
    sub_free(r"(?<!\w)(пр\.|проспект)\s*", {"ka": "გამზ. ", "en": "Ave. ", "ru": "пр. "}[lang], re.I)
    sub_free(r"(გამზ\.|გამზირი)\s*", {"ka": "გამზ. ", "en": "Ave. ", "ru": "пр. "}[lang])

    if lang == "ka":
        sub_free(r"дж", "ჯ", re.I); sub_free(r"дз", "ძ", re.I)
    table = {"ka": RU_KA, "en": {**RU_EN, **KA_EN}, "ru": KA_RU}[lang]
    res = "".join(seg if done else _tr(seg, table) for seg, done in segs)
    if was_georgian and lang != "ka":  # в грузинском нет заглавных — делаем их у названий
        res = re.sub(r"(?<![\w])([a-zа-яё])(?=[\w-]{2,})", lambda m: m.group(1).upper(), res)
        res = re.sub(r"(?<![\w])([a-zа-яё])(?=\.)", lambda m: m.group(1).upper(), res)
    return res.strip()


def _pick(options, seed, salt):
    h = int(hashlib.md5(f"{seed}-{salt}".encode()).hexdigest(), 16)
    return options[h % len(options)]


def _ru_plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _num(v):
    try:
        f = float(v)
        return int(f) if f.is_integer() else round(f, 1)
    except (TypeError, ValueError):
        return None


def _ka_floor(n):
    return "პირველ" if n == 1 else f"მე-{n}"


def _join(items, last_ru="и"):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {last_ru} " + items[-1]


def detect(text):
    text = (text or "").lower()
    feats = [f for f in FEATURES if re.search(f[1], text)]
    near = [f for f in NEARBY if re.search(f[1], text)]
    return feats, near


def generate(d, phone, name=""):
    rooms, bedrooms = _num(d.get("rooms")), _num(d.get("bedrooms"))
    area, floor, floors = _num(d.get("area")), _num(d.get("floor")), _num(d.get("floors_total"))
    L = {lang: (localize(d.get("district"), lang), localize(d.get("address"), lang), localize(d.get("city"), lang))
         for lang in ("ru", "ka", "en")}
    district, address, city = L["ru"]
    seed = d.get("source_url") or f"{rooms}-{area}-{floor}-{d.get('price')}"
    cur = "$"   # цены только в долларах
    price = f"{int(float(d['price'])):,}".replace(",", " ") + f" {cur}" if _num(d.get("price")) else ""
    feats, near = detect(" ".join(str(d.get(k) or "") for k in ("notes", "features", "title")))
    cond = CONDITION.get(d.get("condition"))
    bld = BUILDING.get(d.get("building_status"))
    who_ru = f" ({name})" if name else ""

    # ---------- русский ----------
    adj_nom, adj_acc = _pick(RU_ADJ, seed, "ru_adj")
    flat_nom = f"{rooms}-комнатная квартира" if rooms else "квартира"
    flat_acc = f"{rooms}-комнатную квартиру" if rooms else "квартиру"
    intro = _pick([
        f"Предлагаем к продаже {adj_acc} {flat_acc}" + (f" площадью {area} м²" if area else ""),
        f"В продаже {adj_nom} {flat_nom}" + (f" общей площадью {area} м²" if area else ""),
        f"Продаётся {adj_nom} {flat_nom}" + (f", {area} м²" if area else ""),
    ], seed, "ru_intro")
    ru = [intro + (f" в районе {district}" if district else "") + "."]
    if floor:
        ru.append(f"Квартира находится на {floor}-м этаже" + (f" {floors}-этажного дома" if floors else "") +
                  (f" {bld[0]}" if bld else "") + ".")
    elif bld:
        ru.append(f"Квартира находится {bld[0]}.")
    if bedrooms:
        ru.append(f"В квартире {bedrooms} {_ru_plural(bedrooms, 'спальня', 'спальни', 'спален')}" +
                  (f", она {cond[0]}." if cond else "."))
    elif cond:
        ru.append(f"Квартира {cond[0]}.")
    if feats:
        ru.append(_pick(["Из преимуществ: ", "Есть ", "Для удобства: "], seed, "ru_feat") +
                  _join([f[2] for f in feats]) + ".")
    if near:
        ru.append("Рядом " + _join([f[2] for f in near]) + ".")
    if address:
        ru.append(f"Адрес: {', '.join(x for x in (city, address) if x)}.")
    if price:
        ru.append(f"Цена: {price}.")
    ru.append(_pick(["Звоните, покажу квартиру в удобное для вас время",
                     "Звоните, отвечу на вопросы и организую просмотр",
                     "Буду рад показать квартиру, звоните"], seed, "ru_end") + f": {phone}{who_ru}.")
    ru_title = "Продаётся " + flat_nom + (f", {area} м²" if area else "") + (f", {district}" if district else "")

    # ---------- ქართული ----------
    district, address, city = L["ka"]
    ka_nom, ka_dat = _pick(KA_ADJ, seed, "ka_adj")
    ka_intro = _pick([
        f"გთავაზობთ {ka_dat} " + (f"{rooms}-ოთახიან " if rooms else "") + "ბინას" + (f", საერთო ფართით {area} მ²" if area else ""),
        f"იყიდება {ka_nom} " + (f"{rooms}-ოთახიანი " if rooms else "") + "ბინა" + (f", ფართი {area} მ²" if area else ""),
    ], seed, "ka_intro")
    ka = [ka_intro + "."]
    if district:
        ka.append(f"მდებარეობა: {district}.")
    if floor:
        ka.append("ბინა მდებარეობს " + (f"{floors}-სართულიანი სახლის " if floors else "") + f"{_ka_floor(floor)} სართულზე.")
    if bld:
        ka.append(bld[1])
    if bedrooms:
        ka.append(f"ბინაში არის {bedrooms} საძინებელი.")
    if cond:
        ka.append(cond[1])
    if feats:
        ka.append("უპირატესობები: " + ", ".join(f[3] for f in feats) + ".")
    if near:
        ka.append("ახლოს: " + ", ".join(f[3] for f in near) + ".")
    if address:
        ka.append(f"მისამართი: {', '.join(x for x in (city, address) if x)}.")
    if price:
        ka.append(f"ფასი: {price}.")
    ka.append(_pick(["დამიკავშირდით ბინის სანახავად", "დარეკეთ, გაჩვენებთ ბინას თქვენთვის მოსახერხებელ დროს",
                     "დამატებითი ინფორმაციისთვის დამიკავშირდით"], seed, "ka_end") + f": {phone}.")
    ka_title = "იყიდება " + (f"{rooms}-ოთახიანი " if rooms else "") + "ბინა" + (f", {area} მ²" if area else "") + \
               (f", {district}" if district else "")

    # ---------- English ----------
    en_adj = _pick(EN_ADJ, seed, "en_adj")
    en_rooms = f"{rooms}-room apartment" if rooms else "apartment"
    district, address, city = L["en"]
    size = f" of {area} m²" if area else ""
    loc = f" in {district}" if district else ""
    en = [_pick([f"For sale: a {en_adj} {en_rooms}{size}{loc}.", f"We offer a {en_adj} {en_rooms}{size} for sale{loc}.",
                 f"A {en_adj} {en_rooms}{size} is for sale{loc}."], seed, "en_intro")]
    if floor:
        en.append(f"It is located on floor {floor}" + (f" of {floors}" if floors else "") + (f", {bld[2]}" if bld else "") + ".")
    if bedrooms:
        en.append(f"The apartment has {bedrooms} bedroom{'s' if bedrooms != 1 else ''}" + (f" and is {cond[2]}." if cond else "."))
    elif cond:
        en.append(f"The apartment is {cond[2]}.")
    if feats:
        en.append("Features: " + ", ".join(f[4] for f in feats) + ".")
    if near:
        en.append("Nearby: " + ", ".join(f[4] for f in near) + ".")
    if address:
        en.append(f"Address: {', '.join(x for x in (city, address) if x)}.")
    if price:
        en.append(f"Price: {price}.")
    en.append(f"Call to arrange a viewing: {phone}.")
    en_title = f"For sale: {en_rooms}" + (f", {area} m²" if area else "") + (f", {district}" if district else "")

    return {"title_ru": ru_title[:70], "title_ka": ka_title[:70], "title_en": en_title[:70],
            "description_ru": " ".join(ru), "description_ka": " ".join(ka), "description_en": " ".join(en)}


# ---------- короткий пост для соцсетей (Threads: до 500 символов) ----------
TAGS = {"ru": "#недвижимостьтбилиси", "ka": "#უძრავიქონება", "en": "#TbilisiRealEstate"}


def social(d, phone, name=""):
    """Короткий пост с эмодзи на трёх языках — только факты объекта, без ссылок на источник."""
    rooms, area = _num(d.get("rooms")), _num(d.get("area"))
    floor, floors = _num(d.get("floor")), _num(d.get("floors_total"))
    price = f"{int(float(d['price'])):,}".replace(",", " ") + " $" if _num(d.get("price")) else ""
    feats, near = detect(" ".join(str(d.get(k) or "") for k in ("notes", "features", "title")))
    out = {}
    for lang in ("ru", "ka", "en"):
        district, address, _ = (localize(d.get("district"), lang), localize(d.get("address"), lang), "")
        if lang == "ru":
            head = "🏠 Продаётся " + (f"{rooms}-комнатная квартира" if rooms else "квартира") + (f", {area} м²" if area else "")
            fl = f"🏢 Этаж {floor}" + (f" из {floors}" if floors else "") if floor else ""
            fe = ("✨ " + ", ".join(f[2] for f in feats[:4])) if feats else ""
            pr = f"💰 {price}" if price else ""
            ph = f"📞 {phone}" + (f" ({name})" if name else "")
        elif lang == "ka":
            head = "🏠 იყიდება " + (f"{rooms}-ოთახიანი ბინა" if rooms else "ბინა") + (f", {area} მ²" if area else "")
            fl = f"🏢 სართული {floor}" + (f"/{floors}" if floors else "") if floor else ""
            fe = ("✨ " + ", ".join(f[3] for f in feats[:4])) if feats else ""
            pr = f"💰 {price}" if price else ""
            ph = f"📞 {phone}"
        else:
            head = "🏠 For sale: " + (f"{rooms}-room apartment" if rooms else "apartment") + (f", {area} m²" if area else "")
            fl = f"🏢 Floor {floor}" + (f" of {floors}" if floors else "") if floor else ""
            fe = ("✨ " + ", ".join(f[4] for f in feats[:4])) if feats else ""
            pr = f"💰 {price}" if price else ""
            ph = f"📞 {phone}"
        loc = "📍 " + ", ".join(x for x in (district, address) if x) if (district or address) else ""
        text = "\n".join(x for x in (head, loc, fl, fe, pr, ph) if x) + f"\n\n{TAGS[lang]}"
        out[f"social_{lang}"] = text[:500]
    return out
