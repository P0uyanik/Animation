"""Hybrid felt hair (`groom/2`, "hair v3", T-044; approach C of the T-049 study, owner decision 2026-11-17).

Felted base volumes carry the mass and the silhouette (crown, fringe, temples, buns, back mass); a small, spec-driven
budget of broad felt clumps, locks and ringlets at the edges carries the character of the hairstyle and the secondary
motion. Character-independent: every shape, count, size, colour and attachment point is spec data (spec.hair); no
character names. groom/1 (groom.py, groom_felt.py) is used as a library and is never changed, so characters pinned to
groom/1 or hair_clumps/* build exactly as before.

spec.hair (generator "groom/2"):
  structures    the groom/1 structure types (scalp_cap, felt_volume, bun, locks, sweep, fringe, tie, bow, flowers;
                see groom.py / groom_felt.py) plus two hybrid primitives:
    clumps      broad felted clumps that follow the scalp along a flow map and lift off towards a soft point
                (spiky/short styles, fringe clumps, crown tufts, temple and back clumps):
                {"type": "clumps", "name", "rows": [{"count", "az": [a0, a1], "el": [lo, hi],
                  "flow": "away" | "down" | "toward" | "stand", "pole": {"az", "el"} (whorl for away/toward/stand),
                  "len_deg": [lo, hi], "lift": [root, tip], "lift_power", "width": [lo, hi], "thick": [lo, hi],
                  "jitter_deg", "converge" (tips pulled towards az 0 by this fraction), "curl_deg" (sideways bend),
                  "lift": [root, peak, tip] + "lift_peak" (0..1, default 0.6) arches the clump up and back down
                  towards the scalp (tufts that curl back, rounded puffy clumps; T-070),
                  "flick_m" (outward flick of the last third of the tip), "taper_power" (width profile 1 - s^p:
                  ~2.4 leaf, ~1.1 cone), "az_list" (explicit root azimuths instead of an even spread)}],
                 "seg", "step_m", "grooves", "groove_depth", "irregularity", "keepout" (overrides the hair keep-out)}
    curtain     a sculpted long-hair base shell over the back/shoulders (thin felt base under the edge ringlets/locks):
                {"type": "curtain", "name", "az": [a0, a1], "root_el": [[az, el], ...], "leave_el",
                 "z_end": [[az, z], ...] (absolute metres, over |az|), "rest_radii": [rx, ry], "rest_z", "columns",
                 "thick", "column_depth", "lobe": {"pitch", "depth", "twist"}, "scallop", "resolution": [nu, nv],
                 "inset"}
    felt_bow    a puffy felt bow (rounded felt loops around a knot) on the scalp or a bun (attachment point as spec
                data): {"type": "felt_bow", "name", "az", "el", "out" | "bun", "around_deg", "height_frac", "out",
                 "size", "tilt_deg", "loops": [{"angle_deg", "length", "width", "thick", "swirl"}], "knot",
                 "material" (default slot "hair_bow")}; on a bun with a chain it follows the bun like a groom/1 bow.
  face_keepout  {"az": deg, "el_min": deg, "margin_deg" (default 2)}: the face window. Every clump tip with |azimuth| < az is held at or above
                el_min (the brow line); locks rooted inside the window are rejected by validation; felt fringe tips
                (tip_az/tip_el form) inside the window must stay at or above el_min. The build reports the hair
                vertices found inside the window in front of the face ("keepout": {"violations": n}).
  fibres, dynamics, binding, seed, scalp_offset_m, finish: as groom/1 (groom.py); a fibre layer may set
                "shaft_radius_mm" (+ "tip_ratio") for a constant shaft width (fine long roving fibres; T-070). Dynamics: "clumps" structures get
                one spring chain per clump (every k-th), "locks" one per lock, "bun" a chain of n bones per bun
                (3-bone FK chains as in the hair-rig blueprints); ties, bows and flowers on a bun follow its chain.
Materials: each structure names a slot ("material", default "hair"); presets in materials/presets.json (hair v3 uses
"felt hair/2", the felt hair surface plus a dense fibre halo)."""
import json
import math
import random

