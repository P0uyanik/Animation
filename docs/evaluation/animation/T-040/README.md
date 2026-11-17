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

---

# T-040r1: arm-body clearance from the real mesh (redesign): results

**Status: NOT READY (blocked).** Branch `t-040-claude-pose-clearance`. The redesign is in place and fixes the three
test_clips cases and the test time. It does **not** meet criteria 2 and 3 on the real shots. On e904, e905 and e906 it
is *worse* than T-040's capsule post-pass. Details and the reasons follow.

## What was built (engine/scene/interaction.{h,cpp} only)
- **`TorsoField`**: a signed distance field of each package's own skinned torso, built at character load. It is
  generic (no character names).
  - Body triangles use the T-040 measurement rule (>= 90 % torso-carried, the hips' leg-carried sides down to the
    pelvis bottom, hair excluded). Packages whose torso skin is shared with the neck also count torso-dominant vertices
    with < 10 % arm weight. Without that, the legacy girl m3 package has no chest at all.
  - Grid: 6 mm. The distance is exact within 3 cm (nearest triangle), and the nearest triangle is swept outwards beyond
    that.
  - The sign follows the T-040 tool: the angle-weighted pseudo-normal (an open boundary counts as outside), and a
    negative sign must be confirmed by 2 of 3 rays hitting the same shell.
  - Per torso bone, a weight curve over height. A world point is mapped to rest space by blending its per-bone rest
    positions, then the field is looked up once.
- **Dense arm surface** (`ArmModel::dense`): one arm vertex per 3 mm cell, about 1,500 to 5,000 per arm. It is used
  by the post-pass only. The 600-point subsample missed the girl's sleeve puffs, which were the deepest points. The
  interaction solver keeps its 600 points, `sectionGap` and `kArmBodyMargin` unchanged.
- **Solver**: still a pure function of the pose, run in fixed rounds (3).
  - Each round takes a direction: the deficit-weighted gradient of the points' gaps (weights fade to 0 at the target).
  - It then finds the smallest angle along that direction where the largest deficit reaches 0, using Newton steps and
    an Illinois bracket.
  - If the deficit stops falling first, the round stops at that local minimum (golden section) and the next round
    continues from there.
  - Margin is 0.4 mm and the C1 band 0.8 mm. These must be this small: the legacy hand-key pose is only 0.2 mm clear on
    the mesh, and it must stay untouched.

### Approaches tried and abandoned (each failed at least twice)
1. **Radial profile** (rays from a per-row centre) with Gauss-Newton or Levenberg-Marquardt over 6 or 4 DOF. Branch
   switching gave 15 to 100 mm wrist jumps per degree. Filling holes linearly, with a 45° slope or with a closing made
   the profile up to 29 mm fuller than the mesh at the legacy boy's open waist sides.
2. **SDF with the per-bone gaps blended** instead of the rest positions. It was noisy, with jumps of up to 17 mm
   between points 3 mm apart. Blending rest positions fixed this.
3. **Direction from the linearised QP** (min |x|² + K Σ max(0, d − Jx)², semismooth Newton). It was worse (e906 girl
   R f1 −12.7 mm) and slower. Reverted.
4. **Ray confirmation against any body layer.** It changed nothing useful. Reverted to the T-040 tool's own-shell
   rule, so the engine and the evidence agree on what is inside.
5. **Legs as field carriers.** No measurable change. Reverted.

## Acceptance criteria
| # | criterion | result |
|---|---|---|
| 1 | per-torso-bone clearance from the package's own skinned mesh, post-pass only, `sectionGap` unchanged | **DONE** (see above). |
| 2 | mesh distance ≥ 0 mm, both arms, both characters, e904/e906 (e905 except pinned wrists) | **FAIL** (table below) |
| 3 | ≤ 2°/frame and bounded acceleration | **FAIL**: up to 12.9°/frame (e906 girl L); boy R e906 3.3°/frame |
| 4 | the 3 test_clips cases pass, expectations unchanged | **PASS**: role direction 2.2e-5°, base-pose arm y < −0.9, hand key < 0.01° |
| 5 | plush_tests and CTest pass; contacts ≤ 5 mm; no prop jumps; doctest ≤ 60 s | **PARTIAL** (list below) |
| 6 | mesh JSON e904/e905/e906, e906 contact sheet | **DONE** (files below) |

Criterion 5 in detail:
- plush_tests: **86 of 88** test cases pass, **22143 of 22152** assertions (9 fail). The two failing cases are T-040's
  own post-pass doctests, listed under "plush_tests failures" below.
