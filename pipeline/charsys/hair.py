"""Parametric felted-hair generator (charsys hair module, `hair_clumps/1`).

With empty params it reproduces the v6 hair exactly: the same clump layout, random draws (random.Random(seed)) and
call order as build_boy_pilot.build_hair. Every experimental control is a no-op at its default and draws its own
randomness from a second generator, so the v6 draws are never shifted.

Controls (spec.hair.params):
  length            {group: scale}   tuft length along root->tip (groups: crown, centre, top, side, back)
  up_bias, out_bias {group: weight}  turns tuft direction towards +Z / horizontally outwards
  jitter_m          float            random tip offset (irregularity)
  width_jitter      float            random relative width/thickness variation
  asymmetry         float            length x (1 + a) on his left (+X), x (1 - a) on his right
  width_scale, thick_scale float     clump cross-section scale (smaller = gaps between clumps)
  drop_fraction     float            fraction of non-fringe clumps removed (gaps)
  mass_inset_m      float            extra inset of the base hair mass under the clumps
  tip_frac_scale    float            tip thickness scale (<1 = pointier tufts)
  lift_scale        float            how far tips lift off the base (layering)
  spikes            dict             extra projecting tufts: count, length_m, el_deg, az_deg, up, out, width_m, thick_m, tip_frac
  felt              dict             clump noise amp_m/scale, mass noise amp_m/scale
"""
import math
import random

from mathutils import Vector

GROUPS = ("crown", "centre", "top", "side", "back")


