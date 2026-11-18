"""Generic facial production system (spec.face.generator = "face_generic/1").

One implementation for every humanoid character; a character differs only by data:
  spec.face.layout        where the features sit (relative to the eye bones and the head surface)
  spec.face.eyes          eyeball size/shape/orientation, iris, highlights, lid rest openness, lashes
  spec.face.brows, ears, nose, blush
  spec.face.mouth         face.py lips_jaw/2 (lips, seam, interior, oral layers, jaw) + extra lip shapes
  spec.face.blink         face.py lid_seam/1 (+ timing data for the engine)
  spec.face.smile_coupling
  spec.face.expressions   intensity / per-preset scale / weight overrides for the shared library
                          (pipeline/charsys/face_library/expressions.json); optional `custom` presets (T-058)
  spec.face.action_units  motion sizes; optional (T-058, off = unchanged output) `split` (per-side .L/.R copies of
                          symmetric action units, e.g. BrowDown.L / MouthSmile.R) and `pout_m` (MouthPout)

Shared functions never test a character's name; everything is placed from the eye bones, the head surface (ray
casts on the head mesh) and landmarks derived from the layout. The legacy boy (body_v6) is not built here: his v6
eyes and face stay on the legacy path until a separately approved migration.

Eye frames: each eye has a frame T = Translation(c) @ Rz(yaw) @ Rx(pitch) @ Scale(scale). The lids and lashes are
built and animated in that frame's unit-sphere space, so ellipsoidal or rotated eyes reuse face.py's lid-seam blink
unchanged (the meshes are moved into the frame, keyed, and moved back with their shape keys)."""
import json
import math
import os

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import face as FACE
import face_features as FF
import geom as G
from materials import builder as MATERIALS

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(HERE, "face_library", "expressions.json")
SIDES = ((1, "L"), (-1, "R"))  # +x = the character's left
GENERATOR_VERSIONS = ("face_generic/1", "face_generic/2")  # versions implemented here (versions.py; released = immutable)
INBETWEENS = (0.25, 0.5, 0.75)  # in-between keys "<key>@25/50/75" for rotation-type motions (blink)


def load_library(path=LIBRARY):
    return json.load(open(path))


def _f(d, k, default):
    return float(d.get(k, default)) if d is not None else float(default)


class FaceContext:
    """The duck-typed 'B' that face.py's shared lips / interior / jaw functions expect (the legacy boy passes the
    body_v6 module). face_y ray-casts the actual head mesh (a BVH, rebuilt after the mesh changes)."""

    def __init__(self, head, z_mouth, eye_r):
        self.G = G
        self.Z = {"mouth": z_mouth}
        self.EYE_R = eye_r
        self.head = head
        self._tree = None

    def invalidate(self):
        self._tree = None

    def tree(self):
        if self._tree is None:
            mw = self.head.matrix_world
            me = self.head.data
            self._tree = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
        return self._tree

    def face_y(self, head, x, z):
        loc, nrm, idx, dist = self.tree().ray_cast(Vector((x, -5.0, z)), Vector((0, 1, 0)), 10.0)
        if loc is None:
            raise ValueError(f"face_y: no head surface in front at x={x:.4f} z={z:.4f}")
        return loc.y

    def side_x(self, side, y, z):
        """Outer surface x of the head at (y, z) on one side (sx = +1 left, -1 right)."""
        loc, nrm, idx, dist = self.tree().ray_cast(Vector((side * 5.0, y, z)), Vector((-side, 0, 0)), 10.0)
        return None if loc is None else loc.x

    def nearest(self, p):
        loc, nrm, idx, dist = self.tree().find_nearest(Vector(p))
        return loc, nrm


# ------------------------------------------------------------------------------------------------ eyes
def eye_frame(c, sx, ecfg):
    """World matrix of an eye's local frame (unit-sphere space x radius; -y = the eye's forward)."""
    yaw = math.radians(sx * _f(ecfg, "yaw_deg", 0.0))  # positive yaw turns both eyes outwards
    pitch = math.radians(_f(ecfg, "pitch_deg", 0.0))  # positive = looking down
    s = ecfg.get("scale", [1.0, 1.0, 1.0])
    roll = _f(ecfg, "roll_deg", 0.0)  # eye tilt: positive raises the outer corners (v2 option; 0 = unchanged)
    R = Matrix.Rotation(math.radians(-sx * roll), 4, "Y") if roll else Matrix.Identity(4)
    return Matrix.Translation(c) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "X") @ R @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))


def gaze_envelope(sx, ecfg):
    """Largest radius, in the eye's unit frame (1 = the eyeball surface), that the eyeball reaches when the eye bone
    turns it rigidly over the configured gaze range (spec.face.eyes.gaze_range_deg = [yaw, pitch], default
    [20, 12]): the spectral norm of A^-1 R A over the range, A = the eye frame. Exactly 1 for spherical eyes; an oval
    eye turned rigidly sweeps outside its own ellipsoid (G03: 1.18), so lids built on the ellipsoid would be cut."""
    s = ecfg.get("scale", [1.0, 1.0, 1.0])
    if max(abs(float(k) - 1.0) for k in s) < 1e-9:
        return 1.0
    import numpy as np
    A = np.array(eye_frame(Vector((0, 0, 0)), sx, ecfg).to_3x3())
    Ai = np.linalg.inv(A)
    gy, gp = (float(v) for v in ecfg.get("gaze_range_deg", [20.0, 12.0]))
    worst = 1.0
    for i in range(11):
        for j in range(7):
            R = np.array(Matrix.Rotation(math.radians(-gy + 2 * gy * i / 10), 3, "Z") @ Matrix.Rotation(math.radians(-gp + 2 * gp * j / 6), 3, "X"))
            worst = max(worst, float(np.linalg.norm(Ai @ R @ A, 2)))
    return worst


def _plane_point(q, k, rr, a, upper):
    """Point at azimuth a (around the forward axis) on the sphere of radius rr that lies on the lid plane through q
    (upper: z - q.z + k (y - q.y) = 0; lower: z - q.z - k (y - q.y) = 0). Bisection on the elevation."""
    sgn = 1.0 if upper else -1.0

    def g(e):
        p = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * rr
        return (p.z - q.z) + sgn * k * (p.y - q.y), p
    lo, hi = math.radians(-85), math.radians(85)
    glo, ghi = g(lo)[0], g(hi)[0]
    if glo * ghi > 0:
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        gm = g(mid)[0]
        if (gm > 0) == (ghi > 0):
            hi, ghi = mid, gm
        else:
            lo = mid
    return g((lo + hi) / 2)[1]


def _lid_edge(q, k, rr, a, lids_cfg, upper):
    """Lid edge point at azimuth a (unit frame), with the v2 lid curvature applied (see face_features.curve_lid)."""
    p = _plane_point(q, k, rr, a, upper)
    c = _f(lids_cfg, "upper_curve" if upper else "lower_curve", 0.0)
    if p is None or abs(c) < 1e-9:
        return p
    u = p.x / rr
    return Matrix.Rotation((1.0 if upper else -1.0) * c * u * u * (math.pi / 4), 3, "X") @ p


