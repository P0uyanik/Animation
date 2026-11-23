# T-194: hybrid hair push-out (render-time, on the real meshes)

Branch `t-194-claude-hair-pushout`. Opt-in: `shot_render.py --hair-pushout [on | spec.json | {inline json}]`, or
`production.render.hair_pushout` in a shot file (forwarded by `run_shot.py`). Absent = the old path, identical.
Code: `pipeline/charsys/hair_pushout.py`; test: `pipeline/charsys/tests/test_hair_pushout.py` (37 checks, synthetic
scenes, no assets, < 1 s here; registered `local` in TESTS.manifest). Round history: `ROUND.md`.

## Method (short)

- Stage A (Python, per frame): every `DYN-*` chain is walked from its root with segment rays against all colliders
  (own figure, the other characters, props with caps, the bake's boxes); blocked joints slide out, lengths kept, bones
  re-keyed. Stage B (Geometry Nodes on every hair object): a ray from each vertex's anchor (chain centre line, or a
  static anchor 30 mm out from the rest surface) to the vertex; a blocked vertex is put 1.5 mm before the hit.
- Stateless per frame: no state is carried between frames.

### Rules added in session 3 (spec keys, all on by default)

| key | value | what it does | why |
|---|---|---|---|
| `static_inside` | `keep` | a static vertex whose anchor ray first meets a back face (anchor inside a collider) is left as baked | boy cap anchors inside the hood rim tube when the head turns: the old clamp put the cap 28 mm into the rim |
| (same switch) | | a vertex is clamped only when behind a surface (its own ray to the anchor first meets a back face) | anchor ray through a thin part (rim tube, ear edge) while the vertex is outside |
| `keep_outside` | `all` | the rule above for chain vertices too (`static`: static only) | white `hair_back_under_00` through the ear edge, s020 f50 +18 mm |
| `static_fade_m` | [0.002, 0.01] | a static clamp is faded in with the hit's distance from the anchor (none at <= 2 mm, full at >= 10 mm) | anchors within ~0.5 mm of a surface flipped sides frame to frame: ~30 mm pops |
| `other_skin_fade_m` | [0.004, 0.012] | a push against ANOTHER character's body skin that moves a vertex (stage B) or a chain (stage A, solved with and without the neighbours' skins) by d is applied in full up to 4 mm, faded to nothing at 12 mm: applied d (12 - d) / 8 between, never more than 4.5 mm | heads overlap (T-191 staging, boy fringe in the auburn head up to 73 mm): a deep clamp lets go when the neighbour leaves, +44 mm pops |
| `static_move_fade_m` | [0.004, 0.012] | the same move fade for every clamp of a static vertex; [0, 0] = off | a static vertex deep in a fold / under cloth that sweeps over the head lets go in one frame (+5..13 mm). **Owner decision pending (ON vs OFF, below)** |

Deeper overlaps with a neighbour (> 4 mm) are listed apart as **staging** (frames and depth), not fixed.

## Results (T-183 pin `c7b3cee2`, candidate bakes `cand2`, every 2nd frame)

Calm = not a body-snap frame +-1 (T-183 `snaps.py`). Apart (not in the columns): boy's rigid hair in his own head
skin (T-191), hair against glasses (not colliders), staging. Pops = frame x character entries where the push-out
adds > 5 mm to the largest vertex jump (f-2 -> f).

### e912 s030 (`results/e912_s030c2_*`, defaults)

| | off | on |
|---|---|---|
| calm frames > 1 mm (123 fr x 2) | 171 / 246 | 121 / 246 |
| max calm | 40.7 mm | 40.7 mm (auburn curtain in the blouse, f67, same in off) |
| pops > 5 mm | | 0 (largest +2.5 mm) |
| new surfaces | | none |
| apart | staging 87.0 mm 30 fr, boy head 47.0, glasses 1.4 | same |

