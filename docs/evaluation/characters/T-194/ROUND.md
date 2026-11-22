# T-194 round file: hybrid hair (engine chains + render-time push-out on the real meshes)

Branch `t-194-claude-hair-pushout` (from main `3183184`). Owner approval of the hybrid: 2026-11-22 ~13:45 CET.
Supervisor: `session_01NPjxePvWAMsLopzSs1fMXB`. Write-set: `pipeline/charsys/shot_render.py`,
`pipeline/charsys/hair_pushout.py` (new), `pipeline/charsys/tests/test_hair_pushout.py` (new),
`docs/evaluation/characters/T-194/**`. T-183 files (engine secondary / scene, `groom_contact.py`, `groom_r6.py`) are
read-only here.

## Step 1 (STATUS, waiting for approval): analysis and design

Numbers are the T-183 round 3 measures (`t-183-claude-hair-contact@c775d69`, ROUND.md "Session 6"; limit 1 mm).

### Which of our measured problems the push-out solves

| Problem (T-183 r3 candidate unless noted) | Push-out | Why / what is left |
|---|---|---|
| Table, e912 s010/s020/s030, both girls (released 12.5 mm, 9-164 fr; candidate 0) | solved (safety net) | the table is one more real mesh (bake box objects and props) |
| Own garments, one-frame pops: s010 blouse 20.4 / 9.1 / 8.9 mm (f101 / f161 / f79), s020 18.0 / 12.2 / 10.9 mm, s030 f93 22.0 / 19.1 / 14.5 + vest 8.4, white s030 f93 bodice 23.0 / 13.8 | penetration solved | stateless per frame, so the lock is clamped on the chest in the pop frame. The jump itself (joint 3 of `ringlets_side_r00` travels 66 + 52 mm in two frames) is in the bake and stays: the lock still sweeps across the chest, on top of the cloth instead of through it |
| Auburn hair in the boy: s020 hoodie 71.7 / strap 75.2 / skin 49.9 / hand.R 52.0 mm, up to 118 fr; s030 47.6 / 34.8 / 20.7 mm; s010 only f1-36 (before the rendered range) | penetration solved | the boy's evaluated meshes are colliders of her hair. At 72-75 mm for 118 frames the bake has her locks deep in him most of the shot; the push-out stops them at his surface, so they bend or bunch at his shoulder with no sliding. That is correct but can look stiff; T-183's neighbour colliders give the motion, and the push-out then removes the rest. Where his body is inside hers (T-191), hair squeezed in between cannot be outside both: reported per frame, not solved |
| Boat / boat_end_a in her hand: s020 12.8 / 15.0 mm, 37 / 48 fr; s030 13.4 / 9.0 mm | solved | props are already real meshes in `setup_props` |
| e909 s010 cup 23.9 mm, 157 of 286 fr | solved | open-top cylinder: the hair copy of the collider gets a closing cap, so hair cannot drop into the cup through its opening (render mesh unchanged) |
| e909 the boy's hand.R 11.8 mm, 18 fr | solved | neighbour mesh |
| Nape cap / curtain against the neck skin: s020 cap 25.5 / curtain 20.9 mm, ~100 of 104 fr; s030 cap 22.0 mm; e909 cap 12.4 / curtain 11.0 mm | only with the per-vertex stage | static hair has no chains, so a chain push-out does not touch it. Cause: the neck skin folds over the hairline when the head tilts (body skinning). The per-vertex stage pushes those cap / curtain vertices out over the fold (hidden under the ringlets); the skin itself is not changed |
| White-haired girl ear.L 10.2 mm (static `back_mass`, chains `back_under_06` / `_00`), every frame | per-vertex stage (static), both stages (chains) | |
| Fan-out / standing off in the lean (T-183 r2: out-of-outline 999 against 843 cm2, 27 crossings against 16) | not solved | that is engine motion. The push-out uses a small core radius, so it adds no stand-off. Later, T-183 could lower its engine radii (the fan-out cause, (a) in session 5), with the push-out as the zero-penetration guarantee |
| Hair against hair (locks into the static curtain / crown, girl against girl hair) | not in scope | question 3 |
| Sliding / settling on props | not solved | owner: resting without sliding is fine for now |

### Interaction with T-183's engine colliders

