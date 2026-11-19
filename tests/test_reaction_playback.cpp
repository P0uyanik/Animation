// T-097D: reactions in playback. A scene's opt-in "events" are planned per character (scene/reaction.h) and played as
// generated actions: a look at the source after the notice delay (gaze habit: held, then back), a blended emotion
// (T-097A) and the chosen gesture. Tests: the reaction is delayed and blended, the generated actions are deterministic,
// animcheck's acting rule (T-097C) sees the delay, and a scene without events plays as before.
#include <doctest/doctest.h>

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <fstream>

#include "geom/json_io.h"
#include "scene/reaction.h"
#include "scene/scene.h"

using namespace plush;

namespace {
const std::filesystem::path kSrc = PLUSH_SOURCE_DIR;

// Two characters with personality profiles (read from content/personality, nothing tuned here) and a ball.
Scene reactionScene(const Json& events) {
  Scene s;
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 96;
  s.path = kSrc / "tests/data/imported/scene.json";
  const char* names[] = {"girl", "boy"};
  const char* packages[] = {"girl_auburn_bun_glasses_m3/character.json", "boy_yellow_hoodie_1.0.0/character.json"};
  const char* profiles[] = {"girl_auburn_bun_glasses", "boy_yellow_hoodie"};
  for (int i = 0; i < 2; ++i) {
    CharacterDesc cd;
    cd.name = names[i];
    cd.asset = packages[i];
    cd.position = vec3(i == 0 ? -0.3f : 0.3f, 0, 0);
    cd.yawDeg = i == 0 ? 60.f : -60.f;
    cd.life.enabled = true;
    cd.personality = profiles[i];
    s.characters.push_back(cd);
  }
  ObjectDesc ball;
  ball.name = "ball";
  ball.boxMin = vec3(-0.04f);
  ball.boxMax = vec3(0.04f);
  ball.position = vec3(0, 0.3f, 0.5f);
  s.objects.push_back(ball);
  s.actions = Json::array();
  s.events = events;
  return s;
}

std::unique_ptr<SceneEvaluator> load(const Scene& s) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE_MESSAGE(r.has_value(), (r ? "" : r.error().message));
  return ev;
}

const Json kEvents = Json::parse(R"([
  {"time": 1.0, "kind": "object_appears", "name": "ball appears", "source": "ball"},
  {"time": 2.5, "kind": "partner_acts", "name": "boy waves", "source": "boy", "salience": 0.6}
])");

std::vector<Json> generated(const SceneEvaluator& ev, const std::string& who, const std::string& type) {
  std::vector<Json> out;
  for (const Json& a : ev.reactionActions())
    if (a.value("character", "") == who && a.value("type", "") == type) out.push_back(a);
  return out;
}

double bodyDiff(const SceneEvaluator& a, const SceneEvaluator& b, size_t c, double f) {
  auto ga = a.characterGlobals(c, f), gb = b.characterGlobals(c, f);
  double d = 0;
  for (size_t i = 0; i < ga.size(); ++i) d = std::max(d, double(glm::length(vec3(ga[i][3]) - vec3(gb[i][3]))));
  return d;
}
}  // namespace

TEST_CASE("scene events: parsing, validation and save round trip") {
  auto ok = reactionEventsFromJson(kEvents);
  REQUIRE(ok.has_value());
  REQUIRE(ok->size() == 2);
  CHECK((*ok)[0].event.kind == ReactionEvent::Kind::ObjectAppears);
  CHECK((*ok)[1].event.salience == doctest::Approx(0.6));
  CHECK(reactionEventsFromJson(Json()).value().empty());
  CHECK_FALSE(reactionEventsFromJson(Json::parse(R"({"time": 1})")).has_value());
  CHECK_FALSE(reactionEventsFromJson(Json::parse(R"([{"time": 1, "kind": "explodes"}])")).has_value());
  CHECK_FALSE(reactionEventsFromJson(Json::parse(R"([{"time": -1, "kind": "success"}])")).has_value());
  CHECK_FALSE(reactionEventsFromJson(Json::parse(R"([{"time": 1, "kind": "custom"}])")).has_value());  // needs a name
  CHECK_FALSE(reactionEventsFromJson(Json::parse(R"([{"time": 1, "kind": "success", "salience": 2}])")).has_value());
  Scene s = reactionScene(kEvents);
  CHECK(sceneToJson(s)["events"] == kEvents);
  s.events = nullptr;
  CHECK_FALSE(sceneToJson(s).contains("events"));
}

