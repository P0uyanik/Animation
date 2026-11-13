# Iteration 4 — acceptance report

_Date: 2026-11-13. Every number below was measured on the cloud build container (4-core Intel Xeon @ 2.1 GHz,
15 GB RAM, no GPU). Your computer has not been measured; nothing here predicts its speed._

**Verdict:** the three characters are clearly closer to your designs than in iteration 3 (side-by-side sheets
below), skin now has subsurface scattering, and a shot can be described with actions instead of bone keys —
characters breathe, blink, look, walk, grip, lift, place and touch, and an automatic camera cuts to close-ups at
the key moments. **The characters are not yet identical to the references** (list below). Character approval is
yours: I have not treated them as approved. **Iteration 5 has not been started.**

Status words: Implemented · Tested · Visually inspected · Incomplete · Not tested.

## Inputs
- References on disk: three character sheets, the lineup, three classroom stills, one video (`docs/references/`).
- **Missing:** the second animation reference video mentioned in the brief was never in this workspace (only
  `video_watertable.mp4`). Nothing in this iteration is based on it.
- Phase A analysis: `docs/ITERATION_04_PHASE_A_ANALYSIS.md` (measured eye size/spacing/face proportions).

## Deliverables
| # | Deliverable | Where | Status |
| --- | --- | --- | --- |
| 1 | Updated models A, B, C | `content/characters/*.character.json` (from `tools/charkit.py`) | Implemented, visually inspected; awaiting your approval |
| 2 | Turnarounds (front, three-quarter, side, back) | `renders/it4/lineup_{front_1280x960,threequarter,side,back}_*.png` | Rendered, visually inspected |
| 3 | Face close-ups | `renders/it4/face_{A,B,C}_900.png` | Rendered, visually inspected |
| 4 | Hair close-ups (three-quarter and back) | `renders/it4/hair_{A,B,C}_{threequarter,back}_900x700.png` | Rendered, visually inspected |
| 5 | Clothing close-ups | `renders/it4/cloth_{A_dress,B_vest_blouse,C_hoodie}.png` | Rendered, visually inspected |
| 6 | Expression sheets (10 each) | `renders/it4/expression_sheet_{girl_white_hair,girl_brown_glasses,boy_dark_hair}.png` | Rendered, visually inspected |
| 7 | Reference vs iteration 3 vs iteration 4 | `docs/iteration4/compare_{A,B,C}_ref_it3_it4.png`, `compare_ABC_ref_it3_it4.png` | Done (same camera for It3/It4) |
| 8 | Improved group scene | `renders/it4/group_watertable_v4_wide_f172_1280x720.png` + director shots f62/f92/f146 | Rendered, visually inspected |
| 9 | Short animation (natural movement and interaction) | `renders/it4/watertable_v4_640x360_30fps.mp4` (6 s, 180 frames, 30 fps) | See "Animation" |
| 10 | Test results | below | Tested |
| 11 | Performance and memory | below | Measured (cloud machine only) |
| 12 | Documentation | state files, `docs/ACTIONS_AND_DIRECTOR.md`, TD-26…34 | Updated |
| 13 | Backup | git bundle (see final report) | Done |

## What changed, by priority
**1. Character fidelity** (Implemented, visually inspected)
- Faces (all): eyes larger (iris 31–34°) and wider-set, deep-set so lids fit; shorter upper face, lower fuller chin
  (mouth ≈0.3 eye spacings above the chin, as measured on reference A); smaller embedded nose.
- Mouths: resting mouth baked into the skin with dark interior, upper teeth and tongue (A small open smile, B wide
  grin, C slight frown, closed); expressions fill or grow the opening.
- Hair: felted clump volumes for fringes and crowns (A, B) and the whole of C's spiky hair; a soft hair mass under
  A's and B's locks; A's buns ×1.22 and bow ×1.6; B's fringe swept from a centre parting.
- Garments: A short bodice + bell skirt + ribbed hem band; B one-piece V-neck vest in dusty rose with felt flower
  motifs; C looser hoodie with ribbed cuffs/hem and the pouch pocket on the new surface, wider joggers gathered at
  the ankle. Hands: two-segment fingers on finger bones.

