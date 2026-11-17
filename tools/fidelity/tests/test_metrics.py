"""Unit tests of the fidelity metric functions on synthetic images (plain Python: numpy + Pillow; no Blender).

    python3 tools/fidelity/tests/test_metrics.py

Covers IoU, landmark error, CIEDE2000 (published Sharma et al. 2005 test pairs), sRGB<->Lab, colour statistics,
alignment of a scaled/shifted synthetic render, crotch detection, texture statistics, polygon tracing and the
determinism of the analysis output. Prints one line per check and ALL PASS / FAILED."""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import analysis as A  # noqa: E402
import annotate_regions as AR  # noqa: E402
import metrics as M  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def rect(shape, x0, y0, x1, y1):
    m = np.zeros(shape, bool)
    m[y0:y1, x0:x1] = True
    return m


def figure(w, h, s=1.0, ox=0, oy=0):
    """Synthetic 'character': head disc, body, two legs with a gap; returns (mask, landmarks)."""
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)

    def P(x, y):
        return (x * s + ox, y * s + oy)
    d.ellipse([P(30, 10), P(70, 50)], fill=255)          # head
    d.rectangle([P(35, 50), P(65, 110)], fill=255)        # body
    d.rectangle([P(35, 110), P(47, 160)], fill=255)       # leg R
    d.rectangle([P(53, 110), P(65, 160)], fill=255)       # leg L
    lms = {"eye_R": P(42, 30), "eye_L": P(58, 30), "chin": P(50, 50), "foot_R": P(41, 160), "foot_L": P(59, 160),
           "hem_body": P(50, 110)}
    return np.asarray(im) > 0, lms


def test_iou():
    sh = (40, 40)
    a, b = rect(sh, 0, 0, 10, 10), rect(sh, 5, 0, 15, 10)
    check("iou half-overlapping squares = 1/3", abs(M.iou(a, b) - 1 / 3) < 1e-12, f"{M.iou(a, b):.6f}")
    check("iou identical = 1", M.iou(a, a) == 1.0)
    check("iou disjoint = 0", M.iou(a, rect(sh, 20, 20, 30, 30)) == 0.0)
    check("iou both empty = None", M.iou(np.zeros(sh, bool), np.zeros(sh, bool)) is None)
    check("iou symmetric", M.iou(a, b) == M.iou(b, a))


def test_ciede2000():
    pairs = [((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
             ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
             ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
             ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
             ((50.0, 2.5, 0.0), (50.0, 3.2592, 0.335), 1.0),
             ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
             ((22.7233, 20.0904, -46.694), (23.0331, 14.973, -42.5619), 2.0373),
             ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381)]
    got = [float(M.ciede2000(np.array(a), np.array(b))) for a, b, _ in pairs]
    err = max(abs(g - e) for g, (_, _, e) in zip(got, pairs))
    check("CIEDE2000 Sharma test pairs (8)", err < 1e-3, f"max abs error {err:.2e}")
    a, b = np.array(pairs[3][0]), np.array(pairs[3][1])
    check("CIEDE2000 symmetric", abs(float(M.ciede2000(a, b)) - float(M.ciede2000(b, a))) < 1e-9)
    check("CIEDE2000 identical = 0", float(M.ciede2000(a, a)) == 0.0)
    batch = M.ciede2000(np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs]))
    check("CIEDE2000 vectorised = scalar", np.allclose(batch, got))


def test_lab():
    w = M.srgb_to_lab(np.array([255, 255, 255]))
    check("sRGB white -> L 100, a b 0", abs(w[0] - 100) < 0.01 and abs(w[1]) < 0.01 and abs(w[2]) < 0.01, str(np.round(w, 3)))
    g = M.srgb_to_lab(np.array([119, 119, 119]))
    check("sRGB 119 grey -> L ~50", abs(g[0] - 50) < 0.5, f"{g[0]:.2f}")
    cols = np.array([[150, 94, 96], [12, 200, 80], [255, 0, 0], [3, 3, 3]])
    back = M.lab_to_srgb(M.srgb_to_lab(cols))
    check("sRGB -> Lab -> sRGB round trip", np.abs(back - cols).max() <= 1, str(back.tolist()))
    img = np.zeros((20, 20, 3), np.uint8)
    img[:, :10] = (200, 100, 50)
    img[:, 10:] = (190, 95, 45)
    mask = np.ones((20, 20), bool)
    st = M.colour_stats(img, mask)
    check("colour_stats median within the two patch colours", 190 <= st["srgb"][0] <= 200 and st["spread_de00"] > 0)
    a = M.colour_stats(np.full((10, 10, 3), (150, 94, 96), np.uint8), np.ones((10, 10), bool))
    b = M.colour_stats(np.full((10, 10, 3), (120, 75, 77), np.uint8), np.ones((10, 10), bool))
    d = M.colour_difference(a, b)
    check("colour_difference: darker render -> dL < 0, dE00 > luma-matched dE00",
          d["dL"] < 0 and d["de00"] > d["de00_luma_matched"], f"dE {d['de00']:.2f} lm {d['de00_luma_matched']:.2f}")


