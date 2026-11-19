"""``garment/3`` ``cuff_gather`` (shorts): bloomer legs gathered into two separate cuffs.

``garment/1`` puts one cuff ring per leg at the hem, sized from the generic leg measure plus the garment's ease; on
full bloomers the two rings overlap at the centre and the puffed shell hangs past them as one skirt hem.
``cuff_gather`` measures each thigh on the body at the cuff height and
  - resizes each cuff band to that thigh (the measured section + ``ease_m``), so the two bands are separate rings;
  - gathers the shell into them: from ``height_m`` above the cuff down to the hem, every piece of the item except the
    bands is drawn towards its own leg's band (a quick balloon profile: full ``height_m`` above the band, tight at
    it), the cloth that hung below the band is taken up into the gather (rows keep their order), and ``pleats``
    vertical gathers of ``pleat_depth_m`` fan out of each band;
  - never moves a vertex across the centre plane, and within ``centre_m`` of it holds the cloth back on the band's
    radius (fading out upwards): the cloth that bridged the two legs at the front and back centre becomes a
    recessed cleft between two lobes;
  - keeps the two bands apart: where they would overlap between the thighs they are pressed flat against the centre
    plane.

  {"height_m": 0.07, "ease_m": 0.004, "pleats": 10, "pleat_depth_m": 0.004, "fullness": 1.0, "centre_m": 0.02}
``fullness`` (0.3..1.5) scales how quickly the cloth balloons above the band (1 = a quarter sine). ``centre_m`` 0
switches the cleft off. Lengths are multiplied by the leg scale of the body.
Character-agnostic: the cuff height comes from the built bands, the thigh section from the body."""
import math

from mathutils import Vector

from garments import generator as GEN

GATHER = {"height_m": 0.07, "ease_m": 0.004, "pleats": 10, "pleat_depth_m": 0.004, "fullness": 1.0, "centre_m": 0.02}
RANGES = {"height_m": (0.01, 0.3), "ease_m": (0.0, 0.03), "pleat_depth_m": (0.0, 0.02), "fullness": (0.3, 1.5),
          "centre_m": (0.0, 0.05)}
SECTORS = 48
TUBE, RING = 8, 32  # garment/1 cuff ring: vertices around the tube, sections round the leg


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.cuff_gather must be true or an object")
    for key in v:
        if key not in GATHER:
            raise ValueError(f"garment {name}.cuff_gather.{key}: unknown field (known: {sorted(GATHER)})")
        if key == "pleats":
            if not isinstance(v[key], int) or isinstance(v[key], bool) or not 0 <= v[key] <= 40:
                raise ValueError(f"garment {name}.cuff_gather.pleats must be an integer in [0, 40]")
        else:
            GEN._number(v[key], f"garment {name}.cuff_gather.{key}", *RANGES[key])


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def thigh_section(body, side, z, band):
    """Centre (x, y) and per-sector radius of one thigh at height z (+1 left, -1 right), measured on the body."""
    pts = [v.co for v in body.data.vertices if abs(v.co.z - z) <= band and v.co.x * side > 0]
    if not pts:
        raise ValueError("cuff_gather: no body vertices at the cuff height")
    cx = 0.5 * (min(p.x for p in pts) + max(p.x for p in pts))
    cy = 0.5 * (min(p.y for p in pts) + max(p.y for p in pts))
    reach = 1.2 * max(max(p.x for p in pts) - cx, max(p.y for p in pts) - cy)
    radii = GEN._section_radii(body, (cx, cy), z, SECTORS, band, reach, reach / 1.2)
    for _ in range(2):  # soften the measured section (the band is a smooth ring)
        radii = [0.25 * radii[k - 1] + 0.5 * radii[k] + 0.25 * radii[(k + 1) % SECTORS] for k in range(SECTORS)]
    return (cx, cy), radii


def _radius(radii, angle):
    f = (angle % (2 * math.pi)) / (2 * math.pi) * SECTORS
    k = int(math.floor(f)) % SECTORS
    t = f - math.floor(f)
    return radii[k] * (1 - t) + radii[(k + 1) % SECTORS] * t


