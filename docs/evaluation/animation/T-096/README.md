# T-096: inter-character clearance and visible grip (round 2, Phase C)

Branch `t-096-claude-clearance-grip` from `origin/integration/round2-bc` at input `4910b69`. Lane C, path B (the owner
judges the renders). Task: [docs/tasks/T-096.md](../../../tasks/T-096.md).

## 1. Objective
Keep two characters' heads (and hair) apart, keep the cup visible while it is held and handed over, and find and fix
the 4.5 mm cup-hold drift on boy 2.0.0. All new behaviour is opt-in; existing shots bake identically.

## 2. Result: **complete** (path B: the owner judges the sheet)
| Criterion | Before | After | Evidence |
| --- | --- | --- | --- |
| 1. Heads, e905 latest staging (current cast) | touching: closest head/hair vertices **0.07 mm** (f48); volumes overlap −20.3 mm | **36.6 mm** closest vertices; volumes ≥ 30.1 mm; neck tilt ≤ 12.5°, ≤ 0.6°/frame | `data/e905_before.json`, `data/e905_after.json` |
| 1. Heads, diagnostic lean-in (current cast) | touching: **0.05 mm** | **13.8 mm**; volumes ≥ 10.0 mm (clearance 10 mm); tilt ≤ 12° (they start close: tilted from f1) | `data/lean_in_before.json`, `data/lean_in_after.json` |
| 2. Zero change by default | — | 15/15 existing shot bakes **bit-identical** (input-SHA binary vs branch binary); 132/132 doctest; ctest green | `data/existing_shot_bakes_base_vs_branch.txt` |
| 3. Cup visible from the shot camera (e905) | hold f25 **23 %**, contact f46 **23 %**, shared f50 **31 %** | f25 **70 %**, f46 **74 %**, f50 **74 %** (f17–52: 63–74 %) | `data/e905_*.json` → `visibility` |
| 4. Cup-hold drift, boy 2.0.0 (f17–51) | **4.51 mm** (f51) | **0.10 mm** (f48.5) | `data/e905_*.json` → `drift` |
| 5. Visual | cheap first frame, then one strict sheet before/after | | `t096_cheap_first_frame_f46.jpg`, `t096_e905_before_after_sheet.jpg` |
| 6. Engine tests | | 8 new C++ tests (4 collision, 4 interaction) | `tests/test_collision.cpp`, `tests/test_interaction.cpp` |

### The 4.5 mm drift: cause
Measured per frame (palm point in the cup's frame, every half frame): the boy's hold is exact from his grasp (f17)
to the girl's contact (f46, ≤ 0.0003 mm). The drift starts at **f48** and grows to **4.51 mm at f51** (his release).
- At f46 the cup's parent switches to the girl's hand, while the boy holds his wrist still until he lets go.
- The girl receives with her arm at full reach. After her contact her base idle sways her shoulder back: her IK
  target stays put, but it goes out of reach (**185.5 mm needed, arm 180.0 mm**, f52). Her wrist falls short (4.5 mm at
  f51, 5.5 mm at f52) and the cup goes with her hand.
- The boy's frozen hand stays where it was, so his palm separates from his socket. It is a reach shortfall of the
  receiver during the shared hold, not solver precision (contacts stay ≤ 0.0003 mm).
- **Fix (opt-in `followSharedProp`):** while both hold the cup (her contact → his release) his palm follows its own
  socket every frame (the existing contact correction, now per frame). His return path takes the last offset out
  gradually, so the release does not step. Result: 0.10 mm (between keys at half frames). Her reach is not changed:
  re-staging her closer is a staging decision (see 8).

## 3. Files changed
| File | Purpose |
| --- | --- |
| `engine/scene/collision.h`, `engine/scene/collision.cpp` | Head and hair volumes: `CollisionSphere`, `CollisionBody::heads` (empty unless asked), `addHeadVolumes`, `headSpheres`, `headGap`. Never written to or read from the package block. |
| `engine/scene/scene.h`, `engine/scene/scene.cpp` | Switch parsing only: the scene key `"interaction"` (`InteractionOptions`, `interactionOptionsFromJson`), loaded, checked and saved as written. |
| `engine/scene/interaction.h`, `engine/scene/interaction.cpp` | Head volumes when opted in; the head clearance pass; `applyHeadTilt`; the hand-over shared span (`followSharedProp`); `visibleGrip` (turned grip and its side approach). |
| `tests/test_collision.cpp` | 4 tests: head volumes (opt-in, cover every head vertex, ≤ 13 mm spheres, not in the block) on 4 character sources; the signed gap; the switch (checked, saved, typos are errors); every option off = the behaviour before T-096. |
| `tests/test_interaction.cpp` | 4 tests: head clearance on a lean-in (necks only: hands, chest and neck joint unchanged, gaze kept, ≤ 15°, ≤ 0.6°/frame); `followSharedProp` (giver on its socket within 0.5 mm, no snap at the release); `visibleGrip` on 3 skeletons and for a hand-over receiver. |

Not changed: `content/assets/felt_cup.asset.json`. The cup needed no new socket (see 4.3). Exporter, renderer,
`actions.cpp`, published or frozen files: untouched.

Evidence in this folder: this README, `measure_t096.cpp` (the measuring tool), `make_sheet_t096.py` (the sheet),
`shots/` (four diagnostic shots, cast `"current"`), `data/` (measurements) and the two JPEGs.

## 4. What was implemented
**Switch (opt-in).** A scene key `"interaction"`. Every field is optional and off by default; an unknown key or a bad
value is a load error.
```json
"interaction": {"headVolumes": true, "headClearance": 0.03, "followSharedProp": true, "visibleGrip": true}
```

### 4.1 Head and hair volumes (`collision.h`)
- Taken from the character's own mesh: every rest vertex carried by the head bone or its descendants (≥ 50 % of the
  weight: skin, hair, ears, eyes, glasses), all carried by the head bone.