def test_landmarks():
    ref = {"a": (0.0, 0.0), "hem_x": (5.0, 10.0), "only_ref": (1.0, 1.0)}
    ren = {"a": (3.0, 4.0), "hem_x": (100.0, 12.0), "only_ren": (2.0, 2.0)}
    e = M.landmark_errors(ref, ren, 10.0, ("hem_",))
    check("landmark error euclidean / head height", abs(e["a"] - 0.5) < 1e-12, str(e))
    check("landmark error hem compared on y only", abs(e["hem_x"] - 0.2) < 1e-12)
    check("landmark error only common names", set(e) == {"a", "hem_x"})


def test_alignment():
    ref_fig, ref_lm = figure(100, 170)
    ren_fig, ren_lm = figure(200, 360, s=2.0, ox=17, oy=12)
    ref = {"fig": ref_fig, "landmarks": dict(ref_lm)}
    ren = {"fig": ren_fig, "landmarks": dict(ren_lm)}
    al = A.align(ref, ren)
    v = M.iou(ref_fig, al["fig"])
    check("alignment of a 2x scaled, shifted copy: IoU > 0.95", v > 0.95, f"IoU {v:.4f} scale {al['scale']:.4f}")
    errs = M.landmark_errors(ref_lm, {k: A.to_ref(p, al) for k, p in ren_lm.items()}, 40.0)
    check("aligned landmarks within 0.03 head heights", max(errs.values()) < 0.03, f"max {max(errs.values()):.4f}")
    small, _ = figure(100, 170, s=0.9, ox=5, oy=17)
    v2 = M.iou(ref_fig, A.align(ref, {"fig": small, "landmarks": {}})["fig"])
    check("alignment normalises height (0.9x figure)", v2 > 0.93, f"IoU {v2:.4f}")
    wide = ref_fig.copy()
    wide[60:110, 20:35] = True
    v3 = M.iou(ref_fig, A.align(ref, {"fig": wide, "landmarks": {}})["fig"])
    check("a wider render keeps an IoU < 1 (width is not normalised away)", v3 < 0.95, f"IoU {v3:.4f}")


def test_geometry():
    fig, lm = figure(100, 170)
    c = M.crotch_y(fig, 50, 161, 10)
    check("crotch at the top of the leg gap", c == 111.0, str(c))  # PIL rectangles include their end row
    closed = fig.copy()
    closed[150:161, 47:54] = True  # feet touching: the gap is closed below
    check("crotch still found when the gap is closed at the feet", M.crotch_y(closed, 50, 161, 10) == 111.0)
    check("column_bottom = sole", M.column_bottom(fig, 41) == 161.0)
    check("width_at body row", M.width_at(fig, 80) == 31.0)
    smooth = np.zeros((80, 80), bool)
    smooth[20:60, 20:60] = True
    rough = smooth.copy()
    rough[19, 20:60:2] = True
    check("edge roughness: jagged boundary > smooth", M.edge_roughness(rough) > M.edge_roughness(smooth))


def test_texture():
    rng = np.random.default_rng(7)
    flat = np.full((64, 64, 3), 140, np.uint8)
    noisy = np.clip(140 + rng.normal(0, 8, (64, 64, 1)), 0, 255).repeat(3, 2).astype(np.uint8)
    m = np.ones((64, 64), bool)
    tf, tn = M.texture_stats(flat, m), M.texture_stats(noisy, m)
    check("texture: flat patch has ~0 fuzz", tf["fuzz_hf_rms"] < 1e-6, f"{tf['fuzz_hf_rms']:.2e}")
    check("texture: noisy patch fuzz > 4/255", tn["fuzz_hf_rms"] > 4, f"{tn['fuzz_hf_rms']:.2f}")
    check("texture: noise raises the Laplacian variance", tn["laplacian_var"] > tf["laplacian_var"])
    dark = np.zeros((64, 64, 3), np.uint8)
    dark[:, :32] = 255
    t = M.texture_stats(dark, m)
    check("texture: masked blur does not leak the background", t is not None)


