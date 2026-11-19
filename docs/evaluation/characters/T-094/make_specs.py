"""T-094: compose boy_yellow_hoodie 2.1.0 and girl_auburn_bun_glasses 0.12.0 from the current approved specs (2.0.0,
0.11.0) and the owner-approved Phase B/D candidates. Reads the candidates (read-only), writes the two new
`*.spec.json` files (complete, monolithic specs; no overrides at build time).

    python3 docs/evaluation/characters/T-094/make_specs.py [--check]

--check: compose in memory and fail if the committed spec files differ (nothing written).

Merge order (each a deep merge, dicts recursively, lists replaced; candidate `metadata`/`notes` are not copied):
  1. face   T-089b `face3b` override (face_generic/3 + T-089b polish: boy heavy lids, girl rounder face/wider eyes);
  2. hair   T-091 `hair_r4` override (groom/3 masses; boy fringe/crown, girl centre part, swept sections, back
            sections, tapered ringlets, gathered scrunchie). The directional-fibre experiment is NOT used: the T-091
            strict sheets were rendered without it (README: "Left off in the main candidates");
  3. garments + materials  the combined garment override that already carries the T-092 presets/3 merge:
            boy  T-093 `T-093+T-092.combined` (T-093b dropped the T-090b variant: the boy keeps T-093);
            girl T-093b `T-093b+T-092.combined` (leg_split crotch arch + sleeve/shorts refit).
            Its `clothing` and `materials` sections are applied whole. The girl's combined override also carries
            T-093 hair data; only what T-091 does not redo is taken from it: the `flowers` structure (one pink felt
            flower, owner design point 2026-11-18 "blue-grey scrunchie with one pink felt flower") and
            `hair.components` (its description). Its `band` (the old tie, retuned) is NOT taken: T-091's gathered
            scrunchie replaces the tie and keeps the `band` name and the `hair_band` slot;
  4. pins   generators.materials = presets/3 (T-092 README: T-094 must set it); the other pins come from the
            candidates (face_generic/3, groom/3, garment/2);
  5. metadata  spec_version, status, scope, parent_versions, sources (every input file), history.
Identity (identity, proportions) is unchanged; face, hair, clothing and materials change (owner-approved systems),
so the publish carries --identity-change-approved-by."""
import copy
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
CH = os.path.join(ROOT, "assets", "characters")

CHARS = {
    "boy_yellow_hoodie": {
        "parent": "2.0.0", "version": "2.1.0",
        "face": "T-089b/boy_face3b.override.json",
        "hair": "T-091/boy_yellow_hoodie.hair_r4.override.json",
        "garments": "T-093/boy_yellow_hoodie.T-093+T-092.combined.override.json",
        "hair_from_garments": [],
        "scope": "boy 2.0.0 + Phase B/D systems: face_generic/3 with the T-089b sleepy heavy lids (eye size of T-089), "
                 "groom/3 hair round 4 (T-091: fringe to the brows, fuller outline, standing crown petals), garment/2 "
                 "(T-093: B06 flap backpack, plain felt drawstrings with dark tips, sneakers, reach correctives), "
                 "presets/3 materials (T-092: hoodie fleece/3, trouser pile/3, skin-felt/3)",
    },
    "girl_auburn_bun_glasses": {
        "parent": "0.11.0", "version": "0.12.0",
        "face": "T-089b/girl_face3b.override.json",
        "hair": "T-091/girl_auburn_bun_glasses.hair_r4.override.json",
        "garments": "T-093b/girl_auburn_bun_glasses.T-093b+T-092.combined.override.json",
        "hair_from_garments": ["flowers"],
        "scope": "girl 0.11.0 + Phase B/D systems: face_generic/3 with the T-089b rounder, fuller face and wider eyes "
                 "(socket corner relax), groom/3 hair round 4 (T-091: centre part, two swept sections per side, soft "
                 "back transition, tapered ringlets, gathered scrunchie) with one pink felt flower (T-093), garment/2 "
                 "(T-093: rounded blouse collar, clean vest edges, reach correctives; T-093b: shorts leg split), "
                 "presets/3 materials (T-092: vest felt/3, brushed cotton/3, cuff fleece/3, skin-felt/3)",
    },
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compose(cid, cfg):
    sp = os.path.join(CH, cid, "spec")
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")  # noqa: E731
    parent_path = os.path.join(sp, f"{cid}.{cfg['parent']}.spec.json")
    spec = load(parent_path)
    paths = {k: os.path.join(sp, "candidates", cfg[k]) for k in ("face", "hair", "garments")}
    ov = {k: load(p)["override"] for k, p in paths.items()}
    strip = lambda o, *keys: {k: v for k, v in o.items() if k not in ("metadata", "notes") + keys}  # noqa: E731
    spec = deep_merge(spec, strip(ov["face"]))
    spec = deep_merge(spec, strip(ov["hair"]))
    garments = ov["garments"]
    spec = deep_merge(spec, strip(garments, "hair"))
    taken = []
    gh = garments.get("hair") or {}
    if gh:
        by_name = {s["name"]: s for s in gh.get("structures", [])}
        structures = spec["hair"]["structures"]
        for name in cfg["hair_from_garments"]:
            i = next(i for i, s in enumerate(structures) if s["name"] == name)
            structures[i] = copy.deepcopy(by_name[name])
            taken.append(f"hair.structures.{name}")
        if "components" in gh:
            spec["hair"]["components"] = copy.deepcopy(gh["components"])
            taken.append("hair.components")
    spec["generators"]["materials"] = "presets/3"
    parent_md = spec["metadata"]
    md = {
        "spec_version": cfg["version"],
        "status": "T-094: published to the asset store with tools/version_switch.py --publish-only; NOT approved, not "
                  f"current (current stays {cfg['parent']} until the owner decides)",
        "scope": cfg["scope"],
        "parent_versions": list(parent_md.get("parent_versions", [])) + [cfg["parent"]],
        "sources": {
            "base": rel(parent_path),
            "face": rel(paths["face"]),
            "hair": rel(paths["hair"]),
            "garments_and_materials": rel(paths["garments"]),
            "hair_from_garments": taken,
            "composed_by": "docs/evaluation/characters/T-094/make_specs.py",
        },
        "owner_decisions": "docs/process/OWNER_DECISIONS.md 2026-11-18: T-092 approved ~19:20Z; T-093 and T-089 "
                           "approved ~22:35Z; Phase D approved ~22:50Z; standing approval ~23:10Z (T-091, T-089b, "
                           "T-093b merged by Supervisor review; T-094 publishes, the owner approves before current)",
    }
    if "history" in parent_md:
        md["history"] = list(parent_md["history"]) + [f"{cfg['version']} (T-094): {cfg['scope']}"]
    spec["metadata"] = md
    return spec


def main():
    check = "--check" in sys.argv[1:]
    bad = 0
    for cid, cfg in CHARS.items():
        spec = compose(cid, cfg)
        path = os.path.join(CH, cid, "spec", f"{cid}.{cfg['version']}.spec.json")
        text = json.dumps(spec, indent=1, ensure_ascii=False) + "\n"
        if check:
            same = os.path.isfile(path) and open(path, encoding="utf-8").read() == text
            print(f"{'OK' if same else 'DIFFERS'} {os.path.relpath(path, ROOT)}")
            bad += not same
        else:
            if os.path.exists(path):
                print(f"exists, not overwritten: {os.path.relpath(path, ROOT)} (delete it first if intended)")
                bad += 1
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"wrote {os.path.relpath(path, ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
