# T-021: secondary motion (spring chains): visible proof

Status: implemented on branch `t-021-claude-secondary-motion`. Nothing is approved or published.

## Files

| File | What it shows |
|---|---|
| `T021_dynamics_on_vs_off.mp4` | 1280×480: dynamics ON (left) and OFF (right), each panel 640×480. 48 frames, 24 fps, 2 s |
| `T021_keyframes_on_top_off_bottom.jpg` | Frames 8, 14, 20, 28, 34, 40 and 48; ON on top, OFF below |

## Shot

`episodes/e904_secondary_motion/shots/s010` (ON) and `s020` (OFF). The two shot files are identical except that
`s020` sets `"dynamics": false` on the character.

- **Cast:** the girl from the 0.7.1 spec plus the new unpublished override
  `girl_auburn_bun_glasses.dynamics.override.json` (spec_version `0.7.1+dynamics`), which adds only `hair.dynamics`.
  - It defines 28 chains: one bun bone, plus 2–5 bones for each temple puff, side curl, back curl and nape curl,
    91 bones in total.
  - Colliders: a head sphere, a torso capsule and two shoulder spheres.
- **Animation (existing material only):**
  - `idle_relaxed` base clip;
  - `happy` emotion;
  - `wave` clip (speed 1.35);
  - keyed neck and head turns: 0° → +46° (frames 6–13), then → −42° (frames 24–31), then held.
- **Pipeline:** `run_shot.py`, stages prepare → bake → render → encode. Engine bake `plush.shot_bake/1`, then Blender
  5.3 Cycles at 16 samples with OIDN denoising, 640×480.
  - Bone reconstruction error in Blender: ≤ 0.0024 mm (ON) and ≤ 0.033 mm (OFF).
  - Engine bake time: 0.5 s for 48 frames, including the spring simulation.
  - Render time: about 380 s per run.

## What to look for

- **After each head turn** (frames 13–20 and 31–40), the side and back curls lag behind, swing out past the rest
  shape and then settle back. With OFF they move rigidly with the head.
- **The bun** gives a small lag of 1–3 cm, held to 12°.
- **Collision:** with ON, no chain joint enters the head collider. The minimum clearance to the sphere plus the joint
  radius is 0.0 mm, meaning joints reach the surface and are held there. With OFF it is 24.7 mm.

## Measurements

Tip offset of each chain, ON vs OFF, from the two bakes, in mm. Before the first turn the offset is the gravity sag
caused by the idle clip's slight head tilt.

| Chain | Max | Frames 1, 7, 13, 19, 25, 31, 37, 43 |
|---|---|---|
| back_curls.06 | 124 | 8 9 17 25 24 50 103 29 |
| back_curls.07 | 121 | 8 9 19 25 23 46 110 27 |
| side_curls.02 | 115 | 8 8 27 33 31 106 77 20 |
| side_curls.00 | 111 | 8 8 25 34 31 103 58 15 |
| median of all 28 chains | 70 | |

back_curls.03, every frame: 8 8 8 8 9 9 9 9 9 11 12 14 23 28 26 24 23 23 24 25 25 25 24 24 23 23 22 21 25 47 46 12 11
29 62 90 102 97 79 60 42 27 19 19 22 24 23 21.

## Limits

- Still to judge:
  - the eyes and glasses look of the girl;
  - curls crossing the cheek in three-quarter views (also present with OFF).

  Both belong to the open T-026 girl visual issues, not to this task.
- Parameters are a first tuning. Long back curls swing up to about 12 cm on a fast 45° head turn.
- Chains do not collide with each other, and there is no lock-to-lock friction.
