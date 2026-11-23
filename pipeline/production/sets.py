"""Sets as data (T-098L experiment): applies a set (plush.set/1, content/sets/*.set.json) to a shot scene and writes a
new shot file. One set, one shot; this is not an environment system.

    python3 pipeline/production/sets.py validate --set content/sets/<id>.set.json
    python3 pipeline/production/sets.py apply --set content/sets/<id>.set.json --shot <shot.scene.json> --out <new.json>

A set holds (all in one file, every key checked; unknown keys are refused):
  materials   plush.scene materials ("standard": name, baseColor, roughness, specular). A set material named like a
              shot material restyles it (e.g. the shot's table).
  objects     boxes {name, group, min, max, material}; group only labels the set's shapes (recorded, not rendered).
  keep_objects  names of shot objects the set keeps (the shot's own staging, e.g. the table holding a prop). Every
              other shot object (floor, walls) and every shot light is replaced by the set's.
  lights      rect {name, center, aim, size [w, h], color, intensity} (converted to the scene's corner/edgeU/edgeV,
              emitting from center towards aim), sun {name, direction, angleDeg, color, intensity},
              sky {name, color, intensity}.
  camera      one preset {name, framing: "keep", fStop, focus: "target" | [x, y, z]}: the shot's camera position,
              target and lens are kept; depth of field is added, focused at the camera target (or a point).
  render      optional {exposureEV}.
  blender_light_rig  optional (T-221): the id of the set's Blender light rig (content/sets/rigs/<id>.light_rig.json,
              pipeline/charsys/set_lights.py). apply records it as x_set.light_rig; the Blender render then lights the
              shot with the rig instead of translating the set's engine lights (which stay for engine previews). A shot
              picks another rig with the top-level scene key "x_light_rig" (<id> or "engine"). Absent = as before.
Only what pipeline/charsys/shot_render.py already translates (boxes with a base colour, sun/rect/sky lights, camera
depth of field). Characters, props, actions, frames and the production block of the shot are copied unchanged.
Output is deterministic: same set + same shot -> byte-identical file (records both inputs' sha256 under "x_set")."""
import argparse
import copy
import hashlib
import json
import math
import os
import sys

SET_KEYS = {"format", "version", "id", "description", "convention", "keep_objects", "materials", "objects", "lights",
            "camera", "render", "blender_light_rig"}
SET_REQUIRED = {"format", "version", "id", "materials", "objects", "lights", "camera"}
MATERIAL_KEYS = {"name", "type", "baseColor", "roughness", "specular"}
OBJECT_KEYS = {"name", "group", "min", "max", "material"}
LIGHT_KEYS = {"rect": {"name", "type", "center", "aim", "size", "color", "intensity"},
              "sun": {"name", "type", "direction", "angleDeg", "color", "intensity"},
              "sky": {"name", "type", "color", "intensity"}}
CAMERA_KEYS = {"name", "framing", "fStop", "focus"}
RENDER_KEYS = {"exposureEV"}
DIGITS = 4


class SetError(ValueError):
    pass


def _keys(where, d, allowed, required=None):
    if not isinstance(d, dict):
        raise SetError(f"{where}: must be an object")
    unknown = sorted(set(d) - allowed)
    if unknown:
        raise SetError(f"{where}: unknown key(s) {unknown}")
    missing = sorted((allowed if required is None else required) - set(d))
    if missing:
        raise SetError(f"{where}: missing key(s) {missing}")


