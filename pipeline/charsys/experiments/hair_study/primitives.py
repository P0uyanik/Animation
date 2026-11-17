"""T-049 hair study: experiment-only hair primitives, registered into the shared groom/1 builder AT RUNTIME
(no shared file is edited; see register()). Character-independent: every shape, count and size is spec data.

study_clumps  felted, leaf-shaped hair clumps (tapered, flattened, pointed, soft irregular section with shallow fibre
              grooves) that follow the scalp from a root direction and lift off towards the tip. The building block for
              spiky/short styles (approach A: many narrow clumps; C: a few broad clumps over a base volume; B: clumps
              fused into the base volume).
              {"type": "study_clumps", "name", "seed", "keepout": {"az": deg, "el_min": deg},
               "rows": [{"count", "az": [a0, a1], "el": [lo, hi], "flow": "away" | "down" | "toward" | "stand",
                         "pole": {"az", "el"} (whorl for away/toward), "len_deg": [lo, hi], "lift": [root, tip],
                         "lift_power", "width": [lo, hi], "thick": [lo, hi], "jitter_deg", "converge" (fringe:
                         tips pulled towards az 0 by this fraction), "curl_deg" (sideways bend of the tip),
                         "taper_power" (width profile 1 - s^p: 2.4 leaf, ~1.1 cone)}],
               "seg", "step_m", "grooves": n, "groove_depth", "irregularity"}
study_curtain sculpted long-hair curtain: one thick felted shell hanging from the scalp over the back/shoulders, with
              ringlet columns and helical lobes carved into it (sculpted curls, approach B/C), rounded scalloped tips.
              {"type": "study_curtain", "name", "az": [a0, a1], "root_el": [[az, el], ...], "leave_el",
               "z_end": [[az, z], ...] (absolute, metres; interpolated over |az|), "rest_radii": [rx, ry], "rest_z",
               "columns", "thick", "column_depth", "lobe": {"pitch", "depth", "twist"}, "scallop", "resolution":
               [nu, nv], "inset"}
fuse(objs)    voxel-remesh union of meshes into one sculpted volume (approach B), then a light smooth.

Dynamics: study_clumps records every clump as a "lock" (centre line + vertex range), so the shared groom dynamics
(spec.hair.dynamics.structures.<name>) adds spring-chain bones exactly as for groom locks."""
import math
import random

from mathutils import Vector


def _groom():
    import groom
    return groom


def _felt():
    import groom_felt
    return groom_felt


def lerp_table(tab, x):
    x = abs(((x + 180) % 360) - 180)
    tab = sorted(tab)
    if x <= tab[0][0]:
        return tab[0][1]
    for (a0, v0), (a1, v1) in zip(tab, tab[1:]):
        if x <= a1:
            t = (x - a0) / (a1 - a0)
            return v0 + (v1 - v0) * t
    return tab[-1][1]


def rr(R, v):
    return R.uniform(float(v[0]), float(v[1])) if isinstance(v, (list, tuple)) else float(v)


# ---------------------------------------------------------------------------------------------------------- clumps
def _rotate_towards(d, target, angle):
    """Rotate unit vector d by `angle` (radians) along the great circle towards target."""
    axis = d.cross(target)
    if axis.length < 1e-6:
        axis = d.orthogonal()
    from mathutils import Matrix
    return (Matrix.Rotation(angle, 3, axis.normalized()) @ d).normalized()


