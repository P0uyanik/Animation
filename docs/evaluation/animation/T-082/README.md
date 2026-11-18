# T-082: a calm, natural hand-over for the boy in e905 (collision follow-up to T-047)

Branch `t-082-claude-collision-elbow`, from `t-047-claude-collisions@91dae13`, with `origin/staging` merged in (581b01d,
clean). Lane C, path B: the owner checks the renders.

## 1. Task and objective
In the e905 cup hand-over, the boy's elbow must stay calm, with no "wing" elbow beside his head. Everything T-047
achieved must stay.

**Owner direction (2026-11-18, after the first READY):** the goal is natural, realistic motion that matches the
references and the boy's personality, not a number such as the swing angle. The owner then approved re-staging the
e905 hand-over (option "Re-stage the shot").

## 2. Result: **complete; path B (the owner judges the renders)**
- **The cause was the staging, not the elbow solver.** The e905 hand path carried the cup up to the boy's chin:
  - the `hold` after the pick-up lifted it 10 cm;
  - the hand-over point was "0.4 arm below the shoulders", measured from the cup's base, but he holds the grip
    6.6 cm higher.
  - With 23 cm arms, a cup in front of the face leaves only bad poses: a wing elbow (T-047, 84° swing), a curled
    arm, or a lean back (the first T-082 READY, 37.5° swing plus an 8° lean). None matches his references.
- **The re-staged e905 is derived from each character's natural hand.**
  - The natural hand is an easy, almost straight arm held forward and a little down. That is how short-armed chibi
    characters hand things over, and it keeps the cup low, the elbows down and the heads apart.
  - The cup is picked up where his hand naturally is and held out low; nothing lifts it.
  - The girl stands across the cup, offset so the two right hands line up instead of crossing their own bodies.
- **Boy (current casts and declared casts):**
  - the planner needs no correction at all: no elbow swing, no wrist push, no torso turn;
  - his forearm stays 10.7 mm outside his body, his elbow stays low (54 mm below the shoulder), and he holds the cup
    out at his own height.
- **Girl:** she needs only a 7.5° elbow swing to take the cup (T-047: 32.5°). Her elbow stays 40 mm below her shoulder
  (T-047: 38 mm).
- **Heads:** at least 34 cm apart, head centre to head centre (old staging: 19 cm, with their hair overlapping).
- Contacts are exact (≤ 0.0003 mm). The cup stays 75 to 78 mm from both bodies. animcheck passes, and there are no
  warnings.
- e904 s010, e904 s020 and e906 s010 are bit-identical to T-047 per frame.
- **Planner:** the elbow swing limit stays (30° by default, character data). The backward lean is gone. The last
  resort for a held-still hand-over is now a small turn of the upper body about its vertical axis (≤ 15°,
  ≤ 0.5°/frame), as a person turns into a close hand-over. e905 no longer needs it.

## 3. Files changed
| File | Purpose |
| --- | --- |
| `episodes/e905_props_test/make_shot.py` | **Re-staging** (owner approval 2026-11-18; outside the original claim, see 8.1). Placement comes from the natural hands (`ARM_REACH` 0.93 of the arm, `ARM_DROP` 20° below horizontal). The cup is at his natural hand and lifted only 1 cm. Her natural hand is across the cup (`HANDOVER_GAP` 3 cm). T-022's 22° cheat towards the camera is kept. The camera is perpendicular to the pair, on the side where the hands meet. Her neck assist for looking down is 20° (`life.gaze.assistPitchDeg`). The derivation is written into the shot (`x_t082_staging`). No character names: everything comes from the package skeletons. |
| `episodes/e905_props_test/shots/s010/shot.scene.json` | Regenerated with `make_shot.py --boy-package --girl-package`, using the declared casts' packages. |
| `engine/scene/collision.h`, `engine/scene/collision.cpp` | `CollisionBody::maxElbowSwing`: the elbow swing limit as character data. The package block field is `"max_elbow_swing_deg"` (optional, 0 to 120); the shared default is 30°. |
| `engine/scene/interaction.h`, `engine/scene/interaction.cpp` | The planner keeps the swing within the limit. Past the limit it swings only far enough to keep the forearm out (≥ 0 mm). New last resort: a torso turn (step 3). `swungArmGap` takes an optional limit; the hand-over point is still scored with the full range. |
| `engine/scene/actions.cpp` | The `collision` action takes `"maxElbowSwingDeg"`, a per-shot override (0 to 120). |
| `pipeline/charsys/export_engine.py` | The export/6 block writes `"max_elbow_swing_deg"`. export/4 and export/5 are unchanged. |
| `tests/test_collision.cpp` | The limit as block data (default, round trip, optional field, refused values), the scene override and its errors, and `swungArmGap` with a limit. |
| `tests/test_interaction.cpp` | A held-still hand-over close to the giver's chest: at 30° the elbow stays ≥ 1 cm lower than with the full range, the turn is vertical-axis only (≤ 15°, ≤ 0.5°/frame), the arm stays clear and the contacts are exact. |

