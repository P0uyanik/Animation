# garment/3 (T-119): garments round 3

Opt-in shared garment generator, registered as `garment/3` (module `garments_v3`, `pipeline/charsys/versions.py`).
It **reuses `garment/2` by import** (`pipeline/charsys/garments_v2`, unchanged, which reuses `garment/1`): every item
is built by the `garment/2` code from the *garment/2 view* of the clothing block (the block without the new fields),
then the new item fields reshape that item's pieces or add new ones. A `garment/3` block without any new field builds
the `garment/2` geometry (only the `ps_garment_generator` tag and the build report differ). No character data in the
code: every size comes from the spec, the rig or measures taken on the body and the built pieces.

Pin it with `"generators": {"garment": "garment/3"}` **and** `"clothing": {"generator": "garment/3", ...}`.

| item type | field | what it does | module |
|---|---|---|---|
| `top`, `shirt`, `dress` (round collar) | `collar_seat` | the rounded (Peter Pan) collar: set on the neckline and laid over the layers under it (body, the item's own main piece, the `over` items; `over` may be empty); carried by the chest and the shoulders, not by the head or the arm; a reach key keeps it over the posed layers; `thickness_m` for a knitted collar. Replaces `collar_clear` on that item | `collar.py` |
| `top`, `shirt`, `dress`, `hoodie` (sleeve cuff bands) | `rib_cuff` | a close cuff band from each sleeve's seam ring towards the hand (pieces `garment.<item>.ribcuff.L/R`, part `rib_cuff`), with `ribs` wales along the arm (`ribs: 0` = a plain cuff) | `ribs.py` |
| `shorts` | `cuff_gather` | each cuff band is resized to its thigh (measured on the body) and the shell is gathered into the two bands, with a recessed cleft between the lobes; the bands never overlap | `cuffs.py` |
| `trousers` | `ankle_close` | a close inner cuff in the trouser fabric on the leg skin from above the hem into the shoe (pieces `garment.<item>.ankle.L/R`, part `ankle`), skinned like the skin under it, so no skin shows between hem and shoe in any ankle pose | `ankle.py` |
| `tights` (new item type, T-126) | (the item itself) | a close knitted shell on the legs and feet from `waist_z_m` to the toes (piece `garment.<item>.main`), skinned with the skin under it and masked like any item; not part of the `garment/2` view | `tights.py` |
| `dress`, `skirt` | `skirt_pattern` (T-126) | a knitted relief on the skirt piece: `panels` repeats of a rope cable and a leaf column, moved outward by `relief_m` after the piece is refined (`subdivide`) | `pattern.py` |
| any item | `fibre_uv` (T-126) | writes the `ps_fibre` UV map on every piece (metres: U round the limb or body, V along it), so a material with `fibre.coordinates: "uv"` runs its knit along the sleeve and down the body | `fibre_uv.py` |
| `boots`, `shoes` | `sole_stitch` (T-126) | a row of raised yarn stitches round the upper just above the sole (pieces `garment.<item>.stitch.L/R`, part `stitch`) | `stitch.py` |
| `dress`, `skirt` | `cloth_sim` (T-126) | marks the skirt piece for the opt-in baked simulation of `pipeline/charsys/cloth_sim` (property `ps_cloth_sim`, pin attribute `ps_cloth_pin`); the build simulates nothing | `cloth_tag.py` |

Field details and defaults are in each module's docstring.

Notes
- `collar_seat` relies on the `garment/1` round-collar grid (73 x 7 columns/rows, solidified) and `cuff_gather` on the
  `garment/1` cuff ring layout (33 sections of 8 vertices); both raise a clear error on another layout.
- The collar is laid over what stands under it. Where an `over` item's neckline stands well clear of the body (a vest
  with a large ease), the collar rides on that neckline and its outer edge stands off the shoulder behind it.
- The reach key of the collar is driven like the `garment/2` reach correctives (arm forward swing, Blender driver);
  the engine export carries it as a morph target but nothing drives it in the engine yet.
- `ankle_close` and `rib_cuff` pieces get the shared surface fibres of their fabric, like any `garment/1` piece.
- `rib_cuff` adds a band; it does not gather the sleeve (use `sleeve_puff_m` for a fuller sleeve end) and it keeps the
  `garment/1` seam ring.
- The opt-in limb skin of T-119 is not part of this package: `materials.assignments.skin_limbs` (hands) is read by
  `build_character.py`, its preset comes from `pipeline/charsys/materials/skin_presets_r3.json`.
- T-126 fields: `skirt_pattern` runs after the item's build-time drape, so the relief is not smoothed away; it moves
  both walls of the piece outward only. `fibre_uv` gives knit *columns* along a piece; the `knit` material kind draws
  its rows from the third coordinate, which a UV map does not have, so stitch rows need shader work
  (`materials/builder.py`, not part of this package). A refined skirt has about 77,000 vertices at `subdivide: 2`.
