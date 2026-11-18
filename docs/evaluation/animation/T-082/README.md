# T-082: calm elbow for the boy in the e905 hand-over (collision follow-up to T-047)

Branch `t-082-claude-collision-elbow`, from `t-047-claude-collisions@91dae13` with `origin/staging` (8943332) merged
in (clean merge). Lane C, path B: the owner checks the before/after renders.

## 1. Task and objective
The boy's elbow must stay low and calm in the e905 cup hand-over: T-047 put it up beside his head (84° swing, a
"wing" elbow). Everything T-047 achieved must stay, and the girl's result must not change.

## 2. Result: **complete, with one deviation to decide** (section 8.1)
- The boy's largest elbow swing is **37.5°** (T-047: 83.7°). The aim was about 30°.
  - The planner keeps the swing at the 30° limit. It goes past the limit only where the limit, the wrist push and
    the torso lean together still leave the forearm inside the body. Beyond the limit it swings only far enough to
    keep the forearm out (≥ 0 mm), not to the 5 mm margin. In e905 that happens on 10 frames (f42 to f51), while
    the giver must hold the cup still.
  - The elbow stays **60 mm below the shoulder**. T-047 had it 9 mm below, and planning off has it 70 mm below.
- The boy's forearm and hand stay outside the body (**+0.5 mm**). Contacts are exact (≤ 0.0003 mm) and animcheck
  passes.
- Every planner correction changes by ≤ 1.5°/frame (the lean by ≤ 0.5°/frame). The boy's arm is no longer faster
  than his unplanned arm (+1.8°/frame; T-047: +4.5°/frame).
- **The girl is unchanged in every T-047 measure** (section 5): her left arm is identical per frame. Her right arm
  differs by at most 0.73 mm, because her reach swing (32.5°) is now held at 30° and a small wrist push does the rest.
- e904 s010, e904 s020 and e906 s010 are **bit-identical to T-047** per frame.
- The boy now leans his upper body back by up to 8° while he holds the cup out. This is new visible motion
  (section 7).

## 3. Files changed
| File | Purpose |
| --- | --- |
| `engine/scene/collision.h`, `engine/scene/collision.cpp` | `CollisionBody::maxElbowSwing`: the elbow swing limit, character data. It is read from and written to the package block as `"max_elbow_swing_deg"` (optional; 0 to 120). The shared default `kDefaultMaxElbowSwingDeg` is 30. |
| `engine/scene/interaction.h`, `engine/scene/interaction.cpp` | The planner keeps the swing within the limit. Past the limit it allows only the swing needed to keep the forearm out (≥ 0 mm). New: the torso lean (step 3 of the arm planner). `swungArmGap` takes an optional limit; the hand-over point is still scored with the full range. |
| `engine/scene/actions.cpp` | The `collision` action takes `"maxElbowSwingDeg"` (0 to 120), a per-shot override for one character. An invalid value is a load error. |
| `pipeline/charsys/export_engine.py` | The export/6 `collision` block writes `"max_elbow_swing_deg": 30.0`, so a character version freezes the value. export/4 and export/5 are unchanged. |
| `tests/test_collision.cpp` | New case: the limit as block data (default, round trip, optional field, out-of-range values refused), the scene override and its errors, and `swungArmGap` with a limit. |
| `tests/test_interaction.cpp` | New case: an e905-like hand-over held still close to the giver's chest (section 5). |

Evidence in this folder:
- `README.md` (this report).
- `measure_t082.cpp`: T-047's measurement tool, plus the largest swing, the lean and the elbow height. It is not
  built by CMake.
- `make_sheet_t082.py`: makes the sheet, the side strip and the MP4.
- The JSON files listed in section 5, and the media files in section 7.
- The renders use `../T-047/render_t047.py` unchanged. The contact and prop tools are `../T-047/contacts_e905.cpp`
  and `../T-047/prop_clearance_e905.cpp`, also unchanged.

## 4. What was implemented
**Swing limit (data).** The limit belongs to the character's collision body.

Where the value comes from, in order of precedence:
1. The scene's `{"type": "collision", "character", "maxElbowSwingDeg"}`, for one shot.
2. The package block's `"max_elbow_swing_deg"`, frozen with the character version (export/6).
3. The shared default of 30°.

There are no character names in code.

The e905 shot has no override, and no released package has a block yet (export/6 is not registered; T-047 item
8.1). Both characters therefore use the default.

