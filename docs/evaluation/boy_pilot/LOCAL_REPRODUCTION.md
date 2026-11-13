# Reproducing pilot v6 with the Blender on your computer

Goal: a verified local v6 baseline before any character change. Nothing here reinstalls Blender, changes the
character, or touches the engine.

## Why you run it (no Remote Control needed)
This Claude session runs in a cloud container and cannot see your computer: no folder of yours is shared with it.
You can run the reproduction yourself with one command (below) and send back the result file.

Remote Control is only needed if you want **this** session to run it for you. Then, in the Claude desktop app on
that computer, open Settings → Claude Code → Remote Control and add the project folder. The app must stay running and
the computer online; this session then asks you to approve access to that folder. Using a folder from a cloud session
is not available to every account yet. A Claude Code session started on your computer works as well.

## 1. Get the project onto your computer
The project has no GitHub remote yet, so it comes as a download:
- `plush-studio-backup.bundle`: the full git repository with history. Clone it with
  `git clone plush-studio-backup.bundle plush-studio`. Or:
- `plush-studio-source.zip`: the current files without history (unzip anywhere).

## 2. Requirements
- Your installed Blender, ideally 4.1 or newer. The scripts were tested only with 5.3.0; the environment check
  reports missing features.
- A Python 3.9+ with numpy and Pillow, for the sheets and metrics:
  - Windows: `py -m pip install numpy pillow`
  - macOS/Linux: `python3 -m pip install numpy pillow`
- About 1 GB of free disk space and 5–15 minutes (CPU rendering, 16 + 6 views).

## 3. Run (from the project folder)
Use your own Blender path.

Windows (PowerShell):
```
py pipeline\blender\boy_pilot\reproduce_v6.py --blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --out out\local_v6
```
macOS:
```
python3 pipeline/blender/boy_pilot/reproduce_v6.py --blender /Applications/Blender.app/Contents/MacOS/Blender --out out/local_v6
```
Linux:
```
python3 pipeline/blender/boy_pilot/reproduce_v6.py --blender "$(command -v blender)" --out out/local_v6
```

What it does, all headless (`blender -b --factory-startup`, so your Blender preferences and add-ons are not
used or changed):
1. Records `blender --version` and checks the environment: Python, numpy, Rigify, Cycles, AgX and the material
   inputs the scripts use.
2. Builds the master `.blend`, the comparison `.blend` and the `.glb` with the committed v6 scripts and colour
   calibration. Calibration is not re-run.
3. Fingerprints the geometry; renders the 16 harness views; makes the comparison sheet; renders the regions;
   computes the metrics; runs the rig, expression and glTF tests.
4. Compares everything with the frozen cloud v6 baseline (`cloud_v6_baseline/`): files, geometry, renders per view,
   metrics, and rig and glTF contents.

**Safety:**
- Everything is written under `--out`, which must be a new or empty folder.
- The script refuses to write into `docs/`, `assets/`, `pipeline/` or the cloud results.
- Tracked files and the v6 evidence are never modified.

## 4. Send back
- `out/local_v6/VERIFICATION.md`: verdict, Blender version, every step and every check.
- If anything failed: `out/local_v6/run.log` and `out/local_v6/verification.json`.
- Optionally `out/local_v6/report/comparison_sheet.png`.

## 5. How to read the verdict
| Verdict | Meaning |
| --- | --- |
| REPRODUCED | All steps ran and all checks are within tolerance: your Blender reproduces cloud v6 |
| RAN WITH DIFFERENCES | All steps ran, but some check is outside tolerance; the table shows which (e.g. a different Blender version renders fur or materials slightly differently) |
| FAILED | A step did not complete; `run.log` has the error |

Tolerances:
- Silhouette overlap with the cloud renders ≥ 0.98 per view.
- Mean colour difference ≤ 6/255.
- Metric IoU within ±0.01.
- Outline distance within ±0.15%.
- Landmark errors within ±1.5 points.
- ΔE2000 within ±1.5.
- Geometry: same objects and vertex/face counts; bounding box, centroid and spread within 0.5 mm.

Tested in the cloud with Blender 5.3.0 (Python module): verdict REPRODUCED.
- Worst per-view silhouette overlap with the cloud renders: 0.9999.
- Worst mean colour difference: 0.31/255.
- Metrics identical.
- Geometry identical except one object's exact coordinate hash (floating-point rounding, informational).
