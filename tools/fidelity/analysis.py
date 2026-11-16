"""Fidelity analysis of one character: reference annotations vs. a render of the current build (plain Python: numpy +
Pillow; no Blender). Character-independent; everything per character comes from the annotation data.

Inputs per view: the reference view (references/views/<view>.png, its silhouette mask <view>_mask.png and the annotation
annotations/<view>.json) and the render side written by run.py: <view>.png (groom_turnaround.py), <view>_regions.png
(+ _regions_glasses.png), <view>_landmarks.json and regions.json (blender_render_side.py)."""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import metrics as M

Y_ONLY = ("hem_",)  # height markers: compared on y only
FACE_PARTS = ("eyes", "face_detail")
PROPORTION_TOL = 0.05
WEIGHTS = {"silhouette": 0.25, "regions": 0.15, "landmarks": 0.20, "proportions": 0.15, "colour": 0.15, "texture": 0.10}


# ---------------------------------------------------------------------------------------------------------- loading
def poly_mask(size, polys, ss=4):
    """Rasterise polygons given in pixel-corner coordinates (a pixel (i, j) spans [i, i+1] x [j, j+1]) to a boolean
    mask of `size` (w, h): 4x supersampled, a pixel is inside when at least half of it is covered."""
    w, h = size
    im = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        if len(p) >= 3:
            d.polygon([(float(x) * ss, float(y) * ss) for x, y in p], fill=1)
    a = np.asarray(im, np.uint8)[:h * ss, :w * ss].reshape(h, ss, w, ss).sum(axis=(1, 3))
    return a >= (ss * ss) / 2


def load_reference(ref_dir, ann):
    img = np.asarray(Image.open(os.path.join(ref_dir, ann["view"] + ".png")).convert("RGB"))
    size = (img.shape[1], img.shape[0])
    regions = {k: poly_mask(size, v) for k, v in ann["regions"].items()}
    mpath = os.path.join(ref_dir, ann["view"] + "_mask.png")
    if os.path.exists(mpath):
        fig = np.asarray(Image.open(mpath).convert("L")) > 127
    else:
        fig = np.zeros(img.shape[:2], bool)
        for m in regions.values():
            fig |= m
    lms = {k: tuple(v) for k, v in ann["landmarks"].items()}
    return {"img": img, "fig": fig, "regions": regions, "landmarks": lms, "hidden": set()}


def colour_masks(rgba, colours, tol=3):
    a = rgba[..., 3] > 127
    out = {}
    for name, c in colours.items():
        out[name] = a & (np.abs(rgba[..., :3].astype(int) - np.array(c)).max(axis=-1) <= tol)
    return out


def load_render(render_dir, view):
    img = np.asarray(Image.open(os.path.join(render_dir, view + ".png")).convert("RGB"))
    info = json.load(open(os.path.join(render_dir, "regions.json")))
    colours = info["colours"]
    rgba = np.asarray(Image.open(os.path.join(render_dir, view + "_regions.png")).convert("RGBA"))
    masks = colour_masks(rgba, colours)
    fig = rgba[..., 3] > 127
    gpath = os.path.join(render_dir, view + "_regions_glasses.png")
    if os.path.exists(gpath):
        g = np.asarray(Image.open(gpath).convert("RGBA"))
        gm = colour_masks(g, colours)
        if "glasses" in gm:
            masks["glasses"] = gm["glasses"]
            fig = fig | gm["glasses"]
    lmj = json.load(open(os.path.join(render_dir, view + "_landmarks.json")))
    chin = lmj.get("chin_y_px")
    regions = {}
    rows = np.arange(fig.shape[0])[:, None]
    skin = masks.get("skin", np.zeros_like(fig))
    above = rows < (chin if chin is not None else -1)
    face_parts = np.zeros_like(fig)
    for p in FACE_PARTS:
        if p in masks:
            face_parts |= masks[p]
    regions["skin_face"] = (skin | face_parts) & above
    regions["skin_limbs"] = skin & ~above
    for k, m in masks.items():
        if k not in ("skin", "face_detail"):
            regions[k] = m
    colour_only = {"skin_face": skin & above, "skin_limbs": skin & ~above}
    lms = {k: tuple(v["xy"]) for k, v in lmj["landmarks"].items() if v["visible"]}
    hidden = {k for k, v in lmj["landmarks"].items() if not v["visible"]}
    return {"img": img, "fig": fig, "regions": regions, "colour_only": colour_only, "landmarks": lms,
            "hidden": hidden, "chin_y": chin}


