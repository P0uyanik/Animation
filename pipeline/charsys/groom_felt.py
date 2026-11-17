"""Felted hair primitives for the shared groom system (groom/1, T-033). Character-independent: every shape, size,
groove and lump is spec data; placement uses groom.Scalp (the character's own head mesh).

Two primitives, used by groom.py:

felt_volume  sculpted, smooth felted masses with soft (rounded) edges, combing grooves and part lines.
             {"type": "felt_volume", "name": ..., "shape": "gather" | "fringe" | "mass", <shape keys>, <surface keys>}
  gather  hair lying on the scalp from a hairline towards a gather point (crown, bun base, nape): one closed shell.
          az [from, to] (360 wide = closed around the head), hairline_el (number, [lo, hi] or a table
          [[az, el], ...] interpolated over |az| unless "symmetric": false), target {"bun": i} | {"az", "el"},
          tuck (fraction of the way to the target, default 1), height [root, mid, end] (metres above the head
          surface: the shell's outer surface; mid at half way), inset (how far the inner surface sits under the skin),
          part {"az", "width_deg", "depth" (fraction of height), "length" (fraction of the way)}, resolution [nu, nv].
  fringe  a felted fringe sheet from a part line over the forehead (same placement keys as the yarn fringe):
          root_az [...], root_el, tip_x [...], tip_z [...], tip_gap, bulge, thick [root, tip], resolution [nu, nv],
          or tips on the head: tip_az [...], tip_el [...], tip_lift (a curtain falling around the temples);
          root_el may be a list as long as root_az (roots along a part line); tip_jitter (seeded per-strand
          shortening: an irregular, soft tip line),
          tip_scallop (fraction of the length the sheet is shorter between strand crests: rounded strand tips),
          clearance (the sheet is pushed out to lie at least this far plus half its thickness above the head).
          Strand grooves run from the roots to the tips; the tip edge is rounded and scalloped by the grooves.
  mass    an ellipsoidal mass (bun, temple volume, puff): at a bun frame ({"bun": i}, centred half way up the bun)
          or on the scalp (az, el, lift), radii [outward, sideways, along the axis], axis "bun" | "normal" | "up" |
          [x, y, z], swirl (turns of the grooves from the bottom pole to the top), resolution [nu, nv].
  surface keys (all shapes): grooves {count, depth (fraction), sharpness (0..1, narrower grooves when higher),
          wander (in groove widths), wavelength (fraction of the length)}, lumps {amount, scale},
          soft [u0, u1, v0, v1] (rounded-edge width as a fraction of each parameter range), rim (minimum edge height
          as a fraction), seed offset "seed".

felt_lock    the "felt" finish of a hanging lock (groom locks with "finish": "felt"): the same centre line (straight,
             wavy, curly ringlets) and the same dynamics chain, but a soft, slightly irregular cross-section without ply
             ridges: spec "felt": {seg, irregularity (relative), wavelength (m), flatten_twist (turns per metre of
             the slow elliptical twist), flatten (relative)}.

Finish selection: spec.hair.finish ("yarn" default | "felt") with a per-structure "finish" override. A felt sweep is
built as a gather volume, a felt fringe as a fringe sheet, a felt bun as a mass on each bun frame (plus optional
bundles: buns[i].felt_lobes [{offset [out, side, axis], radii, swirl}], relative to the bun frame), felt locks as
felt_lock. Felt meshes get the same per-object UV map name as ropes (U across, V along, metres)."""
import math
import random

try:
    from mathutils import Vector
except ImportError:
    Vector = None

FELT_DEFAULT = {"grooves": {"count": 18, "depth": 0.22, "sharpness": 0.6, "wander": 0.35, "wavelength": 0.5},
                "lumps": {"amount": 0.06, "scale": 1.0}, "rim": 0.1, "soft": [0.08, 0.08, 0.12, 0.12]}
LOCK_DEFAULT = {"seg": 14, "irregularity": 0.10, "wavelength": 0.06, "flatten": 0.08, "flatten_twist": 4.0}
SHAPES = ("gather", "fringe", "mass")


