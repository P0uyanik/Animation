"""T-093 round 2: the combined look for the owner - the T-093 candidate (garment/2 outlines) with the T-092 material
candidate (presets/3) on top, merged field by field. Reads candidates/T-092 (read-only), writes
candidates/T-093/<id>.T-093+T-092.combined.override.json.

    python3 docs/evaluation/characters/T-093/make_combined.py

Rules (the T-094 merge, for review only): T-093's override is the base. Per garment, every key T-092 changed against
the published spec (`material`, `materials.<part>`) is taken from T-092. T-092's `materials` block (skin) is merged
on top. When T-092 assigns the boot cuff band (`materials.band`), T-093's own cuff colour (`materials.cuff`) is
dropped, so the rolled cuff takes T-092's fleece (cuff_roll falls back to `band`)."""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
CH = os.path.join(ROOT, "assets", "characters")
CHARS = {"boy_yellow_hoodie": "2.0.0", "girl_auburn_bun_glasses": "0.11.0"}


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in b.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


for cid, ver in CHARS.items():
    sp = os.path.join(CH, cid, "spec")
    pub = json.load(open(os.path.join(sp, f"{cid}.{ver}.spec.json")))
    t93 = json.load(open(os.path.join(sp, "candidates", "T-093", f"{cid}.T-093.override.json")))["override"]
    t92 = json.load(open(os.path.join(sp, "candidates", "T-092", f"{cid}.materials_r2.override.json")))["override"]
    out = copy.deepcopy(t93)
    pg = {g["name"]: g for g in pub["clothing"]["garments"]}
    g92 = {g["name"]: g for g in t92.get("clothing", {}).get("garments", [])}
    taken = []
    for g in out["clothing"]["garments"]:
        p, m = pg[g["name"]], g92.get(g["name"])
        if m is None:
            continue
        if m.get("material") != p.get("material"):
            g["material"] = copy.deepcopy(m["material"])
            taken.append(f"{g['name']}.material")
        for part in sorted(set(m.get("materials", {})) | set(p.get("materials", {}))):
            if m.get("materials", {}).get(part) != p.get("materials", {}).get(part):
                g.setdefault("materials", {})[part] = copy.deepcopy(m["materials"][part])
                taken.append(f"{g['name']}.materials.{part}")
                if part == "band" and "cuff" in g.get("materials", {}):
                    del g["materials"]["cuff"]
                    taken.append(f"{g['name']}.materials.cuff dropped (cuff_roll uses band)")
    if "materials" in t92:
        out["materials"] = deep_merge(out.get("materials", {}), t92["materials"])
        taken.append("materials (" + ", ".join(sorted(t92["materials"].get("assignments", {}))) + ")")
    out["metadata"] = {"notes": "T-093 round 2 review only (unpublished): T-093 garment/2 candidate with the T-092 "
                                "presets/3 material candidate merged field by field (make_combined.py). Taken from "
                                "T-092: " + "; ".join(taken) + ". Never publish; T-094 does the real merge."}
    path = os.path.join(sp, "candidates", "T-093", f"{cid}.T-093+T-092.combined.override.json")
    json.dump({"override": out}, open(path, "w"), indent=1)
    open(path, "a").write("\n")
    print(path, taken)
