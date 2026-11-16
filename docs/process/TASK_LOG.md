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
| Boy F09 / H28 | Face and hair candidates for the boy | awaiting owner review | — | unpublished experiments |

Tasks from now on are numbered T-001, T-002, …, and pass through the states in `WORKFLOW.md`.