def build_eyes(C, M, ctx, eyes_cfg, ex, ez, protrusion, material_assignment=None):
    """Eyeballs (object frame = eye frame: the iris shader stays circular), lid shells cut by configurable planes,
    an upper lash line with optional outer lashes, an optional lower lash hint (part of the lower lid object so it
    follows every lower-lid motion). Returns eyes, lids [(up, lo, lash, c)], frames {side: T}, info."""
    r = _f(eyes_cfg, "radius_m", 0.03)
    lids_cfg = eyes_cfg.get("lids", {})
    lash_cfg = eyes_cfg.get("lash", {})
    iris = eyes_cfg.get("iris", {})
    if eyes_cfg.get("shader") == "layered/1":
        mat = FF.eye_material_layered("M_eye_generic", eyes_cfg, r)
    else:
        mat = G.eye_material("M_eye_generic", tuple(iris.get("srgb", (110, 66, 40))), tuple(iris.get("dark_srgb", (55, 30, 18))),
                             r, _f(iris, "radius", 0.6) * r, _f(iris, "pupil", 0.28) * r,
                             highlights=[tuple(h) for h in eyes_cfg.get("highlights", [])] or None,
                             sclera_srgb=tuple(eyes_cfg.get("sclera_srgb", (235, 228, 220))))
    if material_assignment:
        MATERIALS.apply_from_assignment(mat, material_assignment, preserve_base_color=True)
    lash_mat = G.material("M_lash_generic", tuple(lash_cfg.get("srgb", (45, 28, 24))), roughness=0.7)
    eyes, lids, frames, info = [], [], {}, {}
    for sx, side in SIDES:
        x, z = sx * ex, ez
        # eye centre: the front of the eye stands `protrusion` in front of the head surface
        T0 = eye_frame(Vector((0, 0, 0)), sx, eyes_cfg)
        fwd = T0.to_3x3() @ Vector((0, -r, 0))
        cy = ctx.face_y(None, x, z)
        for _ in range(3):
            front = Vector((x, cy, z)) + fwd
            cy = ctx.face_y(None, front.x, front.z) - protrusion - fwd.y
        c = Vector((x, cy, z))
        T = eye_frame(c, sx, eyes_cfg)
        frames[side] = T
        eye = G.uv_sphere(f"eye.{side}", (0, 0, 0), r, C, 48, 24)
        eye.matrix_world = T
        G.assign(eye, mat)
        eyes.append(eye)
        # lids, built in the unit frame (radius r), then moved to the eye frame
        e_up, k_up = math.radians(_f(lids_cfg, "upper_edge_deg", 40)), _f(lids_cfg, "upper_back_tilt", 1.0)
        e_lo, k_lo = math.radians(_f(lids_cfg, "lower_edge_deg", -45)), _f(lids_cfg, "lower_tilt", 0.3)
        # lid clearance: the configured gap, widened where needed so the lids clear the eyeball over the gaze range
        env = gaze_envelope(sx, eyes_cfg)
        need = env * 1.01 - 1.0 if env > 1.0 else 0.0
        r_up = r * (1 + max(_f(lids_cfg, "upper_gap", 0.06), need))
        r_lo = r * (1 + max(_f(lids_cfg, "lower_gap", 0.03), need))
        q_up = Vector((0, -math.cos(e_up), math.sin(e_up))) * r_up
        q_lo = Vector((0, -math.cos(e_lo), math.sin(e_lo))) * r_lo
        up = G.uv_sphere(f"lid_upper.{side}", (0, 0, 0), r_up, C, 64, 32)
        G.cut_by_plane(up, q_up, (0, k_up, 1.0), keep_positive=True)
        G.add_mod(up, "SOLIDIFY", thickness=_f(lids_cfg, "upper_thickness_m", 0.0018), offset=1.0)
        lo = G.uv_sphere(f"lid_lower.{side}", (0, 0, 0), r_lo, C, 64, 32)
        G.cut_by_plane(lo, q_lo, (0, k_lo, -1.0), keep_positive=True)
        G.add_mod(lo, "SOLIDIFY", thickness=_f(lids_cfg, "lower_thickness_m", 0.0012), offset=1.0)
        for o in (up, lo):
            G.apply_mods(o)
        FF.curve_lid(up, _f(lids_cfg, "upper_curve", 0.0), True)  # v2 lid edge curvature (0 = unchanged)
        FF.curve_lid(lo, _f(lids_cfg, "lower_curve", 0.0), False)
        # upper lash line along the upper lid's front edge (unit frame), thicker towards the outer corner
        a_max = math.radians(_f(lash_cfg, "span_deg", 70))
        rr = r_up + _f(lids_cfg, "upper_thickness_m", 0.0018) * 0.6
        n = 17
        pts, ths = [], []
        for i in range(n):
            a = -a_max + 2 * a_max * i / (n - 1)
            p = _lid_edge(q_up, k_up, rr, a, lids_cfg, True)
            if p is None:
                continue
            outer = (math.copysign(1, a) == sx) * abs(a) / a_max  # 0 inner .. 1 outer corner
            pts.append(p + Vector((0, -_f(lash_cfg, "forward_m", 0.0004), 0)))
            ths.append(_f(lash_cfg, "thick_m", 0.002) * (1 + _f(lash_cfg, "flare", 0.5) * outer) * (0.55 + 0.45 * math.sin(math.pi * i / (n - 1))))
        Tw = T.to_3x3()
        wpts = [T @ p for p in pts]
        lash = G.tube(f"lash.{side}", wpts, [_f(lash_cfg, "depth_m", 0.0016)] * len(wpts), ths, C,
                      up_hint=tuple(Tw @ Vector((0, 0, 1))), seg=10, cap_start="round", cap_end="round")
        parts = [lash]
        oc = lash_cfg.get("outer", {})
        for j in range(int(oc.get("count", 0))):  # outer lashes: short tapered strands curving out and up
            a = sx * a_max * (1.0 - float(oc.get("spacing", 0.11)) * j)
            base = _lid_edge(q_up, k_up, rr, a, lids_cfg, True)
            if base is None:
                continue
            nxt = _lid_edge(q_up, k_up, rr, a - sx * 0.05, lids_cfg, True)
            tang = (base - nxt).normalized() if nxt is not None else Vector((sx, 0, 0))
            L = float(oc.get("length_m", [0.006])[min(j, len(oc.get("length_m", [0.006])) - 1)])
            d = (tang * 0.8 + Vector((0, -0.35, 1.0)) * float(oc.get("lift", 0.9))).normalized()
            ctrl = [base, base + d * L * 0.5 + Vector((0, 0, L * 0.12)), base + d * L + tang * L * 0.25]
            cp = [T @ p for p in G.bezier(ctrl[0], ctrl[1], ctrl[2], 5)]
            wb = _f(oc, "width_m", 0.0011)
            s = G.tube(f"_lash_outer.{side}.{j}", cp, [wb * (1 - 0.8 * t / 4) for t in range(5)], [wb * 0.6 * (1 - 0.8 * t / 4) for t in range(5)],
                       C, up_hint=tuple(Tw @ Vector((0, -1, 0))), seg=6, cap_start="round", cap_end="point")
            parts.append(s)
        if lash_cfg.get("strands"):  # v2: individual curled upper lashes along the lid edge
            parts += FF.lash_strands(T, lambda a: _lid_edge(q_up, k_up, rr, a, lids_cfg, True), sx, lash_cfg["strands"],
                                     True, f"lash_strand.{side}", C)
        if len(parts) > 1:
            lash = G.join(parts, f"lash.{side}")
        G.assign(lash, lash_mat)
        lo.data.transform(T)
        up.data.transform(T)
        lw = lash_cfg.get("lower")
        if lw:  # thin lower lash hint on the outer part of the lower lid edge (joined into the lower lid)
            a0, a1 = math.radians(_f(lw, "from_deg", 20)), math.radians(_f(lw, "to_deg", 70))
            lpts = []
            for i in range(9):
                a = sx * (a0 + (a1 - a0) * i / 8)
                p = _lid_edge(q_lo, k_lo, r_lo + _f(lids_cfg, "lower_thickness_m", 0.0012) * 0.6, a, lids_cfg, False)
                if p is not None:
                    lpts.append(T @ p)
            if len(lpts) >= 3:
                th = _f(lw, "thick_m", 0.0007)
                ll = G.tube(f"_lash_lower.{side}", lpts, [th] * len(lpts), [th * (0.6 + 0.4 * i / (len(lpts) - 1)) for i in range(len(lpts))],
                            C, up_hint=tuple(Tw @ Vector((0, 0, 1))), seg=8)
                G.assign(lo, M["face_skin"])
                ll.data.materials.clear()
                ll.data.materials.append(M["face_skin"])
                ll.data.materials.append(lash_mat)
                for poly in ll.data.polygons:
                    poly.material_index = 1
                lo = G.join([lo, ll], f"lid_lower.{side}")
        if lash_cfg.get("lower_strands"):  # v2: individual lower lashes, part of the lower lid object
            rl = r_lo + _f(lids_cfg, "lower_thickness_m", 0.0012) * 0.6
            ls = FF.lash_strands(T, lambda a: _lid_edge(q_lo, k_lo, rl, a, lids_cfg, False), sx, lash_cfg["lower_strands"],
                                 False, f"lash_lower_strand.{side}", C)
            if ls:
                if not lo.data.materials:
                    G.assign(lo, M["face_skin"])
                ll = G.join(ls, f"_lash_lower_strands.{side}")
                ll.data.materials.clear()
                for mm in lo.data.materials:
                    ll.data.materials.append(mm)
                if lash_mat.name not in [mm.name for mm in ll.data.materials]:
                    ll.data.materials.append(lash_mat)
                li = [mm.name for mm in ll.data.materials].index(lash_mat.name)
                for poly in ll.data.polygons:
                    poly.material_index = li
                lo = G.join([lo, ll], f"lid_lower.{side}")
        for o in (up, lo):
            if not o.data.materials:
                G.assign(o, M["face_skin"])
        lids.append((up, lo, lash, c))
        info[side] = {"centre_m": [round(v, 4) for v in c], "radius_m": r, "front_protrusion_m": protrusion,
                      "gaze_envelope": round(env, 4), "lid_gap_upper": round(r_up / r - 1, 4), "lid_gap_lower": round(r_lo / r - 1, 4)}
    return eyes, lids, frames, info


