# T-122: candidate versions boy 2.2.0 / girl 0.13.0 (round 4)

Input `integration/r4-start @ 5a90975`; branch `t-122-claude-versions`. Blender: bpy 5.3.0 module (pinned wheel,
sha256 checked) behind `tools/bpy_blender.py`.

**Published as CANDIDATES only.** Approved pointers stay boy **2.1.0** / girl **0.12.0** (`tools/check_assets.py`:
PASS, base origin/main). `fidelity_baseline.json` and golden baselines untouched; `--approve-published` not run.

## Specs
- `boy_yellow_hoodie.2.2.0.spec.json` = 2.1.0 + T-109 `boy_face4` + T-113 `boy_t113` (closed_fit, shell_subsurface 0,
  optional Pout). T-115 boy: keep T-109 (its proposal repeats the start), so no change.
- `girl_auburn_bun_glasses.0.13.0.spec.json` = 0.12.0 + T-109 `girl_face4` + T-113 `girl_t113` (closed_fit,
  gaze_range 26/26, shell_subsurface 0) + T-115 `girl/proposal.json` (layered last).
- `--identity-change-approved-by` cites OWNER_DECISIONS 2026-11-19 ~11:40Z (face section changes, as T-094).
- Not included (fold into 2.3.0 / 0.14.0): hair r5 (T-118), garments r3 (T-119), fingers (T-121).

## T-115 girl, verified through the glasses first
[girl_t115_through_glasses.jpg](girl_t115_through_glasses.jpg) (Cycles 12 spp, face_probe.py from T-109, glasses on):
0.12.0 | T-109+T-113 | +T-115. With T-115 the cheeks are fuller and the eyes read rounder and more open, closer to
ref_30; no shelf under the lenses. The upper lid reads a little flatter (upper_curve 0.12 → 0.024) than ref_30's arch:
a watch point, not a reason to drop it. **Kept.**

## Evidence
| | boy | girl |
|---|---|---|
| cheap preview (Cycles 2 spp) | [boy_preview.jpg](boy_sheet/boy_preview.jpg) | [girl_preview.jpg](girl_sheet/girl_preview.jpg) |
| T-087 strict sheet (Cycles 16 spp), current vs candidate | [boy_strict.jpg](boy_sheet/boy_strict.jpg) | [girl_strict.jpg](girl_sheet/girl_strict.jpg) |
| expressions (T-113 tooling, Cycles 12 spp): emotion set + Blink / Smile / Laugh / Squint | [boy_expressions_strict.jpg](boy_expressions_strict.jpg) | [girl_expressions_strict.jpg](girl_expressions_strict.jpg) |
| fidelity (publish-only) | [report](fidelity/boy_yellow_hoodie/report.md) | [report](fidelity/girl_auburn_bun_glasses/report.md) |

## Visual read (fidelity to the references over scores)
- **Girl 0.13.0: closer.** The pale band under the lenses is gone (lower_fit); the cheeks are fuller and rounder, as
  in ref_30. Closed lids read as skin (no white dome). girl_delighted now plays the open D smile (SmileOpen; the current
  master lacks it). Body, hair and garments unchanged.
- **Boy 2.2.0: closer in the face.** The lower face is slightly fuller and rounder (hero24). Blink/Smile/Laugh lids now
  read as skin instead of a pale dome; boy_reluctant plays Pout (missing on 2.1.0). Body unchanged.
- **Scores:** fidelity boy 67.25 (2.1.0: 67.72), girl 64.13 (0.12.0: 65.01): a small drop. The fidelity pass sees the
  silhouette and masks. The visible gains are the lid colour, the lens shelf and the expressions, which it does not
  score.

## Checks (version_switch step 6)
10/12 passed in the run. `tools/check_assets.py` failed only because the clone had no `origin/main` ref; after
fetching it: PASS. `pipeline/charsys/tests/test_store.py` needs `renders/charsys/ref_1.0.0/build_report.json`, a
git-ignored local reference build that this checkout does not have, so it needs a re-run where that build exists. No
test or threshold was changed.
