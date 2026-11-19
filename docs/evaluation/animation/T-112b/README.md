# T-112b evidence: pass, reactions, hand shapes, two-handed grasp sets

Input d2567cb (integration/t-094c), branch `t-112b-claude-verbs-pass`. Design: `docs/architecture/INTERACTION_AFFORDANCES.md`
2.3, 2.4, 2.6, 4.4, 4.5 and 5. Verbs reference: `docs/ACTIONS_AND_DIRECTOR.md` "Verbs".

## 1. What was built
| Criterion | Implementation | Test (`tests/test_verbs.cpp`) |
| --- | --- | --- |
| 1 pass | `content/verbs/pass.verb.json` (lowers to `handover`). It has two manipulate phases, told apart by `part` (offer / shared), and a `who` per phase. With no profile the frames are the handover defaults; with a profile the receiver's beats are `reaction_delay` and `reach` and the giver's are `shared_hold` and `release`. | "pass without a profile expands to the hand-written handover, key for key": boy→girl and girl→boy, defaults and authored frames, 755 keys and 0 differences per case; "pass phases follow the handover frames" |
| 2 reactions | `"react": true` puts `partner_acts` (pass) or `success` (place) in `VerbExpansion::events`. `actions.cpp` plans them with the scene's own events (Supervisor-approved hook, 12 lines). | "react appends partner_acts / success events" (pure); "a reacting pass compiles through the reaction system" (compiled, boy and girl as receiver) |
| 3 hand shapes | `reachTo` / `release` key the open and closed poses of `palm`, `cradle`, `pinch` and `hook`, with no contact search. `wrap` keeps today's code path. | "non-wrap hand shapes key their open / closed poses" |
| 4 two hands | `hands: ["L","R"]`. The leader's grasp is the parent. The follower is a grasp with `"follower": true` (`InteractionContext::followers`): wrist keyed in the prop frame every frame, held by the clearance pass, palm corrected every frame in `finishInteractions`. New asset `content/assets/felt_tray.asset.json` (design 2.6). | "two-handed tray - pick up, carry, place on boy and girl skeletons" |
| 5 band | `hand.<s>.band` = (lo, hi, thumb), Step key at the reach start (track contract of design 5). `engine/anim` is untouched. | "hand.<s>.band keys from a site's fingers block" |
| 6 failures | `same_hand`, `hand_full` (receiver), `hands_meet` (socket / band), `shared_too_short`, `two_hands`, `out_of_reach` (receiver, second hand along the carry), `wrong_hand` / `unknown_set` / `bad_hand` for two-hand sets, `arm_in_body` (bound through the hook) | the "verb failures T-112b" cases |
| 7 s010_verbs | the full exchange as verbs (section 3) | bake, animcheck, preview, strict sheet |
| 8 baselines | golden hashes unchanged, no test loosened | section 4 |

Measured (two-handed tray, scale 0.6, calibrated profile; boy / girl test skeletons):
| | boy | girl |
| --- | --- | --- |
| leader / follower contact | f32 / f34 (2 f apart; simultaneous_frames 2) | f32 / f34 |
| max palm-to-socket error, follower contact → place contact | 0.0007 mm | 0.07 mm |
| min arm gap (both arms, same span) | 15.0 mm | 15.2 mm |
| max tilt of the tray's up axis | 0.0° (limit 8°) | 0.0° |

Reaction notice delay (frames after the pass start; the reach starts at the next whole frame ≥ notice + 4):
| receiver profile | delay | rule |
| --- | --- | --- |
| girl | 4.5 | delay_frames mid 5 x reaction tempo_scale 0.9, never under delay_frames lo 4 |
| boy | 21 | delay_frames mid 21 x 1.0 (reluctant: his look phase is delayed too, T-111 decision) |
| none | 6 | the profile's reaction_delay |

## 2. Decisions (accepted by the Supervisor) and corrections
- **Finger band gating.** The band is written when the scene has a timing profile or the action sets `"fingers": true`.
  It is never written with `"fingers": false`. felt_cup's sites already carry a `fingers` block, so writing it on
  every verb grasp would add a track and break T-112a's legacy key-for-key test. Without a profile the expansion is
  exactly the T-112a legacy one.
- **Shared hold.** With no profile, a pass keeps today's handover shared hold of 4 f. The `shared_too_short` error
  (under 6 f) applies to authored or profile frames only.
- **Cup bands (design correction).** The design says the cup's two bands do not overlap. They do: [0.045, 0.09] and
  [0.01, 0.055] share 10 mm. The sockets sit on opposite sides (grip +x, grip_b -x), so the hands never meet.
  `hands_meet` therefore fires for overlapping bands only when the sockets are on the same side of the up axis
  (radial directions under 90° apart), or when both use the same socket.
- **One gaze source under react.** The `partner_acts` reaction's look is aimed at its source, the giver's face: that
  is the receiver's notice. The handover itself plays no gaze. From her reach start, a generated `look` keeps her eyes
  on the prop until contact + 8. The giver's gaze is generated too: at the prop until the release, then at her.
- **Two-hand leader.** The first of `hands` leads. The second hand contacts
  clamp(round(reaction_delay / 3), 1, simultaneous_frames) frames later.
- **Pinch** is a fixed pose (curl 0.6, thumb 0.5, index 0.35). The per-finger index-and-thumb search the design
  describes belongs to T-051's `applyHandPose`.
- **Tray scale.** At full size (0.30 x 0.20 m, design 2.6) the tray is too deep for the doll-sized test girl to hold
  in front of her, so the tests scale the instance to 0.6 (`transform.scale`). The asset keeps the design's size.
