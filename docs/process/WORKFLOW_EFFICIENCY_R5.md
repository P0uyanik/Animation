# T-162 · Workflow efficiency, round 5 (builds on T-152)

M = measured (session API, transcripts, CI API, ledgers); E = estimate with the stated basis. Prices as given
(Opus $4/$20, Fable $8/$40, Sonnet $2/$10 per M; cache reads $0.20/M). Per-session figures: [data.csv](T-162/data.csv).
Sampled transcripts (newest 1–4 pages each, usage de-duplicated per API call; the full T-143 sample matches its
lifetime reads exactly): T-137, T-134 (Fable); T-136, T-138, T-131, T-117 (Opus); T-143 (Sonnet); Supervisors R2, R3.

## Summary
1. Cost per API call is roughly the context size times $0.20/M. Each call carries about 82k tokens of fixed harness prefix (M). Long Supervisor and liaison contexts (350–760k) make every wake cost $0.07–0.15 per call.
2. The biggest avoidable cost is wakes that need no action. In the R2 sample, 15 of 23 wakes were edits to the PR #2 gate comment, and about 8 of those needed nothing (M). R3 is not subscribed and runs at $2.1/h against R2's $7.6/h (M).
3. READY handling causes repeated round trips: duplicate sends (2–3 copies), READY sent before the push, READY lost during the rotation, and stale queued messages. Each costs 1–3 extra turns on both sides.
4. Visual tasks keep rebuilding the same evidence tooling: 40 per-task sheet scripts are on main (M). Rework rounds run at 400k+ context: the T-134 review round alone cost $4.25 (M).
5. The checks are sound and should stay. The savings are in routing, context size and a small shared kit: roughly **$60–140/day (E)** at Nov-19 activity, with no change to the gate or to the owner's approvals.

## Where tokens and time go
| Step | Tokens / $ | Time | Evidence |
|---|---|---|---|
| Fixed prefix (system prompt, tool schemas, skills) | ~82k per call: 63.8k cache read + 17.7k written on T-143's first call (M). About 40% of the median implementer call (~200k) (E) | – | T-143 |
| Orientation and reading | Small. Briefs are already pointer-based (1.5k-char prompt plus a ~2.4k task file). T-143's first 5 calls cost 0.41M reads, about $0.08 (M). Sessions do not read the 50k-token "read first" list | 1–2 min | T-143, T-131 |
| Context growth (images, logs, sheets) | T-137 went from 94k to 368k. One page carried 4 tool results over 15k chars (744k chars in all). Fable at 450k costs $0.09 per call against ~$0.02 at 100k (M) | – | T-137, T-134 |
| Build | Few tokens when run in the background. Repeats: six sequential builds for T-137's hash re-check (deliberate), T-136 re-ran ctest because its log kept only the tail (M) | 290 min over 12 ledgers, ~24 min/task (M) | ledgers |
| Render | Waiting is free when backgrounded: T-137 waited 85 min with zero turns (M). Two renders at once starved each other (T-137) | 991 min over 12 ledgers, 600 of them T-124 (M) | ledgers, T-137 |
| CI / checks | Integration gate green median 18.6 min, p90 20.4 (M). Task branches: 117 runs and 1,167 runner-minutes in 18 h, mostly red by design (M). Implementers polled CI with send_later: 2–3 check-ins each (T-136, T-138) | 19 min per merge cycle | gh runs |
| Messaging / coordination | A Supervisor wake costs ~2.7 calls and ~0.99M reads, about **$0.20** (M, R2). The owner liaison at 757k costs ~$0.15 per call: +$20.71 overnight (M). Supervisors held 41% of interval cost (T-152, M) | minutes per hop | R2, R3, original |
| Report writing | READY/CHECKPOINT messages run 0.9–3.6k chars, plus a 1.2–2.8k-char closing chat summary that repeats them (M). Output is ~13% of lifetime $ (8.9M × $20, E) | – | all implementers |
| Waiting on limits | 5-hour stops in 3 of 8 sampled implementers: T-117 41 min, T-134 and T-143 ~9 min each (M), plus one 85 min all-session stop (T-130) | ≤ 85 min | T-117, T-134, T-143 |

## Repeated work that can be standardised
- **Evidence sheets for shots.** 40 per-task `make_sheet*/strip/contact` scripts are on main (159 kB, M). T-137 wrote inline PIL scripts, edited them with sed and re-ran them. Characters already have `tools/review/recipe.py`, which does preview then strict sheet. Shots have no equivalent: they need before/after frame grids, crops and labels.
- **Logged test and build runs.** A wrapper that writes the full log to a file and prints a one-line summary (pass/fail counts, exit code) would have avoided T-136's ctest re-run. It would also stop sessions from hand-writing `tail` and `grep` pipelines for every run.
- **Waiting on CI.** One background `gh run watch` gives one notification, replacing repeated send_later check-ins.
- **READY preflight.** Three Supervisor send-backs were mechanical: T-162 and T-163 sent READY before pushing, and T-163 had a new test not registered in the gate (R3 sample, M). T-131 was BLOCKED at dispatch because its claim was missing (M); R3 now checks claims before dispatch.
- **"Before" renders.** Several tasks render the same e910 before-frames on the same main SHA (T-134, T-137, T-117). Reuse is possible only with an exact key, and after T-158. See "Not to change".

