# T-196 · Blender-first or hybrid? Architecture review (research only)

Owner request 2026-11-22 ~14:05 CET. Branch `t-196-claude-blender-hybrid-review` from `main@3183184`. Docs only: no
code, packages, bakes or goldens change. It builds on four earlier reviews and does not repeat them:
[T-174](../../evaluation/animation/T-174/README.md) (animation reuse vs build),
[T-176](../T-176/REPORT.md) (workflow and cost), [T-189](../../evaluation/world/T-189/README.md) (world assets) and
[T-193](../../evaluation/characters/T-193/README.md) (hair hybrid). Work already running is left alone: T-183 (hair
colliders), T-190 (finger limits), T-191 (body clearance), T-194 (hair push-out at render time) and T-195 (vocal sounds).

## The short answer

1. **Is our approach the best one? Mostly yes.** We already use Blender for everything to do with how things look.
   Blender builds the characters (body, face, garments, hair, materials, Rigify rig, face shape keys driven by
   controls) and renders every final frame in Cycles. Our engine decides how things move: acting, verbs, grasp,
   timing, the mocap walk, camera choice. It writes those decisions into one exact bake (TD-35, TD-42, TD-44). That
   split is sound, and moving the animation into Blender would cost weeks and gain nothing, because nobody animates
   by hand in Blender.
2. **The one weak spot is contact.** The engine checks contact against simplified shapes: spheres for hair, capsules
   and ellipses for bodies and hands. The real meshes only exist in Blender. So the same kind of fault keeps coming
   back in new places: hair in the body or the table (T-183, three rounds), garments under the skin when seated
   (T-184), bodies through each other (T-191), arm clearance (T-040r1, T-047). T-193 found the fix for hair: **the
   engine keeps planning the motion, and Blender checks and corrects the contact on the real meshes at render
   time.** We should make that the standard pattern for every kind of contact, not a hair-only patch.
3. **The steps after the render have not been built yet**: editing shots together, sound, final image polish.
   Blender's built-in tools cover all three, run without a screen and give the same result every run. Our own probe
   mixed two sound tracks twice and got identical files (appendix A). We should use them instead of writing our own.
4. **Don't move** acting, locomotion, IK, hands or the camera into Blender (NLA, a Rigify control rig, Blender IK).
   Don't switch hair to Blender's experimental hair simulation. Don't add paid or outside tools. Reasons are in
   section 3.
5. **Size of the change:** 4 quick wins (about 4–6 task-days in total) and 3 larger steps (about 8–13 task-days).
   None of them touches the engine's animation core or the approved character versions without a new version and
   the owner's approval.

## 1. What tools and resources help the whole project (question 1)

| Kind | Already in use | Worth adding (free, no paid tools) |
|---|---|---|
| Blender built-ins | bpy 5.3.0 pinned, Rigify metarig, shape keys + drivers (face), Armature/Shrinkwrap/Solidify/Subsurf/Surface Deform modifiers, BVH trees (27 charsys files), Cloth (skirt prototype, T-126c), Geometry Nodes and hair curves (groom), Cycles + OIDN, EEVEE (selectable, not measured for looks), library overrides for linked masters | **Corrective Smooth** and corrective shape keys at joints, the **compositor**, the **Video Sequencer** (edit + sound mix), Mesh Cache playback for more cloth bakes, Grease Pencil v3 / Geometry Nodes for effects when a scene needs them. All of these exist in our 5.3.0 build (probe, appendix A) |
| Our engine | verbs, affordances, grasp, personality, reactions, timing, director, mocap retarget + foot lock, spring chains, shot bake, motion_checks, animcheck | nothing new: finish the running tasks |
| Open data and tools | CMU mocap (T-175), Rhubarb Lip Sync 1.13.0 ([LIPSYNC.md](../../LIPSYNC.md)), Poly Haven + ambientCG CC0 (T-170c/d, T-189), ffmpeg | CC0 kit models from Quaternius (host reachable now) and Kenney (see appendix B); CC0 sound effects for the episode layer (the source still to be chosen with T-195) |

## 2. Area map: today vs a Blender or hybrid alternative

"Effort" is in task-days. "Keep" means the current path stays. Determinism is checked on the pinned bpy 5.3.0.

