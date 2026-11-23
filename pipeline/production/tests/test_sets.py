"""T-098L tests: sets as data (pipeline/production/sets.py). Fast: no Blender, no engine.

    python3 pipeline/production/tests/test_sets.py

1. Schema: every set in content/sets validates; broken sets (wrong format, bad numbers, min >= max, unknown
   material, duplicate names, two skies, bad camera framing) are refused.
2. Unknown keys are refused at every level (set, material, object, light, camera, render).
3. Deterministic output: applying the same set to the same shot twice gives byte-identical text; the inputs are not
   mutated; the CLI writes exactly that text.
4. Apply rules: kept objects are copied unchanged, other shot objects and all shot lights are replaced, a set
   material restyles a kept object's material, characters/props/actions/production are unchanged, the camera keeps
   its framing and gets depth of field focused at its target, a rect light emits from its center towards its aim.
5. Refusals on apply: a kept object missing in the shot, a set object named like a shot object, a non-scene shot.
6. Blender light rig (T-221): a set may name a rig (blender_light_rig: an id, not a path, not 'engine'); apply
   records it as x_set.light_rig; a set without one gives exactly the pre-T-221 output (no light_rig key)."""
import copy
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAILS = []


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sets = load("sets", "pipeline/production/sets.py")


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def refused(fn, *args, contains=""):
    try:
        fn(*args)
    except sets.SetError as e:
        return contains in str(e)
    return False


SET = {
    "format": "plush.set", "version": 1, "id": "fixture",
    "keep_objects": ["table"],
    "materials": [{"name": "table_mat", "type": "standard", "baseColor": [0.5, 0.4, 0.3], "roughness": 0.7},
                  {"name": "wall", "type": "standard", "baseColor": [0.8, 0.7, 0.6]}],
    "objects": [{"name": "back", "group": "wall", "min": [-2, 0, -1.1], "max": [2, 2, -1.0], "material": "wall"}],
    "lights": [{"name": "key", "type": "rect", "center": [-1.0, 1.0, 1.0], "aim": [0, 0.5, 0], "size": [1.0, 0.5],
                "color": [1, 0.9, 0.8], "intensity": 2.0},
               {"name": "sun", "type": "sun", "direction": [0, -2, -1], "angleDeg": 3, "color": [1, 1, 1],
                "intensity": 1.0},
               {"name": "sky", "type": "sky", "color": [0.9, 0.9, 1.0], "intensity": 0.5}],
    "camera": {"name": "dof", "framing": "keep", "fStop": 2.0, "focus": "target"},
    "render": {"exposureEV": -0.5},
}
SHOT = {
    "format": "plush.scene", "version": 1, "name": "fixture shot", "frameStart": 1, "frameEnd": 10,
    "render": {"width": 64, "height": 36, "exposureEV": 0.3},
    "camera": {"position": [0.0, 1.0, 2.0], "target": [0.0, 1.0, 0.0], "focalMm": 35.0, "fStop": 0,
               "focusDistance": -1},
    "materials": [{"name": "floor_mat", "type": "standard", "baseColor": [0.4, 0.4, 0.4]},
                  {"name": "table_mat", "type": "standard", "baseColor": [0.4, 0.3, 0.2]}],
    "lights": [{"type": "sky", "color": [0.6, 0.6, 0.6], "intensity": 0.4}],
    "objects": [{"name": "floor", "kind": "box", "min": [-4, -0.05, -3], "max": [4, 0, 4], "material": "floor_mat"},
                {"name": "table", "kind": "box", "min": [-0.1, 0.4, -0.1], "max": [0.1, 0.45, 0.1],
                 "material": "table_mat"}],
    "props": [{"name": "cup", "id": "prop.felt_cup", "transform": {"translation": [0, 0.45, 0]}}],
    "characters": [{"name": "a", "asset": "x", "position": [0.3, 0, 0], "yawDeg": -20}],
    "actions": [{"type": "clip", "character": "a", "clip": "idle_relaxed", "base": True}],
    "production": {"cast": {"a": {"character_id": "a", "version": "current"}}},
}