- **Order:** engine bake (T-183 colliders: skin spheres, boxes, neighbour / carried prop) -> `shot_render` keys the
  bones -> stage A (chain joints) re-keys only the `DYN-*` bones -> Armature -> stage B (per-vertex Geometry Nodes
  modifier) -> render. It is a pure post-process of the bake: nothing goes back into the solver, the bake format and
  the engine stay unchanged, and it works on released and candidate packages alike.
- **No double correction:** the targets are absolute ("surface + margin" or "the last free point of the segment"),
  not increments. A joint the engine already holds outside (engine radius up to 53 mm, much larger than the
  push-out's core radius + margin) is not touched: hair that is already outside comes out bit-identical. Applying the
  push-out twice gives the same result (unit test).
- **Flicker:** the clamped path is the bake path cut at a surface that moves smoothly, so contact that starts or ends
  is continuous whenever the bake is. Jumps come only from the bake (the pops above) or from a lock changing sides of
  a thin part. Measured as frame-to-frame jumps of vertices before and after (tip-jump statistic like T-183's
  `tip_noise.py`). Optional smoothing over f-1..f+1: off by default, because it is not local and it can re-enter a
  surface.

### Method (from the T-193 probe, made robust for open shells and deep cases)

- **Stage A, chain joints (Python, `mathutils.bvhtree`):** per frame, after all non-hair bones are keyed, the
  colliders are evaluated once per frame (one BVH per character figure, prop and box set). Each `DYN-*` chain is
  walked from its root in a fixed order. Segment k is tested by a **ray from joint k-1 (already outside) to joint k**:
  every face it crosses counts (this catches open garment shells, inside-out trims and 75 mm deep cases, where a
  "nearest point + normal" test would push to the wrong side). On a hit, the joint is put back at segment length,
  slid along the tangent plane at the hit with `core + margin` clearance, then re-tested (at most 3 tries; the
  fallback is the last free point along the normal, length kept). The root segment ignores the crossings it already
  has at rest (the root sits in the scalp). Pose quaternions of the `DYN-*` bones are rewritten and keyed, so
  `shot.blend` contains the result.
- **Stage B, every hair vertex (Geometry Nodes modifier, evaluated by Blender, no Python at render time):** each hair
  object gets a hidden **anchor proxy**: a local copy of its mesh skinned with the same groups, with every chain
  vertex moved onto its chain's centre line at rest. A vertex is clamped where the ray from its anchor (outside
  after stage A) to the vertex crosses a collider (probe on `hair_ringlets_back_00`: works on the override object,
  saved and reloaded, 0.12 s per evaluation after a 1.1 s first BVH over 43 meshes). Static vertices (cap, curtain,
  temples, `back_mass`) have no centre line: they use the signed nearest-surface test with a rest allowance (a
  vertex that sits at its rest depth from the same part, like a root in the scalp, is not moved).
- **Colliders per character:** own figure (evaluated `body_skin` with its mask, ears, hands, garments; not
  `garment.collider.*`, hair, `WGT-*` or the face parts of T-183's SKIP list), the other characters' figures, the
  props (cups get a closing cap) and the bake's box objects. Hair is not a collider.

### Determinism, cost

- Stateless per frame. Inputs at frame f are only the evaluated meshes at f, in a fixed chain and collider order,
  so render order, a partial `--frames` range and restarts do not change it. Test: SHA-256 of all evaluated hair
  vertices, two runs, and a single frame against the same frame inside a range.
- Cost to measure (step 3); estimate +3-8 s per frame per shot with three characters (evaluating and building the
  BVH of the figure meshes dominates), against about 40 s per close-up frame (640x360, 8 spp) and more for final720.
  Stage A is a pre-pass over the frames before `render(animation=True)`.

### Design

- `pipeline/charsys/hair_pushout.py` (new): `collect_colliders(states, props, boxes)`, `pushout_chains(...)`
  (stage A), `install_vertex_stage(...)` (stage B node group + anchor proxies), pure geometry helpers that tests can
  call on small meshes, and a per-frame report (pushed joints, push depth, vertices clamped, squeezed vertices that
  cannot get out).
- **Opt-in:** `shot_render.py --hair-pushout [spec.json]`; absent = today's path, bit-identical (no proxies, no
  modifier, no extra keys). Spec defaults: `margin_m` 0.002, `core_radius_m` 0.012, `vertex_margin_m` 0.0015,
  `characters` all, `stages` ["chains", "vertices"]. Report in `shot_render.json` under `hair_pushout`.
  `run_shot.py` is outside the write-set, so for now the tests call `shot_render.py` directly on the bakes;
  forwarding a `production.render.hair_pushout` key from `run_shot.py` is a one-line follow-up (question 1).
