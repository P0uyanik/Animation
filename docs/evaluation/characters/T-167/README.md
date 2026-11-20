# T-167: hair round 7 (closer to the reference images)

Branch `t-167-claude-hair-r7` from `t-160-claude-hair-r6@2dccd74`; input main `3c698c7`. Opt-in only; nothing
published, no current or candidate version changed. Target brief: T-169 study (`t-169-codex-hair-study@38759ccc`,
read-only). Also folded in: bow front seat (owner decision), ear tuck for both girls (T-159 input).

## Generator
`pipeline/charsys/groom_r6.py` (groom/5): new opt-in key `clump` on `masses` / `locks`
(`bend_m`, `twist_deg`, `lumps`, `lump_wavelength`, `seed`): each clump gets its own bend, twist and thickness
variation from a fixed sequence (no random numbers). Specs without the key build as before.

## Overrides
`tools/make_overrides.py --base-dir <T-155 candidate specs @0677274>` writes `overrides/<id>.hair_r7.override.json`
from the T-160 r6 overrides. Build: `build_character.py --spec <T-155 candidate spec> --override <file> --out <dir>`.

| character | change against r6 |
|---|---|
| boy | blunt uneven clumps instead of pointed leaves (`hold`, `taper_power`, `clump`), shorter outward flicks, extra lower back row, 3 crown tufts, uneven fringe with a longer centre lock; pickup keep-out kept |
| auburn girl | thinner ringlets on a wider coil with fuller ends, back curls 9 cm longer, off-centre part with higher sweeps (more forehead), side hair moved behind the ears, smaller bun with fewer grooves and a thin band, about half the fuzz, glossier material override |
| third girl | 19 soft blunt fringe wisps instead of spikes, wider / thicker / more side and back locks, side hair moved behind the ears, bow on her right at the front hairline below the bun, tilted, partly over the fringe |

## Evidence
Per character `<char>/`: `preview.jpg` (2 spp, seen before the long renders), `strict.jpg` (16 spp, 360 px; columns
reference, candidate + hair r6, candidate + hair r7, AI target; A-pose masters, `tools/strict_r7.py`),
`hair_crops.jpg` (100 %, 600 px, 16 spp; front, 3/4, side, back; rows reference, AI target, r6, r7;
`tools/hair_crops.py`), `flicker.json`. Render: strict about 16 min each; crops 864 / 527 / 755 s.

For the owner's choice per character: `<char>/r6_vs_r7.jpg` (left r6, right r7; front, 3/4, side, back at 100 %;
same cameras and light; composed by `tools/pairs.py` from the crop renders, no new render). Full figure: the r6 and
r7 columns of `strict.jpg`.

What the crops show against the references:
- boy: closer in mass (round mop, chunky clumps, fuller back and nape). Not matched: the reference outline still has
  small pointed tuft ends and a tall top tuft, r7 is now too rounded and lumpy; fringe shorter than the reference.
- auburn girl: more forehead, ears visible, defined separate curls, longer back, smaller bun. Not matched: curls are
  thinner and sparser than the chunky reference ringlets; loose thin strands hang in front of cheek and sleeve in
  3/4; crown still fuzzy rather than combed yarn; gloss gain is small.
- third girl: soft fringe, fuller sides and back, bow at the reference seat. Not matched: in side view the ear tuck
  leaves a bare notch between temple and back hair that the reference does not have; back waves are bulkier and
  less fine than the reference; fringe wisps read as flat strips.

## Checks
| check | result |
|---|---|
| `test_hair_r6.py` (incl. `clump`, r7 overrides) | 42 / 42 |
| `test_hair_r5.py`, `test_versions.py`, `test_guard_allowlist.py` | 79 / 79, 121 / 121, 21 / 21 |
| r6 overrides, old against extended generator (`tools/r6_unchanged.py`, `checks/r6_unchanged_*.json`) | boy 10 objects identical; third girl 30 identical; auburn girl identical except the two flower objects, which also differ between two builds of the old module (existing build-to-build variation) |
| boy pickup sightline (`checks/boy_pickup_sightline.json`), eye L / R at pitch 30 / 40 / 50 | r7 1.0 / 0.891, 0.89 / 0.781, 0.608 / 0.539; r6 0.976 / 0.889, 0.853 / 0.721, 0.588 / 0.525; keep-out 0 |
| keep-out violations (build report) | boy 0 (r6 0), auburn girl 0 (0), third girl 20 (58) |
| dynamics chains | boy 34 (r6 26), auburn girl 21 (26), third girl 49 (38) |

## Flicker (T-160 `tools/flicker_turntable.py`, same settings as T-160)
8 frames, 2° per frame from yaw 150°, Cycles 16 spp, 400 px. Hair region, denoised; r6 values from the T-160 README.

| character | column | flip share median / max (limit 0.405) | worst tile (limit 0.88) | held noise median / max (limit 0.056) | hair issues |
|---|---|---|---|---|---|
| boy | r6 | 0.204 / 0.206 | 0.51 | 0.047 / 0.049 | 0 |
| boy | r7 | 0.212 / 0.225 | 0.57 | 0.052 / 0.057 | 1 (held noise, one frame) |
| auburn girl | r6 | 0.246 / 0.250 | 0.51 | 0.055 / 0.069 | 2 |
| auburn girl | r7 | 0.135 / 0.143 | 0.42 | 0.050 / 0.052 | 0 |
| third girl | r6 | 0.059 / 0.061 | 0.47 | 0.027 / 0.030 | 0 |
| third girl | r7 | 0.050 / 0.051 | 0.39 | 0.031 / 0.032 | 0 |

Result: both girls no worse than r6 (auburn girl clearly better; third girl held noise +0.004, far below the limit).
The boy is slightly worse than r6: all measures up, held noise 0.001 over the limit in one frame (0.5 % of hair
pixels are "held"), flip share within 0.02 of r6. "No worse than base" is therefore not met for the boy.
Outside the hair region: boy cloth flip share 0.262 (limit 0.161; r6 0.251); none for the girls.

Boy, longer measure (24 frames, 16 spp; scratch runs, not in the repository), hair held noise median / max:
r6 0.041 / 0.049 (0 issues); r7 0.053 / 0.066 (4 issues); flip share r6 0.204 / 0.208, r7 0.210 / 0.225.
32 spp, 8 frames, r7: 0.059 / 0.063. Two trial fixes did not pass and were dropped: calmer crown tufts
(0.052 / 0.064) and calmer top clumps with narrower gaps (0.054 / 0.061). The difference sits on the top of the
head: r6's broad top leaves give about 300 calm held pixels (noise about 0.03), r7's top clumps about 130 at 0.05.

## Not done / limits
- Boy flicker slightly above r6 (above); not tuned further.
- Visual gaps listed under Evidence; one pass per character after the T-169 brief, no second visual iteration.
- No shot baked or rendered; more dynamics chains for boy and third girl, cost not measured.
- Full gate (`tools/check_all.py`) not run. Strict sheets use an own driver, not `recipe.py`; T-165 kit not on main.
- Based on unmerged T-155 / T-160; rebase and re-check when they land.
