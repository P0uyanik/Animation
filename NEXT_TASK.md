# ▶ T-173 — NEW CODEX ASSIGNMENT (owner ~23:45 CET 2026-11-20; posted by the owner liaison session_01NPjxeKamtbdzi3YwrgsWXU for the round-3 Supervisor session_01NPjxeL81bNYoFDm9Ypv5Ck)
Codex does **T-173: LOCAL GPU RENDER BENCHMARK** on the owner's PC (NVIDIA GeForce). Measurement only, token-efficient.
No project code, spec, test or asset changes; never change driver/system settings; no installs beyond Blender itself
if missing (ask the owner first in that case). No GPU rental.

1. Branch `t-173-codex-gpu-bench` from the latest `origin/main` in a new worktree on C: (never write on D:). Write ONLY
   `docs/evaluation/rendering/T-173/**`.
2. Record the machine: GPU model + VRAM, driver version (`nvidia-smi`), CPU, RAM, OS, Blender version used (same major
   as the pipeline's pinned bpy 5.3 if available; note any difference).
3. Benchmark with the repo's own render path where possible (see `docs/evaluation/rendering/T-124/` and the `final720`
   preset from T-166): render the same 3–5 frames of an existing shot (or a character turntable/strict-sheet scene if
   a shot needs the cloud-only setup) with Cycles on (a) CPU, (b) GPU OptiX, (c) GPU CUDA. Same samples/denoiser/
   resolution as `final720`; also one run at the old `legacy128` preset for comparison. Warm-up frame excluded.
4. Report: seconds/frame per device, speed-up vs CPU, peak VRAM, any errors/fallbacks, and whether the GPU output
   matches CPU visually (side-by-side crop + simple per-pixel difference stats; small noise differences expected).
   Estimate the time for an 8 s / 24 fps shot (192 frames) per device.
5. Output: `README.md` (≤1 page, headline numbers first), `bench.csv`, ≤ 3 evidence JPEGs (≤ 2048 px), and the exact
   commands used so the owner can re-run it.
6. Post `| T-173 | STARTED |`; when done push and post
   `<UTC> | T-173 | READY | t-173-codex-gpu-bench@<sha> | input <sha> | <headline>` + ledger.
7. Model: medium effort, token-efficient. If Codex is limited, post a STATUS line and wait.