def build_hair(C, M, head, B, params=None, seed=11):
    """B is the body module (on_hair, clump, face_y, G and the configured HAIR_C/HAIR_R)."""
    import bmesh
    G = B.G
    P = params or {}
    length = P.get("length", {})
    up_b, out_b = P.get("up_bias", {}), P.get("out_bias", {})
    jit, wjit = float(P.get("jitter_m", 0.0)), float(P.get("width_jitter", 0.0))
    asym = float(P.get("asymmetry", 0.0))
    wsc, tsc = float(P.get("width_scale", 1.0)), float(P.get("thick_scale", 1.0))
    drop = float(P.get("drop_fraction", 0.0))
    inset = float(P.get("mass_inset_m", 0.0))
    tfs = float(P.get("tip_frac_scale", 1.0))
    lift_s = float(P.get("lift_scale", 1.0))
    felt = P.get("felt", {})
    R = random.Random(seed)
    R2 = random.Random(seed + 7919)  # experimental controls only
    on_hair, clump, face_y = B.on_hair, B.clump, B.face_y
    HAIR_C, HAIR_R = B.HAIR_C, B.HAIR_R

    mass = G.uv_sphere("hair_mass", HAIR_C + Vector((0, 0.006, -0.006)), 1.0, C, 48, 24,
                       tuple(HAIR_R - Vector((0.022 + inset, 0.022 + inset, 0.022 + inset))))
    bm = bmesh.new()
    bm.from_mesh(mass.data)
    kill = [f for f in bm.faces if f.calc_center_median().y < -0.05 and f.calc_center_median().z < 0.955]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(mass.data)
    bm.free()
    G.displace_noise(mass, float(felt.get("mass_amp_m", 0.008)), float(felt.get("mass_scale", 0.035)), subdiv=1)
    clumps = []
    stats = {"clumps": 0, "dropped": 0, "spikes": 0}

    def shape(group, root, mid, tip, n):
        s = float(length.get(group, 1.0))
        if asym:
            s *= (1 + asym) if root.x > 0 else (1 - asym)
        u, o = float(up_b.get(group, 0.0)), float(out_b.get(group, 0.0))
        if s == 1.0 and not u and not o and not jit:
            return mid, tip
        d = tip - root
        L = d.length
        dirn = d.normalized()
        if u or o:
            h = Vector((n.x, n.y, 0.0))
            h = h.normalized() if h.length > 1e-6 else Vector((0, 0, 0))
            dirn = (dirn + Vector((0, 0, 1)) * u + h * o).normalized()
        off = mid - (root + tip) / 2
        new_tip = root + dirn * (L * s)
        if jit:
            new_tip = new_tip + Vector((R2.uniform(-1, 1), R2.uniform(-1, 1), R2.uniform(-1, 1))) * jit
        return (root + new_tip) / 2 + off * s, new_tip

    def add(name, root, mid, tip, width, thick, n, tip_frac=0.28, group=None):
        if group is not None:
            mid, tip = shape(group, root, mid, tip, n)
            if drop and R2.random() < drop:
                stats["dropped"] += 1
                return
        width, thick = width * wsc, thick * tsc
        if wjit:
            k = 1 + R2.uniform(-wjit, wjit)
            width, thick = width * k, thick * k
        clumps.append(clump(name, C, root, mid, tip, width, thick, n, tip_frac=tip_frac * tfs))
        stats["clumps"] += 1

    # Fringe (as v6): 7 irregular chunks from the hairline down to the brows.
    xs = [-0.125, -0.085, -0.044, -0.004, 0.038, 0.080, 0.122]
    tips = [0.838, 0.826, 0.814, 0.802, 0.818, 0.828, 0.842]
    for k, (xt, zt) in enumerate(zip(xs, tips)):
        xt += R.uniform(-0.006, 0.006)
        zt += R.uniform(-0.006, 0.006)
        az = math.degrees(math.atan2(xt, 0.16)) * 1.25
        root, n = on_hair(az, 22 + R.uniform(-4, 4), 0.004)
        yt = face_y(head, xt, zt) - 0.020
        tip = Vector((xt * 1.04, yt, zt))
        mid = (root + tip) / 2 + n * 0.022 + Vector((0, -0.010, 0.0))
        add(f"hair.fringe.{k}", root, mid, tip, R.uniform(0.060, 0.072), R.uniform(0.036, 0.044), n, tip_frac=0.32)
    # Crown: big upward tufts alternating with smaller outward ones.
    for k in range(8):
        az = -160 + 320 * (k + R.uniform(0.25, 0.75)) / 8
        big = k % 2 == 0
        root, n = on_hair(az, (72 if big else 60) + R.uniform(-5, 5), -0.006)
        dirv = (n * (0.45 if big else 0.8) + Vector((0, 0, 1)) * (0.9 if big else 0.55)).normalized()
        L = R.uniform(0.045, 0.065) if big else R.uniform(0.035, 0.050)
        tip = root + dirv * L + Vector((R.uniform(-0.02, 0.02), R.uniform(-0.02, 0.02), 0))
        mid = root + dirv * L * 0.5 + n * 0.008
        add(f"hair.crown.{k}", root, mid, tip, R.uniform(0.050, 0.066), R.uniform(0.038, 0.048), n, tip_frac=0.30,
            group="crown")
    # Centre of the crown.
    for k in range(7):
        az = -180 + 360 * (k + R.uniform(0.2, 0.8)) / 7
        root, n = on_hair(az + 180, 86, -0.004)
        tip, tn = on_hair(az + R.uniform(-15, 15), 62 + R.uniform(-6, 6), 0.035 * lift_s)
        mid = (root + tip) / 2 + (n + tn).normalized() * 0.035
        add(f"hair.centre.{k}", root, mid, tip, R.uniform(0.066, 0.080), R.uniform(0.046, 0.056), (n + tn).normalized(),
            tip_frac=0.35, group="centre")
    # Top layer.
    for k in range(16):
        az = -180 + 360 * (k + R.uniform(0.2, 0.8)) / 16
        root, n = on_hair(az, 70 + R.uniform(-8, 8), -0.004)
        tip, tn = on_hair(az + R.uniform(-12, 12), 46 + R.uniform(-8, 6), 0.035 * lift_s)
        mid = (root + tip) / 2 + (n + tn).normalized() * 0.030
        add(f"hair.top.{k}", root, mid, tip, R.uniform(0.064, 0.078), R.uniform(0.044, 0.054), (n + tn).normalized(),
            tip_frac=0.35, group="top")
    # Sides: clusters flaring outwards to the measured width.
    for sx in (1, -1):
        for row, (el0, el1, cnt, reach, lift) in enumerate(((48, 22, 5, (0.170, 0.184), 0.030), (28, 2, 5, (0.168, 0.180), 0.028),
                                                            (10, -14, 4, (0.160, 0.172), 0.022))):
            for k in range(cnt):
                az = sx * (48 + 80 * (k + R.uniform(0.2, 0.8)) / cnt)
                root, n = on_hair(az, el0 + R.uniform(-5, 5), -0.004)
                tip, tn = on_hair(az + sx * R.uniform(-4, 12), el1 + R.uniform(-6, 6), lift * lift_s)
                tip.x = sx * max(abs(tip.x), R.uniform(*reach))
                mid = (root + tip) / 2 + n * 0.030
                add(f"hair.side{'L' if sx > 0 else 'R'}{row}.{k}", root, mid, tip, R.uniform(0.062, 0.076),
                    R.uniform(0.042, 0.052), n, tip_frac=0.33, group="side")
    # Back: layers of lumpy clumps to the nape.
    for row, (el0, el1, cnt, lift) in enumerate(((60, 30, 9, 0.032), (34, 4, 10, 0.030), (8, -30, 10, 0.024), (-12, -58, 9, 0.018))):
        for k in range(cnt):
            az = 180 + (-100 + 200 * (k + R.uniform(0.2, 0.8)) / cnt)
            root, n = on_hair(az, el0 + R.uniform(-5, 5), -0.004)
            tip, tn = on_hair(az + R.uniform(-10, 10), el1 + R.uniform(-6, 4), lift * lift_s)
            mid = (root + tip) / 2 + n * 0.030
            add(f"hair.back{row}.{k}", root, mid, tip, R.uniform(0.064, 0.078), R.uniform(0.044, 0.054), n,
                tip_frac=0.33, group="back")
    # Experimental: extra projecting tufts (upward / outward spikes with gaps between them).
    sp = P.get("spikes") or {}
    for k in range(int(sp.get("count", 0))):
        a0, a1 = sp.get("az_deg", [-180, 180])
        az = a0 + (a1 - a0) * (k + R2.uniform(0.15, 0.85)) / max(1, int(sp["count"]))
        el = R2.uniform(*sp.get("el_deg", [35, 75]))
        root, n = on_hair(az, el, -0.006)
        h = Vector((n.x, n.y, 0.0))
        h = h.normalized() if h.length > 1e-6 else Vector((0, 0, 0))
        dirv = (n + Vector((0, 0, 1)) * float(sp.get("up", 0.6)) + h * float(sp.get("out", 0.3))).normalized()
        L = R2.uniform(*sp.get("length_m", [0.06, 0.09]))
        tip = root + dirv * L
        mid = root + dirv * L * 0.5 + n * 0.006
        clumps.append(clump(f"hair.spike.{k}", C, root, mid, tip, R2.uniform(*sp.get("width_m", [0.034, 0.048])),
                            R2.uniform(*sp.get("thick_m", [0.028, 0.038])), n, tip_frac=float(sp.get("tip_frac", 0.14))))
        stats["spikes"] += 1
    for c in clumps:
        G.displace_noise(c, float(felt.get("amp_m", 0.005)), float(felt.get("scale", 0.016)), subdiv=1)
    hair = G.join(clumps, "hair_clumps")
    # A few thin stray strands on top (as v6).
    strays = []
    for k, (az, el) in enumerate(((-30, 82), (40, 78), (150, 76))):
        root, n = on_hair(az, el, 0.02)
        tip = root + (n * 0.6 + Vector((R.uniform(-0.4, 0.4), R.uniform(-0.4, 0.4), 0.6))).normalized() * 0.05
        mid = (root + tip) / 2 + Vector((R.uniform(-0.015, 0.015), 0, 0.012))
        strays.append(G.tube(f"hair_stray.{k}", G.bezier(root, mid, tip, 8), [0.0022] * 8, [0.0022] * 8, C, seg=8))
    stray = G.join(strays, "hair_strays")
    for o in (mass, hair, stray):
        G.assign(o, M["hair"])
    return [mass, hair, stray], stats


