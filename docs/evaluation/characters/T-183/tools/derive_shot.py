"""T-183 round 3: the T-183 copy of a shot (opt-in; the source shot and the released packages stay as they are).

    python3 derive_shot.py <.../shots/<shot>/shot.scene.json> [...] [--suffix=_t183] [--skip-objects=pattern,...]
                           [--radius-m=0.01] [--props] [--skip-props=pattern,...] [--neighbours-from=<bake.json>]
                           [--reach-m=0.1] [--no-neighbours] [--check]

Writes <.../shots/<shot><suffix>/shot.scene.json> = the source shot with
  1. production.cast: every character that has a T-183 candidate (CANDIDATES, by character id) is built from its
     released spec plus the candidate override instead of the published version;
  2. characters[<that character>].dynamics.colliders: the scene's box objects as world-space box colliders
     ("scene.<object name>"; docs/SECONDARY_MOTION.md, "Scene colliders"), so its hair lies on the table, the seat and
     the floor instead of passing through them. Objects matching --skip-objects get no collider;
  3. "x_t183": {"source", "change"} and the shot's name with the suffix.
Opt-in per shot (off without the options; tools/neighbours.py, docs/SECONDARY_MOTION.md "Scene colliders"):
  4. --props: the scene's box and cylinder props as colliders that ride on the prop ("prop.<name>": a boat in a
     hand, a cup);
  5. --neighbours-from=<bake.json>: spheres on the other characters' bones ("nb.<character>.<i>"), fitted on their
     package meshes where the hair of the candidate comes within --reach-m of them in that bake. The bake is one of
     this copy WITHOUT neighbour colliders (derive, prepare, bake, then derive again with the option). Without the
     option the neighbour colliders of the copy on disk are kept as they are (--no-neighbours drops them).
Nothing else changes: the copy is the source file key for key. --check writes nothing and fails when a copy on disk
differs from what would be written with the options that copy records in x_t183.options (run it after the source
shot changed); the neighbour colliders themselves are not refitted by --check.
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


def is_neighbour(c):
    return isinstance(c, dict) and "character" in c


def derive(path, suffix, skip, radius, props=False, skip_props=(), neighbours=None, reach=0.1, keep_neighbours=True):
    """neighbours: a bake path (fit them), None (keep those of the copy on disk when keep_neighbours)."""
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
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), shot + suffix, "shot.scene.json")
    on_disk = json.load(open(out)) if os.path.exists(out) else {}
    pboxes, nb, nb_note = [], {}, None
    if props:
        import neighbours as NB
        pboxes = NB.prop_boxes(scene, path, skip_props)
    if neighbours:
        import neighbours as NB
        counts = {}
        for name in changed:
            nb[name], rep_ = NB.neighbour_spheres(neighbours, name, reach=reach)
            counts[name] = {k: v["spheres"] for k, v in rep_.items()}
        nb_note = {"reach_m": reach, "bake": os.path.relpath(os.path.abspath(neighbours), ROOT).replace(os.sep, "/"), "spheres": counts,
                   "fit": "tools/neighbours.py (groom_contact.skin_spheres on the neighbours' package meshes)"}
    elif keep_neighbours:
        for ch in on_disk.get("characters", []):
            kept = [c for c in (ch.get("dynamics") or {}).get("colliders", []) if is_neighbour(c)] if isinstance(ch.get("dynamics"), dict) else []
            if kept:
                nb[ch["name"]] = kept
        nb_note = on_disk.get("x_t183", {}).get("neighbours") if nb else None
    for ch in scene.get("characters", []):
        add = boxes + pboxes + nb.get(ch["name"], [])
        if ch["name"] in changed and add:
            dyn = ch.get("dynamics")
            if dyn is False or (isinstance(dyn, dict) and dyn.get("enabled") is False):
                continue
            dyn = dict(dyn) if isinstance(dyn, dict) else {}
            dyn["colliders"] = list(dyn.get("colliders", [])) + add
            ch["dynamics"] = dyn
    scene["name"] = f"{scene['name'].split(':', 1)[0].replace(shot, shot + suffix)}: {shot} with the T-183 hair-contact candidates ({', '.join(changed)}; opt-in, unpublished)"
    scene["x_t183"] = {"source": rel,
                       "change": f"production.cast of {', '.join(changed)}; characters[].dynamics.colliders of the same = the scene's box objects"
                                 f" ({', '.join(b['name'][6:] for b in boxes)})",
                       "tool": "docs/evaluation/characters/T-183/tools/derive_shot.py"}
    if pboxes or nb:  # opt-in parts: recorded so that --check derives the same copy again
        scene["x_t183"]["change"] += "; opt-in scene colliders: " + ", ".join(
            ([f"props ({', '.join(b['prop'] for b in pboxes)})"] if pboxes else []) +
            ([f"neighbours ({', '.join(f'{k}: {len(v)} spheres' for k, v in nb.items())})"] if nb else []))
        scene["x_t183"]["options"] = {"props": bool(pboxes), "skip_props": list(skip_props)}
        if nb_note:
            scene["x_t183"]["neighbours"] = nb_note
    return out, _dump(scene), changed, boxes + pboxes + [c for v in nb.values() for c in v]


def _dump(scene):
    """indent=1; a collider list with neighbour spheres (hundreds) is written one collider per line."""
    import copy
    scene = copy.deepcopy(scene)
    lists = {}
    for ch in scene.get("characters", []):
        cols = (ch.get("dynamics") or {}).get("colliders") if isinstance(ch.get("dynamics"), dict) else None
        if cols and any(is_neighbour(c) for c in cols):
            token = f"@@colliders:{ch['name']}@@"
            lists[token] = "[\n" + ",\n".join("     " + json.dumps(c) for c in cols) + "\n    ]"
            ch["dynamics"]["colliders"] = token
    text = json.dumps(scene, indent=1)
    for token, block in lists.items():
        text = text.replace(json.dumps(token), block)
    return text + "\n"


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    suffix = opt("suffix", "_t183")
    skip = [p for p in (opt("skip-objects", "") or "").split(",") if p]
    radius = float(opt("radius-m", "0.01"))
    bad = 0
    check = "--check" in sys.argv
    for p in paths:
        props, skip_props, nb_from = "--props" in sys.argv, [x for x in (opt("skip-props", "") or "").split(",") if x], opt("neighbours-from")
        if check:  # the options the copy on disk records
            o = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(p))), os.path.basename(os.path.dirname(os.path.abspath(p))) + suffix, "shot.scene.json")
            rec = (json.load(open(o)).get("x_t183", {}).get("options", {})) if os.path.exists(o) else {}
            props, skip_props, nb_from = rec.get("props", False), rec.get("skip_props", []), None
        out, text, changed, boxes = derive(p, suffix, skip, radius, props, skip_props, nb_from, float(opt("reach-m", "0.1")),
                                           "--no-neighbours" not in sys.argv)
        rel = os.path.relpath(out, ROOT)
        if check:
            same = os.path.exists(out) and open(out).read() == text
            print(f"{rel}: {'up to date' if same else 'DIFFERS from the derived copy'}")
            bad += not same
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w").write(text)
        print(f"{rel}: candidates for {changed}, {len(boxes)} colliders per character at most (boxes, props, neighbours)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