# -------------------------------------------------------------------------------------------------------- alignment
def snap_feet(side):
    for k in ("foot_L", "foot_R"):
        if k in side["landmarks"]:
            x, y = side["landmarks"][k]
            b = M.column_bottom(side["fig"], x)
            if b is not None:
                side["landmarks"][k] = (x, b)


def frame(side):
    x0, y0, x1, y1 = M.bbox(side["fig"])
    return {"top": float(y0), "bottom": float(y1), "cx": (x0 + x1) / 2.0, "height": float(y1 - y0),
            "width": float(x1 - x0)}


def place(mask, s, ox, oy, shape):
    """Scale a boolean mask by s (nearest) and paste it at integer offset (ox, oy) on a canvas of `shape`."""
    h, w = mask.shape
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    m = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((nw, nh), Image.NEAREST)) > 127
    out = np.zeros(shape, bool)
    xa, ya = max(0, ox), max(0, oy)
    xb, yb = min(shape[1], ox + nw), min(shape[0], oy + nh)
    if xb > xa and yb > ya:
        out[ya:yb, xa:xb] = m[ya - oy:yb - oy, xa - ox:xb - ox]
    return out


def place_image(img, s, ox, oy, shape, bg):
    h, w = img.shape[:2]
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    im = Image.fromarray(img).resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (shape[1], shape[0]), tuple(int(c) for c in bg))
    canvas.paste(im, (ox, oy))
    return np.asarray(canvas)


def align(ref, ren, search=(10, 3)):
    """Uniform scale by figure height (sole to top); bottom and horizontal centre aligned, then the integer offset
    within +-search px that maximises the figure IoU (camera framing differs between sheet and render)."""
    fr, fn = frame(ref), frame(ren)
    s = fr["height"] / fn["height"]
    ox0 = int(round(fr["cx"] - fn["cx"] * s))
    oy0 = int(round(fr["bottom"] - fn["bottom"] * s))
    best = None
    for dy in range(-search[1], search[1] + 1):
        for dx in range(-search[0], search[0] + 1):
            m = place(ren["fig"], s, ox0 + dx, oy0 + dy, ref["fig"].shape)
            v = M.iou(ref["fig"], m) or 0.0
            key = (round(v, 6), -abs(dx) - abs(dy))
            if best is None or key > best[0]:
                best = (key, dx, dy, m)
    _, dx, dy, fig = best
    return {"scale": s, "ox": ox0 + dx, "oy": oy0 + dy, "dx": dx, "dy": dy, "fig": fig}


def to_ref(pt, al):
    return (pt[0] * al["scale"] + al["ox"], pt[1] * al["scale"] + al["oy"])