TEST_CASE("an event triggers a delayed, blended reaction (look, emotion, gesture) per character") {
  auto ev = load(reactionScene(kEvents));
  auto plain = load(reactionScene(nullptr));
  CHECK(plain->reactionActions().empty());
  // The planned notice delays (personality profiles) decide where the generated actions start.
  ReactionEvent appear{ReactionEvent::Kind::ObjectAppears, "ball appears", "ball", 1.0, 1.f};
  for (size_t c = 0; c < 2; ++c) {
    const std::string who = ev->scene().characters[c].name;
    const ReactionPlan plan = planReaction(appear, ev->personality(c));
    REQUIRE(ev->personality(c));
    REQUIRE(plan.noticeDelay > 0);
    const double start = 1 + reactionStart(appear, plan) * 24;
    auto looks = generated(*ev, who, "look");
    auto emotions = generated(*ev, who, "emotion");
    REQUIRE(!looks.empty());
    REQUIRE(!emotions.empty());
    CHECK(looks[0]["start"].get<double>() == doctest::Approx(start));
    CHECK(looks[0]["object"] == "ball");
    CHECK(emotions[0]["start"].get<double>() == doctest::Approx(start));
    CHECK(emotions[0]["name"] == plan.target.weights.front().first);
    CHECK(emotions[0]["blend"] == true);
    CHECK(emotions[0]["intensity"].get<double>() == doctest::Approx(plan.target.weights.front().second));
    // Delayed: nothing differs from the scene without events before the reaction starts; afterwards the body moves.
    // Blended: the change ramps in (small one frame in, larger once the emotion has risen).
    const double before = bodyDiff(*ev, *plain, c, std::floor(start) - 1);
    const double in1 = bodyDiff(*ev, *plain, c, std::ceil(start) + 1), later = bodyDiff(*ev, *plain, c, start + 14);
    MESSAGE(who << ": delay " << plan.noticeDelay * 24 << " f, reaction at f" << start << ", body diff before " << before
                << " m, +1 f " << in1 << " m, +14 f " << later << " m");
    double step = 0;  // no pop: the largest change of the difference from one frame to the next
    for (int k = 0; k < 24; ++k)
      step = std::max(step, std::abs(bodyDiff(*ev, *plain, c, std::floor(start) + k + 1) - bodyDiff(*ev, *plain, c, std::floor(start) + k)));
    MESSAGE(who << ": largest per-frame step of the difference " << step << " m");
    CHECK(before < 1e-6);
    CHECK(later > 2e-3);
    CHECK(in1 < 0.5 * later);
    CHECK(step < 0.4 * later);  // spread over several frames (a snap would be ~1 x later in one frame)
    // Gaze habit: the look is held for gazeShift of the reaction (at least 3 frames), then the gaze goes back.
    CHECK(looks[0]["end"].get<double>() == doctest::Approx(start + std::max(3.0, plan.modulation.gazeShift * plan.duration * 24)));
    CHECK(looks[0]["back"] == true);
  }
  // A partner's action: the actor does not react to itself; the partner looks at the actor.
  CHECK(generated(*ev, "girl", "look").size() == 2);
  CHECK(generated(*ev, "girl", "look")[1]["atCharacter"] == "boy");
  CHECK(generated(*ev, "boy", "look").size() == 1);
}

TEST_CASE("reaction playback is deterministic: same actions for the same events in any list order") {
  auto a = load(reactionScene(kEvents));
  auto b = load(reactionScene(kEvents));
  Json reversed = Json::array({kEvents[1], kEvents[0]});
  auto c = load(reactionScene(reversed));
  CHECK(a->reactionActions() == b->reactionActions());
  CHECK(a->reactionActions() == c->reactionActions());
  // Event order, then scene character order; per reaction: look, emotion, gesture.
  std::vector<std::string> order;
  for (const Json& x : a->reactionActions()) order.push_back(x.value("character", "") + ":" + x.value("type", ""));
  CHECK(order == std::vector<std::string>{"girl:look", "girl:emotion", "boy:look", "boy:emotion", "girl:look", "girl:emotion"});
  for (double f : {20.0, 37.5, 60.0}) CHECK(bodyDiff(*a, *c, 0, f) == 0.0);
  // "characters" restricts who reacts.
  Json only = kEvents;
  only[0]["characters"] = Json::array({"boy"});
  auto d = load(reactionScene(only));
  CHECK(generated(*d, "girl", "emotion").size() == 1);
  CHECK(generated(*d, "boy", "emotion").size() == 1);
}

