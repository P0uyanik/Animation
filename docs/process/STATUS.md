# Status board

Updated by the Supervisor in the same commit as every merge or dispatch. Sources: [TASK_LOG](TASK_LOG.md),
[OWNERSHIP](OWNERSHIP.md), [OWNER_DECISIONS](OWNER_DECISIONS.md) (2026-11-20). As of 2026-11-20 ~15:45Z. main = `7320a6e` + docs. Fix round in progress; next versions = one bundled set after owner approval.
Session cap: 6 (temporary 8 ended 08:20Z). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU (from ~08:30Z). ETA "—" = none given yet.

## Character look
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-156 eyes/lashes to T-150 targets | Fable 5.2 | running (third renders, READY) | — | `t-156-claude-eye-targets` |
| T-160 hair round 6 (opt-in, not adopted; docs/evaluation/characters/T-160/README.md) | Fable 5.2 | READY; merge as opt-in base after T-155 | — | `t-160-claude-hair-r6` |
| T-158 deterministic builds | Opus 5.5 | merged (main 2a02532) | — | — |
| T-167 hair round 7, reference fidelity | Fable 5.2 | running (bow seat, evidence; + Codex T-169) | — | `t-167-claude-hair-r7` |
| T-168 boy face contour + nose | Fable 5.2 | running (fix: cheek-pad fade + nose) | — | `t-168-claude-boy-face` |
| T-159 temple hollow (both girls, owner ~08:35Z) then ears | Fable 5.2 | running (cheek seam, then ears); temple fix cafa12c opt-in | — | `t-159-claude-ears` |

Codex T-169 hair reference study (relay 2987afa) feeds T-167. Codex T-161 reference targets (lashes, ears, hair silhouette) go to T-156 and T-160 as targets.json.

## Release
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-154 guard allowlist + T-137 faces (F1a/F1b/F2, owner-approved ~07:00Z) | — | on `integration/t-137`, gate running | — | `integration/t-137` |
| T-155 boy 2.3.0 / girl 0.14.0 / third 0.1.0 | Opus 5.5 | HELD by owner (~16:25 CET): bundled into the next version set; current stays 2.2.0/0.13.0 | — | `t-155-claude-candidates-r2@2774c13` |

## Interaction
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-157 grasp gap: wider band (a) stays opt-in until hands round 2 | Opus 5.5 | merged (main 2a02532) | — | — |
| Hands round 2 (then revisit T-157 option a default) | — | queued: starts once T-155 is published | — | — |

## Other
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-141 native hair curves (opt-in tool) | Fable 5.2 | merged (main 2a02532) | — | — |
| T-144 retire unpinned generator versions, option (b) (owner ~07:35Z) | Opus 5.5 | queued: after T-158 merges and a slot is free | — | `t-144-claude-retire-versions` |
| T-153 fidelity score v2 | Opus | merged; experimental, default stays v1 | — | `t-153-claude-fidelity-v2` |
| T-161 Codex reference targets | Codex | assigned (relay f33c4868); Codex limited until 2026-11-23 ~21:43Z | — | — |
| T-162 this board | Sonnet 5.5 | merged; Supervisor maintains | — | — |
| T-164 gate PR #2 comment only for integration/staging/main | Sonnet 5.5 | merged (main 2a02532) | — | — |
| T-165 shared task kit + tools/ready.py | Opus 5.5 | merged (main 2a02532) | — | — |
| T-163 starter felt prop library | Sonnet 5.5 | merged (main 2a02532) | — | — |

## Waiting for owner
1. T-170 world style plan review (`docs/evaluation/world/T-170/README.md`; 8 questions incl. wood style and water container).
2. "Start the planned automatic tasks" (HOLD ~09:05Z).
3. T-141b: not approved; owner to discuss.

## On hold (owner ~10:05 CET; release phrase via the liaison)
- T-166 final720 default + HEVC 10-bit delivery.
- T-144 option (b) (prerequisite T-158 now merged).
- Hands round 2 (after T-155 is published).
- Next character versions; new Codex tasks.

## Decided today (for reference)
T-137 approved (~07:00Z); T-124 keep the existing final preset (~06:40Z); T-144 option (b) (~07:35Z); fidelity v2 stays
experimental (~06:40Z); T-138 gap not accepted → T-157 (~06:40Z); T-155 approved, boy 2.3.0 / girl 0.14.0 → CURRENT, third 0.1.0 first version (~08:20Z); T-157 option (a) stays opt-in until hands round 2 (~08:20Z); T-124 final720 + HEVC default → T-166 (~08:20Z); guard option 1: current versions only with a named current_decision (~08:20Z+); bow seat front per refs 01/02 (~09:00Z).