| Area | Today (where) | Blender / hybrid option | Quality | Effort | Main risk | Verdict |
|---|---|---|---|---|---|---|
| **Characters** (body, face, garments, groom, materials) | Already built in Blender by our Python generators (`pipeline/charsys/`, TD-37 to TD-41) | Geometry Nodes generators instead of Python | same | high (rewrite) | new versions of every character | **Keep**. Already Blender-first |
| **Rig and joint deformation** | Rigify deform rig, weights from role rules, plain linear skinning; known stiff shoulders and hips ([ANIMATION_CLIPS §9](../../ANIMATION_CLIPS.md)) | **Hybrid:** the character build adds corrective shape keys at shoulders, hips, elbows and knees, driven by bone angle (the same driver mechanism the face already uses), plus Corrective Smooth on the render mesh | + better bends and fewer gaps | 3–5 + 1 review round | needs new character versions; engine previews and collision proxies don't see the correction (a few mm) | **Adopt (L2)** |
| **Acting, verbs, reactions, timing** | Engine (`engine/scene/verbs.*`, `reaction.*`, `anim/personality.*`, `content/`) | NLA strips / animation layers in Blender | − (needs a person keyframing by hand) | weeks | loses data-driven, tested behaviour | **Keep** (T-174) |
| **Locomotion** | CMU mocap clips + foot lock in the engine (T-175, merged) | Blender retarget add-ons | same | — | — | **Keep** (T-174) |
| **IK, constraints, hands, grasp, finger limits** | Engine IK and constraints (TD-18), grasp, T-190 limits; the bake mutes Blender constraints | Blender IK and Limit Rotation constraints at render time | − (would fight the engine's hand placement on props) | 3–5 | two places deciding the same pose | **Keep**; let the contact audit (Q1) measure hand–prop contact on the real meshes |
| **Hair** | Engine spring chains (T-183) + T-194 push-out on real meshes | Blender GN Hair Dynamics (experimental) | − (stretch 1.3–2.4×, T-193) | 6–10 | API "may change" | **Keep the T-193 hybrid** |
| **Garments in motion** | Skinned with the body; opt-in "seated" key (T-184); skirt cloth bake prototype in Blender, baked to a cache and played back ([cloth_sim](../../../pipeline/charsys/cloth_sim/README.md)) | **Hybrid:** use the same push-out step as hair for tight garments (lift any garment vertex that ends up inside the posed body, at render time), and the cloth bake for loose pieces (skirts, dresses, hoods) | + no skin through cloth when seated, natural skirts | 3–5 | cloth gives the same cache twice on one machine; across machines not tested | **Adopt (L1)** after T-194 |
| **Collisions and contact** | Engine proxies: torso sections and hand capsules (T-047), body-part capsules (T-191), hair spheres (T-183) | **Hybrid:** the engine keeps its proxies for planning; Blender measures contact on the final meshes in every shot and the push-out steps fix what is left | + we measure what the owner actually sees | 1.5–2 for the audit | measuring only, so the risk is low | **Adopt (Q1)** |
| **Props and world** | Engine places props; Blender renders boxes and asset props from the bake; T-189 CC0 + material override plan | Blender-native set files | + | as T-189 | — | **Keep T-189**, plus Q4 |
| **Lighting** | Engine lights translated into Blender with an approximate scale ([PRODUCTION_PIPELINE](../../PRODUCTION_PIPELINE.md), "Not covered yet") | **Light rigs and HDRI saved in the Blender set file**, picked by name in the shot | + no translation error; built and seen in Blender | 1–1.5 | engine previews are lit differently (previews only) | **Adopt (Q4)** |
| **Camera and staging** | Engine director (TD-33), camera every frame in the bake, depth of field translated | Blender camera rigs and constraints | same | — | — | **Keep** |
| **Rendering** | Cycles `final720` about 208 s per frame, `review` about 65 s (T-124); no compositor; EEVEE selectable but not measured | (a) **compositor preset**: soft glow, colour grade, vignette, opt-in per profile; (b) **measure EEVEE** for review and timing renders; (c) GPU, already studied (T-050, T-173) | + finish; review renders far faster | 0.5–1 + 1 | (a) changes the look, so the owner approves; the compositor's Python API changes in 6.0 (probe warning). (b) fibre and skin look differs in EEVEE, so review renders only | **Adopt (Q2, Q3)** |
| **Edit, sound, episode** (V8) | One video per shot via ffmpeg (`run_shot.py`); lip sync tools; T-195 vocal sounds; no sequence assembly | **Video Sequencer**, run by script: shot strips + dialogue + effects + music, volume keys, then our ffmpeg encode (T-166) | + one timeline in frames, so lip sync and sound stay aligned | 2–3 | small: our probe mixed the same sound file twice | **Adopt (L3)** after T-195 |
| **Effects** (sparkle, surprise marks; V4) | none | Grease Pencil v3 or Geometry Nodes particles in the render scene | + | 1–2 when needed | style decision | **Later**, when a scene needs one |
| **Review and tests** | goldens, determinism tests, motion_checks, animcheck, contact sheets | real-mesh contact numbers (Q1) in every shot's run report | + | inside Q1 | — | **Keep**, plus Q1 |

## 3. What not to move to Blender, and why

- **Animation authoring in Blender** (NLA, action layers, a Rigify control rig, Blender IK). Blender's animation
  tools are built for a person moving controls in the viewport. Here, agents write data and the engine turns it into
  motion that is tested, repeatable and the same for every character. Using Blender's tools would mean keyframing by
  hand and would break the exact bake, the goldens and the Studio previews. The owner decided on 2026-11-15 that the
  engine stays the animation authority, and T-174 confirmed it.
- **Blender's experimental hair simulation, Cloth on hair ribbons, rigid-body characters.** In T-193's tests these
  stretched, tangled or blew up. The cloth bake stays for skirt-like garments, where it works.
- **Asset Browser and other viewport-first tools.** The user never opens Blender (TD-35), so the gain is small;
  linking masters and set files already does the job.
- **External or paid tools** (Houdini, Cascadeur, Auto-Rig Pro, ML motion). T-174 and T-193 already rejected them.
  They also go against the owner's 13:45 CET guidance.

## 4. Ranked recommendations

### Quick wins (each ≤ 2 task-days, no change to approved characters or the engine)

| # | What | Effort | Benefit | Risk |
|---|---|---|---|---|
| Q1 | **Real-mesh contact audit** in `shot_render.py` (or a sibling script). On the final evaluated meshes in Blender, every frame: body vs body, hair vs body and props, garment vs body, hand vs prop. Report frames, depth and parts in the shot's run report. Reuse the BVH code of T-183/T-194, the T-191 numbers and `cloth_sim` penetration. Start after T-194 merges, to avoid touching the same file | 1.5–2 | One number for "does anything go through anything" in what the owner sees; catches problems before the owner does | low (measuring only); render time +1–3 s per frame (E) |
| Q2 | **Compositor look preset** (soft glow, gentle grade, vignette) as an opt-in field in `render_profiles.json` | 0.5–1 | Finish closer to the benchmark at no render-time cost | the look changes, so the owner reviews it side by side; the Python API changes in 6.0 |
| Q3 | **Measure EEVEE as a review profile**: time per frame and side-by-side with Cycles `review` on one shot (T-074 is on hold) | 1 | If it holds up, timing and acting reviews take seconds per frame instead of about 65 s | fibre and skin look differs, so it is never used for final frames |
| Q4 | **Lights and HDRI kept in the Blender set file**, picked by name in the shot; the engine lights stay for previews | 1–1.5 | No approximate light translation; ties in with T-189's room | engine previews are lit differently (acceptable) |

### Larger steps (each needs an owner decision first)

| # | What | Effort | Benefit | Risk |
|---|---|---|---|---|
| L1 | **Garment contact hybrid**: render-time push-out of garment vertices that end up inside the posed body (the same method as T-194), and the existing cloth bake extended to skirts, dresses and hoods, opt-in per shot | 3–5 | Fixes "garment under skin" and "thigh through the front panel" (T-184 follow-ups) everywhere, not shot by shot | cloth determinism across machines not tested (keep the pinned Blender and the stored caches); render time per shot goes up |
| L2 | **Joint correctives**: the generators add pose-driven corrective shape keys and Corrective Smooth at shoulders, hips, elbows and knees | 3–5 + review | Softer, plush-like bends; fewer gaps at the shoulders and pelvis in leans (T-174 risk list) | new character versions and owner approval (TD-36); engine previews don't show it |
| L3 | **Episode layer on the Video Sequencer**: shots, dialogue, vocal sounds, effects and music on one timeline; mixdown to WAV; final encode with the existing ffmpeg step | 2–3 | V8 without building our own editor; exact frame alignment for lip sync | low; start after T-195 so the sound formats are settled |

Suggested order: Q1 → Q4 → Q2/Q3 (in parallel) → L1 → L3 → L2 (last, because it needs new character versions).
Total about 12–19 task-days, compared with continuing to fix contact one shot and one system at a time, which
has no clear end (T-183 is in its third round).

## 5. Verdict: is our current approach the best one?

**Yes for the split, no for contact, and incomplete after the render.**

- The engine/Blender split is right. Blender does what it is strong at (meshes, materials, deformation, rendering),
  and the engine does what Blender can't do without a human animator (data-driven acting that is the same for every
  character and can be tested). The exact bake between them is cheap and has been verified (0.0003 mm, 0.0°).
