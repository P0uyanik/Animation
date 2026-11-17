# Regression baselines (T-041)

Approved per-character regression baselines for `tools/regression/run.py` (see `docs/process/GATE.md` §3).
One folder per character and spec version: `golden.json` (spec inputs hash, fingerprint hash, order-independent
engine-export summary, render hashes), `fingerprint.json` (format 2, 0.01 mm) and `images/*.png` (fixed cameras of
`tools/regression/views.json`). Guarded: changes need a `Supervisor-Approved:` trailer; a new character version adds
a new folder (new files only) through an owner-approved pin-bump task.

Initial set: made by T-041 from `origin/main` spec inputs (boy 1.1.0 = spec + 1.1.0 override, girl 0.9.0), bpy 5.3.0
on Linux x86_64. Fidelity of the same build: boy 64.08 (baseline 64.49), girl 65.48 (baseline 65.41).
