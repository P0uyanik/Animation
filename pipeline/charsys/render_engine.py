"""Shared Cycles/EEVEE renderer selection for character-system tools.

The Cycles branch deliberately mirrors the settings that predate T-020. In
particular, callers decide whether to select a device or a denoiser so the
default production-shot path is not perturbed.
"""


def configure(scene, engine, samples, *, cycles_device=None, cycles_denoiser=None):
    """Configure ``scene`` and return the settings recorded in render reports."""
    if engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        if cycles_device is not None:
            scene.cycles.device = cycles_device
        if cycles_denoiser is not None:
            scene.cycles.denoiser = cycles_denoiser
        return {"engine": "cycles", "blender_engine": "CYCLES", "samples": samples,
                "denoising": True}
    if engine != "eevee":
        raise ValueError(f"unknown render engine {engine!r}")

    scene.render.engine = "BLENDER_EEVEE"
    eevee = scene.eevee
    eevee.taa_render_samples = samples
    eevee.use_shadows = True
    eevee.shadow_ray_count = 4
    eevee.use_fast_gi = True
    eevee.fast_gi_method = "AMBIENT_OCCLUSION_ONLY"
    # Softness still comes primarily from area-light size / sun angle. Shadow
    # jitter gives those finite emitters enough samples in draft renders.
    for obj in scene.objects:
        if obj.type == "LIGHT":
            light = obj.data
            light.use_shadow = True
            if hasattr(light, "use_shadow_jitter"):
                light.use_shadow_jitter = True
    # Blender 5.x removed EEVEE's old bloom toggle. With no compositor Glare
    # added here, bloom is explicitly absent from this render path.
    return {"engine": "eevee", "blender_engine": "BLENDER_EEVEE", "samples": samples,
            "soft_shadows": True, "shadow_rays": 4, "ambient_occlusion": True,
            "fast_gi_method": "AMBIENT_OCCLUSION_ONLY", "bloom": False}


def apply_profile(scene, profile):
    """T-124: applies an opt-in render profile's extra settings (``cycles``, ``eevee`` (T-201) and ``render`` blocks
    of render_profiles.json) after configure(); returns what was set. A profile with an ``engine`` key (T-201
    preview_eevee) must run on that engine: configure() picks the engine from --engine, so a mismatch is refused
    instead of silently rendering an EEVEE profile with Cycles."""
    applied = {}
    want = profile.get("engine")  # T-201: absent on the Cycles profiles; checked only when a profile names one
    if want is not None:
        blender_engine = {"cycles": "CYCLES", "eevee": "BLENDER_EEVEE"}.get(want)
        if blender_engine is None:
            raise ValueError(f"profile engine {want!r} is not cycles or eevee")
        if scene.render.engine != blender_engine:
            raise ValueError(f"this profile renders with {want}, but the scene is set to {scene.render.engine}: "
                             f"pass --engine {want}")
        applied["engine"] = want
    for block in ("cycles", "eevee", "render"):  # attribute read only for blocks the profile has
        if block not in profile:
            continue
        target = getattr(scene, block)
        for key, value in profile[block].items():
            if not hasattr(target, key):
                raise ValueError(f"profile setting {block}.{key} does not exist")
            setattr(target, key, value)
            applied[f"{block}.{key}"] = value
    if "compositor" in profile:  # T-199: opt-in look; absent = the path above, untouched
        applied["compositor"] = apply_compositor_look(scene, profile["compositor"])
    return applied


# ---------------------------------------------------------------------------------------------------------------
# T-199 compositor look. One function, Blender 5.x only: 5.0 replaced Scene.node_tree/use_nodes + the Composite node
# by Scene.compositing_node_group + a Group Output, and 6.0 changes the API again (T-196 probe). Anything else
# raises ValueError instead of silently rendering without the look.
_LOOK_KEYS = {"look": None, "glow": {"type", "quality", "threshold", "smoothness", "strength", "size"},
              "grade": {"saturation", "gain", "lift"}, "vignette": {"strength", "size", "softness"}}


def _sock(node, name, kind=None, outputs=False):
    """Socket by name or identifier (and type: ColorBalance has a VALUE and an RGBA 'Gain')."""
    for s in (node.outputs if outputs else node.inputs):
        if name in (s.name, s.identifier) and (kind is None or s.type == kind):
            return s
    raise ValueError(f"compositor node {node.bl_idname} has no input {name!r} ({kind})")