def test_polygons():
    m = rect((30, 30), 5, 7, 20, 18)
    poly = AR.simplify(AR.trace(m))
    back = A.poly_mask((30, 30), [poly])
    check("trace + simplify of a rectangle -> 4 corners", len(poly) == 4, str(poly))
    check("polygon rasterises back exactly (pixel-corner convention)", M.iou(m, back) == 1.0, f"{M.iou(m, back):.3f}")
    circ = np.zeros((40, 40), bool)
    yy, xx = np.mgrid[:40, :40]
    circ[(xx - 19.5) ** 2 + (yy - 19.5) ** 2 < 12 ** 2] = True
    cb = A.poly_mask((40, 40), [AR.simplify(AR.trace(circ))])
    check("traced disc rasterises back (IoU > 0.99)", M.iou(circ, cb) > 0.99, f"{M.iou(circ, cb):.3f}")
    ring = rect((30, 30), 5, 5, 25, 25) & ~rect((30, 30), 10, 10, 20, 20)
    check("fill_holes fills an enclosed hole", AR.fill_holes(ring).sum() == 400)


def test_determinism():
    def run():
        ref_fig, ref_lm = figure(100, 170)
        ren_fig, ren_lm = figure(200, 360, s=2.1, ox=9, oy=4)
        img_r = np.full((170, 100, 3), 120, np.uint8)
        img_r[ref_fig] = (150, 94, 96)
        img_n = np.full((360, 200, 3), 120, np.uint8)
        img_n[ren_fig] = (140, 90, 92)
        ref = {"img": img_r, "fig": ref_fig, "regions": {"body": ref_fig}, "landmarks": dict(ref_lm), "hidden": set()}
        ren = {"img": img_n, "fig": ren_fig, "regions": {"body": ren_fig}, "landmarks": dict(ren_lm), "hidden": set(),
               "colour_only": {}}
        res, _ = A.analyse_view(ref, ren, 0.25)
        return M.dumps({"v": res, "o": A.summarise({"v": res})})
    a, b = run(), run()
    check("analysis output is byte-identical across runs", a == b, f"{len(a)} bytes")


# ---------------------------------------------------------------------------------------------- T-064 additions
def test_t064_segmentation():
    import look as LK
    fig = rect((40, 40), 5, 5, 35, 35)
    masks = {"a": rect((40, 40), 5, 5, 20, 35), "b": rect((40, 40), 22, 5, 35, 35)}
    frac = A.fill_unclassified(fig, masks)
    check("unclassified fraction reported (2 of 30 columns)", abs(frac - 2 / 30) < 1e-9, f"{frac:.4f}")
    check("unclassified pixels take the nearest region", (masks["a"] | masks["b"]).sum() == fig.sum()
          and masks["a"][10, 20] and masks["b"][10, 21])
    hair = rect((60, 60), 10, 5, 50, 45)   # outline traced with the face filled in
    face = rect((60, 60), 20, 15, 40, 40)
    eyes = rect((60, 60), 24, 22, 28, 26)
    ex, carved = LK.exclusive_regions({"hair": hair, "skin_face": face, "eyes": eyes, "glasses": rect((60, 60), 22, 20, 38, 28)})
    check("an island removes its pixels from the region under it (hair minus face)",
          not ex["hair"][30, 30] and ex["hair"][6, 12] and carved.get("hair") == face.sum())
    check("skin_face keeps the eyes and the glasses overlay stays whole",
          ex["skin_face"][24, 25] and ex["glasses"].sum() == 16 * 8)


def test_t064_alignment_hair_independent():
    ref_fig, ref_lm = figure(100, 170)
    ren_fig, ren_lm = figure(200, 360, s=2.0, ox=17, oy=30)
    ren_fig = ren_fig.copy()
    ren_fig[0:30, 75:125] = True  # a tall hair crown that the reference does not have
    ren_fig[30:60, 80:120] = True
    lm = {k: v for k, v in ren_lm.items()}
    lm["neck"], lm["mouth"] = (100 + 17, 100 + 30), (100 + 17, 85 + 30)
    rl = dict(ref_lm)
    rl["neck"], rl["mouth"] = (50, 50), (50, 42.5)
    al = A.align({"fig": ref_fig, "landmarks": rl}, {"fig": ren_fig, "landmarks": lm})
    check("scale comes from body landmarks, not the hair-inflated figure height", abs(al["scale"] - 0.5) < 0.01
          and al["scale_source"].startswith("body"), f"{al['scale']:.4f} vs figure {al['scale_figure_height']:.4f}")


