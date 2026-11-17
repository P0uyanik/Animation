# White-haired girl (`girl_white_hair_blue_dress`): reference behaviour guide (T-057 draft, 2026-11-17)

Owner brief (2026-11-17): **a little goofy, not very bright, bubbly and cheerful**. This guide records what her
references show first; anything they do not show is in §7 and marked **EXTRAPOLATION**. Evidence:
[contact sheet](../../evaluation/characters/T-057/contact_her.jpg) and the strips in
[T-057](../../evaluation/characters/T-057/README.md). Construction and gap analysis: [SYSTEM_GAPS.md](SYSTEM_GAPS.md).

Citation keys: `w01`–`w15` = her uploads `assets/characters/girl_white_hair_blue_dress/references/uploads/NN_*.webp`
(e.g. `w04` = `04_facial_rig_expression_blueprint.webp`); tiles by the ids in `references/reference_index.json`
(e.g. `m04_pucker`, `f14_e8_side_glance_smile`). `WT fNNN`, `PB fNNN`, `C1`, `CD`, `CW`, `lineup` as in
[REFERENCE_INVENTORY.md](../REFERENCE_INVENTORY.md) (0-based frames, 24 fps). `w01` is the same file as
`docs/references/char_A_white_hair.webp`; `w03` = the girl's `ref_32` = the boy's `#10`; `w06` = the girl's `ref_37`.

Face-control vocabulary: the shared action units of `pipeline/charsys/face_library/expressions.json`. Weights are
visual **ESTIMATES** (0–1).

## 1. Appearance cues that carry the personality
| Cue | What the references show | Citations |
| --- | --- | --- |
| Very large, round eyes | Blue irises ≈ 47 px across in a 270 px wide face, wider set than the girl's (eye spacing / ear width 0.42 vs 0.365); upper lid above the iris at rest; one big and one small highlight; thick dark upper lash line with 3–4 outer flicks | `w01`; `m04_neutral`; `f14_e1`; `measurements.json` |
| Brows | thin, light brown, high; mostly hidden under the fringe, so the **eyes and mouth carry the expression** | `m04_neutral`, `m04_anger`, `f14_e4_sad` |
| Mouth | small; at rest **either** a small open smile with upper teeth (`w01`, `w10`, `w15` neutral, `lineup`) **or** a closed soft smile (`s02_face_neutral`, `m04_neutral`, `f14_e1`, `p13_face_tests` neutral): open conflict §8.2 | see cells |
| Lips parted while watching | in both videos her mouth hangs slightly open while she watches the boat: an "agape", wide-eyed look | `WT f000`–`f018`, `f066`–`f084`; `PB f249`–`f288` |
| Cheeks | strong round blush, cheeks rise in smiles and laughs | `w01`; `m04_smile`, `m04_laugh`; `f14_e3_laugh` |
| Silhouette | round head, two pom-pom buns ("ears"), soft fuzzy halo of off-white felt, bow on her right side; ≈ 2.7 heads tall incl. buns | `w01`, `w02`, `w07`, `measurements.json` |
| Posture | upright, feet together, arms hanging straight and close to the body, hands relaxed and slightly forward | `w01`; `s02_front`; `c15_front`; `C1`; `lineup` |
| Attention | watches the object or **the other children's work** (not their faces); leans in to watch rather than to act | `WT` (boat); `PB f000`–`f031`, `f112`–`f150` (the girl's paper); `PB S6` (boat) |

Reading: sweet, wide-eyed, open-mouthed wonder; a doll-like, naive design. Nothing in the references is
heavy-lidded or sly at rest (contrast with the boy).

## 2. Expression catalogue
Sheets: `w04` (15 labelled tiles), `w14` (11 unlabelled expressions e1–e11 + 10 mouths m1–m10, names are readings),
`w02` (5 labelled tiles), `w13` (4 tests).