def schema():
    files = sorted((ROOT / "content" / "sets").glob("*.set.json"))
    check(len(files) >= 1, f"content/sets holds set files ({len(files)})")
    for f in files:
        try:
            sets.validate(json.load(open(f)))
            check(True, f"{f.relative_to(ROOT)} validates")
        except sets.SetError as e:
            check(False, f"{f.relative_to(ROOT)} validates ({e})")
    check(sets.validate(copy.deepcopy(SET)) is not None, "fixture set validates")

    def broken(edit, contains, label):
        s = copy.deepcopy(SET)
        edit(s)
        check(refused(sets.validate, s, contains=contains), f"refused: {label}")

    broken(lambda s: s.update(format="plush.scene"), "plush.set/1", "wrong format")
    broken(lambda s: s.update(version=2), "plush.set/1", "wrong version")
    broken(lambda s: s.pop("camera"), "missing", "missing camera")
    broken(lambda s: s["objects"][0].update(min=[3, 0, 0]), "min must be below max", "min >= max")
    broken(lambda s: s["objects"][0].update(material="nope"), "not a set material", "unknown material")
    broken(lambda s: s["objects"].append(dict(s["objects"][0])), "duplicate object", "duplicate object")
    broken(lambda s: s["objects"][0].update(name="table"), "duplicate object", "set object named like a kept one")
    broken(lambda s: s["materials"].append(dict(s["materials"][0])), "duplicate material", "duplicate material")
    broken(lambda s: s["materials"][0].update(baseColor=[1.5, 0, 0]), "outside", "colour above 1")
    broken(lambda s: s["materials"][0].update(type="glass"), "standard", "non-standard material")
    broken(lambda s: s["lights"][0].update(intensity=float("nan")), "finite", "NaN intensity")
    broken(lambda s: s["lights"][0].update(size=[1.0, 0.0]), "positive", "zero light size")
    broken(lambda s: s["lights"][0].update(aim=[-1.0, 1.0, 1.0]), "aim must differ", "aim == center")
    broken(lambda s: s["lights"][0].update(type="spot"), "type", "unknown light type")
    broken(lambda s: s["lights"].append(dict(s["lights"][2], name="sky2")), "at most one sky", "two skies")
    broken(lambda s: s["camera"].update(framing="new"), "keep", "camera framing other than keep")
    broken(lambda s: s["camera"].update(fStop=0), "outside", "fStop 0")
    broken(lambda s: s["camera"].update(focus=[0, 1]), "3 numbers", "bad focus point")
    broken(lambda s: s["objects"][0].update(min=[0, True, 0]), "finite", "boolean coordinate")


def unknown_keys():
    cases = [("set", lambda s: s.update(extra=1)),
             ("material", lambda s: s["materials"][0].update(metallic=1.0)),
             ("object", lambda s: s["objects"][0].update(kind="sdf")),
             ("rect light", lambda s: s["lights"][0].update(spread=30)),
             ("sun light", lambda s: s["lights"][1].update(center=[0, 0, 0])),
             ("sky light", lambda s: s["lights"][2].update(texture="hdri.exr")),
             ("camera", lambda s: s["camera"].update(position=[0, 0, 0])),
             ("render", lambda s: s["render"].update(samples=64))]
    for label, edit in cases:
        s = copy.deepcopy(SET)
        edit(s)
        check(refused(sets.validate, s, contains="unknown key"), f"unknown key refused in {label}")
        check(refused(sets.apply, s, copy.deepcopy(SHOT), contains="unknown key"),
              f"unknown key refused by apply ({label})")


def deterministic():
    s, shot = copy.deepcopy(SET), copy.deepcopy(SHOT)
    a = sets.dumps(sets.apply(s, shot))
    b = sets.dumps(sets.apply(copy.deepcopy(SET), copy.deepcopy(SHOT)))
    check(a == b, "apply twice: byte-identical text")
    check(s == SET and shot == SHOT, "apply does not mutate its inputs")
    with tempfile.TemporaryDirectory() as d:
        sp, hp, op = (os.path.join(d, n) for n in ("s.json", "shot.json", "out/new.json"))
        json.dump(SET, open(sp, "w"))
        json.dump(SHOT, open(hp, "w"))
        hp_text = open(hp).read()
        r = subprocess.run([sys.executable, str(ROOT / "pipeline/production/sets.py"), "apply", "--set", sp,
                            "--shot", hp, "--out", op], capture_output=True, text=True)
        check(r.returncode == 0 and open(op).read() == a, "CLI apply writes the same text")
        check(open(hp).read() == hp_text, "CLI leaves the input shot file unchanged")
        bad = dict(SET, extra=True)
        json.dump(bad, open(sp, "w"))
        r = subprocess.run([sys.executable, str(ROOT / "pipeline/production/sets.py"), "validate", "--set", sp],
                           capture_output=True, text=True)
        check(r.returncode == 2 and "unknown key" in r.stderr, "CLI refuses an unknown key (exit 2)")
    for f in sorted((ROOT / "content" / "sets").glob("*.set.json")):
        repo = json.load(open(f))
        x = sets.dumps(sets.apply(repo, copy.deepcopy(SHOT) | {"objects": [o for o in SHOT["objects"]] + [
            {"name": n, "kind": "box", "min": [0, 0, 0], "max": [0.1, 0.1, 0.1], "material": "table_mat"}
            for n in repo.get("keep_objects", []) if n != "table"]}))
        check(x.endswith("\n") and json.loads(x)["x_set"]["set"] == repo["id"], f"{f.name} applies to a fixture shot")