# ------------------------------------------------------------------------------------------------------ proportions
def proportions(side):
    f = frame(side)
    H, top = f["height"], f["top"]
    lm = side["landmarks"]
    out = {"figure_width": f["width"] / H}
    chin = lm.get("chin")
    head = (chin[1] - top) if chin else None
    if head:
        out["head_to_height"] = head / H
        if "eye_L" in lm or "eye_R" in lm:
            ys = [lm[k][1] for k in ("eye_L", "eye_R") if k in lm]
            out["eye_line"] = (sum(ys) / len(ys) - top) / H
        if "mouth" in lm:
            out["mouth_line"] = (lm["mouth"][1] - top) / H
        ws = [math.dist(lm[f"eye_inner_{s}"], lm[f"eye_outer_{s}"]) for s in ("L", "R")
              if f"eye_inner_{s}" in lm and f"eye_outer_{s}" in lm]
        if ws:
            out["eye_width_to_head"] = sum(ws) / len(ws) / head
        if "eye_L" in lm and "eye_R" in lm:
            out["eye_spacing_to_head"] = abs(lm["eye_L"][0] - lm["eye_R"][0]) / head
    arms = [math.dist(lm[f"shoulder_{s}"], lm[f"hand_{s}"]) for s in ("L", "R")
            if f"shoulder_{s}" in lm and f"hand_{s}" in lm]
    if arms:
        out["arm_length"] = sum(arms) / len(arms) / H
    if "shoulder_L" in lm and "shoulder_R" in lm and abs(lm["shoulder_L"][0] - lm["shoulder_R"][0]) > 0.05 * H:
        out["shoulder_width"] = abs(lm["shoulder_L"][0] - lm["shoulder_R"][0]) / H
    if "foot_L" in lm and "foot_R" in lm and abs(lm["foot_L"][0] - lm["foot_R"][0]) > 0.04 * H:
        c = M.crotch_y(side["fig"], (lm["foot_L"][0] + lm["foot_R"][0]) / 2, f["bottom"], f["top"])
        if c is not None:
            out["leg_gap_height"] = (f["bottom"] - c) / H
    for k, v in lm.items():
        if k.startswith("hem_"):
            out[k + "_height"] = (v[1] - top) / H
    hair = side["regions"].get("hair")
    if hair is not None and hair.any():
        out["hair_area"] = float(hair.sum()) / H ** 2
        ys = np.nonzero(hair.any(axis=1))[0]
        out["hair_length"] = (ys.max() + 1 - top) / H
        if "eye_line" in out:
            ye = top + out["eye_line"] * H  # mean over a band of +-1.5% of the height around the eye line
            rows = range(int(round(ye - 0.015 * H)), int(round(ye + 0.015 * H)) + 1)
            out["hair_width_at_eyes"] = sum(M.width_at(hair, y) for y in rows) / len(rows) / H
    eyes = side["regions"].get("eyes")
    if head and eyes is not None and eyes.any():
        out["eye_area_to_head"] = float(eyes.sum()) / head ** 2
    return out