TEST_CASE("animcheck's acting rule (T-097C) sees the notice delay of the generated reaction") {
  auto ev = load(reactionScene(kEvents));
  // The scene as the acting rule reads it: the generated actions appended, profiles next to it (content/personality).
  const auto dir = std::filesystem::temp_directory_path() / "plush_t097d_acting";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "content" / "personality");
  for (const char* p : {"girl_auburn_bun_glasses", "boy_yellow_hoodie"})
    std::filesystem::copy_file(kSrc / "content/personality" / (std::string(p) + ".json"),
                               dir / "content/personality" / (std::string(p) + ".json"));
  Json sj = sceneToJson(ev->scene());
  for (const Json& a : ev->reactionActions()) sj["actions"].push_back(a);
  std::ofstream(dir / "shot.scene.json") << sj.dump(1);
  std::string py;
  for (const char* cand : {"python3", "python"})
    if (std::system(std::format("{} -c \"import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)\"", cand).c_str()) == 0) {
      py = cand;
      break;
    }
  if (py.empty()) {
    MESSAGE("no python3 found: acting-rule part not run");
    return;
  }
  const auto report = dir / "acting.json";
  const std::string cmd = std::format("{} \"{}\" --scene \"{}\" --json \"{}\"", py, (kSrc / "tools/animcheck/acting.py").string(),
                                      (dir / "shot.scene.json").string(), report.string());
  REQUIRE(std::system(cmd.c_str()) == 0);
  auto rep = parseJsonFile(report);
  REQUIRE(rep.has_value());
  CHECK((*rep)["warnings"].empty());
  ReactionEvent appear{ReactionEvent::Kind::ObjectAppears, "ball appears", "ball", 1.0, 1.f};
  for (const Json& ch : (*rep)["characters"]) {
    const size_t c = ch["character"] == "girl" ? 0 : 1;
    const double delay = planReaction(appear, ev->personality(c)).noticeDelay * 24;
    REQUIRE(!ch["glances"].empty());
    const Json& g = ch["glances"][0];
    MESSAGE(ch["character"].get<std::string>() << ": acting rule glance " << g["delay_frames"].get<double>()
                                                << " f after the event, notice delay " << g["notice_delay_frames"]);
    CHECK(g["event"] == "ball appears");
    CHECK(g["delay_frames"].get<double>() == doctest::Approx(delay).epsilon(0.01));
    CHECK(g["delay_frames"].get<double>() >= g["notice_delay_frames"].get<double>());
  }
  std::filesystem::remove_all(dir);
}

TEST_CASE("a profile's preferred gesture plays as a clip at the reaction start (only clips the library has)") {
  // A fixture profile (test data, not a character's tuning) next to a copy of the shared emotion and clip libraries.
  const auto dir = std::filesystem::temp_directory_path() / "plush_t097d_gesture";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "content" / "personality");
  for (const char* lib : {"emotions", "clips"})
    std::filesystem::copy(kSrc / "content" / lib, dir / "content" / lib, std::filesystem::copy_options::recursive);
  std::ofstream(dir / "content/personality/reaction_fixture.json") << R"({"format": "plush.personality", "version": 0,
    "reaction": {"events": {"object_appears": {"emotion": "surprised", "intensity": 0.9, "gestures": ["no_such_clip", "point"]}}}})";
  Scene s = reactionScene(Json::parse(R"([{"time": 1.0, "kind": "object_appears", "source": "ball", "characters": ["girl"]}])"));
  s.path = dir / "scene.json";
  for (auto& cd : s.characters) cd.asset = (kSrc / "tests/data/imported" / cd.asset).string();
  s.characters[0].personality = "reaction_fixture";
  s.characters[1].personality = nullptr;  // the shared defaults
  auto ev = load(s);
  for (const auto& w : ev->warnings()) MESSAGE(w);
  auto clips = generated(*ev, "girl", "clip"), emotions = generated(*ev, "girl", "emotion");
  REQUIRE(clips.size() == 1);
  REQUIRE(emotions.size() == 1);
  CHECK(clips[0]["clip"] == "point");  // the first preferred gesture the library has
  CHECK(clips[0]["start"] == emotions[0]["start"]);
  CHECK(emotions[0]["name"] == "surprised");
  CHECK(generated(*ev, "boy", "clip").empty());
  bool planned = false;
  for (const auto& L : ev->clipLayerPlans(0)) planned |= L.clip == "point" && std::abs(L.start - clips[0]["start"].get<double>()) < 1e-9;
  CHECK(planned);
  ev.reset();
  std::filesystem::remove_all(dir);
}

