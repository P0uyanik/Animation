"""T-198 evidence (not part of the gate): compare two golden_dump_t198 outputs (before / after build).
Per scene: frames that differ, frame range, max world turn (deg) and pivot travel (mm), per character the bones that
differ by > 0.01 deg / 0.01 mm with their max.  python3 golden_delta_t198.py before.txt after.txt"""
import math
import sys
from collections import defaultdict


def load(path):
    out = {}
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) != 11 or "/" not in p[0]:  # evaluator messages
                continue
            out[(p[0], p[1], int(p[2]), p[3])] = [float(x) for x in p[4:]]
    return out


def main(a_path, b_path):
    a, b = load(a_path), load(b_path)
    scenes = defaultdict(lambda: {"frames": set(), "deg": 0.0, "mm": 0.0, "bones": defaultdict(lambda: [0.0, 0.0, set()])})
    for k, va in a.items():
        vb = b[k]
        mm = math.dist(va[:3], vb[:3]) * 1e3
        chord = min(math.dist(va[3:], vb[3:]), math.dist(va[3:], [-x for x in vb[3:]]))
        deg = math.degrees(4 * math.asin(min(1.0, chord / 2)))  # precise for small turns
        if mm < 0.01 and deg < 0.01:
            continue
        s = scenes[k[0]]
        s["frames"].add(k[2])
        s["deg"], s["mm"] = max(s["deg"], deg), max(s["mm"], mm)
        bone = s["bones"][(k[1], k[3])]
        bone[0], bone[1] = max(bone[0], deg), max(bone[1], mm)
        bone[2].add(k[2])
    allscenes = sorted({k[0] for k in a})
    for name in allscenes:
        s = scenes.get(name)
        if not s:
            print(f"{name}: identical")
            continue
        fr = sorted(s["frames"])
        print(f"{name}: {len(fr)} frames ({fr[0]}-{fr[-1]}), max {s['deg']:.2f} deg / {s['mm']:.1f} mm")
        rows = sorted(s["bones"].items(), key=lambda kv: -max(kv[1][0], kv[1][1] / 2))
        for (who, bone), (deg, mm, frs) in rows[:int(sys.argv[3]) if len(sys.argv) > 3 else 12]:
            frs = sorted(frs)
            print(f"   {who} {bone}: {deg:.2f} deg / {mm:.1f} mm, frames {frs[0]}-{frs[-1]} ({len(frs)})")
        print(f"   ({len(rows)} bones differ)")


main(sys.argv[1], sys.argv[2])