def _num(where, v, lo=None, hi=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise SetError(f"{where}: must be a finite number")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise SetError(f"{where}: {v} outside [{lo}, {hi}]")
    return float(v)


def _vec(where, v, n=3, lo=None, hi=None):
    if not isinstance(v, list) or len(v) != n:
        raise SetError(f"{where}: must be a list of {n} numbers")
    return [_num(f"{where}[{i}]", x, lo, hi) for i, x in enumerate(v)]


def _name(where, v):
    if not isinstance(v, str) or not v or v.strip() != v:
        raise SetError(f"{where}: must be a non-empty string")
    return v


def validate(s):
    """Raises SetError on any schema problem; returns the set unchanged."""
    _keys("set", s, SET_KEYS, SET_REQUIRED)
    if s["format"] != "plush.set" or s["version"] != 1:
        raise SetError("set: not a plush.set/1 file")
    _name("set.id", s["id"])
    for k in ("description", "convention"):
        if k in s and not isinstance(s[k], str):
            raise SetError(f"set.{k}: must be a string")
    keep = s.get("keep_objects", [])
    if not isinstance(keep, list) or len(set(keep)) != len(keep):
        raise SetError("set.keep_objects: must be a list of distinct names")
    for i, n in enumerate(keep):
        _name(f"set.keep_objects[{i}]", n)
    mats = set()
    if not isinstance(s["materials"], list):
        raise SetError("set.materials: must be a list")
    for i, m in enumerate(s["materials"]):
        w = f"set.materials[{i}]"
        _keys(w, m, MATERIAL_KEYS, {"name", "type", "baseColor"})
        n = _name(f"{w}.name", m["name"])
        if n in mats:
            raise SetError(f"{w}: duplicate material {n!r}")
        mats.add(n)
        if m["type"] != "standard":
            raise SetError(f"{w}.type: only 'standard' (shot_render translates base colour only)")
        _vec(f"{w}.baseColor", m["baseColor"], 3, 0.0, 1.0)
        for k in ("roughness", "specular"):
            if k in m:
                _num(f"{w}.{k}", m[k], 0.0, 1.0)
    names = set(keep)
    if not isinstance(s["objects"], list) or not s["objects"]:
        raise SetError("set.objects: must be a non-empty list")
    for i, o in enumerate(s["objects"]):
        w = f"set.objects[{i}]"
        _keys(w, o, OBJECT_KEYS)
        n = _name(f"{w}.name", o["name"])
        if n in names:
            raise SetError(f"{w}: duplicate object name {n!r}")
        names.add(n)
        _name(f"{w}.group", o["group"])
        lo, hi = _vec(f"{w}.min", o["min"]), _vec(f"{w}.max", o["max"])
        if any(a >= b for a, b in zip(lo, hi)):
            raise SetError(f"{w}: min must be below max on every axis")
        if o["material"] not in mats:
            raise SetError(f"{w}.material: {o['material']!r} is not a set material")
    lnames = set()
    if not isinstance(s["lights"], list) or not s["lights"]:
        raise SetError("set.lights: must be a non-empty list")
    for i, l in enumerate(s["lights"]):
        w = f"set.lights[{i}]"
        if not isinstance(l, dict) or l.get("type") not in LIGHT_KEYS:
            raise SetError(f"{w}.type: must be one of {sorted(LIGHT_KEYS)}")
        _keys(w, l, LIGHT_KEYS[l["type"]])
        n = _name(f"{w}.name", l["name"])
        if n in lnames:
            raise SetError(f"{w}: duplicate light name {n!r}")
        lnames.add(n)
        _vec(f"{w}.color", l["color"], 3, 0.0, 1.0)
        _num(f"{w}.intensity", l["intensity"], 0.0)
        if l["type"] == "rect":
            c, a = _vec(f"{w}.center", l["center"]), _vec(f"{w}.aim", l["aim"])
            if math.dist(c, a) < 1e-6:
                raise SetError(f"{w}: aim must differ from center")
            sz = _vec(f"{w}.size", l["size"], 2)
            if min(sz) <= 0:
                raise SetError(f"{w}.size: must be positive")
        elif l["type"] == "sun":
            d = _vec(f"{w}.direction", l["direction"])
            if math.hypot(*d) < 1e-6:
                raise SetError(f"{w}.direction: must not be zero")
            _num(f"{w}.angleDeg", l["angleDeg"], 0.0, 90.0)
    if sum(1 for l in s["lights"] if l["type"] == "sky") > 1:
        raise SetError("set.lights: at most one sky")
    c = s["camera"]
    _keys("set.camera", c, CAMERA_KEYS)
    _name("set.camera.name", c["name"])
    if c["framing"] != "keep":
        raise SetError("set.camera.framing: only 'keep' (the shot's own framing)")
    _num("set.camera.fStop", c["fStop"], 0.1, 64.0)
    if c["focus"] != "target":
        _vec("set.camera.focus", c["focus"])
    if "blender_light_rig" in s:
        r = _name("set.blender_light_rig", s["blender_light_rig"])
        if "/" in r or "\\" in r or r == "engine":
            raise SetError("set.blender_light_rig: a rig id (no path, not 'engine')")
    if "render" in s:
        _keys("set.render", s["render"], RENDER_KEYS, set())
        if "exposureEV" in s["render"]:
            _num("set.render.exposureEV", s["render"]["exposureEV"], -10.0, 10.0)
    return s


def _r(v):
    return round(float(v), DIGITS) + 0.0  # + 0.0: no "-0.0" in the output


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _unit(a):
    n = math.hypot(*a)
    return [x / n for x in a]


def rect_light(l):
    """center/aim/size -> the scene's rect light: corner + edgeU x edgeV, emitting along edgeU x edgeV (towards aim).
    edgeU is horizontal (perpendicular to +Y) unless the light points straight up or down."""
    n = _unit(_sub(l["aim"], l["center"]))
    up = [0.0, 1.0, 0.0] if abs(n[1]) < 0.999 else [0.0, 0.0, 1.0]
    u = _unit(_cross(up, n))
    v = _cross(n, u)  # u x v == n
    w, h = l["size"]
    corner = [c - 0.5 * w * a - 0.5 * h * b for c, a, b in zip(l["center"], u, v)]
    return {"type": "rect", "corner": [_r(x) for x in corner], "edgeU": [_r(w * x) for x in u],
            "edgeV": [_r(h * x) for x in v], "color": [_r(x) for x in l["color"]], "intensity": _r(l["intensity"])}


def scene_light(l):
    if l["type"] == "rect":
        return rect_light(l)
    out = {"type": l["type"]}
    if l["type"] == "sun":
        out.update(direction=[_r(x) for x in _unit(l["direction"])], angleDeg=_r(l["angleDeg"]))
    out.update(color=[_r(x) for x in l["color"]], intensity=_r(l["intensity"]))
    return out


def canonical_sha(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def apply(s, shot):
    """Returns a new shot scene dict: the shot with the set's world (objects, materials, lights, camera preset)."""
    validate(s)
    if not isinstance(shot, dict) or shot.get("format") != "plush.scene":
        raise SetError("shot: not a plush.scene file")
    out = copy.deepcopy(shot)
    shot_objects = shot.get("objects", [])
    by_name = {o.get("name"): o for o in shot_objects}
    missing = [n for n in s.get("keep_objects", []) if n not in by_name]
    if missing:
        raise SetError(f"set.keep_objects: not in the shot: {missing}")
    keep = [copy.deepcopy(o) for o in shot_objects if o.get("name") in set(s.get("keep_objects", []))]
    clash = sorted({o["name"] for o in s["objects"]} & {o.get("name") for o in shot_objects})
    if clash:
        raise SetError(f"set objects would shadow shot objects: {clash}")
    set_objects = [{"name": o["name"], "kind": "box", "min": [_r(x) for x in o["min"]],
                    "max": [_r(x) for x in o["max"]], "material": o["material"]} for o in s["objects"]]
    out["objects"] = keep + set_objects
    set_mats = {m["name"]: m for m in s["materials"]}
    used = []
    for o in keep:
        if o.get("material") and o["material"] not in used:
            used.append(o["material"])
    shot_mats = {m.get("name"): m for m in shot.get("materials", [])}
    mats = []
    for n in used:
        if n in set_mats:
            mats.append(copy.deepcopy(set_mats[n]))
        elif n in shot_mats:
            mats.append(copy.deepcopy(shot_mats[n]))
        else:
            raise SetError(f"kept object material {n!r} is neither in the shot nor in the set")
    mats += [copy.deepcopy(m) for m in s["materials"] if m["name"] not in used]
    out["materials"] = mats
    out["lights"] = [scene_light(l) for l in s["lights"]]
    cam = copy.deepcopy(shot.get("camera"))
    if not isinstance(cam, dict) or "position" not in cam or "target" not in cam:
        raise SetError("shot: camera needs position and target")
    focus = cam["target"] if s["camera"]["focus"] == "target" else s["camera"]["focus"]
    cam["fStop"] = _r(s["camera"]["fStop"])
    cam["focusDistance"] = _r(math.dist(cam["position"], focus))
    out["camera"] = cam
    if "exposureEV" in s.get("render", {}):
        out.setdefault("render", {})["exposureEV"] = _r(s["render"]["exposureEV"])
    out["name"] = f"{shot.get('name', 'shot')} | set {s['id']}"
    groups = {}
    for o in s["objects"]:
        groups.setdefault(o["group"], []).append(o["name"])
    out["x_set"] = {"set": s["id"], "set_sha256": canonical_sha(s), "source_shot_sha256": canonical_sha(shot),
                    "kept_objects": [o["name"] for o in keep],
                    "replaced_objects": [o.get("name") for o in shot_objects if o.get("name") not in set(s.get("keep_objects", []))],
                    "replaced_lights": len(shot.get("lights", [])), "groups": groups,
                    "lights": [l["name"] for l in s["lights"]],
                    "camera_preset": {"name": s["camera"]["name"], "fStop": cam["fStop"],
                                      "focusDistance": cam["focusDistance"]}}
    if "blender_light_rig" in s:  # (no key without a rig: outputs of rig-less sets stay byte-identical)
        out["x_set"]["light_rig"] = s["blender_light_rig"]
    return out


def dumps(d):
    return json.dumps(d, indent=1, ensure_ascii=False) + "\n"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--set", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--set", required=True)
    a.add_argument("--shot", required=True)
    a.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        s = validate(load(args.set))
        if args.cmd == "validate":
            print(f"[sets] {args.set}: ok ({len(s['objects'])} objects, {len(s['lights'])} lights)")
            return 0
        text = dumps(apply(s, load(args.shot)))
    except SetError as e:
        print(f"[sets] refused: {e}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[sets] wrote {args.out} (sha256 {hashlib.sha256(text.encode()).hexdigest()[:16]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