def gather(cfg, mine, body, fit):
    st = dict(GATHER, **(cfg["cuff_gather"] if isinstance(cfg["cuff_gather"], dict) else {}))
    bands = {s: next((o for o in mine if o.name.endswith(f".band.cuff.{s}")), None) for s in ("L", "R")}
    if None in bands.values():
        raise ValueError(f"garment {cfg['name']}.cuff_gather: the item has no cuff bands")
    thick = cfg["thickness_m"]
    ease = float(st["ease_m"]) * fit.leg
    height = float(st["height_m"]) * fit.leg
    pleats, pdepth = int(st["pleats"]), float(st["pleat_depth_m"]) * fit.leg
    full, cw = float(st["fullness"]), float(st["centre_m"]) * fit.leg
    info = {"bands": {}}
    rings = {}
    for s, sx in (("L", 1.0), ("R", -1.0)):
        ob = bands[s]
        mw, inv = ob.matrix_world, ob.matrix_world.inverted()
        pts = [mw @ v.co for v in ob.data.vertices]
        if len(pts) % TUBE:
            raise ValueError(f"{ob.name}: not a garment/1 limb ring")
        # garment/1 _limb_ring: SECTIONS + 1 sections of TUBE vertices, one section after the other round the leg
        # (section j at the angle pi + 2 pi j / SECTIONS; the last repeats the first). garment/2 may have squashed
        # the sections facing the other leg, so the tube's cross-section is read from the outermost section only.
        if len(pts) != (RING + 1) * TUBE:
            raise ValueError(f"{ob.name}: not a garment/1 limb ring")
        mids = [sum(pts[j:j + TUBE], Vector((0.0, 0.0, 0.0))) / TUBE for j in range(0, len(pts), TUBE)]
        old = sum(mids[:RING], Vector((0.0, 0.0, 0.0))) / RING
        major = sum(math.hypot(m.x - old.x, m.y - old.y) for m in mids) / len(mids)
        j0 = RING // 2 if sx > 0 else 0  # the section on the outer side of this leg
        d0 = Vector((sx, 0.0, 0.0))
        section = [((pts[j0 * TUBE + k] - mids[j0]).dot(d0), (pts[j0 * TUBE + k] - mids[j0]).z) for k in range(TUBE)]
        minor = max(abs(z) for _, z in section)
        centre, radii = thigh_section(body, sx, old.z, 0.004 * fit.leg)
        for j in range(RING + 1):
            a = math.pi + 2 * math.pi * j / RING
            d = Vector((math.cos(a), math.sin(a), 0.0))
            r = _radius(radii, a) + ease + thick + minor
            for k, (across, up) in enumerate(section):
                q = Vector((centre[0], centre[1], old.z)) + d * (r + across) + Vector((0.0, 0.0, up))
                q.x = sx * max(q.x * sx, 0.0005)  # the two bands meet at the centre plane, they never overlap
                ob.data.vertices[j * TUBE + k].co = inv @ q
        ob.data.update()
        rings[sx] = (centre, radii, old.z, minor)
        info["bands"][ob.name] = {"centre_m": [round(centre[0], 4), round(centre[1], 4)], "z_m": round(old.z, 4),
                                  "mean_radius_m": round(sum(radii) / SECTORS + ease + thick + minor, 4),
                                  "previous_radius_m": round(major, 4)}
    zc = 0.5 * (rings[1.0][2] + rings[-1.0][2])
    top = zc + height
    cloth = [o for o in mine if o.type == "MESH" and o not in bands.values()]
    main = next(o for o in mine if o.get("ps_garment_part") == "main")
    # the hem height of each leg (from the shell's lowest vertex per sector about the thigh centre)
    hems = {}
    for sx in (1.0, -1.0):
        centre = rings[sx][0]
        low = [None] * SECTORS
        for v in main.data.vertices:
            p = main.matrix_world @ v.co
            if p.z >= top or (p.x >= 0) != (sx > 0):
                continue
            a = math.atan2(p.y - centre[1], p.x - centre[0]) % (2 * math.pi)
            k = int(round(a / (2 * math.pi) * SECTORS)) % SECTORS
            low[k] = p.z if low[k] is None else min(low[k], p.z)
        known = [z for z in low if z is not None]
        if not known:
            raise ValueError(f"garment {cfg['name']}.cuff_gather: the shell does not reach the cuff")
        # the leg's hem is the median over the sectors: cloth sagging below it (the bridge between the legs) is tucked
        # into the band, cloth that ends above it (the inner leg below the crotch) is drawn down to the band
        mid = sorted(known)[len(known) // 2]
        low = [max(z, mid) if z is not None else mid for z in low]
        for _ in range(2):
            low = [0.25 * low[k - 1] + 0.5 * low[k] + 0.25 * low[(k + 1) % SECTORS] for k in range(SECTORS)]
        hems[sx] = (mid, low)
    bottom = min(h[0] for h in hems.values())
    moved, biggest = 0, 0.0
    for ob in cloth:
        mw, inv = ob.matrix_world, ob.matrix_world.inverted()
        gusset = ob.get("ps_garment_part") == "gusset"
        for v in ob.data.vertices:
            p = mw @ v.co
            if p.z >= top:
                continue
            sx = 1.0 if p.x >= 0 else -1.0
            centre, radii, _, minor = rings[sx]
            dx, dy = p.x - centre[0], p.y - centre[1]
            hem = min(_radius(hems[sx][1], math.atan2(dy, dx)), top - 1e-4)
            u = max(0.0, (p.z - hem) / (top - hem))  # 0 at this leg's hem, 1 where the gather ends
            z = zc + u * (top - zc)  # the hem is taken (up or down) to the band
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            target = _radius(radii, a) + ease + thick
            g = math.sin(0.5 * math.pi * min(1.0, u / max(full, 1e-6)) ** 0.75) if u < full else 1.0
            g = max(g, _smooth((u - 0.6) / 0.4))  # no step where the gather ends
            if gusset:  # the crotch piece stays on the legs, behind the gathered shell
                g = 0.0
            if cw > 0.0:  # the cleft: next to the centre plane the cloth stays on the band's radius, fading upwards
                g *= 1.0 - (1.0 - _smooth(abs(p.x) / cw)) * (1.0 - u)
            rn = target + (r - target) * g
            if pleats:
                rn += pdepth * math.cos(pleats * a) * math.sin(math.pi * min(1.0, u * 1.6) ** 0.6) * (1.0 - u)
            rn = max(rn, target) if not gusset else target - thick
            q = Vector((centre[0] + math.cos(a) * rn, centre[1] + math.sin(a) * rn, z))
            # no vertex crosses the centre plane
            q.x = sx * max(q.x * sx, 0.0)
            v.co = inv @ q
            moved += 1
            biggest = max(biggest, (q - p).length)
        ob.data.update()
        GEN._ensure_clearance(body, ob, thick * 0.5)
    lo = min((bands["L"].matrix_world @ v.co).x for v in bands["L"].data.vertices)
    hi = max((bands["R"].matrix_world @ v.co).x for v in bands["R"].data.vertices)
    info.update({"cuff_z_m": round(zc, 4), "gather_top_z_m": round(top, 4), "hem_z_m": round(bottom, 4),
                 "vertices_moved": moved, "max_move_m": round(biggest, 5), "band_gap_m": round(lo - hi, 4)})
    return info
