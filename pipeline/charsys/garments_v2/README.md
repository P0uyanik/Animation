# garment/2 (T-093): garment outlines and accessories

Opt-in shared garment generator, registered as `garment/2` (module `garments_v2`, `pipeline/charsys/versions.py`).
It **reuses `garment/1` by import** (`pipeline/charsys/garments`, unchanged): every item is built by the `garment/1`
code from the *garment/1 view* of the clothing block (the block without the new fields), then the new item fields
reshape that item's pieces or add new ones. A `garment/2` block without any new field builds exactly the `garment/1`
geometry (only the `ps_garment_generator` tag and the build report differ). No character data in the code: every size
comes from the spec or from the generic body measures.

Pin it with `"generators": {"garment": "garment/2"}` **and** `"clothing": {"generator": "garment/2", ...}`.

| item type | field | what it does | module |
|---|---|---|---|
| `sneakers` | `stripes` | slanted felt bands laid on the side walls of the upper (part `stripe`) | `shoes.py` |
| `backpack` | `flap`, `tab`, `pocket_flap` | rounded lid flap over the bag, tab closure with a loop, flap over the front pocket (parts `flap`, `tab`, `buckle`, `pocket_flap`); use with `zip: false` for a flap bag | `pack.py` |
| `trousers`, `shorts` | `hem_break` | the hem settles on the shoe: flare, soft slanted folds, front drop | `outlines.py` |
| `shorts` | `leg_split` | bloomer legs read as two legs: the inner halves are drawn to their leg axes (never past the measured inner leg surface); shorter gusset | `outlines.py` |
| `boots` | `cuff_roll` | turned-down cuff rolled over the shaft rim (part `cuff`, falls back to `band`); replaces the `garment/1` cuff tube | `outlines.py` |
| `top`, `shirt`, `vest`, `hoodie`, `dress` | `correctives.reach` | shape keys `corrective.reach.L/R` that keep the piece on the torso when the arm reaches, driven by the arm's forward swing | `correctives.py` |

Field details are in each module's docstring. `evaluate.py` holds the reach pose and the flare measure (distance of a
piece to the posed torso skin) used by `pipeline/charsys/tests/test_garments_v2.py` and the T-093 evidence.

Notes
- New pieces are tagged, weighted and given surface fibres like `garment/1` pieces. Rigid items (backpack, sneakers)
  give their new pieces the item's weight anchor.
- The reach correctives are solved through each vertex's linear-blend skinning matrix for the configured reach and
  driven in Blender (TRANSFORMS driver, local space, swing-twist about the bone's length axis). The engine export
  carries garment shape keys as morph targets, but nothing drives them in the engine yet.
- `pipeline/charsys/tools/garment_pose_eval.py` selects `garment/1` pieces by their generator tag; it does not see
  `garment/2` pieces yet.
