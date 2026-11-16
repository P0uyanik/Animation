"""Data-driven Cycles material construction.

The module is importable in ordinary Python: Blender is imported only by the
functions that create or edit a material. Character specs remain byte/render
compatible because no caller enters this code without an explicit assignment.
"""
import copy
import colorsys
import json
import math
import os


SCHEMA = "plush-studio.material-presets/1"
HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS_PATH = os.path.join(HERE, "presets.json")
KINDS = {"noise", "yarn", "knit", "weave", "denim"}
FIBRE_LODS = {"close", "wide", "off"}
FIBRE_GROUP = "PS Shared Surface Fibres/1"
FIBRE_GROUP_VERSION = 2
# T-026 per-fibre look controls (all 0..1): stochastic per-strand value spread, tilt spread around the authored lean,
# and alpha fade at the root (blends into the surface) and the tip (soft halo instead of hard ends).
FIBRE_LOOK_FIELDS = ("color_variation", "lean_variation", "root_transparency", "tip_transparency")
FIBRE_TONE_ATTRIBUTE = "ps_fibre_tone"
# T-028 mid-scale nap/clump highlight layer ("nap" preset section). VISUAL_TARGET's sheen ratio removes form with a
# 31 px blur and the fuzz metric removes everything above a 9 px blur, so a P90/P50 >= 1.08 needs ~8 % relative
# luminance structure in the 9-31 px band at H = 256 (nap clumps, fibre-broken highlights) that fuzz barely sees.
# The layer is one smooth clump mask (a reference-scaled noise through a smoothstep window); inside a clump the
# albedo is lifted, between clumps it is lowered, the Principled sheen grows and a broad bump tilts the clump so its
# highlight follows the light. The same mask tints the generated fibres, so nap reads through dense fibres.
# T-028 iteration 1: broad 40-50 %-coverage clumps that also darken the gaps read as camouflage before the metric moves.
# The layer is therefore positive and sparse: a high threshold leaves ~10-15 % of the surface as clump tips, the
# per-axis ``anisotropy`` stretches them into streaks along the nap, and ``roughness_drop`` makes the tips glossier so
# the lift is a light-catching highlight rather than paint.
NAP_FIELDS = ("scale_per_reference", "detail", "roughness", "distortion", "threshold", "softness", "value_gain",
              "value_shadow", "sheen_gain", "roughness_drop", "fibre_gloss", "bump_strength", "distance_fraction")
# ``fibre_gloss`` (0..1): generated fibres lower their Principled Hair roughness by up to this fraction, fully on a clump
# and by half elsewhere, so clump fibres throw strand-shaped glints where the light catches them - the "highlights
# broken by fibre" of the VISUAL_TARGET benchmark sleeves - instead of a painted lift.
FIBRE_ROUGHNESS = 0.64
# fibre.coordinates: "object" (default, object space) or "uv" (the mesh's "ps_fibre" UV map, e.g. groom ropes: U around
# the rope, V along it, in metres), so directional fibre patterns follow the geometry instead of object axes.
COORDINATES = {"object", "uv"}
FIBRE_UV = "ps_fibre"


def deep_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_library(path=PRESETS_PATH):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    errors = validate_library(data)
    if errors:
        raise ValueError("invalid material preset library: " + "; ".join(errors))
    return data


def _range_errors(value, label):
    if value is None:
        return []
    if not isinstance(value, dict) or set(value) != {"range", "source"}:
        return [f"{label} must be null or contain range and source"]
    bounds = value.get("range")
    if (not isinstance(bounds, list) or len(bounds) != 2 or
            not all(isinstance(v, (int, float)) for v in bounds) or bounds[0] > bounds[1]):
        return [f"{label}.range must be an ordered numeric pair"]
    if not isinstance(value.get("source"), str) or not value["source"]:
        return [f"{label}.source must be non-empty"]
    return []


def validate_library(data):
    errors = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if not isinstance(data.get("reference_size_m"), (int, float)) or data.get("reference_size_m", 0) <= 0:
        errors.append("reference_size_m must be positive")
    defaults = data.get("defaults")
    if not isinstance(defaults, dict):
        errors.append("defaults must be an object")
        defaults = {}
    for section in ("surface", "fibre", "micro_relief", "nap", "fibres", "silhouette"):
        if not isinstance(defaults.get(section), dict):
            errors.append(f"defaults.{section} must be an object")
    presets = data.get("presets")
    if not isinstance(presets, dict) or not presets:
        errors.append("presets must be a non-empty object")
        return errors
    target_names = {"fuzz_rms_y255", "sheen_p90_p50", "saturation_retention_percent"}
    for name, raw in presets.items():
        if not isinstance(raw, dict):
            errors.append(f"preset {name} must be an object")
            continue
        resolved = deep_merge(defaults, raw)
        color = resolved.get("swatch_srgb")
        if (not isinstance(color, list) or len(color) != 3 or
                not all(isinstance(v, (int, float)) and 0 <= v <= 255 for v in color)):
            errors.append(f"{name}.swatch_srgb must be three 0..255 values")
        fibre = resolved.get("fibre", {})
        if fibre.get("kind") not in KINDS:
            errors.append(f"{name}.fibre.kind must be one of {sorted(KINDS)}")
        if not isinstance(fibre.get("scale_per_reference"), (int, float)) or fibre.get("scale_per_reference", 0) <= 0:
            errors.append(f"{name}.fibre.scale_per_reference must be positive")
        if not isinstance(fibre.get("distance_fraction"), (int, float)) or fibre.get("distance_fraction", -1) < 0:
            errors.append(f"{name}.fibre.distance_fraction must be non-negative")
        if fibre.get("coordinates", "object") not in COORDINATES:
            errors.append(f"{name}.fibre.coordinates must be one of {sorted(COORDINATES)}")
        micro = resolved.get("micro_relief", {})
        for field in ("scale_per_reference", "detail", "roughness", "strength", "distance_fraction",
                      "color_strength", "roughness_variation"):
            if not isinstance(micro.get(field), (int, float)) or micro.get(field, -1) < 0:
                errors.append(f"{name}.micro_relief.{field} must be non-negative")
        fibres = resolved.get("fibres", {})
        if not isinstance(fibres.get("enabled"), bool):
            errors.append(f"{name}.fibres.enabled must be a boolean")
        for field in ("density_per_cm2", "length_mm", "curl", "lean", "lod"):
            if not isinstance(fibres.get(field), (int, float)) or fibres.get(field, -1) < 0:
                errors.append(f"{name}.fibres.{field} must be non-negative")
        if not 0 <= fibres.get("lod", -1) <= 1:
            errors.append(f"{name}.fibres.lod must be in 0..1")
        for field in FIBRE_LOOK_FIELDS:
            value = fibres.get(field, 0.0)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"{name}.fibres.{field} must be in 0..1")
        nap = resolved.get("nap", {})
        if not isinstance(nap.get("enabled"), bool):
            errors.append(f"{name}.nap.enabled must be a boolean")
        for field in NAP_FIELDS:
            if not isinstance(nap.get(field), (int, float)) or nap.get(field, -1) < 0:
                errors.append(f"{name}.nap.{field} must be non-negative")
        if not 0 <= nap.get("value_shadow", 0.0) < 1:
            errors.append(f"{name}.nap.value_shadow must be in [0, 1)")
        if nap.get("softness", 1.0) <= 0:
            errors.append(f"{name}.nap.softness must be positive")
        if not 0 <= nap.get("fibre_gloss", 0.0) < 1:
            errors.append(f"{name}.nap.fibre_gloss must be in [0, 1)")
        if not 0 <= nap.get("roughness_drop", 0.0) < 1:
            errors.append(f"{name}.nap.roughness_drop must be in [0, 1)")
        stretch = nap.get("anisotropy")
        if (not isinstance(stretch, list) or len(stretch) != 3 or
                not all(isinstance(v, (int, float)) and v > 0 for v in stretch)):
            errors.append(f"{name}.nap.anisotropy must be three positive numbers")
        silhouette = resolved.get("silhouette", {})
        if silhouette.get("mode") != "sheen_layer":
            errors.append(f"{name}.silhouette.mode must be sheen_layer")
        targets = raw.get("targets")
        if not isinstance(targets, dict) or set(targets) != target_names:
            errors.append(f"{name}.targets must contain {sorted(target_names)}")
        else:
            for metric, target in targets.items():
                errors += _range_errors(target, f"{name}.targets.{metric}")
    return errors


