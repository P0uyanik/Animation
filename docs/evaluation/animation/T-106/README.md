# T-106 · Reference performance extraction

The clearest shared timing target is the watertable point. The girl reaches over 17 frames, holds the point for 22 more and takes 35 frames to withdraw and straighten. The boy keeps his gaze toward the boat through that action, with three distinct blinks. In paperboat, the white-haired girl's three visible blinks fall in three separate shots. These frame ranges give T-097B/G and T-104 starting points for matching specific performances.

## Calibration table

Both clips run at 24 fps. Frame zero is the first decoded frame. All intervals use **[first frame, end frame)**, so [151, 175) lasts exactly 24 frames or 1.00 s. A blank CSV field or JSON null means unavailable. A numeric zero is an observation.

| Clip | Character | Reviewed face frames | Face matches | Matched pose noses | Blinks | Partial dips | Blinks / visible min |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Paperboat | Boy | 101 | 34 (33.7%) | 12 | 0 | 1 | 0.0 |
| Paperboat | Girl with glasses | 105 | 80 (76.2%) | 23 | 0 | 0 | 0.0 |
| Paperboat | White-haired girl | 117 | 63 (53.8%) | 0 | 3 | 0 | 36.9 |
| Watertable | Boy | 121 | 70 (57.9%) | 0 | 3 | 0 | 35.7 |
| Watertable | Girl with glasses | 121 | 105 (86.8%) | 0 | 3 | 1 | 35.7 |
| Watertable | White-haired girl | 121 | 67 (55.4%) | 0 | 3 | 0 | 35.7 |

Paperboat is 289 frames, with cuts at f32, f112, f151, f191 and f239. Facial coverage includes [0, 32) and [112, 151) for all three. In the final camera reveal, the white-haired girl's reviewed window starts at f243, the girl with glasses at f255 and the boy at f259. Each ends at f289. The hand and boat inserts have separate action records. All three faces were reviewable throughout watertable's 121 frames. Detection percentages use these same per-character windows, including closed lids. Blink rates divide the observed count by reviewed seconds and multiply by 60. The short, edited exposures make the counts and event spacing especially important.

## Acting and timing targets

| Character | Paperboat | Watertable |
| --- | --- | --- |
| Boy | Heavy lids over the paper for [0, 32), 1.33 s. The f128 dip leaves iris visible. His eyes open wider and his mouth parts in the [259, 289) reveal. | Holds the rightward look for [27, 60), 1.38 s. Blink minima at f22, f62 and f83 give spacings of 1.67 and 0.88 s. Over [60, 81) the upper face moves 58 px left and 29 px up with about 5° counterclockwise roll. The final [87, 121) hold has under 1 px net translation on either axis. |
| Girl with glasses | A small upward eye adjustment occupies [125, 132), 0.29 s, followed by a 0.79 s hold. The closed mouth at the desk gives way across the cut to an open smile at the tub. Her hands lower the boat over [151, 175), 1.00 s, and release over [175, 191), 0.67 s. | Rounded mouth and hand at chin lead into the reach [22, 39) and point hold [39, 61), 0.71 and 0.92 s. During straightening [81, 96) the face moves 31 px left and 36 px up. Arms stay down for [96, 121), 1.04 s. A partial dip at f114 interrupts the settled smile. |
| White-haired girl | Blink envelopes [4, 10), [122, 129) and [245, 250) last 0.25, 0.29 and 0.21 s. After the reveal blink, she holds her hands clasped and eyes toward the glowing boat for [250, 289), 1.63 s. | She looks left toward the table. During [56, 77) she blinks, parts her lips and raises her head, moving 25 px right and 34 px up. A 1.21 s hold follows. Her eye line is more frontal on reopening at f112. |

Head translation is net optical flow in source pixels, with right and down positive. Positive roll is clockwise in the image. The final paperboat reveal includes a substantial camera tilt and pullback. Its vertical flow measures the combined screen movement of the face and camera. Gaze directions and expression boundaries are visual readings at one-frame resolution. Small adjustments can be difficult to separate from a turn of the head. The two wide shots and the reveal supply independent observations of the paperboat expressions.

## Detection limits and evidence

MediaPipe returned a position-matched face on **419 of 686 character-frames (61.1%)**. Only four of the twelve reviewed blink minima had a matched mesh. At the boy's clearly closed watertable f83, left and right blink scores were 0.0050 and 0.0002. A fixed score threshold would miss that closure. The event table therefore uses reviewed lids, eye direction and mouth shapes across all faces. Model scores remain available for inspection. The full-frame pose pass yielded 35 matched noses across paperboat and zero in watertable. Optical flow supplies head measurements throughout the reviewed shots.

- [Performance JSON](performance.json) contains the six coverage rows and all 85 timed observations. The [interval CSV](performance.csv) and [coverage CSV](coverage.csv) contain the same records. Filter intervals by clip, character and kind. Acting, gaze and eyelid rows overlap by design.
- [Frame measurements](frame_measurements.csv) records native frame/time, identity checks, raw blendshapes, matched pose nose and stepwise head motion. Acting beat summaries include median available jaw score, matched frame count, valid flow steps and net motion from first to last included frame. Blink rows give the blendshape readings at their marked minimum when available.
- [Paperboat](paperboat.jpg) and [watertable](watertable.jpg) show the shot context above the character crops. [Eyelid evidence](eyelids.jpg) shows every counted blink and both partial dips, with its preceding, peak and recovered frame.
- [Source manifest](sources.json) records clip dimensions, frame counts, fps and SHA-256 hashes for both inputs and both task bundles. [Tooling and tests](../../../../tools/perf_extract/README.md) give the offline reproduction commands and annotation rules.

The owner evidence uses decoded reference frames. The T-087 Cycles comparison requires baseline and candidate character builds and six matched reference views. T-106 supplies source performances for analysis and has no candidate build. Relay status was recorded in the task conversation within the requested write-set.

ledger: build 10 · render 1 · tests 1 · ci 0 · wait 0 (min)
