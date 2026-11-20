# T-176 · Whole-project review: architecture, workflow, agents, tokens

Analysis only; nothing here is changed without owner approval. **M** = measured (git, CI API, `get_session`,
ledgers). **E** = estimate with its basis. Window: the 183 commits on `main` from 2026-11-19 19:22Z to
2026-11-20 23:36Z (28 h), the last 100 gate runs (2026-11-20 15:09–23:39Z) and session counters read at ~23:40Z.
Data and limits are in the [appendix](#appendix).

## Verdict
1. The gate, the immutable versions and the owner's visual approval are sound and should stay. The engine/Blender
   split (TD-42/TD-44) shows no structural problem in the sampled evidence.
2. The earlier audits worked for coordination: Supervisor plus liaison cost $114 in 24 h ($150 with the old
   liaison's last hours) against about $241 per 24 h before (M/E). The cost has moved to long visual sessions: five of them cost $134 on 2026-11-20 (M).
3. The largest avoidable losses are now structural, not conversational. Ledger commits on `main` trigger and
   invalidate gates; per-feature guard tests turn every release into a permission problem; four hand-edited ledgers
   repeat the same state and drift.
4. The binding limit is the weekly usage window: every session reported `seven_day: allowed_warning` at 23:40Z (M).
5. Expected effect of the proposals below: roughly **$40–90/day (E)** on a day like 2026-11-20, a further $15–35
   per character release, and 2–4 h less waiting on release days, with no check removed.

## 1. Earlier recommendations: adopted, and did they work?
| Recommendation | Adopted | Result |
|---|---|---|
| T-152 #1, T-162 #2: rotate Supervisor and liaison | Yes (R3 23:21Z, liaison 08:30Z) | Worked. R3 ran at $3.6/h against R2's $7.6/h (M). The old liaison stayed in use until 15:27Z at 824k context and cost a further $36 (M). |
| T-162 #1: gate comment only for integration/staging/main; no PR #2 subscription | Yes (T-164) | Worked; part of the R3 saving. |
| T-162 #3, #5: `ready.py` and the shared kit | Yes (T-165) | Partly. No file added to `main` since references the kit, and 4 more per-task sheet scripts arrived (56 now, 40 at T-162) (M). The kit covers shot grids; the day's work was faces and world swatches. |
| T-162 #4: rework over ~250k context in a fresh session | Rule written | Not followed in the fix round: T-159 464k, T-155 436k, T-168 307k after "round 4" in one session (M). |
| T-162 #7, #9: batch gates; Sonnet for mechanical work | Yes | Worked: T-162/163/164/166 merged on Sonnet; T-166 cost $1.11 including a CI change (M). |
| T-162 #8: owner decision queue | Partly | STATUS has "Waiting for owner" (3 items), but 37 decision entries were recorded on 2026-11-20, one at a time (M). |
| T-152 decision rule: $ per accepted task at two merge batches | No | `ready.py` emits `cost $ / ctx`, but TASK_LOG does not store it; only three early rows mention a cost (M). The comparison was never run. |
| T-162 #6: examine the ~82k fixed prefix | No record | Still open. |

## 2. Current problems
### Architecture
- **A1. Guard tests encode a temporary state as a permanent rule.** At least seven test files on `main` check that
  no spec uses feature X (`test_hair_r4/r5`, `test_hair_v3_r2/r3`, `test_hands_r2`, `test_face_r5`, `test_face_v3`);
  the R3 branches add more. Each release that adopts X must relax them. Relaxing a test is correctly refused by the permission
  layer, so it needs the owner's own words. Impact: T-132 waited ~8 h (T-162, M); R3 needed T-154, a 3 kB allowlist
  and three owner statements between 22:00Z and 23:40Z (M). The
  real invariants are already enforced elsewhere: published bytes (frozen manifest, asset-store guard, goldens) and
  an owner decision reference for CURRENT (`version_switch.py`).
- **A2. Two variation mechanisms overlap.** `versions.py` says "new behaviour = a new number" (30 registered pins).
  The R3 rounds instead added opt-in flags inside released modules (`closed_fill`, `lash_curve`, `body.hands`, T-168
  face options). Pin numbers do not match module names (`groom/3` is `groom_r4`, `groom/4` is `groom_r5`, the
  owner's "round 7" lives in `groom_r6.py`). Impact: T-159 and T-168 shared `face_features.py` (1,175 lines) under
  function-level claims, and the release needed "stacked specs" on `integration/r3-faces`.
- **A3. "Current version" is written in many places.** `versions/index.json`, `fidelity_baseline.json`, the golden
  baselines, literals in `test_face_v4.py` and `test_determinism.py`, allowlist `current_decision` fields and e910
  shot files (M). `version_switch.py` updates the first three; the rest are manual release steps.
- **A4. Adding a test touches four central places.** A `Supervisor-Approved` trailer (all tests are guarded), a
  line in `tools/check_all.py` (1,288 lines, 16 commits in the window), `blender_shards.json` and the OWNERSHIP
  row. 48 trailers in 28 h, 30 of them for test files (M).
- **A5. Repository size.** The checkout is 606 MB: 269 MB of review images under `docs/evaluation`, 225 MB of
  published character binaries (9 versions, no LFS; R3 adds three more). The shallow pack alone is 536 MB and every
  session clones it. 328 remote branches (179 task, 123 integration), none removed by rule (M).
- **A6. Tooling outweighs the product.** `tools/` has 19.7k lines of Python against 17.9k lines of C++ in
  `engine/`; `check_all.py` names tests on 86 lines (M). This is not a defect, but every new check is a permanent cost.

### Workflow
- **W1. Ledger commits live on the gated branch.** 70 of 183 commits on `main` are bookkeeping (M). Each starts a
  9–16 min gate run: 31 runs on `main` in 8.5 h, 29 of them for docs-only commits (M). Each also moves `main`, so
  a pending integration branch must merge it and gate again: `integration/r3-faces` merged `main` three times in
  100 minutes (M).
- **W2. A hand-edited ledger row kept the gate red for almost six hours.** From b265c49 (15:41Z) to 6e8e64f
  (21:30Z) the T-155 row in OWNERSHIP had no parseable write-set, which fails the "OWNERSHIP.md parses" check
  (reproduced with `integrate.load_claims`, M). `main` and `staging` had 10 failed runs in that time, all on
  docs-only commits (M).
- **W3. The gate signal is weak.** Of the last 100 runs, 23 were green: 17 docs-only ledger commits, 4 short
  promotion checks and 2 full integration gates. Task
  branches: 33 red, 8 cancelled, 0 green, because guarded paths have no trailer before integration (red "by
  design"). `integration/r3-faces`: 16 runs, 14 cancelled by the next small push, 2 red, 0 green by 23:39Z although
  the release was approved at 23:11Z (M).
- **W4. Four ledgers repeat the same state and drift.** STATUS shows session cap 7 and cap 6 on adjacent lines and
  T-159 as both "accepted" and "running". TASK_LOG holds T-144 and T-166 twice. T-155 is "running" in TASK_LOG and
  "HELD" in STATUS. 23 commit subjects name a decision time later than their own commit, by up to an hour
  (e.g. "~00:40Z" committed at 23:36Z). `WORKFLOW.md` still describes the 2026-11-15 flow (the owner
  pastes prompts; "one agent per chat") (M).
- **W5. "Parallel tasks never share files" was dropped for the fix round.** T-159 and T-168 both worked in
  `face_features.py`, with claims such as "`face_features.py` (build_nose only)". The parser checks globs only, so
  these claims are unenforced, and one broke the parse (W2).

### AI agents
- **G1. The relay cannot deliver approval-class decisions.** 27 of 37 entries on 2026-11-20 were relayed by the
  liaison (M). Both release approvals still had to be typed by the owner in the T-155 session, and the Supervisor
  then verified them in that transcript. This is predictable, but today it is discovered by failing first.
- **G2. The owner dispatches in real time.** 37 decision entries in one day. Each costs a liaison turn at 443k
  context, a Supervisor turn at 339k, a ledger commit and a gate run on `main`.
- **G3. Idle sessions keep large contexts.** T-156, T-159 and T-167 wait "until the bundle merges" at 194–464k.
  Any follow-up there is charged at that size.
- **G4. The Supervisor does mechanical work at 339k context:** 70 ledger commits, 48 trailers and most of the 39 merges in
  the window.
- **G5. Denials are not logged.** The ledgers name three classes (guard relaxation, `create_trigger`/`send_later`,
  sending to the old liaison). The "about six" blocks on 2026-11-20 appear in no file, so the next Supervisor
  cannot avoid them.

### Tokens
- **T1. Long visual sessions are now the largest bucket:** T-155 $33.12, T-156 $34.08, T-159 $31.24, T-167 $22.96
  and T-168 $12.86, $134.26 in total against $113.74 for Supervisor plus liaison (M).
- **T2. No rule sets effort.** T-155, a publish task, ran at effort `max` with fast mode on; T-156 ran at `xhigh`
  (M). Whether that was intended is not recorded.
- **T3. No budget view.** The weekly window reached warning level with no per-task cost on record (see section 1).
- Briefs are not a problem: task files are 1.7–3.4 kB (M).

## 3. Proposals, by priority
Token savings are E, per day at 2026-11-20 activity, and overlap.

| # | Change | Importance | Expected benefit | Effort | Token saving (E) |
|---|---|---|---|---|---|
| 1 | **Approval-class list.** Name the actions that need the owner's own words in the acting session: make a version CURRENT or publish it, relax a test, guard or threshold, add a CI dependency, anything refused once. The liaison prepares the exact sentence and names the session; the owner types it once. Log every denial in one line (G1, G5) | High | Removes stalls like the 8 h wait for T-132 and the 22:00–23:40Z exchange for R3 | Low (one doc section) | $3–8 |
| 2 | **Visual-round budget.** Before sending feedback the Supervisor reads the session's context; over ~250k the round goes to a fresh session. Each visual task keeps a short round file (targets, current overrides, open defects, sheet paths) so a fresh start is cheap. Sheets are read as crops of at most 1024 px. Default effort `high`; `max` or fast mode only at the owner's request (T1, T2, G3) | High | About 40% fewer reads in fix rounds | Low (rule + template) | $20–45 |
| 3 | **Ledger commits stop running and invalidating the gate.** A push to `main`/`staging` that changes only `docs/process/**` and `docs/tasks/**` runs a 1-minute job (links, OWNERSHIP parse, gate-tools test). Promotion accepts an integration commit that differs from `main` only in those paths (W1) | High | ~25 gate runs per 8.5 h avoided; no re-merge and re-gate before a release | Low–medium (`checks.yml`, `ci_status.py`; guarded paths) | $3–6 |
| 4 | **`tools/ledger.py`.** One command each for decision, start, claim and merged. It writes the rows with a tool-generated UTC time, checks the OWNERSHIP parse before committing and regenerates STATUS.md, which is then never hand-edited (W2, W4, G4) | High | No red `main` from a ledger edit; no drift; ~70 ledger commits become ~30 | Medium (one task) | $4–8 |
| 5 | **One release rule in place of per-feature guards.** A spec may use an opt-in feature only if its version is listed, with an owner decision reference, in one release manifest that `version_switch.py` writes. The per-feature "nobody uses X" scans go, and new feature tasks add none (A1) | High | A release needs no test change, so no permission block | Medium; changes tests, owner approval | $10–25 per release |
| 6 | **`version_switch.py` completes the release.** Tests read CURRENT from `index.json` instead of literals; the tool also writes the manifest entry and the eval-shot references (A3) | Medium | One command, one commit, one gate per release | Medium | $5–10 per release |
| 7 | **New tests without a trailer; registration by manifest.** Only changing, renaming or deleting an existing test needs `Supervisor-Approved`. `check_all.py` discovers tests from a per-directory manifest (A4) | Medium | ~30 fewer trailers per 28 h; `check_all.py` is no longer a shared file | Medium; guard policy, owner approval | $2–5 |
| 8 | **Gate hygiene.** A task branch waiting only for a trailer reports neutral, so red means a real failure. Integration branches gate on a `[gate]` marker or manual dispatch (W3) | Medium | A usable CI signal for implementers; 14 of 16 cancelled runs avoided | Low (guarded workflow) | $1–3 |
| 9 | **One owner per file again.** No function-level claims. A fix round inside one module runs in sequence or as one task; claim rows are globs only (W5, A2) | Medium | No stacked-spec bundles; claims are enforceable | Rule | small |
| 10 | **Decision batches, one writer.** The liaison records owner decisions itself (with #4) and sends the Supervisor one batch every 30–60 min, immediately only when running work is blocked (G2) | Medium | 27 relays become ~10 Supervisor wakes | Low | $5–10 |
| 11 | **Record cost per task.** Store the `ready.py` cost line in TASK_LOG and keep a daily total; run the T-152 comparison (T3) | Medium | Makes every other row measurable | Low | enables |
| 12 | **Close a look round with a pin.** When the owner adopts a set of opt-ins, register it as the next generator number with those defaults, and name the module after the pin (A2) | Medium | Specs carry one pin instead of several flags; fewer test paths | Medium–high | none direct |
| 13 | **Repository diet.** Keep only the sheets that READMEs reference in `main`; move raw frames to an evidence branch or release asset; move published binaries to LFS or release assets with the hash manifest in git; archive merged branches monthly (A5) | Low now, rising | Clone 540 MB → under ~100 MB (E); faster session start | Medium–high | none |
| 14 | **Documents.** Rewrite `WORKFLOW.md` to the real flow on one page; split OWNER_DECISIONS (77 kB) and TASK_LOG (55 kB) by month | Low | Correct onboarding for each new session | Low | $1–3 |

## 4. Quick wins and larger changes
- **Quick wins, within a day, no code risk:** 1, 2, 9, 10, 11, 14. Numbers 1 and 2 give most of the benefit.
- **Small tasks, one session each, on guarded files (owner approval):** 3, 4, 8.
- **Larger changes, each needs an owner decision first:** 5 with 6 (release path), 7 (test policy), 12 (version
  naming), 13 (repository storage). Do 5 before the next character release and 13 before the repository passes
  about 1 GB.

## 5. Risks, and what to keep
- **Weaker protection (5, 7).** Mitigation: byte-immutability and the owner decision reference stay; the manifest is
  a guarded file; changing an existing test still needs a trailer.
- **Lost in-session state (2).** Keep the same session while renders or scratch builds are running; the round file
  carries the rest.
- **Delayed decisions (10).** Blocking decisions go at once; batches cover information and queue changes only.
- **A wrong fast path (3).** Decide ledger-only from the path list alone; any other path runs the normal gate.
- **Storage move (13).** The asset-store hash guard and the frozen manifest need the binaries in CI; rehearse on a
  copy and keep `backup.yml` unchanged.
- **Keep:** fresh session per task, the trial-merge gate with all Blender shards and the Windows gate, owner visual
  approval, backgrounded renders, the session cap, Sonnet for mechanical tasks, pointer-based briefs and handovers.

## Appendix
**Session counters (`get_session`, ~23:40Z, M).**

| Session | Model, effort | Age | Cost | Cache reads | Context |
|---|---|---:|---:|---:|---:|
| Supervisor R3 | Opus | 24.3 h | $87.73 | 336.9M | 339k (compacted) |
| Owner liaison (new) | Opus | 15.5 h | $26.01 | 100.5M | 443k |
| Original Supervisor / old liaison | Opus, high | 8 d | $712.92 (+$36.11 since the T-152 export) | 2,248M | 824k |
| T-155 release | Opus, max, fast mode | 16.8 h | $33.12 | 106.7M | 436k (compacted) |
| T-156 eyes | Fable, xhigh | 15.7 h | $34.08 | 61.8M | 297k (compacted) |
| T-159 ears | Fable, high | 11.6 h | $31.24 | 54.4M | 464k |
| T-167 hair r7 | Fable | 12.0 h | $22.96 | 34.1M | 194k (compacted) |
| T-168 boy face | Fable | 9.1 h | $12.86 | 22.5M | 307k |
| T-166 render defaults | Sonnet | 1.4 h | $1.11 | 5.5M | 153k |
| T-174 research | Opus | 0.1 h | $3.16 | 6.7M | 199k |

Sum $288.38. About 17 further sessions from 2026-11-20 were not sampled. All sampled live sessions:
`rateLimitType seven_day`, `allowed_warning`, reset 2026-11-21 00:00Z.

**Gate runs (`checks.yml`, last 100 of 1,165, 15:09–23:39Z, M).** 941 wall-minutes in total.

| Branch class | Green | Red | Cancelled | Median minutes |
|---|---:|---:|---:|---:|
| task (`t-*`) | 0 | 33 | 8 | 11.3 (red) |
| `main` | 19 | 6 | 5 | 12.4 (green) |
| `staging` | 2 | 5 | 0 | 15.0 (red) |
| `integration/*` | 2 | 3 | 14 | 20.2 (green) |

Three runs were still in progress.

**Commits on `main`, 28 h window (M).** 183 commits: 70 bookkeeping, 63 task work, 39 merges, 11 other; 13 merges
of `main` into a branch. Commits touching TASK_LOG 49, OWNERSHIP 47, STATUS 35, OWNER_DECISIONS 35, `check_all.py`
16. `Supervisor-Approved` trailers 48 (tests 30, tools 13, other 5).

**Repository (M).** Checkout 606 MB, 3,481 files: `docs` 318 MB (2,505 files), `assets` 251 MB, `tests` 29 MB.
Code lines: `pipeline/charsys` 32.7k (8.6k tests), `tools` 19.7k, `engine` 17.9k, `tests` 12.2k.

**Limits.** The clone is shallow, so history before 2026-11-19 19:22Z was not read. Supervisor wakes were not
re-counted from transcripts; T-162's $0.20 per wake is reused. Owner time and Codex tokens are outside the
counters. W2 was reproduced locally; the other red runs were not
diagnosed from job logs. Daily savings are gross, overlap between rows and assume 2026-11-20 activity. The engine/Blender split
was reviewed from TD-42/TD-44, the module layout and T-174 only; no engine code was audited.