---
# ▶ T-169 — NEW CODEX ASSIGNMENT (owner ~10:50 CET 2026-11-20; posted by the owner liaison session_01NPjxeKamtbdzi3YwrgsWXU for the round-3 Supervisor session_01NPjxeL81bNYoFDm9Ypv5Ck)
Codex does **T-169: HAIR REFERENCE STUDY**, all three characters. Analysis only, token-efficient. No project code,
spec, test or asset changes. Builds on T-161 (silhouette numbers already in `docs/evaluation/characters/T-161/`;
reuse them, don't re-measure).

Owner direction (~09:50 CET): "do not insist too much on making it look felt-like. The reference hair does not look
that felt-like and is more natural. The decision about hair should be based on the actual reference images. The
main goal is to get closer to the references." Owner's impression: boy hair currently closer than the girls' (unsure);
all three still noticeably different.

1. Branch `t-169-codex-hair-study` from the latest `origin/main` in a new worktree on C: (never write on D:). Write
   ONLY `docs/evaluation/characters/T-169/**`.
2. From the REFERENCES (read-only; same sets as T-161), describe per character what the hair actually looks like:
   - material read: how felt/fuzzy vs smooth/natural; surface sheen/gloss; fibre flyaways (amount, where);
   - strand grouping: lock/clump size, count, shape (petal/leaf vs irregular tufts vs ringlets), tip shape, layering;
   - fringe: outline (regular points vs irregular fall), wisps, length, forehead coverage, parting;
   - volume and fullness per view (front/3/4/side/back), how hair falls on shoulders/back;
   - colour: base, variation, highlight/shadow depth (e.g. boy's dark crown channels);
   - buns/accessories: shape, wrap, size, placement (third girl's blue bow: front, her right side, at the hairline
     below the right bun, slightly tilted — owner confirmed per refs 01/02).
3. Compare with the latest renders: T-160 hair round 6 sheets on branch `t-160-claude-hair-r6`
   (`docs/evaluation/characters/T-160/{boy,girl,third}/strict.jpg` + `hair_crops.jpg`). Note input SHAs.
4. Output: `README.md` (~1–2 pages: per character the top 5 differences ranked by visual impact, each with a concrete
   procedural direction, e.g. "fewer, larger irregular tufts; reduce fuzz shell; add sheen"); `hair_targets.json`
   (per character: qualitative targets + any measurable ones with tolerance); evidence JPEGs (≤ 2048 px,
   reference crop | render crop side by side). These feed hair round 7 (T-167, currently paused).
5. Post `| T-169 | STARTED |`; when done push and post
   `<UTC> | T-169 | READY | t-169-codex-hair-study@<sha> | input <sha> | <headline>` + ledger.
6. Model: medium effort, token-efficient.

---
# ▶ T-161 — NEW CODEX ASSIGNMENT (owner ~07:40Z; posted by the original Supervisor for the round-3 Supervisor session_01NPjxeL81bNYoFDm9Ypv5Ck)
Codex does **T-161: reference target sets for EYELASHES, EARS and HAIR SILHOUETTE**, all three characters, the same
kind of work as T-150 (whose targets.json the face task used directly). Analysis only, token-efficient. No project
code, spec, test or asset changes.

1. Branch `t-161-codex-ref-targets` from the latest `origin/main` in a new worktree on C: (never write on D:). Write
   ONLY `docs/evaluation/characters/T-161/**`.
2. Measure from the REFERENCES (read-only), per character. Report lens and pose caveats as in T-150.
   - References:
     - boy: `assets/characters/boy_yellow_hoodie/references/` (hero24, val27 views, uploads B0x);
     - auburn girl: ref_30, sheet30, G01/G02/G04/G06;
     - third girl: 01, 02, 04, 07, 14, 17_W04.
   - **Lashes**, open and closed eye:
     - upper liner thickness (relative to opening height);
     - number of separate lashes;
     - their positions along the lid, with outer-corner emphasis;
     - lash length and curve;
     - lower lashes yes/no;
     - colour vs liner.
   - **Ears**:
     - size relative to head width and height;
     - vertical position vs the eye line and mouth;
     - protrusion, front and 3/4;
     - outline roundness, inner fold;
     - hair coverage per view.
   - **Hair silhouette**:
     - crown height above the skull;
     - fringe line height and forehead coverage;
     - side sweep height at the temple;
     - outer width at the cheek and shoulder;
     - curl/lock end shape, count and spacing;
     - bun size and position;
     - accessory position.
3. Compare with the CURRENT renders: T-122 sheets (boy 2.2.0, girl 0.13.0) and T-126/T-137 for the third girl. Note
   the input SHA.
4. Output:
   - `targets.json` (per character per measure: target + tolerance);
   - `measures.csv` (reference vs current);
   - evidence JPEGs (≤ 2048 px);
   - a ~1-page README with the largest gaps ranked;
   - a RE-RUNNABLE measurement script plus instructions, so the Supervisor can re-measure new renders without Codex.
   These feed T-156 (lashes/eyes, running now), T-160 (hair round 6, running now) and the coming ears round.
5. Post `| T-161 | STARTED |`; when done push and post
   `<UTC> | T-161 | READY | t-161-codex-ref-targets@<sha> | input <sha> | <headline>` + ledger.
6. Model: medium effort, token-efficient.

---
# ▶ T-152 — NEW CODEX ASSIGNMENT (owner order 2026-11-19 ~23:00Z; posted by the original Supervisor for the round-2 Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **T-152: token-efficiency analysis of the whole development workflow**. Analysis only, focused and
token-efficient. No project code, test, workflow or asset changes.

Owner goal: find where tokens are wasted across the workflow and recommend practical ways to reduce consumption
WITHOUT lowering code quality, testing, reliability or development speed. Deliver a clear report with prioritised
recommendations and estimated benefits.

1. Branch `t-152-codex-token-efficiency` from the latest `origin/main` in a new worktree on C: (never write on D:).
   Write ONLY `docs/audit/token_efficiency/**`.
2. Inputs, read selectively; don't read everything in full:
   - **Usage data:**
     - NEW, `git fetch origin data/token-audit-2026-11-19`, then
       `git show origin/data/token-audit-2026-11-19:docs/audit/data/agent_sessions_2026-11-19.md`: 60 sessions since
       2026-11-18 with cost, output/input/cache-read/cache-write tokens, context size, model, duration;
     - older: `docs/audit/data/agent_sessions_2026-11-18.md`.
     - Totals in the new file: $1,385; 4.47 B cache-read tokens vs 8.9 M output tokens; Opus 5.5 $1,316 (51 sessions),
       Fable 5.2 $68 (7), Sonnet 5.5 $1 (2).
   - **Architecture:** `TECHNICAL_DECISIONS.md` (TD-42), `docs/ROADMAP.md`, `docs/audit/*PROJECT_AUDIT*.md`,
     `docs/audit/legacy_engine_deps/` (T-151).
   - **Roles and process:**
     - `docs/process/IMPLEMENTER_PROMPT.md`, `SUPERVISOR_HANDOVER.md`, `WORKFLOW.md`, `TASK_LOG.md`, `OWNERSHIP.md`,
       `OWNER_DECISIONS.md`, `ROUND2_PLAN.md`; `docs/tasks/T-1*.md` (sample a few);
     - the gate `tools/check_all.py` and `.github/workflows/`;
     - the relay: `RELAY_LOG.md` and `NEXT_TASK.md` on relay-channel.
   - **Reports:**
     - `docs/process/WORKFLOW_EVAL_R4.md` and `docs/evaluation/workflow/T-130/`;
     - `docs/evaluation/tooling/T-128/REPORT.md`; T-127 evidence; `docs/evaluation/process/T-129/`;
     - time-ledger lines in task READMEs.
3. Context (not in the repo):
   - **Roles:**
     - owner: one person, reviews visuals and approves;
     - original Supervisor: a long-lived Claude session that talks to the owner and relays decisions;
     - round-2 Supervisor: a long-lived Claude session, about 570 k tokens of context by afternoon; it writes task
       files, starts implementer sessions, reviews, merges and runs CI;
     - implementers: fresh Claude sessions per task (Opus 5.5 by default, Fable 5.2 for hard visual tasks, Sonnet 5.5
       for data aggregation), up to about 6 at once;
     - Codex (you): evaluations via this relay.
     - Messages flow owner → original Supervisor → round-2 Supervisor → implementers (session messages), and back via
       READY/STATUS lines and session messages.
   - **Limits:**
     - all Claude sessions share one 5-hour usage window (hit at ~15:45–17:10Z; 4% left at ~21:15Z on 11-19) and a
       weekly window;
     - Codex has its own ChatGPT limits (three stops in two days).
   - **Prices** (API list, per M tokens): Opus 5.5 $4 in / $20 out; Fable 5.2 $8 / $40; Sonnet 5.5 $2 / $10. Cache reads
     cost $0.20 on Opus and Fable, so long contexts re-read on every turn dominate.
   - **Known suspects:** check them, don't assume them.
     - long-lived Supervisor contexts re-read each turn;
     - verbose STATUS/READY/README text;
     - check-in/polling turns while renders or CI run;
     - double relays (owner → original Supervisor → round-2 Supervisor → implementer);
     - large file reads and repeated reads;
     - renders and rebuilds inside sessions;
     - many parallel sessions;
     - session setup;
     - tasks too large (rework) or too small (overhead);
     - waking idle sessions with messages.
4. Deliverable:
   - `docs/audit/token_efficiency/REPORT.md` (about 2–3 pages):
     - where the tokens go (by role, session type, model, phase), with numbers from the data;
     - the top wastes, with evidence;
     - a PRIORITISED recommendation table with: estimated saving (% of tokens or $ per day, mark E vs M), effort,
       risk to quality/testing/reliability/speed, and adopt now/later;
     - what NOT to change.
   - Plus `data.csv` with your derived figures.
   - Recommendations must be practical: e.g. Supervisor context resets or handovers, message batching, report
     templates, model routing, session sizing, cache-friendly habits.
5. Post `| T-152 | STARTED |` now. When done, push and post
   `<UTC> | T-152 | READY | t-152-codex-token-efficiency@<sha> | input <sha> | <headline>` + ledger.
   BLOCKED with the question if stuck.
6. Model: medium effort, token-efficient. Keep your own run lean.

---
# ▶ T-150 then T-151 — NEW CODEX ASSIGNMENTS (owner order 2026-11-19 ~20:50Z; posted by the original Supervisor for the round-2 Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Owner: Codex has about 40% of its allowance left, so both tasks are analysis only, short and token-efficient. Do T-150
first. Then do T-151 only if budget remains (post BLOCKED "budget" otherwise). No project code, test, spec or asset
changes. Existing images and tools only; no new renders unless one tiny check is unavoidable (then say exactly what).

## T-150: eye-shape targets for both girls (feeds T-137 F1a/F1b, running now)
1. Branch `t-150-codex-eye-targets` from `origin/main` (at 37901c40 or newer) in a new worktree on C: (never write on D:).
   Write ONLY `docs/evaluation/characters/T-150/**`.
2. From the references, measure per eye:
   - opening roundness (height/width);
   - iris diameter relative to the opening and to the eye spacing;
   - iris position in the opening;
   - visible white above, below and beside the iris;
   - upper-lid arch height;
   - inner/outer corner angles.
   References: auburn girl ref_30 + G01/G02 (the eye seen THROUGH the glasses: report it separately where the lens
   distorts); third girl 01_identity_front, 04, 14 (f14_* crops in views/).
3. Compare with the CURRENT renders:
   - girl 0.13.0: docs/evaluation/characters/T-122/ strict sheet and face crops;
   - third girl: docs/evaluation/characters/T-126/body_face/ (pass 2) and your T-133 evidence.
4. Output:
   - `targets.json`: per character, the target value + tolerance for each measure, from the references;
   - `measures.csv`: reference vs current;
   - one evidence sheet (JPEG ≤ 2048 px);
   - README of about 1 page: the largest gaps, in plain words, ranked.
   These targets must stay valid for future versions.
5. Post `| T-150 | STARTED |` now; when done push and post
   `<UTC> | T-150 | READY | t-150-codex-eye-targets@<sha> | input <sha> | <headline>` + ledger.

## T-151: independent dependency map for A1 (legacy engine removal)
1. Branch `t-151-codex-legacy-deps` from `origin/main`. Write ONLY `docs/audit/legacy_engine_deps/**`.
   Read-only analysis.
2. For the A1 removal candidates, list every reference across engine/, apps/, tests/, tools/, pipeline/,
   .github/workflows, scenes/episodes and docs. Then classify each file or symbol as SAFE TO REMOVE, KEEP (and why)
   or MIXED (which part).
   - Candidates: engine/render/ (path tracer, bsdf, image), the PLUSH_BUILD_RENDERER path, the legacy SDF character
     system (engine/model/character.*, sdf.*, engine/fuzz/), apps/studio, apps/render-cli, apps/export-obj, the
     "linux renderer" CI job and its image regressions, and scenes/tests that use only these.
   - Explicitly identify every SDF piece that COLLISION still needs (scene "sdf" collision shapes, collision.cpp and
     what it pulls in). Those must stay.
3. Output: `deps.md` (about 1–2 pages) + `deps.csv`. This is a second opinion, to be compared with the A1
   implementer's own report before anything is deleted.
4. Post STARTED / READY lines as above (`t-151-codex-legacy-deps`).

Model: as for T-129 (medium, token-efficient).

---
# ▶ T-133 — NEW CODEX ASSIGNMENT (Supervisor 2026-11-19 19:45Z): third-character fit search, then a short review
Owner plan (OWNER_DECISIONS 2026-11-19 ~13:10Z / ~15:20Z): Codex does a fit search on the third character's first
version, then an independent review. Token-efficient; existing tools only.

1. Branch `t-133-codex-third-fit` from the latest `origin/main` (683794f or newer) in a new worktree on C: (never write
   on D:). Write ONLY `docs/evaluation/characters/T-133/**`. No project code, test, spec or asset change; her
   references stay untouched.
2. Her first version = base spec
   `assets/characters/girl_white_hair_blue_dress/spec/candidates/T-126a/girl_white_hair_blue_dress.0.1.0.spec.json`
   + overrides, in this order: `docs/evaluation/characters/T-126/body_face/hands_r2.override.json`,
   `.../T-126/hair/candidates/girl_white_hair_blue_dress.hair.override.json`,
   `.../T-126/dress/girl_white_hair_blue_dress.dress.override.json`,
   `.../T-126/materials/girl_white_hair_blue_dress.T-126d.override.json` (pinned to the old spec path; apply it to the
   T-126a path). Not published (publishing is held for an owner decision); build it locally only.
3. Fit search as in T-115: proportions, face layout and silhouette parameters against her primary target
   `references/uploads/01_identity_front.webp` (+ 02 turnaround, 03 lineup scale). Output a proposed override with
   measured gains, plus a short README: what the first version gets right/wrong vs 01/02/03/04/14/16/17/18, ranked
   next steps. Known gaps: closed eyes lack a dark lash curve (generator gap), faint knit leaves/stitches, small
   collar, squat boots, hair tip shape.
4. Post `| T-133 | STARTED |`; when done push and post
   `<UTC> | T-133 | READY | t-133-codex-third-fit@<sha> | input <sha> | <headline>` + ledger.

---
# ▶ (Supervisor 2026-11-19 19:35Z) T-123 part 2 ACCEPTED and merging — NO CODEX ASSIGNMENT (weekly limit)
Thanks for the round-4 review. Codex is unavailable until ~2026-11-23 21:43Z (weekly limit); no assignment until a new
block appears here after that.

---
# ▶ T-123 PART 2 — NEW CODEX ASSIGNMENT (Supervisor 2026-11-19 17:35Z): end-of-round-4 independent review
Round-4 implementation is complete (T-117 showcase READY). Do the independent review of the round-4 result, like T-116.

1. Branch `t-123-codex-r4-review` from `origin/integration/t-117` (7fb2ffe; reaches main shortly) in a new worktree on
   C: (never write on D:). Write ONLY `docs/audit/round4_review/**`. Evaluation only; no project code, test or asset change.
2. Inputs: boy 2.2.0 / girl 0.13.0 (current after T-131), the round-4 results (T-118 hair r5, T-119 garments r3, T-120
   gaze, T-121 fingers, T-114 e909, T-117 e910 showcase: `docs/evaluation/animation/T-117/`), your own T-116 review and
   T-123 readability tool (use it on e910 for cup and pupil visibility), and the T-129 calibration.
3. Output, short: for each T-116 ranked gap: fixed / improved / still open, with evidence pairs (reference → ours);
   new regressions; a ranked remaining-gap list with procedural next steps; which gaps no task covers yet. Use existing
   renders; a few fresh stills allowed, state exactly what you rendered.
4. Post `| T-123p2 | STARTED |`; when done push and post
   `<UTC> | T-123p2 | READY | t-123-codex-r4-review@<sha> | input <sha> | <headline>` + ledger. Token-efficient.

---
# ▶ (Supervisor 2026-11-19 15:25Z) T-129 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks: clear calibration analysis. Codex stays idle until a new block appears here. Next planned: T-123 part 2,
the independent end-of-round review, after the round-4 tasks merge.

---
# ▶ T-129 — NEW CODEX ASSIGNMENT (owner order 2026-11-19 ~15:00Z; posted by the original Supervisor for the round-2 Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **T-129: fidelity score calibration analysis**. Owner: Codex tokens are limited, so keep it focused and
token-efficient. The result must stay useful across future versions.

1. Branch `t-129-codex-score-calibration` from the latest `origin/main` in a new worktree on C: (never write on D:).
   Write ONLY `docs/evaluation/process/T-129/**`. Do NOT modify project code, tests, thresholds or assets.
2. Question: where does the automatic fidelity score (`tools/fidelity/`, read-only) disagree with the owner's
   visual decisions, and why?
   - Pair every owner verdict in `docs/process/OWNER_DECISIONS.md` (version approvals/rejections, "closer"/"worse"
     notes) with the existing fidelity results for the same versions: `docs/evaluation/characters/*/fidelity/**`
     and the git history of `docs/evaluation/characters/fidelity_baseline.json`.
   - Known case: T-122 boy 2.2.0 / girl 0.13.0 scores dropped (67.72→67.25, 65.01→64.13) although the faces
     visibly improved.
   - Use existing data only. No new renders, unless one tiny check is unavoidable; then say exactly what you rendered.
3. Output, short:
   - `calibration.csv`: one row per decision, with version pair, score delta per component, owner verdict, agree y/n.
   - `README.md`, about 1–2 pages:
     - the agreement rate;
     - which score components track the owner's judgement and which don't;
     - the blind spots (e.g. lid colour, lens shelf, expressions, hair texture, garment detail);
     - concrete, ranked proposals for changing the metric. Proposals only, with no code. Note for each its
       effect on past verdicts, e.g. "with weighting X, N of M past decisions would agree".
4. Post `| T-129 | STARTED |` now. When done, push and post
   `<UTC> | T-129 | READY | t-129-codex-score-calibration@<sha> | input <sha> | <headline>` + the ledger line.
   BLOCKED with the question if stuck. Do not merge.
5. Model: as for T-116. The independent character review (T-123 part 2) comes later, at the end of round 4.

---
# ▶ (Supervisor 2026-11-19 14:15Z) T-123 part 1 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks: readability tool + e907 example accepted (OpenCV cross-check matched 66/66). Codex stays idle until a new
block appears at the top of this file. Part 2 (the end-of-round independent review) comes after the round-4 tasks merge.

---
# ▶ T-123 — NEW CODEX ASSIGNMENT (Supervisor 2026-11-19 11:45Z, owner decision ~11:40Z, round 4)
Task file: `git show origin/integration/r4-start:docs/tasks/T-123.md` (reaches main shortly).

1. Branch `t-123-codex-readability` from the latest `origin/main` in a new worktree on C: (never write on D:).
   Write only `tools/review/readability.py`, `tools/review/tests/test_readability.py`, `docs/evaluation/tools/T-123/**`.
2. Build a per-frame readability check for a rendered shot in the shot camera: visible cup area (largest connected
   patch, px and % of cup) and visible pupil area per character per eye. CSV + short summary; fixture tests; a worked
   example on e907 or e908. Evaluation/tooling only: do not wire it into the gate.
3. Post `| T-123 | STARTED |` when you begin; when done push and post
   `<UTC> | T-123 | READY | t-123-codex-readability@<sha> | input <sha> | <headline>` + the ledger line.
4. Part 2 (end-of-round independent review) comes as a separate block after the round-4 tasks merge.

---
# ▶ (Supervisor 2026-11-19 10:05Z) T-115 and T-116 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks for both. Codex stays idle until a new block appears at the top of this file (standing duty: nightly Windows
result).

---
# ▶ T-116 — NEW CODEX ASSIGNMENT, queued behind T-115 (Supervisor 2026-11-19 09:10Z, owner decision ~09:20Z)
**Do not interrupt T-115.** When T-115 is READY, do **T-116: independent review of the current state** (like T-107,
but on what is on main now: boy 2.1.0 / girl 0.12.0 and every round-3 improvement). Task file:
`git show origin/integration/t-116-prep:docs/tasks/T-116.md` (reaches main shortly).

1. Branch `t-116-codex-current-review` from the latest `origin/main` in a new worktree on C: (never write on D:).
   Write only `docs/audit/current_review/**`. Evaluation only.
2. For each of T-107's 5 gaps: fixed / improved / still open, with evidence pairs (reference → ours); new regressions;
   a ranked remaining-gap list with procedural next steps; say which gaps no task covers yet.
3. Fresh stills of the current masters are allowed; state exactly what you rendered and how.
4. Post `| T-116 | STARTED |` when you begin; when done push and post
   `<UTC> | T-116 | READY | t-116-codex-current-review@<sha> | input <sha> | <headline>` + the ledger line.
5. Model: as for T-107.

---
# ▶ (Supervisor 2026-11-19 09:00Z) T-107 ACCEPTED and merging — NEXT: T-115 (block below)
Thanks for T-107. Now do **T-115** as described in the next block. Current versions are boy 2.1.0 / girl 0.12.0
(on main); T-109 is merged, so its parameter names and tried ranges are in
`docs/evaluation/characters/T-109/fit_parameters.json` on main. Branch `t-115-codex-face-fit` from `origin/main`.

---
# ▶ T-115 — NEW CODEX ASSIGNMENT, queued behind T-107 (Supervisor 2026-11-19 03:05Z, owner-approved round 3)
When Codex is back (~09:00 owner time): **first finish T-107** (block below), then do **T-115: fit search on the
face-round-4 parameters**. Task file: `git show origin/integration/t-094b:docs/tasks/T-115.md` (reaches main shortly).

1. Branch `t-115-codex-face-fit` from `origin/main` in a new worktree on C: (never write on D:). Write only
   `docs/evaluation/characters/T-115/**`. Proposals only: no spec, candidate, code or test changes.
2. `tools/fit` with a larger budget than T-090b on the **current** versions (boy 2.1.0, girl 0.12.0 once T-094 makes
   them current; check `docs/evaluation/characters/fidelity_baseline.json`): lower-face fullness (cheek/jaw), eye
   opening, lid profile; use the parameter names on the `t-109-claude-face-r4` branch if it has added them.
3. Post `| T-115 | STARTED |` when you begin; when done push and post
   `<UTC> | T-115 | READY | t-115-codex-face-fit@<sha> | input <sha> | <headline>` + the ledger line.
4. Model: as for T-090.

---
# ▶ T-107 — NEW CODEX ASSIGNMENT (Supervisor 2026-11-18 23:00Z, owner standing approval for tonight)
Codex does **T-107: independent review of round 2 Phases B and C** (like T-083/T-084). Task file:
`git show origin/integration/t-106:docs/tasks/T-107.md` (reaches main shortly).

1. Branch `t-107-codex-bc-review` from `origin/main` in a new worktree on C: (never write on D:). Write only
   `docs/audit/round2_bc_review/**`. Evaluation only: no code, asset, test or workflow changes.
2. Review the Phase B and C evidence named in the task file against the owner's original references; be independent
   and critical; rank what is still off and give concrete procedural next steps; list the 5 most important gaps.
3. Post `| T-107 | STARTED |` now; when done push and post
   `<UTC> | T-107 | READY | t-107-codex-bc-review@<sha> | input <sha> | <headline>` + the ledger line.
4. Model: as for T-084.

---
# ▶ (Supervisor 2026-11-18 22:58Z) T-106 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks. Codex stays idle until a new block appears at the top of this file (standing duty: nightly Windows result).

---
# ▶ T-106 — NEW CODEX ASSIGNMENT (owner-approved 2026-11-18 ~22:50Z, Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **T-106: reference performance extraction**. Task file:
`git show origin/integration/phase-d:docs/tasks/T-106.md` (reaches main shortly).

1. Branch `t-106-codex-perf-extract` from `origin/main` in a new worktree on C: (never write on D:, never touch the
   owner's personal files). Write only `tools/perf_extract/**` and `docs/evaluation/animation/T-106/**`.
2. Offline MediaPipe analysis (Apache-2.0; install dependencies locally to the tool, e.g. a venv under the worktree)
   of `docs/references/video_paperboat.mp4` and `docs/references/video_watertable.mp4`: per character (boy, girl,
   white-haired girl where visible) expression changes, gaze/glance timing, blink rate, head motion, beat durations.
3. Output: a data table (JSON + CSV) and small evidence contact sheets (JPEG <= 2048 px), as calibration targets for
   T-097B/G (acting) and T-104 (timing). No changes to characters, engine or tests outside the write-set.
4. Post `| T-106 | STARTED |` to `RELAY_LOG.md` now. When done, push and post
   `<UTC> | T-106 | READY | t-106-codex-perf-extract@<sha> | input <sha> | <headline>`, ending with
   `ledger: build N · render N · tests N · ci N · wait N (min)`. BLOCKED with the question if stuck.
5. Model: as for T-090.

---
# ▶ (Supervisor 2026-11-18 22:15Z) T-090b ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks. Codex stays idle until a new block appears at the top of this file (standing duty: nightly Windows result).

---
# ▶ T-090b — NEW CODEX ASSIGNMENT (owner order 2026-11-18 ~20:10Z, Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **T-090b: fit proposals** with the merged T-090 tool. Task file:
`git show origin/integration/t-090b:docs/tasks/T-090b.md` (reaches main shortly).

1. Branch `t-090b-codex-fit-proposals` from `origin/main` in a new worktree on C: (never write on D:, never touch the
   owner's personal files). Write only `docs/evaluation/characters/T-090b/**`. Never edit specs, tools or tests.
2. Run `tools/fit` (Workbench fit renders) and produce **proposals**:
   a. girl face: eye opening, lid profile, cheek profile (input for T-089);
   b. garment outlines: boy inseam / trouser break and shoe volume; girl sleeve reach and shorts (input for T-093).
   Per proposal: override JSON + score table + recipe preview first, then one T-087 strict sheet in Cycles (final only).
3. Post `| T-090b | STARTED |` to `RELAY_LOG.md` now. When done, push and post
   `<UTC> | T-090b | READY | t-090b-codex-fit-proposals@<sha> | input <sha> | <headline>`, ending with
   `ledger: build N · render N · tests N · ci N · wait N (min)`. BLOCKED with the question if stuck.
4. Model: as for T-090.
5. Not for Codex: the time-ledger and preview rules are already done by the Supervisor (docs; `recipe.py preview`
   exists). Standing duty: check the nightly Windows workflow result on main; if it fails, report BLOCKED/STATUS
   with the cause before fixing anything outside an assignment.

---
# ▶ (Supervisor 2026-11-18 19:25Z) T-090 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
T-090 READY at e0ebdad reviewed and merged (integration/t-090). Thanks. Codex stays idle until a new block appears at
the top of this file. Planned next for Codex: independent reviewer at the end of round 2 Phases B and C.

---
# ▶ T-090 FOLLOW-UP (Supervisor 2026-11-18 16:55Z): strict sheets in Cycles, then READY again
T-090 READY at ccb09b8 reviewed: tool and Workbench evidence accepted. Before merge, add the T-087 strict sheets:
1. On `t-090-codex-fit-optimiser`, run `tools/review/recipe.py sheet` for boy and girl with **Cycles at the recipe
   defaults (16 spp, as in docs/evaluation/process/T-087/)**, columns: reference | 2.0.0 / 0.11.0 approved | fit
   candidate (the proposal overrides). Cheap first frame (`recipe.py preview`) first, as the recipe requires.
2. Check the face rows show the head from hair top to chin (T-087 "fit": "head"); in your Workbench sheet the face
   rows stop at the eyes. If recipe.py crops wrongly, say so in the READY line (do not edit tools/review/).
3. Commit the JPEG sheets (≤ 2048 px) to `docs/evaluation/characters/T-090/{boy,girl}/`, push, then post
   `<UTC> | T-090 | READY | t-090-codex-fit-optimiser@<sha> | input 12559bb | strict sheets added`.

---
# ▶ T-090 — NEW CODEX ASSIGNMENT (owner-ordered 2026-11-18 ~16:20Z, round 2 Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **only T-090: reference-fit optimiser** (round 2 Phase B, B2).

1. `git fetch origin` and read the task file: `git show origin/integration/round2-bc:docs/tasks/T-090.md`
   (it reaches main shortly; the round 2 plan is `docs/process/ROUND2_PLAN.md`, review procedure
   `docs/process/REVIEW_RECIPE.md`).
2. Create branch `t-090-codex-fit-optimiser` from `origin/main` (12559bb or newer) in a new worktree on C:
   (e.g. `C:/AnimationWT/t090-codex`). Never write on D:, never touch the owner's personal files.
3. Write only `tools/fit/**` (incl. `tools/fit/tests/**`) and `docs/evaluation/characters/T-090/**`. Never change
   character specs, published versions, frozen files or tests outside `tools/fit/`. Cheap Workbench renders only
   (Blender 5.3 on the PC); evidence JPEG ≤ 2048 px.
4. Use the model you used for T-084 (Astra).
5. Post `<UTC> | T-090 | STARTED | t-090-codex-fit-optimiser | input <sha> | started` to `RELAY_LOG.md` now. When
   done: push the branch, then `<UTC> | T-090 | READY | t-090-codex-fit-optimiser@<sha> | input <sha> | <headline>`
   (BLOCKED with the question if stuck). Only READY/BLOCKED/STATUS lines reach the Supervisor.

---
# ▶ T-084 — NEW CODEX ASSIGNMENT (owner-ordered 2026-11-18, Supervisor): independent PROJECT AUDIT
Everything above T-060/T-054a below is DONE (T-060 merged). Codex now does **only T-084**:

1. `git fetch origin` and read the task file: `git show origin/supervisor/t-084-task:docs/tasks/T-084.md`
   (raw usage data: `git show origin/supervisor/t-084-task:docs/audit/data/agent_sessions_2026-11-18.md`).
2. Create branch `t-084-codex-project-audit` from `origin/main` (0388efb or newer) in a new worktree on C:
   (e.g. `C:/AnimationWT/t084-codex`). Never write on D:, never touch the owner's personal files.
3. Evaluation only: no code, asset, test or workflow changes. Write only `docs/audit/CODEX_PROJECT_AUDIT.md` and
   `docs/audit/codex/**`. Be independent and critical; do not read any `supervisor/audit*` branch.
4. Use the model you used for T-083 (Astra), reasoning high for this task.
5. When done: push the branch, then append to `RELAY_LOG.md` on `relay-channel`:
   `<UTC> | T-084 | READY | t-084-codex-project-audit@<sha> | <one-line headline>`.
   Post a `| T-084 | STARTED |` line first, now.

---
# ▶ T-060 UNBLOCKED — owner approved option B (2026-11-17, Supervisor)
The owner approves installing the C++ Build Tools on this PC **and accepting their licences** for T-060. Do it now,
then continue T-060; T-054a continues in parallel only if it doesn't slow the install/build.

1. **Install on C: only** (C: has space; never install to or write on D:). Use winget, non-interactive:
   - `winget install --id Microsoft.VisualStudio.2022.BuildTools -e --accept-package-agreements --accept-source-agreements --override "--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`
   - `winget install --id Kitware.CMake -e --accept-package-agreements --accept-source-agreements` (skip if `cmake --version` works)
   - `winget install --id Ninja-build.Ninja -e --accept-package-agreements --accept-source-agreements` (if CI uses Ninja)
   - vcpkg: `git clone https://github.com/microsoft/vcpkg C:\vcpkg` and `C:\vcpkg\bootstrap-vcpkg.bat -disableMetrics`;
     set `VCPKG_ROOT=C:\vcpkg` for the build; put the vcpkg binary cache on C: (`VCPKG_DEFAULT_BINARY_CACHE=C:\vcpkg-cache`).
   - Pinned OIDN as `.github/ci-dependencies.json` / `.github/scripts/install_ci_dependencies.ps1` specify, under C:.
   Match versions to the CI Windows job where they are pinned. If an installer asks for elevation (UAC) or a reboot and
   cannot proceed unattended, report BLOCKED with the exact prompt — that is the only thing to ask the owner.
2. **Do not delete, move or modify any of the owner's personal files** (D:\Users etc.). The owner frees space on D:
   personally. Keep all T-060 work (worktree, build dirs, caches) on C:.
3. Then follow `docs/tasks/T-060.md`: reproduce the Windows build, fix portably, local fast tier on Windows, prove the
   GitHub windows job green, report READY via the relay line. Use `gpt-6.2-astra` as before.

---
# ▶ CODEX ASSIGNMENT (Supervisor, owner-ordered 2026-11-17) — replaces the earlier STOP notice
The old local task queue (incl. T-042) stays CANCELLED. Codex works ONLY on the tasks below, under the new workflow
(`docs/process/DELIVERY_PLAN.md` on `main`). Cloud Claude Implementers are running T-044 (hair v3), T-058 (Boy 2.0)
and T-045 (body mechanics, merging); never touch their files (`docs/process/OWNERSHIP.md` lists every claim).

## 1. Model: switch Codex to "Astra" (owner order)
- In Codex, open the model picker (`/model`) or run `codex --help` / check `~/.codex/config.toml`; select the model the
  list shows as **Astra** and set it as the default (`model = "<exact id from the list>"` in `~/.codex/config.toml`).
- Use the exact ID Codex shows; do not guess. If no Astra model is listed for this account, keep the current model,
  continue with the tasks and report "Astra not available: <models listed>" in the relay log.
- Reasoning effort: medium by default; high only for root-cause debugging. Run Codex non-interactively with stdin
  closed (`</dev/null`) and check after 2 minutes that it is producing output/token usage (lesson from T-015).

## 2. Tasks, in order (one at a time)
1. **T-060 — Windows build + CI green** (`docs/tasks/T-060.md`). Ideal for this Windows PC: reproduce the GitHub
   Windows C++ build failure locally, fix it portably, prove it in CI. Branch `t-060-codex-windows-ci` from
   `origin/staging`. Write-set = the T-060 row in `docs/process/OWNERSHIP.md`; if a fix needs C++ source changes
   outside it, push what you have and report the exact files in the relay log first (the Supervisor widens the claim).
2. **T-054a — lip-sync toolchain** (`docs/tasks/T-054a.md`), after T-060 is READY. Branch `t-054a-codex-lipsync-tools`.

## 3. Workflow rules (all tasks)
- Branch from `origin/staging`; push at least hourly; never push to `main`, `staging`, or other tasks' branches; no
  force-push, rebase or history rewrite; never delete branches.
- Before READY: `git merge origin/staging`, then `python tools/check_all.py --base origin/main` (fast tier locally;
  the full tier runs in GitHub CI) — all PASS except guarded paths, which the Supervisor approves.
- Never weaken tests or thresholds; never modify frozen files (`tools/frozen_manifest.txt`); no secrets in the repo.
- Report: push one line `<UTC time> | T-NNN | READY|BLOCKED | <branch>@<commit> | <one-line result>` to `RELAY_LOG.md`
  on `relay-channel` (that wakes the Supervisor). Report BLOCKED instead of waiting; do not ask and wait.
- Keep Codex busy but efficient: when a task is READY, start the next one immediately.

---
# Next task

This file is a pointer (T-071, 2026-11-17). The Supervisor assigns tasks; there is no separate "next task" list here.

- The assigned and queued tasks: [docs/process/TASK_LOG.md](docs/process/TASK_LOG.md) and their prompts in `docs/tasks/`.
- The order of work: [docs/ROADMAP.md](docs/ROADMAP.md) ("Execution order") and
  [docs/process/DELIVERY_PLAN.md](docs/process/DELIVERY_PLAN.md) (§9 batches, §6 planning cadence).
- Who may change which files right now: [docs/process/OWNERSHIP.md](docs/process/OWNERSHIP.md).

The list this file held until 2026-11-15 is archived in
[docs/archive/root_status/NEXT_TASK_2026-11-15.md](docs/archive/root_status/NEXT_TASK_2026-11-15.md).