| Expression | Description for face controls (ESTIMATE weights) | Citations |
| --- | --- | --- |
| **Neutral / resting** | eyes fully open (no Blink), brows level-high, `MouthSmile` 0.2; mouth open/closed pending (§8.2) | `m04_neutral`; `f14_e1`, `f14_e7`; `s02_face_neutral`; `w01` (open variant) |
| Happy (signature) | open smile with upper teeth `MouthWide` 0.5–0.7, `MouthSmile` 0.6, cheeks up, eyes open | `w01`; `s02_face_happy`; `w10`; `w15` wave; `p13_face_tests` "High smile" |
| Happy, eyes closed | eyes closed as upward arcs (`Blink` 1 + `EyeSquint` 0.5), closed smile `MouthSmile` 0.7 | `f14_e2_happy_eyes_closed`; `m04_squint` |
| Laugh | eye arcs closed, open mouth with teeth/tongue `MouthWide` 0.8 | `m04_laugh`, `m04_mouth_open`; `f14_e3_laugh` |
| Wonder / "ooh" (seen in video) | `EyeWide` 0.3–0.5, small round mouth `MouthO` 0.4–0.6 or parted lips `JawOpen` 0.1–0.2, gaze on the object | `PB f249`–`f288` (with clasped hands); `WT f000`–`f018`; `f14_e9_wide_eyes_o`; `f14_m4_round_o` |
| Surprise | `EyeWide` 0.8, `MouthO` 0.5–0.7 | `m04_surprise`; `m04_wide_open` (shown with mesh overlay); `f14_e5_surprised_o`; `s02_face_surprised`; `p13_face_tests` |
| Side glance + smile | eyes turned to one side, closed smile — the most "mischievous/goofy" tile | `f14_e8_side_glance_smile` |
| Dozy / half-lidded | upper lids at mid-iris (`Blink` 0.5), flat mouth — a sleepy, spacey look | `f14_e11_half_lidded` |
| Eyes closed, calm | `Blink` 1, faint smile (content, dreamy) | `f14_e10_eyes_closed_calm`; `m04_blink_both` |
| Pucker | small pursed lips (no action unit: see SYSTEM_GAPS) | `m04_pucker` |
| Confusion | flat brows, small downturned mouth; lopsided mouths (one corner up or down) | `m04_confusion`; `f14_m8_lopsided_flat`, `f14_m10_lopsided_smile` |
| Sad | `BrowSad` 0.6–0.8, `MouthFrown` 0.3–0.5, eyes open and glossy | `m04_sadness`, `m04_frown`; `f14_e4_sad`; `s02_face_sad` |
| Worried / upset | `BrowSad` 0.8, mouth open and downturned (`JawOpen` 0.2, `MouthFrown` 0.5) | `f14_e6_worried_open`; `f14_m7_open_down_eh` |
| Angry | `BrowDown` 0.8 (brows visible through the fringe), small frown, eyes open | `m04_anger`; `s02_face_angry` |
| Blink | both eyes; `w04` "BLINK L"/"BLINK R" also close **both** eyes (§8.4): no wink is shown | `m04_blink_both`, `m04_blink_l`, `m04_blink_r`; `p13_face_tests` "Blinking" |
| Lip-sync mouths | m1 closed flat, m2 closed smile, m3 open smile, m4 round O, m5 frown, m6 small "ah", m7 open down "eh", m8 lopsided flat, m9 deep frown, m10 lopsided smile | `f14_m1`–`f14_m10` |

Key observation: positive and wondering faces dominate every scene reference; the "goofy" shapes the sheets do
provide (side glance, half-lidded, pucker, lopsided mouths) appear **only as tiles**, never in a scene.

## 3. Body language
| Topic | What the references show | Citations |
| --- | --- | --- |
| Watching, leaning on the rim | both hands on the water-table rim, shoulders forward, head tilted down toward the boat, lips parted; she stays there the whole shot | `WT f000`–`f120` (`strips/wt_her_body_every6.jpg`); `CW` |
| Watching others work | sits with forearms on the desk, hands folded/resting together, eyes on the girl's paper; does not fold herself | `PB f000`–`f031`, `f112`–`f150` (`key/pb000.jpg`, `key/pb120.jpg`); `CD` |
| Helping hold | a blue-sleeved hand (hers: she is the only one in blue) rests flat on the corner of the sheet while the girl folds, then touches the boat's side | `PB f044`–`f110` (`strips/pb_her_hand_s2_f032-f110.jpg`) |
| Delight | hands clasped with interlaced fingers just under the chin, mouth opening to a small "o"/smile, eyes wide on the sparkling boat | `PB f239`–`f288` (`strips/pb_her_s6_f239-f288.jpg`) |
| Waving | right hand raised above the shoulder, palm out, open smile, slight head tilt | `c15_animation` (wave) |
| Showing an object | seated, holds a small blue object up at shoulder height in her right hand, looks out with a soft smile | `c15_animation` (last tile) |
| Walking | small steps, head tilted, smile | `c15_animation` (walk); `t05_poses` walking (technical) |
| Technical poses | arms raised in a V, sitting with hands on knees, kneeling, running, deep knee bend, torso twist (rig tests, neutral or blank faces) | `t05_poses`; `p13_deform` |
| Rest pose | arms straight by the sides, feet together | `w01`; `c15_front`; `C1`; `lineup` |

