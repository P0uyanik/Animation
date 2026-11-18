# T-095: a readable two-person exchange (Phase C, round 2)

Branch `t-095-claude-exchange` from `origin/integration/round2-bc@4910b69`. Lane C, path B: the owner judges the renders.
Cast `"current"`: boy_yellow_hoodie 2.0.0, girl_auburn_bun_glasses 0.11.0. Blender: the bpy 5.3.0 module behind a
`blender` wrapper (`tools/bpy_blender.py`).

## 1. Task and objective
Make a 2–3 s exchange in which it is clear who notices, who acts and who reacts. At the moment both hands hold the cup,
both faces (both eyes, her glasses) and the cup must be visible from the shot camera. Data only: no engine or
character change.

## 2. Result: **complete; path B (the owner judges the renders)**
- New shot `episodes/e907_exchange/shots/s010` (66 frames, 2.75 s) and the evaluation shot `content/scenes/eval/exchange/`.
- Accepted frame **f48**: both hands are on the cup, both faces are in three-quarter view, both eyes are visible
  (his under the fringe), both lenses of her glasses are visible, and the cup is between the hands.
- No engine change was needed. One gate item is open: `make_eval_shots.py --check` already fails at 4910b69, on
  `eval/handover`. See 8.1.

## 3. Files changed
| File | Purpose |
| --- | --- |
| `episodes/e907_exchange/make_shot.py` | Shot generator. Staging, camera and beats are derived from the two current packages (skeleton shoulders and arm lengths, head and hair extents from the geometry). The derivation is in its docstring and in `x_t095_staging`. |
| `episodes/e907_exchange/shots/s010/shot.scene.json` | Generated with `--boy-package/--girl-package` from the current packages. |
| `content/scenes/eval/make_eval_shots.py` | One `SHOTS` entry: `exchange`. |
| `content/scenes/eval/exchange/shot.scene.json` | Generated (only this shot; see 8.1). |
| `docs/evaluation/animation/T-095/*` | This report, the tools (`measure_t095.py`, `render_frames.py` (a copy of T-082's), `make_sheet_t095.py`), the measurements (JSON) and the media. |

No clip file was needed. Every beat is a shared action: grasp, hold, handover, hold, look and emotion.

## 4. What was implemented
**Staging (references first).** In PB f12/f272 and WT f24 the children stand next to each other at a table, opened to
the camera; the faces are three-quarter, never profile, and the heads are close.
- He stands on the camera's right and she on its left. Each turns 25° (`TURN`) from the camera towards the other.
- The inner hands do the exchange: his right and her left.
- Natural hand (T-082 rule): 0.93 of the arm length, 20° below horizontal, pointing 50° (`ARM_IN`) towards the partner.
- The cup's grip handle is at his natural hand. She stands where her natural hand is at the other handle (grip_b).
  Her position, the shoulder spacing (0.587 m) and the hand-over point all follow from this.
- The hand-over height keeps her handle at her natural hand height. Her 18 cm arm has no slack; his 27 cm arm reaches
  0.88 of its length.

**Faces.**
- The cup is beside each of them, so the default gaze would turn both heads and chests to profile. That was the T-082
  failure: her near eye went behind her hair and glasses.
- Shot life settings, so the eyes do the looking:
  - `headFollow` 0.3;
  - neck yaw assist 15°;
  - no chest twist (`assistBodyYawDeg` 0);
  - her neck pitch assist 10°.
- Result: head yaw stays at about 51° from the camera for both, with the chests at 25°.

**Camera.**
- In front of the pair, 12° above the target.
- Distance 1.49 m, set so both heads (top 1.17 m) and the table fit with a 1.15 margin (16:9, 32 mm).

**Beats (frame of each):**

| Frame | Beat |
| --- | --- |
| f1 | She looks at the table in front of her; he looks at the cup. |
| f4–f18 | **He acts**: reaches for the cup (contact f18). |
| f20–f28 | He offers the cup towards her. |
| **f20** | **She notices**: her eyes go to the offered cup. |
| **f27** | **Her hand answers**: her reach starts 7 frames after the glance. |
| f29 | He glances up at her face. |
| f44 | His eyes return to the cup. |
| **f45–f51** | **Both hands share the cup.** |
| f43 | She is pleased (happy, 0.7). |
| f49 | She looks up at his face. |
| f51 | He releases the cup. |
| f53 | He glances at her. |
| f59 | He looks off to his side (impatient, low-key). |
| f53–f65 | She draws the cup in. |

**Alternatives rejected (measured with quick bakes and the T-082 clearance tool):**

| Variant | Measured | Verdict |
| --- | --- | --- |
| Cup yaw 0 (handles facing each body) | elbow swings up to 54°, 15° torso turns, rotation pops of 117°/frame (her hand, f34) and 75°/frame (his, f58), her forearm 5 mm into her vest | rejected |
| Cup yaw −75° | no pop: largest step 26.5°/frame (his), 14°/frame (hers) | **kept** |
| Cup centred between the natural hands | her short arm missed grip_b by 22 mm | rejected |
| `TURN` 30, `ARM_IN` 0 | head bones 0.49 m apart; hair touching while he looks down | rejected |
| Default neck and chest assists | his head at −82°, hers at 72° (profile) | rejected |
| Her neck pitch at the e905 value (20°) | her hair within 1 mm of his at f30–32 | rejected |
| Her reach at f30, contact f44 | her forearm 6 mm into her vest at the start of the reach | rejected; the longer reach (f27–f45) clears it |

## 5. Tests executed
| Command | Result |
| --- | --- |
| `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build` | builds |
| `build/tests/plush_tests` | **124 / 124 test cases, 36311 / 36311 assertions** |
| `python3 pipeline/production/run_shot.py --shot episodes/e907_exchange/shots/s010/shot.scene.json --blender <wrapper> --stages prepare,bake,render --blend-only` | prepare, bake and blend; **no engine warnings** |
| `python3 tools/animcheck/animcheck.py --bake <e907 bake> --scene <resolved scene> --check` | **PASS** (`animcheck_exchange.json`; the shot has no clip or touch gestures, so nothing is measured) |
| `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` | **PASS** (clip_gestures 6, personality 3 + limits, wave_touch 4; 0 failures) |
| `build/measure_t082 <resolved scene>` (T-082 tool, arm clearance, swing, turn and rates) | `clearance_exchange.json`, table below |
| `python3 docs/evaluation/animation/T-095/measure_t095.py --bake ... --scene ...` | `measure_exchange.json`, table below |
| `python3 tools/check_cast.py --base origin/main` | **PASS** (7 shots, including `eval/exchange`) |
| `python3 content/scenes/eval/make_eval_shots.py --check` | **FAIL on `eval/handover` only**. It fails identically at 4910b69, before this task (8.1). `eval/exchange` is current. |
| `python3 tools/check_all.py --base 4910b69 --task T-095` | PASS: frozen assets, guarded paths, write-set (13 paths, all inside the claim), shared-systems lint, C++ build, C++ tests, Python tests and links. The Blender tier needs `--blender`; see the READY line for that run. |

**Clearance and rates (every frame, collision body).**

| Arm | Smallest gap | Elbow swing | Torso turn | Largest rotation step | Elbow below shoulder |
| --- | --- | --- | --- | --- | --- |
| Boy R (gives) | 1.3 mm | 30° (limit), 1.5°/f | 0 | 26.5°/f (reach f9, return f57) | 73 mm |
| Girl L (takes) | 0.9 mm | 30° (limit), 1.5°/f | 0 | 14.2°/f | 23 mm |
| Boy L, girl R (clip arms) | ≥ 1.0 mm | none | none | ≤ 1.1°/f | — |

**Head-to-head clearance.**
- Measured on the package head, face and hair meshes, skinned per frame, using every 8th vertex.
- Closest: **8.4 cm** at f31; head bones 0.556 m apart.
- On the shared-cup interval f45–f51: **≥ 12 cm** (the tool's search radius) and head bones ≥ 0.578 m apart.

**Contacts and cup-hold drift** (cup origin in the hand bone's frame):

| Span | Hand | Drift |
| --- | --- | --- |
| Shared, f45–f51 | his | ≤ 0.0003 mm, 0.07° |
| Shared, f45–f51 | hers | ≤ 0.0001 mm, 0.07° |
| f18–f51 | his | ≤ 0.0003 mm |
| f45–f66 | hers | ≤ 0.0001 mm |

The engine reports no missed contact.

Not tested:
- The particle hair Blender adds beyond the package hair meshes is not part of the head measurement. The renders show
  the gap.
- Other cameras and resolutions than those listed in section 7.

## 6. Baselines
- No engine, character, frozen, published, `tests/data`, `content/personality`, `content/clips` or `content/assets`
  file was changed (`git diff --name-only 4910b69..HEAD`).
- Not changed: `episodes/e905_props_test/**` and `content/scenes/eval/handover/**`.
- Other eval shots: `--check` reports only the pre-existing stale handover.
- Shot builds stay in the ignored `build/` folder.

## 7. Visual results
| File | Content |
| --- | --- |
| `t095_blocking_cycles6spp.jpg` | The cheap blocking pass (Cycles 6 spp, 480×270): shot camera at f1, 12, 20, 27, 36, 45, 48, 52, 58 and 66, plus the side and top diagnostic views at f20, 30, 48 and 56. Sent with the STATUS for T-098L. |
| `t095_exchange_strict_sheet.jpg` | **Strict sheet.** Columns: pick-up f18, approach f36, both hands share the cup f48, release f53. Rows: shot camera (32 spp), raised side view from her side, top view (16 spp). A reference row: PB f12, PB f157, PB f272, WT f24. |
| `t095_exchange_shot_camera.mp4` | The whole shot, f1–f66, shot camera, Cycles 10 spp, 640×360, 24 fps. |

What the renders show:
- **Matching the references:**
  - side by side at a table, three-quarter faces, heads close but apart, both looking down at the object;
  - the boy is heavy-lidded and low-key, with practical, low hands;
  - the girl's glasses face the camera.
- **At f48:** both faces and both eyes are visible; his eyes sit under his fringe, as in PB f12. Her glasses (both
  lenses) and the cup between the hands are visible.
- **Deviations from the references:**
  - From f1 to f27 his eyes are hidden under his fringe while he looks down at the cup.
  - The shot uses the plain e905 room, not a classroom.
  - The cup is smaller in frame than the boats in the references, and the camera is wider than PB f272.
- **The side view is of limited use.** It looks along the line between them, so her bun and hair cover most of the
  scene. The top view is the readable diagnostic for spacing.
- Identity, materials, face and hair are unchanged; nothing on the characters was touched.

## 8. Problems, limitations and open questions
1. **`make_eval_shots.py --check` fails on `eval/handover`** at the input SHA. T-082 re-staged e905 without
   regenerating the eval copy. Criterion 8 says the eval handover stays unchanged, so I wrote only `eval/exchange`.
   The Supervisor decides whether the handover eval shot is regenerated (it is outside T-095's write-set).
2. The face visibility rests on per-shot life settings: `headFollow`, the neck and body yaw assists, and her neck pitch.
   They could become a shared "exchange" staging helper or a personality default; that was not done here.
3. Each inner hand holds a handle that faces its own body. The cup has two opposite handles, and side by side no
   orientation suits both hands naturally. A socket made for the receiver (T-096 owns `felt_cup` sockets) would allow
   a more natural support grip.
4. Both inner elbows reach the 30° swing limit; the planner keeps the forearms out.
5. With `run_shot` on this container, the first `--blend-only` build once ended with exit 1 (Blender was killed by
   memory pressure while other renders ran); a rerun succeeded.

## 9. Commits
`git log 4910b69..t-095-claude-exchange`. The READY line names the final SHA.

## 10. Resource use
Token usage: not available.

Repeated work:
- The staging was searched in rounds: turn, inner-arm angle, cup yaw, reach timing, neck and head-follow settings,
  each measured by quick bakes (about 25 s each).
- Five blend builds and cheap renders (about 10 minutes each).
- A Workbench pass was wasted: particle hair renders as noise there.