try:
    from mathutils import Matrix, Vector
except ImportError:  # plain Python: spec validation only
    Matrix = Vector = None

import groom as G1  # groom/1 as a library (read-only use)

GENERATOR_VERSIONS = ("groom/2",)
GENERATOR = "groom/2"
HYBRID_TYPES = {"clumps", "curtain", "felt_bow"}
CHAIN_TYPES = ("locks", "bun", "clumps")


def lerp_table(tab, x):
    x = abs(((x + 180) % 360) - 180)
    tab = sorted(tab)
    if x <= tab[0][0]:
        return tab[0][1]
    for (a0, v0), (a1, v1) in zip(tab, tab[1:]):
        if x <= a1:
            return v0 + (v1 - v0) * (x - a0) / (a1 - a0)
    return tab[-1][1]


def rr(R, v):
    return R.uniform(float(v[0]), float(v[1])) if isinstance(v, (list, tuple)) else float(v)


def az_el(d):
    return math.degrees(math.atan2(d.x, -d.y)), math.degrees(math.asin(max(-1.0, min(1.0, d.z))))


# ---------------------------------------------------------------------------------------------------------- clumps
def _rotate_towards(d, target, angle):
    axis = d.cross(target)
    if axis.length < 1e-6:
        axis = d.orthogonal()
    return (Matrix.Rotation(angle, 3, axis.normalized()) @ d).normalized()


