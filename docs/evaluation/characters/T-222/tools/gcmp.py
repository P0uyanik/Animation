"""Dev: garment_body off/on numbers from two contact_audit JSONs (per character: frame entries over the limit,
max / median depth, frames; garment jump pops by the T-194 rule)."""
import gzip, json, statistics, sys
sys.path.insert(0, "/home/user/Animation/pipeline/production")
import contact_audit as CA

def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))

def per_char(d, limit):
    out = {}
    for r in d["rows"]:
        for ch, m in r["classes"].get("garment_body", {}).items():
            o = out.setdefault(ch, {"entries": 0, "depths": [], "frames": set(), "objects": {}})
            dmax = max((v[1] for v in m.values()), default=0.0)
            if dmax > limit:
                o["entries"] += 1
                o["depths"].append(dmax)
                o["frames"].add(r["frame"])
            for k, (n, dep) in m.items():
                ob = o["objects"].setdefault(k.split(" > ")[0] + " > " + k.split(":")[-1], [0, 0.0, 0])
                ob[0] += 1; ob[1] = max(ob[1], dep); ob[2] = max(ob[2], n)
    return out

a, b = load(sys.argv[1]), load(sys.argv[2])
lim = a["limit_mm"]
A, B = per_char(a, lim), per_char(b, lim)
nfr = len(a["rows"])
print(f"frames measured {nfr} (step {a['step']}, {a['frames']}), limit {lim} mm")
print("| character | entries > 1 mm off -> on | max mm off -> on | median mm off -> on |")
for ch in sorted(set(A) | set(B)):
    x, y = A.get(ch, {"entries": 0, "depths": [], "objects": {}}), B.get(ch, {"entries": 0, "depths": [], "objects": {}})
    md = lambda z: round(statistics.median(z), 1) if z else 0.0
    print(f"| {ch} | {x['entries']} -> {y['entries']} | {max(x['depths'], default=0):.1f} -> {max(y['depths'], default=0):.1f} | {md(x['depths'])} -> {md(y['depths'])} |")
    top = sorted(set(x["objects"]) | set(y["objects"]), key=lambda k: -max(x["objects"].get(k, [0, 0])[1], y["objects"].get(k, [0, 0])[1]))[:8]
    for k in top:
        print(f"    {k}: frames {x['objects'].get(k, [0, 0, 0])[0]} -> {y['objects'].get(k, [0, 0, 0])[0]}, max {x['objects'].get(k, [0, 0.0])[1]:.1f} -> {y['objects'].get(k, [0, 0.0])[1]:.1f} mm")
p = CA.jump_pops(a, b, a["pop_mm"], role="garment")
print("garment jump pops (on adds > 5 mm to the largest garment vertex move):", p["count"], "max added", p["max_added_mm"], p["list"][:20])
sa, sb = a["summary"].get("garment_body", {}), b["summary"].get("garment_body", {})
print("depth pops off/on:", {k: v for k, v in sa.items() if "pop" in k}, {k: v for k, v in sb.items() if "pop" in k})
print("sha off/on:", a["sha256"][:12], b["sha256"][:12])
