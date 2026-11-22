# Secondary motion: spring chains (T-021)

Shared, character-independent secondary motion for hair locks, buns, and any other chain of bones such as ears,
tails or bows. The engine evaluates it, `plush.shot_bake/1` carries it, and Blender renders it. It is off when a
character package has no `dynamics` block, so existing packages, scenes and bakes are unchanged.

| Piece | File |
|---|---|
| Solver, data, JSON | `engine/anim/secondary.{h,cpp}` |
| Hook (after clips, life, constraints, clip fingers) | `SceneEvaluator::characterGlobals` → `kinematicGlobals` + `SpringChainSolver::apply` (`engine/scene/scene.cpp`) |
| Package block | `export_engine.py` (`export_dynamics`, EXPORTER_VERSION 3), read by `engine/model/imported_character.cpp` |
| Hair chain bones | `pipeline/charsys/groom.py` (`spec.hair.dynamics`) |
| Tests | `tests/test_secondary.cpp`, `pipeline/charsys/tests/groom_dynamics_test.py`, `pipeline/charsys/tests/test_hair_contact.py` (contact, T-183) |

## Model

Each chain joint is a point mass that follows its kinematic target through a damped spring. The kinematic target is
where clips, life and constraints put the joint. On top of the spring:

- air drag;
- gravity relative to the modelled rest shape: zero while the chain's root bone keeps its rest orientation, so
  there is no sag in the rest pose; when the parent tilts, gravity pulls the chain back down;
- segment lengths are kept;
- each segment stays within `limit_deg` of its kinematic direction;
- joints are pushed out of collider spheres and capsules that ride on bones. A joint never has to be farther out than
  its own kinematic target, so a modelled shape that touches a collider is not pushed away.

