"""Shared garment evaluation helpers for ``garment/1`` (Blender only; character-independent).

Used by ``tests/garment_generic_test.py`` (synthetic mannequin) and ``tools/garment_pose_eval.py`` (any built
master). Nothing here reads character data: the rig profile, clips and garments come from the arguments.

* ``semantic_fk_rig``: converts a Rigify rig to the plain semantic FK deform rig used to author the repository clips
  (constraints and non-deform bones removed). Destructive: use on a scratch copy of a scene.
* ``ClipPlayer``: samples a repository clip (``content/clips/<name>.clip.json``) and poses the rig.
* ``clearance``: signed clearance of garment vertices over the visible (unmasked) body faces.
* ``clip_extremes`` / ``test_poses`` (T-025): the evaluation pose list, read from ``content/clips/*.clip.json``.
* ``inside_body`` / ``skin_contact`` (T-025): crease-robust inside/outside and skin-contact tests.
"""
import json
import math
import os

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

from . import generator as GEN

PROBES = [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
# Inside/outside vote directions: the 6 axes and the 8 cube diagonals (none parallel to another, so one ray that
# grazes a fold or runs along a crease cannot decide alone).
VOTE_DIRECTIONS = PROBES + [Vector((x, y, z)).normalized() for x in (1, -1) for y in (1, -1) for z in (1, -1)]
# T-025: the one skin-contact tolerance. Two skin surfaces closer than this along the skin normal cannot have a
# garment between them (2 x the 2 mm collision offset + the 0.5 mm rest clearance floor), so a garment vertex that is
# nearest to such skin is reported as skin contact (armpit, crotch, elbow folds), not as poke-through.
SKIN_CONTACT_TOLERANCE_M = 0.0045
# Legacy fixed samples kept in the pose list (T-018/T-024 continuity); every clip also contributes its extreme.
LEGACY_SAMPLES = [("idle_relaxed", 45), ("wave", 52), ("point", 46), ("gest_shrug", 26), ("sit_down", 50),
                  ("emo_happy", 30)]


def _track_value(track, frame):
    if "samples" in track:
        return list(track["samples"][max(0, min(len(track["samples"]) - 1, frame))])
    keys = track["keys"]
    if frame <= keys[0][0]:
        return list(keys[0][1:])
    if frame >= keys[-1][0]:
        return list(keys[-1][1:])
    for left, right in zip(keys, keys[1:]):
        if left[0] <= frame <= right[0]:
            t = (frame - left[0]) / max(1, right[0] - left[0])
            return [a + (b - a) * t for a, b in zip(left[1:], right[1:])]
    return list(keys[-1][1:])


def _angle(q, r):
    n = math.sqrt(sum(x * x for x in q)) * math.sqrt(sum(x * x for x in r))
    return 2.0 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(q, r))) / max(n, 1e-12)))


def clip_extremes(clips_dir, step=2):
    """One sampled extreme per clip in ``clips_dir`` (every ``*.clip.json``): the frame (sampled every ``step``)
    whose pose is farthest from the clip's first frame (sum of the per-role rotation angles plus pi x the root
    translation in leg lengths). A static clip (at most 2 frames, e.g. an emotion pose) gives its last frame.
    New clips automatically become new test poses."""
    out = []
    for name in sorted(f[:-len(".clip.json")] for f in os.listdir(clips_dir) if f.endswith(".clip.json")):
        clip = json.load(open(os.path.join(clips_dir, name + ".clip.json")))
        count = int(clip["frame_count"])
        root = clip.get("root", {}).get("translation")
        if count <= 2:
            out.append({"clip": name, "frame": count - 1, "score": 0.0, "frame_count": count})
            continue
        best = (-1.0, 0)
        for frame in range(0, count, step):
            score = sum(_angle(_track_value(t, frame), _track_value(t, 0)) for t in clip["tracks"].values())
            if root:
                score += math.pi * math.dist(_track_value(root, frame), _track_value(root, 0))
            best = max(best, (score, frame))
        out.append({"clip": name, "frame": best[1], "score": round(best[0], 4), "frame_count": count})
    return out


def test_poses(clips_dir, legacy=LEGACY_SAMPLES):
    """Evaluation poses: the legacy fixed samples (clamped to each clip's length) plus every clip's extreme,
    without duplicates, as ``[(clip, frame)]``."""
    poses, seen = [], set()
    counts = {}
    for name, frame in legacy:
        path = os.path.join(clips_dir, name + ".clip.json")
        if not os.path.exists(path):
            continue
        counts[name] = counts.get(name) or int(json.load(open(path))["frame_count"])
        key = (name, min(frame, counts[name] - 1))
        if key not in seen:
            seen.add(key)
            poses.append((name, frame))
    for entry in clip_extremes(clips_dir):
        key = (entry["clip"], entry["frame"])
        if key not in seen:
            seen.add(key)
            poses.append(key)
    return poses