def _in_frame(objs, T, fn):
    """Runs fn with the objects' meshes (and shape keys) moved into an eye frame's unit space, then moves them back."""
    Ti = T.inverted()
    for o in objs:
        o.data.transform(Ti, shape_keys=True)
    try:
        return fn()
    finally:
        for o in objs:
            o.data.transform(T, shape_keys=True)


def _rot_key(ob, name, deg, origin=Vector((0, 0, 0))):
    """Shape key: the mesh rotated about the frame's x axis through origin (+deg moves the front downwards)."""
    if ob.data.shape_keys is None:
        ob.shape_key_add(name="Basis")
    k = ob.shape_key_add(name=name)
    k.value = 0.0
    R = Matrix.Rotation(math.radians(deg), 3, Vector((1, 0, 0)))
    for i, v in enumerate(ob.data.vertices):
        k.data[i].co = origin + R @ (v.co - origin)
    return k


def _rename_key(ob, old, new):
    if ob.data.shape_keys and old in ob.data.shape_keys.key_blocks:
        ob.data.shape_keys.key_blocks[old].name = new


def eye_action_units(eyes, lids, frames, r, blink_cfg, au_cfg, envelopes=None):
    """Blink.L / Blink.R (face.py lid_seam/1 in the eye frame; optional eyeball flatten), EyeWide, EyeSquint."""
    rep = {}
    wide_up, wide_lo = _f(au_cfg, "wide_upper_deg", 10), _f(au_cfg, "wide_lower_deg", 6)
    sq_lo, sq_up = _f(au_cfg, "squint_lower_deg", 14), _f(au_cfg, "squint_upper_deg", 6)
    flat = _f(blink_cfg, "flatten", 0.0)
    for (sx, side), eye, (up, lo, lash, c) in zip(SIDES, eyes, lids):
        T = frames[side]
        r_closed = r * (envelopes or {}).get(side, 1.0)  # the closed lid also clears the gaze envelope

        def work():
            for f in INBETWEENS:  # partial closures on the true arc (see face.add_blink_lid_seam)
                FACE.add_blink_lid_seam([(up, lo, lash, Vector((0, 0, 0)))], r_closed, G, blink_cfg, fraction=f,
                                        key_name=f"Blink.{side}@{int(round(f * 100))}")
            out = FACE.add_blink_lid_seam([(up, lo, lash, Vector((0, 0, 0)))], r_closed, G, blink_cfg)
            for ob in (up, lash):
                _rename_key(ob, "Blink", f"Blink.{side}")
            _rot_key(up, "EyeWide", -wide_up)
            _rot_key(lash, "EyeWide", -wide_up)
            _rot_key(lo, "EyeWide", wide_lo)
            _rot_key(up, "EyeSquint", sq_up)
            _rot_key(lash, "EyeSquint", sq_up)
            _rot_key(lo, "EyeSquint", -sq_lo)
            return out
        rep[side] = _in_frame([up, lo, lash], T, work)[0]
        if flat > 0:  # eyeball front pressed under the closed lid (object space = eye frame)
            if eye.data.shape_keys is None:
                eye.shape_key_add(name="Basis")
            k = eye.shape_key_add(name=f"Blink.{side}")
            k.value = 0.0
            for i, v in enumerate(eye.data.vertices):
                co = v.co.copy()
                k.data[i].co = Vector((co.x, co.y * (1 - flat), co.z)) if co.y < 0 else co
    return rep


# ------------------------------------------------------------------------------------------------ brows, ears, nose
def _brow_points(ctx, sx, ex, ez, r, bc, up=0.0, inner_dz=0.0, inner_dx=0.0, outer_dz=0.0):
    pts = []
    n = 7
    xi, xo = ex - _f(bc, "inner", 0.6) * r, ex + _f(bc, "outer", 0.85) * r
    z0 = ez + _f(bc, "height", 2.2) * r
    for i in range(n):
        t = i / (n - 1)
        inner = 1 - t
        x = sx * (xi + (xo - xi) * t) - sx * inner_dx * inner
        z = (z0 + _f(bc, "arch_m", 0.004) * math.sin(math.pi * t) - _f(bc, "inner_drop_m", 0.0) * inner
             - _f(bc, "outer_drop_m", 0.002) * t + up + inner_dz * inner + outer_dz * t)
        y = ctx.face_y(None, x, z) - _f(bc, "offset_m", 0.0012)
        pts.append((x, y, z))
    return pts


def _brow_tube(name, pts, bc, C):
    n = len(pts)
    w = [_f(bc, "thick_m", 0.0016) * (0.7 + 0.3 * math.sin(math.pi * (0.25 + 0.6 * i / (n - 1)))) * (1 - _f(bc, "taper", 0.4) * i / (n - 1))
         for i in range(n)]
    return G.tube(name, pts, w, [_f(bc, "depth_m", 0.0012)] * n, C, up_hint=(0, -1, 0), seg=10)


def build_brows(C, ctx, bc, au, ex, ez, r):
    """Thin brows on the face surface; keys BrowUp.<side>, BrowDown, BrowSad (every key re-projected onto the face)."""
    mat = (FF.brow_material("M_brow_generic", bc, MATERIALS) if bc.get("style") else
           G.material("M_brow_generic", tuple(bc.get("srgb", (110, 70, 52))), roughness=0.8))
    brows = []
    up_m, down_m, in_m, sad_m = (_f(au, "brow_up_m", 0.006), _f(au, "brow_down_m", 0.005), _f(au, "brow_in_m", 0.003),
                                 _f(au, "brow_sad_m", 0.005))
    for sx, side in SIDES:
        b = _brow_tube(f"brow.{side}", _brow_points(ctx, sx, ex, ez, r, bc), bc, C)
        G.assign(b, mat)
        b.shape_key_add(name="Basis")
        for name, kw in ((f"BrowUp.{side}", {"up": up_m}),
                         ("BrowDown", {"inner_dz": -down_m, "inner_dx": in_m, "up": -0.2 * down_m}),
                         ("BrowSad", {"inner_dz": sad_m, "outer_dz": -0.4 * sad_m})):
            tmp = _brow_tube("_tmp_brow", _brow_points(ctx, sx, ex, ez, r, bc, **kw), bc, C)
            k = b.shape_key_add(name=name)
            k.value = 0.0
            for i, v in enumerate(tmp.data.vertices):
                k.data[i].co = v.co
            me = tmp.data
            bpy.data.objects.remove(tmp, do_unlink=True)
            bpy.data.meshes.remove(me)
        brows.append(b)
    return brows


def build_ears(C, M, ctx, ec, ez):
    ears = []
    rad = ec.get("radii_m", [0.012, 0.022, 0.030])
    for sx, side in SIDES:
        e = G.uv_sphere(f"ear.{side}", (0, 0, 0), 1.0, C, 32, 16, tuple(rad))
        z = ez - _f(ec, "below_eye_m", 0.01)
        y = _f(ec, "y_m", 0.0)
        sxs = ctx.side_x(sx, y, z)
        x = (sxs if sxs is not None else sx * 0.14) + sx * _f(ec, "out_m", 0.004)
        e.location = (x, y, z)
        e.rotation_euler = (math.radians(_f(ec, "tilt_deg", -8)), 0, math.radians(sx * _f(ec, "yaw_deg", 28)))
        bpy.context.view_layer.update()
        bowl = Vector((x + sx * rad[0] * 0.9, y - rad[1] * 0.25, z))
        G.brush(e, bowl, rad[2] * 0.7, (-sx * rad[0] * 0.5, rad[1] * 0.12, 0))  # inner bowl
        G.add_mod(e, "SUBSURF", levels=1, render_levels=2)
        G.apply_mods(e)
        G.assign(e, M["face_skin"])
        ears.append(e)
    return ears


