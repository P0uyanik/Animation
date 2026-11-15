"""Blender side of the clip system (used by make_clips.py, export_clip.py and measure_clips.py).

Conventions (docs/ANIMATION_CLIPS.md): engine axes = Blender (x, z, -y). A clip stores per role the local rotation
L in reference space; with the authoring rig's own retarget data (the same rules as every package) the rotation of
a role bone relative to its rest is G = G_parent · A_parent⁻¹ · L · A_role, A = Fref · C⁻¹ (engine axes).
- pose_from_clip_rotations(): L per role -> Blender pose (role-bone basis rotations, root location), for authoring;
- clip_rotations_from_pose(): the evaluated Blender pose -> L per role and the normalised root, for export;
- posed_frames(): per role the posed direction and twist reference in engine axes (measurements, C3).
Character-independent: everything comes from the rig profile and the rig's own bones."""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retarget as RT  # noqa: E402

PROFILE = os.path.join(HERE, "..", "charsys", "rig_profiles", "humanoid_rigify.json")
CM = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))  # Blender -> engine axes
CMT = CM.transposed()


def to_engine(v):
    return [float(v[0]), float(v[2]), float(-v[1])]


def q_engine_from_blender_rot(m3):
    """Rotation matrix in Blender armature axes -> quaternion (w, x, y, z) in engine axes."""
    e = CM @ m3 @ CMT
    return RT.quat_from_matrix([[e[r][c] for c in range(3)] for r in range(3)])


def blender_rot_from_q_engine(q):
    e = Quaternion((q[0], q[1], q[2], q[3])).to_matrix()
    return CMT @ e @ CM


class Rig:
    """Role bones, semantic order and per-role A of an armature, from the profile's reference pose."""

    def __init__(self, rig, profile_path=PROFILE):
        prof = json.load(open(profile_path))
        self.profile = prof
        self.ref_block = prof["reference_pose"]
        self.ref = RT.reference_pose(self.ref_block)
        self.rig = rig
        roles = {}
        (el, er), (sl, sr) = prof["mirror"]["engine"], prof["mirror"]["source"]
        for role, src in prof["roles"].items():
            roles[role] = src
            if role.endswith(el):
                roles[role[: -len(el)] + er] = src[: -len(sl)] + sr if src.endswith(sl) else src.replace(sl, sr)
        bones = rig.data.bones
        self.src = {r: s for r, s in roles.items() if s in bones}
        W = rig.matrix_world
        heads = {r: to_engine(W @ bones[s].head_local) for r, s in self.src.items()}
        self.data = RT.derive(heads, self.ref)  # the same block export_engine.py writes for this rig
        self.order = [x for x in self.ref if x["name"] in self.data["roles"]]
        self.A = {}
        for x in self.order:
            c = self.data["roles"][x["name"]]
            self.A[x["name"]] = RT.qmul(RT.frame(x["ref_dir"], x["ref_twist"]), RT.qconj(RT.frame(c["dir"], c["twist"])))
        self.parent = {}
        for x in self.order:  # nearest present semantic ancestor
            p = x["parent"]
            while p and p not in self.data["roles"]:
                p = next((y["parent"] for y in self.ref if y["name"] == p), "")
            self.parent[x["name"]] = p
        self.leg = self.data["leg_length"]
        self.root_role = "hips"

    # ---------------------------------------------------------------- authoring: L -> Blender pose
    def pose_from_clip_rotations(self, L, root=(0.0, 0.0, 0.0)):
        """Sets role-bone basis rotations from reference-space local rotations L ({role: (w,x,y,z)}, missing =
        identity) and the root bone location from the normalised root translation (engine axes / leg length)."""
        G = {}
        D = {}
        rig = self.rig
        for x in self.order:
            r = x["name"]
            p = self.parent[r]
            Gp = G[p] if p else [1.0, 0.0, 0.0, 0.0]
            Ap = self.A[p] if p else [1.0, 0.0, 0.0, 0.0]
            G[r] = RT.qnorm(RT.qmul(RT.qmul(RT.qmul(Gp, RT.qconj(Ap)), L.get(r, [1.0, 0.0, 0.0, 0.0])), self.A[r]))
            D[r] = blender_rot_from_q_engine(G[r])  # rotation relative to rest, armature axes
        for x in self.order:
            r = x["name"]
            pb = rig.pose.bones[self.src[r]]
            rest = pb.bone.matrix_local.to_3x3()
            par = pb.parent
            Dp = Matrix.Identity(3)
            if par is not None:  # the Blender parent is the semantic parent role bone (or a helper following it)
                pr = next((k for k, s in self.src.items() if s == par.name), None)
                if pr in D:
                    Dp = D[pr]
            basis = rest.inverted() @ Dp.inverted() @ D[r] @ rest
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = basis.to_quaternion()
        rb = rig.pose.bones[self.src[self.root_role]]
        off = CMT @ Vector(root) * self.leg
        rb.location = rb.bone.matrix_local.to_3x3().inverted() @ off

    def key(self, frame):
        for x in self.order:
            self.rig.pose.bones[self.src[x["name"]]].keyframe_insert("rotation_quaternion", frame=frame, group=x["name"])
        self.rig.pose.bones[self.src[self.root_role]].keyframe_insert("location", frame=frame, group="root")

    # ---------------------------------------------------------------- export / measurement: evaluated pose -> data
    def engine_deltas(self):
        """Per role: rotation relative to rest (engine axes) of the evaluated pose."""
        out = {}
        for x in self.order:
            pb = self.rig.pose.bones[self.src[x["name"]]]
            m = (self.rig.matrix_world.to_3x3() @ pb.matrix.to_3x3()) @ (self.rig.matrix_world.to_3x3() @ pb.bone.matrix_local.to_3x3()).inverted()
            out[x["name"]] = q_engine_from_blender_rot(m)
        return out

    def clip_rotations_from_pose(self):
        G = self.engine_deltas()
        L = {}
        for x in self.order:
            r = x["name"]
            p = self.parent[r]
            Gp = G[p] if p else [1.0, 0.0, 0.0, 0.0]
            Ap = self.A[p] if p else [1.0, 0.0, 0.0, 0.0]
            # L = A_p · G_p⁻¹ · G · A⁻¹
            L[r] = RT.qnorm(RT.qmul(RT.qmul(RT.qmul(Ap, RT.qconj(Gp)), G[r]), RT.qconj(self.A[r])))
            if L[r][0] < 0:
                L[r] = [-c for c in L[r]]
        rb = self.rig.pose.bones[self.src[self.root_role]]
        W = self.rig.matrix_world
        off = to_engine((W @ rb.head) - (W @ rb.bone.head_local))
        root = [c / self.leg for c in off]
        return L, root

    def posed_frames(self):
        """Per role: posed (direction, twist) in engine axes = G · rest direction / twist."""
        G = self.engine_deltas()
        return {r: (RT.qrot(G[r], self.data["roles"][r]["dir"]), RT.qrot(G[r], self.data["roles"][r]["twist"])) for r in G}


