# Animation clips (T-002, Acting Foundation stage A)

**Status:** implemented and tested on the boy (published 1.0.0) and the girl (unpublished build). The clips are
script-made technical validation clips. They are not final acting quality, and nothing is approved.

**The idea:**
- Body clips are authored once in Blender, on a neutral mannequin.
- They are stored in a character-independent library (`content/clips/`).
- The C++ engine retargets them to every humanoid from generated character data.
- They are layered with the existing actions (look, reach, walk, the life layer).
- They are rendered through the existing pipeline (engine bake, then Blender). There is no new render path.

```
mannequin (Blender) --make_clips/export_clip--> content/clips/<name>.clip.json --engine "clip" action--> bake --> Blender
   reference pose: rig profile          per role: rotations in reference space    retarget data: package block
```

## 1. Clip format `plush.clip/1` (`content/clips/<name>.clip.json`)
| Field | Meaning |
| --- | --- |
| `format`, `version` | `"plush.clip"`, `1` |
| `name`, `description` | identifiers |
| `fps`, `frame_count` | any rate; frames `0 .. frame_count-1`. A loop's period is `frame_count` frames (the frame after the last is frame 0) |
| `loop` | loopable clip (wraps; root motion continues with `root.cycle_offset`) |
| `tracks` | `{role: {"keys": [[frame, w, x, y, z], ...]}}` (sparse, slerp between keys) or `{role: {"samples": [[w, x, y, z], ...]}}` (dense, one per clip frame). Roles are the shared humanoid roles (`hips`, `spine`, `chest`, `neck`, `head`, `upperArm.L`, `forearm.L`, `hand.L`, `thigh.L`, `shin.L`, `foot.L`, fingers `thumbA/B`, `f0a..f3b`, and the `.R` mirrors), never a character's bone names |
| `mask` | the roles the clip drives (body-part mask for layering); default: its track roles |
| `root` | optional root motion: `translation` (keys `[frame, x, y, z]` or samples), in character space and engine axes, **divided by the leg length** (`scale: "leg_length"`); optional `heading` (degrees); optional `cycle_offset` for loops |
| `mirror` | `{"suffix": [".L", ".R"], "axis": "x"}`: mirroring swaps the sides and reflects rotations across x = 0 (`(w, x, -y, -z)`) |
| `source` | `"script"`, `"blender"` or `"mocap"` |
| `license` | **required**; `"project"` for script clips. `attribution` names the author or source |
| `contacts` | optional markers, e.g. `{"type": "foot_plant", "role": "foot.L", "frames": [a, b]}`, `{"type": "seat", "frames": [a, b], "height_ratio": r}` (seat top = r × the character's leg length) |
| `reference_pose` | the reference pose the clip was authored against (a copy of the rig profile block; the rules travel with the clip) |

**Rotations:**
- Each track value `L` is the role's local rotation relative to its semantic parent, in reference space: `R_role = R_parent · L`.
- The posed frame of a role is `R_role · Fref`, where `Fref` is the reference frame from `ref_dir` / `ref_twist`.
- Finger roles are ordinary tracks, so finger motion is optional per clip.

**Forward compatibility:**
- Readers ignore fields they do not know.
- Tools keep them: the engine keeps the raw JSON (`ClipData::raw`), and the exporter's output passes unknown metadata through.
- A new major change gets `version` 2. Version 1 files stay readable.

## 2. Neutral reference pose (shared data, once)
The reference pose lives in `pipeline/charsys/rig_profiles/humanoid_rigify.json` → `reference_pose` (version 1):
- **The pose:** a T-pose. Torso, neck and head upright; arms horizontal; palms down; legs straight; feet forward.
- **Axes:** engine axes (+Y up, the character faces +Z, its left is +X).

Per role it defines:
- `parent`: the semantic parent role. Clips are local to it. Arms hang from the chest and legs from the hips, even
  where a package's bones are top-level.
- **The rest direction rule:** towards the head of `end`, or along a fixed `end_dir` (head: up; foot: forward), or
  `continue` (distal finger joints), or `end_fallback_dir_from_parent`.
- **The twist reference rule:** `twist_hint`, made perpendicular to the direction. For the hand it is the vector from
  the pinky base to the index base (`twist_from`).
- `ref_dir`, `ref_twist`: the reference pose itself.

`.L` entries are mirrored to `.R`. Eyes are not clip roles: gaze belongs to look.

## 3. Character retarget data (generated, never hand-written)
**Written by the exporter:** `export_engine.py` (`EXPORTER_VERSION = "2"`) writes a `retarget` block into every
engine package. It is computed from the package's role pivots with the profile rules (`pipeline/clips/retarget.py`):
- per role: rest direction, twist reference and segment length (engine axes);
- `height`: the head-role pivot height above the ground;
- `leg_length`: thigh → shin → foot pivots.

**Packages without the block** (for example the frozen `tests/data` packages): the engine derives the same data from the
skeleton (`deriveRetarget`, `engine/model/clip.cpp`). Block and derivation agree to ≤ 0.0001° on the boy and girl
packages (`plush_tests` with `PLUSH_TEST_PACKAGE`, `test_clip_pipeline.py`).

**Cache key:** `run_shot.py` keys the package cache on the master hash and the exporter version, so packages are
re-exported when the exporter changes.

## 4. Retargeting (one algorithm, `engine/model/clip.{h,cpp}`)
**Per role:**
- The character's rest frame `C` comes from its retarget data.
- The correction is `A = Fref · C⁻¹`.
- The bone's rotation relative to its axis-aligned rest is `G_role = G_semanticParent · A_parent⁻¹ · L · A_role`. It
  is converted to the engine-local rotation through the bone's actual engine parent.

**Consequences:**
- When a whole chain is driven, every character's posed directions equal `R · ref_dir`. Rest pose and proportions
  drop out.
- A partial clip (for example arm only) is applied in the local space of the pose underneath it.

**Root motion** is the clip value × the character's leg length. There is no per-character code, data file or clip copy.

**Measured** (`docs/evaluation/animation/T-002/`):
- boy vs girl ≤ 0.95° on the driven roles. The worst case is an arm clip on top of each character's own rest torso;
  whole-body clips give 0.0000°.
- Synthetic skeletons: 0.00003°.
- Engine vs Blender mannequin ≤ 0.047°.

## 5. Authoring in Blender
- **Mannequin** (`pipeline/clips/mannequin.json`, `build_mannequin.py`): neutral proportions, built with
  `body_generic/1` and the shared Rigify fit (the same path as every new character). It is then converted to a plain
  FK deform rig with the reference-pose role hierarchy: control bones removed, constraints and drivers cleared,
  B-bones flattened.
- **Authoring:** an artist (or a script) rotates the role (`DEF-`) bones and keys an action. The action carries
  `ps_clip_meta` (name, fps, frame_count, loop, mask, contacts, source, license).
- **Export:** `export_clip.py --blend <file> --out content/clips` samples every frame. It converts the evaluated pose
  into `L` per role with the mannequin's own retarget data, and writes sparse keys (greedy key reduction, 0.02°
  tolerance) or dense samples.
