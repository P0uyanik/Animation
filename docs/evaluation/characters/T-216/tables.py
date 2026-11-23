#!/usr/bin/env python3
"""T-216 tables: per-measure z and result for each reference view, columns = the given measure runs.

    python3 docs/evaluation/characters/T-216/tables.py <out.csv> <label>=<measures.json> [...]

Prints the summary table (within / scored, mean |z|, per view and group) as Markdown."""
import csv
import json
import sys


def main():
    out, runs = sys.argv[1], [a.split("=", 1) for a in sys.argv[2:]]
    data = {n: json.load(open(p)) for n, p in runs}
    rows = {}
    for n, r in data.items():
        for v in r["views"]:
            if not v.get("view"):
                continue
            for m in v["rows"]:
                if m.get("z") is None:
                    continue
                key = (v["view"], m["group"], m["measure"])
                rows.setdefault(key, {"reference": m["reference"], "tolerance": m["tolerance"]})
                rows[key][n] = (m["current"], m["z"], m["result"])
    hold = next(iter(data.values()))["holdout"]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["view", "held_out", "group", "measure", "reference", "tolerance"] +
                   [f"{n} {c}" for n in data for c in ("value", "z", "result")])
        for (view, g, m), d in sorted(rows.items()):
            w.writerow([view, view == hold, g, m, d["reference"], d["tolerance"]] +
                       [x for n in data for x in (d.get(n, ("", "", ""))[0], round(d[n][1], 3) if n in d else "",
                                                  d.get(n, ("", "", ""))[2])])
    print("| View / group | " + " | ".join(data) + " |")
    print("|---|" + "---|" * len(data))
    for key in next(iter(data.values()))["summary"]:
        cells = []
        for n, r in data.items():
            s = r["summary"][key]
            cells.append(f"{s['within']} / {s['scored']} ({s['mean_abs_z']:.2f})")
        print(f"| {key}{' (held out)' if key.startswith(hold) else ''} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
