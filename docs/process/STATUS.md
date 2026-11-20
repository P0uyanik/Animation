# Status board

Updated by the Supervisor in the same commit as every merge or dispatch. Sources: [TASK_LOG](TASK_LOG.md),
[OWNERSHIP](OWNERSHIP.md), [OWNER_DECISIONS](OWNER_DECISIONS.md) (2026-11-20). As of 2026-11-20 ~07:35Z.
Session cap: 8 until 08:20Z, then 6. ETA "—" = none given yet.

## Character look
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-156 eyes/lashes to T-150 targets | Fable 5.2 | running | — | `t-156-claude-eye-targets` |
| T-160 hair round 6 (boy, auburn girl, third girl; owns the fringe) | Fable 5.2 | running | — | `t-160-claude-hair-r6` |
| T-158 deterministic girl 0.13.0 builds | Opus 5.5 | running | — | `t-158-claude-deterministic-build` |
| T-159 ears | — | queued: starts after T-158 merges | — | — |

Codex T-161 reference targets (lashes, ears, hair silhouette) go to T-156 and T-160 as targets.json.

## Release
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-155 candidates boy 2.3.0, girl 0.14.0, third 0.1.0 (current versions unchanged) | Opus 5.5 | running | — | `t-155-claude-candidates` |

## Interaction
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-157 grasp gap: wider band vs fewer fingers | Opus 5.5 | running | — | `t-157-claude-grasp-options` |
| Hands round 2 | — | queued: starts after T-157 and T-155 | — | — |

## Other
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-141 native hair curves (opt-in tool once green) | Fable 5.2 | running | — | `t-141` |
| T-144 retire unpinned generator versions, option (b) | Opus 5.5 | queued: after T-158 merges and a slot is free | — | `t-144-claude-retire-versions` |
| T-153 fidelity score v2 | Opus | merged; experimental, default stays v1 | — | `t-153-claude-fidelity-v2` |
| T-161 Codex reference targets | Codex | assigned (relay f33c4868); Codex limited until 2026-11-23 ~21:43Z | — | — |
| T-162 this board | Sonnet 5.5 | running | — | `t-162-claude-status-board` |
| T-163 starter felt prop library | Sonnet 5.5 | running | — | `t-163-claude-props` |

## Waiting for owner
Sheets are paths in text (branch: path).
1. T-137 faces round 5 (not final, eye openings too wide; T-156 follows up): `t-137-claude-faces`: `docs/evaluation/characters/T-137/f1a`, `.../f1b`, `.../f2`. Choices: 1 accept, 2 reject, 3 wait for T-156.
2. T-124 render preset: `docs/evaluation/rendering/T-124/README.md`. Choices: 1 keep the existing final preset, 2 switch to final720.
3. T-157 grasp gap options: `t-157-claude-grasp-options`: `docs/evaluation/animation/T-157/`. Choices: 1 wider band, 2 fewer fingers, 3 both.
4. T-144 plan (decided: option b, starts after T-158): `t-144-claude-retire-versions`: `docs/evaluation/T-144/PLAN.md`. Choices: a registry-only retire, b file comparisons, c defer.
5. T-155 candidate sheets (reference | current | candidate | target + crops): none yet; approve or reject per candidate.
6. T-141b: not approved; owner to discuss.