## 4. Timing (measured from video, 24 fps, ±1 f)
| Item | Measurement | Citation |
| --- | --- | --- |
| Blinks (`WT`) | 3 in 121 f: f019–f022 (closed f020–f021), f056–f059 (closed f057–f058), f106–f110 (closed f108–f109): 4–5 f each, 2 f closed. Start-to-start 37 and 50 f (≈ 33/min) | `strips/wt_her_blinks_f015-f114.jpg` |
| Blinks (`PB`) | S1 f004–f008 (closed f005–f007); S3 f122–f127 (closed f124–f126); S6 f245–f247 (closed f246; eyes cropped by the frame edge before f244). One per shot (32, 39, 50 f shots) | `strips/pb_her_blinks_s1_s3.jpg`, `strips/pb_her_s6_blink_f240-f251.jpg` |
| Blink placement | WT f019 as her parted mouth closes (f018–f020); PB f245 right before the mouth opens into the "ooh" (f248–f251): blinks mark an **expression change**. WT f106 has no visible trigger | same strips; `strips/wt_her_faces.jpg` |
| Lips parted | WT f000–≈f018 and ≈f066–≈f084 (≈ 19 f each, ±2 f: small face at that scale); closed soft mouth in between and at the end (f120) | `strips/wt_her_faces.jpg`, `key/wt000.jpg`, `key/wt120.jpg` |
| Holds | leaning on the rim ≥ 121 f (whole WT); hand resting on the paper ≈ f044–f086 (≈ 42 f) before it moves to the boat; clasped hands ≥ 50 f (whole S6) | strips above |
| Motion amount | very small in all shots: head and eyes move a little, hands stay put | all video strips |

## 5. Interaction style
- With props: gentle and **passive**: rests a flat hand on the paper to help, touches the finished boat; she never
  folds, points or places (`PB S2`). In stills she holds up a small object to show it (`c15_animation`).
- With others: she is the **follower/onlooker** — watches the girl's work and the boat with an open mouth; she
  never leads, points or explains (the girl does, `WT`). She never looks at another character's face (both videos).
- Reaction to success: clasped hands under the chin, wide eyes, small "o"/smile (`PB S6`): delight is shown with the
  hands and mouth, not with big body motion.

## 6. Personality reading (supported by §1–§5)
- **"Bubbly, cheerful"**: open smile in the identity render and most full-body stills (`w01`, `w10`, `w15`,
  `lineup`), cheek-raising smiles/laughs (`w04`, `w14`), the wave, clasped-hands delight (`PB S6`).
- **"A little goofy, not very bright"** — what the references actually show is subtle and comes from the
  design and the face, not from slapstick: parted lips / mouth agape while watching (`WT`, `PB S6`); very large,
  wide-set eyes and wide-eyed wonder; the onlooker/helper role (watches, holds, does not lead: `PB S1–S3`, `WT`);
  the available comic tiles (side glance, half-lidded, pucker, lopsided mouths: `w04`, `w14`). This is an
  **interpretation (ESTIMATE)**; none of the references shows her making a mistake or a clumsy move.
- **Tempo**: in both videos she is the stillest of the three. Bubbliness in motion is therefore not measured
  (§7).

