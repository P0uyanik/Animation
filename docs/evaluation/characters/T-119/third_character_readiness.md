# T-119: garment readiness for `girl_white_hair_blue_dress` (design note, not a spec)

Scope addition by the owner, 2026-11-19 ~11:55Z. Read as design input: uploads 09 (dress construction and
deformation blueprint) and 16 (W05: dress, tights, boots), plus the upload README. No model, spec, version or render of
her was made, her dress and skirt were not built, and her reference files are untouched. "Supported" below means the
parameter exists and validates today; "built here" means T-119 added it and exercised it on the auburn girl.

## What was built here: two reusable components (garment/3)
Both are parameters on shared item types, with no character data in the code. They were exercised on a fixture (the
auburn girl 0.12.0 without her vest, [override](components/girl_auburn_bun_glasses.components-demo.override.json),
[preview](components/components_preview.jpg), 4 spp). The fixture is not a candidate for her.

| component | how to ask for it | what it gives | carries over to the third character |
|---|---|---|---|
| Rounded (Peter Pan) collar | `collar: {type: "round", width_m, gap_m, tip_round}` on a `top`, `shirt` or `dress`, plus `collar_seat` (`over: []` when nothing is worn over it, `thickness_m` for a knitted collar) | two rounded lobes meeting at the front centre, lying on the bodice (fixture: median 1.8 mm over its gap), carried by chest and shoulders, with a reach key | yes, as is: her collar sits on the dress bodice with nothing over it, which is the fixture's case |
| Rib cuff | `rib_cuff: {height_m, ribs, depth_m, thickness_m, tighten, overlap}` on a `top`, `shirt`, `dress` or `hoodie` that has sleeve cuff bands | a close band from the sleeve's seam ring towards the hand with `ribs` wales along the arm (`ribs: 0` = a plain turned cuff), skinned with the forearm and hand | yes: her sleeves end in a rib band (16); its height, wale count and depth are to be read off 16 when her spec is written |

For the auburn girl the same two components are available: her blouse collar uses `collar_seat` in the T-119 candidate,
and `rib_cuff` with `ribs: 0` would give her blouse a plain cuff band. Neither is forced on her.

## What her dress needs next (not built)

| part (reference) | today | missing |
|---|---|---|
| Stockinette bodice and sleeves, slightly full sleeve gathered into the cuff (16, 09 panel 02) | `dress` item with sleeves, `sleeve_puff_m`, closed armhole, drape; material kind `knit` exists (`cotton knit` preset) | a knit preset at her stitch size with visible V stitches running down the body and along the sleeve. The `knit` pattern is laid in object space for garments (only groom pieces carry the `ps_fibre` UV map), so on a sleeve it does not follow the arm: needs that UV on garment pieces or a per-piece direction |
| Flared skirt in cable / leaf pattern, joined to the bodice at a raised waist with gathers (16) | `dress` skirt part: `flare`, `gathers` (count, depth), drape | the cable/leaf relief. In 16 it stands clearly proud of the ground stitch, so a bump alone will probably not read at figure scale: a displaced panel pattern (repeat count round the skirt, cable width, leaf rows) on the gathered skirt rings is the main new piece of work |
| Rib hem on the skirt (16) | `bands.hem_rib` on skirts and dresses (`ridges`, `height_m`, `relief_m`, `gather`) | nothing structural; set rib height and ridge count from 16. `rib_cuff` and `hem_rib` should use the same wale pitch so cuff and hem read as one knit |
| Peter Pan collar (16, 09 detail circles) | built here | per-character sizes only |
| Rib cuffs (16, 09 detail circles) | built here | per-character sizes only. The sleeve itself is not gathered by `rib_cuff`; a fuller sleeve end comes from `sleeve_puff_m` / `sleeve_puff_peak` |
| Lining / inner hem turn-up (09 panel 02) | solidified shells with rounded edges | not needed at shot scale; skip unless a camera looks under the skirt |
| Cream knit tights (16) | no item type. `trousers` at a small ease cover the leg but end at the ankle | a `tights` item: a close shell on legs and feet (the same skin-following shell that `ankle_close` builds, taken from the waist down to the toes), fine knit preset. Small: the shell code exists |
| Tan shaggy boots with a fold-over cuff and stitched sole (16, 09) | `boots` with `cuff_roll` (garment/2: turned-down fleece cuff), `boot fleece` and `cuff fleece/3` presets, soles | a longer pile on the cuff than on the shaft (16), and the visible sole stitch line; both are material and detail work on existing pieces |
| Skirt and sleeve deformation (09 panel 03: arms up, sit, kneel, walk) | skinning by nearest skin weights (a skirt follows the thighs), post-skinning collision, reach correctives for torso items | untested for a wide flared skirt in sit and kneel: most of it has no skin near it, so it may need its own carry (hip weights with a leg-swing corrective, or dynamics chains as the hair uses). This is the largest open question for her; test it on a plain flared skirt before any pattern work |

## Suggested order when her build is approved
1. Plain `dress` with the Peter Pan collar and rib cuffs (both ready), plain flared gathered skirt with `hem_rib`, boots with `cuff_roll`; check silhouette against 16 and 09 panel 01.
2. Skirt carry in walk and sit (09 panel 03), before any surface pattern.
3. `tights` item.
4. Knit direction on sleeves and bodice, then the cable/leaf relief on the skirt.

## Limits of this note
- Read from two images and the upload README only; no measurement of her proportions was taken, and no numbers above
  are fitted values.
- The rib cuff was only seen on the auburn girl's blouse sleeve at 4 spp; its wales are shallow at the default depth
  and need a closer render against 16 once her sleeve radius is known.
- Whether a displaced cable pattern survives the drape step is untested.
