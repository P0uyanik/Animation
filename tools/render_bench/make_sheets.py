"""T-124 comparison sheets (JPEG): 100% crops per setting, and full 720p frames side by side.

    python make_sheets.py <runs dir> <summary.json> <out dir>
crops_<group>.jpg: one row per run, one 100% crop per column (crops_s010.json), labelled with s/frame and PSNR vs the
512 spp reference. frames_<group>.jpg: full frames at 50% in a grid, same labels."""
import json
import os
import sys

from PIL import Image, ImageDraw

GROUPS = {
 "samples": ["ref512", "baseline_a", "thr02", "thr03", "thr05", "spp64", "spp32", "spp16"],
 "levers": ["baseline_a", "noden", "den_rgb", "bounce6", "bounce3", "sss_burley", "no_rect", "scale75", "fg_catcher"],
 "elements": ["baseline_a", "no_fibres", "no_hair_fibres", "no_garment_fibres", "fibre50", "fibre25", "no_sss", "no_glasses", "no_sun"],
 "proposed": ["ref512", "baseline_a", "thr05", "thr03", "spp64", "review16"],
}


def label(draw, xy, text):
    x, y = xy
    draw.rectangle([x, y, x + 7 * len(text) + 6, y + 14], fill=(0, 0, 0))
    draw.text((x + 3, y + 1), text, fill=(255, 255, 255))


def main():
    runs, summ, out = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    rows, crops = summ["runs"], summ["crops"]
    for g, names in GROUPS.items():
        names = [n for n in names if n in rows and rows[n].get("image")]
        ims = {n: Image.open(os.path.join(runs, rows[n]["image"])).convert("RGB") for n in names}

        def tag(n):
            r = rows[n]
            q = r.get("vs_ref512", {}).get("psnr_db")
            return f"{n}  {r['s_per_frame']:.0f} s/fr" + (f"  {q:.1f} dB" if q else "  (reference)")
        W = sum(c[2] for c in crops.values()) + 4 * (len(crops) - 1)
        H = max(c[3] for c in crops.values())
        sheet = Image.new("RGB", (W, (H + 22) * len(names)), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for i, n in enumerate(names):
            x = 0
            y = i * (H + 22)
            label(d, (2, y + 3), tag(n))
            for cname, (cx, cy, cw, ch) in crops.items():
                sheet.paste(ims[n].crop((cx, cy, cx + cw, cy + ch)), (x, y + 20))
                if i == 0:
                    label(d, (x + 2, y + 22), cname)
                x += cw + 4
        sheet.save(os.path.join(out, f"crops_{g}.jpg"), quality=88)
        cols = 3
        tw, th = 640, 360
        grid = Image.new("RGB", (cols * tw, ((len(names) + cols - 1) // cols) * th), (40, 40, 40))
        d = ImageDraw.Draw(grid)
        for i, n in enumerate(names):
            x, y = (i % cols) * tw, (i // cols) * th
            grid.paste(ims[n].resize((tw, th), Image.LANCZOS), (x, y))
            label(d, (x + 4, y + 4), tag(n))
        grid.save(os.path.join(out, f"frames_{g}.jpg"), quality=85)
        print(g, len(names))


if __name__ == "__main__":
    main()
