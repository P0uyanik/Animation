"""Shared, spec-driven groom system (`groom/1`): hair is a list of structures in spec.hair.structures.

The generalisation of hair_clumps/2 (hair.py). It reuses that module's scalp cap and real-scalp placement and the
character's own head mesh; every shape, count, position, size and material is spec data. No character names.
hair_clumps/1 and /2 stay unchanged (the legacy boy path), so earlier outputs are byte-identical.

Conventions (as hair.py): azimuth 0 = front (-Y), +90 = the character's left (+X), 180 = back; elevation above the
head centre. Lengths in metres. The head frame is the head centre and half-axes from spec.body.params.head.

Structures ({"type": ..., "name": ...}; "name" defaults to the type; objects are named hair_<name>):
  scalp_cap   the head surface above a hairline, offset outwards (hair.scalp_cap): offset, hairline, face_cut
  sweep       locks lying on the scalp from roots towards a gather point (e.g. a bun base, a ponytail, the crown):
              count, az [from, to], el_root [lo, hi], target {"az", "el"} or {"bun": index}, lift, width, thick,
              tuck (fraction of the way to the target, default 1.0)
  fringe      locks from a part line over the forehead: root_az [...], root_el, tip_x [...], tip_z [...], tip_gap,
              bulge, width, thick, sweep_x (tip shift towards the sweep side)
  locks       hanging locks; style "straight" | "wavy" | "curly" (long hair, ringlets, side locks):
              count, az [from, to], mirror, el_root [lo, hi], el_leave, lift [root, leave], hang_radii [rx, ry],
              z_end [lo, hi] (absolute, metres), flare, width, thick, tip_frac,
              curl {radius, pitch, radius_growth, start, start_jitter, jitter, direction ("alternate", "cw", "ccw"),
                    wobble, wobble_wavelength, sway}  (wobble: seeded along-length variation of radius and pitch,
                    relative; sway: lateral wander of the centre line in metres, so ringlets are irregular),
              wave {amplitude, wavelength},
              hang_jitter (per-lock relative jitter of hang_radii: depth layering instead of one curtain),
              rest_radii [rx, ry] + rest_z (drape: below the head the lock moves in to this ellipse by rest_z, so long
              hair lies on the back/shoulders instead of hanging at the skull radius)
  bun         one or more coiled buns: buns [{az, el, lift, radius, height, wrap ("cw"|"ccw"), turns, ropes,
              rope_thick, tilt}]; a core keeps the coil closed
  tie         a band around a bun base: bun (index), radius_scale, tube, height_frac, material slot
  bow         a bow on a bun or the scalp: bun (index) or az/el, around_deg, height_frac, size, loop, tail, material
  flowers     felt flowers on a bun: bun (index), items [{around_deg, height_frac, size}], petals, material,
              centre_material

Yarn: every lock, coil and sweep is a plied rope (spec.hair.yarn: plies, depth, twist_per_m, seg, step_m, fibre_lean),
so the wool-yarn twist is geometry; the fibre/sheen response comes from the material preset (spec.materials.assignments).
Every rope carries its own UV map "ps_fibre" (U = metres around the rope in the frame of the twisting plies, scaled by
fibre_lean; V = metres along the rope), so a preset with fibre.coordinates "uv" lays its ridges along each rope.
Materials: each structure names a slot ("material", default "hair"); the caller resolves slots to materials.
Binding: spec.hair.binding {"blend_z": [lo, hi]}: vertices below lo follow the chest bone, above hi the head bone,
linear in between (long hair hangs from the head but rests on the back). Without it everything follows the head.

Dynamics (optional; T-021, docs/SECONDARY_MOTION.md): spec.hair.dynamics adds spring-chain bones for the engine's
secondary-motion layer. Without it (or with "enabled": false) nothing changes (no bones, same geometry and weights).
  {"enabled": true,
   "defaults": {stiffness, stiffness_tip, damping, gravity, drag, limit_deg, radius},      engine spring parameters
   "structures": {"<structure name>": {"bones": n | [lo, hi], "bone_length": m, "every": k, "blend": f, <params>}},
   "colliders": [{"name", "type": "sphere", "bone": "head"|"chest", "head_offset": [x, y, z], "radius": r} |
                 {"name", "type": "capsule", "bone": "head"|"chest", "a": [x, y, z], "b": [x, y, z], "radius": r}]}
  locks: one chain per lock (every k-th lock) along its hanging centre line, from where it leaves the scalp to the tip;
         n bones, or round(length / bone_length) clamped to [lo, hi]; rope vertices are skinned along the chain
         (linear between bone centres; the first half bone blends from the static binding over "blend" bones).
  bun:   n bones (1-2) along each bun's axis from its base; bun ropes and core, and the ties / bows / flowers that sit
         on that bun, follow it (weights by height along the axis).
  colliders: "bone" names the spec's rig.head_bone / rig.chest_bone; a sphere's centre is the head frame centre plus
         head_offset; capsule ends are absolute (Blender coordinates, metres).
The chain list is stored on the rig object ("ps_dynamics", JSON, Blender coordinates and bone names) for
export_engine.py, which writes the package "dynamics" block.
"""
import json
import math
import random

try:
    from mathutils import Vector
except ImportError:  # plain Python: spec validation only (validate() needs no Blender)
    Vector = None


def _hair():
    import hair
    return hair


def _felt():
    import groom_felt
    return groom_felt


FINISHES = ("yarn", "felt")
FINISH_TYPES = {"sweep", "fringe", "locks", "bun"}


def finish(st, ctx):
    """'yarn' (plied ropes, the groom/1 default) or 'felt' (T-033): structure "finish", else spec.hair.finish."""
    return st.get("finish", ctx.get("finish", "yarn"))

GENERATOR = "groom/1"
YARN_DEFAULT = {"plies": 3, "depth": 0.16, "twist_per_m": 160.0, "seg": 12, "step_m": 0.004, "fibre_lean": 0.5}
UV_NAME = "ps_fibre"


# ------------------------------------------------------------------------------------------- head frame / placement
class Scalp:
    """Points on the real head surface by direction from the head centre (BVH ray cast), ellipsoid fallback."""

    def __init__(self, head, centre, radii, offset):
        import bpy
        from mathutils.bvhtree import BVHTree
        self.centre, self.radii, self.offset = Vector(centre), Vector(radii), float(offset)
        deps = bpy.context.evaluated_depsgraph_get()
        self.bvh = BVHTree.FromObject(head, deps)
        self.mw = head.matrix_world.copy()
        self.inv = self.mw.inverted()

    @staticmethod
    def direction(az, el):
        a, e = math.radians(az), math.radians(el)
        return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))

    def at_dir(self, d, lift=0.0):
        d = Vector(d).normalized()
        o = self.inv @ self.centre
        dl = (self.inv.to_3x3() @ d).normalized()
        hit, nrm, _, _ = self.bvh.ray_cast(o, dl)
        if hit is None:  # ellipsoid fallback
            p = self.centre + Vector((d.x * self.radii.x, d.y * self.radii.y, d.z * self.radii.z))
            n = Vector((d.x / self.radii.x, d.y / self.radii.y, d.z / self.radii.z)).normalized()
        else:
            p = self.mw @ hit
            n = (self.mw.to_3x3().inverted().transposed() @ nrm).normalized()
            if n.dot(d) < 0:
                n = -n
        return p + n * (self.offset + lift), n

    def at(self, az, el, lift=0.0):
        return self.at_dir(self.direction(az, el), lift)