**Planner order per IK arm (T-047's order, with T-082's changes):**
0. **Arm lift** for the clip part of the arm (unchanged).
1. **Elbow swing**, searched only up to the limit. If no swing within the limit reaches the margin, the swing becomes
   the best one within the limit. If even that leaves the forearm inside the body, the swing may go past the limit,
   but only as far as keeping the forearm outside (≥ 0.5 mm), never to the margin. This last resort comes after the
   push and the lean, because the swing is re-planned after each of them.
2. **Wrist push**: unchanged. It still fades to 0 at contacts and while the giver holds still.
3. **Torso lean (new)**: for frames that are still short after steps 1 and 2.
   - Per frame, the planner looks for the smallest lean that lets the limited swing clear the arm, in 0.25° steps up
     to 8°. It tries eight level directions: euler degrees on the generated `<who>/spine.rot` track, added to what
     the track already holds.
   - Per span of such frames, the lean keeps one direction (the need-weighted mean). Its size is the smallest
     envelope above the needs that changes by at most 0.5°/frame.
   - The IK keeps the wrists in place, so contacts and holds stay exact. The swing is then re-planned on the leaned
     body.
   - The planned lean is also written to `<who>/collision.lean.<hand>`, for measurements only.

**Hand-over point**: still chosen as in T-047, with the full swing range as a proxy for "this point can be cleared".

Decision: scoring the hand-over point with the limited swing moved the meeting point 4 to 9 cm (higher, towards
the girl). That raised the girl's elbow to the shoulder (−2 mm, or +15 mm when both arms are limited) and her
speed-up to 8.7 to 15°/frame. That broke "the girl's result stays as in T-047", so it was reverted. The meeting point
is now T-047's, and the girl's reach does not move.

**Rejected alternatives (measured on e905):**
- A strict 30° limit with an 8° lean leaves the boy 4.0 mm inside the body.
- A strict 30° limit needs a 13.5° lean to clear.
- With the lean capped at 5°, the swing must reach 48.7° (elbow 49 mm below the shoulder).
- The forearm meets the lower torso section (`torso_lower_3`, carried by the spine bone), which a spine lean barely
  moves.

## 5. Tests executed
| Command | Result |
| --- | --- |
| `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build` | builds, no warnings in the changed files |
| `build/tests/plush_tests` | **129 / 129 test cases, 36572 / 36572 assertions** (T-047 branch: 119; staging added 8; T-082 +2) |
| `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` | **PASS**: clip_gestures 6, personality 3 + limits, wave_touch 4; 0 failures; thresholds unchanged |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <bpy 5.3 wrapper>` | **13 / 13 PASS** |
| `python3 tools/animcheck/animcheck.py --bake <e905 T-082 bake> --check` | **PASS**, 0 failures (`animcheck_e905_s010.json`) |
| `python3 tools/check_all.py --base origin/staging --task T-082 --blender <bpy 5.3 wrapper>` | section 6 |

The new test case `a held-still hand-over close to the giver's chest keeps the elbow low (swing limit)` uses boy 1.0.0
as the giver and the girl m3 package as the receiver. It sets the hand-over point 8 cm in front of the giver's
shoulder, 8 cm towards his centre line and 10 cm down.

| | full range (120°) | limit 30° (default) |
| --- | --- | --- |
| largest swing | 46.2° | 30.0° (no swing past the limit is needed) |
| lean | 0° | 1.0° (0.5°/frame) |
| elbow above the shoulder | −50 mm | −67 mm |
| gap | 4.7 mm | 4.6 mm |

Both runs: no warnings, contacts < 5 mm, the prop is continuous.

### e905 s010, current approved casts (boy 1.1.0, girl 0.10.0), every frame, on the collision body
- Scene: `../T-047/shots/e905_s010_current/shot.scene.json` (unchanged), prepared and baked with `run_shot.py
  --stages prepare,bake`. The bpy 5.3 module ran as Blender.
- The "T-047" column is the same scene evaluated with the T-047 code at 91dae13: the branch build before any T-082
  edit (`clearance_e905_s010_current_cast_t047_code.json`). It matches T-047's report.
- T-082: `clearance_e905_s010_current_cast.json`.

