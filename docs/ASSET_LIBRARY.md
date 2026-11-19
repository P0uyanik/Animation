# Prop asset library (`plush.asset/1`)

`plush.asset/1` is the reusable metadata for a prop. Files normally live in `content/assets/` and use engine axes
(metres, +Y up). The required fields are `format: "plush.asset"`, `version: 1`, a stable `id`, `licence`,
`attribution`, `mesh`, one or more `material_presets`, and `scale` (metres per source unit).

Production geometry names a source file and object:

```json
"mesh": { "path": "models/example.glb", "object": "Example" }
```

The path must end in `.blend` or `.glb`. Small fixtures may instead use a `box`, `sphere`, or `cylinder` primitive,
as in `content/assets/cup.asset.json`, `content/assets/felt_cup.asset.json` and `content/assets/paper_sheet.asset.json`.
Primitive frames: a box and a sphere are centred on the origin; a cylinder stands on its base at the origin with its
axis along +Y (so a `place` socket at `[0, 0, 0]` is the bottom). A cylinder may add the render-only hints
`"open_top": true` and `"wall": <metres>` (a vessel: no top cap, solidified wall); the engine ignores them.

Sockets are named local transforms with `translation`, `rotationDeg` (XYZ; X applied first), and per-axis `scale`.
Names such as `grip`, `place`, and `contact` carry no hard-coded behavior. An optional `collision` is a `box`
(`size`), `sphere` (`radius`), or capsule (`radius` and tip-to-tip `height`); it may have its own `transform`.

Scenes place instances in `props` (attachment transforms are evaluated by `SceneEvaluator`; the Blender shot render
draws primitive meshes, file meshes are not imported yet):

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
`null` detaches. Entries are evaluated in frame order. At every switch the evaluator rebases the new attachment target
so the blended world transform is continuous, including while `parent.weight` is between zero and one and during
random-access frame evaluation. Later frames follow the new parent (or remain at the detach transform).

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

## Blender render (T-022)

`pipeline/charsys/shot_render.py` creates one object per prop name found in the bake's `props` blocks. It reads the
prop's asset id from the baked scene (`scene_path`) and the asset from the nearest `content/assets` above it, builds the
primitive mesh in Blender axes and assigns the first `material_presets` entry through the shared material library
(`pipeline/charsys/materials/presets.json`, e.g. `felt`). A preset name the library does not have gets a plain
Principled material and is listed under `props.unknown_material_presets` in `shot_render.json` (the older fixtures
`ceramic_glaze` / `paper_white` are such names). The object is keyed on every frame from the baked world matrix.

## Hand interaction (T-022)

The interaction actions (`grasp`/`reach` with `prop`, `hold`, `place`, `handover`; see
`docs/ACTIONS_AND_DIRECTOR.md`) use a prop's sockets as grasp and place points. The grasp size comes from the
primitive mesh (or the collision proxy for file meshes): a socket on a cylinder's side gives a cylindrical grasp of
the cylinder's radius around its axis, a socket on a box face a grasp across that face, a sphere a spherical grasp.
They generate the same `parentSwitch` entries and `<prop>.parent.weight` keys described above, at the contact
frames. `content/assets/felt_cup.asset.json` has two grips, `grip` (upper, local +x) and `grip_b` (lower, local -x),
so two hands can hold it at once during a hand-over.

## Affordances (T-112a)

An optional top-level `"affordances"` object says how a prop is held, carried and put down (design:
`docs/architecture/INTERACTION_AFFORDANCES.md` section 2). The asset format stays `plush.asset/1`. Only the verb
expander (`engine/scene/verbs.h`: `pick_up`, `carry`, `place`) reads the block. The primitive actions (`grasp`, `hold`,
`place`, `handover`) ignore it, so a prop with or without the block bakes the same.

```json
"affordances": {
  "format": "plush.affordances", "version": 1,
  "size_class": "small", "weight_class": "light", "mass_kg": 0.05, "hands": "one",
  "pivot": "place",
  "upright": {"axis": [0, 1, 0], "max_tilt_deg": 20},
  "grasp_sites": [
    {"id": "side_a", "socket": "grip", "hand": "any", "shape": "wrap", "turnable": true,
     "fingers": {"thumb": "opposed", "band": [0.045, 0.09]}}
  ],
  "grasp_sets": [{"id": "a", "sites": ["side_a"]}],
  "handover": {"give": ["a"], "receive": ["b"]},
  "place": {"socket": "place", "surface_normal": [0, 1, 0], "settle": "soft"},
  "deform": {"mode": "rigid"}
}
```

| Key | Values | Meaning |
| --- | --- | --- |
| `size_class` | `hand`, `small`, `medium`, `large` (optional) | largest extent vs. palm length (< 1.5, < 3, < 6, >= 6) |
| `weight_class` | `light` (default), `medium`, `heavy` | `heavy` requires `hands: "two"` |
| `mass_kg` | > 0 (optional) | informative |
| `hands` | `one`, `two`, `either` (default) | `two` requires a grasp set of two sites; a one-hand verb then fails |
| `pivot` | socket name or `[x, y, z]` | rotation origin (read by later verbs) |
| `upright` | `{axis, max_tilt_deg}` (optional) | `carry` / `place` fail if the prop's axis tilts past the bound |
| `grasp_sites[]` | `id`, `socket` (an existing socket), `hand` (`L`/`R`/`any`), `shape` (`wrap`/`pinch`/`palm`/`hook`/`cradle`), `approach`, `aperture`, `turnable`, `fingers {thumb, band}` | where a hand holds the prop. T-112a uses `wrap` only. `fingers` is read by T-051. |
| `grasp_sets[]` | `id`, `sites` (one or two site ids), `simultaneous_frames` | which sites are used together |
| `handover` | `give`, `receive` (set ids) | sets for the giver and the receiver (`pass`, T-112b) |
| `place` | `socket` (default `place`), `surface_normal`, `settle` (`rigid`/`soft`) | how the prop is put down |
| `push_pull` | `axis`, `sites`, `friction` | reserved for later verbs |
| `deform` | `mode` (`rigid`/`squash`/`bend`/`fold`), `squash` | only `rigid` is supported. Other modes load, but a verb on the prop fails with "deform mode not supported yet". |

Validation (`affordancesFromJson`) checks the following:
- every named socket exists;
- site and set ids are unique;
- every set names existing sites;
- `hands: "two"` has a set of two sites;
- `heavy` implies `hands: "two"`;
- enums, axes and bands are well formed.

An invalid block does **not** fail the asset. `PropAsset::affordances->error` keeps the message, and only a verb action
on that prop fails with it. `content/assets/felt_cup.asset.json` carries the block of design 2.5 (sites `side_a` on
`grip` and `side_b` on `grip_b`, sets `a` and `b`).