def slerp(a, b, t):
    a, b = a.normalized(), b.normalized()
    dot = max(-1.0, min(1.0, a.dot(b)))
    om = math.acos(dot)
    if om < 1e-5:
        return a.copy()
    return (a * math.sin((1 - t) * om) + b * math.sin(t * om)) / math.sin(om)


def catmull_rom(ctrl, step):
    """Resample a control polyline with a centripetal-ish Catmull-Rom spline at about `step` metres."""
    P = [Vector(p) for p in ctrl]
    if len(P) < 2:
        return P
    ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(2, int(math.ceil((p2 - p1).length / step)))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1].copy())
    return out


def resample(pts, step):
    """Uniform spacing along a dense polyline."""
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + (b - a).length)
    L = s[-1]
    n = max(2, int(math.ceil(L / step)) + 1)
    out, j = [], 0
    for i in range(n):
        x = L * i / (n - 1)
        while j < len(s) - 2 and s[j + 1] < x:
            j += 1
        t = 0.0 if s[j + 1] == s[j] else (x - s[j]) / (s[j + 1] - s[j])
        out.append(pts[j].lerp(pts[j + 1], t))
    return out


# ------------------------------------------------------------------------------------------------ yarn rope geometry
def rope_mesh(pts, widths, thicks, yarn, up_hint=(0, 0, 1), closed=False, phase=0.0, cap_rings=3, section=None):
    """Vertices, faces and per-corner UVs of a plied yarn rope along pts: a section whose radius is modulated by
    `plies` lobes that rotate with arc length (twist), so the plies wind around the rope. Rounded end caps.
    UV (metres): U around the rope, measured in the frame of the plies (lean = yarn.fibre_lean), V along it.
    section(theta, s) -> radius multiplier replaces the ply modulation (felt locks: soft irregular section)."""
    G = HAIR_G()
    seg = int(yarn["seg"])
    plies, depth, tw = int(yarn["plies"]), float(yarn["depth"]), float(yarn["twist_per_m"])
    P, T, N, B = G.frames_along(pts, up_hint)
    s = [0.0]
    for a, b in zip(P, P[1:]):
        s.append(s[-1] + (b - a).length)
    rings, ring_s, ring_r = [], [], []
    lean = float(yarn.get("fibre_lean", 0.5))

    def ring(p, t, n, b, w, h, sk):
        ph = phase + sk * tw
        r = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            if section is not None:
                m = section(th, sk)
            else:
                m = 1.0 + depth * math.cos(plies * (th - ph)) if plies > 1 else 1.0
            r.append(p + b * (math.cos(th) * w * m) + n * (math.sin(th) * h * m))
        return r
    for i, p in enumerate(P):
        rings.append(ring(p, T[i], N[i], B[i], widths[i], thicks[i], s[i]))
        ring_s.append(s[i])
        ring_r.append(0.5 * (widths[i] + thicks[i]))
    caps = []
    if not closed:
        for end, sign in ((0, -1), (len(P) - 1, 1)):
            ext = []
            for k in range(1, cap_rings + 1):
                ang = k * (math.pi / 2) / (cap_rings + 1)
                f = math.cos(ang)
                off = T[end] * sign * max(widths[end], thicks[end]) * math.sin(ang)
                ext.append(ring(P[end] + off, T[end], N[end], B[end], widths[end] * f, thicks[end] * f, s[end]))
            caps.append((ext, P[end] + T[end] * sign * max(widths[end], thicks[end])))
        r0, r1 = max(widths[0], thicks[0]), max(widths[-1], thicks[-1])
        pre = [-r0 * math.sin(k * (math.pi / 2) / (cap_rings + 1)) for k in range(cap_rings, 0, -1)]
        post = [s[-1] + r1 * math.sin(k * (math.pi / 2) / (cap_rings + 1)) for k in range(1, cap_rings + 1)]
        ring_r = [ring_r[0]] * cap_rings + ring_r + [ring_r[-1]] * cap_rings
        ring_s = pre + ring_s + post
        rings = list(reversed(caps[0][0])) + rings + caps[1][0]
    verts = [tuple(v) for r in rings for v in r]
    faces, uvs = [], []
    nr = len(rings)
    total = ring_s[-1] + (ring_s[1] - ring_s[0] if closed and nr > 1 else 0.0)

    def uv(i, k, wrap_s=False):  # k may equal seg (seam): U keeps increasing instead of wrapping to 0
        si = total if wrap_s else ring_s[i]
        rr = ring_r[i]
        return (rr * (2 * math.pi * k / seg - lean * (phase + si * tw)), si)
    for i in range(nr - 1 + (1 if closed else 0)):
        a, b = i % nr, (i + 1) % nr
        wrap = closed and b == 0
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((a * seg + k, a * seg + k2, b * seg + k2, b * seg + k))
            uvs.append((uv(a, k), uv(a, k + 1), uv(b, k + 1, wrap), uv(b, k, wrap)))
    if not closed:
        i0 = len(verts)
        verts.append(tuple(caps[0][1]))
        faces += [(i0, k2, k) for k, k2 in ((k, (k + 1) % seg) for k in range(seg))]
        uvs += [((ring_r[0] * math.pi * (2 * k + 1) / seg, ring_s[0] - 0.002), uv(0, k + 1), uv(0, k)) for k in range(seg)]
        i1 = len(verts)
        verts.append(tuple(caps[1][1]))
        last = (nr - 1) * seg
        faces += [(i1, last + k, last + k2) for k, k2 in ((k, (k + 1) % seg) for k in range(seg))]
        uvs += [((ring_r[-1] * math.pi * (2 * k + 1) / seg, ring_s[-1] + 0.002), uv(nr - 1, k), uv(nr - 1, k + 1))
                for k in range(seg)]
    return verts, faces, uvs


def HAIR_G():
    import geom
    return geom


class MeshBucket:
    """Collects vertices/faces of many ropes into one object (fast; one object per structure)."""

    def __init__(self):
        self.verts, self.faces, self.uvs = [], [], []
        self.recalc = False  # felt shells: make face winding consistent (outwards) before smooth shading

    def add(self, verts, faces, uvs=None):
        o = len(self.verts)
        self.verts.extend(verts)
        self.faces.extend(tuple(i + o for i in f) for f in faces)
        self.uvs.extend(uvs if uvs is not None else [((0.0, 0.0),) * len(f) for f in faces])

    def obj(self, name, C):
        """One mesh with the per-rope UV map (set before validate(), which keeps the loop data consistent)."""
        import bpy
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        layer = me.uv_layers.new(name=UV_NAME)
        flat = [c for f in self.uvs for corner in f for c in corner]
        layer.data.foreach_set("uv", flat)
        me.validate()
        if self.recalc:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        me.shade_smooth()
        ob = bpy.data.objects.new(name, me)
        C.objects.link(ob)
        return ob


