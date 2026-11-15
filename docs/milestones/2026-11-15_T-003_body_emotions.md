# T-003 — A2 Body Emotions (2026-11-15)

**Status:** implemented and tested on branch `t-003-body-emotions` (from `main` ae07b5f). Awaiting Supervisor and
owner review. Nothing is approved or published. Format and usage: `docs/EMOTIONS.md`.

## Implemented
- `plush.emotion/1` (`engine/scene/emotion.{h,cpp}`): face mix of engine expression names, posture clip + mask,
  optional gesture (offset, blends, optional face accent), timing (onset, hold, release, smooth/linear curve),
  variants as JSON merge patches, unknown fields kept.
- `emotion` action (`engine/scene/actions.cpp`): face → per-frame generated morph keys (track + Σ weight × envelope ×
  intensity); body → tier-1 clip layers (`clip_layers.cpp`: base 0 < emotion 1 < clip actions 2; emotion layers
  blend in reference space so intensity scales the deviation exactly); crossfade of consecutive emotions over
  (release + onset); one warning per missing morph per character and emotion.
- Library `content/emotions/`: happy (+laugh), sad (+cry), angry, surprised, confused (shrug), afraid,
  sleepy (yawn), curious. Clips `content/clips/emo_*` (10) and `gest_*` (2) from
  `pipeline/clips/make_emotion_clips.py` (T-002 mannequin and exporter).
- Test shot `episodes/e902_emotion_test/shots/s010` (`pipeline/clips/make_emotion_shot.py`): both characters,
  the 10 emotions in sequence with crossfades, looking at the camera, then a layering segment (emotion + walk +
  look + wave). Blinks are disabled in this shot (`blinkInterval` 100 s) so faces are judged at the peaks.
- Tests: `pipeline/clips/test_emotions.py` (AC2–AC6), `tests/test_emotions.cpp` (format, library).

## Results (`docs/evaluation/animation/T-003/emotion_measurements.json`)
- AC2: at each peak, face weights − definition ≤ 2.4e-8; body vs the posture clip ≤ 1.7e-6°; boy vs girl
  ≤ 5.1e-5° (limit 2.0°).
- AC3: intensity 0.5 face error 0; body deviation ratio 0.49999–0.50000 on 152 role samples (limit ±5 %).
- AC4: 22 entry/transition/exit windows, worst 0.89 × the limit (1.25 × interior max), max 6.7°/frame; each
  emotion alone ≤ 10.7°/frame; entry/exit vs the underlying pose ≤ 1.7e-6°, face 0.
- AC5: walk keeps hips/legs/root (0°, 0 m); the wave keeps its roles (4.8e-5°); gaze unchanged (0°); reaching
  hand unchanged (5e-7 m); hand-keyed head wins (0°); the emotion stays visible on the torso during the walk.
- AC6: boy warnings exactly the unresolved names (also when played twice); other morphs unchanged; girl none.
- AC7: s010 bakes of e000_pilot, e900_workflow_test, e901_clip_test byte-identical with `main`.
- AC9: `ctest` 4/4 (OIDN 2.3.3), `plush_tests` 43/43, `test_export_engine` 8/8, `verify_charsys`,
  `test_run_shot_workflow`, `test_clip_pipeline`: all pass.

## Visual evidence (`docs/evaluation/animation/T-003/`)
`contact_sheet.png` (boy and girl × neutral + 10 emotions, 320×180, 16 samples), `faces_girl_vs_ref34.png`,
`faces_boy_vs_ref28.png` (640×360 crops beside the reference tiles).
- Readable: happy, laugh, surprised (both); confused (head tilt, shrug), afraid (guarding arms), angry (bent arms,
  lean), sad/cry (slump) through the body.
- **Open issue:** whenever the head pitches down, both characters' eyes render closed in Blender, although the bake's
  Blink weight is 0 and the eyes aim at the camera; level/up head poses render open. Cause not investigated
  (render / master side, protected). It hurts the face reading of sad, cry, angry, afraid, sleepy and curious.
- The boy (1.0.0) shows only smile, brow-down, jaw and blink; the girl is unclothed and bald (M4/M5 not built).

## Decisions and assumptions
- Face names: engine names where they exist; face-library preset names (`Worried`, `WideOpen`, `Curious`) where
  the engine has none, through the existing resolution fallback (no face-library change).
- Variants live in their parent file and are played as `name/variant`.
- Crossfade = release + onset (keeps transitions within the AC4 limit for any pair of postures).
- Emotion clip root motion is not used (postures have none).
