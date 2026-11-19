# T-107 · Independent review of round 2, Phases B and C

**The boy’s eyes are closer in width, the fabrics separate, and the cup changes hands. The largest remaining gap is seeing the thought behind the action.** At the shared hold in e907 f48, both glasses lenses fit in the frame, yet the girl’s dark irises are pushed to their edges. The largest light shape on the cup is the boy’s fist. In the owner’s Paperboat f272, the direction of the pupils tells us what matters even before we follow the hands. The strongest evidence for the next round would be that same readable relationship in a moving two-shot with the combined characters. [Exchange sheet][exchange] · [Shared-hold crops](shared_hold.jpg)

Reviewed at `45679f3` against the original boy portrait, val27 and hero24, the girl portrait, ref_30 and sheet30, and the owner-accepted Higgsfield details. I decoded the complete e907, Paperboat (PB) and Watertable (WT) clips and compared selected frames. e907 frame numbers start at 1, PB and WT at 0. Numerical results below come from the saved evidence unless identified as a calculation. The owner approved T-089, T-092 and round-two T-093 as systems. The exchange and lighting frames use the published boy 2.0.0 and girl 0.11.0. Only the T-093 + T-092 sheets show clothing and materials together. [Boy portrait][boy-ref] · [Girl portrait][girl-ref] · [Design decisions][decisions] · [PB][pb] · [WT][wt]

## Phase B

### T-089 · Faces and eyes

The boy gains a wider, continuous dark upper lid and a readable far eye at three-quarter. Front opening width / eye-centre spacing moves from 0.36 to 0.47 against val27’s 0.48. The girl gains a single iris highlight and less exposed shell at the outer corner. These changes make the pupil easier to locate behind her glasses in neutral. Both blink strips show front closure and a change of gaze. [Boy strict sheet][boy89] · [Girl strict sheet][girl89] · [Opening measurements][eyes]

1. **Girl, face front and three-quarter, inside the lenses and below the cheekbones.** G01/G02 have a rounded cheek carrying a broad eye. The candidate tapers sharply to the chin. The lid opening has a sloping inner edge and a pale horizontal shelf below the iris. Width / spacing reaches only 0.53 from 0.51 against sheet30’s 0.66. Start with the lateral socket opening and cheek cross-section, hold the glasses and eye centres fixed, and vary the inner and outer lid corners independently. Compare the outline under the near lens at three-quarter before increasing eye radius again. [Girl strict sheet][girl89]
2. **Boy, face front and three-quarter, upper lid across the iris.** The brows sit well above the lids and the deeper opening makes his rest face look watchful. A check on the saved geometry explains the impression. Front opening height / width is about 0.61 (39.25 / 63.75 mm). The bounding boxes of the two annotated val27 front eye polygons give roughly 0.40 and 0.52. Treat those hand-marked bounds as a range. Retain the new width, lower the neutral upper arc across the pupil, and judge the result with the fringe on against hero24 and B01/B02. [Boy strict sheet][boy89] · [Reference eye polygons][val27] · [Opening measurements][eyes]
3. **Both blink strips, candidate three-quarter column, outer-lower corners.** His rim is cleaner, though the recorded outer-corner fold is still 59.5°. Her full blink leaves 27.2 mm² of visible near eye against 23.3 previously. At full closure the lit, domed lid still draws attention to the eye assembly. Smooth the local socket-to-cheek transition and adjust the lateral closure path. Check neutral, half blink, full blink and glance with the same camera, then restore the glasses and hair for a shot-size check. [Boy strip][boy-blink] · [Girl strip][girl-blink] · [Fold and exposure diagnostics][face-data]

### T-092 · Materials and skin

In the front and back rows, the boy’s mustard hoodie loses the bright, irregular flecks that previously broke up its outline. On the girl, the dusty-rose vest separates from the quieter cream blouse, and the boot cuff reads as a separate fleece roll in the combined sheet. Neutral shot-size colour error (ΔE00, lower is closer) falls from 6.50 to 3.07 for the vest and 34.9 to 4.22 for the cuff. The cream cuff follows G08, while sheet30 remains the guide to boot shape. [Boy material sheet][boy92] · [Girl material sheet][girl92] · [Patch comparison][patches]