def taper(n, w0, w1, tip_frac=1.0, swell=0.15):
    """Per-point half-widths: w0 at the root to w1, a slight swell in the middle, and tip_frac at the very tip."""
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        w = w0 + (w1 - w0) * t
        w *= 1.0 + swell * math.sin(math.pi * t)
        if t > 0.85:
            w *= 1.0 - (1.0 - tip_frac) * ((t - 0.85) / 0.15)
        out.append(w)
    return out


def rng_range(R, v):
    return R.uniform(*v) if isinstance(v, (list, tuple)) else float(v)


# ------------------------------------------------------------------------------------------------------- structures
def build_sweep(st, ctx, R):
    if finish(st, ctx) == "felt":
        b, info = _felt().build_volume(_felt().sweep_as_gather(st), ctx, R)
        return b, dict(info, finish="felt")
    sc, yarn = ctx["scalp"], ctx["yarn"]
    tgt = st.get("target", {})
    if "bun" in tgt:
        tdir = ctx["buns"][int(tgt["bun"])]["base_dir"]
    else:
        tdir = Scalp.direction(float(tgt["az"]), float(tgt["el"]))
    bucket = MeshBucket()
    cnt = int(st["count"])
    a0, a1 = st["az"]
    lift = st.get("lift", [0.004, 0.010])
    tuck = float(st.get("tuck", 1.0))
    for k in range(cnt):
        az = a0 + (a1 - a0) * (k + R.uniform(0.3, 0.7)) / cnt
        d0 = Scalp.direction(az, rng_range(R, st["el_root"]))
        n_pts = 24
        pts = []
        for i in range(n_pts):
            t = i / (n_pts - 1) * tuck
            d = slerp(d0, tdir, t)
            p, _ = sc.at_dir(d, lift[0] + (lift[1] - lift[0]) * math.sin(math.pi * min(1.0, t * 1.1)))
            pts.append(p)
        pts = resample(catmull_rom(pts, yarn["step_m"]), yarn["step_m"])
        w, h = rng_range(R, st["width"]) / 2, rng_range(R, st["thick"]) / 2
        nrm = sc.at_dir(d0)[1]
        bucket.add(*rope_mesh(pts, taper(len(pts), w, w * 0.75, 0.5), taper(len(pts), h, h * 0.8, 0.5), yarn,
                              up_hint=nrm, phase=R.uniform(0, 6.28)))
    return bucket, {"locks": cnt}


def build_fringe(st, ctx, R):
    if finish(st, ctx) == "felt":
        b, info = _felt().build_volume(_felt().fringe_as_sheet(st), ctx, R)
        return b, dict(info, finish="felt")
    sc, yarn, face_y, head = ctx["scalp"], ctx["yarn"], ctx["face_y"], ctx["head"]
    bucket = MeshBucket()
    n = len(st["tip_x"])
    for k in range(n):
        az = st["root_az"][k] + R.uniform(-3, 3)
        root, nr = sc.at(az, rng_range(R, st["root_el"]), 0.004)
        xt = st["tip_x"][k] + R.uniform(-0.004, 0.004)
        zt = st["tip_z"][k] + R.uniform(-0.004, 0.004)
        tip = Vector((xt, face_y(head, xt, zt) - float(st.get("tip_gap", 0.012)), zt))
        mid = (root + tip) / 2 + nr * float(st.get("bulge", 0.02))
        q = HAIR_G().bezier(root, mid, tip, 16)
        pts = resample(catmull_rom(q, yarn["step_m"]), yarn["step_m"])
        w, h = rng_range(R, st["width"]) / 2, rng_range(R, st["thick"]) / 2
        bucket.add(*rope_mesh(pts, taper(len(pts), w, w * 0.8, float(st.get("tip_frac", 0.45))),
                              taper(len(pts), h, h * 0.85, float(st.get("tip_frac", 0.45))), yarn, up_hint=nr,
                              phase=R.uniform(0, 6.28)))
    return bucket, {"locks": n}


def hanging_path(st, ctx, R, az, sx):
    """Centre line of a hanging lock: along the scalp from el_root to el_leave, then down at the hang ellipse."""
    sc = ctx["scalp"]
    c = sc.centre
    el0 = rng_range(R, st["el_root"])
    el1 = float(st.get("el_leave", -10))
    l0, l1 = st.get("lift", [0.004, 0.02])
    ctrl = []
    m = 6
    for i in range(m):
        t = i / (m - 1)
        p, _ = sc.at(az, el0 + (el1 - el0) * t, l0 + (l1 - l0) * t)
        ctrl.append(p)
    rx, ry = st["hang_radii"]
    if st.get("hang_jitter"):  # per-lock depth layering (only drawn when asked: other locks keep their seeds)
        j = 1 + float(st["hang_jitter"]) * R.uniform(-1, 1)
        rx, ry = rx * j, ry * j
    a = math.radians(az)
    hdir = Vector((math.sin(a), -math.cos(a), 0.0))
    last = ctrl[-1]
    hang = Vector((c.x + math.sin(a) * rx, c.y - math.cos(a) * ry, 0))
    if (last.xy - c.xy).length > (hang.xy - c.xy).length:  # never pull a lock inwards of where it leaves the scalp
        hang = Vector((last.x, last.y, 0))
    z_end = rng_range(R, st["z_end"])
    flare = float(st.get("flare", 0.0))
    z1 = last.z - 0.03
    ctrl.append(Vector((hang.x, hang.y, z1)))
    drop = max(0.0, z1 - z_end)
    if st.get("rest_radii") and z_end < float(st.get("rest_z", z1)) < z1:
        # drape: below the head the lock moves in towards the rest ellipse (shoulders/back), reached at rest_z
        qx, qy = st["rest_radii"]
        rest = Vector((c.x + math.sin(a) * qx, c.y - math.cos(a) * qy, 0))
        if (rest.xy - c.xy).length < (hang.xy - c.xy).length:
            zr = float(st["rest_z"])
            mid = hang.lerp(rest, 0.6)
            ctrl.append(Vector((mid.x, mid.y, z1 - 0.55 * (z1 - zr))))
            ctrl.append(Vector((rest.x, rest.y, zr)))
            hang, z1 = rest, zr
            drop = max(0.0, z1 - z_end)
    tipxy = hang + hdir * flare * drop
    if drop > 0.06:
        ctrl.append(Vector((hang.x, hang.y, z1)).lerp(Vector((tipxy.x, tipxy.y, z_end)), 0.5))
    ctrl.append(Vector((tipxy.x, tipxy.y, min(z_end, z1 - 0.01))))
    return ctrl, hdir


