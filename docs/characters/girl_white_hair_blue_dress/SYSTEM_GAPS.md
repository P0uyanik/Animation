# White-haired girl: gap analysis vs the shared character systems (T-057, 2026-11-17)

Study only: nothing was built or rendered. For each feature of her references (keys as in
[REFERENCE_BEHAVIOUR.md](REFERENCE_BEHAVIOUR.md); data in `assets/characters/girl_white_hair_blue_dress/references/`)
this says whether today's shared systems can express it.

**Versions considered** (the ones the girl `girl_auburn_bun_glasses` builds with on `origin/staging`, recorded by
T-043 as pins): `body_generic/1`, `face_generic/1` (mouth `lips_jaw/2`, blink `lid_seam/1`), `groom/1` (yarn and
felt finish, T-033), `garment/1` (incl. T-024/T-025 options and T-034 `drape`), `accessories/1`, `rigify_human/1`,
`presets/1` (`pipeline/charsys/materials/presets.json`), `export/4`. `docs/CHARACTER_SYSTEM_VERSIONS.md` is on the
T-043 branch and not yet on `staging`; the version names follow it.

Verdicts:
- **S** = spec only (existing parameters; values from `measurements.json`, `landmarks.json`, `color_targets.json`).
- **S?** = spec only on paper, but the look is unproven for her and needs a check render before V6 is planned.
- **V** = needs a new version / opt-in feature of an existing system.
- **T** = needs a new garment or accessory type.