def rules():
    out = sets.apply(copy.deepcopy(SET), copy.deepcopy(SHOT))
    names = [o["name"] for o in out["objects"]]
    check(names == ["table", "back"], f"objects: kept table + set objects, floor replaced ({names})")
    check(out["objects"][0] == SHOT["objects"][1], "kept object copied unchanged")
    check(all(o.get("kind") == "box" and "group" not in o for o in out["objects"]), "set objects are plain boxes")
    mats = {m["name"]: m for m in out["materials"]}
    check(mats["table_mat"]["baseColor"] == [0.5, 0.4, 0.3], "set material restyles the kept table")
    check("floor_mat" not in mats and "wall" in mats, "unused shot material dropped, set material added")
    check([l["type"] for l in out["lights"]] == ["rect", "sun", "sky"], "shot lights replaced by the set rig")
    for k in ("characters", "props", "actions", "production", "frameStart", "frameEnd"):
        check(out[k] == SHOT[k], f"{k} unchanged")
    cam = out["camera"]
    check(all(cam[k] == SHOT["camera"][k] for k in ("position", "target", "focalMm")), "camera framing kept")
    check(cam["fStop"] == 2.0 and abs(cam["focusDistance"] - 2.0) < 1e-9, "depth of field focused at the target")
    check(out["render"]["exposureEV"] == -0.5 and out["render"]["width"] == 64, "render: exposure set, rest kept")
    r = out["lights"][0]
    u, v = r["edgeU"], r["edgeV"]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    centre = [c + 0.5 * a + 0.5 * b for c, a, b in zip(r["corner"], u, v)]
    to_aim = [a - c for a, c in zip(SET["lights"][0]["aim"], centre)]
    cos = sum(x * y for x, y in zip(n, to_aim)) / (math.hypot(*n) * math.hypot(*to_aim))
    check(cos > 0.999, f"rect light emits from its center towards its aim (cos {cos:.4f})")
    check(abs(math.hypot(*u) - 1.0) < 1e-3 and abs(math.hypot(*v) - 0.5) < 1e-3 and abs(u[1]) < 1e-9,
          "rect light size kept, edgeU horizontal")
    check(all(abs(c - e) < 1e-3 for c, e in zip(centre, SET["lights"][0]["center"])), "rect light centred")
    x = out["x_set"]
    check(x["kept_objects"] == ["table"] and x["replaced_objects"] == ["floor"] and x["replaced_lights"] == 1,
          "x_set records kept and replaced objects")
    check(x["groups"] == {"wall": ["back"]} and x["lights"] == ["key", "sun", "sky"], "x_set records groups, lights")


def apply_refusals():
    check(refused(sets.apply, dict(SET, keep_objects=["missing"]), copy.deepcopy(SHOT), contains="not in the shot"),
          "refused: kept object missing in the shot")
    s = copy.deepcopy(SET)
    s["objects"][0]["name"] = "floor"
    check(refused(sets.apply, s, copy.deepcopy(SHOT), contains="shadow"), "refused: set object named like a shot object")
    check(refused(sets.apply, copy.deepcopy(SET), {"format": "plush.set"}, contains="plush.scene"),
          "refused: shot that is not a plush.scene")
    shot = copy.deepcopy(SHOT)
    del shot["camera"]["target"]
    check(refused(sets.apply, copy.deepcopy(SET), shot, contains="camera"), "refused: shot camera without target")


def light_rig():
    plain = sets.dumps(sets.apply(copy.deepcopy(SET), copy.deepcopy(SHOT)))
    check("light_rig" not in json.loads(plain)["x_set"], "set without a rig: no x_set.light_rig (output as before)")
    s = dict(copy.deepcopy(SET), blender_light_rig="fixture_rig")
    check(sets.validate(s) is s, "set with blender_light_rig validates")
    out = sets.apply(s, copy.deepcopy(SHOT))
    check(out["x_set"]["light_rig"] == "fixture_rig", "apply records the set's rig as x_set.light_rig")
    check(out["lights"] == json.loads(plain)["lights"], "the set's engine lights are still written (engine previews)")
    for bad, label in (("", "empty"), ("a/b", "a path"), ("engine", "'engine'"), (3, "not a string")):
        check(refused(sets.validate, dict(copy.deepcopy(SET), blender_light_rig=bad), contains="blender_light_rig"),
              f"refused: blender_light_rig {label}")


def main():
    schema()
    unknown_keys()
    deterministic()
    rules()
    apply_refusals()
    light_rig()
    print(f"\n{'FAILED' if FAILS else 'PASSED'}: {len(FAILS)} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
