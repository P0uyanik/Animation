#pragma once
// Plush Studio production workflow (T-001): the non-UI half of the Production panel. Studio orchestrates and
// displays; it never animates, bakes, retargets or renders. All production work is done by the one workflow
// contract, pipeline/production/run_shot.py (stages prepare, bake, render, encode; per-run folders; status.json),
// which the command line uses as well. This module:
//   - discovers shots (every episodes/*/shots/*/shot.scene.json) - no shot, episode or character names in code;
//   - builds run_shot.py command lines and runs them as jobs (own process group; cancel = SIGTERM to the group,
//     then SIGKILL after a timeout; no orphans);
//   - reads status.json, lists runs, maps timeline frames to a run's rendered frames;
//   - saves edits by merging them into the source shot file (only an explicit list of edit paths may change).
// No OpenGL, no ImGui: unit-tested in tests/test_shot_workflow.cpp.
#include <sys/types.h>

#include <filesystem>
#include <optional>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "scene/scene.h"

namespace plush::workflow {

namespace fs = std::filesystem;
using OJson = nlohmann::ordered_json;  // keeps a file's key order on save

// ------------------------------------------------------------------ configuration
struct Config {
  fs::path root;            // repository root (shots live in <root>/episodes)
  fs::path python = "python3";
  fs::path runShot;         // <root>/pipeline/production/run_shot.py
  fs::path engine;          // plush-render (from the build configuration)
  std::string blender;      // Blender executable
  std::string blenderSource;  // "--blender", "PLUSH_BLENDER", "settings file <path>" or "" (not configured)
};
// Settings file: $PLUSH_STUDIO_SETTINGS, else $HOME/.config/plush-studio/settings.json ({"blender": "..."}).
fs::path settingsFilePath();
// Blender precedence: the --blender argument, the PLUSH_BLENDER environment variable, the settings file.
Config makeConfig(const fs::path& root, const fs::path& engine, const std::string& blenderArg);

// ------------------------------------------------------------------ shot discovery
struct CastMember {
  std::string name;        // character name in the scene
  std::string sourceKind;  // "published" (version_dir), "spec" (unpublished build) or "missing"
  std::string source;      // the version_dir or spec path as written in the shot
};
struct ShotInfo {
  fs::path path;           // .../episodes/<episode>/shots/<shot>/shot.scene.json
  std::string episode, shot, name;
  int frameStart = 1, frameEnd = 48;
  std::vector<CastMember> cast;
  bool hasProduction = false;
  int width = 0, height = 0, samples = 32;  // production.render defaults (0 = the scene's own render size)
  double lightScale = 1.0;
  fs::path buildDir() const { return path.parent_path() / "build"; }
  fs::path runsDir() const { return buildDir() / "runs"; }
  fs::path resolvedScene() const { return buildDir() / "shot.resolved.scene.json"; }
};
Result<ShotInfo> readShotInfo(const fs::path& shotFile);
std::vector<ShotInfo> discoverShots(const fs::path& root);

// Prepared = the resolved scene exists, every package it names exists, and it equals the source shot apart from
// the production block and the resolved asset paths (so edits saved since the last prepare are detected).
bool isPrepared(const ShotInfo& shot);
// prepare.json of the shot's build folder (null if missing).
Json readPrepareReport(const ShotInfo& shot);

// ------------------------------------------------------------------ jobs and runs
struct RunSettings {
  std::vector<std::string> stages{"prepare", "bake", "render", "encode"};
  int frameA = 1, frameB = 1;
  int width = 0, height = 0;  // 0 = shot default
  int samples = 0;            // 0 = shot default
};
std::string newRunId();  // time-based, sortable (YYYYMMDD-HHMMSS-mmm)
std::vector<std::string> buildCommand(const Config& cfg, const ShotInfo& shot, const std::string& runId, const RunSettings& s);
std::vector<std::string> markCancelledCommand(const Config& cfg, const ShotInfo& shot, const std::string& runId);

struct RunStatus {
  bool valid = false;
  std::string runId, state, stage, error, started;  // state: running / done / failed / cancelled
  std::vector<std::string> stages, stagesDone;
  int frameA = 0, frameB = -1, framesDone = 0, framesTotal = 0;
  int width = 0, height = 0, samples = 0;
  double lightScale = 1.0, exposureEV = 0.0;
  bool terminal() const { return state == "done" || state == "failed" || state == "cancelled"; }
};
RunStatus parseStatus(const Json& j);
RunStatus readStatus(const fs::path& statusFile);

struct RunInfo {
  std::string id;
  fs::path dir;
  RunStatus status;
  bool latest = false;
};
// Runs of a shot, newest first (folders of <build>/runs that hold a status.json); `latest` marks the pointer.
std::vector<RunInfo> listRuns(const ShotInfo& shot);
std::string latestRunId(const ShotInfo& shot);

// The image a run holds for a timeline frame: only frames inside the run's range map to its files
// (frame_####.png carries the shot's own frame number).
struct FrameView {
  bool inRange = false, available = false;
  fs::path image;
  std::string message;  // shown instead of an image
};
FrameView mapFrame(const RunInfo& run, int frame);

// A child process in its own process group (run_shot.py and everything it starts: Blender, ffmpeg ...).
class Job {
 public:
  Job() = default;
  Job(const Job&) = delete;
  Job& operator=(const Job&) = delete;
  ~Job();
  // Starts argv; stdout and stderr go to `logFile` (appended).
  Result<void> start(const std::vector<std::string>& argv, const fs::path& logFile);
  bool running();                 // non-blocking (reaps the child when it has exited)
  int exitCode() const { return exitCode_; }
  pid_t pid() const { return pid_; }
  pid_t pgid() const { return pgid_; }
  struct CancelResult {
    bool wasRunning = false, graceful = false, forced = false, groupGone = false;
    double seconds = 0;
  };
  // SIGTERM to the whole group, SIGKILL after `graceSeconds`; waits until no process of the group is left.
  CancelResult cancel(double graceSeconds = 8.0);
  bool waitFor(double seconds);  // waits for the child to exit
 private:
  void reapGroup();
  pid_t pid_ = -1, pgid_ = -1;
  int exitCode_ = -1;
  bool exited_ = true;
};
// Processes currently in a process group (from /proc): pid and command line. Used for orphan checks.
struct ProcInfo {
  pid_t pid;
  std::string cmd;
};
std::vector<ProcInfo> processGroupMembers(pid_t pgid);
// Makes this process the reaper of its orphaned descendants (Linux), so a cancelled job leaves no zombies.
void becomeSubreaper();

// Last `lines` lines of a text file ("" if missing).
std::string tailFile(const fs::path& file, int lines);

// ------------------------------------------------------------------ safe save
// Edit paths that may change on save (everything else in the file is kept exactly as read, at every depth):
//   camera, animation (tracks / keys), actions, render, frameStart, frameEnd, characters[*].{position, yawDeg, life}.
// `original` is the file as read; `before` is sceneToJson(loadScene(file)) (the engine's view of the file);
// `edited` is sceneToJson(the edited scene). Only differences between `before` and `edited` are applied to
// `original`, as minimal patches, so unknown keys and untouched values keep their exact form.
OJson mergeShotEdits(const OJson& original, const Json& before, const Json& edited);
// Reads `shotFile`, merges the edits of `edited` and writes it back (only if something changed).
// Returns whether the file was written.
Result<bool> mergeSaveShot(const fs::path& shotFile, const Scene& edited);

}  // namespace plush::workflow