# ------------------------------------------------------------------------------------------------ expression library
SPLITTABLE = ("BrowDown", "BrowSad", "EyeSquint", "EyeWide", "MouthSmile", "MouthFrown", "MouthPout")


def _smooth01(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def add_pout(objs, centre, cfg, mouth_half_w):
    """Optional action unit MouthPout (T-058; spec.face.action_units.pout_m > 0): the lips and the skin around them push
    forward (lower lip more) and narrow slightly. One displacement field applied to every given mesh (lips, interior,
    head skin), so the lips stay on the skin. Returns the objects that got the key."""
    import numpy as np
    amount = _f(cfg, "pout_m", 0.0)
    rx = _f(cfg, "pout_radius_m", 2.4 * mouth_half_w)
    rz = rx * _f(cfg, "pout_radius_z", 0.75)
    lower = _f(cfg, "pout_lower", 0.5)    # extra forward share below the mouth line (lower lip forward)
    narrow = _f(cfg, "pout_narrow", 0.12)  # corners move in by this fraction of their x
    done = []
    for ob in objs:
        me = ob.data
        n = len(me.vertices)
        mw = ob.matrix_world
        mi = mw.inverted().to_3x3()
        co = np.empty(n * 3)
        (me.shape_keys.key_blocks[0].data if me.shape_keys else me.vertices).foreach_get("co", co)
        co = co.reshape(n, 3)
        delta = np.zeros((n, 3))
        hit = False
        for i in range(n):
            p = mw @ Vector(co[i])
            if p.y > centre.y + rx:  # front of the face only
                continue
            d = math.sqrt((p.x / rx) ** 2 + ((p.z - centre.z) / rz) ** 2)
            if d >= 1.0:
                continue
            w = (1 - d * d) ** 2
            fwd = amount * w * (1 + lower * _smooth01((centre.z - p.z) / rz * 2))
            dw = Vector((-narrow * p.x * w, -fwd, 0.0))
            delta[i] = mi @ dw
            hit = True
        if not hit:
            continue
        if me.shape_keys is None:
            ob.shape_key_add(name="Basis")
        k = ob.shape_key_add(name="MouthPout", from_mix=False)
        k.value = 0.0
        k.data.foreach_set("co", (co + delta).ravel())
        done.append(ob.name)
    return done


def split_action_units(objs, names, blend_m):
    """Optional per-side copies (T-058; spec.face.action_units.split): for every listed symmetric action unit X on any
    mesh, keys X.L (the character's left, +x) and X.R carrying the motion on that side only, blended across the
    midline over +-blend_m (world x), so X.L + X.R = X. Returns {X: [X.L, X.R]} for the units that exist."""
    import numpy as np
    made = {}
    for name in names:
        if name not in SPLITTABLE:
            raise ValueError(f"face.action_units.split: {name!r} is not splittable ({', '.join(SPLITTABLE)})")
        for ob in objs:
            sk = ob.data.shape_keys
            if sk is None or name not in sk.key_blocks:
                continue
            kb = sk.key_blocks
            n = len(ob.data.vertices)
            base = np.empty(n * 3)
            kb[0].data.foreach_get("co", base)
            full = np.empty(n * 3)
            kb[name].data.foreach_get("co", full)
            mw = ob.matrix_world
            xs = np.array([(mw @ Vector(base[3 * i:3 * i + 3])).x for i in range(n)])
            wl = np.array([_smooth01(0.5 + x / (2 * blend_m)) if blend_m > 0 else float(x > 0) for x in xs])
            for side, w in (("L", wl), ("R", 1.0 - wl)):
                k = ob.shape_key_add(name=f"{name}.{side}", from_mix=False)
                k.value = 0.0
                k.data.foreach_set("co", base + (full - base) * np.repeat(w, 3))
            made[name] = [f"{name}.L", f"{name}.R"]
    return made


def _au_shape(kb, base, au, w, np):
    """Coordinates delta of action unit `au` at weight w on one mesh: piecewise along its in-between keys when it has
    them (rotation-type motions), else linear."""
    if au not in kb:
        return 0.0
    n = len(base)

    def get(name):
        d = np.empty(n)
        kb[name].data.foreach_get("co", d)
        return d - base
    stops = [(0.0, None)] + [(f, f"{au}@{int(round(f * 100))}") for f in INBETWEENS if f"{au}@{int(round(f * 100))}" in kb] + [(1.0, au)]
    if len(stops) == 2 or w <= 0 or w > 1:
        return get(au) * w
    for (f0, k0), (f1, k1) in zip(stops, stops[1:]):
        if w <= f1 + 1e-9:
            d0 = 0.0 if k0 is None else get(k0)
            return d0 + (get(k1) - d0) * ((w - f0) / (f1 - f0))
    return get(au) * w


def bake_presets(objs, lib, ecfg, au_names):
    """Semantic presets -> shape keys of the preset name on every mesh whose action units move it, evaluated on the
    true arc of rotation-type units (their in-between keys). Meshes moved by such units also get preset in-betweens
    "<preset>@25/50/75" so the control's transition follows the arc. Returns the built preset names and each preset's
    JawOpen weight (the jaw bone is driven separately)."""
    import numpy as np
    inten = _f(ecfg, "intensity", 1.0)
    scale = ecfg.get("scale", {})
    over = ecfg.get("override", {})
    presets = dict(lib["presets"])
    for name in ecfg.get("optional", []):
        presets[name] = lib["optional_presets"][name]
    for name, w in (ecfg.get("custom") or {}).items():  # T-058: character presets as spec data (absent = unchanged)
        if name in presets:
            raise ValueError(f"face.expressions.custom: {name!r} already exists in the shared library (use override)")
        presets[name] = w
    built, jaw = [], {}
    for p, w in presets.items():
        w = {**w, **over.get(p, {})}
        s = inten * float(scale.get(p, 1.0))
        w = {k: v * s for k, v in w.items() if k in au_names and abs(v) > 1e-6}
        if not w:
            continue
        built.append(p)
        if "JawOpen" in w:
            jaw[p] = w["JawOpen"]
        for ob in objs:
            sk = ob.data.shape_keys
            if sk is None:
                continue
            kb = sk.key_blocks
            if not any(a in kb for a in w):
                continue
            n = len(ob.data.vertices) * 3
            base = np.empty(n)
            kb[0].data.foreach_get("co", base)
            arc = any(f"{a}@{int(round(INBETWEENS[0] * 100))}" in kb for a in w)
            for g in (INBETWEENS if arc else ()) + (1.0,):
                acc = base.copy()
                for a, v in w.items():
                    acc = acc + _au_shape(kb, base, a, v * g, np)
                k = ob.shape_key_add(name=p if g == 1.0 else f"{p}@{int(round(g * 100))}", from_mix=False)
                k.value = 0.0
                k.data.foreach_set("co", acc)
    return built, jaw


def add_inbetween_drivers(rig, objs):
    """Keys "<X>@NN" take a hat-shaped share of control face_<X>; the full key <X> then only covers the last
    segment, so driving face_<X> from 0 to 1 follows the in-between chain (piecewise along the arc)."""
    stops = [0.0] + list(INBETWEENS) + [1.0]
    n = 0
    for ob in objs:
        sk = ob.data.shape_keys
        if sk is None:
            continue
        names = {k.name for k in sk.key_blocks}
        for k in sk.key_blocks:
            if "@" not in k.name:
                continue
            base, pct = k.name.rsplit("@", 1)
            if f"face_{base}" not in rig.keys():
                continue
            f = int(pct) / 100.0
            i = stops.index(f)
            lo, hi = stops[i - 1], stops[i + 1]
            for key, expr in ((k, f"max(0.0, min((v - {lo}) / {f - lo:.4f}, ({hi} - v) / {hi - f:.4f}))"),
                              (sk.key_blocks[base] if base in names else None, f"max(0.0, (v - {stops[-2]}) / {1.0 - stops[-2]:.4f})")):
                if key is None:
                    continue
                key.driver_remove("value")
                d = key.driver_add("value").driver
                d.type = "SCRIPTED"
                var = d.variables.new()
                var.name, var.type = "v", "SINGLE_PROP"
                var.targets[0].id = rig
                var.targets[0].data_path = f'["face_{base}"]'
                d.expression = expr
                n += 1
    return n


def add_jaw_preset_drivers(rig, jaw_weights, angle_deg):
    """DEF-jaw rotation = (face_JawOpen + sum w_p * face_<preset>) * angle."""
    if rig.pose.bones.get("DEF-jaw") is None or rig.animation_data is None:
        return
    fc = next((f for f in rig.animation_data.drivers if f.data_path == 'pose.bones["DEF-jaw"].rotation_euler' and f.array_index == 0), None)
    if fc is None:
        return
    d = fc.driver
    terms = ["j"]
    for i, (p, w) in enumerate(sorted(jaw_weights.items())):
        v = d.variables.new()
        v.name, v.type = f"p{i}", "SINGLE_PROP"
        v.targets[0].id = rig
        v.targets[0].data_path = f'["face_{p}"]'
        terms.append(f"{w:.4f} * p{i}")
    d.expression = f"({' + '.join(terms)}) * {math.radians(angle_deg):.5f}"


# ------------------------------------------------------------------------------------------------ build
def build(C, M, head, spec, P, H, head_bone="DEF-spine.006", eye_bone="DEF-eye.{s}"):
    """Builds the face on the head mesh `head` (any skin mesh with a face). Updates P['eyes']['y'] so the eye bones
    sit at the eye centres. Returns a dict with objects, landmarks, rigid bindings, names and a report.
    A spec pinned to face_generic/2 builds through build_v2 (T-065); face_generic/1 continues below unchanged."""
    if face_version(spec) == 2:
        return build_v2(C, M, head, spec, P, H, head_bone, eye_bone)
    fs = spec["face"]
    L = fs.get("layout", {})
    ecfg = fs.get("eyes", {})
    lib = load_library()
    ex, ez = P["eyes"]["x"] * H, P["eyes"]["z"] * H
    if "spacing_m" in ecfg or "offset_z_m" in ecfg:  # v2: eye spacing (centre to centre) and height as spec values
        ex = _f(ecfg, "spacing_m", 2 * ex) / 2
        ez = ez + _f(ecfg, "offset_z_m", 0.0)
        P["eyes"]["x"], P["eyes"]["z"] = ex / H, ez / H  # the eye bones follow
    r = _f(ecfg, "radius_m", 0.03)
    z_mouth = ez - _f(L, "mouth_below_eye_m", 0.05)
    ctx = FaceContext(head, z_mouth, r)
    rep = {"generator": "face_generic/1"}
    # face skin (blush spots from the layout), used by the head skin, ears and lids
    skin_rgb = tuple(spec["materials"].get("albedo_srgb", {}).get("skin") or spec["materials"]["target_colors_srgb"]["skin"])
    bl = fs.get("blush")
    z_nose = ez - _f(L, "nose_below_eye_m", 0.03)
    if fs.get("shape"):  # v2 head proportions, sculpted before anything is placed on the surface
        rep["shape"] = FF.shape_head(head, ctx, fs["shape"], ex, ez, r)
    if fs.get("skin"):  # v2 felt face skin: soft felt blush patches + occlusion compensation (one material, body too)
        spots = []
        if bl:
            for sx, _ in SIDES:
                bx, bz = sx * (ex + _f(bl, "out_m", 0.0)), ez - _f(bl, "below_eye_m", 0.04)
                spots.append(((bx, ctx.face_y(None, bx, bz), bz), _f(bl, "radius_m", 0.025), _f(bl, "intensity", 1.0)))
            if bl.get("nose"):
                zn = z_nose + _f(fs.get("nose", {}), "offset_z_m", 0.0)
                spots.append(((0.0, ctx.face_y(None, 0.0, zn), zn), _f(bl, "nose_radius_m", _f(bl, "radius_m", 0.025)),
                              _f(bl, "nose_intensity", _f(bl, "intensity", 1.0))))
        fc = (0.0, ctx.face_y(None, 0.0, z_nose), z_nose)  # face centre (bleed weighting)
        M["face_skin"] = FF.face_skin_material("M_skin_face", skin_rgb, bl, spots, fs["skin"], fc)
        skin_assignment = MATERIALS.get_assignment(spec["materials"], "skin")
        if skin_assignment:
            MATERIALS.apply_from_assignment(M["face_skin"], skin_assignment, preserve_base_color=True)
        FF.carry_base_to_rim(M["face_skin"])
    elif bl:
        spots = []
        for sx, _ in SIDES:
            bx, bz = sx * (ex + _f(bl, "out_m", 0.0)), ez - _f(bl, "below_eye_m", 0.04)
            spots.append((bx, ctx.face_y(None, bx, bz), bz))
        if bl.get("nose"):
            spots.append((0.0, ctx.face_y(None, 0.0, z_nose), z_nose))
        M["face_skin"] = G.blush_skin_material("M_skin_face", skin_rgb, tuple(bl.get("srgb", (226, 150, 150))), spots,
                                               _f(bl, "radius_m", 0.025), subsurface=0.2)
        skin_assignment = MATERIALS.get_assignment(spec["materials"], "skin")
        if skin_assignment:
            MATERIALS.apply_from_assignment(M["face_skin"], skin_assignment, preserve_base_color=True)
    else:
        M["face_skin"] = M["skin"]
    G.assign(head, M["face_skin"])
    # nose: a soft bump on the head surface
    nc = fs.get("nose", {})
    nose_obj = None
    if nc.get("type"):  # v2 nose types
        nose_obj, nose_tip = FF.build_nose(C, M, head, ctx, nc, z_nose)
        z_nose = nose_tip.z
        rep["nose"] = {"type": nc["type"], "tip_m": [round(v, 4) for v in nose_tip]}
    elif nc:
        ny = ctx.face_y(None, 0.0, z_nose)
        G.brush(head, (0.0, ny + _f(nc, "radius_m", 0.016) * 0.3, z_nose), _f(nc, "radius_m", 0.016), (0, -_f(nc, "height_m", 0.004), 0))
        ctx.invalidate()
    # landmarks (before the eyes push nothing; the head mesh is final from here on)
    lm = {"mouth": Vector((0.0, ctx.face_y(None, 0.0, z_mouth), z_mouth))}
    zc = ez - _f(L, "chin_below_eye_m", 0.09)
    lm["chin"] = Vector((0.0, ctx.face_y(None, 0.0, zc), zc))
    lm["nose"] = Vector((0.0, ctx.face_y(None, 0.0, z_nose), z_nose))
    # eyes
    eyes, lids, frames, einfo = build_eyes(C, M, ctx, ecfg, ex, ez, _f(ecfg, "protrusion_m", 0.015),
                                           MATERIALS.get_assignment(spec["materials"], "eyes"))
    P["eyes"]["y"] = lids[0][3].y / H  # the eye bones sit at the eye centres (gaze rotates about them)
    rep["eyes"] = einfo
    for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):
        lm[f"eye_{side}"] = frames[side] @ Vector((0, -r, 0))
    ears = build_ears(C, M, ctx, fs.get("ears", {}), ez) if fs.get("ears") else []
    for (sx, side), e in zip(SIDES, ears):
        lm[f"ear_{side}"] = e.location.copy()
    if not ears:  # the jaw pivot needs ear landmarks: use the head sides at the eye line
        for sx, side in SIDES:
            lm[f"ear_{side}"] = Vector((ctx.side_x(sx, 0.0, ez - 0.01) or sx * 0.1, 0.0, ez - 0.01))
    au = fs.get("action_units", {})
    brows = build_brows(C, ctx, fs.get("brows", {}), au, ex, ez, r) if fs.get("brows") else []
    # mouth (face.py lips_jaw/2 through the context) and its interior with oral layers
    mcfg = dict(fs["mouth"])
    M.setdefault("lip", G.material("M_lip_generic", tuple(mcfg.get("lip_srgb", skin_rgb)), roughness=0.5, subsurface=0.15))
    mouth = FACE.build_mouth_lips(C, M, head, ctx, mcfg)
    cavity = FACE.cut_mouth_and_cavity(C, M, head, ctx, mcfg, mouth)
    # action units: eyes (in their frames), smile coupling (cheeks + lower lids join the lips' Smile)
    # closed-lid radius factor: 1 for spherical eyes (unchanged); with a gaze envelope the closed lid keeps the same
    # relation to the (widened) lower lid as on a spherical eye, but never comes closer than the envelope
    closed = {}
    off = _f(fs.get("blink", {}), "closed_offset_m", 0.0012) / r
    for _, side in SIDES:
        env = einfo[side]["gaze_envelope"]
        closed[side] = 1.0 if env <= 1.0 else max(env * 1.005 - off, 1 + einfo[side]["lid_gap_lower"] - _f(ecfg.get("lids", {}), "lower_gap", 0.03))
    bcfg = dict(fs.get("blink", {}))
    widened = max(einfo[side]["lid_gap_lower"] - _f(ecfg.get("lids", {}), "lower_gap", 0.03) for _, side in SIDES)
    if widened > 0:  # lids standing further off the eye need a larger seam overlap to stay closed when seen off-axis
        bcfg["overlap_deg"] = _f(bcfg, "overlap_deg", 3.0) + math.degrees(widened)
        rep["blink_overlap_deg"] = round(bcfg["overlap_deg"], 2)
    rep["blink"] = eye_action_units(eyes, lids, frames, r, bcfg, au, closed)
    if fs.get("smile_coupling"):
        rep["smile_coupling"] = FACE.add_smile_coupling(head, lids, mouth, lm, fs["smile_coupling"])
    for ob in [mouth, cavity, head] + [l[1] for l in lids]:
        _rename_key(ob, "Smile", "MouthSmile")
    if _f(au, "pout_m", 0.0) > 0:  # T-058 opt-in MouthPout (before the rest-shape bake, which may use it)
        rep["pout"] = add_pout([mouth, cavity, head], lm["mouth"], au, _f(mcfg, "half_width_m", 0.0125))
    if mcfg.get("rest_shape", "closed_smile") != "closed_smile":  # v2 mouth rest shape (baked into the basis)
        rep["mouth_rest_shape"] = {"shape": mcfg["rest_shape"],
                                   "objects": FF.bake_rest_shape([mouth, cavity, head], mcfg["rest_shape"],
                                                                     mcfg.get("rest_mix"))}
    au_names = [a for a in lib["action_units"]]
    lid_objs = [o for l in lids for o in l[:3]]
    face_objs = eyes + lid_objs + brows + [mouth, cavity, head]
    # T-058 opt-in controls (absent = unchanged output): MouthPout and per-side copies of symmetric units
    if _f(au, "pout_m", 0.0) > 0:
        au_names.append("MouthPout")
    if au.get("split"):
        rep["split_action_units"] = split_action_units(face_objs, list(au["split"]), _f(au, "split_blend_m", 0.006))
        au_names += [n for pair in rep["split_action_units"].values() for n in pair]
    present = sorted({k.name for o in face_objs if o.data.shape_keys for k in o.data.shape_keys.key_blocks[1:] if "@" not in k.name} | {"JawOpen"})
    au_built = [a for a in au_names if a in present]
    presets, jaw_w = bake_presets(face_objs, lib, fs.get("expressions", {}), set(au_built))
    rep["action_units"] = au_built
    rep["action_units_missing"] = [a for a in au_names if a not in au_built]
    rep["presets"] = presets
    rigid = [(o, head_bone) for o in brows + ears + [mouth, cavity] + ([nose_obj] if nose_obj else [])] + [(e, eye_bone.format(s=s)) for e, (_, s) in zip(eyes, SIDES)]
    # Lids use the shared binding rule: rigid to the head, or split between head and eye bone so they follow a
    # configured fraction of gaze. Concentric shells around a spherical eye never intersect it at any fraction.
    track = _f(ecfg, "lid_tracking", 0.0)
    rigid.extend(FACE.lid_bindings(lids, head_bone, eye_bone, track, tuple(side for _, side in SIDES)))
    sc = ecfg.get("scale", [1, 1, 1])
    if max(abs(float(k) - 1.0) for k in sc) > 1e-6:
        env = max(einfo[s]["gaze_envelope"] for _, s in SIDES)
        rep.setdefault("notes", []).append(
            "non-spherical eyeball (scale %s): the lids clear its rigid gaze sweep over gaze_range_deg %s (envelope %.3f, "
            "lid gap widened to at least %.1f%% of the radius); gaze beyond that range is not covered"
            % (sc, ecfg.get("gaze_range_deg", [20.0, 12.0]), env, (env * 1.01 - 1) * 100))
        if env > 1.25:
            rep.setdefault("warnings", []).append(
                "gaze envelope %.3f: the lids stand more than 25%% of the radius off the eyeball at rest (visible gap); "
                "reduce the gaze range or the eye's ovalness (iris-sliding gaze is not implemented)" % env)
    engine = {k: v for k, v in lib["engine_expressions"].items() if v in set(au_built) | set(presets)}
    for name in (fs.get("expressions", {}).get("custom") or {}):  # T-058: custom presets under their lowerCamel name
        if name in presets:
            engine.setdefault(name[0].lower() + name[1:], name)
    return {"eyes": eyes, "lids": lids, "brows": brows, "ears": ears, "nose": nose_obj, "mouth": mouth, "cavity": cavity, "landmarks": lm,
            "rigid": rigid, "frames": frames, "ctx": ctx, "controls": au_built + presets, "jaw_preset_weights": jaw_w,
            "engine_expressions": engine, "mouth_cfg": mcfg, "report": rep}


