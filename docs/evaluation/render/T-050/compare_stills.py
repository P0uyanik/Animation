"""T-050: metrics and a 1:1 crop sheet for the quality stills (no rendering).

    python3 docs/evaluation/render/T-050/compare_stills.py <stills_dir> <timings_dir> <out_dir>

PSNR (dB, sRGB 8-bit) and mean absolute error against the 1024-spp reference, over the full frame and over a
face/hair crop of the right character; writes quality.json and quality_sheet.jpg (crops at 100%)."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

STILLS = [("q1_ref_c1024", "Cycles 1024 spp (adaptive 0.002) + OIDN = reference"),
          ("q2_c16_oidn", "Cycles 16 spp + OIDN (today's production)"),
          ("q3_c16_raw", "Cycles 16 spp, no denoise"),
          ("q4_c64_oidn", "Cycles 64 spp + OIDN"),
          ("q5_c128_oidn", "Cycles 128 spp + OIDN"),
          ("q6_c256_oidn", "Cycles 256 spp + OIDN"),
          ("q7_e16", "EEVEE 16 samples"),
          ("q8_e64", "EEVEE 64 samples")]
CROP = (990, 180, 1430, 510)  # right character: hair, eyes, cheeks, hood strings


def psnr(a, b):
    mse = np.mean((a - b) ** 2)
    return float("inf") if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)


def main():
    src, tim, out = sys.argv[1:4]
    imgs = {k: np.asarray(Image.open(os.path.join(src, k + ".png")).convert("RGB")).astype(np.float64) for k, _ in STILLS}
    ref = imgs["q1_ref_c1024"]
    x0, y0, x1, y1 = CROP
    rep = {}
    for k, label in STILLS:
        t = json.load(open(os.path.join(tim, k + ".json")))
        im = imgs[k]
        rep[k] = {"label": label, "render_s": t["renders_s"][-1], "settings": t["engine_settings"],
                  "psnr_full_db": round(psnr(im, ref), 2), "psnr_crop_db": round(psnr(im[y0:y1, x0:x1], ref[y0:y1, x0:x1]), 2),
                  "mae_crop": round(float(np.mean(np.abs(im[y0:y1, x0:x1] - ref[y0:y1, x0:x1]))), 2)}
    json.dump(rep, open(os.path.join(out, "quality.json"), "w"), indent=1)
    cw, ch, lab = x1 - x0, y1 - y0, 40
    sheet = Image.new("RGB", (cw * 4, (ch + lab) * 2), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (k, label) in enumerate(STILLS):
        c, r = i % 4, i // 4
        crop = Image.open(os.path.join(src, k + ".png")).convert("RGB").crop(CROP)
        sheet.paste(crop, (c * cw, r * (ch + lab) + lab))
        m = rep[k]
        sub = "reference" if k == "q1_ref_c1024" else f"PSNR crop {m['psnr_crop_db']} dB"
        d.text((c * cw + 6, r * (ch + lab) + 4), label[:60], fill=(255, 255, 255))
        d.text((c * cw + 6, r * (ch + lab) + 20), f"{m['render_s']} s/frame (4-core CPU, 1080p)  {sub}", fill=(255, 220, 0))
    sheet.save(os.path.join(out, "quality_sheet.jpg"), quality=90)
    for k, m in rep.items():
        print(k, m["render_s"], m["psnr_full_db"], m["psnr_crop_db"], m["mae_crop"])


main()