The root joint (the first bone's pivot) is kinematic. Bones are rebuilt as the shortest-arc swing from their own
kinematic direction to the simulated segment, so twist is kept, and non-chain children follow rigidly.

- **Anchor (optional, per chain):** joint *k*'s target is blended towards where `anchor.bone` carries its rest
  position, with weight `anchor.weights[k]`. groom/1 derives the weights from `hair.binding.blend_z`, so long hair
  that rests on the back follows the chest as its static skin binding did.
- **Determinism and frame-rate independence:**
  - the state advances on a fixed grid of `substep_hz` steps, counted in seconds from the scene's first frame;
  - before the first frame, a preroll of `preroll_s` settles the chain at the first frame's pose;
  - the driver is sampled at the grid times, and a frame between grid points takes one partial step that is not
    cached;
  - states are cached at checkpoints on the same grid, so the order in which frames are requested does not change
    the result;
  - a checkpoint is dropped when the driver no longer reproduces its kinematic joints. The cache is also cleared on
    `load()`, `mutableScene()` and `rebuildCharacter()`;
  - frames before `frameStart` stay kinematic.
- **Off:** a scene can override the package with `false` or `"enabled": false`.
  - For a package without anchors, the result is exactly the kinematic pose, bit for bit.
  - For anchored chains, the chain is posed statically at its anchored targets, with lengths kept. This is the
    no-motion equivalent of the static binding.

## Package block (`character.json` → `"dynamics"`, engine axes, rest space, metres)

```json
"dynamics": {
  "enabled": true, "substep_hz": 240, "preroll_s": 1.0,
  "defaults": {"stiffness": 60, "damping": 6},
  "colliders": [{"name": "head", "type": "sphere", "bone": "head", "centre": [x, y, z], "radius": 0.128},
                {"name": "torso", "type": "capsule", "bone": "chest", "a": [...], "b": [...], "radius": 0.082}],
  "chains": [{"name": "back_curls.03", "group": "back_curls", "bones": ["DYN-back_curls.03.0", "..."],
              "tip": [x, y, z], "stiffness": 90, "stiffness_tip": 60, "damping": 7, "gravity": 0.5, "drag": 0.8,
              "limit_deg": 30, "radius": 0.014, "colliders": [],
              "anchor": {"bone": "chest", "weights": [0, 0, 0.3, 0.8, 1, 1]}}]
}
```

| Key | Meaning | Default |
|---|---|---|
| `stiffness` | 1/s², spring towards the kinematic joint (`stiffness_tip`: linear towards the last joint) | 60 |
| `damping` | 1/s, on the velocity relative to the kinematic joint (overshoot vs settle) | 6 |
| `gravity` | × 9.81 m/s², relative to the rest shape | 1 |
| `drag` | 1/s, on the absolute velocity | 0.5 |
| `limit_deg` | max angle between a segment and its kinematic direction | 60 |
| `radius` | joint radius for collisions (m) | 0.01 |
| `colliders` | names of the colliders this chain uses (empty = all) | all |

Each chain bone must be the child of the previous one. A bone may belong to one chain only.

## Contact (T-183, opt-in per chain)

A chain may carry a `"contact"` block. Without it the chain takes exactly the path described above (bit-identical;
`tests/test_secondary.cpp` checks it), so existing packages, scenes and bakes do not change.

```json
{"name": "side.00", "bones": ["..."], "tip": [x, y, z],
 "contact": {"solid": ["hand_l", "hand_r"], "segments": true, "anchored_gravity": true}}
```

| Key | Meaning | Default |
|---|---|---|
| `solid` | collider names that push to their full radius: the exemption "never farther out than the kinematic target" is off for them. For moving parts (hands, forearms) that enter the place where the hair rests. They are added to the chain's colliders. | none |
| `segments` | the segments between joints collide as capsules of the chain `radius`, not only the joints. The segment's closest point is moved out by swinging its end joint. | false |
| `anchored_gravity` | gravity is scaled by `1 - anchor weight` per joint: a joint whose target the anchor bone carries already hangs where that bone puts it, so the head's tilt does not pull it off. | false |
| `radii` | one collision radius per joint (bones + 1 values, metres) instead of the chain `radius`; a segment is a tapered capsule between its two joints' radii. | chain `radius` |
| `rest` | resting contact: every collider acts at its full radius (no exemption for the kinematic target, `solid` is not needed). A pushed joint takes the collider's velocity along the contact normal and loses its sliding speed by `friction`; the middle of each segment is tested with a fixed lever; colliders far from the chain are skipped per step. | false |
| `friction` | with `rest`: sliding speed lost in contact, 1/s. | 40 |
| `max_swing` | with `rest`: a segment turns at most this much faster (rad/s) than its kinematic direction, so a lock squeezed between two colliders moves steadily instead of snapping. 0 = no bound. | 12 |
| `carry` | with `rest` and `max_swing` (T-183 round 3): the `max_swing` bound yields to a collider that moves: a pushed joint may also turn as fast as that collider moves relative to the joint's kinematic target. A forearm that sweeps a lock across the chest within a frame then takes the lock along instead of leaving it inside the arm or the chest for that frame; a still collider adds nothing, so a squeezed lock stays steady. | false |
| `clear_targets` | with `rest` (T-183 round 3): a joint's spring target is first taken out of the chain's colliders (pushed to the full radius, as a joint), the preroll starts the chain at those targets, and the `max_swing` bound does not hold a joint inside a collider when the uncapped direction has it outside every collider of the chain (a lock squeezed between two colliders has no such place, and the bound holds as before). For an anchored target that lies inside the body: e912 s030 f1-10, the head turned 54 degrees against the chest anchor put a side lock's target inside the upper arm; started there, each step's way out was turned back by the bound and the lock stayed 30 mm inside the arm (7.7 mm through the blouse). Off = bit-identical. | false |
| `locks` | lock against lock (T-183 round 3): a joint keeps off the joints of the other chains that carry the key by `locks` x (the two joints' radii), never by more than the two kinematic joints are apart (locks that lie together stay together). Joints only, not segments. The chains are solved in their fixed order, half the overlap is taken back per step: deterministic. A number in [0, 1]. | 0 (off) |

- A push by any collider of a contact chain is inelastic: the pushed joint keeps at most the speed it had before the
  push or the speed of its kinematic target, so a hand moves a lock aside without throwing it.
- A solid collider that passes a joint or segment within one step does not flip it to the far side: it leaves on the
  side it was on at the previous step.
- A collider that the hair rests on (head, shoulders, upper arms, ears) should stay a plain collider: a solid collider
  in resting contact showed ±3-4 mm frame-to-frame noise at the lock tip (T-183, ears as solid).
- Colliders may ride on any deform bone (this was already so in the package; groom/1 limited its own to head and
  chest).
- With `rest` the angular limit (`limit_deg`) yields to contact: a joint that a collider pushed in this or the last
  step is not clamped back; once free, its limit shrinks from the angle it had to `limit_deg` at 12 1/s. Without this
  a collider that holds a tip beyond the limit and the clamp alternate, and the tip slides round the limit cone
  (25 mm per frame measured on a forearm, T-183).
- With `radii` and without `rest`, a tapered segment is tested where its surface is nearest to the collider (at its
  middle when its thick end is the first joint).

Groom side (`spec.hair`, groom/5 module, `pipeline/charsys/groom_contact.py`), both keys opt-in:

- `hair.dynamics.contact`: `{"colliders": [...], "segments", "anchored_gravity", "structures"}`. Each collider is
  fitted at bind time from the meshes bound to the rig: `"fit": "blob"` (capsule along the principal axis of the
  vertices; hands, ears) or `"limb"` (capsule along the bone axis `bones`, radius = `percentile` of the distance to
  it). Vertices come from the vertex `groups` that carry at least half the weight, or from named `objects`.
  `"solid": true` puts the collider in the chains' `contact.solid`. Lock chains get the block; bun chains keep their
  previous colliders.
- Round 2 keys of `hair.dynamics.contact` (all optional, bind time):
  - collider `"fit": "skin"` with any of `groups`, `objects`, `exclude_groups`, `exclude_objects` (none = the whole
    figure) and `spacing_m`, `radius_m`, `pad_m`, `reach_m`, `min_radius_m`: sphere colliders named `<name>.<i>` that
    follow the figure's surface from inside, each on the deform bone that carries its vertex most. The figure is every
    evaluated mesh bound to the rig except the hair and `"figure": {"exclude": [...]}` (default: collision proxies,
    widgets, face features, glasses); cloth counts as surface, and the outward side is found by what is open, not by
    the stored normal. The girl of T-183 takes five sets (head, ears, torso with the garments, arms, hands): about
    820 spheres.
  - `"radii": {"percentile", "floor_m"}`: one collision radius per joint from the vertices the chain carries, capped
    by the joint's rest clearance to the colliders on the chain's root bone (so a lock that starts on the head does
    not collide with the head at rest). The root joint takes the next joint's radius, capped the same way: with a
    root radius of 0 the first segment was a thin cone and the short side locks turned 5-7 mm into the ears.
  - `"rest": true | {"friction", "max_swing", "carry", "clear_targets"}`: the chains get resting contact against every collider.
- `hair.ear_keepout`: `{"objects": ["ear.*"], "margin_m", "smooth", "structures"}`. Hair surface vertices inside a
  keep-out mesh are moved out along the head's front/back axis (the shorter way) before the fibres are grown, and the
  move is relaxed over the neighbours. Vertex counts and order do not change.

The release rule (`pipeline/charsys/release_rule.py`, feature `hair_contact`) keeps both keys out of published
specs unless the release manifest lists the version.

## Scene override (character → `"dynamics"`)

`false`, `{"enabled": false}`, or an object that overrides parameters:
`{"substep_hz": .., "preroll_s": .., "chains": {"*" | "<group>" | "<chain>": {params}}}`. The more specific key
wins. An override cannot switch on dynamics for a package without chains. It is saved with the scene as written.

### Scene colliders (T-183 round 3, opt-in)

`"colliders": [...]` in the override adds colliders to the package's. An entry is a package collider (sphere or
capsule on a bone of the character) or a box of the scene in world space:

```json
"dynamics": {"colliders": [{"name": "table_top", "type": "box", "space": "world",
                            "min": [-0.66, 0.425, 0.055], "max": [0.66, 0.45, 0.325], "radius": 0.01}]}
```

- `radius` is the rounding of the box's edges (default 0.01 m, at most the smallest half extent). The faces stay where
  `min` / `max` put them.
- A new collider joins every chain, also chains that name their colliders. A name the package uses already is an error.
- A chain is kept out by the full radius only when it has `contact.rest` (or names the collider in `contact.solid`).
  A chain without a contact block is never pushed farther than its kinematic joint is, so a table holds nothing.
- A world box does not move. Segments are tested at the point nearest to the box (at their middle with `contact.rest`).
- Without the key the solver takes the previous path (a box out of reach is bit-identical too: `test_secondary.cpp`).
- `docs/evaluation/characters/T-183/tools/derive_shot.py` writes the boxes of a shot's `objects` into a shot copy.

Colliders that move with something outside the character (same list, same rules; opt-in per shot):

```json
"dynamics": {"colliders": [
  {"name": "nb.boy.0", "type": "sphere", "character": "boy", "bone": "DEF-upper_arm.L", "centre": [0.21, 0.74, 0.01], "radius": 0.04},
  {"name": "prop.boat", "type": "box", "prop": "boat", "min": [-0.05, -0.013, -0.021], "max": [0.05, 0.013, 0.021], "radius": 0.003},
  {"name": "prop.cup", "type": "cylinder", "prop": "cup", "a": [0, 0, 0], "b": [0, 0.1, 0], "radius": 0.04, "round": 0.003}]}
```

- `"character"`: the scene name of ANOTHER character; `bone` is one of its bones and the shape (sphere or capsule) is
  in that character's rest space, like a package collider is in the character's own. The hair of one character then
  keeps off the body of its neighbour.
- `"prop"`: the name of a scene prop; the shape (box, sphere, capsule or cylinder, no `bone`) is in the prop's own
  frame, so it goes where the prop goes, also in a hand (the box is oriented). A scale in the prop's transform scales
  the shape.
- `"type": "cylinder"` (on a prop only): a solid cylinder, `a` and `b` the centres of its two end faces, `radius` its
  radius, `round` the rounding of its two rims (default 0.003 m, at most the radius and half the height). The faces
  and the side stay where `a`, `b` and `radius` put them. A cup is such a cylinder (its hollow counts as solid: no
  hair hangs into it). Segments are tested like a box's. A scene without one runs as before.
- The scene gives the solver the frames of these carriers at every step (`SpringChainSolver::External`): the other
  characters' poses before their own secondary motion and the props on those poses, so no solver waits for another
  and a prop in the character's own hand does not re-enter its solver. An unknown character, bone or prop is a load
  error. The carriers' poses are evaluated at the step rate (240 Hz), each once (a memo shared by the characters).
- Without such a collider nothing of this runs: the scene calls the solver exactly as before (the golden bake hashes
  of `tests/test_bake_golden.cpp` are unchanged, and `test_secondary.cpp` checks the solver bit for bit).
- `derive_shot.py --props --neighbours-from=<bake>` writes them into a shot copy: the scene's box and cylinder
  props, and spheres fitted on the neighbours' package meshes where the hair comes near them (`tools/neighbours.py`).

## Groom (`spec.hair.dynamics`, groom/1)

```json
"dynamics": {"enabled": true, "defaults": {...params},
  "structures": {"back_curls": {"bones": [3, 5], "bone_length": 0.07, "every": 1, "blend": 0.5, ...params},
                 "bun": {"bones": 1, "stiffness": 140}},
  "colliders": [{"name": "head", "type": "sphere", "bone": "head", "head_offset": [0, 0, 0], "radius": 0.128},
                {"name": "torso", "type": "capsule", "bone": "chest", "a": [...], "b": [...], "radius": 0.08}]}
```

- **Locks:**
  - there is one chain per lock, or per every *k*-th lock;
  - the chain runs along the lock's hanging centre line, from where the lock leaves the scalp to its tip;
  - the bone count is `n`, or `round(length / bone_length)` clamped to `[lo, hi]`;
  - rope vertices are weighted linearly between bone centres;
  - over the first `blend` bones the weights blend from the static binding into the chain;
  - scalp-side vertices keep the static binding.
- **Buns:** 1–2 bones along the bun axis. The bun's ropes and core follow the chain by height. So do ties, bows and
  flowers that sit on that bun.
- **Bones:** `DYN-<structure>.<lock>.<k>` deform bones, parented to `rig.head_bone`. Collider `bone` is `head` or
  `chest`, resolved to `rig.head_bone` / `rig.chest_bone`.
- **Hand-off:** the metadata goes on the rig object as `ps_dynamics` (JSON, Blender world coordinates).
  `export_engine.py` converts it into the package block.
- **No dynamics block:** no bones are added, and geometry and weights are unchanged. `groom_dynamics_test.py` checks
  this.

The girl's candidate version is the unpublished override `girl_auburn_bun_glasses.dynamics.override.json`
(spec_version `0.7.1+dynamics`). It adds only `hair.dynamics`.
