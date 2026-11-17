"""Deterministic process and Blender defaults for character builds.

Process-level hash and math-library thread settings must be supplied before
Blender starts; ``subprocess_env`` is the single source of truth used by CI
drivers.  ``configure_blender`` covers state that can safely be reset after
``read_factory_settings``.
"""
import os
import random


DEFAULT_SEED = 0
ENVIRONMENT = {
    "PYTHONHASHSEED": "0",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}
RUNTIME_TIMING_KEYS = {"model_s", "master_s", "total_s", "generate_s", "weights_s"}


def subprocess_env(base=None):
    """Return an environment suitable for launching a reproducible build."""
    env = dict(os.environ if base is None else base)
    env.update(ENVIRONMENT)
    return env


def configure_blender(seed=DEFAULT_SEED):
    """Seed shared RNGs and pin Blender's exposed worker count to one."""
    import bpy
    import numpy as np
    from mathutils import noise

    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed)
    noise.seed_set(seed)
    scene = bpy.context.scene
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    return seed


def strip_runtime_timings(value):
    """Remove wall-clock measurements while preserving semantic time values."""
    if isinstance(value, dict):
        for key in list(value):
            if key in RUNTIME_TIMING_KEYS:
                del value[key]
            else:
                strip_runtime_timings(value[key])
    elif isinstance(value, list):
        for item in value:
            strip_runtime_timings(item)
    return value
