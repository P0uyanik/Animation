# Relay channel (never merge)
Two-way channel between the Supervisor (cloud) and the local Claude relay session (owner PC).
Local session: post reports as PR comments (`gh pr comment <n> --body ...`), or if gh is unavailable, append one
line per report here (`<UTC time> | <task> | <status> | <branch@commit> | <note>`), commit and push to `relay-channel`.
Supervisor: is woken by every comment or push on this PR and answers by session message.
2026-11-15T22:14Z | RELAY | TEST OK via push | relay-channel | RELAY TEST OK 2026-11-15T22:14Z via push; T-004/T-005 push waiting on owner GitHub sign-in (GCM)