def smooth_noise(R, wavelength):
    """A seeded smooth 1-D function of arc length in [-1, 1]: two incommensurate sines with random phases."""
    l1, l2 = wavelength * R.uniform(0.8, 1.25), wavelength * R.uniform(0.38, 0.55)
    p1, p2 = R.uniform(0, 2 * math.pi), R.uniform(0, 2 * math.pi)
    return lambda x: 0.65 * math.sin(2 * math.pi * x / l1 + p1) + 0.35 * math.sin(2 * math.pi * x / l2 + p2)


def build_locks(st, ctx, R):
    yarn = ctx["yarn"]
    style = st.get("style", "straight")
    felt = finish(st, ctx) == "felt"
    bucket = MeshBucket()
    if felt:  # felt_lock: soft irregular section, no plies (its own seeded stream: centre lines keep their seeds)
        RF = random.Random("felt_lock:" + st.get("name", st["type"]) + ":" + str(ctx.get("seed", 0)))
        bucket.recalc = True
    sides = (1, -1) if st.get("mirror") else (1,)
    a0, a1 = st["az"]
    cnt = int(st["count"])
    curl = st.get("curl") or {}
    wave = st.get("wave") or {}
    made = 0
    for sx in sides:
        for k in range(cnt):
            az = sx * (a0 + (a1 - a0) * (k + R.uniform(0.25, 0.75)) / cnt)
            ctrl, hdir = hanging_path(st, ctx, R, az, sx)
            base = resample(catmull_rom(ctrl, 0.004), 0.004)
            n_scalp = 5  # control points on the scalp (the hanging part starts after them)
            s = [0.0]
            for p, q in zip(base, base[1:]):
                s.append(s[-1] + (q - p).length)
            # where the lock leaves the scalp: the arc length of the scalp control points
            s_leave = sum((ctrl[i + 1] - ctrl[i]).length for i in range(n_scalp - 1))
            pts = base
            if style in ("curly", "wavy"):
                tang = Vector((0, 0, 1)).cross(hdir).normalized()
                ph = R.uniform(0, 2 * math.pi)
                if style == "curly":
                    jt = float(curl.get("jitter", 0.0))  # per-lock relative variation of radius and pitch
                    r0 = float(curl["radius"]) * (1 + jt * R.uniform(-1, 1))
                    pitch = float(curl["pitch"]) * (1 + jt * R.uniform(-1, 1))
                    grow = float(curl.get("radius_growth", 0.0))
                    dmode = curl.get("direction", "alternate")
                    dsign = (1 if (k + (sx < 0)) % 2 == 0 else -1) if dmode == "alternate" else (1 if dmode == "ccw" else -1)
                    s0 = s_leave + float(curl.get("start", 0.03)) + R.uniform(0, float(curl.get("start_jitter", 0.0)))
                    wob = float(curl.get("wobble", 0.0))  # along-length irregularity of radius and pitch
                    sway = float(curl.get("sway", 0.0))  # lateral wander of the centre line (m)
                    if wob or sway:
                        wl = float(curl.get("wobble_wavelength", 0.12))
                        n_r, n_p, n_s = smooth_noise(R, wl), smooth_noise(R, wl), smooth_noise(R, wl * 1.6)
                    # helix: dense sampling of the centre line, then the offset around it
                    dense = resample(base, min(0.002, pitch / 14))
                    sd = [0.0]
                    for p, q in zip(dense, dense[1:]):
                        sd.append(sd[-1] + (q - p).length)
                    L = sd[-1]
                    pts = []
                    phi, prev = ph, None
                    for p, si in zip(dense, sd):
                        u = max(0.0, si - s0)
                        ramp = min(1.0, u / max(1e-6, pitch * 0.75))
                        r = r0 * (1 + grow * (si - s0) / max(1e-6, L - s0)) * ramp
                        if wob or sway:
                            pl = pitch * (1 + wob * n_p(si))
                            if prev is not None:
                                phi += dsign * 2 * math.pi * (max(0.0, si - s0) - max(0.0, prev - s0)) / pl
                            prev = si
                            r *= 1 + wob * n_r(si)
                            p = p + tang * (sway * n_s(si) * ramp)
                        else:
                            phi = ph + dsign * 2 * math.pi * u / pitch
                        pts.append(p + (hdir * math.cos(phi) + tang * math.sin(phi)) * r)
                    pts = resample(pts, yarn["step_m"])
                else:
                    amp, wl = float(wave["amplitude"]), float(wave["wavelength"])
                    pts = []
                    for p, si in zip(base, s):
                        u = max(0.0, si - s_leave)
                        pts.append(p + tang * amp * min(1.0, u / wl) * math.sin(ph + 2 * math.pi * u / wl))
            w, h = rng_range(R, st["width"]) / 2, rng_range(R, st["thick"]) / 2
            tf = float(st.get("tip_frac", 0.6))
            v_start = len(bucket.verts)
            if felt:
                section, seg = _felt().lock_section(st, RF)
                ph = R.uniform(0, 6.28)
                bucket.add(*rope_mesh(pts, taper(len(pts), w, w * float(st.get("end_scale", 0.85)), tf, swell=0.05),
                                      taper(len(pts), h, h * float(st.get("end_scale", 0.85)), tf, swell=0.05),
                                      dict(yarn, seg=seg), up_hint=hdir, phase=ph, section=section))
            else:
                bucket.add(*rope_mesh(pts, taper(len(pts), w, w * float(st.get("end_scale", 0.85)), tf, swell=0.05),
                                      taper(len(pts), h, h * float(st.get("end_scale", 0.85)), tf, swell=0.05), yarn,
                                      up_hint=hdir, phase=R.uniform(0, 6.28)))
            if ctx.get("dynamics") is not None:  # centre line of the hanging part (no random draws: same geometry)
                hang = [p.copy() for p, si in zip(base, s) if si >= s_leave]
                ctx["dynamics"].append({"kind": "lock", "structure": st.get("name", st["type"]), "index": made,
                                        "line": hang, "verts": (v_start, len(bucket.verts))})
            made += 1
    return bucket, dict({"locks": made, "style": style}, **({"finish": "felt"} if felt else {}))


def bun_frames(st, ctx):
    """Base point, axis and radius of every bun (used by sweep targets and accessories)."""
    sc = ctx["scalp"]
    out = []
    for b in st["buns"]:
        d = Scalp.direction(float(b["az"]), float(b["el"]))
        base, n = sc.at_dir(d, float(b.get("lift", 0.0)))
        tilt = float(b.get("tilt", 0.5))  # 0 = along the scalp normal, 1 = straight up
        axis = (n * (1 - tilt) + Vector((0, 0, 1)) * tilt).normalized()
        out.append({"base": base, "axis": axis, "radius": float(b["radius"]), "height": float(b["height"]), "base_dir": d,
                    "cfg": b})
    return out


