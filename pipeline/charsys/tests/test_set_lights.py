"""T-221 tests: set light rigs, pure part (pipeline/charsys/set_lights.py). Fast: no Blender, no engine.

    python3 pipeline/charsys/tests/test_set_lights.py

1. Rig loading: every rig in content/sets/rigs validates and is found by id and by path; every set naming a
   blender_light_rig names an existing rig.
2. Schema: broken rigs (wrong format, reserved id, duplicate names, missing/extra orientation, bad shape size,
   negative energy, world with both colour and HDRI, absolute HDRI path, file name != id) are refused; unknown keys
   are refused at every level (rig, light, world).
3. Name picking: --light-rig > scene x_light_rig > x_set.light_rig > none; "engine" means no rig; a scene without
   any pick (and an unreadable scene) resolves to no rig (the pre-T-221 path).
4. Missing rig: an unknown name is refused with the searched folders and the available rigs listed.
Exit code 1 on any failure."""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline" / "charsys"))
import set_lights as SL  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def refused(fn, *args, contains=""):
    try:
        fn(*args)
    except SL.RigError as e:
        if contains not in str(e):
            print(f"     (message was: {e})")
        return contains in str(e)
    return False


RIG = {
    "format": "plush.light_rig", "version": 1, "id": "fixture_rig", "description": "test",
    "lights": [
        {"name": "key", "type": "area", "location": [-1, -1, 1.5], "aim": [0, 0, 1], "shape": "RECTANGLE",
         "size": [1.0, 0.5], "energy": 80.0, "color": [1, 0.9, 0.8]},
        {"name": "sun", "type": "sun", "direction": [0.2, 0.5, -1], "strength": 3.0, "angle_deg": 2, "color": [1, 1, 1]},
        {"name": "bulb", "type": "point", "location": [0, 1, 2], "radius": 0.1, "energy": 20, "color": [1, 1, 1],
         "cast_shadow": False},
        {"name": "spot", "type": "spot", "location": [1, -2, 2], "rotation_deg": [45, 0, 30], "spot_size_deg": 40,
         "spot_blend": 0.2, "energy": 50, "color": [1, 1, 1]},
    ],
    "world": {"color": [0.5, 0.5, 0.6], "strength": 0.3},
}


def rigs_in_repo():
    d = ROOT / SL.RIG_DIR
    files = sorted(d.glob("*" + SL.SUFFIX))
    check(len(files) >= 1, f"content/sets/rigs holds rigs ({len(files)})")
    for f in files:
        r = SL.load(str(f))
        check(r["id"] + SL.SUFFIX == f.name and r["_path"] == str(f), f"{f.name}: loads and validates")
        check(SL.find(r["id"])["_path"] == str(f), f"{f.name}: found by id")
        check(SL.find(str(f))["id"] == r["id"], f"{f.name}: found by path")
    for s in sorted((ROOT / "content" / "sets").glob("*.set.json")):
        j = json.loads(s.read_text())
        if "blender_light_rig" in j:
            check((d / (j["blender_light_rig"] + SL.SUFFIX)).is_file(), f"{s.name}: its rig {j['blender_light_rig']} exists")
    wtc = json.loads((ROOT / "content/sets/water_table_corner.set.json").read_text())
    check(wtc.get("blender_light_rig") == "water_table_corner_window", "water_table_corner names its starting rig")


def schema():
    check(SL.validate(copy.deepcopy(RIG)) is not None, "fixture rig validates (all four light types, colour world)")
    hd = copy.deepcopy(RIG)
    hd["world"] = {"hdri": "hdri/room.hdr", "strength": 1.0, "rotation_deg": 90}
    check(SL.validate(hd) is not None, "HDRI world validates")
    check(SL.validate({"format": "plush.light_rig", "version": 1, "id": "w", "lights": [],
                       "world": {"color": [1, 1, 1], "strength": 1}}) is not None, "world-only rig validates")

    def broken(edit, contains, label):
        r = copy.deepcopy(RIG)
        edit(r)
        check(refused(SL.validate, r, contains=contains), f"refused: {label}")

    broken(lambda r: r.update(format="plush.set"), "not a plush.light_rig", "wrong format")
    broken(lambda r: r.update(version=2), "not a plush.light_rig", "wrong version")
    broken(lambda r: r.update(id="engine"), "reserved", "id 'engine'")
    broken(lambda r: r.update(id="a/b"), "slashes", "id with a slash")
    broken(lambda r: r["lights"][1].update(name="key"), "duplicate light", "duplicate light names")
    broken(lambda r: r["lights"][0].pop("aim"), "exactly one of aim | rotation_deg", "area without orientation")
    broken(lambda r: r["lights"][0].update(rotation_deg=[0, 0, 0]), "exactly one of", "area with aim and rotation")
    broken(lambda r: r["lights"][1].pop("direction"), "direction | rotation_deg", "sun without orientation")
    broken(lambda r: r["lights"][0].update(aim=[-1, -1, 1.5]), "must differ", "aim == location")
    broken(lambda r: r["lights"][1].update(direction=[0, 0, 0]), "must not be zero", "zero sun direction")
    broken(lambda r: r["lights"][0].update(shape="SQUARE"), "list of 1", "square with two sizes")
    broken(lambda r: r["lights"][0].update(shape="HEX"), "shape", "unknown area shape")
    broken(lambda r: r["lights"][0].update(size=[1.0, 0.0]), "positive", "zero area size")
    broken(lambda r: r["lights"][0].update(energy=-1), "outside", "negative energy")
    broken(lambda r: r["lights"][0].update(color=[1, 1]), "list of 3", "colour with two channels")
    broken(lambda r: r["lights"][2].update(cast_shadow=1), "true or false", "non-boolean cast_shadow")
    broken(lambda r: r["lights"][3].update(spot_size_deg=0.5), "outside", "spot size below 1 deg")
    broken(lambda r: r["lights"][0].update(type="rect"), "type", "engine light type in a rig")
    broken(lambda r: r["world"].update(hdri="x.hdr"), "exactly one of color | hdri", "world with colour and HDRI")
    broken(lambda r: r.update(world={"hdri": "/abs/x.hdr", "strength": 1}), "relative", "absolute HDRI path")
    broken(lambda r: r.update(world={"color": [1, 1, 1], "strength": 1, "rotation_deg": 3}), "only with hdri",
           "world rotation without HDRI")
    broken(lambda r: r.update(lights=[], world=None) or r.pop("world"), "at least one", "rig with nothing")
    for where, edit in (("rig", lambda r: r.update(extra=1)), ("light", lambda r: r["lights"][0].update(intensity=2)),
                        ("sun", lambda r: r["lights"][1].update(energy=2)),
                        ("world", lambda r: r["world"].update(exposure=1))):
        broken(edit, "unknown key", f"unknown key in {where}")
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "other_name" + SL.SUFFIX)
        Path(p).write_text(json.dumps(RIG))
        check(refused(SL.load, p, contains="file name must be"), "refused: file name differs from the rig id")
        p = os.path.join(t, "bad" + SL.SUFFIX)
        Path(p).write_text("{not json")
        check(refused(SL.load, p, contains="cannot read"), "refused: unreadable rig file")


