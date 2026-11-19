# T-118: groom/4 readiness for `girl_white_hair_blue_dress` (design note, not a spec)

Scope addition by the owner, 2026-11-19 ~11:55Z. Read as design input: uploads 07 (groom blueprint), 08 (hair rig /
secondary motion), 17 (W04 back waves + buns), 18 (W02 blue felt bow; the bow is canonical). No model, spec, version
or render of her was made, and her reference files are untouched. Nothing below was built; "supported" means the
parameter exists in groom/4 and validates, and is used by the boy or girl today unless marked otherwise.

## What the references ask for
| feature (reference) | groom/4 today | status |
|---|---|---|
| Two round top buns with wrapped strands (07, 17) | `bun` takes a list of `buns` (az, el, radius, height, tilt), each with `ropes`, `wrap`, `turns` and felt lobes | supported; the girl uses one bun, two were not built here |
| Long, clearly separated locks with soft S-waves (17) | `locks` with `style: "wavy"` (`wave.amplitude`, `wave.wavelength`) or `"curly"` with `curl.ellipse < 1`; `hang_radii`, `rest_radii`, `z_end` | supported |
| Different lock lengths, tapered wispy tips (17) | `stagger.z_end`, `stagger.end_scale`, `end_scale`, `tip_frac` (new in groom/4) | supported; used by the girl candidate |
| Fringe clumps (07) | `masses` items with the face keep-out | supported; used by the boy |
| Wavy side locks (07) | `locks`, `mirror: true`, wavy style, own `az` band | supported |
| Smooth scalp coverage under the locks (07 "scalp coverage") | `scalp_cap`, `felt_volume`, `curtain`, `masses` rows | supported |
| Felt bow: two loops, knot, two tails (18) | `felt_bow` with a `loops` list (angle, length, width, thick), `knot`, `tilt_deg`, `lean` | supported as shape; tails are two more loops pointing down |
| One attachment point for bow and flower | Both sit on a bun (`bun`, `around_deg`, `height_frac`, `out`). A bow can sit on the scalp (`az`, `el`, `out`); a flower item can move there with `attach`. `turn` works on both (new in groom/4) | supported, with the limit below |
| Bun, lock and accessory secondary motion (08) | `dynamics.structures` chains for locks and buns; accessories on a bun follow its chain | supported for buns and locks |

## Missing or weak
- **Attachment on the hair surface.** `out` is measured from the scalp. An accessory beside a bun, on top of thick
  hair as in 17/18, needs a hand-set `out`; too small a value buries it (seen in a quick geometry test on the girl).
  A seat on the built hair surface (ray cast against the hair objects) is the missing piece.
- **Scalp accessories have no dynamics.** Only accessories on a bun follow a chain. Her bow sits beside the bun.
- **Fused back mass that separates into locks.** 17 shows a continuous felted back that splits into locks lower down.
  Today that is `masses` rows over the lock roots (as the girl's `back_sections`); there is no single primitive.
- **S-wave phase.** Wavy locks draw their phase at random. 17 shows neighbouring locks waving roughly together;
  a `stagger`-style phase list would give that control.
- **Bun wrap as visible strands.** The rope wrap exists, but the felt finish softens it. 17 shows distinct wrapped
  strands; this needs a look test, not a new parameter.
- **Fibre halo.** The references show a strong cream halo. That is the material preset's fibre layers, outside groom.

## Rough parameter sketch (illustrative values, not a spec)
```json
{"generator": "groom/4", "finish": "felt", "face_keepout": {"az": 34, "el_min": 2},
 "structures": [
  {"type": "scalp_cap", "name": "cap"},
  {"type": "bun", "name": "buns", "buns": [
    {"az": 140, "el": 62, "radius": 0.075, "height": 0.1, "tilt": 0.5, "wrap": "ccw", "turns": 1.2, "ropes": 4},
    {"az": -140, "el": 62, "radius": 0.075, "height": 0.1, "tilt": 0.5, "wrap": "cw", "turns": 1.2, "ropes": 4}]},
  {"type": "masses", "name": "fringe", "items": [
    {"root": [0, 72], "tip": [-6, 6], "width": 0.09, "depth": 0.6, "lift": [0.008, 0.035, 0.008]},
    {"root": [22, 66], "tip": [26, 4], "width": 0.085, "depth": 0.6, "lift": [0.008, 0.035, 0.008]},
    {"root": [-22, 66], "tip": [-28, 4], "width": 0.085, "depth": 0.6, "lift": [0.008, 0.035, 0.008]}]},
  {"type": "masses", "name": "crown", "rows": [
    {"count": 9, "pole": {"az": 180, "el": 80}, "ring": {"radius_deg": 12, "around": [60, 300]}, "len_deg": 70,
     "width": 0.09, "depth": 0.4, "lift": [0.0, 0.012, 0.01], "channel": {"gap": 0.08},
     "stagger": {"len": [1.0, 0.9, 1.08]}}]},
  {"type": "locks", "name": "side_locks", "style": "wavy", "count": 2, "mirror": true, "az": [62, 96],
   "el_root": [6, 18], "hang_radii": [0.17, 0.15], "z_end": [0.5, 0.56], "width": 0.045, "thick": 0.036,
   "wave": {"amplitude": 0.012, "wavelength": 0.11}, "end_scale": 0.3, "tip_frac": 0.3,
   "stagger": {"z_end": [0.0, 0.04], "mirror_shift": 1}},
  {"type": "locks", "name": "back_locks", "style": "wavy", "count": 9, "az": [110, 250], "el_root": [-10, 4],
   "hang_radii": [0.18, 0.16], "z_end": [0.34, 0.4], "width": 0.05, "thick": 0.04,
   "wave": {"amplitude": 0.014, "wavelength": 0.12}, "end_scale": 0.3, "tip_frac": 0.3,
   "stagger": {"z_end": [0.0, 0.05, -0.02, 0.07, 0.02], "end_scale": [1.0, 0.8, 1.1]}},
  {"type": "felt_bow", "name": "bow", "bun": 0, "around_deg": 70, "height_frac": 0.1, "out": 0.02, "size": 0.06,
   "knot": 0.18, "loops": [
     {"angle_deg": 20, "length": 0.55, "width": 0.36, "thick": 0.2}, {"angle_deg": 160, "length": 0.55, "width": 0.36, "thick": 0.2},
     {"angle_deg": 240, "length": 0.4, "width": 0.22, "thick": 0.14}, {"angle_deg": 300, "length": 0.4, "width": 0.22, "thick": 0.14}],
   "turn": {"toward": [60, 20], "amount": 0.5}}],
 "dynamics": {"enabled": true, "structures": {"buns": {"bones": 3}, "back_locks": {"bones": [3, 5], "bone_length": 0.07},
                                               "side_locks": {"bones": [3, 4], "bone_length": 0.06}}}}
```
The sketch places the bow on a bun so it follows that bun's chain. Angles, sizes and counts are guesses from the
images and would need her head proportions and a geometry preview first.

## Suggested order if she is built later
1. Two-bun and wavy-lock geometry preview (no new code expected).
2. Hair-surface accessory seat and a chain for scalp accessories (new code, small).
3. Wave phase control and the back-mass-to-locks transition (new code, after seeing step 1).
