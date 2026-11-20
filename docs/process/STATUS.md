# Status board

Updated by the Supervisor in the same commit as every merge or dispatch. Sources: [TASK_LOG](TASK_LOG.md),
[OWNERSHIP](OWNERSHIP.md), [OWNER_DECISIONS](OWNER_DECISIONS.md) (2026-11-20). As of 2026-11-20 ~07:40Z.
Session cap: 8 until 08:20Z, then 6. ETA "—" = none given yet.

## Character look
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-156 eyes/lashes to T-150 targets | Fable 5.2 | running | — | `t-156-claude-eye-targets` |
| T-160 hair round 6 (boy, auburn girl, third girl; owns the fringe) | Fable 5.2 | running | — | `t-160-claude-hair-r6` |
| T-158 deterministic builds (recorded uv_sphere topology) | Opus 5.5 | running; every published version must still regenerate | — | `t-158-claude-deterministic-build` |
| T-159 ears | — | queued: starts after T-158 merges | — | — |

Codex T-161 reference targets (lashes, ears, hair silhouette) go to T-156 and T-160 as targets.json.

## Release
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-154 guard allowlist + T-137 faces (F1a/F1b/F2, owner-approved ~07:00Z) | — | on `integration/t-137`, gate running | — | `integration/t-137` |
| T-155 candidates boy 2.3.0, girl 0.14.0, third 0.1.0 (current versions unchanged) | Opus 5.5 | published on branch, sheets rendering | — | `t-155-claude-candidates-r2` |

## Interaction
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-157 grasp gap: wider band vs fewer fingers (opt-in) | Opus 5.5 | gate green; batched with T-163 on `integration/t-163` | — | `t-157-claude-grasp-options` |
| Hands round 2 | — | queued: starts after T-157 and T-155 | — | — |

## Other
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-141 native hair curves (opt-in tool once green) | Fable 5.2 | running | — | `t-141` |
| T-144 retire unpinned generator versions, option (b) (owner ~07:35Z) | Opus 5.5 | queued: after T-158 merges and a slot is free | — | `t-144-claude-retire-versions` |
| T-153 fidelity score v2 | Opus | merged; experimental, default stays v1 | — | `t-153-claude-fidelity-v2` |
| T-161 Codex reference targets | Codex | assigned (relay f33c4868); Codex limited until 2026-11-23 ~21:43Z | — | — |
| T-162 this board | Sonnet 5.5 | merged; Supervisor maintains | — | — |
| T-163 starter felt prop library (docs/evaluation/props/T-163/contact_sheet_render.png) | Sonnet 5.5 | on `integration/t-163`, gate running | — | `t-163-claude-props` |

## Waiting for owner
Sheets are paths in text (branch: path).
1. T-155 candidate sheets (reference | current | new | target, eye crops, expressions): pending from T-155. Then the
   owner's one-word OK makes boy 2.3.0 / girl 0.14.0 CURRENT (version_switch + fidelity rebaseline); third 0.1.0 is her
   first published version.
2. T-157 make option (a) the default? Needs `felt_cup` side_a band [0.04, 0.095] (changes existing shots).
   `t-157-claude-grasp-options`: `docs/evaluation/animation/T-157/`. Choices: 1 yes, 2 keep opt-in.
3. T-141b: not approved; owner to discuss.

## Decided today (for reference)
T-137 approved (~07:00Z); T-124 keep the existing final preset (~06:40Z); T-144 option (b) (~07:35Z); fidelity v2 stays
experimental (~06:40Z); T-138 gap not accepted → T-157 (~06:40Z).