# ============================================================================== hair_clumps/2
# Lock layout derived from the measured v6 mismatch (docs/evaluation/hair_experiments/HAIR_EXPERIMENTS.md, CP-2):
# the v6 hair is too full, never too small; the crown is a broad dome where the references show a few narrow
# tufts (side view, top 8% of the figure: +74..116% too wide), and the band 8-12% below the top is ~20% too wide.
# So: the dark base mass stays (no scalp), the locks lie close to it (low lift), and only a few blunt crown tufts
# reach the top. 30-40 larger locks in families; each lock may split into a second, smaller tip (felted grouping).
FAMILIES_V2 = {  # name: count, az range (deg), root el, tip el, tip lift (m), width, thick, tip_frac, split
    "crown":   dict(count=5, az=(-150, 150), el_root=(78, 86), up=1.0, out=0.35, length=(0.050, 0.064),
                    width=(0.058, 0.068), thick=(0.044, 0.052), tip_frac=0.40, split=True),
    "top":     dict(count=6, az=(-180, 180), el_root=(76, 84), el_tip=(48, 56), lift=0.012,
                    width=(0.092, 0.104), thick=(0.052, 0.060), tip_frac=0.38, split=False),
    "side":    dict(count=4, az=(52, 132), el_root=(50, 56), el_tip=(-12, 0), lift=0.014,
                    width=(0.086, 0.098), thick=(0.050, 0.058), tip_frac=0.36, split=True, flick=0.010, mirror=True),
    "back_hi": dict(count=6, az=(130, 230), el_root=(58, 66), el_tip=(14, 24), lift=0.016,
                    width=(0.092, 0.104), thick=(0.052, 0.060), tip_frac=0.36, split=True),
    "back_lo": dict(count=6, az=(125, 235), el_root=(18, 26), el_tip=(-50, -40), lift=0.012,
                    width=(0.088, 0.100), thick=(0.050, 0.058), tip_frac=0.34, split=True, flick=0.012),
}