def resolve_preset(name, overrides=None, library=None):
    library = library or load_library()
    if name not in library["presets"]:
        raise KeyError(f"unknown material preset: {name}")
    resolved = deep_merge(library["defaults"], library["presets"][name])
    resolved = deep_merge(resolved, overrides)
    resolved["name"] = name
    return resolved


def get_assignment(materials_spec, slot):
    """Return one opt-in assignment, or None for the exact legacy path."""
    assignments = (materials_spec or {}).get("assignments") or {}
    return assignments.get(slot)


def validate_assignments(materials_spec, library=None):
    assignments = (materials_spec or {}).get("assignments")
    if assignments is None:
        return []
    if not isinstance(assignments, dict):
        return ["materials.assignments must be an object or null"]
    library = library or load_library()
    errors = []
    for slot, assignment in assignments.items():
        label = f"materials.assignments.{slot}"
        if not isinstance(assignment, dict):
            errors.append(f"{label} must be an object")
            continue
        if assignment.get("preset") not in library["presets"]:
            errors.append(f"{label}.preset is unknown: {assignment.get('preset')}")
        color = assignment.get("base_color_srgb")
        if (not isinstance(color, list) or len(color) != 3 or
                not all(isinstance(v, (int, float)) and 0 <= v <= 255 for v in color)):
            errors.append(f"{label}.base_color_srgb must be three 0..255 values")
        ref = assignment.get("reference_size_m", library["reference_size_m"])
        if not isinstance(ref, (int, float)) or ref <= 0:
            errors.append(f"{label}.reference_size_m must be positive")
        if "overrides" in assignment and not isinstance(assignment["overrides"], dict):
            errors.append(f"{label}.overrides must be an object")
    return errors


def _input(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    return None


def _set(node, value, *names):
    socket = _input(node, *names)
    if socket is not None:
        socket.default_value = value


def _tag(node, name):
    node.name = "PS " + name
    node.label = name
    node["ps_material_library"] = True
    return node


def _new(nodes, node_type, name):
    return _tag(nodes.new(node_type), name)


def _srgb_to_linear(color):
    from geom import srgb_to_linear
    return srgb_to_linear(color)


def _saturate_srgb(color, factor):
    rgb = tuple(float(v) / (255.0 if max(color) > 1.0 else 1.0) for v in color)
    hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
    out = colorsys.hsv_to_rgb(hue, min(1.0, saturation * float(factor)), value)
    return tuple(v * 255.0 for v in out)


def _principled(material):
    nodes = material.node_tree.nodes
    return nodes.get("Principled BSDF") or next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)


def _clear_generated_nodes(material):
    nodes = material.node_tree.nodes
    for node in list(nodes):
        if node.get("ps_material_library"):
            nodes.remove(node)


def _noise(nodes, links, vector, fibre):
    noise = _new(nodes, "ShaderNodeTexNoise", "Fibre Noise")
    _set(noise, float(fibre["scale_per_reference"]), "Scale")
    _set(noise, float(fibre.get("detail", 8.0)), "Detail")
    _set(noise, float(fibre.get("roughness", 0.7)), "Roughness")
    _set(noise, float(fibre.get("distortion", 0.0)), "Distortion")
    links.new(vector, noise.inputs["Vector"])
    return noise.outputs["Fac"]


def _wave(nodes, links, vector, fibre, direction, scale=1.0):
    wave = _new(nodes, "ShaderNodeTexWave", f"Fibre {direction} Wave")
    wave.wave_type = "BANDS"
    wave.bands_direction = direction
    _set(wave, float(fibre["scale_per_reference"]) * scale, "Scale")
    _set(wave, float(fibre.get("distortion", 0.0)), "Distortion")
    _set(wave, float(fibre.get("detail", 4.0)), "Detail")
    _set(wave, float(fibre.get("roughness", 0.6)), "Detail Roughness")
    links.new(vector, wave.inputs["Vector"])
    return wave.outputs["Color"]


