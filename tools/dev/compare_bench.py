#!/usr/bin/env python3
"""T-128 opt-in: compare the regression image verdict (tools/regression/run.py image_difference +
within_noise) with OpenImageIO and scikit-image on the same inputs. Not used by the gate.

  python tools/dev/compare_bench.py OUT_DIR   (needs requirements-tools.txt in a venv)
Inputs: tests/regression/*.png plus deterministic perturbations (seeded). Prints one row per pair
and a summary; exit 1 if any OIIO verdict differs from the existing verdict.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from regression.run import NOISE, image_difference, within_noise  # noqa: E402  existing code, unchanged


def variants(src: Path, out: Path):
    mode = Image.open(src).mode  # keep the source mode (RGB stays RGB) so both tools see the same channels
    base = np.asarray(Image.open(src).convert("RGBA"), dtype=np.int16)
    rng = np.random.default_rng(128)
    rgb = (slice(None), slice(None), slice(0, 3))
    def save(tag, arr):
        p = out / f"{src.stem}__{tag}.png"
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").convert(mode).save(p)
        return p
    yield "identical", save("identical", base)
    for tag, amp in (("noise1", 1), ("noise3", 3), ("noise12", 12)):
        a = base.copy(); a[rgb] += rng.integers(-amp, amp + 1, a[rgb].shape); yield tag, save(tag, a)
    a = base.copy(); a[rgb] += 2; yield "bright2", save("bright2", a)
    yield "shift1px", save("shift1px", np.roll(base, 1, axis=1))
    a = base.copy(); h, w = a.shape[:2]; a[h // 3:h // 3 + max(2, h // 40), w // 3:w // 3 + max(2, w // 40), :3] = 255
    yield "patch", save("patch", a)


def oiio_diff(a: Path, b: Path) -> dict:
    import OpenImageIO as oiio
    cfg = oiio.ImageSpec(); cfg.attribute("oiio:UnassociatedAlpha", 1)  # no premultiply: PIL semantics
    A, B = oiio.ImageBuf(str(a), 0, 0, config=cfg), oiio.ImageBuf(str(b), 0, 0, config=cfg)
    r = oiio.ImageBufAlgo.compare(A, B, 8 / 255 + 1e-9, 1.0)
    if A.nchannels != B.nchannels:  # existing code returns a hard mismatch only on shape, not channels
        raise SystemExit(f"channel count differs: {a} {b}")
    n = A.spec().width * A.spec().height
    # OIIO counts per-pixel failures over all channels -> same definition as changed_fraction.
    return {"rmse": round(float(r.rms_error), 6), "changed_fraction": round(r.nfail / n, 6), "max_abs": round(float(r.maxerror), 6)}


def ssim(a: Path, b: Path) -> float:
    from skimage.metrics import structural_similarity
    x = np.asarray(Image.open(a).convert("RGBA")); y = np.asarray(Image.open(b).convert("RGBA"))
    return round(float(structural_similarity(x, y, channel_axis=2, data_range=255)), 5)


def timed(fn, *args, reps=5):
    t = time.perf_counter()
    for _ in range(reps):
        value = fn(*args)
    return value, (time.perf_counter() - t) / reps * 1000


def main() -> int:
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    noise = json.loads(NOISE.read_text())
    rows, mismatches, tt = [], 0, {"existing": 0.0, "oiio": 0.0, "ssim": 0.0}
    for src in sorted((ROOT / "tests/regression").glob("*.png")):
        for tag, var in variants(src, out):
            e, te = timed(image_difference, src, var)
            o, to = timed(oiio_diff, src, var)
            s, ts = timed(ssim, src, var)
            ve, vo = within_noise(e, noise), within_noise(o, noise)
            mismatches += ve != vo
            tt["existing"] += te; tt["oiio"] += to; tt["ssim"] += ts
            rows.append(f"{src.stem:22} {tag:9} existing={'PASS' if ve else 'FAIL'} rmse={e['rmse']:.6f} chg={e['changed_fraction']:.6f} "
                        f"| oiio={'PASS' if vo else 'FAIL'} rmse={o['rmse']:.6f} chg={o['changed_fraction']:.6f} | ssim={s} "
                        f"| ms {te:.1f}/{to:.1f}/{ts:.1f}")
    print("\n".join(rows))
    print(f"# pairs={len(rows)} verdict_mismatches={mismatches} total_ms existing={tt['existing']:.0f} oiio={tt['oiio']:.0f} ssim={tt['ssim']:.0f}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
