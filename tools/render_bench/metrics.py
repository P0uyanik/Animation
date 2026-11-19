"""T-124 objective metrics (supporting evidence only; the stills and clips are the primary evidence).

    python metrics.py still <test.png> <ref.png> [--crops crops.json]        -> JSON: PSNR, SSIM (global and per crop),
                                                                             mean abs error (8-bit levels)
    python metrics.py flicker <test_dir> <ref_dir> <first> <last>          -> JSON: temporal flicker of test vs ref

SSIM: single-scale on luma (BT.709), 8x8 Gaussian-weighted windows (sigma 1.5), constants K1 0.01 / K2 0.03.
Flicker: per pixel, the frame-to-frame change of the residual (test - ref), r_t - r_{t-1}, averaged in absolute value
over the frame (8-bit luma levels); ref is the clip the profile is compared against. 0 = the test adds no temporal
change of its own; noise or denoiser shimmer raise it. Also reports each clip's own mean frame-to-frame change."""
import json
import os
import sys

import numpy as np
from PIL import Image


def luma(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722, a


def gauss(img, sigma=1.5):
    r = int(3 * sigma + 0.5)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(img, r, mode="reflect")
    t = sum(k[i] * p[:, i:i + img.shape[1]] for i in range(2 * r + 1))
    return sum(k[i] * t[i:i + img.shape[0], :] for i in range(2 * r + 1))


def ssim(x, y):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mx, my = gauss(x), gauss(y)
    sxx, syy, sxy = gauss(x * x) - mx * mx, gauss(y * y) - my * my, gauss(x * y) - mx * my
    m = ((2 * mx * my + c1) * (2 * sxy + c2)) / ((mx * mx + my * my + c1) * (sxx + syy + c2))
    return m


def psnr(a, b):
    mse = np.mean((a - b) ** 2)
    return float("inf") if mse == 0 else 10 * np.log10(255 ** 2 / mse)


def still(test, ref, crops=None):
    yt, rt = luma(test)
    yr, rr = luma(ref)
    if yt.shape != yr.shape:
        raise SystemExit(f"size mismatch {yt.shape} vs {yr.shape}")
    sm = ssim(yt, yr)
    out = {"psnr_db": round(psnr(rt, rr), 2), "ssim": round(float(sm.mean()), 4),
           "mae_levels": round(float(np.abs(rt - rr).mean()), 3), "crops": {}}
    for name, (x, y, w, h) in (crops or {}).items():
        out["crops"][name] = {"psnr_db": round(psnr(rt[y:y + h, x:x + w], rr[y:y + h, x:x + w]), 2),
                              "ssim": round(float(sm[y:y + h, x:x + w].mean()), 4)}
    return out


def flicker(tdir, rdir, a, b):
    def fr(d, f):
        return luma(os.path.join(d, f"frame_{f:04d}.png"))[0]
    prev = None
    res, own_t, own_r = [], [], []
    pt = pr = None
    for f in range(a, b + 1):
        t, r = fr(tdir, f), fr(rdir, f)
        d = t - r
        if prev is not None:
            res.append(np.abs(d - prev).mean())
            own_t.append(np.abs(t - pt).mean())
            own_r.append(np.abs(r - pr).mean())
        prev, pt, pr = d, t, r
    return {"frames": [a, b], "residual_flicker_levels": round(float(np.mean(res)), 3),
            "test_frame_change_levels": round(float(np.mean(own_t)), 3),
            "ref_frame_change_levels": round(float(np.mean(own_r)), 3)}


def main():
    mode = sys.argv[1]
    if mode == "still":
        crops = None
        if "--crops" in sys.argv:
            crops = json.load(open(sys.argv[sys.argv.index("--crops") + 1]))
        print(json.dumps(still(sys.argv[2], sys.argv[3], crops)))
    elif mode == "flicker":
        print(json.dumps(flicker(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))))


if __name__ == "__main__":
    main()
