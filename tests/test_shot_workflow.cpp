// Plush Studio production workflow (apps/studio/shot_workflow.h, T-001): shot discovery, command and stage
// building, status parsing, frame mapping, merge-save with unknown fields at every depth, and the job runner on a
// dummy process tree (child + grandchildren): progress, cancel (graceful and forced), no orphans.
#include <doctest/doctest.h>

#include <signal.h>
#include <unistd.h>

#include <chrono>
#include <fstream>
#include <thread>

#include "shot_workflow.h"

using namespace plush;
namespace wf = plush::workflow;
namespace fs = std::filesystem;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;
fs::path tempDir(const std::string& name) {
  fs::path d = fs::temp_directory_path() / std::format("plush_wf_{}_{}", name, ::getpid());
  fs::remove_all(d);
  fs::create_directories(d);
  return d;
}
void writeFile(const fs::path& p, const std::string& text) {
  fs::create_directories(p.parent_path());
  std::ofstream(p) << text;
}
std::string readFile(const fs::path& p) {
  std::ifstream f(p);
  return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}
const char* kMiniShot = R"J({"format": "plush.scene", "version": 1, "name": "mini", "frameStart": 3, "frameEnd": 9,
  "characters": [{"name": "a", "asset": "(set by run_shot)"}, {"name": "b", "asset": "(set by run_shot)"}],
  "production": {"cast": {"a": {"version_dir": "store/a/1.0.0"}, "b": {"spec": "specs/b.json"}},
                 "render": {"resolution": [320, 180], "samples": 8, "light_scale": 0.5}}})J";
}  // namespace

TEST_CASE("workflow: shot discovery reads every episodes/*/shots/*/shot.scene.json, no per-shot code") {
  fs::path root = tempDir("discover");
  writeFile(root / "episodes/e1/shots/s010/shot.scene.json", kMiniShot);
  writeFile(root / "episodes/e2/shots/x/shot.scene.json", R"({"format": "plush.scene", "version": 1, "name": "plain"})");
  writeFile(root / "episodes/e2/shots/notes/readme.txt", "not a shot");
  writeFile(root / "episodes/e2/shots/broken/shot.scene.json", R"({"format": "something else"})");
  auto shots = wf::discoverShots(root);
  REQUIRE(shots.size() == 2);
  CHECK(shots[0].episode == "e1");
  CHECK(shots[0].shot == "s010");
  CHECK(shots[0].frameStart == 3);
  CHECK(shots[0].frameEnd == 9);
  CHECK(shots[0].hasProduction);
  REQUIRE(shots[0].cast.size() == 2);
  CHECK(shots[0].cast[0].sourceKind == "published");
  CHECK(shots[0].cast[0].source == "store/a/1.0.0");
  CHECK(shots[0].cast[1].sourceKind == "spec");
  CHECK(shots[0].width == 320);
  CHECK(shots[0].samples == 8);
  CHECK(shots[0].lightScale == doctest::Approx(0.5));
  CHECK(shots[1].episode == "e2");
  CHECK_FALSE(shots[1].hasProduction);
  CHECK(shots[0].runsDir() == shots[0].path.parent_path() / "build" / "runs");
  // the repository's own shots are found the same way
  auto repo = wf::discoverShots(kRoot);
  CHECK(repo.size() >= 2);
  for (auto& s : repo) CHECK(s.hasProduction);
  fs::remove_all(root);
}

