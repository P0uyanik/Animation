"""T-110 felt surface (presets/4): one shared Geometry Nodes fibre halo for every felt surface.

The references show one consistent felt surface: skin, garments and hair edges all carry the same soft fibre halo
that is visible where a surface turns away from the camera (silhouettes) and nearly invisible face-on. This module is
the single implementation of that halo:

* ``halo_node_group()`` - the shared Geometry Nodes group ``PS Felt Halo/1``. It passes its input geometry through
  and joins short, tapered, randomly tilted curve fibres distributed over the surface object (optionally only over
  the faces of one material). Each fibre stores its root surface normal (``ps_halo_normal``) and a tone.
* ``halo_material()`` - the halo fibre shader: a Principled Hair strand whose opacity follows the root normal's
  facing ratio (silhouette weight), so the halo reads at the edges, plus a tip fade.
* ``add_halo_modifier()`` - adds the group as a modifier to a curves object (the surface-fibre object built by
  ``builder.add_fibres_geometry`` for hair and garments, or a halo-only curves object).
* ``add_missing_halos()`` - the post-build pass for surfaces that the build never routes through the fibre path (the
  skin): every non-garment mesh whose material carries a presets/4 halo and that has no halo yet gets one halo object.

Density, length and colour are per preset (``halo`` section of ``presets_felt.json``). Only presets/4 ids carry a
halo, so every presets/1..3 build is unchanged: nothing in this module runs for them.
"""
import json
import math

HALO_GROUP = "PS Felt Halo/1"
HALO_GROUP_VERSION = 1
HALO_NORMAL_ATTRIBUTE = "ps_halo_normal"
HALO_TONE_ATTRIBUTE = "ps_halo_tone"
HALO_MATERIAL_PROP = "ps_felt_halo"       # on a surface material: the presets/4 assignment (JSON)
HALO_OBJECT_PROP = "ps_felt_halo_source"  # on a curves object carrying a halo: the source mesh name
HALO_FIELDS = ("density_per_cm2", "length_mm", "spread", "opacity", "facing_floor", "silhouette_power",
               "tip_transparency", "color_value", "color_saturation", "radius_fraction", "lod")
HALO_RANGES = {"density_per_cm2": (0.0, 400.0), "length_mm": (0.05, 20.0), "spread": (0.0, 1.0),
               "opacity": (0.0, 1.0), "facing_floor": (0.0, 1.0), "silhouette_power": (0.1, 8.0),
               "tip_transparency": (0.0, 1.0), "color_value": (0.2, 3.0), "color_saturation": (0.0, 2.0),
               "radius_fraction": (0.01, 0.4), "lod": (0.0, 1.0)}