1. **Character sheets, exposed hands and cheeks under the fringe or lenses.** The cheek carries a localized pink patch while the hand below the cuff looks pale and smooth. The effect is especially clear beside the boy’s mustard sleeve. The skin sphere barely changes under either rig and cannot settle a judgement about creases. Under the neutral rig, sample lit cheek, shadow cheek, neck and back of hand on the same character. Tune the relative limb value and occlusion warmth separately, then compare the same surfaces in a grasp under warm light. This protects the face from a global skin adjustment. [Boy material sheet][boy92] · [Girl material sheet][girl92] · [Patch measurements][patch-data]
2. **Boy front and side, hoodie pocket and dark trouser legs.** The pocket is easier to see, but the candidate legs become nearly uniform from thigh to ankle. B08’s hoodie edge and B09’s trousers still carry a short, soft pile after the large flecks disappear. Neutral shot-size high-frequency RMS falls from 10.9 to 4.4 on the hoodie and 4.0 to 1.4 on the trousers. Those decreases quantify smoothing, while hoodie colour error actually rises from 2.82 to 3.55. Hold the dye constant and sweep fibre length and coverage on the trouser edge first. Select at figure scale, then inspect the macro for stray fibres. [Boy material sheet][boy92] · [Patch comparison][patches] · [Boy detail references][boy-uploads]

### T-093 · Round-two garments, including T-092 materials

The boy’s back row now shows B06’s navy pack, rounded flap, centre tab and separate front pocket. His side view shows the white stripes and cream sole. The front cords have dark tips. B07 supplies pack depth and strap path, B09 the toe and lace construction. The girl has covered shoulders, a longer cuffed sleeve and one pink flower. The combined sheets make the pocket edge and the vest front easier to read. At reach, the large shoulder opening in 0.11.0 gives way to a continuous blouse sleeve. [Boy garment sheet][boy93] · [Boy combined][boy-combined] · [Girl garment sheet][girl93] · [Girl combined][girl-combined] · [Reach sheet][reach]

1. **Girl combined, face-front row at the neck, and reach sheet, right column at the raised shoulder.** The white collar turns up into two wings. Dark triangular breaks interrupt its front edge even with the cleaner cloth. In the side reach there is daylight beneath the collar. Compare the rounded collar lying flat in ref_30. Follow the neckline with a rounded two-layer collar, limit lift locally to where the vest actually intersects, and distribute bending from the neck to the tips. Check both arms through rest, partial reach and full reach in the shot pipeline. The Blender diagnostic lowers 95th-percentile penetration from 2.35 cm to 0.40 cm, but 495 vertices remain inside the blouse and the worst depth is 1.9 cm. Weight changes account for most of the flare reduction even with the corrective keys muted. Engine playback of those keys is unproven here. [Girl combined][girl-combined] · [Reach sheet][reach] · [Reach data][reach-data]
2. **Girl combined, front and back from vest hem to knees.** G08 and sheet30 show two puffed thighs narrowing independently above gathered bands. The candidate’s pleats are visible, but the long lower edge still reads as one garment spanning both legs. A modeled 13 mm hem gap gets lost at this distance. Increase the inner-leg separation and shape each cuff around its own thigh. Compare front, back and profile at equal figure height before adding finer pleats. [Girl garment sheet][girl93] · [Girl combined][girl-combined] · [G08 and original ref_30][girl-uploads]
3. **Boy combined, side ankle and back panel.** The shoe is slimmer, but a skin-coloured notch interrupts the dark hem over the near shoe. The pack has the right components, yet the flap, tab and grab loop merge in value under the hood more than in B06. Shape the trouser break over the shoe collar across ankle flexion. Preserve the accepted pack pattern and increase flap-edge relief and loop clearance just enough to read in the back row. [Boy garment sheet][boy93] · [Boy combined][boy-combined]

### T-090 · First reference fits

The boy’s three-quarter visible-eye intersection-over-union (IoU) rises from 0.286 to 0.430. Opening the eye is a productive search direction on the approved baseline. The girl gains only 0.25 points overall, with front eye IoU moving from 0.391 to 0.396. These were three-build searches on the published characters, independent of T-089. [Boy overlay][boy-fit] · [Girl overlay][girl-fit] · [Fit results][fit-results]

1. **Boy strict, face three-quarter, near lid and brow.** More gold eye pixels land in the target outline, but more iris shows below the lid, and the visible pale corner persists. Both inner-brow errors worsen in front. Run a bounded lid-height and brow-position sweep on the v3 face, constrain width to the T-089 result, and compare neutral expression with B02 before accepting a higher aggregate score. [Boy fit sheet][boy90] · [Boy scores][boy90-scores]
2. **Girl strict, face front, eye relative to the wire ring.** The candidate is hard to distinguish from 0.11.0 at figure size and still lacks the breadth of the original eye. Front left inner-brow error increases from about 0.047 to 0.056 head heights. Use the lens-free overlay to locate corners and the Cycles row with lenses to judge the expression. Compare face crops at matched eye spacing, since the strict reference and candidate head crops differ in scale. [Girl fit sheet][girl90] · [Girl scores][girl90-scores]

