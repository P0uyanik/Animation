# Animation clips (T-002, Acting Foundation stage A)

**Status:** implemented and tested on the boy (published 1.0.0; T-027 also on the unpublished 1.1.0 candidate) and
the girl (unpublished build). The clips are script-made. T-027 gave the gesture, idle and emotion clips an acting pass
with shared animation principles (section 5a) and added the automatic base idle (section 6a). Nothing is approved.

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
| `idle_relaxed` | loop, 180 frames (6 s): asymmetric contrapposto stance (weight on the right leg, feet planted, free knee bent), slow weight drift, breathing travelling up the spine, head drift, arm overlap; root motion (weight shift) | all roles |
| `wave` | 90 frames: right arm, palm forward, three waves; anticipation, successive breaking, overshoot / settle, hip and spine support; held rest frames at both ends | hips, spine, chest, right arm, hand, fingers |
| `point` | 84 frames: right arm forward, index straight, other fingers curled; anticipation, overlap, an emphasis push, settle; weight towards the target, chest turn, lean in | hips, spine, chest, right arm, hand, fingers |
| `sit_down` / `stand_up` | standing (the idle's stance) ↔ seated, with root motion down and back; seat contact `height_ratio` 0.617 | spine, chest, neck, legs (arms, hips and head stay with the base layer) |
| `dense_test` | 60 fps, 120 dense frames on several roles (mocap-like data) | all roles |

The emotion clips (`emo_*`, `gest_shrug`, `gest_yawn`) come from `make_emotion_clips.py` with the same helpers
(`docs/EMOTIONS.md`): postures start from the idle's asymmetric stance arms; loops travel up the chain with per-joint
phase lags and eased, non-sinusoidal pulses; the shrug (chest, neck, head, arms) and the yawn (torso, arms) use
anticipation, overshoot / settle and successive breaking, with the two arms out of sync.

**Regenerate** (headless Blender; the mannequin from `build_mannequin.py`):
```
blender -b --factory-startup -P pipeline/clips/make_clips.py -- --mannequin <dir>/neutral_mannequin.blend --out content/clips
blender -b --factory-startup -P pipeline/clips/make_emotion_clips.py -- --mannequin <dir>/neutral_mannequin.blend --out content/clips
```
Both are deterministic: the same scripts and mannequin give byte-identical files.

## 5a. Acting principles (`pipeline/clips/clip_principles.py`, T-027)
Shared, parameterised authoring helpers on the shared skeleton roles. Pure Python (no Blender), no character names;
poses are `{role: L}` in the clip convention and root offsets are in leg lengths.

| Principle | Helper | What it does |
| --- | --- | --- |
| Eased spacing | `ease(u, kind, power)` | `linear`, `in`, `out`, `inout` (power > 1 sharpens it) instead of uniform spacing |
| Anticipation, overshoot, settle | `move(u, anticipation, ant, overshoot, settle, power, bounce)` | a 0 → 1 transition: a counter-move to `-anticipation` over the first `ant` of the time, the eased main move to `1 + overshoot`, a settle back to 1 with one small damped undershoot; every phase joins with zero velocity (C1) |
| Successive breaking / overlap | `perform(beats, n, delay, follow)` with `Beat(frame, pose, **motion)` and `chain_delays()` | each role reaches a beat `delay[role]` frames late (spine, chest → shoulder → elbow → wrist → fingers), so the joints no longer rotate in sync and the hand path arcs; overshoot grows past the shoulder (follow-through); `per_role` overrides single roles |
| Whole-body support | `support(pose, side, k, tilt, counter, chest, yaw, lean, shift)` | the pelvis shifts towards the action side and hikes there, spine and chest counter-rotate, the trunk turns and leans; returns the root offset |
| Planted feet | `plant_legs(pose, root, body)` with `Body.from_heads()` | two-bone IK in reference space: both feet stay at their reference position, flat and forward, under the hips rotation and root offset; the root sinks where a leg cannot reach (the free knee bends) |
| Loops | `periodic()`, `lagged()` | harmonics and per-depth phase lags for idles |

`make_clips.py` keys every frame of the acting clips, so the spacing is the authored one (not Blender's interpolation);
the exporter's key reduction (0.02°) keeps the shape.

**Gestures do not own the legs or the root.** A gesture (wave, point) drives hips, spine and chest for support but
leaves the legs and root to the layer underneath, so it also plays over a sit or a walk without moving the feet. The
weight shift with planted feet lives in the base idle.

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

## 6a. Automatic base idle (T-027, `clip_layers.cpp`)
A character with **no base clip action** plays the shared `idle_relaxed` as its base layer automatically, so nobody
stands frozen in the package's default pose:
- **Who:** humanoid engine packages with generated retarget data (exporter version ≥ 2; the production path). The
  clip must be found in `content/clips` above the scene file, and the character must have the core roles (hips, spine,
  chest, head, both upper arms and thighs). Procedural characters and legacy packages without the `retarget` block
  (for example the frozen `tests/data` packages) keep their default pose.
- **Opt out** per character in the scene: `{"name": "boy", ..., "autoIdle": false}` (written back only when false).
- **Timing:** loops for the whole shot, with a per-character phase offset from its name, so two characters do not
  breathe in sync.
- **Layering:** exactly like a `base: true` clip (tier 0, under emotions and clip actions). Any base clip action replaces
  it; the check is made at evaluation, so recompiled actions decide.
- **Existing shots:** bakes change only for characters without a base clip (e000, e900 in this repository); shots
  with a base clip keep their base. The life layer (breathing, sway, blinks) is unchanged and still adds on top;
  test shots that disable blinks keep them disabled.
- **Measurement scenes** that need a clip alone (`measure_clips.py` per-clip and walk-alone scenes,
  `measure_shot.py` before/after mode) set `"autoIdle": false`.

## 7. Layering (order of a character's pose)
1. Keyed and generated tracks (unchanged).
2. **Base clip** on its mask. Generated action motion (walk arm swing, reach lean) is added on top of it as a change
   relative to the default pose.
3. **Clip actions** in start order, each overriding its mask with its blend weight:
   - **Walk:** a walk keeps the hips, legs and root (clip weight × (1 − walk ownership), ramped over 4 frames).
     The base clip's legs also follow the walk while it owns them (T-027): the base idle's weight shift, for
     example a bent free knee, does not leak into the walk; the hips keep the base pose plus the walk's change.
   - **Arm clips during a walk:** an arm clip replaces the walk's arm swing **only on the roles in its mask**; the
     other arm keeps the swing (owner-approved rule).
   - **Hand keys:** a hand-keyed role (`<char>/<role>.rot` keys) always wins.
4. Life layer (breathing, sway, head follow): unchanged, on top.
5. Constraints: IK (reach, touch, foot plants), hand pose and look. They run after the clips, so **reach/grasp keeps
   its arm and look keeps the gaze**.
6. Clip finger tracks, unless a hand track (reach, touch, hand keys) owns that hand.

**Without clip layers none of this runs:** the old code path is used unchanged. Since T-027 a humanoid package
character without a base clip has the automatic idle as its clip layer (section 6a); with `"autoIdle": false` (or a
procedural / legacy package) the old path runs, as before.

## 7a. Emotions (T-003)
Emotions (`docs/EMOTIONS.md`) reuse this clip path: an `emotion` action plays a posture clip and an optional
gesture clip (`content/clips/emo_*`, `gest_*`, made with `pipeline/clips/make_emotion_clips.py`) as **tier-1** layers:
above the base clip, below clip actions; walk, IK, look and hand keys keep their priority. Emotion layers blend in
the clip's reference-space rotations (intensity k = k × the deviation), and consecutive emotions crossfade. The clip
format is unchanged; `clip` actions behave exactly as before.

## 8. Exact quaternion and retarget convention (including future motion capture)

**Multiplication convention and spaces.** Quaternions are stored as `(w, x, y, z)` and use the Hamilton product. In
`q1 · q2`, `q2` acts first: rotating a vector is `q · v · q⁻¹` (`pipeline/clips/retarget.py:132-151`; clip JSON is
read in that component order at `engine/model/clip.cpp:195-196`). For a role `r` and its nearest present semantic
parent `p`:

- `F_r = frame(ref_dir_r, ref_twist_r)` is the shared reference-pose frame, expressed in character/engine axes. It is
  not parent-local. `frame(d, t)` uses the orthonormal basis whose columns are `x = d × t`, `y = d`, `z = t`, after
  making `t` perpendicular to `d` (`pipeline/clips/retarget.py:178-183`, `engine/model/clip.cpp:18-21`).
- `C_r = frame(dir_r, twist_r)` is the character (or mocap source) rest frame, also expressed in character/engine
  axes, not parent-local. Despite the shorthand “retarget quaternion”, the package `retarget` block contains `dir`
  and `twist` vectors, not quaternion fields; the engine reads and orthonormalizes those vectors, then constructs
  `C_r` when binding the clip (`engine/model/clip.cpp:138-153`, `engine/model/clip.cpp:313-322`). The scene uses that
  package block when its reference version matches, otherwise it derives the same vectors from the skeleton
  (`engine/scene/clip_layers.cpp:43-49`).
- `G_r` is the role bone's character-space rotation delta from its own rest orientation; it is not a bone-local
  rotation and it is not reference-pose-relative. The Blender exporter obtains it as evaluated character-space
  rotation times inverse rest character-space rotation (`pipeline/clips/clip_tools.py:113-120`).
- `R_r = G_r · C_r · F_r⁻¹` is the role's character-space posed frame expressed relative to the shared reference
  frame. `R_r` is still per-role, not parent-local. The stored clip value is
  `L_r = R_p⁻¹ · R_r = A_p · G_p⁻¹ · G_r · A_r⁻¹`, where `A_r = F_r · C_r⁻¹`; for no semantic parent, `R_p`,
  `G_p`, and `A_p` are identity. This is the exact exporter order (`pipeline/clips/clip_tools.py:63-72`,
  `pipeline/clips/clip_tools.py:122-133`).
  Dense and sparse tracks both store this `L_r`; sampling only interpolates it and optionally mirrors it
  (`engine/model/clip.cpp:286-293`).

**Playback.** Binding converts the target character's retarget vectors to `C_r` and stores only
`A_r = F_r · C_r⁻¹` (`engine/model/clip.cpp:313-322`). In semantic-parent order the full-weight target is
`G_r^target = G_p^result · A_p⁻¹ · L_r · A_r`; `G_p^result` is the semantic parent's character-space result after
this layer, including the underlying pose when that parent is not driven (`engine/model/clip.h:130-148`). The engine
then converts that character-space target to the actual skeleton-parent-local quaternion as
`Q_r^local = (G_engineParent^current)⁻¹ · G_r^target` and blends/writes `Q_r^local` into `pose.local`
(`engine/model/clip.h:142-148`). Thus “local” has two distinct meanings: clip `L_r` is local to the **semantic**
parent in reference-pose-relative space; `pose.local` is local to the **actual engine bone parent**.

**Worked two-role example (`p → r`).** Let superscript `s` mean the source rig and `t` the target character.

1. From their rest frames, the source corrections are `A_p^s = F_p · (C_p^s)⁻¹` and
   `A_r^s = F_r · (C_r^s)⁻¹` (`pipeline/clips/clip_tools.py:63-66`).
2. For one source frame, `R_p = G_p^s · C_p^s · F_p⁻¹` and `R_r = G_r^s · C_r^s · F_r⁻¹`, so the exported child
   sample is
   `L_r = R_p⁻¹ · R_r = F_p · (C_p^s)⁻¹ · (G_p^s)⁻¹ · G_r^s · C_r^s · F_r⁻¹ = A_p^s · (G_p^s)⁻¹ · G_r^s · (A_r^s)⁻¹`
   (`pipeline/clips/clip_tools.py:122-133`).
3. Playback builds `A_p^t = F_p · (C_p^t)⁻¹` and `A_r^t = F_r · (C_r^t)⁻¹`, then computes
   `G_r^t = G_p^t · (A_p^t)⁻¹ · L_r · A_r^t` (`engine/model/clip.cpp:313-322`,
   `engine/model/clip.h:139-146`). Substitution gives `G_r^t · C_r^t = R_r · F_r` whenever
   `G_p^t · C_p^t = R_p · F_p`: the target rest frames cancel, while the source's reference-relative motion remains
   (`pipeline/clips/clip_tools.py:122-133`, `engine/model/clip.h:139-146`).

**Future mocap conversion (not implemented).** Map source joints to semantic roles, derive each `C_r^s` from joint
positions with the existing direction/twist rules (`pipeline/clips/retarget.py:95-129`), calculate each frame's `G`
and then `L` exactly as in the worked example, and write dense `samples` at the source fps
(`pipeline/clips/clip_tools.py:175-192`, `pipeline/clips/clip_tools.py:208-226`). Root translation is the source root
offset divided by source leg length (`pipeline/clips/clip_tools.py:134-137`,
`pipeline/clips/clip_tools.py:193-199`). Metadata remains `source: "mocap"`, its licence and
attribution, contacts, and a mask of present joints. The engine already plays dense data at any fps (`dense_test`).

**Open issues.** Full-weight authoring/export and playback agree, but fractional blending uses two spaces. Ordinary
and base clips retarget first and slerp the resulting actual-engine-parent-local quaternion
(`engine/model/clip.h:142-146`; callers at `engine/scene/clip_layers.cpp:84-86` and
`engine/scene/clip_layers.cpp:118`). Tier-1 emotion layers instead
recover the underlying semantic/reference-space value as `L_r^under = A_p · G_p⁻¹ · G_r · A_r⁻¹`, slerp it toward
the clip's `L_r`, and apply that result at full weight (`engine/scene/clip_layers.cpp:97-115`). The endpoints agree,
but intermediate rotations need not when the semantic parent differs from the actual engine parent. Code is
unchanged.

## 9. Limits (known)
- **Clip quality:** the clips are script-made. T-027 added anticipation, overlap, overshoot / settle, support and
  eased spacing (measured in `docs/evaluation/animation/T-027/`); they are still not reviewed acting, and nothing is
  approved.
- **Pelvis tilt on top-level thighs:** clips plant the feet in the semantic hierarchy (thighs hang from the hips). In
  the Rigify packages the thighs are top-level engine bones, so a pelvis tilt does not move the hip joints: with the
  idle's 1° tilt a foot can be off by about 1–2 mm vertically. The tilts are kept small for that reason.
- **Asymmetric idle and mirrored gestures:** a gesture starts from an upright trunk and the stance arms of its own
  side. Over the asymmetric idle, a mirrored gesture blends from the idle's other arm (a few degrees, inside the
  blend-in).
- **Rigid shoulders and hips:** in the Rigify packages, arms and thighs are top-level engine bones. A torso lean
  rotates the arms through the semantic hierarchy, but their pivots do not follow the chest. Sit and stand lean only
  a little.
- **Foot planting:** root motion scales with the leg length. Characters whose thigh/leg ratio differs from the
  mannequin's can show slight foot sliding while sitting. The foot-plant contacts are recorded for a later IK fix-up;
  they are not used yet.
- **Boxes:** box objects are static in the bake (bake v1). An object carried by a reach does not move in the Blender
  render.