def halo_errors(halo, label):
    """Validation of one resolved ``halo`` section (plain Python)."""
    if not isinstance(halo, dict):
        return [f"{label} must be an object"]
    errors = []
    if not isinstance(halo.get("enabled"), bool):
        errors.append(f"{label}.enabled must be a boolean")
    for field in HALO_FIELDS:
        value = halo.get(field)
        lo, hi = HALO_RANGES[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
            errors.append(f"{label}.{field} must be a number in [{lo}, {hi}]")
    unknown = sorted(set(halo) - set(HALO_FIELDS) - {"enabled"})
    if unknown:
        errors.append(f"{label} has unknown fields {unknown}")
    return errors


def halo_color_srgb(base_srgb, halo):
    """The halo strand colour: the surface base colour with the preset's value and saturation factors."""
    import colorsys
    r, g, b = (max(0.0, min(255.0, float(c))) / 255.0 for c in base_srgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = max(0.0, min(1.0, s * float(halo["color_saturation"])))
    v = max(0.0, min(1.0, v * float(halo["color_value"])))
    return tuple(round(c * 255.0, 4) for c in colorsys.hsv_to_rgb(h, s, v))


def halo_settings(halo, reference_size_m, library_reference_m, lod="close"):
    """Modifier inputs (SI units) from a halo section; length and density scale with reference size like the
    surface fibres (T-028): length x k, density / k^2."""
    k = float(reference_size_m) / float(library_reference_m)
    density = float(halo["density_per_cm2"]) * 10000.0 / (k * k)
    if lod == "wide":
        density *= float(halo["lod"])
    return {"density": density, "length": float(halo["length_mm"]) / 1000.0 * k, "spread": float(halo["spread"]),
            "radius_fraction": float(halo["radius_fraction"]), "k": k}


def _math(nodes, operation, a=None, b=None, label=""):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    node.label = label
    if isinstance(a, (int, float)):
        node.inputs[0].default_value = a
    if isinstance(b, (int, float)):
        node.inputs[1].default_value = b
    return node


def halo_node_group():
    """The single shared halo generator (created once per file)."""
    import bpy
    existing = bpy.data.node_groups.get(HALO_GROUP)
    if existing is not None:
        return existing
    group = bpy.data.node_groups.new(HALO_GROUP, "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    for name, socket_type in (("Surface", "NodeSocketObject"), ("Use Selection", "NodeSocketBool"),
                              ("Selection Material", "NodeSocketMaterial"), ("Density", "NodeSocketFloat"),
                              ("Length", "NodeSocketFloat"), ("Spread", "NodeSocketFloat"),
                              ("Radius Fraction", "NodeSocketFloat"), ("Seed", "NodeSocketInt"),
                              ("Material", "NodeSocketMaterial")):
        socket = group.interface.new_socket(name=name, in_out="INPUT", socket_type=socket_type)
        if name == "Length":
            socket.subtype = "DISTANCE"
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = group.nodes, group.links
    gin, gout = nodes.new("NodeGroupInput"), nodes.new("NodeGroupOutput")

    surface = nodes.new("GeometryNodeObjectInfo")
    surface.transform_space = "ORIGINAL"
    links.new(gin.outputs["Surface"], surface.inputs["Object"])
    # Selection: every face, or only the faces of one material (a skin mesh with several material slots).
    mat_sel = nodes.new("GeometryNodeMaterialSelection")
    links.new(gin.outputs["Selection Material"], mat_sel.inputs["Material"])
    use_all = nodes.new("FunctionNodeBooleanMath")
    use_all.operation = "NOT"
    links.new(gin.outputs["Use Selection"], use_all.inputs[0])
    either = nodes.new("FunctionNodeBooleanMath")
    either.operation = "OR"
    links.new(use_all.outputs[0], either.inputs[0])
    links.new(mat_sel.outputs["Selection"], either.inputs[1])
    distribute = nodes.new("GeometryNodeDistributePointsOnFaces")
    distribute.distribute_method = "RANDOM"
    links.new(surface.outputs["Geometry"], distribute.inputs["Mesh"])
    links.new(either.outputs[0], distribute.inputs["Selection"])
    links.new(gin.outputs["Density"], distribute.inputs["Density"])
    seed = _math(nodes, "ADD", b=31337.0, label="Halo seed")
    links.new(gin.outputs["Seed"], seed.inputs[0])
    links.new(seed.outputs[0], distribute.inputs["Seed"])
    # Root surface normal on every point (becomes a per-curve attribute after realizing).
    store_n = nodes.new("GeometryNodeStoreNamedAttribute")
    store_n.data_type = "FLOAT_VECTOR"
    store_n.domain = "POINT"
    store_n.inputs["Name"].default_value = HALO_NORMAL_ATTRIBUTE
    links.new(distribute.outputs["Points"], store_n.inputs["Geometry"])
    links.new(distribute.outputs["Normal"], store_n.inputs["Value"])

    # One strand: a short line along +Z with a slight arc, 5 points, tapered radius.
    line = nodes.new("GeometryNodeCurvePrimitiveLine")
    line.mode = "DIRECTION"
    line.inputs["Direction"].default_value = (0.0, 0.0, 1.0)
    links.new(gin.outputs["Length"], line.inputs["Length"])
    resample = nodes.new("GeometryNodeResampleCurve")
    resample.inputs["Count"].default_value = 5
    links.new(line.outputs["Curve"], resample.inputs["Curve"])
    param = nodes.new("GeometryNodeSplineParameter")
    arc_sq = _math(nodes, "POWER", b=2.0, label="Arc profile")
    links.new(param.outputs["Factor"], arc_sq.inputs[0])
    arc_len = _math(nodes, "MULTIPLY", b=0.35, label="Arc by length")
    links.new(gin.outputs["Length"], arc_len.inputs[0])
    arc = _math(nodes, "MULTIPLY", label="Arc offset")
    links.new(arc_sq.outputs[0], arc.inputs[0])
    links.new(arc_len.outputs[0], arc.inputs[1])
    offset = nodes.new("ShaderNodeCombineXYZ")
    links.new(arc.outputs[0], offset.inputs["X"])
    set_pos = nodes.new("GeometryNodeSetPosition")
    links.new(resample.outputs["Curve"], set_pos.inputs["Geometry"])
    links.new(offset.outputs["Vector"], set_pos.inputs["Offset"])
    radius = _math(nodes, "MULTIPLY", label="Root radius")
    links.new(gin.outputs["Length"], radius.inputs[0])
    links.new(gin.outputs["Radius Fraction"], radius.inputs[1])
    tip = _math(nodes, "MULTIPLY", b=0.2, label="Tip radius")
    links.new(radius.outputs[0], tip.inputs[0])
    taper = nodes.new("ShaderNodeMapRange")
    taper.clamp = True
    links.new(param.outputs["Factor"], taper.inputs["Value"])
    links.new(radius.outputs[0], taper.inputs["To Min"])
    links.new(tip.outputs[0], taper.inputs["To Max"])
    set_radius = nodes.new("GeometryNodeSetCurveRadius")
    links.new(set_pos.outputs["Geometry"], set_radius.inputs["Curve"])
    links.new(taper.outputs["Result"], set_radius.inputs["Radius"])

    inst = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(store_n.outputs["Geometry"], inst.inputs["Points"])
    links.new(set_radius.outputs["Curve"], inst.inputs["Instance"])
    links.new(distribute.outputs["Rotation"], inst.inputs["Rotation"])
    rnd_len = nodes.new("FunctionNodeRandomValue")
    rnd_len.data_type = "FLOAT_VECTOR"
    rnd_len.inputs["Min"].default_value = (1.0, 1.0, 0.55)
    rnd_len.inputs["Max"].default_value = (1.0, 1.0, 1.45)
    links.new(seed.outputs[0], rnd_len.inputs["Seed"])
    links.new(rnd_len.outputs["Value"], inst.inputs["Scale"])
    # Tilt about local X (0..spread x 80 deg, felt fibres lie down more than they stand) and a random azimuth.
    rnd_tilt = nodes.new("FunctionNodeRandomValue")
    rnd_tilt.data_type = "FLOAT"
    rnd_tilt.inputs["Min"].default_value = 0.0
    rnd_tilt.inputs["Max"].default_value = 1.0
    seed_t = _math(nodes, "ADD", b=7919.0, label="Tilt seed")
    links.new(seed.outputs[0], seed_t.inputs[0])
    links.new(seed_t.outputs[0], rnd_tilt.inputs["Seed"])
    tilt_range = _math(nodes, "MULTIPLY", b=math.radians(80.0), label="Tilt range")
    links.new(gin.outputs["Spread"], tilt_range.inputs[0])
    tilt = _math(nodes, "MULTIPLY", label="Tilt")
    links.new(rnd_tilt.outputs["Value"], tilt.inputs[0])
    links.new(tilt_range.outputs[0], tilt.inputs[1])
    rnd_az = nodes.new("FunctionNodeRandomValue")
    rnd_az.data_type = "FLOAT"
    rnd_az.inputs["Min"].default_value = 0.0
    rnd_az.inputs["Max"].default_value = math.tau
    seed_a = _math(nodes, "ADD", b=15485.0, label="Azimuth seed")
    links.new(seed.outputs[0], seed_a.inputs[0])
    links.new(seed_a.outputs[0], rnd_az.inputs["Seed"])
    # Spin about the normal first (local Z), then tilt (local X): two rotate steps keep the order explicit.
    spin = nodes.new("GeometryNodeRotateInstances")
    spin.inputs["Local Space"].default_value = True
    links.new(inst.outputs["Instances"], spin.inputs["Instances"])
    spin_e = nodes.new("ShaderNodeCombineXYZ")
    links.new(rnd_az.outputs["Value"], spin_e.inputs["Z"])
    links.new(spin_e.outputs["Vector"], spin.inputs["Rotation"])
    lean = nodes.new("GeometryNodeRotateInstances")
    lean.inputs["Local Space"].default_value = True
    links.new(spin.outputs["Instances"], lean.inputs["Instances"])
    lean_e = nodes.new("ShaderNodeCombineXYZ")
    links.new(tilt.outputs[0], lean_e.inputs["X"])
    links.new(lean_e.outputs["Vector"], lean.inputs["Rotation"])
    realize = nodes.new("GeometryNodeRealizeInstances")
    links.new(lean.outputs["Instances"], realize.inputs["Geometry"])
    rnd_tone = nodes.new("FunctionNodeRandomValue")
    rnd_tone.data_type = "FLOAT"
    seed_c = _math(nodes, "ADD", b=104729.0, label="Tone seed")
    links.new(seed.outputs[0], seed_c.inputs[0])
    links.new(seed_c.outputs[0], rnd_tone.inputs["Seed"])
    store_c = nodes.new("GeometryNodeStoreNamedAttribute")
    store_c.data_type = "FLOAT"
    store_c.domain = "CURVE"
    store_c.inputs["Name"].default_value = HALO_TONE_ATTRIBUTE
    links.new(realize.outputs["Geometry"], store_c.inputs["Geometry"])
    links.new(rnd_tone.outputs["Value"], store_c.inputs["Value"])
    set_mat = nodes.new("GeometryNodeSetMaterial")
    links.new(store_c.outputs["Geometry"], set_mat.inputs["Geometry"])
    links.new(gin.outputs["Material"], set_mat.inputs["Material"])
    join = nodes.new("GeometryNodeJoinGeometry")
    links.new(set_mat.outputs["Geometry"], join.inputs["Geometry"])
    links.new(gin.outputs["Geometry"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], gout.inputs["Geometry"])
    group["ps_felt_halo"] = True
    group["ps_felt_halo_version"] = HALO_GROUP_VERSION
    return group


def halo_material(name, color_srgb, halo):
    """Principled Hair halo strand; opacity = opacity x silhouette weight x tip fade.

    silhouette weight = floor + (1 - floor) * (1 - |N_root . I|)^power: ~floor where the surface faces the camera,
    1 at the silhouette, so the halo shows on edges and only a faint felt fuzz on faces.
    """
    import bpy
    from geom import srgb_to_linear
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    hair = nodes.new("ShaderNodeBsdfHairPrincipled")
    try:
        hair.parametrization = "DIRECT"
    except Exception:
        pass
    lin = srgb_to_linear(color_srgb)
    tone = nodes.new("ShaderNodeAttribute")
    tone.attribute_type = "GEOMETRY"
    tone.attribute_name = HALO_TONE_ATTRIBUTE
    tone_gain = nodes.new("ShaderNodeMapRange")  # +/- 15 % value per strand
    tone_gain.inputs["To Min"].default_value = 0.85
    tone_gain.inputs["To Max"].default_value = 1.15
    links.new(tone.outputs["Fac"], tone_gain.inputs["Value"])
    col = nodes.new("ShaderNodeVectorMath")
    col.operation = "SCALE"
    col.inputs[0].default_value = tuple(lin)
    links.new(tone_gain.outputs["Result"], col.inputs["Scale"])
    links.new(col.outputs[0], hair.inputs["Color"])
    for socket, value in (("Roughness", 0.7), ("Radial Roughness", 0.8), ("Random Roughness", 0.15), ("Coat", 0.0)):
        if socket in hair.inputs:
            hair.inputs[socket].default_value = value
    # silhouette weight from the root normal
    nattr = nodes.new("ShaderNodeAttribute")
    nattr.attribute_type = "GEOMETRY"
    nattr.attribute_name = HALO_NORMAL_ATTRIBUTE
    to_world = nodes.new("ShaderNodeVectorTransform")
    to_world.vector_type = "NORMAL"
    to_world.convert_from = "OBJECT"
    to_world.convert_to = "WORLD"
    links.new(nattr.outputs["Vector"], to_world.inputs["Vector"])
    norm = nodes.new("ShaderNodeVectorMath")
    norm.operation = "NORMALIZE"
    links.new(to_world.outputs["Vector"], norm.inputs[0])
    geo = nodes.new("ShaderNodeNewGeometry")
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    links.new(norm.outputs[0], dot.inputs[0])
    links.new(geo.outputs["Incoming"], dot.inputs[1])
    absd = _math(nodes, "ABSOLUTE", label="facing")
    links.new(dot.outputs["Value"], absd.inputs[0])
    edge = _math(nodes, "SUBTRACT", a=1.0, label="edge")
    links.new(absd.outputs[0], edge.inputs[1])
    powr = _math(nodes, "POWER", b=float(halo["silhouette_power"]), label="silhouette power")
    links.new(edge.outputs[0], powr.inputs[0])
    floor = float(halo["facing_floor"])
    weight = _math(nodes, "MULTIPLY_ADD", b=1.0 - floor, label="silhouette weight")
    weight.inputs[2].default_value = floor
    links.new(powr.outputs[0], weight.inputs[0])
    # tip fade
    info = nodes.new("ShaderNodeHairInfo")
    fade = _math(nodes, "MULTIPLY_ADD", b=-float(halo["tip_transparency"]), label="tip fade")
    fade.inputs[2].default_value = 1.0
    links.new(info.outputs["Intercept"], fade.inputs[0])
    alpha = _math(nodes, "MULTIPLY", label="alpha")
    links.new(weight.outputs[0], alpha.inputs[0])
    links.new(fade.outputs[0], alpha.inputs[1])
    alpha2 = _math(nodes, "MULTIPLY", b=float(halo["opacity"]), label="opacity")
    alpha2.use_clamp = True
    links.new(alpha.outputs[0], alpha2.inputs[0])
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(alpha2.outputs[0], mix.inputs["Fac"])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(hair.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    m["ps_felt_halo_material"] = True
    return m


def _set_input(modifier, group, name, value):
    socket = next(item for item in group.interface.items_tree
                  if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == name)
    getattr(modifier.properties.inputs, socket.identifier).value = value


def seed_for(name):
    return sum((index + 1) * ord(char) for index, char in enumerate(name)) % 100000


def add_halo_modifier(curves_object, surface, preset_name, halo, base_color_srgb, reference_size_m,
                      library_reference_m, lod="close", selection_material=None):
    """Add the shared halo group to a curves object whose transform matches ``surface``. Returns the modifier."""
    group = halo_node_group()
    s = halo_settings(halo, reference_size_m, library_reference_m, lod)
    color = halo_color_srgb(base_color_srgb, halo)
    tag = selection_material.name if selection_material is not None else surface.name
    material = halo_material(f"M_halo_{preset_name}_{tag}", color, halo)
    curves_object.data.materials.append(material)
    mod = curves_object.modifiers.new("PS Felt Halo", "NODES")
    mod.node_group = group
    _set_input(mod, group, "Surface", surface)
    _set_input(mod, group, "Use Selection", selection_material is not None)
    if selection_material is not None:
        _set_input(mod, group, "Selection Material", selection_material)
    _set_input(mod, group, "Density", s["density"])
    _set_input(mod, group, "Length", s["length"])
    _set_input(mod, group, "Spread", s["spread"])
    _set_input(mod, group, "Radius Fraction", s["radius_fraction"])
    _set_input(mod, group, "Seed", seed_for(preset_name + "/" + tag))
    _set_input(mod, group, "Material", material)
    curves_object[HALO_OBJECT_PROP] = surface.name
    curves_object["ps_felt_halo_preset"] = preset_name
    return mod


def new_curves_object(surface, name):
    """An empty curves object on the surface's transform, in the surface's collection."""
    import bpy
    curves = bpy.data.hair_curves.new(name)
    ob = bpy.data.objects.new(name, curves)
    (surface.users_collection[0] if surface.users_collection else bpy.context.scene.collection).objects.link(ob)
    ob.matrix_world = surface.matrix_world.copy()
    if hasattr(curves, "surface"):
        curves.surface = surface
    return ob


def has_halo(surface, material=None):
    import bpy
    for ob in bpy.data.objects:
        if ob.get(HALO_OBJECT_PROP) == surface.name:
            if material is None:
                return True
            for mod in ob.modifiers:
                if mod.type == "NODES" and mod.node_group is not None and mod.node_group.name == HALO_GROUP:
                    sel = getattr(mod.properties.inputs, _ident(mod.node_group, "Selection Material")).value
                    use = getattr(mod.properties.inputs, _ident(mod.node_group, "Use Selection")).value
                    if not use or sel == material:
                        return True
    return False


def _ident(group, name):
    return next(item.identifier for item in group.interface.items_tree
                if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == name)


def add_missing_halos(objects, lod="close"):
    """Post-build pass: every mesh in ``objects`` with a presets/4 halo material (``ps_felt_halo``) that has no halo
    yet (the skin: the build never routes it through the surface-fibre path) gets one halo curves object, parented
    to the mesh with an identity transform (follows deformation like the garment fibres). One modifier per halo
    material on the mesh, restricted to that material's faces. Returns the new objects."""
    from materials import builder as B
    made = []
    for surface in sorted((o for o in objects if o.type == "MESH"), key=lambda o: o.name):
        if surface.get(HALO_OBJECT_PROP) or surface.hide_render or surface.get("ps_garment_item") is not None:
            continue  # garment pieces get (or deliberately skip) their halo through the surface-fibre path
        halo_mats = []
        for mat in surface.data.materials:
            if mat is not None and mat.get(HALO_MATERIAL_PROP) and mat not in halo_mats:
                halo_mats.append(mat)
        halo_mats = [m for m in halo_mats if not has_halo(surface, m)]
        if not halo_mats:
            continue
        multi = len([m for m in surface.data.materials if m is not None]) > 1
        target = None
        for mat in halo_mats:
            asg = json.loads(mat[HALO_MATERIAL_PROP])
            preset = B.resolve_preset(asg["preset"], asg.get("overrides"))
            halo = preset.get("halo") or {}
            if not halo.get("enabled") or lod == "off":
                continue
            if target is None:
                target = new_curves_object(surface, surface.name + ".halo")
                target.parent = surface
                target.matrix_parent_inverse.identity()
                target.matrix_basis.identity()
            library = B.library_for(asg["preset"])
            add_halo_modifier(target, surface, asg["preset"], halo, asg["base_color_srgb"],
                              asg.get("reference_size_m") or library["reference_size_m"], B.load_library()["reference_size_m"],
                              lod, mat if multi else None)
        if target is not None:
            made.append(target)
    return made
