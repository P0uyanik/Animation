"""T-183 round 3: the T-183 copy of a shot (opt-in; the source shot and the released packages stay as they are).

    python3 derive_shot.py <.../shots/<shot>/shot.scene.json> [...] [--suffix=_t183] [--skip-objects=pattern,...]
                           [--radius-m=0.01] [--check]

Writes <.../shots/<shot><suffix>/shot.scene.json> = the source shot with
  1. production.cast: every character that has a T-183 candidate (CANDIDATES, by character id) is built from its
     released spec plus the candidate override instead of the published version;
  2. characters[<that character>].dynamics.colliders: the scene's box objects as world-space box colliders
     ("scene.<object name>"; docs/SECONDARY_MOTION.md, "Scene colliders"), so its hair lies on the table, the seat and
     the floor instead of passing through them. Objects matching --skip-objects get no collider;
  3. "x_t183": {"source", "change"} and the shot's name with the suffix.
Nothing else changes: the copy is the source file key for key. --check writes nothing and fails when a copy on disk
differs from what would be written (run it after the source shot changed).
"""
import fnmatch
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
CAND = "docs/evaluation/characters/T-183/candidates"
# character id -> the cast entry of its candidate (released spec + the unpublished override)
CANDIDATES = {
    "girl_auburn_bun_glasses": {
        "spec": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.14.0.spec.json",
        "overrides": [f"{CAND}/girl_auburn_bun_glasses.hair_contact.override.json"]},
    "girl_white_hair_blue_dress": {
        "spec": "assets/characters/girl_white_hair_blue_dress/versions/0.1.0/spec.json",
        "overrides": [f"{CAND}/girl_white_hair_blue_dress.hair_contact.override.json"]},
}


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def character_id(entry):
    if "character_id" in entry:
        return entry["character_id"]
    for key in ("version_dir", "spec"):
        if key in entry:
            return next((c for c in CANDIDATES if f"/{c}/" in "/" + entry[key].replace(os.sep, "/")), None)
    return None


def derive(path, suffix, skip, radius):
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, "/")
    scene = json.load(open(path))
    shot = os.path.basename(os.path.dirname(rel))
    cast = scene["production"]["cast"]
    changed = []
    for name, entry in cast.items():
        cid = character_id(entry)
        if cid not in CANDIDATES or not all(os.path.exists(os.path.join(ROOT, o)) for o in CANDIDATES[cid]["overrides"]):
            continue
        cast[name] = dict(CANDIDATES[cid])
        changed.append(name)
    boxes = [{"name": f"scene.{o['name']}", "type": "box", "space": "world", "min": o["min"], "max": o["max"], "radius": radius}
             for o in scene.get("objects", [])
             if o.get("kind", "box") == "box" and "min" in o and not any(fnmatch.fnmatchcase(o["name"], s) for s in skip)]
    for ch in scene.get("characters", []):
        if ch["name"] in changed and boxes:
            dyn = ch.get("dynamics")
            if dyn is False or (isinstance(dyn, dict) and dyn.get("enabled") is False):
                continue
            dyn = dict(dyn) if isinstance(dyn, dict) else {}
            dyn["colliders"] = list(dyn.get("colliders", [])) + boxes
            ch["dynamics"] = dyn
    scene["name"] = f"{scene['name'].split(':', 1)[0].replace(shot, shot + suffix)}: {shot} with the T-183 hair-contact candidates ({', '.join(changed)}; opt-in, unpublished)"
    scene["x_t183"] = {"source": rel,
                       "change": f"production.cast of {', '.join(changed)}; characters[].dynamics.colliders of the same = the scene's box objects"
                                 f" ({', '.join(b['name'][6:] for b in boxes)})",
                       "tool": "docs/evaluation/characters/T-183/tools/derive_shot.py"}
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), shot + suffix, "shot.scene.json")
    return out, json.dumps(scene, indent=1) + "\n", changed, boxes


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    suffix = opt("suffix", "_t183")
    skip = [p for p in (opt("skip-objects", "") or "").split(",") if p]
    radius = float(opt("radius-m", "0.01"))
    bad = 0
    for p in paths:
        out, text, changed, boxes = derive(p, suffix, skip, radius)
        rel = os.path.relpath(out, ROOT)
        if "--check" in sys.argv:
            same = os.path.exists(out) and open(out).read() == text
            print(f"{rel}: {'up to date' if same else 'DIFFERS from the derived copy'}")
            bad += not same
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w").write(text)
        print(f"{rel}: candidates for {changed}, {len(boxes)} box colliders")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
