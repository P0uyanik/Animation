"""Look metrics added in T-064: hair read, skin colour under lighting, face windows (plain Python: numpy only).

All functions work in the reference frame on one view: the reference image with its region masks, and the render
image and masks already placed into that frame by analysis.align (uniform scale, integer offset). Sizes are given in
reference head heights (chin to figure top), so the same rules apply to every character. Nothing here is tuned to a
character; the tolerances are round numbers documented in docs/CHARACTER_FIDELITY.md.

Why these exist (T-063 §5.2): region IoU alone ranked a fused helmet above felt clumps (T-049), the skin median hid a
grey cast and missing blush, and nothing looked at the eye lids or cheeks."""
import math

import numpy as np

import metrics as M

# A region S that lies mostly (> 50 %) inside region R is an island on top of R (a reference polygon is traced with its
# holes filled, so the girl's front hair outline also covers her face). R loses those pixels, except for the parts R
# includes by convention on both sides (skin_face contains the eyes and face details), and except for the glasses,
# which are a filled overlay on both sides (the render's glasses pass is drawn over the main pass).
CONTAINS = {"skin_face": {"eyes"}}
OVERLAYS = {"glasses"}


def exclusive_regions(regions):
    """Reference regions without the islands lying on top of them; skin_face also takes in the eyes (the hand eye
    ellipses can stick out of the colour-traced face). Returns (regions, {region: px removed (+) or added (-)})."""
    out, carved = {}, {}
    area = {k: int(m.sum()) for k, m in regions.items()}
    for r, m in sorted(regions.items()):
        if r in OVERLAYS:
            out[r] = m
            continue
        mm = m.copy()
        for s, o in sorted(regions.items()):
            if s == r or s in OVERLAYS or s in CONTAINS.get(r, ()) or area[s] == 0:
                continue
            ov = int((o & m).sum())
            if ov > 0.5 * area[s] and area[s] < area[r]:
                mm &= ~o
        for s in sorted(CONTAINS.get(r, ())):  # skin_face holds the eyes, as on the render side
            if s in regions:
                mm |= regions[s]
        out[r] = mm
        if int(mm.sum()) != area[r]:
            carved[r] = area[r] - int(mm.sum())
    return out, carved


# ----------------------------------------------------------------------------------------------------------- hair
LOCK = 0.035     # lock / clump scale (head heights): felt clumps and ringlets are a few % of the head
OUTLINE = 0.04   # outline smoothing scale (head heights)


def _perimeter(m):
    m = m.astype(np.int8)
    return float(np.abs(np.diff(m, axis=0)).sum() + np.abs(np.diff(m, axis=1)).sum())


def hair_read(img, hair, head_px):
    """Image measures of how hair reads, inside one hair mask (None when the mask is too small).

    outline:  perimeter of the hair mask / perimeter after smoothing at the outline scale. Thin strands, ropes and
              fibre spikes raise it; broad locks with pointed tips sit near the reference; a fused shell is low.
    strand:   luma structure-tensor coherence at the lock scale, energy weighted. Parallel ropes, carved rows and
              straight-cut grooves are highly directional; felted clumps are not.
    relief:   band-pass luma contrast at the lock scale (difference of two Gaussians, mask normalised) divided by the
              mean luma: separate locks with shaded gaps between them have relief, a fused helmet has little."""
    core = M.erode(hair, 2)
    if core.sum() < 200:
        return None
    y = M.luma(img)
    s = max(0.6, LOCK * head_px)
    b1, b2 = M.masked_blur(y, hair, s), M.masked_blur(y, hair, 2 * s)
    relief = float(np.sqrt(np.mean((b1 - b2)[core] ** 2)) / max(1.0, float(np.mean(y[core]))))
    yb = M.blur(y, 0.4 * s)
    gx, gy = np.gradient(yb, axis=1), np.gradient(yb, axis=0)
    jxx, jyy, jxy = (M.masked_blur(gx * gx, hair, s), M.masked_blur(gy * gy, hair, s),
                     M.masked_blur(gx * gy, hair, s))
    tr = jxx + jyy
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / np.maximum(tr, 1e-9)
    strand = float(np.sum((coh * tr)[core]) / max(1e-9, float(np.sum(tr[core]))))
    smooth = M.blur(hair.astype(float), max(1.0, OUTLINE * head_px)) > 0.5
    outline = _perimeter(hair) / max(1.0, _perimeter(smooth))
    return {"outline": outline, "strand": strand, "relief": relief}


