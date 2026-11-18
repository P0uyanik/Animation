# T-089: face and eye system round 3 (`face_generic/3`)

Implementer report data for T-089 (Phase B, round 2). Input SHA `4910b69`; branch `t-089-claude-face-eyes-r3`.
Blender used for everything here: the **bpy 5.3.0 module** (Python 3.13) behind a `blender` wrapper (no Blender
binary in the cloud container). Baseline check: the published boy 2.0.0 and girl 0.11.0 rebuilt here give face
build reports **identical** to their published `build_report.json`, and fidelity scores 67.42 / 62.28 (published
67.63 / 62.29).

## Owner evidence
| | boy (2.0.0 vs candidate) | girl (0.11.0 vs candidate) |
|---|---|---|
| strict sheet (T-087 recipe) | [boy_2.0.0_vs_face3_strict.jpg](boy_sheet/boy_2.0.0_vs_face3_strict.jpg) | [girl_0.11.0_vs_face3_strict.jpg](girl_sheet/girl_0.11.0_vs_face3_strict.jpg) |
| blink / glance strip | [boy_blink_glance_strip.jpg](boy_sheet/boy_blink_glance_strip.jpg) | [girl_blink_glance_strip.jpg](girl_sheet/girl_blink_glance_strip.jpg) |
| recipe | [boy_2.0.0_vs_face3.recipe.json](boy_2.0.0_vs_face3.recipe.json) | [girl_0.11.0_vs_face3.recipe.json](girl_0.11.0_vs_face3.recipe.json) |
| first frame (preview) | [boy_first_frame_preview.jpg](boy_preview/boy_first_frame_preview.jpg) | [preview.jpg](girl_sheet/preview.jpg) |

Sheet columns: original reference | current approved | T-089 candidate | AI target (Higgsfield B01/B02, G01/G02;
face rows only). The strips are head-only renders (no hair, clothing or glasses) of neutral, blink 50 %, blink 100 %
and glance (eye bones 15 deg), front and 3/4, current vs candidate.

## What `face_generic/3` adds (code)
`pipeline/charsys/face_generic_v3.py` = `face_generic/2`'s build (copied; `face_generic.py` is untouched) plus
opt-in spec data. With none of the options set, a v3 build equals v2. Measured: pin-only builds give the same
eye-corner fold values as the published versions, boy 157.73 and girl 40.318 deg.
- **Lid shells that end at the eye corners** (`eyes.lids.trim`, `face_v3/lids.py`, `face_v3/socket.py`). Each
  shell is cut at x = r·sin(outer_deg) (and optionally inner) in its eye frame, and optionally behind y = −back·r
  (`up_back` / `lo_back`). Blink, wide and squint rotate the lids about the frame's x axis, so a trimmed shell stays
  inside its x bound in every lid key. The test checks that bound, and the build report records it as
  `lid_corner_extent_m`. The socket is a copy of `lid_socket` with a per-vertex cover radius: past the trim, the
  skin covers the eyeball instead of being lifted over a shell that is no longer there. Only shell faces are cut
  (lash strands joined into a lid stay whole).
- **Lid roll** (`eyes.lids.upper_roll_deg` / `lower_roll_deg`). Rotates one lid on its sphere (still concentric
  with the eyeball). With the lower lid rising to the outer corner, this gives the D-shaped felt-doll opening.
- **Felt eye mode** (`eyes.shader = "felt/1"`, `eyes.felt`, `face_v3/felt_eye.py`). The iris is matte (no clear
  coat, rough base, sheen, no streaks) with exactly one crisp highlight, and the lash tube becomes a matte felt lid
  line. `round_iris` keeps the iris round on a non-uniformly scaled eyeball. The glossy `layered/1` eye stays the
  default.
- **Report:** `lid_trim`, `lid_roll_deg`, `lid_corner_extent_m` (over the basis and every lid key),
  `lid_shell_exposed_3q` (3/4 rim diagnostic, see below) and `felt_eye`.
- **Character-agnostic:** no character id, name or dimension in the shared code (tested).

## Candidates (spec data only; no published file or `*.spec.json` changed; no version bump)
- `assets/characters/boy_yellow_hoodie/spec/candidates/T-089/boy_face3.override.json` on `boy_yellow_hoodie.2.0.0.spec.json`
- `assets/characters/girl_auburn_bun_glasses/spec/candidates/T-089/girl_face3.override.json` on `girl_auburn_bun_glasses.0.11.0.spec.json`

**Boy** (targets: val27 and hero24 originals, B01–B03).
- Spherical eyeball, r 42 → 52 mm. The 42 mm eye was deep-set, and the visible width could not grow past about
  51 mm through the lids alone.
- Iris scaled to keep its size.
- Socket corner 52 → 60 deg.
- Upper lid edge 6 → 14 deg (Supervisor review: taller, more iris below the lid). Upper roll 7 deg gives a level
  lid line; lower roll 14 deg gives the D shape.
- Thick flat felt lid line, no visible lid bands.
- Trims: upper outer 64 deg / back at y < 0.1 r; lower outer 62 deg / back 0.3.
- Wall smoothing 25.
- Brows thinner (4.2 → 2.8 mm) and higher (0.72 → 1.2 r), with a gap above the lid.
- Felt eye. Blink overlap 12 deg.

**Girl** (targets: ref_30 and sheet30 originals, G01–G03).
- Eye r 42 → 48 mm. The oval eyeball stays, narrowed in x (scale 0.9, 0.8, 1; `round_iris`).
- Lower gap 0.03 → 0.015 and lower band 1 deg (tucks the bright shelf).
- Trims: upper outer 66 deg (no upper back cut, because her open lid needs the whole shell to close); lower outer
  62 deg / back 0.3.
