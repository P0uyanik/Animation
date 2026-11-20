#!/usr/bin/env python3
"""T-156: measured vs T-150 target tables (markdown) from eye_measure.py outputs.

    python3 docs/evaluation/characters/T-156/report.py <targets.json> <character key> <view key> <before.json> <after.json>

targets.json = docs/evaluation/characters/T-150/targets.json (main); character key "auburn" | "white_haired"; view key
"front" | "oblique_near+oblique_far" (image_left = near, image_right = far at a negative yaw). A value is "in" when
|value - target| <= tolerance; out-of-band values are bold."""
import json
import sys


def main():
    tj, who, view, before, after = sys.argv[1:6]
    T = json.load(open(tj))["characters"][who]
    B, A = (json.load(open(p))["eyes"] for p in (before, after))
    views = view.split("+")
    eyes = ["image_left", "image_right"]
    tv = {e: T[views[min(i, len(views) - 1)]] for i, e in enumerate(eyes)}
    tcols = eyes if len(views) > 1 else eyes[:1]
    print("| metric | " + " | ".join(f"target {v}" for v in views) +
          " | before left | before right | after left | after right |")
    print("|---|" + "---|" * (4 + len(tcols)))
    count = {"before": 0, "after": 0}
    for k in tv[eyes[0]]:
        tcells = [f"{tv[e][k]['value']:.3f} ±{tv[e][k]['tolerance']:.3f}" for e in tcols]
        cells = []
        for name, M in (("before", B), ("after", A)):
            for e in eyes:
                v, t = M[e]["metrics"][k], tv[e][k]
                ok = abs(v - t["value"]) <= t["tolerance"]
                count[name] += ok
                cells.append(f"{v:.3f}" if ok else f"**{v:.3f}**")
        print(f"| {k} | " + " | ".join(tcells + cells) + " |")
    n = 2 * len(tv[eyes[0]])
    print(f"\nIn tolerance: before {count['before']}/{n}, after {count['after']}/{n}. left / right = image left / right "
          "(the viewer's); bold = out of band.")


if __name__ == "__main__":
    main()