def _pattern(nodes, links, vector, fibre):
    noise = _noise(nodes, links, vector, fibre)
    kind = fibre["kind"]
    if kind == "noise":
        return noise
    if kind == "denim":
        mapping = _new(nodes, "ShaderNodeMapping", "Twill Rotation")
        mapping.inputs["Rotation"].default_value[1] = 0.785398
        links.new(vector, mapping.inputs["Vector"])
        a = _wave(nodes, links, mapping.outputs["Vector"], fibre, "X")
        mix = _new(nodes, "ShaderNodeMath", "Twill Breakup")
        mix.operation = "MULTIPLY"
        links.new(a, mix.inputs[0])
        links.new(noise, mix.inputs[1])
        return mix.outputs[0]
    a = _wave(nodes, links, vector, fibre, "X")
    b = _wave(nodes, links, vector, fibre, "Z", 0.5 if kind == "yarn" else 1.0)
    mix = _new(nodes, "ShaderNodeMath", "Fibre Pattern")
    mix.operation = "MULTIPLY" if kind in ("weave", "knit") else "ADD"
    links.new(a, mix.inputs[0])
    links.new(b, mix.inputs[1])
    breakup = _new(nodes, "ShaderNodeMath", "Pattern Breakup")
    breakup.operation = "MULTIPLY"
    links.new(mix.outputs[0], breakup.inputs[0])
    links.new(noise, breakup.inputs[1])
    return breakup.outputs[0]