def build_bun(st, ctx, R):
    if finish(st, ctx) == "felt":
        return _felt().felt_bun(st, ctx, R)
    yarn = ctx["yarn"]
    bucket = MeshBucket()
    G = HAIR_G()
    ropes_total = 0
    for bf in ctx["buns"]:
        b = bf["cfg"]
        base, ax, Rb, Hb = bf["base"], bf["axis"], bf["radius"], bf["height"]
        u = ax.orthogonal().normalized()
        v = ax.cross(u)
        nro = int(b.get("ropes", 5))
        turns = float(b.get("turns", 1.2))
        dsign = 1 if b.get("wrap", "ccw") == "ccw" else -1
        thick = float(b.get("rope_thick", Rb * 0.42)) / 2
        v_start = len(bucket.verts)
        for k in range(nro):
            ph = 2 * math.pi * k / nro + R.uniform(-0.3, 0.3)
            ctrl = []
            m = 28
            h0, h1 = R.uniform(0.02, 0.12), R.uniform(0.80, 0.95)
            for i in range(m):
                t = i / (m - 1)
                hf = h0 + (h1 - h0) * t
                rho = Rb * math.sqrt(max(0.0, 1 - 0.82 * (2 * hf - 1) ** 2)) * (1 + R.uniform(-0.04, 0.04))
                th = ph + dsign * 2 * math.pi * turns * t
                ctrl.append(base + ax * (Hb * hf) + (u * math.cos(th) + v * math.sin(th)) * (rho - thick * 0.6))
            ctrl[-1] = base + ax * (Hb * h1 * 0.98) + (ctrl[-1] - base - ax * (Hb * h1)) * 0.3  # tuck the end in
            pts = resample(catmull_rom(ctrl, yarn["step_m"]), yarn["step_m"])
            bucket.add(*rope_mesh(pts, taper(len(pts), thick * 1.05, thick, 0.6),
                                  taper(len(pts), thick * 0.9, thick * 0.85, 0.6), yarn, up_hint=ax, phase=R.uniform(0, 6.28)))
            ropes_total += 1
        core = G.uv_sphere("_bun_core", base + ax * (Hb * 0.5), 1.0, ctx["C"], 24, 12, (1, 1, 1))
        # orient the core along the axis
        for vtx in core.data.vertices:
            p = Vector(vtx.co) - (base + ax * (Hb * 0.5))
            q = u * (p.x * Rb * 0.78) + v * (p.y * Rb * 0.78) + ax * (p.z * Hb * 0.44)
            vtx.co = base + ax * (Hb * 0.5) + q
        bucket.add([tuple(vtx.co) for vtx in core.data.vertices], [tuple(f.vertices) for f in core.data.polygons])
        _hair().bpy_data_remove(core)
        if ctx.get("dynamics") is not None:
            ctx["dynamics"].append({"kind": "bun", "structure": st.get("name", st["type"]),
                                    "bun": next(i for i, x in enumerate(ctx["buns"]) if x is bf),
                                    "verts": (v_start, len(bucket.verts))})
    return bucket, {"buns": len(ctx["buns"]), "ropes": ropes_total}


def _bun_point(ctx, st, around_deg, height_frac, out=0.0):
    bf = ctx["buns"][int(st.get("bun", 0))]
    ax = bf["axis"]
    front = Vector((0, -1, 0))
    u = (front - ax * front.dot(ax))
    u = u.normalized() if u.length > 1e-6 else ax.orthogonal().normalized()
    v = ax.cross(u)
    a = math.radians(around_deg)
    hf = height_frac
    rho = bf["radius"] * math.sqrt(max(0.0, 1 - 0.82 * (2 * hf - 1) ** 2))
    radial = u * math.cos(a) + v * math.sin(a)  # 0 = front, +90 = the character's left (+X) when the axis is up
    return bf["base"] + ax * (bf["height"] * hf) + radial * (rho + out), radial, ax


def build_tie(st, ctx, R):
    yarn = dict(ctx["yarn"], plies=int(st.get("plies", 1)), depth=0.0)
    bf = ctx["buns"][int(st.get("bun", 0))]
    ax = bf["axis"]
    u = ax.orthogonal().normalized()
    v = ax.cross(u)
    hf = float(st.get("height_frac", 0.12))
    rho = bf["radius"] * math.sqrt(max(0.0, 1 - 0.82 * (2 * hf - 1) ** 2)) * float(st.get("radius_scale", 1.0))
    c = bf["base"] + ax * (bf["height"] * hf)
    n = 48
    pts = [c + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * rho for i in range(n)]
    r = float(st.get("tube", 0.008))
    bucket = MeshBucket()
    bucket.add(*rope_mesh(pts, [r * float(st.get("width_scale", 1.4))] * n, [r] * n, yarn, up_hint=ax, closed=True))
    return bucket, {"radius_m": round(rho, 4)}


def build_bow(st, ctx, R):
    yarn = dict(ctx["yarn"], plies=1, depth=0.0)
    if "bun" in st:
        c, radial, ax = _bun_point(ctx, st, float(st.get("around_deg", 0)), float(st.get("height_frac", 0.15)),
                                   float(st.get("out", 0.004)))
    else:
        c, radial = ctx["scalp"].at(float(st["az"]), float(st["el"]), float(st.get("out", 0.006)))
        ax = Vector((0, 0, 1))
    side = ax.cross(radial).normalized()
    up = radial.cross(side).normalized()
    size = float(st.get("size", 0.04))
    t = float(st.get("ribbon_thick", 0.003))
    w = float(st.get("ribbon_width", size * 0.28))
    bucket = MeshBucket()
    for sgn in (1, -1):  # two loops
        ctrl = [c]
        for i in range(1, 12):
            a = math.pi * i / 12
            ctrl.append(c + side * sgn * size * 0.5 * (1 - math.cos(a)) * 1.0 + up * size * 0.28 * math.sin(a) * math.sin(a / 2)
                        + up * size * 0.22 * math.sin(2 * a) * 0.5)
        ctrl.append(c)
        pts = resample(catmull_rom(ctrl, 0.003), 0.003)
        bucket.add(*rope_mesh(pts, [w / 2] * len(pts), [t] * len(pts), yarn, up_hint=radial))
        tail = [c, c + side * sgn * size * 0.15 - up * size * 0.35, c + side * sgn * size * 0.30 - up * size * 0.62]
        pts = resample(catmull_rom(tail, 0.003), 0.003)
        bucket.add(*rope_mesh(pts, [w / 2] * len(pts), [t] * len(pts), yarn, up_hint=radial))
    knot = resample(catmull_rom([c - up * size * 0.08, c + up * size * 0.08], 0.003), 0.003)
    bucket.add(*rope_mesh(knot, [w * 0.45] * len(knot), [w * 0.35] * len(knot), yarn, up_hint=radial))
    return bucket, {"size_m": size}


