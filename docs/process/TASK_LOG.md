# Task log

| ID | Task | State | Commit / branch | Notes |
| --- | --- | --- | --- | --- |
| M3 | Generic facial system (girl face, expression library, glasses) | delivered; awaiting owner acceptance | b41c88f | `docs/second_character/M3_FACE_SYSTEM.md` |
| M3.1 | Facial engine completion (blink in-betweens, jaw, timing, oval eyes) | delivered; awaiting owner acceptance | 9d9612f | M3.1 section of the same document |
| M3.2 | First end-to-end production path (engine animates, Blender renders) | delivered; awaiting owner acceptance | 7ff08cc | `docs/PRODUCTION_PIPELINE.md` |
| T-001 | Plush Studio drives the shot pipeline (workflow contract, Production panel, safe save) | **result accepted** 2026-11-15 (option 1: shot-actions timing editor and life checkbox kept) | branch t-001-studio-shot-pipeline (763d469), merged in 5f4276a | ctest 4/4 with OIDN 2.3.3 (Implementer and Supervisor); Implementer cost about $10.08 at list price |
| T-002 | Clip Foundation (shared clips, generated retarget data, clip actions, 6 clips) | **result accepted** 2026-11-15 | branch t-002-clip-foundation (6478c30), merged | AC1–AC9 PASS; Supervisor re-ran ctest 4/4 and plush_tests 46/46; Implementer cost about $26 at list price |
| T-003 | Body emotions (8 emotions, 12 clips, emotion layer) | **result accepted** 2026-11-15 | branch t-003-body-emotions (9f9f1f7), merged e8fd5d5 | AC1–AC7, AC9 PASS; AC8 evidence; Supervisor re-ran ctest 4/4, plush_tests 20,576 assertions; eye-closing on head pitch → T-006 |
| T-004 | Clip file validation test (Codex) | **result accepted** 2026-11-15 | t-004-codex-clip-check (687362b), merged | 18/18 clips PASS, selftest OK |
| T-005 | Markdown link checker (Antigravity) | **result accepted** 2026-11-15 | t-005-agy-doc-links (0c2f178), merged | 0 broken links |
| T-006 | Soft gaze range limit relative to head (Codex) | **result accepted** 2026-11-15 | t-006-codex-gaze-limit (8f48548), merged | ctest 4/4, plush_tests 20,591 assertions; render check pending (test video) |
| T-007 | Mocap licence verification (Antigravity) | **result accepted** 2026-11-15 | t-007-agy-mocap-licences (211d412), merged | ACCAD/CMU ALLOW, Mixamo/Rokoko LOCAL-ONLY; CMU quote to re-check in converter task |
| T-008 | Exact clip retarget formula, ANIMATION_CLIPS.md §8 (Codex) | **result accepted** 2026-11-15 | t-008-codex-clip-formula (b766ecc), merged | formulas match code; open issue: fractional blend spaces differ (emotion vs clip layers) |
| T-009 | ACCAD/CMU mocap formats + role mapping (Antigravity) | **result accepted** 2026-11-15 | t-009-agy-mocap-formats (cea7424, pushed by agy), merged | 5 UNVERIFIED points; verify against real files in converter task |
| T-010 | V1 test video, 2.5 s two-shot (Claude Implementer) | **result accepted** 2026-11-15 | t-010-claude-test-video (5020d2a), merged | 60 frames, smooth PASS, gaze in limits; girl eyes PASS, boy eyes FAIL (lid rig of frozen 1.0.0) → T-014; gap list → V2–V6 |
| T-012 | Measurable visual target spec (Codex; agy quota-out) | **result accepted** 2026-11-15 | t-012-codex-visual-target (6f84e3c), merged | 33 ESTIMATE values; 17 benchmark frames |
| T-013 | plush.asset/1 prop library + scene props (Codex, 1 fix round) | **result accepted** 2026-11-15 | t-013-codex-asset-library (b8c76df), merged | ctest 4/4, plush_tests 20,652 assertions |
| T-014 | Boy eyelids: shared lids-follow-gaze, boy 1.1.0 unpublished candidate (Codex + Supervisor cloud shot) | **result accepted** 2026-11-16 | t-014-codex-boy-lids (e2d708e), merged | 1.0.0 unchanged; girl render 0 px diff; verify_charsys, export 8/8, face tests PASS; eyes open in T-010 shot except fringe occlusion at max pitch |
| T-017 | Prop attachment evaluation + bake (Codex) | **result accepted** 2026-11-16 | t-017-codex-prop-eval (10aacbf), merged | ctest 4/4, plush_tests 20,754 assertions |
| T-015/16/18/19/24/25 | V3 batch: material library + GN fibres, groom/1 girl hair, garment/1 + robustness, girl outfit (spec 0.7.1) | **merged** 2026-11-16 (functional) | integration/v3 (2cb4616) | ctest 4/4, plush_tests, presets 54/54, verify_charsys PASS (boy unchanged), garment test PASS both bodies. **Girl visual quality NOT approved**; open T-026: fuzz below target (felt, wool, boots), sheen systemic miss, grey face, boot lining ring |
| T-020..T-039 (consolidation) | Batch 1 + V3b work consolidated: secondary motion, interactions, acting, materials, face v2, hair v2, garment drape, girl 0.9.0 (intermediate, owner-approved), fidelity CI, gate, determinism, Boy 2.0 body | **in main** 2026-11-17 | integration/consolidated (d70bc8f) | full gate PASS (all tiers); fidelity boy 64.05 (−0.44), girl 65.45 (+0.04); report `docs/evaluation/integration/consolidation/README.md` |
| T-038b | Boy `hair_mass` bit-determinism (canonical topology before SUBSURF+DISPLACE) | **in main** 2026-11-17 | t-038b-claude-hair-determinism (d70bc8f) | determinism 3× PASS, verify_charsys PASS |
| T-040 | Arm-body clearance in all poses | **open, redesign** | t-040-claude-pose-clearance (2e81e45) | not merged: e905 −37.7 mm while wrist pinned, 3 clip tests over-corrected; split into T-040r1 (mesh-based clearance) and T-040r2 (hold/hand-over path planning, with T-047) |
| T-041 | Gate on GitHub, file claims, full regression, unchanged-character guard, durable backups | assigned (first batch) | t-041-claude-gate-claims | `docs/tasks/T-041.md` |
| T-043 | Spec parts, per-feature generator versions, helpers out of body_v6 | assigned (first batch) | t-043-claude-spec-versions | `docs/tasks/T-043.md` |
| T-046 | Facial animation | assigned (first batch) | t-046-claude-facial-animation | `docs/tasks/T-046.md` |
| T-040r1 | Clearance from the real mesh, smooth correction | assigned (first batch) | t-040-claude-pose-clearance | `docs/tasks/T-040r1.md` |
| T-053a | Reference behaviour and expression analysis; draft personality profiles | assigned 2026-11-17 | t-053a-claude-reference-behaviour | `docs/tasks/T-053a.md` |
| T-048 | Branch cleanup workflow + tests | **in main** 2026-11-17 | t-048-claude-branch-cleanup (8f1c3ce), merge ae15c0b | 25/25 cleanup tests, full gate PASS; first real dry run after T-041 backups |
| T-049 | Hair approach study (strand vs sculpted vs hybrid) | assigned 2026-11-17 | t-049-claude-hair-study | `docs/tasks/T-049.md` |
| T-050 | GPU / render cost study (no spending) | **in main** 2026-11-17; owner decision pending | t-050-claude-render-cost (242c97c) | previews CPU; review/finals on rented RTX 4090 ≈ $0.84/finished min, ≈ $10–25/month; do not buy a GPU for cost alone |
| T-044 | Hair v3 | queued (after T-043) | — | — |
| Boy F09 / H28 | Face and hair candidates for the boy | awaiting owner review | — | unpublished experiments |

Tasks from now on are numbered T-001, T-002, …, and pass through the states in `WORKFLOW.md`.

## Open visual issues (owner: girl visual quality not yet approved)
| ID | Issue | Status |
| --- | --- | --- |
| T-026a | Fibre fuzz below VISUAL_TARGET on felt, wool yarn, boot fleece (fleece passes) | open |
| T-026b | Sheen P90/P50 below target on all presets (systemic: light or metric) | open |
| T-026c | Girl face skin renders greyer than body skin | open |
| T-026d | Boot top shows lining ring | open |