# --------------------------------------------------------------------------------------------------------- per view
def analyse_view(ref, ren, head_fraction_ref):
    snap_feet(ref)
    snap_feet(ren)
    al = align(ref, ren)
    shape = ref["fig"].shape
    fr = frame(ref)
    head_px = ((ref["landmarks"]["chin"][1] - fr["top"]) if "chin" in ref["landmarks"]
               else head_fraction_ref * fr["height"])
    res = {"alignment": {"scale": al["scale"], "offset_px": [al["ox"], al["oy"]], "search_shift_px": [al["dx"], al["dy"]]},
           "head_height_px": head_px, "figure_iou": M.iou(ref["fig"], al["fig"]),
           "edge_roughness": {"reference": M.edge_roughness(ref["fig"]), "render": M.edge_roughness(ren["fig"])}}
    # regions
    reg = {}
    aligned = {}
    res["render_regions_not_annotated"] = sorted(set(ren["regions"]) - set(ref["regions"]))
    for name in sorted(ref["regions"]):  # only what the annotator marked in this view is compared
        rm = ref["regions"].get(name)
        nm = ren["regions"].get(name)
        am = place(nm, al["scale"], al["ox"], al["oy"], shape) if nm is not None else None
        aligned[name] = am
        ra = float(rm.sum()) if rm is not None else 0.0
        na = float(am.sum()) if am is not None else 0.0
        if ra < 20 and na < 20:
            continue
        reg[name] = {"iou": M.iou(rm if rm is not None else np.zeros(shape, bool), am if am is not None else np.zeros(shape, bool)),
                     "area_ratio": (na / ra) if ra > 0 else None, "reference_px": ra, "render_px": na}
    res["regions"] = reg
    # landmarks
    rl = ref["landmarks"]
    nl = {k: to_ref(v, al) for k, v in ren["landmarks"].items()}
    errs = M.landmark_errors(rl, nl, head_px, Y_ONLY)
    res["landmarks"] = {k: {"error_head": e, "reference": list(rl[k]), "render": [round(c, 2) for c in nl[k]],
                            "dx_head": (nl[k][0] - rl[k][0]) / head_px, "dy_head": (nl[k][1] - rl[k][1]) / head_px}
                        for k, e in errs.items()}
    res["landmark_nme"] = M.mean(errs.values())
    res["hidden_in_render"] = sorted(k for k in rl if k in ren["hidden"])
    res["not_projected"] = sorted(k for k in rl if k not in ren["landmarks"] and k not in ren["hidden"])
    # proportions (each image in its own frame; ratios are dimensionless)
    pr, pn = proportions(ref), proportions(ren)
    res["proportions"] = {k: {"reference": pr[k], "render": pn[k], "relative": (pn[k] / pr[k] - 1) if pr[k] else None}
                          for k in sorted(set(pr) & set(pn))}
    # colour and texture (colour on native pixels; texture with the render resampled to the reference scale)
    ren_img_ref = place_image(ren["img"], al["scale"], al["ox"], al["oy"], shape, (0, 0, 0))
    col, tex = {}, {}
    px_per_h = head_px / 256.0
    for name in sorted(reg):
        if name in ("eyes", "glasses"):
            continue
        rm = ref["regions"].get(name)
        if rm is None:
            continue
        rmc = rm.copy()
        for other, om in ref["regions"].items():  # remove regions lying on top (islands, eyes, glasses)
            if other != name and (om & rm).sum() < 0.5 * rm.sum():
                rmc &= ~om
        rmc = M.erode(rmc, 1)
        nmc = ren.get("colour_only", {}).get(name, ren["regions"].get(name))
        if nmc is None:
            continue
        nmc = M.erode(nmc, 1)
        a, b = M.colour_stats(ref["img"], rmc), M.colour_stats(ren["img"], nmc)
        if a and b and a["n"] >= 30 and b["n"] >= 30:
            d = M.colour_difference(a, b)
            col[name] = {"reference_srgb": a["srgb"], "render_srgb": b["srgb"], "reference_lab": a["lab"].tolist(),
                         "render_lab": b["lab"].tolist(), "spread_de00": {"reference": a["spread_de00"], "render": b["spread_de00"]},
                         **d}
        am = aligned.get(name)
        if am is not None:
            ta = M.texture_stats(ref["img"], rmc, px_per_h)
            tb = M.texture_stats(ren_img_ref, am & M.erode(al["fig"], 1), px_per_h)
            if ta and tb:
                tex[name] = {"reference": ta, "render": tb,
                             "fuzz_ratio": tb["fuzz_hf_rms"] / ta["fuzz_hf_rms"] if ta["fuzz_hf_rms"] > 0 else None,
                             "sheen_ratio": tb["sheen_p90_p50"] / ta["sheen_p90_p50"] if ta["sheen_p90_p50"] > 0 else None}
    res["colour"] = col
    res["texture"] = tex
    return res, {"aligned_fig": al["fig"], "aligned_regions": aligned, "render_img": ren_img_ref,
                 "render_landmarks": nl, "alignment": al}


# --------------------------------------------------------------------------------------------------------- overall
def _med(vals):
    vals = [v for v in vals if v is not None]
    return float(np.median(vals)) if vals else None


