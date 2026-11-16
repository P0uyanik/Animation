# T-014 — boy eyelids under upward gaze

Status: **Blender-local evidence passes; the end-to-end T-010 rerun fails before bake because this Windows host has
no `plush-render` binary or C++ toolchain**. The candidate is represented by the base 1.0.0 spec plus
`assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json`. It remains unpublished and
unapproved. No file or pointer under `versions/1.0.0` was changed, and no `1.1.0` asset-store version was published.

## Root cause

The failure is geometric/rigging, not a blink or expression value:

- The 1.0.0 master comes from `body_v6.build_eyes`. Its eyeball radius is 37 mm, iris radius 23 mm and pupil radius
  10.5 mm. The upper lid is a concentric 40.5 mm shell cut by a near-horizontal plane. Solving that plane/sphere
  intersection at the front centre puts the free edge about 3.3 mm below the eye centre, intentionally covering
  about 40–45% of the iris at rest.
- `eye.L/R` are weighted 100% to `DEF-eye.L/R`, so their generated-coordinate iris shader rotates with gaze.
- `lid_upper.*`, `lid_lower.*` and `lash.*` each have only the head binding in 1.0.0. The build path put all six on
  `DEF-spine.006` with weight 1.0. They have no gaze constraint or gaze driver. Blink is only a shape-key driver on
  the upper lids and lashes; T-010 measured that driver at zero.
- Consequently, at +15° upward gaze the iris centre moves about `37 sin(15°) = 9.58 mm` upward behind a lid opening
  that does not move. At T-010's measured maximum +14.3°, the relative displacement is about 9.14 mm. This is enough
  to put nearly the entire 10.5 mm pupil behind the already-low upper edge, which reads as a closed eye.

The girl does not have this topology/weighting mismatch. `face_generic/1` already consumes
`spec.face.eyes.lid_tracking`; her value is 0.3, producing uniform head/eye weights 0.7/0.3 on the lids and lashes.

## Fix

`face.lid_bindings` is now the shared, character-independent binding rule used by both `face_generic/1` and the
legacy-body build path. The spec value is constrained to 0–1:

| `lid_tracking` | Head weight | Eye weight | Relative iris/lid gaze at +15° |
| ---: | ---: | ---: | ---: |
| boy 1.0.0 (implicit 0.0) | 1.0 | 0.0 | 15° (9.58 mm surface displacement) |
| boy 1.1.0 candidate (1.0) | 0.0 | 1.0 | 0° (0 mm relative displacement) |
| girl (unchanged 0.3) | 0.7 | 0.3 | nominal 10.5° (existing linear-blend tracking) |

Full tracking is intentional for the boy's half-closed stylised lid geometry: on concentric spherical shells it
preserves the approved rest-pose opening exactly at every gaze angle and cannot introduce an eyeball/lid
intersection. No character id is tested in shared code. The girl's input and resulting 0.7/0.3 weights are unchanged.

## Evidence and results

Blender 5.3.0 ran CPU-only. The user-profile Python executable was inaccessible to the managed sandbox, so the
standalone Python entry points used Blender's bundled Python 3.13.13. Blender scripts ran normally through
`D:/Animation/tools/blender-5.3/blender.exe`.

### Candidate build and engine export

The relay build completed in 13.4 s (`master_s` 11.5 s, glTF 1.8 s): 410 Rigify bones, 73 deform bones, 17,490
weighted vertices and zero vertices unweighted after cleanup. The failed export procedure was corrected by using a
new output directory instead of the already-populated `engine` directory:

```powershell
$BlenderExe = 'D:/Animation/tools/blender-5.3/blender.exe'

& $BlenderExe -b --factory-startup -P pipeline/charsys/export_engine.py -- `
  --blend build/t014/boy_yellow_hoodie_1.1.0/boy_yellow_hoodie_master.blend `
  --profile pipeline/charsys/rig_profiles/humanoid_rigify.json `
  --out build/t014/boy_yellow_hoodie_1.1.0/engine_export