## 1. Feature table
| Feature | Reference evidence | Verdict | System and parameters / what is missing |
| --- | --- | --- | --- |
| Body proportions | 2.66 heads incl. buns, 2.99 excl.; ~0.97× the girl's height; short limbs, feet together | **S** | `body_generic/1` `body.params` (head, neck, torso, arm, leg, foot); the girl is 2.62 heads, so the same range |
| Neck, hands, ears | thin short neck; small 4-finger + thumb skin hands (`p13_hands_feet`); round ears beside the cheeks, partly in the hair (`w01`, `w10` "Hair / Ears") | **S** | body `neck`, `hand`; `face.ears` |
| Eyes | very large round blue irises, wide set (eye spacing / ear width 0.42 vs girl 0.365), two highlights, glossy | **S?** | `face.eyes` (`iris.srgb/dark_srgb/radius/pupil`, `highlights`, eye scale/spacing). Check that eye scale this large stays inside the lid/lash geometry limits of `face_generic/1` |
| Lashes | thick dark upper lash line, 3–4 outer flicks, no lower lashes | **S** | `face.eyes.lash` (`thick_m`, `flare`, `outer.count`), `lower_strands` off |
| Brows | thin, light brown, mostly under the fringe | **S** | `face.brows`; the fringe must be thin enough at the brows to show `BrowDown`/`BrowSad` (`m04_anger`, `f14_e4`) |
| Blush | strong round cheek blush (`cheeks_blush` colour) | **S** | `face.blush` |
| Mouth, open smile with teeth | small mouth; open smile with upper teeth/tongue (`w01`, `m04_laugh`) | **S** | `lips_jaw/2` cavity with teeth/tongue layers (`face.py` `cut_mouth_and_cavity`) |
| Expressions | `w04` 15 tiles, `w14` e1–e11 | **S** | shared presets Neutral, Blink, Squint, WideOpen, Smile, Frown, MouthOpen, Laugh, Surprise, Sadness, Anger, Confusion (+ optional Curious, SmileClosed, Thinking) |
| Pucker | `m04_pucker` | **V** | no pursed-lips action unit (13 AUs; `MouthO` opens instead of pursing). Optional preset `Thinking` has a small pursed mouth: check whether it is close enough; else new AU `MouthPucker` (face library + `face_generic/2`) |
| Lopsided mouth | `f14_m8`, `f14_m10` (one corner up/down) | **V** | `MouthSmile`/`MouthFrown` are not sided (`BrowUp` and `Blink` are). Sided mouth-corner AUs would be an opt-in `face_generic/2` feature (also useful for the boy's pout and the girl's Confusion) |
| Side glance, half lids | `f14_e8`, `f14_e11` | **S** | eye targets (`gaze_range_deg`) + partial `Blink` |
| Long wavy hair to the waist | soft S-waves, back mass + side locks (`w07` structure, `w02` back) | **S?** | `groom/1` `locks` style `wavy`/`curly` with `curl.ellipse` (soft S-waves), `rest_radii`, `hang_jitter`, felt finish (`felt_lock`). Expressible; reaching the reference's soft fuzzy wave volume is exactly the hair-v3 question (T-049/T-044) |
| Fringe + face-framing locks | full fringe to the brows, clumped wispy tips; side bangs framing the cheeks | **S?** | `felt_volume` `fringe` (`tip_jitter`, `tip_scallop`, grooves) + front `locks`; quality as above |
| Two pom-pom buns | round fuzzy balls high on both sides (no visible coil), tops ~0.18 H apart (w01) | **S?** | felt `bun` = `felt_volume` `mass` on bun frames (`swirl` 0, `lumps`), two entries in `buns`; the yarn `bun` (coiled ropes) is the wrong look. Fuzzy outline depends on the fibre halo below |
| Fuzzy fibre halo | "soft fuzzy halo, irregular wool density" (`h07_fibre`, `w10` M_Hair_Felt) | **S?** | `felt hair` preset fibres (`fibres_lod`, preset overrides). The halo is longer/denser than the girl's; if overrides cannot reach it, a new preset version (**V**, `presets/2`) |
| Hair motion | `w08`: 3-bone FK bun chains, back-mass chains, fringe/side-lock chains, collision hulls, damped settle | **S** / **V** | `groom/1` `hair.dynamics` (lock chains, colliders, spring parameters) = S. Bun chains are clamped to 1–2 bones: 3 bones = small **V** |
| Bow | blue felt bow, two loops + two tails, on her right side in front of the right bun | **S** | groom `bow` structure (`az`/`el` on the scalp, `size`, `loop`, `tail`, material) or `accessories/1` if it must be a separate prop |
| Flower (alternative, conflict §8.1) | 4-petal blue flower at the same place (`w05`–`w08`) | **V** | groom `flowers` only sits on a bun; a scalp position (`az`/`el`) would be new |
| Dress bodice | knit bodice, waist seam at 0.533 H, long sleeves gathered into cuffs | **S** | `garment/1` `dress` (bodice + skirt parts), `sleeve_length`, `sleeve_puff_m`, `bands.cuff`, `cuff_radius_m`, `seam_lines` (back seam `w02`, `w09`) |
| Peter Pan collar | flat round collar, two rounded halves meeting at the front | **S?** | `collar: {"type": "round", width_m, gap_m, tip_round, slope}`; check that a near-zero front gap reads as her collar |
| Full gathered / pleated skirt | full skirt from the waist seam to 0.735 H, soft flutes all round, ribbed hem band (`w01`, `w09` 01–03) | **V** | `garment/1` skirts are smooth lofted flares; `drape.gather` is documented for shells (bodices, tops) and is **not verified** on the lofted skirt part. Needs an opt-in skirt fullness feature (gathers/flutes at the waist seam, knife or box pleats as a variant) + hem rib band (`bands.hem` exists) |
| Cable-knit pattern | cable/diamond relief on the skirt, knit texture on the bodice (`w10` M_Dress_Knit, `w02` swatch) | **V** | presets have `wool yarn`/`cotton knit` weave and `surface_detail` lumps/streaks, but no cable relief pattern: a new preset (`cable knit`) or pattern mode = `presets/2` |
| Tights | off-white knitted tights from under the skirt into the boots | **S?** / **T** | no `tights`/legwear type. Workable as `trousers` with ~0 ease, ankle length and `cotton knit`, hidden at the top by the skirt (S?). A real second-skin legwear type (or a body-region skin material) is cleaner (**T**, low priority) |
| Fluffy boots | camel shaggy fleece boots, wide fluffy turned-down cuff, round toe | **S** | `boots` + `shaft_width_m`, `toe_volume_m`, `bands.cuff_radius_m`, `boot fleece` preset (as the girl's fur boots) |
| Materials | M_Hair_Felt, M_Skin_Flock (SSS), M_Dress_Knit, M_Tights_Cotton, M_Boots_Fleece, M_Eye_Glass, felt bow | **S** except cable knit | `felt hair`, `skin-felt` (opt-in `surface_detail`), `cotton knit`/`wool yarn`, `boot fleece`, `felt`; eye gloss in the face eye material |
| Rig | standard humanoid (`w06`), FK/IK, finger chains, eye targets | **S** | `rigify_human/1` |
| Behaviour | profile draft `content/personality/girl_white_hair_blue_dress.draft.json` | — | waits for the T-053 profile reader |

## 2. Prioritised list
**Hair v3 (T-044)** — her hair is the hardest part of her look and overlaps the other two characters:
1. **Long, soft S-wave felt locks to the waist with a layered back mass** (she and the girl both need long felt hair;
   most visible area in `w02` back views). Decide in T-049/T-044 between strand grooming and sculpted felt.
2. **Pom-pom buns ×2 with a fuzzy halo**: felt `mass` buns + a stronger fibre halo (shares the halo work with the
   girl's bun and the boy's felt hair).
3. **Full fringe with clumped wispy tips + face-framing side bangs**, thin enough at the brows to show them.
4. **Per-character halo strength** (preset overrides; else `presets/2`).
5. **Dynamics**: 3-bone bun chains (small `groom` version bump), long-lock chains with chest/shoulder colliders,
   bow follows the head.
6. Bow is already supported; the flower variant only if the owner chooses it (conflict §8.1).

**Garment work** (order by visual weight in her references):
1. **Full gathered/pleated skirt with a ribbed hem** (new opt-in skirt feature; reusable for future dresses and
   skirts).
2. **Cable-knit relief material** (`cable knit` preset, materials version bump; reusable for sweaters).
3. **Tights** via tight `trousers` first; a dedicated legwear type only if that fails at the knee/ankle.
4. **Peter Pan collar + gathered cuffs** (spec; verify look).
5. **Fluffy boots** (spec; reuse the girl's boot settings with her colours and wider cuff).

**Face** (smaller): verify very large eyes in `face_generic/1`; sided mouth corners (lopsided smile) and a pucker
AU as one opt-in `face_generic/2` feature, shared with the other characters' expression sheets.