def _micro_relief(material, principled, vector, reference, micro, base):
    """Add fine, reference-scaled relief that remains readable after OIDN.

    The primary fibre pattern describes weave/nap.  This second octave is kept
    independent so it can be fine enough for 1--2 px fibre breakup without
    forcing the broad pattern into noisy, repeating clumps.
    """
    if not micro.get("enabled", True):
        return None
    nodes, links = material.node_tree.nodes, material.node_tree.links
    noise = _new(nodes, "ShaderNodeTexNoise", "Micro Fibre Relief")
    _set(noise, float(micro["scale_per_reference"]), "Scale")
    _set(noise, float(micro["detail"]), "Detail")
    _set(noise, float(micro["roughness"]), "Roughness")
    links.new(vector, noise.inputs["Vector"])

    normal = _input(principled, "Normal")
    previous = next((link.from_socket for link in normal.links), None)
    bump = _new(nodes, "ShaderNodeBump", "Micro Fibre Normal")
    bump.inputs["Strength"].default_value = float(micro["strength"])
    bump.inputs["Distance"].default_value = reference * float(micro["distance_fraction"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    if previous is not None:
        links.new(previous, bump.inputs["Normal"])
    links.new(bump.outputs["Normal"], normal)

    roughness = _input(principled, "Roughness")
    variation = float(micro.get("roughness_variation", 0.0))
    if variation > 0.0:
        centre = float(roughness.default_value)
        ramp = _new(nodes, "ShaderNodeMapRange", "Broken Fibre Roughness")
        ramp.clamp = True
        # Noise Fac spends most of its area around 0.3--0.7.  Expanding that
        # useful band makes the authored variation survive low-sample OIDN;
        # mapping the unreachable 0--1 extrema made every preset nearly flat.
        ramp.inputs["From Min"].default_value = 0.3
        ramp.inputs["From Max"].default_value = 0.7
        ramp.inputs["To Min"].default_value = max(0.02, centre - variation)
        ramp.inputs["To Max"].default_value = min(1.0, centre + variation)
        links.new(noise.outputs["Fac"], ramp.inputs["Value"])
        links.new(ramp.outputs["Result"], roughness)

    color_strength = float(micro.get("color_strength", 0.0))
    if color_strength > 0.0:
        source = next((link.from_socket for link in base.links), None)
        modulation = _new(nodes, "ShaderNodeMapRange", "Fibre Albedo Variation")
        modulation.clamp = True
        modulation.inputs["From Min"].default_value = 0.3
        modulation.inputs["From Max"].default_value = 0.7
        modulation.inputs["To Min"].default_value = 1.0 - color_strength
        modulation.inputs["To Max"].default_value = 1.0 + color_strength
        links.new(noise.outputs["Fac"], modulation.inputs["Value"])
        multiply = _new(nodes, "ShaderNodeMixRGB", "Fibre Albedo Breakup")
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1.0
        if source is None:
            multiply.inputs[1].default_value = base.default_value
        else:
            links.new(source, multiply.inputs[1])
        links.new(modulation.outputs["Result"], multiply.inputs[2])
        links.new(multiply.outputs[0], base)
    return noise.outputs["Fac"]


def _nap_mask(nodes, links, vector, nap, tag=None):
    """Smooth 0..1 clump mask of the nap layer from reference-scaled coordinates."""
    tag = tag or (lambda node, name: node)
    stretch = tag(nodes.new("ShaderNodeVectorMath"), "Nap Streak Stretch")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = tuple(float(v) for v in nap["anisotropy"])
    links.new(vector, stretch.inputs[0])
    vector = stretch.outputs[0]
    noise = tag(nodes.new("ShaderNodeTexNoise"), "Nap Clumps")
    _set(noise, float(nap["scale_per_reference"]), "Scale")
    _set(noise, float(nap["detail"]), "Detail")
    _set(noise, float(nap["roughness"]), "Roughness")
    _set(noise, float(nap["distortion"]), "Distortion")
    links.new(vector, noise.inputs["Vector"])
    window = tag(nodes.new("ShaderNodeMapRange"), "Nap Clump Mask")
    window.interpolation_type = "SMOOTHSTEP"
    window.clamp = True
    threshold, softness = float(nap["threshold"]), float(nap["softness"])
    window.inputs["From Min"].default_value = threshold - softness
    window.inputs["From Max"].default_value = threshold + softness
    links.new(noise.outputs["Fac"], window.inputs["Value"])
    return window.outputs["Result"]


def _nap_gain(nodes, links, mask, nap, tag=None):
    """Albedo multiplier: 1 - value_shadow between clumps, 1 + value_gain on a clump."""
    tag = tag or (lambda node, name: node)
    gain = tag(nodes.new("ShaderNodeMapRange"), "Nap Value")
    gain.clamp = False
    gain.inputs["To Min"].default_value = 1.0 - float(nap["value_shadow"])
    gain.inputs["To Max"].default_value = 1.0 + float(nap["value_gain"])
    links.new(mask, gain.inputs["Value"])
    return gain.outputs["Result"]


def _nap_layer(material, principled, vector, reference, nap, base):
    """T-028 shared mid-scale nap/clump highlight layer (see NAP_FIELDS)."""
    if not nap.get("enabled", False):
        return None
    nodes, links = material.node_tree.nodes, material.node_tree.links
    mask = _nap_mask(nodes, links, vector, nap, _tag)
    if float(nap["value_gain"]) > 0.0 or float(nap["value_shadow"]) > 0.0:
        source = next((link.from_socket for link in base.links), None)
        multiply = _new(nodes, "ShaderNodeMixRGB", "Nap Albedo")
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1.0
        if source is None:
            multiply.inputs[1].default_value = base.default_value
        else:
            links.new(source, multiply.inputs[1])
        links.new(_nap_gain(nodes, links, mask, nap, _tag), multiply.inputs[2])
        links.new(multiply.outputs[0], base)
    sheen = _input(principled, "Sheen Weight", "Sheen")
    if sheen is not None and float(nap["sheen_gain"]) > 0.0 and float(sheen.default_value) > 0.0 and not sheen.links:
        weight = float(sheen.default_value)
        ramp = _new(nodes, "ShaderNodeMapRange", "Nap Sheen")
        ramp.clamp = False
        ramp.inputs["To Min"].default_value = weight
        ramp.inputs["To Max"].default_value = weight * (1.0 + float(nap["sheen_gain"]))
        links.new(mask, ramp.inputs["Value"])
        links.new(ramp.outputs["Result"], sheen)
    drop = float(nap["roughness_drop"])
    roughness = _input(principled, "Roughness")
    if drop > 0.0 and roughness is not None:
        source = next((link.from_socket for link in roughness.links), None)
        factor = _new(nodes, "ShaderNodeMapRange", "Nap Tip Gloss")
        factor.clamp = True
        factor.inputs["To Min"].default_value = 1.0
        factor.inputs["To Max"].default_value = 1.0 - drop
        links.new(mask, factor.inputs["Value"])
        glossy = _new(nodes, "ShaderNodeMath", "Nap Tip Roughness")
        glossy.operation = "MULTIPLY"
        if source is None:
            glossy.inputs[0].default_value = float(roughness.default_value)
        else:
            links.new(source, glossy.inputs[0])
        links.new(factor.outputs["Result"], glossy.inputs[1])
        links.new(glossy.outputs[0], roughness)
    if float(nap["bump_strength"]) > 0.0 and float(nap["distance_fraction"]) > 0.0:
        normal = _input(principled, "Normal")
        previous = next((link.from_socket for link in normal.links), None)
        bump = _new(nodes, "ShaderNodeBump", "Nap Clump Normal")
        bump.inputs["Strength"].default_value = float(nap["bump_strength"])
        bump.inputs["Distance"].default_value = reference * float(nap["distance_fraction"])
        links.new(mask, bump.inputs["Height"])
        if previous is not None:
            links.new(previous, bump.inputs["Normal"])
        links.new(bump.outputs["Normal"], normal)
    return mask


def _add_rim_layer(material, principled, preset, base_color, breakup=None):
    silhouette = preset["silhouette"]
    if not silhouette.get("enabled"):
        return
    nodes, links = material.node_tree.nodes, material.node_tree.links
    out = nodes.get("Material Output") or next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
    old = next((link.from_socket for link in out.inputs["Surface"].links), principled.outputs[0])
    rim = _new(nodes, "ShaderNodeBsdfPrincipled", "Rim Sheen")
    _set(rim, (*_srgb_to_linear(base_color), 1), "Base Color")
    _set(rim, float(silhouette.get("roughness", 0.8)), "Roughness")
    _set(rim, 1.0, "Sheen Weight", "Sheen")
    layer = _new(nodes, "ShaderNodeLayerWeight", "Rim Facing")
    invert = _new(nodes, "ShaderNodeMath", "Rim Invert")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    links.new(layer.outputs["Facing"], invert.inputs[1])
    power = _new(nodes, "ShaderNodeMath", "Rim Width")
    power.operation = "POWER"
    power.inputs[1].default_value = float(silhouette.get("width", 3.0))
    links.new(invert.outputs[0], power.inputs[0])
    weight = _new(nodes, "ShaderNodeMath", "Rim Weight")
    weight.operation = "MULTIPLY"
    weight.inputs[1].default_value = float(silhouette.get("weight", 0.22))
    links.new(power.outputs[0], weight.inputs[0])
    rim_factor = weight.outputs[0]
    if breakup is not None:
        broken = _new(nodes, "ShaderNodeMath", "Rim Fibre Breakup")
        broken.operation = "MULTIPLY"
        links.new(rim_factor, broken.inputs[0])
        links.new(breakup, broken.inputs[1])
        rim_factor = broken.outputs[0]
    mix = _new(nodes, "ShaderNodeMixShader", "Rim Mix")
    links.new(rim_factor, mix.inputs[0])
    links.new(old, mix.inputs[1])
    links.new(rim.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])


def _add_shadow_transmission(material, amount):
    """Porous surfaces (chunky yarn locks): each shadow-ray crossing of the surface passes ``amount`` of the light (a
    closed rope is crossed twice, so 0.75 per surface is ~0.56 per lock). Camera, diffuse and glossy
    rays still see the full shader, so the surface itself renders unchanged; only the shadow it casts is lighter."""
    if amount <= 0.0:
        return
    nodes, links = material.node_tree.nodes, material.node_tree.links
    out = nodes.get("Material Output") or next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out is None or not out.inputs["Surface"].links:
        return
    shaded = out.inputs["Surface"].links[0].from_socket
    path = _new(nodes, "ShaderNodeLightPath", "Shadow Ray")
    factor = _new(nodes, "ShaderNodeMath", "Shadow Transmission")
    factor.operation = "MULTIPLY"
    factor.inputs[1].default_value = amount
    links.new(path.outputs["Is Shadow Ray"], factor.inputs[0])
    clear = _new(nodes, "ShaderNodeBsdfTransparent", "Shadow Transparent")
    mix = _new(nodes, "ShaderNodeMixShader", "Shadow Mix")
    links.new(factor.outputs[0], mix.inputs[0])
    links.new(shaded, mix.inputs[1])
    links.new(clear.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])


