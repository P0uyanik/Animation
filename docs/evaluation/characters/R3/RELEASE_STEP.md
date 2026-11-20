# R3 faces: items for the release step (listed, NOT applied)

Branch `integration/r3-faces`. The stacked candidate specs live in `docs/evaluation/characters/R3/specs/`
(`stack_specs.py`; layers in each spec's `metadata.layers`). Nothing below is applied on this branch.

## 1. Reference update: `pipeline/charsys/tests/test_face_v4.py`
15/17 since the 2.3.0 / 0.14.0 switch. The only failures are the two pins "T-109 candidate is on the current version":
`CANDIDATES` still names `boy_yellow_hoodie.2.2.0.spec.json` / `versions/2.2.0` and
`girl_auburn_bun_glasses.0.13.0.spec.json` / `versions/0.13.0`. Update: 2.3.0 and 0.14.0 (four paths, same edit as
eaa72e8 at the previous switch; every check and limit kept). At the R3 release the pins follow the new current
versions again. Note: the T-109 values are already inside 2.2.0 / 2.3.0 (boy: all 17 leaves) and 0.13.0 / 0.14.0
(girl: 11 equal, 5 retuned later), so its Blender "fuller lower face >= 3 mm against the published master" check
compares a version with itself; it is plain-only in the gate (check_all.py).

## 2. Guards for the specs under `assets/` (owner decision needed: needs a guard-test change)
Owner direction (Supervisor ~21:55Z): satisfy the guards through `pipeline/charsys/tests/owner_approved_candidates.json`
entries with owner-decision references, no guard change. Blocker: that file is read only by `test_hair_r5`
(groom/4), `test_hands_r2` (body.hands) and the lash_curve check of `test_face_r5`, and `test_guard_allowlist.py`
accepts only `FEATURES = ("groom/4", "body.hands", "lash_curve")` (other features fail as "unknown feature").
The R3 specs trip three other guards that do not read the allowlist:

| guard | check | R3 specs it flags |
|---|---|---|
| `test_face_t168.py:57` | no spec under assets/ uses the new options (T-168 face r4) | boy |
| `test_hair_r6.py:73` | no file under assets/characters pins groom/5 | boy (r6), girl (r7), third (r7) |
| `test_face_r5.py:82` | no spec opts into lid yaw, closed_fit.sink_m, shell_occlusion_tint or socket.closed_fill (T-156) | girl, third |

Allowlist entries alone cannot pass these. The T-154 pattern would: add the features to `FEATURES` and call
`GA.split` in those three checks. That is a change to guard tests, so it needs the owner's choice.
Entries then needed (exact character + RELEASE version, each with its owner decision; current versions need a
`current_decision`):
- boy: T-168 face r4; groom/5 (hair r6); plus the existing groom/4 / body.hands entries carried to the new version if
  the spec still carries them.
- girl auburn: groom/5 (hair r7); T-156 lid options (closed_fill, sink_m, shell_occlusion_tint, upper_yaw_deg);
  lash_curve (T-156 sets closed_fit.lash_curve); existing groom/4 / body.hands carried over as applicable.
- third: groom/5 (hair r7); T-156 lid options; lash_curve; body.hands as applicable.

## 3. Shape keys (T-156)
`body_skin` gains `Blink`, `Blink.L/R`, the winks and their `@75` in-betweens on both girls. See `chain_deltas` and
the export check in `README.md` for what the engine package receives.