PROP_WORDS = {
    "head_to_height": ("head", "large", "small", "relative to the body"),
    "eye_width_to_head": ("eyes", "large", "small", "(width relative to head height)"),
    "eye_area_to_head": ("eye area", "large", "small", "relative to head height squared"),
    "eye_spacing_to_head": ("eye spacing", "wide", "narrow", "relative to head height"),
    "eye_line": ("eye line", "low", "high", "on the figure"),
    "mouth_line": ("mouth", "low", "high", "on the figure"),
    "arm_length": ("arms", "long", "short", "relative to height"),
    "leg_gap_height": ("visible gap between the legs (crotch to sole)", "long", "short", "relative to height"),
    "shoulder_width": ("shoulders", "wide", "narrow", "relative to height"),
    "figure_width": ("overall silhouette", "wide", "narrow", "relative to height"),
    "hair_area": ("hair volume (silhouette area)", "large", "small", ""),
    "hair_width_at_eyes": ("hair width at the temples (eye level)", "wide", "narrow", ""),
    "hair_length": ("hair length", "long", "short", ""),
}


def summarise(views):
    """views: {view: per-view result}. Returns the overall block, the ranked differences and the score."""
    names = list(views)
    figs = [views[v]["figure_iou"] for v in names]
    reg = {}
    for v in names:
        for k, r in views[v]["regions"].items():
            reg.setdefault(k, []).append((v, r))
    region_summary = {k: {"iou_mean": M.mean([r["iou"] for _, r in lst]),
                          "area_ratio_median": _med([r["area_ratio"] for _, r in lst]),
                          "views": len(lst)} for k, lst in sorted(reg.items())}
    lmk = {}
    for v in names:
        for k, r in views[v]["landmarks"].items():
            lmk.setdefault(k, []).append((v, r))
    landmark_summary = {k: {"error_head_mean": M.mean([r["error_head"] for _, r in lst]),
                            "dy_head_mean": M.mean([r["dy_head"] for _, r in lst]),
                            "dx_head_mean": M.mean([r["dx_head"] for _, r in lst]), "views": len(lst)}
                        for k, lst in sorted(lmk.items())}
    props = {}
    for v in names:
        for k, r in views[v]["proportions"].items():
            props.setdefault(k, []).append((v, r))
    prop_summary = {k: {"relative_median": _med([r["relative"] for _, r in lst]),
                        "reference_median": _med([r["reference"] for _, r in lst]),
                        "render_median": _med([r["render"] for _, r in lst]),
                        "by_view": {v: r["relative"] for v, r in lst}} for k, lst in sorted(props.items())}
    cols = {}
    for v in names:
        for k, r in views[v]["colour"].items():
            cols.setdefault(k, []).append((v, r))
    colour_summary = {k: {"de00_median": _med([r["de00"] for _, r in lst]),
                          "de00_luma_matched_median": _med([r["de00_luma_matched"] for _, r in lst]),
                          "dL_median": _med([r["dL"] for _, r in lst]), "dC_median": _med([r["dC"] for _, r in lst]),
                          "dh_median": _med([r["dh_deg"] for _, r in lst]),
                          "spread_ratio_median": _med([r["spread_ratio"] for _, r in lst]),
                          "reference_lab_median": np.median([r["reference_lab"] for _, r in lst], axis=0).tolist(),
                          "render_lab_median": np.median([r["render_lab"] for _, r in lst], axis=0).tolist(),
                          "views": len(lst)} for k, lst in sorted(cols.items())}
    texs = {}
    for v in names:
        for k, r in views[v]["texture"].items():
            texs.setdefault(k, []).append(r)
    texture_summary = {k: {"fuzz_ratio_median": _med([r["fuzz_ratio"] for r in lst]),
                           "sheen_ratio_median": _med([r["sheen_ratio"] for r in lst]), "views": len(lst)}
                       for k, lst in sorted(texs.items())}
    hidden = {}
    for v in names:
        for k in views[v]["hidden_in_render"]:
            hidden.setdefault(k, []).append(v)
    # sub-scores (0..1) and the single score
    nme = M.mean([views[v]["landmark_nme"] for v in names])
    mre = M.mean([abs(p["relative_median"]) for p in prop_summary.values() if p["relative_median"] is not None])
    de = M.mean([c["de00_median"] for c in colour_summary.values()])
    tx = M.mean([abs(math.log2(t[key])) for t in texture_summary.values()
                 for key in ("fuzz_ratio_median", "sheen_ratio_median") if t.get(key)])
    sub = {"silhouette": M.clamp01((M.mean(figs) - 0.5) / 0.5) if figs else None,
           "regions": region_score(views),
           "landmarks": M.clamp01(1 - nme / 0.3) if nme is not None else None,
           "proportions": M.clamp01(1 - mre / 0.3) if mre is not None else None,
           "colour": M.clamp01(1 - de / 20) if de is not None else None,
           "texture": M.clamp01(1 - tx / 1.5) if tx is not None else None}
    wsum = sum(WEIGHTS[k] for k, v in sub.items() if v is not None)
    score = 100 * sum(WEIGHTS[k] * v for k, v in sub.items() if v is not None) / wsum if wsum else None
    overall = {"figure_iou_mean": M.mean(figs), "landmark_nme_mean": nme, "proportion_rel_error_mean": mre,
               "colour_de00_mean": de, "texture_log2_ratio_mean": tx, "subscores": sub, "weights": WEIGHTS,
               "score": score, "regions": region_summary, "landmarks": landmark_summary, "proportions": prop_summary,
               "colour": colour_summary, "texture": texture_summary, "hidden_in_render": hidden}
    overall["differences"] = differences(overall, len(names))
    return overall