def apply_preset(material, preset_name, base_color_srgb=None, reference_size_m=None, overrides=None,
                 preserve_base_color=False):
    """Apply one resolved preset to a material's existing Principled shader.

    Existing colour links (for example the face blush and procedural iris) can
    be preserved while the shared fibre, roughness and sheen response is added.
    """
    library = load_library()
    preset = resolve_preset(preset_name, overrides, library)
    color = tuple(base_color_srgb or preset["swatch_srgb"])
    reference = float(reference_size_m or library["reference_size_m"])
    if reference <= 0:
        raise ValueError("reference_size_m must be positive")
    if not material.use_nodes:
        material.use_nodes = True
    _clear_generated_nodes(material)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    principled = _principled(material)
    if principled is None:
        raise ValueError(f"material {material.name} has no Principled BSDF")
    output = nodes.get("Material Output") or next((node for node in nodes if node.type == "OUTPUT_MATERIAL"), None)
    if output is not None and not output.inputs["Surface"].links:
        links.new(principled.outputs[0], output.inputs["Surface"])
    surface = preset["surface"]
    shader_color = _saturate_srgb(color, surface.get("saturation_compensation", 1.0))
    base = _input(principled, "Base Color")
    if not preserve_base_color or not base.links:
        base.default_value = (*_srgb_to_linear(shader_color), 1)
    _set(principled, float(surface["roughness"]), "Roughness")
    _set(principled, float(surface["metallic"]), "Metallic")
    _set(principled, float(surface["specular_ior_level"]), "Specular IOR Level", "Specular")
    _set(principled, float(surface["ior"]), "IOR")
    _set(principled, float(surface["alpha"]), "Alpha")
    _set(principled, float(surface["transmission_weight"]), "Transmission Weight", "Transmission")
    _set(principled, float(surface["subsurface_weight"]), "Subsurface Weight", "Subsurface")
    _set(principled, reference * float(surface["subsurface_scale_fraction"]), "Subsurface Scale")
    _set(principled, (1.0, 0.45, 0.3), "Subsurface Radius")
    _set(principled, float(surface["sheen_weight"]), "Sheen Weight", "Sheen")
    _set(principled, float(surface["sheen_roughness"]), "Sheen Roughness")

    fibre = preset["fibre"]
    if fibre.get("coordinates", "object") == "uv":
        coords = _new(nodes, "ShaderNodeUVMap", "Fibre UV")
        coords.uv_map = FIBRE_UV
        coords_out = coords.outputs["UV"]
    else:
        coords = _new(nodes, "ShaderNodeTexCoord", "Material Coordinates")
        coords_out = coords.outputs["Object"]
    ref = _new(nodes, "ShaderNodeVectorMath", "Reference Scale")
    ref.operation = "SCALE"
    _set(ref, 1.0 / reference, "Scale")
    links.new(coords_out, ref.inputs[0])
    anis = _new(nodes, "ShaderNodeVectorMath", "Fibre Anisotropy")
    anis.operation = "MULTIPLY"
    anis.inputs[1].default_value = tuple(float(v) for v in fibre["anisotropy"])
    links.new(ref.outputs[0], anis.inputs[0])
    height = _pattern(nodes, links, anis.outputs[0], fibre)
    normal = _input(principled, "Normal")
    previous = next((link.from_socket for link in normal.links), None)
    bump = _new(nodes, "ShaderNodeBump", "Fibre Bump")
    bump.inputs["Strength"].default_value = float(fibre["strength"])
    bump.inputs["Distance"].default_value = reference * float(fibre["distance_fraction"])
    links.new(height, bump.inputs["Height"])
    if previous is not None:
        links.new(previous, bump.inputs["Normal"])
    links.new(bump.outputs["Normal"], normal)
    micro_breakup = _micro_relief(material, principled, anis.outputs[0], reference, preset["micro_relief"], base)
    _nap_layer(material, principled, anis.outputs[0], reference, preset["nap"], base)
    if float(surface["alpha"]) < 1.0:
        try:
            material.surface_render_method = "DITHERED"
        except Exception:  # Blender 4.0 and older
            material.blend_method = "BLEND"
    _add_rim_layer(material, principled, preset, shader_color, micro_breakup)
    _add_shadow_transmission(material, float(surface.get("shadow_transmission", 0.0)))
    material["ps_material_preset"] = preset_name
    material["ps_material_reference_size_m"] = reference
    return material


