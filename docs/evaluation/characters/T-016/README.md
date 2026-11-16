# T-016: girl hair through the shared groom system (V3, part 1)

Status: **implemented; the visual result is not yet close to the reference.** Nothing is published or approved.
The girl's spec version is 0.5.0 and is unpublished.

## What was built
- `pipeline/charsys/groom.py` adds `groom/1`, the shared groom system. Hair is a list of spec structures:
  - `scalp_cap` reuses `hair.scalp_cap`;
  - `sweep` is locks on the scalp drawn towards a gather point or bun;
  - `fringe` is locks from a part line to the forehead;
  - `locks` are hanging locks in the style `straight`, `wavy` or `curly`, so long and curly hair are parameters;
  - `bun` is a list of coiled buns, each with its own position, size, wrap direction, turns and rope count;
  - `tie`, `bow` and `flowers` are hair accessories.

  Every lock is a plied yarn rope: the ply count, depth, twist, sections and step are set in `spec.hair.yarn`.

  Binding: by default the hair follows the head bone. The spec can set `spec.hair.binding.blend_z` so that long
  hair blends from the head bone to the chest bone.
- The generator has no character names. The boy's `hair_clumps/1` and `hair_clumps/2` are unchanged.
  `build_character.main_generic` calls `groom/1` only when the spec asks for it.
- Girl spec 0.5.0:
  - groom structures: a cap, one bun, front and back sweeps, a side-swept fringe, side, back and nape spiral curls,
    a band and 3 flowers;
  - material slots: `hair` uses the T-015 `wool yarn` preset in auburn `#56362C`; `hair_band`, `hair_flower` and
    `hair_flower_centre` use `felt`.
- `tools/groom_turnaround.py` renders the cameras from the reference index under the harness lighting. AgX, exposure
  −1.
- `tests/groom_generic_test.py` builds a synthetic egg head with no character data. It uses the structures the girl
  does not use: two buns with opposite wraps, a bow, straight and wavy long locks.

## Evidence
- `turnaround_vs_reference.png`: front, 3/4 (yaw −45), side (yaw 90) and back. Each view is a 640 px render next to
  the matching `sheet30_*` reference view. Cycles, 32 samples, OIDN.
- `yarn_closeup.png`: orthographic close-up, 0.30 m wide at 640 px, of the bun, the sweep and the back curls.
- `render_timings.json`.

## Matches the reference
- **Structure:** one high bun slightly behind the crown, with the top at about 1.09 m (target 1.10 m). A band at the
  bun base, flowers on the bun's front-left, hair swept up into the bun, spiral curls at the sides and back.
- **Length:** the back curls reach z ≈ 0.45–0.54 m, about mid-back, which matches #30 and #39/#40.
- **Yarn as geometry:** the ropes show plied twist ridges, visible in the close-up.
- **Face unaffected:** `face_system_test` gives the same 584 values with and without the groom: no eye occlusion and
  no glasses or eye overlaps.

## Deviates from the reference (open)
1. **Colour.** The hair reads grey-mauve, not auburn. The back-view hair median is sRGB (114, 92, 86); the reference
   is (88, 49, 40). The skin is also desaturated: leg (184, 169, 165) against (204, 160, 144). Likely causes:
   - the harness lighting under AgX;
   - the white sheen of the `wool yarn` preset (0.42).

   This needs lighting/exposure calibration for character renders, or a hair-preset override. I did not override the
   shared T-015 presets.
2. **Curl look.** The curls read as tight, regular "springs" or an accordion curtain. The reference has soft, chunky,
   irregular ringlets. On the back, the curls merge into a horizontal ribbed sheet with a hard lower edge. Also:
   - the twist ridges are too fine and too regular;
   - the material's object-space yarn waves add horizontal stripes everywhere. Ridges that follow each rope need
     UVs or tangents.
3. **Volume.** The side and back curls hang too far from the head: the side view shows a gap. The front view lacks
   the puffy temple volume of the reference.
4. **Fringe.** The fringe barely reads in the front view, and the forehead looks bare. The tips need more coverage
   and more contrast.
5. **Accessories.** The flowers are small and partly hidden. The band is buried inside the bun ropes. In the
   reference, the flowers are larger and pinker and the band is clearly visible.
6. **Pose.** Long hair is rigid to head and chest through a linear blend only. There are no hair dynamics and no
   collision check against arms or garments. The garments do not exist yet.
7. **Task wording.** The task says "buns with a bow". The reference and the approved identity decision show a
   single bun with flowers and a blue-grey band, so the girl uses those. Several buns and a bow are supported and
   tested on the synthetic head.

## Render time (CPU, 4 cores, Blender 5.3 bpy)
| Step | Time |
|---|---|
| Girl build (master + glb), groom part ≈ 2 s | 37.4 s |
| 4 turnaround views at 320×640, 32 samples | 17.0 s (5.0, 4.4, 3.6, 4.1) |
| Yarn close-up at 640×640 | 16.7 s |

The groom has 128,868 vertices in 11 objects. Budget used: 2 low-resolution iteration renders at 200×400 and 16
samples, plus 1 final turnaround and the close-up.

## Commands
```
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir>
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --closeup "yarn_closeup:135:10:0.02,0.06,0.93:0.30"
blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>
```