TEST_CASE("a quick profile (reaction tempo_scale < 1) never reacts before its shortest notice delay") {
  // Fixture profile: delay_frames [2, 4] (mid 3) x tempo_scale 0.5 plans 1.5 f; playback starts at 2 f, the profile's
  // shortest delay, which is what animcheck's acting rule (T-097C) requires.
  const auto dir = std::filesystem::temp_directory_path() / "plush_t097d_quick";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "content" / "personality");
  for (const char* lib : {"emotions", "clips"})
    std::filesystem::copy(kSrc / "content" / lib, dir / "content" / lib, std::filesystem::copy_options::recursive);
  std::ofstream(dir / "content/personality/quick_fixture.json")
      << R"({"format": "plush.personality", "version": 0, "reaction": {"delay_frames": [2, 4], "tempo_scale": 0.5}})";
  Scene s = reactionScene(Json::parse(R"([{"time": 1.0, "kind": "object_appears", "name": "ball appears", "source": "ball",
    "characters": ["girl"]}])"));
  s.path = dir / "shot.scene.json";
  for (auto& cd : s.characters) cd.asset = (kSrc / "tests/data/imported" / cd.asset).string();
  s.characters[0].personality = "quick_fixture";
  s.characters[1].personality = nullptr;
  auto ev = load(s);
  REQUIRE(ev->personality(0));
  ReactionEvent appear{ReactionEvent::Kind::ObjectAppears, "ball appears", "ball", 1.0, 1.f};
  CHECK(planReaction(appear, ev->personality(0)).noticeDelay * 24 == doctest::Approx(1.5));
  auto looks = generated(*ev, "girl", "look"), emotions = generated(*ev, "girl", "emotion");
  REQUIRE(looks.size() == 1);
  REQUIRE(emotions.size() == 1);
  CHECK(looks[0]["start"].get<double>() == doctest::Approx(1 + 24 + 2));
  CHECK(emotions[0]["start"] == looks[0]["start"]);
  // The acting rule on the scene with the generated actions: no warning.
  Json sj = sceneToJson(ev->scene());
  for (const Json& a : ev->reactionActions()) sj["actions"].push_back(a);
  std::ofstream(dir / "expanded.scene.json") << sj.dump(1);
  std::string py;
  for (const char* cand : {"python3", "python"})
    if (std::system(std::format("{} -c \"import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)\"", cand).c_str()) == 0) {
      py = cand;
      break;
    }
  if (!py.empty()) {
    const auto report = dir / "acting.json";
    REQUIRE(std::system(std::format("{} \"{}\" --scene \"{}\" --json \"{}\"", py, (kSrc / "tools/animcheck/acting.py").string(),
                                    (dir / "expanded.scene.json").string(), report.string()).c_str()) == 0);
    auto rep = parseJsonFile(report);
    REQUIRE(rep.has_value());
    CHECK((*rep)["warnings"].empty());
    REQUIRE(!(*rep)["characters"][0]["glances"].empty());
    CHECK((*rep)["characters"][0]["glances"][0]["delay_frames"].get<double>() == doctest::Approx(2));
  } else {
    MESSAGE("no python3 found: acting-rule part not run");
  }
  ev.reset();
  std::filesystem::remove_all(dir);
}