**2. Materials** — random-walk subsurface scattering for skin (Implemented, tested); ribbed rib bands (Implemented).
Not done: skirt relief pattern, seams, pocket flaps/buttons on B's vest pockets, suede/felt changes beyond iteration 3.

**3. Natural animation** — life layer, actions (look, expression, reach with lean, touch, walk), generated tracks
that never override hand keys (Implemented, tested). Not done: running, sitting, turning in place, two-handed
actions, collision with furniture.

**4. Hands** — curl/thumb/spread/point and contact grasp that adapts to object size (Implemented, tested).

**5. Water-table benchmark** — `content/scenes/watertable_v4.scene.json`: C walks in; B grips the floating boat,
lifts it, looks at it, puts it back (ripples); A is surprised, then touches the water (ripples); everyone breathes
and blinks; **no hand-made keys**. Director shot list: wide → medium (reach) → insert (grip) → close-up (B with the
boat) → insert (placing) → insert (touch) → wide.

**Cinematic presentation** — director (Experimental): shot planning, focus on the subject with f/2.8 close-ups,
push-ins, cuts; manual camera keys override it. Occlusion check covers characters only.

**Environment** — bunting, toy shelf with plush toys and blocks, round rug (modest, as asked).

**30 fps** — default for new scenes. The 24 fps of the iteration-3 video was a test setting carried over from
milestone 01; iteration-3 scenes keep it so their regressions stay valid.

## Still different from your designs (visible in the comparison sheets)
**A:** side locks are thick cords that end at the chest; the reference has many thin wavy/curly locks to the waist ·
skirt flares less and lacks the knitted wave pattern; legs+boots still slightly long · buns are coiled locks, the
reference buns are fluffy felt balls.
**B:** the open mouth reads as surprised rather than the reference's happy smile (corners not lifted, cheeks not
raised) and the brows are thick and flat where the reference's are thin and arched (`face_B_900.png`) · curls are more
regular and less voluminous around the face, and their roots show as round knobs beside the head in three-quarter
view (`hair_B_threequarter_900x700.png`) · glasses frames thinner and lighter than the
reference's dark brown frames · vest lacks the fair-isle band and pocket buttons; shorts slightly long.
**C:** hair clumps more uniform in size and direction than the reference's mix of large and small clumps · hands not
in the hoodie pocket (reference pose) · trouser cuffs less bunched.
**All:** eyes show a bit more white around the iris than the references, most visibly in three-quarter views where
the eyeball's side shows (`hair_A_threequarter_900x700.png`); hand/finger shapes are stubby.

## Tests (all passing at the end of the iteration)
- `plush_tests`: 24 test cases (iteration 3's 16 plus: mesher brick culling vs exhaustive; subsurface furnace test
  (base 0.5 → 0.526, 0.95 → 0.949); fingers (fist, point, grasp adapts 27° vs 16°); blinks (count, determinism);
  life (breathing moves the chest; head turns 0° two frames after a gaze jump, 21° fifteen frames after);
  reach (wrist 51 mm from the object at contact, carried ≥3 cm up, left where placed, gaze on it); walk (arrives
  exactly, 0/59 frames with both feet sliding, feet lift ~2 cm); touch (index fingertip 1.4 mm from target)).
- Image regressions: milestone 01 (unchanged, RMSE 0.016 ≤ 0.03), v2 face (unchanged), A/B/C lineup
  (re-baselined on purpose for the new characters; the iteration-3 image is kept as `lineup_abc_320x240_it3.png`).
- Studio save/reopen round trip on a copy of the v4 scene: see "Studio" below.

## Performance and memory (cloud machine)
MEASUREMENTS_PLACEHOLDER

## Process notes
- Tried and rejected (all logged in `DEVELOPMENT_LOG.md`): opening mouths with morph targets (crumpled, lining hid
  the interior); uniform channel choice in the subsurface walk (fireflies); per-primitive culling margin in the
  mesher (changed the face slightly); 12/40 relaxation passes (lumps).
- A leftover iteration-3 frown helper with old coordinates was found and removed (it moved the cheeks).