### e912 s020 (`results/e912_s020c2_*`): ON vs OFF of `static_move_fade_m`

| | off (no push-out) | ON (defaults, `_fin_on`) | OFF (`[0, 0]`, `_nofade_on`) |
|---|---|---|---|
| calm frames > 1 mm (144 fr x 2) | 192 / 288 | 149 / 288 | 99 / 288 |
| max calm | 33.8 mm | 33.8 mm | 24.0 mm (auburn cap in own skin, f83) |
| pops > 5 mm | | 3: white +7.2 f109, +6.2 f185, +6.3 f205 | 17: auburn 14 (+5.0..13.4 mm: f93-105, 129, 151-159, 201-207; static cap / curtain letting go of a fold or of the blouse in one frame), white the same 3 |
| new surfaces | | boy fringe 3.3 mm in the auburn skin, 2 fr (shallow edge of the staging overlap) | the same (boy fringe 3.3 mm) |
| cost | | setup 46 s, stage A 3.1 s / frame | setup 22 s, stage A 1.6 s / frame (less load on the machine) |
| staging (apart) | 77.6 mm, 40 fr | 77.6 mm, 33 fr | 77.6 mm, 33 fr |

Cost of ON against OFF (frames where ON leaves hair deeper by > 1 mm, `tools/compare_runs.py`,
`results/e912_s020c2_fade_cost_vs_off.json`): 

| where | frames | max depth with ON | deeper than OFF by |
|---|---|---|---|
| **nape / fold**: auburn `hair_cap.001` in own skin | 81 (f35-207) | 33.8 mm | up to 30.2 mm |
| **nape / fold**: auburn `hair_curtain` in own skin | 72 (f17-207) | 15.4 mm | up to 7.6 mm |
| nape / fold: auburn `hair_back_sections` in own skin | 2 | 3.5 mm | 3.5 mm |
| white `hair_back_mass` in her own `ear.L` | 53 (f1-207) | 6.4 mm | 6.4 mm |

So ON trades the 14 auburn release pops for nape hair left inside the neck skin that OFF pushes out (calm 99 -> 149
of 288). R7 takes ON vs OFF to the owner (Step-1 answer "nape: push out").

Earlier full run before the session 3 fades (`results/e912_s020c2_on.m.json`): calm 99 / 288, max 24.0 mm, 20 pops.

## Determinism, identity, cost

- No flag = identical: main's `shot_render.py` (worktree of origin/main `c58cf48`) and ours without the flag, same
  bake, s020 f100-112: object list, bone poses and SHA-256 of every evaluated mesh (all and hair) equal at f100 / 106 /
  110 / 112 (`results/ident/main_off.h.json`, `our_off.h.json`).
- Ranges: the full-shot blend (f1-208) and a f100-112 blend give the same hashes at f110 (all meshes, hair, pose);
  two separate on-blends of f100-112 are identical at all four frames (`on1` / `on2.h.json`). A single-frame blend (f110 only): hair hash equal; the other meshes differ only by float noise
  (<= 1.8e-7 m, auburn finger bones and hands, from the bone keying of a one-frame range, not from the push-out).
- Cost (s020, 3 characters, 640x360): setup 46 s once (rest pass, anchor proxies); stage A 3.1 s per frame (s030
  4.0 s); stage B within timing noise (hair evaluation 1.46 / 1.52 s with it against 1.57 / 1.56 s without, f110 /
  f60). On the candidate bakes stage A moves only the boy's chains (the T-183 engine keeps the girls' chains out).

## Not done

- s010 and e909 s010 on the candidate pin (time); released bakes were measured in session 2 only.
- A per-vertex rate limit (offset change per frame <= 4 mm), proposed by R7: it needs state between frames
  (simulation zone or a per-vertex offset cache, ~0.9 GB per shot) and breaks the stateless / single-frame contract.
- Hair against hair (out of scope), sliding on props.

## Sheet

SHEET_LINE
