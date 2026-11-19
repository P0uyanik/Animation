# T-112a evidence: affordances, verb expander, pick up / carry / place

Input 6df7e8e (integration/t-094b), branch `t-112a-claude-verbs`. This is a technical task: one cheap preview frame
and no strict sheet.

## Demo shot `episodes/e907_exchange/shots/s010_verbs/`
The staging, set, camera and cast are those of e907 `s010`, cast with the current approved versions (boy 2.0.0, girl
0.11.0, resolved by `run_shot` cast `current`). The shot has `"timing": "calibrated"`, and the boy has
`"personality": "boy_yellow_hoodie"` (tempo `beat_scale` 1.2). The boy acts through three verb actions:

```json
{"type": "pick_up", "character": "boy", "hand": "R", "prop": "cup", "set": "a", "start": 8},
{"type": "carry",   "character": "boy", "hand": "R", "by": [0.02, 0.04, 0.0]},
{"type": "place", "verb": true, "character": "boy", "hand": "R", "at": [-0.025, 0.4695, 0.02]}
```

The girl watches the cup through a `look` with the new `atProp`. Her personality is not set, so her life values stay
as in `s010`. `s010` and `s010_calibrated` are unchanged; the golden test covers them.

`s010_verbs.expanded.scene.json` is the scene after the verb expander: the primitive actions and phase spans
(`x_t112a_phases`). It was dumped with a scratch program that calls `expandVerbs`, and it is not part of the build.
The phases in frames, with the boy's tempo applied:

| verb | look | anticipate | approach | contact | manipulate | release | settle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pick_up | 1-8 (7) | 8-18 (10) | 18-31 (13) | 31-37 (6) | | | 37-51 (14) |
| carry | | | | | 51-67 (16) | | 67-81 (14) |
| place | 74-81 (7) | | | 107 | 81-107 (26) | 107-124 (17) | 124-138 (14) |

The bake (`run_shot --stages prepare,bake`, bpy 5.3.0 module through `tools/bpy_blender.py`) passed every verb
constraint (reach, palm on socket, place contact, upright) with no interaction warnings.

## animcheck timing rule (`tools/animcheck/timing.py`, warnings only)
| file | scene | warnings |
| --- | --- | --- |
| `timing_s010_verbs.json` | s010_verbs as authored | 0 (0 beats: the read-only rule does not know verb types; still check only) |
| `timing_s010_verbs_expanded.json` | s010_verbs expanded | 0 (4 beats: reach 19, carry 16, place 26, release 17) |
| `timing_s010.json` | s010 (baseline, the same engine build) | 3 (hold reach 8 f, shared_hold 6 f, release 10 f) |

The verbs add no new timing warnings. The longest still run is 67 frames (f36 to f103).

## Preview
`s010_verbs_preview_f037_cycles4spp.png` is frame 37 (the pick-up contact), Cycles at 4 spp and 320x180, rendered
with `run_shot --frames 37-37 --samples 4 --resolution 320 180`. The boy's right palm is on the cup's `grip` side,
and the girl looks at the cup. `tools/review/recipe.py preview` renders character turnaround columns (reference,
previous, candidate) and has no shot-frame input, so the shot's own render path was used for the one cheap frame.

## Not verified
- No strict sheet (technical task).
- No full-length render or video.
- The girl's acting is unchanged from `s010` (she only watches).