def crossings(bvh, origin, direction):
    count, start = 0, origin
    for _ in range(64):
        hit = bvh.ray_cast(start + direction * 1e-6, direction)
        if hit[0] is None:
            break
        count, start = count + 1, hit[0]
    return count


def inside_body(bvh, point):
    """Crease-robust inside test for a closed body surface: a majority vote of ray-crossing parity over the 14
    ``VOTE_DIRECTIONS``. In folds (armpit, crotch, elbow) single rays graze or run along the crease and miscount; the
    vote ignores them."""
    odd = sum(crossings(bvh, point, d) % 2 for d in VOTE_DIRECTIONS)
    return odd * 2 > len(VOTE_DIRECTIONS)


def skin_contact(bvh, location, normal, tolerance=SKIN_CONTACT_TOLERANCE_M):
    """True when the skin at ``location`` touches other skin: another body surface faces it within ``tolerance``
    along its normal, or the posed body has pushed this skin inside another body part. ``clearance`` also applies it
    to the skin a garment vertex was built from (``ps_body_vertex``): when the pose sinks that skin into another
    body part (an upper arm into the ribs, the hip front into a raised thigh), the garment vertex that follows it is
    in a skin fold, not poking through."""
    probe = location + normal * 1e-4
    if bvh.ray_cast(probe, normal, tolerance)[0] is not None:
        return True
    return inside_body(bvh, probe)


def semantic_fk_rig(rig, root):
    """Re-parent the deform bones of a Rigify rig to the semantic hierarchy of ``rig_profiles/humanoid_rigify.json``,
    drop constraints and non-deform bones, and return a ``clip_tools.Rig`` for posing from clips."""
    import clip_tools as CT
    import retarget as RT
    profile = json.load(open(os.path.join(root, "pipeline", "charsys", "rig_profiles", "humanoid_rigify.json")))
    ref = RT.reference_pose(profile["reference_pose"])
    (el, er), (sl, sr) = profile["mirror"]["engine"], profile["mirror"]["source"]
    roles = {}
    for role, source in profile["roles"].items():
        roles[role] = source
        if role.endswith(el):
            roles[role[:-len(el)] + er] = source[:-len(sl)] + sr if source.endswith(sl) else source.replace(sl, sr)
    sources = {role: source for role, source in roles.items() if source in rig.data.bones and rig.data.bones[source].use_deform}
    semantic_parent = {entry["name"]: entry["parent"] for entry in ref}

    def deform_parent(bone):
        parent = bone.parent
        while parent is not None and not parent.use_deform:
            # Rigify: a mechanism/original bone (ORG-x, MCH-x) stands for its deform twin DEF-x (eyes and jaw sit
            # under ORG-face/ORG-spine.006, so their deform parent is the head's DEF bone, not the root).
            twin = rig.data.bones.get("DEF-" + parent.name.split("-", 1)[1]) if "-" in parent.name else None
            if twin is not None and twin.use_deform and twin != bone:
                return twin.name
            parent = parent.parent
        return parent.name if parent else None

    new_parent = {bone.name: deform_parent(bone) for bone in rig.data.bones if bone.use_deform}
    role_of = {source: role for role, source in sources.items()}
    for source, role in role_of.items():
        parent = semantic_parent.get(role)
        while parent and parent not in sources:
            parent = semantic_parent.get(parent)
        new_parent[source] = sources[parent] if parent else None
    rig.animation_data_clear()
    for pb in rig.pose.bones:
        for constraint in list(pb.constraints):
            pb.constraints.remove(constraint)
    bpy.ops.object.select_all(action="DESELECT")
    rig.hide_set(False)
    rig.hide_viewport = False
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    for name, parent in new_parent.items():
        edit[name].use_connect = False
        edit[name].parent = edit[parent] if parent else None
        edit[name].bbone_segments = 1
    for bone in list(edit):
        if not bone.use_deform:
            edit.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.custom_shape = None
    return CT.Rig(rig)


class ClipPlayer:
    def __init__(self, rig, clip_rig, clips_dir):
        self.rig, self.clip_rig, self.clips_dir = rig, clip_rig, clips_dir

    def reset(self):
        for pb in self.rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        bpy.context.view_layer.update()

    @staticmethod
    def sample(track, frame, quaternion=True):
        if "samples" in track:
            values = track["samples"][max(0, min(len(track["samples"]) - 1, frame))]
            return list(values)
        keys = track["keys"]
        if frame <= keys[0][0]:
            return list(keys[0][1:])
        if frame >= keys[-1][0]:
            return list(keys[-1][1:])
        for left, right in zip(keys, keys[1:]):
            if left[0] <= frame <= right[0]:
                t = (frame - left[0]) / max(1, right[0] - left[0])
                if quaternion:
                    return list(Quaternion(left[1:]).slerp(Quaternion(right[1:]), t))
                return [a + (b - a) * t for a, b in zip(left[1:], right[1:])]
        raise AssertionError("unreachable clip sample")

    def apply(self, name, frame):
        clip = json.load(open(os.path.join(self.clips_dir, name + ".clip.json")))
        rotations = {role: self.sample(track, frame) for role, track in clip["tracks"].items()}
        root = [0.0, 0.0, 0.0]
        if clip.get("root", {}).get("translation"):
            root = self.sample(clip["root"]["translation"], frame, quaternion=False)
        self.reset()
        self.clip_rig.pose_from_clip_rotations(rotations, root)
        bpy.context.view_layer.update()
        return {"clip": name, "frame": frame, "frame_count": clip["frame_count"]}


