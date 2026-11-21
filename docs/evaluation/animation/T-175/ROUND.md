# T-175 round file (locomotion layer: CMU importer, foot-lock, chibi style filter)

Keep this current each round so a fresh session can take over. Details and numbers: [`README.md`](README.md).
Branch `t-175-claude-locomotion`. Opt-in only (a clip without a `style` block is untouched).

## Round 2 (2026-11-21): owner style review of the first delivery
### Targets (owner feedback 2026-11-21 ~12:30Z)
| # | Target | State |
| --- | --- | --- |
| 1 | Walk: NOT bouncier, keep the up-down as is | kept: same root motion; the 1-frame pelvis dips at toe-off are gone (soft knee) |
| 2 | Walk: footsteps softer and gentler | done: `soft_step` (foot path low-passed around landing and toe-off), `foot_pitch`, `foot_flat` |
| 3 | Walk: feet sink slightly into the ground | done: `sole_floor` (shoe mesh never under the ground) + the review shot stands the characters ON the floor |
| 4 | Sit: upright 90°, no forward / back lean | done: `seat_lean` 0 while the seat contact holds |
| 5 | Sit: hands resting at the sides of the body | done: `seat_pose` (arms hanging at the sides, head level) |
| 6 | Stand-up: remove the ~90° turn and the extra step | done: `cmu_stand_up` is `cmu_sit_down` played backwards; `--no-turn`; feet at home |
| 7 | Stand-up: the boy's legs intersect | done: `foot_home` (feet stay on their rest positions, legs by IK); knees never cross (test) |
| 8 | Black hands at stand-up | done: no hand (wrist) roles in the mocap clips |
| 9 | Popping check flags on footfalls | done for feet, toes, soles, shins; what is left is listed under "Open defects" |
| 10 | Garment under skin when seated | boy: gone while seated; girl shorts: open, needs the garment side (outside this claim) |

### Current overrides (per clip `style` block, written by `pipeline/clips/import_bvh.py`)
| Key | `cmu_walk` | `cmu_sit_down` / `cmu_stand_up` |
| --- | --- | --- |
| `lean` / `seat_lean` | 0.6 / – | 0.2 / 0 |
| `head_level` | 0 | 0.5 |
| `stride`, `tempo` | 1.0, 1.125 | 1.0, 1.1 |
| `arm_swing`, `arm_out` | 0.85, 25° | 1.0, 0 |
| `foot_lock`, `foot_in`, `foot_release`, `foot_lead` | on, 2, 8, 0 | on, (2), (6), – |
| `soft_step`, `soft_knee` | 3.5 frames, 0.94 | –, 0.94 |
| `foot_pitch`, `foot_flat`, `sole_floor` | 0.6, 1.0, on | 1.0, 1.0, on |
| `foot_home` | – | on |
| `seat_blend`, `seat_pose` | – | 14 frames; upper arms 30° out from straight down, elbows 12°, neck and head level |

Importer options used: walk `--loop auto --style walk --tempo 1.125 --smooth-arms 2`; sit `--frames 195:345 --origin-frame 345
--origin-feet --no-turn --style sit --seat 28:30`; stand the same plus `--reverse --seat 0:2`. Hands are left out by default
(`--hands` keeps them). Exact commands: README "How it works".

Review shot (`make_review_shot.py`): characters stand on the floor (scene position y = 27.1 mm boy / 29.5 mm girl, the
depth of their rest soles under the character origin); stools placed from a first bake (`--seat-from`).

### Open defects
- **Girl's shorts under the skin while seated** (motion check: 25 of 1032 sampled vertices, worst −58 mm; gusset −15 mm). Not
  visible from the review camera. Animation side is done (upright sit, thighs level); the rest is garment skinning at a 90°
  hip bend (`pipeline/charsys/garments_v2/correctives.py` / garment weights), outside this claim. Reported to the
  Supervisor, not edited.
- **Boy's trousers and hoodie in transit** (−12 mm trousers at the deepest forward bend of sit-down / stand-up). Same cause.
- **Remaining popping flags** (motion check on the review bake; none on feet, toes, soles or ankles):
  - walk: boy trousers at the knee on toe-off (9.8 mm/f², ratio 0.49; limits 8 and 0.45), hair spring chains
    (`DYN-*`, present in round 1 too);
  - sit / stand: hands and fingers at the idle ↔ clip hand-overs and when the arms settle, from the arm-body clearance
    planner (`engine/scene/interaction.cpp` `planArmLift`, rate-limited lift; not a T-175 file), and hair spring chains.
- **Packages rest 27 / 30 mm under their origin**: every shot that puts a character at floor height sinks the shoes by that
  much. The foot-lock's ground is the rest sole level; the review shot compensates with the scene position. A package or
  scene-level fix is outside this claim (reported).
- The girl's boot soles (a dark slab under the boots) are now visible because the boots no longer sink.
- Walk arms: the style turns the upper arms 25° outward (`arm_out`) so the clearance planner has nothing to add (its lift
  was 11–43° with a triangle profile, which is what flagged the hands).

### Sheet and clip paths
- Clips: [`clips/walk.mp4`](clips/walk.mp4), [`clips/sit_stand.mp4`](clips/sit_stand.mp4) (review profile).
- Strict sheet (one, both characters, round 1 vs round 2): [`sheet_r2.jpg`](sheet_r2.jpg) + `sheet_r2.json`.
- Cheap preview (8 spp single frames) was checked before the review render: `shots/review/build/runs/pv1_*` (not committed).
- Numbers: [`feet_lock.json`](feet_lock.json), [`feet_nolock.json`](feet_nolock.json), `motion_checks_r2.json`.
- Round 1 sheets (kept for comparison): `sheet_boy.jpg`, `sheet_girl.jpg`.

## Round 1 (2026-11-21, checkpoint 53cf255)
First delivery: importer, three clips, foot-lock (ankle pin), style block (lean, head level, arm swing, stride, tempo).
Owner questions and answers: see round 2 targets.