Evidence in this folder:
- `README.md` (this report).
- `shots/e905_s010_current/shot.scene.json`: the re-staged shot with the current approved casts.
- `measure_t082.cpp`: T-047's tool, plus the largest swing, the turn and the elbow height.
- `render_frames.py`: renders chosen frames of a shot.blend through the shot's camera or a given one.
- `make_sheet_t082.py`: makes the sheet and the MP4.
- JSON results (section 5) and media (section 7).

## 4. What was implemented
**Staging rule (`make_shot.py`).**
- A character's *natural hand* is its right wrist with the arm held easily forward: 0.93 of the arm length, 20°
  below horizontal, from the right shoulder of its package skeleton.
- Why this rule: the boy's references show low, practical hands and elbows in. At these proportions (boy arm 23 cm,
  girl 18 cm, large heads) an elbow tucked at the side reaches only about 11 cm forward. That puts the two heads
  together (measured: 26 cm head-centre distance, hair overlapping). A nearly straight, lowered arm keeps the hands
  low and the heads apart.
- The cup stands on the table just outside and in front of his natural hand. He picks it up and holds it out,
  barely lifted.
- Her natural hand is across the cup from his (cup width + 3 cm). Her position follows from that.
- **Rejected alternatives (measured):**
  - The girl's left hand: the cup's second handle (`grip_b`) faces her right, so her left arm would need swings
    above 90°.
  - A larger spacing with a lower cup: out of reach for her 18 cm arm; she leans in and her head meets his.
- Her neck assist for looking down is limited to 20° (default 35°). She looks down at the cup more with her eyes.
  With 35° her hair touches his head at f38 to f46 (head centres 0.325 m apart; with 20°, 0.347 m).
  - His references do show their heads close together (`pb f272`, `f287`; "positions himself close to her").
- The camera stands perpendicular to the line between the two, on the hand-over side, 1.75 m away at 0.9 m height.
  The old camera looked along the line in which they are now offset, so she would hide him.

**Planner (unchanged from the first READY except step 3):**
1. Elbow swing, limited by the character's `maxElbowSwing` (30° default). Past the limit the swing only keeps the
   forearm out of the body (≥ 0 mm), as a last resort.
2. Wrist push (unchanged).
3. **Torso turn**, replacing the lean:
   - Only for frames the limited swing and the push leave short.
   - The upper body turns about its own vertical axis (spine Y), either way, in 0.25° steps up to 15°.
   - Per span the turn keeps one direction, and it changes by at most 0.5°/frame. The IK keeps the wrists, so
     contacts stay exact.
   - Never a lean: leaning back from a held object contradicts the references.
   - Tracks: generated `<who>/spine.rot`, and `<who>/collision.turn.<hand>` for measurements.

