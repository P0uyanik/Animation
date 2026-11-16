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
