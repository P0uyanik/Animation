# T-118: hair round 5 (`groom/4`): whorl tiers with channels, staggered ends

Date: 2026-11-19. Input `integration/r4-start` @ 5a90975; branch `t-118-claude-hair-r5`. Blender: bpy module 5.3.0
(Linux, CPU) through `tools/bpy_blender.py`; Workbench (Mesa llvmpipe) for the geometry strips, Cycles for the recipe
previews and the strict sheets.
Status: **candidate for owner review (path B).** Nothing is published, approved or promoted. No character spec,
current version, `fidelity_baseline.json`, frozen file or existing groom module changed. `groom/4` is opt-in: only the
two candidate overrides here pin it.

## What groom/4 adds (`pipeline/charsys/groom_r5.py`)
groom/3 (`groom_r4.py`) is used read-only as a library. Each new feature is lowered to plain groom/3 data before the
build, so a hair spec that uses none of them builds exactly as through groom/3. All of it is spec data; no character
names.

- **Ring rows** (`masses` rows with `"ring"`). The roots sit on a circle round the row's whorl pole and the masses run
  straight away from it. No random numbers are used.
  - `stagger`: lists of factors for length, lift and width (and degrees added to the ring radius) that repeat over the
    masses, so heights and lengths differ by design.
  - `channel {"gap"}`: limits each mass to `(1 - gap)` of its share of the circle and narrows its root, so an open
    channel runs down from the whorl between every two masses. The build reports the smallest gap.
- **Staggered lock ends** (`locks` with `"stagger"`). Offsets added to `z_end` per lock, and end-scale factors. Each
  lock becomes its own structure (`<name>_00`, `<name>_r00` on the mirrored side) with the dynamics settings of the
  original name.
- **Turned flowers** (flower items with `"turn"`). The flower rotates about its seat on the bun towards a head
  direction.

Registry: one line in `pipeline/charsys/versions.py` (`groom/4` → `groom_r5`). `build_character.py` needed no change:
it loads the pinned groom module through the registry.

## Candidates (`candidates/`, written by `tools/make_candidates.py`)
On the current specs (boy 2.1.0, girl 0.12.0). Only `generators.groom`, `hair.generator` and `hair.structures` change.

**Boy** (B05, B04, val27 back):
- Whorl pole moved to the upper back (az 180, el 62; was el 78).
- Three ring tiers round it replace the 9 broad `top` masses: 6 at the whorl, 8 over them, 9 over the sides and back.
  Each tier has a channel gap (smallest open gap 8–15 mm) and three to five different lengths.
- 6 crown petals stand in front of the whorl with tip lifts from 60 to 130 mm (was 6 at 70 mm and 3 at 85 mm).
- Fringe: the two clumps over the eyes end at el 5 (was −3) and lie closer to the forehead; the centre point keeps
  the brow line; the temple clumps hang a little lower and further out.
- Nape row, side masses and felt base are unchanged. 33 masses → 44.

**Girl** (G04, ref_30, G05, G06):
- Inner sweeps are wider (150 mm) and bow down over the forehead; outer sweeps start nearer the parting and end at
  el −14 by the temples (was −6).
- Back, outer and side ringlets end at designed, different heights (spread 100 mm at the back; neighbours differ by
  at least 20 mm) and taper to 0.36 of their width (was 0.55).
- The flower sits at bearing 38 on the bun (was 55), slightly larger, turned 17° towards the front quarter.

## Evidence
| | boy | girl |
|---|---|---|
| cheap first frame (Cycles 2 spp, 120 px) | [boy_preview](boy_preview/boy_first_frame_preview.jpg) | [girl_preview](girl_preview/girl_first_frame_preview.jpg) |
| strict sheet (T-087 recipe, Cycles 16 spp): reference, current, candidate, AI target | [boy_sheet](boy_sheet/boy_2.1.0_vs_hair_r5_strict.jpg) | [girl_sheet](girl_sheet/girl_0.12.0_vs_hair_r5_strict.jpg) |
| hair geometry, current over candidate (Workbench, no fibres) | [boy](media/boy_geometry_current_vs_candidate.jpg) | [girl](media/girl_geometry_current_vs_candidate.jpg) |

## Strict sheets (one each; render 467 s + 451 s boy, 531 s + 504 s girl)
- **Boy.** Back: locks radiate from the whorl in tiers with dark channels between them, and the crown shows petals of
  different heights, as B05 and val27 back. Front and face rows: the crown is taller and uneven; the eyes are clearer
  under the fringe. Remaining gap: B05's locks are thicker and lumpier, and its tallest petal stands higher still.
- **Girl.** Front and 3/4: the sweeps come further down over the forehead, so the bare arc above the brows is
  smaller, and the flower shows at the front quarter of the bun. Side: the flower faces forward. Back: the curl ends
  sit at different heights with thinner tips. Remaining gap: the forehead centre is still more open than G04, and the
  curls are shorter and tighter than G05. The face rows are framed below the hairline, so they show little of the
  sweeps.

## Pickup sightline (boy)
The e907 pickup camera was **not** re-baked here: that needs the engine build and a shot run. The check is a proxy.
The view comes from 25° to the boy's left, at an elevation equal to the head pitch seen from a level camera. For each
pitch, ray casts measure the share of the camera-facing eye surface with no hair in front
([boy_pickup_sightline.json](checks/boy_pickup_sightline.json); the last three tiles of the boy geometry strip show
the same views).

| head pitch | current, left / right eye | candidate, left / right eye |
|---|---|---|
| 30° | 0.86 / 0.65 | 0.98 / 0.89 |
| 40° | 0.68 / 0.48 | 0.85 / 0.72 |
| 50° | 0.49 / 0.33 | 0.59 / 0.53 |

The sightline is more open at every pitch. At 50° about half of each eye is still covered, so a strongly pitched
head will still hide part of the glance.

## Checks
| check | result |
|---|---|
| `python3 pipeline/charsys/tests/test_hair_r5.py` (new, plain) | 56/56 PASS |
| `test_hair_r4.py`, `test_versions.py`, `test_hair_v3_r3.py` (plain) | 37/37, 107/107, 25/25 PASS |
| default build, hash check (`tools/hash_check.py`, [boy](checks/boy_default_hash.json), [girl](checks/girl_default_hash.json)) | the current hair built by groom/3 and by groom/4 has the same SHA-256 (boy 52,296 vertices, girl 167,510); the released groom files and `build_character.py` are unchanged against 5a90975 |
| face keep-out on the candidate builds | boy 0, girl 0 violations |
| candidate build reports | boy 58,060 hair vertices, 27 chains; girl 162,202 vertices, 26 chains |

Note on the hash check: faces are hashed as sorted vertex indices. The winding that Blender's `recalc_face_normals`
picks for felt shells differs between two builds in one session, for groom/3 alone as well; vertex coordinates are
equal.

## Limitations / open points
- The pickup check is a geometric proxy, not the e907 frame.
- Not run: Blender test files of earlier rounds, export of the candidate masters, head-turn check, fidelity score.
- Boy: the crown petals are smooth cones; B05's are lumpier. The fringe over the eyes is shorter than in B01.
- Girl: each staggered ringlet is its own object (21 single-lock objects instead of 4), so the candidate has 93
  fibre objects. Chain names of staggered locks change (`ringlets_back_03.00`).
- Girl: the face keep-out (el 5 inside az ±34) still limits how far the sweeps come down over the centre forehead.