def region_score(views):
    """Region IoU averaged over views and regions, weighted by the reference area (small parts weigh less)."""
    num = den = 0.0
    for r in views.values():
        for k, x in r["regions"].items():
            if x["iou"] is not None and x["reference_px"] > 0:
                num += x["iou"] * x["reference_px"]
                den += x["reference_px"]
    return num / den if den else None


def _pct(r):
    return f"{abs(r) * 100:.0f}%"


def _lm_group(k):
    for s in ("_L", "_R"):
        if k.endswith(s):
            return k[:-2]
    return k


LM_WORDS = {"eye": "eye centres", "iris": "irises", "eye_inner": "inner eye corners", "eye_outer": "outer eye corners",
            "brow_inner": "inner brow ends", "brow_outer": "outer brow ends", "nose": "nose tip", "mouth": "mouth centre",
            "mouth_corner": "mouth corners", "chin": "chin", "ear_top": "ear tops", "hairline": "hairline",
            "neck": "neck", "shoulder": "shoulders", "hand": "hands", "foot": "feet"}


def differences(o, nviews):
    """Ranked list of the largest differences in plain words. severity = size of the difference divided by a
    tolerance (5% for proportions, 0.05 head heights for landmarks, 0.15 IoU loss for regions, dE00 4 for colour,
    one half log2 step for texture)."""
    items = []
    for k, p in o["proportions"].items():
        r = p["relative_median"]
        if r is None:
            continue
        if k.startswith("hem_"):
            item = k[4:-7]
            d = p["render_median"] - p["reference_median"]
            items.append({"kind": "proportion", "key": k, "severity": abs(d) / 0.02,
                          "text": f"{item} hem {abs(d) * 100:.1f}% of the height too {'low' if d > 0 else 'high'}"})
            continue
        w = PROP_WORDS.get(k)
        if not w:
            continue
        tol = 0.10 if k.startswith("hair") or k == "eye_area_to_head" else PROPORTION_TOL
        if k in ("eye_line", "mouth_line"):
            d = p["render_median"] - p["reference_median"]
            items.append({"kind": "proportion", "key": k, "severity": abs(d) / 0.02,
                          "text": f"{w[0]} {abs(d) * 100:.1f}% of the height too {w[1] if d > 0 else w[2]}"})
            continue
        sign = f"{'+' if r > 0 else '-'}{_pct(r)}"
        txt = (f"{w[0]} {_pct(r)} too {w[1] if r > 0 else w[2]} {w[3]}".strip() if not k.startswith("hair")
               else f"{w[0]} {sign}")
        items.append({"kind": "proportion", "key": k, "severity": abs(r) / tol, "text": txt})
    groups = {}
    for k, l in o["landmarks"].items():
        g = _lm_group(k)
        if g.startswith("hem_"):
            continue
        groups.setdefault(g, []).append(l)
    for g, ls in groups.items():
        e = M.mean([l["error_head_mean"] for l in ls])
        dy = M.mean([l["dy_head_mean"] for l in ls])
        if e is None:
            continue
        dirn = f", render {'lower' if dy > 0 else 'higher'} by {abs(dy):.2f}" if dy is not None and abs(dy) > 0.5 * e else ""
        items.append({"kind": "landmark", "key": g, "severity": e / 0.05,
                      "text": f"{LM_WORDS.get(g, g)} off by {e:.2f} head heights{dirn}"})
    for k, r in o["regions"].items():
        if r["iou_mean"] is None:
            continue
        ar = r["area_ratio_median"]
        extra = f"; render area {'+' if ar >= 1 else '-'}{_pct(ar - 1)}" if ar else "; missing in render"
        items.append({"kind": "region", "key": k, "severity": (1 - r["iou_mean"]) / 0.15,
                      "text": f"{k.replace('garment:', '').replace('accessory:', '')} silhouette overlap {r['iou_mean']:.2f}{extra}"})
    for k, c in o["colour"].items():
        if c["de00_median"] is None:
            continue
        parts = []
        if abs(c["dL_median"]) >= 3:
            parts.append(f"{'lighter' if c['dL_median'] > 0 else 'darker'} by {abs(c['dL_median']):.0f} L*")
        if abs(c["dC_median"]) >= 3:
            parts.append(f"{'more' if c['dC_median'] > 0 else 'less'} saturated by {abs(c['dC_median']):.0f} C*")
        if abs(c["dh_median"]) >= 8:
            parts.append(f"hue shifted {abs(c['dh_median']):.0f} deg {'towards yellow/green' if c['dh_median'] > 0 else 'towards red/magenta'}")
        name = k.replace("garment:", "").replace("accessory:", "").replace("_", " ")
        items.append({"kind": "colour", "key": k, "severity": c["de00_median"] / 4,
                      "text": f"{name} colour dE00 {c['de00_median']:.1f}" + (f" (render {', '.join(parts)})" if parts else "")
                      + f"; luma-matched dE00 {c['de00_luma_matched_median']:.1f}"})
    for k, t in o["texture"].items():
        name = k.replace("garment:", "").replace("accessory:", "").replace("_", " ")
        for key, label in (("fuzz_ratio_median", "fuzz / fibre texture"), ("sheen_ratio_median", "sheen highlights")):
            v = t.get(key)
            if v:
                items.append({"kind": "texture", "key": f"{k}:{key[:-13]}", "severity": abs(math.log2(v)) / 0.5,
                              "text": f"{name} {label} {'+' if v >= 1 else '-'}{_pct(v - 1)} vs reference"})
    for k, vs in o["hidden_in_render"].items():
        items.append({"kind": "visibility", "key": k, "severity": 1.0 + 0.5 * len(vs),
                      "text": f"{LM_WORDS.get(_lm_group(k), k)} ({k}) hidden in the render but visible in the reference ({len(vs)} of {nviews} views)"})
    items.sort(key=lambda d: (-round(d["severity"], 6), d["key"]))
    for i, d in enumerate(items):
        d["rank"] = i + 1
    return items