- Shape: a **shell of small spheres**, one per 1.5 cm voxel of those vertices (centre: the middle of the group's
  bounding box; radius: its farthest vertex, so ≤ 13 mm). The union covers every head vertex.
- Fit on the current casts: the outer surface lies within **4.1 / 4.3 mm** (median) and **7.6 / 7.9 mm** (p90) of
  the nearest head vertex (boy / girl; max 14.3 mm). The boy has 7,824 spheres, the girl 11,069 (`data/head_volume_fit.txt`).
- Why not one round volume: head plus hair is not convex, and the girl's ringlets reach her shoulders. A
  direction-sphere fit was tried first and overshot by 23 mm (boy) and 82 mm (girl) at the median.
- `headGap` is exact while the heads are apart and negative once the shells overlap (a sign, not a depth). It is
  computed through a grid, so the cost is a few milliseconds per frame.

### 4.2 Head clearance (`interaction.cpp`, option `headVolumes`)
- Per frame where two characters' head volumes come closer than `headClearance`, both heads tilt away from each
  other about their neck, by the same angle each. The angle is the smallest 0.5° step (≤ 15°) that opens the gap,
  measured on the pose as it plays back.
- Then comes the smallest envelope above those angles with at most **0.6°/frame**, so heads ease away and back.
- The tilt axis moves the closest head point horizontally away from the other head.
- The tilt is a generated track `<who>/headTilt`, applied by `applyHeadTilt` **after IK and look-at**. A generated
  `neck.rot` was tried first: the head follow and the neck assist re-aimed the head and cancelled most of it (15° of
  tilt opened about 3 mm).
- The eyes keep their world rotation, so the gaze stays on its target (test: < 0.05°).
- Neck only: hands, forearms, chest and the neck joint do not move (test: < 0.01 mm).
- Frames it cannot clear within 15° are reported as a warning: "move them apart".
- `<who>/collision.headTilt.<other>` records the angle for measurements.
- **Placement of the hook (Supervisor, please confirm):** `applyHeadTilt` is called from the start of
  `applyArmPoles` (interaction.cpp). That point of the pose path is after IK and look-at, so `scene.cpp` stays
  switch-parsing only. A separate one-line call in `kinematicGlobals` would be cleaner, but it is outside the
  write-set. Without the track it is a no-op.

