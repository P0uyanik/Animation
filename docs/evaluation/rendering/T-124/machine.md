# T-124 benchmark machine

Recorded 2026-11-19T13:06Z in the cloud container that ran every measurement in this folder.

| | |
|---|---|
| CPU | Intel(R) Xeon(R) Processor @ 2.30GHz |
| Cores / threads used | 4 vCPU, 1 thread per core (Cycles threads: auto = 4) |
| L3 (reported) | 504 MiB (1 instance) |
| RAM | 15 GiB |
| Kernel | 6.18.44-fc-v653 |
| GPU | none (Cycles device CPU; OIDN on CPU) |
| Blender | 5.3.0 (official `bpy` 5.3.0 wheel from PyPI, Python 3.13; pinned version of `pipeline/blender/BLENDER_VERSION`) |
| ffmpeg | 6.1.1-3ubuntu5 (libx264, libx265, libsvtav1; no libvmaf) |

Why the bpy wheel: download.blender.org is blocked by this environment's network policy (proxy 403), PyPI is not.
`tools/render_bench/blender_shim.py` gives the pipeline the `blender -b -P script -- args` command line on top of the
wheel; the render code inside is the same Blender 5.3.0 build (Cycles, OIDN).

Shared vCPU: neighbouring load on the host can move times; see the variance runs in README.md.
