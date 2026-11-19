"""Bake the skirt cloth simulation of a built master for one motion (opt-in; the master file is not changed).

    blender -b --factory-startup -P pipeline/charsys/cloth_sim/run.py -- <master.blend> <walk|sit|kneel> <out dir>
        [--seed 126] [--set key=value ...] [--save]

Writes <out>/<motion>.pc2 (the bake: the proxy's points per frame, object space, frame 1 = rest) and
<out>/<motion>.json (settings, seed, sha256 of the cache, per-evidence-frame penetration of the simulated and of the
skinned skirt against the posed body, timings). ``--save`` also writes <out>/<motion>.blend with the bake applied
(Mesh Cache on the proxy, Surface Deform on the skirt; the skinned skirt is one ``skirt.show(followers, False)``
away). The same master, motion, seed and settings give the same cache (README.md, "Determinism")."""
import hashlib
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import motions as M  # noqa: E402
import skirt as S  # noqa: E402


def prepare(blend, motion_name, seed, overrides, lean=True):
    """Open the master and set the simulation up. Returns a dict of the objects involved. ``lean`` disables every
    object the simulation does not read (they stay in the file)."""
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
    pieces = S.tagged()
    if len(pieces) != 1:
        raise SystemExit(f"cloth_sim: expected one piece tagged ps_cloth_sim, found {[p.name for p in pieces]}")
    piece = pieces[0]
    st = S.settings(overrides)
    body = bpy.data.objects[piece["ps_weight_source"]]
    motion = M.MOTIONS[motion_name]()
    bpy.context.scene.frame_set(1)
    S._apply_pose(rig, [])
    proxy = S.make_proxy(piece, st, seed)
    followers = S.bind(piece, proxy)
    col = S.collider(rig, body, st["body_thickness_m"], st["friction"])
    props = []
    if "seat" in motion["props"]:
        hip = rig.matrix_world @ rig.pose.bones["thigh_fk.L"].head
        radius = max(abs((body.matrix_world @ v.co).y - hip.y) for v in body.data.vertices
                     if abs((body.matrix_world @ v.co).z - (hip.z - 0.03)) < 0.004)
        top = hip.z - radius - st["body_thickness_m"] - 0.004
        props.append(S.box("cloth.prop.seat", (-0.3, hip.y - 0.5 * radius, top - 0.04), (0.3, hip.y + 0.35, top)))
    if lean:  # only what the simulation reads is evaluated per frame (fibres, hair and face are not)
        keep = {rig, piece, proxy, col, *props}
        for o in bpy.data.objects:
            o.hide_viewport = o not in keep
    return {"rig": rig, "piece": piece, "proxy": proxy, "followers": followers, "collider": col, "motion": motion,
            "settings": st, "props": props, "body": body}


def measure(ctx, layer_m):
    """Penetration at the evidence frames: simulated (baked) skirt and the build's skinned skirt."""
    sc, out = bpy.context.scene, {}
    for o in bpy.data.objects:  # the skinned skirt needs its collision target evaluated again
        if o.get("ps_garment_item") or o.get("ps_collision_proxy"):
            o.hide_viewport = False
    for name, frame in sorted(ctx["motion"]["evidence"].items(), key=lambda kv: kv[1]):
        S._apply_pose(ctx["rig"], ctx["motion"]["pose"](frame))
        sc.frame_set(frame)
        row = {"frame": frame}
        for label, sim in (("simulated", True), ("skinned", False)):
            S.show(ctx["followers"], sim)
            bpy.context.view_layer.update()
            row[label] = S.penetration(ctx["piece"], ctx["collider"], layer_m)
        S.show(ctx["followers"], True)
        row["proxy"] = S.penetration(ctx["proxy"], ctx["collider"], layer_m)
        out[name] = row
    return out


def tights_layer(piece):
    """Thickness of a skin-following layer worn under the piece (a ``tights`` item), from the built pieces."""
    for o in bpy.data.objects:
        if o.get("ps_garment_type") == "tights" and o.type == "MESH" and o.get("ps_garment_part") == "main":
            report = json.loads(bpy.data.texts["ps_cloth_layer"].as_string()) if "ps_cloth_layer" in bpy.data.texts else {}
            return float(report.get("layer_m", 0.0036))
    return 0.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend, motion_name, out = argv[0], argv[1], os.path.abspath(argv[2])
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 126
    overrides = {}
    for i, a in enumerate(argv):
        if a == "--set":
            k, v = argv[i + 1].split("=", 1)
            overrides[k] = type(S.DEFAULTS[k])(json.loads(v))
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    ctx = prepare(blend, motion_name, seed, overrides)
    t1 = time.time()
    pc2 = os.path.join(out, motion_name + ".pc2")
    data = S.simulate(ctx["rig"], ctx["proxy"], ctx["motion"], ctx["settings"], pc2)
    t2 = time.time()
    S.replay(ctx["proxy"], pc2)
    layer = tights_layer(ctx["piece"])
    pen = measure(ctx, layer)
    report = {"master": os.path.basename(blend), "motion": motion_name, "frames": int(data.shape[0]),
              "evidence_frames": ctx["motion"]["evidence"], "seed": seed, "settings": ctx["settings"],
              "piece": ctx["piece"].name, "followers": [o.name for o in ctx["followers"]],
              "proxy_vertices": int(data.shape[1]), "props": [o.name for o in ctx["props"]],
              "cache": os.path.basename(pc2), "cache_sha256": hashlib.sha256(open(pc2, "rb").read()).hexdigest(),
              "penetration": pen, "blender": bpy.app.version_string,
              "seconds": {"setup": round(t1 - t0, 1), "simulate": round(t2 - t1, 1), "measure": round(time.time() - t2, 1)}}
    json.dump(report, open(os.path.join(out, motion_name + ".json"), "w"), indent=1)
    print("[cloth_sim]", json.dumps({k: report[k] for k in ("motion", "frames", "cache_sha256", "seconds")}))
    print("[cloth_sim]", json.dumps(pen))
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, motion_name + ".blend"), copy=True)
    return ctx


if __name__ == "__main__":
    main()
