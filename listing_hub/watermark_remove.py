"""
Попытка убрать полупрозрачный водяной знак площадки (например, логотип MyHome по центру фото).

Как это работает:
1. Площадка ставит один и тот же знак на все фото объявления в одно и то же место.
   Если сложить градиенты (контуры) всех фото, контуры комнат «гасят» друг друга,
   а контуры знака складываются — так находим, где именно знак (маска).
2. Знак — белый, полупрозрачный: пиксель = α·белый + (1−α)·фото. По всем фото
   оцениваем прозрачность α в каждой точке знака и «вычитаем» белый обратно —
   так сохраняется текстура комнаты, а не просто размывается центр.
3. Где знак почти непрозрачный, точку дорисовываем по соседним пикселям.

Нужно минимум 3 фото одного объявления. Результат стоит проверить глазами.
"""
from pathlib import Path

import cv2
import numpy as np

NORM_W = 1000  # фото приводим к общей ширине, чтобы сопоставить положение знака


def _load(paths):
    imgs = []
    for p in paths:
        im = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if im is not None:
            imgs.append((p, im))
    return imgs


def _norm_size(imgs):
    # берём самую частую пропорцию кадра — знак на них стоит одинаково
    ratios = [round(im.shape[0] / im.shape[1], 2) for _, im in imgs]
    common = max(set(ratios), key=ratios.count)
    same = [(p, im) for (p, im), r in zip(imgs, ratios) if r == common]
    return same, (NORM_W, int(NORM_W * common))


def estimate_mask(imgs, size):
    """Ищем контуры, которые есть почти на КАЖДОМ фото объявления в одном и том же месте центральной части кадра.
    Контуры комнат на разных фото не совпадают, а контуры водяного знака — совпадают всегда."""
    w, h = size
    n = len(imgs)
    count = np.zeros((h, w), np.uint8)
    gx_sum = np.zeros((h, w), np.float32)
    gy_sum = np.zeros((h, w), np.float32)
    for _, im in imgs:
        g = cv2.cvtColor(cv2.resize(im, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        edge = (np.sqrt(gx ** 2 + gy ** 2) > 30).astype(np.uint8)
        count += cv2.dilate(edge, np.ones((3, 3), np.uint8))   # допускаем сдвиг на 1 пиксель после сжатия
        gx_sum += gx; gy_sum += gy
    need = max(3, n - 1 - n // 8)   # контур должен быть почти на всех фото (допускаем 1–2 фото, где он не виден)
    center = np.zeros((h, w), bool)
    center[int(0.2 * h):int(0.8 * h), int(0.1 * w):int(0.9 * w)] = True
    mag = np.sqrt(gx_sum ** 2 + gy_sum ** 2) / n
    edges = ((count >= need) & center & (mag > 15)).astype(np.uint8) * 255
    edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    # знак — одно плотное скопление совпавших контуров; берём самое крупное скопление, одиночные совпадения отбрасываем
    groups = cv2.dilate(edges, np.ones((25, 25), np.uint8))
    num, lab, stats, _ = cv2.connectedComponentsWithStats(groups)
    if num <= 1:
        return np.zeros_like(edges)
    best, best_px = 0, 0
    for i in range(1, num):
        px = int((edges[lab == i] > 0).sum())
        if px > best_px:
            best, best_px = i, px
    x, y, bw, bh = stats[best, :4]
    edges = np.where(lab == best, edges, 0).astype(np.uint8)
    density = best_px / max(bw * bh, 1)
    if best_px < 0.002 * w * h or bw * bh > 0.3 * w * h or density < 0.04:
        return np.zeros_like(edges)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = [c for c in cnts if cv2.contourArea(c) > 40]
    if len(cnts) < 2:
        return np.zeros_like(edges)
    filled = np.zeros_like(edges)
    cv2.drawContours(filled, cnts, -1, 255, thickness=cv2.FILLED)
    return cv2.dilate(filled, np.ones((5, 5), np.uint8), iterations=1)


def remove(paths, out_dir):
    """Возвращает (список новых путей, сообщение). Если знак не найден — ([], причина)."""
    imgs = _load(paths)
    if len(imgs) < 3:
        return [], "Нужно минимум 3 фото объявления, чтобы найти водяной знак."
    same, size = _norm_size(imgs)
    if len(same) < 3:
        return [], "Фото слишком разные по размеру, найти общий водяной знак не получилось."
    mask_n = estimate_mask(same, size)
    share = mask_n.mean() / 255
    if share < 0.001:
        return [], "Водяной знак не найден — похоже, его на этих фото нет."
    if share > 0.12:
        return [], "Не удалось надёжно выделить водяной знак: фото слишком похожи друг на друга."

    # оценка прозрачности знака по всем фото (2 прохода: грубый фон → уточнённый фон)
    Is = [cv2.resize(im, size, interpolation=cv2.INTER_AREA).astype(np.float32) for _, im in same]
    Bs = [cv2.inpaint(I.astype(np.uint8), mask_n, 7, cv2.INPAINT_TELEA).astype(np.float32) for I in Is]
    for _ in range(2):
        alpha_n = np.median(np.stack([((I - B) / np.maximum(255 - B, 8)).mean(axis=2) for I, B in zip(Is, Bs)]), axis=0)
        alpha_n = np.clip(alpha_n, 0, 0.95)
        alpha_n[mask_n == 0] = 0
        Bs = [cv2.GaussianBlur(np.clip((I - alpha_n[..., None] * 255) / np.maximum(1 - alpha_n[..., None], 0.05), 0, 255),
                               (0, 0), 2) for I in Is]

    out = []
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for i, (p, im) in enumerate(imgs):
        H, W = im.shape[:2]
        mask = cv2.resize(mask_n, (W, H), interpolation=cv2.INTER_NEAREST)
        alpha = cv2.resize(alpha_n, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        I = im.astype(np.float32)
        J = (I - alpha * 255) / np.maximum(1 - alpha, 0.05)             # «вычитаем» белый знак
        B = cv2.inpaint(im, mask, 5, cv2.INPAINT_TELEA).astype(np.float32)  # дорисовка по соседям
        opaque = np.clip((alpha - 0.75) / 0.15, 0, 1)                    # где знак почти непрозрачный — дорисовка
        R = J * (1 - opaque) + B * opaque
        m = (mask > 0)[..., None]
        res = np.where(m, np.clip(R, 0, 255), I).astype(np.uint8)
        dst = Path(out_dir) / f"{i:02d}.jpg"
        cv2.imwrite(str(dst), res, [cv2.IMWRITE_JPEG_QUALITY, 92])
        out.append(str(dst))
    return out, f"Водяной знак найден и убран на {len(out)} фото. Проверь результат."
