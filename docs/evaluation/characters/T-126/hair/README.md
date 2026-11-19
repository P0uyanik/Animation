# T-126b: long hair for `girl_white_hair_blue_dress` on groom/4 (candidate)

Date: 2026-11-19. Input `integration/docs-r4` @ 6596eaf; branch `t-126b-claude-hair`. Blender: bpy module 5.3.0
(Linux, CPU) through `tools/bpy_blender.py`. Environment setup: **none needed** ("Animation" environment as provided).
Status: **candidate, first version.** Nothing is published, approved, promoted or current. No character spec, version,
baseline, frozen file, threshold or existing test changed. Her references were only read.

Body used: T-126a's base spec `assets/characters/girl_white_hair_blue_dress/spec/candidates/T-126a/girl_white_hair_blue_dress.0.1.0.spec.json`
on `t-126a-claude-body-face` @ 0e7aaad (read-only), built with T-126a's `hands_r2.override.json` plus the hair override
here. The first geometry previews used the T-070 `third.base.spec` draft as a fixture head (`media/`).

## Deliverable
`candidates/girl_white_hair_blue_dress.hair.override.json` (written by `tools/make_candidate.py`): only
`generators.groom` = `groom/4` and `spec.hair`. Structures (refs 07, 08, 17_W04, 18_W02, 01):

| part | how |
|---|---|
| two round top buns, wrapped strands | `bun` with two buns (az ±56, el 54), opposite wrap, 1.3 turns, swirled felt grooves |
| scalp coverage | `scalp_cap` + `felt_volume` crown gathered to the top |
| fringe clumps | `masses`, 7 clumps to the brow line, the outer two longer; 2 temple masses |
| fused back that splits into locks | `curtain` back mass under two layers of wavy locks (8 over 7) |
| long cream S-wave locks, tapered staggered ends | `locks` style `wavy` with `stagger` (`z_end`, `end_scale`) and the new `phase_deg` |
| wavy side locks | 2 + 2 mirrored locks in front of the ears, 2 + 2 outer locks |
| blue felt bow (18_W02) | `felt_bow`: two rounded loops, knot, two shorter narrower tails; on her right, below the bun on the fringe roots, with the new `"seat": "hair"` and the shared `turn` rule |
| secondary motion (08) | chains for buns (3 bones), every lock, fringe and temples: 34 chains |

The base spec's hair keeps its dynamics names for other structures in a dict merge, so the override reuses the names
`buns`, `fringe`, `temples`, `side_locks`, `back_locks`, `outer_locks` (and adds `back_under`). Hair colours come from
the base spec (cream felt hair, blue `hair_bow`); T-126d owns the material preset.

## groom/4 additions (`pipeline/charsys/groom_r5.py`, generic, spec data only)
Both are gaps listed in `docs/evaluation/characters/T-118/third_character_readiness.md`. A hair spec that uses neither
takes exactly the earlier code path (`lower` returns it unchanged; the fibre callback is passed through).
- **Wave phase**: `locks.stagger.phase_deg` (list, repeats over the locks; style `wavy` only). The S-wave phase is set
  by design instead of a random draw, so neighbours wave roughly together; the mirrored side adds 180° so both sides
  mirror. The lock is built straight by groom/3 and groom/4 lays the wave on the built lock (`wave.amplitude`,
  `wave.wavelength`, new optional `wave.depth`, `wave.ramp_m`, `wave.start_m`, `wave.tip_gain`). Vertex counts, order
  and heights do not change, so dynamics chains and binding stay valid; fibres are grown after the wave.
- **Accessory seat on the hair surface**: `"seat": "hair"` on a `felt_bow` or a flower item. A ray along the seat's
  outward direction finds the outermost built hair surface (accessories excluded) and `out` is measured from there.
  On her the bow moved out 54 mm from its scalp seat (`checks/candidate_build_hair_report.json`).

## Evidence
| | file |
|---|---|
| geometry preview on the fixture head (Workbench, hair only; not her head) | [media/fixture_geometry_preview.jpg](media/fixture_geometry_preview.jpg) |
| cheap first frame (Cycles 2 spp, 120 px; 83 s) | [preview/preview.jpg](preview/preview.jpg) |
| strict sheet: reference, candidate, Higgsfield target (T-087 layout and render side, Cycles 16 spp, 360 px; 617 s) | [sheet/strict.jpg](sheet/strict.jpg) |
| hair views at 100% (front, bow side, side, back, bow; 600 px, never scaled; 1001 s) | [sheet/hair_crops.jpg](sheet/hair_crops.jpg) |