def apply_compositor_look(scene, cfg):
    """Build the look node tree on ``scene`` and return what was applied (for the run report): look name, resolved
    parameters, Blender version, node chain. Chain: Render Layers -> Glare -> Color Balance -> Color Correction
    [-> vignette: Ellipse Mask -> Blur (sized from the image) -> Math -> Mix multiply] -> Group Output."""
    import warnings
    import bpy  # lazy: the profile tests and non-look renders never import it here

    for key, value in cfg.items():
        if key not in _LOOK_KEYS:
            raise ValueError(f"compositor.{key} is not a known setting")
        if _LOOK_KEYS[key] is not None:
            extra = set(value) - _LOOK_KEYS[key]
            if extra:
                raise ValueError(f"compositor.{key} has unknown keys {sorted(extra)}")
    version = tuple(bpy.app.version)
    if not ((5, 0) <= version[:2] < (6, 0)):
        raise ValueError(f"compositor look supports Blender 5.x only, this is {bpy.app.version_string} "
                         "(the compositor Python API differs in 4.x and changes in 6.0)")
    g, c, v = cfg["glow"], cfg["grade"], cfg["vignette"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)  # compositing_node_group: "removed in 6.0"
        if getattr(scene, "compositing_node_group", None) is not None:
            raise ValueError("scene already has a compositor node group; refusing to replace it")
        tree = bpy.data.node_groups.new(f"look_{cfg['look']}", "CompositorNodeTree")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        N, L, chain = tree.nodes, tree.links, []

        def node(idname, label):
            n = N.new(idname)
            n.label = label
            chain.append(f"{label}:{idname}")
            return n

        rl = node("CompositorNodeRLayers", "render")
        glare = node("CompositorNodeGlare", "glow")
        for name, value in (("Type", g["type"]), ("Quality", g["quality"])):
            _sock(glare, name).default_value = value
        for name, key in (("Threshold", "threshold"), ("Smoothness", "smoothness"), ("Strength", "strength"),
                          ("Size", "size")):
            _sock(glare, name).default_value = g[key]
        bal = node("CompositorNodeColorBalance", "tint")
        _sock(bal, "Type").default_value = "Lift/Gamma/Gain"
        _sock(bal, "Lift", "RGBA").default_value = (*c["lift"], 1.0)
        _sock(bal, "Gain", "RGBA").default_value = (*c["gain"], 1.0)
        cc = node("CompositorNodeColorCorrection", "saturation")
        _sock(cc, "Saturation").default_value = c["saturation"]  # first one = master
        L.new(rl.outputs["Image"], glare.inputs["Image"])
        L.new(glare.outputs["Image"], bal.inputs["Image"])
        L.new(bal.outputs["Image"], cc.inputs["Image"])
        last = cc.outputs["Image"]
        if v["strength"] > 0:
            mask = node("CompositorNodeEllipseMask", "vignette_mask")
            mask.inputs["Position"].default_value = (0.5, 0.5)
            mask.inputs["Size"].default_value = tuple(v["size"])
            info = node("CompositorNodeImageInfo", "vignette_dims")  # blur size follows the render resolution
            scale = node("ShaderNodeVectorMath", "vignette_soft")
            scale.operation = "SCALE"
            scale.inputs["Scale"].default_value = v["softness"]
            blur = node("CompositorNodeBlur", "vignette_blur")
            blur.inputs["Type"].default_value = "Gaussian"
            gain = node("ShaderNodeMath", "vignette_gain")  # mask*s + (1-s): 1 inside, 1-s at the corners
            gain.operation = "MULTIPLY_ADD"
            gain.inputs[1].default_value = v["strength"]
            gain.inputs[2].default_value = 1.0 - v["strength"]
            mix = node("ShaderNodeMix", "vignette_mix")
            mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
            _sock(mix, "Factor_Float").default_value = 1.0
            L.new(rl.outputs["Image"], info.inputs["Image"])
            L.new(info.outputs["Dimensions"], scale.inputs[0])
            L.new(scale.outputs["Vector"], blur.inputs["Size"])
            L.new(mask.outputs["Mask"], blur.inputs["Image"])
            L.new(blur.outputs["Image"], gain.inputs[0])
            L.new(last, _sock(mix, "A_Color"))
            L.new(gain.outputs["Value"], _sock(mix, "B_Color"))
            last = _sock(mix, "Result_Color", outputs=True)
        out = node("NodeGroupOutput", "out")
        L.new(last, out.inputs[0])
        scene.compositing_node_group = tree
        scene.render.use_compositing = True
    return {"look": cfg["look"], "params": {k: cfg[k] for k in ("glow", "grade", "vignette")},
            "blender": bpy.app.version_string, "node_chain": chain}
