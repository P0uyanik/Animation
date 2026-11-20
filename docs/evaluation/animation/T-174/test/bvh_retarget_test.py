"""T-174 throwaway feasibility test (research only, not part of the pipeline or the gate).

BVH (CMU / cgspeed 2010 release, frame 1 = T-pose) -> plush.clip/1 with the EXISTING retarget math
(pipeline/clips/retarget.py, clip_tools.py; ANIMATION_CLIPS.md section 8 "future mocap conversion"), then plays the
clip on the neutral chibi mannequin (build_mannequin.py) with clip_tools.Rig.pose_from_clip_rotations and measures:
  - direction error per driven role (mannequin bone direction vs source bone direction, engine axes),
  - foot behaviour: ankle height range, slide while planted, ground penetration vs rest,
  - a Workbench contact strip.

Usage (headless, deterministic):
  blender -b --factory-startup -P bvh_retarget_test.py -- --bvh 07_01.bvh --mannequin <dir>/neutral_mannequin.blend \
      --out <scratch>/out --name cmu_07_01_walk --step 5 [--frames 2:200]
The source BVH and the generated clip stay OUTSIDE the repository (scratchpad); only the numbers are reported.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
sys.path.insert(0, os.path.join(REPO, "pipeline", "clips"))
import retarget as RT  # noqa: E402
import clip_tools as CT  # noqa: E402

# CMU (cgspeed 2010, MotionBuilder names) -> shared roles. Fingers are not mapped (CMU has only stubs).
CMU_ROLES = {"hips": "Hips", "spine": "Spine", "chest": "Spine1", "neck": "Neck", "head": "Head",
             "upperArm.L": "LeftArm", "forearm.L": "LeftForeArm", "hand.L": "LeftHand",
             "thigh.L": "LeftUpLeg", "shin.L": "LeftLeg", "foot.L": "LeftFoot"}


def roles_full():
    out = dict(CMU_ROLES)
    for r, s in CMU_ROLES.items():
        if r.endswith(".L"):
            out[r[:-2] + ".R"] = s.replace("Left", "Right")
    return out


def world_rot(rig, pb):
    return rig.matrix_world.to_3x3() @ pb.matrix.to_3x3()


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--bvh", required=True)
    a.add_argument("--mannequin", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--name", required=True)
    a.add_argument("--step", type=int, default=5, help="source frames per clip frame (120 fps / 5 = 24 fps)")
    a.add_argument("--frames", default="2:", help="source frame range a:b (frame 1 is the T-pose)")
    a.add_argument("--loop", action="store_true")
    args = a.parse_args(sys.argv[sys.argv.index("--") + 1:])
    os.makedirs(args.out, exist_ok=True)
    prof = json.load(open(CT.PROFILE))
    ref = RT.reference_pose(prof["reference_pose"])

    # ---------------------------------------------------------------- 1. source: BVH, T-pose frame as rest
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_anim.bvh(filepath=os.path.abspath(args.bvh), global_scale=1.0, rotate_mode="NATIVE",
                            update_scene_fps=False, update_scene_duration=True)
    src = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    sc = bpy.context.scene
    f_end = int(src.animation_data.action.frame_range[1])
    lo, hi = args.frames.split(":")
    f0, f1 = int(lo or 2), int(hi or f_end)
    roles = {r: s for r, s in roles_full().items() if s in src.pose.bones}
    W = src.matrix_world
    sc.frame_set(1)  # T-pose
    heads0 = {r: CT.to_engine(W @ src.pose.bones[s].head) for r, s in roles.items()}
    rot0 = {r: world_rot(src, src.pose.bones[s]) for r, s in roles.items()}
    data = RT.derive(heads0, ref)
    order = [x for x in ref if x["name"] in data["roles"]]
    A, parent = {}, {}
    for x in order:
        c = data["roles"][x["name"]]
        A[x["name"]] = RT.qmul(RT.frame(x["ref_dir"], x["ref_twist"]), RT.qconj(RT.frame(c["dir"], c["twist"])))
        p = x["parent"]
        while p and p not in data["roles"]:
            p = next((y["parent"] for y in ref if y["name"] == p), "")
        parent[x["name"]] = p
    leg = data["leg_length"]
    hip0 = Vector(heads0["hips"])

    samples, roots, src_dirs = [], [], []
    frames = list(range(f0, f1 + 1, args.step))
    for f in frames:
        sc.frame_set(f)
        G = {}
        for x in order:
            r = x["name"]
            m = world_rot(src, src.pose.bones[roles[r]]) @ rot0[r].inverted()
            G[r] = CT.q_engine_from_blender_rot(m)
        L = {}
        for x in order:
            r = x["name"]
            p = parent[r]
            Gp = G[p] if p else [1.0, 0.0, 0.0, 0.0]
            Ap = A[p] if p else [1.0, 0.0, 0.0, 0.0]
            q = RT.qnorm(RT.qmul(RT.qmul(RT.qmul(Ap, RT.qconj(Gp)), G[r]), RT.qconj(A[r])))
            L[r] = [-c for c in q] if q[0] < 0 else q
        samples.append(L)
        h = Vector(CT.to_engine(W @ src.pose.bones[roles["hips"]].head))
        roots.append([c / leg for c in (h - hip0)])
        d = {}
        for x in order:
            r, e = x["name"], x["end"]
            if e and e in roles:
                v = Vector(CT.to_engine(W @ src.pose.bones[roles[e]].head)) - Vector(CT.to_engine(W @ src.pose.bones[roles[r]].head))
                d[r] = v.normalized()
        src_dirs.append(d)
    roots = [[r[0] - roots[0][0], r[1], r[2] - roots[0][2]] for r in roots]  # start at the origin (x/z), keep height
    fps = 120.0 / args.step
    meta = {"source": "mocap", "license": "CMU-Mocap", "loop": args.loop,
            "attribution": "The data used in this project was obtained from mocap.cs.cmu.edu. The database was created "
                           "with funding from NSF EIA-0196217. BVH conversion: Bruce Hahne (cgspeed).",
            "description": f"T-174 feasibility test from {os.path.basename(args.bvh)} frames {f0}..{f1} step {args.step}",
            "mask": [x["name"] for x in order]}
    clip_path = os.path.join(args.out, f"{args.name}.clip.json")
    clip = CT.write_clip(clip_path, args.name, fps, samples, roots, meta, prof["reference_pose"], dense=True)

    # ---------------------------------------------------------------- 2. target: chibi mannequin
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.mannequin))
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    R = CT.Rig(rig)
    sc = bpy.context.scene
    Wt = rig.matrix_world
    ankles = {s: [] for s in (".L", ".R")}
    dir_err = []
    per_role = {}
    rest_ankle = {s: CT.to_engine(Wt @ rig.data.bones[R.src["foot" + s]].head_local)[1] for s in (".L", ".R")}
    for i, L in enumerate(samples):
        # horizontal root motion on the object (as the engine moves the whole character; the mannequin's shoulder and
        # pelvis deform bones are top-level and would stay behind), vertical on the hips bone
        r = roots[i]
        R.pose_from_clip_rotations(L, (0.0, r[1], 0.0))
        rig.location = CT.CMT @ Vector((r[0], 0.0, r[2])) * R.leg
        rig.keyframe_insert("location", frame=i + 1)
        bpy.context.view_layer.update()
        for s in (".L", ".R"):
            ankles[s].append(Vector(CT.to_engine(Wt @ rig.pose.bones[R.src["foot" + s]].head)))
        for r, dv in src_dirs[i].items():
            e = next(x["end"] for x in R.order if x["name"] == r)
            if r in R.src and e in R.src:
                v = Vector(CT.to_engine(Wt @ rig.pose.bones[R.src[e]].head)) - Vector(CT.to_engine(Wt @ rig.pose.bones[R.src[r]].head))
                if v.length > 1e-6:
                    ang = math.degrees(v.normalized().angle(dv))
                    dir_err.append(ang)
                    per_role[r] = max(per_role.get(r, 0.0), round(ang, 3))
        R.key(i + 1)
    # foot plant: a frame is "planted" when the ankle is within 15 % of the leg length of its lowest height
    rep = {"clip": clip_path, "frames": len(samples), "fps": fps, "source_leg_m": leg, "target_leg_m": R.leg,
           "dir_err_deg_max": round(max(dir_err), 4), "dir_err_deg_mean": round(sum(dir_err) / len(dir_err), 5), "dir_err_deg_max_per_role": per_role}
    for s, ys in ankles.items():
        h = [p.y for p in ys]
        lo_h = min(h)
        thr = lo_h + 0.15 * R.leg * 0.25
        slide, run, best = 0.0, 0.0, 0.0
        for k in range(1, len(ys)):
            if h[k] < thr and h[k - 1] < thr:
                dxz = math.hypot(ys[k].x - ys[k - 1].x, ys[k].z - ys[k - 1].z)
                slide += dxz
                run += dxz
                best = max(best, run)
            else:
                run = 0.0
        travel = math.hypot(ys[-1].x - ys[0].x, ys[-1].z - ys[0].z)
        rep["foot" + s] = {"ankle_min_minus_rest_mm": round((lo_h - rest_ankle[s]) * 1000, 1),
                           "ankle_lift_mm": round((max(h) - lo_h) * 1000, 1),
                           "slide_while_planted_mm_total": round(slide * 1000, 1),
                           "slide_longest_plant_mm": round(best * 1000, 1), "travel_mm": round(travel * 1000, 1)}
    hips = [roots[i] for i in range(len(roots))]
    rep["root_travel_mm"] = round(math.hypot(hips[-1][0], hips[-1][2]) * R.leg * 1000, 1)
    json.dump(rep, open(os.path.join(args.out, f"{args.name}.report.json"), "w"), indent=1)
    print("[T-174]", json.dumps(rep))

    # ---------------------------------------------------------------- 3. Workbench strip (8 frames)
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 320, 400
    sc.render.film_transparent = False
    cam_data = bpy.data.cameras.new("t174cam")
    cam = bpy.data.objects.new("t174cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1.6
    idx = [round(k * (len(samples) - 1) / 7) for k in range(8)]
    paths = []
    for n, i in enumerate(idx):
        sc.frame_set(i + 1)
        hp = rig.matrix_world @ rig.pose.bones[R.src["hips"]].head
        cam.location = (hp.x + 3.0, hp.y - 0.0, 0.55)  # side view (character faces -Y in Blender)
        cam.rotation_euler = (math.radians(90), 0, math.radians(90))
        p = os.path.join(args.out, f"{args.name}_f{n}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    print("[T-174] frames", paths)


main()