- **Shots:** copies under `docs/evaluation/characters/T-194/shots/` (released e912 s010 / s020 / s030, e909 s010) and
  T-183's `*_t183` copies read only. Build outputs in ignored `build/` folders or the scratch folder.

### Test plan

1. `pipeline/charsys/tests/test_hair_pushout.py` (needs the bpy module): a plane and a box (closed), an open shell
   and an inside-out shell; a chain through them ends with no crossing, segment lengths within 1e-6; an outside chain
   stays bit-identical; idempotent; deterministic; a root embedded at rest is allowed; a static vertex in a skin fold
   comes out; an open-top cup with its cap; `shot_render` without the flag adds nothing.
2. Real shots: e912 s010 / s020 / s030 and e909 s010, released and T-183 candidate bakes (the candidate engine from a
   worktree of the T-183 branch at a pinned commit, read only). A measure on the **Blender-evaluated** hair after
   the push-out (the bake-based T-183 measures cannot see it): the T-183 `measure_body.py` / `measure_props.py`
   rules, ported into `T-194/tools/`, per surface per frame, before and after. Plus the jump statistic, render cost
   per frame and the determinism hash.
3. Visual (P2): one strict sheet of <= 1024 px crops: e912 s020 at the boy's shoulder, s010 f101 (the pop), e909
   f75 (cup), the s020 nape; before / after.

### Questions for the Supervisor

1. Switch: only `shot_render.py --hair-pushout` now (tests call it directly); who forwards it from `run_shot.py`
   later?
2. Nape cap / curtain over the folded neck skin: push the hair out (the default, for zero penetration), or leave it
   to the body-skinning follow-up?
