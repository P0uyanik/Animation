# T-014 — boy eyelids under upward gaze

Status: **implementation prepared; Blender evidence pending**. The candidate is represented by the base 1.0.0 spec
plus `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json`. It is unpublished and
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

## Evidence

No images are checked in yet because Blender is unavailable on this PC. Do not treat this implementation-only run
as a visual pass. The commands below generate twelve 320×320 close-ups (within the 400 px limit), `eye_strip.png`,
and the 640×360 T-010 frames 30–60 contact strip once Blender is installed.

## Pending Blender steps

Run from the repository root in PowerShell, replacing only the executable path in the first line:

```powershell
$BlenderExe = 'C:\Program Files\Blender Foundation\Blender 5.3\blender.exe'

& $BlenderExe -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json --override assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json --out build/t014/boy_yellow_hoodie_1.1.0 --no-compare

& $BlenderExe -b --factory-startup -P pipeline/charsys/export_engine.py -- --blend build/t014/boy_yellow_hoodie_1.1.0/boy_yellow_hoodie_master.blend --profile pipeline/charsys/rig_profiles/humanoid_rigify.json --out build/t014/boy_yellow_hoodie_1.1.0/engine

& $BlenderExe -b --factory-startup -P pipeline/charsys/tests/eye_pitch_strip.py -- --old assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend --new build/t014/boy_yellow_hoodie_1.1.0/boy_yellow_hoodie_master.blend --out docs/evaluation/characters/T-014

py -3 pipeline/clips/make_t014_shot.py --out build/t014/t010_1.1.0.scene.json
py -3 pipeline/production/run_shot.py --shot build/t014/t010_1.1.0.scene.json --blender $BlenderExe --frames 30-60 --resolution 640 360 --samples 16 --run-dir t014-1.1.0
py -3 pipeline/clips/measure_shot.py --scene build/t014/build/shot.resolved.scene.json --bake build/t014/build/runs/t014-1.1.0/bake.json --out docs/evaluation/characters/T-014
py -3 pipeline/clips/t014_contact_sheet.py --frames build/t014/build/runs/t014-1.1.0/render --out docs/evaluation/characters/T-014
```

Then inspect every eye-strip cell and every contact-strip frame before recording a PASS here. Do not publish or
approve 1.1.0. The existing asset-store command named `publish` is deliberately not part of this procedure: the
store has no separate unpublished staging operation, and publishing would contradict the owner decision.

### Pending checks

```powershell
py -3 pipeline/charsys/verify_charsys.py --blender $BlenderExe --out build/t014/verify_charsys --version 1.0.0
py -3 pipeline/charsys/tests/test_export_engine.py --blender $BlenderExe
& $BlenderExe -b --factory-startup -P pipeline/charsys/tests/face_test.py -- build/t014/boy_yellow_hoodie_1.1.0/boy_yellow_hoodie_master.blend build/t014/face_test_boy_1.1.0

& $BlenderExe -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out build/t014/girl_control --no-compare
& $BlenderExe -b --factory-startup -P pipeline/charsys/tests/face_system_test.py -- build/t014/girl_control/girl_auburn_bun_glasses_master.blend build/t014/face_system_test_girl
```

`face_system_test.py` applies only to `face_generic/1`; the boy retains his approved legacy face geometry and uses
the shared lid-binding rule. `face_test.py` is the applicable boy face test.

## Checks in this Blender-free run

| Check | Result |
| --- | --- |
| 1.0.0 manifest payload hashes | PRE-EXISTING CHECKOUT ISSUE — master `.blend` and `.glb` match; the four JSON payloads are Git-clean but checked out as CRLF (`i/lf w/crlf`) and therefore do not match their published LF byte hashes |
| 1.0.0 asset-store directory / index diff | PASS — no T-014 content changes; the pre-existing CRLF payloads were not rewritten |
| Shared-rule source review | PASS — no character-name branch; girl keeps the same 0.7/0.3 weights |
| `py -3` checks | BLOCKED — `C:\Windows\py.exe` reports `No installed Pythons found!`; the launcher exists but no interpreter is registered |
| Blender build, package export, eye strip, contact strip and face checks | PENDING — Blender is not installed, per relay constraint |
| C++ `ctest` | PENDING SUPERVISOR — no C++ toolchain is available on this PC |

