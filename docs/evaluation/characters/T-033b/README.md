# T-033b: girl felted hair, round 2 (groom/1)

Branch `t-033b-claude-hair-r2`, from `t-033-claude-hair-v2`. The girl's spec changes **only in `hair`**; her version number is not bumped, so the face agent's spec work does not conflict.
Nothing was published or approved. **The final visual approval is the owner's.**

## Shared primitives (generic spec keys, no character names)
All the new keys are optional. When a key is absent the geometry is unchanged, so the boy stays byte-identical.

- **Wave shaping for hanging locks** (`groom.py`, `locks.curl`):
  - **`ellipse`**: below 1, it flattens the helix towards the lateral plane, so a lock reads as a soft S-wave instead of a round coil.
  - **`tip {from, radius, pitch, ellipse}`**: multipliers blended in smoothly over the end of the lock. With radius up, pitch down and ellipse 1, a wave ends in a round ringlet.
  - Both work with the existing `wobble`/`sway` irregularity and the felt section.
- **Curtain / side-swept felt fringe** (`groom_felt.py`, `felt_volume` shape `fringe`):
  - **`tip_az`/`tip_el`/`tip_lift`**: tips placed on the head instead of on the face (`tip_x`/`tip_z`), so a fringe sheet can fall from the part around the temple.
  - **`root_el` as a list as long as `root_az`**: one elevation per root, so the roots run along a part line.
  - **`tip_jitter`**: seeded per-strand shortening, so the tip line is irregular, not a blunt band.
- **Felt bun bundles** (`buns[i].felt_lobes [{offset, radii, swirl}]`, relative to the bun frame):
  - extra felted masses of the same bun;
  - they are inside the bun's dynamics vertex range, so they move with the bun chain.

## Girl hair (spec tuning)
- **Fringe:** the single blunt fringe sheet is replaced by a curtain of two felt sheets from the part at az −17…−27.
  - The long sheet sweeps to her left; the short one sweeps to her right.
  - Both have irregular, scalloped tips that reach down to the temples.
- **Crown:** the crown gather now reaches down over the temples (hairline el about 0° at az 72–95) and is higher (50 mm at mid-height).
- **Temple masses:** larger.
- **Bun:** frame r 0.088 / h 0.14, plus three felted lobes (left, right and back), so it is wider and bundled. The band now sits tighter.
- **Locks:** temple, side, back and nape locks are chunky felted waves (`ellipse` 0.3, pitch 0.10) that end in ringlets (`tip`).
  - They are wider (34–46 mm) and rounder in section, with a slower, smoother felt irregularity.
  - There are 15 back locks (was 12). They are rooted under the back gather, which tapers out so it leaves no shelf.
  - There are 5 side locks per side (was 6).
- **Dynamics:** the T-021 dynamics override still applies by structure name: **40 chains** (was 39, because of the lock counts) and 4 colliders in the exported package.

## Evidence
- **`turnaround_vs_reference.png`:**
  - front, 3/4, side and back next to the sheet30 views;
  - 640 px, shared calibration `character_neutral/1`, 32 samples.
- **`hair_closeup_vs_reference.png`:** ortho 0.42 m close-ups next to the `ref_30.webp` crops (70, 600, 330, 860) and (965, 615, 1155, 805).
- **`fidelity_hair_summary.json`:**
  - the T-032 tool, run read-only from a scratch worktree of `origin/t-032-claude-fidelity`;
  - three runs: before, iteration 5 and final.
- **`colour_checks.json`, `render_timings.json`, `groom_generic_test.json`.**
- **Iteration renders:** 5, each a front, 3/4 and back crop at 16 samples. Then one final build with a bun correction (see below), and the final renders.

### Fidelity numbers (hair)
| | before (0.8.0) | final |
|---|---|---|
| overall score | 62.5 | **64.8** |
| hair area vs. reference (median) | −35.8 % | **−19.5 %** |
| hair IoU (mean of 5 views) | 0.538 | **0.594** |
| hair region area ratio | 0.64 | **0.80** |
| hair width at eye level (median / front) | +0.5 % / +8.8 % | +5.3 % / +15.0 % |
| hair dE00 | 2.86 | 2.55 |
| figure IoU (silhouette) | 0.786 | 0.817 |

