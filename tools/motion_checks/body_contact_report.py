"""T-191: worst character-character contacts from body_contact.cpp traces (plush.body_contact/1).

    python3 tools/motion_checks/body_contact_report.py <label>=<contact.json>[@A-B] ... [--json out.json] [--top N]
        [--limit-mm 5]

Per trace and pair: the worst capsule gap and the worst mesh gap (mm; negative = depth inside), their frame and
parts, and how many frames go deeper than --limit-mm. Then the --top worst cases over all traces: one per run of
consecutive frames deeper than the limit (pair, parts at the deepest frame, frame range, deepest frame, depth).
hand-hand contacts are listed apart ("by design" candidates: a hand-over's shared hold). @A-B restricts a trace to
its rendered frames."""
import argparse
import json
import sys


def runs(frames, vals, limit):
    out, cur = [], []
    for i, v in enumerate(vals):
        if v < limit:
            cur.append(i)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def hand_hand(a, b):
    return a.startswith("hand") and b.startswith("hand")


def analyse(label, path, rng, limit_mm):
    t = json.load(open(path))
    fr = t["frames"]
    keep = [i for i, f in enumerate(fr) if rng is None or rng[0] <= f <= rng[1]]
    rows, cases = [], []
    for p in t["pairs"]:
        cg = [p["capsule"]["gap"][i] * 1000 for i in keep]
        mg = [p["mesh"]["gap"][i] * 1000 for i in keep]
        pa = [p["capsule"]["partA"][i] for i in keep]
        pb = [p["capsule"]["partB"][i] for i in keep]
        mp = [(p["mesh"]["who"][i], p["mesh"]["part"][i], p["mesh"]["in"][i]) for i in keep]
        hg = [p["head_gap"][i] * 1000 for i in keep]
        fk = [fr[i] for i in keep]
        ic, im = min(range(len(cg)), key=cg.__getitem__), min(range(len(mg)), key=mg.__getitem__)
        rows.append({"trace": label, "pair": f"{p['a']}-{p['b']}",
                     "capsule_mm": round(cg[ic], 1), "capsule_frame": fk[ic], "capsule_parts": f"{pa[ic]}/{pb[ic]}",
                     "capsule_frames_over": sum(v < -limit_mm for v in cg),
                     "mesh_mm": round(mg[im], 1) if mg[im] < 1e5 else None, "mesh_frame": fk[im],
                     "mesh_parts": f"{mp[im][0]}.{mp[im][1]} in {mp[im][2]}",
                     "mesh_frames_over": sum(v < -limit_mm for v in mg),
                     "head_gap_min_mm": round(min(hg), 1), "frames": len(fk)})
        for r in runs(fk, cg, -limit_mm):
            k = min(r, key=cg.__getitem__)
            cases.append({"trace": label, "pair": f"{p['a']}-{p['b']}", "parts": f"{pa[k]}/{pb[k]}",
                          "frames": [fk[r[0]], fk[r[-1]]], "frame": fk[k], "capsule_mm": round(cg[k], 1),
                          "mesh_mm": round(mg[k], 1), "hand_hand": hand_hand(pa[k], pb[k])})
    return rows, cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--limit-mm", type=float, default=5.0)
    a = ap.parse_args()
    rows, cases = [], []
    for spec in a.traces:
        label, rest = spec.split("=", 1)
        rng = None
        if "@" in rest:
            rest, r = rest.rsplit("@", 1)
            rng = tuple(int(x) for x in r.split("-"))
        r, c = analyse(label, rest, rng, a.limit_mm)
        rows += r
        cases += c
    cases.sort(key=lambda c: c["capsule_mm"])
    w = sys.stdout.write
    w(f"| trace | pair | worst capsule mm (frame, parts) | frames < -{a.limit_mm:g} | worst mesh mm (frame, vertex in) "
      f"| frames < -{a.limit_mm:g} | head shell min mm |\n|---|---|---|---|---|---|---|\n")
    for r in rows:
        w(f"| {r['trace']} | {r['pair']} | {r['capsule_mm']} (f{r['capsule_frame']}, {r['capsule_parts']}) | "
          f"{r['capsule_frames_over']}/{r['frames']} | {r['mesh_mm']} (f{r['mesh_frame']}, {r['mesh_parts']}) | "
          f"{r['mesh_frames_over']}/{r['frames']} | {r['head_gap_min_mm']} |\n")
    for title, sel in (("worst cases", [c for c in cases if not c["hand_hand"]]),
                       ("hand-hand (by-design candidates)", [c for c in cases if c["hand_hand"]])):
        w(f"\n{title} (runs deeper than {a.limit_mm:g} mm, capsule measure)\n\n"
          "| trace | pair | parts | frames | deepest frame | capsule mm | mesh mm |\n|---|---|---|---|---|---|---|\n")
        for c in sel[:a.top]:
            w(f"| {c['trace']} | {c['pair']} | {c['parts']} | {c['frames'][0]}-{c['frames'][1]} | {c['frame']} | "
              f"{c['capsule_mm']} | {c['mesh_mm']} |\n")
    if a.json:
        json.dump({"format": "plush.body_contact_report", "version": 1, "limit_mm": a.limit_mm, "pairs": rows,
                   "cases": cases}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