def clump_mesh(path, ups, widths, thicks, seg, R, grooves, gdepth, irr):
    """Felted clump: a soft irregular, flattened section with shallow fibre grooves along a path; the root pole is sunk
    into the base, the tip ends in a soft point."""
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
    sc = ctx["scalp"]
    bucket = G1.MeshBucket()
    bucket.recalc = True
    seg = int(st.get("seg", 14))
    step = float(st.get("step_m", 0.004))
    grooves = int(st.get("grooves", 3))
    gdepth = float(st.get("groove_depth", 0.12))
    irr = float(st.get("irregularity", 0.06))
    keep = st.get("keepout", ctx.get("keepout"))
    made = clamped = 0
    for row in st["rows"]:
        cnt = int(row["count"])
        a0, a1 = [float(x) for x in row["az"]]
        flow = row.get("flow", "away")
        pole = row.get("pole", {"az": 180, "el": 60})
        pdir = G1.Scalp.direction(float(pole["az"]), float(pole["el"]))
        azl = row.get("az_list")
        for c in range(cnt):
            if azl:
                az = float(azl[c % len(azl)]) + R.uniform(-2, 2)
            else:
                az = a0 + (a1 - a0) * ((c + R.uniform(0.2, 0.8)) / cnt) if cnt > 1 else (a0 + a1) / 2
            el = rr(R, row["el"])
            d0 = G1.Scalp.direction(az, el)
            L = math.radians(rr(R, row["len_deg"]))
            jit = math.radians(R.uniform(-1, 1) * float(row.get("jitter_deg", 8)))
            if flow == "down":
                tgt = Vector((d0.x, d0.y, -1.6)).normalized()
            elif flow == "toward":
                tgt = pdir
            elif flow == "stand":
                tgt = _rotate_towards(d0, -pdir, 1.0)
            else:
                tgt = _rotate_towards(d0, -pdir, 3.0) if (d0 - pdir).length > 1e-4 else d0.orthogonal()
            conv = float(row.get("converge", 0.0))
            d1 = _rotate_towards(d0, tgt, L)
            if conv:
                fa, fe = az_el(d1)
                d1 = G1.Scalp.direction(fa * (1 - conv), fe)
            d1 = (Matrix.Rotation(jit, 3, d0) @ d1).normalized()
            if keep:
                fa, fe = az_el(d1)
                if abs(fa) < float(keep["az"]) and fe < float(keep["el_min"]):
                    d1 = G1.Scalp.direction(fa, float(keep["el_min"]) + R.uniform(0, 3))
                    clamped += 1
            lift = [float(x) for x in row.get("lift", [0.0, 0.02])]
            l0, l1 = lift[0], lift[-1]
            lp = float(row.get("lift_power", 1.6))
            arch = lift[1] if len(lift) == 3 else None  # T-070: [root, peak, tip] arches the clump back to the scalp
            pk = float(row.get("lift_peak", 0.6))
            flick = float(row.get("flick_m", 0.0))
            wl = rr(R, row["width"])
            tk = rr(R, row["thick"])
            curl = math.radians(R.uniform(-1, 1) * float(row.get("curl_deg", 0.0)))
            arc = sc.radii.length / math.sqrt(3) * max(L, 0.05) + abs(l1 - l0)
            n = max(6, int(arc / step))
            path, ups = [], []
            for i in range(n):
                s = i / (n - 1)
                d = G1.slerp(d0, d1, s)
                if curl:
                    d = (Matrix.Rotation(curl * s * s, 3, d0) @ d).normalized()
                if keep:  # every point of the clump stays out of the face window (curl and jitter included); the
                    # centre line keeps margin_deg (default 2) above el_min for the clump's own thickness
                    fa, fe = az_el(d)
                    lim = float(keep["el_min"]) + float(keep.get("margin_deg", 2.0))
                    if abs(fa) < float(keep["az"]) + float(keep.get("margin_deg", 2.0)) and fe < lim:
                        d = G1.Scalp.direction(fa, lim)
                fl = flick * max(0.0, (s - 0.66) / 0.34) ** 2
                if arch is None:
                    h = l0 + (l1 - l0) * s ** lp
                elif s <= pk:
                    h = l0 + (arch - l0) * (1 - (1 - s / pk) ** 2) ** (1.0 / lp)
                else:
                    h = arch + (l1 - arch) * ((s - pk) / (1 - pk)) ** 2
                p, nrm = sc.at_dir(d, h + fl - 0.004 * (1 - s) ** 4)
                path.append(p)
                ups.append(nrm)
            tp = float(row.get("taper_power", 2.4))
            prof = [(1 - (i / (n - 1)) ** tp) ** 0.65 * (0.85 + 0.3 * math.sin(math.pi * i / (n - 1))) for i in range(n)]
            widths = [max(0.003, wl * p) for p in prof]
            thicks = [max(0.0025, tk * (0.6 + 0.4 * p)) * (0.35 + 0.65 * p) for p in prof]
            v_start = len(bucket.verts)
            vs, fs = clump_mesh(path, ups, widths, thicks, seg, R, grooves, gdepth, irr)
            bucket.add(vs, fs)
            if ctx.get("dynamics") is not None:
                k0 = int(0.35 * (n - 1))  # the chain starts where the clump leaves the scalp
                ctx["dynamics"].append({"kind": "lock", "structure": st.get("name", st["type"]), "index": made,
                                        "line": path[k0:], "verts": (v_start, len(bucket.verts))})
            made += 1
    return bucket, {"clumps": made, "keepout_clamped": clamped}


# --------------------------------------------------------------------------------------------------------- curtain
def build_curtain(st, ctx, R):
    F = G1._felt()
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
    head_frac = 0.3
    base, nrm, hout, hin = [], [], [], []
    c = sc.centre
    for i in range(nu):
        u = i / (nu - 1)
        az = a0 + (a1 - a0) * u
        el0 = lerp_table(st["root_el"], az)
        cu = u * ncol
        ci = min(ncol, int(cu))
        fc = cu - ci
        colp = 0.5 + 0.5 * math.cos(2 * math.pi * fc)
        zend = lerp_table(st["z_end"], az) + cend[ci] * (1 - fc) + cend[ci + 1] * fc
        zend += scal * (1 - colp) ** 1.5
        p_leave, _ = sc.at(az, leave, 0.0)
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
            hel = math.sin(2 * math.pi * (z / float(lobe["pitch"])) + float(lobe.get("twist", 0.6)) * 2 * math.pi * fc
                           + cphase[ci])
            depth_on = min(1.0, v / head_frac) ** 2
            h = thick * (1 - cdep * depth_on * (1 - colp ** 0.6)) * (1 + float(lobe["depth"]) * depth_on * hel * colp)
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
    bucket = G1.MeshBucket()
    bucket.add(*F.shell_mesh(base, nrm, hout, hin, False))
    bucket.recalc = True
    return bucket, {"shape": "curtain", "grid": [nu, nv], "columns": ncol}


