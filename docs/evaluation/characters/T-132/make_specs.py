"""T-132: compose boy 2.3.0 / girl 0.14.0 = 2.2.0 / 0.13.0 + T-118 hair r5 + T-119 garments r3 (+ limb skin) + T-121 hands_r2.

Each override's `override` block is deep-merged (pipeline/charsys/spec.deep_merge) in that order; their own
metadata notes are dropped and replaced by the T-132 metadata. Run from the repository root.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "pipeline/charsys")
from spec import deep_merge  # noqa: E402

E = "docs/evaluation/characters"
JOBS = [
    ("boy_yellow_hoodie", "2.2.0", "2.3.0", [
        f"{E}/T-118/candidates/boy_yellow_hoodie.hair_r5.override.json",
        f"{E}/T-119/boy_yellow_hoodie.T-119.override.json",
        f"{E}/T-121/hands_r2.override.json"]),
    ("girl_auburn_bun_glasses", "0.13.0", "0.14.0", [
        f"{E}/T-118/candidates/girl_auburn_bun_glasses.hair_r5.override.json",
        f"{E}/T-119/girl_auburn_bun_glasses.T-119.override.json",
        f"{E}/T-121/hands_r2.override.json"]),
]
SCOPE = ("{parent} + T-118 hair r5 (groom/4: {hair}; flower/bow attachment rule of T-118: accessory stays on its seat, "
         "turned with `turn`) + T-119 garments r3 (garment/3: {garm}{skin}) + T-121 hands_r2 (separated fingers, same bones).")

for cid, parent, ver, layers in JOBS:
    d = Path(f"assets/characters/{cid}/spec")
    spec = json.loads((d / f"{cid}.{parent}.spec.json").read_text())
    meta = spec.pop("metadata")
    for p in layers:
        ov = json.loads(Path(p).read_text())
        ov = dict(ov.get("override", ov))
        ov.pop("metadata", None)
        spec = deep_merge(spec, ov)
    boy = cid.startswith("boy")
    spec["metadata"] = {
        "spec_version": ver,
        "status": f"T-132: published to the asset store with tools/version_switch.py --publish-only as a CANDIDATE; "
                  f"NOT approved, not current (current stays {parent})",
        "scope": SCOPE.format(
            parent=f"{cid.split('_')[0]} {parent}",
            hair="whorl tiers with channels, staggered crown petals, fringe lifted" if boy else
                 "lower outer sweeps, staggered tapered curl ends, flower turned to the front quarter",
            garm="ankle_close on the trousers" if boy else "collar_seat on the blouse, cuff_gather on the bloomers",
            skin="; limb skin skin-felt-limbs/3, base 226/178/162 = the reference-hand match as accepted, not the "
                 "5 L* limb-region median" if boy else ""),
        "parent_versions": [parent],
        "sources": {"derived_from": str(d / f"{cid}.{parent}.spec.json"), "layers": layers,
                    "composed_by": f"{E}/T-132/make_specs.py"},
        "owner_decisions": "docs/process/OWNER_DECISIONS.md 2026-11-19 ~15:10Z: \"approve the 2.3.0 and 0.14.0 "
                           "candidates task\" (T-132); parent history in "
                           f"{cid}.{parent}.spec.json",
        "parent_metadata_owner_decisions": meta.get("owner_decisions", ""),
    }
    out = d / f"{cid}.{ver}.spec.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print("wrote", out)
