"""Face system v2 feature options (T-031): shared, character-independent builders and shaders used by face_generic.

Every option is spec data under spec.face (a character only differs by values); an option that is absent leaves the
face_generic/1 behaviour unchanged, so older specs build exactly as before.

  eyes.shader = "layered/1"   glossy plush eye: layered iris (inner/mid/outer colours, vertical gradient, radial
                              streaks, limbal ring), soft-edged pupil, 1-2 emissive catchlights, wet clear coat
  eyes.spacing_m / offset_z_m / roll_deg      eye spacing (centre to centre), height offset, tilt (outer corner up)
  eyes.lids.upper_curve / lower_curve          lid edge curvature (rotation of the shell about the eye centre that
                                               grows towards the corners: the shell stays concentric, no intersection)
  eyes.lash.strands / lower_strands            individual lashes: count, length, curl, span, width
  brows.style = "felt" | "embroidered"         felt strip or stitched (striated) brow; colour, shape, thickness, height
  nose.type = "bump" | "small_round" | "button" | "minimal_line"   with size_m and offset_z_m
  blush.intensity / softness / nose_intensity  soft felt colour patch
  shape.cheek_roundness_m / chin_forward_m / chin_drop_m / forehead_height_m / forehead_fullness_m   head shape
  skin.occlusion                               felt-skin occlusion compensation (see face_skin_material)
  mouth.rest_shape = "closed_smile" | "open_smile" | "small_o"; mouth.rest_mix {key: weight} tunes the baked weights
"""
import math

import bpy
from mathutils import Vector

import geom as G

SIDES = ((1, "L"), (-1, "R"))


def _f(d, k, default):
    return float(d.get(k, default)) if d is not None else float(default)


def _lin(rgb):
    return (*G.srgb_to_linear(tuple(rgb)), 1.0)


