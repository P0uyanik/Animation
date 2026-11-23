# T-218: per-shot contact audit (`pipeline/production/contact_audit.py`)

One tool for the penetration measures of T-183 / T-194: it opens (or builds) a shot.blend, evaluates the real meshes
per frame and reports penetrations by pair class, with JSON + markdown output. Audit only: it changes no shot, asset,
bake or engine file. Method and roles: the module docstring.

## Findings (e912 s020, every 2nd frame, 104 frames x 3 characters)

### 1. Released s020 with `--hair-pushout`: 117 hair pops, auburn up to +238 mm (report only)

On the released chain (`rel_*`) the push-out makes the hair jump: **117 frame x character entries where the push-out
adds > 5 mm to the largest frame-to-frame hair vertex move, largest +237.7 mm (auburn, f47)**. 111 are calm; 6 fall
in a T-194 snap window (f45, f47, f111 auburn; f45, f47, f135 white).
On the T-183 candidate (`cand_*`) the same push-out adds __CAND_POPS__.

| character | pop frames | median added | max added |
|---|---|---|---|
| girl_auburn_bun_glasses | 85 / 104 | +77.5 mm | +237.7 mm (f47) |
| girl_white_hair_blue_dress | 32 / 104 | +18.0 mm | +36.5 mm (f31) |
| boy_yellow_hoodie | 0 | | |

Auburn (frame +added mm): f3 +139, f5 +138, f7 +152, f9 +218, f11 +138, f13 +144, f15 +124, f17 +185, f19 +123,
f21 +173, f23 +187, f25 +222, f27 +151, f29 +191, f31 +160, f33 +118, f35 +108, f37 +74, f39 +136, f41 +191, f43 +138,
f45 +144, f47 +238, f49 +103, f51 +75, f53 +117, f55 +122, f57 +73, f59 +77, f61 +101, f63 +83, f65 +79, f67 +130,
f69 +179, f71 +212, f73 +121, f75 +173, f77 +146, f79 +109, f81 +32, f83 +8, f85 +39, f91 +11, f97 +18, f99 +18,
f101 +27, f103 +24, f105 +7, f111 +33, f117 +60, f119 +97, f121 +26, f125 +10, f127 +10, f129 +21, f131 +15, f141 +36,
f143 +27, f145 +206, f147 +155, f149 +88, f151 +79, f153 +83, f155 +76, f157 +75, f159 +127, f161 +50, f171 +14,
f175 +14, f177 +13, f179 +21, f181 +25, f183 +25, f185 +25, f187 +25, f189 +17, f191 +27, f193 +27, f195 +28,
f197 +17, f199 +23, f201 +24, f203 +16, f205 +27, f207 +28.

White: f9 +21, f21 +18, f23 +16, f25 +8, f27 +16, f29 +16, f31 +36, f33 +19, f43 +8, f45 +16, f47 +18, f49 +18,
f51 +28, f55 +7, f57 +36, f59 +25, f61 +9, f65 +8, f67 +18, f69 +23, f71 +24, f73 +25, f75 +27, f77 +25, f81 +26,
f85 +8, f87 +18, f91 +17, f99 +20, f119 +22, f135 +9, f181 +10.

What the push-out buys on the released chain: hair_set 103 -> 4 calm entries (hair through the table), staging
55 -> 28, max calm hair 109.5 -> 88.2 mm; calm entries over 1 mm 192 -> 196 / 288. So on released chains
`--hair-pushout` trades set penetration for large per-frame hair jumps on auburn (f3-f79 and f145-f161 above
+70 mm on most frames). The released bake already jumps without it (auburn hair moves 167 mm f107 -> f109, a body
snap), so the pops are measured against that. Not fixed in T-218.

### 2. Validation against T-194 (candidate bakes `cand2`, T-194 snap frames 45, 46, 109, 111, 133, 134, 136-138)

Same counting as T-194 (`docs/evaluation/characters/T-194/results/e912_s020c2.sum.json`): frame x character entries,
calm = not a snap frame +-1, boy's rigid hair (T-191, `known_e912.json`), glasses and staging apart.

| | T-194 off | T-218 off | T-194 on | T-218 on |
|---|---|---|---|---|
| calm entries > 1 mm | 192 / 288 | 192 / 288 | 149 / 288 | __CAND_ON_CALM__ |
| max calm | 33.81 (f115 auburn `hair_cap.001` in own skin) | 33.81 (same) | 33.81 | __CAND_ON_MAX__ |
| all entries > 1 mm | 208 / 312 | 208 / 312 | 159 / 312 | __CAND_ON_ALL__ |
| pops > 5 mm | | | 3: white f109 +7.2, f185 +6.2, f205 +6.3 | __CAND_ON_POPS__ |
| boy head (apart) | 45 fr, 52.29 | 45, 52.29 | | |
| staging (apart) | 40 fr, 77.55 | 39, 77.55 | 33 fr, 77.55 | __CAND_ON_STAGING__ |
| glasses (apart) | 104 fr, 1.4 | 104, 1.30 | | |

