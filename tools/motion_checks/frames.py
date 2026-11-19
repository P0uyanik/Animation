"""Frame passes for the flicker check: reduction of a render_passes.py EXR to a compact npz, and loading."""
import os

import numpy as np

LUMA = (0.2126, 0.7152, 0.0722)  # Rec.709 weights on the scene-linear RGB


def _get(d, *keys):
    for k in keys:
        for name, v in d.items():
            if name.endswith(k):
                return v
    raise KeyError(keys)


def exr_to_npz(exr_path, npz_path, vectors_only=False):
    import exr
    d = exr.read(exr_path)
    vec = None
    try:
        vec = np.stack([_get(d, f"Vector.{c}") for c in "XYZW"], -1).astype(np.float16)
    except KeyError:
        pass
    if vectors_only:
        np.savez(npz_path, vector=vec)
        return

    def lum(layer):
        return sum(w * _get(d, f"{layer}.{c}") for w, c in zip(LUMA, "RGB")).astype(np.float16)
    np.savez(npz_path, denoised=lum("Combined"), noisy=lum("Noisy Image"),
             index=np.rint(_get(d, "Object Index.X", "IndexOB.X")).astype(np.uint8),
             depth=_get(d, "Depth.Z").astype(np.float16),
             normal=np.stack([_get(d, f"Denoising Normal.{c}") for c in "XYZ"], -1).astype(np.float16),
             **({} if vec is None else {"vector": vec}))


def load_dir(path):
    """(frame numbers, dict of stacked arrays: denoised, noisy, index, depth, normal[, vector]) from NNNN.npz files
    (vectors from NNNN_vec.npz when the frame's own file has none)."""
    names = sorted(n for n in os.listdir(path) if n.endswith(".npz") and n[:-4].isdigit())
    if not names:
        raise SystemExit(f"no NNNN.npz frames in {path}")
    frames, stacks = [int(n[:-4]) for n in names], {}
    for n in names:
        with np.load(os.path.join(path, n)) as z:
            for k in z.files:
                stacks.setdefault(k, []).append(z[k])
        vec = os.path.join(path, n[:-4] + "_vec.npz")
        if "vector" not in stacks or len(stacks["vector"]) < len(stacks["denoised"]):
            if os.path.exists(vec):
                with np.load(vec) as z:
                    stacks.setdefault("vector", []).append(z["vector"])
    if "vector" in stacks and len(stacks["vector"]) != len(frames):
        del stacks["vector"]  # vectors for only some frames: not used
    return frames, {k: np.stack(v) for k, v in stacks.items()}