def scalp_cap(C, head, cfg):
    """Dark cap = the head surface above a hairline, offset outwards along its normals. The head is wider than the
    base mass at every height (measured: 0.155-0.160 m vs 0.145-0.153 m half-width), so without it skin shows
    wherever locks lie close. cfg: offset (m), hairline [[azimuth deg from front, min z], ...] (|azimuth|)."""
    import bisect
    import bmesh
    import bpy
    off = float(cfg.get("offset", 0.006))
    hl = sorted(cfg.get("hairline", [[0, 0.93], [60, 0.86], [90, 0.80], [180, 0.73]]))
    azs, zs = [a for a, _ in hl], [z for _, z in hl]

    def zmin(a):
        i = bisect.bisect_left(azs, a)
        if i <= 0:
            return zs[0]
        if i >= len(azs):
            return zs[-1]
        t = (a - azs[i - 1]) / (azs[i] - azs[i - 1])
        return zs[i - 1] + t * (zs[i] - zs[i - 1])
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.transform(head.matrix_world)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        a = abs(math.degrees(math.atan2(c.x, -c.y)))
        if c.z < zmin(a) or (c.y < -0.05 and c.z < 0.955):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * off
    me = bpy.data.meshes.new("hair_cap")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("hair_cap", me)
    C.objects.link(ob)
    return ob