Per frame (T-194 `results/e912_s020c2_off.m.json` against `cand_off`, worst hair depth per frame and girl, staging
and glasses apart): 201 of 208 agree within 0.1 mm. The 7 that differ are all around the two body snaps, f105-113
and f133-135. At f109, T-194 has auburn's `hair_cap.001` 37.4 mm and `hair_curtain` 37.6 mm in her skin; in the T-218
blend the cap is not in the skin at all (raw depth 0 before the rest rule; checked with a separate script) and the curtain
sits at its rest depth. So the difference is the evaluated hair at the snap, not the depth rules: the two shot.blends
were built at different times by shot_render (T-194's in its own session), and auburn's hair moves differently
across the snap (largest move f107 -> f109: 368 mm in T-194, 167 mm here; the move differs on most auburn
frames from f105 on, while the depths agree). The calm counts and the calm max are the same, and snap frames are not
in the calm columns. This is noted, not resolved: T-218 does not rebuild T-194's blend.

### 3. The other classes (same in all four runs: the push-out moves hair only)

| class | entries > 1 mm / 312 | max mm | worst | depth pops > 5 mm |
|---|---|---|---|---|
| garment_body | 311 | 40.91 | f51 auburn `garment.blouse.main` in her collision body | 92 (max 32.9) |
| body_body | 38 | 58.03 | f17 boy's right hand in auburn's body | 52 (max 58.0) |
| hand_prop | 66 | 20.41 | f57 auburn's left hand in `prop.boat` | 13 (max 19.0) |
| body_set | 312 | 62.57 | f9 boy's trousers in the `stool_boy` box | 133 (max 14.4) |

- garment_body is measured against the closed collision proxy (`garment.collider.body_skin*`), the cloth's
  collider, after subtracting what is embedded at rest. Largest: auburn blouse 40.9 (all 104 frames), vest 33.7,
  shorts 32.9, vest edge 31.4; boy hoodie pocket 30.7, hoodie 29.3; white skirt 22.2, hem 21.5. Whether the proxy
  is the right reference for "body through the cloth" (it may sit outside the rendered skin) is for L1 to decide;
  the tool can be pointed at another solid by metadata.
- body_body is staging: the boy's right hand and auburn's left hand / torso overlap f17-f31 (58.0, 25.8, 23.5,
  22.7 mm).
- hand_prop: auburn's left hand in the paper boat (65 of 104 frames, up to 20.4 mm): the boat is held.
- body_set: the set boxes are the bake's boxes, so the seated characters' feet and trousers are inside the stool
  boxes on every frame (boy 62.6, white 52.6, auburn 40.9 mm). Real penetration of the stool mesh needs the set
  mesh instead of its box; the tool measures what the bake collides with.

## Runtime and determinism

| run (104 frames, `--jobs 1`, 3 audits in parallel on one machine) | total | evaluate | hair | garment_body | body_body | rest | hand_prop | body_set |
|---|---|---|---|---|---|---|---|---|
| released off | 5091 s | 655 | 1896 | 1811 | 599 | 49 | 27 | 24 |
| released on | 4882 s | 871 | 1482 | 1803 | 581 | 59 | 26 | 23 |
| candidate off | 4491 s | 679 | 1293 | 1782 | 599 | 47 | 27 | 23 |
| candidate on | __CAND_ON_T__ |

About 45-50 s a measured frame with three audits sharing the machine. `--jobs N` splits the frames into N Blender
processes (each warms up on the frame before its chunk); `--step`, `--frames` and `--classes` cut the cost (hair only:
~20 s a frame). Building the shot.blend from a run folder (shot_render `--blend-only`) took 56-119 min per chain and is
not included.

Deterministic: a SHA-256 per frame over every evaluated query vertex, and one over all frames. On the real shot,
frames 101-111 with `--jobs 2` gave the same frame hashes, entries and depths as the full `--jobs 1` run (only the
first frame of a chunk has no jump value). The unit test checks `--jobs 2` == `--jobs 1` and `--step 2`.

## Test

`pipeline/production/tests/test_contact_audit.py`: synthetic scene (two rigs, keyed hair, garment, lining, hand,
prop, floor box, masked skin + hidden proxy, glasses), 37 checks, ~8 s, no assets:
`python3 tools/bpy_blender.py -b --factory-startup -P pipeline/production/tests/test_contact_audit.py` (or
`blender -b --factory-startup -P ...`). It covers every class, both depth rules (including a 300 mm deep point and
a sharp edge where the nearest face's sign is wrong), the rest rule, staging, known rules, depth and jump pops,
`compare`, the markdown, `--jobs` and `--step`.

## Usage

```
# a shot.blend (its bake from shot_render.json beside it)
python3 pipeline/production/contact_audit.py audit --blend <shot.blend> --out a.json --md a.md --step 2 \
    --known docs/evaluation/production/T-218/known_e912.json
# a run_shot run folder or a bake package (builds the blend with shot_render --blend-only)
python3 pipeline/production/contact_audit.py audit --run-dir <run> --out a.json [--hair-pushout on]
# push-out pops and per-class change between two audits of the same shot
python3 pipeline/production/contact_audit.py compare off.json on.json --md cmp.md [--snap-frames 45,46,...]
```

`--snap-frames` replaces the bake's snap frames (today's bakes record none for s020; the T-194 list is the
earlier bake's). `--blender` takes a command, e.g. `'python3 tools/bpy_blender.py'`.

## Notes and limits

- Roles come from metadata (deforming armature, `is_hair`, `ps_garment_item`, `ps_collision_proxy`, MASK
  modifier, the rig profile's hand bones, the bake's box and prop names); no character is named in the code.
  `known_e912.json` is per-production data.
- Library overrides: a shot.blend links the masters and overrides them; only local (override) objects are measured,
  the linked originals keep the rest state.
- Hair vs hair is not a class. Hidden objects (push-out caps, anchor proxies) are never surfaces.
- Staging is split from hair_other only for another character's BODY (garments stay in hair_other).

## Files

- `results/*.md`: the four audits and the two compares (with T-194 snap frames).
- `results/*.json.gz`: the full audit JSONs (per frame rows, 0.9-1.4 MB each before gzip) and the compare JSONs.
- `known_e912.json`: the accepted case moved apart (boy's rigid hair in his head, T-191).