def picking():
    x_set = {"set": "s", "light_rig": "from_set"}
    check(SL.pick({}, None) == (None, "none"), "no pick: none")
    check(SL.pick(None, None) == (None, "none"), "no scene: none")
    check(SL.pick({"x_set": {"set": "s"}}, None) == (None, "none"), "set without a rig: none")
    check(SL.pick({"x_set": x_set}, None) == ("from_set", "set s"), "set rig is the default")
    check(SL.pick({"x_set": x_set, "x_light_rig": "shot_rig"}, None)[0] == "shot_rig", "shot x_light_rig beats the set")
    check(SL.pick({"x_set": x_set, "x_light_rig": "engine"}, None)[0] is None, "x_light_rig 'engine' turns the rig off")
    check(SL.pick({"x_set": x_set, "x_light_rig": "shot_rig"}, "cli_rig")[0] == "cli_rig", "--light-rig beats all")
    check(SL.pick({"x_set": x_set}, "engine")[0] is None, "--light-rig engine turns the rig off")
    check(refused(SL.pick, {"x_light_rig": 3}, None, contains="non-empty string"), "refused: non-string pick")
    with tempfile.TemporaryDirectory() as t:
        rigs = Path(t) / SL.RIG_DIR
        rigs.mkdir(parents=True)
        r = copy.deepcopy(RIG)
        (rigs / ("fixture_rig" + SL.SUFFIX)).write_text(json.dumps(r))
        shot = Path(t) / "ep" / "build" / "shot.resolved.scene.json"
        shot.parent.mkdir(parents=True)
        shot.write_text(json.dumps({"format": "plush.scene", "x_light_rig": "fixture_rig"}))
        rig, rep = SL.resolve(str(shot))
        check(rig is not None and rig["_path"] == str(rigs / ("fixture_rig" + SL.SUFFIX)),
              "resolve: the rig next to the scene's content/sets/rigs is found first")
        check(rep == {"rig": "fixture_rig", "source": "scene x_light_rig", "file": rig["_path"],
                      "lights": ["key", "sun", "bulb", "spot"], "world": "color"}, "resolve: report")
        r["world"] = {"hdri": "../hdri/room.hdr", "strength": 1}
        (rigs / ("fixture_rig" + SL.SUFFIX)).write_text(json.dumps(r))
        check(SL.hdri_path(SL.find("fixture_rig", str(shot))) == os.path.join(t, "content", "sets", "hdri", "room.hdr"),
              "HDRI path is relative to the rig file")
        shot.write_text(json.dumps({"format": "plush.scene"}))
        check(SL.resolve(str(shot)) == (None, {"rig": None, "source": "none"}), "resolve: no pick -> no rig (as before)")
        check(SL.resolve(str(Path(t) / "missing.json")) == (None, {"rig": None, "source": "none"}),
              "resolve: unreadable scene -> no rig")
        check(SL.resolve(None) == (None, {"rig": None, "source": "none"}), "resolve: bake without scene_path -> no rig")
        shot.write_text(json.dumps({"format": "plush.scene", "x_light_rig": "nope"}))
        try:
            SL.resolve(str(shot))
            msg = ""
        except SL.RigError as e:
            msg = str(e)
        check("'nope' not found" in msg and "fixture_rig" in msg and "water_table_corner_window" in msg,
              "missing rig: refused, listing the available rigs")
        check(refused(SL.find, "../x", contains="slashes"), "refused: rig name with a path")


def main():
    rigs_in_repo()
    schema()
    picking()
    print(f"\n{'FAILED' if FAILS else 'PASSED'}: {len(FAILS)} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