TEST_CASE("workflow: command and stage building") {
  wf::ShotInfo shot = *wf::readShotInfo(kRoot / "episodes/e000_pilot/shots/s010/shot.scene.json");
  wf::Config cfg = wf::makeConfig(kRoot, "/x/plush-render", "/opt/blender");
  CHECK(cfg.blenderSource == "--blender");
  wf::RunSettings s;
  s.stages = {"prepare", "bake", "render"};
  s.frameA = 5;
  s.frameB = 7;
  s.width = 320;
  s.height = 180;
  s.samples = 16;
  auto cmd = wf::buildCommand(cfg, shot, "run1", s);
  std::string joined;
  for (auto& c : cmd) joined += c + " ";
  CHECK(cmd[0] == "python3");
  CHECK(cmd[1] == (kRoot / "pipeline/production/run_shot.py").string());
  CHECK(joined.find("--shot " + shot.path.string()) != std::string::npos);
  CHECK(joined.find("--blender /opt/blender") != std::string::npos);
  CHECK(joined.find("--engine /x/plush-render") != std::string::npos);
  CHECK(joined.find("--run-dir run1") != std::string::npos);
  CHECK(joined.find("--stages prepare,bake,render ") != std::string::npos);
  CHECK(joined.find("--frames 5-7") != std::string::npos);
  CHECK(joined.find("--resolution 320 180") != std::string::npos);
  CHECK(joined.find("--samples 16") != std::string::npos);
  s.width = s.height = s.samples = 0;  // shot defaults: not passed
  joined.clear();
  for (auto& c : wf::buildCommand(cfg, shot, "run2", s)) joined += c + " ";
  CHECK(joined.find("--resolution") == std::string::npos);
  CHECK(joined.find("--samples") == std::string::npos);
  auto mc = wf::markCancelledCommand(cfg, shot, "run1");
  CHECK(mc.back() == "--mark-cancelled");
  // Blender from the environment, then the settings file
  fs::path d = tempDir("cfg");
  writeFile(d / "settings.json", R"({"blender": "/from/settings"})");
  setenv("PLUSH_STUDIO_SETTINGS", (d / "settings.json").c_str(), 1);
  setenv("PLUSH_BLENDER", "/from/env", 1);
  CHECK(wf::makeConfig(kRoot, "", "").blender == "/from/env");
  unsetenv("PLUSH_BLENDER");
  CHECK(wf::makeConfig(kRoot, "", "").blender == "/from/settings");
  CHECK(wf::makeConfig(kRoot, "", "").blenderSource.find("settings file") == 0);
  unsetenv("PLUSH_STUDIO_SETTINGS");
  CHECK(wf::newRunId().size() == 19);
  fs::remove_all(d);
}

TEST_CASE("workflow: status parsing and frame mapping (offset range, out-of-range frames)") {
  Json j = Json::parse(R"({"format": "plush.run_status", "version": 1, "run_id": "r1", "state": "done", "stage": "",
    "stages": ["prepare", "bake", "render"], "stages_done": ["prepare", "bake", "render"], "frames": [5, 7],
    "frames_done": 3, "frames_total": 3, "resolution": [320, 180], "samples": 16, "light_scale": 1.0,
    "exposure_ev": 0.4, "error": ""})");
  wf::RunStatus st = wf::parseStatus(j);
  CHECK(st.valid);
  CHECK(st.terminal());
  CHECK(st.frameA == 5);
  CHECK(st.frameB == 7);
  CHECK(st.width == 320);
  CHECK(st.height == 180);
  CHECK(st.samples == 16);
  CHECK(st.exposureEV == doctest::Approx(0.4));
  CHECK_FALSE(wf::parseStatus(Json::parse(R"({"format": "other"})")).valid);
  st.state = "running";
  CHECK_FALSE(st.terminal());

  fs::path d = tempDir("map");
  wf::RunInfo run{"r1", d / "r1", wf::parseStatus(j), true};
  writeFile(run.dir / "render/frame_0005.png", "x");
  writeFile(run.dir / "render/frame_0006.png", "x");
  for (int f : {1, 4, 8, 120}) {
    auto v = wf::mapFrame(run, f);
    CHECK_FALSE(v.inRange);
    CHECK_FALSE(v.available);
    CHECK(v.message == "not rendered in this run (run range 5-7)");
  }
  auto v5 = wf::mapFrame(run, 5);
  CHECK(v5.inRange);
  CHECK(v5.available);
  CHECK(v5.image == run.dir / "render/frame_0005.png");
  CHECK(wf::mapFrame(run, 6).image.filename() == "frame_0006.png");
  auto v7 = wf::mapFrame(run, 7);  // in range but missing on disk (e.g. cancelled)
  CHECK(v7.inRange);
  CHECK_FALSE(v7.available);
  CHECK(v7.message == "frame missing (run done)");
  wf::RunInfo prep = run;
  prep.status.stages = {"prepare"};
  CHECK(wf::mapFrame(prep, 5).message == "not rendered in this run (no render stage)");

  // run listing: newest first, latest pointer
  wf::ShotInfo shot = *wf::readShotInfo([&] {
    writeFile(d / "ep/shots/s/shot.scene.json", kMiniShot);
    return d / "ep/shots/s/shot.scene.json";
  }());
  for (std::string id : {"20260101-000000-000", "20260102-000000-000"}) {
    Json s = j;
    s["run_id"] = id;
    writeFile(shot.runsDir() / id / "status.json", s.dump());
  }
  writeFile(shot.runsDir() / "not-a-run/readme.txt", "x");
  writeFile(shot.runsDir() / "latest", "20260101-000000-000\n");
  auto runs = wf::listRuns(shot);
  REQUIRE(runs.size() == 2);
  CHECK(runs[0].id == "20260102-000000-000");
  CHECK_FALSE(runs[0].latest);
  CHECK(runs[1].latest);
  CHECK(wf::latestRunId(shot) == "20260101-000000-000");
  fs::remove_all(d);
}