def world_mesh(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = ob.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    verts = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    faces = [tuple(poly.vertices) for poly in mesh.polygons]
    evaluated.to_mesh_clear()
    return verts, faces


def clearance(body, objects, floor, contact_gap=SKIN_CONTACT_TOLERANCE_M, contact_floor=None):
    """Signed clearance of garment vertices over visible body faces (hidden regions reported for information).
    Passes when no vertex over visible skin is closer than ``floor`` (negative = inside the body). A vertex whose
    nearest-face sign says inside is re-checked with the crease-robust ``inside_body`` vote. Vertices closer than
    ``contact_floor`` (default ``floor``) over skin that touches other skin (``skin_contact`` with ``contact_gap``,
    default ``SKIN_CONTACT_TOLERANCE_M``) are counted as skin contact, not as poke-through."""
    contact_floor = floor if contact_floor is None else contact_floor
    mask_mod = body.modifiers.get(GEN.MASK_MODIFIER)
    garment_points = []
    for ob in objects:
        attr = ob.data.attributes.get("ps_body_vertex")
        sources = [d.value for d in attr.data] if attr is not None else None
        for i, p in enumerate(world_mesh(ob)[0]):
            garment_points.append((ob.name, p, sources[i] if sources is not None and i < len(sources) else -1))
    visible = GEN.visible_face_flags(body)
    enabled = mask_mod.show_viewport if mask_mod else False
    if mask_mod:
        mask_mod.show_viewport = False  # full posed body; face indices match body.data.polygons
    body_verts, body_faces = world_mesh(body)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    rot = evaluated.matrix_world.to_3x3()
    body_normals = [(rot @ v.normal).normalized() for v in mesh.vertices]
    evaluated.to_mesh_clear()
    if mask_mod:
        mask_mod.show_viewport = enabled
        bpy.context.view_layer.update()
    assert len(body_faces) == len(visible)
    bvh = BVHTree.FromPolygons(body_verts, body_faces, all_triangles=False)
    best = {"visible": [float("inf"), None, None, None], "hidden": [float("inf"), None, None, None]}
    counted, inside, buried, buried_min, revoted, folded = 0, 0, 0, float("inf"), 0, 0
    source_contact = {}

    def source_in_fold(index):
        if index not in source_contact:
            source_contact[index] = (0 <= index < len(body_verts) and
                                     inside_body(bvh, body_verts[index] + body_normals[index] * 1e-4))
        return source_contact[index]

    for name, point, source in garment_points:
        location, normal, index, distance = bvh.find_nearest(point)
        if location is None:
            continue
        signed = (point - location).dot(normal)
        if signed < 0 and distance > 1e-6 and not inside_body(bvh, point):
            # Posed creases make the nearest-face sign unreliable (nearest point on an edge, or on a face that
            # the bent body itself has pushed inside another part); the vote says the point is outside.
            signed = distance
            revoted += 1
        if signed < contact_floor and visible[index] and (skin_contact(bvh, location, normal, contact_gap) or
                                                          (source >= 0 and source_in_fold(source))):
            folded += source >= 0 and source_contact.get(source, False)
            buried += 1
            buried_min = min(buried_min, signed)
            continue
        key = "visible" if visible[index] else "hidden"
        counted += key == "visible"
        inside += key == "visible" and signed < 0
        if signed < best[key][0]:
            best[key] = [signed, name, tuple(round(v, 6) for v in point), tuple(round(v, 6) for v in location)]
    value, closest, garment_point, body_point = best["visible"]
    return {"min_clearance_m": round(value, 6), "closest_object": closest,
            "garment_point_m": garment_point, "body_point_m": body_point,
            "vertices_over_visible_body": counted, "vertices_inside_visible_body": inside,
            "vertices_total": len(garment_points), "floor_m": floor,
            "hidden_region_min_m": round(best["hidden"][0], 6) if best["hidden"][1] else None,
            "skin_contact_vertices": buried,
            "skin_contact_min_m": round(buried_min, 6) if buried else None,
            "skin_contact_tolerance_m": contact_gap, "sign_corrected_by_vote": revoted,
            "skin_contact_over_folded_source_skin": folded,
            "pass": value >= floor}


def rms_motion(a, b):
    if len(a) != len(b):
        return 0.0
    return math.sqrt(sum((p - q).length_squared for p, q in zip(a, b)) / max(1, len(a)))
