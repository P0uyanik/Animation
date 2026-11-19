# T-143 cleanup notes

- Archived `pipeline/charsys/experiments/hair_study` -> `archive/experiments/charsys/hair_study` (git mv; no code/test/CI user; doc links updated).
- `tools/lipsync` stays (required gate check in tools/check_all.py). `tools/cleanup/**` stays (live in cleanup.yml).
- Helpers left unchanged, no hash proof was needed because no code changed: the two `geom.py` files have diverged (only
  `bezier` matches), the two `catmull_rom` functions differ in signature, and the `slerp` copies are pure Python with
  their own float path (mathutils is Blender-only). Replacing them would risk byte changes for no gain.
- `tools/bpy_blender.py` mode 644 -> 755.
- Gate on this branch: only `tools/fidelity/tests/test_ci.py` (1 error) fails; it fails identically at 200ae3b (pre-existing).
- Revert: `git revert` the archive commit (and doc-link commit).
