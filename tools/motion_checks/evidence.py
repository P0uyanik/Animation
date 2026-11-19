"""Small evidence strips (JPEG) per issue: rendered crops of frames peak-1, peak, peak+1 around the issue (when
rendered frames are given) and a plot of the measured value over the issue's neighbourhood with the threshold."""
import numpy as np
from PIL import Image, ImageDraw

CROP = 96  # source pixels around the point
SCALE = 2
PLOT_W, PLOT_H = 240, CROP * SCALE


def tone(L, ev=0.3):
    return (np.clip(L.astype(np.float32) * 2 ** ev, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def crop(img, cx, cy, size=CROP):
    H, W = img.shape[:2]
    x0 = int(np.clip(cx - size / 2, 0, max(W - size, 0)))
    y0 = int(np.clip(cy - size / 2, 0, max(H - size, 0)))
    return img[y0:y0 + size, x0:x0 + size], (x0, y0)


def plot(series, frames, peak, limit, lo, hi, label):
    im = Image.new("RGB", (PLOT_W, PLOT_H), (250, 250, 250))
    d = ImageDraw.Draw(im)
    a = max(0, list(frames).index(peak) - 12)
    b = min(len(frames), list(frames).index(peak) + 13)
    fr, v = np.asarray(frames[a:b]), np.asarray(series[a:b], dtype=np.float64)
    vals = np.concatenate([v, [limit]]) if limit is not None else v
    vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
    if vmax - vmin < 1e-9:
        vmax = vmin + 1
    X = lambda f: 8 + (f - fr[0]) / max(fr[-1] - fr[0], 1) * (PLOT_W - 16)
    Y = lambda y: PLOT_H - 22 - (y - vmin) / (vmax - vmin) * (PLOT_H - 40)
    d.rectangle([X(max(lo, fr[0])) - 2, 14, X(min(hi, fr[-1])) + 2, PLOT_H - 20], fill=(255, 225, 205))
    if limit is not None:
        d.line([8, Y(limit), PLOT_W - 8, Y(limit)], fill=(200, 60, 40), width=1)
    pts = [(X(f), Y(y)) for f, y in zip(fr, v)]
    d.line(pts, fill=(30, 70, 160), width=2)
    for p in pts:
        d.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=(30, 70, 160))
    d.text((6, 1), label[:40], fill=(20, 20, 20))
    d.text((6, PLOT_H - 14), f"f{fr[0]}", fill=(80, 80, 80))
    d.text((PLOT_W - 34, PLOT_H - 14), f"f{fr[-1]}", fill=(80, 80, 80))
    return im


def strip(path, panels):
    """panels: list of PIL images or (H, W) / (H, W, 3) uint8 arrays; written side by side as a JPEG."""
    ims = []
    for p in panels:
        if isinstance(p, np.ndarray):
            p = Image.fromarray(p).resize((p.shape[1] * SCALE, p.shape[0] * SCALE), Image.NEAREST)
        ims.append(p.convert("RGB"))
    h = max(i.height for i in ims)
    out = Image.new("RGB", (sum(i.width for i in ims) + 4 * (len(ims) - 1), h), (255, 255, 255))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + 4
    out.save(path, "JPEG", quality=80, optimize=True)


def frame_crops(images, frames, peak, cx, cy, extra=None):
    """Crops of peak-1, peak, peak+1 from (F, H, W) luminance images (tone mapped), plus an optional map."""
    out = []
    for f in (peak - 1, peak, peak + 1):
        if f in frames:
            c, _ = crop(tone(images[frames.index(f)]), cx, cy)
            out.append(c)
    if extra is not None:
        c, _ = crop(extra, cx, cy)
        out.append(c)
    return out
