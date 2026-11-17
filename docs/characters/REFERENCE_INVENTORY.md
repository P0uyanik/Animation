# Reference inventory for behaviour and expression (T-053a, 2026-11-17)

Every owner reference that can carry personality, with what it shows about **behaviour** (not construction).
Frame numbers are 0-based at 24 fps. Extracted frames live in
[`docs/evaluation/characters/T-053a/`](../evaluation/characters/T-053a/README.md).

Citation keys used in all T-053a documents:

| Key | Meaning |
| --- | --- |
| `WT fNNN` | `docs/references/video_watertable.mp4`, frame NNN (0–120) |
| `PB fNNN` | `docs/references/video_paperboat.mp4`, frame NNN (0–288); shot `S1`–`S6` (cuts below) |
| `#NN` | boy pipeline sheet `docs/references/boy_pipeline/NN_*.webp` (e.g. `#28`) |
| `ref_NN` | girl upload `assets/characters/girl_auburn_bun_glasses/references/uploads/ref_NN.webp` |
| `C1`, `CD`, `CW` | `classroom_1.webp`, `classroom_drawing.webp`, `classroom_watertable.webp` |
| `char_C`, `char_B`, `lineup` | `char_C_boy.jpg`, `char_B_brown_hair.webp`, `lineup.webp` |

## Who is who
- **Boy** (`boy_yellow_hoodie`): black felt hair, yellow hoodie, charcoal backpack. Unambiguous everywhere.
- **Girl** (`girl_auburn_bun_glasses`): brown/auburn curls, high bun with pink flowers, round glasses, brown vest,
  sage shorts. `char_B` is the original render of the same design (index name `girl_brown_glasses`, an older engine
  character) and is used here for expression and posture only.
- **White-haired girl** (blue dress, blue bow): a third character, **not** analysed. She appears in both videos and
  most group images; her behaviour (e.g. clasped hands in `PB S6`) is never attributed to the girl.
- Sheet labels are unreliable: the girl's `ref_30`/`ref_36` and the boy's `#08` are all titled "Character A";
  identity is taken from appearance only.

## Videos

| File | Shots (cut frames measured with ffmpeg scene detection) | Boy | Girl |
| --- | --- | --- | --- |
| `video_watertable.mp4` (5.04 s, 121 f, one shot, slow push-in/tilt from ~f064) | single shot at a water table | yes: front-left, leaning on the rim, watching | yes: centre, gesturing, pointing, talking |
| `video_paperboat.mp4` (12.04 s, 289 f) | S1 f0–31 desk ensemble · S2 f32–111 hands folding · S3 f112–150 desk ensemble · S4 f151–190 hands placing boat · S5 f191–238 boat + sparkle insert · S6 f239–288 reaction at the tub | S1, S3 face; S2 right-hand (yellow sleeve) helps fold; S6 face (behind, centre) | S1, S3 face; S2 centre hands (cream sleeves, brown vest) fold; S4 her hands place the boat; S6 face and hands on the rim |

S5 shows no character. `docs/references/visual_target/frames/*` are older 1 s samples of the same videos (used
by `VISUAL_TARGET.md`); this study uses its own extraction.

## Still images: behaviour content

| Reference | Character | Behaviour content |
| --- | --- | --- |
| `char_C` | boy | identity authority: heavy lids, pout, one hand in pocket, slight slouch |
| `#08` | boy | turnaround with hands in pockets; face tiles Neutral/Happy/Sad/Surprised/Angry; T-pose keeps the heavy lids |
| `#09` (= `ref_31`, same SHA-256) | all three | boy "Key Animation" (one leg up, arms flung out, eyes closed); boy face strip (3 heavy-lid + 3 open-eye variants); girl "Animation" (walking, smiling, arm swing) |
| `#10` (= `ref_32`) | all three | rig screenshot, neutral poses only |
| `#11`, `#12` | boy | face topology and blendshape matrix (Neutral, Blink, Squint, Wide-Open, Smile, Frown, Mouth Open, Laugh, Surprise, Sadness, Anger, Confusion, Puff Cheeks) |
| `#18` | boy (generic hand) | hand pose set: relaxed, open, fist, half-closed, pointing, pinching, peace, holding paper boat, pencil, cup, releasing |
| `#19` | boy | arms raised, bent over, sitting, walking, kneeling (wireframe, neutral face) |
| `#26` | boy | grasp types, pick-up/release sequence, leaning on a table with a flat palm, sitting |
| `#28` | boy | 16-tile expression library (three-quarter views) — main face authority |
| `#29` | boy | canonical turnaround, hands in pockets; "no mesh collisions" tile: head down, hunched |
| `#20`–`#25`, `#27` | boy | construction only (skeleton, hair, clothing, materials, UV, deformation): no behaviour |
| `ref_30` | girl | turnaround (A-pose, open smile), face tiles Neutral/Happy/Sad/Surprised/Angry |
| `ref_34` | girl | face rig + 18-tile blendshape matrix — main face authority |
| `ref_36` | girl | body poses: neutral standing, arms raised, sitting, walking, running, squatting |
| `ref_44` | girl | grasp types, pick-up sequence, holding a book, handing an object over, leaning on a table |
| `ref_45` | girl | facial tests (neutral, smile, surprise ×2, sad, eyes closed), walk/run/jump/landing |
| `ref_46` | girl | walk, sit on chair, wave |
| `ref_35`, `ref_37`–`ref_43` | girl / generic | construction only; `ref_37` outlines the white-haired girl |
| `char_B` | girl | original render: open smile, upright, arms relaxed |
| `C1` | all three | standing around a paper boat on the floor |
| `CD` | all three | folding paper at a desk |
| `CW` | all three | at the water table (still version of the video set-up) |
| `lineup` | all three | standing line-up: girl open smile, boy heavy lids and pout |
| `char_A_white_hair` | white-haired girl | analysed in T-057: see `docs/characters/girl_white_hair_blue_dress/REFERENCE_BEHAVIOUR.md` |

Text documents: `VIDEO_BENCHMARKS.md` (summary: "the girl talks and gestures, the boy leans in" — confirmed by the
frames below), `VISUAL_TARGET.md` (global motion envelope: blink 4–7 f, holds 8–18 f, anticipation 5–10 f; those
are ESTIMATES for all characters, refined per character here). `MOCAP_*.md` contain no character behaviour.

## Known conflicts in the references
Resolved by the owner 2026-11-17: (1) girl's eyes are **brown**; (2) girl's neutral mouth is **closed with a gentle smile**;
boy's impatience stays **subtle, calm and low-energy** as in the references.

1. `ref_30` face tiles **Sad, Surprised, Angry** show **blue irises** (and Surprised a different face shape): they
   look borrowed from the white-haired girl. Use their brow/mouth shapes only; her irises are brown everywhere else.
2. `ref_30` "Neutral" tile and the turnaround show an **open smile**; `ref_34` "Neutral" and the owner-approved
   index decision use a **closed soft smile**. Neutral = closed soft smile; open smile = Happy.
3. `#28` has duplicated/misspelt labels: row 3 "05. ANGRY" shows calm closed eyes, "07. COLFITED" is a heavy-lid
   flat-mouth face (reads as unimpressed/conflicted). Tiles are cited by row/column, labels quoted as printed.
4. Boy's hands: `char_C` has his right hand hanging, left in pocket; `#08`/`#29`/`C1` show both hands in pockets.
   Both are valid idle variants.