TEST_CASE("workflow: merge-save keeps everything not explicitly edited (unknown fields at every depth)") {
  fs::path d = tempDir("merge");
  fs::path shotFile = d / "shot.scene.json";
  wf::OJson o = wf::OJson::parse(readFile(kRoot / "episodes/e000_pilot/shots/s010/shot.scene.json"));
  // unknown or unsupported keys at several depths
  o["x_top"] = {{"note", "kept"}, {"nested", {{"deep", {1, 2, {{"deeper", true}}}}}}};
  o["production"]["x_prod"] = {{"a", 1}};
  o["production"]["cast"]["girl"]["x_cast"] = "kept";
  o["production"]["render"]["x_render"] = 7;
  o["camera"]["x_cam"] = {{"rig", "dolly"}};
  o["render"]["x_engine_render"] = "kept";
  o["characters"][0]["x_char"] = {{"costume", {{"layer", 2}}}};
  o["characters"][1]["x_char"] = "kept";
  o["actions"][0]["x_action"] = {{"why", "kept"}};
  o["actions"][2]["x_action"] = 3;
  o["animation"]["camera.position"][0].push_back({{"x_key", "kept"}});    // 4th element of a key
  o["animation"]["camera.position"][1].push_back("x_key_tail");
  o["animation"]["x_unused.track"] = {{10, 0.5, "linear"}};                  // a track nothing uses
  o["lights"][0]["x_light"] = 1;
  o["objects"][0]["x_obj"] = {{"tag", "floor"}};
  o["materials"][0]["x_mat"] = 2;
  const std::string originalText = o.dump(1);
  writeFile(shotFile, originalText);
  const wf::OJson original = wf::OJson::parse(originalText);

  SUBCASE("unedited save: semantically identical, file not rewritten") {
    auto scene = loadScene(shotFile);
    REQUIRE(scene);
    CHECK(wf::mergeShotEdits(original, sceneToJson(*scene), sceneToJson(*scene)) == original);
    auto r = wf::mergeSaveShot(shotFile, *scene);
    REQUIRE(r);
    CHECK_FALSE(*r);
    CHECK(readFile(shotFile) == originalText);
  }
  SUBCASE("edits: only the allowed paths change") {
    auto scene = loadScene(shotFile);
    REQUIRE(scene);
    Scene& s = *scene;
    s.camera.focalMm = 50;                                                     // camera
    s.animation.tracks["camera.position"].setKey({120, vec3(0.2f, 0.8f, 1.8f), Interp::Smooth});  // edit a key
    s.animation.tracks["camera.position"].setKey({60, vec3(0.05f, 0.79f, 2.1f), Interp::Linear});  // insert a key
    s.animation.tracks["boy/head.rot"].setKey({30, vec3(0, 10, 0), Interp::Smooth});                // new track
    s.actions[1]["end"] = 35;                                                  // actions
    s.render.exposureEV = 0.6f;                                                // render settings
    s.frameEnd = 100;                                                          // frame range
    s.characters[0].position = vec3(-0.3f, 0, 0.05f);                          // placement
    s.characters[1].yawDeg = -20;
    s.characters[1].life.breathing = 0.5f;                                     // life
    s.characters[0].asset = "build/packages/should_not_be_saved/character.json";  // not an edit path
    s.name = "renamed";                                                        // not an edit path
    s.lights[0].intensity = 99;                                                // not an edit path
    auto r = wf::mergeSaveShot(shotFile, s);
    REQUIRE(r);
    CHECK(*r);
    wf::OJson m = wf::OJson::parse(readFile(shotFile));
    // edits applied
    CHECK(m["camera"]["focalMm"].get<double>() == doctest::Approx(50));
    CHECK(m["render"]["exposureEV"].get<double>() == doctest::Approx(0.6));
    CHECK(m["frameEnd"] == 100);
    CHECK(m["actions"][1]["end"] == 35);
    CHECK(m["characters"][0]["position"][2].get<double>() == doctest::Approx(0.05));
    CHECK(m["characters"][1]["yawDeg"].get<double>() == doctest::Approx(-20));
    CHECK(m["characters"][1]["life"]["breathing"].get<double>() == doctest::Approx(0.5));
    CHECK(m["animation"]["camera.position"].size() == 3);
    CHECK(m["animation"]["boy/head.rot"].size() == 1);
    // not-edit paths unchanged
    CHECK(m["name"] == original["name"]);
    CHECK(m["lights"] == original["lights"]);
    CHECK(m["characters"][0]["asset"] == original["characters"][0]["asset"]);
    CHECK(m["production"] == original["production"]);
    CHECK(m["objects"] == original["objects"]);
    CHECK(m["materials"] == original["materials"]);
    CHECK(m["frameStart"] == original["frameStart"]);
    CHECK(m["frameRate"] == original["frameRate"]);
    // unknown fields at every depth
    CHECK(m["x_top"] == original["x_top"]);
    CHECK(m["camera"]["x_cam"] == original["camera"]["x_cam"]);
    CHECK(m["render"]["x_engine_render"] == "kept");
    CHECK(m["characters"][0]["x_char"] == original["characters"][0]["x_char"]);
    CHECK(m["characters"][1]["x_char"] == "kept");
    CHECK(m["characters"][0]["life"] == original["characters"][0]["life"]);  // unedited life kept as written (true)
    CHECK(m["actions"][0] == original["actions"][0]);
    CHECK(m["actions"][2] == original["actions"][2]);
    CHECK(m["actions"][1]["start"] == original["actions"][1]["start"]);
    CHECK(m["animation"]["camera.position"][0] == original["animation"]["camera.position"][0]);  // key 1 untouched
    CHECK(m["animation"]["camera.position"][2].size() == 4);  // edited key 120 keeps its unknown tail
    CHECK(m["animation"]["camera.position"][2][3] == "x_key_tail");
    CHECK(m["animation"]["x_unused.track"] == original["animation"]["x_unused.track"]);
    // and the file still loads as a scene
    CHECK(loadScene(shotFile).has_value());
    // a second save of the reloaded file with no edits changes nothing
    std::string after = readFile(shotFile);
    auto again = loadScene(shotFile);
    REQUIRE(wf::mergeSaveShot(shotFile, *again));
    CHECK(readFile(shotFile) == after);
  }
  SUBCASE("removing a key or a track, disabling life") {
    auto scene = loadScene(shotFile);
    REQUIRE(scene);
    scene->animation.tracks["camera.position"].removeKey(120, 0.01);
    scene->characters[1].life.enabled = false;
    REQUIRE(wf::mergeSaveShot(shotFile, *scene));
    wf::OJson m = wf::OJson::parse(readFile(shotFile));
    CHECK(m["animation"]["camera.position"].size() == 1);
    CHECK(m["animation"]["camera.position"][0] == original["animation"]["camera.position"][0]);
    CHECK_FALSE(m["characters"][1].contains("life"));
    CHECK(m["characters"][1]["x_char"] == "kept");
  }
  fs::remove_all(d);
}