def build_flowers(st, ctx, R):
    G = HAIR_G()
    petals = int(st.get("petals", 5))
    pet, cen = MeshBucket(), MeshBucket()
    for it in st["items"]:
        c, radial, ax = _bun_point(ctx, st, float(it["around_deg"]), float(it.get("height_frac", 0.2)),
                                   float(it.get("out", 0.0)))
        s = float(it.get("size", 0.02))
        side = ax.cross(radial).normalized()
        up = radial.cross(side).normalized()
        rot = R.uniform(0, 6.28)
        for k in range(petals):
            a = rot + 2 * math.pi * k / petals
            d = side * math.cos(a) + up * math.sin(a)
            o = G.uv_sphere("_petal", (0, 0, 0), 1.0, ctx["C"], 12, 8, (1, 1, 1))
            pc = c + d * s * 0.55 + radial * s * 0.05
            vs = []
            for vtx in o.data.vertices:
                p = Vector(vtx.co)
                vs.append(tuple(pc + d * (p.x * s * 0.5) + d.cross(radial).normalized() * (p.y * s * 0.42) + radial * (p.z * s * 0.22)))
            pet.add(vs, [tuple(f.vertices) for f in o.data.polygons])
            _hair().bpy_data_remove(o)
        o = G.uv_sphere("_centre", (0, 0, 0), 1.0, ctx["C"], 12, 8, (1, 1, 1))
        cc = c + radial * s * 0.18
        cen.add([tuple(cc + side * (v.co.x * s * 0.24) + up * (v.co.y * s * 0.24) + radial * (v.co.z * s * 0.16))
                 for v in o.data.vertices], [tuple(f.vertices) for f in o.data.polygons])
        _hair().bpy_data_remove(o)
    return {"petals": pet, "centres": cen}, {"flowers": len(st["items"])}


def build_felt_volume(st, ctx, R):
    return _felt().build_volume(st, ctx, R)


BUILDERS = {"sweep": build_sweep, "fringe": build_fringe, "locks": build_locks, "bun": build_bun, "tie": build_tie,
            "bow": build_bow, "flowers": build_flowers, "felt_volume": build_felt_volume}
ACCESSORY_TYPES = {"tie", "bow", "flowers"}
TYPES = {"scalp_cap"} | set(BUILDERS)


def validate(hair_spec):
    """Errors in a groom/1 hair spec (structure types, required keys, bun references)."""
    errs = []
    sts = hair_spec.get("structures")
    if not isinstance(sts, list) or not sts:
        return ["hair.structures must be a non-empty list"]
    nb = sum(len(s.get("buns", [])) for s in sts if s.get("type") == "bun")
    need = {"sweep": ("count", "az", "el_root", "width", "thick", "target"), "fringe": ("root_az", "root_el", "tip_x", "tip_z", "width", "thick"),
            "locks": ("count", "az", "el_root", "hang_radii", "z_end", "width", "thick"), "bun": ("buns",), "flowers": ("items",)}
    for i, s in enumerate(sts):
        t = s.get("type")
        if t not in TYPES:
            errs.append(f"hair.structures[{i}].type unknown: {t}")
            continue
        for k in need.get(t, ()):
            if k not in s:
                errs.append(f"hair.structures[{i}] ({t}) needs '{k}'")
        if t == "locks" and s.get("style") == "curly" and not (s.get("curl") or {}).get("radius"):
            errs.append(f"hair.structures[{i}] curly locks need curl.radius and curl.pitch")
        if t == "fringe" and len(s.get("tip_x", [])) != len(s.get("tip_z", [])):
            errs.append(f"hair.structures[{i}] fringe tip_x and tip_z differ in length")
        if t == "felt_volume":
            errs += _felt().validate(s, i, nb)
            continue
        if "finish" in s and (s["finish"] not in FINISHES or t not in FINISH_TYPES):
            errs.append(f"hair.structures[{i}] ({t}) finish must be one of {', '.join(FINISHES)} on "
                        f"{', '.join(sorted(FINISH_TYPES))}")
        ref = s.get("bun", (s.get("target") or {}).get("bun"))
        if t in ("tie", "flowers", "sweep", "bow") and ref is not None and int(ref) >= nb:
            errs.append(f"hair.structures[{i}] refers to bun {ref}, but only {nb} bun(s) exist")
    if hair_spec.get("finish", "yarn") not in FINISHES:
        errs.append(f"hair.finish must be one of {', '.join(FINISHES)}")
    fb = hair_spec.get("fibres")
    if fb is not None and (not isinstance(fb, dict) or not isinstance(fb.get("layers", []), list)):
        errs.append("hair.fibres must be an object with an optional 'layers' list")
    errs += validate_dynamics(hair_spec)
    return errs


# ------------------------------------------------------------------------------------------- dynamics (chain bones)
DYN_PARAMS = ("stiffness", "stiffness_tip", "damping", "gravity", "drag", "limit_deg", "radius")
DYN_STRUCTURE_KEYS = {"bones", "bone_length", "every", "blend"} | set(DYN_PARAMS)
DYN_BONE_PREFIX = "DYN-"


def dynamics_spec(hair_spec):
    """The enabled dynamics block of a hair spec, or None (absent or "enabled": false)."""
    d = hair_spec.get("dynamics")
    if not d or not d.get("enabled", True):
        return None
    return d


def validate_dynamics(hair_spec):
    d = hair_spec.get("dynamics")
    if d is None:
        return []
    if not isinstance(d, dict):
        return ["hair.dynamics must be an object"]
    errs = []
    names = {s.get("name", s.get("type")): s.get("type") for s in hair_spec.get("structures", [])}
    for k in d.get("defaults", {}):
        if k not in DYN_PARAMS:
            errs.append(f"hair.dynamics.defaults: unknown key {k}")
    for name, cfg in (d.get("structures") or {}).items():
        if names.get(name) not in ("locks", "bun"):
            errs.append(f"hair.dynamics.structures.{name}: no locks or bun structure of that name")
            continue
        for k in cfg:
            if k not in DYN_STRUCTURE_KEYS:
                errs.append(f"hair.dynamics.structures.{name}: unknown key {k}")
        b = cfg.get("bones", 3)
        lo_hi = b if isinstance(b, list) else [b, b]
        if len(lo_hi) != 2 or not all(isinstance(x, int) and 1 <= x <= 12 for x in lo_hi) or lo_hi[0] > lo_hi[1]:
            errs.append(f"hair.dynamics.structures.{name}.bones must be an integer or [lo, hi] in 1..12")
        if isinstance(b, list) and not cfg.get("bone_length"):
            errs.append(f"hair.dynamics.structures.{name}: bones [lo, hi] needs bone_length")
    for c in d.get("colliders", []):
        if c.get("type") not in ("sphere", "capsule") or c.get("bone") not in ("head", "chest") or not c.get("name") \
                or not float(c.get("radius", 0)) > 0:
            errs.append(f"hair.dynamics.colliders: {c.get('name')} needs name, type sphere|capsule, bone head|chest, radius > 0")
        elif c["type"] == "capsule" and not ("a" in c and "b" in c):
            errs.append(f"hair.dynamics.colliders: capsule {c['name']} needs a and b")
    return errs


def _chain_params(dyn, cfg):
    p = {k: float(v) for k, v in (dyn.get("defaults") or {}).items() if k in DYN_PARAMS}
    p.update({k: float(v) for k, v in cfg.items() if k in DYN_PARAMS})
    return p


