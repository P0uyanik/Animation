# Reference performance extraction

Run the three scripts from the repository root with the tool-local Python environment. They measure the two T-106 reference MP4s, join the measurements to reviewed acting intervals, and make labelled JPEG contact sheets. The [evaluation report](../../docs/evaluation/animation/T-106/README.md) describes the frame convention, denominators and calibration examples.

## Recreate the environment

The recorded environment uses Windows x64, CPython 3.12.14, MediaPipe 1.2.3 (Apache-2.0), OpenCV 5.1.0 and NumPy 2.5.5. [requirements.txt](requirements.txt) pins the installed distributions, including the OpenCV wheel build numbers. On a machine provisioning a fresh environment, run the following PowerShell commands. For offline provisioning, add `--no-index --find-links <wheelhouse>` to the install command and point it to a pre-populated wheel directory.

```powershell
py -3.12 -m venv build/perf-venv
build/perf-venv/Scripts/python.exe -m pip install -r tools/perf_extract/requirements.txt
```

Place the following two task bundles under `build/perf-models/` when provisioning. The download endpoints use a moving version label. Match the SHA-256 values in the [source manifest](../../docs/evaluation/animation/T-106/sources.json) to reproduce this run.

- [face_landmarker.task](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task)
- [pose_landmarker_full.task](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task)

Keep the venv, wheels and task files under ignored build storage. The prepared worktree already has its dependencies. Analysis runs offline.

## Run and verify

```powershell
$python = "build/perf-venv/Scripts/python.exe"
& $python -B tools/perf_extract/measure.py
& $python -B tools/perf_extract/report.py
& $python -B tools/perf_extract/sheets.py
& $python -B -m unittest discover -s tools/perf_extract/tests -v
```

All three scripts default to `docs/evaluation/animation/T-106/`. Pass the same `--out build/<directory>` to each to reproduce the data separately. The tests include checks on the published evaluation files as well as synthetic motion and interval arithmetic.

## Measurement method

1. `measure.py` verifies SHA-256 before applying the source-specific annotations. It sequentially decodes all frames. [reference.py](reference.py) records cut boundaries and manually marked eye-line anchors in display pixels. Each knot supplies a frame, an approximate centre and a face width. Interpolation stays within the character's reviewed window in each shot. The video determines the source dimensions and frame rate.
2. On each eligible character-frame the CPU MediaPipe Face Landmarker examines a clipped crop around the anchor in IMAGE mode at the default 0.5 detection and presence thresholds. A mesh matches the character when its outer-eye midpoint falls within 0.35 annotated face widths of the anchor. `face_returned` records any mesh and `face_matched` records this positional check. The CSV retains five raw blendshape scores for matched frames. The score scale is 0 to 1.
3. On each frame with at least one eligible face, the full-frame CPU Pose Landmarker looks for up to three people. A nose with visibility and presence at least 0.5 is assigned to the nearest anchor in face-width units, up to 0.5 widths. The closest eligible nose per character supplies the image-space coordinates. Misses have empty fields.
4. OpenCV tracks up to 64 Shi-Tomasi features on the preceding frame's upper face with pyramidal Lucas-Kanade flow. At least five features must track back to within one pixel. Their median displacement estimates on-screen head translation. A similarity fit with a 1.5 px RANSAC threshold and at least five inliers estimates apparent roll. Each step ends at the row's frame. The first sample in a window has no incoming step. Camera movement, changing scale, eyelids and hair can contribute.
5. For the visual fallback, review contiguous face crops one native frame at a time with the full shot for context. Identify the cast from clothing, hair and glasses on each cut. Record expression, gaze direction, action boundaries and eyelid closure in [observations.py](observations.py). For each closure mark the first clear lowering, a minimum-aperture frame and the first recovered frame. Count a blink when the readable eye reaches closure or a narrow slit and reopens. Code a distinct dip with a plainly visible iris as partial. The near eye provides the reading on the boy's profile. Gaze annotations describe sustained screen direction and visible changes. Target objects are inferred from composition. Blinks interrupt visibility within a gaze span.
6. `report.py` checks that acting and gaze intervals exactly cover each character's observed frames. It exports matching JSON/CSV tables. `sheets.py` rebuilds the contact sheets directly from the hashed MP4s and the reviewed frame indices.

ledger: build 10 · render 1 · tests 1 · ci 0 · wait 0 (min)
