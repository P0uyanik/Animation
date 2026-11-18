"""``garment/2`` outline fields (T-093): trouser break, split bloomer legs and the rolled boot cuff.

hem_break (``trousers`` / ``shorts``): the hem settles on the shoe. Over ``height_m`` above the hem the leg flares
  out by up to ``flare_m`` at the hem, bunches into ``folds`` soft horizontal folds of ``fold_depth_m`` (slightly
  slanted around the leg so they do not read as rings) and the front of the hem drops ``front_drop_m`` onto the
  shoe; ``pleats`` vertical gathers of ``pleat_depth_m`` above the hem (a gathered cuff, e.g. on bloomers). Every
  piece of the item is moved (shell, bands, seams), so they stay together.
leg_split (``shorts``): bloomer legs read as two legs. From ``start`` thigh radii below the hip line down to the
  hem, the inner half of each leg (facing the other leg) is drawn towards its own leg's axis by up to ``amount``
  (share of the distance; a smooth ramp below the split top, ``hem_amount`` of it kept at the hem, so the hem bands
  follow), but never past the body's own inner leg surface (measured) less ``clearance_m`` and the garment
  thickness, so the inner wall ends between the legs and a crease opens at the front and back centre; the gusset is shortened by ``gusset_rise`` (share of its drop).
cuff_roll (``boots``): a turned-down fleece cuff around the top of the shaft instead of the ``garment/1`` cuff tube:
  ``height_m`` deep, ``thickness_m`` proud of the shaft at its fullest, rolling over the rim into the boot down to
  ``inner_m``; ``lumps`` (0..1) gives the felt roll a soft irregular surface. Material part ``cuff`` (falls back to
  ``band``, then ``main``).
Character-agnostic: the leg axes and shaft radii are measured on the built pieces and the generic body."""
import math

from mathutils import Vector

from garments import generator as GEN
from garments import shapes as S

HEM_BREAK = {"height_m": 0.05, "flare_m": 0.004, "folds": 2, "fold_depth_m": 0.002, "front_drop_m": 0.006,
             "pleats": 0, "pleat_depth_m": 0.002}
LEG_SPLIT = {"amount": 0.6, "start": 0.5, "hem_amount": 1.0, "clearance_m": 0.002, "gusset_rise": 0.5}
CUFF_ROLL = {"height_m": 0.03, "thickness_m": 0.008, "inner_m": 0.012, "lumps": 0.15, "segments": 72}


def _check(v, name, field, defaults, ranges):
    if v is False:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.{field} must be an object or false")
    for key, val in v.items():
        if key not in defaults:
            raise ValueError(f"garment {name}.{field}.{key}: unknown field (known: {sorted(defaults)})")
        lo, hi = ranges[key]
        if isinstance(defaults[key], int) and not isinstance(defaults[key], bool) and key in ("folds", "segments",
                                                                                              "pleats"):
            if not isinstance(val, int) or isinstance(val, bool) or not lo <= val <= hi:
                raise ValueError(f"garment {name}.{field}.{key} must be an integer in [{lo}, {hi}]")
        else:
            GEN._number(val, f"garment {name}.{field}.{key}", lo, hi)


def validate_hem_break(v, name):
    _check(v, name, "hem_break", HEM_BREAK, {"height_m": (0.005, 0.3), "flare_m": (0.0, 0.05), "folds": (0, 6),
                                            "fold_depth_m": (0.0, 0.02), "front_drop_m": (0.0, 0.05),
                                            "pleats": (0, 40), "pleat_depth_m": (0.0, 0.02)})


def validate_leg_split(v, name):
    _check(v, name, "leg_split", LEG_SPLIT, {"amount": (0.0, 1.0), "start": (0.0, 1.5), "hem_amount": (0.0, 1.0),
                                            "clearance_m": (0.0, 0.02),
                                            "gusset_rise": (0.0, 1.0)})


def validate_cuff_roll(v, name):
    _check(v, name, "cuff_roll", CUFF_ROLL, {"height_m": (0.005, 0.15), "thickness_m": (0.001, 0.05),
                                            "inner_m": (0.0, 0.1), "lumps": (0.0, 1.0), "segments": (24, 160)})