- **The validation clips:** `make_clips.py` writes poses as joint rotations in each role's reference frame (for example
  `upperArm.L = rz(-76)` hangs the left arm down). Right-side clips are the mirror of the left-side definition.

| Clip | Content | Mask |
| --- | --- | --- |
| `idle_relaxed` | loop, 90 frames: arms down, breathing, weight shift, head drift | all roles |
| `wave` | right arm, palm forward, forearm swings in the frontal plane; held start and end | right arm |
| `point` | right arm forward, index straight, other fingers curled | right arm, hand, fingers |
| `sit_down` / `stand_up` | standing ↔ seated, with root motion down and back; seat contact `height_ratio` 0.617 | spine, chest, neck, legs (arms, hips and head stay with the base layer) |
| `dense_test` | 60 fps, 120 dense frames on several roles (mocap-like data) | all roles |

## 6. Playback: the `clip` action (`engine/scene/actions.cpp`, `clip_layers.cpp`)
```json
{"type": "clip", "character": "boy", "clip": "wave", "start": 10, "end": 120, "speed": 1, "weight": 1,
 "blendIn": 6, "blendOut": 6, "loop": false, "mirror": false, "base": false}
```
**Fields:**
- `clip`: a library name. It resolves to `content/clips/<name>.clip.json`, found by walking up from the scene file;
  `file` gives a path instead.