## 7. Gaps and suggestions (EXTRAPOLATION — not shown in any reference)
Keep these within the references' calm, small motion; they add colour, they must not turn her into a slapstick
character (owner to confirm the intensity, as for the boy in T-053a).
- **Delayed "getting it"** (not very bright): 4–8 f later reaction than the others, a blink, then the "ooh"
  (the measured blink-before-expression pattern), occasionally a small double-take (look away, look back).
- **Puzzled beat**: head tilt 8–12° + `f14_e8` side glance or `m04_confusion` + `m04_pucker` for 12–24 f, then a
  bright smile (she gives up and smiles).
- **Bubbly bounce**: small up-down bob (≤ 0.01 H) on happy beats, slight overshoot (≈ 8 %) on head turns, a little
  rise on the toes when delighted; giggle = `m04_laugh` for 6–10 f with shoulder bounce.
- **Spacey idle**: occasional unfocused gaze up/aside with `f14_e11` half-lids for 24–48 f, then snaps back with
  `EyeWide` (attention span shorter than the girl's).
- **Hands**: clasp-under-chin as her go-to positive gesture; hands folded in front at rest; fiddling with a lock
  of hair or the bow (not shown).
- **Speech**: her mouth shapes are in `w14`; no audio reference exists (dialogue task).
- **Single-eye wink**: not shown (both "BLINK L/R" tiles close both eyes); do not invent unless the owner wants it.

## 8. Reference conflicts
Resolved by the owner 2026-11-17 (see docs/process/OWNER_DECISIONS.md): bow; neutral = closed soft smile (parted while
watching, open small smile = presentation/Happy); goofiness subtle; cable-knit dress and fleece boots.

1. **Hair accessory: bow vs flower.** A two-loop felt **bow** with two tails on her right side (`w01`, `w02`, `w03`,
   `w04`, `w10`, `w12` thumbnail, `w13`, `w14`, `w15`, `WT`, `PB`, `lineup`, `C1`, `CD`, `CW`) vs a **4-petal blue
   flower** at the same place (`w05`, `w06`, `w07` "BLUE FLOWER ACCESSORY", `w08` "Flower Accessory Rig").
   `w10` text says "BOW: felted fibre fabric". Majority, identity render and both videos: bow.
2. **Neutral mouth: open vs closed.** Open small smile with teeth: `w01`, `w10`, `w15` neutral tiles, `lineup`,
   `p13_deform` arm raise. Closed soft smile: `s02_face_neutral`, `m04_neutral`, `f14_e1`/`e7`, `p13_face_tests`
   neutral. Videos at rest: closed (`WT f120`, `PB f000`), parted while watching.
3. **Iris colour.** Her irises are blue in every image of her. The girl's `ref_30` Sad/Surprised/Angry tiles also
   show blue irises (T-053a conflict 1): those tiles look borrowed from this character; no conflict for her.
4. **Blink L / Blink R tiles** (`w04`) close both eyes; no single-eye blink exists in her references.
5. **Skirt surface.** Cable-knit patterned skirt and knit bodice (`w01`, `w02`, `w10` "M_Dress_Knit", `w13`, `w15`)
   vs a plain smooth skirt in the construction sheet (`w09`) and a plain dress in `w11`.
6. **Boots.** Shaggy faux-fur fleece boots with a fluffy cuff (`w01`, `w02`, `w10` "M_Boots_Fleece", `w13`, `w15`)
   vs smooth, clay-like boots in `w09`.
7. **Colours in `w11`** (lavender hair, pink flower, red/blue panel lines) are UV false colours, not a variant.
8. **Labels.** `w02` "Right" is a second left-side view (face points screen-left, no bow); `w05`/`w06` are titled
   "@char_character_b_reference_01", `w10`/`w12` "Character B", `w15` "ASSET ID: @char_character_b", `w02`
   "Character A" (the girl's and the boy's sheets use the same letters): identity from appearance only.
9. **Printed dimensions** ("DIMENSION: 220 cm" `w15`, "3.0m"/"150m" `w07`, ruler numbers `w05`) are inconsistent
   and ignored; scale comes from `w03` (`measurements.json`).
10. **Hands.** `w12` shows generic white felt hands with four fingers and a thumb; her own hands are skin-coloured
    (`w01`, `p13_hands_feet`): the `w12` hands are a generic construction reference.