## Redundant overhead and coordination problems
- **Gate comment wakes.** `checks.yml` "Update the one PR #2 comment" runs `if: always()` on every branch, task branches included. A Supervisor subscribed to PR #2 is woken by each edit. In the R2 sample, R2 replied "Nothing to do" to old runs, superseded staging runs and expected red task-branch runs (M). R2 was still being woken ~20 min after its handover (M).
- **Owner relay path.** Owner → liaison (757k context) → Supervisor adds a full-price hop per decision. Sending to the liaison fails without a trusted device, so copies to it are wasted and the morning summary could not be delivered (M). The permission classifier also denied create_trigger and send_later to R3, so no hourly self-check ran.
- **Duplicate and stale messages.** T-136 and T-138 each sent READY to 3 recipients; T-137 sent F1a to 2 (M). Each delivered copy wakes a recipient at 350k+. Messages queued before a READY arrived after it and cost 1–3 turns (T-117, T-134, T-138), and crossed messages added more (T-158, T-163). T-138's READY was lost during the rotation, and the handover message was read 37 min late.
- **Bottlenecks.** The first is owner decisions: T-132 and the third-character candidate waited ~8 h on the guard-test question, from ~22:45Z to the ~06:40Z decision (M). The others are the shared 5-hour window and the 19-minute gate per merge (when merges are not batched). Render CPU is the fourth: run one heavy job at a time.

## Ranked improvements
| # | Change | Expected saving | Effort | Risk to quality / reliability | When · who |
|---|---|---|---|---|---|
| 1 | Post the PR #2 gate comment only for `integration/*`, `staging` and `main`. Standing rule: the Supervisor does not subscribe to PR #2 and waits on its own runs with one background `gh run watch` | **$15–45/day E** (8–15 no-action wakes/h × $0.20 over ~10 busy h). R3 already shows the effect: $2.1/h vs $7.6/h, M at lower load | Low (one `if:`, guarded-path approval) | Low: main, staging and integration still report, and implementers still see their own runs | Now · Opus small task |
| 2 | Rotate the owner liaison as T-152 #1 proposed (second half), using the R3 handover format. The owner sends decisions straight to the acting Supervisor where possible | **$25–45/day E** (liaison ~$45–65/day; reads −75% at ~150k context) | Medium | Lost context: reconcile against OWNER_DECISIONS, STATUS and the handover | Now · owner + new Opus session |
| 3 | `tools/ready.py` preflight: branch pushed at the SHA, `integrate.py claims --check`, write-set, new tests registered, doc links. It then sends one READY line (≤ 300 chars, evidence path, ledger, `cost $ / ctx k` from the session's own get_session) to `@parent` only, once | **$8–20/day E** (2–4 avoided wakes per task × $0.20, ~20–25 tasks/day), plus 10–40 min per affected task | Low–medium | Low: adds checks; the Supervisor review is unchanged. Also gives the per-task cost T-130 and T-152 lacked | Now · Opus |
| 4 | Rework rule: if the implementer's context is over ~250k and the feedback is narrow, run the round in a fresh session with a pointer brief (task file, review points, branch@sha, README) or after a compaction. One consolidated feedback message per round | **$5–15/day E** (~$2–3 per round; T-134's round cost $4.25 at 430k, M) | Low (Supervisor rule) | Medium–low: keep the same session when the fix depends on in-session state (running renders, scratch builds) | Now · Supervisor |
| 5 | Shared kit: `tools/review/shot_sheet.py` (JSON-driven before/after grid and crops, ≤ 2048 px), `tools/run_logged.py`, `tools/wait_gate.py`, and a one-render-at-a-time queue. The task template names them | **$5–12/day E**, plus 10–20 min per visual task | Medium (one task with tests) | Low: tooling only, outside the gate | Now · Opus |
| 6 | Find out what makes up the ~82k fixed prefix in implementer sessions and disable connectors or plugins the pipeline never uses | **$10–20/day E** if 15–25k comes out (~4,800 implementer calls/day, E) | Low (settings) | Low; check first that no needed tool goes | Later, after checking · owner |
| 7 | Batch 2–3 READY tasks with disjoint write-sets into one integration gate (as R3 did with T-157 + T-163) | $1–3/day E; 20–40 min per batch | Low | A red batch needs splitting; keep write-sets disjoint | Now · Supervisor |
| 8 | Decision queue in STATUS.md (options, default, which tasks it blocks), answered by the owner in one batch. Tasks that depend on an open decision are not dispatched | Hours of blocked time (8 h, M); $2–5/day E | Low | None | Now · Supervisor + owner |
| 9 | Sonnet for mechanical work: version switches like T-131, cleanups, status boards, GREEN watching | $1–4/day E (T-143 cost $0.56, M) | Low | Rework if misrouted; keep reviews on Opus | Now, matched pilot · Supervisor |
| 10 | Shared "before" renders per main SHA, keyed by SHA, Blender version, profile, frames and seed, with hash-verified reuse | 10–60 machine-min per visual task E; few tokens | Medium | **Real**: the girl 0.13.0 build is not repeatable (found in T-137, fix in T-158), and the owner declined character-build caching (item 6). Re-render whenever the key is in doubt | Later, only after T-158 and only with owner approval |

Measure as T-152 proposed: at the next two merge batches, compare $ and reads per accepted task, rework rounds, first-review acceptance and READY-to-merge time. The READY line from item 3 supplies the per-task cost.

## What not to change
- Fresh session per task. The prefix cost is fixed, and long-lived implementers cost more per call.
- Trial-merge integration gate, all five Blender shards, character regressions, guarded/frozen and write-set checks, the Windows gate, and probes.
- Owner visual approval. Recipe preview before the strict sheet. One judgeable outcome per checkpoint. Opt-in engine changes until D1.
- Backgrounded renders and builds without polling (T-137's 85-min wait cost no turns).
- The cap of 6 parallel sessions, and "do not wait for Codex".
- Essential tests, even where they are slow (`garment_generic_test` 15.6 min).
- No caching of character builds or renders without the owner's explicit approval. Item 6 was declined; item 10 is presented with its risks and is not assumed.