### T-090b · Regional fit proposals

The boy’s higher inseam and smaller shoe are the most useful directions. Trouser and shoe overlap improves in all three views, with mean garment score 61.10 to 63.90. The girl’s blouse improves in profile and her front eye gains a little width. All three fits start from the published specs. T-093 already changes the gusset, sleeves and shoe shape, so measure the approved round-two composite before transferring individual parameters. [Proposal results and inputs][fitb]

1. **Girl face, front and side at the lower lid and cheek.** Front widths reach 25/24 px against 32/30 px, while heights are already 24/23 against 23/23 px. Side eye IoU falls from 0.297 to 0.282 and the fit reduces cheek fullness. The mean gain is 0.02 points. Keep the width measurements as targets for the T-089 socket work. Omit this proposal’s cheek reduction and extra protrusion from the composite. [Girl face sheet][face90b] · [Eye dimensions][face90b-data]
2. **Girl garments, front between the thighs and side at the shorts hem.** Front shorts IoU improves, but the side hem ends 14 px low and side IoU falls from 0.674 to 0.633. The left sleeve target reaches 117% of the shoulder-to-palm distance, past the palm itself. Check the wrist landmark and sleeve mask visually, fit each cuff separately, and evaluate the trouser-leg split on garment/2 before adopting a length change. [Girl garment fit][girl90b] · [Regional measurements][girl90b-data]
3. **Boy garments, front crotch and shoe, side near ankle.** Crotch-to-sole gap moves from 111 to 126 px toward 143. Front shoe area falls from 10,506 to 9,439 px², still about 54% above 6,120 px² in val27, and the side ankle shows through. Refit gusset and shoe upper independently on garment/2, keeping the cream sole and stripes. Rank trials on the leg gap, shoe area and coverage of the ankle in all three views. [Boy garment fit][boy90b] · [Regional measurements][boy90b-data]

## Phase C

### T-095 · Two-person exchange, e907

The shot has a readable beginning and end. In f1 the cup stands alone on the table. The boy reaches first, the girl notices at f20 and starts her reach at f27. At f58 his retreating hand reveals the red cup on her side. The top row of the blocking sheet and the overhead view establish the direction of transfer. Measured shared-hold drift is at most 0.0003 mm for his hand. PB f157–175 supplies a visual reference for hands approaching and leaving an object. [Movie][movie] · [Blocking sheet][blocking] · [Strict sheet][exchange] · [Measurements][e907-data]

1. **Shot camera, f36 / f48 / f53, where both sleeves meet.** These three pictures look remarkably similar at playback size despite representing approach, shared hold and release. At f48 the fist covers the middle of the cup, leaving a red rim and narrow side. In PB f157 the paper hull remains legible between the two hands. Rotate the grip around the cup, stagger the two wrists in depth, and choose a camera offset at which the near hand leaves a continuous patch of cup wall visible. Compare all three beats at 640 × 360. [Shared-hold crops](shared_hold.jpg) · [Strict sheet][exchange]
2. **Shot camera, f18 under his fringe and f48 behind her lenses.** His downward pitch hides the pickup glance. At f48 both eyes are in frame on both faces, but most of what shows through her glasses is pale sclera. PB f12 and f272 retain dark pupils that point to the work. Open the faces slightly to camera, share the turn between head and eyes, and test the downward pitch against the groom. Check each character looking at the object and then at the partner. [Blocking sheet][blocking] · [Full-resolution studio f48][studio48]
3. **Movie, f43–59, smile, shared hold and release.** Pleasure at f43, her look up at f49, his release at f51 and his next look at f53 compete for attention. At 24 fps the seven displayed shared-hold frames last 0.29 s. Try a quiet anticipation, a held receiving pose, then her delighted mouth as a separate beat. Let his response arrive later. Compare the same-camera versions at normal speed with PB f157–175 and the sustained WT f22–60 gesture. T-104 already owns timing calibration. [Movie][movie] · [Timing task][timing]

### T-096 · Clearance and grip, e905 diagnostic

At f46 the after-shot exposes a broad red cup wall beside the yellow cuff. The top view also opens a gap between the heads. The visibility probe samples the cup surface against the posed character meshes from the shot camera. Its estimate rises from 23% to 74% at contact and from 31% to 74% at f50. Giver drift falls from 4.51 mm to 0.10 mm across the hold. Those are e905 measurements. e907 uses a different camera, arrangement and receiving hand. [Before/after sheet][grip] · [Before data][e905-before] · [After data][e905-after]