def hair_view(ref_img, ref_regions, ren_img, ren_hair, head_px):
    """Per-view hair block: reference and render measures, their log2 ratios, and the face cover (render hair over
    the face the reference shows uncovered, as a fraction of that face; views with eyes annotated only)."""
    rh = ref_regions.get("hair")
    if rh is None or ren_hair is None or rh.sum() < 200:
        return None
    a, b = hair_read(ref_img, rh, head_px), hair_read(ren_img, ren_hair, head_px)
    out = {"reference": a, "render": b}
    if a and b:
        out["log2_ratio"] = {k: math.log2(b[k] / a[k]) if a[k] > 0 and b[k] > 0 else None for k in a}
    face = ref_regions.get("skin_face")
    if face is not None and "eyes" in ref_regions and face.sum() > 100:
        out["face_cover"] = float((ren_hair & face).sum()) / float(face.sum())
    return out


HAIR_TOL = {"outline": 1.0, "strand": 1.0, "relief": 2.0}  # log2 steps that score 0
COVER_TOL = 0.3   # face fraction covered that scores 0
VOLUME_TOL = 0.5  # mean |relative error| of hair_area / hair_width_at_eyes / hair_length that scores 0
HAIR_PROPORTIONS = ("hair_area", "hair_width_at_eyes", "hair_length")


def hair_summary(views, prop_summary, region_summary):
    """Hair sub-score (0..1): the equal-weight mean of six parts, each 0..1:
    shape (hair IoU), volume (hair proportions), outline, strand, relief (log2 ratios vs the reference) and face
    cover. A part with no data is left out."""
    ratios = {k: [] for k in HAIR_TOL}
    cover = []
    for r in views.values():
        h = r.get("hair") or {}
        for k, v in (h.get("log2_ratio") or {}).items():
            if v is not None:
                ratios[k].append(abs(v))
        if h.get("face_cover") is not None:
            cover.append(h["face_cover"])
    vol = [abs(prop_summary[k]["relative_median"]) for k in HAIR_PROPORTIONS
           if k in prop_summary and prop_summary[k]["relative_median"] is not None]
    parts = {"shape": region_summary.get("hair", {}).get("iou_mean"),
             "volume": M.clamp01(1 - M.mean(vol) / VOLUME_TOL) if vol else None,
             "face_cover": M.clamp01(1 - M.mean(cover) / COVER_TOL) if cover else None}
    for k, tol in HAIR_TOL.items():
        parts[k] = M.clamp01(1 - M.mean(ratios[k]) / tol) if ratios[k] else None
    means = {"mean_abs_log2_" + k: M.mean(v) for k, v in ratios.items()}
    signed = {k: [] for k in HAIR_TOL}
    for r in views.values():
        for k, v in ((r.get("hair") or {}).get("log2_ratio") or {}).items():
            if v is not None:
                signed[k].append(v)
    means.update({"mean_log2_" + k: M.mean(v) for k, v in signed.items()})
    return {"parts": parts, "score": M.mean(parts.values()), "face_cover_mean": M.mean(cover),
            "volume_abs_rel_mean": M.mean(vol), **means}


# ----------------------------------------------------------------------------------------------------------- skin
SHADE_Q, LIT_Q = 30, 70  # percentiles of L* that split shade / light pixels


def skin_stats(img, mask):
    """Colour statistics of a skin patch that a single median misses: chroma in shade and in light (the references
    keep warm chroma in shade; a grey cast drains it) and the 90th percentile of a* (blush / warmth)."""
    m = M.erode(mask, 1)
    if m.sum() < 60:
        return None
    lab = M.srgb_to_lab(img[m])
    L, C, a = lab[:, 0], np.hypot(lab[:, 1], lab[:, 2]), lab[:, 1]
    lo, hi = L <= np.percentile(L, SHADE_Q), L >= np.percentile(L, LIT_Q)
    return {"n": int(m.sum()), "L_median": float(np.median(L)), "C_median": float(np.median(C)),
            "C_shade": float(np.median(C[lo])), "C_light": float(np.median(C[hi])), "a_p90": float(np.percentile(a, 90))}


SKIN_TOL = {"de00_luma_matched": 10.0, "dL": 30.0, "C_shade": 15.0, "a_p90": 15.0}


