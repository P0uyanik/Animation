# T-219 round file (hair release: V1 flock + H2 volume + cap border)

Branch `t-219-claude-hair-release` (input origin/main `39717ee`; origin/main `8f2237e7` merged in, force-push refused
so no rebase). Supervisor `session_01NPjxeNFfmkruSmnvcb3uSH`. Owner decision: OWNER_DECISIONS.md 2026-11-23 ~06:58 CET.

## State
- PUBLISHED as CANDIDATES (asset_store.py publish, status candidate, pointers unchanged; CURRENT stays 0.14.0 / 0.1.0):
  girl_auburn_bun_glasses **0.15.0** (parent 0.14.0), girl_white_hair_blue_dress **0.2.0** (parent 0.1.0).
  release_manifest.json entries written with release_rule.write_entry (features incl. hair_flock, cap_contour).
  version_switch.py was not usable: its regression gate wants `spec/<id>.<ver>.spec.json` (outside the write-set) and
  the white character has no base spec; white 0.1.0 (R3) was published the same way.
- Specs: `assets/characters/<id>/spec/candidates/T-219/<id>.<ver>.spec.json` = CURRENT published spec + `hair.flock`
  (T-207 V1) + `h2/<id>.json` (H2 values, `hair.cap_contour`), composed by `make_specs.py`. Face untouched (D6).

## H2 values (h2/<id>.json)
- both: `hair.cap_contour` {structure cap, corner_round_m 0.008}.
- auburn: crown height [0.022, 0.036, 0.03] (mid was 0.05), bun el 62 (was 82), curtain rest_radii [0.15, 0.145],
  ringlets_back(_b) rest_radii [0.17, 0.165], ringlets_side/outer hang_radii x 0.176.
- white: buns az +-84 el 60 (was +-56 / 54), back_mass / back_under / back_locks / outer_locks / side_locks radii
  -5..9 %, back/outer lock lift reduced.

## Silhouette vs ORIGINAL turnaround references (hair_silhouette.py; silhouette/*.json, *_overlay.png)
Head zone = rows above the shoulder line (eye line + 0.2 x sole-to-eye), body-scaled (sole-to-eye of the front view),
front / 3/4 / side / back equal weights. Ratios are render / reference.

| | IoU head | area ratio | width ratio | top ratio |
|---|---|---|---|---|
| auburn 0.14.0 (current) | 0.819 | 1.025 | 0.948 | 1.045 |
| auburn 0.15.0 (candidate) | 0.870 | 1.015 | 0.972 | 1.015 |
| white 0.1.0 (current) | 0.805 | 1.102 | 1.096 | 0.983 |
| white 0.2.0 (candidate) | 0.850 | 1.036 | 1.021 | 0.993 |

## Stair-step
Cause: hair.scalp_cap deletes whole head faces under the hairline / face_cut, so the cap border follows the head's
faces. Fix (opt-in `hair.cap_contour`, cap_contour section of groom_r6.py): the head surface is clipped along the zero line of the
same hairline/face_cut field (edges split at the bisected root, faces split, no slivers). Present in released auburn
0.14.0 at the forehead and both ears, and in white 0.1.0 at both ears (her fringe hides the forehead); gone in both
candidates (sheets/*_crops_100.jpg).

## Identity (identity.json)
Without the keys published builds are unchanged (boy 2.3.0, auburn 0.14.0, white 0.1.0 hair hashes before = after).
Pre-existing, not T-219: auburn `garment.vest.embroidery*.fibres` evaluated points differ between every build (also
the stored 0.14.0 master); not hair.

## Sheets
- Preview (8 spp): preview/{auburn,white}_preview.jpg.
- Strict, default final profile `final720_look` (plush_soft, 128 spp), 512 px tiles, 70 mm, character_neutral/1:
  sheets/auburn_strict.jpg, sheets/white_strict.jpg; 100 % crops (768 px head renders): sheets/*_crops_100.jpg.

## Push-out (step 6) — pushout.json, pushout_compare.py
e912 s030 copies (written by make_pushout_shots.py into a scratch folder, not committed: they pin non-current versions on purpose and check_cast cannot resolve the white girl, who has no fidelity_baseline current entry) with the girls cast explicitly (current = version_dir 0.14.0 / 0.1.0; candidate = the
T-219 candidate specs, built by run_shot), boy current 2.3.0; frames 1-80, measured every 2nd frame with T-194
tools/measure_eval.py. ON = run_shot with hair push-out (T-194 defaults, static_move_fade on); OFF = shot_render on the
same bake without --hair-pushout. Pops = frames where push-out adds > 5 mm to the largest hair-vertex jump (T-194 rule).
Depth = deepest hair vertex, all surfaces incl. staging overlaps (boy fringe in the auburn skin, 87 mm, both runs).

| run | character | pops >5 mm | max added mm | max depth ON | frames >1 mm ON | max depth OFF | frames >1 mm OFF |
|---|---|---|---|---|---|---|---|
| current | boy 2.3.0 | 0/40 | 2.5 | 87.0 | 40 | 87.0 | 40 |
| current | auburn 0.14.0 | 28/40 | 178.7 | 49.5 | 40 | 72.3 | 40 |
| current | white 0.1.0 | 25/40 | 80.8 | 23.7 | 40 | 35.0 | 40 |
| candidate | boy 2.3.0 | 1/40 (f41, 45.2) | 45.2 | 87.0 | 40 | 87.0 | 40 |
| candidate | auburn 0.15.0 | 28/40 | 156.1 | 56.2 | 40 | 71.9 | 40 |
| candidate | white 0.2.0 | 23/40 | 95.3 | 26.6 | 40 | 40.3 | 40 |

Reading: push-out and dynamics work on the candidates (same behaviour class as the release). The large push-out pops
exist in the RELEASED versions too (T-218 finding); the candidates do not remove them (auburn max addition 179 -> 156 mm,
white 81 -> 95 mm, counts 28 -> 28 / 25 -> 23). Deepest ON contact: auburn outer ringlet in her own skin 49.5 -> 56.2 mm,
white back mass in her bodice 23.7 -> 26.6 mm. The boy (unchanged) gets one pop at f41 (45 mm) next to the changed
auburn. Flock strands are render-only curves (no colliders, no chains); they are not in these numbers (hair meshes only).
