# T-197 · EEVEE preview on the GeForce MX350

**Use EEVEE for blocking and broad acting review. Keep Cycles for look approval and final frames.** At 1280×720, four matched stills averaged **4.54 s/frame in EEVEE versus 60.98 s in Cycles CPU (13.4× faster)**. EEVEE peaked at **1,645 / 2,048 MiB** during warm-up and **1,571 MiB** during measured frames. Cycles CPU registered 0 MiB on the MX350.

| Matched view and 1:1 crop (Cycles left, EEVEE right) | Cycles s | EEVEE s | RGB MAE (0–255) |
|---|---:|---:|---:|
| [Girl · front](sheet-front.jpg) | 31.11 | 4.58 | 1.28 |
| [e912 · paper boat on table](prop-boat.jpg) | 18.87 | 2.33 | 7.05 |
| [Girl · three-quarter](sheet-threequarter.jpg) | 28.55 | 5.92 | 1.21 |
| [Girl · face front](sheet-face_front.jpg) | 165.39 | 5.36 | 5.52 |

**What reads.** Pupil direction, catchlights, glasses rims and the mouth line agree at both character scales. In close-up, EEVEE adds grain to the pupils and cheeks, breaks up the soft forehead shading and loses fine lit fibres along the hairline. The boot fleece is brighter and coarser. On the boat, both renderers hold focus on the hull and soften the far edges at f/5.6. EEVEE darkens the gaps under the sail and the contact shadow at the right end.

**Scope.** Windows application control blocked the e912 bake executable built from `3d85c2a0` (WinError 4551) after all three cast exports succeeded. The local worktrees had no saved e912 bake or shot blend. Substitutes were the published girl 0.14.0 with T-155 strict-sheet camera geometry and lighting at review resolution, and the s020 classroom, lights and four assembled boat pieces at rest with a detail camera. The three-character VRAM peak, hand-over contact, walking and temporal flicker remain unmeasured.

**Settings and timing.** Blender 5.3.0, driver 581.83, i5-1135G7. Use EEVEE Vulkan, 16 samples, jittered soft shadows, 4 shadow rays, 128 MiB shadow pool, quarter-resolution screen tracing and fast-GI ambient occlusion. Cycles used the `review` profile, automatic CPU threads, 16 spp, adaptive 0.05, persistent data and CPU OIDN. Times include render and PNG write after scene setup. The excluded three-quarter face warm-up took 124.96 s CPU and 55.69 s EEVEE. VRAM is whole-device usage sampled every 500 ms. Differences use all RGB channels of the full display-referred PNGs, including the sheet backdrop. [Per-frame peaks, timings, MAE, RMSE and maximum differences](bench.csv)

**Re-run** from the worktree root in PowerShell. Each run keeps its PNGs, logs and caches under `build/t197/`. The final command regenerates the CSV and crops here.

```powershell
$p = 'C:/AnimationWT/t106-codex/build/perf-venv/Scripts/python.exe'
$b = 'docs/evaluation/rendering/T-197'
$env:T197_RUN = Get-Date -Format 'yyyyMMdd-HHmmss'
& $p -B "$b/bench.py" cycles
& $p -B "$b/bench.py" eevee
& $p -B "$b/compare.py" eevee
```
