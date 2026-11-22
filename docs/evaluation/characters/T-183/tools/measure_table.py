"""T-183: per-surface table of measure_body.py results (frames deeper than the limit, max depth, most vertices in one
frame), one column group per measure.

    python3 measure_table.py <label>=<measure.json> [<label>=<measure.json> ...] [--pairs=N]

Surfaces are the solid parts grouped by name (skin, ears, hands, blouse, vest, ...). --pairs=N also lists the N worst
hair part > surface pairs of the last measure."""
import json
import re
import sys


def surface(part):
    if part.startswith("garment."):
        s = part.split(".")
        return s[1] + (" cuffs" if "cuff" in part and s[1] == "blouse" else "")
    return {"body_skin": "skin"}.get(part, re.sub(r"\.[LR]$", "s", part))


def main():
    runs = [a.split("=", 1) for a in sys.argv[1:] if not a.startswith("--")]
    npairs = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--pairs=")), 0)
    table, heads = {}, []
    for label, path in runs:
        d = json.load(open(path, encoding="utf-8"))
        s = d["summary"]
        heads.append(f"{label}: {s['frames_deeper_than_limit']} of {s['frames_measured']} frames, max {s['max_depth_mm']} mm, "
                     f"most vertices in one frame {s['max_vertices']}")
        per = {}
        for fr in d["frames"]:
            seen = {}
            for pair, (mm, n) in fr["by_pair"].items():
                k = surface(pair.split(">")[1])
                a = seen.setdefault(k, [0.0, 0])
                a[0], a[1] = max(a[0], mm), a[1] + n
            for k, (mm, n) in seen.items():
                a = per.setdefault(k, [0, 0.0, 0])
                a[0], a[1], a[2] = a[0] + 1, max(a[1], mm), max(a[2], n)
        for k, v in per.items():
            table.setdefault(k, {})[label] = v
    print("\n".join(heads))
    print("| Surface | " + " | ".join(f"{lb}: frames, max mm, vertices" for lb, _ in runs) + " |")
    print("|---|" + "---|" * len(runs))
    for k in sorted(table, key=lambda k: -max(v[1] for v in table[k].values())):
        cells = [("{} , {:.1f} , {}".format(*table[k][lb]) if lb in table[k] else "0") for lb, _ in runs]
        print(f"| {k} | " + " | ".join(cells) + " |")
    if npairs:
        pairs = sorted(d["summary"]["pairs"].items(), key=lambda kv: -kv[1]["max_mm"])[:npairs]
        for k, v in pairs:
            print(f"  {k}: {json.dumps(v)}")


if __name__ == "__main__":
    main()