### 4.3 Visible grip (option `visibleGrip`)
- The grasp pose comes from the socket's position and the prop's grasp shape only. On a round prop (the cup's side)
  the same grip therefore fits anywhere around the axis.
- The grasp (and a hand-over receiver) turns the authored socket about the prop's axis by the smallest 5° step
  (≤ 90°) that puts the palm's side of the prop ≥ 65° away from the shot camera. When no allowed turn gets there, it
  takes the allowed turn that gets furthest.
- Allowed turns:
  - The palm side stays within 100° of the character's shoulder (never the far side).
  - For a receiver, the palm side stays ≥ 90° from the giver's socket.
  - The arm stays clear of the body. This is the planner's own forearm and hand capsules for that wrist, with the
    elbow in its present plane, swung within the character's limit. The arm must keep at least the margin, or be as
    clear as with the authored grip.
- The turned socket is added to the scene's in-memory copy of the asset (`grip@boy.R`); the asset file is unchanged.
- A turned grip often holds the near side, palm away from the body (as one takes a glass). Its approach backs off
  sideways and up, never towards the body, so the short forearm does not enter it.
- **e905:** the boy's grip turns 75° to the near side of the cup. The girl's `grip_b` already faces away from the
  camera and is kept. Visible cup goes from 23–31 % to 70–74 %. What still hides it is his cuff (9–13 %) and wrist
  skin (11–12 %); his hand hides ≤ 6 %.

## 5. Tests executed
- `cmake --build build` (Release, `PLUSH_BUILD_RENDERER` default OFF); `ctest` in `build/`: 100 % passed
  (`renderer_tests_skipped` skipped, as configured).
- `build/tests/plush_tests`: **132/132 test cases, 43,152 assertions passed** (8 new T-096 cases included:
  `-tc="*T-096*"` → 8/8).
- Bake identity: 15 existing shots (`episodes/*/shots/*`, `content/scenes/eval/*`) prepared with `run_shot --stages
  prepare` and baked by `plush-render --bake` built at input `4910b69` and on this branch: **15/15 identical SHA-256**
  (`data/existing_shot_bakes_base_vs_branch.txt`). The T-082 latest copy without the switch
  (`shots/e905_s010_current`) also bakes identically before and after the change (`233d57e6…`).
- Measurements: `build/measure_t096 <resolved scene> [--interaction ...] --vis 17,25,30,40,46,48,50,52`.
- Not run: the frozen image regressions need the renderer (OFF here; `engine/render/` is untouched); see 6 for
  `tools/check_all.py`.

## 6. Baselines
- No frozen, published or exporter file changed (`git diff --stat 4910b69` lists only the write-set and this folder).
- Exported packages: unchanged. Head volumes are never written to the collision block (test). export/6 parity is
  untouched.
- `engine/render/` untouched.

## 7. Visual results
- `t096_cheap_first_frame_f46.jpg`: the first cheap frame (f46, shot camera and from above, 16 spp, with the first
  clearance of 10 mm). It showed that 10 mm of mesh clearance still reads as touching in the render: wool and hair
  fibres stand off the mesh. The after-shot therefore uses `headClearance` 0.03 (tilt 12.5° instead of 10°).
- `t096_e905_before_after_sheet.jpg`: the strict sheet. Same cameras, 32 spp. Rows f25 (hold), f46 (contact) and
  f50 (both hold). Columns before / after through the shot camera, then before / after from above.
- Identity: characters, materials, staging and timing are unchanged. Changed: the boy's grip (near side of the cup),
  a head tilt away from the other head (both, up to 12.5° at f38, eased at ≤ 0.6°/frame; the heads are already close
  at f1, so it spans f1–62), and the boy's hand following the cup over f47–51.

## 8. Problems, limitations, open questions
1. **Tilt limit.** 15° clears the e905 hand-over and the lean-in at the e905 spacing. At 0.95 of that spacing the
   lean-in keeps −2.1 mm (volumes; 11.1 mm between vertices) and the engine warns. Closer staging needs re-staging,
   not a larger tilt.
2. **Visual clearance vs mesh clearance.** Fibres need about 3 cm of mesh clearance to read as apart. Should
   `headClearance` default to 0.03 for felt characters? The default stays 0.01, as the task names no number.
3. **Receiver reach (e905).** The girl's arm is at 103 % of its length after her contact (her idle sway). The drift
   is fixed on the giver's side; moving her ~5 mm closer in `make_shot.py` (T-095/T-082 staging, outside this task)
   would remove the cause.
4. `applyHeadTilt` placement (4.2): confirm, or approve a one-line `scene.cpp` call.
5. `shots/` hold the diagnostic copies with cast `"current"`. Their `build/` folders are not committed (gitignored).

## 9. Commits
See the READY line (branch `t-096-claude-clearance-grip`).

## 10. Resource use
Token usage: not available. Repeated work: two head-volume fits and two tilt mechanisms were measured and replaced
(see 4.1, 4.2). One cheap 16-spp still was re-rendered because its side camera was placed inside the girl's hair.
The `.blend` setup takes ~7 min per shot with the bpy 5.3 module (no Blender binary here).
