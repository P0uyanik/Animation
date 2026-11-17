"""Integration batch 1: is T-027's automatic idle active? Compares a bake with a bake of the same shot with
"autoIdle": false (python3). Per character and role, the largest world-position difference of the bone origin
(translation column of its skinning matrix applied to the rest head is not needed: the column suffices for a
presence check), plus the trunk's own motion range in both bakes.

    python3 docs/evaluation/integration/batch1/measure_auto_idle.py --with <bake.json> --without <bake.json>"""
import argparse
import json

ROLES = ("hips", "spine", "chest", "neck", "head", "upperArm.L", "upperArm.R", "hand.L", "hand.R")


def series(bake):
    out = {}
    for c in bake["characters"]:
        idx = {r: c["bones"].index(r) for r in ROLES if r in c["bones"]}
        out[c["name"]] = {r: [fd["characters"][c["name"]]["skin"][i * 16:(i + 1) * 16] for fd in bake["frame_data"]] for r, i in idx.items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with", dest="w", required=True)
    ap.add_argument("--without", required=True)
    a = ap.parse_args()
    w, wo = series(json.load(open(a.w))), series(json.load(open(a.without)))
    rep = {}
    for ch in w:
        rep[ch] = {}
        for r in w[ch]:
            diff = max(max(abs(x - y) for x, y in zip(m1, m2)) for m1, m2 in zip(w[ch][r], wo[ch][r]))
            rng = lambda s: max(max(m[k] for m in s) - min(m[k] for m in s) for k in range(16))  # noqa: E731
            rep[ch][r] = {"max_skin_matrix_diff": round(diff, 4), "range_with": round(rng(w[ch][r]), 4),
                          "range_without": round(rng(wo[ch][r]), 4)}
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
