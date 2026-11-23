"""Set light rigs for the Blender render (T-221, T-196 Q4). Pure Python (no bpy): schema, lookup and the shot's pick.

Final renders light a shot with a Blender light rig named by the set (or picked by the shot) instead of translating
the engine's lights; the engine's lights stay for engine previews. A shot without a rig renders exactly as before.

Rig file: content/sets/rigs/<id>.light_rig.json (plush.light_rig/1). Blender world axes (+Z up, metres) and
Blender units, so a rig built or tuned in Blender is saved as-is (set_lights_blender.py dump):

  {"format": "plush.light_rig", "version": 1, "id": "<id>", "description": "...",
   "lights": [
     {"name", "type": "area", "location": [x,y,z], "aim": [x,y,z] | "rotation_deg": [rx,ry,rz],
      "shape": "RECTANGLE"|"SQUARE"|"DISK"|"ELLIPSE", "size": [w, h] (SQUARE/DISK: [s]), "energy": W, "color": [r,g,b]},
     {"name", "type": "sun", "direction": [x,y,z] (the way the light travels) | "rotation_deg", "strength": W/m^2,
      "angle_deg": a, "color"},
     {"name", "type": "point", "location", "radius": m, "energy": W, "color"},
     {"name", "type": "spot", "location", "aim" | "rotation_deg", "radius", "spot_size_deg", "spot_blend", "energy",
      "color"}],
   "world": {"color": [r,g,b], "strength": s}  or  {"hdri": "<path relative to the rig file>", "strength": s,
             "rotation_deg": z}                (optional; absent = black world, strength 0)}
Optional per light: "cast_shadow" (bool, default true). Unknown keys are refused.

Which rig a shot uses (first that applies): shot_render --light-rig <id|path|engine>, the scene's top-level
"x_light_rig" (<id> or "engine"), the set's "blender_light_rig" recorded by sets.py apply as x_set.light_rig, none.
"engine" (or none) keeps the engine-light translation exactly as before T-221."""
import json
import math
import os

FORMAT, VERSION = "plush.light_rig", 1
ENGINE = "engine"  # the pick that keeps today's engine-light translation
RIG_DIR = os.path.join("content", "sets", "rigs")
SUFFIX = ".light_rig.json"
TOP_KEYS = {"format", "version", "id", "description", "lights", "world"}
COMMON = {"name", "type", "color", "cast_shadow"}
LIGHT_KEYS = {"area": COMMON | {"location", "aim", "rotation_deg", "shape", "size", "energy"},
              "sun": COMMON | {"direction", "rotation_deg", "strength", "angle_deg"},
              "point": COMMON | {"location", "radius", "energy"},
              "spot": COMMON | {"location", "aim", "rotation_deg", "radius", "spot_size_deg", "spot_blend", "energy"}}
LIGHT_REQUIRED = {"area": {"location", "shape", "size", "energy"}, "sun": {"strength"},
                  "point": {"location", "energy"}, "spot": {"location", "energy", "spot_size_deg"}}
AREA_SHAPES = {"RECTANGLE": 2, "ELLIPSE": 2, "SQUARE": 1, "DISK": 1}
WORLD_KEYS = {"color", "strength", "hdri", "rotation_deg"}


class RigError(ValueError):
    pass


