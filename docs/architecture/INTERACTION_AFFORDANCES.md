# Interaction affordances and the verb library (T-111, design)

Status: **design only** (T-111, 2026-11-19). Nothing here is implemented. Implementation tasks: `docs/tasks/T-112a.md`
(affordances + verb library, pick up / carry / place), `docs/tasks/T-112b.md` (pass, two-handed grasps, reactions),
`docs/tasks/T-051.md` (finger grasps on the grasp sites).

Read with: `engine/scene/interaction.{h,cpp}` (T-022 / T-047 / T-096 planner), `engine/scene/collision.h` (T-047),
`engine/scene/reaction.h` + `actions.cpp` `planReactionActions` (T-097B/D), `engine/anim/personality.h`
`TimingProfile` + `content/timing/*.json` (T-104), `engine/scene/asset_library.{h,cpp}`, `docs/ASSET_LIBRARY.md`.

## 0. Summary

Today the planner knows four primitive actions (`reach`/`grasp`, `hold`, `place`, `handover`). Each derives the
grasp from the prop's primitive or collision proxy (`graspShape`), its frames from hard-coded defaults or the
timing profile, and its gaze from a `look` flag. Objects say nothing about how they are held; verbs share no phase
structure; anticipation, settle and the observer's reaction are authored by hand in each shot script
(`episodes/e907_exchange/make_shot.py`).

The design adds two pieces of **data** and one **pure pre-pass**, and keeps the planner:

1. **Object affordances**: an optional `"affordances"` block in `plush.asset/1` (grasp sites on existing sockets,
   hand shape, one or two hands, weight / size class, pivot, push/pull axis, deform mode, carry and place rules).
2. **Verb library**: `content/verbs/<verb>.verb.json` (`plush.verb/1`): phases look / anticipate / approach /
   contact / manipulate / release / settle, each with a timing beat (from the T-104 profile), an easing curve and
   constraints.
3. **Verb expander** (`engine/scene/verbs.{h,cpp}`, new): turns a verb action (`pick_up`, `carry`, `place`, `pass`)
   into the existing primitive actions plus the generated look / anticipation / settle keys and reaction events,
   before `planReactionActions` and `compileInteraction` run. The primitives, the collision planner and the contact
   correction are reused unchanged.

**Byte-identical rule:** a scene with no verb action never enters the expander, the affordance block is read only
by the expander, and no existing default changes. Every existing bake stays byte-identical until a shot is opted in
by writing a verb action (section 6).

## 1. What exists (read from the code)

| Piece | Where | What it does today | Reused as |
| --- | --- | --- | --- |
| `reach` / `grasp` | `interaction.cpp` `reachTo` | IK wrist keys start → `pre` (approach, 5 cm back off the inward direction, 2 cm up) → `contact`; `pre = contact - min(6, 0.4·(contact-start))`; hand curl `kRelaxed` → `kOpen` at `pre`; grasp weight 0 at `contact-4` → 1 at `contact`; palm orientation from the socket frame; parent switch at `contact`; `correctKey` to 0.3 mm | approach + contact phases of every verb |
| `hold` | `interaction.cpp` | moves a held prop to `at` / `by`, world orientation kept; default end = start + max(hold, travel frames) with a profile | manipulate phase of carry |
| `place` | `interaction.cpp` | lowers the held prop so `socket` lands on `at` / `onto`; detach / re-parent at contact; hand opens, arm returns by `end` | contact + release of place |
| `handover` | `interaction.cpp` | giver holds still at `at` (or a planned meeting point clear of both bodies), receiver `reachTo`s its socket, parent switch at receiver contact, giver releases at `release`, returns by `end`; `Freeze` and `Shared` spans | the pass verb |
| `graspShape` | `interaction.cpp` | grasp centre / inward / axis / radius from the primitive (cylinder side, cap, box face, sphere) | default hand shape `wrap` |
| `visibleGrip` | scene `interaction` option | turns a round-prop grasp about its axis away from the camera (T-096) | grasp site `turnable` flag |
| Collision | `collision.h`, `armClearancePass`, `writeArmPole`, `planArmLift`, head volumes | plans elbow swing, wrist push and head tilt against each character's collision body | unchanged; a verb constraint only reads its warnings |
| Hand pose | `anim/animation.h` `HandPose`, `applyHandPose` | (curl, thumb, spread, index) plus a single sphere / cylinder contact search for all fingers | hand shapes map onto it (section 2.3); T-051 refines per finger |
| Timing | `TimingProfile::frames(beat, fallback, who)`, `travelFrames` | beat lengths with personality `tempo.beat_scale` / `hold_scale`; scale-aware travel | every phase length |
| Reactions | `reaction.h` `planReactions`, `actions.cpp` `planReactionActions` | scene `events` → look at the source, emotion, gesture per character, notice delay from `reaction_delay` | verbs emit events into the same list |

