# T-047: collision system (one collision body per character; arms, hands and props outside the body)

Branch `t-047-claude-collisions` (from `origin/staging` e449ef1; staging had not moved at READY). Lane C,
path A (+ evidence). Redesign of T-040 / T-040r1.

## 1. Task and objective
One collision body per character, exported with the engine package and derived by the engine for packages without it;
the engine answers clearance queries against it and the arm planner keeps forearms, hands and held props outside it,
smoothly, while contacts stay exact.

## 2. Result: **complete, with three items for the Supervisor** (section 8)
- Criterion 1 (exported body): the export/6 code path and its block are implemented and verified against the engine
  on every package (≤ 0.0005 mm). A spec cannot pin `export/6` yet: the per-feature registry
  `pipeline/charsys/versions.py` is outside this task's write-set (one line, 8.1).
- Criterion 3 (smoothness): every correction the planner adds changes by ≤ 1.5°/frame (swing, lift) and ≤ 4 mm/frame
  (wrist push). Two e905 IK arms still move up to 4.5° / 4.9° per frame faster than the unplanned arms (8.2).
- The planned arms change visibly where the old arms were inside the body (the girl's hanging arms in e904/e905/e906
  are turned out by up to 16°). Path A was assigned; this needs the owner's eyes (8.3). No render was made.

## 3. Files changed
| File | Purpose |
| --- | --- |
| `engine/scene/collision.h`, `engine/scene/collision.cpp` | New: the collision body (torso sections + per-bone limb capsules), its fit from the skinned rest meshes, the package block (read/write), clearance queries. |
| `engine/scene/interaction.h`, `engine/scene/interaction.cpp` | Arm clearance on the collision body; the planner (elbow swing, arm lift, rate-limited wrist push, pinned contacts); planning on the playback pose (auto idle); swing and lift tracks in `applyArmPoles`; hand-over scoring with the planned swing. |
| `engine/scene/actions.cpp` | `collision` action (`enabled:false` switches planning off per character, for A/B measurements). |
| `engine/model/character.h`, `engine/model/imported_character.cpp` | `CharacterAsset::collisionBlock` read from the package's `"collision"` block. |
| `pipeline/charsys/export_engine.py` | `export/6` path: export/5 + `"collision"` block (`collision_block()`, the engine fit in numpy). `main()` runs under `__main__` only (so the function can be imported); export/4 and export/5 output unchanged. |
| `tests/test_collision.cpp` | Placeholder replaced by 6 test cases (section 5). |

