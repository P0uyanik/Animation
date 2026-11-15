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

Scenes place data-only instances in `props` (rendering/import is intentionally deferred):

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
    }
  }
]
```

`name` identifies the instance and must be non-empty and unique among the scene's props; `id` identifies the reusable
asset, so multiple instances may share an asset ID. The optional `parent` names the instance that owns the attachment
socket. Its `kind` is either `prop` or `character`. A prop parent must exist and its `socket` must be declared by that
prop's asset. Assets are found by ID in `content/assets` by walking up from the scene file. A character parent must
exist (`actor_a` in the example) and its socket must be a non-empty bone or role name; character sockets are resolved
later during evaluation. Prop-to-prop parenting must not contain a cycle.
