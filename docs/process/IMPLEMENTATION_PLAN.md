# Implementation plan and queue (Supervisor working plan, 2026-11-18)

Owner-facing priority and phases: `docs/ROADMAP.md` (Priority v5 + architecture addendum). Decisions:
`docs/process/OWNER_DECISIONS.md`. Status per task: `docs/process/TASK_LOG.md`. This file is the Supervisor's ordered
queue with dependencies, so the next tasks can be written and started without re-deriving the plan.

## 0. Rules that shape the plan
- **Priority: reference-quality characters first** (face, hair, skin, materials, garments), for every character, as
  shared spec-driven systems. The owner's references are the target; visual fidelity beats scores.
- **Owner rule (2026-11-17): no new tasks until the running ones finish.** Start nothing below without the owner's
  OK; when the owner lifts the hold, start in the order below as dependencies clear (max ≈ 6 parallel, file claims
  must not overlap, DELIVERY_PLAN rev. 2).
- Path B (visual) tasks: owner approves render sheets before merge; approved versions change only by owner approval.
- Codex (owner's PC, via relay): only tasks the owner assigns to it (currently: finish T-060 only).

## 1. Running now
| Task | What | Merge path | Unblocks |
| --- | --- | --- | --- |
| T-065 | Face v2 (`face_generic/2`) + criterion 0: 3D head geometry (chin, jaw, face shape) | B (owner decides; likely "system only, characters unchanged") | T-059, Boy 2.0 r2, third character |
| T-070 | Hair v3 round 2 (girl fringe/bun/ringlets, boy clumps/tufts, third S-waves) | B | releases `pipeline/charsys/materials/presets.json` → T-066 |
| T-060 | Windows build + Windows CI (Codex) | A | `apps/export-obj` archive (T-069 item 5) |

## 2. Queue (in order; write the task file from the source noted, then claim and start)
| # | Task | Scope (short) | Source for the task file | Starts after | Path |
| --- | --- | --- | --- | --- | --- |
| 1 | **T-066 skin** | `presets/2` skin for all characters: porcelain-peach, warm blush, flocked/felt look, creases warm but not glowing; split `presets.json` by family | T-063 report P2 (`docs/evaluation/review/T-063/README.md`), T-065 notes on skin | T-070 releases `presets.json` | B |
| 2 | **T-067 materials** | fleece (matte, fibre halo, rim sheen), shaggy boots, rib/cable knit, cord, suede, felt | T-063 P3; boy close-ups upload `assets/characters/boy_yellow_hoodie/references/uploads/01_*` | T-066 | B |
| 3 | **T-068 garment details** | sneakers, backpack, hood volume + underarm fix, gathered skirt + hem rib, vest embroidery/decals | T-063 P4 | T-067 | B |
| 4 | **T-059 girl look round** | proportions, mouth/cheeks/eyes on face v2, vest, boots, ears, accessories, colour calibration | TASK_LOG row T-059; T-055 limits; T-063 | T-065, T-066, T-067 approved | B (new girl version) |
| 5 | **Boy 2.0 round 2** | hair v3 + face v2 + materials + sneakers/backpack + hands in pockets on `2.0.0-dev` | T-058 report, T-063 | same as #4 | B (new boy version) |
| 6 | **T-047 collisions** | one collision body per character built by the pipeline and exported; arms/hands/props planned outside the body; smooth (≤ 2°/frame) | TASK_LOG row T-047; T-040/T-040r1 reports | T-061 (merged) | A (+ evidence) |
| 7 | **T-051 fingers** | per-finger curl/spread/thumb opposition, hand-pose library, grasp shapes, **two-hand grasp/carry/place primitive** (T-076 G1) | ROADMAP phase 2; T-076 §2.2 | T-061, T-047 | A/B |
| 8 | **T-053 personality profiles** | profile reader resolving `content/personality/*` once for all layers; per-character `limits` (clamp + gate check via `tools/animcheck`); boy subtle low-energy, girl cheerful/intelligent, third subtly goofy | ROADMAP phase 4; `docs/characters/*/REFERENCE_BEHAVIOUR.md`; T-076 §4 (G3) | T-045 (merged), T-061 (merged) | B (owner approves profile clips) |
| 9 | **Gate wiring** | wire the 14 ungated tests (11 pass; fix or quarantine with owner OK: deform_test MASK crash, test_shot_eyes girl 0.829 mm, test_emotions AC5) and `tools/check_assets.py` into `tools/check_all.py` | `docs/evaluation/review/T-071/` (wiring diff), T-075 report | free slot (touches `check_all.py`) | A |
| 10 | **T-054b lip-sync aligner** | real Rhubarb 1.13.0 aligner, tested on speech | `docs/tasks/T-054b.md` | any time (owner: not for Codex now) | A |

Studies/ideas on hold (owner OK needed): **T-074** CPU render optimisation study (task file exists; must finish before
the benchmark scene), **T-073** PC render benchmark (Codex idea, not assigned).

## 3. After the queue (ROADMAP phases 4–6)
1. **Acting round:** boy slouch + hands in pockets, girl hand-to-chin/pointing, third clasped hands, using T-053, T-051,
   T-047; new verbs **lean-on** and **self-contact** (T-076 G2).
2. **Dialogue + lip sync in the engine:** shot-spec dialogue, viseme track blended with emotion/personality (T-054).
3. **Third character (V6):** only when readiness holds (hair v3, face v2, skin/materials approved; boy and girl have
   no severe gaps); built from spec + assets + profile only. References: `assets/characters/girl_white_hair_blue_dress/`.
   Owner decisions: blue felt bow (no flower), cable-knit dress, fleece boots, closed soft smile, subtly goofy.
4. **Before the benchmark scene:** T-074 render profiles implemented (path B), file-mesh props in `shot_render.py`
   (T-076 G4), light-rig and camera presets as data (G5), unify props on `plush.asset/1` (G6).
5. **V5 benchmark scene** (simple set, no water/paper unless needed) → **V7 classroom kit** → **V8 first episode**
   (sequence assembly, T-076 G9). Water/paper/sparkles (G7/G8) only when a scene needs them.

## 4. Owner approvals still open
Face v2 (after criterion-0 sheets) · T-070 renders · lifting the "no new tasks" hold · T-076 recommendations ·
optional: GitHub rulesets import, close-up reference sheets for the girl and third character, PC backup.

## 5. Follow-ups noted 2026-11-18 (not started; owner decides when)
- **Face follow-up:** third character 3/4 eye-socket rim (lid shells must end at the corners, T-065 report) and the girl's sharp cheek folds below the eye rims (T-066 fix report, `docs/evaluation/characters/T-066/fix/README.md`).
- **Old failing tests (T-077):** deform_test MASK crash, spring-chain joint gaps (engine vs shot_render), AC5 cup out of reach + emotion layers vs T-061 principles; decisions listed in `docs/evaluation/process/T-077/README.md`.
- **Pin bumps:** register `presets/2`, `garment`/`accessories` versions and the boy skin legacy hook when the girl look round (T-059) and Boy 2.0 round 2 pin the new systems.
