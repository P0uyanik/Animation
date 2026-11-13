"""Builds the reference comparison sheet and silhouette measurements for one subject.

    python3 pipeline/compare_sheet.py --index assets/characters/boy_yellow_hoodie/references/reference_index.json \
        --blender renders/compare/it4_boy/blender --plush renders/compare/it4_boy/plush --out renders/compare/it4_boy/report \
        --label "Iteration 4 boy (stand-in)"

Per view: reference | Blender render | Plush render | silhouette overlay (reference magenta, subject cyan).
For views with a reference silhouette, the subject silhouette (the Blender render's alpha) is scaled to the same
figure height and aligned at the feet and the horizontal centre; then:
  iou            overlap of the two silhouettes (1 = identical outline)
  head_fraction  head + hair height / figure height (head ends at the narrowest row between 22% and 50%: the neck)
  width_*        widest extent within a band / figure height (head 0-38%, torso 38-65%, legs 65-92%, feet 92-100%)
  aspect         figure height / widest extent
Needs numpy and Pillow."""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BANDS = {"head": (0.0, 0.38), "torso": (0.38, 0.65), "legs": (0.65, 0.92), "feet": (0.92, 1.0)}


def bbox(mask):
    ys, xs = np.nonzero(mask)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def measures(mask):
    x0, y0, x1, y1 = bbox(mask)
    m = mask[y0:y1, x0:x1]
    h = m.shape[0]
    widths = np.array([(np.ptp(np.nonzero(r)[0]) + 1) if r.any() else 0 for r in m], float)
    out = {"aspect": round(h / widths.max(), 3)}
    for k, (a, b) in BANDS.items():
        out["width_" + k] = round(widths[int(a * h):max(int(b * h), int(a * h) + 1)].max() / h, 3)
    lo, hi = int(0.22 * h), int(0.5 * h)
    neck = lo + int(np.argmin(widths[lo:hi]))
    out["head_fraction"] = round(neck / h, 3)
    return out


def align(sub_mask, ref_mask):
    """Scales the subject silhouette to the reference figure height and aligns feet and centre."""
    rx0, ry0, rx1, ry1 = bbox(ref_mask)
    sx0, sy0, sx1, sy1 = bbox(sub_mask)
    s = (ry1 - ry0) / (sy1 - sy0)
    crop = Image.fromarray(sub_mask[sy0:sy1, sx0:sx1].astype(np.uint8) * 255)
    crop = crop.resize((max(1, round(crop.width * s)), ry1 - ry0), Image.BILINEAR)
    canvas = Image.new("L", (ref_mask.shape[1], ref_mask.shape[0]), 0)
    cx = (rx0 + rx1) / 2
    canvas.paste(crop, (round(cx - crop.width / 2), ry0))
    return np.asarray(canvas) > 127


def edges(mask):
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.FIND_EDGES)) > 0


def fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def label(im, text, color=(255, 255, 255)):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 6 * len(text), 16), fill=(20, 20, 20))
    d.text((4, 3), text, fill=color)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--blender", required=True)
    ap.add_argument("--plush", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="subject")
    ap.add_argument("--row-height", type=int, default=360)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    index = json.load(open(a.index))
    vdir = os.path.join(os.path.dirname(a.index), "views")
    H = a.row_height
    rows, report = [], {"subject": a.label, "views": []}
    for v in index["views"]:
        bpath = os.path.join(a.blender, v["id"] + ".png")
        if not os.path.exists(bpath):
            continue
        ref = Image.open(os.path.join(vdir, v["id"] + ".png")).convert("RGB")
        brgba = Image.open(bpath).convert("RGBA")
        bgrey = Image.new("RGBA", brgba.size, (128, 128, 128, 255))
        bgrey.alpha_composite(brgba)
        cells = [label(fit(ref, H), f"reference #{v['upload']} {v['id']}"),
                 label(fit(bgrey.convert("RGB"), H), "Blender (stand-in geometry)")]
        ppath = os.path.join(a.plush, v["id"] + ".png") if a.plush else ""
        if ppath and os.path.exists(ppath):
            cells.append(label(fit(Image.open(ppath).convert("RGB"), H), "Plush render (same camera)"))
        entry = {"id": v["id"], "upload": v["upload"], "yaw_deg": v["yaw_deg"]}
        sub_mask = np.asarray(brgba)[:, :, 3] > 127
        mpath = os.path.join(vdir, v["id"] + "_mask.png")
        if v.get("silhouette") and os.path.exists(mpath):
            ref_mask = np.asarray(Image.open(mpath)) > 127
            al = align(sub_mask, ref_mask)
            inter, union = (al & ref_mask).sum(), (al | ref_mask).sum()
            entry["iou"] = round(float(inter / union), 3)
            entry["reference"] = measures(ref_mask)
            entry["subject"] = measures(al)
            ov = (np.asarray(ref, np.float32) * 0.45).astype(np.uint8)
            ov[edges(ref_mask)] = (255, 0, 255)
            ov[edges(al)] = (0, 255, 255)
            cells.append(label(fit(Image.fromarray(ov), H), f"overlay IoU {entry['iou']:.2f}"))
        report["views"].append(entry)
        w = sum(c.width for c in cells) + 6 * (len(cells) - 1)
        row = Image.new("RGB", (w, H), (255, 255, 255))
        x = 0
        for c in cells:
            row.paste(c, (x, 0))
            x += c.width + 6
        rows.append(row)
    if not rows:
        raise SystemExit("no renders found")
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, len(rows) * (H + 8) + 30), (255, 255, 255))
    ImageDraw.Draw(sheet).text((6, 8), f"Camera-matched comparison: {a.label} vs. boy_yellow_hoodie references", fill=(0, 0, 0))
    for i, r in enumerate(rows):
        sheet.paste(r, (0, 30 + i * (H + 8)))
    sheet.save(os.path.join(a.out, "comparison_sheet.png"))
    measured = [e for e in report["views"] if "iou" in e]
    if measured:
        keys = ["head_fraction", "aspect"] + ["width_" + k for k in BANDS]
        report["summary"] = {"mean_iou": round(float(np.mean([e["iou"] for e in measured])), 3)}
        for k in keys:
            ref_v = np.mean([e["reference"][k] for e in measured])
            sub_v = np.mean([e["subject"][k] for e in measured])
            report["summary"][k] = {"reference": round(float(ref_v), 3), "subject": round(float(sub_v), 3),
                                    "subject_vs_reference": round(float(sub_v / ref_v), 3)}
    json.dump(report, open(os.path.join(a.out, "measurements.json"), "w"), indent=1)
    print(json.dumps(report.get("summary", {}), indent=1))


if __name__ == "__main__":
    main()