- We are not using Blender enough where the real geometry matters, which is contact. The engine should keep
  planning with its simple shapes, but whether something touches or passes through should be measured, and finally
  corrected, on the real meshes in Blender. T-193 showed this works for hair (120 of 120 frames inside the body → 0)
  and stays repeatable.
- The steps after the render (edit, sound, image finish) are missing, and Blender already has all of them built in.

**Development approach.** Keep the measured, opt-in, evidence-first way of working (TD-35: "nothing kept because it
exists, nothing discarded without evidence"). Add one rule: *before a new engine-side collision or proxy feature,
check whether a measure-and-correct step on the real meshes in Blender would do the same job.* That rule would have
shortened T-183 and T-184.

## Appendix

### A. Probe run here (bpy 5.3.0, `blender -b --factory-startup`)
Script [`probe/probe.py`](probe/probe.py), output [`probe/probe_result.json`](probe/probe_result.json):
- Video Sequencer: two generated sound tracks on two channels (the second at volume 0.5) mixed to a 16-bit WAV twice
  in one run. The SHA-256 was **the same for both** (`a9d02ed90eb13ceb…`). In 5.3 the API is `sequence_editor.strips`;
  the old name `sequences` is gone (a script-compatibility risk).
- Available in the build: Corrective Smooth, Shrinkwrap, Surface Deform, Cloth, Geometry Nodes and Mesh Cache
  modifiers; Grease Pencil v3 data; the compositor (`Scene.compositing_node_group`, which warns that it will be
  removed in 6.0); FFmpeg codecs including H.264, H.265, AV1, ProRes and FFV1.
- Not tested: render times (EEVEE vs Cycles) or the look of correctives and the compositor. Those are what Q2, Q3
  and L2 measure.

### B. Hosts (checked 2026-11-22 ~14:00 CET from this container)
| Host | Result | Use |
|---|---|---|
| `quaternius.com` | 200, reachable | CC0 low-poly kits (T-189) |
| `kenney.nl` | 403 from the **site itself** (nginx), not from our proxy | CC0 kits and CC0 audio packs. It probably blocks automated clients, so the owner may need to download them by hand |
| `docs.blender.org`, `www.blender.org`, `extensions.blender.org`, `projects.blender.org` | blocked by the proxy | Blender manual and API reference. Useful but not needed: T-193 and this review worked without them |
| `freesound.org` | blocked by the proxy | Sound effects. Licences are mixed (CC0, CC BY, and NC, which is not allowed), so not recommended without a CC0 filter |

### C. Evidence used (files on `main`)
`TECHNICAL_DECISIONS.md` TD-35, TD-42, TD-43 and **TD-44** (TD-44 removed the engine renderer on 2026-11-19 and
replaces the "renderer stays" parts of TD-43), `docs/ROADMAP.md` (V4, V8, the architecture addendum),
`docs/PRODUCTION_PIPELINE.md` (bake contract, "Not covered yet"), `docs/ANIMATION_CLIPS.md` §9,
`engine/scene/collision.h`, `engine/scene/shot_bake.h`, `pipeline/charsys/shot_render.py`, `render_engine.py`,
`render_profiles.json`, `pipeline/charsys/cloth_sim/README.md`, `pipeline/charsys/garments_v3/README.md`,
`pipeline/production/sets.py`, `docs/LIPSYNC.md`, `docs/process/TASK_LOG.md` and `OWNER_DECISIONS.md` (to
2026-11-22 04:20 CET), and the T-191 README on its branch (`docs/evaluation/interaction/T-191/README.md`, capsule
method). Task-day estimates follow the sizes recorded in T-174, T-189 and T-193 for similar steps (E). Nothing in
the engine or the pipeline was run except the probe.

### D. Questions for the owner
1. Should Q1 (contact audit) become a standard line in every shot report, with a limit agreed later?
2. Q2 (compositor look) changes the final image. Do you want a side-by-side before it is adopted?
3. L2 (joint correctives) needs new character versions. Should it come now, or after the next release?
4. Kenney packs: can you download them by hand if the site keeps refusing automated downloads?