def skin_view(ref_img, ref_mask, ren_img, ren_mask, colour):
    """Skin block for one region in one view. colour: the colour_difference dict of the same masks. Terms (each
    scores 0 at its SKIN_TOL): luma-matched dE00 (hue/chroma at equal lightness), |dL*| with a wide tolerance (the
    references have their own light, yet a much darker skin is a real miss), the chroma in shade (grey cast) and the
    a* 90th percentile (blush / warmth)."""
    a, b = skin_stats(ref_img, ref_mask), skin_stats(ren_img, ren_mask)
    if not a or not b:
        return None
    d = {"de00": colour["de00"], "de00_luma_matched": colour["de00_luma_matched"], "dL": colour["dL"],
         "dC_shade": b["C_shade"] - a["C_shade"], "da_p90": b["a_p90"] - a["a_p90"],
         "grey_cast": max(0.0, a["C_shade"] - b["C_shade"])}
    terms = [d["de00_luma_matched"] / SKIN_TOL["de00_luma_matched"], abs(d["dL"]) / SKIN_TOL["dL"],
             abs(d["dC_shade"]) / SKIN_TOL["C_shade"], abs(d["da_p90"]) / SKIN_TOL["a_p90"]]
    d["score"] = M.clamp01(1 - M.mean(terms))
    return {"reference": a, "render": b, **d}


# ---------------------------------------------------------------------------------------------------- face windows
def _ellipse(shape, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx - cx) / max(rx, 0.5)) ** 2 + ((yy - cy) / max(ry, 0.5)) ** 2 <= 1.0


def _ring(m, r=2):
    return m & ~M.erode(m, r) if m is not None else None


def eye_windows(shape, lm, side, eyes=None):
    """Lid and cheek windows for one eye, sized by the eye width w (inner to outer corner landmarks).
    lid: a band 0.25 w high starting 0.06 w above the top edge of the visible eye opening (the eyes mask near this
    eye; the gap skips the lash line), over the eye's width; without an eyes mask, an ellipse 0.55 w above the eye
    centre. cheek: below and outside the eye (0.85 w down, 0.2 w outwards; 0.35 w x 0.25 w)."""
    keys = (f"eye_{side}", f"eye_inner_{side}", f"eye_outer_{side}")
    if not all(k in lm for k in keys):
        return None
    c, i, o = (lm[k] for k in keys)
    w = math.dist(i, o)
    if w < 4:
        return None
    out_dir = 1.0 if o[0] > i[0] else -1.0
    lid = None
    if eyes is not None:
        near = eyes & _ellipse(shape, c[0], c[1], 0.8 * w, 0.8 * w)
        cols = np.nonzero(near.any(axis=0))[0]
        if len(cols) >= 3:
            top = np.argmax(near, axis=0)  # first eye row per column
            yy = np.arange(shape[0])[:, None]
            band = (yy < top[None, :] - 0.06 * w) & (yy >= top[None, :] - 0.31 * w)
            lid = band & near.any(axis=0)[None, :]
    if lid is None:
        lid = _ellipse(shape, c[0], c[1] - 0.55 * w, 0.5 * w, 0.22 * w)
    return {"lid": lid, "cheek": _ellipse(shape, c[0] + out_dir * 0.2 * w, c[1] + 0.85 * w, 0.35 * w, 0.25 * w),
            "w": w}


def _lab_median(img, m):
    if m is None or m.sum() < 12:
        return None
    return np.median(M.srgb_to_lab(img[m]), axis=0)


FACE_TOL = {"lid_dL": 15.0, "lid_dC": 10.0, "blush_da": 10.0}


