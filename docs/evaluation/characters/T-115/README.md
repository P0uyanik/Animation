# T-115 face fit

READY for review on `t-115-codex-face-fit` at input `35479ed35669406c490571c8544deab1d4a4549f`. The fidelity baseline and the approved pointers in both version indexes agree on boy **2.1.0** and girl **0.12.0**. Trial 0 is the published spec with the corresponding T-109 face override applied. The proposed layer goes last, after that override. [Baseline](../fidelity_baseline.json) · [Boy index](../../../../assets/characters/boy_yellow_hoodie/versions/index.json) · [Girl index](../../../../assets/characters/girl_auburn_bun_glasses/versions/index.json) · [T-109 parameters and candidates](../T-109/fit_parameters.json)

| T-109 start → proposed trial | Front | Three-quarter | Side | Mean / 100 |
|---|---:|---:|---:|---:|
| Boy, trial 0 | 73.11 → 73.11 | 74.14 → 74.14 | 60.24 → 60.24 | 69.16 → 69.16 |
| Girl, trial 2 | 74.28 → 75.34 | 74.65 → 74.92 | 66.24 → 66.39 | 71.72 → 72.22 |

| Character | Override | Visual evidence | Scores and reproduction data |
|---|---|---|---|
| Boy | [Proposal](boy/proposal.json) | [Face overlays and eye detail](boy/overlay.jpg) | [Start and proposal by view and landmark](boy/scores.csv) · [All trials](boy/trials.csv) · [Search bounds](boy/bounds.json) |
| Girl | [Proposal](girl/proposal.json) | [Face overlays and eye detail](girl/overlay.jpg) | [Start and proposal by view and landmark](girl/scores.csv) · [All trials](girl/trials.csv) · [Search bounds](girl/bounds.json) |

## Reading the results

**Boy 2.1.0. Keep the T-109 face.** The mean of 69.163 was the highest of seven trials. The runner-up, trial 2, gained 1.43 points at three-quarter but lost 1.70 at the front and 0.01 in profile, finishing at 69.071. The front eye IoU fell from 0.381 to 0.331. The proposal repeats the starting values for the searched paths. That build passed all 12 face checks, including full blink closure, an 8.8% maximum three-quarter rim and a 16.54 mm lower-face displacement at the 95th percentile relative to the published master.

**Girl 0.12.0. Propose trial 2.** The largest gain was at the front (+1.06 points), where eye IoU rose from 0.434 to 0.464. The three-quarter and profile scores also improved. Profile eye IoU dipped slightly (0.31153 to 0.31132). The cheek pad grew from 14.00 to 19.26 mm and the jaw rounding from 10.00 to 12.27 mm. The upper and lower lid edges moved from 47.00° and −50.00° to 45.48° and −51.49°. The lower-lid fit gap fell from 0.00500 to 0.00259. All 14 face checks passed. Maximum lower-lid shell exposure fell from 4.8% to 0.0%, the maximum three-quarter rim was 8.0%, and lower-face displacement reached 26.35 mm at the 95th percentile relative to the published master.

Each sheet uses the same reference crop for both overlaid trials. The rightmost column magnifies changes to the visible eye pixels after registration. The boy sheet compares the retained start with the closest alternative, while the girl sheet compares the start with the proposal. The score CSVs always compare the start with the selected proposal. Transparent glasses lenses are omitted from the fit pass.

## Search and verification

Blender 5.3.0 produced three 320 × 640 Workbench passes per trial. The T-090b face objective averages figure-mask IoU, eye-mask IoU and landmark agreement per view. Each annotated landmark earns `max(0, 1 − distance / reference head height)`. Front, three-quarter and side have equal weight. Cheek and jaw fullness influence the contour indirectly. The reference sets supply no direct cheek-depth target. [Fit objective](../../../../tools/fit/README.md) · [T-090b](../T-090b/README.md)