def add_landmarks(C, lm):
    empties = {}
    for k, p in lm.items():
        em = bpy.data.objects.new(f"LM_{k}", None)
        em.empty_display_size = 0.01
        em.location = p
        C.objects.link(em)
        empties[k] = em
    return empties


def bind_rigid(rig, pairs):
    """Rigid parts: full weight to one deform bone + Armature modifier (as the legacy path)."""
    for ob, bone in pairs:
        ob.parent = rig
        ob.matrix_parent_inverse = rig.matrix_world.inverted()
        for name, w in (bone.items() if isinstance(bone, dict) else ((bone, 1.0),)):  # {bone: weight} splits a part
            vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
            vg.add(list(range(len(ob.data.vertices))), w, "REPLACE")
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = rig


# ================================================================================================ face_generic/2 (T-065)
# Opt-in by the spec's face pin (generators.face or face.generator = "face_generic/2"). Everything face_generic/1 does,
# plus (spec data; see face_features "face_generic/2"):
#   lids blended into the skin   face.eyes.socket {band_deg, lower_band_deg, ramp_deg, reach_deg, clearance_m,
#                                inner_scale, follow_reach_deg}: the head skin wraps the lid shells, only a lid band shows;
#                                the socket skin follows every lid motion (Blink.*, EyeWide, EyeSquint, the smile's
#                                lower-lid lift) through shape keys on the head
#   round, full-cheeked faces    face.shape: outline_roundness/exponent, face_width_m, lower_face_length_m,
#                                cheek_fullness_m, jaw_depth_roundness (+ the face_generic/1 shape options)
#   cheek lift                   face.cheeks -> action unit CheekRaise; mouth.rest_shape "soft_smile" (closed smile
#                                with cheek lift), "parted"; rest_mix honoured for every rest shape; Smile/Frown/CheekRaise
#                                keep their absolute targets over a baked rest
#   brows                        face.brows.shape "flat_stroke" | "soft_arch" | "short_arc" presets, tapered both ends
#   lips                         face.mouth.fullness {upper, lower, forward_m, lower_forward}
def face_version(spec):
    """2 when the spec pins face_generic/2 (generators.face, else face.generator), otherwise 1."""
    pin = (spec.get("generators") or {}).get("face") or (spec.get("face") or {}).get("generator")
    return 2 if pin == "face_generic/2" else 1