# ------------------------------------------------------------------------------------------------------- felt bow
def build_felt_bow(st, ctx, R):
    """A puffy felt bow: rounded felt loops (ellipsoids with soft grooves) radiating from a knot, on the scalp
    (az, el, out) or on a bun (bun, around_deg, height_frac, out). Loops: [{"angle_deg" (0 = towards the character's
    left in the bow plane, 90 = up), "length", "width", "thick", "swirl"}]; "knot" radius; "tilt_deg" turns the bow
    in its plane; "lean" tilts its plane towards the head top."""
    F = G1._felt()
    if "bun" in st:
        c, radial, ax = G1._bun_point(ctx, st, float(st.get("around_deg", 0)), float(st.get("height_frac", 0.15)),
                                      float(st.get("out", 0.006)))
    else:
        c, radial = ctx["scalp"].at(float(st["az"]), float(st["el"]), float(st.get("out", 0.008)))
        ax = Vector((0, 0, 1))
    side = ax.cross(radial)
    side = side.normalized() if side.length > 1e-6 else radial.orthogonal().normalized()
    up = radial.cross(side).normalized()
    tilt = math.radians(float(st.get("tilt_deg", 0.0)))
    side, up = side * math.cos(tilt) + up * math.sin(tilt), up * math.cos(tilt) - side * math.sin(tilt)
    size = float(st.get("size", 0.05))
    loops = st.get("loops") or [{"angle_deg": 30, "length": 0.55, "width": 0.36, "thick": 0.2},
                                {"angle_deg": 150, "length": 0.55, "width": 0.36, "thick": 0.2},
                                {"angle_deg": -40, "length": 0.42, "width": 0.28, "thick": 0.18},
                                {"angle_deg": -140, "length": 0.42, "width": 0.28, "thick": 0.18}]
    surf = {"grooves": st.get("grooves", {"count": 5, "depth": 0.25, "sharpness": 0.6, "wander": 0.3,
                                           "wavelength": 0.6}),
            "lumps": st.get("lumps", {"amount": 0.05, "scale": 1.0}), "resolution": st.get("resolution", [32, 20])}
    bucket = G1.MeshBucket()
    bucket.recalc = True
    for lp in loops:
        a = math.radians(float(lp["angle_deg"]))
        d = side * math.cos(a) + up * math.sin(a)
        L = float(lp["length"]) * size
        lc = c + d * (L * 0.5) + radial * (float(lp.get("thick", 0.2)) * size * 0.3)
        sw = d.cross(radial).normalized()
        (v, f, uv), _ = F.mass(dict(surf, swirl=float(lp.get("swirl", 0.0))), ctx, random.Random(R.random()),
                               (lc, d, radial, sw), (float(lp.get("thick", 0.2)) * size * 0.5,
                                                     float(lp["width"]) * size * 0.5, L * 0.5))
        bucket.add(v, f, uv)
    k = float(st.get("knot", 0.16)) * size
    (v, f, uv), _ = F.mass(dict(surf, swirl=0.0), ctx, random.Random(R.random()), (c + radial * k * 0.6, up, radial, side),
                           (k, k, k * 1.1))
    bucket.add(v, f, uv)
    return bucket, {"size_m": size, "loops": len(loops)}


BUILDERS = dict(G1.BUILDERS, clumps=build_clumps, curtain=build_curtain, felt_bow=build_felt_bow)
TYPES = G1.TYPES | HYBRID_TYPES
ACCESSORY_TYPES = G1.ACCESSORY_TYPES | {"felt_bow"}