- **T-104d coupling.** Every "profile" gate (optional phases, band, shared-hold check) reads the profile the compile
  resolved (`VerbContext::timing`). Once T-104d makes calibrated the default, a scene without a `timing` key gets the
  profile. The legacy-equivalence tests then need `"timing": "none"`; their scenes have no timing key today. Checked
  here: absent key = legacy (T-112a and T-112b equivalence tests). `"timing": "none"` cannot be checked before T-104d
  merges, because today it is looked up as a profile file named "none".

## 3. s010_verbs: the full exchange
`episodes/e907_exchange/shots/s010_verbs/shot.scene.json`. Current approved versions (boy 2.0.0, girl 0.11.0, cast
`current`), the calibrated profile, both personality profiles, and `"events": []`:
```json
{"type": "pick_up", "character": "boy", "hand": "R", "prop": "cup", "set": "a", "start": 1, "settle": 5},
{"type": "pass", "character": "boy", "hand": "R", "to": "girl", "toHand": "L", "at": [-0.0423, 0.5327, 0.0065], "react": true},
{"type": "carry", "character": "girl", "hand": "L", "by": [-0.03, 0.03, -0.02]}
```
These stay authored, as in s010_calibrated: her look at the table (f1-34), her happy emotion at her contact - 2
(f56), her look up at him at accept + 2 (f66), and his look off at the end (his end + anticipation, f103).
`settle: 5` is make_shot.py's grip settle (anticipation // 2). `s010_verbs.expanded.scene.json` holds the expansion
(primitives, events and phase spans); it was dumped with `dump_expansion.cpp`, a scratch program outside the build.

| beat | s010_calibrated | s010_verbs | why |
| --- | --- | --- | --- |
| his grasp → contact | 11 → 30 | 11 → 30 | same (anticipation 10, reach 19) |
| offer (cup to the meeting point) | 35 → 45 | 35 → 54 | the pass's offer runs to the giver's still frame (contact - min(4, 0.3 x span)); make_shot used the travel time 10 f, then a separate hold |
| her notice | 35 (glance) | 39.5 (reaction look at him) | partner_acts notice delay 4.5 f (expected change; Supervisor) |
| her reach → contact | 42 → 64 (22) | 44 → 58 (14) | the verb uses the reach beat (16 x 0.85); make_shot used max(reach, travel) = 22 |
| shared hold | 64 → 82 (18) | 58 → 76 (18) | same beat |
| his release → end | 82 → 99 (17) | 76 → 93 (17) | same beat |
| her draw | 84 → 94 (10) | 76 → 96 (20) | chained on his release; carry = max(hold 16 x 1.25, travel) |
| end | 129 | 129 | same length |

Visible differences on the strict sheet: every verbs frame after his contact is the same beat about 6 f earlier.
At "offer held" (f54) her hand is already on its way, while in calibrated (f45) she has only just started. At the
end the cup sits a little higher in her hand: the draw-in runs 20 f instead of 10, but by the same offset. Her
blink interval comes from her personality (the authored 2.6 s was outside its limits, so the key was removed). She
also plays the partner_acts reaction emotion before the authored happy. Staging, camera, set and character looks are
unchanged.

Engine: the bake (`run_shot --stages prepare,bake`, bpy 5.3.0 module through `tools/bpy_blender.py`) passes every verb
constraint (reach, palm on socket, arm_in_body) with no warnings. animcheck: `timing_s010_verbs.json` (authored, 0
beats, 0 warnings), `timing_s010_verbs_expanded.json` (5 beats, 0 warnings), `timing_s010_calibrated.json` (6 beats,
0 warnings), `acting_s010_verbs.json` (2 characters, 0 warnings). `tools/animcheck/run_gate.py`: all regression
shots PASS.

## 4. Baselines
- `tests/golden/interaction_hashes.json` is unchanged and the golden test passes. Non-verb scenes never enter the
  expander, the hook appends nothing without verb events, and the new grasp keys are absent from every authored scene.
- e907 s010_calibrated bake (run_shot, sha256): `0807ad2c`, as recorded in T-104.
- ctest (build/, renderer off): 2/2; plush_tests: all cases pass (171 earlier + 27 verb cases).
- Image regressions (build-r/, renderer on): `regression_milestone01` (rmse 0.0464) and `regression_face_neutral`
  (0.0406) fail here, with identical values from the input SHA's renderer built in a clean worktree. The cause is
  this environment, which has no Open Image Denoise ("denoiser unavailable"); the scenes contain no interaction
  actions. All other renderer tests pass.
- Unchanged: `engine/anim/**` (T-051), `engine/render/**`, the T-112a verb files, `felt_cup.asset.json`, published
  versions and frozen files.

## 5. Visual results
| File | Content |
| --- | --- |
| `t112b_s010_verbs_preview_cycles4spp.jpg` | cheap preview, Cycles 4 spp, 240x135, the six sheet frames of s010_verbs |
| `t112b_calibrated_vs_verbs_strict_sheet.jpg` | strict sheet, Cycles 32 spp, 640x360, shot camera (`make_sheet_t112b.py`, T-104 layout): dope sheet; rows calibrated / verbs at his contact, offer held, her contact, shared hold, his release, end hold; reference row |

Workbench needs a GPU here, so the cheap preview used Cycles at 4 spp (as in T-104).

## 6. Not verified
- No full-length movie.
- Per-finger contact on the band (T-051 reads the track).
- MSVC: the golden hashes are a linux gcc-13 set (T-112a).
