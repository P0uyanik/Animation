# T-183: hair contact (hand in hair, hair in ear, hair follows the body)

Owner 2026-11-21 ~12:30Z. Round 1, opt-in. Round file: `ROUND.md`. Blender: bpy 5.3.0 module (`tools/bpy_blender.py`).

## Cause per defect (released boy 2.3.0 + girl 0.14.0, e909 s010, the T-172 shot)

| Defect | Measured | Cause |
|---|---|---|
| Hand in hair | 28 of 286 frames, worst 6.7 mm (hand.R in `ringlets_side_r00`, f63; hand.L in `ringlets_side_00`, f107-121) | The spring-chain solver only had head, torso and shoulder colliders; it tested joints only (6-7 cm apart); a joint was never pushed farther than its kinematic target, so a hand that moves into the hair's rest place was ignored. |
| Hair in ear | static: temples 6.1-7.1 mm, cap 4.4-5.8 mm, every frame; moving: `ringlets_side_b` to 10.5 mm | No keep-out for the ear in the groom build; no ear collider. |
| Hair moves independently | chain tips 42-105 mm (rms ~26 mm) off the body-anchored pose | Gravity used the head's tilt for every joint, also joints anchored to the chest (head tilt to 33 deg, chest <= 9 deg: 25-45 mm drift); damping ratio 0.41-0.50 (~1 s ringing); soft bun (35 mm lag). |

## What was built (all opt-in; absent keys = previous path)

- Engine `engine/anim/secondary.{h,cpp}`: chain key `"contact": {"solid", "segments", "anchored_gravity"}`;
  inelastic pushes and no side flip for contact chains. Format: `docs/SECONDARY_MOTION.md`.
- Groom `pipeline/charsys/groom_contact.py` (called from `groom_r6.py`, groom/5): `hair.ear_keepout`,
  `hair.dynamics.contact` (colliders fitted from the rig's meshes at bind time).
- Release rule: feature `hair_contact` (`pipeline/charsys/release_rule.py`), one sample in `test_release_rule.py`.
- Candidate: `candidates/girl_auburn_bun_glasses.hair_contact.override.json`: ear keep-out (margin 3 mm); hands and
  forearms solid, upper arms and ears resting contact; locks damping 7 -> 14; bun stiffness 140/120 -> 400/320,
  damping 9 -> 34, limit 12 -> 6 deg. Shot: `episodes/e909_two_char_acting/shots/s010_t183/`.

Fitted colliders (girl): hand 28.7-28.8 mm, forearm 22.8 mm, upper arm 28.1 mm, ear 20.3 mm radius.
Ear keep-out moved 229-331 vertices per mesh by at most 12.7 mm; 0 hair vertices inside the ear at rest afterwards.

## Result (same shot, same frames 1-286, `tools/measure_contact.py`, `tools/follow.py`)

| Measure | Released | Candidate |
|---|---|---|
| Hand vertices inside hair | 28 frames, worst 6.7 mm | 0 frames |
| Cap / temples inside the ear | 286 frames, 4.4-7.1 mm | 0 frames |
| `ringlets_side_b` inside the ear (L / R) | to 10.2 / 10.5 mm, 216 / 188 frames | to 7.6 / 5.1 mm, 169 / 111 frames |
| `ringlets_outer_00` inside ear.L | to 9.3 mm, 123 frames | to 5.2 mm, 113 frames |
| Back ringlet tips off the anchored pose (max / rms) | 42-47 / 25-26 mm | 5-24 / 1.6-3.6 mm |
| Outer ringlet tips | 44-47 / 26 mm | 10-28 / 4.1-5.8 mm |
| `ringlets_side_00` | 51 / 29 mm | 15 / 7.4 mm |
| `ringlets_side_r00` (the hand passes it) | 68 / 29 mm | 89 / 19 mm |
| `ringlets_side_b` | 105 / 28 mm | 96 / 9.4 mm |
| Bun | 35.5 / 15.3 mm | 17.8 / 6.8 mm |

The measure counts vertices behind the nearest face; a thin rope bounds the depth at its radius (~12 mm).

## Clip and sheet (for the owner)

Same shot as T-172 (`e909 s010`, frames 60-228, 640x360, 16 spp, profile `final720`, 24 fps). Before = the T-172 clip
(released boy 2.3.0 + girl 0.14.0, `docs/evaluation/video/T-172/`); after = the same command on `s010_t183`
(`--run-dir t183_after`; girl 0.14.0 spec + the candidate override, boy unchanged). The boy's half of the picture is
the same in both clips (PSNR 44-47 dB, codec noise only), so only the girl's hair differs. The after clip's bake equals
frames 60-228 of the measured candidate bake.

| File | What |
|---|---|
| `T-183_s010_f060-228_before_after.mp4` | before / after side by side, 1280x360, H.264, frame number burnt in |
| `T-183_s010_f060-228_girl_zoom_half_speed.mp4` | the girl only, 2x zoom, half speed, before / after |
| `T-183_s010_f060-228_after_hevc10.mp4` | the after clip as rendered (HEVC 10-bit) |
| `T-183_strict_sheet.jpg` | strict sheet: girl's head, before / after, frames 26, 63, 103, 115 |
| `sheet/before/`, `sheet/after/` | the sheet's tiles at full size (768 px crops of a 2560 px frame, 24 spp); spec `sheet/strict_sheet.json` |

What the sheet shows (read from the 768 px tiles, 3/4 view from the girl's right):

- f26, f63 (ear, hand): before, two ringlets cross in front of the ear; after, the ear is clear and the ringlets sit
  behind it. The hand is clear of the hair in both views at these frames (the measured 6.7 mm overlap at f63 is on the
  far side of the lock).
- f103, f115 (follow, ear): before, the side ringlets swing forward across the ear and hang away from the head while
  she leans; after, they stay behind the ear and close to the head and shoulder.
- Still visible after: the front lock rests on the puffy sleeve and curls onto it (open defect 3 in `ROUND.md`); the
  ringlets behind the ear lie stacked close together at f63. The far (left) side of the head is not in this view; it
  is covered by the measurement only.