def clump_mesh(path, ups, widths, thicks, seg, R, grooves, gdepth, irr):
    n = len(path)
    verts, faces = [], []
    ph = [R.uniform(0, 6.283) for _ in range(6)]
    gph = R.uniform(0, 6.283)
    for i in range(n):
        T = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        N = (ups[i] - T * ups[i].dot(T)).normalized()
        B = T.cross(N).normalized()
        for k in range(seg):
            phi = 2 * math.pi * k / seg
            noise = irr * (math.sin(i * 0.35 + ph[0] + 2 * phi) * 0.6 + math.sin(i * 0.9 + ph[1] + 3 * phi) * 0.4)
            groove = -gdepth * max(0.0, math.cos(grooves * phi + gph)) ** 3 if grooves else 0.0
            r = 1.0 + noise + groove
            verts.append(path[i] + B * (math.cos(phi) * widths[i] * 0.5 * r) + N * (math.sin(phi) * thicks[i] * 0.5 * r))
    for i in range(n - 1):
        for k in range(seg):
            a, b = i * seg + k, i * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    # caps: a pole vertex at each end (root sunk into the cap; tip slightly beyond the last ring: a soft point)
    T0 = (path[1] - path[0]).normalized()
    Tn = (path[-1] - path[-2]).normalized()
    root = len(verts)
    verts.append(path[0] - T0 * thicks[0] * 0.3)
    tip = len(verts)
    verts.append(path[-1] + Tn * max(widths[-1], thicks[-1]) * 0.6)
    last = (n - 1) * seg
    for k in range(seg):
        faces.append((root, (k + 1) % seg, k))
        faces.append((last + k, last + (k + 1) % seg, tip))
    return verts, faces


def build_clumps(st, ctx, R):
    G = _groom()
    sc = ctx["scalp"]
    bucket = G.MeshBucket()
    seg = int(st.get("seg", 14))
    step = float(st.get("step_m", 0.004))
    grooves = int(st.get("grooves", 3))
    gdepth = float(st.get("groove_depth", 0.12))
    irr = float(st.get("irregularity", 0.06))
    keep = st.get("keepout")
    made = 0
    for row in st["rows"]:
        cnt = int(row["count"])
        a0, a1 = [float(x) for x in row["az"]]
        flow = row.get("flow", "away")
        pole = row.get("pole", {"az": 180, "el": 60})
        pdir = G.Scalp.direction(float(pole["az"]), float(pole["el"]))
        for c in range(cnt):
            az = a0 + (a1 - a0) * ((c + R.uniform(0.2, 0.8)) / cnt) if cnt > 1 else (a0 + a1) / 2
            el = rr(R, row["el"])
            d0 = G.Scalp.direction(az, el)
            L = math.radians(rr(R, row["len_deg"]))
            jit = math.radians(R.uniform(-1, 1) * float(row.get("jitter_deg", 8)))
            if flow == "down":
                tgt = Vector((d0.x, d0.y, -1.6)).normalized()
            elif flow == "toward":
                tgt = pdir
            elif flow == "stand":
                tgt = _rotate_towards(d0, -pdir, 1.0)  # short arc leaning away from the whorl; the lift makes it stand
            else:  # away from the pole (whorl)
                tgt = _rotate_towards(d0, -pdir, 3.0) if (d0 - pdir).length > 1e-4 else d0.orthogonal()
            conv = float(row.get("converge", 0.0))
            d1 = _rotate_towards(d0, tgt, L)
            if conv:
                fa = math.degrees(math.atan2(d1.x, -d1.y))
                fe = math.degrees(math.asin(max(-1, min(1, d1.z))))
                d1 = G.Scalp.direction(fa * (1 - conv), fe)
            # sideways jitter of the tip direction (around d0)
            from mathutils import Matrix
            d1 = (Matrix.Rotation(jit, 3, d0) @ d1).normalized()
            if keep:
                fa = math.degrees(math.atan2(d1.x, -d1.y))
                fe = math.degrees(math.asin(max(-1, min(1, d1.z))))
                if abs(fa) < float(keep["az"]) and fe < float(keep["el_min"]):
                    d1 = G.Scalp.direction(fa, float(keep["el_min"]) + R.uniform(0, 3))
            l0, l1 = [float(x) for x in row.get("lift", [0.0, 0.02])]
            lp = float(row.get("lift_power", 1.6))
            wl = rr(R, row["width"])
            tk = rr(R, row["thick"])
            curl = math.radians(R.uniform(-1, 1) * float(row.get("curl_deg", 0.0)))
            # path length estimate (arc on the head + lift)
            arc = sc.radii.length / math.sqrt(3) * max(L, 0.05) + abs(l1 - l0)
            n = max(6, int(arc / step))
            path, ups = [], []
            for i in range(n):
                s = i / (n - 1)
                d = G.slerp(d0, d1, s)
                if curl:
                    d = (Matrix.Rotation(curl * s * s, 3, d0) @ d).normalized()
                p, nrm = sc.at_dir(d, l0 + (l1 - l0) * s ** lp - 0.004 * (1 - s) ** 4)
                path.append(p)
                ups.append(nrm)
            tp = float(row.get("taper_power", 2.4))  # lower = more conical (spikes)
            prof = [(1 - (i / (n - 1)) ** tp) ** 0.65 * (0.85 + 0.3 * math.sin(math.pi * i / (n - 1))) for i in range(n)]
            widths = [max(0.003, wl * p) for p in prof]
            thicks = [max(0.0025, tk * (0.6 + 0.4 * p)) * (0.35 + 0.65 * p) for p in prof]
            v_start = len(bucket.verts)
            vs, fs = clump_mesh(path, ups, widths, thicks, seg, R, grooves, gdepth, irr)
            bucket.add(vs, fs)
            if "dynamics" in ctx:
                # the chain runs from where the clump leaves the scalp (40%) to the tip
                k0 = int(0.35 * (n - 1))
                ctx["dynamics"].append({"kind": "lock", "structure": st.get("name", st["type"]), "index": made,
                                        "line": path[k0:], "verts": (v_start, len(bucket.verts))})
            made += 1
    return bucket, {"clumps": made}


