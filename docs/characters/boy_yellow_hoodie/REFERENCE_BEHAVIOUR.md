# Boy (`boy_yellow_hoodie`): reference behaviour guide (T-053a draft, 2026-11-17)

Owner brief: **impatient, easily bored**. This guide records only what the references show; citation keys are
defined in [REFERENCE_INVENTORY.md](../REFERENCE_INVENTORY.md). Anything not shown is in §7 and marked
**EXTRAPOLATION**. Evidence images: [contact sheet](../../evaluation/characters/T-053a/contact_boy.jpg) and the
frame strips in [T-053a](../../evaluation/characters/T-053a/README.md).

Face-control vocabulary is the shared action-unit set of `pipeline/charsys/face_library/expressions.json`
(`Blink.L/R`, `EyeWide`, `EyeSquint`, `BrowUp.L/R`, `BrowDown`, `BrowSad`, `MouthSmile`, `MouthFrown`, `MouthWide`,
`MouthO`, `JawOpen`). Weights are visual **ESTIMATES** (0–1) read from the images, not measurements.

## 1. Appearance cues that carry the personality
| Cue | What the references show | Citations |
| --- | --- | --- |
| Heavy upper lids | Resting upper lid crosses the iris at about its middle; flat, almost straight lid line; lower lid neutral. Present even in T-pose and technical renders: it is his **default**, not an expression | `char_C`; `#08` turnaround, Neutral, T-pose; `#28` r1c1; `#12` Neutral; `lineup` |
| Low, flat brows | Brows sit low and close to the lid line, nearly horizontal, slight downward slope to the inner end | `char_C`; `#28` r1c1 |
| Small pout | Tiny mouth, corners slightly down (a small "u" turned over), lower lip slightly forward | `char_C`; `#08` Neutral; `#28` r1c1 |
| Head | Chin slightly down; head often pitched forward/down toward the object | `char_C`; `C1`; `WT f002`–`f120`; `PB S1`/`S3` |
| Posture | Mild slouch: shoulders relaxed and slightly forward, arms hanging, hands in pockets; weight shifted to one leg in the three-quarter turnaround | `char_C`; `#08`; `#29` turnaround and "No Mesh Collisions" tile; `C1` |
| Eye contact | In every scene image and video he looks **down at the object**, never at the girl or camera | `C1`, `CD`, `CW`, `WT`, `PB S1/S3/S6` |

Reading: low-energy, half-interested default. The heavy lid is the single most important identity cue: a boy
with fully open eyes at rest no longer matches `char_C`.

## 2. Expression catalogue
r = row, c = column of `#28` (4×4 grid, three-quarter view).

| Expression | Description for face controls (ESTIMATE weights) | Citations |
| --- | --- | --- |
| **Neutral / resting (signature)** | `Blink` 0.40–0.50 both eyes (upper lid at mid-iris), `BrowDown` 0.15, `MouthFrown` 0.20, jaw closed, cheeks flat | `char_C`; `#28` r1c1; `#08` Neutral; `#12` Neutral |
| Unimpressed / "Colfited" | Neutral plus brows a touch lower and flatter, gaze slightly off-axis; `Blink` 0.5, `MouthFrown` 0.3 | `#28` r3c3; `#09` face strip tile 1–2 |
| Skeptical | one brow raised over a heavy lid: `BrowUp.L` (or R) 0.4, `Blink` 0.45 | `#09` face strip tile 3 |
| Concentrating / intrigued (seen in video) | brows pulled **down and in** (`BrowDown` 0.5–0.6), eyes **more open** than his rest (`Blink` 0.15–0.25), gaze locked down on the object, small open mouth `MouthO` 0.3–0.4 | `PB f264`–`f288` (S6); `WT f036`, `WT f072` (mouth closed variant, `MouthFrown` 0.3) |
| Frustrated / sulky with a task | inner brows angled (BrowDown 0.4 + slight BrowSad 0.2), heavy lids, pout `MouthFrown` 0.4, blush visible | `CD` (holding an uneven fold; interpretation of "frustrated" is ours) |
| Happy | eyes closed as upward arcs (`Squint`-like: `Blink` 0.9 + `EyeSquint` 1), small closed smile `MouthSmile` 0.6, blush | `#28` r1c2; `#08` Happy |
| Gentle smile | heavy lids kept (`Blink` 0.45), small closed smile `MouthSmile` 0.35, slight head tilt | `#28` r4c4 |
| Happy, open | eyes open round, open smile `MouthWide` 0.6 (teeth) | `#28` r3c2; `#09` face strip tile 4 |
| Excited | `EyeWide` 0.6, `MouthWide` 0.8, brows up 0.4 | `#28` r4c2 |
| Surprised / curious | eyes fully open round (`EyeWide` 0.5–0.8), brows up 0.5, small `MouthO` 0.5 | `#28` r1c4, r2c4, r3c4; `#08` Surprised; `#12` Surprise |
| Sad | `BrowSad` 0.6, `Blink` 0.45, `MouthFrown` 0.5 | `#28` r1c3; `#08` Sad; `#12` Sadness |
| Worried | `BrowSad` 0.7, eyes open (`Blink` 0.1), wavy small mouth (`MouthFrown` 0.3) | `#28` r2c2 |
| Confused | asymmetric brows (`BrowUp` one side 0.5, `BrowDown` 0.2), mouth pulled to one side | `#28` r2c3; `#12` Confusion |
| Angry | `BrowDown` 1.0, `EyeSquint` 0.5 + `Blink` 0.35, flat pout `MouthFrown` 0.5 | `#28` r2c1; `#08` Angry; `#12` Anger |
| Embarrassed | heavy lids, gaze down-side, blush, `MouthFrown` 0.3 | `#28` r4c3 |
| Sleepy | eyes closed (`Blink` 1.0), head tilted, mouth flat | `#28` r4c1; also r3c1 (labelled "Angry", visually calm-closed) |
| Puff cheeks | cheeks puffed, lips closed (no shared action unit yet) | `#12` Puff Cheeks |

