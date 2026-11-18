"""Hair round 4 (`groom/3`, T-091): few large, overlapping felt masses.

The references (boy B04/B05 + originals, girl G01/G02/G04-G06 + ref_30) show a few large felted masses that overlap
like petals or swept sections, with deep channels between them and a clear taper to the tip. Round 3 (groom/2) built
the same hairstyles from many thin, flat clumps. groom/3 adds the primitive for the reference construction and keeps
everything else from groom/2 (groom_hybrid.py, used read-only as a library; groom/1 and groom/2 builds are unchanged).

Character-independent: every shape, count, size and attachment point is spec data (spec.hair); no character names.

spec.hair (generator "groom/3"): every groom/2 structure type (see groom_hybrid.py) plus
  masses      large felt masses with a round, deep section (depth = thickness / width, default 0.8), so two
              neighbours meet in a deep channel; a root sunk into the base, a held full width over `hold` of the
              length and a pointed taper; later layers sit over earlier ones (layer x layer_lift_m), so the masses
              overlap like petals:
              {"type": "masses", "name", "layer_lift_m" (default 0.008), "root_sink_m" (0.006), "seg" (18),
               "step_m" (0.004), "grooves" (1 = one soft central furrow), "groove_depth" (0.16), "irregularity",
               "keepout" (overrides the hair keep-out),
               "items": [{"root": [az, el], "tip": [az, el], ...per-mass keys}]   explicit masses, and/or
               "rows":  [{"count", "az": [a0, a1] | "az_list", "el": [lo, hi], "flow": "away"|"down"|"toward",
                          "pole": {"az", "el"}, "len_deg": [lo, hi], "jitter_deg", ...per-mass keys}]}
              per-mass keys: "width": m | [lo, hi], "depth" (0.8), "lift": [root, peak, tip] (m), "lift_peak" (0.5),
              "hold" (0.45), "taper_power" (1.6), "flick_m" (outward flick of the last third), "curl_deg"
              (sideways bend), "layer" (int, default 0), "sweep" (0..1: bends the path out along a great circle
              through the tip's side, for swept fringe sections), "root_width" (fraction of width at the root, 0.7)
  scrunchie   a gathered fabric band around a bun (the girl's G04 scrunchie): {"type": "scrunchie", "name", "bun",
              "height_frac", "radius_scale", "tube" (m), "gathers" (count), "gather_depth" (0..0.6), "width_scale",
              "ruffle" (0..0.3), "material" (default slot "hair_band")}; follows the bun's chain like a tie.
  fibres.directional (T-091 experiment, one flag, default off): {"enabled": bool, "strength": 0..2} combs the shared
              surface fibres of every mass along its centre line (the mass tangent is stored on the mesh as the
              "ps_comb" point attribute; other structures carry none and keep the shared fibre look).
The face keep-out, fibres, dynamics and binding work as in groom/2; masses get one spring chain per mass like clumps."""
import json
import math
import random

try:
    from mathutils import Matrix, Vector
except ImportError:  # plain Python: spec validation only
    Matrix = Vector = None

import groom as G1  # groom/1 as a library (read-only use)
import groom_hybrid as H  # groom/2 as a library (read-only use)

GENERATOR_VERSIONS = ("groom/3",)
GENERATOR = "groom/3"
R4_TYPES = {"masses", "scrunchie"}
COMB_ATTR = "ps_comb"


def _rr(R, v):
    return H.rr(R, v)


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------------------- masses
def mass_profile(n, hold, taper_power, root_width):
    """Width factor along a mass: root_width at the root, full width over [~0.15, hold], then a pointed taper."""
    out = []
    for i in range(n):
        s = i / (n - 1)
        if s < hold:
            f = root_width + (1 - root_width) * _smooth(s / max(0.05, min(hold, 0.3)))
        else:
            t = (s - hold) / max(1e-6, 1 - hold)
            f = max(0.0, 1 - t ** taper_power) ** 0.7
        out.append(f)
    return out