# --------------------------------------------------------------------------------------------------------- curtain
def build_curtain(st, ctx, R):
    G = _groom()
    F = _felt()
    sc = ctx["scalp"]
    a0, a1 = [float(x) for x in st["az"]]
    nu, nv = st.get("resolution", [180, 90])
    leave = float(st.get("leave_el", -15))
    rx, ry = [float(x) for x in st.get("rest_radii", [0.17, 0.14])]
    rest_z = float(st.get("rest_z", 0.62))
    ncol = int(st.get("columns", 14))
    thick = float(st.get("thick", 0.03))
    cdep = float(st.get("column_depth", 0.5))
    lobe = st.get("lobe", {"pitch": 0.05, "depth": 0.35, "twist": 0.6})
    scal = float(st.get("scallop", 0.05))
    inset = float(st.get("inset", 0.004))
    cphase = [R.uniform(0, 6.283) for _ in range(ncol + 2)]
    cend = [R.uniform(-0.03, 0.03) for _ in range(ncol + 2)]
    head_frac = 0.3  # share of v on the head
    base, nrm, hout, hin = [], [], [], []
    c = sc.centre
    for i in range(nu):
        u = i / (nu - 1)
        az = a0 + (a1 - a0) * u
        el0 = lerp_table(st["root_el"], az)
        cu = u * ncol
        ci = min(ncol, int(cu))
        fc = cu - ci
        colp = 0.5 + 0.5 * math.cos(2 * math.pi * fc)  # 1 at column centres (u = k/ncol), 0 between
        zend = lerp_table(st["z_end"], az) + cend[ci] * (1 - fc) + cend[ci + 1] * fc
        zend += scal * (1 - colp) ** 1.5  # scalloped bottom: shorter between columns
        pl, nl = sc.at(az, leave, 0.0)
        p_leave = pl
        dxy = Vector((p_leave.x - c.x, p_leave.y - c.y, 0.0))
        r_leave = dxy.length
        dirxy = dxy.normalized()
        a = math.radians(az)
        r_rest = 1.0 / math.sqrt((math.sin(a) / rx) ** 2 + (math.cos(a) / ry) ** 2)
        brow, nrow, ho, hi = [], [], [], []
        for j in range(nv):
            v = j / (nv - 1)
            if v <= head_frac:
                e = el0 + (leave - el0) * (v / head_frac)
                p, n = sc.at(az, e, -sc.offset)
                z = p.z
            else:
                t = (v - head_frac) / (1 - head_frac)
                z = p_leave.z + (zend - p_leave.z) * t
                k = min(1.0, max(0.0, (p_leave.z - z) / max(1e-4, p_leave.z - rest_z)))
                k = k * k * (3 - 2 * k)
                r = r_leave + (r_rest - r_leave) * k
                p = Vector((c.x + dirxy.x * r, c.y + dirxy.y * r, z))
                n = Vector((dirxy.x, dirxy.y, 0.25 * (1 - k))).normalized()
            # sculpted ringlets: columns + helical lobes travelling around each column
            hel = math.sin(2 * math.pi * (z / float(lobe["pitch"])) + float(lobe.get("twist", 0.6)) * 2 * math.pi * fc
                           + cphase[ci])
            depth_on = min(1.0, v / head_frac) ** 2  # smooth on the scalp, ringlets once the hair hangs
            h = thick * (1 - cdep * depth_on * (1 - colp ** 0.6)) * (1 + float(lobe["depth"]) * depth_on * hel * colp)
            # rounded tips and soft side edges
            tip = min(1.0, (1 - v) / 0.08)
            side = min(1.0, u / 0.04, (1 - u) / 0.04)
            h *= math.sqrt(max(0.0, tip)) * (0.35 + 0.65 * side)
            h *= 0.55 + 0.45 * min(1.0, v / 0.12)
            brow.append(p)
            nrow.append(n)
            ho.append(max(0.0008, h))
            hi.append(inset if v <= head_frac else thick * 0.25)
        base.append(brow)
        nrm.append(nrow)
        hout.append(ho)
        hin.append(hi)
    bucket = G.MeshBucket()
    bucket.add(*F.shell_mesh(base, nrm, hout, hin, False))
    bucket.recalc = True
    return bucket, {"shape": "curtain", "grid": [nu, nv], "columns": ncol}


