# T-097-boy: boy acting

Implementer: Claude (cloud) · lane C · path B · branch `t-097-boy-claude-acting` from `origin/main` (input SHA in the task prompt).
Round 2 Phase D, owner-approved 2026-11-18 ~22:50Z / ~23:00Z (renamed from T-097B/G), standing approval ~23:10Z.
Track: Personality. Uses the shared acting system (T-097A blending, T-097B reaction planner, T-097C checks; T-097D wires
reactions into playback and is merging in parallel — use it as soon as it lands; until then author with explicit
emotion/gesture actions). Calibration targets: `docs/evaluation/animation/T-106/` (Codex reference performance data)
and `content/timing/reference_timing.json` (T-104). Touch ONLY this character's files; never the shared system, the
other character, or the e907 exchange shot.

## Target personality
subtle, low energy, delayed interest; sideways glances; small mouth changes; reluctant gestures (impatient, easily bored). Match the reference videos first; invent only what they do not show, in the same spirit.

## Acceptance criteria
1. Tune `content/personality/boy_yellow_hoodie.json` (reaction, tempo, gaze habit, gesture preferences, limits) toward the T-106
   measurements; document each value's source.
2. Character gesture clips and character-prefixed emotion files (`content/emotions/<char>_*.emotion.json`) (new files with the character
   prefix); for the girl the open "delighted" mouth is an acting-beat expression, rest face unchanged.
3. One solo test shot folder `episodes/e908_boy_acting/` (new) showing notice -> reaction -> gesture -> hold to an
   event; animcheck incl. the T-097C acting checks passes with no warnings for this character.
4. Signature tests for this character (`tools/animcheck/tests/fixtures` not touched; own test file).
5. Evidence: cheap preview first, then a short Cycles clip + strip vs the reference moments; time-ledger line.

## Write-set
`content/personality/boy_yellow_hoodie.json`, `content/clips/boy_*.clip.json` (new), `content/emotions/boy_*.emotion.json` (new),
`episodes/e908_boy_acting/**` (new), `tests/acting/test_boy_signature.py` (new),
`docs/evaluation/animation/T-097-boy/**`.

## Read-only
Everything shared: `engine/**`, `tools/animcheck/**`, `content/personality/shared.json`, `content/personality/SCHEMA.md`,
the other character's files, `episodes/e907_exchange/**`.

## Reporting
send_message to the Supervisor session `session_01NPjxeNGwvGuevzV1aTjiEo`:
`<UTC> | T-097-boy | READY|BLOCKED|STATUS | <branch@sha> | input <SHA> | <one line>` + ledger line.