- Felt eye with one crisp highlight at upper screen-right. Blink overlap 3 → 14 deg.

## Measurements (before → after)
Eye opening per view: `measure_eyes.py` ray-casts the visible eyeball (all values in
[measurements.json](measurements.json)). Reference ratio = eye width / eye-centre spacing from the original
landmark annotations.

| | view | width mm | height mm | width / spacing | reference |
|---|---|---|---|---|---|
| boy | front | 48.8 → **63.8** | 26.5 → **39.3** | 0.36 → **0.47** | 0.48 (val27) |
| boy | 3/4 near eye | 50.0 → 66.3 | 26.3 → 39.8 | 0.45 → 0.60 | 0.64 near / 0.35 far |
| boy | 3/4 far eye | 30.3 → 38.8 | 26.5 → 38.3 | 0.27 → 0.35 | |
| boy | side | 17.5 → 28.0 | 25.0 → 39.5 | side/front 0.36 → 0.44 | 0.51 |
| girl | front | 59.0 → **61.3** | 53.3 → **59.0** | 0.51 → **0.53** | 0.66 (sheet30) |
| girl | 3/4 near eye | 66.8 → 68.8 | 53.0 → 59.0 | 0.70 → 0.72 | |
| girl | side | 34.8 → 37.0 | 49.8 → 57.5 | | |

Blink and glance:
- **Blink 100 %:** both characters close fully in front. At 3/4, the boy closes fully. The girl's near eye keeps a
  corner sliver of 27.2 mm² (gb14 trial build of the final override). Published 0.11.0 keeps 23.3 mm² there.
- **Blink 50 %:** both show a half-closed lid (see the strips).
- **Glance (15 deg):** the opening is unchanged, as expected for a spherical eye (boy) and the lid tracking of the
  oval eye (girl). The iris moves; see the strips.

Fidelity (`tools/fidelity/run.py`, same Blender, `fidelity/*/fidelity.json`):

| | score | eye width vs ref | eye area vs ref | eye-region IoU |
|---|---|---|---|---|
| boy 2.0.0 → candidate | 67.42 → **68.67** | −29.9 % → −17.6 % (front −29.5 → −3.0 %) | −40.2 % → +20.2 % | 0.149 → 0.313 |
| girl 0.11.0 → candidate | 62.28 → **62.54** | −18.7 % → −13.9 % | −29.7 % → −18.1 % | 0.239 → 0.236 |

The girl's fidelity run used the candidate one commit before her final blink overlap (`cb3cc81`). The overlap
changes only the blink shape keys, and fidelity renders have the face controls at zero.

## Socket rim and skin smoothness
**3/4 rim.** `lid_shell_exposed_3q` = share of shell vertices past the opening's corner that are visible at yaw
±35 deg. Before values come from pin-only v3 builds, which equal v2.

| | upper shell | lower shell |
|---|---|---|
| boy 2.0.0 → candidate | 9.8 % → 4.5 % | 16.8–19.7 % → 0 % |
| girl 0.11.0 → candidate | 10.0–10.3 % → 0.5 % | 47 % → 0 % |

**Folds** (T-081 probe: max dihedral on `body_skin`).

| | cheek | eye corner |
|---|---|---|
| boy 2.0.0 → candidate | 15.0 → 12.2 deg | 157.7 → 59.5 deg |
| girl 0.11.0 → candidate | 22.2 → 19.5 deg | 40.3 → **35.2** deg |

T-081's smoothing gain is kept and improved on the girl. The boy never had the T-081 smoothing; his candidate is
far smoother than 2.0.0 but still above 45 deg at the outer-lower corner (see open points).

## Tests
`pipeline/charsys/tests/test_face_v3.py` (new; to be wired into the gate by the Supervisor):
- **Plain checks:** declared pins; published specs unchanged; candidates pin v3; no character names in shared code.
- **Unit checks in Blender:**
  - registry load;
  - felt mode on/off;
  - lid-corner bound over rotations;
  - back cut;
  - v3 socket = v2 without trim.
- **Build checks per character:**
  - felt eye present;
  - shells within bounds;
  - 3/4 rim ≤ 10 %;
  - folds no worse than the published version;
  - full blink closes, within 1.25× the published version's own residue.

Regression on this machine:
- `test_versions.py` 91/91.
- `test_face_v2_socket_wall.py --girl011` 13/13. This includes the build checks on a fresh 0.11.0 build.

## Open points / limitations
1. **Boy eye-corner folds 59.5 deg.** Better than 2.0.0's 157.7 deg but above T-081's 45 deg bar. The cause is the
   lower roll (the D shape). Without the roll the folds are 59.2 deg, with the trim off 66.8 deg, and more wall
   smoothing brings them to 59.5 deg. Not fixed by any socket data option tried (corner close/blend, bands, cover
   softness).
2. **Girl width.** +4 % only (0.51 → 0.53 of spacing; reference 0.66); height +11 %, area +16 %.
   - A spherical eye or r ≥ 52 mm raised her corner folds to 55–69 deg, above 0.11.0's 40.3.
   - `cover_sides` (needed to keep a larger eyeball's side under the skin at 3/4) gives 73–78 deg folds.
   - A larger girl eye needs a head or socket change beyond this task.
3. The girl's 3/4 blink keeps a corner sliver (27 mm² vs 23 mm² on 0.11.0).
4. Brows: the reference brows sit largely under the fringe. In the face-only strips they show fully; in the sheets
   they are under the hair (boy).
