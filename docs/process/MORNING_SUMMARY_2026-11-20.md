# Morning summary 2026-11-20 (Round-3 Supervisor, as of ~02:30Z)

Written early: the hourly self-check could not be created (see Usage), so this may not be updated before 06:45Z.
main = staging = `974dcee`.

## Merged overnight (all full gate green; defaults unchanged, new behaviour opt-in)
- T-142 A1 legacy renderer removal (`ac56901`; Windows red was a T-114 CRLF issue, fixed with a `.gitattributes` eol rule).
- T-152 Codex token audit + R3 handover; T-153 fidelity score v2 (opt-in); T-138 E4 grasp fit (opt-in) — batch `38bdf70`.
- T-124 720p render optimisation + opt-in `--profile final720|review` (`a12dbfc`).
- T-136 E2 blink schedule + E3 gaze chain, opt-in (`974dcee`).

## Waiting for the owner (not merged)
- T-137 faces, branch `t-137-claude-faces@321466a`, three independent parts:
  `docs/evaluation/characters/T-137/f1a/` (auburn girl eyes), `f1b/` (third girl eyes + fringe),
  `f2/` (boy "noticing"; part 1 changes the default `boy_interested.emotion.json`). All still outside T-150 eye targets.

## Running
- T-141 A2 native hair curves (Fable 5.2, session_01NPjxeLjT4M1U7aEjhC4Wuf), experiment, opt-in module `pipeline/charsys/groom/hair_curves.py`.
- Then T-144 A3 (plan only, to the owner). Phase 3 S1a/S1b/S1c postponed (owner ~23:30Z).

## Blocked
- T-132 publish (boy 2.3.0 / girl 0.14.0) and third character 0.1.0 candidate: guard tests `test_hair_r5` / `test_hands_r2`.

## Decisions needed
1. Guard tests: (a) narrow to named owner-approved candidates (+ permission rule) or (b) retire them.
2. T-137: approve/reject F1a, F1b, F2 one by one; F2 profile intensity stays 0.6 (higher also moves head turn and reach).
3. T-138: remaining 4.3 mm band gap is geometric: (a) wider band, (b) fewer fingers on the band, (c) accept.
4. T-153: adopt fidelity v2 as default? 11/13 vs 9/13 owner-decision agreement, but tuned in-sample.
5. T-124: use `final720` (207 s vs 433 s/frame, -52%) for finals? (`docs/evaluation/rendering/T-124/`)
6. New task? Girl 0.13.0 default build is not repeatable (ears/upper lid differ in ~half of 9 runs; found by T-137).

## Usage notes
- The permission classifier denied `create_trigger` and `send_later`: no hourly check ran; the Supervisor only woke on
  session messages. Fix: add permission rules for both, or create the hourly task by hand.
- Sending to session_01NPjxeNTmHt2DtBN8F8uLqB fails (needs a trusted device), so "MORNING SUMMARY <sha>" could not be sent.
- Sessions archived when merged: round-2 Supervisor, T-124, T-136, T-138, T-142, T-153.

## Update ~06:45Z (owner decisions ~06:40Z recorded in OWNER_DECISIONS.md, `e2c8904`)
- Started: T-154 guard allowlist, T-156 eyes to T-150 targets (Fable), T-157 grasp options, T-158 deterministic builds.
  T-155 candidate publish follows T-154; T-144 plan when a slot frees. Running sessions: 6/6.
- T-137 sheets (branch `t-137-claude-faces@321466a`, `docs/evaluation/characters/T-137/`): `f1a/strict.jpg`,
  `f1a/eyes_100.jpg`; `f1b/strict.jpg`, `f1b/eyes_100.jpg`; `f2/e910_f47-80_before_after.jpg`, `f2/mouth_shot_size.jpg`
  (F2 has no strict sheet).
- T-124 comparison (main, [T-124](../evaluation/rendering/T-124/README.md)): `README.md` table, `sheets/frames_proposed.jpg`,
  `sheets/crops_proposed.jpg`, `clips/clip_full.mp4`, `clips/clip_crop.mp4`.