def _expand(st, R):
    """Explicit masses from st.items and st.rows: [(root_dir, tip_dir, params)]."""
    out = []
    for it in st.get("items") or []:
        d0 = G1.Scalp.direction(float(it["root"][0]), float(it["root"][1]))
        d1 = G1.Scalp.direction(float(it["tip"][0]), float(it["tip"][1]))
        out.append((d0, d1, it))
    for row in st.get("rows") or []:
        cnt = int(row["count"])
        a0, a1 = [float(x) for x in row.get("az", [0, 0])]
        pole = row.get("pole", {"az": 180, "el": 70})
        pdir = G1.Scalp.direction(float(pole["az"]), float(pole["el"]))
        azl = row.get("az_list")
        flow = row.get("flow", "away")
        for c in range(cnt):
            if azl:
                az = float(azl[c % len(azl)]) + R.uniform(-1.5, 1.5)
            else:
                az = a0 + (a1 - a0) * ((c + R.uniform(0.3, 0.7)) / cnt) if cnt > 1 else (a0 + a1) / 2
            d0 = G1.Scalp.direction(az, _rr(R, row["el"]))
            L = math.radians(_rr(R, row["len_deg"]))
            if flow == "down":
                tgt = Vector((d0.x, d0.y, -1.6)).normalized()
            elif flow == "toward":
                tgt = pdir
            else:
                tgt = H._rotate_towards(d0, -pdir, 3.0) if (d0 - pdir).length > 1e-4 else d0.orthogonal()
            d1 = H._rotate_towards(d0, tgt, L)
            jit = math.radians(R.uniform(-1, 1) * float(row.get("jitter_deg", 6)))
            d1 = (Matrix.Rotation(jit, 3, d0) @ d1).normalized()
            out.append((d0, d1, row))
    return out


def _keep_dir(d, keep, margin):
    fa, fe = H.az_el(d)
    lim = float(keep["el_min"]) + margin
    if abs(fa) < float(keep["az"]) + margin and fe < lim:
        return G1.Scalp.direction(fa, lim), True
    return d, False


