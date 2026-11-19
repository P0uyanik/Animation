# T-111 process note (2026-11-19)

Design-only task. Deliverables: `docs/architecture/INTERACTION_AFFORDANCES.md`, `docs/tasks/T-112a.md`,
`docs/tasks/T-112b.md`, `docs/tasks/T-051.md`. No code, content, test or frozen file changed.

Input: `f550cbd` (integration/round3, as the task prompt names; the task file says `origin/main`).

Code read (read-only): `engine/scene/interaction.{h,cpp}` (reachTo, plan, graspShape, visibleSocket, hold / place /
handover, armClearancePass, finishInteractions), `engine/scene/collision.h`, `engine/scene/reaction.h`,
`engine/scene/actions.cpp` (planReactionActions, look action), `engine/scene/asset_library.{h,cpp}` (unknown keys
are ignored, so an additive `affordances` block is safe), `engine/scene/scene.h` (InteractionOptions),
`engine/anim/personality.h` (TimingProfile), `engine/anim/animation.h` (HandPose, applyHandPose),
`content/timing/*.json`, `content/assets/*.asset.json`, `episodes/e907_exchange/make_shot.py`,
`tests/test_interaction.cpp`, `tests/test_timing_profile.cpp` (test names only).

Split decision: T-112 is split into T-112a (format, expander, pick up / carry / place, golden hashes) and T-112b
(pass, reactions, hand shapes, two hands), because the golden-hash safety net must land before any planner change.
T-112b and T-051 run in parallel after T-112a; their only coupling is the `hand.<s>.band` track (design section 5).

Not verified (design assumptions to check in T-112a): that every content scene with interaction actions is covered by
the grep in design 6.3; that `SceneEvaluator` can expose the read-only geometry callback the expander needs without
touching `scene.h` (if not, T-112a adds `engine/scene/scene.h` to its write-set with the Supervisor's approval).

Builds, renders, tests: none (docs only).
