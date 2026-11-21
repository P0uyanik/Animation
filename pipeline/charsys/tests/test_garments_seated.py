"""T-184: the opt-in ``garment/3`` item field ``seated`` (``garments_v3/seated.py``, shorts / trousers).

    python3 pipeline/charsys/tests/test_garments_seated.py [--blender <exe>]

Checks (each line PASS/FAIL; exit code 1 on any FAIL):
  plain     (no Blender) no file under assets/ uses the field (released specs, packages and candidates are
            unchanged); the two T-184 evidence overrides load on the current specs and differ from them only by the
            field; the module names no character.
  validate  (Blender) ``true`` and full blocks validate on the current outfits; an unknown key, a wrong type, an
            out-of-range value, both parts switched off and the field on another item type are rejected; the
            garment/2 view of a block with the field is the block without it.
  bind      (Blender, a small synthetic body: one trunk, two legs, a shorts shell whose leg tubes were extruded
            from the trunk, so they are carried by it) without the field ``garment/3`` binds exactly like
            ``garment/2`` and reports nothing; with it, the leg tubes are carried by their own thigh, vertices over
            the shin keep their weights, vertices at the centre plane keep part of their old weights, and with both
            thighs bent 90 degrees no tube vertex is left inside a leg (without the field many are).
  collision (Blender, same body with the covered skin hidden) the collision weight is raised where bare leg skin
            comes within the radius in a hip bend (the front of the trunk tube), is not raised at the back, is
            never lowered, and the rig is left in its rest pose."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
CH = os.path.join(ROOT, "assets", "characters")
T184 = os.path.join(ROOT, "docs", "evaluation", "characters", "T-184")
CAST = {"girl": ("girl_auburn_bun_glasses", "0.14.0", "shorts"), "boy": ("boy_yellow_hoodie", "2.3.0", "trousers")}
FIELD = "seated"
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_garments_seated] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"),
          flush=True)


def spec_path(who):
    cid, version, _ = CAST[who]
    return os.path.join(CH, cid, "spec", f"{cid}.{version}.spec.json")


def override_path(who):
    return os.path.join(T184, "overrides", f"{CAST[who][0]}.T-184.override.json")


def has_key(d, key):
    if isinstance(d, dict):
        return key in d or any(has_key(v, key) for v in d.values())
    if isinstance(d, list):
        return any(has_key(v, key) for v in d)
    return False


def test_plain():
    import spec as S

    users = []
    for d, _, files in os.walk(os.path.join(ROOT, "assets")):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            try:
                doc = json.load(open(os.path.join(d, f), encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            if has_key(doc, FIELD):
                users.append(os.path.relpath(os.path.join(d, f), ROOT))
    check("no file under assets/ uses the field", not users, users[:5] or None)
    for who, (cid, version, item) in CAST.items():
        base, _ = S.load(spec_path(who))
        over, _ = S.load(spec_path(who), [override_path(who)])
        on = [g["name"] for g in over["clothing"]["garments"] if g.get(FIELD) not in (None, False)]
        for g in over["clothing"]["garments"]:
            g.pop(FIELD, None)
        check(f"{who}: the T-184 override switches the field on for [{item}] only and changes nothing else on "
              f"{version}", on == [item] and over == base, on)
    src = open(os.path.join(CHARSYS, "garments_v3", "seated.py"), encoding="utf-8").read().lower()
    named = [c for c in sorted(os.listdir(CH)) if c.lower() in src or c.split("_")[0] in src.split()]
    check("garments_v3/seated.py names no character", not named, named or None)


VALIDATE = r'''
import copy
import spec as S
from garments_v3 import core, seated
out = []
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
for who, spec_path, override, item in %r:
    block = S.load(spec_path, [override])[0]["clothing"]
    plain = S.load(spec_path)[0]["clothing"]
    out.append((f"{who}: the block with the field validates", not raises(lambda: core.validate(block))))
    out.append((f"{who}: the current block (no field) still validates", not raises(lambda: core.validate(plain))))
    view = core.v2_view(block)
    out.append((f"{who}: the garment/2 view is the view of the block without the field",
                view == core.v2_view(plain)))
    def with_value(value, name=item):
        b = copy.deepcopy(block)
        for g in b["garments"]:
            g.pop("seated", None)
            if g["name"] == name:
                g["seated"] = value
        return b
    full = {"leg_weights": {"centre_m": 0.008}, "collision": {"hip_deg": [60, 90], "radius_m": 0.02,
            "falloff_m": 0.02}, "leg_bone": "DEF-thigh.{side}", "fk_bone": "thigh_fk.{side}"}
    out.append((f"{who}: a full block validates", not raises(lambda: core.validate(with_value(full)))))
    out.append((f"{who}: one part off validates",
                not raises(lambda: core.validate(with_value({"collision": False})))))
    for label, value in (("a string", "yes"), ("an unknown key", {"knee": True}),
                         ("an unknown leg_weights key", {"leg_weights": {"center": 0.01}}),
                         ("centre_m out of range", {"leg_weights": {"centre_m": 0.5}}),
                         ("an empty hip_deg", {"collision": {"hip_deg": []}}),
                         ("a hip angle out of range", {"collision": {"hip_deg": [200]}}),
                         ("a bone pattern without {side}", {"leg_bone": "DEF-thigh.L"}),
                         ("both parts off", {"leg_weights": False, "collision": False})):
        out.append((f"{who}: {label} is rejected", raises(lambda: core.validate(with_value(value)))))
    other = next(g["name"] for g in block["garments"] if g["type"] not in ("shorts", "trousers"))
    out.append((f"{who}: the field on {other} is rejected", raises(lambda: core.validate(with_value(True, other)))))
RESULT["validate"] = out
'''

# A synthetic body in Blender axes (front -Y, left +X): trunk radius 0.08 (z 0.25..0.45), legs radius 0.03 at
# x = +-0.045 (z 0.02..0.27, knee at 0.14). Shell "shorts": a trunk tube (radius 0.09, z 0.26..0.40) and two leg tubes
# (radius 0.04, z 0.08..0.30). Every leg-tube vertex names a TRUNK vertex as its source, the fault T-184 corrects.
SCENE = r'''
import math
import bmesh
from mathutils import Matrix, Vector
from garments import generator as GEN
from garments_v2 import core as V2
from garments_v3 import core, seated

LEG_X, LEG_R, TUBE_R, TRUNK_R, HIP_Z, KNEE_Z = 0.045, 0.03, 0.04, 0.08, 0.25, 0.14


def tube(bm, cx, r, z0, z1, seg=16, step=0.01):
    rings = []
    n = int(round((z1 - z0) / step))
    for k in range(n + 1):
        z = z0 + (z1 - z0) * k / n
        rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * (i + 0.5) / seg),
                                    r * math.sin(2 * math.pi * (i + 0.5) / seg), z)) for i in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    for ring, flip in ((rings[0], True), (rings[-1], False)):
        bm.faces.new(list(reversed(ring)) if flip else ring)


def mesh_object(name, build):
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make():
    """(rig, body, [shorts shell])"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = bpy.data.armatures.new("rig")
    rig = bpy.data.objects.new("rig", arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    def bone(name, head, tail, parent=None):
        b = arm.edit_bones.new(name)
        b.head, b.tail = head, tail
        b.parent = arm.edit_bones[parent] if parent else None
        return b
    bone("DEF-spine", (0, 0, HIP_Z), (0, 0, 0.45))
    for s, x in (("L", LEG_X), ("R", -LEG_X)):
        bone(f"DEF-thigh.{s}", (x, 0, HIP_Z), (x, 0, KNEE_Z), "DEF-spine")
        bone(f"DEF-shin.{s}", (x, 0, KNEE_Z), (x, 0, 0.02), f"DEF-thigh.{s}")
    bpy.ops.object.mode_set(mode="OBJECT")

    def body_geo(bm):
        tube(bm, 0.0, TRUNK_R, HIP_Z, 0.45)
        tube(bm, LEG_X, LEG_R, 0.02, 0.27)
        tube(bm, -LEG_X, LEG_R, 0.02, 0.27)
    body = mesh_object("body_skin", body_geo)
    groups = {b.name: body.vertex_groups.new(name=b.name) for b in arm.bones}
    for v in body.data.vertices:
        if abs(math.hypot(abs(v.co.x) - LEG_X, v.co.y) - LEG_R) > 1e-4:
            groups["DEF-spine"].add([v.index], 1.0, "REPLACE")
        else:
            s = "L" if v.co.x > 0 else "R"
            groups[f"DEF-{'thigh' if v.co.z >= KNEE_Z else 'shin'}.{s}"].add([v.index], 1.0, "REPLACE")
    body.parent = rig
    body.modifiers.new("Armature", "ARMATURE").object = rig

    def shell_geo(bm):
        tube(bm, 0.0, 0.09, 0.26, 0.40)
        tube(bm, LEG_X, TUBE_R, 0.08, 0.30)
        tube(bm, -LEG_X, TUBE_R, 0.08, 0.30)
    shell = mesh_object("garment.shorts.main", shell_geo)
    shell["ps_garment_item"], shell["ps_garment_part"] = "shorts", "main"
    trunk = [v for v in body.data.vertices if any(g.group == groups["DEF-spine"].index for g in v.groups)]
    attr = shell.data.attributes.new("ps_body_vertex", "INT", "POINT")
    for v in shell.data.vertices:
        attr.data[v.index].value = min(trunk, key=lambda b: (b.co - v.co).length).index
    return rig, body, [shell]


def weights(ob):
    names = {g.index: g.name for g in ob.vertex_groups if not g.name.startswith("ps_")}
    return [{names[g.group]: round(g.weight, 5) for g in v.groups if g.group in names and g.weight > 0}
            for v in ob.data.vertices]


def is_leg_tube(v):
    return abs(math.hypot(abs(v.co.x) - LEG_X, v.co.y) - TUBE_R) < 1e-4


def inside_bent_leg(rig, shell, cfg):
    """Leg-tube vertices over the thigh that lie inside a leg (2 mm or deeper) with both thighs bent forward by 45
    and by 90 degrees (summed), armature only."""
    from garments_v2 import correctives as CORR
    off = [m for m in shell.modifiers if m.type == "SHRINKWRAP" and m.show_viewport]
    for m in off:
        m.show_viewport = False
    n = 0
    for deg in (45.0, 90.0):
        R = Matrix.Rotation(math.radians(-deg), 3, "X")
        undo = [CORR._pose_fk(rig, s, R, cfg["fk_bone"]) for s in ("L", "R")]
        pts = seated._evaluated_points(shell)
        for u in reversed(undo):
            u()
        for v, p in zip(shell.data.vertices, pts):
            if not is_leg_tube(v) or not KNEE_Z + 0.025 < v.co.z < HIP_Z - 0.015:
                continue
            a = Vector((LEG_X if v.co.x > 0 else -LEG_X, 0, HIP_Z))
            b = a + R @ Vector((0, 0, 0.02 - HIP_Z))  # the straight leg, hip to foot
            t = max(0.0, min(1.0, (p - a).dot(b - a) / (b - a).length_squared))
            n += (p - (a + (b - a) * t)).length < LEG_R - 0.002
    for m in off:
        m.show_viewport = True
    return n
'''

BIND = SCENE + r'''
CFG = {"fk_bone": "DEF-thigh.{side}", "leg_bone": "DEF-thigh.{side}"}
out = []
rig, body, shells = make()
ref = V2.bind_to_body(rig, body, shells)
w_v2 = weights(shells[0])

rig, body, shells = make()
rep = core.bind_to_body(rig, body, shells)
w_plain = weights(shells[0])
out.append(("without the field garment/3 binds exactly like garment/2", w_plain == w_v2))
out.append(("without the field nothing is reported or stored", "seated" not in rep and core.SEATED_PROP not in body
            and seated.REPORT_PROP not in shells[0]))
before = inside_bent_leg(rig, shells[0], CFG)
out.append((f"without the field the bent legs come through the tubes ({before} vertices inside a leg)", before > 20))

rig, body, shells = make()
body[core.SEATED_PROP] = json.dumps({"shorts": CFG})
rep = core.bind_to_body(rig, body, shells)
shell = shells[0]
w = weights(shell)
info = rep.get("seated", {}).get("shorts", {})
out.append(("with the field both parts are reported", "leg_weights" in info and "collision" in info
            and info["leg_weights"]["vertices_changed"] > 0))
outer = [v.index for v in shell.data.vertices if is_leg_tube(v) and KNEE_Z + 0.025 < v.co.z < HIP_Z - 0.015
         and abs(v.co.x) > 0.03]
own = [w[i].get("DEF-thigh.L" if shell.data.vertices[i].co.x > 0 else "DEF-thigh.R", 0.0) for i in outer]
out.append((f"leg-tube vertices over the thigh are carried by their own thigh (lowest share {min(own):.2f})",
            len(outer) > 40 and min(own) > 0.95))
shin = [v.index for v in shell.data.vertices if is_leg_tube(v) and v.co.z < KNEE_Z - 0.025]
out.append(("vertices over the shin keep their weights", len(shin) > 20 and all(w[i] == w_plain[i] for i in shin)))
inner = [v.index for v in shell.data.vertices if is_leg_tube(v) and KNEE_Z + 0.025 < v.co.z < HIP_Z - 0.015
         and abs(v.co.x) < 0.008]
kept = [w[i].get("DEF-spine", 0.0) for i in inner]
out.append((f"vertices at the centre plane keep part of their old weights ({min(kept):.2f}..{max(kept):.2f})",
            len(inner) > 4 and min(kept) > 0.05))
trunk = [v.index for v in shell.data.vertices if not is_leg_tube(v)]
out.append(("the trunk tube keeps its weights", all(w[i] == w_plain[i] for i in trunk)))
after = inside_bent_leg(rig, shell, CFG)
out.append((f"with the field the tubes follow the bent legs ({before} -> {after} vertices inside a leg)",
            after <= before // 10))
RESULT["bind"] = out
'''

COLLISION = SCENE + r'''
out = []
rig, body, shells = make()
core.bind_to_body(rig, body, shells)
shell = shells[0]
mask = body.vertex_groups.get(GEN.MASK_GROUP) or body.vertex_groups.new(name=GEN.MASK_GROUP)
spine = body.vertex_groups["DEF-spine"].index
hidden = [v.index for v in body.data.vertices if v.co.z > 0.17 or any(g.group == spine for g in v.groups)]
mask.add(hidden, 1.0, "REPLACE")
group = shell.vertex_groups[GEN.COLLISION_GROUP]
group.remove(list(range(len(shell.data.vertices))))
marked = next(v.index for v in shell.data.vertices if not is_leg_tube(v) and v.co.y > 0.08)
group.add([marked], 0.7, "REPLACE")
st = seated.settings({"fk_bone": "DEF-thigh.{side}", "collision": {"hip_deg": [90.0]}})
rep = seated.sweep_collision(rig, body, shells, st, "shorts")
def cw(i):
    return next((g.weight for g in shell.data.vertices[i].groups if g.group == group.index), 0.0)
front = [v.index for v in shell.data.vertices if not is_leg_tube(v) and v.co.y < -0.07 and v.co.z < 0.30
         and abs(abs(v.co.x) - LEG_X) < 0.04]
back = [v.index for v in shell.data.vertices if not is_leg_tube(v) and v.co.y > 0.05 and v.index != marked]
out.append((f"the weight is raised where bare leg skin comes close ({rep['vertices_raised']} vertices)",
            rep["vertices_raised"] > 0 and len(front) > 2 and max(cw(i) for i in front) > 0.99))
out.append(("the back of the trunk tube is not raised", len(back) > 10 and all(cw(i) == 0.0 for i in back)))
out.append(("a weight is never lowered", abs(cw(marked) - 0.7) < 1e-4))
rest = all(abs(pb.matrix_basis[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for pb in rig.pose.bones
           for i in range(4) for j in range(4))
on = all(m.show_viewport for m in shell.modifiers if m.type == "SHRINKWRAP")
out.append(("the rig is left in its rest pose and the collision modifiers stay on", rest and on))
RESULT["collision"] = out
'''


def probe(blender, script):
    with tempfile.TemporaryDirectory() as tmp:
        src, out, log = os.path.join(tmp, "probe.py"), os.path.join(tmp, "out.json"), os.path.join(tmp, "log.txt")
        open(src, "w").write("import bpy, json, sys\nsys.path.insert(0, %r)\nRESULT = {}\n%s\n"
                             "json.dump(RESULT, open(%r, 'w'))\n" % (CHARSYS, script, out))
        with open(log, "w") as f:
            subprocess.run([blender, "-b", "--factory-startup", "-P", src, "--"], stdout=f, stderr=subprocess.STDOUT)
        if not os.path.exists(out):
            print("".join(open(log).readlines()[-25:]))
            return {}
        return json.load(open(out))


def main():
    blender = arg("--blender")
    test_plain()
    if blender:
        cases = [(who, spec_path(who), override_path(who), CAST[who][2]) for who in ("girl", "boy")]
        for key, script in (("validate", VALIDATE % (cases,)), ("bind", BIND), ("collision", COLLISION)):
            got = probe(blender, script).get(key)
            if got is None:
                check(f"{key}: the Blender probe ran", False)
            for name, ok in got or []:
                check(name, ok)
    else:
        print("[test_garments_seated] SKIP Blender checks (no --blender)")
    print(f"[test_garments_seated] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
