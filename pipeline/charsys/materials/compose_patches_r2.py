"""Compose and measure the T-092 material patches (plain Python: numpy + Pillow).

    python3 pipeline/charsys/materials/compose_patches_r2.py --plan docs/evaluation/materials/T-092/patches.plan.json \
        --tiles <render_patches_r2 out dir> --out docs/evaluation/materials/T-092

Writes <out>/patch_sheet.jpg (one row per material: macro and shot-size, before | after, neutral and warm rig; the
shot-size tiles are shown 2x nearest-neighbour so their native pixels stay visible) and <out>/patch_metrics.json:
per material the CIEDE2000 of the form's median colour (shot-size, disc of 0.92 R) to the reference target, before
and after, under each rig, the VISUAL_TARGET texture statistics (tools/fidelity/metrics.texture_stats) of the macro
and shot-size tiles, and the render seconds of every tile.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "fidelity"))
import metrics as FM  # noqa: E402

BG = (36, 34, 35)
FG = (232, 228, 224)


def load(path):
    return np.asarray(Image.open(path).convert("RGB"))


def disc(shape, radius_px, frac=0.92):
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    return (xx - (w - 1) / 2) ** 2 + (yy - (h - 1) / 2) ** 2 <= (radius_px * frac) ** 2


def lit_box(shape):
    """The macro tile's surface region: the lower-right two thirds lie on the form (the silhouette crosses the
    upper-left third)."""
    h, w = shape[:2]
    m = np.zeros(shape[:2], bool)
    m[int(h * 0.45):int(h * 0.95), int(w * 0.45):int(w * 0.95)] = True
    return m


def r(v, nd=3):
    return None if v is None else round(float(v), nd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", required=True)
    p.add_argument("--tiles", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    rendered = json.load(open(os.path.join(a.tiles, "patches_render.json"), encoding="utf-8"))
    tiles = {(t["label"], t["variant"], t["light_tag"], t["scale"]): t for t in rendered["tiles"]}
    shot = rendered["cameras"]["shot"]
    form_px = float(rendered["form_radius_m"]) * shot["px_per_m"]
    lights = [l["tag"] for l in plan["lights"]]
    metrics = {"schema": "plush-studio.material-patch-metrics/1", "task": "T-092", "blender": rendered["blender"],
               "samples": rendered["samples"], "denoiser": rendered["denoiser"], "device": rendered["device"],
               "cameras": rendered["cameras"], "lights": plan["lights"],
               "colour_region": "shot-size tile, disc of 0.92 x form radius (lit and shaded side, as a garment median)",
               "materials": [], "render_seconds_total": round(sum(t["seconds"] for t in rendered["tiles"]), 2)}
    rows = []
    for m in plan["materials"]:
        target_lab = FM.srgb_to_lab(np.array(m["target_srgb"], float))
        entry = {"label": m["label"], "target_srgb": m["target_srgb"], "target_source": m["target_source"],
                 "before": m["before"]["preset"], "after": m["after"]["preset"], "lights": {}}
        row = []
        for tag in lights:
            per = {}
            for variant in ("before", "after"):
                s = load(os.path.join(a.tiles, tiles[(m["label"], variant, tag, "shot")]["file"]))
                mac = load(os.path.join(a.tiles, tiles[(m["label"], variant, tag, "macro")]["file"]))
                mask = disc(s.shape, form_px)
                stats = FM.colour_stats(s, mask)
                tex_shot = FM.texture_stats(s, mask, px_per_h=s.shape[0] / 256)
                tex_macro = FM.texture_stats(mac, lit_box(mac.shape), px_per_h=1.0)
                per[variant] = {
                    "median_srgb": stats["srgb"], "de00_to_target": r(FM.ciede2000(stats["lab"], target_lab), 2),
                    "dL_to_target": r(stats["lab"][0] - target_lab[0], 2),
                    "spread_de00": r(stats["spread_de00"], 2),
                    "shot_texture": {k: r(v) for k, v in (tex_shot or {}).items()},
                    "macro_texture": {k: r(v) for k, v in (tex_macro or {}).items()},
                    "seconds": {sc: tiles[(m["label"], variant, tag, sc)]["seconds"] for sc in ("macro", "shot")}}
                row.append((variant, tag, mac, s))
            entry["lights"][tag] = per
        metrics["materials"].append(entry)
        rows.append((m, row))

    font = ImageFont.load_default()
    macro_px = rendered["cameras"]["macro"]["px"]
    shot_show = rendered["cameras"]["shot"]["px"] * 2
    cell = max(macro_px, shot_show)
    label_w, head_h, pad = 170, 34, 6
    cols = [(v, t, sc) for sc in ("macro", "shot") for t in lights for v in ("before", "after")]
    W = label_w + len(cols) * (cell + pad)
    H = head_h + len(rows) * (cell + pad) + 40
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    for i, (v, t, sc) in enumerate(cols):
        x = label_w + i * (cell + pad)
        d.text((x + 4, 4), f"{sc} | {t}", fill=FG, font=font)
        d.text((x + 4, 18), v, fill=FG, font=font)
    for j, (m, row) in enumerate(rows):
        y = head_h + j * (cell + pad)
        e = metrics["materials"][j]
        d.text((6, y + 6), m["label"], fill=FG, font=font)
        d.text((6, y + 22), f"before: {m['before']['preset']}", fill=FG, font=font)
        d.text((6, y + 36), f"after:  {m['after']['preset']}", fill=FG, font=font)
        d.text((6, y + 54), f"target sRGB {tuple(m['target_srgb'])}", fill=FG, font=font)
        for k, tag in enumerate(lights):
            b, af = e["lights"][tag]["before"], e["lights"][tag]["after"]
            d.text((6, y + 72 + 30 * k), f"dE00 {tag}: {b['de00_to_target']} -> {af['de00_to_target']}",
                   fill=FG, font=font)
            d.text((6, y + 86 + 30 * k), f"  s {b['seconds']['shot']}/{af['seconds']['shot']} "
                   f"m {b['seconds']['macro']}/{af['seconds']['macro']}", fill=FG, font=font)
        byk = {(v, t): (mac, s) for v, t, mac, s in row}
        for i, (v, t, sc) in enumerate(cols):
            x = label_w + i * (cell + pad)
            mac, s = byk[(v, t)]
            img = Image.fromarray(mac) if sc == "macro" else Image.fromarray(s).resize((shot_show, shot_show),
                                                                                       Image.NEAREST)
            sheet.paste(img, (x, y))
    d.text((6, H - 32), "T-092 material patches. Shot-size tiles: strict-sheet body-row camera distance and pixel density "
           f"({shot['px_per_m']:.0f} px/m), shown 2x. Macro: {rendered['cameras']['macro']['frame_m']} m field. "
           f"Cycles {rendered['samples']} spp + OIDN, CPU.", fill=FG, font=font)
    d.text((6, H - 18), "Lights: character_neutral/1 (render_calibration.json), character_warm_indoor/1 "
           "(materials/r2_lights.json). Seconds: before/after per tile.", fill=FG, font=font)
    os.makedirs(a.out, exist_ok=True)
    sheet.save(os.path.join(a.out, "patch_sheet.jpg"), quality=90)
    with open(os.path.join(a.out, "patch_metrics.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(metrics, fh, indent=1)
        fh.write("\n")
    for e in metrics["materials"]:
        n = e["lights"]["neutral"]
        print(f"{e['label']:16s} dE00 neutral {n['before']['de00_to_target']:6} -> {n['after']['de00_to_target']:6} "
              f"| macro fuzz {n['before']['macro_texture'].get('fuzz_hf_rms')} -> {n['after']['macro_texture'].get('fuzz_hf_rms')}"
              f" | shot fuzz {n['before']['shot_texture'].get('fuzz_hf_rms')} -> {n['after']['shot_texture'].get('fuzz_hf_rms')}")


if __name__ == "__main__":
    main()