def _fibres_material(name, color, fibres=None, nap=None, reference=None, anisotropy=(1.0, 1.0, 1.0)):
    """Principled Hair material for the generated native curve fibres.

    ``fibres`` (the resolved preset block) adds the T-026 look: each strand's value is scaled by
    ``1 +/- color_variation`` from the per-curve ``ps_fibre_tone`` attribute written by the shared node group, and
    the strand fades to ``1 - root_transparency`` at the root and ``1 - tip_transparency`` at the tip.
    ``nap`` (T-028, the resolved nap block, with the surface's ``reference`` size and fibre ``anisotropy``) applies
    the surface's clump albedo gain to the strands: the curves object shares the surface object's transform, so its
    object coordinates evaluate the same clump mask as the surface under each fibre.
    """
    import bpy
    fibres = fibres or {}
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfHairPrincipled")
    try:
        shader.parametrization = "DIRECT"
    except Exception:
        pass
    _set(shader, (*_srgb_to_linear(color), 1), "Color", "Base Color")
    _set(shader, FIBRE_ROUGHNESS, "Roughness")
    _set(shader, 0.74, "Radial Roughness")
    _set(shader, 0.12, "Random Roughness")
    variation = float(fibres.get("color_variation", 0.0))
    colour_socket = None
    if variation > 0.0:
        tone = nodes.new("ShaderNodeAttribute")
        tone.attribute_type = "GEOMETRY"
        tone.attribute_name = FIBRE_TONE_ATTRIBUTE
        gain = nodes.new("ShaderNodeMapRange")
        gain.clamp = True
        gain.inputs["To Min"].default_value = max(0.0, 1.0 - variation)
        gain.inputs["To Max"].default_value = 1.0 + variation
        links.new(tone.outputs["Fac"], gain.inputs["Value"])
        scaled = nodes.new("ShaderNodeVectorMath")
        scaled.operation = "SCALE"
        scaled.inputs[0].default_value = _srgb_to_linear(color)
        links.new(gain.outputs["Result"], scaled.inputs["Scale"])
        colour_socket = scaled.outputs["Vector"]
    gloss = float(nap["fibre_gloss"]) if nap and nap.get("enabled") else 0.0
    if nap and nap.get("enabled") and reference and (float(nap["value_gain"]) > 0.0 or
                                                       float(nap["value_shadow"]) > 0.0 or gloss > 0.0):
        coords = nodes.new("ShaderNodeTexCoord")
        ref = nodes.new("ShaderNodeVectorMath")
        ref.operation = "SCALE"
        ref.inputs["Scale"].default_value = 1.0 / float(reference)
        links.new(coords.outputs["Object"], ref.inputs[0])
        anis = nodes.new("ShaderNodeVectorMath")
        anis.operation = "MULTIPLY"
        anis.inputs[1].default_value = tuple(float(v) for v in anisotropy)
        links.new(ref.outputs[0], anis.inputs[0])
        mask = _nap_mask(nodes, links, anis.outputs[0], nap)
        if gloss > 0.0:
            rough = nodes.new("ShaderNodeMapRange")
            rough.clamp = True
            rough.inputs["To Min"].default_value = FIBRE_ROUGHNESS * (1.0 - 0.5 * gloss)
            rough.inputs["To Max"].default_value = FIBRE_ROUGHNESS * (1.0 - gloss)
            links.new(mask, rough.inputs["Value"])
            links.new(rough.outputs["Result"], _input(shader, "Roughness"))
        nap_gain = _nap_gain(nodes, links, mask, nap)
        clumped = nodes.new("ShaderNodeVectorMath")
        clumped.operation = "SCALE"
        if colour_socket is None:
            clumped.inputs[0].default_value = _srgb_to_linear(color)
        else:
            links.new(colour_socket, clumped.inputs[0])
        links.new(nap_gain, clumped.inputs["Scale"])
        colour_socket = clumped.outputs["Vector"]
    if colour_socket is not None:
        links.new(colour_socket, _input(shader, "Color", "Base Color"))
    surface = shader.outputs[0]
    root_t = float(fibres.get("root_transparency", 0.0))
    tip_t = float(fibres.get("tip_transparency", 0.0))
    if root_t > 0.0 or tip_t > 0.0:
        info = nodes.new("ShaderNodeHairInfo")
        root = nodes.new("ShaderNodeMapRange")
        root.clamp = True
        root.inputs["From Min"].default_value, root.inputs["From Max"].default_value = 0.0, 0.3
        root.inputs["To Min"].default_value, root.inputs["To Max"].default_value = 1.0 - root_t, 1.0
        tip = nodes.new("ShaderNodeMapRange")
        tip.clamp = True
        tip.inputs["From Min"].default_value, tip.inputs["From Max"].default_value = 0.5, 1.0
        tip.inputs["To Min"].default_value, tip.inputs["To Max"].default_value = 1.0, 1.0 - tip_t
        for node in (root, tip):
            links.new(info.outputs["Intercept"], node.inputs["Value"])
        alpha = _math(nodes, "MULTIPLY", name="Fibre alpha")
        links.new(root.outputs["Result"], alpha.inputs[0])
        links.new(tip.outputs["Result"], alpha.inputs[1])
        clear = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        links.new(alpha.outputs[0], mix.inputs[0])
        links.new(clear.outputs[0], mix.inputs[1])
        links.new(surface, mix.inputs[2])
        surface = mix.outputs[0]
    links.new(surface, output.inputs["Surface"])
    material["ps_material_fibres"] = True
    material["ps_material_fibres_shader"] = "principled_hair"
    return material


def _math(nodes, operation, a=None, b=None, name=""):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    node.label = name
    if isinstance(a, (int, float)):
        node.inputs[0].default_value = a
    if isinstance(b, (int, float)):
        node.inputs[1].default_value = b
    return node


