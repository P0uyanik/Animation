# T-137 F2: boy, clearer noticing reaction and mouth shapes at shot size

Two separable parts:
1. `content/emotions/boy_interested.emotion.json`: EyeWide 0.8 -> 1.0, BrowDown 0.5 -> 0.3, MouthO 0.25 -> 0.3
   (JawOpen unchanged). On e910 f47-80: peak EyeWide 0.38 -> 0.45, BrowDown 0.19 -> 0.11, MouthO 0.09 -> 0.11.
2. `boy_yellow_hoodie.face.override.json` (on 2.2.0, opt-in): EyeWide lid travel 30 -> 40 deg; mouth wider
   (half width 8.5 -> 11.5 mm), darker and thicker mouth line, jaw 9 -> 15 deg, larger MouthO.

Profile intensity (`content/personality/boy_yellow_hoodie.json`) is NOT changed: any value above 0.6 also changed
his head turn in f51-83 (he turns to the girl later) and his reach arm, so it is not a face-only change.

Evidence:
- `e910_f47-80_before_after.jpg`: boy crop x3 at f47/56/64/72/80, rows before / emotion only / emotion + override
  (640x360, 12 spp, all 34 frames rendered under `build/T-137/f2/`, not committed).
- `e910_f68_full_frames.jpg`: full frames, same three columns.
- `mouth_shot_size.jpg`: mouth shapes at shot size (1.7 mm/px, x2), 2.2.0 vs override.
- `pupils.csv`: readability.py pupil px per eye, 85/16 in both (rest eye unchanged).

Tests: tests/acting 33 passed; test_expressions_r3 68/68; test_face_r5 14/14.

Open issues:
- The emotion-only change is hard to see at shot size; the lid lift only reads clearly with the override.
- The mouth is still small at shot size (about 9 px wide); MouthO shows a pale tooth dot; MouthO + JawOpen pulls
  the chin (already in 2.2.0).
- The override changes his rest mouth slightly (wider), so it needs the owner's look against the character refs.