1. **After, shot camera f46 and f50, cup ends and palms.** The exposed red wall is an improvement, yet the wrists and sleeves still conceal how the receiver supports it. Her shoulder sway asks for 185.5 mm of reach from a 180 mm arm at f52. Following the prop repairs the giver's drift while the receiver remains extended. Move the handover point slightly into her reach through the entire idle cycle, then choose the grip azimuth with both sleeve contours in view. Check half-frame drift through release and the rim in the actual e907 camera. [Grip sheet][grip] · [Reach and drift diagnosis][grip-data]
2. **After, f46/f50 shot versus overhead, near fringe against her bun.** The mesh minimum rises from 0.07 to 36.6 mm on e905, yet the projected hair edges run close together and his fringe still masks his gaze. The 10 mm cheap trial also reads as touching through the fibres. Stage the heads with a visible gap first, using a small depth or yaw offset, and retain the capped tilt for the remaining close frames. Verify with groom and glasses visible. At 95% spacing the lean-in already reaches its tilt limit. [Grip sheet][grip] · [Cheap f46][cheap-grip] · [Lean-in limits][grip-data]

### T-098L · Set and lighting experiment, findings only

At fixed e907 f48 the warmer right-hand image gives the boy’s crown and the girl’s bun a light edge. Window divisions and a softer rear wall suggest a place. The side-by-side studio frame shows how much of the hand and eye problem is already present under neutral light. [Studio/set sheet][set-sheet] · [Studio detail][studio48] · [Set detail][set48]

1. **Final row, faces and hand above the table.** The added bounce lifts skin and cuffs together. Her near iris and the cup behind his palm are still difficult to pick out. PB f12 separates faces with local shadows, and PB f231 puts its brightest edge on the story object. For Phase D character comparisons, use the existing studio f48 as the control and the existing warm frame as a secondary check on pupil, cheek and cuff contrast. [Studio/set sheet][set-sheet]
2. **Final set frame, rear window, shelf and table, versus WT f24.** Large matte rectangles establish the room, but the tabletop lacks WT’s reflected window and the shelf lacks the depth cues of PB f12. The recorded box-only geometry, fixed roughness and uniform sky explain the limits of this experiment. On its four-core CPU, review costs 67.7 to 80.8 s/frame and final f48 costs 965.2 to 1,180.7 s, about 22% more. The final sample is one frame. Use those costs only as context for interpreting the existing images. Environment development remains deferred. [Experiment findings][set-findings] · [Recorded costs][costs]