# ------------------------------------------------------------------------------------------------------------ fuse
def fuse(objs, name, C, voxel=0.0022, smooth_iters=4, smooth_factor=0.6):
    """Voxel-remesh union of the given meshes into one sculpted volume (approach B). Returns the new object."""
    import bpy
    import bmesh
    bm = bmesh.new()
    for ob in objs:
        me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        me.transform(ob.matrix_world)
        bm.from_mesh(me)
        ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    out = bpy.data.objects.new(name, me)
    C.objects.link(out)
    me.remesh_voxel_size = voxel
    me.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = out
    out.select_set(True)
    bpy.ops.object.voxel_remesh()
    m = out.modifiers.new("smooth", "SMOOTH")
    m.iterations, m.factor = smooth_iters, smooth_factor
    bpy.ops.object.modifier_apply(modifier=m.name)
    out.data.shade_smooth()
    for ob in objs:
        bpy.data.objects.remove(ob, do_unlink=True)
    return out


def register():
    """Adds the study primitives to the shared groom builder in this process only (no file is changed)."""
    G = _groom()
    G.BUILDERS["study_clumps"] = build_clumps
    G.BUILDERS["study_curtain"] = build_curtain
    G.TYPES.update({"study_clumps", "study_curtain"})
    if not getattr(G.validate_dynamics, "_study", False):
        orig = G.validate_dynamics

        def validate_dynamics(hair_spec):  # study clumps carry lock chains: validate them as locks
            hs = dict(hair_spec, structures=[dict(s, type="locks") if s.get("type") == "study_clumps" else s
                                             for s in hair_spec.get("structures", [])])
            return orig(hs)
        validate_dynamics._study = True
        G.validate_dynamics = validate_dynamics
