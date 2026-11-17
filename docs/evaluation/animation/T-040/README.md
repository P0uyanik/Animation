# T-040: always-on arm-body clearance post-pass: final evidence

**Status: NOT ACCEPTED.** The post-pass works on e904, but **e905 and e906 still have arms inside the body mesh**. Three
older test_clips assertions fail because of the post-pass. Branch `t-040-claude-pose-clearance`.

## What this session changed
- **Performance (kept, exact):** `applyArmBodyClearance` is memoised on the exact bytes of its inputs (model id,
  skeleton, world, side, pin, keepHand, pose, options; thread-local, bounded at 8192 entries). The pass is a pure
  function, so results are bit-identical (the e906 measurement before and after the memo is identical). The ternary
  search no longer evaluates each probe twice. Effect on the slow doctests: hand-over 300 s+ (timed out) → 154 s,
  "hold pulled across" 112 s → 38 s. The full plush_tests run takes about 7 to 8 minutes.
- **Measure tool:** `measure_t040.cpp` takes an optional frame range (`[stride] [first] [last]`).
  `contact_sheet_t040.py` is new.
- **Tried and reverted (2 fix iterations, per the time box):**
  1. Body sections that follow the mesh cross-section (a 16-bin angular radius profile per band instead of the
     ellipse), with the floor at 4 mm, plus interior arm points (resting > 20 mm deep) excluded.
     - It brought the three test_clips poses closer to passing (20.6°→11.0°, −0.827→−0.894, 22.1°→15.8°).
     - It made the IK-ramp doctest fail (step 36.8 > 28.1 mm). A 7 mm floor failed too; an 11 mm floor passed.
     - With 11 mm it still left e906 girl L at −0.9 mm.
     - The full suite then showed **5 interaction doctests broken**, because `sectionGap` is shared with the T-030
       interaction solver.
  2. Refitting sparse bands from torso ≥ 0.5 vertices (legacy test packages). This broke the package-fit doctest
     (band r1 21 mm).

  Both were reverted. **The engine is 2f0d3c8 plus the exact memo** (commit 133b5f5).

## Measurements (mesh-based, `measure_t040.cpp`, every frame, both characters)
How the numbers are measured:
- Mesh distance is rest-relative. The armpit band is reported apart.
- "off" means the post-pass is disabled.
- "max step" is the largest frame-to-frame change of the post-pass's shoulder or elbow correction.

The before and after pose numbers are the same, because the memo changes nothing.

| shot | char/arm | mesh min (mm) | off (mm) | max correction | max step/frame | corr. accel (°/f²) |
|---|---|---|---|---|---|---|
| e904 s010 | girl L | 13.1 | −6.2 | 26.3° | 1.3° | 1.27 |
| e904 s010 | girl R | 15.0 | −18.6 | 33.6° | **12.2° (f9)** | 7.88 |
| e905 s010 | boy L | 15.3 | −11.5 | 17.7° | 0.2° | 0.08 |
| e905 s010 | boy R | **−37.7 (f56)** | −36.9 | 23.1° | **10.4° (f57)** | 12.06 |
| e905 s010 | girl L | 12.5 | −23.1 | 33.4° | 1.0° | 1.09 |
| e905 s010 | girl R | **−1.0 (f56)** | −14.3 | 31.6° | **11.8° (f35)** | 14.6 |
| e906 s010 | boy L | 17.6 | −9.6 | 15.4° | 0.4° | 0.45 |
| e906 s010 | boy R | 7.2 | −8.3 | 9.3° | 4.5° | 4.49 |
| e906 s010 | girl L | **−0.9 (f73–75)** | −22.7 | 33.6° | 6.7° (f73) | 7.05 |
| e906 s010 | girl R | 12.3 | −18.0 | 32.7° | 0.6° | 0.48 |

(e904 s020 gives the same numbers as s010.) Files: `e90{4,5,6}_s010_final.json`.

Acceptance:
- **Minimum distance ≥ 0 mm on the mesh: FAIL.**
  - e905 boy R is −37.7 mm on the mesh (frames 16–25 and 33–58; capsule −78 mm). This is the arm pinned by IK while
    it holds the cup and hands it over: the pinned swing is capped at 0.35 rad and the wrist must stay on the socket.
  - e905 girl R is −1.0 mm (frames 43–65, receiving the cup).
  - e906 girl L is −0.9 mm at frames 73–75: the blouse sleeve puff touches the vest just past the elbow. The capsule
    reads 11 mm there, so the ellipse fit is about 12 mm inside the vest at its front/side corner.
- **Interaction contacts ≤ 5 mm: PASS.** Palm to socket is ≤ 0.0001 mm at the grasp and at both hand-over ends, and
  ≤ 0.0002 mm drift while held (`e905_contacts_final.json`, T-030 tool). No warnings.
- **No prop jumps: PASS.** The parent switches at f17 and f46 move the prop ≤ 0.0012 mm. Prop speed is at most
  17.1 mm/frame and the cup stays upright (cos 1.0).
- **Smooth correction: FAIL in places.** Steps of 10–12° per frame occur where an arm enters or leaves deep
  penetration (e904 girl R f9, e905 boy R f57, e905 girl R f35). Elsewhere the steps are ≤ 1.3°/frame.

## Evidence
- `e906_s010_t040.mp4`: 640×360, 75 frames, Cycles 16 samples with OIDN denoising, rendered on the final engine.
- `e906_t040_contact_sheet.png`: frames 1, 8, 23, 44, 72, 73 and 75, with left and right arm close-ups per character.
  Each close-up is labelled with the mesh distance; red means inside (girl L at f73 and f75).

## Tests (final engine)
- **ctest: 3/4.** The 3 regression tests pass; plush_tests fails.
- **plush_tests: 87/88 test cases, 22149/22152 assertions.** All 3 failures are in "clips: scene playback…" and were
  already failing at 2f0d3c8 (verified by an A/B build):
  - boy vs girl role direction 20.6° (must be ≤ 2°)
  - base-pose arm direction y −0.827 (must be < −0.9)
  - a hand key on upperArm.R changed by 22.1° (must be < 0.01°)

  Measured with the mesh tool, none of these poses is inside the mesh without the post-pass (clearance 0.2–24 mm).
  The post-pass over-corrects them, because the capsules of the legacy test packages (boy 1.0.0, girl m3, which have
  sparse torso weights) are fuller than the mesh. They were not loosened.

## Remaining work (for the next task)
1. Make IK holds and hand-overs avoid the body. The prop path and meeting point should be planned outside the body;
   the post-pass alone cannot do this while the wrist is pinned. This is the e905 −37.7 mm case.
2. Fit the body to the mesh separately from T-030. A post-pass-only section model (a profile or an SDF per torso
   bone) would leave `sectionGap` unchanged for the interaction solver. Its free-stage path search must also stay
   continuous, because the IK-ramp doctest showed jumps below an 11 mm floor.
3. Smooth the entry and exit of deep corrections: per-frame steps of 10–12° occur.
4. Decide what the 3 test_clips expectations should be under the owner rule. These clips and hand keys now get
   corrected; the poses are clear on the mesh, but the capsule fits of the legacy packages are too full.
5. Speed: the post-pass still dominates the interaction compile (a 150 s doctest).