def _num(where, v, lo=None, hi=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise RigError(f"{where}: must be a finite number")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise RigError(f"{where}: {v} outside [{lo}, {hi}]")
    return float(v)


def _vec(where, v, n=3, lo=None, hi=None):
    if not isinstance(v, list) or len(v) != n:
        raise RigError(f"{where}: must be a list of {n} numbers")
    return [_num(f"{where}[{i}]", x, lo, hi) for i, x in enumerate(v)]


def _name(where, v):
    if not isinstance(v, str) or not v or v.strip() != v or "/" in v or "\\" in v:
        raise RigError(f"{where}: must be a non-empty name without slashes")
    return v


def _keys(where, d, allowed, required):
    if not isinstance(d, dict):
        raise RigError(f"{where}: must be an object")
    unknown = sorted(set(d) - allowed)
    if unknown:
        raise RigError(f"{where}: unknown key(s) {unknown}")
    missing = sorted(required - set(d))
    if missing:
        raise RigError(f"{where}: missing key(s) {missing}")


def validate(rig):
    """Raises RigError on any schema problem; returns the rig unchanged."""
    _keys("rig", rig, TOP_KEYS, {"format", "version", "id", "lights"})
    if rig["format"] != FORMAT or rig["version"] != VERSION:
        raise RigError(f"rig: not a {FORMAT}/{VERSION} file")
    _name("rig.id", rig["id"])
    if rig["id"] == ENGINE:
        raise RigError(f"rig.id: {ENGINE!r} is reserved (the engine-light translation)")
    if "description" in rig and not isinstance(rig["description"], str):
        raise RigError("rig.description: must be a string")
    if not isinstance(rig["lights"], list):
        raise RigError("rig.lights: must be a list")
    names = set()
    for i, l in enumerate(rig["lights"]):
        w = f"rig.lights[{i}]"
        if not isinstance(l, dict) or l.get("type") not in LIGHT_KEYS:
            raise RigError(f"{w}.type: must be one of {sorted(LIGHT_KEYS)}")
        t = l["type"]
        _keys(w, l, LIGHT_KEYS[t], LIGHT_REQUIRED[t] | {"name", "color"})
        n = _name(f"{w}.name", l["name"])
        if n in names:
            raise RigError(f"{w}: duplicate light name {n!r}")
        names.add(n)
        _vec(f"{w}.color", l["color"], 3, 0.0, None)
        if "cast_shadow" in l and not isinstance(l["cast_shadow"], bool):
            raise RigError(f"{w}.cast_shadow: must be true or false")
        if "location" in l:
            _vec(f"{w}.location", l["location"])
        orient = [k for k in ("aim", "rotation_deg", "direction") if k in l]
        if t in ("area", "spot", "sun") and len(orient) != 1:
            need = "direction | rotation_deg" if t == "sun" else "aim | rotation_deg"
            raise RigError(f"{w}: exactly one of {need}")
        if "aim" in l and math.dist(_vec(f"{w}.aim", l["aim"]), l["location"]) < 1e-9:
            raise RigError(f"{w}.aim: must differ from location")
        if "rotation_deg" in l:
            _vec(f"{w}.rotation_deg", l["rotation_deg"])
        if "direction" in l and math.hypot(*_vec(f"{w}.direction", l["direction"])) < 1e-9:
            raise RigError(f"{w}.direction: must not be zero")
        if "energy" in l:
            _num(f"{w}.energy", l["energy"], 0.0)
        if t == "area":
            if l["shape"] not in AREA_SHAPES:
                raise RigError(f"{w}.shape: must be one of {sorted(AREA_SHAPES)}")
            sz = _vec(f"{w}.size", l["size"], AREA_SHAPES[l["shape"]])
            if min(sz) <= 0:
                raise RigError(f"{w}.size: must be positive")
        if t == "sun":
            _num(f"{w}.strength", l["strength"], 0.0)
            if "angle_deg" in l:
                _num(f"{w}.angle_deg", l["angle_deg"], 0.0, 180.0)
        if "radius" in l:
            _num(f"{w}.radius", l["radius"], 0.0)
        if t == "spot":
            _num(f"{w}.spot_size_deg", l["spot_size_deg"], 1.0, 180.0)
            if "spot_blend" in l:
                _num(f"{w}.spot_blend", l["spot_blend"], 0.0, 1.0)
    if "world" in rig:
        wd = rig["world"]
        _keys("rig.world", wd, WORLD_KEYS, {"strength"})
        _num("rig.world.strength", wd["strength"], 0.0)
        if ("hdri" in wd) == ("color" in wd):
            raise RigError("rig.world: exactly one of color | hdri")
        if "color" in wd:
            _vec("rig.world.color", wd["color"], 3, 0.0, None)
            if "rotation_deg" in wd:
                raise RigError("rig.world.rotation_deg: only with hdri")
        else:
            if not isinstance(wd["hdri"], str) or not wd["hdri"] or os.path.isabs(wd["hdri"]):
                raise RigError("rig.world.hdri: must be a path relative to the rig file")
            if "rotation_deg" in wd:
                _num("rig.world.rotation_deg", wd["rotation_deg"])
    if not rig["lights"] and "world" not in rig:
        raise RigError("rig: needs at least one light or a world")
    return rig


def load(path):
    """Loads and validates a rig file; the result carries "_path" (absolute) for relative HDRI paths."""
    try:
        with open(path, encoding="utf-8") as f:
            rig = json.load(f)
    except (OSError, ValueError) as e:
        raise RigError(f"{path}: cannot read rig ({e})") from None
    validate(rig)
    if os.path.basename(path) != rig["id"] + SUFFIX:
        raise RigError(f"{path}: file name must be {rig['id']}{SUFFIX}")
    rig = dict(rig)
    rig["_path"] = os.path.abspath(path)
    return rig


def hdri_path(rig):
    wd = rig.get("world") or {}
    if "hdri" not in wd:
        return None
    return os.path.normpath(os.path.join(os.path.dirname(rig["_path"]), wd["hdri"]))


def rig_dirs(scene_path=None):
    """content/sets/rigs folders to search: the nearest above the scene, then this repository's."""
    out = []
    if scene_path:
        d = os.path.dirname(os.path.abspath(scene_path))
        while True:
            c = os.path.join(d, RIG_DIR)
            if os.path.isdir(c) and c not in out:
                out.append(c)
                break
            if os.path.dirname(d) == d:
                break
            d = os.path.dirname(d)
    own = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", RIG_DIR))
    if own not in out:
        out.append(own)
    return out


def available(dirs):
    names = set()
    for d in dirs:
        if os.path.isdir(d):
            names |= {n[:-len(SUFFIX)] for n in os.listdir(d) if n.endswith(SUFFIX)}
    return sorted(names)


def find(name, scene_path=None):
    """A rig by id (searched in rig_dirs) or by path to a .light_rig.json file. Unknown -> RigError (lists rigs)."""
    if name.endswith(SUFFIX) and os.path.isfile(name):
        return load(name)
    _name("light rig", name)
    dirs = rig_dirs(scene_path)
    for d in dirs:
        p = os.path.join(d, name + SUFFIX)
        if os.path.isfile(p):
            return load(p)
    raise RigError(f"light rig {name!r} not found in {dirs} (available: {available(dirs) or 'none'})")


def pick(scene, cli=None):
    """The rig name a shot asks for: (name or None, source). None means no rig (the engine-light translation)."""
    if cli:
        name, src = cli, "--light-rig"
    elif isinstance(scene, dict) and scene.get("x_light_rig") is not None:
        name, src = scene["x_light_rig"], "scene x_light_rig"
    elif isinstance(scene, dict) and isinstance(scene.get("x_set"), dict) and scene["x_set"].get("light_rig"):
        name, src = scene["x_set"]["light_rig"], f"set {scene['x_set'].get('set')}"
    else:
        return None, "none"
    if not isinstance(name, str) or not name:
        raise RigError(f"{src}: light rig must be a non-empty string")
    return (None if name == ENGINE else name), src


def resolve(scene_path, cli=None):
    """(rig dict or None, report) for a baked scene. A missing or unreadable scene file means no pick from it."""
    scene = None
    if scene_path:
        try:
            with open(scene_path, encoding="utf-8") as f:
                scene = json.load(f)
        except (OSError, ValueError):
            scene = None
    name, src = pick(scene, cli)
    if name is None:
        return None, {"rig": None, "source": src}
    rig = find(name, scene_path)
    return rig, {"rig": rig["id"], "source": src, "file": rig["_path"], "lights": [l["name"] for l in rig["lights"]],
                 "world": ("hdri" if "hdri" in rig.get("world", {}) else "color" if "world" in rig else "none")}