```

The export passed: 73 bones (39 semantic roles), 56 meshes, eight morph blocks, a 60,891-byte
`character.json`, and a 14,030,000-byte `geometry.bin`.

### Eye-pitch strip

`eye_pitch_strip.py` rendered twelve 320×320 cells at −15°, −5°, 0°, +5°, +10° and +15°, within the 400 px cell
limit. Because Pillow is absent from Blender Python, `eye_strip.png` was recomposed from the individual PNGs with
System.Drawing. Every cell was inspected at original resolution.

| Pitch | 1.0.0 iris visible | 1.1.0 iris visible | Change |
| ---: | ---: | ---: | ---: |
| 0° | 26.5% | 26.5% | 0.0 pp |
| +10° | 18.6% | 26.5% | +7.9 pp |
| +15° | 16.8% | 24.8% | +8.0 pp |

Visual result: **PASS for the T-014 upward-gaze defect**. The 1.1.0 pupil remains plainly visible at +10° and
+15°, the rest pose is unchanged, and no lid/eyeball intersection or render artifact is visible. The full-tracking
row also shows the intended downward following at negative pitch.

### Boy and girl face checks

- `face_test.py` on the boy 1.1.0 candidate passed all four states: neutral eye visibility 37.2%, Blink 0.0%,
  Smile corner lift +4.5 mm, and JawOpen mouth opening 13.6 mm. Maximum skin stretch was 1.0 in every state.
- The current-branch girl build completed in 53.4 s. `face_system_test.py` completed 28 controls, 34 expression/AU
  states and ten gaze cases. Open gaze at ±20° horizontal and ±12° vertical had zero lid overlaps and zero glasses
  overlaps; blink gaze had 0.0% visible eye surface in every direction. A task-local image-composition shim was used
  only because Pillow was unavailable; the test calculations and Blender renders were unchanged.

### Girl render regression against `origin/main` 573a065

The baseline charsys was obtained with read-only `git archive 573a065 pipeline/charsys`. Its archive SHA-256 is
`e5cc91e236b2bd5fb917621a5072dd239613c56801ee413f1d4fc2089077832e`; the archived blobs for `face.py`,
`face_generic.py`, `build_character.py` and `body_v6.py` exactly match commit
`573a065989e3f285ad66019f055b3c3d51f24bc8`.

Both sources built the girl from the same spec and rendered the same neutral 300×300 Eevee head close-up in Blender
5.3.0. Decoded 8-bit RGB comparison across all 90,000 pixels: **max absolute difference 0, mean absolute difference
0.0, changed pixels 0**. The 28-control/34-state/ten-gaze-case face-system metrics are also exactly equal between
the two builds. See `girl_origin_573a065_head.png`, `girl_current_head.png`,
`girl_render_compare.png` and `girl_pixel_compare.json`.

### T-010 frames 30–60 attempt

`make_t014_shot.py` succeeded and `run_shot.py` completed the prepare stage from cached boy/girl masters and engine
packages. The fresh run directory was `build/t014/build/runs/t014-1.1.0-final`; existing failed run directories were
not overwritten. The run then failed at the bake stage before any frame was rendered:

```text
FileNotFoundError: [WinError 2] The system cannot find the file specified
```

The missing file is `build/apps/render-cli/plush-render` (or `plush-render.exe`). No renderer binary exists in the
repository or elsewhere under `D:/Animation`, the public repository has no release/action build artifact, and this
host has no CMake, Ninja, MSVC, Clang or GCC toolchain with which to build it. Therefore there is no engine bake,
no 640×360 frames 30–60, no executed OIDN render, no `measure_shot` result, and no contact strip to inspect. These
checks are recorded as FAIL, not silently treated as pending or passed. A synthetic/non-engine bake was deliberately
not substituted.

`face_system_test.py` applies only to `face_generic/1`; the boy retains his legacy face geometry and uses the shared
lid-binding rule. `face_test.py` is the applicable boy face test.

## Final checks

| Check | Result |
| --- | --- |
| Boy 1.1.0 candidate build | **PASS** — Blender 5.3.0, 13.4 s, zero unweighted vertices after cleanup |
| Engine package export | **PASS** — clean `engine_export` directory; 73 bones, 56 meshes, 8 morph blocks, 14,090,891 bytes total |
| Eye strip generation and inspection | **PASS** — twelve 320 px cells inspected; +15° iris visibility 16.8% → 24.8% |
| T-010 prepare | **PASS** — resolved scene/cast produced; both character builds and packages cached |
| T-010 engine bake | **FAIL** — `plush-render` is absent and cannot be built on this host |
| T-010 frames 30–60, 640×360, 16 samples, OIDN | **FAIL** — no bake, therefore zero of 31 frames rendered |
| `measure_shot.py` | **FAIL** — no `bake.json` exists |
| Contact strip generation and visual inspection | **FAIL** — no rendered frames exist |
| `verify_charsys.py --version 1.0.0` | **PASS** — build, geometry fingerprint, store tests and reuse test all pass |
| `test_export_engine.py` | **PASS** — 8/8 checks |
| Boy `face_test.py` | **PASS** — neutral/Blink/Smile/JawOpen metrics and eight renders completed |
| Girl build | **PASS** — current branch and archived 573a065 control builds completed |
| Girl `face_system_test.py` | **PASS** — 28 controls, 34 states, ten gaze cases, zero gaze overlaps |
| Girl pixel regression vs 573a065 | **PASS** — max 0, mean 0.0 across decoded RGB pixels |
| Shared-rule source review | **PASS** — no character-name branch; girl remains at 0.7/0.3 head/eye weights |
| Frozen `versions/1.0.0` and `tests/data` working-tree diff | **PASS** — Git-clean; no frozen file was rewritten |
| 1.0.0 manifest payload byte hashes | **FAIL (pre-existing checkout issue)** — `.blend` and `.glb` match; four Git-clean JSON payloads are CRLF and do not match the published LF hashes |
| Publish/approve safety | **PASS** — no publish or approve command ran; no 1.1.0 store version or pointer exists |
| C++ `ctest` | **FAIL (environment)** — no C++ toolchain is installed |


### T-010 frames 30–60 with 1.1.0 (Supervisor, cloud engine bake)
`t010_shot_1.1.0_frames30-60.png`: frames 30, 36, 42, 48, 54, 60 at 960×540, Cycles 16 samples. Bake and render PASS on Linux. The eyes are open in 30, 36, 54 and 60 (irises visible, with the character's heavy lid design). In 42–48, at maximum head pitch, the eyes are mostly hidden by the fringe from this camera, not closed. In 1.0.0, frames 34–60 were closed.
