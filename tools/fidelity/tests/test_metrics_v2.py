"""Unit tests of the fidelity score v2 metric functions (T-153) on synthetic images; numpy only, no Blender.

    python3 tools/fidelity/tests/test_metrics_v2.py

Prints one line per check and ALL PASS / FAILED."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
import metrics_v2 as V  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RESULTS = []
SKIN, PALE, DARK = (230, 180, 160), (245, 235, 230), (90, 30, 40)


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def canvas(colour=SKIN, h=60, w=80):
    return np.tile(np.array(colour, np.uint8), (h, w, 1))


def main():
    img = canvas()
    r = V.lid_skin_contrast(img, [10, 10, 30, 30], [40, 10, 60, 30])
    check("lid equal to skin scores 1", abs(r["score"] - 1) < 1e-9 and r["de00"] < 1e-6)
    img[10:30, 10:30] = PALE
    r2 = V.lid_skin_contrast(img, [10, 10, 30, 30], [40, 10, 60, 30])
    check("pale lid scores lower, lighter dL", r2["score"] < 0.8 and r2["dL"] > 0, f"{r2['score']:.3f}")

    img = canvas()
    check("no shelf -> fraction 0", V.shelf_fraction(img, [10, 40, 50, 50], [10, 0, 50, 10])["fraction"] == 0)
    img[40:45, 10:50] = PALE
    s = V.shelf_fraction(img, [10, 40, 50, 50], [10, 0, 50, 10])
    check("half-pale band -> fraction 0.5, score 0", abs(s["fraction"] - 0.5) < 1e-9 and s["score"] == 0)

    closed, smile, frown, opened = canvas(), canvas(), canvas(), canvas()
    closed[30, 20:60] = DARK
    for i, x in enumerate(range(20, 60)):
        d = int(round(((x - 40) / 20) ** 2 * 8))
        smile[38 - d, x] = DARK
        frown[30 + d, x] = DARK
    opened[25:40, 20:60] = DARK
    box = [0, 0, 80, 60]
    mc, ms, mf, mo = (V.mouth_shape(i, box) for i in (closed, smile, frown, opened))
    check("straight mouth: curve ~0", abs(mc["curve"]) < 0.02, f"{mc['curve']:.3f}")
    check("smile curve > 0 > frown curve", ms["curve"] > 0.05 and mf["curve"] < -0.05,
          f"{ms['curve']:.3f} / {mf['curve']:.3f}")
    check("open mouth: larger dark fraction", mo["open"] > 0.1 > mc["open"], f"{mo['open']:.3f}")
    check("mouth_match self = 1", V.mouth_match(ms, ms)["score"] == 1.0)
    check("open vs closed mismatch < 0.6", V.mouth_match(mc, mo)["score"] < 0.6)

    t = {"a": {"value": 1.0, "tolerance": 0.1}, "b": {"value": 0.0, "tolerance": 0.1}}
    e = V.eye_shape_score({"a": 1.05, "b": 0.3}, t)
    check("eye shape: in band 1, 2 tol outside 0", e["per_key"]["a"] == 1.0 and abs(e["per_key"]["b"]) < 1e-9
          and e["in_band"] == 0.5)
    check("eye shape: no keys -> None", V.eye_shape_score({}, t) is None)

    sub = {k: 0.5 for k in V.V1_WEIGHTS}
    check("reweighted constant subscores = 50", abs(V.reweighted(sub) - 50) < 1e-9)
    check("v2 weights sum to 1, silhouette 0.13, face 0.12",
          abs(sum(V.V2_WEIGHTS.values()) - 1) < 1e-9 and V.V2_WEIGHTS["silhouette"] == 0.13
          and V.V2_WEIGHTS["face"] == 0.12)
    check("v2_total blend 80/20", abs(V.v2_total(sub, 1.0) - (0.8 * 50 + 20)) < 1e-9 and V.v2_total(sub) == 50)
    p = os.path.join(ROOT, "docs/evaluation/characters/T-094/fidelity/girl_auburn_bun_glasses/fidelity.json")
    if os.path.exists(p):
        o = json.load(open(p))["overall"]
        check("v1 weights reproduce archived v1 score", abs(V.reweighted(o["subscores"], V.V1_WEIGHTS) - o["score"]) < 1e-3)

    rng = np.random.default_rng(0)
    stripes = np.zeros((64, 64, 3), np.uint8)
    stripes[:, ::4] = 200
    stripes[:, 1::4] = 200
    stripes = np.clip(stripes.astype(int) + rng.integers(0, 20, stripes.shape), 0, 255).astype(np.uint8)
    o = V.orientation(V.M.luma(stripes))
    check("vertical stripes: coherent, horizontal gradient", o["coherence"] > 0.8 and min(o["angle_deg"], 180 - o["angle_deg"]) < 10,
          f"{o['angle_deg']:.1f} {o['coherence']:.2f}")
    lp = V.local_patch(stripes, [0, 0, 64, 64], stripes, [0, 0, 64, 64])
    check("local patch self-compare = 1", abs(lp["score"] - 1) < 1e-9)
    rot = np.ascontiguousarray(stripes.transpose(1, 0, 2))
    lr = V.local_patch(stripes, [0, 0, 64, 64], rot, [0, 0, 64, 64])
    check("local patch: rotated strands lose direction", lr["parts"]["direction"] < 0.6 and lr["score"] < 1)

    ok = all(RESULTS)
    print(f"{'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
