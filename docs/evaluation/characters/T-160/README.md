# T-160: hair round 6 on the base groom system (`groom/5`), all three characters

Date: 2026-11-20. Input main `af0bc37`; branch `t-160-claude-hair-r6` from `integration/t-137` @ 593dbe1.
Blender: bpy module 5.3.0 (Linux, CPU) through `tools/bpy_blender.py`; Cycles for every sheet and crop, Workbench
only for the iteration previews (not evidence).
Status: **candidates for owner review. Nothing is published, approved or promoted.** No current or candidate
version, character spec, baseline, frozen file, test, threshold or golden changed. `groom/5` is opt-in: only the
three overrides here pin it.

Base: the T-155 candidate specs (boy 2.3.0, girl 0.14.0, third 0.1.0), read from `t-155-claude-candidates-r2`
@ 0677274 because T-155 was not merged when this ran. Each override replaces `generators.groom`, `hair.generator`
and `hair.structures` of its candidate spec; nothing else.

## What groom/5 adds (`pipeline/charsys/groom_r6.py`)
groom/4 (`groom_r5.py`) is used read-only. Two keys, applied to the built mesh before the fibres are grown; vertex
counts, order and faces do not change, so dynamics records, binding and fibre layers stay valid. No character names.

- **`stand`** on `masses` (`{"smooth": n}`). The centre line of every mass is relaxed and its sections are carried
  along it by parallel transport from the root. Reason: a petal that stands far off the scalp took its section frame
  from the scalp normal of every path point and came out ribbed and twisted (seen on the boy's crown).
- **`tips`** on `masses` and `locks` (`{"from", "scale", "power", "flatten", "calm", "round"}`). Over the end of the
  mass or lock the section thins to `scale`, its depth flattens, and the centre line is pulled towards the smoothed
  line (takes the hook out of a waved end). `round` ends a clump in a soft blunt tip.

A hair spec with neither key takes groom/4's path unchanged (`lower` returns the same object, the fibre callback is
passed through). Registry: one line in `versions.py`; one line in `tools/check_all.py` for the new test.
Bun strands and the softer fringe needed no code: they are spec data (felt grooves, clump counts).

## Overrides (`overrides/`, written by `tools/make_overrides.py`)
| character | changes against its T-155 candidate |
|---|---|
| boy | whorl tiers: wider channel gaps (0.22 / 0.3 / 0.28, was 0.12 / 0.2 / 0.15), rounder locks (depth 0.82-0.9), `stand`; crown: 5 broad petals in front of the whorl with tip lifts 60-125 mm in an uneven order (was 6 thin petals), `stand`. Fringe, sides, back row and base untouched |
| auburn girl | inner sweeps wider and lower (tips at el 5), outer sweeps start nearer the parting and end at el -22 (was -14); every ringlet `tips` (thin, flat end) and an opened last coil; bun: 7 broad swirled grooves (was 14 fine), more turns; flower larger (62 mm, was 56) and turned 0.8 (was 0.6) towards the front |
| third girl | fringe: 11 narrower clumps over the same span (was 7), designed uneven ends (±1.5°), shallower grooves, `tips` with a rounded end; temples `tips`; all locks `tips` (from 0.58, scale 0.3, flatten 0.4, calm 0.5), 10 % thinner, more irregular, no wave gain at the tip; buns: 5 broad swirled grooves (was 11); bow: plumper loops and knot |

## Evidence
Per character `<char>/`: `preview.jpg` (cheap first frame, Cycles 2 spp, 120 px), `strict.jpg` (Cycles 16 spp,
360 px), `hair_crops.jpg` (front, 3/4, back at 100 %, 600 px, 16 spp; top row T-155 candidate, bottom row round 6),
`flicker.json`.

| | strict sheet columns | render |
|---|---|---|
| boy | reference, 2.2.0 current, 2.3.0 + hair r6, AI target; compare variant (arms down); `boy_2.2.0_vs_hair_r6.recipe.json` | 421 s + 440 s; crops 815 s |
| auburn girl | reference, 0.13.0 current, 0.14.0 + hair r6, AI target; A-pose masters as T-155; `girl_0.13.0_vs_hair_r6.recipe.json` | 539 s + 483 s; crops 448 s |
| third girl | reference, 0.1.0 T-155 candidate, 0.1.0 + hair r6, Higgsfield target; `tools/third_sheet.py` (she has no current version, as T-155) | 552 s + 509 s; crops 593 s |

The two recipes name the candidate as a built `.blend` under `build/t160/` (not in the repository). To rebuild:
`build_character.py --spec <T-155 candidate spec> --override overrides/<id>.hair_r6.override.json --out <dir>`.
Once T-155 is merged the recipes can name spec + override instead.

What the sheets and crops show against the references:
- **Boy (val27, B04, B05).** Crown: broad petals of clearly different heights, the tallest on his right, instead
  of thin horns; smooth, no ribs. Back: fewer, rounder locks radiating from the whorl with open channels between
  them. Remaining gap: B05's channels are darker and its locks lumpier; val27 shows more small tufts between the
  tall petals.