def _g():
    import groom
    return groom


def merged(st, key):
    """Spec surface settings with defaults (dicts merged one level)."""
    d = FELT_DEFAULT[key]
    v = st.get(key, d)
    return dict(d, **v) if isinstance(d, dict) and isinstance(v, dict) else v


def lerp_table(table, x, symmetric=True):
    """Piecewise-linear interpolation in a [[x, y], ...] table (|x| when symmetric)."""
    if symmetric:
        x = abs(x)
    t = sorted(table)
    if x <= t[0][0]:
        return float(t[0][1])
    for (x0, y0), (x1, y1) in zip(t, t[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return float(t[-1][1])


def smooth_list(vals, u):
    """Smooth (Catmull-Rom) interpolation through a list of values at u in [0, 1]."""
    n = len(vals)
    if n == 1:
        return float(vals[0])
    f = u * (n - 1)
    i = min(n - 2, int(math.floor(f)))
    t = f - i
    p0, p1, p2, p3 = vals[max(0, i - 1)], vals[i], vals[i + 1], vals[min(n - 1, i + 2)]
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


class Surface:
    """Groove and lump field over the (u, v) parameter square, seeded."""

    def __init__(self, st, R, u_span=1.0):
        gr, lu = merged(st, "grooves"), merged(st, "lumps")
        self.n = float(gr["count"]) * u_span
        self.depth = float(gr["depth"])
        self.sharp = min(0.95, max(0.0, float(gr["sharpness"])))
        self.wander = float(gr["wander"])
        self.wl = max(0.05, float(gr["wavelength"]))
        self.lump = float(lu["amount"])
        self.ls = float(lu["scale"])
        self.ph = [R.uniform(0, 2 * math.pi) for _ in range(8)]
        self.cyclic_n = max(1, round(self.n))

    def groove(self, u, v, cyclic=False):
        """In [-1, 0]: 0 on the broad strand crests, -1 in the narrow grooves between them."""
        if self.depth <= 0 or self.n <= 0:
            return 0.0
        n = self.cyclic_n if cyclic else self.n
        # wander: smooth in u and v, so grooves are slightly irregular, never parallel ruled lines
        w = self.wander * (0.6 * math.sin(2 * math.pi * v / self.wl + self.ph[0] + 2 * math.pi * 1.0 * u)
                           + 0.4 * math.sin(2 * math.pi * v / (self.wl * 0.43) + self.ph[1] + 2 * math.pi * 2.0 * u))
        x = abs(math.sin(math.pi * (n * u + w)))
        return x ** (1.0 - self.sharp) - 1.0

    def lumps(self, u, v):
        if self.lump <= 0:
            return 0.0
        s = self.ls
        a = math.sin(2 * math.pi * (1.7 * s * u + 0.6 * s * v) + self.ph[2]) * math.sin(2 * math.pi * 1.3 * s * v + self.ph[3])
        b = math.sin(2 * math.pi * (3.1 * s * u - 1.4 * s * v) + self.ph[4])
        return self.lump * (0.65 * a + 0.35 * b)


def _edge(x, soft):
    """Quarter-circle rounding over the first `soft` of a parameter range: 0 at the edge, 1 inside."""
    if soft <= 0:
        return 1.0
    y = min(1.0, max(0.0, x / soft))
    return math.sqrt(max(0.0, 1.0 - (1.0 - y) ** 2))


def shell_mesh(base, nrm, h_out, h_in, closed_u=False):
    """A closed felt shell from a base grid: base[i][j] (nu x nv Vectors), unit normals nrm[i][j], outer offsets
    h_out[i][j] and inner offsets h_in[i][j] (along -normal). Outer and inner grids joined by side walls on every
    open border. UVs: U across (metres along v=const), V along (metres along u=const)."""
    nu, nv = len(base), len(base[0])
    outer = [[base[i][j] + nrm[i][j] * h_out[i][j] for j in range(nv)] for i in range(nu)]
    inner = [[base[i][j] - nrm[i][j] * h_in[i][j] for j in range(nv)] for i in range(nu)]
    us = [[0.0] * nv for _ in range(nu)]
    for j in range(nv):
        for i in range(1, nu):
            us[i][j] = us[i - 1][j] + (outer[i][j] - outer[i - 1][j]).length
    vs = [[0.0] * nv for _ in range(nu)]
    for i in range(nu):
        for j in range(1, nv):
            vs[i][j] = vs[i][j - 1] + (outer[i][j] - outer[i][j - 1]).length
    verts = [tuple(p) for row in outer for p in row] + [tuple(p) for row in inner for p in row]
    off = nu * nv

    def o(i, j):
        return (i % nu) * nv + j

    def uv(i, j, wrap=False):
        return (us[i % nu][j] + (us[-1][j] + (outer[0][j] - outer[-1][j]).length if wrap else 0.0), vs[i % nu][j])
    faces, uvs = [], []
    ni = nu if closed_u else nu - 1
    for i in range(ni):
        wrap = closed_u and i == nu - 1
        for j in range(nv - 1):
            a, b, c, d = o(i, j), o(i + 1, j), o(i + 1, j + 1), o(i, j + 1)
            faces.append((a, b, c, d))
            uvs.append((uv(i, j), uv(i + 1, j, wrap), uv(i + 1, j + 1, wrap), uv(i, j + 1)))
            faces.append((d + off, c + off, b + off, a + off))
            uvs.append((uv(i, j + 1), uv(i + 1, j + 1, wrap), uv(i + 1, j, wrap), uv(i, j)))
    for j, sgn in ((0, 1), (nv - 1, -1)):  # walls along v = 0 and v = 1
        for i in range(ni):
            wrap = closed_u and i == nu - 1
            a, b = o(i, j), o(i + 1, j)
            f = (a, b, b + off, a + off) if sgn < 0 else (b, a, a + off, b + off)
            faces.append(f)
            uvs.append(((0.0, -0.002), (0.004, -0.002), (0.004, 0.0), (0.0, 0.0)))
    if not closed_u:
        for i, sgn in ((0, -1), (nu - 1, 1)):
            for j in range(nv - 1):
                a, b = o(i, j), o(i, j + 1)
                f = (a, b, b + off, a + off) if sgn < 0 else (b, a, a + off, b + off)
                faces.append(f)
                uvs.append(((0.0, -0.002), (0.004, -0.002), (0.004, 0.0), (0.0, 0.0)))
    return verts, faces, uvs


def grid_normals(base, hint, closed_u=False):
    """Unit normals of a grid surface from central differences, oriented along hint(i, j) (fallback where the grid
    is degenerate, e.g. where lines converge)."""
    nu, nv = len(base), len(base[0])
    out = []
    for i in range(nu):
        row = []
        for j in range(nv):
            if closed_u:
                du = base[(i + 1) % nu][j] - base[(i - 1) % nu][j]
            else:
                du = base[min(nu - 1, i + 1)][j] - base[max(0, i - 1)][j]
            dv = base[i][min(nv - 1, j + 1)] - base[i][max(0, j - 1)]
            n = du.cross(dv)
            h = hint(i, j)
            if n.length < 1e-9 or du.length < 1e-6:
                n = h.copy()
            n.normalize()
            if n.dot(h) < 0:
                n = -n
            row.append(n)
        out.append(row)
    return out


def _profile(u, v, soft, closed_u, rim):
    e = _edge(v, soft[2]) * _edge(1 - v, soft[3])
    if not closed_u:
        e *= _edge(u, soft[0]) * _edge(1 - u, soft[1])
    return rim + (1 - rim) * e


def _height3(h, t):
    """Quadratic through [root, mid, end] at t in [0, 1]."""
    if not isinstance(h, (list, tuple)):
        return float(h)
    if len(h) == 2:
        return h[0] + (h[1] - h[0]) * t
    a, m, b = h
    return a * (1 - t) * (1 - 2 * t) + 4 * m * t * (1 - t) + b * t * (2 * t - 1)


# ------------------------------------------------------------------------------------------------------------ shapes
def gather(st, ctx, R):
    G = _g()
    sc = ctx["scalp"]
    tgt = st.get("target", {"az": 0, "el": 90})
    tdir = ctx["buns"][int(tgt["bun"])]["base_dir"] if "bun" in tgt else G.Scalp.direction(float(tgt["az"]), float(tgt["el"]))
    a0, a1 = [float(x) for x in st.get("az", [-180, 180])]
    closed_u = (a1 - a0) >= 359.999
    nu, nv = st.get("resolution", [int(max(24, abs(a1 - a0) / 2)), 40])
    hl = st.get("hairline_el", 30)
    sym = st.get("symmetric", True)
    tuck = float(st.get("tuck", 1.0))
    height = st.get("height", [0.012, 0.022, 0.016])
    inset = float(st.get("inset", 0.004))
    soft = merged(st, "soft")
    rim = float(merged(st, "rim"))
    part = st.get("part")
    S = Surface(st, R, abs(a1 - a0) / 360.0 if closed_u else 1.0)
    base, nrm, hout, hin, hint_n = [], [], [], [], []
    for i in range(nu):
        u = i / nu if closed_u else i / (nu - 1)
        az = a0 + (a1 - a0) * u
        if isinstance(hl, (list, tuple)) and hl and isinstance(hl[0], (list, tuple)):
            el = lerp_table(hl, ((az + 180) % 360) - 180, sym)
        else:
            el = float(sum(hl) / len(hl)) if isinstance(hl, (list, tuple)) else float(hl)
        d0 = G.Scalp.direction(az, el)
        brow, nrow, ho, hi = [], [], [], []
        for j in range(nv):
            v = j / (nv - 1)
            d = G.slerp(d0, tdir, v * tuck)
            p, n = sc.at_dir(d, -sc.offset)  # the head surface itself
            h = _height3(height, v) * _profile(u, v, soft, closed_u, rim)
            g = S.groove(u, v, closed_u)
            if part:
                da = ((az - float(part["az"]) + 180) % 360) - 180
                if v <= float(part.get("length", 0.6)):
                    fade = 1.0 - max(0.0, (v - float(part.get("length", 0.6)) * 0.7) / (float(part.get("length", 0.6)) * 0.3))
                    h *= 1 - float(part.get("depth", 0.5)) * math.exp(-(da / float(part.get("width_deg", 3))) ** 2) * fade
            h *= 1 + S.depth * g + S.lumps(u, v)
            brow.append(p)
            nrow.append(n)
            ho.append(max(0.0005, h))
            hi.append(inset)
        base.append(brow)
        nrm.append(nrow)
        hout.append(ho)
        hin.append(hi)
    return shell_mesh(base, nrm, hout, hin, closed_u), {"shape": "gather", "grid": [nu, nv]}


def fringe(st, ctx, R):
    G = _g()
    sc, face_y, head = ctx["scalp"], ctx["face_y"], ctx["head"]
    nu, nv = st.get("resolution", [48, 32])
    th = st.get("thick", [0.02, 0.012])
    th = [float(x) for x in th] if isinstance(th, (list, tuple)) else [float(th)] * 2
    soft = merged(st, "soft")
    rim = float(merged(st, "rim"))
    el = st["root_el"]
    # a root_el list as long as root_az (T-033b) gives one elevation per root (roots along a part line);
    # otherwise [lo, hi] is averaged as before
    el_along = isinstance(el, (list, tuple)) and len(el) == len(st["root_az"]) and len(el) > 2
    el = el if el_along else sum(el) / 2 if isinstance(el, (list, tuple)) else float(el)
    S = Surface(st, R)
    scal = float(st.get("tip_scallop", 0.0))  # tips end in rounded strand lobes: the sheet is shorter between strands
    clear = float(st.get("clearance", 0.003))
    # T-033b, optional: tips on the scalp/side of the head (tip_az, tip_el [, tip_lift]) instead of on the face
    # (tip_x, tip_z): a curtain fringe that falls from the part around the temples; tip_jitter shortens each strand
    # by a seeded random fraction, so the tip line is irregular instead of a blunt band
    on_scalp = "tip_az" in st
    tjit = float(st.get("tip_jitter", 0.0))
    if tjit:
        RJ = random.Random("felt_fringe:" + st.get("name", "fringe") + ":" + str(ctx.get("seed", 0)))
        jit = [RJ.uniform(0.0, tjit) for _ in range(int(S.n) + 2)]
    base, hints = [], []
    for i in range(nu):
        u = i / (nu - 1)
        az = smooth_list(st["root_az"], u)
        root, nr = sc.at(az, smooth_list(el, u) if el_along else el, 0.004)
        if on_scalp:
            tl = st.get("tip_lift", 0.006)
            tl = smooth_list(tl, u) if isinstance(tl, (list, tuple)) else float(tl)
            tip, _ = sc.at(smooth_list(st["tip_az"], u), smooth_list(st["tip_el"], u), tl)
        else:
            xt, zt = smooth_list(st["tip_x"], u), smooth_list(st["tip_z"], u)
            tip = Vector((xt, face_y(head, xt, zt) - float(st.get("tip_gap", 0.012)), zt))
        mid = (root + tip) / 2 + nr * float(st.get("bulge", 0.02))
        dense = G.HAIR_G().bezier(root, mid, tip, nv * 4)
        crest = abs(math.sin(math.pi * S.n * u)) ** 0.6 if S.n > 0 else 1.0
        vmax = 1.0 - scal * (1.0 - crest)
        if tjit:
            vmax *= 1.0 - jit[min(len(jit) - 1, int(S.n * u))]
        line = G.resample(dense, 0.001)
        L = len(line) - 1
        row = []
        for j in range(nv):
            p = line[min(L, int(round(L * vmax * j / (nv - 1))))].copy()
            # conform: the sheet never passes inside the head (it lies on the scalp/forehead, clearance + half thick)
            d = p - sc.centre
            s_, n_ = sc.at_dir(d, -sc.offset)
            need = (s_ - sc.centre).length + clear + 0.5 * (th[0] + (th[1] - th[0]) * j / (nv - 1))
            if d.length < need and d.dot(n_) > 0:
                p = sc.centre + d.normalized() * need
            row.append(p)
        base.append(row)
        hints.append(nr)
    c = sc.centre
    nrm = grid_normals(base, lambda i, j: (base[i][j] - c).normalized())
    hout, hin = [], []
    for i in range(nu):
        u = i / (nu - 1)
        ho, hi = [], []
        for j in range(nv):
            v = j / (nv - 1)
            t = (th[0] + (th[1] - th[0]) * v) * 0.5 * _profile(u, v, soft, False, rim)
            ho.append(max(0.0005, t * (1 + S.depth * S.groove(u, v) + S.lumps(u, v))))
            hi.append(max(0.0005, t))
        hout.append(ho)
        hin.append(hi)
    return shell_mesh(base, nrm, hout, hin, False), {"shape": "fringe", "grid": [nu, nv]}


def mass_frame(st, ctx):
    """Centre, axis and the two perpendicular directions (outward, sideways) of a mass."""
    G = _g()
    if "bun" in st:
        bf = ctx["buns"][int(st["bun"])]
        ax = bf["axis"]
        c = bf["base"] + ax * (bf["height"] * float(st.get("centre_frac", 0.5)))
        out = Vector((0, -1, 0))
    else:
        c, n = ctx["scalp"].at(float(st["az"]), float(st["el"]), float(st.get("lift", 0.0)))
        a = st.get("axis", "up")
        ax = n if a == "normal" else Vector((0, 0, 1)) if a == "up" else Vector(a).normalized()
        out = n
    out = out - ax * out.dot(ax)
    out = out.normalized() if out.length > 1e-6 else ax.orthogonal().normalized()
    side = ax.cross(out).normalized()
    return c, ax, out, side


def mass(st, ctx, R, frame=None, radii=None):
    c, ax, out, side = frame or mass_frame(st, ctx)
    r1, r2, r3 = radii or st["radii"]
    nu, nv = st.get("resolution", [64, 36])
    swirl = float(st.get("swirl", 0.0))
    S = Surface(st, R)
    verts, faces, uvs = [], [], []
    rows = []
    for j in range(1, nv):
        v = j / nv
        th = math.pi * v  # from the bottom pole (along -axis) to the top pole
        row = []
        for i in range(nu):
            u = i / nu
            ph = 2 * math.pi * u
            dirv = out * (math.sin(th) * math.cos(ph) * r1) + side * (math.sin(th) * math.sin(ph) * r2) - ax * (math.cos(th) * r3)
            pole = math.sin(th) ** 0.5  # grooves and lumps fade towards the poles
            g = S.groove((u + swirl * v) % 1.0, v, True)
            m = 1 + pole * (S.depth * 0.25 * g + S.lumps(u, v))
            row.append(len(verts))
            verts.append(tuple(c + dirv * m))
        rows.append(row)
    bot, top = len(verts), len(verts) + 1
    verts.append(tuple(c - ax * r3 * 0.98))
    verts.append(tuple(c + ax * r3 * 0.98))
    circ = 2 * math.pi * max(r1, r2)
    for j in range(len(rows) - 1):
        for i in range(nu):
            i2 = (i + 1) % nu
            faces.append((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            u0, u1 = circ * i / nu, circ * (i + 1) / nu
            v0, v1 = math.pi * r3 * (j + 1) / nv, math.pi * r3 * (j + 2) / nv
            uvs.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
    for i in range(nu):
        i2 = (i + 1) % nu
        faces.append((bot, rows[0][i2], rows[0][i]))
        uvs.append(((circ * (i + 0.5) / nu, 0.0), (circ * (i + 1) / nu, math.pi * r3 / nv), (circ * i / nu, math.pi * r3 / nv)))
        faces.append((top, rows[-1][i], rows[-1][i2]))
        vt = math.pi * r3
        uvs.append(((circ * (i + 0.5) / nu, vt), (circ * i / nu, vt - math.pi * r3 / nv), (circ * (i + 1) / nu, vt - math.pi * r3 / nv)))
    return (verts, faces, uvs), {"shape": "mass", "grid": [nu, nv]}


BUILD = {"gather": gather, "fringe": fringe, "mass": mass}


def build_volume(st, ctx, R):
    G = _g()
    bucket = G.MeshBucket()
    bucket.recalc = True
    (v, f, uv), info = BUILD[st["shape"]](st, ctx, R)
    bucket.add(v, f, uv)
    return bucket, info


def felt_bun(st, ctx, R):
    """The felt finish of a bun structure: one mass per bun frame (swirled grooves), dynamics records as ropes."""
    G = _g()
    bucket = G.MeshBucket()
    bucket.recalc = True
    felt = st.get("felt", {})
    for k, bf in enumerate(ctx["buns"]):
        b = bf["cfg"]
        ax = bf["axis"]
        c = bf["base"] + ax * (bf["height"] * 0.5)
        out = Vector((0, -1, 0)) - ax * Vector((0, -1, 0)).dot(ax)
        out = out.normalized() if out.length > 1e-6 else ax.orthogonal().normalized()
        side = ax.cross(out).normalized()
        sq = b.get("felt_radii", [1.0, 1.0, 1.0])  # relative to radius, radius, height / 2
        spec = dict(felt)
        spec.setdefault("swirl", float(b.get("turns", 1.0)) * (1 if b.get("wrap", "ccw") == "ccw" else -1))
        v_start = len(bucket.verts)
        (v, f, uv), _ = mass(spec, ctx, random.Random(R.random()), (c, ax, out, side),
                             (bf["radius"] * sq[0], bf["radius"] * sq[1], bf["height"] * 0.5 * sq[2]))
        bucket.add(v, f, uv)
        # T-033b, optional: felt_lobes [{offset [out, side, axis], radii [r1, r2, r3]}] (relative to the bun radius,
        # radius, half height): extra felted bundles of the same bun, inside its dynamics record (they move with it)
        for lb in b.get("felt_lobes", []):
            o = lb.get("offset", [0.0, 0.0, 0.0])
            lc = c + (out * o[0] + side * o[1]) * bf["radius"] + ax * (o[2] * bf["height"] * 0.5)
            lr = lb.get("radii", [0.6, 0.6, 0.6])
            lspec = dict(spec, swirl=float(lb.get("swirl", spec["swirl"])))
            (v, f, uv), _ = mass(lspec, ctx, random.Random(R.random()), (lc, ax, out, side),
                                 (bf["radius"] * lr[0], bf["radius"] * lr[1], bf["height"] * 0.5 * lr[2]))
            bucket.add(v, f, uv)
        if ctx.get("dynamics") is not None:
            ctx["dynamics"].append({"kind": "bun", "structure": st.get("name", st["type"]), "bun": k,
                                    "verts": (v_start, len(bucket.verts))})
    return bucket, {"buns": len(ctx["buns"]), "finish": "felt"}


def sweep_as_gather(st):
    """A felt sweep is a gather volume over the same region towards the same target."""
    l0, l1 = st.get("lift", [0.004, 0.010])
    t = sum(st["thick"]) / 2 if isinstance(st["thick"], (list, tuple)) else float(st["thick"])
    g = {"shape": "gather", "az": st["az"], "hairline_el": st["el_root"], "target": st["target"],
         "tuck": st.get("tuck", 1.0), "height": [l0 + t, l1 + t, l0 + t]}
    g.update(st.get("felt", {}))
    return g


def fringe_as_sheet(st):
    t = sum(st["thick"]) / 2 if isinstance(st["thick"], (list, tuple)) else float(st["thick"])
    g = {k: st[k] for k in ("root_az", "root_el", "tip_x", "tip_z", "tip_gap", "bulge") if k in st}
    g.update(shape="fringe", thick=[t * 2, t * 1.2])
    g.update(st.get("felt", {}))
    return g


def lock_section(st, R):
    """Soft, slightly irregular felt-lock cross-section: smooth along-length variation of two low harmonics around
    the section plus a slow elliptical twist; no ply ridges."""
    f = dict(LOCK_DEFAULT, **(st.get("felt") or {}))
    irr, wl = float(f["irregularity"]), max(0.005, float(f["wavelength"]))
    fl, tw = float(f["flatten"]), float(f["flatten_twist"])
    ph = [R.uniform(0, 2 * math.pi) for _ in range(6)]
    l1, l2 = wl * R.uniform(0.8, 1.25), wl * R.uniform(0.4, 0.6)

    def section(th, s):
        a1 = math.sin(2 * math.pi * s / l1 + ph[0])
        a2 = math.sin(2 * math.pi * s / l2 + ph[1])
        m = 1.0 + irr * (0.6 * a1 * math.cos(th - ph[2] - s / l1) + 0.4 * a2 * math.cos(3 * th - ph[3] + s / l2))
        return m * (1.0 + fl * math.cos(2 * (th - ph[4] - 2 * math.pi * tw * s)))
    return section, int(f["seg"])


def validate(st, i, nb):
    errs = []
    sh = st.get("shape")
    if sh not in SHAPES:
        return [f"hair.structures[{i}] felt_volume shape must be one of {', '.join(SHAPES)}"]
    tips = ("tip_az", "tip_el") if "tip_az" in st else ("tip_x", "tip_z")
    need = {"gather": ("hairline_el", "height"), "fringe": ("root_az", "root_el") + tips + ("thick",),
            "mass": ("radii",)}[sh]
    for k in need:
        if k not in st:
            errs.append(f"hair.structures[{i}] (felt_volume {sh}) needs '{k}'")
    if sh == "fringe" and len(st.get(tips[0], [])) != len(st.get(tips[1], [])):
        errs.append(f"hair.structures[{i}] felt fringe tip_x and tip_z differ in length")
    if sh == "mass" and "bun" not in st and not all(k in st for k in ("az", "el")):
        errs.append(f"hair.structures[{i}] felt mass needs 'bun' or 'az' and 'el'")
    ref = st.get("bun", (st.get("target") or {}).get("bun"))
    if ref is not None and int(ref) >= nb:
        errs.append(f"hair.structures[{i}] refers to bun {ref}, but only {nb} bun(s) exist")
    return errs