def shared_fibre_node_group():
    """Return the single parameterised Geometry Nodes hair-curve generator."""
    import bpy
    existing = bpy.data.node_groups.get(FIBRE_GROUP)
    if existing is not None:
        return existing
    group = bpy.data.node_groups.new(FIBRE_GROUP, "GeometryNodeTree")
    for name, socket_type in (("Surface", "NodeSocketObject"), ("Density", "NodeSocketFloat"),
                              ("Length", "NodeSocketFloat"), ("Curl", "NodeSocketFloat"),
                              ("Lean", "NodeSocketFloat"), ("Seed", "NodeSocketInt"),
                              ("Lean Variation", "NodeSocketFloat"),
                              ("Material", "NodeSocketMaterial")):
        socket = group.interface.new_socket(name=name, in_out="INPUT", socket_type=socket_type)
        if name == "Length":
            socket.subtype = "DISTANCE"
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = group.nodes, group.links
    group_in, group_out = nodes.new("NodeGroupInput"), nodes.new("NodeGroupOutput")
    surface = nodes.new("GeometryNodeObjectInfo")
    surface.transform_space = "ORIGINAL"
    links.new(group_in.outputs["Surface"], surface.inputs["Object"])
    distribute = nodes.new("GeometryNodeDistributePointsOnFaces")
    distribute.distribute_method = "RANDOM"
    links.new(surface.outputs["Geometry"], distribute.inputs["Mesh"])
    links.new(group_in.outputs["Density"], distribute.inputs["Density"])
    links.new(group_in.outputs["Seed"], distribute.inputs["Seed"])

    line = nodes.new("GeometryNodeCurvePrimitiveLine")
    line.mode = "DIRECTION"
    line.inputs["Direction"].default_value = (0.0, 0.0, 1.0)
    links.new(group_in.outputs["Length"], line.inputs["Length"])
    resample = nodes.new("GeometryNodeResampleCurve")
    resample.inputs["Count"].default_value = 6
    links.new(line.outputs["Curve"], resample.inputs["Curve"])
    parameter = nodes.new("GeometryNodeSplineParameter")

    lean_length = _math(nodes, "MULTIPLY", name="Lean by length")
    links.new(group_in.outputs["Length"], lean_length.inputs[0])
    links.new(group_in.outputs["Lean"], lean_length.inputs[1])
    lean = _math(nodes, "MULTIPLY", name="Lean along strand")
    links.new(parameter.outputs["Factor"], lean.inputs[0])
    links.new(lean_length.outputs[0], lean.inputs[1])
    phase = _math(nodes, "MULTIPLY", b=math.pi, name="Curl phase")
    links.new(parameter.outputs["Factor"], phase.inputs[0])
    sine = _math(nodes, "SINE", name="Curl arc")
    links.new(phase.outputs[0], sine.inputs[0])
    curl_length = _math(nodes, "MULTIPLY", name="Curl by length")
    links.new(group_in.outputs["Length"], curl_length.inputs[0])
    links.new(group_in.outputs["Curl"], curl_length.inputs[1])
    curl = _math(nodes, "MULTIPLY", name="Curl offset")
    links.new(sine.outputs[0], curl.inputs[0])
    links.new(curl_length.outputs[0], curl.inputs[1])
    offset = nodes.new("ShaderNodeCombineXYZ")
    links.new(lean.outputs[0], offset.inputs["X"])
    links.new(curl.outputs[0], offset.inputs["Y"])
    set_position = nodes.new("GeometryNodeSetPosition")
    links.new(resample.outputs["Curve"], set_position.inputs["Geometry"])
    links.new(offset.outputs["Vector"], set_position.inputs["Offset"])

    # Shaft radius 0.16 x length (T-026, was 0.11): a 4-6 mm fibre is 1.3-1.9 mm wide, the VISUAL_TARGET felt-fibre
    # width of 1-2 px at H = 256 for the 0.256 m reference; thinner shafts fell below 1 px and averaged away.
    radius = _math(nodes, "MULTIPLY", b=0.16, name="Shaft radius")
    links.new(group_in.outputs["Length"], radius.inputs[0])
    tip_radius = _math(nodes, "MULTIPLY", b=0.18, name="Tapered tip")
    links.new(radius.outputs[0], tip_radius.inputs[0])
    taper = nodes.new("ShaderNodeMapRange")
    taper.clamp = True
    taper.inputs["From Min"].default_value = 0.0
    taper.inputs["From Max"].default_value = 1.0
    links.new(parameter.outputs["Factor"], taper.inputs["Value"])
    links.new(radius.outputs[0], taper.inputs["To Min"])
    links.new(tip_radius.outputs[0], taper.inputs["To Max"])
    set_radius = nodes.new("GeometryNodeSetCurveRadius")
    links.new(set_position.outputs["Geometry"], set_radius.inputs["Curve"])
    links.new(taper.outputs["Result"], set_radius.inputs["Radius"])

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(distribute.outputs["Points"], instance.inputs["Points"])
    links.new(set_radius.outputs["Curve"], instance.inputs["Instance"])
    links.new(distribute.outputs["Rotation"], instance.inputs["Rotation"])
    random_length = nodes.new("FunctionNodeRandomValue")
    random_length.data_type = "FLOAT_VECTOR"
    random_length.inputs["Min"].default_value = (1.0, 1.0, 0.72)
    random_length.inputs["Max"].default_value = (1.0, 1.0, 1.28)
    links.new(group_in.outputs["Seed"], random_length.inputs["Seed"])
    links.new(random_length.outputs["Value"], instance.inputs["Scale"])
    rotate = nodes.new("GeometryNodeRotateInstances")
    links.new(instance.outputs["Instances"], rotate.inputs["Instances"])
    random_azimuth = nodes.new("FunctionNodeRandomValue")
    random_azimuth.data_type = "FLOAT_VECTOR"
    random_azimuth.inputs["Min"].default_value = (0.0, 0.0, 0.0)
    random_azimuth.inputs["Max"].default_value = (0.0, 0.0, math.tau)
    links.new(group_in.outputs["Seed"], random_azimuth.inputs["Seed"])
    # Per-fibre tilt about the local X axis (applied before the azimuth spin): +/- Lean Variation x 60 degrees, so
    # strands range from upright to lying along the surface instead of one combed angle.
    random_tilt = nodes.new("FunctionNodeRandomValue")
    random_tilt.data_type = "FLOAT"
    random_tilt.inputs["Min"].default_value = -1.0
    random_tilt.inputs["Max"].default_value = 1.0
    seed_tilt = _math(nodes, "ADD", b=7919.0, name="Tilt seed")
    links.new(group_in.outputs["Seed"], seed_tilt.inputs[0])
    links.new(seed_tilt.outputs[0], random_tilt.inputs["Seed"])
    tilt = _math(nodes, "MULTIPLY", name="Tilt amount")
    links.new(random_tilt.outputs["Value"], tilt.inputs[0])
    tilt_scale = _math(nodes, "MULTIPLY", b=math.radians(60.0), name="Tilt range")
    links.new(group_in.outputs["Lean Variation"], tilt_scale.inputs[0])
    links.new(tilt_scale.outputs[0], tilt.inputs[1])
    azimuth = nodes.new("ShaderNodeSeparateXYZ")
    links.new(random_azimuth.outputs["Value"], azimuth.inputs[0])
    euler = nodes.new("ShaderNodeCombineXYZ")
    links.new(tilt.outputs[0], euler.inputs["X"])
    links.new(azimuth.outputs["Z"], euler.inputs["Z"])
    links.new(euler.outputs["Vector"], rotate.inputs["Rotation"])
    rotate.inputs["Local Space"].default_value = True
    realize = nodes.new("GeometryNodeRealizeInstances")
    links.new(rotate.outputs["Instances"], realize.inputs["Geometry"])
    # Per-strand tone (0..1) for the fibre material's value variation.
    random_tone = nodes.new("FunctionNodeRandomValue")
    random_tone.data_type = "FLOAT"
    seed_tone = _math(nodes, "ADD", b=104729.0, name="Tone seed")
    links.new(group_in.outputs["Seed"], seed_tone.inputs[0])
    links.new(seed_tone.outputs[0], random_tone.inputs["Seed"])
    store_tone = nodes.new("GeometryNodeStoreNamedAttribute")
    store_tone.data_type = "FLOAT"
    store_tone.domain = "CURVE"
    store_tone.inputs["Name"].default_value = FIBRE_TONE_ATTRIBUTE
    links.new(realize.outputs["Geometry"], store_tone.inputs["Geometry"])
    links.new(random_tone.outputs["Value"], store_tone.inputs["Value"])
    set_material = nodes.new("GeometryNodeSetMaterial")
    links.new(store_tone.outputs["Geometry"], set_material.inputs["Geometry"])
    links.new(group_in.outputs["Material"], set_material.inputs["Material"])
    links.new(set_material.outputs["Geometry"], group_out.inputs["Geometry"])
    group["ps_material_fibres"] = True
    group["ps_material_fibres_version"] = FIBRE_GROUP_VERSION
    return group


