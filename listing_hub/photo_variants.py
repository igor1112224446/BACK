"""
Отдельный набор фото для публикации на Korter (только для объектов из твоего аккаунта).

Для каждого фото: лёгкая обрезка краёв, небольшой поворот (1–2°) с подрезкой углов,
чуть другая яркость и контраст, новое сжатие без служебных данных. Обложкой ставится
другой кадр. По желанию — твой логотип и телефон.
Оригиналы при этом не меняются: набор хранится отдельно и используется только для Korter.
"""
import random
from math import radians, tan
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from images import watermark


def _variant(src, dst, rnd):
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    W, H = img.size

    # поворот на 1–2° в случайную сторону и подрезка, чтобы не было пустых углов
    angle = rnd.uniform(1.0, 2.0) * rnd.choice((-1, 1))
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    t = tan(radians(abs(angle)))
    inset_x, inset_y = int(H * t) + 2, int(W * t) + 2

    # лёгкая обрезка краёв: 2–4 %, по-разному с каждой стороны
    l = inset_x + int(W * rnd.uniform(0.02, 0.04)); r = inset_x + int(W * rnd.uniform(0.02, 0.04))
    tp = inset_y + int(H * rnd.uniform(0.02, 0.04)); b = inset_y + int(H * rnd.uniform(0.02, 0.04))
    img = img.crop((l, tp, W - r, H - b))

    # яркость и контраст ±3–6 %
    img = ImageEnhance.Brightness(img).enhance(rnd.uniform(0.95, 1.06))
    img = ImageEnhance.Contrast(img).enhance(rnd.uniform(0.95, 1.06))
    img.thumbnail((2000, 2000), Image.LANCZOS)

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=rnd.randint(86, 91), optimize=True)   # без EXIF
    return dst


def prepare(paths, out_dir, seed, logo_path=None, phone=None, add_logo=False, logo_ratio=0.18):
    rnd = random.Random(seed)
    out = []
    for i, p in enumerate(paths):
        dst = Path(out_dir) / f"{i:02d}.jpg"
        _variant(p, dst, rnd)
        if add_logo:
            watermark(dst, dst, logo_path, phone, logo_ratio, enabled=True)
        out.append(str(dst))
    # обложка — другой кадр: второе фото становится первым
    if len(out) > 1:
        out[0], out[1] = out[1], out[0]
    return out