TEST_CASE("workflow: job runner on a dummy process tree (progress, cancel, no orphans)") {
  wf::becomeSubreaper();
  fs::path d = tempDir("job");
  SUBCASE("progress through status.json, normal exit") {
    std::string script = std::format(
        "for i in 1 2 3; do printf '{{\"format\":\"plush.run_status\",\"state\":\"%s\",\"frames\":[5,7],\"frames_done\":%d,"
        "\"frames_total\":3}}' $([ $i = 3 ] && echo done || echo running) $i > {0}/s.tmp && mv {0}/s.tmp {0}/status.json; "
        "sleep 0.3; done",
        d.string());
    wf::Job job;
    REQUIRE(job.start({"sh", "-c", script}, d / "job.log"));
    int maxSeen = 0, polls = 0;
    while (job.running()) {
      auto st = wf::readStatus(d / "status.json");
      if (st.valid) {
        CHECK(st.framesDone >= maxSeen);  // monotonic
        maxSeen = st.framesDone;
      }
      ++polls;
      std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    CHECK(job.exitCode() == 0);
    CHECK(polls > 5);  // the caller kept running while the job ran
    auto st = wf::readStatus(d / "status.json");
    CHECK(st.framesDone == 3);
    CHECK(st.state == "done");
  }
  SUBCASE("graceful cancel stops child and grandchildren") {
    wf::Job job;
    REQUIRE(job.start({"sh", "-c", "sleep 60 & sh -c 'sleep 61 & wait' & wait"}, d / "job.log"));
    std::vector<wf::ProcInfo> before;
    for (int i = 0; i < 100 && before.size() < 4; ++i) {
      std::this_thread::sleep_for(std::chrono::milliseconds(20));
      before = wf::processGroupMembers(job.pgid());
    }
    CHECK(before.size() == 4);  // sh, sleep 60, sh, sleep 61
    auto r = job.cancel(5.0);
    CHECK(r.wasRunning);
    CHECK(r.graceful);
    CHECK_FALSE(r.forced);
    CHECK(r.groupGone);
    CHECK(wf::processGroupMembers(job.pgid()).empty());
    for (auto& p : before) CHECK(::kill(p.pid, 0) != 0);  // no orphan, no zombie
    CHECK_FALSE(job.running());
  }
  SUBCASE("forced cancel when the tree ignores SIGTERM") {
    wf::Job job;
    REQUIRE(job.start({"sh", "-c", "trap '' TERM; sleep 60 & sleep 61 & wait"}, d / "job.log"));
    std::vector<wf::ProcInfo> before;
    for (int i = 0; i < 100 && before.size() < 3; ++i) {
      std::this_thread::sleep_for(std::chrono::milliseconds(20));
      before = wf::processGroupMembers(job.pgid());
    }
    CHECK(before.size() == 3);
    auto r = job.cancel(0.5);
    CHECK(r.wasRunning);
    CHECK_FALSE(r.graceful);
    CHECK(r.forced);
    CHECK(r.groupGone);
    for (auto& p : before) CHECK(::kill(p.pid, 0) != 0);
  }
  SUBCASE("tail of a log") {
    writeFile(d / "t.log", "a\nb\nc\nd\n");
    CHECK(wf::tailFile(d / "t.log", 2) == "c\nd\n");
    CHECK(wf::tailFile(d / "missing.log", 2).empty());
  }
  fs::remove_all(d);
}
