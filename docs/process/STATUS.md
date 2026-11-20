# Status board

Updated by the Supervisor in the same commit as every merge or dispatch. Sources: [TASK_LOG](TASK_LOG.md),
[OWNERSHIP](OWNERSHIP.md), [OWNER_DECISIONS](OWNER_DECISIONS.md) (2026-11-20). As of 2026-11-20 ~08:20Z.
Session cap: 6 (temporary 8 ended 08:20Z). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU (from ~08:30Z). ETA "—" = none given yet.

## Character look
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-156 eyes/lashes to T-150 targets | Fable 5.2 | running | — | `t-156-claude-eye-targets` |
| T-160 hair round 6 (boy, auburn girl, third girl; owns the fringe) | Fable 5.2 | running | — | `t-160-claude-hair-r6` |
| T-158 deterministic builds (recorded uv_sphere topology) | Opus 5.5 | on `integration/t-158`, gate running | — | `t-158-claude-deterministic-build` |
| T-159 ears | — | queued: starts after T-158 merges | — | — |

Codex T-161 reference targets (lashes, ears, hair silhouette) go to T-156 and T-160 as targets.json.

## Release
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-154 guard allowlist + T-137 faces (F1a/F1b/F2, owner-approved ~07:00Z) | — | on `integration/t-137`, gate running | — | `integration/t-137` |
| T-155 boy 2.3.0 / girl 0.14.0 → CURRENT, third 0.1.0 first version (owner ~08:20Z) | Opus 5.5 | version switch + rebaseline | — | `t-155-claude-candidates-r2` |

## Interaction
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-157 grasp gap: wider band vs fewer fingers (opt-in) | Opus 5.5 | on `integration/t-157`, gate running | — | `t-157-claude-grasp-options` |
| Hands round 2 (then revisit T-157 option a default) | — | queued: starts once T-155 is published | — | — |

## Other
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-141 native hair curves (opt-in tool; docs/evaluation/characters/T-141/README.md) | Fable 5.2 | on `integration/t-141`, gate running | — | `t-141` |
| T-144 retire unpinned generator versions, option (b) (owner ~07:35Z) | Opus 5.5 | queued: after T-158 merges and a slot is free | — | `t-144-claude-retire-versions` |
| T-153 fidelity score v2 | Opus | merged; experimental, default stays v1 | — | `t-153-claude-fidelity-v2` |
| T-161 Codex reference targets | Codex | assigned (relay f33c4868); Codex limited until 2026-11-23 ~21:43Z | — | — |
| T-162 this board | Sonnet 5.5 | merged; Supervisor maintains | — | — |
| T-164 gate PR #2 comment only for integration/staging/main | Sonnet 5.5 | running | — | `t-164-claude-gate-comment` |
| T-165 shared task kit + tools/ready.py | Opus 5.5 | running | — | `t-165-claude-task-kit` |
| T-163 starter felt prop library | Sonnet 5.5 | running | — | `t-163-claude-props` |

## Waiting for owner
1. T-141b: not approved; owner to discuss.

## Queued (start conditions)
- T-166 final720 default + HEVC 10-bit delivery (Sonnet): next free slot.
- T-159 ears, T-144 option (b): after T-158 merges.
- Hands round 2: after T-155 is published.

## Decided today (for reference)
T-137 approved (~07:00Z); T-124 keep the existing final preset (~06:40Z); T-144 option (b) (~07:35Z); fidelity v2 stays
experimental (~06:40Z); T-138 gap not accepted → T-157 (~06:40Z); T-155 approved, boy 2.3.0 / girl 0.14.0 → CURRENT, third 0.1.0 first version (~08:20Z); T-157 option (a) stays opt-in until hands round 2 (~08:20Z); T-124 final720 + HEVC default → T-166 (~08:20Z); guard option 1: current versions only with a named current_decision (~08:20Z+).