- `start`, `end`: scene frames. Without `end`, a non-looping clip ends after its length; past its last frame a clip
  holds the last pose until `end`.
- `speed`: a time scale. Any source fps works: clip frame = (scene frame − start) × speed × clip fps / scene fps.
- `blendIn` / `blendOut`: smoothstep ramps in scene frames. The clip's first frame (weight 0) equals the underlying pose.
- `base: true`: the character's base layer for the whole shot. It replaces the package's default pose (the A-pose),
  with no blend.

Studio and scene files use this same JSON. No new UI is needed.

## 7. Layering (order of a character's pose)
1. Keyed and generated tracks (unchanged).
2. **Base clip** on its mask. Generated action motion (walk arm swing, reach lean) is added on top of it as a change
   relative to the default pose.
3. **Clip actions** in start order, each overriding its mask with its blend weight:
   - **Walk:** a walk keeps the hips, legs and root (clip weight × (1 − walk ownership), ramped over 4 frames).
   - **Arm clips during a walk:** an arm clip replaces the walk's arm swing **only on the roles in its mask**; the
     other arm keeps the swing (owner-approved rule).
   - **Hand keys:** a hand-keyed role (`<char>/<role>.rot` keys) always wins.
4. Life layer (breathing, sway, head follow): unchanged, on top.
5. Constraints: IK (reach, touch, foot plants), hand pose and look. They run after the clips, so **reach/grasp keeps
   its arm and look keeps the gaze**.
6. Clip finger tracks, unless a hand track (reach, touch, hand keys) owns that hand.

**Without clip actions none of this runs:** the old code path is used unchanged. The s010 bake is byte-identical with
`main`.

## 8. Future motion capture (not implemented)
A converter maps a BVH (or similar) take into `plush.clip/1` without format changes:
1. **Role mapping:** map the source joints to roles (a mapping table per mocap skeleton family, like a rig profile).
2. **Source frames:** compute the source's rest frames with the same rules: direction to the child joint, twist from
   a hint. A BVH has no meshes, so the rules work on joint positions, exactly as `deriveRetarget` does.
3. **Per frame and role:** `R = G_source · C_source · Fref⁻¹`, then `L = R_parent⁻¹ · R`. Write dense `samples` at
   the source fps.
4. **Root:** the root translation relative to the first frame, divided by the source leg length; heading from the hips'
   yaw if wanted.
5. **Metadata:** `source: "mocap"` with `license` and `attribution` filled from the take's licence, foot-plant
   contacts from velocity thresholds, `mask` from the joints present.

The engine already plays dense data at any fps (`dense_test`).

## 9. Limits (known)
- **Clip quality:** the clips are mechanical script poses; acting quality and the reference videos remain future work.
- **Rigid shoulders and hips:** in the Rigify packages, arms and thighs are top-level engine bones. A torso lean
  rotates the arms through the semantic hierarchy, but their pivots do not follow the chest. Sit and stand lean only
  a little.
- **Foot planting:** root motion scales with the leg length. Characters whose thigh/leg ratio differs from the
  mannequin's can show slight foot sliding while sitting. The foot-plant contacts are recorded for a later IK fix-up;
  they are not used yet.
- **Boxes:** box objects are static in the bake (bake v1). An object carried by a reach does not move in the Blender
  render.
