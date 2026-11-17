# Character animation review checklist (T-053a draft, 2026-11-17)

Use for reviewing animation tasks (T-045, T-046, T-051, T-053, T-054, and later ones) against the owner references.
Each point is checkable on a render or curve; the citation says what to compare with. Full evidence:
[boy guide](boy_yellow_hoodie/REFERENCE_BEHAVIOUR.md), [girl guide](girl_auburn_bun_glasses/REFERENCE_BEHAVIOUR.md),
[inventory and citation keys](REFERENCE_INVENTORY.md). A FAIL on an identity point (marked **I**) blocks acceptance;
other points are reported with the shot and reason.

## Both characters
- [ ] **I** Appearance unchanged by animation: proportions, hair, clothing, glasses (compare front views
      `canon29_front`, `sheet30_front`).
- [ ] Gaze rests on the task object during handwork; eyes hold within 3° of the target (`VISUAL_TARGET.md`).
- [ ] Blinks: closing faster than opening; 3–7 f total; no two characters blinking in sync for long stretches.
- [ ] Eyes/brows lead mouth/head by 2–4 f on reactions.
- [ ] Hands: contact without gaps or penetration; fingers curled naturally when resting (`#18`, `ref_44`).
- [ ] The two characters stay readable as opposites when on screen together (heavy-lid low energy vs. open-eyed
      bright), as in `lineup`, `C1`, `WT`, `PB S6`.
- [ ] Anything not shown in the references is listed as extrapolation in the task report.

## Boy (`boy_yellow_hoodie`)
- [ ] **I** Resting upper lid at about mid-iris (Blink ≈ 0.4–0.5) whenever he is not surprised/excited; never
      fully open eyes at rest (`char_C`, `#28` r1c1).
- [ ] **I** Resting mouth = small pout (corners slightly down), brows low and flat (`char_C`).
- [ ] Mild slouch, shoulders forward, chin down; head pitched toward the object (`char_C`, `C1`, `WT`).
- [ ] Idle hands: in pockets, or resting on a rim with fingers curled over the edge (`#08`, `WT f002`, `CW`).
- [ ] Low body motion during holds; no big gestures except deliberate goofy moments (`WT`, `#09` key animation).
- [ ] Smiles are rare; engagement shows as eyes opening + brows down in concentration, small `MouthO`
      (`PB f255`–`f288`), not as a grin.
- [ ] Long unchanged stares are allowed (≥ 1–3 s) when bored (`PB S1`, `S3`).
- [ ] Impatience reads through small actions (reaching in to grab/lift, fidgets), not exaggerated tantrums
      (`PB f044`–`f068`; fidgets are extrapolation).
- [ ] He does not look at the girl unless the shot requires it (no reference shows it).

## Girl (`girl_auburn_bun_glasses`)
- [ ] **I** Eyes fully open at rest, no lid overlap on the iris; brows high and arched (`char_B`, `ref_34` Neutral).
- [ ] **I** Resting mouth = closed soft smile; open smile (teeth + tongue) for happy beats (`ref_34`, `char_B`).
- [ ] **I** Irises brown (not the blue of the `ref_30` Sad/Surprised/Angry tiles).
- [ ] Upright, open posture; slight head tilt allowed (`char_B`, `ref_46`, `#09`).
- [ ] Thinking: hand to chin with loosely curled fingers (`WT f000`–`f012`).
- [ ] Explaining: lean in, index-finger point held while talking (≥ 1 s), eyes on the object (`WT f022`–`f060`).
- [ ] Reach brisk: ≈ 8–10 f from start to pointing pose (`WT f012`–`f022`).
- [ ] Handwork careful and two-handed: flat palms on paper, fingertip holds, slow placement (≈ 1 s lowering,
      ≈ 0.5 s release) (`PB S2`, `S4`).
- [ ] Blinks every ≈ 1–1.6 s in active scenes, often at a change of action; longer (≈ 7 f) blink when the head and
      gaze drop (`WT f016`, `f080`–`f084`).
- [ ] Reaction to success: lean in, open smile, brows up (`PB f242`–`f288`).
- [ ] She is never shown bored, sulky or slouched in scene references.

## Task-specific focus
| Task | Check first |
| --- | --- |
| T-045 (body mechanics) | boy slouch, head pitch, weight on one leg, leaning on a rim; girl upright, lean-in when explaining |
| T-046 (facial animation) | the **I** face points; blink timing per character; expression tables (weights are estimates) |
| T-051 (finger animation) | girl: flat-palm creasing, fingertip holds, index point, chin touch; boy: curled fingers on the rim, corner grab |
| T-053 (personality system) | values match `content/personality/*.draft.json` and their citations; blink/boredom generators reproduce the measured ranges; extrapolated behaviours (boy fidgets) stay small and keep the heavy lid |
| T-054 (dialogue, lip sync) | girl talks with brows up and eyes on the object (`WT f020`–`f052`); boy never talks in the references: keep heavy lids, small jaw |
