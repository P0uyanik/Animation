# T-173 · Local Cycles benchmark

**CPU was fastest at 76.5 s/frame. OptiX took 167.1 s and CUDA took 1,399.3 s** on the same two views of the girl character turntable.

| Preset | Device | Mean s/frame | Speed vs final720 CPU | Peak VRAM (MiB) | 192 frames (hours) |
|---|---|---:|---:|---:|---:|
| final720 | CPU | 76.5 | 1.00× | — | 4.08 |
| final720 | MX350 OptiX | 167.1 | 0.458× | 1,635 | 8.91 |
| final720 | MX350 CUDA | 1,399.3 | 0.055× | 1,407 | 74.63 |
| legacy128 | CPU | 256.3 | 0.299× | — | 13.67 |

**Image agreement.** Both GPU crops match the CPU face, glasses and hair by eye. Across both matched PNGs, mean absolute RGB differences on the 0–255 scale were 0.103 for OptiX and 0.068 for CUDA. Maximum channel differences were 30 and 27. [Front-view crops at 1:1](front.jpg) · [Individual timings and differences](bench.csv)

**Workload.** Windows application control blocked the T-124 shot bake (WinError 4551). The turntable uses the published girl 0.13.0 master, T-081 body camera and `character_neutral/1` lights. The table averages the front and three-quarter views after a −15° warm-up. Multi-hour telemetry gaps invalidated the CUDA side view. The 8 s / 24 fps projection multiplies each mean by 192 and excludes setup and encoding.

**Settings.** 1280×720, 128 spp, CPU OpenImageDenoise, PNG output. Final720 uses adaptive threshold 0.05 and persistent data. Legacy128 uses 0.01 and releases render data between frames. Timings include view setup, rendering, denoising and PNG write. OptiX compilation took 120 s during warm-up. Both GPU backends reduced concurrency to fit memory and completed the matched frames without OOM or CPU tracing fallback. VRAM is the whole-device peak sampled by `nvidia-smi` every 500 ms, including warm-up. [T-166 presets](../T-166/README.md) · [T-124 baseline](../T-124/README.md)

**Machine.** GeForce MX350, 2,048 MiB, driver 581.83 · Core i5-1135G7, 4 cores / 8 threads · 15.67 GiB RAM · Windows 11 Home 25H2 (26200.9974) · Blender 5.3.0 (`02f0899d78e3`, matches pipeline). CPU threading was automatic. Legacy128 ran after the interruption and its two matched frames took 359 s and 153 s. Laptop power and clock speeds were uncontrolled.

**Re-run** from the worktree root at `7a708139` in PowerShell. Frame 4 repeats the interrupted CUDA side view. The summary uses frames 2 and 3.

```powershell
$p = 'C:/AnimationWT/t106-codex/build/perf-venv/Scripts/python.exe'
$b = 'docs/evaluation/rendering/T-173'
$env:T173_RUN = 't173-' + (Get-Date -Format yyyyMMdd-HHmmss)
foreach ($d in 'CPU','OPTIX','CUDA') { & $p -B "$b/bench.py" $d final720 1 2 3 4 }
& $p -B "$b/bench.py" CPU legacy128 1 2 3 4
& $p -B "$b/summarize.py"
```
