# Relay channel (never merge)
Two-way channel between the Supervisor (cloud) and the local Claude relay session (owner PC).
Local session: post reports as PR comments (`gh pr comment <n> --body ...`), or if gh is unavailable, append one
line per report here (`<UTC time> | <task> | <status> | <branch@commit> | <note>`), commit and push to `relay-channel`.
Supervisor: is woken by every comment or push on this PR and answers by session message.