# ------------------------------------------------------------------------------------------------ eye shader
def eye_material_layered(name, ecfg, r):
    """Glossy plush eye (object space: eyeball centre at the origin, -Y forward; 'Generated' coordinates so the iris
    follows the eye bone). Radii are fractions of the eyeball radius measured from the forward axis."""
    iris = ecfg.get("iris", {})
    ir, pr = _f(iris, "radius", 0.55), _f(iris, "pupil", 0.26)
    m = G.material(name, tuple(ecfg.get("sclera_srgb", (238, 232, 226))), roughness=0.3, specular=0.5)
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    p = nodes.get("Principled BSDF")
    wet = ecfg.get("wet_coat", {})
    p.inputs["Coat Weight"].default_value = _f(wet, "weight", 1.0)
    p.inputs["Coat Roughness"].default_value = _f(wet, "roughness", 0.03)
    p.inputs["Coat IOR"].default_value = _f(wet, "ior", 1.45)
    p.inputs["Roughness"].default_value = _f(wet, "base_roughness", 0.35)
    tc = nodes.new("ShaderNodeTexCoord")
    gen = nodes.new("ShaderNodeVectorMath")
    gen.operation = "MULTIPLY_ADD"  # generated 0..1 -> unit sphere (-1..1)
    gen.inputs[1].default_value = (2.0, 2.0, 2.0)
    gen.inputs[2].default_value = (-1.0, -1.0, -1.0)
    links.new(tc.outputs["Generated"], gen.inputs[0])
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(gen.outputs[0], sep.inputs[0])
    comb = nodes.new("ShaderNodeCombineXYZ")
    links.new(sep.outputs["X"], comb.inputs["X"])
    links.new(sep.outputs["Z"], comb.inputs["Z"])
    rho = nodes.new("ShaderNodeVectorMath")
    rho.operation = "LENGTH"
    links.new(comb.outputs[0], rho.inputs[0])
    front = nodes.new("ShaderNodeMath")
    front.operation = "LESS_THAN"
    front.inputs[1].default_value = 0.0
    links.new(sep.outputs["Y"], front.inputs[0])

    def math_node(op, a, b=None):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = float(v)
            else:
                links.new(v, n.inputs[i])
        return n.outputs[0]

    # layered colour ramp over rho: pupil | inner iris | mid | outer | limbal ring | sclera
    inner = tuple(iris.get("inner_srgb", iris.get("srgb", (150, 95, 50))))
    mid = tuple(iris.get("srgb", (122, 72, 42)))
    outer = tuple(iris.get("dark_srgb", (70, 38, 22)))
    limbal = tuple(iris.get("limbal_srgb", (30, 16, 10)))
    pupil = tuple(iris.get("pupil_srgb", (8, 6, 6)))
    lw = _f(iris, "limbal_width", 0.06)
    soft = _f(iris, "pupil_softness", 0.02)
    ramp = nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "LINEAR"
    stops = [(0.0, pupil), (max(pr - soft, 0.001), pupil), (pr + soft, inner), (pr + (ir - pr) * 0.5, mid),
             (ir - lw * 1.2, outer), (ir - lw * 0.35, limbal), (ir + 0.012, tuple(ecfg.get("sclera_srgb", (238, 232, 226)))),
             (1.0, tuple(ecfg.get("sclera_edge_srgb", ecfg.get("sclera_srgb", (238, 232, 226)))))]
    cr.elements[0].position = 0.0
    cr.elements[0].color = _lin(stops[0][1])
    cr.elements[1].position = 1.0
    cr.elements[1].color = _lin(stops[-1][1])
    for pos, c in stops[1:-1]:  # increasing positions; new() keeps the list sorted
        el = cr.elements.new(min(max(pos, 0.0), 1.0))
        el.color = _lin(c)
    links.new(rho.outputs["Value"], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    iris_mask = math_node("MULTIPLY", math_node("LESS_THAN", rho.outputs["Value"], ir), front.outputs[0])
    iris_ring = math_node("MULTIPLY", iris_mask, math_node("GREATER_THAN", rho.outputs["Value"], pr + soft))
    # radial streaks: noise over the direction around the axis, stretched along the radius
    st = _f(iris, "streaks", 0.25)
    if st > 0:
        inv = math_node("DIVIDE", 1.0, math_node("MAXIMUM", rho.outputs["Value"], 1e-4))
        dirv = nodes.new("ShaderNodeCombineXYZ")
        links.new(math_node("MULTIPLY", math_node("MULTIPLY", sep.outputs["X"], inv), 7.0), dirv.inputs["X"])
        links.new(math_node("MULTIPLY", math_node("MULTIPLY", sep.outputs["Z"], inv), 7.0), dirv.inputs["Y"])
        links.new(math_node("MULTIPLY", rho.outputs["Value"], 2.0), dirv.inputs["Z"])
        nz = nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 2.5
        nz.inputs["Detail"].default_value = 3.0
        links.new(dirv.outputs[0], nz.inputs["Vector"])
        mx = nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "OVERLAY"
        links.new(math_node("MULTIPLY", iris_ring, st), mx.inputs["Factor"])
        links.new(col, mx.inputs["A"])
        links.new(nz.outputs["Fac"], mx.inputs["B"])
        col = mx.outputs["Result"]
    # vertical gradient: the lower iris lighter (light enters through the lower cornea), the upper darker (lid shade)
    vg = _f(iris, "vertical_gradient", 0.35)
    if vg > 0:
        lo = math_node("MULTIPLY", math_node("MULTIPLY", math_node("MINIMUM", math_node("MAXIMUM", math_node("DIVIDE", sep.outputs["Z"], -ir), -1.0), 1.0),
                                                                    vg), iris_ring)
        mx = nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "SCREEN"
        mx.inputs["B"].default_value = _lin(tuple(iris.get("glow_srgb", inner)))
        links.new(math_node("MAXIMUM", lo, 0.0), mx.inputs["Factor"])
        links.new(col, mx.inputs["A"])
        dk = nodes.new("ShaderNodeMix")
        dk.data_type = "RGBA"
        dk.blend_type = "MULTIPLY"
        dk.inputs["B"].default_value = _lin(tuple(iris.get("shade_srgb", outer)))
        links.new(math_node("MAXIMUM", math_node("MULTIPLY", lo, -1.0), 0.0), dk.inputs["Factor"])
        links.new(mx.outputs["Result"], dk.inputs["A"])
        col = dk.outputs["Result"]
    # the back half stays sclera
    back = nodes.new("ShaderNodeMix")
    back.data_type = "RGBA"
    back.inputs["A"].default_value = _lin(tuple(ecfg.get("sclera_srgb", (238, 232, 226))))
    links.new(front.outputs[0], back.inputs["Factor"])
    links.new(col, back.inputs["B"])
    links.new(back.outputs["Result"], p.inputs["Base Color"])
    # catchlights: emissive soft discs on the front (x, z, radius[, strength]) in fractions of the radius
    acc = None
    for h in ecfg.get("highlights", []):
        hx, hz, hr = float(h[0]), float(h[1]), float(h[2])
        dv = nodes.new("ShaderNodeVectorMath")
        dv.operation = "DISTANCE"
        dv.inputs[1].default_value = (hx, hz, 0.0)
        c2 = nodes.new("ShaderNodeCombineXYZ")
        links.new(sep.outputs["X"], c2.inputs["X"])
        links.new(sep.outputs["Z"], c2.inputs["Y"])
        links.new(c2.outputs[0], dv.inputs[0])
        mr = nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = hr * (1 - _f(ecfg, "catchlight_softness", 0.25))
        mr.inputs["From Max"].default_value = hr
        mr.inputs["To Min"].default_value = float(h[3]) if len(h) > 3 else 1.0
        mr.inputs["To Max"].default_value = 0.0
        links.new(dv.outputs["Value"], mr.inputs["Value"])
        v = math_node("MULTIPLY", mr.outputs["Result"], front.outputs[0])
        acc = v if acc is None else math_node("MAXIMUM", acc, v)
    if acc is not None:
        em = nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 0.99, 0.97, 1.0)
        em.inputs["Strength"].default_value = _f(ecfg, "catchlight_strength", 1.6)
        mix = nodes.new("ShaderNodeMixShader")
        out = nodes.get("Material Output")
        links.new(acc, mix.inputs[0])
        links.new(p.outputs[0], mix.inputs[1])
        links.new(em.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
    m["ps_face_shader"] = "eye/layered/1"
    return m


# ------------------------------------------------------------------------------------------------ face skin
def face_skin_material(name, skin_rgb, blush_cfg, spots, skin_cfg):
    """Felt face skin: base colour, soft felt blush patches (intensity, softness, felt breakup) and an occlusion
    compensation. Plush felt scatters light into creases, so creases read warm instead of grey: where the ambient
    occlusion (distance occlusion.distance_m) is high, the albedo shifts towards occlusion.warm_srgb by `lift`.
    spots: [(xyz, radius, intensity)] in object coordinates (the skin object sits at the origin)."""
    m = G.material(name, tuple(skin_rgb), roughness=0.55, subsurface=0.2, sss_radius=(1.0, 0.45, 0.3), sss_scale=0.012,
                   specular=0.35)
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    p = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    col = None
    base = _lin(skin_rgb)
    if blush_cfg and spots:
        soft = _f(blush_cfg, "softness", 0.8)
        nz = nodes.new("ShaderNodeTexNoise")  # felt breakup of the patch edge
        nz.inputs["Scale"].default_value = _f(blush_cfg, "breakup_scale", 180.0)
        nz.inputs["Detail"].default_value = 4.0
        links.new(tc.outputs["Object"], nz.inputs["Vector"])
        acc = None
        for s, rad, inten in spots:
            vm = nodes.new("ShaderNodeVectorMath")
            vm.operation = "DISTANCE"
            vm.inputs[1].default_value = tuple(s)
            links.new(tc.outputs["Object"], vm.inputs[0])
            mr = nodes.new("ShaderNodeMapRange")
            mr.interpolation_type = "SMOOTHSTEP"
            mr.inputs["From Min"].default_value = rad * (1 - soft)
            mr.inputs["From Max"].default_value = rad
            mr.inputs["To Min"].default_value = inten
            mr.inputs["To Max"].default_value = 0.0
            links.new(vm.outputs["Value"], mr.inputs["Value"])
            o = mr.outputs["Result"]
            acc = o if acc is None else _max(nodes, links, acc, o)
        br = nodes.new("ShaderNodeMath")
        br.operation = "MULTIPLY_ADD"  # factor * (1 - b/2 + b * noise)
        b = _f(blush_cfg, "breakup", 0.25)
        links.new(nz.outputs["Fac"], br.inputs[0])
        br.inputs[1].default_value = b
        br.inputs[2].default_value = 1.0 - b / 2
        fm = nodes.new("ShaderNodeMath")
        fm.operation = "MULTIPLY"
        fm.use_clamp = True
        links.new(acc, fm.inputs[0])
        links.new(br.outputs[0], fm.inputs[1])
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = base
        mix.inputs["B"].default_value = _lin(tuple(blush_cfg.get("srgb", (226, 150, 150))))
        links.new(fm.outputs[0], mix.inputs["Factor"])
        col = mix.outputs["Result"]
    occ = (skin_cfg or {}).get("occlusion")
    if occ:
        ao = nodes.new("ShaderNodeAmbientOcclusion")
        ao.samples = int(occ.get("samples", 8))
        ao.inputs["Distance"].default_value = _f(occ, "distance_m", 0.03)
        f = nodes.new("ShaderNodeMath")
        f.operation = "MULTIPLY"
        f.use_clamp = True
        inv = nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        links.new(ao.outputs["AO"], inv.inputs[1])
        links.new(inv.outputs[0], f.inputs[0])
        f.inputs[1].default_value = _f(occ, "lift", 0.5)
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        if col is None:
            mix.inputs["A"].default_value = base
        else:
            links.new(col, mix.inputs["A"])
        mix.inputs["B"].default_value = _lin(tuple(occ.get("warm_srgb", skin_rgb)))
        links.new(f.outputs[0], mix.inputs["Factor"])
        col = mix.outputs["Result"]
    if col is not None:
        links.new(col, p.inputs["Base Color"])
    m["ps_face_shader"] = "skin/felt_face/1"
    return m


def _max(nodes, links, a, b):
    mx = nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    links.new(a, mx.inputs[0])
    links.new(b, mx.inputs[1])
    return mx.outputs[0]


def carry_base_to_rim(material):
    """The shared preset rim layer (silhouette sheen) uses a flat base colour; give it the face skin's colour graph
    so blush and the occlusion compensation stay visible near the silhouette (cheeks seen at 3/4)."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    p = nodes.get("Principled BSDF")
    rim = next((n for n in nodes if n.type == "BSDF_PRINCIPLED" and n != p and n.label == "Rim Sheen"), None)
    if rim is None:
        rim = next((n for n in nodes if n.type == "BSDF_PRINCIPLED" and n != p), None)
    src = next((l.from_socket for l in p.inputs["Base Color"].links), None)
    if rim is not None and src is not None:
        links.new(src, rim.inputs["Base Color"])


# ------------------------------------------------------------------------------------------------ brows
def brow_material(name, bc, MATERIALS):
    """Felt or embroidered brows. Felt: the shared 'felt' preset. Embroidered: felt plus a stitch relief (bands
    across the brow's length, in object space) and a slight satin sheen."""
    rgb = tuple(bc.get("srgb", (110, 70, 52)))
    m = G.material(name, rgb, roughness=0.8)
    style = bc.get("style")
    if style in ("felt", "embroidered"):
        MATERIALS.apply_preset(m, "felt", rgb, reference_size_m=_f(bc, "reference_size_m", 0.06))
    if style == "embroidered":
        nt = m.node_tree
        nodes, links = nt.nodes, nt.links
        p = nodes.get("Principled BSDF")
        tc = nodes.new("ShaderNodeTexCoord")
        wv = nodes.new("ShaderNodeTexWave")
        wv.wave_type = "BANDS"
        wv.bands_direction = "X"
        wv.inputs["Scale"].default_value = _f(bc, "stitch_per_m", 600.0) / 10.0
        wv.inputs["Distortion"].default_value = 1.5
        links.new(tc.outputs["Object"], wv.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.6
        bump.inputs["Distance"].default_value = 0.0004
        links.new(wv.outputs["Fac"], bump.inputs["Height"])
        prev = next((l.from_socket for l in p.inputs["Normal"].links), None)
        if prev is not None:
            links.new(prev, bump.inputs["Normal"])
        links.new(bump.outputs["Normal"], p.inputs["Normal"])
        p.inputs["Sheen Weight"].default_value = 0.5
    m["ps_face_shader"] = f"brow/{style or 'plain'}/1"
    return m


# ------------------------------------------------------------------------------------------------ lashes
def lash_strands(T, edge_point, sx, cfg, upper, name, C):
    """Individual curved lashes along a lid edge (built in the eye's unit frame, returned in world space).
    cfg: count, length_m (scalar or list, inner -> outer), curl (0 straight .. 1 strongly curled), from_deg/to_deg
    (azimuth span from the eye axis, positive = towards the outer corner), width_m, outward (lean towards the outer
    corner), forward (how far they stand out of the face, default 0.25). edge_point(a) gives the lid edge at azimuth a (radians, frame space) or None."""
    n = int(cfg.get("count", 0))
    if n <= 0:
        return []
    a0, a1 = math.radians(_f(cfg, "from_deg", 20)), math.radians(_f(cfg, "to_deg", 75))
    lengths = cfg.get("length_m", 0.005)
    lengths = lengths if isinstance(lengths, list) else [lengths]
    curl, wb, lean = _f(cfg, "curl", 0.5), _f(cfg, "width_m", 0.001), _f(cfg, "outward", 0.6)
    fwd = _f(cfg, "forward", 0.25)  # how far the lashes stand out of the face (glasses sit close in front)
    vz = 1.0 if upper else -1.0
    Tw = T.to_3x3()
    out = []
    for j in range(n):
        t = j / max(n - 1, 1)
        a = sx * (a0 + (a1 - a0) * t)
        base = edge_point(a)
        if base is None:
            continue
        nxt = edge_point(a - sx * 0.05)
        tang = (base - nxt).normalized() if nxt is not None else Vector((sx, 0, 0))  # towards the outer corner
        L = float(lengths[min(int(round(t * (len(lengths) - 1))), len(lengths) - 1)])
        radial = base.normalized()
        d = (radial * fwd + Vector((0, 0, vz)) * 0.8 + tang * lean * t).normalized()
        tip = base + d * L + Vector((0, 0, vz)) * L * curl * 0.6 + Vector((0, -1, 0)) * L * (0.2 - 0.4 * curl)
        mid = base + d * L * 0.55 + Vector((0, -1, 0)) * L * 0.15 * fwd
        cp = [T @ p for p in G.bezier(base, mid, tip, 6)]
        s = G.tube(f"_{name}.{j}", cp, [wb * (1 - 0.85 * k / 5) for k in range(6)], [wb * 0.6 * (1 - 0.85 * k / 5) for k in range(6)],
                   C, up_hint=tuple(Tw @ Vector((0, -1, 0))), seg=6, cap_start="round", cap_end="point")
        out.append(s)
    return out


def curve_lid(ob, curve, upper):
    """Lid edge curvature: each vertex is rotated about the frame's x axis (through the eye centre) by an angle that
    grows with (x/r)^2, so the corners drop (upper, curve > 0) or rise (lower, curve > 0): a rounder opening. The
    shell keeps its radius (no new intersection with the eyeball). Mesh in unit-frame coordinates."""
    if abs(curve) < 1e-9:
        return
    from mathutils import Matrix
    rr = max((v.co.length for v in ob.data.vertices), default=1.0)
    sgn = 1.0 if upper else -1.0
    for v in ob.data.vertices:
        u = v.co.x / rr
        ang = sgn * curve * u * u * (math.pi / 4)
        v.co = Matrix.Rotation(ang, 3, "X") @ v.co
    ob.data.update()


# ------------------------------------------------------------------------------------------------ nose
def build_nose(C, M, head, ctx, nc, z_nose):
    """Nose types. bump (legacy): a soft bump sculpted into the head; small_round: a smaller, rounder, prouder bump;
    button: a separate felt ellipsoid sitting on the surface; minimal_line: a short curved line (tube). Returns the
    separate object (or None) and the nose tip landmark."""
    t = nc.get("type", "bump")
    size = _f(nc, "size_m", _f(nc, "radius_m", 0.016))
    z = z_nose + _f(nc, "offset_z_m", 0.0)
    ny = ctx.face_y(None, 0.0, z)
    obj = None
    if t in ("bump", "small_round"):
        h = _f(nc, "height_m", 0.004 if t == "bump" else size * 0.45)
        G.brush(head, (0.0, ny + size * 0.3, z), size, (0, -h, 0), power=2.0 if t == "bump" else 1.4)
        ctx.invalidate()
    elif t == "button":
        rad = (size * 0.62, size * 0.42, size * 0.5)
        obj = G.uv_sphere("nose", (0, 0, 0), 1.0, C, 24, 12, rad)
        obj.location = (0.0, ny - rad[1] * (1 - _f(nc, "inset", 0.35)), z)
        bpy.context.view_layer.update()
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = obj.matrix_world.__class__.Identity(4)
        G.assign(obj, M["face_skin"])
    elif t == "minimal_line":
        pts = []
        w = size * 0.5
        for i in range(7):
            u = -1 + 2 * i / 6
            x, zz = u * w, z - (1 - u * u) * size * 0.18
            pts.append((x, ctx.face_y(None, x, zz) - 0.0004, zz))
        obj = G.tube("nose", pts, [_f(nc, "line_m", 0.0012)] * 7, [0.0006] * 7, C, up_hint=(0, -1, 0), seg=8)
        G.assign(obj, G.material("M_nose_line", tuple(nc.get("srgb", (150, 95, 85))), roughness=0.8))
    else:
        raise ValueError(f"face.nose.type {t!r}: bump | small_round | button | minimal_line")
    ny = ctx.face_y(None, 0.0, z)
    tip = Vector((0.0, ny, z))
    if obj is not None and t == "button":
        tip = Vector((0.0, min(v.co.y for v in obj.data.vertices), z))
    return obj, tip


# ------------------------------------------------------------------------------------------------ head shape
def shape_head(head, ctx, sc, ex, ez, r):
    """Head proportion options sculpted into the head mesh before the features are placed (all 0 = unchanged)."""
    rep = {}
    cr = _f(sc, "cheek_roundness_m", 0.0)
    if cr:
        for sx, _ in SIDES:
            x, z = sx * ex * _f(sc, "cheek_x", 0.85), ez - _f(sc, "cheek_below_eye_m", 0.045)
            c = (x, ctx.face_y(None, x, z), z)
            G.brush(head, c, _f(sc, "cheek_radius_m", 0.04), cr, normal_mode=True)
        ctx.invalidate()
        rep["cheek_roundness_m"] = cr
    cf, cd = _f(sc, "chin_forward_m", 0.0), _f(sc, "chin_drop_m", 0.0)
    if cf or cd:
        z = ez - _f(sc, "chin_below_eye_m", 0.09)
        c = (0.0, ctx.face_y(None, 0.0, z), z)
        G.brush(head, c, _f(sc, "chin_radius_m", 0.035), (0, -cf, -cd))
        ctx.invalidate()
        rep["chin_m"] = [cf, cd]
    fh, ff = _f(sc, "forehead_height_m", 0.0), _f(sc, "forehead_fullness_m", 0.0)
    if fh or ff:
        z = ez + _f(sc, "forehead_above_eye_m", 0.08)
        c = (0.0, ctx.face_y(None, 0.0, z), z)
        rad = _f(sc, "forehead_radius_m", 0.08)
        if fh:
            G.brush(head, (c[0], c[1] + rad * 0.4, c[2] + rad * 0.3), rad, (0, 0, fh))
        if ff:
            G.brush(head, c, rad, ff, normal_mode=True)
        ctx.invalidate()
        rep["forehead_m"] = [fh, ff]
    return rep


# ------------------------------------------------------------------------------------------------ mouth rest shape
REST_SHAPES = {"closed_smile": {}, "open_smile": {"MouthWide": 0.8, "MouthSmile": 0.4}, "small_o": {"MouthO": 0.9}}


def bake_rest_shape(objs, shape, mix=None):
    """Makes a mouth shape the rest state: its deltas are added to the basis and to every shape key (relative action
    units keep working on top). closed_smile = the lips_jaw/2 neutral (nothing baked). `mix` (spec
    face.mouth.rest_mix, {shape key: weight}) replaces the shape's default weights, e.g. a gentler open smile."""
    import numpy as np
    if shape not in REST_SHAPES:
        raise ValueError(f"face.mouth.rest_shape {shape!r}: {sorted(REST_SHAPES)}")
    w = dict(mix) if mix else REST_SHAPES[shape]
    done = []
    for ob in objs:
        sk = ob.data.shape_keys
        if sk is None or not any(k in sk.key_blocks for k in w):
            continue
        kb = sk.key_blocks
        n = len(ob.data.vertices) * 3
        base = np.empty(n)
        kb[0].data.foreach_get("co", base)
        delta = np.zeros(n)
        for k, v in w.items():
            if k in kb:
                d = np.empty(n)
                kb[k].data.foreach_get("co", d)
                delta += (d - base) * v
        for k in kb:
            d = np.empty(n)
            k.data.foreach_get("co", d)
            k.data.foreach_set("co", d + delta)
        ob.data.vertices.foreach_set("co", base + delta)
        ob.data.update()
        done.append(ob.name)
    return done
