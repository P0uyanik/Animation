# Girl (`girl_auburn_bun_glasses`): reference behaviour guide (T-053a draft, 2026-11-17)

Owner brief: **cheerful, intelligent**. Only what the references show; citation keys in
[REFERENCE_INVENTORY.md](../REFERENCE_INVENTORY.md). Anything not shown is in §7 and marked **EXTRAPOLATION**.
Evidence: [contact sheet](../../evaluation/characters/T-053a/contact_girl.jpg) and the strips in
[T-053a](../../evaluation/characters/T-053a/README.md). The white-haired girl in the same videos is a different
character; her behaviour (clasped hands, `PB S6`) is **not** used here.

Face-control vocabulary: shared action units of `pipeline/charsys/face_library/expressions.json`. Weights are
visual **ESTIMATES** (0–1).

## 1. Appearance cues that carry the personality
| Cue | What the references show | Citations |
| --- | --- | --- |
| Open, round eyes | Large brown irises, upper lid at or just above the top of the iris (no lid overlap at rest), highlights visible; the glasses frame them and enlarge the read | `char_B`; `ref_30` turnaround; `ref_34` Neutral; `ref_45` Neutral; `WT f000`–`f010` |
| Raised, arched brows | Thin brows high above the glasses rim, gentle arch | `char_B`; `ref_34` Neutral; `ref_30` Neutral |
| Mouth | Rest = **closed soft smile** (corners slightly up); frequent open smile with upper teeth and tongue visible | rest: `ref_34` Neutral, `WT f110`; open: `char_B`, `lineup`, `ref_30`, `PB f258`–`f288` |
| Cheeks | Soft blush, cheeks rise with the smile | `ref_34` Smile; `char_B` |
| Posture | Upright, chest open, arms relaxed close to the body, feet together/slightly apart; slight head tilt in several poses | `char_B`; `lineup`; `ref_46` wave; `#09` girl Animation |
| Attention | Looks **at the object being worked on** and leans toward it; when explaining, keeps looking at the object while pointing | `WT f022`–`f060`; `CD`; `CW`; `PB S1/S3/S6` |

Reading: alert, open, warm. Her eyes are never heavy-lidded at rest — the visual opposite of the boy.

## 2. Expression catalogue
| Expression | Description for face controls (ESTIMATE weights) | Citations |
| --- | --- | --- |
| **Neutral / resting** | eyes open (no Blink), brows slightly up (`BrowUp` 0.15), closed smile `MouthSmile` 0.25 | `ref_34` Neutral; `WT f110`; decision in the reference index |
| Happy (signature) | open smile `MouthWide` 0.6–0.8 (upper teeth + tongue), cheeks up, eyes open or slightly narrowed by the cheeks (`EyeSquint` 0.2) | `char_B`; `ref_30` Neutral/Happy tiles; `lineup`; `ref_46`; `PB f258`–`f288` |
| Smile (closed) | `MouthSmile` 0.6, cheeks up, lower lids up slightly | `ref_34` Smile; `ref_45` Smile |
| Wonder / "oh!" (seen in video) | `EyeWide` 0.4–0.6, brows up 0.4–0.5, small round mouth `MouthO` 0.5–0.6; hand to the chin | `WT f000`–`f012`; `key/wt002` |
| Explaining / talking | eyes wide and on the object, brows up 0.3, mouth cycling between `MouthO` 0.3–0.6 and nearly closed | `WT f020`–`f052` (`strips/wt_girl_eyes_f020-080.jpg`) |
| Focused at work | eyes looking down (lids follow gaze: upper lid lowered ≈ 0.3 by the downward look, not boredom), brows level, mouth closed neutral-to-soft-smile | `CD`; `PB f004`, `f028`, `f116`, `f146` |
| Delighted (reaction) | leaning forward, `MouthWide` 0.7, `EyeWide` 0.3, brows up 0.5, gaze on the object | `PB f258`, `f272`, `f287` |
| Wide-open / surprise | `EyeWide` 0.8, brows up 0.8, `MouthO`/`JawOpen` 0.4–0.6 | `ref_34` Wide-Open, Surprise ×2; `ref_45` Surprise ×2; `ref_30` Surprised (shape only, see conflicts) |
| Laugh | eyes closed as arcs, `MouthWide` 0.9 | `ref_34` Laugh, Mouth Open |
| Squint | eyes nearly closed, curved, small smile | `ref_34` Squint |
| Sad | `BrowSad` 0.6, eyes half-lowered, `MouthFrown` 0.4 | `ref_34` Sadness; `ref_45` Sad; `ref_30` Sad (shape only) |
| Frown | `BrowDown` 0.4, `MouthFrown` 0.4 | `ref_34` Frown ×2 |
| Angry | `BrowDown` 1.0, eyes narrowed, mouth flat/down | `ref_34` Anger; `ref_30` Angry (shape only) |
| Confusion | brows asymmetric, mouth flat-sideways | `ref_34` Confusion |
| Blink / one eye closed (wink) | `Blink` 1.0; `Blink.L` / `Blink.R` 1.0 | `ref_34` Blink, Left/Right Eye Closed; `ref_45` Eyes Closed |

