# T-124: 720p render optimisation, measured

Shot: e907 `s010_verbs` (129 frames, 24 fps, both characters, still camera), rendered at 1280x720 through the unchanged
production path (`shot_render.py --blend-only --resolution 1280 720 --samples 128`). Every lever then renders the same
`shot.blend` with one change. Machine: 4 vCPU Xeon @ 2.30 GHz, 15 GiB, no GPU, Blender 5.3.0 ([machine.md](machine.md)).
Numbers are measurements on this machine. The owner chooses; nothing here changes the default render.

## 1. Baseline: what one frame costs today

Current final settings: 128 spp, OIDN (albedo+normal, accurate prefilter, high quality), adaptive sampling 0.01,
12 bounces (diffuse 4, glossy 4, transmission 12, transparent 8), clamp indirect 10.

| Run | Frame | s/frame |
|---|---|---|
| process A | 1 / 65 / 129 | 413 / 437 / 453 |
| process B | 65, 65 (same process) | 428 / 428 |
| probe | 65 | 433 |
| 12-frame clip | 60–71 | mean 436 (426–510; first frame overlapped the encoding run) |

The same frame repeats within about 2% (428–437 s). Frame to frame, the cost moves by about ±5% with the pose.
**The whole shot costs about 15.5 h of CPU** (129 × 433 s).