def build_masses(st, ctx, R):
    sc = ctx["scalp"]
    bucket = G1.MeshBucket()
    bucket.recalc = True
    bucket.comb = []
    seg = int(st.get("seg", 18))
    step = float(st.get("step_m", 0.004))
    grooves = int(st.get("grooves", 1))
    gdepth = float(st.get("groove_depth", 0.16))
    irr = float(st.get("irregularity", 0.05))
    ll = float(st.get("layer_lift_m", 0.008))
    sink = float(st.get("root_sink_m", 0.006))
    keep = st.get("keepout", ctx.get("keepout"))
    made = clamped = 0
    foot, depths = [], []
    for d0, d1, p in _expand(st, R):
        width = _rr(R, p.get("width", 0.08))
        depth = float(p.get("depth", 0.8))
        lift = [float(x) for x in p.get("lift", [0.0, 0.02, 0.01])]
        if len(lift) == 2:
            lift = [lift[0], (lift[0] + lift[1]) / 2, lift[1]]
        pk = float(p.get("lift_peak", 0.5))
        hold = float(p.get("hold", 0.45))
        tpow = float(p.get("taper_power", 1.6))
        flick = float(p.get("flick_m", 0.0))
        curl = math.radians(R.uniform(-1, 1) * float(p.get("curl_deg", 0.0)))
        layer = int(p.get("layer", 0))
        sweep = float(p.get("sweep", 0.0))
        rw = float(p.get("root_width", 0.7))
        ang = math.acos(max(-1.0, min(1.0, d0.dot(d1))))
        arc = sc.radii.length / math.sqrt(3) * max(ang, 0.05) + abs(lift[2] - lift[0])
        n = max(8, int(arc / step))
        side = d0.cross(d1)
        side = side.normalized() if side.length > 1e-6 else d0.orthogonal().normalized()
        path, ups, hit = [], [], False
        for i in range(n):
            s = i / (n - 1)
            d = G1.slerp(d0, d1, s)
            if sweep:  # swept section: the middle of the path bows off the great circle (sign of sweep = side)
                d = (d - side * (sweep * 0.25 * math.sin(math.pi * s))).normalized()
            if curl:
                d = (Matrix.Rotation(curl * s * s, 3, d0) @ d).normalized()
            if keep:
                d, c = _keep_dir(d, keep, float(keep.get("margin_deg", 2.0)))
                hit = hit or c
            if s <= pk:
                h = lift[0] + (lift[1] - lift[0]) * math.sin(0.5 * math.pi * s / pk)
            else:
                h = lift[1] + (lift[2] - lift[1]) * _smooth((s - pk) / (1 - pk))
            h += layer * ll * min(1.0, s / 0.2) - sink * (1 - s) ** 3
            h += flick * max(0.0, (s - 0.66) / 0.34) ** 2
            pt, nrm = sc.at_dir(d, h)
            path.append(pt)
            ups.append(nrm)
        clamped += hit
        # stable section frame: the width lies along `side` (across the flow), the depth along side x tangent, turned
        # to the scalp normal's side. The scalp normal alone flips the section where a mass rises steeply (standing
        # crown petals), which twisted it into a rosette.
        tang = [(path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized() for i in range(n)]
        frame_ups = []
        for i in range(n):
            nn = side.cross(tang[i])
            nn = nn.normalized() if nn.length > 1e-6 else ups[i]
            frame_ups.append(nn if nn.dot(ups[i]) >= 0 else -nn)
        ups = frame_ups
        prof = mass_profile(n, hold, tpow, rw)
        widths = [max(0.003, width * f) for f in prof]
        thicks = [max(0.0025, width * depth * (0.5 + 0.5 * f) * f ** 0.5) for f in prof]
        vs, fs = H.clump_mesh(path, ups, widths, thicks, seg, R, grooves, gdepth, irr)
        v_start = len(bucket.verts)
        bucket.add(vs, fs)
        for i in range(n):
            bucket.comb += [tang[i]] * seg
        bucket.comb += [tang[0], tang[-1]]
        if ctx.get("dynamics") is not None:
            k0 = int(0.3 * (n - 1))
            ctx["dynamics"].append({"kind": "lock", "structure": st.get("name", st["type"]), "index": made,
                                    "line": path[k0:], "verts": (v_start, len(bucket.verts))})
        L = sum((q - a).length for a, q in zip(path, path[1:]))
        foot.append(L * width)
        depths.append(depth)
        made += 1
    return bucket, {"masses": made, "keepout_clamped": clamped,
                    "mean_footprint_cm2": round(1e4 * sum(foot) / max(1, made), 1),
                    "mean_depth": round(sum(depths) / max(1, made), 3)}


# ------------------------------------------------------------------------------------------------------- scrunchie
def build_scrunchie(st, ctx, R):
    bf = ctx["buns"][int(st.get("bun", 0))]
    ax = bf["axis"].normalized()
    u = ax.orthogonal().normalized()
    v = ax.cross(u)
    hf = float(st.get("height_frac", 0.1))
    rho = bf["radius"] * math.sqrt(max(0.0, 1 - 0.82 * (2 * hf - 1) ** 2)) * float(st.get("radius_scale", 1.0))
    c = bf["base"] + ax * (bf["height"] * hf)
    tube = float(st.get("tube", 0.011))
    ng = int(st.get("gathers", 9))
    gd = float(st.get("gather_depth", 0.35))
    ws = float(st.get("width_scale", 1.25))
    ruf = float(st.get("ruffle", 0.12))
    nu, seg = ng * 12, 16
    ph = [R.uniform(0, 6.283) for _ in range(4)]
    verts, faces = [], []
    for i in range(nu):
        th = 2 * math.pi * i / nu
        radial = u * math.cos(th) + v * math.sin(th)
        g = 0.5 + 0.5 * math.cos(ng * th + ph[0])
        r = tube * (1 - gd + gd * 2 * g ** 0.7) * (1 + 0.08 * math.sin(3 * th + ph[1]))
        ctr = c + radial * (rho + r * 0.6)
        for k in range(seg):
            phi = 2 * math.pi * k / seg
            rf = 1 + ruf * math.sin(5 * phi + 2.3 * ng * th + ph[2]) * g
            verts.append(ctr + (radial * math.cos(phi) + ax * (math.sin(phi) * ws)) * r * rf)
    for i in range(nu):
        for k in range(seg):
            a, b = i * seg + k, i * seg + (k + 1) % seg
            a2, b2 = ((i + 1) % nu) * seg + k, ((i + 1) % nu) * seg + (k + 1) % seg
            faces.append((a, b, b2, a2))
    bucket = G1.MeshBucket()
    bucket.recalc = True
    bucket.add(verts, faces)
    return bucket, {"radius_m": round(rho, 4), "gathers": ng}


BUILDERS = dict(H.BUILDERS, masses=build_masses, scrunchie=build_scrunchie)
TYPES = H.TYPES | R4_TYPES
ACCESSORY_TYPES = H.ACCESSORY_TYPES | {"scrunchie"}


# ------------------------------------------------------------------------------------------------------ validation
def validate(hair_spec):
    """groom/2 rules for groom/2 types (dynamics with masses as clumps), plus the masses/scrunchie primitives and the
    directional-fibre flag."""
    sts = hair_spec.get("structures")
    if not isinstance(sts, list) or not sts:
        return ["hair.structures must be a non-empty list"]
    errs = []
    as_v2 = [dict(s, type="clumps", rows=[{"count": 1, "az": [0, 0], "el": [0, 0], "len_deg": [1, 1], "width": 0.01,
                                           "thick": 0.01}]) if s.get("type") == "masses" else
             dict(s, type="tie") if s.get("type") == "scrunchie" else s for s in sts]
    errs += H.validate(dict(hair_spec, structures=as_v2))
    keep = hair_spec.get("face_keepout")
    nb = sum(len(x.get("buns", [])) for x in sts if x.get("type") == "bun")
    for i, s in enumerate(sts):
        t = s.get("type")
        if t == "masses":
            items, rows = s.get("items") or [], s.get("rows") or []
            if not items and not rows:
                errs.append(f"hair.structures[{i}] (masses) needs 'items' and/or 'rows'")
            for j, it in enumerate(items):
                for k in ("root", "tip"):
                    if not (isinstance(it.get(k), list) and len(it[k]) == 2):
                        errs.append(f"hair.structures[{i}].items[{j}] (masses) needs '{k}': [az, el]")
                if keep and "root" in it and abs(float(it["root"][0])) < float(keep["az"]) \
                        and float(it["root"][1]) < float(keep["el_min"]):
                    errs.append(f"hair.structures[{i}].items[{j}] is rooted inside the face keep-out")
            for j, row in enumerate(rows):
                for k in ("count", "el", "len_deg"):
                    if k not in row:
                        errs.append(f"hair.structures[{i}].rows[{j}] (masses) needs '{k}'")
                if row.get("flow", "away") not in ("away", "down", "toward"):
                    errs.append(f"hair.structures[{i}].rows[{j}] flow must be away, down or toward")
            for j, p in enumerate(items + rows):
                if not 0.2 <= float(p.get("depth", 0.8)) <= 1.5:
                    errs.append(f"hair.structures[{i}] mass {j}: depth must be within 0.2..1.5")
                if not 0.05 <= float(p.get("lift_peak", 0.5)) <= 0.95:
                    errs.append(f"hair.structures[{i}] mass {j}: lift_peak must be within 0.05..0.95")
                if not 0.0 <= float(p.get("hold", 0.45)) <= 0.9:
                    errs.append(f"hair.structures[{i}] mass {j}: hold must be within 0..0.9")
        elif t == "scrunchie":
            if int(s.get("bun", 0)) >= nb:
                errs.append(f"hair.structures[{i}] (scrunchie) refers to bun {s.get('bun', 0)}, but only {nb} bun(s) exist")
            if not 0.0 <= float(s.get("gather_depth", 0.35)) <= 0.6:
                errs.append(f"hair.structures[{i}] (scrunchie) gather_depth must be within 0..0.6")
    dr = (hair_spec.get("fibres") or {}).get("directional")
    if dr is not None:
        if not isinstance(dr, dict) or not isinstance(dr.get("enabled"), bool):
            errs.append("hair.fibres.directional must be {\"enabled\": bool, \"strength\": 0..2}")
        elif not 0.0 <= float(dr.get("strength", 0.8)) <= 2.0:
            errs.append("hair.fibres.directional.strength must be within 0..2")
    return errs


# ------------------------------------------------------------------------------------------------- fibre combing
COMB_GROUP = "PS Fibre Comb/1"


def comb_fibres(fo, surface, strength):
    """T-091 experiment: bend each fibre along the mass direction stored on its surface (point attribute ps_comb,
    sampled at the nearest surface point); fibre offset = comb x distance along the fibre x strength. Surfaces without
    the attribute sample zero, so their fibres are unchanged."""
    import bpy
    g = bpy.data.node_groups.get(COMB_GROUP)
    if g is None:
        g = bpy.data.node_groups.new(COMB_GROUP, "GeometryNodeTree")
        g.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        g.interface.new_socket(name="Surface", in_out="INPUT", socket_type="NodeSocketObject")
        g.interface.new_socket(name="Strength", in_out="INPUT", socket_type="NodeSocketFloat")
        g.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        n, ln = g.nodes, g.links
        gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
        info = n.new("GeometryNodeObjectInfo")
        info.transform_space = "ORIGINAL"
        ln.new(gi.outputs["Surface"], info.inputs["Object"])
        attr = n.new("GeometryNodeInputNamedAttribute")
        attr.data_type = "FLOAT_VECTOR"
        attr.inputs["Name"].default_value = COMB_ATTR
        samp = n.new("GeometryNodeSampleNearestSurface")
        samp.data_type = "FLOAT_VECTOR"
        ln.new(info.outputs["Geometry"], samp.inputs["Mesh"])
        ln.new(attr.outputs["Attribute"], samp.inputs["Value"])
        pos = n.new("GeometryNodeInputPosition")
        ln.new(pos.outputs["Position"], samp.inputs["Sample Position"])
        par = n.new("GeometryNodeSplineParameter")
        k = n.new("ShaderNodeMath")
        k.operation = "MULTIPLY"
        ln.new(par.outputs["Length"], k.inputs[0])
        ln.new(gi.outputs["Strength"], k.inputs[1])
        sc = n.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        ln.new(samp.outputs["Value"], sc.inputs[0])
        ln.new(k.outputs[0], sc.inputs["Scale"])
        sp = n.new("GeometryNodeSetPosition")
        ln.new(gi.outputs["Geometry"], sp.inputs["Geometry"])
        ln.new(sc.outputs["Vector"], sp.inputs["Offset"])
        ln.new(sp.outputs["Geometry"], go.inputs["Geometry"])
    m = fo.modifiers.new("PS Fibre Comb", "NODES")
    m.node_group = g
    for item in g.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT":
            if item.name == "Surface":
                getattr(m.properties.inputs, item.identifier).value = surface
            elif item.name == "Strength":
                getattr(m.properties.inputs, item.identifier).value = strength
    fo["ps_fibre_comb"] = strength


def _store_comb(ob, comb):
    if not comb or len(comb) != len(ob.data.vertices):
        return
    a = ob.data.attributes.new(COMB_ATTR, "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", [c for t in comb for c in t])


# ------------------------------------------------------------------------------------------------------------ build
def build(C, head, frame, hair_spec, material, face_y, fibres=None):
    """As groom.build / groom_hybrid.build (same arguments and return value), for groom/3 specs."""
    errs = validate(hair_spec)
    if errs:
        raise SystemExit("groom/3: " + "; ".join(errs))
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
            H.drop_stale_weights(ob)
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
            default = ("hair" if t not in ACCESSORY_TYPES else "hair_bow" if t == "felt_bow" else
                       "hair_band" if t == "scrunchie" else "hair_" + t)
            ob = result.obj(f"hair_{name}", C)
            _store_comb(ob, getattr(result, "comb", None))
            G1.HAIR_G().assign(ob, material(s.get("material", default)))
            slot_of[ob.name] = s.get("material", default)
            made.append(ob)
        objs += made
        if dyn:
            as_t = {"felt_bow": "bow", "scrunchie": "tie"}.get(t)
            G1._store_dynamics_records(made, dict(s, type=as_t) if as_t else s, ctx["dynamics"][n_rec:], ctx, dyn)
        info.update(type=t)
        rep["structures"][name] = info
    rep["objects"] = [o.name for o in objs]
    rep["vertices"] = sum(len(o.data.vertices) for o in objs)
    if keep:
        hair_slots = {o.name for o in objs if slot_of.get(o.name) == "hair"}
        per = {o.name: H.keepout_violations([o], scalp, keep) for o in objs if o.name in hair_slots}
        rep["keepout"] = {"az": float(keep["az"]), "el_min": float(keep["el_min"]),
                          "violations": sum(per.values()), "by_object": {k: v for k, v in per.items() if v}}
    fb = hair_spec.get("fibres")
    if fb and fb.get("enabled", True) and fibres is not None:
        slots = set(fb.get("slots", ["hair"]))
        dr = fb.get("directional") or {}
        comb = float(dr.get("strength", 0.8)) if dr.get("enabled") else 0.0
        made = []
        for ob in objs:
            if slot_of.get(ob.name) in slots:
                for layer in fb.get("layers", [{}]):
                    fo = fibres(ob, slot_of[ob.name], layer.get("overrides") or {})
                    if fo is not None:
                        if layer.get("shaft_radius_mm"):
                            H.fixed_shaft(fo, float(layer["shaft_radius_mm"]) / 1000.0, float(layer.get("tip_ratio", 0.35)))
                        if comb and COMB_ATTR in ob.data.attributes:
                            comb_fibres(fo, ob, comb)
                        fo.parent = ob
                        fo.matrix_parent_inverse = ob.matrix_world.inverted()
                        fo["ps_groom_fibres"] = layer.get("name", "fibres")
                        made.append(fo.name)
        rep["fibres"] = {"objects": len(made), "layers": [l.get("name", "fibres") for l in fb.get("layers", [{}])],
                         "directional": comb}
    if dyn:
        rep["dynamics"] = {"chains": sum(len(json.loads(o.get("ps_dyn", "{}")).get("chains", [])) for o in objs)}
    return objs, rep


def bind(rig, objs, head_bone, chest_bone, binding):
    """As groom.bind."""
    G1.bind(rig, objs, head_bone, chest_bone, binding)