Gaps the design closes: no anticipation or settle beat in any primitive (the shot script adds holds by hand); the
look before a reach is the primitive's `gazeOn` from `start - 4` only (reference: the gaze leads the hand by 2–5 f,
`reaction_delay` 4–10 f); no notion of "this object needs two hands" or "keep it upright"; failure cases are
warnings, not a structured result.

## 2. Object affordances (asset format)

### 2.1 Placement and compatibility
An optional top-level `"affordances"` object in `plush.asset/1` (the version stays 1). `assetFromJson` today reads
only the keys it knows (`find`/`contains`) and ignores the rest, so existing loaders accept an asset with the block
and nothing that reads `PropAsset` changes. T-112a adds `PropAsset::affordances` (`std::optional`), parsed and
validated only when present; an invalid block is a load error only for the expander (a verb action on that prop),
never for a scene that does not use it. Socket names stay the anchors: a grasp site **names an existing socket**, so
the primitives keep working with the same asset.

### 2.2 Schema sketch
```jsonc
"affordances": {
  "format": "plush.affordances", "version": 1,
  "size_class": "hand" | "small" | "medium" | "large",      // largest extent vs. the actor's palm length:
                                                             // hand < 1.5, small < 3, medium < 6, large >= 6
  "weight_class": "light" | "medium" | "heavy",             // light: one hand, no body response;
                                                             // medium: lean / brace (T-045); heavy: two hands required
  "mass_kg": 0.08,                                           // optional, informative (secondary motion later)
  "hands": "one" | "two" | "either",                         // what a grasp set needs (section 2.4)
  "pivot": "place" | [x, y, z],                              // rotation origin for carry tilt and turns (socket or point)
  "upright": {"axis": [0, 1, 0], "max_tilt_deg": 15},        // optional: carry / pass keep this axis within the tilt
  "grasp_sites": [{
    "id": "rim_front",
    "socket": "grip",                                        // existing socket (palm contact point and frame)
    "hand": "L" | "R" | "any",
    "shape": "wrap" | "pinch" | "palm" | "hook" | "cradle",  // hand shape (2.3)
    "approach": [1, 0, 0],                                   // optional: prop-frame direction the palm comes from
                                                             // (default: graspShape inward reversed)
    "aperture": 0.09,                                        // optional: open hand width before contact (m)
    "turnable": true,                                        // optional: the site may turn about the grasp axis
                                                             // (T-096 visibleGrip) - same grip anywhere around it
    "fingers": {"thumb": "opposed" | "along" | "tucked",     // optional, read by T-051 only (section 5)
                "band": [0.02, 0.08]}                        // contact band along the grasp axis (m, prop frame)
  }],
  "grasp_sets": [                                            // which sites are used together
    {"id": "one_hand", "sites": ["rim_front"]},
    {"id": "both", "sites": ["side_l", "side_r"], "simultaneous_frames": 2}
  ],
  "handover": {"give": ["one_hand"], "receive": ["one_hand_b"]},  // optional: sets for the giver / the receiver
  "place": {"socket": "place", "surface_normal": [0, 1, 0], "settle": "rigid" | "soft"},
  "push_pull": {"axis": [0, 0, 1], "sites": ["front"], "friction": "slide" | "tip"},  // optional, later verbs
  "deform": {"mode": "rigid" | "squash" | "bend" | "fold",
             "squash": 0.0}                                  // rigid only in T-112; others are reserved (T-099)
}
```
Validation (T-112a): every `socket` exists; site ids unique; every set's sites exist; `hands:"two"` needs a set of
two sites; `heavy` implies `hands:"two"`; `deform` other than `rigid` loads but makes a verb fail with "deform mode
not supported yet" (no silent rigid fallback).

