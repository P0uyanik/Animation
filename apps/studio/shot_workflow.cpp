#include "shot_workflow.h"

#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <map>
#include <sstream>
#include <thread>

#include "geom/json_io.h"

namespace plush::workflow {

namespace {
Json readJson(const fs::path& p) {
  std::ifstream f(p);
  if (!f) return nullptr;
  Json j = Json::parse(f, nullptr, false);
  return j.is_discarded() ? Json(nullptr) : j;
}
double now() {
  return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
}  // namespace

// ------------------------------------------------------------------ configuration
fs::path settingsFilePath() {
  if (const char* p = std::getenv("PLUSH_STUDIO_SETTINGS"); p && *p) return p;
  const char* home = std::getenv("HOME");
  return fs::path(home ? home : ".") / ".config" / "plush-studio" / "settings.json";
}

Config makeConfig(const fs::path& root, const fs::path& engine, const std::string& blenderArg) {
  Config c;
  c.root = root;
  c.runShot = root / "pipeline" / "production" / "run_shot.py";
  c.engine = engine;
  if (!blenderArg.empty()) {
    c.blender = blenderArg;
    c.blenderSource = "--blender";
  } else if (const char* e = std::getenv("PLUSH_BLENDER"); e && *e) {
    c.blender = e;
    c.blenderSource = "PLUSH_BLENDER";
  } else {
    fs::path sf = settingsFilePath();
    Json j = readJson(sf);
    if (j.is_object() && j.contains("blender") && j["blender"].is_string()) {
      c.blender = j["blender"].get<std::string>();
      c.blenderSource = "settings file " + sf.string();
    }
  }
  return c;
}

// ------------------------------------------------------------------ shot discovery
Result<ShotInfo> readShotInfo(const fs::path& shotFile) {
  Json j = readJson(shotFile);
  if (!j.is_object()) return fail(shotFile.string() + ": not a JSON object");
  if (j.value("format", "") != "plush.scene") return fail(shotFile.string() + ": not a plush.scene file");
  ShotInfo s;
  s.path = fs::absolute(shotFile).lexically_normal();
  s.shot = s.path.parent_path().filename().string();
  s.episode = s.path.parent_path().parent_path().parent_path().filename().string();
  s.name = j.value("name", s.shot);
  s.frameStart = j.value("frameStart", 1);
  s.frameEnd = j.value("frameEnd", 48);
  const Json& prod = j.contains("production") && j["production"].is_object() ? j["production"] : Json::object();
  s.hasProduction = !prod.empty();
  const Json cast = prod.value("cast", Json::object());
  for (const Json& c : j.value("characters", Json::array())) {
    CastMember m{c.value("name", ""), "missing", ""};
    if (cast.contains(m.name)) {
      const Json& src = cast[m.name];
      if (src.contains("version_dir")) m.sourceKind = "published", m.source = src["version_dir"].get<std::string>();
      else if (src.contains("spec")) m.sourceKind = "spec", m.source = src["spec"].get<std::string>();
    }
    s.cast.push_back(m);
  }
  const Json r = prod.value("render", Json::object());
  if (r.contains("resolution") && r["resolution"].is_array() && r["resolution"].size() == 2)
    s.width = r["resolution"][0].get<int>(), s.height = r["resolution"][1].get<int>();
  s.samples = r.value("samples", 32);
  s.lightScale = r.value("light_scale", 1.0);
  return s;
}

std::vector<ShotInfo> discoverShots(const fs::path& root) {
  std::vector<ShotInfo> out;
  std::error_code ec;
  fs::path eps = root / "episodes";
  if (!fs::is_directory(eps, ec)) return out;
  for (const auto& ep : fs::directory_iterator(eps, ec)) {
    fs::path shots = ep.path() / "shots";
    if (!fs::is_directory(shots, ec)) continue;
    for (const auto& sh : fs::directory_iterator(shots, ec)) {
      fs::path f = sh.path() / "shot.scene.json";
      if (!fs::is_regular_file(f, ec)) continue;
      if (auto info = readShotInfo(f)) out.push_back(*info);
    }
  }
  std::sort(out.begin(), out.end(), [](const ShotInfo& a, const ShotInfo& b) { return a.path < b.path; });
  return out;
}

bool isPrepared(const ShotInfo& shot) {
  Json src = readJson(shot.path), res = readJson(shot.resolvedScene());
  if (!src.is_object() || !res.is_object()) return false;
  src.erase("production");
  if (!res.contains("characters") || !src.contains("characters") || res["characters"].size() != src["characters"].size()) return false;
  for (size_t i = 0; i < res["characters"].size(); ++i) {
    fs::path pkg = shot.buildDir() / res["characters"][i].value("asset", "");
    if (!fs::exists(pkg)) return false;
    res["characters"][i]["asset"] = "";
    src["characters"][i]["asset"] = "";
  }
  return src == res;
}

Json readPrepareReport(const ShotInfo& shot) { return readJson(shot.buildDir() / "prepare.json"); }

// ------------------------------------------------------------------ jobs and runs
std::string newRunId() {
  auto t = std::chrono::system_clock::now();
  std::time_t tt = std::chrono::system_clock::to_time_t(t);
  std::tm tm{};
  localtime_r(&tt, &tm);
  int ms = int(std::chrono::duration_cast<std::chrono::milliseconds>(t.time_since_epoch()).count() % 1000);
  char buf[64];
  std::snprintf(buf, sizeof buf, "%04d%02d%02d-%02d%02d%02d-%03d", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour,
                tm.tm_min, tm.tm_sec, ms);
  return buf;
}

std::vector<std::string> buildCommand(const Config& cfg, const ShotInfo& shot, const std::string& runId, const RunSettings& s) {
  std::vector<std::string> cmd{cfg.python.string(), cfg.runShot.string(), "--shot", shot.path.string(), "--blender", cfg.blender};
  if (!cfg.engine.empty()) cmd.insert(cmd.end(), {"--engine", cfg.engine.string()});
  cmd.insert(cmd.end(), {"--run-dir", runId});
  std::string st;
  for (const auto& x : s.stages) st += (st.empty() ? "" : ",") + x;
  cmd.insert(cmd.end(), {"--stages", st});
  cmd.insert(cmd.end(), {"--frames", std::to_string(s.frameA) + "-" + std::to_string(s.frameB)});
  if (s.width > 0 && s.height > 0) cmd.insert(cmd.end(), {"--resolution", std::to_string(s.width), std::to_string(s.height)});
  if (s.samples > 0) cmd.insert(cmd.end(), {"--samples", std::to_string(s.samples)});
  return cmd;
}

std::vector<std::string> markCancelledCommand(const Config& cfg, const ShotInfo& shot, const std::string& runId) {
  return {cfg.python.string(), cfg.runShot.string(), "--shot", shot.path.string(), "--run-dir", runId, "--mark-cancelled"};
}

RunStatus parseStatus(const Json& j) {
  RunStatus s;
  if (!j.is_object() || j.value("format", "") != "plush.run_status") return s;
  s.valid = true;
  s.runId = j.value("run_id", "");
  s.state = j.value("state", "");
  s.stage = j.value("stage", "");
  s.error = j.value("error", "");
  s.started = j.value("started", "");
  for (auto& x : j.value("stages", Json::array())) s.stages.push_back(x.get<std::string>());
  for (auto& x : j.value("stages_done", Json::array())) s.stagesDone.push_back(x.get<std::string>());
  if (auto f = j.value("frames", Json::array()); f.size() == 2) s.frameA = f[0].get<int>(), s.frameB = f[1].get<int>();
  s.framesDone = j.value("frames_done", 0);
  s.framesTotal = j.value("frames_total", 0);
  if (auto r = j.value("resolution", Json::array()); r.size() == 2) s.width = r[0].get<int>(), s.height = r[1].get<int>();
  s.samples = j.value("samples", 0);
  s.lightScale = j.value("light_scale", 1.0);
  s.exposureEV = j.value("exposure_ev", 0.0);
  return s;
}

RunStatus readStatus(const fs::path& statusFile) { return parseStatus(readJson(statusFile)); }

std::string latestRunId(const ShotInfo& shot) {
  std::ifstream f(shot.runsDir() / "latest");
  std::string id;
  std::getline(f, id);
  return id;
}

std::vector<RunInfo> listRuns(const ShotInfo& shot) {
  std::vector<RunInfo> out;
  std::error_code ec;
  if (!fs::is_directory(shot.runsDir(), ec)) return out;
  std::string latest = latestRunId(shot);
  for (const auto& d : fs::directory_iterator(shot.runsDir(), ec)) {
    if (!d.is_directory() || !fs::exists(d.path() / "status.json")) continue;
    RunInfo r{d.path().filename().string(), d.path(), readStatus(d.path() / "status.json"), false};
    r.latest = r.id == latest;
    out.push_back(r);
  }
  std::sort(out.begin(), out.end(), [](const RunInfo& a, const RunInfo& b) {  // newest first: start time, then id
    return a.status.started != b.status.started ? a.status.started > b.status.started : a.id > b.id;
  });
  return out;
}

FrameView mapFrame(const RunInfo& run, int frame) {
  FrameView v;
  const RunStatus& s = run.status;
  bool rendersFrames = std::find(s.stages.begin(), s.stages.end(), "render") != s.stages.end();
  v.inRange = rendersFrames && frame >= s.frameA && frame <= s.frameB;
  if (!v.inRange) {
    v.message = rendersFrames ? std::format("not rendered in this run (run range {}-{})", s.frameA, s.frameB)
                              : "not rendered in this run (no render stage)";
    return v;
  }
  v.image = run.dir / "render" / std::format("frame_{:04d}.png", frame);
  v.available = fs::exists(v.image);
  if (!v.available) v.message = s.state == "running" ? "frame not rendered yet" : std::format("frame missing (run {})", s.state);
  return v;
}

Job::~Job() {
  if (!exited_) cancel(2.0);
}

Result<void> Job::start(const std::vector<std::string>& argv, const fs::path& logFile) {
  if (!exited_) return fail("a job is already running");
  if (argv.empty()) return fail("empty command");
  std::error_code ec;
  if (!logFile.parent_path().empty()) fs::create_directories(logFile.parent_path(), ec);
  int fd = ::open(logFile.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
  if (fd < 0) return fail("cannot open " + logFile.string());
  std::vector<char*> args;
  for (const auto& a : argv) args.push_back(const_cast<char*>(a.c_str()));
  args.push_back(nullptr);
  pid_t pid = ::fork();
  if (pid < 0) {
    ::close(fd);
    return fail("fork failed");
  }
  if (pid == 0) {  // child: own process group, output to the log
    ::setpgid(0, 0);
    ::dup2(fd, 1);
    ::dup2(fd, 2);
    int devnull = ::open("/dev/null", O_RDONLY);
    if (devnull >= 0) ::dup2(devnull, 0);
    ::execvp(args[0], args.data());
    std::fprintf(stderr, "exec failed: %s\n", args[0]);
    ::_exit(127);
  }
  ::setpgid(pid, pid);  // also in the parent (no race with an early cancel)
  ::close(fd);
  pid_ = pid;
  pgid_ = pid;
  exited_ = false;
  exitCode_ = -1;
  return {};
}

void Job::reapGroup() {
  // Orphaned descendants of the job are re-parented to us (subreaper): reap them so none stays a zombie.
  if (pgid_ > 0)
    while (::waitpid(-pgid_, nullptr, WNOHANG) > 0) {
    }
}

bool Job::running() {
  if (exited_) return false;
  int st = 0;
  pid_t r = ::waitpid(pid_, &st, WNOHANG);
  if (r == pid_) {
    exited_ = true;
    exitCode_ = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
    reapGroup();
    return false;
  }
  return true;
}

bool Job::waitFor(double seconds) {
  double t0 = now();
  while (running()) {
    if (now() - t0 > seconds) return false;
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  return true;
}

Job::CancelResult Job::cancel(double graceSeconds) {
  CancelResult r;
  double t0 = now();
  r.wasRunning = running() || !processGroupMembers(pgid_).empty();
  if (pgid_ <= 0) return r;
  auto groupAlive = [&] {
    running();
    reapGroup();
    return ::kill(-pgid_, 0) == 0 && !processGroupMembers(pgid_).empty();
  };
  ::kill(-pgid_, SIGTERM);
  while (groupAlive() && now() - t0 < graceSeconds) std::this_thread::sleep_for(std::chrono::milliseconds(25));
  r.graceful = !groupAlive();
  if (!r.graceful) {
    ::kill(-pgid_, SIGKILL);
    r.forced = true;
    double t1 = now();
    while (groupAlive() && now() - t1 < 10.0) std::this_thread::sleep_for(std::chrono::milliseconds(25));
  }
  if (!exited_) waitFor(5.0);
  r.groupGone = !groupAlive();
  r.seconds = now() - t0;
  return r;
}

std::vector<ProcInfo> processGroupMembers(pid_t pgid) {
  std::vector<ProcInfo> out;
  if (pgid <= 0) return out;
  std::error_code ec;
  for (const auto& d : fs::directory_iterator("/proc", ec)) {
    const std::string n = d.path().filename().string();
    if (n.empty() || !std::all_of(n.begin(), n.end(), ::isdigit)) continue;
    std::ifstream sf(d.path() / "stat");
    std::string stat((std::istreambuf_iterator<char>(sf)), std::istreambuf_iterator<char>());
    size_t rp = stat.rfind(')');
    if (rp == std::string::npos) continue;
    std::istringstream rest(stat.substr(rp + 2));
    char state = 0;
    long ppid = 0, pg = 0;
    rest >> state >> ppid >> pg;
    if (pg != pgid || state == 'Z') continue;  // zombies are dead (only waiting to be reaped)
    std::ifstream cf(d.path() / "cmdline");
    std::string cmd((std::istreambuf_iterator<char>(cf)), std::istreambuf_iterator<char>());
    std::replace(cmd.begin(), cmd.end(), '\0', ' ');
    out.push_back({pid_t(std::stol(n)), cmd});
  }
  return out;
}

void becomeSubreaper() {
#ifdef __linux__
  ::prctl(PR_SET_CHILD_SUBREAPER, 1);
#endif
}

std::string tailFile(const fs::path& file, int lines) {
  std::ifstream f(file, std::ios::binary);
  if (!f) return "";
  f.seekg(0, std::ios::end);
  std::streamoff size = f.tellg(), from = std::max<std::streamoff>(0, size - 16384);
  f.seekg(from);
  std::string text((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
  size_t pos = text.size();
  for (int n = 0; n <= lines && pos != std::string::npos && pos > 0; ++n) pos = text.rfind('\n', pos - 1);
  return pos == std::string::npos || pos == 0 ? text : text.substr(pos + 1);
}

// ------------------------------------------------------------------ safe save
namespace {
OJson toO(const Json& j) { return OJson::parse(j.dump()); }

// Applies the change a -> b to `orig` (which a was read from): equal values keep their original form; objects and
// equal-length arrays are patched member by member, so keys unknown to the engine survive at every depth.
OJson patch(const OJson& orig, const OJson& a, const OJson& b) {
  if (a == b) return orig;
  if (a.is_object() && b.is_object() && orig.is_object()) {
    OJson res = orig;
    for (auto it = b.begin(); it != b.end(); ++it) {
      if (a.contains(it.key())) res[it.key()] = patch(orig.contains(it.key()) ? orig[it.key()] : a[it.key()], a[it.key()], it.value());
      else res[it.key()] = it.value();
    }
    for (auto it = a.begin(); it != a.end(); ++it)
      if (!b.contains(it.key())) res.erase(it.key());
    return res;
  }
  if (a.is_array() && b.is_array() && orig.is_array() && a.size() == b.size() && orig.size() >= a.size()) {
    OJson res = orig;
    for (size_t i = 0; i < a.size(); ++i) res[i] = patch(orig[i], a[i], b[i]);
    return res;
  }
  return b;
}

// One key of an object: added, removed or patched.
void patchKey(OJson& obj, const std::string& k, const OJson& a, const OJson& b) {
  bool inA = a.is_object() && a.contains(k), inB = b.is_object() && b.contains(k);
  if (inA && inB) obj[k] = patch(obj.contains(k) ? obj[k] : a[k], a[k], b[k]);
  else if (inB) obj[k] = b[k];
  else if (inA) obj.erase(k);
}

// Animation tracks: keys are matched by frame, so editing or inserting one key keeps the others as written.
OJson patchTrack(const OJson& orig, const OJson& a, const OJson& b) {
  if (a == b) return orig;
  auto frameOf = [](const OJson& k) { return k.is_array() && !k.empty() && k[0].is_number() ? k[0].get<double>() : -1e300; };
  auto find = [&](const OJson& keys, double f) -> const OJson* {
    if (keys.is_array())
      for (const auto& k : keys)
        if (std::abs(frameOf(k) - f) < 1e-9) return &k;
    return nullptr;
  };
  OJson res = OJson::array();
  for (const auto& kb : b) {
    const OJson* ka = find(a, frameOf(kb));
    const OJson* ko = find(orig, frameOf(kb));
    res.push_back(ka && ko ? patch(*ko, *ka, kb) : kb);
  }
  return res;
}
}  // namespace

OJson mergeShotEdits(const OJson& original, const Json& beforeJ, const Json& editedJ) {
  const OJson before = toO(beforeJ), edited = toO(editedJ);
  OJson out = original;
  for (const char* k : {"camera", "render", "frameStart", "frameEnd", "actions"}) patchKey(out, k, before, edited);
  // animation: per track
  {
    const OJson a = before.value("animation", OJson::object()), b = edited.value("animation", OJson::object());
    if (a != b) {
      OJson anim = out.contains("animation") && out["animation"].is_object() ? out["animation"] : OJson::object();
      for (auto it = b.begin(); it != b.end(); ++it) {
        if (a.contains(it.key())) anim[it.key()] = patchTrack(anim.contains(it.key()) ? anim[it.key()] : a[it.key()], a[it.key()], it.value());
        else anim[it.key()] = it.value();
      }
      for (auto it = a.begin(); it != a.end(); ++it)
        if (!b.contains(it.key())) anim.erase(it.key());
      out["animation"] = anim;
    }
  }
  // characters: matched by name; only placement and life
  if (out.contains("characters") && out["characters"].is_array() && before.contains("characters") && edited.contains("characters")) {
    auto byName = [](const OJson& list, const std::string& n) -> const OJson* {
      for (const auto& c : list)
        if (c.value("name", "") == n) return &c;
      return nullptr;
    };
    for (auto& c : out["characters"]) {
      const std::string n = c.value("name", "");
      const OJson *a = byName(before["characters"], n), *b = byName(edited["characters"], n);
      if (!a || !b) continue;
      for (const char* k : {"position", "yawDeg", "life"}) patchKey(c, k, *a, *b);
    }
  }
  return out;
}

Result<bool> mergeSaveShot(const fs::path& shotFile, const Scene& edited) {
  auto text = readTextFile(shotFile);
  if (!text) return std::unexpected(text.error());
  OJson original = OJson::parse(*text, nullptr, false);
  if (original.is_discarded()) return fail(shotFile.string() + ": invalid JSON");
  auto before = loadScene(shotFile);
  if (!before) return std::unexpected(before.error());
  OJson merged = mergeShotEdits(original, sceneToJson(*before), sceneToJson(edited));
  if (merged == original) return false;
  if (auto r = writeTextFile(shotFile, merged.dump(1) + "\n"); !r) return std::unexpected(r.error());
  return true;
}

}  // namespace plush::workflow
