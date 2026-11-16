"""Integration batch 1: secondary-motion (T-021) measurements from engine bakes (python3, no Blender).

    python3 docs/evaluation/integration/batch1/measure_dynamics.py --package <girl pkg dir> --on <bake.json> \
        [--off <bake.json>] [--character girl] [--out <json>]

Chain tip = skinning matrix of the chain's last bone applied to the chain's rest tip (package "dynamics" block, engine
axes). With --off: per chain, the tip offset ON vs OFF in mm (the T-021 README table: max, frames 1, 7, ..., 43, the
median of the chain maxima). Without it, the tip's displacement from the head-carried rest tip (shows that the chains
move against the head)."""
import argparse
import json
import statistics


def xf(m, p):
    return [m[0 + r] * p[0] + m[4 + r] * p[1] + m[8 + r] * p[2] + m[12 + r] for r in range(3)]


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def tips(bake, ch_name, chains):
    ci = next(i for i, c in enumerate(bake["characters"]) if c["name"] == ch_name)
    bones = bake["characters"][ci]["bones"]
    out = {c["name"]: [] for c in chains}
    for fd in bake["frame_data"]:
        skin = fd["characters"][ci]["skin"] if isinstance(fd["characters"], list) else fd["characters"][ch_name]["skin"]
        for c in chains:
            i = bones.index(c["bones"][-1])
            out[c["name"]].append(xf(skin[i * 16:(i + 1) * 16], c["tip"]))
    return out, [fd["frame"] for fd in bake["frame_data"]], bones, ci


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--off")
    ap.add_argument("--character", default="girl")
    ap.add_argument("--out")
    a = ap.parse_args()
    pkg = json.load(open(f"{a.package}/character.json"))
    dyn = pkg.get("dynamics")
    if not dyn:
        raise SystemExit("package has no dynamics block")
    chains = dyn["chains"]
    on = json.load(open(a.on))
    t_on, frames, bones, ci = tips(on, a.character, chains)
    rep = {"chains": len(chains), "dynamics_enabled": dyn.get("enabled", True), "frames": [frames[0], frames[-1]]}
    # T-021 collision figure: smallest (joint/tip to sphere-collider centre) - (collider radius + chain joint radius)
    heads = {b["name"]: b["head"] for b in pkg["skeleton"]}
    clear = {}
    for col in dyn.get("colliders", []):
        if col["type"] != "sphere":
            continue
        cb = bones.index(col["bone"])
        best = None
        for k, fd in enumerate(on["frame_data"]):
            skin = fd["characters"][ci]["skin"] if isinstance(fd["characters"], list) else fd["characters"][a.character]["skin"]
            c = xf(skin[cb * 16:(cb + 1) * 16], col["centre"])
            for ch in chains:
                pts = [xf(skin[bones.index(b) * 16:(bones.index(b) + 1) * 16], heads[b]) for b in ch["bones"][1:]]
                pts.append(t_on[ch["name"]][k])
                r = ch.get("radius", dyn.get("defaults", {}).get("radius", 0.0))
                for p in pts:
                    g = (dist(p, c) - col["radius"] - r) * 1000
                    if best is None or g < best[0]:
                        best = (g, fd["frame"], ch["name"])
        if best:
            clear[col["name"]] = {"min_clearance_mm": round(best[0], 2), "frame": best[1], "chain": best[2]}
    rep["sphere_collider_clearance"] = clear
    if a.off:
        t_off, _, _, _ = tips(json.load(open(a.off)), a.character, chains)
        per = {}
        for n in t_on:
            d = [dist(p, q) * 1000 for p, q in zip(t_on[n], t_off[n])]
            per[n] = {"max_mm": round(max(d), 1), "sampled_mm": [round(d[f - frames[0]]) for f in (1, 7, 13, 19, 25, 31, 37, 43)
                                                                if frames[0] <= f <= frames[-1]], "every_frame_mm": [round(x) for x in d]}
        rep["tip_offset_on_vs_off"] = per
        rep["median_of_chain_max_mm"] = round(statistics.median(v["max_mm"] for v in per.values()), 1)
        rep["max_mm"] = max(v["max_mm"] for v in per.values())
    else:
        # head-relative tip motion: tip in the head bone's rest frame (inverse of the head skin matrix)
        hi = bones.index("head")
        import numpy as np
        mv = {}
        for n in t_on:
            rel = []
            for k, fd in enumerate(on["frame_data"]):
                skin = fd["characters"][ci]["skin"] if isinstance(fd["characters"], list) else fd["characters"][a.character]["skin"]
                H = np.array(skin[hi * 16:(hi + 1) * 16]).reshape(4, 4).T
                rel.append(np.linalg.solve(H, np.r_[t_on[n][k], 1.0])[:3])
            rel = np.array(rel)
            mv[n] = round(float(np.max(np.linalg.norm(rel - rel[0], axis=1)) * 1000), 1)
        rep["tip_motion_relative_to_head_max_mm"] = mv
        rep["median_mm"] = round(statistics.median(mv.values()), 1)
        rep["max_mm"] = max(mv.values())
    s = json.dumps(rep, indent=1)
    if a.out:
        open(a.out, "w").write(s)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("tip_offset_on_vs_off", "tip_motion_relative_to_head_max_mm")}))
    if "tip_offset_on_vs_off" in rep:
        for n in ("back_curls.06", "back_curls.07", "side_curls.02", "side_curls.00", "back_curls.03"):
            if n in rep["tip_offset_on_vs_off"]:
                v = rep["tip_offset_on_vs_off"][n]
                print(n, v["max_mm"], v["sampled_mm"], *(["every:", v["every_frame_mm"]] if n == "back_curls.03" else []))


if __name__ == "__main__":
    main()