# ------------------------------------------------------------------------------------------------------ validation
def validate(hair_spec):
    """Errors in a groom/2 hair spec: the groom/1 rules for groom/1 types, the hybrid primitives, the face keep-out
    and the dynamics block (chains on clumps, locks and buns)."""
    sts = hair_spec.get("structures")
    if not isinstance(sts, list) or not sts:
        return ["hair.structures must be a non-empty list"]
    errs = []
    v1 = [s for s in sts if s.get("type") not in HYBRID_TYPES]
    if v1:
        errs += [e for e in G1.validate({k: v for k, v in hair_spec.items() if k != "dynamics"} | {"structures": v1})]
    keep = hair_spec.get("face_keepout")
    if keep is not None and not (isinstance(keep, dict) and "az" in keep and "el_min" in keep):
        errs.append("hair.face_keepout must be {\"az\": deg, \"el_min\": deg}")
        keep = None
    for i, s in enumerate(sts):
        t = s.get("type")
        if t == "clumps":
            rows = s.get("rows")
            if not isinstance(rows, list) or not rows:
                errs.append(f"hair.structures[{i}] (clumps) needs a non-empty 'rows' list")
                continue
            for j, row in enumerate(rows):
                for k in ("count", "az", "el", "len_deg", "width", "thick"):
                    if k not in row:
                        errs.append(f"hair.structures[{i}].rows[{j}] (clumps) needs '{k}'")
                if row.get("flow", "away") not in ("away", "down", "toward", "stand"):
                    errs.append(f"hair.structures[{i}].rows[{j}] flow must be away, down, toward or stand")
                lift = row.get("lift", [0.0, 0.02])
                if not (isinstance(lift, list) and len(lift) in (2, 3)):
                    errs.append(f"hair.structures[{i}].rows[{j}] lift must be [root, tip] or [root, peak, tip]")
                if not 0.05 <= float(row.get("lift_peak", 0.6)) <= 0.95:
                    errs.append(f"hair.structures[{i}].rows[{j}] lift_peak must be within 0.05..0.95")
        elif t == "felt_bow":
            if "bun" not in s and not all(k in s for k in ("az", "el")):
                errs.append(f"hair.structures[{i}] (felt_bow) needs 'bun' or 'az' and 'el'")
            nb = sum(len(x.get("buns", [])) for x in sts if x.get("type") == "bun")
            if "bun" in s and int(s["bun"]) >= nb:
                errs.append(f"hair.structures[{i}] refers to bun {s['bun']}, but only {nb} bun(s) exist")
        elif t == "curtain":
            for k in ("az", "root_el", "z_end"):
                if k not in s:
                    errs.append(f"hair.structures[{i}] (curtain) needs '{k}'")
        if keep:
            ka, ke = float(keep["az"]), float(keep["el_min"])
            if t == "locks":
                lo, hi = sorted(float(x) for x in s["az"])
                roots = [lo, hi] + ([-lo, -hi] if s.get("mirror") else [])
                if any(abs(a) < ka for a in roots) or (lo < 0 < hi):
                    errs.append(f"hair.structures[{i}] (locks {s.get('name', '')}) is rooted inside the face keep-out "
                                f"(|az| < {ka:g})")
            if t == "felt_volume" and s.get("shape") == "fringe" and "tip_az" in s:
                for a, e in zip(s["tip_az"], s["tip_el"]):
                    if abs(float(a)) < ka and float(e) < ke:
                        errs.append(f"hair.structures[{i}] fringe tip ({a}, {e}) is inside the face keep-out")
                        break
    for k, layer in enumerate((hair_spec.get("fibres") or {}).get("layers") or []):
        if "shaft_radius_mm" in layer and not 0.0 < float(layer["shaft_radius_mm"]) <= 2.0:
            errs.append(f"hair.fibres.layers[{k}].shaft_radius_mm must be within (0, 2]")
        if "tip_ratio" in layer and not 0.0 <= float(layer["tip_ratio"]) <= 1.0:
            errs.append(f"hair.fibres.layers[{k}].tip_ratio must be within 0..1")
    errs += validate_dynamics(hair_spec)
    return errs


