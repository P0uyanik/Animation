"""T-219 step 6: push-out ON vs OFF, current vs candidate, from T-194 measure_eval.py results (plain Python).

    python3 docs/evaluation/characters/T-219/pushout_compare.py <cur_on> <cur_off> <cand_on> <cand_off> [--json out]

Per character: pops = frames where push-out adds more than 5 mm to the largest hair-vertex jump (ON jump - OFF jump,
T-194 rule) and the largest addition; depth = deepest hair vertex over the measured frames and the frames with any
vertex deeper than 1 mm (all surfaces, staging overlaps with other characters included, as measured)."""
import json
import sys


def load(p):
    d = json.load(open(p))
    return d, {r["frame"]: r["chars"] for r in d["rows"]}


def depth(rows, n):
    mx, over = 0.0, 0
    for ch in rows.values():
        s = ch.get(n, {}).get("surfaces", {})
        if s:
            over += 1
            mx = max(mx, max(v[1] for v in s.values()))
    return round(mx, 1), over


def compare(on_p, off_p):
    on, ron = load(on_p)
    off, roff = load(off_p)
    out = {}
    for n in sorted(on["summary"]):
        adds = [(f, ron[f][n]["jump_mm"] - roff[f][n]["jump_mm"]) for f in sorted(ron) if f in roff and n in roff[f]]
        pops = [(f, round(a, 1)) for f, a in adds if a > 5.0]
        don, oon = depth(ron, n)
        doff, ooff = depth(roff, n)
        out[n] = {"frames": len(adds), "pops_gt5mm": len(pops), "max_added_mm": round(max(a for _, a in adds), 1),
                  "pop_frames": pops[:20], "max_depth_on_mm": don, "frames_gt1mm_on": oon,
                  "max_depth_off_mm": doff, "frames_gt1mm_off": ooff}
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    res = {"current": compare(a[0], a[1]), "candidate": compare(a[2], a[3]),
           "inputs": {"current_on": a[0], "current_off": a[1], "candidate_on": a[2], "candidate_off": a[3]}}
    if "--json" in a:
        json.dump(res, open(a[a.index("--json") + 1], "w"), indent=1)
    print("| run | character | pops >5 mm | max added | max depth ON | fr >1 mm ON | max depth OFF | fr >1 mm OFF |")
    for run in ("current", "candidate"):
        for n, r in res[run].items():
            print(f"| {run} | {n} | {r['pops_gt5mm']}/{r['frames']} | {r['max_added_mm']} | {r['max_depth_on_mm']} | "
                  f"{r['frames_gt1mm_on']} | {r['max_depth_off_mm']} | {r['frames_gt1mm_off']} |")
