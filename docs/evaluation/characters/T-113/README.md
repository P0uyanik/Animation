# T-113: expression library expansion with per-character sets (round 3)

Implementer report data for T-113. Input SHA `bf37671` (`integration/t-109`, boy 2.1.0 / girl 0.12.0 current, T-109 face
options merged); branch `t-113-claude-expressions`. Blender for everything here: the **bpy 5.3.0 module** (Python
3.13) behind `tools/bpy_blender.py` (no Blender binary in the cloud container). Engine bake: `plush-render` built here
(cmake + ninja, Release, `PLUSH_BUILD_RENDERER=OFF`; no engine file touched).

## Owner evidence
| | boy | girl |
|---|---|---|
| strict sheet (Cycles 12 spp, T-087 light rig, 3/4 at -30 deg): reference crop, published master, current + T-113 | [boy_expressions_strict.jpg](sheets/boy_expressions_strict.jpg) | [girl_expressions_strict.jpg](sheets/girl_expressions_strict.jpg) |
| cheap preview (Cycles 2 spp; first pass, not for approval; framing changed after it) | [boy_preview.jpg](sheets/boy_preview.jpg) | [girl_preview.jpg](sheets/girl_preview.jpg) |
| T-109 candidates + T-113 (Cycles 12 spp) | [t109_candidates_t113_strict.jpg](sheets/t109_candidates_t113_strict.jpg) | (same sheet) |
| e908 acting frames, re-baked with the new sets (Cycles 16 spp, the shot's lights) | [e908_t113_acting.jpg](acting/e908_t113_acting.jpg) | (same sheet) |
| closed lids on the published masters, before (Cycles 8 spp eye crops) | [boy_published_lid_crops.jpg](sheets/boy_published_lid_crops.jpg) | [girl_published_lid_crops.jpg](sheets/girl_published_lid_crops.jpg) |
| why the closed lid is pale (lid subsurface on / off) | [boy_lid_subsurface_diagnosis.jpg](sheets/boy_lid_subsurface_diagnosis.jpg) | |
| full blink with the eyes turned (published vs T-113) | | [girl_blink_gaze_coverage.jpg](sheets/girl_blink_gaze_coverage.jpg) |

- **Reference column.** The crop of the closest reference frame. It comes from the T-106 frame anchors
  ([ref_frames.py](ref_frames.py), `tools/perf_extract` face crops) or from a still-reference tile (#28, #34).
- **Rendered columns.** Each row shows the controls the emotion file drives, at its expressed intensity
  ([make_jobs.py](make_jobs.py) → [expr_sheet.py](expr_sheet.py) → [compose_sheet.py](compose_sheet.py)).
  - Intensity: boy 0.42 (event 0.7 × his `reaction.intensity_scale` 0.6); girl at her event intensities (delighted 0.9,
    wonder 0.7, others 0.8).
  - Gaze bias: turns the eye controls.
  - faceMotion channels: added to the face.
  - Not shown: the body clip.
- **Lid rows.** Each preset at 1.0, with no gaze.
- **Missing controls.** A red "missing: SmileOpen" means the published master does not build that preset. The
  engine then skips that face part.
- **Cast for the e908 frames.** The current spec plus the T-113 candidate override, on scratch copies of
  `episodes/e908_*_acting/shots/s010` under the git-ignored `build/t113_e908/`. The committed shots keep cast
  `"current"`.
  - The boy copy adds one `boy_unimpressed` emotion action over f0–f29 (WT [0, 20) "brows low"). Without it e908
    plays no new boy set.
  - Rendered with [T-109's acting_face.py](../T-109/acting_face.py).

## What changed
### Per-character expression sets (data)
The sets are `content/emotions/<char>_*.emotion.json`. They are listed in `pipeline/charsys/tests/test_expressions_r3.py`
and documented in `pipeline/charsys/face_library/README.md`. Every file cites its frame ranges, from
`docs/evaluation/animation/T-106/performance.csv` or from still references.

| emotion | face (intensity 1) | calibrated against |
|---|---|---|
| boy_interested (T-097, `reference` added) | EyeWide 0.8, BrowDown 0.5, MouthO 0.25, JawOpen 0.08 | PB [259, 289); WT [60, 81), [87, 121) |
| **boy_sleepy** | blink 1.0, BrowDown 0.25, MouthO 0.4, JawOpen 0.12 | PB [0, 12) onset 0.50 s, [12, 32) hold 0.83 s, [125, 132) iris stays visible; PB boy 0 blinks in 4.2 s |
| **boy_unimpressed** | BrowDown 1.0, blink 0.5, MouthFrown 0.7 | PB [112, 125) onset 0.54 s; WT [0, 20) hold 0.83 s, jaw shut (median 0.001) |
| **boy_reluctant** | **pout** 1.0, blink 0.5, BrowSad 0.6 | #28 r3c3 (heavy lids, inner brows up, sulky pout), hero24 / #08 pout |
| **boy_focused** | blink 0.3, BrowDown 0.35, MouthO 0.2, JawOpen 0.5 | PB [132, 151) median jawOpen 0.21 = 0.5 × 0.42; [125, 132) onset 0.29 s |
| girl_delighted (T-097, now **smileOpen**) | smileOpen 1.0 | PB [255, 289) open D smile; WT [81, 96) release |
| girl_wonder (T-097, unchanged) | WideOpen 0.8, jawOpen 0.1 | WT [0, 15), [22, 39), [39, 61) |
| **girl_eager** | EyeWide 0.5, BrowUp 0.45, MouthO 0.45, MouthSmile 0.1, JawOpen 0.1 | WT [22, 39) onset 0.71 s, [39, 61) hold 0.92 s, f033 round "o" |
| **girl_shy** | SmileClosed 0.5, blink 0.3, BrowSad 0.15 | PB [0, 32) closed smile, eyes down (hold 1.33 s), [112, 125), [132, 151) |
| **girl_content** | SmileClosed 0.6, MouthSmile 0.2, JawOpen 0.08, EyeSquint 0.15 | WT [81, 96) onset 0.63 s, [96, 121) hold 1.04 s (median jawOpen 0.046) |

- **Shared library.** It stays exactly 8 (test_emotions.cpp counts only files without a boy_/girl_ prefix).
- **Personality (emotion references only):**
  - boy `reaction.events.failure` now plays `boy_reluctant` (was the shared sad);
  - the girl's `delighted_style` text names SmileOpen / girl_delighted.
- **Signature test.** `tests/acting/test_girl_signature.py` uses the new expression names: `smileOpen` in the file
  check and the `SmileOpen` morph in the bake check. Nothing else changed.

### Closed lids: `eyes.lids.closed_fit` (face_v3/lids.py `fit_closed_lids`; opt-in)
**Diagnosis.** Two causes, measured on the published masters (crops above):
1. **Geometry.**
   - The closed upper lid closes at the eye's *global* gaze envelope.
   - Smile, Laugh and Squint add a squint rotation linearly to the closure, so the shell rides further out. In the
     boy's Smile it rides past its rest radius and pokes through the brow skin as a bump.
   - Visible closed-lid gap to the eyeball (p95): boy Smile/Laugh/Squint 6.05 mm; girl Blink 5.51 mm, Laugh 7.88 mm,
     Squint 8.62 mm.
2. **Subsurface (the "pale").**
   - The skin's subsurface weight is 0.5, with a radius of 1.0 × 14.5 mm.
   - The lid shell is only 1.2–1.6 mm thick, so the white eyeball and its highlight shine through it.
   - With the lid's subsurface off, the closed lid reads as skin ([diagnosis](sheets/boy_lid_subsurface_diagnosis.jpg)).

**Fix.** It runs after the presets are baked. For every upper-lid and lash shape key (AU keys, in-betweens, presets):
- **Pull.** Each vertex is pulled in along its eye-frame radius towards `r (envelope(u) + gap) + its shell thickness`.
  - The amount is weighted by the vertex's closure in that key (its downward rotation ÷ the Blink rotation).
  - It uses the per-direction gaze envelope, as T-109's lower_fit does.
- **Fades.** The pull fades out:
  - above the rest lid edge, under the socket skin (`fade_deg`, `fade_above_edge_deg`);
  - towards the eye corners (`corner_fade`, default [0.7, 0.95] eye radii).
- **Cap.** No key carries the shell past its rest radius; this removes the bump.
- **Rules.** Pulled in only, never pushed out. Open keys (EyeWide, brows, mouth) are unchanged.
- **Options:**
  - `gaze_range_deg`: the sweep the closed lid must still clear;
  - `shell_subsurface`: the upper lid shell gets a copy of its skin material, "M_skin_face.lid", with the subsurface
    weight scaled by this factor.
- **Hook.** One `if` in `face_generic_v3.py` after `bake_presets`, 5 lines; this is outside the T-113 write-set (see
  open points).

**Candidates** ([candidates/](candidates/); they stack on the published spec or on the T-109 candidate):
- `boy_t113.override.json`: closed_fit (gap 0.01, fade 20/20, shell_subsurface 0) and optional `[Worried, Curious, Pout]`.
- `girl_t113.override.json`: the same, plus closed_fit `gaze_range_deg [26, 26]`, and optional
  `[Worried, Curious, SmileClosed, Thinking, SmileOpen]`.

**Tuning record** (what was tried, and why it was rejected):

| tried | result | decision |
|---|---|---|
| fade only below the rest edge | boy Smile unchanged: the visible closed lid lies above his edge (-9.5 deg) | full pull up to the edge, fade above it |
| girl gaze_range [8, 4] | Blink 5.5 → 3.3 mm, but at e908 f42 the iris showed through the closed lid | rejected |
| girl gaze_range (own 16 / 8) | at f42 the iris still showed, more than published (white only) | rejected |
| girl gaze_range [26, 26] | at f42 less eye than published; Blink stays about published, Laugh / Squint 7.9 / 8.6 → 5.8 mm | **kept** |
| no corner fade | test_face_v4: 3/4 full-blink residue 44.8 mm² (limit 29.1) | corner_fade [0.7, 0.95] → 9.1 mm² (T-109 alone 8.5) |

Gaze check: e908 girl f42 has her eyes 25 deg down and 18–26 deg sideways while she blinks. That is beyond her spec
gaze_range_deg (16 / 8), so the look action is not limited to it (open point 3).

### Measurements (test_expressions_r3 build checks; visible upper-lid vertices from the front and from 3/4, distance to the eyeball, p95)
| | published | current + T-113 | T-109 + T-113 | bound |
|---|---|---|---|---|
| boy Blink | 2.61 | 2.56 | 2.57 | 3.5 |
| boy Smile / Laugh / Squint | 6.05 / 6.05 / 6.01 | 3.37 / 3.37 / 3.37 | 3.37 / 3.37 / 3.37 | 3.5 |
| girl Blink | 5.51 | 5.38 | 5.40 | 6.0 |
| girl Laugh / Squint | 7.88 / 8.62 | 5.86 / 5.81 | 5.79 / 5.78 | 6.0 |
| girl Smile (eyes stay open; not a closed lid, not checked) | 5.81 | 5.79 | 5.79 | – |
| no visible lid inside the eyeball (min ≥ 0) | – | min 1.76 (boy) / 4.01 (girl) | min 1.76 / 3.61 | ≥ 0 |
| Blink with eyes turned ±16 / ±8 deg: eyeball vertices visible from the front | 0 | 0 | 0 | 0 |

- **Boy.** His visible closed lid sits at about 3.4 mm, his rest-lid radius (his eyeball is a 52 mm sphere).
- **Girl.** Her Blink keeps about 5.4 mm: the 26-deg sweep of her oval eye.
- **Pale look.** The fix for the pale look itself is `shell_subsurface` (strict sheets: closed lids now read as skin,
  with no shine-through highlight).

## Default output unchanged
- **Method.** The published specs (boy 2.1.0, girl 0.12.0, no override) were built twice:
  - at the input SHA (git worktree of `bf37671`);
  - with the T-113 code.
- **Geometry.** [T-109's mesh_hash.py](../T-109/mesh_hash.py) hashes every mesh and every shape key. All **220 (boy)
  and 207 (girl)** objects are identical.
- **Reports.** `components.json`, `animation_compat.json` and `spec.resolved.json` are identical. `build_report.json`
  differs only in the cloth `seconds` timing.
- **Why identical.** closed_fit is gated on the spec key, and no published spec sets it.
- **Timing caveat.** These builds ran before `corner_fade` was added. That code is inside the gated function.

## Tests
| command | result |
|---|---|
| `python3 pipeline/charsys/tests/test_expressions_r3.py` (plain) | 68/68 PASS |
| `... --blender <bpy> --boy <current+T-113> --girl <current+T-113>` | 86/86 PASS |
| `... --boy <T-109+T-113> --girl <T-109+T-113>` | 86/86 PASS |
| `... --boy/--girl <published masters>` (control: the new checks must fail) | 78/86: dome checks for boy Smile/Laugh/Squint and girl Laugh/Squint fail, as intended (closed_fit "built" checks fail too) |
| `python3 pipeline/charsys/tests/test_face_v4.py --blender <bpy> --unit --boy/--girl <T-109+T-113>` | 55/55 PASS (incl. full-blink residue front/3/4 and the 15-deg lid-line glance check; T-109 limits unchanged) |
| `test_face_v3.py` 7/7, `test_face_v3b.py` 10/10, `test_face_v4.py` (plain) 17/17, `test_versions.py` 105/105, `test_asset_store_guard.py` 33/33 | PASS |
| `ctest` (build/, renderer off) | 2/2 (renderer tests skipped: no Embree) |
| `build/tests/plush_tests -tc="*emotion*,*personality*,*reaction*"` | all pass (shared library = 8) |
| `tests/acting/test_girl_signature.py` (data) / `--bake <e908 girl T-113 bake>` | 21 OK (5 skipped) / 21 OK, incl. the SmileOpen beat (peak 0.9 at f94, < 0.05 before E2 and at the end) |
| `tests/acting/test_boy_signature.py` (data) | 15 OK (3 skipped: its bake tests bake the committed shot's resolved scene, which needs a "current" run) |

Not run:
- `verify_charsys.py`: legacy boy path, untouched.
- Engine image regressions: no engine or renderer file was touched.
- The fidelity scores: the owner decides on the sheets.

## Open points
1. **SmileOpen / Pout are not in the published masters.**
   - girl_delighted (smileOpen) and boy_reluctant (pout) lose that face part on a `"current"` cast: the engine skips it
     with one warning. The strict sheets show this as "missing" in the published column.
   - test_girl_signature's bake check now looks for the `SmileOpen` morph, so it fails on a bake of the committed
     (current-cast) e908 until a girl version lists SmileOpen.
   - It passes on the T-113 cast bake.
   - The owner decides whether the next versions list them; the T-113 / T-109 overrides do.
2. **Out of the write-set:**
   - the 5-line hook in `face_generic_v3.py`;
   - the candidate overrides stored here, not in `assets/characters/*/spec/candidates/T-113/`;
   - `shell_subsurface`, a lid-only material copy that touches T-110's skin area. It is opt-in; drop it if T-110 should
     own it.
3. **Gaze beyond the spec range during blinks** (pre-existing). e908 girl f42 blinks with her eyes 25 deg down and
   18–26 deg sideways, past her `gaze_range_deg` 16 / 8.
   - The published lid shows eyeball white there, and so does T-113, slightly less ([coverage sheet](sheets/girl_blink_gaze_coverage.jpg)).
   - The look action or the engine should clamp gaze to the spec range, or close the gaze with the blink.
4. **No lash line on closed eyes** (pre-existing, both versions).
   - The references draw a closed eye as a dark arc: WT f017 / f083, #28 Happy / Sleepy, #34 Laugh.
   - Our closed lids show no line in front, and the boy shows only the outer corner. The blink `overlap_deg` (boy 12,
     girl 33) carries the lash under the lower lid.
   - Worth its own task, together with point 5.
5. **The girl's closed eye still reads as a rounded dome.** Her eyeball is oval (scale 1.03 / 0.8 / 1.0), protrudes
   4 mm, and the lid must clear its gaze sweep. The references' closed lids are much flatter. The geometry fit cannot
   go below the eyeball.
6. **The boy's sets are subtle by design.**
   - He plays at 0.42 (his profile's `intensity_scale`), so the pout reads weakly next to #28 r3c3. Raising it is a
     personality decision, not an expression one.
   - Gaze bias is shown with the eye controls; the body clips are not in the sheets.