[boy-ref]: ../../references/char_C_boy.jpg
[girl-ref]: ../../references/char_B_brown_hair.webp
[boy-uploads]: ../../../assets/characters/boy_yellow_hoodie/references/uploads/
[girl-uploads]: ../../../assets/characters/girl_auburn_bun_glasses/references/uploads/
[val27]: ../../../assets/characters/boy_yellow_hoodie/references/annotations/val27_front.json
[decisions]: ../../process/OWNER_DECISIONS.md
[pb]: ../../references/video_paperboat.mp4
[wt]: ../../references/video_watertable.mp4
[boy89]: ../../evaluation/characters/T-089/boy_sheet/boy_2.0.0_vs_face3_strict.jpg
[girl89]: ../../evaluation/characters/T-089/girl_sheet/girl_0.11.0_vs_face3_strict.jpg
[boy-blink]: ../../evaluation/characters/T-089/boy_sheet/boy_blink_glance_strip.jpg
[girl-blink]: ../../evaluation/characters/T-089/girl_sheet/girl_blink_glance_strip.jpg
[eyes]: ../../evaluation/characters/T-089/measurements.json
[face-data]: ../../evaluation/characters/T-089/README.md
[boy92]: ../../evaluation/materials/T-092/boy_yellow_hoodie_strict.jpg
[girl92]: ../../evaluation/materials/T-092/girl_auburn_bun_glasses_strict.jpg
[patches]: ../../evaluation/materials/T-092/patch_sheet.jpg
[patch-data]: ../../evaluation/materials/T-092/patch_metrics.json
[boy93]: ../../evaluation/characters/T-093/boy_2.0.0_vs_T-093/boy_2.0.0_vs_T-093_strict.jpg
[girl93]: ../../evaluation/characters/T-093/girl_0.11.0_vs_T-093/girl_0.11.0_vs_T-093_strict.jpg
[boy-combined]: ../../evaluation/characters/T-093/boy_2.0.0_vs_T-093_T-092/boy_2.0.0_vs_T-093_T-092_strict.jpg
[girl-combined]: ../../evaluation/characters/T-093/girl_0.11.0_vs_T-093_T-092/girl_0.11.0_vs_T-093_T-092_strict.jpg
[reach]: ../../evaluation/characters/T-093/reach/reach_before_after.jpg
[reach-data]: ../../evaluation/characters/T-093/reach/reach.json
[boy-fit]: ../../evaluation/characters/T-090/boy/overlay.jpg
[girl-fit]: ../../evaluation/characters/T-090/girl/overlay.jpg
[boy90]: ../../evaluation/characters/T-090/boy/strict-sheet.jpg
[girl90]: ../../evaluation/characters/T-090/girl/strict-sheet.jpg
[boy90-scores]: ../../evaluation/characters/T-090/boy/scores.csv
[girl90-scores]: ../../evaluation/characters/T-090/girl/scores.csv
[fit-results]: ../../evaluation/characters/T-090/README.md
[fitb]: ../../evaluation/characters/T-090b/README.md
[face90b]: ../../evaluation/characters/T-090b/girl-face/sheet.jpg
[face90b-data]: ../../evaluation/characters/T-090b/girl-face/measurements.csv
[girl90b]: ../../evaluation/characters/T-090b/girl-garments/sheet.jpg
[girl90b-data]: ../../evaluation/characters/T-090b/girl-garments/measurements.csv
[boy90b]: ../../evaluation/characters/T-090b/boy-garments/sheet.jpg
[boy90b-data]: ../../evaluation/characters/T-090b/boy-garments/measurements.csv
[movie]: ../../evaluation/animation/T-095/t095_exchange_shot_camera.mp4
[blocking]: ../../evaluation/animation/T-095/t095_blocking_cycles6spp.jpg
[exchange]: ../../evaluation/animation/T-095/t095_exchange_strict_sheet.jpg
[e907-data]: ../../evaluation/animation/T-095/measure_exchange.json
[timing]: ../../tasks/T-104.md
[grip]: ../../evaluation/animation/T-096/t096_e905_before_after_sheet.jpg
[cheap-grip]: ../../evaluation/animation/T-096/t096_cheap_first_frame_f46.jpg
[grip-data]: ../../evaluation/animation/T-096/README.md
[e905-after]: ../../evaluation/animation/T-096/data/e905_after.json
[e905-before]: ../../evaluation/animation/T-096/data/e905_before.json
[studio48]: ../../evaluation/rendering/T-098L/t098l_f48_studio_final_1920.jpg
[set48]: ../../evaluation/rendering/T-098L/t098l_f48_set_final_1920.jpg
[set-sheet]: ../../evaluation/rendering/T-098L/t098l_f48_studio_vs_set_sheet.jpg
[set-findings]: ../../evaluation/rendering/T-098L/README.md
[costs]: ../../evaluation/rendering/T-098L/costs.json

**Review time.** About eight minutes of active inspection, frame extraction, writing and verification across the two sessions. The usage-limit interruption accounts for approximately 588 minutes, from 23:00 UTC on 18 November to 08:48 UTC on 19 November. The ledger records project build, render, test and CI time separately from active review. All visual comparisons used existing media.

## Five most important gaps for Phase D

1. **Resting faces and directed gaze.** Give the girl fuller cheeks and broader eye openings behind the lenses. Preserve the boy’s new eye width and restore the heavy upper lid. Judge each in neutral, blink and downward glance, then together at f48.
2. **Cup and hands during transfer.** Keep the cup wall, both wrists and the receiver’s support visible through approach, hold and release. Recheck contact and reach on the combined characters in the e907 camera.
3. **Hair shape around the faces.** Build depth between the boy’s overlapping crown petals and open a sightline under the fringe. Give the girl G04’s two centre-parted sweeps, ref_30’s soft back-to-ringlet transition and tapered ends. Keep one pink flower on a gathered blue-grey band. Check the back view and the pickup pose. [Boy detail references][boy-uploads] · [Girl detail references][girl-uploads]
4. **Time to read each reaction.** Give her notice, reach and delight distinct holds. Let his glance and withdrawal follow at a different pace. At normal speed a viewer should be able to identify who noticed, who received and who reacted without frame labels.
5. **Clothing under motion and at figure scale.** Seat the girl’s collar through a one-arm reach, make both bloomer cuffs legible, and close the boy’s ankle notch. Compare the T-092 + T-093 result in turnaround and on the moving cast, including the contrast between pale hands and cuffs.

ledger: build 0 · render 0 · tests 0 · ci 0 · wait 588 (min)
