"""T-155: compose the three candidate specs (publish-only, not current). Run from the repository root.

- boy 2.3.0 / girl 0.14.0: the T-132 composition (docs/evaluation/characters/T-132/make_specs.py on branch
  t-132-claude-versions f28fe2a): 2.2.0 / 0.13.0 + T-118 hair_r5 + T-119 garments r3 + T-121 hands_r2, then the
  approved T-137 face: F2 face override (boy), F1a eyes override (girl).
- third 0.1.0: spec/candidates/T-126a + T-126 hands_r2, hair, dress, T-126d materials + T-137 F1b eyes and fringe.
  With --with-t133 the T-133 proposal goes last; its hair.structures list (charsys replaces lists) gets F1b's fringe
  item and its face_keepout from the F1b fringe override, so F1b survives. Owner 07:00Z: proposal only if it improves.
Usage: python3 docs/evaluation/characters/T-155/make_specs.py [--with-t133 | --third-only-out <file> [--with-t133]]
Each layer's `override` block (or the whole file) is deep-merged (spec.deep_merge: dicts recursive, lists replaced)
in that order; layer metadata is dropped and replaced by T-155 metadata.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "pipeline/charsys")
from spec import deep_merge  # noqa: E402

E = "docs/evaluation/characters"
DEC = "docs/process/OWNER_DECISIONS.md 2026-11-20 ~06:40Z item 4"
A = "assets/characters"
JOBS = [
    ("boy_yellow_hoodie", f"{A}/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.2.0.spec.json", "2.3.0", "2.2.0", [
        f"{E}/T-118/candidates/boy_yellow_hoodie.hair_r5.override.json",
        f"{E}/T-119/boy_yellow_hoodie.T-119.override.json",
        f"{E}/T-121/hands_r2.override.json",
        f"{E}/T-137/f2/boy_yellow_hoodie.face.override.json"]),
    ("girl_auburn_bun_glasses", f"{A}/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.13.0.spec.json",
     "0.14.0", "0.13.0", [
        f"{E}/T-118/candidates/girl_auburn_bun_glasses.hair_r5.override.json",
        f"{E}/T-119/girl_auburn_bun_glasses.T-119.override.json",
        f"{E}/T-121/hands_r2.override.json",
        f"{E}/T-137/f1a/girl_auburn_bun_glasses.eyes.override.json"]),
    ("girl_white_hair_blue_dress",
     f"{A}/girl_white_hair_blue_dress/spec/candidates/T-126a/girl_white_hair_blue_dress.0.1.0.spec.json",
     "0.1.0", None, [
        f"{E}/T-126/body_face/hands_r2.override.json",
        f"{E}/T-126/hair/candidates/girl_white_hair_blue_dress.hair.override.json",
        f"{E}/T-126/dress/girl_white_hair_blue_dress.dress.override.json",
        f"{E}/T-126/materials/girl_white_hair_blue_dress.T-126d.override.json",
        f"{E}/T-137/f1b/girl_white_hair_blue_dress.eyes.override.json",
        f"{E}/T-137/f1b/girl_white_hair_blue_dress.fringe.override.json"]),
]
WITH_T133 = "--with-t133" in sys.argv
THIRD_OUT = sys.argv[sys.argv.index("--third-only-out") + 1] if "--third-only-out" in sys.argv else None
FRINGE = f"{E}/T-137/f1b/girl_white_hair_blue_dress.fringe.override.json"


def t133_layer():
    """T-133 proposal with the F1b fringe kept (lists are replaced whole by deep_merge)."""
    prop = json.loads(Path(f"{E}/T-133/proposal.json").read_text())
    fr = json.loads(Path(FRINGE).read_text())["override"]["hair"]
    fringe = next(s for s in fr["structures"] if s["name"] == "fringe")
    prop["hair"]["structures"] = [fringe if s["name"] == "fringe" else s for s in prop["hair"]["structures"]]
    prop["hair"]["face_keepout"] = fr["face_keepout"]
    return prop

for cid, base, ver, parent, layers in JOBS:
    spec = json.loads(Path(base).read_text())
    meta = spec.pop("metadata", {})
    if THIRD_OUT and parent is not None:
        continue
    if WITH_T133 and parent is None:
        layers = layers + [f"{E}/T-133/proposal.json (F1b fringe kept)"]
    for p in layers:
        if p.startswith(f"{E}/T-133/"):
            spec = deep_merge(spec, t133_layer())
            continue
        ov = json.loads(Path(p).read_text())
        ov = dict(ov["override"]) if "override" in ov else ov
        ov.pop("metadata", None)
        spec = deep_merge(spec, ov)
    spec["metadata"] = {
        "spec_version": ver,
        "status": "T-155: published with tools/version_switch.py --publish-only as a CANDIDATE; NOT approved, "
                  "not current" + (f" (current stays {parent})" if parent else " (the character has no current version)"),
        "parent_versions": [parent] if parent else [],
        "sources": {"derived_from": base, "layers": layers, "composed_by": f"{E}/T-155/make_specs.py"},
        "owner_decisions": f"{DEC}: publish boy 2.3.0, girl 0.14.0 and third character 0.1.0 as CANDIDATES",
        "parent_metadata_owner_decisions": meta.get("owner_decisions", ""),
    }
    out = Path(THIRD_OUT) if THIRD_OUT else Path(f"{A}/{cid}/spec/candidates/T-155/{cid}.{ver}.spec.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print("wrote", out)
