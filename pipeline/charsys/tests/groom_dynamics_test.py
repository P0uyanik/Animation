"""Groom dynamics (groom/1 hair.dynamics, T-021) test (headless Blender; no rendering, writes only <out.json>).

    blender -b --factory-startup -P pipeline/charsys/tests/groom_dynamics_test.py -- <out.json>

A SYNTHETIC egg head and a two-bone armature (no character data). The same synthetic groom is built twice, without
and with a dynamics block. Checks:
  1. dynamics change nothing in the geometry (same vertices in every object) and add no bones when absent;
  2. chain bones: one chain per lock (every k-th), bone counts from "bones" / "bone_length", a bun chain; deform
     bones parented root -> tip under the head bone, connected from the second bone on;
  3. skinning: every chain-lock vertex has weights summing to 1 with at most 3 groups; tip vertices follow the last
     chain bone; scalp-side vertices keep the static binding; the tie on the bun follows the bun chain at its top;
  4. rig metadata ps_dynamics: chains with bones/tip/params, colliders resolved to the rig's bone names, anchors from
     binding.blend_z (chest weight rising towards the tip);
  5. validation rejects an unknown structure, a bad bone count and a bad collider.
Exit code 1 on any failure."""
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import geom as G  # noqa: E402
import groom as GROOM  # noqa: E402

out = sys.argv[sys.argv.index("--") + 1]
R = {"checks": {}}
ok = True


def check(name, cond, val=None):
    global ok
    R["checks"][name] = {"pass": bool(cond), "value": val}
    ok &= bool(cond)
    print(f"[groom_dynamics_test] {'PASS' if cond else 'FAIL'} {name} {'' if val is None else val}")


centre, radii = Vector((0.02, 0.01, 1.40)), Vector((0.11, 0.12, 0.10))
cz = centre.z
DYN = {"enabled": True, "defaults": {"stiffness": 70, "damping": 6, "gravity": 0.5, "limit_deg": 40, "radius": 0.01},
       "structures": {"long": {"bones": [2, 6], "bone_length": 0.08, "every": 2},
                      "curls": {"bones": 3, "stiffness": 40},
                      "buns": {"bones": 1, "stiffness": 150}},
       "colliders": [{"name": "skull", "type": "sphere", "bone": "head", "head_offset": [0, 0, 0], "radius": 0.095},
                     {"name": "back", "type": "capsule", "bone": "chest", "a": [0, 0.02, 0.9], "b": [0, 0.02, 1.15],
                      "radius": 0.08}]}


def groom_spec(dynamics):
    s = {"generator": "groom/1", "seed": 5, "scalp_offset_m": 0.006, "yarn": {"step_m": 0.004},
         "binding": {"blend_z": [cz - 0.30, cz - 0.12]},
         "structures": [
             {"type": "bun", "name": "buns", "buns": [{"az": 180, "el": 60, "radius": 0.035, "height": 0.06, "ropes": 4}]},
             {"type": "locks", "name": "long", "style": "straight", "count": 5, "az": [130, 230], "el_root": [10, 20],
              "hang_radii": [0.12, 0.13], "z_end": [cz - 0.40, cz - 0.40], "width": 0.02, "thick": 0.012},
             {"type": "locks", "name": "curls", "style": "curly", "count": 2, "mirror": True, "az": [80, 110],
              "el_root": [0, 10], "hang_radii": [0.125, 0.12], "z_end": [cz - 0.22, cz - 0.2], "width": 0.016,
              "thick": 0.012, "curl": {"radius": 0.01, "pitch": 0.03, "jitter": 0.2}},
             {"type": "tie", "name": "tie", "bun": 0}]}
    if dynamics:
        s["dynamics"] = dynamics
    return s


def build(dynamics):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    C = bpy.data.collections.new("synthetic")
    bpy.context.scene.collection.children.link(C)
    head = G.uv_sphere("head", centre, 1.0, C, 64, 32, tuple(radii))
    arm = bpy.data.armatures.new("rig")
    rig = bpy.data.objects.new("rig", arm)
    C.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    chest = arm.edit_bones.new("spine_chest")
    chest.head, chest.tail = (0, 0, 1.0), (0, 0, 1.25)
    hb = arm.edit_bones.new("skull")
    hb.head, hb.tail = (0, 0, 1.25), (0, 0, 1.5)
    hb.parent = chest
    bpy.ops.object.mode_set(mode="OBJECT")
    mats = {}
    spec = groom_spec(dynamics)
    objs, rep = GROOM.build(C, head, {"centre": centre, "radii": radii}, spec,
                            lambda slot: mats.setdefault(slot, G.material("M_" + slot, (90, 60, 50))),
                            lambda h, x, z: (G.surface_point(h, (x, -1.0, z), (0, 1, 0))[0] or Vector((0, -0.1, 0))).y)
    GROOM.bind(rig, objs, "skull", "spine_chest", spec["binding"])
    geo = {o.name: [tuple(round(c, 7) for c in v.co) for v in o.data.vertices] for o in objs}
    return rig, objs, rep, geo


rig0, objs0, rep0, geo0 = build(None)
bones0 = sorted(b.name for b in rig0.data.bones)
weights0 = {o.name: [sorted((o.vertex_groups[g.group].name, round(g.weight, 6)) for g in v.groups) for v in o.data.vertices]
            for o in objs0}
