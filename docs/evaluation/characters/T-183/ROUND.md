# T-183 round file: hair contact (hand / ear / follow)

Branch `t-183-claude-hair-contact`, input `7135087`. Owner defects (2026-11-21 ~12:30Z): the girl's hand goes into her
hair and her hair into her hand; hair goes into her ear; hair moves independently of the body.

## Targets (measured on e909 s010, 286 frames, girl; tools in `tools/`)

| Target | Released 0.14.0 | Round 1 candidate | State |
|---|---|---|---|
| Hand vertices inside hair | 28 frames, worst 6.7 mm | 0 frames | met |
| Static hair inside the ear (cap, temples) | every frame, 4.4-7.1 mm | 0 | met |
| Moving ringlets inside the ear | side_b to 10.5 mm (188-216 fr), outer to 9.3 mm (123 fr) | side_b to 7.6 mm (111-169 fr), outer to 5.2 mm (113 fr) | open, reduced |
| Back / outer ringlet tips vs body-anchored pose | 42-47 mm max, 25-26 mm rms | 5-28 mm max, 1.6-5.8 mm rms | met |
| Bun vs head | 35.5 mm max, 15.3 mm rms | 17.8 mm max, 6.8 mm rms | improved |

## Current overrides

- `candidates/girl_auburn_bun_glasses.hair_contact.override.json` on girl 0.14.0 (not a version, not published).
- Shot: `episodes/e909_two_char_acting/shots/s010_t183/shot.scene.json` (s010 with that cast entry only).

## Open defects

1. Moving side ringlets still dip up to 7.6 mm into the ear rim while the head is tilted. A solid ear collider
   (radius 26 mm) removes it (<= 2.6 mm) but adds +-3-4 mm frame-to-frame noise at the lock tip: not adopted.
2. The side lock on the hand side is pushed up to 89 mm off its anchored place when the hand passes the temple
   (frames 24-27): the lock is moved by the hand; check in motion.
3. Locks still rest in the puffy sleeves (upper arm, forearm cloth): forearm and upper-arm colliders are fitted to the
   arm, not the sleeve cloth. A sleeve-sized solid collider throws the side lock 150-200 mm: not adopted.
4. Not in this round (recorded for the owner by the Supervisor): static hair masses vs hand (arm planner), contact
   with props or the other character, the fully clear tucked-behind ear look.

## Sheets and clip

- Clip: `T-183_s010_f060-228_before_after.mp4` (side by side), `T-183_s010_f060-228_girl_zoom_half_speed.mp4`.
- Strict sheet: `T-183_strict_sheet.jpg` (frames 26, 63, 103, 115); tiles in `sheet/before/`, `sheet/after/`.
- Read sheets as crops of at most 1024 px (the tiles are 768 px). Notes per frame: `README.md`.
