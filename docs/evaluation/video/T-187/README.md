# T-187 · Paper-boat test scene (low-quality preview, not for publication)

Owner request ~22:45 CET 21 Nov: three children sit in a classroom; the girl with glasses (auburn) makes a paper boat,
everyone is surprised, she gives the boat to the boy, then they stand up together and walk off. Branch
`t-187-claude-paper-boat`. Episode `episodes/e912_paper_boat/`. **Status: CHECKPOINT** (first full preview).

## What to look at
| File | What |
| --- | --- |
| [`T-187_paper_boat_h264.mp4`](T-187_paper_boat_h264.mp4) | the whole scene, H.264, 640x360, 24 fps, Cycles 4 spp + denoise (preview quality) |
| [`contact_sheet.jpg`](contact_sheet.jpg) | one tile every 0.5 s plus the first frame of every shot (yellow label = cut) |
| [`preview_frames.jpg`](preview_frames.jpg) | the cheap 4 spp check frames, one per shot, rendered before the full run (some before the last camera moves) |
| [`assembly.json`](assembly.json) | clip frame -> scene, scene frame, shot |

Cast (the current released characters): `boy_yellow_hoodie` 2.3.0 and `girl_auburn_bun_glasses` 0.14.0 (cast
`"current"`), `girl_white_hair_blue_dress` 0.1.0 (published version dir: she is not in the fidelity baseline that
`"current"` reads). Seating, camera left to right: white-hair girl | auburn girl | boy.

## Shots (24 fps)
| Shot | Clip time | Scene, frames | Camera | Who does what | Existing system |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0-2.5 s | s010 f41-100 (60 f) | wide, front | all seated at the table, the sheet in front of her; she looks at it, the others at her, then at the sheet; at the end her left hand goes to the sheet | T-175 `cmu_sit_down` (held), `look`, `emotion` girl_eager, `touch` |
| 2 | 2.5-6.0 s | s010 f101-184 (84 f) | medium on her: face + hands, the others at the frame edges | her hands alternate on the sheet's near corners (5 touches, 15 f apart); no finger folding, the framing sells it; the boy focused, the white-hair girl curious | `touch`, `look`, `emotion` boy_focused / curious |
| 3 | 6.0-9.5 s | s020 f41-124 (84 f) | medium wide, all three, from above the table | **cut: the boat is there** where the sheet was; she picks it up (left hand) and shows it; the boy and the white-hair girl are surprised (eyes on the boat); she is delighted | verbs `pick_up` + `carry` with T-185 r3 `fingerClose`, `emotion` surprised / girl_delighted |
| 4 | 9.5-13.0 s | s020 f125-208 (84 f) | two-shot, her and the boy | the hand-over: her left hand to his right (shared hold 20 f), she looks at him, he at the boat, then at her, then smiles | verb `pass` (e907/e910 hand-over) with r3, `carry`, `emotion` happy |
| 5a | 13.0-15.0 s | s030 f45-92 (48 f) | wide, front | all three stand up together; the boy has the boat in his hand | T-175 `cmu_stand_up` (+ foot-lock, foot_home), `idle_relaxed` |
| 5b | 15.0-18.1 s | s030 f93-166 (74 f) | side-on | cut: they walk off to the right in single file (boy first) | T-175 `cmu_walk` (+ foot-lock); position / yaw stepped at the cut as in T-175's review shot |

Total 434 frames, 18.1 s. Timing profile `calibrated` (T-104/T-106) on every scene; life on (sway off: it fights the
seat), personalities on.

## How it is built
- **Three scene files, two scene cuts.** s010 = shots 1-2 (sheet), s020 = shots 3-4 (boat), s030 = shot 5. The cut
  2 -> 3 swaps the sheet for the boat without any prop popping inside a scene; the cut 4 -> 5a lets s030 move the
  table back (below). Camera cuts inside a scene are step keys on `camera.position` / `.target` / `.lens`.
- **Hidden pre-roll in every scene:** the cast stands at the stools (idle), sits down from f6 (`cmu_sit_down`, 28 f)
  and is seated by ~f35; the rendered ranges start at f41 / f41 / f45. Bakes cover all frames, so hair springs and
  clips are settled when the render starts.
- **Feet on the floor (T-175 compensation):** each character's scene position is raised by its sole depth under the
  origin: boy 27.1 mm, auburn 29.5 mm (T-175), white-hair girl 23.8 mm (measured here from her 0.1.0 package,
  `measure_staging.py`). Lowest shoe point over the rendered frames: 0.0 mm in s010 / s020; s030 (stand + walk)
  -0.8 / -1.0 / -3.9 mm (white / auburn / boy).