Each search used seed 4. The initial ceiling was 10 builds per character. Measured build times led to an early stop after seven boy trials and nine girl trials, each including its start, compared with three in T-090 and T-090b. Each completed sequence matches a stock run at the stated budget. Odd-numbered trials sample the full bounds. Even-numbered trials sample a shrinking interval around the highest mean so far. Both fits varied cheek-pad amount and radius, cheekbone fullness, jaw amount and lateral placement, upper and lower lid edges, and both lid curves. The boy also varied both lid rolls. The girl varied her lower-lid fit gap. All varied paths use their complete T-109 tried intervals. Eyeball scale and outline stayed at the T-109 start, as did the boy's jaw-down value of zero to avoid the documented three-quarter crease.

Selection uses the highest three-view mean that also passes the T-109 geometry checks, with earlier trials winning ties. In descending score order, the build reports screen the three-quarter rim (maximum 10%) and the girl's exposed lower lid (maximum 5%). For surviving finalists, the per-character build, glance and shape checks from `test_face_v4.py` run on the already-built master. Empty eligibility cells in the trial tables identify lower-ranked trials that needed no further testing. All saved passes were re-scored, every sampled override was replayed and its composed SHA-256 compared with the build report. [Face checks](../../../../pipeline/charsys/tests/test_face_v4.py)

Run each command from the repository root with a fresh output directory, NumPy and Pillow. Both use the T-090b face landmarks. The reference index selects the boy's arms-down compare pose and the girl's A-pose master.

```sh
python tools/fit/run.py --spec assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.1.0.spec.json --override assets/characters/boy_yellow_hoodie/spec/candidates/T-109/boy_face4.override.json --bounds docs/evaluation/characters/T-115/boy/bounds.json --views val27_front,val27_threequarter_right,val27_side_right --landmarks eye_L,eye_R,eye_inner_L,eye_inner_R,eye_outer_L,eye_outer_R,nose,mouth,chin --seed 4 --budget 7 --height 640 --blender D:/Animation/tools/blender-5.3/blender.exe --out build/t115-replay-boy
```

```sh
python tools/fit/run.py --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.12.0.spec.json --override assets/characters/girl_auburn_bun_glasses/spec/candidates/T-109/girl_face4.override.json --bounds docs/evaluation/characters/T-115/girl/bounds.json --views sheet30_front,sheet30_front_left,sheet30_left --landmarks eye_L,eye_R,eye_inner_L,eye_inner_R,eye_outer_L,eye_outer_R,nose,mouth,chin --seed 4 --budget 9 --height 640 --blender D:/Animation/tools/blender-5.3/blender.exe --out build/t115-replay-girl
```

## Wall time and budget

| Character | Search wall, min | Build, min | Fit render and score, min | Extra Cycles attempt, min | Checks and replay, min | Builds / fit frames |
|---|---:|---:|---:|---:|---:|---:|
| Boy | 44.13 | 41.19 | 2.94 | 3.50 | 1.89 | 7 / 21 |
| Girl | 42.08 | 39.46 | 2.61 | 5.52 | 2.00 | 9 / 27 |

Elapsed time from search launch through overlay verification was 50.44 minutes for the boy and 50.53 minutes for the girl. The two searches ran concurrently. Per-character times are elapsed worker minutes. The ledger counts overlapping wall intervals once and divides them equally among active categories, following T-090b. Render includes registration, scoring and the optional Cycles attempts. Both Cycles jobs were stopped before their first frame to bound render time. The delivered overlays use the scored Workbench passes. Fit builds and renders completed for every reported trial. There was no quota or CI wait.

The report is uncommitted. Posting it on the relay branch requires a commit, so the READY line below is the local handoff.

2026-11-19T09:48:56Z | T-115 | READY | t-115-codex-face-fit@35479ed | input 35479ed | Girl improves in all three views (+0.49 mean). Boy retains T-109 (69.16).

ledger: build 40.33 · render 7.30 · tests 2.00 · ci 0 · wait 0 (min)