def _settings(cfg, field, defaults):
    v = cfg.get(field)
    return dict(defaults, **v) if isinstance(v, dict) else dict(defaults)


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _world_verts(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def _leg_axes(main, bottom_z, band):
    """Per side (+1 = left, -1 = right): the (x, y) centre of the shell's vertices within ``band`` above the hem."""
    out = {}
    pts = [p for p in _world_verts(main) if p.z <= bottom_z + band]
    for s in (1.0, -1.0):
        mine = [p for p in pts if p.x * s > 0]
        if mine:
            out[s] = (sum(p.x for p in mine) / len(mine), sum(p.y for p in mine) / len(mine))
    return out


def hem_break(cfg, mine, P, H, J, fit):
    st = _settings(cfg, "hem_break", HEM_BREAK)
    main = next(o for o in mine if o.get("ps_garment_part") == "main")
    pts = _world_verts(main)
    bottom = min(p.z for p in pts)
    h = float(st["height_m"]) * fit.leg
    axes = _leg_axes(main, bottom, 0.25 * h)
    flare, depth = float(st["flare_m"]) * fit.leg, float(st["fold_depth_m"]) * fit.leg
    drop, folds = float(st["front_drop_m"]) * fit.leg, int(st["folds"])
    pleats, pdepth = int(st["pleats"]), float(st["pleat_depth_m"]) * fit.leg
    moved, max_move = 0, 0.0
    for ob in mine:
        if ob.type != "MESH":
            continue
        inv = ob.matrix_world.inverted()
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            u = (p.z - bottom) / max(h, 1e-9)
            if u >= 1.0 or p.x == 0.0:
                continue
            u = max(0.0, u)
            cx, cy = axes.get(1.0 if p.x > 0 else -1.0, (p.x, p.y))
            d = Vector((p.x - cx, p.y - cy, 0.0))
            r = d.length
            if r < 1e-6:
                continue
            d /= r
            a = math.atan2(d.y, d.x)
            w = (1.0 - u) ** 2
            ripple = math.sin(math.pi * folds * u + 0.7 * math.sin(2.0 * a)) * math.sin(math.pi * u) if folds else 0.0
            # vertical pleats gathered into the hem band: tight at the band, fullest just above it, gone at the top
            pleat = pdepth * (0.5 + 0.5 * math.cos(pleats * a)) * math.sin(math.pi * min(1.0, 1.4 * u)) ** 0.7 if pleats else 0.0
            dr = flare * w + depth * ripple + pleat
            dz = -drop * max(0.0, -d.y) ** 1.5 * w
            q = p + d * dr + Vector((0.0, 0.0, dz))
            v.co = inv @ q
            moved += 1
            max_move = max(max_move, (q - p).length)
        ob.data.update()
    return {"hem_z_m": round(bottom, 4), "height_m": round(h, 4), "vertices_moved": moved,
            "max_move_m": round(max_move, 5)}


def _inner_surface(body, side, z_lo, z_hi, cell):
    """(z, y) cell -> the smallest |x| of the body's vertices on one side (+1 left, -1 right): the inner surface of
    the leg facing the other leg, measured on the generic body."""
    out = {}
    for v in body.data.vertices:
        p = body.matrix_world @ v.co
        if p.x * side <= 0 or not z_lo - cell < p.z < z_hi + cell:
            continue
        k = (round(p.z / cell), round(p.y / cell))
        out[k] = min(out.get(k, 1e9), abs(p.x))
    return out


def leg_split(cfg, mine, P, H, J, fit, body=None):
    st = _settings(cfg, "leg_split", LEG_SPLIT)
    main = next(o for o in mine if o.get("ps_garment_part") == "main")
    pts = [p for o in mine if o.type == "MESH" for p in _world_verts(o)]
    bottom = min(p.z for p in pts)
    hip_z = P["leg"]["hip_z"] * H
    r0 = P["leg"]["radii"][0] * H
    crotch = hip_z - float(st["start"]) * r0
    amount, hem = float(st["amount"]), float(st["hem_amount"])
    clear = float(st["clearance_m"]) * fit.leg + cfg["thickness_m"]
    hx = {1.0: abs(J["hip.L"].x), -1.0: -abs(J["hip.R"].x)}
    cell = 0.003 * fit.leg
    inner = {s: _inner_surface(body, s, bottom, crotch, cell) for s in (1.0, -1.0)} if body is not None else None
    span = max(crotch - bottom, 1e-9)
    moved, max_move, gap = 0, 0.0, None
    for ob in mine:
        if ob.type != "MESH" or ob.get("ps_garment_part") == "gusset":
            continue
        inv, mw = ob.matrix_world.inverted(), ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            if not bottom - 1e-6 <= p.z < crotch or p.x == 0.0:
                continue
            s = 1.0 if p.x > 0 else -1.0
            dx = p.x - hx[s]
            if dx * s >= 0.0:  # outer half of the leg: unchanged
                continue
            u = (crotch - p.z) / span  # 0 at the split top, 1 at the hem
            ramp = _smooth(u / 0.25) * (1.0 - (1.0 - hem) * _smooth((u - 0.6) / 0.4))
            x = p.x - dx * amount * ramp
            if inner is not None:  # never into the own leg: stop at its inner surface (measured) - clearance
                k = (round(p.z / cell), round(p.y / cell))
                near = [inner[s][kk] for kk in ((k[0] + i, k[1] + j) for i in (-1, 0, 1) for j in (-1, 0, 1))
                        if kk in inner[s]]
                if near:
                    limit = max(min(near) - clear, 0.0)
                    x = s * min(abs(x), max(limit, abs(p.x)))
            q = Vector((x, p.y, p.z))
            v.co = inv @ q
            moved += 1
            max_move = max(max_move, (q - p).length)
        ob.data.update()
    # the gap the split opened at the hem, front/back centre (for the report)
    hem_pts = [mw_p for mw_p in _world_verts(main) if abs(mw_p.z - (bottom + 0.1 * span)) < 0.003 and abs(mw_p.y) < 0.015]
    lp = [p.x for p in hem_pts if p.x > 0]
    rp = [p.x for p in hem_pts if p.x < 0]
    if lp and rp:
        gap = round(min(lp) - max(rp), 4)
    rise = float(st["gusset_rise"])
    for ob in mine:
        if ob.get("ps_garment_part") != "gusset" or rise <= 0:
            continue
        gp = _world_verts(ob)
        top = max(p.z for p in gp)
        inv = ob.matrix_world.inverted()
        for v, p in zip(ob.data.vertices, gp):
            v.co = inv @ Vector((p.x, p.y, top - (top - p.z) * (1.0 - rise)))
        ob.data.update()
    return {"split_top_z_m": round(crotch, 4), "hem_z_m": round(bottom, 4), "vertices_moved": moved,
            "max_move_m": round(max_move, 5), "hem_gap_m": gap, "gusset_rise": rise}


def cuff_roll(C, body, cfg, mine, P, H, J, G, fit):
    st = _settings(cfg, "cuff_roll", CUFF_ROLL)
    lm = fit.leg
    h, T = float(st["height_m"]) * lm, float(st["thickness_m"]) * lm
    inner, lumps, n = float(st["inner_m"]) * lm, float(st["lumps"]), int(st["segments"])
    clearance = float(cfg.get("collision_clearance_m", max(0.003, cfg["thickness_m"] * 1.5)))
    mats = cfg.get("materials", {})
    mat = GEN._mat_for(G, cfg, next((k for k in ("cuff", "band") if k in mats), "main"), H)
    made, report = [], []
    for side in ("L", "R"):
        main = next((o for o in mine if o.name == f"garment.{cfg['name']}.main.{side}"), None)
        if main is None:
            continue
        pts = _world_verts(main)
        top = max(p.z for p in pts)
        rim = [p for p in pts if p.z > top - 0.006 * lm]
        centre = (sum(p.x for p in rim) / len(rim), sum(p.y for p in rim) / len(rim))
        max_r = abs(J[f"ankle.{side}"].x) * 0.95 + 0.06 * lm
        # shaft radius per sector, measured on the built shell over the cuff's depth (widest), and the leg inside
        shaft = [max(rs) for rs in zip(*[GEN._section_radii(main, centre, z, n, 0.003 * lm, max_r, 0.05 * lm)
                                         for z in (top - 0.15 * h, top - 0.5 * h, top - 0.85 * h)])]
        leg = GEN._section_radii(body, centre, top - 0.002 * lm, n, 0.004 * lm, max_r, 0.03 * lm)
        # profile (radial offset from the shaft, z): up the outside, over the rim, down the inside
        prof = [(-0.15 * T, top - 1.02 * h), (0.45 * T, top - 0.9 * h), (0.85 * T, top - 0.65 * h),
                (1.0 * T, top - 0.38 * h), (0.9 * T, top - 0.12 * h), (0.55 * T, top + 0.3 * T),
                (0.0, top + 0.45 * T), ("in", top + 0.25 * T), ("in", top - 0.4 * inner), ("in", top - inner)]
        verts = []
        rows = None
        for k in range(n):
            a = 2 * math.pi * k / n
            d = Vector((math.cos(a), math.sin(a), 0.0))
            r_in = min(leg[k] + clearance, shaft[k] - 0.3 * T)
            ctrl = []
            for dr, z in prof:
                r = r_in if dr == "in" else shaft[k] + dr
                ctrl.append(Vector((r, 0.0, z)))
            ring = S.catmull_rom(ctrl, 4)
            rows = len(ring)
            for j, q in enumerate(ring):
                t = j / max(rows - 1, 1)
                phase = 0.4 if side == "L" else 1.1
                bump = lumps * T * 0.18 * math.sin(math.pi * t) * (math.sin(7 * a + 1.3) + 0.6 * math.sin(13 * a + phase))
                r = q.x + bump
                verts.append(tuple(Vector((centre[0], centre[1], q.z)) + d * r))
        faces = []
        for k in range(n):
            k2 = (k + 1) % n
            for j in range(rows - 1):
                faces.append((k * rows + j, k * rows + j + 1, k2 * rows + j + 1, k2 * rows + j))
        ob = G.new_object(f"garment.{cfg['name']}.cuff.{side}", verts, faces, C)
        S.solidify(ob, max(cfg["thickness_m"], 0.0015), offset=0.0)
        GEN._feature(made, ob, cfg, "cuff", mat, G)
        report.append({"object": ob.name, "top_z_m": round(top, 4), "shaft_r_m": round(sum(shaft) / n, 4),
                       "outer_r_m": round(sum(shaft) / n + T, 4)})
    return made, {"height_m": round(h, 4), "thickness_m": round(T, 4), "pieces": report}