def build_hair_v2(C, M, head, B, params=None, seed=11):
    import bmesh
    G = B.G
    P = params or {}
    R = random.Random(seed)
    on_hair, clump, face_y = B.on_hair, B.clump, B.face_y
    HAIR_C, HAIR_R = B.HAIR_C, B.HAIR_R
    fam = {k: dict(v) for k, v in FAMILIES_V2.items()}
    for k, v in P.get("families", {}).items():  # override or add families (count 0 disables one)
        fam[k] = dict(fam.get(k, {}), **v)
    noise = P.get("lock_noise", [0.006, 0.018])
    ms = P.get("mass_scale", [1.0, 1.0, 0.97])
    inset = 0.022
    mass = G.uv_sphere("hair_mass", HAIR_C + Vector((0, 0.006, -0.010)), 1.0, C, 48, 24,
                       tuple((HAIR_R[i] - inset) * ms[i] for i in range(3)))
    bm = bmesh.new()
    bm.from_mesh(mass.data)
    kill = [f for f in bm.faces if f.calc_center_median().y < -0.05 and f.calc_center_median().z < 0.955]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(mass.data)
    bm.free()
    G.displace_noise(mass, 0.008, 0.035, subdiv=1)
    if P.get("scalp_cap"):
        mass = G.join([mass, scalp_cap(C, head, P["scalp_cap"])], "hair_mass")
    locks, parts = [], []

    def lock(name, root, mid, tip, width, thick, n, tip_frac, split):
        objs = [clump(name, C, root, mid, tip, width, thick, n, tip_frac=tip_frac)]
        if split:  # a smaller second tip leaving the lock at ~45%: grouped felted strands, notch at the tip
            a = root + (tip - root) * 0.45
            axis = n.normalized()
            ang = math.radians(R.choice((-1, 1)) * R.uniform(14, 22))
            d = (tip - a)
            d2 = d * math.cos(ang) + axis.cross(d) * math.sin(ang) + axis * axis.dot(d) * (1 - math.cos(ang))
            t2 = a + d2 * R.uniform(0.80, 0.92)
            objs.append(clump(name + ".b", C, a, (a + t2) / 2 + n * 0.006, t2, width * 0.55, thick * 0.65, n,
                              tip_frac=tip_frac))
        locks.append(name)
        parts.extend(objs)

    # Fringe: the v6 fringe (its front-view fit is already good), 7 locks.
    xs = [-0.125, -0.085, -0.044, -0.004, 0.038, 0.080, 0.122]
    tips = [0.838, 0.826, 0.814, 0.802, 0.818, 0.828, 0.842]
    for k, (xt, zt) in enumerate(zip(xs, tips)):
        xt += R.uniform(-0.006, 0.006)
        zt += R.uniform(-0.006, 0.006)
        az = math.degrees(math.atan2(xt, 0.16)) * 1.25
        root, n = on_hair(az, 22 + R.uniform(-4, 4), 0.004)
        tip = Vector((xt * 1.04, face_y(head, xt, zt) - 0.020, zt))
        mid = (root + tip) / 2 + n * 0.022 + Vector((0, -0.010, 0.0))
        lock(f"hair.fringe.{k}", root, mid, tip, R.uniform(0.060, 0.072), R.uniform(0.036, 0.044), n, 0.32, False)
    # Crown tufts: few, blunt, mostly upward, near the top centre.
    f = fam["crown"]
    for k in range(f["count"]):
        az = f["az"][0] + (f["az"][1] - f["az"][0]) * (k + R.uniform(0.3, 0.7)) / f["count"]
        root, n = on_hair(az, R.uniform(*f["el_root"]), -0.008)
        h = Vector((n.x, n.y, 0))
        h = h.normalized() if h.length > 1e-6 else h
        dirv = (Vector((0, 0, 1)) * f["up"] + h * f["out"]).normalized()
        L = R.uniform(*f["length"])
        tip = root + dirv * L
        mid = root + dirv * L * 0.5 + h * 0.008
        lock(f"hair.crown.{k}", root, mid, tip, R.uniform(*f["width"]), R.uniform(*f["thick"]), n, f["tip_frac"], f["split"])
    # Families of locks lying close over the base mass.
    for name in [k for k in fam if k != "crown"]:
        f = fam[name]
        sides = (1, -1) if f.get("mirror") else (1,)
        for sx in sides:
            for k in range(f["count"]):
                az = sx * (f["az"][0] + (f["az"][1] - f["az"][0]) * (k + R.uniform(0.25, 0.75)) / f["count"])
                root, n = on_hair(az, R.uniform(*f["el_root"]), -0.006)
                tip, tn = on_hair(az + R.uniform(-8, 8), R.uniform(*f["el_tip"]), f["lift"])
                if f.get("flick"):
                    hh = Vector((tn.x, tn.y, 0))
                    tip = tip + (hh.normalized() if hh.length > 1e-6 else hh) * f["flick"]
                nn = (n + tn).normalized()
                mid = (root + tip) / 2 + nn * (f["lift"] + f.get("bulge", 0.010))
                lock(f"hair.{name}{'L' if sx > 0 else 'R'}.{k}" if f.get("mirror") else f"hair.{name}.{k}", root, mid, tip,
                     R.uniform(*f["width"]), R.uniform(*f["thick"]), nn, f["tip_frac"], f["split"])
    for c in parts:
        G.displace_noise(c, noise[0], noise[1], subdiv=1)
    hair = G.join(parts, "hair_clumps")
    strays = []
    for k, (az, el) in enumerate(((-30, 82), (40, 78), (150, 76))):
        root, n = on_hair(az, el, 0.0)
        tip = root + (n * 0.6 + Vector((R.uniform(-0.4, 0.4), R.uniform(-0.4, 0.4), 0.6))).normalized() * 0.04
        mid = (root + tip) / 2 + Vector((R.uniform(-0.012, 0.012), 0, 0.010))
        strays.append(G.tube(f"hair_stray.{k}", G.bezier(root, mid, tip, 8), [0.0022] * 8, [0.0022] * 8, C, seg=8))
    stray = G.join(strays, "hair_strays")
    for o in (mass, hair, stray):
        G.assign(o, M["hair"])
    return [mass, hair, stray], {"generator": "hair_clumps/2", "locks": len(locks), "clump_parts": len(parts)}


def build(C, M, head, B, hair_spec):
    """Dispatches on spec.hair.generator (hair_clumps/1 = v6 layout, hair_clumps/2 = lock families)."""
    gen = hair_spec.get("generator", "hair_clumps/1")
    seed = int(hair_spec.get("seed", 11))
    if gen == "hair_clumps/1":
        return build_hair(C, M, head, B, hair_spec.get("params"), seed=seed)
    if gen == "hair_clumps/2":
        return build_hair_v2(C, M, head, B, hair_spec.get("params"), seed=seed)
    raise ValueError(f"unknown hair generator {gen}")