def face_view(ref, ren, ref_regions, ren_regions_native):
    """Face-window block for one view, each side measured in its own frame with its own landmarks:
    lid_dL / lid_dC: lightness / chroma of the lid window minus the face skin median (pale or grey lid shells read as
    domes); blush_da: a* of the cheek window (75th percentile) minus the face skin median a*.
    The render minus reference differences are scored against FACE_TOL."""
    sides = {}
    for side in (ref, ren):  # frontal views only: both eyes, spaced at least 1.2 eye widths apart
        lm = side["landmarks"]
        need = [f"eye{p}_{s}" for s in ("L", "R") for p in ("", "_inner", "_outer")]
        if not all(k in lm for k in need):
            return None
        w = (math.dist(lm["eye_inner_L"], lm["eye_outer_L"]) + math.dist(lm["eye_inner_R"], lm["eye_outer_R"])) / 2
        if abs(lm["eye_L"][0] - lm["eye_R"][0]) < 1.2 * w:
            return None
    for tag, side, regs in (("reference", ref, ref_regions), ("render", ren, ren_regions_native)):
        skin = regs.get("skin_face")
        if skin is None:
            return None
        eyes = regs.get("eyes")
        if eyes is not None:
            skin = skin & ~eyes
        g = regs.get("glasses")
        if g is not None:
            skin = skin & ~_ring(g, 2)
        hair = regs.get("hair")
        if hair is not None:
            skin = skin & ~hair
        base = _lab_median(side["img"], M.erode(skin, 1))
        if base is None:
            return None
        per_eye = {}
        for s in ("L", "R"):
            win = eye_windows(skin.shape, side["landmarks"], s, regs.get("eyes"))
            if not win:
                continue
            lid_px = win["lid"] & skin
            if lid_px.sum() >= 12:  # lashes and brow strokes are not lid skin: drop pixels far darker than the skin
                lab = M.srgb_to_lab(side["img"])
                lid_px &= lab[..., 0] > base[0] - 25
            lid = _lab_median(side["img"], lid_px)
            ck = win["cheek"] & skin
            cheek_a = float(np.percentile(M.srgb_to_lab(side["img"][ck])[:, 1], 75)) if ck.sum() >= 12 else None
            per_eye[s] = {"lid_dL": float(lid[0] - base[0]) if lid is not None else None,
                          "lid_dC": float(math.hypot(lid[1], lid[2]) - math.hypot(base[1], base[2])) if lid is not None else None,
                          "blush_da": float(cheek_a - base[1]) if cheek_a is not None else None}
        sides[tag] = per_eye
    diffs = {}
    for s in sorted(set(sides["reference"]) & set(sides["render"])):
        for k in FACE_TOL:
            a, b = sides["reference"][s].get(k), sides["render"][s].get(k)
            if a is not None and b is not None:
                diffs.setdefault(k, []).append(b - a)
    if not diffs:
        return None
    d = {k: M.mean(v) for k, v in diffs.items()}
    score = M.clamp01(1 - M.mean([abs(v) / FACE_TOL[k] for k, v in d.items()]))
    return {"reference": sides["reference"], "render": sides["render"], "difference": d, "score": score}


HAIR_WORDS = {"outline": ("hair outline", "more ragged / stringy", "smoother / more fused"),
              "strand": ("hair strand direction", "more directional (ropes, rows or grooves)", "less directional"),
              "relief": ("hair lock relief", "stronger", "weaker (fused, helmet-like)")}


def differences(o):
    """Ranked-difference items for the T-064 parts (same severity convention as analysis.differences)."""
    items = []
    h = o.get("hair") or {}
    for k, (name, more, less) in HAIR_WORDS.items():
        v = h.get("mean_log2_" + k)
        if v is not None:
            items.append({"kind": "hair", "key": "hair:" + k, "severity": abs(v) / (0.25 * HAIR_TOL[k]),
                          "text": f"{name} {more if v > 0 else less} than the reference ({v:+.2f} log2)"})
    if h.get("face_cover_mean") is not None:
        c = h["face_cover_mean"]
        items.append({"kind": "hair", "key": "hair:face_cover", "severity": c / 0.05,
                      "text": f"hair covers {c * 100:.0f}% of the face that the reference shows uncovered"})
    for k, sk in (o.get("skin") or {}).items():
        name = k.replace("_", " ")
        if sk.get("dC_shade_median") is not None:
            d = sk["dC_shade_median"]
            items.append({"kind": "skin", "key": k + ":shade", "severity": abs(d) / 4,
                          "text": f"{name} chroma in shade {d:+.1f} C*" + (" (grey cast)" if d < 0 else " (too saturated)")})
        if sk.get("da_p90_median") is not None:
            d = sk["da_p90_median"]
            items.append({"kind": "skin", "key": k + ":blush", "severity": abs(d) / 4,
                          "text": f"{name} warmth / blush (a* P90) {d:+.1f}" + (" (weaker)" if d < 0 else " (stronger)")})
    f = (o.get("face") or {}).get("difference_mean") or {}
    words = {"lid_dL": ("lids vs face skin, lightness", "L*", "paler lids (shell domes)", "darker lids"),
             "lid_dC": ("lids vs face skin, chroma", "C*", "more saturated lids", "greyer lids"),
             "blush_da": ("cheek blush vs face skin", "a*", "stronger blush", "weaker blush")}
    for k, (name, unit, pos, neg) in words.items():
        v = f.get(k)
        if v is not None:
            items.append({"kind": "face", "key": "face:" + k, "severity": abs(v) / 4,
                          "text": f"{name} {v:+.1f} {unit} vs the reference ({pos if v > 0 else neg})"})
    return items