| arm | off (mm) | T-047 gap | **T-082 gap** | T-047 swing | **T-082 swing** | T-082 lean | elbow above shoulder: off / T-047 / **T-082** (mm) | speed-up T-047 / **T-082** (°/f) | rates swing / lift / push / lean |
|---|---|---|---|---|---|---|---|---|---|
| boy L | 2.7 | 2.7 | **2.7** | 0 | **0** | 0 | −116.7 / −116.7 / **−116.7** | 0.0 / **0.06** | 0 / 0 / 0 / 0 |
| boy R | −71.9 | 5.2 | **0.5** (f45) | 83.7 | **37.5** (f42) | 8.0° (f42) | −69.8 / −9.1 / **−59.6** | 4.49 / **1.84** | 1.50 / 1.52 / 4.0 mm / 0.50 |
| girl L | −31.7 | 1.0 | **1.0** | 0 | **0** | 0 | −89.9 / −83.7 / **−83.7** | 0.49 / **0.49** | 0 / 1.50 / 0 / 0 |
| girl R | −23.3 | 1.0 | **1.0** | 32.5 | **30.0** | 0 | −39.4 / −38.2 / **−39.3** | 4.93 / **4.97** | 1.50 / 1.51 / 0 / 0 |

- **≥ 0 mm on the collision body: PASS** on every arm. The engine reports no warning.
- **Contacts: PASS** (`e905_contacts.json`):
  - boy grasp f17: 0.00004 mm; held f17 to f51: ≤ 0.0003 mm;
  - girl grasp f46: 0.0002 mm; held f46 to f72: ≤ 0.0002 mm;
  - prop jump at the parent switches: 0.0002 mm.
- **Held cup**: its surface stays ≥ 34.7 mm (boy) and ≥ 33.8 mm (girl) from the bodies (`e905_prop_clearance.json`;
  T-047: 28 / 34 mm).
- **Rates**:
  - Every planner correction is ≤ 1.5°/frame. The boy's lift is 1.52°/frame, the same as T-047: the envelope's size
    is limited to 1.5°/frame and its direction turns slightly.
  - The lean is ≤ 0.5°/frame and the wrist push ≤ 4 mm/frame.
- **Girl, no regression**:
  - Left arm: identical to T-047 per frame (0.000 mm).
  - Right arm: per-frame gap within 0.73 mm on 28 frames (f30 to f45, her reach). Her swing is held at 30° instead
    of 32.5°, and a small wrist push does the rest. Her minimum gap (1.0 mm), elbow height and speed-up (+0.04°/frame)
    are unchanged.
  - Her meeting point and contact are unchanged.

### Other T-047 shots (casts as the shots declare them)
`clearance_e904_s010.json`, `clearance_e904_s020.json` and `clearance_e906_s010.json`: every arm's per-frame gap is
identical to T-047's files (0.000 mm). No swing or lean is planned there. The e904 animcheck failure on the cut-off
wave is the pre-existing one T-047 reports. These shots were not re-run through animcheck, because their bakes are
identical.

Not tested:
- A real Blender export pinned to export/6: export/6 is still unregistered (T-047 item 8.1).
- The e90x shots with personality profiles: none of them enables one.
- Cycles renders of the girl: her poses are unchanged within 0.73 mm.

## 6. Baselines and gate
- No frozen asset, spec, package, baseline image, `content/` or `tests/data/` file was changed.
- export/4 and export/5 output is unchanged (`test_export_engine.py` 13/13).
- The shot builds live in ignored `build/` folders. The e905 working copy used for the bakes
  (`episodes/e905_props_test/shots/t082_current/`) was not committed.
- `tools/check_all.py --base origin/staging --task T-082 --blender <bpy 5.3 wrapper>` was run on the branch with
  `origin/staging` 581b01d merged in. The Blender tier used the bpy 5.3.0 module (Python 3.13) behind a `blender`
  wrapper, not a Blender executable.
  - PASS: Frozen assets, Shared-systems lint, C++ build, Python tests and links. The Blender tier's export, face,
    garment, groom, determinism and verify_charsys checks passed. Only its regression part failed (below).
  - **FAIL Guarded paths**: `tests/test_collision.cpp` and `tests/test_interaction.cpp` need Supervisor approval.
    They are this task's own test files, inside the claimed write-set; only test cases were added, and no existing
    check was loosened.
  - **FAIL Write-set** in that run: `episodes/e905_props_test/shots/t082_current/shot.scene.json`. This was my
    untracked working copy of the e905 shot, never committed. It was moved out of the repository after the run.
    The committed diff touches only claimed paths.
  - **FAIL C++ tests**: only the two CTest image regressions, `regression_milestone01` (rmse 0.0464) and
    `regression_face_neutral` (rmse 0.0406). These are the same values T-047 recorded on staging in a container
    without Open Image Denoise. `plush_tests` passes 129/129.
  - **FAIL Blender tier, regression boy_yellow_hoodie**: "engine export differs: character.json". The fingerprint
    is byte-equal, the renders are within noise and fidelity is 66.41 vs 66.41.
    - **origin/staging fails identically in this container**: `tools/regression/run.py --character
      boy_yellow_hoodie --base origin/staging`, run in an origin/staging worktree with the same wrapper.
    - The exported `character.json` carries no `collision` block, so the T-082 exporter change does not reach it.
    - The cause is the environment (the bpy module build of the master), not this task. GitHub CI, with its pinned
      dependencies, is the evidence for this tier.
    - girl_auburn_bun_glasses and girl_white_hair_blue_dress PASS.