def validate_dynamics(hair_spec):
    """groom/1 dynamics rules, with chains also allowed on clumps (one chain per clump, like a lock)."""
    as_v1 = dict(hair_spec, structures=[dict(s, type="locks") if s.get("type") == "clumps" else s
                                        for s in hair_spec.get("structures", [])])
    return G1.validate_dynamics(as_v1)


# ------------------------------------------------------------------------------------------------------------ build
def keepout_violations(objs, scalp, keep, depth_m=0.03):
    """Hair vertices inside the face window (|az| < keep.az, el < keep.el_min, as seen from the head centre) that lie
    in front of the face surface within depth_m: hair that would hang over the face."""
    if not keep:
        return 0
    ka, ke = float(keep["az"]), float(keep["el_min"])
    n = 0
    for ob in objs:
        if ob.type != "MESH":
            continue
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            d = p - scalp.centre
            if d.length < 1e-6:
                continue
            a, e = az_el(d.normalized())
            if abs(a) < ka and e < ke:
                surf, _ = scalp.at_dir(d, -scalp.offset)
                r_s = (surf - scalp.centre).length
                if d.length > r_s - 0.002 and d.length < r_s + depth_m:
                    n += 1
    return n


SHAFT_GROUP = "PS Fibre Fixed Shaft/1"


def fixed_shaft(fo, radius, tip_ratio):
    """T-070: a constant fibre shaft (radius at the root, radius x tip_ratio at the tip) after the shared fibre group,
    whose shaft width scales with fibre length (0.16 x length): long, fine roving fibres for a smooth halo. Opt-in per
    fibre layer ("shaft_radius_mm", "tip_ratio"); layers without it are unchanged."""
    import bpy
    g = bpy.data.node_groups.get(SHAFT_GROUP)
    if g is None:
        g = bpy.data.node_groups.new(SHAFT_GROUP, "GeometryNodeTree")
        g.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        for nm in ("Radius", "Tip Ratio"):
            g.interface.new_socket(name=nm, in_out="INPUT", socket_type="NodeSocketFloat")
        g.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        n, ln = g.nodes, g.links
        gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
        par = n.new("GeometryNodeSplineParameter")
        tip = n.new("ShaderNodeMath")
        tip.operation = "MULTIPLY"
        ln.new(gi.outputs["Radius"], tip.inputs[0])
        ln.new(gi.outputs["Tip Ratio"], tip.inputs[1])
        mr = n.new("ShaderNodeMapRange")
        mr.clamp = True
        ln.new(par.outputs["Factor"], mr.inputs["Value"])
        ln.new(gi.outputs["Radius"], mr.inputs["To Min"])
        ln.new(tip.outputs[0], mr.inputs["To Max"])
        sr = n.new("GeometryNodeSetCurveRadius")
        ln.new(gi.outputs["Geometry"], sr.inputs["Curve"])
        ln.new(mr.outputs["Result"], sr.inputs["Radius"])
        ln.new(sr.outputs["Curve"], go.inputs["Geometry"])
    m = fo.modifiers.new("PS Fibre Fixed Shaft", "NODES")
    m.node_group = g
    for item in g.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name in ("Radius", "Tip Ratio"):
            getattr(m.properties.inputs, item.identifier).value = radius if item.name == "Radius" else tip_ratio
    fo["ps_fibre_shaft_m"] = radius