Hair IoU went up in every view: front 0.43→0.47, 3/4 0.51→0.60, side 0.48→0.53, back-right 0.57→0.64, back 0.70→0.73.

**Note on "hair width at eye level −71 %":** this tool, on this build and the 0.8.0 build, measures about 0 % (front +9 %). I could not reproduce −71 %; it was probably taken from a different view or region mask.
Visually, the temple hair was narrow, and it is now fuller (the curtain sheets, the crown down over the temples, and larger temple masses). The eye-level width is now slightly *wider* than the reference's.

**Iteration 5 (score 57.9):** that bun was 55 mm taller. The tool normalises by figure height, so a taller bun shrinks the whole figure: arms, eyes and leg gap all got worse.
The final bun is wider rather than taller, which recovers that loss. **Lesson:** keep the top of the hair at the reference's height.

## What still differs, and why
1. **Back of the head** (most visible).
   - **Reference:** long, separate wavy locks start right under the bun and run down the back.
   - **Ours:** a smooth combed gather shell, then the locks emerge at about ear level, with a row of rounded lock roots visible where they leave the shell.
   - **Why:** a lock follows the scalp from `el_root` and then hangs. A gather shell and locks are two separate surfaces, and they never blend into one combed-then-hanging piece of felt.
   - **Proposal:** a `felt_volume` shape `gather_locks` that splits the lower edge of a gather into N lock tubes (the gather's grooves become the lock boundaries). The shell and the locks would then share one surface, and the locks would keep their own dynamics chains.
2. **Waves vs. the sheet's softness.**
   - The locks now wave and end in ringlets, but they are still distinct tubes with a fuzzy surface.
   - The reference waves merge into one cascading mass, with locks overlapping and flattening against each other.
   - **Why:** locks do not collide or flatten against their neighbours at build time.
   - **Proposal:** a build-time relaxation pass (push overlapping lock sections apart and flatten them against each other, like the existing fringe conform step), plus larger `hang_jitter` layering.
3. **Fringe coverage.**
   - **Reference:** the swept fringe covers more of the forehead on her left, down to the brow.
   - **Ours:** a bare triangle of forehead shows under the part.
   - **Fix:** a spec tune of `tip_el`/`tip_az` on the long sheet (lower centre tips). It is not done here because the iteration budget ran out.
4. **Bun shape.**
   - **Reference:** rolled bundles with visible coils.
   - **Ours:** three smooth lobes on a felt ball, with the band still showing as a ring at the front.
   - **Proposal:** lobes along a short spiral path (a coiled rope section of the felt bun).
5. **Fuzz texture** (unchanged from T-033): it reads a little like towelling. This needs a direction input in the shared fibre GN group, which belongs to the materials owner.
6. **Close-up framing:** the `head_back` close-up uses the same camera as T-033, so the top of the wider bun is cropped.
7. **Not hair** (other owners): face/skin colour, eye size, arm length; the flower colour check (dE00 26, the same as T-033).

## Checks
| Check | Result |
|---|---|
| `groom_generic_test.py` (+5 synthetic T-033b checks: ellipse wave, ringlet tip, curtain fringe, bun lobes in the dynamics record, validation) | PASS 24/24 |
| `groom_dynamics_test.py` (T-021) | PASS |
| `verify_charsys.py` (boy) | PASS 68 / FAIL 0, master byte-identical |
| `test_export_engine.py` | ALL PASS 8/8 |
| girl + dynamics override → `export_engine.py` | 40 chains, 4 colliders |

No threshold was changed. The frozen boy versions, `tests/data`, the baselines and `docs/references` are untouched.

## Reproduce
Same commands as `docs/evaluation/characters/T-033/README.md`, with `--tag T-033b`.

Fidelity:
`python3 tools/fidelity/run.py --character girl_auburn_bun_glasses --build <master.blend> --out <dir>`, run from a worktree of `origin/t-032-claude-fidelity`.
