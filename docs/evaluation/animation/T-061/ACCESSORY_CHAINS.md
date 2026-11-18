# Accessory secondary motion: spring chains on garment and accessory bones (T-061)

For T-044 (hair v3) and T-058 (hoodie, boy 2.0): how drawstrings, straps, bow tails and tassels get secondary motion
from data. It reuses the T-021 spring-chain solver (`engine/anim/secondary.h`, [SECONDARY_MOTION.md](../../../SECONDARY_MOTION.md))
unchanged; T-061 adds **presets** and **attach-by-name**. No engine change is needed per character or garment.

## What the pipeline has to provide

1. **Bones** for the part: a chain of deform bones, each the child of the previous one, the first parented to the
   bone the part hangs from (e.g. `chest` for hoodie strings, `head` for a bow). Name them `<prefix><n>`,
   `<prefix>.<n>`, `<prefix>_<n>` or `<prefix>-<n>` with `n` = 0, 1, 2 … from the root (numeric order, so `.10` comes
   after `.9`). Suggested: `DYN-<part>.<side>.<n>`, like the groom's `DYN-<structure>.<lock>.<k>`.
2. **Weights**: the part's vertices skinned to those bones (as the groom does for locks). The engine poses the bones;
   the bake carries them to the Blender render like any other bone.
3. **A chain entry** naming a preset in the rig's `ps_dynamics` metadata (exported today, see the end of this
   page), or an **attach entry** in the package's `dynamics` block / in the shot (scene override).

## Package block (`character.json` → `"dynamics"`)

```json
"dynamics": {
  "presets": {"drawstring": {"damping": 2.5}},
  "attach": [
    {"name": "string.L", "prefix": "DYN-string.L", "preset": "drawstring", "colliders": ["torso"]},
    {"name": "string.R", "prefix": "DYN-string.R", "preset": "drawstring", "colliders": ["torso"]},
    {"name": "bow.tail.1", "bones": ["DYN-bow.0", "DYN-bow.1"], "preset": "bow_tail", "tip": [0.05, 0.71, -0.02]}
  ],
  "colliders": [{"name": "torso", "type": "capsule", "bone": "chest", "a": [0, 0.40, 0.01], "b": [0, 0.55, 0.01], "radius": 0.08}]
}
```

| Attach key | Meaning | Default |
| --- | --- | --- |
| `name` | chain name (unique; scene overrides address it) | the prefix |
| `prefix` / `bones` | bones by name prefix (see above) or an explicit list, root first | — (one is required) |
| `preset` | spring preset: built-in or from `presets` | none: the solver's defaults |
| `group` | group name for scene overrides (`"chains": {"<group>": {...}}`) | the preset |
| `tip` | rest-space end of the last bone | last segment extended by its own length; one bone: 3 cm along parent → bone |
| `colliders`, `anchor`, spring keys | as for `chains` ([SECONDARY_MOTION.md](../../../SECONDARY_MOTION.md)); explicit keys override the preset | |

`presets` adds presets or changes built-in ones (field by field). A `chains` entry may also name a `preset`.

## Built-in presets (`builtinSpringPresets`)

| Preset | stiffness (tip) | damping | gravity | drag | limit° | radius | Intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `drawstring` | 25 (15) | 3.0 | 1.0 | 0.6 | 70 | 6 mm | a light cord: swings freely, settles slowly |
| `strap` | 90 (70) | 8.0 | 0.6 | 0.4 | 35 | 10 mm | a heavier band (bag strap, apron tie): little swing, quick settle |
| `bow_tail` | 40 (25) | 4.0 | 0.8 | 1.2 | 55 | 8 mm | ribbon ends: soft, slowed by air |
| `tassel` | 30 (20) | 3.5 | 1.0 | 0.8 | 60 | 8 mm | a short, heavy tip: gravity dominated |

Values are starting points measured on the toy fixture (a hips swing of ±50°: the tail lags up to 77 mm and settles
within 2 mm by 3 s, `tests/test_anim_principles.cpp`). Tune per part through the package `presets` / attach keys,
never in engine code.

## Scene override (shot JSON, character → `"dynamics"`)

`{"attach": [...], "presets": {...}}` adds chains for one shot (e.g. to try a part before the pipeline exports it)
and switches the layer on for that character unless `"enabled": false` is given. Package attach entries are resolved
first, so `"chains": {"string.L": {...}}` in a scene can tune them; chains the scene itself attaches carry their own
keys. A missing bone, a prefix that matches nothing, an unknown preset or a bone already used by another chain fails
the scene load with a message.

## Not done here

- No garment or hair data was changed (T-044 / T-058 own them); the boy 1.0.0 and girl m3 packages have no
  accessory bones, so no shot shows accessory motion yet. The mechanism is tested on the toy fixture's tail bones
  (`tail_1`, `tail_2`) and on a synthetic drawstring skeleton.
- **Exporter (checked, not changed: pipeline is outside this task's write-set).** `export_engine.py`
  (`export_dynamics`) rebuilds the block from the rig's `ps_dynamics` metadata: it carries `enabled`, `substep_hz`,
  `preroll_s`, `colliders` and `chains` (every chain key except `bones` / `tip` / `anchor` is copied as written, so
  **a chain's `"preset"` already reaches the package**), converting bone names and Blender coordinates. It does **not**
  carry `attach` or `presets`. So today a garment generator should write explicit `chains` entries (bones, tip in
  Blender world coordinates, `"preset": "drawstring"`) into `ps_dynamics`; `attach` / `presets` work from the package
  block or the scene once the exporter passes them through (a small change in `export_dynamics`: copy `presets`, map
  `attach[].bones` / `prefix` through `engine_name`, convert `attach[].tip`) — proposed for T-058 / T-044 or a
  pipeline follow-up. Not verified end to end in Blender in this task.