def _lid_geometry(sx, ecfg, r):
    """The lid planes and radii exactly as build_eyes makes them (unit eye frame)."""
    lids_cfg = ecfg.get("lids", {})
    e_up, k_up = math.radians(_f(lids_cfg, "upper_edge_deg", 40)), _f(lids_cfg, "upper_back_tilt", 1.0)
    e_lo, k_lo = math.radians(_f(lids_cfg, "lower_edge_deg", -45)), _f(lids_cfg, "lower_tilt", 0.3)
    env = gaze_envelope(sx, ecfg)
    need = env * 1.01 - 1.0 if env > 1.0 else 0.0
    r_up = r * (1 + max(_f(lids_cfg, "upper_gap", 0.06), need))
    r_lo = r * (1 + max(_f(lids_cfg, "lower_gap", 0.03), need))
    q_up = Vector((0, -math.cos(e_up), math.sin(e_up))) * r_up
    q_lo = Vector((0, -math.cos(e_lo), math.sin(e_lo))) * r_lo
    return {"q_up": q_up, "k_up": k_up, "r_up": r_up, "q_lo": q_lo, "k_lo": k_lo, "r_lo": r_lo,
            "r_up_out": r_up + _f(lids_cfg, "upper_thickness_m", 0.0018),
            "r_lo_out": r_lo + _f(lids_cfg, "lower_thickness_m", 0.0012), "lids_cfg": lids_cfg}