def build(C, head, frame, hair_spec, material, face_y, fibres=None):
    """As groom.build (same arguments and return value), for groom/2 specs."""
    errs = validate(hair_spec)
    if errs:
        raise SystemExit("groom/2: " + "; ".join(errs))
    seed = int(hair_spec.get("seed", 11))
    yarn = dict(G1.YARN_DEFAULT, **(hair_spec.get("yarn") or {}))
    scalp = G1.Scalp(head, frame["centre"], frame["radii"], float(hair_spec.get("scalp_offset_m", 0.008)))
    keep = hair_spec.get("face_keepout")
    ctx = {"C": C, "head": head, "scalp": scalp, "yarn": yarn, "face_y": face_y, "buns": [],
           "finish": hair_spec.get("finish", "felt"), "seed": seed, "keepout": keep}
    dyn = G1.dynamics_spec(hair_spec)
    if dyn:
        ctx["dynamics"] = []
    sts = hair_spec["structures"]
    for s in sts:
        if s["type"] == "bun":
            ctx["buns"] += G1.bun_frames(s, ctx)
    objs, rep = [], {"generator": GENERATOR, "structures": {}}
    slot_of = {}
    for i, s in enumerate(sts):
        t = s["type"]
        name = s.get("name", t)
        R = random.Random(seed * 7919 + i)
        if t == "scalp_cap":
            ob = G1._hair().scalp_cap(C, head, s)
            ob.name = ob.data.name = f"hair_{name}"
            G1.HAIR_G().assign(ob, material(s.get("material", "hair")))
            slot_of[ob.name] = s.get("material", "hair")
            objs.append(ob)
            rep["structures"][name] = {"type": t, "faces": len(ob.data.polygons)}
            continue
        n_rec = len(ctx["dynamics"]) if dyn else 0
        result, info = BUILDERS[t](s, ctx, R)
        made = []
        if isinstance(result, dict):
            slots = {"petals": s.get("material", "hair_flower"), "centres": s.get("centre_material", "hair_flower_centre")}
            for part, bucket in result.items():
                ob = bucket.obj(f"hair_{name}_{part}", C)
                G1.HAIR_G().assign(ob, material(slots[part]))
                slot_of[ob.name] = slots[part]
                made.append(ob)
        else:
            default = "hair" if t not in ACCESSORY_TYPES else "hair_bow" if t == "felt_bow" else "hair_" + t
            ob = result.obj(f"hair_{name}", C)
            G1.HAIR_G().assign(ob, material(s.get("material", default)))
            slot_of[ob.name] = s.get("material", default)
            made.append(ob)
        objs += made
        if dyn:
            # a felt bow on a bun follows the bun's chain like a groom/1 bow
            G1._store_dynamics_records(made, dict(s, type="bow") if t == "felt_bow" else s, ctx["dynamics"][n_rec:],
                                       ctx, dyn)
        info.update(type=t)
        rep["structures"][name] = info
    rep["objects"] = [o.name for o in objs]
    rep["vertices"] = sum(len(o.data.vertices) for o in objs)
    if keep:
        hair_slots = {o.name for o in objs if slot_of.get(o.name) == "hair"}
        per = {o.name: keepout_violations([o], scalp, keep) for o in objs if o.name in hair_slots}
        rep["keepout"] = {"az": float(keep["az"]), "el_min": float(keep["el_min"]),
                          "violations": sum(per.values()), "by_object": {k: v for k, v in per.items() if v}}
    fb = hair_spec.get("fibres")
    if fb and fb.get("enabled", True) and fibres is not None:
        slots = set(fb.get("slots", ["hair"]))
        made = []
        for ob in objs:
            if slot_of.get(ob.name) in slots:
                for layer in fb.get("layers", [{}]):
                    fo = fibres(ob, slot_of[ob.name], layer.get("overrides") or {})
                    if fo is not None:
                        if layer.get("shaft_radius_mm"):
                            fixed_shaft(fo, float(layer["shaft_radius_mm"]) / 1000.0, float(layer.get("tip_ratio", 0.35)))
                        fo.parent = ob
                        fo.matrix_parent_inverse = ob.matrix_world.inverted()
                        fo["ps_groom_fibres"] = layer.get("name", "fibres")
                        made.append(fo.name)
        rep["fibres"] = {"objects": len(made), "layers": [l.get("name", "fibres") for l in fb.get("layers", [{}])]}
    if dyn:
        rep["dynamics"] = {"chains": sum(len(json.loads(o.get("ps_dyn", "{}")).get("chains", [])) for o in objs)}
    return objs, rep


def bind(rig, objs, head_bone, chest_bone, binding):
    """As groom.bind (head/chest blend, chain bones and their skinning; the chain list for the engine exporter)."""
    G1.bind(rig, objs, head_bone, chest_bone, binding)