Size class is derived when missing (from `graspShape` / the primitive and the actor's `HandGrip::palmLength`), so
the doll-sized e907 characters and a human-sized character get the right class from the same asset (scale-aware,
like T-104 travel).

### 2.3 Hand shapes (onto today's `HandPose`)
A hand shape is a named entry of the hand-shape table (`content/hand_shapes/*.json`, `plush.hand_shape/1`, owned by
T-051; T-112a ships the five defaults below inline in the expander so it does not wait for T-051). Each sets the
approach pose (open) and the closed pose; the closing search stays `applyHandPose`.

| shape | approach (curl, thumb, spread) | closed | contact search | used for |
| --- | --- | --- | --- | --- |
| `wrap` | `kOpen` (0.03, 0.05, 0.35) | grasp search on the cylinder / sphere of `graspShape` | today's (all fingers) | cups, bottles, handles; **= current behaviour** |
| `pinch` | (0.1, 0.2, 0.1), index 0.1 | index + thumb search on a small sphere (radius from the site or 1 cm), other fingers curl 0.6 | sphere | small pieces, paper corners |
| `palm` | (0.08, 0.3, 0.0) | flat: curl 0.15, thumb 0.35, no search | none (palm on the face) | box sides, two-handed carries |
| `hook` | (0.2, 0.1, 0.0) | curl 0.7, thumb 0.1 | none | basket handles, bag straps |
| `cradle` | (0.1, 0.25, 0.2) | curl 0.3, palm up | none | holding from below (PB S2 boat in both hands) |

`wrap` with no `fingers` block produces exactly today's tracks (`hand.<s>`, `.grasp`, `.graspRadius`, `.graspAxis`,
`.grasp.weight`), so a migrated cup grasp bakes as before (section 6).

