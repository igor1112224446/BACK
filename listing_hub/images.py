"""Логотип и телефон на фото. EXIF (включая геометку) при этом удаляется."""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONTS = ["C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(size):
    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def watermark(src, dst, logo_path, phone, width_ratio=0.18, max_side=2000, enabled=True):
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGBA")
    img.thumbnail((max_side, max_side), Image.LANCZOS)  # площадки режут большие файлы
    if not enabled:  # без логотипа и телефона: только выпрямляем, уменьшаем и убираем EXIF
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(dst, "JPEG", quality=90)
        return dst
    W, H = img.size
    pad = int(W * 0.025)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    font = _font(max(18, int(W * 0.035)))
    tb = draw.textbbox((0, 0), phone, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    box_h = th + pad
    y_box = H - pad - box_h

    if logo_path and Path(logo_path).exists():
        logo = Image.open(logo_path).convert("RGBA")
        lw = int(W * width_ratio)
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        layer.alpha_composite(logo, (W - pad - lw, y_box - logo.height - pad // 2))

    x_box = W - pad - tw - pad
    draw.rounded_rectangle((x_box, y_box, W - pad, y_box + box_h), radius=box_h // 4, fill=(0, 0, 0, 160))
    draw.text((x_box + pad // 2, y_box + pad // 2 - tb[1]), phone, font=font, fill=(255, 255, 255, 255))

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(img, layer).convert("RGB").save(dst, "JPEG", quality=88)
    return dst