Key observation: **he rarely leaves the heavy-lid state**. Only surprise/curiosity/excitement and the
concentrated stare of `PB S6` open the eyes fully; most other expressions are layered on top of the heavy lid.

## 3. Body language
| Topic | What the references show | Citations |
| --- | --- | --- |
| Standing idle | hands in hoodie pockets (both, or one), weight on one leg, shoulders forward, head down | `#08`, `#29`, `char_C`, `C1` |
| Leaning in | at a table he **leans on it**: hands resting on the rim with fingers curled over the edge (`WT`), or a forearm on the rim (`CW`), or a straight arm with flat palm (`#26` "Leaning & Support"). Upper body tilted toward the object, head forward | `WT f000`–`f120`; `CW`; `#26` |
| Sitting at work | holds the paper with both hands near the table edge, elbows in, back rounded, head down | `PB f004`, `f028`, `f116`, `f146`; `CD` |
| Hands | relaxed half-curled fingers when resting; **reaches into a shared task** with one hand (lifts the paper corner while the girl holds the sheet) | `WT f002`; `PB f038`–`f068` (yellow sleeve, S2), `key/pb_hands050`, `pb_hands062` |
| Full-body action | the only dynamic pose of his own is a loose, off-balance "key animation": one knee up, arms flung out, eyes closed — playful flailing rather than controlled | `#09` Key Animation |
| Technical poses | arms raised, bent over, walk, kneel, sit (neutral, not acting) | `#19`, `#26`, `#29` validation tiles |

## 4. Timing (measured from video)
| Item | Measurement | Citation |
| --- | --- | --- |
| Blinks (`WT`) | 3 blinks in 121 f: ≈ f020–f025, f060–f065, f081–f084 (closed f082–f083). Total ≈ 4–6 f each (first two ±1 f: the fringe hides the eye). Start-to-start ≈ 40 f and 21 f → ≈ 36 blinks/min in this shot | `strips/wt_boy_eyes_f000-120.jpg` |
| Blinks (`PB S1+S3`) | none seen in 71 f sampled every 3 f (a 4–6 f blink could hide between samples only if ≤2 f closed): long low-energy stares are also in character | `strips/pb_boy_face_s1_s3.jpg` |
| Lid level over time | heavy lid holds for the whole of `PB S1` and `S3` (≈ 2.9 s total) with no change of expression | same strip |
| Head motion | very small in `WT` (stays leaning, head down, f000–f120); visible changes are mostly the camera push-in from ≈ f064 | `frames/wt_2fps_*` |
| Shift from bored to engaged | `PB S6`: when the boat sparkles he appears behind the girls with eyes opened and brows down within the first visible frames (≈ f255–f264) and holds that stare to the end (≈ 1.4 s) | `strips/pb_boy_face_s6.jpg` |

## 5. Interaction style
- With props: practical, slightly careless — in `CD` paper scraps lie on the desk between him and the girl and his fold is uneven;
  in `PB S2` he grabs and lifts a paper corner rather than smoothing it (`PB f050`–`f068`).
- With the girl: works **beside** her, joins her task with one hand (`PB S2`), positions himself close to her at the
  tub (`PB S6`). He does not look at her in any reference; attention goes to the object.
- Engagement is shown by **opening the eyes and frowning in concentration**, not by smiling (`PB S6`, `WT f036`).

## 6. Personality reading (supported by §1–§5)
"Easily bored": the default heavy lids, pout and slouch; long unchanging stares at the task (`PB S1/S3`).
"Impatient": joins/takes over a fold by grabbing the paper (`PB S2`), frustrated-looking face over an uneven fold (`CD`).
Both are subtle in the references: he is **low-key**, never shown stamping, sighing visibly or fidgeting.

## 7. Gaps and suggestions (EXTRAPOLATION — not shown in any reference)
- **Fidgets** (not shown): small, low-energy actions in the same spirit — finger tapping on the table rim, shifting
  weight from foot to foot, rolling the head, looking away from the task for 1–2 s, then back. Keep amplitudes small
  and keep the heavy lid; no big gestures.
- **Sigh** (not shown): shoulders rise 2–3 f slower than they fall; mouth stays closed or a short `MouthO` 0.2.
- **Impatience escalation** (not shown): brow lowers (BrowDown 0.3) and blink rate rises after a long wait; he
  reaches into the task (as in `PB S2`).
- **Talking** (not shown): he never speaks in the references. Suggest small jaw opening (`JawOpen` ≤ 0.4) with heavy
  lids kept, few hand gestures.
- **Reacting to the girl** (not shown): glance with eyes only (head stays), short hold (≤ 12 f), back to the object.
- **Walking/running acting** (only technical poses in `#19`, `#29`): suggest a loose, slightly dragging walk with
  hands in pockets as idle variant.
- **Laugh, anger escalation, crying**: faces exist (`#28`, `#12`) but no timing; use the global envelope in
  `VISUAL_TARGET.md`.