`tools/review/recipe.py` needs a published baseline version, which she does not have, so `tools/sheet.py` (like
T-126a's driver) calls the unchanged shared pieces `tools/review/blender_render.py` and `strict_sheet.make_sheet`
with the candidate column only. Views are the A-pose master.

What the sheet shows against her references:
- **Back (17_W04, s02_back).** Two buns on top, a fused felted back that splits into separate locks, S-waves that run
  roughly together across the row, staggered tapered ends at mid-back. Remaining gap: 17 shows about three wave
  crests with a softer, hairier surface and strand lines in the upper back; here the upper back is smooth and the
  lock ends are thinner and more pointed than the wispy tips of 17.
- **Front, 3/4 (01, s02_front).** Fringe clumps to the brow line, wavy side locks down to the chest, the bow on her
  right below the bun. Remaining gap: the reference hair is wider and fluffier beside the cheeks and shoulders, with
  thin curly strands; the fringe here is more regular.
- **Buns (07, 17).** Round and in the reference position; the wrap grooves are visible but soft under the fibre
  layer. 17 shows clearly separate wrapped strands.
- **Bow (18_W02, canonical).** Two loops, knot and two tails in dusty blue, seated on the hair. Remaining gap: the
  loops are flatter and more pointed than the plump rounded loops of 18, and the knot is small.
- **Halo.** The fibre halo is much weaker than in 17; that is the material preset's fibre layers (T-126d).

## Checks
| check | result |
|---|---|
| `python3 pipeline/charsys/tests/test_hair_r5.py` | 78/78 PASS (58 earlier checks unchanged + 20 new: wave phase, seat, no character name in `groom_r5.py`, her override) |
| `test_hair_r4.py`, `test_versions.py`, `test_hair_v3_r3.py` | 37/37, 119/119, 25/25 PASS |
| candidate build | 120,200 hair vertices, 90 fibre objects, 34 chains, 0 face keep-out violations |
| T-118 hash check, boy (2.1.0 and 2.2.0), `checks/boy_*` | groom/3 and groom/4 builds **identical** (same SHA-256) |
| T-118 hash check, girl (0.12.0 and 0.13.0), `checks/girl_*` | SHA-256 **differs**; see below |

**Girl hash check.** The T-118 script (`docs/evaluation/characters/T-118/tools/hash_check.py`, unchanged, run with the
`determinism.py` environment) reports different hashes for her groom/3 and groom/4 builds, and the values change from
run to run. `tools/hash_detail.py` compares per object, and also builds groom/3 a second time
(`checks/girl_auburn_bun_glasses_0.13.0_hash_detail.json`): all 17 hair objects have identical vertex coordinates
(largest difference 0.0 m) in all three builds; only the face lists of the two flower objects differ, and they differ
in the same way between groom/3 and groom/3 again. So the difference is an unstable face order in the flower builder
that exists without groom/4, not a geometry change from this task. The same check on the untouched input commit
(6596eaf) also gave different hashes (that run was without the deterministic environment and during a render). Her spec uses no groom/4 feature, so her build takes the unchanged path. The
T-118 README recorded equal hashes; that could not be reproduced here. The script's field
`released_files_unchanged_vs_5a90975` is false because the integration branch moved those files after T-118; this
branch changes only `groom_r5.py` and `test_hair_r5.py` among code files.

## Limitations / open points
- First version: the visual gaps listed above are open (lock tips, upper-back strand lines, side volume, bow loop
  shape, halo).
- The bow sits on the scalp side of the rule, so it is rigid with the head; scalp accessories still have no chain
  (readiness note, not in this task's scope).
- The designed wave moves the built lock sideways as a function of height, so a lock's section is sheared a little
  at the steepest part of the wave instead of following the curve.
- Lock sizes are scaled from the fixture head to her head by one factor (`fit` in `tools/make_candidate.py`); if
  T-126a changes the head again the factor needs a re-run of the script.
- Not run: export, head-turn and motion check of the chains, fidelity score, full Blender test files of earlier rounds.
- The test "no file under assets/characters pins groom/4" still passes because the override lives under `docs/`;
  publishing her combined spec will need that rule looked at by the Supervisor.