- **Auburn girl (ref_30, G04, G06).** Sweeps reach the brows, a small bare triangle is left at the parting (G04).
  The flower faces the camera from the front. The bun shows wrapped strands from the back and side. Ringlet ends are
  thinner and stand apart. Remaining gap: ref_30 / G05 curls are longer and looser; the forehead centre is still more
  open than G04.
- **Third girl (01, 02, 07, 17_W04).** Fringe edge is finer and softer. Locks are flatter with thin tapered wisps and
  no hooked ends. Buns read as wound strands. Remaining gap: her hair is clearly less full than 01 / 02 beside the
  cheeks and shoulders, and has no thin curly strands; the fringe tips are still points, not wisps; the halo is the
  material preset's.
- **Bow seat (third girl): not changed.** Two seats further to her right (az -74 and -60) were tried in the geometry
  preview; both hide most of the bow from the front, where 01 and 02 show it. The T-126 seat on the hair below her
  right bun is kept; only the loops and the knot are plumper. Needs a decision if 17_W04's side position is wanted.

## Checks
| check | result |
|---|---|
| `pipeline/charsys/tests/test_hair_r6.py` (new; plain Python and under bpy) | 26/26 |
| `test_hair_r5.py`, `test_versions.py`, `test_guard_allowlist.py` | 79/79, 121/121, 21/21 |
| groom/4 specs through groom/5 (`tools/passthrough_hash.py`, hair only): vertex and face hashes | identical: boy 10/10 objects, third girl 30/30 (`checks/passthrough_*.json`) |
| overrides equal the built candidates (`cmp` against the build's override copy) | identical, all three |
| boy pickup sightline proxy (T-118 `hair_iter.py`; share of each eye not covered, pitch 30 / 40 / 50°) | 0.98 / 0.89, 0.85 / 0.72, 0.59 / 0.53: identical to 2.3.0 (`checks/boy_pickup_sightline.json`) |
| face keep-out violations (build report) | boy 0, auburn girl 0, third girl 58 on the fringe (T-155 candidate: 54; same lowered fringe line from T-137) |
| dynamics chains | boy 26, auburn girl 26, third girl 38 |

## Flicker (turntable, `tools/flicker_turntable.py`)
Each master turns 2° per frame for 8 frames (back view, start yaw 150°) under a fixed camera and the fixed
`character_neutral/1` light; Cycles 16 spp, OIDN, fixed seed, 400 px. Passes and measures are
`tools/motion_checks/render_passes.py` and `flicker.py`, unchanged, with motion vectors. The T-125 limits were set on
the shots' framing (640 × 360, full figure); this is a head close-up, so they are a yardstick and the comparison
between the two columns is the result. Hair region, denoised image:

| character | column | flip share median / max (limit 0.405) | worst tile (limit 0.88) | held noise median / max (limit 0.056) | hair issues |
|---|---|---|---|---|---|
| boy | T-155 candidate | 0.214 / 0.221 | 0.52 | 0.055 / 0.068 | 2 (held noise) |
| boy | hair r6 | 0.204 / 0.206 | 0.51 | 0.047 / 0.049 | 0 |
| auburn girl | T-155 candidate | 0.239 / 0.248 | 0.50 | 0.058 / 0.064 | 1 (held noise) |
| auburn girl | hair r6 | 0.246 / 0.250 | 0.51 | 0.055 / 0.069 | 2 (held noise) |
| third girl | T-155 candidate | 0.058 / 0.062 | 0.48 | 0.028 / 0.029 | 0 |
| third girl | hair r6 | 0.059 / 0.061 | 0.47 | 0.027 / 0.030 | 0 |

Result: round 6 does not add flicker. Flip share and worst tile are within the limits for all three and equal to the
T-155 candidates within 0.02. Held noise: boy lower than his baseline (0.047 against 0.055, issues 2 -> 0); third girl
unchanged and far below the limit; auburn girl at the yardstick in both columns (median 0.058 -> 0.055, max 0.064 ->
0.069: one frame more over the limit). Issues outside the hair region in these close back views (the two skin
issues are in the r6 columns only, one frame each; cause not examined): boy T-155 candidate: cloth flip_share 0.272 (limit 0.161); boy hair r6: cloth flip_share 0.251 (limit 0.161); auburn girl hair r6: skin flip_share 0.244 (limit 0.18); third girl T-155 candidate: cloth held_noise 0.058 (limit 0.021); third girl hair r6: cloth held_noise 0.057 (limit 0.021); third girl hair r6: skin flip_share 0.216 (limit 0.18).

Almost no hair pixel is "held" on a turntable (0.4-1.5 %), so the held-noise value rests on few pixels; the
motion-compensated flip share is the meaningful measure here.

## Not done / limits
- No shot was baked or rendered: the flicker check is a turntable, not a production shot with secondary motion.
- Full gate (`tools/check_all.py`) not run; only the plain tests above.
- Build determinism (T-158) not verified here; hair-only builds were repeatable (pass-through hashes).
- Based on an unmerged T-155 branch; rebase and re-check when T-155 lands.
