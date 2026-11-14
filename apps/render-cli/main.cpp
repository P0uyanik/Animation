// plush-render: headless renderer for scenes (stills, frame sequences, video).
//   plush-render scene.json --frame 1 --out frame.png
//   plush-render scene.json --frames 1-48 --outdir renders/shot --video shot.mp4
// Frame sequences resume automatically: frames that already exist are skipped.
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <filesystem>
#include <optional>
#include <string>

#include "render/image.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
void usage() {
  std::puts(
      "usage: plush-render <scene.json> [options]\n"
      "  --frame N            render one frame (default: scene start)\n"
      "  --bake FILE.json     write the shot bake (plush.shot_bake/1) for the frame range instead of rendering\n"
      "  --frames A-B         render a frame range into --outdir\n"
      "  --out FILE.png       output for a single frame (default render.png)\n"
      "  --outdir DIR         output folder for sequences (frame_0001.png ...)\n"
      "  --video FILE.mp4     encode the sequence with ffmpeg afterwards\n"
      "  --width W --height H --spp S --depth D --exposure EV\n"
      "  --preview            quick quality: coarser meshes, fewer fibers\n"
      "  --voxel-scale X      mesh coarseness multiplier (default 1)\n"
      "  --fuzz-density X     fiber count multiplier (default 1)\n"
      "  --no-fuzz            disable all fibers\n"
      "  --no-lod             disable fibre level of detail\n"
      "  --adaptive X         adaptive sampling threshold (0 = off)\n"
      "  --no-denoise         skip the denoiser\n"
      "  --overwrite          re-render frames that already exist\n"
      "  --hdr                also write linear .hdr files\n"
      "  --compare REF.png    compare the result with a reference image (exit 3 if different)\n"
      "  --max-rmse X         tolerance for --compare (default 0.03)\n"
      "  --threads N          worker threads (default: all)\n"
      "  --camera X,Y,Z --target X,Y,Z --focal MM --fstop N   camera overrides (look dev)");
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    usage();
    return 1;
  }
  fs::path scenePath = argv[1];
  int frameA = INT32_MIN, frameB = INT32_MIN;
  fs::path out = "render.png", outdir, video, bakePath;
  EvalOptions eval;
  bool overwrite = false, hdr = false;
  int width = 0, height = 0, spp = 0, depth = 0;
  float exposure = NAN;
  bool noDenoise = false;
  bool noLod = false;
  float adaptive = -1;
  fs::path compareRef;
  double maxRmse = 0.03;
  std::optional<vec3> camPos, camTarget;
  float focal = 0, fstop = -1;
  auto parseVec3 = [](const std::string& t) {
    vec3 v(0);
    std::sscanf(t.c_str(), "%f,%f,%f", &v.x, &v.y, &v.z);
    return v;
  };
  for (int i = 2; i < argc; ++i) {
    std::string a = argv[i];
    auto next = [&]() -> std::string {
      if (i + 1 >= argc) {
        logError("missing value for {}", a);
        std::exit(1);
      }
      return argv[++i];
    };
    if (a == "--frame") frameA = frameB = std::stoi(next());
    else if (a == "--frames") {
      std::string r = next();
      auto dash = r.find('-', 1);
      frameA = std::stoi(r.substr(0, dash));
      frameB = dash == std::string::npos ? frameA : std::stoi(r.substr(dash + 1));
    } else if (a == "--out") out = next();
    else if (a == "--bake") bakePath = next();
    else if (a == "--outdir") outdir = next();
    else if (a == "--video") video = next();
    else if (a == "--width") width = std::stoi(next());
    else if (a == "--height") height = std::stoi(next());
    else if (a == "--spp") spp = std::stoi(next());
    else if (a == "--depth") depth = std::stoi(next());
    else if (a == "--exposure") exposure = std::stof(next());
    else if (a == "--preview") { eval.voxelScale = 2.0f; eval.fuzzDensity = 0.35f; }
    else if (a == "--voxel-scale") eval.voxelScale = std::stof(next());
    else if (a == "--fuzz-density") eval.fuzzDensity = std::stof(next());
    else if (a == "--no-fuzz") eval.fuzz = false;
    else if (a == "--no-lod") noLod = true;
    else if (a == "--adaptive") adaptive = std::stof(next());
    else if (a == "--no-denoise") noDenoise = true;
    else if (a == "--overwrite") overwrite = true;
    else if (a == "--compare") compareRef = next();
    else if (a == "--max-rmse") maxRmse = std::stod(next());
    else if (a == "--hdr") hdr = true;
    else if (a == "--threads") setWorkerCount(unsigned(std::stoi(next())));
    else if (a == "--camera") camPos = parseVec3(next());
    else if (a == "--target") camTarget = parseVec3(next());
    else if (a == "--focal") focal = std::stof(next());
    else if (a == "--fstop") fstop = std::stof(next());
    else if (a == "--help" || a == "-h") { usage(); return 0; }
    else { logError("unknown option '{}'", a); usage(); return 1; }
  }

  auto scene = loadScene(scenePath);
  if (!scene) {
    logError("{}", scene.error().message);
    return 1;
  }
  RenderSettings rs = scene->render;
  if (width > 0) rs.width = width;
  if (height > 0) rs.height = height;
  if (spp > 0) rs.spp = spp;
  if (depth > 0) rs.maxDepth = depth;
  if (!std::isnan(exposure)) rs.exposureEV = exposure;
  if (noDenoise) rs.denoise = false;
  if (adaptive >= 0) rs.adaptiveThreshold = adaptive;
  if (frameA == INT32_MIN) frameA = frameB = scene->frameStart;
  if (camPos || camTarget) {  // a fixed look-dev camera ignores camera animation
    scene->animation.tracks.erase("camera.position");
    scene->animation.tracks.erase("camera.target");
    if (camPos) scene->camera.position = *camPos;
    if (camTarget) scene->camera.target = *camTarget;
    scene->camera.focusDistance = -1;
  }
  if (focal > 0) scene->camera.focalMm = focal;
  if (fstop >= 0) scene->camera.fStop = fstop;
  bool sequence = !outdir.empty();
  eval.lodWidth = noLod ? 0 : rs.width;

  Stopwatch total;
  SceneEvaluator evaluator;
  if (auto r = evaluator.load(*scene, eval); !r) {
    logError("{}", r.error().message);
    return 1;
  }
  logInfo("scene '{}' prepared in {:.2f}s ({} threads, denoiser {})", scene->name, total.seconds(), workerCount(),
          denoiserAvailable() ? "on" : "unavailable");

  if (!bakePath.empty()) {  // animation hand-off to a production renderer (see engine/scene/shot_bake.h)
    if (frameB == frameA && frameA == scene->frameStart) frameB = scene->frameEnd;  // default: the whole shot
    Stopwatch sw;
    Json bake = bakeShot(evaluator, frameA, frameB);
    std::ofstream f(bakePath);
    f << bake.dump();
    if (!f) {
      logError("cannot write {}", bakePath.string());
      return 1;
    }
    logInfo("baked frames {}-{} of '{}' -> {} ({:.1f}s)", frameA, frameB, scene->name, bakePath.string(), sw.seconds());
    for (const auto& w : evaluator.warnings()) logInfo("warning: {}", w);
    return 0;
  }
  PathTracer tracer;
  for (int f = frameA; f <= frameB; ++f) {
    fs::path target = sequence ? outdir / std::format("frame_{:04d}.png", f) : out;
    if (sequence && !overwrite && fs::exists(target) && fs::file_size(target) > 0) {
      logInfo("frame {} exists, skipping", f);
      continue;
    }
    Stopwatch sw;
    auto snap = evaluator.evaluate(double(f));
    int lastPct = -1;
    RenderOutput result = tracer.render(snap, rs, [&](float p) {
      int pct = int(p * 100);
      if (pct / 25 != lastPct / 25) {
        lastPct = pct;
        logInfo("  frame {}: {}%", f, pct);
      }
    });
    if (rs.denoise) denoise(result, rs.denoiseBlend);
    auto rgb = toneMapToSrgb8(result.color, ToneMapSettings{rs.exposureEV});
    // Write to a temp name first so an interrupted job never leaves a half file.
    fs::path tmp = target;
    tmp += ".tmp.png";
    if (auto r = writePng(tmp, rs.width, rs.height, rgb); !r) {
      logError("{}", r.error().message);
      return 1;
    }
    fs::rename(tmp, target);
    if (!compareRef.empty()) {
      int rw = 0, rh = 0;
      auto ref = readImageRgb8(compareRef, rw, rh);
      if (!ref) {
        logError("{}", ref.error().message);
        return 3;
      }
      double rmse = imageRmse(rgb, *ref);
      logInfo("regression: rmse {:.4f} vs {} (limit {:.4f})", rmse, compareRef.string(), maxRmse);
      if (rmse < 0 || rmse > maxRmse) {
        logError("regression FAILED for frame {}", f);
        return 3;
      }
    }
    if (hdr) {
      fs::path h = target;
      h.replace_extension(".hdr");
      (void)writeHdr(h, result.color);
    }
    logInfo("frame {} -> {} ({}x{}, {} spp, {:.1f}s)", f, target.string(), rs.width, rs.height, result.samples, sw.seconds());
  }

  if (sequence && !video.empty()) {
    std::string cmd = std::format(
        "ffmpeg -y -loglevel error -framerate {}/{} -start_number {} -i \"{}\" -c:v libx264 -pix_fmt yuv420p -crf 16 "
        "-preset slow \"{}\"",
        scene->rate.num, scene->rate.den, frameA, (outdir / "frame_%04d.png").string(), video.string());
    logInfo("encoding video: {}", video.string());
    if (std::system(cmd.c_str()) != 0) {
      logError("ffmpeg failed (is it installed and on PATH?)");
      return 1;
    }
  }
  logInfo("done in {:.1f}s", total.seconds());
  return 0;
}
