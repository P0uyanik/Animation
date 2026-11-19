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
| `top`, `shirt`, `dress` (round collar) | `collar_seat` | the collar is set on the neckline and laid over the layers under it (body, the item's own main piece, the `over` items); it is carried by the chest and the shoulders, not by the head or the arm, and a reach key keeps it over the posed layers. Replaces `collar_clear` on that item | `collar.py` |
| `shorts` | `cuff_gather` | each cuff band is resized to its thigh (measured on the body) and the shell is gathered into the two bands, with a recessed cleft between the lobes; the bands never overlap | `cuffs.py` |
| `trousers` | `ankle_close` | a close inner cuff in the trouser fabric on the leg skin from above the hem into the shoe (pieces `garment.<item>.ankle.L/R`, part `ankle`), skinned like the skin under it, so no skin shows between hem and shoe in any ankle pose | `ankle.py` |

Field details and defaults are in each module's docstring.

Notes
- `collar_seat` relies on the `garment/1` round-collar grid (73 x 7 columns/rows, solidified) and `cuff_gather` on the
  `garment/1` cuff ring layout (33 sections of 8 vertices); both raise a clear error on another layout.
- The collar is laid over what stands under it. Where an `over` item's neckline stands well clear of the body (a vest
  with a large ease), the collar rides on that neckline and its outer edge stands off the shoulder behind it.
- The reach key of the collar is driven like the `garment/2` reach correctives (arm forward swing, Blender driver);
  the engine export carries it as a morph target but nothing drives it in the engine yet.
- `ankle_close` pieces get the shared surface fibres of their fabric, like any `garment/1` piece.
- The opt-in limb skin of T-119 is not part of this package: `materials.assignments.skin_limbs` (hands) is read by
  `build_character.py`, its preset comes from `pipeline/charsys/materials/skin_presets_r3.json`.
