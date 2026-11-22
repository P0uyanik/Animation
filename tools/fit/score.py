"""Measure registered Workbench passes in reference crop coordinates."""
import csv
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from core import ROOT, read

sys.path.insert(0, str(ROOT / "tools/fidelity"))
import analysis as fidelity
import metrics
from pipeline.reference_views import outline, segment


def reference(index, view):
    root = index.parent
    name = view["id"]
    image = Image.open(root / "views" / (name + ".png")).convert("RGB")
    mask = root / "views" / (name + "_mask.png")
    annotation = root / "annotations" / (name + ".json")
    if annotation.is_file():
        ann = read(annotation)
    else:
        ann = {"landmarks": read(root / "landmarks.json")["views"][name]}
    if mask.is_file():
        fig = np.asarray(Image.open(mask).convert("L")) > 127
    elif view.get("silhouette"):
        fig, _ = segment(image, **view.get("segmentation", {}))
    else:
        raise ValueError(f"{name}: reference silhouette unavailable")
    if fig.shape != (image.height, image.width) or not fig.any():
        raise ValueError(f"{name}: invalid reference mask")
    eyes = ann.get("regions", {}).get("eyes")
    return {"img": image, "fig": fig, "landmarks": ann["landmarks"],
            "eyes": fidelity.poly_mask(image.size, eyes) if eyes else None}


def features(rgba, points):
    """Visible eye centres and endpoints, and endpoints of each visible brow."""
    rgb = rgba[:, :, :3].astype(np.int16)
    fig = rgba[:, :, 3] > 127
    eyes = np.zeros_like(fig)
    for part, side, colour in (("eye", "L", (255, 0, 0)), ("eye", "R", (0, 255, 0)),
                               ("brow", "L", (0, 0, 255)), ("brow", "R", (255, 255, 0))):
        mask = fig & (np.abs(rgb - colour).max(axis=2) < 40)
        ys, xs = np.nonzero(mask)
        if part == "eye":
            eyes |= mask
            points.pop("eye_" + side, None)
        if len(xs):
            if part == "eye":
                points["eye_" + side] = [float(xs.mean()) + 0.5, float(ys.mean()) + 0.5]
            ends = (xs.min(), xs.max()) if side == "L" else (xs.max(), xs.min())
            for end, x in zip(("inner", "outer"), ends):
                points[f"{part}_{end}_{side}"] = [float(x) + 0.5, float(ys[xs == x].mean()) + 0.5]
    return {"fig": fig, "eyes": eyes, "landmarks": points}


def measure(ref, ren, names):
    """Each available signal votes equally. A missing requested point earns zero."""
    if not ren["fig"].any():
        raise ValueError("empty Workbench silhouette")
    al = fidelity.align(ref, ren)
    iou = metrics.iou(ref["fig"], al["fig"])
    eye_mask = fidelity.place(ren["eyes"], al["scale"], al["ox"], al["oy"], ref["fig"].shape)
    eye_iou = metrics.iou(ref["eyes"], eye_mask) if ref["eyes"] is not None else None
    frame = fidelity.frame(ref)
    scale = ref["landmarks"].get("chin", (0, frame["top"] + frame["height"]))[1] - frame["top"]
    if scale <= 0:
        raise ValueError("invalid landmark normalisation height")
    terms = [iou]
    if eye_iou is not None:
        terms.append(eye_iou)
    points = {}
    for key in sorted(set(names) & ref["landmarks"].keys()):
        target = ref["landmarks"][key]
        xy = fidelity.to_ref(ren["landmarks"][key], al) if key in ren["landmarks"] else None
        error = math.dist(target, xy) / scale if xy is not None else None
        points[key] = {"target": target, "candidate": xy, "error_head": error,
                       "score": max(0, 1 - error) if error is not None else 0}
    if points:
        terms.append(np.mean([p["score"] for p in points.values()]))
    result = {"score": float(np.mean(terms) * 100), "figure_iou": iou, "eye_iou": eye_iou,
              "landmarks": points, "alignment": {k: al[k] for k in ("scale", "ox", "oy")}}
    canvas = np.where(ref["fig"][:, :, None], (99, 114, 122), (24, 30, 34)).astype("uint8")
    if ref["eyes"] is not None:
        canvas[ref["eyes"]] = (100, 186, 171)
    canvas[eye_mask] = (241, 180, 74)
    panel = outline(canvas, al["fig"])
    draw = ImageDraw.Draw(panel)
    for point in points.values():
        x, y = point["target"]
        draw.ellipse((x-2, y-2, x+2, y+2), fill="cyan")
        if point["candidate"]:
            a, b = point["candidate"]
            draw.line((x, y, a, b), fill="white")
            draw.point((a, b), fill="orange")
    return result, panel