check("without dynamics: no chain bones, no metadata", bones0 == ["skull", "spine_chest"] and "ps_dynamics" not in rig0,
      bones0)
rig, objs, rep, geo = build(DYN)
check("dynamics leave the geometry unchanged", geo == geo0, sorted(geo))
dyn = json.loads(rig["ps_dynamics"])
chains = {c["name"]: c for c in dyn["chains"]}
R["chains"] = {n: len(c["bones"]) for n, c in chains.items()}
long_chains = sorted(n for n in chains if n.startswith("long."))
check("one chain per 2nd long lock (5 locks, every 2 -> 3 chains)", long_chains == ["long.00", "long.02", "long.04"],
      long_chains)
check("bone count from bone_length (about 0.3 m hanging / 0.08 -> 3..5, within [2, 6])",
      all(3 <= len(chains[n]["bones"]) <= 5 for n in long_chains), [len(chains[n]["bones"]) for n in long_chains])
check("curly locks: 3 bones each (mirror: 4 chains)",
      sorted(len(c["bones"]) for n, c in chains.items() if n.startswith("curls.")) == [3, 3, 3, 3], R["chains"])
check("bun chain: 1 bone", "buns.0" in chains and len(chains["buns.0"]["bones"]) == 1)
hier = True
for c in dyn["chains"]:
    for k, bn in enumerate(c["bones"]):
        b = rig.data.bones[bn]
        hier &= b.use_deform and b.parent is not None and b.parent.name == ("skull" if k == 0 else c["bones"][k - 1])
        hier &= b.use_connect == (k > 0)
check("chain bones: deform, root under the head bone, parented root -> tip", hier)
# skinning
ob = bpy.data.objects["hair_long"]
mw = ob.matrix_world
sums_ok, max_groups, tip_ok, scalp_ok = True, 0, True, True
last = {n: chains[n]["bones"][-1] for n in long_chains}
for v in ob.data.vertices:
    ws = {ob.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-6}
    sums_ok &= abs(sum(ws.values()) - 1.0) < 1e-4
    max_groups = max(max_groups, len(ws))
    p = mw @ v.co
    if p.z < cz - 0.385:  # tips of every lock: chained locks follow their last bone only
        chain_w = [w for n, w in ws.items() if n.startswith(GROOM.DYN_BONE_PREFIX)]
        if chain_w:
            tip_ok &= any(n in last.values() and w > 0.99 for n, w in ws.items())
    if p.z > cz + 0.0 and any(n.startswith(GROOM.DYN_BONE_PREFIX) for n in ws):
        scalp_ok = False
check("lock vertices: weights sum to 1, at most 3 groups", sums_ok and max_groups <= 3, max_groups)
check("lock tips follow the last chain bone", tip_ok)
check("scalp-side vertices keep the static binding (no chain weight above the head centre)", scalp_ok)
unchained = sum(1 for v in ob.data.vertices if not any(ob.vertex_groups[g.group].name.startswith(GROOM.DYN_BONE_PREFIX)
                                                       for g in v.groups))
check("unchained locks keep the static binding", unchained > 0, unchained)
tie = bpy.data.objects["hair_tie"]
bun_bone = chains["buns.0"]["bones"][0]
tie_w = [max((g.weight for g in v.groups if tie.vertex_groups[g.group].name == bun_bone), default=0.0) for v in tie.data.vertices]
check("the tie on the bun follows the bun chain (partly, near the base)", max(tie_w) > 0.0 and max(tie_w) < 1.0,
      round(max(tie_w), 3))
check("colliders resolved to the rig's bones", sorted((c["name"], c["bone"]) for c in dyn["colliders"]) ==
      [("back", "spine_chest"), ("skull", "skull")], dyn["colliders"])
check("skull collider centred on the head frame", Vector(next(c for c in dyn["colliders"] if c["name"] == "skull")["centre"])
      == centre)
anc = chains["long.00"].get("anchor")
check("anchor from binding.blend_z: chest weights rise towards the tip",
      anc is not None and anc["bone"] == "spine_chest" and anc["weights"][0] == 0 and anc["weights"][-1] > anc["weights"][1]
      and anc["weights"][-1] == 1.0, anc)
check("chain parameters from defaults + structure", chains["curls.00"]["stiffness"] == 40 and chains["curls.00"]["damping"] == 6)
check("report counts chains", rep["dynamics"]["chains"] == len(dyn["chains"]), rep.get("dynamics"))
bad = [dict(groom_spec(None), dynamics={"structures": {"nope": {"bones": 2}}}),
       dict(groom_spec(None), dynamics={"structures": {"long": {"bones": 0}}}),
       dict(groom_spec(None), dynamics={"colliders": [{"name": "x", "type": "cube", "bone": "head", "radius": 1}]})]
errs = [GROOM.validate(b) for b in bad]
check("validation rejects bad dynamics blocks", all(errs), errs)
check("synthetic dynamics spec validates", GROOM.validate(groom_spec(DYN)) == [])
R["pass"] = ok
json.dump(R, open(out, "w"), indent=1, default=str)
sys.exit(0 if ok else 1)
