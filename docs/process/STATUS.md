# Status board

Updated by the Supervisor in the same commit as every merge or dispatch. Sources: [TASK_LOG](TASK_LOG.md),
[OWNERSHIP](OWNERSHIP.md), [OWNER_DECISIONS](OWNER_DECISIONS.md) (2026-11-21). As of 2026-11-21 ~10:45Z (R4 Supervisor session_01NPjxeNjJghYQMGjDycpnsC). R3 released (main ea4e440). T-171 CHECKPOINT and T-172 READY wait for the owner; T-175 style review pending; T-177 and T-179 merged, T-178 running; P2 rule applied. Session cap temporarily 7.
Session cap: 6 (temporary 8 ended 08:20Z). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU (from ~08:30Z). ETA "—" = none given yet.

## Character look
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-156 eyes/lashes to T-150 targets | Fable 5.2 | running (third renders, READY) | — | `t-156-claude-eye-targets` |
| T-160 hair round 6 (opt-in, not adopted; docs/evaluation/characters/T-160/README.md) | Fable 5.2 | READY; merge as opt-in base after T-155 | — | `t-160-claude-hair-r6` |
| T-158 deterministic builds | Opus 5.5 | merged (main 2a02532) | — | — |
| T-167 hair round 7, reference fidelity | Fable 5.2 | merged in R3 (boy r6, girls r7) | — | `t-167-claude-hair-r7` |
| T-168 boy face contour + nose | Fable 5.2 | running (fix: cheek-pad fade + nose) | — | `t-168-claude-boy-face` |
| T-159 temple hollow (both girls, owner ~08:35Z) then ears | Fable 5.2 | running (cheek seam, then ears); temple fix cafa12c opt-in | — | `t-159-claude-ears` |

Codex T-169 hair reference study (relay 2987afa) feeds T-167. Codex T-161 reference targets (lashes, ears, hair silhouette) go to T-156 and T-160 as targets.json.

## Release
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-154 guard allowlist + T-137 faces (F1a/F1b/F2, owner-approved ~07:00Z) | — | on `integration/t-137`, gate running | — | `integration/t-137` |
| T-155 R3 release: boy 2.3.0 / girl 0.14.0 / third 0.1.0 CURRENT | Opus 5.5 | merged (main ea4e440, gate 44849547856 green) | — | — |

## Interaction
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-157 grasp gap: wider band (a) stays opt-in until hands round 2 | Opus 5.5 | merged (main 2a02532) | — | — |
| T-171 hands round 2 (then revisit T-157 option a default) | Fable 5.2 | CHECKPOINT d1d150f: opt-in fingerClose; 4 owner decisions | — | `t-171-claude-hands-r2` |
| T-172 test video with released R3 characters (5–8 s, existing shot) | Sonnet 5.5 | READY 9eaa8a2 (640x360); owner: accept or 720p | — | `t-172-claude-test-video` |

## Other
| Task | Model | State | ETA | Branch |
| --- | --- | --- | --- | --- |
| T-141 native hair curves (opt-in tool) | Fable 5.2 | merged (main 2a02532) | — | — |
| T-144 retire unpinned generator versions | Opus 5.5 | done: option (c), legacy documented, no removal (owner ~20:50Z) | — | — |
| T-166 final720 default + HEVC 10-bit delivery | Sonnet 5.5 | merged (main 86288cb); ffmpeg added to CI pins | — | — |
| T-175 locomotion layer: CMU importer + foot-lock + chibi style filter (owner go ~23:35Z) | Opus 5.5 | running; first a walk + sit/stand style review | — | `t-175-claude-locomotion` |
| T-176 whole-project review (analysis) | Opus 5.5 | merged; P2/P3/P5 approved ~04:10Z, rest undecided |
| T-177 docs-only fast path (T-176 P3) | Sonnet 5.5 | merged (main c16ef79) |
| T-179 generator pin map (T-176 P12 light) | Sonnet 5.5 | merged (docs/process/GENERATOR_PINS.md) |
| T-178 one release-manifest rule (T-176 P5) | Opus 5.5 | stage 1 at 2f7c55b (new rule, 130/130); old guards wait for owner's typed approval in its session | — | — |
| T-174 animation reuse vs build (research) | Opus 5.5 | merged: keep engine for acting/verbs/grasp; reuse CMU mocap for walk/run/sit/stand; build importer + foot lock (~3.5–4 d); owner questions open | — | — |
| T-153 fidelity score v2 | Opus | merged; experimental, default stays v1 | — | `t-153-claude-fidelity-v2` |
| T-161 Codex reference targets | Codex | assigned (relay f33c4868); Codex limited until 2026-11-23 ~21:43Z | — | — |
| T-162 this board | Sonnet 5.5 | merged; Supervisor maintains | — | — |
| T-164 gate PR #2 comment only for integration/staging/main | Sonnet 5.5 | merged (main 2a02532) | — | — |
| T-165 shared task kit + tools/ready.py | Opus 5.5 | merged (main 2a02532) | — | — |
| T-163 starter felt prop library | Sonnet 5.5 | merged (main 2a02532) | — | — |

## Waiting for owner
1. T-170 world plan: trimmed (T-170d, 4.5–6 task-days) + ready-made materials only; on hold.
2. "Start the planned automatic tasks" (HOLD ~09:05Z).
3. T-141b: not approved; owner to discuss.

## On hold (owner ~10:05 CET; release phrase via the liaison)
- T-170 world plan (ready-made materials only, ~20:10Z).
- Next character versions; new Codex tasks.

## Decided today (for reference)
T-137 approved (~07:00Z); T-124 keep the existing final preset (~06:40Z); T-144 option (b) (~07:35Z); fidelity v2 stays
experimental (~06:40Z); T-138 gap not accepted → T-157 (~06:40Z); T-155 approved, boy 2.3.0 / girl 0.14.0 → CURRENT, third 0.1.0 first version (~08:20Z); T-157 option (a) stays opt-in until hands round 2 (~08:20Z); T-124 final720 + HEVC default → T-166 (~08:20Z); guard option 1: current versions only with a named current_decision (~08:20Z+); bow seat front per refs 01/02 (~09:00Z).