Documentation / evidence (this folder): `README.md`; `measure_t047.cpp` (measurement tool, not built by CMake);
`collision_block_from_package.py` (export/6 block from a package's own arrays); `contacts_e905.cpp`,
`prop_clearance_e905.cpp`; result JSON files listed in section 5.

## 4. What was implemented
### Collision body (`engine/scene/collision.h`)
- **Body**: 7 torso sections along the spine (2 pelvis, 3 lower torso, 2 upper torso), each carried rigidly by one torso
  role (hips, spine, chest). They have elliptical cross-sections fitted to the torso-carried rest vertices, garments
  included (front half, 99th percentile; the T-030 fit, moved here). The stack is closed, with round end caps.
- **Moving parts**: per-bone capsules: the wrist half of each forearm (carried by `forearm.*`) and each hand (carried
  by `hand.*`, wrist to the 98th percentile of the hand's vertices along the finger direction). The radius is the
  **median** distance of the limb's vertices from its axis (its core). A puffed sleeve or spread fingers lie outside
  the core. That soft layer may touch the body's garment shell, as cloth does.
  - Decision: the 90th percentile made the girl's puffed sleeves (4.5 cm) collide with her vest whenever the arms hang
    down. The median gives 3.5 cm (girl forearm) and 2.0 cm (boy forearm).
- **Rest pose clear by construction**: a forearm that touches the body at rest is shortened towards the wrist (up to
  85 %), then both limbs are thinned to at most 60 %. What remains is kept as a per-limb rest **allowance**: the limb
  may rest that deep, never deeper.
  - Only the engine SDF character (arms modelled hanging against its skirt) needs an allowance: −11 mm forearm.
  - The imported packages have none.
- **Queries**: `sectionGap`, `segmentClearance`, `limbClearance` (signed gap, the point, the unit push direction).
  A capsule is convex and rigid, so the clearance is a continuous, piecewise smooth function of the pose, with one
  inside/outside definition shared by the solver and the evidence. This addresses T-040r1's root cause 1.
- **Source**: the package's `"collision"` block (`plush.collision_body/1`) when it is valid for the skeleton.
  Otherwise the body is derived from the meshes with the same rules. A bad block gives a scene warning and falls back
  to the derived body. Shared roles only; no character names.

### Planner (`engine/scene/interaction.cpp`), inside the action solve
The planner runs in `finishInteractions` (the end of `compileActions`), on the pose as it plays back:
- `prepareAutoIdle` is applied for the planning. The automatic `idle_relaxed` base moved the girl's elbows by about
  2 cm after the old pass ran, which is why arms planned "clear" played back inside.
- The hand-over meeting-point search is also scored on that pose.

Per arm, in this order:
1. **Arm lift** (clip and hand-keyed arms, and the clip share of an IK arm): the whole arm turns about the shoulder,
   along the gap gradient, by the smallest angle that leaves the forearm and hand touching at most (≥ 1 mm).
   - The size follows the smallest envelope above the per-frame need whose rate is ≤ 1.5°/frame, so the move starts
     early and never steps.
   - The size is 0 on full-IK frames. Track: `<who>/abduct.<hand>` (rotation vector in the chest frame).
2. **Elbow swing** (IK arms; replaces T-030's fixed outward pole): the elbow turns about the shoulder→wrist axis, so
   the wrist, the hand and a held prop stay where they are.
   - The planner uses the smallest swing that clears the forearm. Each contiguous span keeps one direction, with the
     same rate-limited envelope (≤ 1.5°/frame).
   - A clear arm gets no swing, so the T-030 pole's unnecessary rotation is gone (wave_touch boy R: 6.6°/frame of
     pole rotation before, 0 now).
   - The swing acts through contacts and holds; it is what freed the pinned e905 arm (T-040's −37.7 mm case).
   - Track: `<who>/swing.<hand>`.
3. **Wrist push** (only where 1 and 2 are not enough): the IK target moves out along the gap gradient.
   - Its size is the smallest envelope above the need with a rate ≤ 4 mm/frame.
   - Near a contact or a held-still span it is capped by 4 mm per frame of distance to it, so it reaches 0 there.
   - It is refined (deficit added and eased again) up to 3 times, with the swing re-planned.
4. After the contacts are re-corrected, the swings are re-planned. They never move a wrist or a hand, so the contacts
   stay exact.

### Exporter (`export/6`)
`collision_block(skel, mesh_arrays)` computes the same body as `deriveCollisionBody` from exactly what the package
stores (engine axes, float32 positions, joints, weights). The block is written only for `export/6`; export/4 and 5
are unchanged.

## 5. Tests executed
| Command | Result |
| --- | --- |
| `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build` | builds, no warnings in the changed files |
| `build/tests/plush_tests` | **119 / 119 test cases, 35355 / 35355 assertions** (staging: 114 cases; +6 collision, −1 placeholder) |
| `build/tests/plush_tests -tc="collision*"` | 6 / 6 (602 assertions) |
| `ctest` (build/) | 2 / 4. `regression_milestone01` (rmse 0.0464) and `regression_face_neutral` (rmse 0.0406) fail. **origin/staging fails both identically in this container** (built and run in a separate worktree: same rmse). The container has no Open Image Denoise; T-040 recorded the same. These scenes have no actions, so the planner does not run on them. |
| `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` | **PASS**: clip_gestures 6 gestures, wave_touch 4 gestures, 0 failures (`animcheck_gate_shots.json`); thresholds unchanged |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <bpy 5.3 wrapper>` | **13 / 13 PASS** (export/4 and 5 paths unchanged) |
| `python3 tools/check_all.py --base origin/staging --task T-047` | see section 6 |

New test cases (`tests/test_collision.cpp`):
- **Body fit** on 4 sources (boy 1.0.0, girl m3, girl m2, engine SDF girl_white_hair): 7 sections and 4 limbs, radii
  in range, rest pose ≥ margin, allowance 0 for the packages.
- **Package block**: round trip, the block wins over the derivation, bad blocks are refused and fall back.
- **Queries**: signed and 1-Lipschitz along a path, one surface crossing, the gradient points out; a hand in the belly
  reads < −20 mm with a forward push; `swungArmGap` ≥ the unswung gap.
- **Planner**: a hand key drives the right arm 21 mm (boy) / 43 mm (girl) into the body; with planning it stays at
  ≥ 1.3 mm, the lift changes ≤ 1.5°/frame, and the clear left arm is bit-identical to the unplanned one.
- **Elbow swing**: turns the elbow by exactly θ about the shoulder→wrist axis; the wrist and the hand rotation stay.
- **Collision action**: an unknown character is a load error.

### Shot measurements (`measure_t047.cpp`, every frame, on the collision body)
Packages: `run_shot.py --stages prepare,bake` with the bpy 5.3 module as Blender. The run_shot casts are as the shots
declare them; both characters were "unpublished build from spec". The animcheck shots use the test packages.

How to read the table:
- **off**: the same scene with `{"type":"collision","enabled":false}`.
- **upper**: the upper arm / elbow surface samples. These are reported only; they rest against the side.
- **rates**: the planner's own corrections per frame: swing (°), lift (°), wrist push (mm).
- **speed-up**: max over frames and arm bones of the planned bone's rotation since the previous frame, minus the
  unplanned bone's.

| shot | arm | off (mm) | **gap (mm)** | upper (mm) | rates swing / lift / push | speed-up (°/f) | warnings |
|---|---|---|---|---|---|---|---|
| e904 s010 | girl L | −9.5 | **1.0** | −19.4 | 0.00 / 0.50 / 0.00 | 0.5 | 0 |
| e904 s010 | girl R | −15.1 | **1.1** | −22.9 | 0.00 / 1.50 / 0.00 | 0.1 | 0 |
| e904 s020 | girl L / R | same as s010 | **1.0 / 1.1** | | | | 0 |
| e905 s010 | boy L | 2.7 | **2.7** | −5.7 | 0 / 0 / 0 | 0.0 | 0 |
| e905 s010 | boy R | **−71.9** | **5.2** | −80.8 | 1.50 / 1.52 / 0.00 | **4.5** | 0 |
| e905 s010 | girl L | −31.7 | **1.0** | −11.6 | 0.00 / 1.50 / 0.00 | 0.5 | 0 |
| e905 s010 | girl R | −23.3 | **1.0** | −24.8 | 1.50 / 1.51 / 0.00 | **4.9** | 0 |
| e906 s010 | boy L | 3.4 | **3.4** | −3.0 | 0 / 0 / 0 | 0.0 | 0 |
| e906 s010 | boy R | 11.3 | **11.3** | −1.9 | 0 / 0 / 0 | 0.0 | 0 |
| e906 s010 | girl L | −32.2 | **1.0** | −18.4 | 0.00 / 1.50 / 0.00 | 0.2 | 0 |
| e906 s010 | girl R | −26.6 | **1.0** | −19.8 | 0.00 / 0.51 / 0.00 | 0.5 | 0 |
| animcheck wave_touch | 4 arms | 12.5 to 42.4 | **12.5 to 42.4** (unchanged) | | 0 / 0 / 0 | 0.0 | 0 |
| animcheck clip_gestures | 4 arms | 6.8 to 16.0 | **6.8 to 16.0** (unchanged) | | 0 / 0 / 0 | 0.0 | 0 |

- **No penetration (≥ 0 mm on the collision body): PASS on every arm of every shot.** The clear animcheck arms are
  untouched (identical poses; their planned tracks are empty).
- **Contacts (e905, `contacts_e905.cpp`, `e905_contacts.json`): PASS.**
  - Palm to socket: boy grasp f17 0.00004 mm, girl grasp f46 0.00014 mm.
  - While held: ≤ 0.0003 mm (boy f17–51, girl f46–72).
  - The prop moves ≤ 0.0002 mm across the parent switches.
  - These numbers are unchanged against planning off (≤ 0.0003 mm).
- **Held prop**: the cup's surface (cylinder proxy) stays ≥ 28 mm (boy) and ≥ 34 mm (girl) from the bodies
  (`e905_prop_clearance.json`). Measured, not planned (8.4).
- **Animcheck on the e90x bakes** (`animcheck_e90*.json`):
  - e905 and e906: PASS.
  - e904 s010/s020: FAIL `wave exit stop_step 0.859`. This is pre-existing: with planning off it fails the same and
    also `ease_out 0.905`. The wave is cut off by the shot's last frame (48). e904 is not a gate shot.
- **export/6 block vs the engine derivation** (`export6_block_vs_engine.jsonl`): ≤ 0.0005 mm in points, ≤ 0.0005 mm in
  radii and allowances, on all 9 packages (4 test packages, 5 spec-built e904/e905/e906 packages). Example block:
  `export6_block_boy_1.0.0_test_package.json`.

Not tested:
- A real Blender export pinned to export/6 (blocked by the registry, 8.1).
- A Cycles render of the planned motion (8.3).
- The e90x shots with T-062 "current" casts: run_shot used the casts the shots declare.
- The full Blender tier of the gate locally: GitHub CI runs it.

## 6. Baselines and gate
- No frozen asset, spec, package or baseline image was changed. No file under `assets/`, `tests/data/`,
  `tests/regression/` or `content/` was touched. The shot builds live in the ignored `episodes/*/build/` folders.
- export/4 and export/5 code paths are unchanged (`test_export_engine.py` 13/13). Existing packages load unchanged
  (no block, so the derived body is used).
- `tools/check_all.py --base origin/staging --task T-047`, run locally without a Blender executable:
  - PASS: Frozen assets, Write-set (25 paths, all inside the claim), Shared-systems lint, C++ build, Python tests and
    links.
  - **FAIL Guarded paths**: `tests/test_collision.cpp` requires Supervisor approval. It is the task's own test file,
    replacing the placeholder as the task asks.
  - **FAIL C++ tests**: only the two CTest image regressions above (no OIDN here; staging fails the same).
  - **FAIL Blender tier**: no Blender executable was given locally. The full tier is required by the engine and
    exporter paths and is never skipped, so GitHub CI runs it.
- GitHub CI on the branch is the evidence for the full tier.

## 7. Visual results
No renders. Change: the girl's hanging arms (e904, e905, e906) are turned out by up to 16° at the shoulder. They hung
9–32 mm inside her collision body: her puffed sleeves into her vest. The e905 hand-over arms take a different elbow
path and meeting point. The boy's clip arms in e905/e906 and every animcheck arm are unchanged. The references were not
compared; that needs the owner (8.3).

## 8. Problems, limitations and open questions
1. **Register export/6** (outside this write-set): `pipeline/charsys/versions.py` needs
   `_r("exporter", "export", 6, "export_engine", declared=False, note="export/5 + collision block (T-047)")`. A spec
   can pin it after that. Until then no package carries the block. The engine derives the identical body from the
   meshes, so the behaviour does not depend on it.
2. **"≤ 2°/frame added rotation"**: the planner's own corrections are rate-limited to 1.5°/frame and 4 mm/frame (all
   shots), so the criterion holds if it means the correction (as T-040 measured it). Two e905 IK arms are faster than
   the unplanned arms:
   - boy R: +4.5° at f60, the giver's return;
   - girl R: +4.9° at f38, the receiver's reach.
   The cause: a planned elbow swing of 20–30° rides on IK ramps that already turn the arm 18–27°/frame (T-061 quintic
   ramps). The hand-over point also moved.
   - Capping the swing at 20° and pushing the wrist instead made it worse (16.9°). This was reverted.
   - Decision needed: accept, or a follow-up that plans the reach path (IK target via-points) outside the body instead
     of swinging the elbow.
3. **Visual change in path A**: the corrected arms look different from before (section 7), with up to 16° of shoulder
   lift on the girl. They now rest against the body instead of inside it. Please review on a render before
   promotion.
   - Open choice: if the owner prefers the old silhouette, the girl's vest-side sections (99th percentile front-half
     fit) or her limb core would have to be thinner, which is a definition change.
4. **Not in the body or not planned**:
   - The head is not part of the collision body.
   - Held props are measured (≥ 28 mm in e905), not planned.
   - The upper arm and the elbow half of the forearm are reported only (`upper_gap`, down to −81 mm at the e905
     giver's shoulder, mostly the armpit band folding with the shoulder).
   - Legs are not checked.
5. **Body definition**: the torso sections are the T-030 fit, so long hair or a backpack behind is not body. The limb
   radius is the median core, so sleeves may overlap the body by up to their soft layer.
6. Guarded paths: none touched.

## 9. Commits
See `git log origin/staging..t-047-claude-collisions`. The READY line names the final SHA.

## 10. Resource use
Token usage is not available. Repeated work:
- The run_shot prepare stage was started three times: a missing `/usr/bin/time`, then a directory instead of the scene
  path.
- One reverted experiment (the 20° swing cap).