def _polyline_points(line, n):
    """n + 1 points at equal arc length along a polyline (Vectors)."""
    s = [0.0]
    for a, b in zip(line, line[1:]):
        s.append(s[-1] + (b - a).length)
    L, out, j = s[-1], [], 0
    for i in range(n + 1):
        x = L * i / n
        while j < len(s) - 2 and s[j + 1] < x:
            j += 1
        t = 0.0 if s[j + 1] == s[j] else (x - s[j]) / (s[j + 1] - s[j])
        out.append(line[j].lerp(line[j + 1], t))
    return out, L


def _store_dynamics_records(objs, st, records, ctx, dyn):
    """Turns the builder's records into chains (joint positions, vertex ranges) stored on the structure's object(s)
    as JSON ("ps_dyn"); ties, bows and flowers on a bun with a chain follow that bun."""
    name = st.get("name", st["type"])
    cfg = (dyn.get("structures") or {}).get(name)
    chains, follow = [], []
    if cfg is not None:
        every = max(1, int(cfg.get("every", 1)))
        for r in records:
            b = cfg.get("bones", 3)
            if r["kind"] == "lock":
                if r["index"] % every or len(r["line"]) < 2:
                    continue
                L = sum((q - p).length for p, q in zip(r["line"], r["line"][1:]))
                n = b if isinstance(b, int) else max(b[0], min(b[1], round(L / float(cfg["bone_length"]))))
                pts, _ = _polyline_points(r["line"], n)
                chains.append({"name": f"{name}.{r['index']:02d}", "group": name, "kind": "lock",
                               "joints": [list(p) for p in pts], "verts": list(r["verts"]),
                               "blend": float(cfg.get("blend", 0.5)), "params": _chain_params(dyn, cfg)})
            else:
                bf = ctx["buns"][r["bun"]]
                n = b if isinstance(b, int) else b[0]
                pts = [bf["base"] + bf["axis"] * (bf["height"] * k / n) for k in range(n + 1)]
                cname = f"{name}.{r['bun']}"
                ctx.setdefault("bun_chain", {})[r["bun"]] = cname
                chains.append({"name": cname, "group": name, "kind": "bun", "joints": [list(p) for p in pts],
                               "verts": list(r["verts"]), "base": list(bf["base"]), "axis": list(bf["axis"]),
                               "height": bf["height"], "params": _chain_params(dyn, cfg)})
    elif st["type"] in ACCESSORY_TYPES and "bun" in st and int(st["bun"]) in ctx.get("bun_chain", {}):
        bf = ctx["buns"][int(st["bun"])]
        follow.append({"chain": ctx["bun_chain"][int(st["bun"])], "base": list(bf["base"]), "axis": list(bf["axis"]),
                       "height": bf["height"]})
    if not chains and not follow:
        return
    sc = ctx["scalp"]
    colliders = []
    for c in dyn.get("colliders", []):
        e = {"name": c["name"], "type": c["type"], "bone": c["bone"], "radius": float(c["radius"])}
        if c["type"] == "sphere":
            e["centre"] = list(sc.centre + Vector(c.get("head_offset", (0, 0, 0))))
        else:
            e["a"], e["b"] = list(c["a"]), list(c["b"])
        colliders.append(e)
    data = {"chains": chains, "follow": follow, "colliders": colliders,
            "settings": {k: dyn[k] for k in ("substep_hz", "preroll_s") if k in dyn}}
    for ob in objs:  # chains are per object (vertex ranges): a structure with dynamics makes one object
        ob["ps_dyn"] = json.dumps(data)


def build(C, head, frame, hair_spec, material, face_y, fibres=None):
    """Builds every structure. frame: {"centre", "radii"} of the head; material(slot) -> bpy material;
    face_y(head, x, z) -> y of the face surface. Returns (objects, report).
    fibres(obj, slot, overrides) -> fibre object (the shared GN surface-fibre group with the slot's material preset):
    with spec.hair.fibres {"slots": [...] (default ["hair"]), "layers": [{"overrides": {...}}, ...]} every object
    of those slots gets one fibre object per layer (e.g. a dense short felt layer and a sparse long flyaway layer).
    Fibre objects are not returned with the meshes (they are not skinned; they follow the surface they grow on)."""
    errs = validate(hair_spec)
    if errs:
        raise SystemExit("groom/1: " + "; ".join(errs))
    seed = int(hair_spec.get("seed", 11))
    yarn = dict(YARN_DEFAULT, **(hair_spec.get("yarn") or {}))
    scalp = Scalp(head, frame["centre"], frame["radii"], float(hair_spec.get("scalp_offset_m", 0.008)))
    ctx = {"C": C, "head": head, "scalp": scalp, "yarn": yarn, "face_y": face_y, "buns": [],
           "finish": hair_spec.get("finish", "yarn"), "seed": seed}
    dyn = dynamics_spec(hair_spec)
    if dyn:
        ctx["dynamics"] = []
    sts = hair_spec["structures"]
    for s in sts:  # bun frames first: sweeps and accessories refer to them
        if s["type"] == "bun":
            ctx["buns"] += bun_frames(s, ctx)
    objs, rep = [], {"generator": GENERATOR, "structures": {}}
    slot_of = {}
    for i, s in enumerate(sts):
        t = s["type"]
        name = s.get("name", t)
        R = random.Random(seed * 7919 + i)
        if t == "scalp_cap":
            ob = _hair().scalp_cap(C, head, s)
            ob.name = ob.data.name = f"hair_{name}"
            HAIR_G().assign(ob, material(s.get("material", "hair")))
            slot_of[ob.name] = s.get("material", "hair")
            objs.append(ob)
            rep["structures"][name] = {"type": t, "faces": len(ob.data.polygons)}
            continue
        n_rec = len(ctx["dynamics"]) if dyn else 0
        result, info = BUILDERS[t](s, ctx, R)
        made = []
        if isinstance(result, dict):  # several parts with their own material slots
            slots = {"petals": s.get("material", "hair_flower"), "centres": s.get("centre_material", "hair_flower_centre")}
            for part, bucket in result.items():
                ob = bucket.obj(f"hair_{name}_{part}", C)
                HAIR_G().assign(ob, material(slots[part]))
                slot_of[ob.name] = slots[part]
                made.append(ob)
        else:
            default = "hair" if t not in ACCESSORY_TYPES else "hair_" + t
            ob = result.obj(f"hair_{name}", C)
            HAIR_G().assign(ob, material(s.get("material", default)))
            slot_of[ob.name] = s.get("material", default)
            made.append(ob)
        objs += made
        if dyn:
            _store_dynamics_records(made, s, ctx["dynamics"][n_rec:], ctx, dyn)
        info.update(type=t)
        rep["structures"][name] = info
    rep["objects"] = [o.name for o in objs]
    rep["vertices"] = sum(len(o.data.vertices) for o in objs)
    fb = hair_spec.get("fibres")
    if fb and fb.get("enabled", True) and fibres is not None:
        slots = set(fb.get("slots", ["hair"]))
        made = []
        for ob in objs:
            if slot_of.get(ob.name) in slots:
                for layer in fb.get("layers", [{}]):
                    fo = fibres(ob, slot_of[ob.name], layer.get("overrides") or {})
                    if fo is not None:
                        fo.parent = ob  # rides with the surface (its geometry is the surface's own, deformed)
                        fo.matrix_parent_inverse = ob.matrix_world.inverted()
                        fo["ps_groom_fibres"] = layer.get("name", "fibres")
                        made.append(fo.name)
        rep["fibres"] = {"objects": len(made), "layers": [l.get("name", "fibres") for l in fb.get("layers", [{}])]}
    if dyn:
        rep["dynamics"] = {"chains": sum(len(json.loads(o.get("ps_dyn", "{}")).get("chains", [])) for o in objs)}
    return objs, rep


