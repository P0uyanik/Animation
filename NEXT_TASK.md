# Next task

1. **Owner decision (waiting):**
   - H26 hair and F02 face stay experimental candidates. Nothing is published.
   - Improvement requests on record:
     - H26: irregular, asymmetric crown; more fibrous look.
     - F02: neutral closure, flatter lids, cheek and eye coupling, expressive JawOpen.
2. **Proposed next engineering step (needs your go-ahead: small engine changes):** make the four engine assumptions
   generic, each in a few lines with its own test on both packages:
   - walk step length from leg length;
   - hand palm and finger axes from the hand's rest geometry or the profile;
   - blink via a morph named in the package;
   - per-character expression name map in the package.
3. **Without engine changes:**
   - face expression layer (cheek raise, lower-lid narrowing coupled to Smile; neutral closure; flatter closed
     lids), via `spec.face`, measured with `face_test.py`;
   - H26 irregularity variants (asymmetric crown spread, dominant tuft, fibre detail), 8-view review;
   - minimum fixes for the boy-specific modules listed in `docs/CHARACTER_REUSABILITY.md`.