3. Hair against hair (locks into the static curtain / crown, and the girls' hair against each other): out of scope
   unless you want it.
4. Face parts as colliders: keep T-183's SKIP list (eyes, brows, lashes, lids, mouth, glasses) so the measures
   agree, or add the glasses frame?
5. Effort: 3-4 task-days as in T-193 (stage A 1.5 d, stage B 1 d, measure + sheet 1 d).

## Step 1 answer (Supervisor R6, 2026-11-22 ~13:06Z): APPROVED

(1) `pipeline/production/run_shot.py` added to the T-194 row: forward `production.render.hair_pushout`. (2) Nape cap /
curtain over the neck fold: push out. (3) Hair against hair: out of scope (note it). (4) Keep T-183's SKIP list;
report hair against glasses as its own line. (5) 3-4 task-days. List the body-snap frames separately (s010 fold
cycle, s020 f109 / f133-136, s030 f93; excluded +-1 from the zero criterion). Candidate engine pin: T-183 `e31f1e03`
for now (this session used `c775d69`; re-bake with the final pin). Before READY: cost per frame, sheet <= 1024 px,
`test_hair_pushout.py` (registration in `TESTS` is the Supervisor's).

## CHECKPOINT (session 1, WIP; continue in a fresh session)

### Done (committed)

- `pipeline/charsys/hair_pushout.py`: `load_spec`, stage A `push_chain` (segment rays, slide with clearance,
  fallbacks; enclosure test with the T-183 26-direction rule, so a joint that slipped in through an opening is moved
  out through its shortest wall), `rest_allowance` (only head-dominant SKIN triangles, not ears, not cloth),
  `static_anchor` (outward from the nearest rest surface; `static_in_head` never moved; `static_in_cloth` only when
  enclosed), `PushOut` (colliders incl. the unmasked `garment.collider.body_skin` proxy, cup caps, rest pass, anchor
  proxies with the `ps_exit` flag, per-frame stage A re-key, `install` of the stage B GN clamp: anchor ray + an exit
  test (two rays meeting back faces) against the CLOSED colliders only).
- `shot_render.py --hair-pushout [on|file|{json}]` (absent = old path); the push-out runs after the eye check and
  reuses its evaluation; pushed bones are left out of the reconstruction check; report `hair_pushout` in
  `shot_render.json`. `run_shot.py` forwards `production.render.hair_pushout`.
- `pipeline/charsys/tests/test_hair_pushout.py`: 28 checks, all pass (`python3 tools/bpy_blender.py -b
  --factory-startup -P pipeline/charsys/tests/test_hair_pushout.py -- out.json`). Not yet in `TESTS` (Supervisor).
  Missing case: the exit test (needs a closed `garment.collider.body_skin`-named solid in the scene).
- `tools/measure_eval.py`: the evaluated hair of a `shot.blend` against all colliders + glasses line, T-183 rules,
  per frame per surface, frame-to-frame jump, SHA-256. About 33 s per frame for three characters (use `--jobs`).
- Shot copies: `shots/e912/{s010,s020,s030}`, `shots/e909/s010` (+ `shots/e912/content/assets`). Released s020 baked
  (`shots/e912/s020/build/runs/rel1`, ignored). Candidate s020 baked in a T-183 worktree at `c775d69`
  (`/home/user/t183wt`, gone with the container).

### Measured so far (released e912 s020, frames 100-112 only, every 2nd frame; not a result yet)

- Cost: stage A 1.6 s per frame (3 characters; BVH of 1.4 M collider triangles ~1.2 s), rest pass 15-24 s once.
  Stage B evaluation cost not yet measured separately.
- Fixed in this window: ringlets in the blouse through the neck opening (outer_b 27.7 mm -> 0), the constant 3 mm
  static sets (white `back_mass` / crown, boy `hair_base`) -> 0.
- Left (f100-108): auburn `hair_curtain > blouse.main` 3-4 mm (5-8 v; anchor carried into the blouse by the head
  turn), boy `hair_top_outer > auburn skin` 1.9 mm (25 v, f108: heads overlap), glasses line `hair_cap > glasses`
  1.2 mm (4 v, every frame; glasses are not colliders).
- **Regression to investigate first:** with the last commit (exit test on closed colliders) f110-f112 show large
  residues and jumps (auburn jump 229-318 mm; `ringlets_back_b_00 > skin` 34.7 mm, `> blouse` 33.6 mm;
  `side_00 > boat_sail` 2.9 mm). f109 is a listed body-snap frame (head turn), but these are bigger than before the
  exit test. Compare a run with the exit test switched off (stages / a spec key) on f100-112 before anything else.

### Next (in this order)

1. Find the f110-112 regression (exit test vs stage A in the head-turn snap); keep the exit test only if it does not
   add residue or jumps; add its unit case.
2. Full s020 released: blends `--blend-only` with and without push-out (`/tmp/.../blends.sh` pattern: shot_render
   twice), `measure_eval.py --jobs=2 --step=2`; snap frames listed apart.
3. Re-bake the candidate with the T-183 pin **`e7547ab4`** (Supervisor 15:59Z; adds a cylinder prop collider, e909 cup -> 0 in the engine); e912 s010 / s030, e909 s010, released and candidate.
4. Cost per frame (stage A, stage B, total vs off), determinism (two runs, a single frame vs in a range), "no flag
   = identical" (object list and a frame hash against main's shot_render).
5. Sheet <= 1024 px crops (s020 boy's shoulder, s010 f101, e909 f75 cup, s020 nape), README, `tools/ready.py`, READY.

## CHECKPOINT (session 2, round 2, WIP)

Branch head: see `git log`; main merged twice (last: `927131b`, T-190 hand limits + T-205). Released bakes redone on
merged main (`build/runs/rel2`); candidate bakes with the T-183 pin **`e7547ab4`** (read-only worktree, run id
`cand1`; T-183 will give a final pin with its READY).

### f110-112 regression: found and fixed

- The 200-400 mm frame-to-frame jumps at s020 f109-112 are **in the released bake** (push-out off: 330 / 197 / 406 /
  259 mm, auburn). Not a push-out effect.
- Real bug: stage A shortened a segment when slide and normal were both blocked, but the re-key only rotates bones, so
  the keyed tail came out at full length back inside (f112 `ringlets_side_r00` joint 3). Now lengths are always kept;
  last resort = the free direction nearest to the baked one among 128 fixed (`_fan`), "blocked" if none. After the fix
  stage A at f111-112: 0 crossing segments, 0 enclosed joints.
- Stage B exit test made a 109 mm one-vertex spike (f107, out through the far side of the neck) -> reach 30 mm, and
  then **off by default** (spec `exit_test`): it still made 30 mm pops (boy at f108).
- New squeeze rule (stage B): a vertex whose anchor is inside ANOTHER character (first hit of the anchor ray on the
  other characters' unmasked skins is a back face) is not clamped. Boy 30 mm pops at s020 f108-110 gone (bake: 0
  flagged there; the clamp had moved his hair next to its anchor inside her head).
- Tried and rejected: a "vertex behind a back face" rule (solidified garments' inner layer faces the body -> blouse
  residue 31 mm); the lock-volume test (spec `lock_volume`, stage A, rest lock radius per segment): f111-112 residue
  564 -> 174 / 693 -> 76 vertices, but 10 mm frame-to-frame flicker of white `outer_locks_02` -> **off by default**.
- Open push-out pops (to report with the jump statistic): white `hair_back_under_00` beside the ear ~26 mm at s020
  f104->105 and f108->109 (anchor ray grazes the ear on alternate frames); auburn `hair_curtain` static vertices ~30 mm
  at f103-106 (bake 6-17 mm).
- Open residue s020 (rel2, defaults): f111-112 auburn ringlets in the pocket under vest / blouse collar (564 / 693 v,
  up to 35 mm; before 13971 / 17494) = snap aftermath, outside the +-1 window of f109.

### Tools (T-194/tools)

`measure_eval.py` (exact `enclosed()` prefilter, rows and hash identical), `hash_eval.py` (object list, pose and
geometry hashes per frame, `--time` stage B cost), `jump.py` (largest per-object vertex jump f -> f+1),
`blend.sh` (shot_render --blend-only, off / on), `queue.sh` (all 16 blends then 16 measures, step 2, 3 at a time;
outputs in the scratch folder `full/`, lost with the container). Tests: `test_hair_pushout.py` 31/31.

### Next

1. Read `full/*.m.json`: per shot x bake, off vs on: frames over 1 mm excluding snap frames +-1 (s010 fold cycle, s020
   f109 / f133-136, s030 f93), max per surface, glasses line, boy-head rigid hair apart; jump statistic (per frame
   max jump, on minus off; frames where on adds > 5 mm).
2. Cost: `shot_render.json` hair_pushout timing (setup, chains_s / frames) + `hash_eval.py --time` (stage B).
3. Determinism: two on-blends of s020 f100-112 and a single-frame f110 blend, `hash_eval.py` hashes equal; "no flag
   = identical": main's shot_render (worktree of origin/main) vs ours without flag, same bake, `hash_eval.py`.
4. Sheet <= 1024 px crops (s020 boy's shoulder, s010 f101, e909 cup, s020 nape), README, `tools/ready.py`, READY.

## CHECKPOINT (session 2, end: context limit; continue in a fresh session)

Supervisor is now R7 `session_01NPjxeKJV7E1M9rnLTkzJoo` (R6 confirmed; SUPERVISOR_HANDOVER_R7.md). R7: `local`
registration in TESTS.manifest is fine (R7 adds it to the Blender unit at merge); READY must say the test takes ~1 min
and needs no assets (synthetic scenes). Final numbers: candidate s020 + s030 on T-183 final pin **`c7b3cee2`**
(differs from `e7547ab4` by T-190 hand limits, contact.clear_targets on in the candidate overrides, neighbour PAD
2.5 -> 4 mm); s010 / e909 on `e7547ab4` only if time allows; README must name the pin per table.

### First full result: e912 s020, candidate `e7547ab4`, every 2nd frame (`results/e912_s020c*`)

Snap frames (T-183 snaps.py, same bake): 45 46 109 111 133 134 136 137 138 (+-1 excluded). f110-112 are inside.

| | frames > 1 mm (calm, 144 fr x 2 chars counted per frame) | max calm |
|---|---|---|
| off | 210 / 288 | 77.6 mm (auburn fringe in the boy's body skin, f79) |
| on  | 123 / 288 | 77.6 mm (same: squeezed, anchor inside the boy) |

Calm, by kind (frames with > 1 mm / max): off own girls 192 / 33.8, auburn in boy 20 / 77.6, boy in auburn 18 / 73.0;
on own girls 93 / 20.6, **boy own 29 / 28.1 (NEW: boy hair in `garment.hoodie.hood.rim`, created by the push-out)**,
auburn in boy 24 / 77.6, boy in auburn 1 / 21.9, prop 1 / 1.7. White girl: 0 frames. Apart: boy rigid hair in own
head skin 52.3 mm (T-191), glasses 1.3 mm. Pops: 55 frame x character entries where on adds > 5 mm to the jump,
max +43.8 mm (boy, f83). Cost: setup 55 s, stage A 4.0 s / frame (3 workers busy), measure 1921 s for 104 frames.

### Next (fresh session; the queue in the old container is lost with it)

1. Boy vs own hood rim (new, 29 frames, 28 mm) and the boy pops (f83 +44 mm): most likely static anchors (30 mm out
   from the head centre) that lie inside the hood at a frame -> clamp puts hair next to the anchor in the hood. Try:
   static anchor = the own rest surface point + reach along its normal but tested against the posed hood (or clamp
   only against other parts than the one the anchor is in), then the squeeze rule for own garments too.
2. Auburn in the boy (77.6 mm, squeezed: the bodies overlap, T-191 staging) -> listed apart like the boy-head case.
3. Re-run: `tools/queue.sh` (edit paths: T-183 worktrees at e7547ab4 and c7b3cee2, `cand1` / `cand2` bakes,
   released `rel2`); blends ~60 min, measures ~32 min per item, at most 2 measures at a time (3 = out of memory).
4. Then summarise.py per item (fix: its "apart" frame counter is never incremented), cost, determinism, identity vs
   main, sheet, README, READY.

## Session 3 (WIP)

Main merged (`ac462b9`; shallow clone: `git fetch --depth=300 origin main` first). T-183 final pin **`c7b3cee2`**:
worktree `/home/user/t183c2` (Release engine build), bakes `cand2` for `episodes/e912_paper_boat/shots/s020_t183`
and `s030_t183` (`run_shot.py --stages prepare,bake --run-dir cand2`, ~3 min each). The boy's cand2 numbers equal
cand1 (`e7547ab4`) at f41-53.

### The hood-rim regression and the pops: cause and fix (all static anchors)

Probes (`p4`/`p5` in the scratch folder: anchor, raw vertex, first hit of anchor->vertex and vertex->anchor per
collider) on s020 cand2:

- Boy `hair_cap.002` f45: anchor 0.9 mm inside the `hood.rim` tube, vertex 15 mm outside; first hit = back face ->
  clamp snapped the vertex into the rim (27.7 mm). Fix 1 `static_inside: keep`: a static vertex whose anchor ray
  first meets a BACK face is left as baked.
- Boy cap f53 and auburn `hair_curtain` f53: anchor and vertex both outside, the ray only crosses a thin part (rim
  tube). Fix 2: a static vertex is clamped only when behind a surface (its own ray to the anchor first meets a back
  face).
- Boy cap f49, auburn curtain f68 (own neck skin, inside 6/6), auburn fringe f69 (boy's body): the anchor is within
  ~0.5 mm of a surface and flips sides frame to frame; each flip moves the vertex by its whole reach (~30 mm = the
  girl pops). Fix 3 `static_fade_m [0.002, 0.01]`: the static clamp is faded in with the hit's distance from the
  anchor (continuous).
- Window f39-85 (every 2nd frame, frames x characters > 1 mm, boy own head skin and glasses apart): off 56, on before
  the fixes 37 with the rim, after fix 3 **25, no new surface**; pops left: white `hair_back_under_00` v574 f50
  (+18 mm, chain vertex, anchor ray through the ear edge, vertex outside it) and the boy f75-83 (+8..44 mm).
- Boy f75-83: chain vertex of `hair_fringe.002` really inside the auburn head (heads overlap up to 73 mm, T-191); the
  clamp is right per frame and lets go when her head leaves. Asked the Supervisor (fade against other characters'
  skin beyond ~5 mm = staging, reported apart, or keep).
- `keep_outside: all` (fix 2 for chain vertices too, for the ear case) is an option; session 2 rejected a similar
  rule for the blouse residue, so it is measured on full s020 next to the default.
- Unit test: 34 checks (new: anchor inside a moving box kept; thin slab between vertex and anchor kept); the first
  fails with `static_inside: clamp` (60 vertices into the box).

### Running (lost with the container if not finished)

`/tmp/claude-0/s/full/run3.sh`: s020 cand2 full (1-208, step 2) off / on / on + keep_outside all; then
`summarise.py` (T183_ROOT=/home/user/t183c2), STATUS, s030 pair, cost, determinism, identity, sheet, READY.