def bind(rig, objs, head_bone, chest_bone, binding):
    """Armature binding: head bone by default; with binding.blend_z [lo, hi] vertices below lo follow the chest bone
    and blend linearly to the head bone at hi (vertex groups + Armature modifier, as face_generic.bind_rigid)."""
    lo_hi = (binding or {}).get("blend_z")
    for ob in objs:
        ob.parent = rig
        ob.matrix_parent_inverse = rig.matrix_world.inverted()
        gh = ob.vertex_groups.new(name=head_bone)
        if lo_hi:
            lo, hi = float(lo_hi[0]), float(lo_hi[1])
            gc = ob.vertex_groups.new(name=chest_bone)
            for v in ob.data.vertices:
                z = (ob.matrix_world @ v.co).z
                w = min(1.0, max(0.0, (z - lo) / (hi - lo)))
                if w > 0:
                    gh.add([v.index], w, "REPLACE")
                if w < 1:
                    gc.add([v.index], 1.0 - w, "REPLACE")
        else:
            gh.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = rig
    _bind_dynamics(rig, objs, head_bone, chest_bone, lo_hi)


def _chain_weights(u, n):
    """Weights of the n chain bones at chain coordinate u (in bones from the root): linear between bone centres."""
    b = min(max(u - 0.5, 0.0), n - 1.0)
    lo = int(math.floor(b))
    f = b - lo
    w = {lo: 1.0 - f}
    if f > 0 and lo + 1 < n:
        w[lo + 1] = f
    return w


def _bind_dynamics(rig, objs, head_bone, chest_bone, blend_z=None):
    """Adds the chain bones (deform, parented to the head bone) and skins the chain vertices; stores the chain list on
    the rig ("ps_dynamics") for the engine exporter. No-op without dynamics records. With binding.blend_z a lock chain
    gets an anchor: each joint's kinematic target follows the chest bone with the static binding's chest weight at
    the joint's height, so hair that rests on the back keeps resting there."""
    import bpy
    recs = [(ob, json.loads(ob["ps_dyn"])) for ob in objs if "ps_dyn" in ob]
    if not recs:
        return
    inv = rig.matrix_world.inverted()
    bpy.ops.object.select_all(action="DESELECT")
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    bone_names = {}
    for ob, d in recs:
        for ch in d["chains"]:
            prev, names = eb[head_bone], []
            J = [Vector(p) for p in ch["joints"]]
            for k in range(len(J) - 1):
                b = eb.new(f"{DYN_BONE_PREFIX}{ch['name']}.{k}")
                b.head, b.tail = inv @ J[k], inv @ J[k + 1]
                b.parent = prev
                b.use_connect = k > 0
                b.use_deform = True
                prev = b
                names.append(b.name)
            bone_names[ch["name"]] = names
    bpy.ops.object.mode_set(mode="OBJECT")
    chains_out, colliders = [], {}
    resolve = {"head": head_bone, "chest": chest_bone}

    def blend_into(ob, v, target):
        """Sets vertex v's weights: target {group: w} plus the static weights scaled by 1 - sum(target)."""
        keep = 1.0 - sum(target.values())
        for g in list(v.groups):
            vg = ob.vertex_groups[g.group]
            if keep <= 1e-6:
                vg.remove([v.index])
            else:
                vg.add([v.index], g.weight * keep, "REPLACE")
        for gname, w in target.items():
            if w > 1e-6:
                vg = ob.vertex_groups.get(gname) or ob.vertex_groups.new(name=gname)
                vg.add([v.index], w, "REPLACE")

    def axial(ob, v, base, axis, height, names):
        p = ob.matrix_world @ v.co
        h = (p - Vector(base)).dot(Vector(axis)) / height  # 0 at the base, 1 at the top
        n = len(names)
        a = min(1.0, max(0.0, (h - 0.1) / 0.3))  # the lowest part stays on the head
        blend_into(ob, v, {names[i]: w * a for i, w in _chain_weights(h * n, n).items()})

    for ob, d in recs:
        mw = ob.matrix_world
        for ch in d["chains"]:
            names = bone_names[ch["name"]]
            v0, v1 = ch["verts"]
            if ch["kind"] == "bun":
                for v in ob.data.vertices[v0:v1]:
                    axial(ob, v, ch["base"], ch["axis"], ch["height"], names)
            else:
                J = [Vector(p) for p in ch["joints"]]
                n = len(J) - 1
                for v in ob.data.vertices[v0:v1]:
                    p = mw @ v.co
                    best, u = 1e9, 0.0
                    for k in range(n):  # closest point on the chain polyline -> chain coordinate u
                        a, b = J[k], J[k + 1]
                        ab = b - a
                        t = (p - a).dot(ab) / max(1e-12, ab.dot(ab))
                        tc = min(1.0, max(0.0, t)) if 0 < k < n - 1 else (min(1.0, t) if k == 0 else max(0.0, t))
                        if n == 1:
                            tc = t
                        dist = (p - (a + ab * min(1.0, max(0.0, tc)))).length
                        if dist < best:
                            best, u = dist, k + tc
                    if u <= 0:
                        continue  # on the scalp, before the chain: static binding
                    a = min(1.0, u / max(1e-6, ch["blend"]))
                    blend_into(ob, v, {names[i]: w * a for i, w in _chain_weights(u, n).items()})
            p = ch["params"]
            out = {"name": ch["name"], "group": ch["group"], "bones": names, "tip": ch["joints"][-1], **p}
            if blend_z and ch["kind"] == "lock" and chest_bone != head_bone:
                lo, hi = float(blend_z[0]), float(blend_z[1])
                w = [round(1.0 - min(1.0, max(0.0, ((mw @ Vector(j)).z - lo) / (hi - lo))), 4) for j in ch["joints"]]
                if any(w):
                    out["anchor"] = {"bone": chest_bone, "weights": [0.0] + w[1:]}
            chains_out.append(out)
        for f in d["follow"]:
            names = bone_names.get(f["chain"])
            if names:
                for v in ob.data.vertices:
                    axial(ob, v, f["base"], f["axis"], f["height"], names)
        for c in d["colliders"]:
            colliders[c["name"]] = dict(c, bone=resolve[c["bone"]])
        settings = d.get("settings", {})
    rig["ps_dynamics"] = json.dumps({"enabled": True, **settings, "chains": chains_out, "colliders": list(colliders.values()),
                                     "coordinates": "Blender world, metres; bones are source names"})