def build_brows_v2(C, ctx, bc, au, ex, ez, r):
    """face_generic/2 brows: shape preset (brows.shape) under the spec values, a soft stroke tapered at both ends with
    rounded caps, re-projected on the face for every key (BrowUp.<side>, BrowDown, BrowSad)."""
    bc = FF.brow_config(bc)
    mat = (FF.brow_material("M_brow_generic", bc, MATERIALS) if bc.get("style") else
           G.material("M_brow_generic", tuple(bc.get("srgb", (110, 70, 52))), roughness=0.8))
    up_m, down_m, in_m, sad_m = (_f(au, "brow_up_m", 0.006), _f(au, "brow_down_m", 0.005), _f(au, "brow_in_m", 0.003),
                                 _f(au, "brow_sad_m", 0.005))
    sad_out = _f(au, "brow_sad_outer", 0.4)

    def tube(name, pts):
        n = len(pts)
        return G.tube(name, pts, FF.brow_widths(bc, n), [_f(bc, "depth_m", 0.0012)] * n, C, up_hint=(0, -1, 0), seg=10,
                      cap_start="round", cap_end="round")
    brows = []
    for sx, side in SIDES:
        b = tube(f"brow.{side}", _brow_points(ctx, sx, ex, ez, r, bc))
        G.assign(b, mat)
        b.shape_key_add(name="Basis")
        for name, kw in ((f"BrowUp.{side}", {"up": up_m}),
                         ("BrowDown", {"inner_dz": -down_m, "inner_dx": in_m, "up": -0.2 * down_m}),
                         ("BrowSad", {"inner_dz": sad_m, "outer_dz": -sad_out * sad_m})):
            tmp = tube("_tmp_brow", _brow_points(ctx, sx, ex, ez, r, bc, **kw))
            k = b.shape_key_add(name=name)
            k.value = 0.0
            for i, v in enumerate(tmp.data.vertices):
                k.data[i].co = v.co
            me = tmp.data
            bpy.data.objects.remove(tmp, do_unlink=True)
            bpy.data.meshes.remove(me)
        brows.append(b)
    return brows