- All interaction doctests pass: contacts are within 5 mm and the hand-over prop is continuous.
- Slowest doctest: **51 s**, down from 150 s. The full suite takes about 3 minutes, down from 7 to 8.
- ctest: 2 image regressions fail. **origin/staging fails them identically here** (rmse 0.0464 in this environment,
  which has no OIDN). The post-pass changes none of those poses: max bone offset on vs off is 0.000 mm.

### Mesh distance (T-040 tool `measure_t040.cpp`, unchanged; rest-relative; armpit band apart)
| shot (stride) | char/arm | mesh min (mm) | off (mm) | T-040 capsule pass | max step |
|---|---|---|---|---|---|
| e906 s010 (1) | boy L | **−7.5** (f6–19) | −9.6 | 17.6 | 4.7°/f |
| e906 s010 (1) | boy R | 1.6 | −8.3 | 7.2 | 3.3°/f |
| e906 s010 (1) | girl L | **−18.7** (f75) | −22.5 | −0.9 | 12.9°/f |
| e906 s010 (1) | girl R | **−14.2** (f72) | −17.8 | 12.3 | 12.2°/f |
| e904 s010 (4) | girl L | **−8.3** | −6.1 | 13.1 | 8.7° / 4 f |
| e904 s010 (4) | girl R | **−5.2** | −17.3 | 15.0 | 10.4° / 4 f |
| e905 s010 (4) | boy L | **−6.9** | −11.5 | 15.3 | 4.3° / 4 f |
| e905 s010 (4) | boy R (pinned: T-040r2) | −26.6 | −30.8 | −37.7 | 5.8° / 4 f |
| e905 s010 (4) | girl L | **−11.3** | −22.3 | 12.5 | 12.8° / 4 f |
| e905 s010 (4) | girl R | **−2.0** | −15.5 | −1.0 | 28.4° / 4 f |

Files: `e906_s010_t040r1.json`, `e904_s010_t040r1.json`, `e905_s010_t040r1.json`, and
`e906_t040r1_contact_sheet.png` (frames 1, 8, 23, 44, 73 and 75, Cycles 16 spp, bpy 5.3 module). The e904 and e905
runs used stride 4 to fit the time box, so their steps are per 4 frames. e905 contacts were not re-measured with the
T-030 tool. The interaction doctests cover the ≤ 5 mm contacts.

### Why it falls short (what the next attempt needs)
1. **The engine and the tool still disagree on what is inside, in posed frames.**
   - At rest they agree: p50 0.2 mm, p90 0.9 mm.
   - Posed (e906 f1, f19, f73) they differ: p50 0.25 to 0.40 mm, p90 1.3 to 2.3 mm, p99 up to 15 mm, with 3 to 26
     sign disagreements among about 100 to 2,900 arm vertices within 3 cm.
   - Part of this is the tool itself. Its own-shell ray rule reports a girl vertex as 22.6 mm *outside* when the
     vertex maps into the hips 7 cm from the axis. Rays escape the inner blouse through its openings, so with layered
     garments "inside" is ambiguous.
   - So a pose the engine has cleared can still read as −5 to −19 mm. One case (e904 girl L) reads worse than with the
     post-pass off.
   - A decision is needed on **one inside/outside definition** for layered, open garments, used by both the engine and
     the evidence. A generalized winding number per garment, or a closed body proxy, are options.
2. **Smoothness.** A pure function of the pose with a hard "every vertex ≥ 0" target cannot ease in over several frames
   when the input moves in fast, or when points conflict. Steps of 10 to 28°/frame come from rounds stopping at
   different local minima. A ≤ 2°/frame guarantee needs either temporal state (filtering in `scene.cpp`, which is
   outside this task's write-set) or a softer target.
3. **The legacy test packages have open torso sides.** On the boy 1.0.0 the hoodie's waist sides are carried by the
   arm and are not body. Under mesh semantics, the arm poses that T-040's doctests choose "deep in the body" are not
   inside.
   - The IK-ramp doctest's boy pose is clear on the mesh, so its correction is 0.
   - The sweep doctest passes through the open side.
   - Those two doctests were written for capsules. They fail, and their expectations were **not** changed.

### plush_tests failures (unchanged expectations)
- "arm-body post-pass: continuous and smooth as an arm sweeps into the body":
  - boy: worst −15.2 mm, wrist step 27.9 mm (allowed 2.5 mm)
  - girl: worst −0.7 mm, step 8.2 mm (allowed 1.9 mm)
- "arm-body post-pass: an IK weight ramp hands over…":
  - boy: the deep pose is clear on the mesh, so total 0
  - girl: step 46.6 mm per 0.02 of IK weight (allowed 15.1 mm)

### Baselines
No frozen asset, spec or package was touched. Shot builds (packages, renders) stay in the ignored `build/` folders.
The T-040 engine is commit `2e81e45` if the Supervisor prefers its shot results over the test_clips fix.
