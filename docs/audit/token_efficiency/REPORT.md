# T-152 · Token efficiency across the development workflow

**Start with Supervisor handovers.** During the round-2 observation interval, the two Supervisors accounted for **1.278 billion of 2.580 billion cache-read tokens (49.5%, M)** and **$330.25 of $797.95 (41.4%, M)**. Nearly four-fifths of those Supervisor reads came from the round-2 coordinator. A handover that cuts Supervisor reads by one-quarter at the same throughput would save **about $47 per 24 hours in cache reads (E)** at the observed activity level. This is the first change worth testing before changing models or reducing parallel work.

## Where the tokens went

**M** denotes observed usage or arithmetic on observed counters. **E** denotes a scenario with an explicit assumption. The November 19 export covers two Supervisors and 58 children at about 22:50 UTC. Three children (T-113, T-119 and T-138) have no usage block. The sums cover 57 reporters, including unfinished sessions. Owner time and Codex tokens fall outside these counters.

| Session role | Sessions reporting / listed | Lifetime cost | Output | Cache reads | Cost since Nov 18 snapshot | Reads since snapshot |
|---|---:|---:|---:|---:|---:|---:|
| Original Supervisor, owner liaison | 1/1 | $676.81 | 3.710M | 2,156M | $89.57 | 267M |
| Round-2 Supervisor, dispatch/review/merge | 1/1 | $240.68 | 0.678M | 1,011M | $240.68 | 1,011M |
| Task sessions | 55/58 | $467.70 | 4.532M | 1,302M | $467.70 | 1,302M |
| **Total (M)** | **57/60** | **$1,385.19** | **8.920M** | **4,469M** | **$797.95** | **2,580M** |

The original Supervisor started November 12. At about 14:00 UTC November 18 it had already used $587.24 and 1,889M reads (M). Subtracting its earlier counters aligns the interval for all three rows, about 32 h 50 min (E). The earlier export also lists 66 child sessions costing $555.93 (M), a separate historical cohort. Lifetime totals answer a different question from the interval figures. [Earlier snapshot](../data/agent_sessions_2026-11-18.md) · [Derived figures and exact counters](data.csv)

Across the November 19 lifetime counters, each output token corresponds to **501 cache-read tokens (M)**. Fresh input was 0.644M and cache writes were 35.473M (M). Applying the supplied $0.20/M read price to Opus and Fable alone gives **$893 of read traffic (E)**, about 64% of reported lifetime cost. Reusing a cached prefix is cheap per token, but a long conversation incurs that cost repeatedly. The original and round-2 contexts ended at 614k and 317k tokens (M). The reported round-2 afternoon context of about 570k (E) illustrates how much a single endpoint can miss.

| Configured model | Sessions | Lifetime cost | Cache reads | Output |
|---|---:|---:|---:|---:|
| Opus 5.5 | 51 | $1,316.45 | 4,349.3M | 8.359M |
| Fable 5.2 | 7 | $67.62 | 115.7M | 0.538M |
| Sonnet 5.5 | 2 | $1.12 | 4.3M | 0.024M |

All model totals are M. Opus includes both Supervisors. Sonnet handled T-130 workflow evaluation and T-143 cleanup at $0.56 each (M). Scope and complexity differ across models, and the missing T-119 usage limits the visual-task comparison.

**Task phase.** Grouping children once by their primary assignment gives production/implementation **$369.65** (40 sessions), tooling/CI/checks **$65.98** (10), release/versioning **$26.71** (5), and measurement/evaluation **$5.36** (3). Costs and counts are M, using title-based classifications. Release comprises T-088/094/122/131/132, evaluation T-130/135/142, tooling T-085/086/087/101/124/125/127/128/139/143, and production the remainder. These are whole-task costs. The API gives no within-task split for setup, reading, coding, rendering, waiting or reporting.

## Which work can be avoided?