- **Staging from a bake** (`shots/measure` -> `measure_staging.py` -> `staging.json`): a stool under each seated
  pelvis (top = 2nd percentile of the pelvis-carried vertices, T-175's rule). The children's arms are short (shoulder
  to wrist 0.18 m for the girls, 0.27 m for the boy; hand 0.05 / 0.08 m), so the table is high (top 0.45 m, 8 cm under
  her seated shoulders) and its near edge 5.5 cm in front of the seated chests; her touch targets sit in front of each
  shoulder (targets nearer the middle are pushed out by the arm-body clearance, T-030). Standing, the chests come
  8-13 cm forward, so s030 has the table 11 cm further back (nobody touches it there).
- **Props** (episode-local, `episodes/e912_paper_boat/content/assets/`, primitives, material preset `paper_white`
  = the renderer's plain Principled fallback, no new material): `origami_sheet` (15 cm square, 1.2 mm), `paper_boat`
  (hull box 100 x 26 x 42 mm with grasp sites `side_a` / `side_b` on its two ends; hand-over gives `b` and receives
  `a`), `paper_boat_sail` (a thin square turned 45 deg on the hull: a triangle above it) and `paper_boat_end` (two
  flared ends), parented to the hull's sockets.
- **Shot 5: the boat rides in the boy's hand.** s030 parents the boat to his `hand.R` from the start, with the hand ->
  boat offset measured at the end of s020's hand-over (`BOAT_IN_HAND`). No hold IK there: a `carry` target is a world
  point, and kept through the stand-up the arm-body clearance pushed the hand 15-20 cm across his body (tried; also a
  pick-up during the sit-down drifts because its lift is planned from the standing body).
- **The walk-off travels (supervisor check 1).** Yes, L -> R: the travel is the `cmu_walk` clip's own root motion
  (`root.cycle_offset`, as in T-175's review shot); the characters' scene position and yaw are constant during the
  walk (stepped once at the 5a -> 5b cut), which is what the foot-lock's character-space pin needs. Hips over
  f93-166 (s030 bake): boy x -0.45 -> 0.84 m (0.42 m/s), auburn -0.97 -> 0.36 (0.44 m/s), white -1.50 -> -0.36
  (0.37 m/s), depth unchanged. No `walk` action and no camera move.
- **Grasp:** every verb carries T-185's r3 `fingerClose` key for key (`episodes/e910_showcase/make_shot.py` `R3`).
  main was merged with T-186 (grip natural keeps the prop still from contact to lift) before the final bakes.

## Known defects (acceptable for this test; not fixed here)
1. **Hair contact / hair springs:** the hair spring chains flag most of the popping (motion check: hair 12 / 15 / 43
   flags in s010 / s020 / s030 rendered ranges, most around the stand-up and the first walk frames; at the 5a -> 5b
   cut the characters are moved, so the springs swing for a few frames after the cut). The auburn girl's ringlets and
   bun touch the neighbours' heads when she bends over the sheet (seats 0.40-0.43 m apart, the heads are ~0.3 m wide).
2. **Grasp:** the boat is a box, not a cup: the r3 thumb-up grip closes round the hull's end face; small finger
   pops at contact / release (hand and finger flags: 24 / 13 / 13). In shot 5 the boy's fingers are not closed round
   the boat (it is parented to the hand, no grasp action), it reads as held loosely.
3. **Garment at deep bends:** auburn's shorts and the boy's trousers go under the skin while seated and in the walk
   (interpenetration flags 7 / 4 / 22; T-175 open point 1, garment side).
4. **Arm into body:** her left / right arm passes 18-28 mm into her body for a few frames between touches (f98,
   f180) and before the pick-up (s020 f51) (bake warnings).
5. **Table:** high for the children (they sit chest-high to it) and it moves 11 cm back between shot 4 and shot 5a
   (hidden by the cut and the wide framing). In 5a they stand behind it, the table edge at their waists.
6. **Head bowed in shot 2:** while she works the sheet her head is bowed low, so the face reads mostly through the
   glasses and brows.
7. **Feet** sit up to 3.9 mm under the floor in the walk (T-175: soft step), 0 mm seated.
8. Motion-check tallies above are over the rendered frames only; the pre-roll and the scene cuts are not counted.

## Commands
```
python3 episodes/e912_paper_boat/make_shots.py --stage measure      # the seated cast, no furniture
python3 pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/measure/shot.scene.json --blender <b> --stages prepare,bake --run-dir m3
python3 episodes/e912_paper_boat/measure_staging.py episodes/e912_paper_boat/shots/measure/build/runs/m3/bake.json --frame 50
python3 episodes/e912_paper_boat/make_shots.py                      # shots/s010, s020, s030
# per scene: bake all frames, then render the range in x_t187.render_frames
python3 pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/s010/shot.scene.json --blender <b> --stages prepare,bake
python3 pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/s010/shot.scene.json --blender <b> \
    --profile review --samples 4 --resolution 640 360 --codec h264 --frames 41-184 --stages render,encode
python3 episodes/e912_paper_boat/preview.py s010 <run-id> 60,140      # cheap check frames (subset bake, 4 spp)
python3 episodes/e912_paper_boat/assemble.py -                       # clip + contact sheet + assembly.json
```