# ------------------------------------------------------------------ plush.clip/1 writer
def _simplify(frames, values, err, tol):
    """Greedy key reduction: keep a key where linear interpolation from the last kept key would deviate > tol."""
    if len(frames) <= 2:
        return list(range(len(frames)))
    keep = [0]
    k = 0
    j = 2
    while j < len(frames):
        ok = all(err(values[k], values[j], (frames[i] - frames[k]) / (frames[j] - frames[k]), values[i]) <= tol for i in range(k + 1, j))
        if not ok:
            keep.append(j - 1)
            k = j - 1
        j += 1
    keep.append(len(frames) - 1)
    return keep


def _slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = [-c for c in b], -d
    if d > 0.9995:
        return RT.qnorm([x + (y - x) * t for x, y in zip(a, b)])
    th = math.acos(d)
    s = math.sin(th)
    return [(math.sin((1 - t) * th) * x + math.sin(t * th) * y) / s for x, y in zip(a, b)]


def write_clip(path, name, fps, samples, roots, meta, ref_block, dense=False, tol_deg=0.02, root_tol=1e-5):
    """samples: [{role: L}] per clip frame 0..N-1; roots: [normalised root] per frame. Sparse keys unless dense."""
    n = len(samples)
    roles = [r for r in samples[0] if not meta.get("mask") or r in meta["mask"]]  # tracks for the masked roles only
    tracks = {}
    for r in roles:
        vals = [s[r] for s in samples]
        if dense:
            tracks[r] = {"samples": [[round(c, 7) for c in q] for q in vals]}
            continue
        idx = _simplify(list(range(n)), vals, lambda a, b, t, v: RT.qangle_deg(_slerp(a, b, t), v), tol_deg)
        tracks[r] = {"keys": [[i] + [round(c, 7) for c in vals[i]] for i in idx]}
    clip = {"format": "plush.clip", "version": 1, "name": name, "fps": fps, "frame_count": n,
            "loop": bool(meta.get("loop", False)), "source": meta.get("source", "script"),
            "license": meta.get("license", "project"), "attribution": meta.get("attribution", "Plush Studio project (script-made)"),
            "description": meta.get("description", ""), "mask": meta.get("mask") or roles,
            "mirror": {"suffix": [".L", ".R"], "axis": "x", "note": meta.get("mirror_note", "mirrorable")},
            "contacts": meta.get("contacts", []), "tracks": tracks, "reference_pose": ref_block}
    if any(any(abs(c) > 1e-9 for c in r) for r in roots):
        if dense:
            tr = {"samples": [[round(c, 7) for c in r] for r in roots]}
        else:
            idx = _simplify(list(range(n)), roots, lambda a, b, t, v: math.dist([x + (y - x) * t for x, y in zip(a, b)], v), root_tol)
            tr = {"keys": [[i] + [round(c, 7) for c in roots[i]] for i in idx]}
        clip["root"] = {"translation": tr, "scale": "leg_length", "space": "character, engine axes"}
    for k in ("x_authoring",):
        if k in meta:
            clip[k] = meta[k]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    json.dump(clip, open(path, "w"), indent=1)
    return clip


def export_action(rig_obj, action, out_dir, profile_path=PROFILE):
    """Samples a Blender action on the authoring rig at every frame and writes <out_dir>/<name>.clip.json."""
    meta = json.loads(action.get("ps_clip_meta", "{}"))
    R = Rig(rig_obj, profile_path)
    sc = bpy.context.scene
    rig_obj.animation_data_create()
    rig_obj.animation_data.action = action
    f0, f1 = int(action.frame_range[0]), int(action.frame_range[1])
    n = int(meta.get("frame_count", f1 - f0 + 1))
    fps = float(meta.get("fps", sc.render.fps / sc.render.fps_base))
    samples, roots = [], []
    for f in range(f0, f0 + n):
        sc.frame_set(f)
        L, root = R.clip_rotations_from_pose()
        samples.append(L)
        roots.append(root)
    name = meta.get("name", action.name)
    path = os.path.join(out_dir, f"{name}.clip.json")
    write_clip(path, name, fps, samples, roots, meta, R.ref_block, dense=bool(meta.get("dense")))
    return path