Breakdown per frame (from Blender's render-stats stream, `tools/render_bench/bench.py`):

| Phase | Seconds | Share |
|---|---|---|
| Opening `shot.blend` (once per process) | 3.2–3.5 | – |
| Depsgraph and sync into Cycles (armature, geometry nodes, 20.0 M fibre curve points in 147 fibre objects) | 7.0–8.6 | ~2% |
| BVH build | 2.5–3.1 | <1% |
| Path tracing + OIDN (OIDN has no progress message of its own) | 400–441 | ~97% |
| Finishing | ~2.2 | <1% |
| PNG save | 0.1–0.2 | – |

OIDN's own cost is lost in the noise: with denoising off the frame took 451 s, inside the per-frame variation. The
fixed per-frame cost (sync + BVH + finishing) is about 13 s; everything else is path tracing.

### Cost drivers (each element switched off alone, frame 65)

| Element off | s/frame | Saving | Note |
|---|---|---|---|
| All fibre strands (hair + garment fuzz) | 263 | −39% (−170 s) | the look changes completely |
| Garment fibre strands (fuzz/halo) | 340 | −22% (−93 s) | hoodie loses its felt |
| Skin/lip subsurface (weight 0) | 337 | −22% (−96 s) | faces flatter |
| Hair fibre strands (hair meshes kept) | 375 | −13% (−58 s) | hair loses its felt |
| Rect area light (sun only) | 384 | −11% (−49 s) | small light change (46.5 dB vs current) |
| Sun light | 424 | −2% | the key light; the frame goes dark |
| Glasses | 429 | −1% | glasses cost almost nothing |

So the fibres and the random-walk skin subsurface are where the time goes. Glasses, transparency depth and bounces
are not.

## 2. Levers (frame 65, each alone, then combined)

Quality is measured against a 512 spp reference (adaptive 0.005, 1669 s), PSNR / SSIM on the whole frame, plus SSIM
on 100% crops (glasses+eyes / girl bun / boy hair edge / hoodie fibres; regions in
`tools/render_bench/crops_s010.json`). For scale, the **current final scores 41.2 dB / 0.978**. The metrics only
support the sheets: look at `sheets/` first.

| Run | Change | s/frame | vs 433 s | vs 512 spp ref: dB / SSIM | vs current: dB | crop SSIM eyes / bun / hair edge / hoodie |
|---|---|---|---|---|---|---|
| `noadapt` | adaptive sampling off | 432 | 0% | 41.21 / 0.978 | 58.0 | 0.973 / 0.959 / 0.967 / 0.896 |
| `thr02` | adaptive threshold 0.02 | 390 | −10% | 40.75 / 0.976 | 49.5 | 0.972 / 0.951 / 0.956 / 0.896 |
| `thr03` | adaptive threshold 0.03 | 305 | −30% | 40.05 / 0.971 | 45.1 | 0.968 / 0.937 / 0.945 / 0.892 |
| **`thr05`** | **adaptive threshold 0.05** | **208** | **−52%** | **39.36 / 0.968** | 42.7 | 0.962 / 0.930 / 0.944 / 0.866 |
| `spp64` | 64 spp | 231 | −47% | 39.77 / 0.971 | 39.3 | 0.964 / 0.940 / 0.951 / 0.867 |
| `spp32` | 32 spp | 125 | −71% | 38.34 / 0.960 | 38.2 | 0.953 / 0.914 / 0.930 / 0.829 |
| **`spp16`** | **16 spp** | **69** | **−84%** | **37.13 / 0.948** | 37.1 | 0.939 / 0.877 / 0.906 / 0.797 |
| `noden` | denoising off | 451 | +4% | 37.85 / 0.950 | 41.3 | 0.845 / 0.940 / 0.951 / 0.849 |
| `den_rgb` | OIDN colour only | 433 | 0% | 41.17 / 0.978 | 47.2 | 0.967 / 0.955 / 0.966 / 0.910 |
| `den_fast_prefilter` | OIDN prefilter fast | 433 | 0% | 40.93 / 0.977 | 49.5 | 0.970 / 0.958 / 0.963 / 0.897 |
| `den_balanced` | OIDN quality balanced | 430 | −1% | 40.85 / 0.976 | 50.0 | 0.969 / 0.957 / 0.963 / 0.888 |
| `bounce6` | max 6 / diff 2 / gloss 2 / trans 4 | 417 | −4% | 36.46 / 0.975 | 38.0 | 0.972 / 0.959 / 0.965 / 0.865 |
| `bounce3` | max 3 / diff 1 / gloss 1 / trans 2 | 378 | −13% | 29.23 / 0.961 | 29.4 | 0.959 / 0.959 / 0.966 / 0.706 |
| `transp4` / `transp16` | transparent bounces 4 / 16 | 428 / 440 | −1% / +2% | 41.1 / 41.2 | 57.9 / 67.6 | unchanged |
| `clamp3` | indirect clamp 3 | 431 | −1% | 41.17 / 0.978 | 64.5 | unchanged |
| `no_rect` | one light fewer (rect off) | 384 | −11% | 41.71 / 0.981 | 46.5 | 0.976 / 0.968 / 0.971 / 0.905 |
| `sss_burley` | skin SSS random walk → Christensen-Burley (render copy only) | 386 | −11% | 40.68 / 0.978 | 48.6 | 0.969 / 0.959 / 0.965 / 0.896 |
| `persistent16` vs `spp16_seq` | persistent data, frames 62–66 at 16 spp | 66.8 vs 67.9 mean | −1.1 s/frame | identical | – | – |
| `fibre50` | fibre LOD: keep 50% of curves | 381 | −12% | 33.32 / 0.936 | 33.5 | 0.947 / 0.848 / 0.859 / 0.768 |
| `fibre25` | fibre LOD: keep 25% of curves | 348 | −20% | 30.05 / 0.907 | 30.1 | 0.919 / 0.765 / 0.795 / 0.685 |
| `fg_catcher` + `bg_plate` | still camera: characters over shadow-catcher props + plate rendered once | 540 + 36 once | **+25%** | 27.22 / 0.965 (composite) | 27.4 | 0.970 / 0.954 / 0.954 / 0.866 |
| `scale75` | 960x540, Lanczos upscale to 720p | 244 | −44% | 38.40 / 0.959 | 38.2 | 0.950 / 0.912 / 0.926 / 0.864 |
| `tile512` | tile 512 (default 2048) | 437 | +1% | identical | – | – |
| `threads2_16` | 2 threads vs 4 (16 spp) | 126 vs 69 | ×1.83 | identical | – | – |
| `thr05_b6` | combined: thr 0.05 + bounce6 + persistent | 191 | −56% | 35.73 / 0.965 | 36.8 | 0.961 / 0.931 / 0.944 / 0.837 |
| `review16` | combined: 16 spp + thr 0.05 + persistent | 66 | −85% | 37.13 / 0.948 | 37.1 | 0.939 / 0.877 / 0.906 / 0.797 |

What the measurements say:

- **Sample count and adaptive threshold are the only big, look-preserving levers.** At 128 spp the current threshold
  (0.01) stops almost no pixels early: turning adaptive sampling off costs nothing. Loosening the threshold lets the
  flat areas stop early. 0.05 halves the frame (208 s) at 39.4 dB, close to 64 spp (231 s, 39.8 dB). 0.03 gives −30%
  at 40.1 dB. At 16 spp the threshold has no effect (`review16` = `spp16`).
- **Denoiser options do not matter here.** They don't change the time, and the quality differences are inside 0.3 dB.
  Keep the current OIDN settings; denoising off is clearly worse (eyes crop 0.845).
- **Bounces:** the saving is small (−4% for max 6) and the hoodie darkens (hoodie crop 0.865; −1.7 dB on top of thr05
  in `thr05_b6`). Max 3 is −13% with visibly darker felt. **Not recommended.** Transparent bounces and clamping change
  nothing.
- **Persistent data saves about 1 s per frame** (sync is small and the characters deform every frame, so most data is
  re-synced anyway). It's harmless, so it's included in both profiles.
- **Fibre LOD by density changes the look:** fewer curves make the felt thinner and the hair edges less fuzzy
  (`sheets/crops_elements.jpg`). LOD by on-screen size can't keep silhouettes unchanged with this fibre system without
  edits to the fibre node group (an asset change, not allowed here). **Not recommended.**
- **Static background plus shadow catcher is slower on this shot (+25%)**, not faster. The background is already
  cheap: the plate alone renders in 36 s, and adaptive sampling stops on the flat wall early. The shadow catcher then
  adds work on the props behind the characters. The composite also differs in shadows (27 dB). **Not recommended.**
- **Hold-frame reuse: 0 identical frames in this shot** (`data/holds.json`, `tools/render_bench/holds.py`). The
  characters' idle motion never stops, so there is nothing to reuse here. The script can check other shots.
- **540p + upscale:** at 244 s it is slower than 32 spp at native 720p and slightly worse (38.4 vs 38.3 dB with
  softer edges). **Not recommended.**
- **Threads:** scaling from 2 to 4 threads is ×1.83, nearly linear. Splitting frame ranges across sessions or
  machines therefore wins almost fully.
- **Tiles:** no effect at 720p.
- **Skin SSS method (Burley instead of random walk) −11% at nearly the same quality.** This is a material-behaviour
  choice, not a sampling one. I measured it in the render copy only and **did not put it in a profile**; the
  owner/material lane decides.
- **Rect light off −11%:** this is lighting/staging, not a render setting, so it's measured only.

### Moving clips (frames 60–71, 16-bit masters; `clips/`)

`clips/clip_full.mp4` (2x2 at 50%) and `clips/clip_crop.mp4` (2x2, 100% crop of glasses/eyes/hair) show the same 12
frames, looped 4×: current final, thr 0.05, 64 spp, review.

| Clip | Mean s/frame (60–71) | Residual flicker vs current final (8-bit luma levels) | Own frame-to-frame change |
|---|---|---|---|
| current final, 128 spp thr 0.01 | 436 | – | 2.16 |
| thr 0.05 (proposed `final720`) | 207 | 1.06 | 2.25 (+4%) |
| 64 spp | 218 | 1.58 | 2.23 (+3%) |
| 16 spp (proposed `review`) | 65 | 1.90 | 2.27 (+5%) |

Residual flicker = mean |(test − current)_t − (test − current)_{t−1}|: how much a setting adds its own frame-to-frame
noise relative to the current final (`tools/render_bench/metrics.py`). The current final itself is not noise-free; I
did not render a 512 spp clip (about 5.5 h for 12 frames). thr 0.05 adds the least temporal noise of the three
candidates, less than 64 spp at a similar cost. In the stills (`sheets/crops_proposed.jpg`) the review profile shows
slightly smeared hair fibres (OIDN on 16 spp). The clips are for the owner to judge flicker and shimmer by eye; I did
not review them frame by frame.

## 3. Encoding (`data/encode.json`, `tools/render_bench/encode_bench.py`)

The master is the 48-frame (2 s) 16-bit PNG review clip, frames 41–88. Metrics are against the master in
yuv444p16, so chroma subsampling counts against every codec. libvmaf isn't available in this ffmpeg (6.1.1), so
SSIM/PSNR are used and **VMAF was not measured**.

| Codec (preset) | CRF | Mbit/s | SSIM | PSNR dB | gradient crop PSNR dB | encode s (2 s clip) |
|---|---|---|---|---|---|---|
| H.264 8-bit 4:2:0 (x264 slow) | 12 / 16 / 20 / 24 | 14.4 / 8.7 / 4.6 / 2.1 | 0.9927 / 0.9899 / 0.9856 / 0.9794 | 46.8 / 45.6 / 44.0 / 42.4 | 54.3 / 53.5 / 52.4 / 51.1 | 5.4 / 4.7 / 4.0 / 3.1 |
| HEVC 10-bit 4:2:0 (x265 slow) | 14 / 18 / 22 / 26 | 11.4 / 6.9 / 3.8 / 1.8 | 0.9931 / 0.9902 / 0.9860 / 0.9801 | 46.8 / 45.6 / 44.2 / 42.6 | 56.3 / 55.0 / 53.7 / 52.1 | 13.2 / 11.9 / 10.7 / 8.4 |
| AV1 10-bit 4:2:0 (SVT-AV1 p6) | 18 / 26 / 34 / 42 | 5.5 / 2.8 / 1.2 / 0.6 | 0.9896 / 0.9855 / 0.9806 / 0.9758 | 45.4 / 44.1 / 42.7 / 41.6 | 55.1 / 54.0 / 52.3 / 50.8 | 7.1 / 6.1 / 5.2 / 5.0 |

At matched quality (SSIM ≈ 0.990 / ≈ 0.986): H.264 8.7 / 4.6 Mbit/s, HEVC 6.9 / 3.8 (**−20%**), AV1 5.5 / 2.8
(**−37 to −40%**).

Banding on the soft gradients: at matched quality both 10-bit codecs keep the background gradient 1.5–2 dB closer to
the master. In `sheets/banding_codecs.jpg` (contrast ×8 on the wall/floor and the hoodie), H.264 8-bit shows a
slight colour cast and blocky steps on the wall; HEVC 10-bit shows some blocking; AV1 10-bit is the cleanest.

The encoding was measured on a 2 s clip only: sizes per minute will move with motion and content, but the ratios
between codecs are the useful part.

Playback compatibility (general knowledge as of 2026, **not tested on devices here**):

| | H.264 8-bit | HEVC 10-bit | AV1 10-bit |
|---|---|---|---|
| Phones | all | iPhone, most Android (hardware) | recent iPhones (A17 Pro and later) and recent Android; older phones software-decode or not at all |
| Browsers | all | Safari; Chrome/Edge only with hardware support; Firefox limited | Chrome, Edge, Firefox; Safari on hardware with AV1 decode |
| YouTube upload | yes | yes | yes (YouTube re-encodes every upload) |

Suggested delivery: keep lossless masters (16-bit PNG or EXR) out of git. For YouTube, upload a high-rate master
(H.264 8-bit CRF ≤ 16 or HEVC 10-bit CRF ≤ 18), since YouTube re-encodes everything. For direct files, HEVC 10-bit
covers phones; AV1 10-bit is smallest but older phones can't play it. Keep H.264 as the fallback for anything else.

## 4. EEVEE

EEVEE needs a GPU backend. In this container Blender found no Vulkan device (no GPU). With the lavapipe software
Vulkan driver the process ran for about 20 minutes and exited without producing frame 65 or an error
message. So **EEVEE could not be compared here**; a
software-emulated GPU says nothing about EEVEE on real hardware. Compare it on the owner's PC or a rented GPU.

## 5. Proposed opt-in profiles (`pipeline/charsys/render_profiles.json`)

`shot_render.py --profile <name>` (also sets resolution and samples unless `--resolution`/`--samples` are given).
Without `--profile`, nothing changes: I ran the same `--blend-only` command with the input SHA (8d86e03) and with this
branch, and the saved scenes' render/Cycles/image settings (all writable properties) and `shot_render.json` are
identical except for the setup time. The existing `test_render_engine.py` passes.

| Profile | Settings | s/frame here | Shot (129 frames) on this 4-core machine | Quality |
|---|---|---|---|---|
| (current) | 128 spp, thr 0.01 | 433 | 15.5 h | 41.2 dB vs 512 spp |
| `final720` | 1280x720, 128 spp, **adaptive 0.05**, persistent data | 207 | 7.4 h (**−52%**) | 39.4 dB; least added flicker of the candidates |
| `review` | 1280x720, 16 spp, adaptive 0.05, persistent data | 65–67 | 2.4 h (**−85%**) | 37.1 dB; slightly smeared hair fibres; for timing/acting review |

Owner choices the data leaves open:

1. `final720` with threshold **0.05** (−52%) or **0.03** (−30%, 40.1 dB, closer to today).
2. Whether to try the Burley skin SSS (−11%, a material decision).
3. Whether the rect light earns its 11%.

## Reproduce

```
pipeline/blender/install_blender.sh            # or: python3.13 -m venv v && v/bin/pip install bpy==5.3.0 numpy pillow
blender=<blender, or "v/bin/python tools/render_bench/blender_shim.py">
python3 pipeline/production/run_shot.py --shot episodes/e907_exchange/shots/s010_verbs/shot.scene.json --blender $blender --stages prepare,bake
$blender -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake <build>/bake.json --cast <build>/cast.json --out runs/base --resolution 1280 720 --samples 128 --blend-only
tools/render_bench/run_queue.sh $blender runs/base/shot.blend runs <queue file: "variant frames [repeat] [name] [--png16]" per line>
python tools/render_bench/summarise.py runs summary.json ; python tools/render_bench/make_sheets.py runs summary.json sheets
python tools/render_bench/make_clips.py runs clips 60 71 ; python3 tools/render_bench/encode_bench.py runs/clip_review16 41 enc
python3 tools/render_bench/holds.py <build>/bake.json
```

Variants are in `tools/render_bench/variants.json`. Raw per-run results (per-frame phases and timelines) are in
`data/bench/*.json`. Lossless masters and per-run PNGs are not committed.

## Caveats

- One shot and one machine; frame 65 for most levers (the 3-frame baseline spans ±5%).
- Shared vCPUs: repeat runs agree within about 2%.
- The first clip frame (60, 510 s) overlapped the encoding run.
- About 1.5 h of queue time was lost to a session restart. It didn't affect any measurement: the interrupted run was
  redone from scratch.
