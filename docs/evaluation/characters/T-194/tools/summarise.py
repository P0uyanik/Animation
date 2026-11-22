"""T-194: off / on summary of measure_eval.py results for one shot and bake.

    python3 summarise.py <name> <bake.json> <off.m.json> <on.m.json> <on shot_render.json> [--json=out.json]

Penetration = the deepest hair vertex per frame (> 1 mm counts), split into ALL measured frames, CALM frames (not a
source-body snap frame +-1; T-183 `tools/snaps.py` on the same bake, imported read-only from the T-183 worktree,
T183_ROOT, default /home/user/t183wt) and SNAP frames. Listed apart and not in those columns: hair against glasses
(glasses are not colliders, T-183 SKIP list), the boy's rigid hair inside his own head skin (T-191 staging), and
"staging": hair deeper than 4 mm in ANOTHER character's body skin (heads / bodies overlap, T-191), listed per frame.
Pops: per frame and character, the largest vertex jump f-step -> f (measure_eval), on minus off: frames where the
push-out adds more than 5 mm, and the largest addition. Cost: shot_render's hair_pushout timing."""
import json
import os
import sys

T183 = os.environ.get("T183_ROOT", "/home/user/t183c2")
sys.path.insert(0, os.path.join(T183, "docs", "evaluation", "characters", "T-183", "tools"))
import snaps  # noqa: E402

name, bake, off_p, on_p, sr_p = sys.argv[1:6]
OUT = next((a.split("=", 1)[1] for a in sys.argv[6:] if a.startswith("--json=")), None)
snap = sorted({f for c in snaps.snap_frames(bake).values() for f in c})
near = {f + d for f in snap for d in (-1, 0, 1)}


STAGING_MM = 4.0  # hair_pushout other_skin_fade_m[0]: deeper in a neighbour's skin = bodies overlap (T-191)


def apart(char, key, mm):
    part = key.split(" > ", 1)[1]
    if part.endswith(":glasses"):
        return "glasses"
    if char.startswith("boy") and part.startswith("own:body_skin"):
        return "boy_head"
    if not part.startswith(("own:", "prop", "box")) and part.split(":", 1)[-1].startswith("body_skin") \
            and mm > STAGING_MM:
        return "staging"
    return None


def table(path):
    d = json.load(open(path))
    res = {"cols": {}, "apart": {}, "jump": {}}
    for r in d["rows"]:
        f = r["frame"]
        for n, c in r["chars"].items():
            res["jump"].setdefault(n, {})[f] = c["jump_mm"]
            worst, worst_key = 0.0, None
            seen = set()
            for k, (cnt, mm) in c["surfaces"].items():
                a = apart(n, k, mm)
                if a:
                    s = res["apart"].setdefault(a, {"frames": 0, "max_mm": 0.0, "list": []})
                    if mm > 1.0 and a not in seen:
                        s["frames"] += 1
                        seen.add(a)
                    if a == "staging" and mm > 1.0:
                        s["list"].append([f, n, k, mm])
                    s["max_mm"] = max(s["max_mm"], mm)
                    continue
                if mm > worst:
                    worst, worst_key = mm, k
            for col in ("all", "snap" if f in near else "calm"):
                s = res["cols"].setdefault(col, {"frames": 0, "over": 0, "max_mm": 0.0, "worst": None})
                s["frames"] += 1
                if worst > 1.0:
                    s["over"] += 1
                if worst > s["max_mm"]:
                    s["max_mm"], s["worst"] = worst, f"f{f} {n[:6]} {worst_key}"
    return res, d


off, d_off = table(off_p)
on, d_on = table(on_p)
pops = {"frames_over_5mm": 0, "max_added_mm": 0.0, "where": None}
for n, fr in on["jump"].items():
    for f, j in fr.items():
        add = j - off["jump"].get(n, {}).get(f, 0.0)
        if add > 5.0:
            pops["frames_over_5mm"] += 1
        if add > pops["max_added_mm"]:
            pops["max_added_mm"], pops["where"] = round(add, 2), f"f{f} {n[:6]}"
sr = json.load(open(sr_p))
hp = sr.get("hair_pushout", {}).get("timing", {})
nf = d_on["frames"][1] - d_on["frames"][0] + 1
cost = {"setup_s": hp.get("setup_s"), "stage_a_s_per_frame": round(hp.get("chains_s", 0) / max(1, nf), 2)}
summary = {"name": name, "snap_frames": snap, "off": off["cols"], "on": on["cols"], "apart_off": off["apart"],
           "apart_on": on["apart"], "pops": pops, "cost": cost, "sha256_on": d_on["sha256"], "step": d_on["step"]}
print(f"{name}: snaps {snap}")
for col in ("all", "calm", "snap"):
    a, b = off["cols"].get(col, {}), on["cols"].get(col, {})
    print(f"  {col:5s} frames>1mm off {a.get('over', 0)}/{a.get('frames', 0)} max {a.get('max_mm', 0)} | "
          f"on {b.get('over', 0)}/{b.get('frames', 0)} max {b.get('max_mm', 0)} ({b.get('worst')})")
short = lambda ap: {k: {"frames": v["frames"], "max_mm": v["max_mm"]} for k, v in ap.items()}  # noqa: E731
print(f"  apart off {short(off['apart'])} on {short(on['apart'])}")


def surfaces(d):
    out = {}
    for r in d["rows"]:
        for n, c in r["chars"].items():
            for k, (cnt, mm) in c["surfaces"].items():
                if mm > 1.0 and not apart(n, k, mm):
                    e = out.setdefault((n, k), [0, 0.0])
                    e[0] += 1
                    e[1] = max(e[1], mm)
    return out


so, sn = surfaces(d_off), surfaces(d_on)
new = {f"{n} {k}": v for (n, k), v in sn.items() if (n, k) not in so}
summary["new_surfaces_on"] = new
print(f"  new surfaces with the push-out (frames, max mm): {new}")
print(f"  pops {pops}  cost {cost}")


if OUT:
    json.dump(summary, open(OUT, "w"), indent=1)
