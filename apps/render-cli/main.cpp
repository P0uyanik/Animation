// plush-render: the engine's headless shot bake (the animation hand-off to Blender, plush.shot_bake/1).
//   plush-render scene.json --bake shot_bake.json [--frames A-B]
// The engine path tracer and its image/video output were removed in T-142
// (tag backup/20261119T224500Z/legacy-engine-renderer-2026-11-19).
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <filesystem>
#include <optional>
#include <string>

#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
void usage() {
  std::puts(
      "usage: plush-render <scene.json> --bake FILE.json [options]\n"
      "  --bake FILE.json     write the shot bake (plush.shot_bake/1) for the frame range\n"
      "  --frame N            bake one frame\n"
      "  --frames A-B         bake a frame range (default: the whole shot)\n"
      "  --preview            coarser meshes, fewer fibers\n"
      "  --voxel-scale X      mesh coarseness multiplier (default 1)\n"
      "  --fuzz-density X     fiber count multiplier (default 1)\n"
      "  --no-fuzz            disable all fibers\n"
      "  --no-lod             disable fibre level of detail\n"
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
  fs::path bakePath;
  EvalOptions eval;
  bool noLod = false;
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
    } else if (a == "--bake") bakePath = next();
    else if (a == "--preview") { eval.voxelScale = 2.0f; eval.fuzzDensity = 0.35f; }
    else if (a == "--voxel-scale") eval.voxelScale = std::stof(next());
    else if (a == "--fuzz-density") eval.fuzzDensity = std::stof(next());
    else if (a == "--no-fuzz") eval.fuzz = false;
    else if (a == "--no-lod") noLod = true;
    else if (a == "--threads") setWorkerCount(unsigned(std::stoi(next())));
    else if (a == "--camera") camPos = parseVec3(next());
    else if (a == "--target") camTarget = parseVec3(next());
    else if (a == "--focal") focal = std::stof(next());
    else if (a == "--fstop") fstop = std::stof(next());
    else if (a == "--help" || a == "-h") { usage(); return 0; }
    else { logError("unknown option '{}'", a); usage(); return 1; }
  }

  if (bakePath.empty()) {
    logError("--bake FILE.json is required (the engine image renderer was removed in T-142)");
    usage();
    return 1;
  }
  auto scene = loadScene(scenePath);
  if (!scene) {
    logError("{}", scene.error().message);
    return 1;
  }
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
  eval.lodWidth = noLod ? 0 : scene->render.width;

  Stopwatch total;
  SceneEvaluator evaluator;
  if (auto r = evaluator.load(*scene, eval); !r) {
    logError("{}", r.error().message);
    return 1;
  }
  logInfo("scene '{}' prepared in {:.2f}s ({} threads)", scene->name, total.seconds(), workerCount());

  {  // animation hand-off to the Blender renderer (see engine/scene/shot_bake.h)
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
}