def sheet(panels, path):
    tiles = []
    for name, panel in panels.items():
        tile = Image.new("RGB", (280, 540), (24, 30, 34))
        image = ImageOps.contain(panel, (276, 490))
        tile.paste(image, ((280-image.width)//2, 35))
        ImageDraw.Draw(tile).text((10, 10), name, fill="white")
        tiles.append(tile)
    page = Image.new("RGB", (280*len(tiles), 570), (24, 30, 34))
    for i, tile in enumerate(tiles):
        page.paste(tile, (280*i, 0))
    ImageDraw.Draw(page).text((10, 542), "Grey: reference   Magenta: fit outline   Cyan: target points   Gold: visible eyes", fill="white")
    page.thumbnail((2048, 2048))
    page.save(path, quality=92)


def score_table(path, start, best):
    """One row per comparable measurement, including occluded candidate points."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        rows = csv.writer(stream)
        rows.writerow(("view", "measure", "start", "best"))
        rows.writerow(("all", "score / 100", start["score"], best["score"]))
        for name, first in start["views"].items():
            last = best["views"][name]
            for metric in ("score", "figure_iou", "eye_iou"):
                rows.writerow((name, metric, first[metric], last[metric]))
            for key, point in first["landmarks"].items():
                rows.writerow((name, key + " error (head heights)", point["error_head"],
                               last["landmarks"][key]["error_head"]))


# ---------------------------------------------------------------------------------------------- T-215 (phase P2)
def t204_measure(blend, spec, character, out, yaws=(0,), px=512):
    """T-214 measurer on a built blend with a short view list: every reference view (matched expression) plus the
    given neutral yaws. Yaw 0 must stay in the list: the neutral front anchors the profile chin, as in the default
    measure run. The character is an argument (a key of the T-214 views.json), never named here."""
    import measurer as M
    cfg = M.read(M.CONFIG)
    ch = cfg["characters"][character]
    db = M.read(M.T204 / "targets.json")
    views, names = M.views_for(cfg, character, list(yaws), neutral=False)
    rendered = M.render(blend, views, px, M.iris_radius(spec), out)
    nose = M.read(spec)["face"].get("nose", {})
    results = M.measure_all(rendered, out, character, db, M.t204(), names,
                            float(nose.get("size_m", nose.get("radius_m", 0.016))), ch.get("flags", ()),
                            float(ch.get("lid_shadow_h", 0.0)))
    return {"character": character, "holdout": ch.get("holdout"), "px": px, "timings": rendered["timings"],
            "summary": M.summary(results, ch.get("holdout")), "views": results}


def t204_rows(report):
    """Reference-view rows that carry a T-204 target: {(view, measure): row}."""
    return {(r["view"], x["measure"]): x for r in report["views"] if r["view"]
            for x in r["rows"] if x.get("reference") is not None}


def t204_z(report, group=None):
    """{view: {measure: z or None}} over the scorable reference rows (colour rows have no current value)."""
    out = {}
    for (view, key), row in t204_rows(report).items():
        if row["result"] in ("within", "outside", "unscored") and (group is None or row["group"] == group):
            out.setdefault(view, {})[key] = row["z"]
    return out


def t204_table(path, start, best, holdout):
    """Per-measure start vs best: one row per reference view and measure, the held-out view flagged."""
    a, b = t204_rows(start), t204_rows(best)
    with path.open("w", encoding="utf-8", newline="") as stream:
        rows = csv.writer(stream, lineterminator="\n")
        rows.writerow(("view", "held_out", "group", "measure", "reference", "tolerance", "start", "start_z",
                       "start_result", "best", "best_z", "best_result"))
        for key in sorted(a):
            if a[key]["result"] not in ("within", "outside", "unscored"):
                continue
            s, e = a[key], b.get(key, {})
            rows.writerow((key[0], key[0] == holdout, s["group"], key[1], s["reference"], s["tolerance"],
                           s["current"], s["z"], s["result"], e.get("current"), e.get("z"), e.get("result")))