Key observation: her expressions are driven by **brows up + eyes open + mouth** — positive valence dominates every
scene reference; the negative faces exist only as rig tiles.

## 3. Body language
| Topic | What the references show | Citations |
| --- | --- | --- |
| Thinking gesture | right hand raised to chin/upper chest, fingers loosely curled, index near the lips | `WT f000`–`f012`; `key/wt002` |
| Pointing / explaining | leans forward over the table, right arm extended down toward the object, **index finger pointing**, other fingers curled; held while she talks | `WT f022`–`f060`+; `CW` (same gesture in the still); `key/wt036` |
| Careful handwork | both hands flat on the sheet, fingers together, pressing/smoothing the crease; holds the finished boat with fingertips on both sides; places it on the water with both hands, lowering slowly, then opens the fingers and lets go | `PB f032`–`f110` (S2); `PB f151`–`f190` (S4); `CD`; `key/pb_hands*` |
| Holding / reading | holds an open book at chest height with both hands, looking into it | `ref_44` §4 |
| Offering | extends one arm to hand an object over | `ref_44` §4 |
| Leaning at the tub | leans in with both hands gripping the rim, shoulders forward | `PB f242`–`f288` |
| Waving | one hand raised to shoulder height, palm out, smile | `ref_46` |
| Walking | upright, light step, arms swinging, smiling, slight head tilt | `#09` girl Animation; `ref_46`; `ref_45` walk/run/jump; `ref_36` |
| Rest pose | arms relaxed by the sides, close to the body | `char_B`; `lineup`; `C1` |

## 4. Timing (measured from video)
| Item | Measurement | Citation |
| --- | --- | --- |
| Blinks (`WT`) | 4 blinks in 121 f: f015–f019 (closed f016–f018, 5 f total), f054–f057 (4 f), f079–f085 (closed f080–f084, ≈7 f, during a downward head/gaze shift), f113–f115 (3–4 f). Start-to-start 39, 25, 34 f (mean ≈ 33 f = 1.4 s; ≈ 48/min in this shot) | `strips/wt_girl_eyes_f000-120.jpg`, `strips/wt_girl_eyes_f020-080.jpg` |
| Blink placement | two of four blinks coincide with a **change of action**: f016 during the hand-from-chin → reach transition; f080–f084 with the head/gaze dropping | same + `strips/wt_girl_reach_f004-060.jpg` |
| Hand to chin hold | f000 → ≈f012 (≥ 12 f / 0.5 s; starts before the clip) | `strips/wt_girl_reach_f004-060.jpg` |
| Reach to point | hand leaves the chin ≈ f012–f014, arm extended and pointing by ≈ f022: **≈ 8–10 f** (0.35–0.42 s), no visible overshoot at 2 f sampling | same strip |
| Point + talk hold | pointing held f022 → ≈ f060+ (≥ 38 f / 1.6 s) while the mouth moves | same strip; `frames/wt_2fps_03`–`05` |
| Settle to smile | by ≈ f100–f120 upright, arm down, closed soft smile | `key/wt110`; `frames/wt_2fps_09`, `_10` |
| Placing the boat | lowered from f151 to water contact ≈ f175 (≈ 24 f, 1.0 s, slow and even), release/open fingers ≈ f175–f187 (≈ 12 f) | `PB S4`, `key/pb_hands163`, `pb_hands181` |
| Folding | S2 (80 f, 3.3 s) covers flatten → fold → boat formed; hands remain in near-constant contact with the paper | `PB S2` |

## 5. Interaction style
- With props: precise, two-handed, flat-palmed; fingertips for delicate holds; slow controlled placement (`PB S2`,
  `S4`). This is where "intelligent" reads: careful, methodical handwork and explaining by pointing.
- With others: she is the one who **shows and explains** (pointing + talking, `WT`); she leads the task (her hands
  hold the sheet while others help, `PB S2`); she leans in first at the reveal (`PB S6`).
- Reaction to success: immediate, open delight (`PB S6` open smile).

## 6. Personality reading (supported by §1–§5)
"Cheerful": open eyes, high brows, resting soft smile, frequent open smile, upright open posture.
"Intelligent": thinking gesture (hand to chin), explaining by pointing, careful methodical handwork, focus on the
object while working.

## 7. Gaps and suggestions (EXTRAPOLATION — not shown in any reference)
- **Looking at the boy / others** (not shown: she never looks at another character): suggest brief glances
  (12–24 f) with a smile while explaining, then back to the object.
- **Idle at rest** (no idle video): small weight shifts, occasional head tilt, attentive looking around.
- **Thinking pose variants** (only hand-to-chin seen): finger tap on chin, eyes up-and-aside for 8–16 f before an
  "aha" (brows up, `MouthO` → smile).
- **Speech** (talking seen without audio): jaw/mouth shapes need lip sync (dialogue task); keep the brows active.
- **Negative emotions in motion** (only rig tiles): keep them brief; recover to the soft smile.
- **Glasses push** (not shown): a natural "intelligent" gesture, but invent only if the owner agrees.
