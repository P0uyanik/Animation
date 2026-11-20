"""T-153: evaluate fidelity score v2 against past owner decisions, from archived data only (no renders).

    python3 tools/fidelity/v2/evaluate.py [--out docs/evaluation/process/T-153]

Reads docs/evaluation/process/T-129/calibration.csv (before/after fidelity.json pairs), the T-122 expression sheets
(face states, data/face_states_T122.json), T-150 eye-shape traces and targets, and the T-049 contact sheet
(local hair, data/hair_local_T049.json). Writes evaluation.json and calibration_v2.csv. Never changes v1."""
import argparse
import csv
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import metrics_v2 as V  # noqa: E402

M = V.M
CAL = "docs/evaluation/process/T-129/calibration.csv"
T150 = "docs/evaluation/characters/T-150"


def load_img(p):
    return np.asarray(Image.open(os.path.join(ROOT, p)).convert("RGB"))


def shift(box, x0, y0):
    return [box[0] + x0, box[1] + y0, box[2] + x0, box[3] + y0]


def face_states(cfg):
    """{character: {"before"|"after": {lid, shelf, mouths, score}}} from the expression sheets."""
    P = cfg["panel"]
    out = {}
    for cid, c in cfg["characters"].items():
        img = load_img(c["sheet"])
        res = {}
        for side, col in (("before", "current"), ("after", "candidate")):
            def at(row, box, column=col):
                return shift(box, P["x0"][column], P["row_y0"] + row * P["size"])
            r = {"version": c[side]}
            lid = c["lid"]
            r["lid"] = V.lid_skin_contrast(img, at(lid["row"], lid["lid"]), at(lid["row"], lid["skin"]))
            if c.get("shelf"):
                s = c["shelf"]
                r["shelf"] = V.shelf_fraction(img, at(s["row"], s["band"]), at(s["row"], s["skin"]))
            r["mouths"] = {}
            for m in c["mouths"]:
                ren = V.mouth_shape(img, at(m["row"], m["render"]))
                ref = V.mouth_shape(img, at(m["row"], m["reference"], "reference"))
                r["mouths"][m["label"]] = dict(V.mouth_match(ren, ref), render=ren, reference=ref)
            parts = {"lid": r["lid"]["score"], "shelf": r.get("shelf", {}).get("score"),
                     "expressions": M.mean([v["score"] for v in r["mouths"].values()])}
            r["parts"] = parts
            r["score"] = V.face_state_score(parts)
            res[side] = r
        out[cid] = res
    return out


def eye_shape():
    """T-150 front targets applied to traced front views (auburn only; T-150 traced only the 0.13.0 candidate)."""
    tg = json.load(open(os.path.join(ROOT, T150, "targets.json")))["characters"]
    rows = list(csv.DictReader(open(os.path.join(ROOT, T150, "measures.csv"), encoding="utf-8-sig")))
    out = {}
    for r in rows:
        if r["role"] != "current" or r["condition"] != "front" or r["character"] not in tg:
            continue
        t = tg[r["character"]]["front"]
        m = {k: float(r[k]) for k in t if r.get(k) not in (None, "")}
        out.setdefault(f"{r['character']} {r['view']}", []).append(V.eye_shape_score(m, t))
    return {k: {"score": M.mean(x["score"] for x in v), "in_band": M.mean(x["in_band"] for x in v), "eyes": len(v)}
            for k, v in out.items()}


def hair_local(cfg):
    img = load_img(cfg["sheet"])
    b = cfg["boxes"]
    return {alt: {reg: V.local_patch(img, b["reference"][reg], img, box) for reg, box in b[alt].items()}
            for alt in b if alt != "reference"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "evaluation", "process", "T-153"))
    a = ap.parse_args()
    fs = face_states(json.load(open(os.path.join(HERE, "data", "face_states_T122.json"))))
    hl = hair_local(json.load(open(os.path.join(HERE, "data", "hair_local_T049.json"))))
    eyes = eye_shape()
    rows, table = list(csv.DictReader(open(os.path.join(ROOT, CAL)))), []
    for r in rows:
        if not (r["before_json"] and r["after_json"]):
            continue
        b, f = (json.load(open(os.path.join(ROOT, r[k])))["overall"] for k in ("before_json", "after_json"))
        v1 = f["score"] - b["score"]
        base = V.reweighted(f["subscores"]) - V.reweighted(b["subscores"])
        cid = {"boy": "boy_yellow_hoodie", "girl": "girl_auburn_bun_glasses"}[r["character"]]
        st = fs.get(cid) if r["task"] == "T-122" else None
        v2 = (V.v2_total(f["subscores"], st["after"]["score"]) - V.v2_total(b["subscores"], st["before"]["score"])
              if st else base)
        note = ""
        if r["task"] == "T-049" and r["character"] == "girl":
            h = {k: M.mean(x["score"] for x in hl[k].values()) for k in hl}
            note = f"hair_local {r['before']} {h[r['before']]:.3f} -> C {h['C']:.3f}"
        table.append({"task": r["task"], "character": r["character"], "pair": f"{r['before']} -> {r['after']}",
                      "cohort": r["cohort"], "preferred": "after",
                      "v1_delta": round(v1, 4), "v1_agree": v1 > 0,
                      "v2_base_delta": round(base, 4), "v2_face_states": bool(st),
                      "v2_delta": round(v2, 4), "v2_agree": v2 > 0, "local_note": note})
    n = len(table)
    summary = {"pairs": n, "v1_agree": sum(t["v1_agree"] for t in table), "v2_agree": sum(t["v2_agree"] for t in table)}
    for coh in sorted({t["cohort"] for t in table}):
        sub = [t for t in table if t["cohort"] == coh]
        summary[coh] = {"pairs": len(sub), "v1_agree": sum(t["v1_agree"] for t in sub),
                        "v2_agree": sum(t["v2_agree"] for t in sub)}
    doc = {"schema": "plush-studio.fidelity-v2-evaluation/1", "weights_v1": V.V1_WEIGHTS, "weights_v2": V.V2_WEIGHTS,
           "face_state_blend": V.FACE_STATE_BLEND, "summary": summary, "pairs": table, "face_states_T122": fs,
           "eye_shape_T150": eyes, "hair_local_T049_girl": hl}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "evaluation.json"), "w") as fh:
        fh.write(M.dumps(doc))
    with open(os.path.join(a.out, "calibration_v2.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    print(json.dumps(M.rounded(summary), indent=1))


if __name__ == "__main__":
    main()