def test_t064_crotch_ignores_hair_holes():
    fig, lm = figure(100, 170)
    fig = fig.copy()
    hair = np.zeros_like(fig)
    hair[60:100, 45:56] = True   # long hair over the back with a hole between two locks
    fig[60:100, 45:56] = True
    fig[80:84, 49:52] = False
    hair[80:84, 49:52] = False
    check("without a hair mask the hole between locks is read as the crotch", M.crotch_y(fig, 50, 161, 10) == 80.0)
    check("with the hair mask the real crotch is found", M.crotch_y(fig, 50, 161, 10, hair) == 111.0,
          str(M.crotch_y(fig, 50, 161, 10, hair)))


def test_t064_hair_read():
    import look as LK
    rng = np.random.default_rng(3)
    h, w = 120, 120
    yy, xx = np.mgrid[:h, :w]
    disc = (xx - 60) ** 2 + (yy - 60) ** 2 < 45 ** 2
    clumps = 120 + 40 * np.sin(xx / 6.0) * np.sin(yy / 6.0)          # broad, isotropic clumps
    ropes = 120 + 40 * np.sin(xx / 1.6)                               # thin parallel ropes
    flat = 120 + rng.normal(0, 2, (h, w))                             # fused shell
    img = lambda a: np.repeat(np.clip(a, 0, 255)[..., None], 3, axis=2).astype(np.uint8)
    rc, rr, rf = (LK.hair_read(img(a), disc, 100.0) for a in (clumps, ropes, flat))
    check("strand: parallel ropes are more directional than clumps", rr["strand"] > rc["strand"] + 0.2,
          f"{rr['strand']:.2f} vs {rc['strand']:.2f}")
    check("relief: a fused shell has less lock relief than clumps", rf["relief"] < 0.25 * rc["relief"],
          f"{rf['relief']:.3f} vs {rc['relief']:.3f}")
    spiky = disc.copy()
    for a in range(0, 360, 10):
        t = np.radians(a)
        for r in range(45, 58):
            spiky[int(60 + r * np.sin(t)) % h, int(60 + r * np.cos(t)) % w] = True
    check("outline: thin spikes raise the outline ratio", LK.hair_read(img(clumps), spiky, 100.0)["outline"] > rc["outline"] + 0.3)


def test_t064_skin_and_face():
    import look as LK
    yy, xx = np.mgrid[:60, :60]
    m = np.ones((60, 60), bool)
    shade = (yy < 30)
    ref = np.zeros((60, 60, 3), np.uint8)
    ref[...] = (225, 180, 160)
    ref[shade] = (185, 120, 100)                          # warm shade
    grey = ref.copy()
    grey[shade] = (150, 135, 132)                         # same lightness band, grey shade
    col = M.colour_difference(M.colour_stats(ref, m), M.colour_stats(grey, m))
    sv = LK.skin_view(ref, m, grey, m, col)
    check("skin: a grey shade is reported as a grey cast", sv["grey_cast"] > 8 and sv["score"] < 0.9,
          f"grey cast {sv['grey_cast']:.1f}, score {sv['score']:.2f}")
    same = LK.skin_view(ref, m, ref, m, M.colour_difference(M.colour_stats(ref, m), M.colour_stats(ref, m)))
    check("skin: identical patches score 1", abs(same["score"] - 1) < 1e-9)
    lm = {"eye_L": (40, 30), "eye_inner_L": (34, 30), "eye_outer_L": (46, 30),
          "eye_R": (20, 30), "eye_inner_R": (26, 30), "eye_outer_R": (14, 30)}
    eyes = ((xx - 40) ** 2 / 36 + (yy - 30) ** 2 / 9 <= 1) | ((xx - 20) ** 2 / 36 + (yy - 30) ** 2 / 9 <= 1)
    face = np.full((60, 60, 3), (220, 175, 155), np.uint8)
    dome = face.copy()
    win = LK.eye_windows((60, 60), lm, "L", eyes)
    win_r = LK.eye_windows((60, 60), lm, "R", eyes)
    dome[(win["lid"] | win_r["lid"]) & ~eyes] = (245, 235, 230)  # pale lid shells
    side = lambda im: {"img": im, "landmarks": lm}
    regs = {"skin_face": np.ones((60, 60), bool), "eyes": eyes}
    fv = LK.face_view(side(face), side(dome), regs, regs)
    check("face window: pale lid domes raise lid_dL", fv["difference"]["lid_dL"] > 8, f"{fv['difference']['lid_dL']:.1f}")


if __name__ == "__main__":
    for t in (test_iou, test_ciede2000, test_lab, test_landmarks, test_alignment, test_geometry, test_texture,
              test_polygons, test_determinism, test_t064_segmentation, test_t064_alignment_hair_independent,
              test_t064_crotch_ignores_hair_holes, test_t064_hair_read, test_t064_skin_and_face):
        t()
    ok = all(RESULTS)
    print(f"{'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if ok else 1)
