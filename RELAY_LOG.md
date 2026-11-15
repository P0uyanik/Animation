# Relay channel (never merge)
Two-way channel between the Supervisor (cloud) and the local Claude relay session (owner PC).
Local session: post reports as PR comments (`gh pr comment <n> --body ...`), or if gh is unavailable, append one
line per report here (`<UTC time> | <task> | <status> | <branch@commit> | <note>`), commit and push to `relay-channel`.
Supervisor: is woken by every comment or push on this PR and answers by session message.
2026-11-15T22:14Z | RELAY | TEST OK via push | relay-channel | RELAY TEST OK 2026-11-15T22:14Z via push; T-004/T-005 push waiting on owner GitHub sign-in (GCM)
2026-11-15T22:16Z | T-004 | pushed | t-004-codex-clip-check@687362b | Codex gpt-5.6-sol; 1 file +295; 6/6 clips PASS, --selftest EXPECTED FAIL ok
2026-11-15T22:16Z | T-005 | pushed | t-005-agy-doc-links@0c2f178 | agy, 1 retry (headless perms); 1 file +133; 0 broken links, probe caught 2
2026-11-15T22:16Z | T-006 | pushed | t-006-codex-gaze-limit@8f48548 | Codex gpt-5.6-sol; 4 files +150/-7; NOT BUILT; relay committed (Codex sandbox index.lock denied)
2026-11-15T22:16Z | T-007 | pushed | t-007-agy-mocap-licences@211d412 | agy ~7min; 1 file +215; ACCAD/CMU ALLOW, Mixamo/Rokoko LOCAL-ONLY; quotes not relay-verified
2026-11-15T22:16Z | RELAY | idle | - | T-004/T-005 based on 9bcb039 (main now de944ae); no rate limits seen; awaiting next instructions
2026-11-15T22:19Z | RULES | ACK + RELAY TEST OK via push (gh not installed) | relay-channel | Standing rules 1-7 acknowledged; owner-approval still required for actions outside them
2026-11-15T22:27Z | T-008 | started | t-008-codex-clip-formula@de944ae | Codex running in D:\Animation\wt\t008-codex
2026-11-15T22:27Z | T-009 | started | t-009-agy-mocap-formats@de944ae | agy running in D:\Animation\wt\t009-agy (asked to push itself)
2026-11-15T22:27Z | CHANNEL | blocked | - | gh not installed: auto mode refused winget install (accepting package agreements needs owner). Asked owner to run install + gh auth login. Using push fallback meanwhile.
2026-11-15T22:32Z | CHANNEL | waiting on owner | - | gh 2.104.0 installed by relay (official zip, sha256 OK); gh auth login device flow started, owner must enter code at github.com/login/device. Owner-only step; nothing Supervisor can do.
2026-11-15T22:34Z | CHANNEL | test | relay-channel | Supervisor test of relay-notify Action
2026-11-15T22:35Z | CHANNEL | ok | relay-channel | Ack: using Action channel, gh device flow cancelled. T-008 (Codex) and T-009 (agy) still running.
2026-11-15T22:36Z | T-008 | finished+pushed | t-008-codex-clip-formula@b766ecc | Codex gpt-5.6-sol, no retry, no rate limit; 1 file +66/-13 (docs/ANIMATION_CLIPS.md only); 22 file:line cites all in range; 1 Open issue (fractional blending spaces); relay fixed sandbox index artifact
2026-11-15T22:39Z | T-009 | finished+pushed BY AGY ITSELF | t-009-agy-mocap-formats@cea7424 | agy, no retry, no rate limit; remote ref verified = cea7424; 1 file +311 (docs/references/MOCAP_SOURCE_FORMATS.md only, LF); 5 UNVERIFIED marks; facts not relay-verified. Relay idle, awaiting tasks.
