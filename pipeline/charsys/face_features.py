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
def face_skin_material(name, skin_rgb, blush_cfg, spots, skin_cfg, face_centre=None):
    """Felt face skin: base colour, soft felt blush patches (intensity, softness, felt breakup) and an occlusion
    compensation. Plush felt scatters light into creases, so creases read warm instead of grey: where the ambient
    occlusion (distance occlusion.distance_m) is high, the albedo shifts towards occlusion.warm_srgb by `lift`;
    optional occlusion.bleed (0 = off) adds the light felt scatters into shaded skin (emission of strength
    bleed * occlusion, bleed_srgb (default warm_srgb) x local colour;
    bleed_face_radius_m/bleed_body: full bleed within that radius of face_centre, bleed_body times it elsewhere); occlusion.samples sets the AO samples (noise).
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
        glow = _f(occ, "bleed", 0.0)
        if glow > 0:  # felt light bleed: occluded skin (under fringes, glasses, the chin) re-emits warm scattered light
            g = nodes.new("ShaderNodeMath")
            g.operation = "MULTIPLY"
            links.new(inv.outputs[0], g.inputs[0])
            g.inputs[1].default_value = glow
            fr = _f(occ, "bleed_face_radius_m", 0.0)
            if fr > 0 and face_centre is not None:  # the face sits inside the hair: full bleed on the face, a
                # fraction (bleed_body) elsewhere, fading over half the radius
                dv = nodes.new("ShaderNodeVectorMath")
                dv.operation = "DISTANCE"
                dv.inputs[1].default_value = tuple(face_centre)
                links.new(tc.outputs["Object"], dv.inputs[0])
                fm2 = nodes.new("ShaderNodeMapRange")
                fm2.interpolation_type = "SMOOTHSTEP"
                fm2.inputs["From Min"].default_value = fr
                fm2.inputs["From Max"].default_value = fr * 1.5
                fm2.inputs["To Min"].default_value = 1.0
                fm2.inputs["To Max"].default_value = _f(occ, "bleed_body", 1.0)
                links.new(dv.outputs["Value"], fm2.inputs["Value"])
                g2 = nodes.new("ShaderNodeMath")
                g2.operation = "MULTIPLY"
                links.new(g.outputs[0], g2.inputs[0])
                links.new(fm2.outputs["Result"], g2.inputs[1])
                g = g2
            gc = nodes.new("ShaderNodeMix")
            gc.data_type = "RGBA"
            gc.blend_type = "MULTIPLY"
            gc.inputs["Factor"].default_value = 1.0
            gc.inputs["A"].default_value = _lin(tuple(occ.get("bleed_srgb", occ.get("warm_srgb", skin_rgb))))
            links.new(col, gc.inputs["B"])  # tinted by the local colour (the blush glows rosy)
            links.new(gc.outputs["Result"], p.inputs["Emission Color"])
            links.new(g.outputs[0], p.inputs["Emission Strength"])
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
REST_SHAPES = {"closed_smile": {}, "open_smile": {"MouthWide": 0.8, "MouthSmile": 0.4}, "small_o": {"MouthO": 0.9},
               "pout": {"MouthFrown": 0.5, "MouthPout": 0.6}}  # pout (T-058): small sulky mouth, needs MouthPout


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


# ================================================================================================ face_generic/2 (T-065)
# Everything below is used only by face_generic/2 (opt-in by the spec's face pin). face_generic/1 never calls it.
def _smooth(t):
    import numpy as np
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _head_coords(head):
    """(N, 3) world coordinates of the head mesh's basis and a setter that writes new world coordinates back to the
    basis and adds the same displacement to every shape key (so keys made before keep their relative motion)."""
    import numpy as np
    me = head.data
    n = len(me.vertices)
    mw = np.array(head.matrix_world)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    world = co @ mw[:3, :3].T + mw[:3, 3]

    def write(new_world):
        mi = np.linalg.inv(mw)
        local = new_world @ mi[:3, :3].T + mi[:3, 3]
        delta = (local - co).ravel()
        if me.shape_keys:
            for k in me.shape_keys.key_blocks:
                d = np.empty(n * 3)
                k.data.foreach_get("co", d)
                k.data.foreach_set("co", d + delta)
        me.vertices.foreach_set("co", local.ravel())
        me.update()
    return world, write


# ------------------------------------------------------------------------------------------------ face shape v2
def shape_face_v2(head, ctx, sc, ex, ez, r, z_chin):
    """Round, full-cheeked face options (all absent/0 = unchanged), applied to the head mesh before any feature is
    placed, in this order:
      outline_roundness (0..1), outline_exponent (2 = ellipse), outline_top_below_eye_m: the front-view outline of the
        lower face (from outline_top down to the chin) moves towards a superellipse; every horizontal slice is scaled
        in x (the slice keeps its own shape). outline_chin_width_m keeps a small flat chin (default 0).
      face_width_m: the lower face (below the eye line, front half) widens by this much per side at its widest.
      lower_face_length_m: the region between the eye line and the chin stretches (+) or shortens (-) vertically; the
        chin and everything below it within lower_face_fade_m move by the full amount.
      cheek_fullness_m, cheek_radius_m, cheek_below_eye_m, cheek_x, cheek_forward (0..1): a soft bulge of the cheeks,
        outwards along a direction between the radial direction (from the head centre) and forward; the
        face_generic/1 option cheek_roundness_m is added to it (v2 does not use the v1 normal brush for it).
      jaw_depth_roundness (0..1): the lower face's horizontal sections round off at the front corners (3/4 views).
      lower_face_recede_m, recede_from_below_eye_m: below that line the face curves back towards the chin (side view).
    Returns a report; the face context is invalidated."""
    import numpy as np
    rep = {}
    world, write = _head_coords(head)
    p = world.copy()
    front = p[:, 1] < (ctx.face_y(None, 0.0, ez) + 0.6 * abs(ctx.face_y(None, 0.0, ez)))  # front ~ 80 % of the head
    # --- lower outline (front view)
    ro = _f(sc, "outline_roundness", 0.0)
    if ro > 0:
        z_top = ez - _f(sc, "outline_top_below_eye_m", 0.0)
        nexp = _f(sc, "outline_exponent", 2.2)
        cw = _f(sc, "outline_chin_width_m", 0.0)
        fade = _f(sc, "outline_chin_fade_m", 0.008)
        bins = np.arange(z_chin - 0.01, z_top + 0.004, 0.003)
        widths = []
        for b in bins:
            m = np.abs(p[:, 2] - b) < 0.002
            widths.append(np.abs(p[m, 0]).max() if m.any() else np.nan)
        widths = np.array(widths)
        W = np.nanmax(np.abs(p[np.abs(p[:, 2] - z_top) < 0.002, 0])) if (np.abs(p[:, 2] - z_top) < 0.002).any() else np.nanmax(widths)
        sel = (p[:, 2] < z_top) & (p[:, 2] > z_chin - 0.004)
        xc = np.interp(p[sel, 2], bins[~np.isnan(widths)], widths[~np.isnan(widths)])
        t = np.clip((z_top - p[sel, 2]) / max(z_top - z_chin, 1e-6), 0.0, 1.0)
        xt = cw + (W - cw) * np.power(np.clip(1 - t ** nexp, 0.0, 1.0), 1.0 / nexp)
        a = ro * _smooth((p[sel, 2] - z_chin) / fade + 0.5)
        s = 1.0 + a * (np.clip(xt / np.maximum(xc, 1e-4), 0.55, 1.6) - 1.0)
        p[sel, 0] *= s
        rep["outline"] = {"roundness": ro, "exponent": nexp, "top_z_m": round(z_top, 4), "width_m": round(float(W), 4)}
    # --- face width (lower face, front)
    fw = _f(sc, "face_width_m", 0.0)
    if fw:
        zb = ez - _f(sc, "face_width_below_eye_m", 0.035)
        wz = np.exp(-((p[:, 2] - zb) / _f(sc, "face_width_band_m", 0.035)) ** 2)
        hw = max(np.abs(p[:, 0]).max(), 1e-4)
        p[:, 0] += np.sign(p[:, 0]) * fw * wz * front * np.clip(np.abs(p[:, 0]) / hw, 0, 1) ** 1.5
        rep["face_width_m"] = fw
    # --- lower face length
    lf = _f(sc, "lower_face_length_m", 0.0)
    if lf:
        lff = _f(sc, "lower_face_fade_m", 0.03)
        t = np.clip((ez - p[:, 2]) / max(ez - z_chin, 1e-6), 0.0, 1.0)
        below = np.clip((z_chin - p[:, 2]) / lff, 0.0, 1.0)
        mv = np.where(p[:, 2] >= z_chin, t, 1.0 - _smooth(below))
        p[:, 2] -= lf * mv * (p[:, 2] < ez)
        rep["lower_face_length_m"] = lf
    # --- jaw depth roundness (front corners of the lower face sections)
    jd = _f(sc, "jaw_depth_roundness", 0.0)
    if jd > 0:
        zc = ez - _f(sc, "jaw_depth_below_eye_m", 0.03)
        band = _f(sc, "jaw_depth_band_m", 0.05)
        wz = np.exp(-((p[:, 2] - zc) / band) ** 2) * (p[:, 2] < ez + 0.01)
        yf = p[:, 1].min()
        hw = max(np.abs(p[:, 0]).max(), 1e-4)
        u = np.clip(np.abs(p[:, 0]) / hw, 0, 1)
        back = (p[:, 1] - yf)  # 0 at the front plane
        pull = jd * wz * (u ** 2) * np.clip(1 - back / 0.08, 0, 1) * 0.04
        p[:, 1] += pull * front
        rep["jaw_depth_roundness"] = jd
    # --- lower face recede (side view: the face below recede_from curves back towards the chin)
    rc = _f(sc, "lower_face_recede_m", 0.0)
    if rc:
        z0 = ez - _f(sc, "recede_from_below_eye_m", 0.045)
        yf, yb = p[:, 1].min(), np.median(p[:, 1])
        t = np.clip((z0 - p[:, 2]) / max(z0 - z_chin, 1e-6), 0.0, 1.0) ** 2 * (p[:, 2] > z_chin - 0.02)
        fr = np.clip((yb - p[:, 1]) / max(yb - yf, 1e-6), 0.0, 1.0) ** 2
        p[:, 1] += rc * t * fr
        rep["lower_face_recede_m"] = rc
    write(p)
    ctx.invalidate()
    # --- cheeks: soft bulge (normal + forward), after the global reshape
    cf = _f(sc, "cheek_fullness_m", 0.0) + _f(sc, "cheek_roundness_m", 0.0)  # v1's cheek_roundness joins in (smooth)
    if cf:
        world, write = _head_coords(head)
        p = world.copy()
        # smooth outward directions (radial from the head's centre at the eye line), not the mesh's vertex normals:
        # the v1 cheek brush followed vertex normals and left bumps on coarse cheeks
        hm = p[:, 2] > z_chin
        hc = np.array([0.0, float(np.mean(p[hm, 1])), ez])
        nrm = p - hc
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        fwd = _f(sc, "cheek_forward", 0.4)
        rad = _f(sc, "cheek_radius_m", 0.045)
        for sx, _ in SIDES:
            x, z = sx * ex * _f(sc, "cheek_x", 1.0), ez - _f(sc, "cheek_below_eye_m", 0.045)
            c = np.array([x, ctx.face_y(None, x, z), z])
            d = np.linalg.norm(p - c, axis=1) / rad
            f = np.clip(1 - d * d, 0, None) ** 2
            dirv = nrm * (1 - fwd) + np.array([0, -1.0, 0]) * fwd
            p += dirv * (cf * f)[:, None]
        write(p)
        ctx.invalidate()
        rep["cheek_fullness_m"] = cf
    return rep


# ------------------------------------------------------------------------------------------------ lid socket v2
def lid_edges(edge_fn, n=121, corner_deg=60.0):
    """Unit directions of a lid edge: edge_fn(a) -> point (frame space) or None, for azimuths within +-corner_deg."""
    import numpy as np
    pts = []
    for i in range(n):
        a = math.radians(-corner_deg + 2 * corner_deg * i / (n - 1))
        q = edge_fn(a)
        if q is not None:
            pts.append(np.array(q[:]) / max(q.length, 1e-9))
    return np.array(pts)


def _edge_table(edge):
    """Azimuth-sorted (azimuth, elevation) table of a lid edge given as unit directions in the eye frame."""
    import numpy as np
    a = np.arctan2(edge[:, 0], -edge[:, 1])
    e = np.arcsin(np.clip(edge[:, 2], -1, 1))
    o = np.argsort(a)
    return a[o], e[o]


def lid_socket(head, ctx, sides, cfg):
    """Blends the lids into the skin (face_generic/2). In each eye's frame (azimuth a around the forward axis,
    elevation e), with the lid edges e_up(a) and e_lo(a): above the upper edge the skin stays behind the lid shell for
    band_deg (the visible lid band), rises over ramp_deg to just outside the shell (clearance_m; where it crosses the
    shell is the crease) and blends back to the original face over reach_deg; the same below the lower edge
    (lower_band_deg). Skin far off the shell (radial_reach x radius) and the opening itself stay as they are. Upper
    and lower profiles blend smoothly at the eye corners. The lid shells therefore show only as a narrow band at
    their edge; the rest lies under the face skin.
    sides: [{"side", "T" (eye frame), "r", "up_edge", "lo_edge" (unit directions), "r_up_out", "r_lo_out"}].
    Returns (report, per-side weights {"up", "lo", "T"} for the lid-following shape keys)."""
    import numpy as np
    band_up = math.radians(_f(cfg, "band_deg", 7.0))
    band_lo = math.radians(_f(cfg, "lower_band_deg", _f(cfg, "band_deg", 7.0)))
    ramp = math.radians(_f(cfg, "ramp_deg", 6.0))
    reach = math.radians(_f(cfg, "reach_deg", 24.0))
    clear = _f(cfg, "clearance_m", 0.0006)
    inner = _f(cfg, "inner_scale", 0.95)
    corner = math.radians(_f(cfg, "corner_deg", 60.0))
    follow_reach = math.radians(_f(cfg, "follow_reach_deg", _f(cfg, "reach_deg", 24.0) * 0.6))
    fa = math.radians(_f(cfg, "follow_azimuth_deg", 40.0))
    world, write = _head_coords(head)
    p = world.copy()
    weights, rep = {}, {}
    smooth_sel = []
    soft = _f(cfg, "cover_softness", 0.12)

    def profile(delta, dc, band, R_s, behind, radial):
        """Skin radius along one lid: behind the eye under the lid band, then over the shell (a smooth maximum of the
        face and the shell's outer radius, so the face is only raised where the shell would show). Continuous in
        delta, starting from the opening's own value (behind) at the edge."""
        k = soft * radial / 0.4
        cover = 0.5 * (dc + R_s + np.sqrt((dc - R_s) ** 2 + k * k))
        start = max(band - ramp, 0.0)
        rise = _smooth((delta - start) / max(band - start, math.radians(1.0)))
        back = _smooth((delta - band) / reach) * _smooth((dc - R_s) / (0.5 * radial))  # blend back where the face is in front
        back = np.maximum(back, _smooth((dc - R_s - 0.5 * radial) / radial))  # surfaces far in front (temples, cheeks) stay
        cover = cover * (1 - back) + dc * back
        return behind + (cover - behind) * rise, back
    for s in sides:
        T = np.array(s["T"])
        Ti = np.linalg.inv(T)
        q = p @ Ti[:3, :3].T + Ti[:3, 3]
        d = np.linalg.norm(q, axis=1)
        u = q / np.maximum(d, 1e-9)[:, None]
        cand = (u[:, 1] < -0.05) & (d < s["r"] * 2.2)
        uc, dc = u[cand], d[cand]
        a = np.arctan2(uc[:, 0], -uc[:, 1])
        e = np.arcsin(np.clip(uc[:, 2], -1, 1))
        ac = np.clip(a, -corner, corner)
        tu, tl = _edge_table(s["up_edge"]), _edge_table(s["lo_edge"])
        e_up = np.interp(ac, tu[0], tu[1])
        e_lo = np.interp(ac, tl[0], tl[1])
        # beyond the corner the edges close in towards their mean (the opening ends)
        over = np.abs(a) - corner
        mid = (e_up + e_lo) / 2
        k = _smooth(over / math.radians(12.0))
        e_up = e_up + (mid - e_up) * k
        e_lo = e_lo + (mid - e_lo) * k
        du, dl = e - e_up, e_lo - e
        inside = (du < 0) & (dl < 0)
        radial = _f(cfg, "radial_reach", 0.4) * s["r"]
        t_in = s["r"] * inner
        cr = _f(cfg, "carve_reach", 0.15) * s["r"]  # only skin close in front of the eye is carved (not the corners' skin)
        fo = (1.0 - _smooth((np.abs(a) - (corner - math.radians(10.0))) / math.radians(10.0))) * (1.0 - _smooth((dc - s["r"] - cr) / cr))
        behind = np.where(dc > t_in, dc + (t_in - dc) * fo, dc)  # the opening: skin in front of the eyeball moves behind it
        nu, bu = profile(du, dc, band_up, s["r_up_out"] + clear, behind, radial)
        nl, bl = profile(dl, dc, band_lo, s["r_lo_out"] + clear, behind, radial)
        # beyond the eye corners there is no opening and no lid band: the skin only covers the shells
        cf = 1.0 - _smooth((np.abs(a) - corner) / math.radians(10.0) + 0.5)
        kk = soft * radial / 0.4
        for nn, R_s in ((nu, s["r_up_out"] + clear), (nl, s["r_lo_out"] + clear)):
            cov = 0.5 * (dc + R_s + np.sqrt((dc - R_s) ** 2 + kk * kk))
            cov = cov + (dc - cov) * _smooth((dc - R_s - 0.5 * radial) / radial)
            nn[:] = cov + (nn - cov) * cf
        zu = _smooth((du - dl) / math.radians(8.0) + 0.5)  # 1 = nearer the upper lid (further above it than below the lower)
        newd = np.where(inside, behind, zu * nu + (1 - zu) * nl)
        fw = _smooth((-uc[:, 1] - 0.05) / 0.35)  # the socket fades out towards the eye's sides
        newd = dc + (newd - dc) * fw
        q[cand] = uc * newd[:, None]
        far = np.where(zu > 0.5, du - band_up, dl - band_lo) > math.radians(3.0)
        wsm = (zu * (1 - bu) + (1 - zu) * (1 - bl)) * fw * cf + (1 - cf) * fw  # where the skin covers the shells
        keep = far & ~inside & (wsm > 0.02)
        smooth_sel.append((np.where(cand)[0][keep], wsm[keep]))
        # lid-following weights (EyeWide): the skin from just inside the edge to the crease, over the eye's width
        azw = 1.0 - _smooth((np.abs(a) - fa) / math.radians(35.0))
        azw = azw * (1.0 - _smooth((dc - (s["r_up_out"] + clear)) / (0.35 * s["r"])))  # skin away from the eye moves less
        wu_ = _smooth((du + band_up) / band_up) * (1.0 - _smooth((du - band_up) / follow_reach)) * azw * (1 - bu * _smooth((du - band_up) / math.radians(2.0)))
        wl_ = _smooth((dl + band_lo) / band_lo) * (1.0 - _smooth((dl - band_lo) / (0.4 * follow_reach))) * azw * (1 - bl * _smooth((dl - band_lo) / math.radians(2.0)))
        wu, wl = np.zeros(len(p)), np.zeros(len(p))
        idx = np.where(cand)[0]
        wu[idx], wl[idx] = wu_ * zu, wl_ * (1 - zu)
        weights[s["side"]] = {"up": wu, "lo": wl, "T": s["T"]}
        p = q @ T[:3, :3].T + T[:3, 3]
        rep[s["side"]] = {"vertices": int(cand.sum()), "opening": int(inside.sum()),
                          "moved_max_m": round(float(np.abs(newd - dc).max()) if len(dc) else 0.0, 4)}
    # gentle Laplacian smoothing of the covered / blended skin (never the lid band or the opening): removes the small
    # ripples a coarse cheek surface gets when it is pulled onto the shell
    it = int(_f(cfg, "smooth_iterations", 4))
    if it > 0 and smooth_sel:
        sel = np.zeros(len(p), bool)
        wsel = np.zeros(len(p))
        for idx_s, w_s in smooth_sel:
            sel[idx_s] = True
            wsel[idx_s] = np.maximum(wsel[idx_s], w_s)
        me = head.data
        ed = np.empty(len(me.edges) * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", ed)
        ed = ed.reshape(-1, 2)
        ed = ed[sel[ed[:, 0]] | sel[ed[:, 1]]]
        deg = np.bincount(ed.ravel(), minlength=len(p)).astype(float)
        for _ in range(it):
            acc = np.zeros_like(p)
            np.add.at(acc, ed[:, 0], p[ed[:, 1]])
            np.add.at(acc, ed[:, 1], p[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            p[sel] += (0.5 * wsel[sel])[:, None] * (avg[sel] - p[sel])  # fades out with the cover: no groove at its edge
        rep["smoothed_vertices"] = int(sel.sum())
    write(p)
    ctx.invalidate()
    return rep, weights


def socket_key(head, name, side_w, angles):
    """Adds (or extends) shape key `name` on the head: the socket skin of each side rotates about its eye frame's x
    axis by angles[(side, zone)] degrees times the vertex weight (zone "up" = upper lid skin, "lo" = lower)."""
    import numpy as np
    me = head.data
    n = len(me.vertices)
    if me.shape_keys is None:
        head.shape_key_add(name="Basis")
    kb = me.shape_keys.key_blocks
    base = np.empty(n * 3)
    kb[0].data.foreach_get("co", base)
    base = base.reshape(n, 3)
    if name in kb:
        cur = np.empty(n * 3)
        kb[name].data.foreach_get("co", cur)
        cur = cur.reshape(n, 3)
        key = kb[name]
    else:
        cur = base.copy()
        key = head.shape_key_add(name=name, from_mix=False)
        key.value = 0.0
    mw = np.array(head.matrix_world)
    mi = np.linalg.inv(mw)
    world = base @ mw[:3, :3].T + mw[:3, 3]
    delta = np.zeros_like(world)
    for (side, zone), deg in angles.items():
        if side not in side_w or abs(deg) < 1e-9:
            continue
        w = side_w[side][zone]
        idx = np.nonzero(w > 1e-4)[0]
        if not len(idx):
            continue
        T = np.array(side_w[side]["T"])
        Ti = np.linalg.inv(T)
        q = world[idx] @ Ti[:3, :3].T + Ti[:3, 3]
        a = np.radians(deg) * w[idx]
        c, s_ = np.cos(a), np.sin(a)
        y = q[:, 1] * c - q[:, 2] * s_  # rotation about x by +a (front moves down for positive a)
        z = q[:, 1] * s_ + q[:, 2] * c
        q2 = np.stack([q[:, 0], y, z], axis=1)
        delta[idx] += (q2 @ T[:3, :3].T + T[:3, 3]) - world[idx]
    dl = delta @ mi[:3, :3].T
    key.data.foreach_set("co", (cur + dl).ravel())
    return key


def shell_exposure(head, shells, ctx_tree_fn=None):
    """Fraction of each lid shell's outer vertices that can be seen from the front (no head skin in front of them
    along -y): a diagnostic of the blended lids (the lid band shows, the rest of the shell should be covered)."""
    from mathutils.bvhtree import BVHTree
    mw = head.matrix_world
    me = head.data
    tree = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [pp.vertices[:] for pp in me.polygons])
    out = {}
    for ob in shells:
        tot = vis = 0
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            tot += 1
            hit = tree.ray_cast(w, Vector((0, -1, 0)), 1.0)
            if hit[0] is None:
                vis += 1
        out[ob.name] = round(vis / max(tot, 1), 3)
    return out


# ------------------------------------------------------------------------------------------------ brows v2
BROW_PRESETS = {
    # short, low, nearly flat felt strokes (boy: char_C, #08, #28)
    "flat_stroke": {"inner": 0.45, "outer": 0.9, "arch_m": 0.0006, "inner_drop_m": 0.0012, "outer_drop_m": 0.0012,
                    "thick_m": 0.0045, "depth_m": 0.0014, "taper": 0.45, "taper_inner": 0.35},
    # soft arched, thinner, lighter brows (girl: ref_34, ref_30)
    "soft_arch": {"inner": 0.55, "outer": 1.0, "arch_m": 0.0045, "inner_drop_m": 0.0, "outer_drop_m": 0.003,
                  "thick_m": 0.0032, "depth_m": 0.0012, "taper": 0.6, "taper_inner": 0.3},
    # small, short, high soft arcs (third character: 04, 14)
    "short_arc": {"inner": 0.35, "outer": 0.75, "arch_m": 0.003, "inner_drop_m": 0.0, "outer_drop_m": 0.002,
                  "thick_m": 0.0028, "depth_m": 0.001, "taper": 0.55, "taper_inner": 0.4},
}


def brow_config(bc):
    """Brow preset (bc.shape) merged under the spec's own values."""
    shape = bc.get("shape")
    if shape is None:
        return dict(bc)
    if shape not in BROW_PRESETS:
        raise ValueError(f"face.brows.shape {shape!r}: {sorted(BROW_PRESETS)}")
    return {**BROW_PRESETS[shape], **bc}


def brow_widths(bc, n):
    """Width profile of a v2 brow stroke: tapered at both ends (taper_inner at the inner end, taper at the outer),
    fullest a little inside the middle; soft and felt-like rather than a bar."""
    th = _f(bc, "thick_m", 0.004)
    ti, to = _f(bc, "taper_inner", 0.3), _f(bc, "taper", 0.5)
    out = []
    for i in range(n):
        t = i / (n - 1)
        body = math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.5
        out.append(th * body * (1 - ti * (1 - t) ** 2) * (1 - to * t ** 1.5))
    return out


# ------------------------------------------------------------------------------------------------ mouth v2
def lip_fullness(mouth, cfg):
    """Fuller lips (face_generic/2; spec face.mouth.fullness {upper, lower, forward_m}): the outer lip rows move away
    from the seam (upper/lower = height factors, 1 = unchanged) and the lip body pushes forward into a soft pillow
    (forward_m at the middle of each lip, fading to the corners and to the outer edge). The same displacement is
    added to every shape key, so the action units keep their relative motion."""
    import numpy as np
    fl = cfg.get("fullness")
    if not fl:
        return None
    n = int(mouth["ps_lip_rows"])
    me = mouth.data
    nv = len(me.vertices)
    rows = nv // n
    kb = me.shape_keys.key_blocks
    base = np.empty(nv * 3)
    kb[0].data.foreach_get("co", base)
    base = base.reshape(rows, n, 3)
    seam_up, seam_lo = list(mouth["ps_seam_rows"])
    mid_z = (base[seam_up, :, 2] + base[seam_lo, :, 2]) / 2
    fu, flo, fwd = _f(fl, "upper", 1.0), _f(fl, "lower", 1.0), _f(fl, "forward_m", 0.0)
    delta = np.zeros_like(base)
    u = np.linspace(-1, 1, n)
    env = np.sqrt(np.clip(1 - u * u, 0, 1))
    for rr in range(rows):
        f = fu if rr <= seam_up else flo
        dz = base[rr, :, 2] - mid_z
        delta[rr, :, 2] = dz * (f - 1.0)
        if rr in (0, rows - 1):
            continue  # outer edge stays on the skin
        delta[rr, :, 1] = -fwd * env * (1.0 if rr <= seam_up else _f(fl, "lower_forward", 1.2))
    d = delta.ravel()
    for k in kb:
        c = np.empty(nv * 3)
        k.data.foreach_get("co", c)
        k.data.foreach_set("co", c + d)
    me.vertices.foreach_set("co", (base.ravel() + d))
    me.update()
    return {"upper": fu, "lower": flo, "forward_m": fwd}


REST_SHAPES_V2 = {"closed_smile": {}, "open_smile": {"MouthWide": 0.8, "MouthSmile": 0.4}, "small_o": {"MouthO": 0.9},
                  "pout": {"MouthFrown": 0.5, "MouthPout": 0.6},
                  # soft closed smile with cheek lift (owner decision 2026-11-17, girl ref_34)
                  "soft_smile": {"MouthSmile": 0.35, "CheekRaise": 0.6},
                  # lips slightly parted (third character while watching)
                  "parted": {"MouthO": 0.25, "MouthWide": 0.12}}
RELEASE_V2 = ("MouthSmile", "MouthFrown", "CheekRaise")  # keys that keep their absolute target over a baked rest


def bake_rest_shape_v2(objs, shape, mix=None, release=RELEASE_V2):
    """face_generic/2 rest shape: like bake_rest_shape, but `mix` (spec face.mouth.rest_mix) is honoured for every
    shape (also closed_smile), and the keys in `release` keep their absolute target (their full weight reaches the
    same shape as without the rest; e.g. Frown is not weakened by a baked soft smile)."""
    import numpy as np
    if shape not in REST_SHAPES_V2:
        raise ValueError(f"face.mouth.rest_shape {shape!r}: {sorted(REST_SHAPES_V2)}")
    w = dict(mix) if mix else REST_SHAPES_V2[shape]
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
            if k.name in release:
                continue
            d = np.empty(n)
            k.data.foreach_get("co", d)
            k.data.foreach_set("co", d + delta)
        ob.data.vertices.foreach_set("co", base + delta)
        ob.data.update()
        done.append(ob.name)
    return done


def add_cheek_raise(head, landmarks, cfg, ex, ez):
    """Action unit CheekRaise (face_generic/2): the cheeks lift and round forward (the soft smile's cheek lift, also
    usable by presets). cfg (spec face.cheeks): raise_m, forward_m, radius_m, below_eye_m, x (fraction of the eye x)."""
    import numpy as np
    raise_m, fwd = _f(cfg, "raise_m", 0.003), _f(cfg, "forward_m", 0.002)
    if raise_m == 0 and fwd == 0:
        return None
    rad = _f(cfg, "radius_m", 0.035)
    me = head.data
    n = len(me.vertices)
    if me.shape_keys is None:
        head.shape_key_add(name="Basis")
    kb = me.shape_keys.key_blocks
    base = np.empty(n * 3)
    kb[0].data.foreach_get("co", base)
    base = base.reshape(n, 3)
    mw = np.array(head.matrix_world)
    world = base @ mw[:3, :3].T + mw[:3, 3]
    front = 1.0 - _smooth((world[:, 1] - (landmarks["mouth"].y + 0.02)) / 0.02)  # the front of the face, faded
    delta = np.zeros_like(world)
    for sx, _ in SIDES:
        c = np.array([sx * ex * _f(cfg, "x", 1.0), 0.0, ez - _f(cfg, "below_eye_m", 0.04)])
        fr = front > 0.5
        c[1] = world[fr][np.argmin(np.linalg.norm(world[fr][:, [0, 2]] - c[[0, 2]], axis=1)), 1]
        dd = np.linalg.norm(world - c, axis=1) / rad
        g = np.exp(-dd * dd) * front
        delta += np.outer(g, [0.0, -fwd, raise_m])
    mi = np.linalg.inv(mw)
    k = head.shape_key_add(name="CheekRaise", from_mix=False)
    k.value = 0.0
    k.data.foreach_set("co", (base + delta @ mi[:3, :3].T).ravel())
    return {"raise_m": raise_m, "forward_m": fwd, "radius_m": rad}


def refine_eye_regions(head, frames, r, reach=1.8, cuts=2):
    """Subdivides the head faces around each eye (every vertex within reach x radius of an eye centre, in front of
    it), smooth subdivision (new vertices on a smooth surface, the original vertices do not move), so the lid creases
    of the socket stay smooth and the refined patch shades like the rest of the face. Vertex data (groups, UVs) are
    interpolated by bmesh. Returns the number of faces subdivided."""
    import bmesh
    me = head.data
    bm = bmesh.new()
    bm.from_mesh(me)
    mw = head.matrix_world
    cs = [(T.translation.copy(), T.inverted()) for T in frames]
    sel = set()
    for f in bm.faces:
        ok = True
        for v in f.verts:
            w = mw @ v.co
            if not any((Ti @ w).length < reach * r and (Ti @ w).y < 0.3 * r for c, Ti in cs):
                ok = False
                break
        if ok:
            sel.add(f)
    edges = list({e for f in sel for e in f.edges})
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True, smooth=1.0)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(sel)


def lids_follow_skin(head, lids, names, reach_m=0.012):
    """The lower lid shells ride on the skin around them (face_generic/2): for every head key in `names` (e.g.
    MouthSmile, CheekRaise), each lid vertex gets the displacement of the nearest head vertex (weighted down with the
    distance, 0 beyond reach_m), added to the lid's key of the same name (made if missing). Keeps the cheek lift from
    pushing the blended under-eye skin through the lid."""
    import numpy as np
    from mathutils.kdtree import KDTree
    sk = head.data.shape_keys
    if sk is None:
        return []
    kb = sk.key_blocks
    n = len(head.data.vertices)
    mw = head.matrix_world
    base = np.empty(n * 3)
    kb[0].data.foreach_get("co", base)
    base = base.reshape(n, 3)
    kd = KDTree(n)
    for i in range(n):
        kd.insert(mw @ Vector(base[i]), i)
    kd.balance()
    done = []
    for name in names:
        if name not in kb:
            continue
        cur = np.empty(n * 3)
        kb[name].data.foreach_get("co", cur)
        disp = (cur.reshape(n, 3) - base) @ np.array(mw.to_3x3()).T
        for lid in lids:
            lmw = lid.matrix_world
            li = np.array(lmw.inverted().to_3x3())
            if lid.data.shape_keys is None:
                lid.shape_key_add(name="Basis")
            lkb = lid.data.shape_keys.key_blocks
            m = len(lid.data.vertices)
            lb = np.empty(m * 3)
            lkb[0].data.foreach_get("co", lb)
            lb = lb.reshape(m, 3)
            add = np.zeros((m, 3))
            for j in range(m):
                co, idx, dist = kd.find(lmw @ Vector(lb[j]))
                w = max(0.0, 1.0 - dist / reach_m)
                if w > 0:
                    add[j] = disp[idx] * w
            if not add.any():
                continue
            if name in lkb:
                k = lkb[name]
                c = np.empty(m * 3)
                k.data.foreach_get("co", c)
            else:
                k = lid.shape_key_add(name=name, from_mix=False)
                k.value = 0.0
                c = lb.ravel().copy()
            k.data.foreach_set("co", c + (add @ li.T).ravel())
            done.append(f"{lid.name}:{name}")
    return done


def taper_key_front(head, name, y_cut, width=0.012):
    """Tapers a head shape key's displacement to zero towards a hard front cut-off at y_cut (the smile coupling only
    moves vertices in front of y_cut; without the taper the cheeks get a step there). face_generic/2 only."""
    import numpy as np
    sk = head.data.shape_keys
    if sk is None or name not in sk.key_blocks:
        return False
    kb = sk.key_blocks
    n = len(head.data.vertices)
    base = np.empty(n * 3)
    kb[0].data.foreach_get("co", base)
    cur = np.empty(n * 3)
    kb[name].data.foreach_get("co", cur)
    base, cur = base.reshape(n, 3), cur.reshape(n, 3)
    mw = np.array(head.matrix_world)
    y = (base @ mw[:3, :3].T + mw[:3, 3])[:, 1]
    w = 1.0 - _smooth((y - (y_cut - width)) / width)
    kb[name].data.foreach_set("co", (base + (cur - base) * w[:, None]).ravel())
    return True