def build_v2(C, M, head, spec, P, H, head_bone="DEF-spine.006", eye_bone="DEF-eye.{s}"):
    """face_generic/2 build (see the block comment above). Same outputs as face_generic/1's build."""
    fs = spec["face"]
    L = fs.get("layout", {})
    ecfg = fs.get("eyes", {})
    lib = load_library()
    ex, ez = P["eyes"]["x"] * H, P["eyes"]["z"] * H
    if "spacing_m" in ecfg or "offset_z_m" in ecfg:
        ex = _f(ecfg, "spacing_m", 2 * ex) / 2
        ez = ez + _f(ecfg, "offset_z_m", 0.0)
        P["eyes"]["x"], P["eyes"]["z"] = ex / H, ez / H
    r = _f(ecfg, "radius_m", 0.03)
    z_mouth = ez - _f(L, "mouth_below_eye_m", 0.05)
    ctx = FaceContext(head, z_mouth, r)
    rep = {"generator": "face_generic/2"}
    skin_rgb = tuple(spec["materials"].get("albedo_srgb", {}).get("skin") or spec["materials"]["target_colors_srgb"]["skin"])
    bl = fs.get("blush")
    z_nose = ez - _f(L, "nose_below_eye_m", 0.03)
    if fs.get("shape"):  # head proportions first (v1 options, then the v2 round-face options)
        sh = FF.shape_face_v2(head, ctx, fs["shape"], ex, ez, r, ez - _f(L, "chin_below_eye_m", 0.09))
        sh.update(FF.shape_head(head, ctx, {k: v for k, v in fs["shape"].items() if k != "cheek_roundness_m"}, ex, ez, r))
        rep["shape"] = sh
    if fs.get("skin"):
        spots = []
        if bl:
            for sx, _ in SIDES:
                bx, bz = sx * (ex + _f(bl, "out_m", 0.0)), ez - _f(bl, "below_eye_m", 0.04)
                spots.append(((bx, ctx.face_y(None, bx, bz), bz), _f(bl, "radius_m", 0.025), _f(bl, "intensity", 1.0)))
            if bl.get("nose"):
                zn = z_nose + _f(fs.get("nose", {}), "offset_z_m", 0.0)
                spots.append(((0.0, ctx.face_y(None, 0.0, zn), zn), _f(bl, "nose_radius_m", _f(bl, "radius_m", 0.025)),
                              _f(bl, "nose_intensity", _f(bl, "intensity", 1.0))))
        fc = (0.0, ctx.face_y(None, 0.0, z_nose), z_nose)
        M["face_skin"] = FF.face_skin_material("M_skin_face", skin_rgb, bl, spots, fs["skin"], fc)
        skin_assignment = MATERIALS.get_assignment(spec["materials"], "skin")
        if skin_assignment:
            MATERIALS.apply_from_assignment(M["face_skin"], skin_assignment, preserve_base_color=True)
        FF.carry_base_to_rim(M["face_skin"])
    elif bl:
        spots = []
        for sx, _ in SIDES:
            bx, bz = sx * (ex + _f(bl, "out_m", 0.0)), ez - _f(bl, "below_eye_m", 0.04)
            spots.append((bx, ctx.face_y(None, bx, bz), bz))
        if bl.get("nose"):
            spots.append((0.0, ctx.face_y(None, 0.0, z_nose), z_nose))
        M["face_skin"] = G.blush_skin_material("M_skin_face", skin_rgb, tuple(bl.get("srgb", (226, 150, 150))), spots,
                                               _f(bl, "radius_m", 0.025), subsurface=0.2)
        skin_assignment = MATERIALS.get_assignment(spec["materials"], "skin")
        if skin_assignment:
            MATERIALS.apply_from_assignment(M["face_skin"], skin_assignment, preserve_base_color=True)
    else:
        M["face_skin"] = M["skin"]
    G.assign(head, M["face_skin"])
    nc = fs.get("nose", {})
    nose_obj = None
    if nc.get("type"):
        nose_obj, nose_tip = FF.build_nose(C, M, head, ctx, nc, z_nose)
        z_nose = nose_tip.z
        rep["nose"] = {"type": nc["type"], "tip_m": [round(v, 4) for v in nose_tip]}
    elif nc:
        ny = ctx.face_y(None, 0.0, z_nose)
        G.brush(head, (0.0, ny + _f(nc, "radius_m", 0.016) * 0.3, z_nose), _f(nc, "radius_m", 0.016), (0, -_f(nc, "height_m", 0.004), 0))
        ctx.invalidate()
    lm = {"mouth": Vector((0.0, ctx.face_y(None, 0.0, z_mouth), z_mouth))}
    zc = ez - _f(L, "chin_below_eye_m", 0.09)
    lm["chin"] = Vector((0.0, ctx.face_y(None, 0.0, zc), zc))
    lm["nose"] = Vector((0.0, ctx.face_y(None, 0.0, z_nose), z_nose))
    eyes, lids, frames, einfo = build_eyes(C, M, ctx, ecfg, ex, ez, _f(ecfg, "protrusion_m", 0.015),
                                           MATERIALS.get_assignment(spec["materials"], "eyes"))
    P["eyes"]["y"] = lids[0][3].y / H
    rep["eyes"] = einfo
    for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):
        lm[f"eye_{side}"] = frames[side] @ Vector((0, -r, 0))
    # lids blended into the skin: the head wraps the lid shells (before anything else is placed on the surface)
    sock_cfg = ecfg.get("socket", {})
    socket_w = {}
    if sock_cfg.get("enabled", True):
        if int(sock_cfg.get("refine_cuts", 2)) > 0:
            rep["socket_refined_faces"] = FF.refine_eye_regions(head, [frames[s] for _, s in SIDES], r,
                                                                _f(sock_cfg, "refine_reach", 1.8), int(sock_cfg.get("refine_cuts", 2)))
            ctx.invalidate()
        sides = []
        for sx, side in SIDES:
            lg = _lid_geometry(sx, ecfg, r)
            sides.append({"sx": sx, "side": side, "T": frames[side], "r": r, "r_up_out": lg["r_up_out"], "r_lo_out": lg["r_lo_out"],
                          "up_edge": FF.lid_edges(lambda a, lg=lg: _lid_edge(lg["q_up"], lg["k_up"], lg["r_up"], a, lg["lids_cfg"], True),
                                                  corner_deg=_f(sock_cfg, "corner_deg", 60.0)),
                          "lo_edge": FF.lid_edges(lambda a, lg=lg: _lid_edge(lg["q_lo"], lg["k_lo"], lg["r_lo"], a, lg["lids_cfg"], False),
                                                  corner_deg=_f(sock_cfg, "corner_deg", 60.0))})
        rep["lid_socket"], socket_w = FF.lid_socket(head, ctx, sides, sock_cfg)
    ears = build_ears(C, M, ctx, fs.get("ears", {}), ez) if fs.get("ears") else []
    for (sx, side), e in zip(SIDES, ears):
        lm[f"ear_{side}"] = e.location.copy()
    if not ears:
        for sx, side in SIDES:
            lm[f"ear_{side}"] = Vector((ctx.side_x(sx, 0.0, ez - 0.01) or sx * 0.1, 0.0, ez - 0.01))
    au = fs.get("action_units", {})
    brows = build_brows_v2(C, ctx, fs.get("brows", {}), au, ex, ez, r) if fs.get("brows") else []
    mcfg = dict(fs["mouth"])
    M.setdefault("lip", G.material("M_lip_generic", tuple(mcfg.get("lip_srgb", skin_rgb)), roughness=0.5, subsurface=0.15))
    mouth = FACE.build_mouth_lips(C, M, head, ctx, mcfg)
    cavity = FACE.cut_mouth_and_cavity(C, M, head, ctx, mcfg, mouth)
    full = FF.lip_fullness(mouth, mcfg)
    if full:
        rep["lip_fullness"] = full
    closed = {}
    off = _f(fs.get("blink", {}), "closed_offset_m", 0.0012) / r
    for _, side in SIDES:
        env = einfo[side]["gaze_envelope"]
        closed[side] = 1.0 if env <= 1.0 else max(env * 1.005 - off, 1 + einfo[side]["lid_gap_lower"] - _f(ecfg.get("lids", {}), "lower_gap", 0.03))
    bcfg = dict(fs.get("blink", {}))
    widened = max(einfo[side]["lid_gap_lower"] - _f(ecfg.get("lids", {}), "lower_gap", 0.03) for _, side in SIDES)
    if widened > 0:
        bcfg["overlap_deg"] = _f(bcfg, "overlap_deg", 3.0) + math.degrees(widened)
        rep["blink_overlap_deg"] = round(bcfg["overlap_deg"], 2)
    rep["blink"] = eye_action_units(eyes, lids, frames, r, bcfg, au, closed)
    if socket_w:  # the socket skin follows its lid in every lid motion
        wide_up, wide_lo = _f(au, "wide_upper_deg", 10), _f(au, "wide_lower_deg", 6)
        # A closing lid (Blink, EyeSquint, the smile's lower-lid lift) slides out from under the crease, so the skin
        # stays; an opening lid (EyeWide) retracts under it, so the skin above the crease rises with it.
        FF.socket_key(head, "EyeWide", socket_w, {k: v for _, s in SIDES for k, v in (((s, "up"), -wide_up), ((s, "lo"), wide_lo))})
    if fs.get("smile_coupling"):
        rep["smile_coupling"] = FACE.add_smile_coupling(head, lids, mouth, lm, fs["smile_coupling"])
        FF.taper_key_front(head, "Smile", lm["mouth"].y + 0.03)  # no step on the cheeks at the coupling's cut-off
    for ob in [mouth, cavity, head] + [l[1] for l in lids]:
        _rename_key(ob, "Smile", "MouthSmile")
    if fs.get("cheeks"):
        cr = FF.add_cheek_raise(head, lm, fs["cheeks"], ex, ez)
        if cr:
            rep["cheek_raise"] = cr
    if socket_w:  # the lower lids ride on the cheek skin (smile, cheek lift)
        rep["lids_follow_skin"] = FF.lids_follow_skin(head, [l[1] for l in lids], ("MouthSmile", "CheekRaise"))
    if _f(au, "pout_m", 0.0) > 0:
        rep["pout"] = add_pout([mouth, cavity, head], lm["mouth"], au, _f(mcfg, "half_width_m", 0.0125))
    if mcfg.get("rest_shape", "closed_smile") != "closed_smile" or mcfg.get("rest_mix"):
        rep["mouth_rest_shape"] = {"shape": mcfg.get("rest_shape", "closed_smile"),
                                   "objects": FF.bake_rest_shape_v2([mouth, cavity, head] + [l[1] for l in lids],
                                                                    mcfg.get("rest_shape", "closed_smile"), mcfg.get("rest_mix"))}
    au_names = [a for a in lib["action_units"]]
    if rep.get("cheek_raise"):
        au_names.append("CheekRaise")
    lid_objs = [o for l in lids for o in l[:3]]
    face_objs = eyes + lid_objs + brows + [mouth, cavity, head]
    if _f(au, "pout_m", 0.0) > 0:
        au_names.append("MouthPout")
    if au.get("split"):
        rep["split_action_units"] = split_action_units(face_objs, list(au["split"]), _f(au, "split_blend_m", 0.006))
        au_names += [n for pair in rep["split_action_units"].values() for n in pair]
    present = sorted({k.name for o in face_objs if o.data.shape_keys for k in o.data.shape_keys.key_blocks[1:] if "@" not in k.name} | {"JawOpen"})
    au_built = [a for a in au_names if a in present]
    presets, jaw_w = bake_presets(face_objs, lib, fs.get("expressions", {}), set(au_built))
    rep["action_units"] = au_built
    rep["action_units_missing"] = [a for a in au_names if a not in au_built]
    rep["presets"] = presets
    if socket_w:
        rep["lid_shell_exposed"] = FF.shell_exposure(head, [l[0] for l in lids] + [l[1] for l in lids])
    rigid = [(o, head_bone) for o in brows + ears + [mouth, cavity] + ([nose_obj] if nose_obj else [])] + [(e, eye_bone.format(s=s)) for e, (_, s) in zip(eyes, SIDES)]
    track = _f(ecfg, "lid_tracking", 0.0)
    rigid.extend(FACE.lid_bindings(lids, head_bone, eye_bone, track, tuple(side for _, side in SIDES)))
    sc = ecfg.get("scale", [1, 1, 1])
    if max(abs(float(k) - 1.0) for k in sc) > 1e-6:
        env = max(einfo[s]["gaze_envelope"] for _, s in SIDES)
        rep.setdefault("notes", []).append(
            "non-spherical eyeball (scale %s): the lids clear its rigid gaze sweep over gaze_range_deg %s (envelope %.3f)"
            % (sc, ecfg.get("gaze_range_deg", [20.0, 12.0]), env))
    engine = {k: v for k, v in lib["engine_expressions"].items() if v in set(au_built) | set(presets)}
    for name in (fs.get("expressions", {}).get("custom") or {}):
        if name in presets:
            engine.setdefault(name[0].lower() + name[1:], name)
    return {"eyes": eyes, "lids": lids, "brows": brows, "ears": ears, "nose": nose_obj, "mouth": mouth, "cavity": cavity, "landmarks": lm,
            "rigid": rigid, "frames": frames, "ctx": ctx, "controls": au_built + presets, "jaw_preset_weights": jaw_w,
            "engine_expressions": engine, "mouth_cfg": mcfg, "report": rep}
