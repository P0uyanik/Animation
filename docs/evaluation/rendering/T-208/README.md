# T-208 | EEVEE on three real paper-boat shots

**Use OpenGL EEVEE for acting and timing review on the MX350. Keep Cycles for material and contact-shadow approval.** At 1280×720, the two 48-frame EEVEE strips averaged **26.44 s/frame** including warm-up, versus **164.22 s/frame** across eight Cycles CPU stills. Peak sampled VRAM was **1,803/2,048 MiB** for successful EEVEE runs and **0 MiB** for Cycles. T-197 Vulkan lost its device on the hand-over at a run peak of **1,954 MiB**. Frame 126 repeated frame 125, then Blender crashed. OpenGL completed the same saved scene.

| Shot and evidence | EEVEE mean s/frame | Cycles CPU mean s/frame | EEVEE peak MiB |
|---|---:|---:|---:|
| s010 · [Table](table.jpg), frames 41 and 184 | 272.40 (two cold stills) | 157.93 | 1,778 |
| s020 · [Hand-over strip](s020-hand-over.mp4), 125–172 · [Contact crop](hand-over.jpg) | 24.96 (18.50 after frame 125) | 251.24 (135, 147, 167) | 1,789 |
| s030 · [Walk-off strip](s030-walk-off.mp4), 93–140 · [Stride crop](walk-off.jpg) | 27.91 (21.76 after frame 93) | 81.40 (93, 117, 140) | 1,803 |

**Motion.** The boy’s fingers close around the boat at frame 147 and the release reads at 167. EEVEE deepens the shadow inside his cuff. In the walk-off, heel lifts and foot plants remain distinct, but shadows under the soles are darker and harder-edged. Fine grain crawls on moving pale hair and fleece, especially against the wall. Neither strip shows a whole-frame flash. All three bakes disable depth of field, so these shots provide no DOF comparison.

**Temporal check.** Across 47 adjacent PNG pairs per strip, mean absolute RGB change was **7.10/255** for the hand-over (peak 22.86 during the head turn) and **6.47/255** for the walk-off (peak 7.92). Stationary tabletop and floor patches averaged **0.022** and **0.002** respectively. Full-frame changes include character motion.

**Method.** The renderer verified all three manifests. The input revision and packages lack `preview_eevee`, so this tests the T-197 fallback at 16 samples against Cycles CPU `review`. Frame time runs from Blender’s render-pre callback through PNG write. Sequence assembly added about 12 minutes for s020 and 10 minutes for s030. First OpenGL strip frames took 329 and 317 seconds respectively. VRAM is whole-device usage sampled every 500 ms. An interrupted s030 CPU run was repeated and excluded. [Per-frame measurements](bench.csv) · [Exact offline commands](commands.ps1)