def _set_modifier_input(modifier, group, name, value):
    socket = next(item for item in group.interface.items_tree
                  if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == name)
    getattr(modifier.properties.inputs, socket.identifier).value = value


def add_fibres_geometry(obj, preset_name, base_color_srgb=None, reference_size_m=None, overrides=None, lod="close"):
    """Attach shared native hair curves; wide LOD uses the preset's 0.25 density multiplier."""
    if lod not in FIBRE_LODS:
        raise ValueError(f"lod must be one of {sorted(FIBRE_LODS)}")
    library = load_library()
    preset = resolve_preset(preset_name, overrides, library)
    fibres = preset["fibres"]
    if lod == "off" or not fibres["enabled"]:
        return None
    if obj.type != "MESH":
        raise ValueError("surface fibres require a mesh object")
    reference = float(reference_size_m or library["reference_size_m"])
    if reference <= 0:
        raise ValueError("reference_size_m must be positive")
    # T-028: fibre length and density are authored at the library reference (the size that projects to H); a surface
    # with another reference_size_m keeps the same look in H-normalised pixels: length x k, density / k^2.
    k = reference / float(library["reference_size_m"])
    density = float(fibres["density_per_cm2"]) * 10000.0 / (k * k)
    if lod == "wide":
        density *= float(fibres["lod"])
    length = float(fibres["length_mm"]) / 1000.0 * k
    # The raw base colour: saturation_compensation offsets the desaturating sheen/rim layers of the surface shader,
    # which the Principled Hair fibres do not have (T-026: dense compensated fibres pushed felt hair to 127 %).
    color = tuple(base_color_srgb or preset["swatch_srgb"])
    material = _fibres_material(f"M_fibres_{preset_name}_{obj.name}", color, fibres, preset["nap"], reference,
                                preset["fibre"]["anisotropy"])
    import bpy
    group = shared_fibre_node_group()
    curves = bpy.data.hair_curves.new(obj.name + ".fibres")
    fibre_object = bpy.data.objects.new(obj.name + ".fibres", curves)
    (obj.users_collection[0] if obj.users_collection else bpy.context.scene.collection).objects.link(fibre_object)
    # Object Info supplies source-local geometry; matching transforms places
    # the generated Curves object on the evaluated source surface.
    fibre_object.matrix_world = obj.matrix_world.copy()
    curves.materials.append(material)
    if hasattr(curves, "surface"):
        curves.surface = obj
    modifier = fibre_object.modifiers.new("PS Surface Fibres", "NODES")
    modifier.node_group = group
    _set_modifier_input(modifier, group, "Surface", obj)
    _set_modifier_input(modifier, group, "Density", density)
    _set_modifier_input(modifier, group, "Length", length)
    _set_modifier_input(modifier, group, "Curl", float(fibres["curl"]))
    _set_modifier_input(modifier, group, "Lean", float(fibres["lean"]))
    _set_modifier_input(modifier, group, "Lean Variation", float(fibres.get("lean_variation", 0.0)))
    seed = sum((index + 1) * ord(char) for index, char in enumerate(preset_name)) % 100000
    _set_modifier_input(modifier, group, "Seed", seed)
    _set_modifier_input(modifier, group, "Material", material)
    fibre_object["ps_material_preset"] = preset_name
    fibre_object["ps_fibres_lod"] = lod
    fibre_object["ps_fibres_source"] = obj.name
    fibre_object["ps_fibres_reference_scale"] = k
    return fibre_object


def add_fibres_from_assignment(obj, assignment, lod="close"):
    return add_fibres_geometry(obj, assignment["preset"], assignment["base_color_srgb"],
                               assignment.get("reference_size_m"), assignment.get("overrides"), lod)


def build_material(name, preset_name, base_color_srgb=None, reference_size_m=None, overrides=None):
    import bpy
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    return apply_preset(material, preset_name, base_color_srgb, reference_size_m, overrides)


def build_from_assignment(name, assignment):
    return build_material(name, assignment["preset"], assignment["base_color_srgb"],
                          assignment.get("reference_size_m"), assignment.get("overrides"))


def apply_from_assignment(material, assignment, preserve_base_color=True):
    return apply_preset(material, assignment["preset"], assignment["base_color_srgb"],
                        assignment.get("reference_size_m"), assignment.get("overrides"), preserve_base_color)


def apply_legacy_felt_surface(base, cfg):
    """The original H31 felt-hair graph, kept node-for-node for legacy renders."""
    material = base
    tree = material.node_tree
    principled = tree.nodes.get("Principled BSDF")
    tex = tree.nodes.new("ShaderNodeTexCoord")
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = float(cfg.get("scale", 260.0))
    noise.inputs["Detail"].default_value = float(cfg.get("detail", 12.0))
    if "Roughness" in noise.inputs:
        noise.inputs["Roughness"].default_value = float(cfg.get("noise_roughness", 0.75))
    if "Distortion" in noise.inputs:
        noise.inputs["Distortion"].default_value = float(cfg.get("distortion", 1.5))
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = float(cfg.get("strength", 0.45))
    bump.inputs["Distance"].default_value = float(cfg.get("distance", 0.0015))
    tree.links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    if "Sheen Weight" in principled.inputs:
        principled.inputs["Sheen Weight"].default_value = float(cfg.get("sheen", 0.35))
    if "Roughness" in principled.inputs:
        principled.inputs["Roughness"].default_value = float(cfg.get("roughness", 0.95))
    return material
