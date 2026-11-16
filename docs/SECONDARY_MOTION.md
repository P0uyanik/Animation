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
| Tests | `tests/test_secondary.cpp`, `pipeline/charsys/tests/groom_dynamics_test.py` |

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

## Scene override (character → `"dynamics"`)

`false`, `{"enabled": false}`, or an object that overrides parameters:
`{"substep_hz": .., "preroll_s": .., "chains": {"*" | "<group>" | "<chain>": {params}}}`. The more specific key
wins. An override cannot switch on dynamics for a package without chains. It is saved with the scene as written.

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
