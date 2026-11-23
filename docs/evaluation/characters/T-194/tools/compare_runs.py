"""T-194: where run B leaves hair deeper than run A (same shot, bake and frames), per character and surface.

    python3 compare_runs.py <A.m.json> <B.m.json> [--min-mm=1] [--json=out.json]

A row counts when the surface is deeper than --min-mm in B and B is deeper than A by more than --min-mm at that frame
(a surface missing in A has depth 0). Grouped as "own skin (nape / fold)" (own body_skin), "own other" (own garments,
ears, hands), "neighbour", "prop". Used for the depth cost of static_move_fade_m (A = the full run without it)."""
import json
import sys

a_p, b_p = sys.argv[1:3]
MIN = float(next((x.split("=", 1)[1] for x in sys.argv[3:] if x.startswith("--min-mm=")), "1"))
OUT = next((x.split("=", 1)[1] for x in sys.argv[3:] if x.startswith("--json=")), None)
A = {r["frame"]: r for r in json.load(open(a_p))["rows"]}
B = {r["frame"]: r for r in json.load(open(b_p))["rows"]}


def group(n, k):
    part = k.split(" > ", 1)[1]
    if part.endswith(":glasses") or (n.startswith("boy") and part.startswith("own:body_skin")):
        return None
    if part.startswith("own:body_skin"):
        return "own skin (nape / fold)"
    if part.startswith("own:"):
        return "own other"
    if part.startswith(("prop", "box")):
        return "prop"
    return "neighbour"


res = {}
for f in sorted(B):
    if f not in A:
        continue
    for n, c in B[f]["chars"].items():
        ca = A[f]["chars"].get(n, {"surfaces": {}})["surfaces"]
        for k, (cnt, mm) in c["surfaces"].items():
            g = group(n, k)
            old = ca.get(k, [0, 0.0])[1]
            if g and mm > MIN and mm - old > MIN:
                e = res.setdefault(g, {}).setdefault(f"{n} {k}", {"frames": [], "max_mm": 0.0, "max_added_mm": 0.0})
                e["frames"].append(f)
                e["max_mm"] = max(e["max_mm"], mm)
                e["max_added_mm"] = round(max(e["max_added_mm"], mm - old), 2)
for g, d in res.items():
    print(g)
    for k, e in sorted(d.items()):
        fr = e["frames"]
        print(f"  {k}: {len(fr)} frames ({fr[0]}-{fr[-1]}), max {e['max_mm']} mm, deeper by up to {e['max_added_mm']} mm")
if not res:
    print("B is nowhere deeper than A")
if OUT:
    json.dump(res, open(OUT, "w"), indent=1)
