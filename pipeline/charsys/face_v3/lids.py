"""face_generic/3 lid shells that end at the eye corners (T-089).

face_generic/1-2 lid shells are sphere caps that wrap all the way round the eyeball; the socket skin hides them, but
at the eye's sides (3/4 view) the skin fades back to the head surface and the shell ends show as a pale rim past the
outer corner. v3 cuts each shell at a plane x = const in its eye frame (x = the frame's left-right axis):
  spec.face.eyes.lids.trim = {"outer_deg": a_o, "inner_deg": a_i (optional), "soft": 0.06, "eye_clearance": 0.0}
keeps the shell where sx * x <= r_shell * sin(a_o) (and -sx * x <= r_shell * sin(a_i)). The lids blink, widen and
squint by rotating about the frame's x axis (face.py lid seam, face_generic eye_action_units), which keeps x: a trimmed
shell therefore stays inside its bound through every lid motion (test: lid-corner bound). Only the shell (skin
material) faces are cut; lash strands joined into a lower lid keep their geometry."""
import math

import bmesh
from mathutils import Matrix, Vector

SIDES = ((1, "L"), (-1, "R"))


def _f(d, k, default):
    return float(d.get(k, default)) if d is not None else float(default)


def lid_roll(lids_cfg, sx, zone):
    """3x3 rotation of one lid about its eye's forward axis (lids.upper_roll_deg / lower_roll_deg; positive raises
    the lid's OUTER end, the eye_frame roll_deg convention), or None. A rolled lid stays on its sphere (concentric
    with the eyeball): the lower lid rising to the outer corner gives the D-shaped opening of felt-doll eyes."""
    deg = _f(lids_cfg, "upper_roll_deg" if zone == "up" else "lower_roll_deg", 0.0)
    return Matrix.Rotation(math.radians(-sx * deg), 3, "Y") if abs(deg) > 1e-9 else None


def roll_lid(objs, T, R3):
    """Rotates the objects' meshes (world space data) by R3 about the eye frame's origin, in the frame."""
    M = T @ R3.to_4x4() @ T.inverted()
    for ob in objs:
        ob.data.transform(M)
        ob.data.update()


def rolled_edge(fn, R3):
    """Wraps a lid-edge function (azimuth -> frame point or None) with a lid roll."""
    if R3 is None:
        return fn
    return lambda a: (lambda p: None if p is None else R3 @ p)(fn(a))


def trim_bounds(lids_cfg, r_up_out, r_lo_out):
    """{"up": (outer, inner), "lo": (outer, inner)} in metres (frame units), None = not trimmed."""
    t = (lids_cfg or {}).get("trim")
    if not t:
        return None
    out = {}
    for zone, rr in (("up", r_up_out), ("lo", r_lo_out)):
        o = t.get(f"{zone}_outer_deg", t.get("outer_deg"))
        i = t.get(f"{zone}_inner_deg", t.get("inner_deg"))
        b = t.get(f"{zone}_back", t.get("back"))
        out[zone] = (None if o is None else rr * math.sin(math.radians(float(o))),
                     None if i is None else rr * math.sin(math.radians(float(i))),
                     None if b is None else float(b) * rr)
    return out


def trim_shell(ob, T, sx, bound_outer, bound_inner, bound_back=None, skin_material_name=None):
    """Cuts the shell (object data in world space, object matrix identity) at x = sx*bound_outer / -sx*bound_inner in
    the eye frame T, and (bound_back) at y = -bound_back: only the front of the shell stays (its caps above and below
    the eye no longer run back past the eye's sides; the blink rotation brings the front part, not the back, over
    the eye). Only faces with the skin material (or all faces when the object has a single material) are cut.
    Returns the number of vertices removed."""
    me = ob.data
    Ti = T.inverted()
    me.transform(Ti)
    bm = bmesh.new()
    bm.from_mesh(me)
    n0 = len(bm.verts)
    skin_idx = None
    if skin_material_name and len(me.materials) > 1:
        names = [m.name if m else "" for m in me.materials]
        skin_idx = names.index(skin_material_name) if skin_material_name in names else None
    cuts = [(Vector((sgn * b, 0, 0)), Vector((-sgn, 0, 0))) for b, sgn in ((bound_outer, sx), (bound_inner, -sx))
            if b is not None]
    if bound_back is not None:
        cuts.append((Vector((0, -bound_back, 0)), Vector((0, -1, 0))))
    for co, no in cuts:
        faces = [f for f in bm.faces if skin_idx is None or f.material_index == skin_idx]
        edges = list({e for f in faces for e in f.edges})
        verts = list({v for f in faces for v in f.verts})
        # keep the side the plane normal points to (clear_inner removes the other side)
        bmesh.ops.bisect_plane(bm, geom=verts + edges + faces, plane_co=co, plane_no=no, clear_inner=True,
                               clear_outer=False)
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
    removed = n0 - len(bm.verts)
    bm.to_mesh(me)
    bm.free()
    me.transform(T)
    me.update()
    return removed


def corner_extent(ob, T, sx):
    """Largest sx * x (outer side) and -sx * x (inner side) of the object's vertices in the eye frame, over the basis
    and every shape key (blink, wide, squint, in-betweens): the measured lid-corner bound."""
    Ti = T.inverted()
    mw = ob.matrix_world
    sets = [ob.data.vertices]
    if ob.data.shape_keys:
        sets = [k.data for k in ob.data.shape_keys.key_blocks]
    outer = inner = -1e9
    for data in sets:
        for v in data:
            x = (Ti @ (mw @ v.co)).x
            outer = max(outer, sx * x)
            inner = max(inner, -sx * x)
    return outer, inner


def exposure_from(head, shells, frames, yaw_deg, corner_deg, r):
    """3/4 socket-rim diagnostic. For a camera direction at yaw_deg (0 = front, +90 = the character's left), each shell
    on the side that turns its OUTER corner to that camera: the fraction of its vertices past the opening's corner
    (sx * x > r * sin(corner_deg) in the eye frame) that no head skin hides along the view ray. 0 = no visible rim."""
    from mathutils.bvhtree import BVHTree
    mw = head.matrix_world
    me = head.data
    tree = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
    a = math.radians(yaw_deg)
    d = Vector((math.sin(a), -math.cos(a), 0.0))
    xs = r * math.sin(math.radians(corner_deg))
    out = {}
    for ob in shells:
        side = ob.name.split(".")[-1][:1]
        sx = 1 if side == "L" else -1
        if sx * yaw_deg <= 0:
            continue
        Ti = frames[side].inverted()
        tot = vis = 0
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            if sx * (Ti @ w).x <= xs:
                continue
            tot += 1
            if tree.ray_cast(w + d * 1e-4, d, 1.0)[0] is None:
                vis += 1
        out[ob.name] = {"past_corner_vertices": tot, "visible": vis, "fraction": round(vis / max(tot, 1), 3)}
    return out