### 2.4 One or two hands
A grasp set with one site drives one `reachTo`; a set with two drives two, one per hand, with contacts at most
`simultaneous_frames` apart (the second hand leads by `reaction_delay / 3` rounded, at least 1 f, so the two hands do
not move as a mirror; reference: PB S2/S4 girl's two-handed handwork). The prop's parent becomes the **leading
hand**; the second hand is a constrained follower: its wrist target is keyed in the prop frame from the second
site (new generated keys `ik.<bone>` after contact, re-evaluated per frame like the T-096 `followSharedProp` giver),
so the prop never has two parents. Collision: both arms go through `armClearancePass` as today; the follower's
contacts are added to `InteractionContext::contacts` so the end-of-pass correction keeps them exact.

### 2.5 Worked example 1: the e907 cup (`content/assets/felt_cup.asset.json`)
Existing sockets: `grip` (+x side, 66 mm up), `grip_b` (-x side, 34 mm up), `place` (base), `contact` (rim top).
```json
"affordances": {
  "format": "plush.affordances", "version": 1,
  "size_class": "small", "weight_class": "light", "mass_kg": 0.05, "hands": "one",
  "pivot": "place",
  "upright": {"axis": [0, 1, 0], "max_tilt_deg": 20},
  "grasp_sites": [
    {"id": "side_a", "socket": "grip",   "hand": "any", "shape": "wrap", "turnable": true,
     "fingers": {"thumb": "opposed", "band": [0.045, 0.09]}},
    {"id": "side_b", "socket": "grip_b", "hand": "any", "shape": "wrap", "turnable": true,
     "fingers": {"thumb": "opposed", "band": [0.01, 0.055]}}
  ],
  "grasp_sets": [{"id": "a", "sites": ["side_a"]}, {"id": "b", "sites": ["side_b"]}],
  "handover": {"give": ["a"], "receive": ["b"]},
  "place": {"socket": "place", "surface_normal": [0, 1, 0], "settle": "soft"},
  "deform": {"mode": "rigid"}
}
```
The two bands overlap by 10 mm in height ([0.045, 0.09] and [0.01, 0.055]) but sit on opposite sides of the cup (giver
high, receiver low; T-112b correction), which is what e907 already does with `grip` at 66 mm and `grip_b` at 34 mm:
the hands never meet on the 100 mm cup (`hands_meet` fires only for overlapping bands on the same side). `max_tilt_deg: 20` is a check only for this cup (open
top, felt: nothing spills); the carry already keeps world orientation, so the constraint holds by construction and
reports if a future `hold` with rotation breaks it.

The e907 exchange as verbs (illustrative offsets; the expander fills every frame the action leaves out from the
profile, as `make_shot.py` does by hand today):
```json
{"type": "pick_up", "character": "boy", "hand": "R", "prop": "cup", "set": "a", "start": 4},
{"type": "carry",   "character": "boy", "hand": "R", "by": [0.0, 0.03, 0.05]},
{"type": "pass",    "character": "boy", "hand": "R", "to": "girl", "toHand": "L", "at": [0.02, 0.81, 0.11]}
```

### 2.6 Worked example 2: a two-handed felt tray (`content/assets/felt_tray.asset.json`, new in T-112b)
A box primitive 0.30 × 0.03 × 0.20 m (x × y × z, centred), felt. Sockets `side_l` (-x face), `side_r` (+x face),
`under` (bottom centre), `place` (bottom centre), `top` (top centre).
```json
"affordances": {
  "format": "plush.affordances", "version": 1,
  "size_class": "large", "weight_class": "medium", "hands": "two",
  "pivot": [0, 0, 0],
  "upright": {"axis": [0, 1, 0], "max_tilt_deg": 8},
  "grasp_sites": [
    {"id": "side_l", "socket": "side_l", "hand": "L", "shape": "palm", "approach": [-1, 0, 0]},
    {"id": "side_r", "socket": "side_r", "hand": "R", "shape": "palm", "approach": [1, 0, 0]},
    {"id": "under",  "socket": "under",  "hand": "any", "shape": "cradle", "approach": [0, -1, 0]}
  ],
  "grasp_sets": [{"id": "both_sides", "sites": ["side_l", "side_r"], "simultaneous_frames": 2}],
  "place": {"socket": "place", "surface_normal": [0, 1, 0], "settle": "rigid"},
  "push_pull": {"axis": [0, 0, 1], "sites": ["side_l", "side_r"], "friction": "slide"},
  "deform": {"mode": "rigid"}
}
```
`hands:"two"` makes `pick_up ... hand:"R"` an error ("prop.felt_tray needs two hands: give hands:[L,R] or a set");
`under` is not in a set, so it is not used by T-112 (it documents a later one-hand cradle under a light tray). The
8° tilt bound is checked across carry and place.

## 3. Verb library as data

### 3.1 Phases
Every verb is an ordered subset of seven phases. A phase has a length (a beat of the timing profile or a frame
count), a curve, the tracks it drives and constraints that must hold at its end.

| phase | meaning | beat (`content/timing/calibrated.timing.json`) | reference range (`reference_timing.json`) | default curve |
| --- | --- | --- | --- | --- |
| `look` | eyes (then head) find the target before the hand moves | `reaction_delay` 6 | 4–10 f (gaze leads a hand target by 2–5 f; WT eyes on the boat before the reach) | linear gaze key, `Smooth` head |
| `anticipate` | the pose held or slightly compressed before the action | `anticipation` 8 | 5–12 f (WT chin hold f000–f012) | hold (`Step` / flat `Smooth`) |
| `approach` | hand travels to the pre-contact point, hand opens | `reach` 16 minus the contact share; or `travelFrames(distance, arm)` | 10–20 f | ease in-out (`Smooth`), today's IK keys |
| `contact` | slow-in to the socket, fingers close, parent switches | the last `min(6, 0.4·reach)` of the reach (= `reachTo`'s `pre`) | 2–4 f slow-in under 0.008 H/f (VISUAL_TARGET) | slow-in |
| `manipulate` | carry / hold / lower / offer | `hold` 16 (and `travelFrames`), `place` 22, `shared_hold` 18 | 12–32 / 20–24 / 16–30 f | ease in-out |
| `release` | fingers open, hand withdraws | `release` 14 | 12–18 f (PB S4 f172–f190) | slow-out of the curl, `Smooth` IK |
| `settle` | arm returns, body settles, small hold before the next beat | `settle` 12, then `return` 20 for the arm | 8–18 / 18–53 f | slow-out (WT f023–f033, no overshoot) |

Every beat goes through `TimingProfile::frames(beat, fallback, who)`, so personality tempo (`beat_scale`,
`hold_scale`) applies exactly as in T-104. `fallback` is the **current engine default** for the same span (table
3.3), so a verb without a profile reproduces today's frames.

### 3.2 Verb file (`content/verbs/<verb>.verb.json`, `plush.verb/1`)
```jsonc
{
  "format": "plush.verb", "version": 1, "id": "pick_up",
  "requires": {"hand_state": "empty", "prop_state": "free", "affordances": "optional"},
  "phases": [
    {"name": "look",       "beat": "reaction_delay", "fallback_f": 4, "curve": "linear",
     "drives": ["gaze"], "target": "prop"},
    {"name": "anticipate", "beat": "anticipation",   "fallback_f": 0, "curve": "hold",
     "drives": ["hold_pose"], "optional": true},
    {"name": "approach",   "beat": "reach", "share": "approach", "fallback_f": 14, "curve": "ease_in_out",
     "drives": ["ik", "orient", "hand_shape:open"]},
    {"name": "contact",    "beat": "reach", "share": "contact", "curve": "slow_in",
     "drives": ["ik", "hand_shape:closed", "grasp_weight"],
     "constraints": ["palm_on_socket<=0.5mm", "outside_body"], "events": ["parent:hand"]},
    {"name": "settle",     "beat": "settle", "fallback_f": 0, "curve": "slow_out",
     "drives": ["hold_pose"], "optional": true, "events": ["reaction:success?"]}
  ],
  "lowers_to": "grasp"                         // the primitive the expander emits for approach + contact
}
```
Curves name existing `Interp` modes plus key placement: `linear` (`Interp::Linear`), `ease_in_out`
(`Interp::Smooth`), `slow_in` / `slow_out` (`Smooth` with an extra key at 70 % / 30 % of the span carrying 90 % /
10 % of the change; the same shape `reachTo` gets from its `pre` key), `hold` (`Step`). No new interpolator.

Constraints are named checks, each mapped to an existing measurement: `palm_on_socket<=X` (the `finishInteractions`
contact correction, now an error past X instead of a warning when the verb asks), `outside_body` (`armClearancePass`
residual `gap >= 0`), `upright<=deg` (prop axis vs. `affordances.upright`, sampled every frame of the phase),
`gaze_leads_hand>=2f` (the look phase ends before approach starts), `reachable` (`warnReach`'s 0.98 arm-length
test). A constraint failure is a structured verb failure (section 4), not a silent change of the motion.

`optional` phases are emitted only when the verb action asks (`"anticipate": true`) or the scene's timing profile
is set; with no profile and no flag they have length 0, which is what keeps the legacy expansion identical.

### 3.3 Fallbacks = today's defaults
| span | today (no profile) | today (profile) | verb phase |
| --- | --- | --- | --- |
| reach start → contact | 14 | `reach` | approach + contact |
| contact slow-in | `min(6, 0.4·(contact-start))` | same | contact |
| grasp weight ramp | `contact-4 → contact` | same | contact |
| gaze lead | `start - 4` | same | look (`fallback_f: 4`) |
| hold | given `end` | `max(hold, travelFrames)` | carry manipulate |
| place start → contact | 16 | `place` | place manipulate + contact |
| place contact → end | 14 | `release` | release |
| handover receiverStart | start + 4 | `reaction_delay` (receiver) | pass: receiver look |
| handover contact | start + 18 | receiverStart + `reach` | pass: receiver approach + contact |
| handover release | contact + 4 | contact + `shared_hold` | pass: shared manipulate |
| handover end | release + 12 | release + `release` | pass: giver release |

## 4. First verbs

All frames below are the calibrated profile at neutral tempo; personality scales them. `S` = action start.
Fallback = no profile.

### 4.1 `pick_up` (lowers to `grasp`)
| phase | frames | drives | constraint at end |
| --- | --- | --- | --- |
| look | S-6 → S (fallback S-4) | `lookAt` on the prop middle | gaze on prop |
| anticipate (opt.) | S → S+8 | hand and arm held still (approach starts 8 f later); T-045 body mechanics already leans into the reach, so no new body track | — |
| approach | → contact-6 | IK to the approach point (back-off along `approach`), hand shape open | reachable |
| contact | 6 f slow-in | IK onto socket, hand shape closes (grasp weight ramp last 4 f), parent → hand | palm ≤ 0.5 mm, outside body |
| settle (opt.) | 12 f | grip settles before the lift (e907 already does `anticipation // 2` by hand) | — |

Failures: hand not empty (today: error) · prop held by someone (new: error naming the holder) · site / set not
found or wrong hand (`hand:"L"` site, `R` asked) · two-hand prop with one hand · out of reach (`warnReach` > 5 mm:
becomes an error under the verb, with the shortfall) · arm cannot stay outside the body (`armClearancePass`
residual) · `deform` not rigid.

### 4.2 `carry` (lowers to `hold`)
| phase | frames | drives | constraint |
| --- | --- | --- | --- |
| manipulate | `max(hold, travelFrames(d, arm))`, ease in-out | prop origin to `at` / `by` (world orientation kept) | upright ≤ max_tilt, outside body each frame |
| settle | `settle` 12 | hold still at the end point | — |

Failures: hand empty or holds another prop (today's errors) · target out of reach · upright exceeded (only when the
asset gives `upright`) · two-handed prop whose follower hand cannot reach its site along the path.

### 4.3 `place` (lowers to `place`)
| phase | frames | drives | constraint |
| --- | --- | --- | --- |
| look | 6 f before start | gaze to the place target | — |
| manipulate (lower) | `place` 22, slow-in to contact | prop `place` socket to `at` / `onto` | surface: socket normal within 10° of `surface_normal` |
| contact | at the lower's end | detach / re-parent, `settle:"soft"` adds nothing yet (reserved for felt squash, T-099) | socket on target ≤ 0.5 mm |
| release | `release` 14 | hand shape opens (slow-out), arm returns | outside body |
| settle | `settle` 12 | arm to rest, optional `success` reaction event | — |

Failures: hand empty · target socket missing (`onto`) · target occupied (another prop parented to the same socket at
that frame: new check) · placing onto itself or a descendant · surface normal off · out of reach.

### 4.4 `pass` (lowers to `handover`; giver and receiver)
| phase | who | frames | drives |
| --- | --- | --- | --- |
| look | receiver | at S + `reaction_delay` (fallback +4) | receiver gaze on the prop (`partner_acts` reaction, below) |
| manipulate (offer) | giver | S → meet point, `hold` | prop to `at` or the planned meeting point (T-047/T-082) |
| approach + contact | receiver | `reach` | receiver `reachTo` its `receive` set |
| manipulate (shared) | both | `shared_hold` 18 | `Shared` span; `followSharedProp` as the scene option says |
| release | giver | `release` 14 | giver opens and returns |
| settle | both | `settle` 12 | giver gaze to the receiver's face; receiver may carry on |

Failures: receiver hand full · receiver is the giving hand · giver and receiver sites in the same band or the same
socket (new: error, the hands would meet) · no meeting point keeps both arms outside (today's warning, becomes an
error under the verb) · reach short for either · shared hold shorter than 6 f.

### 4.5 Reactions (T-097)
A verb phase may name a reaction event: `pass` emits `partner_acts` (source = giver, time = offer start) for the
receiver; `place` can emit `success` at settle. The expander appends these to the scene's event list **only when
the verb action sets `"react": true`** and the scene opted into events (`scene.events` present), then
`planReactionActions` plans them as today (notice delay = `reaction_delay` x tempo, emotion, gaze, gesture). The
receiver's `look` phase is then not emitted separately: the reaction's look is the look (one gaze source).

## 5. Fingers (T-051 on the grasp sites)
- A grasp site carries the contact frame (its socket), the shape and the optional `fingers` block (thumb mode,
  contact band along the grasp axis). T-051 replaces the one-sphere contact search for shapes it supports with a
  per-finger search against the prop's grasp geometry (`graspShape`: cylinder axis + radius, box face, sphere):
  each finger's root ray is clamped into the band, the curl searched until the tip is on the surface plus the felt
  thickness (fingertip radius from the skeleton), the thumb placed opposite (`opposed`) or along the axis.
- Track contract (the only coupling between T-112b and T-051, so they can run in parallel): T-112b keys, from a
  site's `fingers` block, `hand.<s>.band` = (lo, hi, thumb) with lo / hi the band's distances from the grasp centre
  along the grasp axis (metres, hand rest frame, like `.grasp` / `.graspAxis`) and thumb 0 opposed, 1 along,
  2 tucked (Step keys at the reach start). T-051 reads it in `applyHandPose`; before T-051 the track is unused.
  T-051 may also write optional per-finger overrides `hand.<s>.f<k>` (curl, spread) and `hand.<s>.thumb`
  (opposition, curl) from the hand-shape table. Absent tracks = today's pose, byte-identical.
- Hand-shape table `content/hand_shapes/*.json` (`plush.hand_shape/1`): the five shapes of 2.3 plus gesture shapes
  (point, count, chin-touch from the girl's references) and the relaxed idle hand; personality may bias rest curl.
- Timing on the grasp sites: fingers close in the last 4 f of `contact` as today, staggered index → little by 1 f
  (follow-through), and open on `release` in reverse order. Nothing changes the wrist or the palm contact point, so
  the T-047 collision plan and the 0.3 mm contact correction stay valid.

## 6. Mapping onto the planner and migration

### 6.1 Pipeline position
```
scene.actions  ──► [verb expander: verb actions → primitive actions + looks + events]  (new, pure Json → Json)
               ──► planReactionActions (T-097D, unchanged) ──► compileActions → compileInteraction (unchanged)
               ──► armClearancePass / finishInteractions (unchanged) ──► verb constraint check (new, read only)
```
The expander runs before `planReactionActions` because it adds events. It needs geometry only for travel and reach
checks; it gets it through a read-only callback into `SceneEvaluator` (prop world, hand grip, arm length), and it
emits frames, not positions, wherever a primitive already computes the position (meeting point, wrist target).

### 6.2 What is reused, what changes
| Item | Reused | Changes |
| --- | --- | --- |
| `reachTo`, `plan`, `graspShape`, `visibleSocket` | as is | `reachTo` gains optional hand-shape keys (open / closed `HandPose` values instead of `kOpen` / grasp search) used only when an action carries `"shape"` other than `wrap` |
| `hold`, `place`, `handover` | as is | none; the verb gives them explicit frames |
| `InteractionContext` | as is | `Contact` entries for the two-hand follower (T-112b) |
| collision planner | as is | none; verb constraints read its residuals |
| `TimingProfile` | as is | none (beats exist); verbs name them |
| reactions | as is | the expander appends events |
| `look` action | as is | new optional key `atProp` (prop middle; today only `target` / `atCharacter`) |
| assets | sockets, collision proxy | optional `affordances` block (ignored by the primitives) |

### 6.3 Byte-identical guarantee and test
1. No new default: the primitives' code paths are unchanged when no `shape`/verb key is present.
2. The expander is skipped when no action has a verb type; its output for a verb is ordinary primitive Json.
3. T-112a commits, **first**, a golden test: for every content scene with interaction actions (at the input SHA:
   `episodes/e907_exchange/shots/s010*`, plus any other scene a `grep` for `"grasp"|"reach"|"place"|"handover"`
   finds) and the `test_interaction.cpp` scenes, compile at the input SHA and store the SHA-256 of the generated clip
   (tracks sorted, keys at full precision) and of the engine's `plush.shot_bake/1` output (`shot_bake.cpp`, no
   Blender). Every later commit must reproduce them.
4. Adding an `affordances` block to `felt_cup.asset.json` is in the same golden run (the e907 bake must not change).
5. Opt-in is per shot: a verb action. A migrated e907 variant (`s010_verbs`) is a new shot directory; the existing
   `s010` / `s010_calibrated` stay as they are.

### 6.4 Migration path
1. **T-112a**: affordance block + validation, verb files for `pick_up`, `carry`, `place`, the expander and the
   constraint check; `felt_cup` gets its block; golden hashes; `s010_verbs` pick up + carry + place equivalent
   proving the legacy expansion (no profile, no optional phases) equals hand-written primitives key for key.
2. **T-112b**: `pass` (with reactions), two-hand grasp sets and the follower hand, `felt_tray` asset, the
   `hand_shape` keys for `palm` / `cradle` / `pinch` / `hook` in `reachTo`, `s010_verbs` as the full exchange.
3. **T-051** (parallel with T-112b once T-112a is merged): per-finger grasps on the sites and the hand-shape table.
4. Later (not planned): `push` / `pull` (`push_pull`), `deform` modes with T-099, migrating `make_shot.py` beats
   to verbs, making verbs the authoring default (owner decision).

## 7. Open questions for the Supervisor
- Two-hand follower: wrist keyed in the prop frame per frame (proposed) or a second parent with blending. The
  proposal keeps one parent per prop and reuses the `followSharedProp` machinery; it adds per-frame IK keys.
- Under a verb, reach and collision warnings become errors (proposed). Shots written as primitives keep warnings.
- Whether the boy's "reluctant" tempo also delays the look phase (personality `reaction.delay_frames`) or only
  stretches beats (`beat_scale`); proposed: both, as `planReactionActions` already does for reactions (T-112b).
