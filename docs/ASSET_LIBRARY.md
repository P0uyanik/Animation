# Prop asset library (`plush.asset/1`)

`plush.asset/1` is the reusable metadata for a prop. Files normally live in `content/assets/` and use engine axes
(metres, +Y up). The required fields are `format: "plush.asset"`, `version: 1`, a stable `id`, `licence`,
`attribution`, `mesh`, one or more `material_presets`, and `scale` (metres per source unit).

Production geometry names a source file and object:

```json
"mesh": { "path": "models/example.glb", "object": "Example" }
```

The path must end in `.blend` or `.glb`. Small fixtures may instead use a `box`, `sphere`, or `cylinder` primitive,
as in `content/assets/cup.asset.json` and `content/assets/paper_sheet.asset.json`.

Sockets are named local transforms with `translation`, `rotationDeg` (XYZ; X applied first), and per-axis `scale`.
Names such as `grip`, `place`, and `contact` carry no hard-coded behavior. An optional `collision` is a `box`
(`size`), `sphere` (`radius`), or capsule (`radius` and tip-to-tip `height`); it may have its own `transform`.

Scenes place instances in `props` (geometry rendering/import is intentionally deferred; attachment transforms are
evaluated by `SceneEvaluator`):

```json
"props": [
  {
    "name": "tea_cup",
    "id": "prop.cup",
    "transform": {
      "translation": [0.4, 0.72, -0.1],
      "rotationDeg": [0, 25, 0],
      "scale": [1, 1, 1]
    },
    "parent": {
      "kind": "character",
      "name": "actor_a",
      "socket": "hand.R"
    },
    "parentSwitch": [
      {
        "frame": 48,
        "parent": { "kind": "prop", "name": "tray", "socket": "place" }
      },
      { "frame": 72, "parent": null }
    ]
  }
]
```

`name` identifies the instance and must be non-empty and unique among the scene's props; `id` identifies the reusable
asset, so multiple instances may share an asset ID. The optional `parent` names the instance that owns the attachment
socket. Its `kind` is either `prop` or `character`. A prop parent must exist and its `socket` must be declared by that
prop's asset. Assets are found by ID in `content/assets` by walking up from the scene file. A character parent must
exist (`actor_a` in the example) and its socket must be a bone name or a shared role name present in that character's
retarget/clip binding. Prop-to-prop parenting is evaluated in dependency order and must not contain a cycle. Missing
character bones/roles and missing prop-asset sockets are load errors.

The instance `transform` is a world placement when the prop is unattached, and is the local offset from the selected
socket when it is attached. The scalar animation track `<prop>.parent.weight` is clamped to `[0, 1]`; it blends the
world placement at zero with the attached placement at one using translation, quaternion rotation, and scale, so an
authored ramp can pick up or put down a prop without a one-frame pop. Its default is one while a parent is active.

`parentSwitch` changes the active parent at the listed frame. Each `parent` has the same shape as the instance parent;
`null` detaches. Entries are evaluated in frame order. At every switch the evaluator derives a new local offset from
the old world transform, so the switch itself is continuous even for random-access frame evaluation. Later frames
follow the new parent (or remain at the detach transform).

## Shot bake

`plush.shot_bake/1` remains backward compatible. When a scene has props, every `frame_data` entry additionally has an
optional `props` object. Its keys are prop instance names and each value is the evaluated column-major 4x4 world
matrix (16 numbers, engine axes/metres):

```json
"props": {
  "tea_cup": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0.4, 0.72, -0.1, 1]
}
```

For a scene with no props the block is omitted, so its bake JSON is unchanged.