## 7. Visual results
All renders use the e905 current-cast bakes: planning off, T-047 on (the T-047 code) and T-082 on. Each one becomes a
`shot.blend` (`shot_render.py --blend-only`), and `../T-047/render_t047.py` renders the boy alone.
- The girl is excluded from the view layer, and the table (`prop.table_top`, `prop.table_leg`) is hidden.
- The camera box is taken from frame 42 for all three variants.

| File | Content |
| --- | --- |
| `t082_e905_f42_boy_cycles_sheet.jpg` | **6 Cycles stills** (32 spp, OIDN) of the boy at e905 **f42**, the frame of the largest swing. Front and 3/4 (45° to his right); off \| T-047 on \| T-082 on. |
| `t082_e905_f42_boy_side_workbench.png` | Workbench extra, the same frame seen from his right side (90°). The front and 3/4 views hide the elbow behind the cup and the head. This view shows it. |
| `t082_e905_boy_handover_off_t047_t082.mp4` | The boy's hand-over, frames 24 to 63, from his right side, off \| T-047 \| T-082 side by side (Workbench, 960×430, H.264, 40 frames at 24 fps). |

What the renders show:
- **Off**: the right forearm folds into the chest.
- **T-047**: the elbow curls up to the shoulder, beside the head: the "wing".
- **T-082**:
  - The upper arm hangs forward and down, the elbow stays well below the shoulder, and the forearm rises to the cup.
  - He leans back slightly, by up to 8° at f42.
  - The cup (in front of his chin) and the hand-over point are the same as in T-047.
  - In the front view the lean is visible as a small tilt of the upper body and the head away from his right arm.
- Identity, materials, face and hair are unchanged; only the boy's arm and upper-body pose differ.
- The cup stays high, in front of his face, in all three variants. The wrist path (hold f19 to f30, hand-over point)
  comes from the scene and T-047's search, not from this task.

## 8. Problems, limitations and open questions
1. **Swing 37.5° instead of ≤ ~30°** on 10 held-still frames (f42 to f51). This is what keeps the forearm outside
   the body there.

   | Alternative | Result (measured) |
   | --- | --- |
   | Strict 30° limit, 8° lean | 4 mm inside the body |
   | Strict 30° limit | needs a 13.5° lean |
   | Lower or further hand-over point | moves the girl's reach (rejected, section 4) |

   Owner choice:
   - accept 37.5°;
   - allow a larger lean (about 13°, more visible); or
   - give e905 a lower hand-over point (`"at"`, a shot edit outside this write-set), which would let both arms stay
     calm.
2. **The limit is not linked to the personality profile.** `content/personality/*` and `engine/anim/personality.*`
   are outside this write-set, and e905 enables no profile.
   - Today the value comes from the package block (export/6), the scene override, or the shared default (30°).
   - A profile field such as `"arm": {"max_elbow_swing_deg"}` would be a small follow-up if the owner wants it per
     personality.
3. **export/6 is still unregistered** (T-047 item 8.1). No released package carries the block yet, so every
   character uses the default until then.
4. **New motion: the torso lean** (≤ 8°, ≤ 0.5°/frame). It is planned only where the limited swing and the wrist
   push cannot clear an IK arm, which in the tested shots is only the e905 giver. The lean limit is a planner
   constant (8°), not character data.
5. The upper arm and elbow are still reported only (`upper_gap`): boy R −68 mm (T-047: −81 mm), mostly the armpit band.
6. Guarded paths: see section 6.

## 9. Commits
`git log t-047-claude-collisions..t-082-claude-collision-elbow`. The READY line names the final SHA.

## 10. Resource use
Token usage is not available. Repeated work:
- The six Cycles stills were rendered twice: the first pass did not hide the table, because the object names in
  the blend are `prop.*`.
- One exploratory parameter scan for the new interaction test (27 hand-over points, removed afterwards).
- Lean/limit sweeps on e905 (limit 35/40/45°, lean 5/8/14°).