* **Coordination turns have the clearest cost exposure.** At the round-2 endpoint, one extra turn reading the full 317k-token context costs about $0.063 in reads alone (E). The owner → original Supervisor → round-2 Supervisor → implementer route can repeat an instruction and wake an idle session. The relay contains STARTED/READY pairs for T-150 and T-151 with complete evidence pointers. The implementer prompt already calls for milestone-only STATUS, one delivery channel plus fallback, and stopping at READY. Frequency of redundant wakes, polling, oversized file reads and duplicate prose is unmeasured. [Implementer prompt](../../process/IMPLEMENTER_PROMPT.md) · [Supervisor handover](../../process/SUPERVISOR_HANDOVER.md)
* **Machine minutes identify waits, not token waste.** T-119 logged 58 build, 55 render and 27 test minutes (M). Its token counters are missing. T-128's warm ccache rebuild took 1.6 s versus 115 s (M). T-127 kept all 20 full-tier commands and reduced gate wall time from 44 to 28 minutes in one equal-load comparison (M). A silent job can run throughout either interval without a model turn. Savings require removing a check-in, repeated log ingestion or an unnecessary rerun. [Tooling trial](../../evaluation/tooling/T-128/REPORT.md) · [CI evidence](../../evaluation/ci/T-127/README.md) · [Workflow evaluation and ledgers](../../process/WORKFLOW_EVAL_R4.md)
* **Scope and parallelism affect time to acceptance.** T-093 and its completion pass cost $25.52 and $7.80, while the standalone T-131 promotion cost $1.91 (M). These are examples of follow-up and dispatch costs, not proof that either task should have been combined. Up to about six simultaneous implementers (E, owner account) draw on one five-hour and one weekly Claude window. Moving all work to Codex trades against its separate quota, with three reported stops in two days. Preserve independent work and sequence tasks whose input depends on an unresolved owner decision.

## Priorities

Daily E figures use the observed interval's activity and supplied list prices. They describe gross opportunities before handover or retry costs. The rows overlap, particularly when both a turn and its context shrink.

| Priority and action | Estimated benefit and basis | Effort | Risk and safeguard | Adopt |
|---|---|---|---|---|
| 1. Rotate the round-2 Supervisor at a completed merge batch, then try the owner liaison at a decision boundary. Hand over current SHA, claims, active session IDs, pending checks, owner decisions and next action. | **$47–93/day E** if reads across both Supervisors fall 25–50%. Basis: 1,278M reads × 24/32.83 h × $0.20/M. | Medium | Lost decisions or duplicate dispatch. Incoming Supervisor reconciles the packet against OWNERSHIP, TASK_LOG and outstanding CI before taking over. | Now, trial one batch |
| 2. Send a single decision or completion to the acting Supervisor. Batch nonurgent FYIs at the next review. Use job completion for renders/CI and wake an implementer only for actionable feedback. | **$0.63–1.90/day E** for 10–30 avoided full-context round-2 turns/day at the snapshot size. Actual redundant turn count unknown. | Low | Delayed blockers. Route failures, approval requests and ownership conflicts immediately. | Now |
| 3. Keep stable task instructions at the front. Pass changed paths, SHA, section pointers and failing log excerpts. Put evidence in one README and use one READY line with result, exceptions, evidence path and ledger. | **0.5–1.5% of interval cache reads E** if shorter repeated material removes 1–3% of child reads (1,302M). | Low | Omitted context. Keep acceptance criteria, reproducer and full logs accessible by path. | Now |
| 4. Pilot Sonnet for bounded aggregation with a checkable total. Keep uncertain visual or architectural decisions with the current reviewer. Bundle adjacent mechanical work only when claim and acceptance point coincide. | **$0.50/day E** on output alone if 50k Opus output tokens/day move at equal volume ($20 vs $10/M). No measured net benefit from resizing tasks. | Low | Rework or slower reviews can erase savings. Escalate ambiguous results and compare accepted tasks of similar scope. | Later, matched pilot |

**Decision rule.** At the next two comparable merge batches, take usage snapshots at handover and READY. Compare reads and USD per accepted task, recording model mix, rework, gate result and READY-to-merge time from existing evidence. Count handover preparation, restart reads and any old-session wake. Keep the change only if costs fall with comparable scope, first-review acceptance, gate coverage and delivery time. The API dollar estimate cannot predict the percentage of a shared usage window recovered.

**Keep the quality boundary.** Retain the trial-merge gate, guarded/frozen and write-set checks, all Blender shards, renderer-on regressions, Windows coverage and the owner's visual acceptance. TD-42 assigns animation to the engine and final rendering to Blender. T-151 identifies SDF dependencies shared with collision fixtures. Removing coverage across that boundary would risk regressions. In T-129 the fidelity score rose in only four of five measurable owner-approved changes (M), so keep visual evidence and owner review even when a score improves. [Technical decisions](../../../TECHNICAL_DECISIONS.md) · [Gate workflow](../../../.github/workflows/checks.yml) · [Legacy dependencies](../legacy_engine_deps/deps.md) · [Owner-score calibration](../../evaluation/process/T-129/README.md)