## 5. Tests executed
| Command | Result |
| --- | --- |
| `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build` | builds, no warnings in the changed files |
| `build/tests/plush_tests` | **129 / 129 test cases, 36715 / 36715 assertions** |
| `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` | **PASS** (clip_gestures 6, personality 3 + limits, wave_touch 4; 0 failures) |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <bpy 5.3 wrapper>` | **13 / 13 PASS** |
| `run_shot.py --stages prepare,bake` on `episodes/e905_props_test/shots/s010` and `shots/e905_s010_current` | both bake, no engine warnings |
| `animcheck.py --bake <e905 bake> --check` (both casts) | **PASS**, 0 failures (`animcheck_e905_s010.json`) |
| `tools/check_all.py --base origin/staging --task T-082 --blender <bpy 5.3 wrapper>` | section 6 |

### e905, every frame, on the collision body
Files: `clearance_e905_s010.json` (declared casts) and `clearance_e905_s010_current_cast.json` (boy 1.1.0 / girl
0.10.0). The two are identical. The old staging with the T-047 code is `clearance_e905_s010_current_cast_t047_code.json`.

| arm | old staging, T-047 | first T-082 READY (old staging) | **re-staged T-082** |
|---|---|---|---|
| boy R gap | 5.2 mm | 0.5 mm | **10.7 mm** (clear without planning) |
| boy R swing / turn or lean / wrist push | 83.7° / 0 / 0 | 37.5° / 8° lean back / 4 mm/f | **0 / 0 / 0** |
| boy R elbow below shoulder | 9 mm | 60 mm | **54 mm** |
| boy R cup height | in front of the chin | in front of the chin | **his natural hand height (table)** |
| girl R swing / lean | 32.5° / 0 | 30° / 0 | **7.5° / 0** |
| girl R elbow below shoulder | 38 mm | 39 mm | **40 mm** |
| girl L | lift 16° (vest) | same | **same (T-047's lift, per frame)** |
| head centres, closest | 0.19 m | 0.19 m | **0.34 m** |

- The boy L and girl L clip arms are planned exactly as in T-047: the boy's needs nothing, and the girl's hanging
  left arm gets T-047's lift away from her vest.
- **Contacts: PASS** (`e905_contacts.json`):
  - boy grasp f17: 0.00006 mm; held f17 to f51: ≤ 0.0003 mm;
  - girl grasp f46: 0.00001 mm; held f46 to f72: ≤ 0.0001 mm;
  - prop jump at the switches: 0.0002 mm.
- **Held cup**: ≥ 78 mm (boy) and ≥ 75 mm (girl) from the bodies (`e905_prop_clearance.json`; old staging: 28 / 34 mm).
- **Rates**: every planner correction is ≤ 1.5°/frame (girl swing and lift). The boy has none.

### Other T-047 shots
`clearance_e904_s010.json`, `clearance_e904_s020.json` and `clearance_e906_s010.json` are identical to T-047's per frame
(0.000 mm). These shots need no swing, push or turn.

Not tested:
- A real Blender export pinned to export/6 (not registered; T-047 item 8.1).
- Personality-profile scenes: e905 enables none.
- e905 at other resolutions or with other cameras than the ones listed in section 7.

## 6. Baselines and gate
- No frozen asset, spec, package, baseline image, `content/` or `tests/data/` file was changed.
- export/4 and export/5 output is unchanged.
- The e905 shot builds stay in ignored `build/` folders.
- `tools/check_all.py --base origin/staging --task T-082 --blender <bpy 5.3 wrapper>`, on the final branch (staging
  581b01d merged). The Blender tier used the bpy 5.3.0 module behind a `blender` wrapper.
  - PASS: Frozen assets, Shared-systems lint, C++ build, Python tests and links. In the Blender tier, everything
    except the boy regression passed.
  - **FAIL Guarded paths**: `tests/test_collision.cpp` and `tests/test_interaction.cpp`. These are the task's own
    test files: test cases were added, and nothing was loosened. They need Supervisor approval.
  - **FAIL Write-set**: `episodes/e905_props_test/make_shot.py` and `shots/s010/shot.scene.json`. This is the
    owner-approved re-staging (8.1); the claim needs widening.
  - **FAIL C++ tests**: only the CTest image regressions `regression_milestone01` (rmse 0.0464) and
    `regression_face_neutral` (rmse 0.0406). These are the values T-047 recorded on staging in containers without
    Open Image Denoise. `plush_tests` passes 129/129.
  - **FAIL Blender tier, regression boy_yellow_hoodie**: "engine export differs: character.json". The fingerprint is
    byte-equal, the renders are within noise and fidelity is 66.41 vs 66.41.
    - **origin/staging fails identically in this container**: `tools/regression/run.py --character
      boy_yellow_hoodie --base origin/staging`, run in an origin/staging worktree with the same wrapper.
    - The exported `character.json` carries no `collision` block, so the exporter change does not reach it.
    - GitHub CI, with its pinned dependencies, is the evidence for this tier.

## 7. Visual results
Renders are made from the current-cast bakes (boy 1.1.0, girl 0.10.0):
- each bake becomes a `shot.blend` (`shot_render.py --blend-only`);
- per-character stills use `../T-047/render_t047.py` (the girl excluded, the table hidden, the camera box from
  f42);
- whole-shot frames use `render_frames.py`, through each shot's own camera.

| File | Content |
| --- | --- |
| `t082_e905_f42_boy_cycles_sheet.jpg` | **6 Cycles stills** (32 spp) of the boy at f42, front and 3/4: old staging with planning off \| old staging with T-047 \| re-staged T-082. |
| `t082_e905_restaged_shot_camera_frames.jpg` | The re-staged shot through its camera: f17 (pick-up), f30, f38, f46 (her contact), f51 (his release), f60 (Cycles 12 spp). |
| `t082_e905_handover_t047_vs_restaged.mp4` | The whole shot, f1 to f72: T-047 (old staging, old camera) \| T-082 (re-staged, new camera), side by side (Cycles 12 spp, 1280×390, H.264, 3 s). |

What the renders show:
- **Old staging:**
  - With planning off, his forearm sinks into his chest.
  - With T-047, the cup is in front of his chin and the elbow is raised.
  - In the whole shot the two heads overlap while she reaches.
- **Re-staged:**
  - He picks the cup up from the table at his own hand height. He holds it out forward and low on an easy arm,
    elbow down, head down, with heavy lids and no extra motion. This matches his references (low, practical hands,
    elbows in, low-key).
  - She reaches with a nearly straight arm and takes it with her right hand; their right hands meet without crossing
    their bodies.
  - Their heads come close at the moment of the hand-over (f38 to f51); her hair brushes his fringe. The references
    show them this close (`pb f272`, `f287`).
- Identity, materials, face and hair are unchanged.
- Changed by the re-staging: their positions (offset, 0.5 m apart), the table position, the camera, and her neck
  assist.

## 8. Problems, limitations and open questions
1. **Write-set**: `episodes/e905_props_test/make_shot.py` and `shots/s010/shot.scene.json` are outside T-082's claim.
   - The owner approved the re-staging in the session on 2026-11-18. No running task claims them.
   - The Supervisor needs to add them to the claim; the gate's Write-set check reports them until then.
2. The staging constants (`ARM_REACH`, `ARM_DROP`, `HANDOVER_GAP`, the girl's neck pitch) are shot data in the
   generator. If more hand-over shots follow, they could become a shared staging helper; that was not done here.
3. **The girl's neck assist (20°)** is a per-shot life setting, not her personality profile. Her profile
   (`content/personality/`) is outside this write-set.
4. **The limit is not linked to the personality profile.** It comes from the package block, the scene override, or
   the shared default.
5. **export/6 is still unregistered** (T-047 item 8.1).
6. The head is still not part of the collision body. Their hair can touch: 0.34 m between head centres at the
   closest, at f38. The references show them that close.

## 9. Commits
`git log t-047-claude-collisions..t-082-claude-collision-elbow`. The READY line names the final SHA.

## 10. Resource use
Token usage is not available. Repeated work:
- The first READY solved the elbow on the old staging. The owner's review moved the fix into the staging, so those
  renders and measurements were redone.
- The staging was searched in several rounds:
  - lower hand paths;
  - a torso turn;
  - the girl's left hand;
  - offset spacings;
  - natural-hand spacings (q1 to q6);
  - neck assists of 25°, 20° and 15°.
  Each round was measured, and the promising ones were rendered.
