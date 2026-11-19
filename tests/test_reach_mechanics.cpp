// T-134: reach mechanics (anim/principles.h ReachMechanics, scene/interaction.cpp), the opt-in scene key
// "reachMechanics": ease, anticipation (body lead), arcs and overlap of the prop reaches.
#include <doctest/doctest.h>

#include <filesystem>
#include <memory>

#include "anim/principles.h"
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* kGirl = "girl_auburn_bun_glasses_m3/character.json";
const char* kSdf = "../../../content/characters/girl_white_hair.character.json";

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

vec3 bonePos(const SceneEvaluator& ev, const char* bone, double f) {
  const int b = ev.characters()[0].asset.skeleton.find(bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(0, f)[size_t(b)][3]);
}

// One actor grasping a felt cup in front of the right shoulder (as tests/test_interaction.cpp), reach f20 -> f38.
constexpr double kStart = 20, kContact = 38;
Scene reachScene(const char* asset, const Json& reachMechanics) {
  Scene s;
  s.name = "reach mechanics test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 80;
  CharacterDesc c;
  c.name = "actor";
  c.asset = asset;
  c.life.enabled = true;
  s.characters.push_back(c);
  auto probe = load(s);
  const vec3 shoulder = bonePos(*probe, "upperArm.R", 1), elbow = bonePos(*probe, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(*probe, "hand.R", 1));
  PropDesc cup;
  cup.name = "cup";
  cup.id = "prop.felt_cup";
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
  const PropAsset pa = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  cup.transform.translation = shoulder + vec3(0.04f, -0.45f, 0.85f) * arm - vec3(rot * vec4(pa.sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, 180, 0};
  s.props.push_back(cup);
  s.actions = Json::array({{{"type", "grasp"}, {"character", "actor"}, {"hand", "R"}, {"prop", "cup"}, {"start", kStart}, {"contact", kContact}}});
  s.reachMechanics = reachMechanics;
  return s;
}

bool hasReachTracks(const SceneEvaluator& ev) {
  const Clip& clip = ev.scene().animation;
  for (const Clip* c : {&clip, clip.generated.get()})
    if (c)
      for (const auto& [name, track] : c->tracks)
        if (name.find("reach.") != std::string::npos) return true;
  return false;
}

// Wrist speed per frame (m / frame) over [a, b).
std::vector<float> wristSpeed(const SceneEvaluator& ev, double a, double b) {
  std::vector<float> v;
  for (double f = a; f < b; f += 1) v.push_back(glm::distance(bonePos(ev, "hand.R", f), bonePos(ev, "hand.R", f + 1)));
  return v;
}

void easeAndAnticipation(const char* asset) {
  auto off = load(reachScene(asset, nullptr));
  auto on = load(reachScene(asset, true));
  CHECK(!hasReachTracks(*off));
  CHECK(hasReachTracks(*on));
  for (const auto& w : on->warnings()) MESSAGE(w);
  CHECK(on->warnings().size() <= off->warnings().size());
  // The contact is as exact as without the mechanics.
  const PropAsset pa = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  const vec3 grip((on->propWorld(0, kContact) * assetTransformMatrix(pa.sockets.at("grip")))[3]);
  const float d = glm::distance(on->handGripPoint(0, 'R', kContact), grip);
  MESSAGE(std::string(asset) << ": palm to grip socket at contact " << d * 1000 << " mm");
  CHECK(d < 0.005f);
  // E1a ease: the wrist leaves and arrives slowly and has one speed peak in between.
  const auto v = wristSpeed(*on, kStart, kContact), v0 = wristSpeed(*off, kStart, kContact);
  const float peak = *std::max_element(v.begin(), v.end());
  MESSAGE(std::string(asset) << ": wrist speed first / peak / last frame " << v.front() * 1000 << " / " << peak * 1000 << " / " << v.back() * 1000
                << " mm/f (off: " << v0.front() * 1000 << " / " << *std::max_element(v0.begin(), v0.end()) * 1000 << " / "
                << v0.back() * 1000 << ")");
  CHECK(v.front() < 0.2f * peak);
  CHECK(v.back() < 0.2f * peak);
  const size_t at = size_t(std::max_element(v.begin(), v.end()) - v.begin());
  CHECK(at > 2);
  CHECK(at + 3 < v.size());
  for (size_t i = 1; i < v.size(); ++i) CHECK((i <= at ? v[i] >= v[i - 1] - 0.0015f : v[i] <= v[i - 1] + 0.0015f));
  // E1a anticipation: the chest moves before the reach starts (first away from the prop, then towards it) and is
  // at least half way into its lead when the wrist has done a tenth of its travel.
  const vec3 dir = glm::normalize(bonePos(*on, "hand.R", kContact) - bonePos(*on, "hand.R", kStart));
  auto lead = [&](double f) { return glm::dot(bonePos(*on, "upperArm.R", f) - bonePos(*off, "upperArm.R", f), dir); };
  float dip = 0, full = 0;
  for (double f = kStart - 8; f <= kStart; f += 1) dip = std::min(dip, lead(f));
  for (double f = kStart; f <= kContact; f += 1) full = std::max(full, lead(f));
  MESSAGE(std::string(asset) << ": shoulder lead along the reach: counter " << dip * 1000 << " mm, full " << full * 1000 << " mm");
  CHECK(dip < -0.0005f);
  CHECK(full > 0.004f);
  CHECK(glm::distance(bonePos(*on, "upperArm.R", kStart - 10), bonePos(*off, "upperArm.R", kStart - 10)) < 1e-5f);
  const float travel = glm::distance(bonePos(*on, "hand.R", kContact), bonePos(*on, "hand.R", kStart));
  double tenth = kStart;
  while (tenth < kContact && glm::distance(bonePos(*on, "hand.R", tenth), bonePos(*on, "hand.R", kStart)) < 0.1f * travel) tenth += 1;
  MESSAGE(std::string(asset) << ": wrist at 10 % of its travel at f" << tenth << ", shoulder lead there " << lead(tenth) / full * 100 << " %");
  CHECK(lead(tenth) > 0.3f * full);
  // The lead is given back after the contact, and the feet stay where they were.
  CHECK(glm::distance(bonePos(*on, "upperArm.R", 70), bonePos(*off, "upperArm.R", 70)) < 0.002f);
  if (on->characters()[0].asset.skeleton.find("foot.R") >= 0)
    for (double f = kStart - 8; f <= 60; f += 2) CHECK(glm::distance(bonePos(*on, "foot.R", f), bonePos(*off, "foot.R", f)) < 0.004f);
}

// Largest deviation of the wrist path over [a, b] from its chord / chord length.
float wristArc(const SceneEvaluator& ev, double a, double b) {
  std::vector<vec3> path;
  for (double f = a; f <= b; f += 1) path.push_back(bonePos(ev, "hand.R", f));
  return arcDeviation(path);
}

// E1b: a carry (hold) after the grasp travels an arc with the timing it had, and still arrives.
void carryArc(const char* asset) {
  auto scene = [&](const Json& rm) {
    Scene s = reachScene(asset, rm);
    s.actions.push_back({{"type", "hold"}, {"character", "actor"}, {"hand", "R"}, {"start", 42}, {"end", 58}, {"by", {0.03, 0.05, -0.02}}});
    return s;
  };
  auto off = load(scene(nullptr));
  auto on = load(scene(Json{{"ease", false}, {"anticipation", false}}));
  for (const auto& w : on->warnings()) MESSAGE(w);
  CHECK(on->warnings().size() <= off->warnings().size());
  const float a0 = wristArc(*off, 42, 58), a1 = wristArc(*on, 42, 58);
  MESSAGE(std::string(asset) << ": carry arc (deviation / chord) off " << a0 << ", on " << a1);
  CHECK(a0 < 0.03f);
  CHECK(a1 > 0.06f);
  CHECK(a1 < 0.2f);
  // Same ends and the same timing: only the path between them changes.
  CHECK(glm::distance(vec3(on->propWorld(0, 58)[3]), vec3(off->propWorld(0, 58)[3])) < 0.001f);
  CHECK(glm::distance(bonePos(*on, "hand.R", 42), bonePos(*off, "hand.R", 42)) < 0.001f);
  const auto v1 = wristSpeed(*on, 42, 58), v0 = wristSpeed(*off, 42, 58);
  for (size_t i = 0; i < v1.size(); ++i) CHECK(std::abs(v1[i] - v0[i]) < 0.003f);
  // The eased reach itself is not a straight chord either.
  auto full = load(scene(true));
  const float r = wristArc(*full, kStart, kContact);
  MESSAGE(std::string(asset) << ": reach arc " << r << ", carry arc with everything on " << wristArc(*full, 42, 58));
  CHECK(r > 0.1f);
  const PropAsset pa = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  const vec3 grip((full->propWorld(0, kContact) * assetTransformMatrix(pa.sockets.at("grip")))[3]);
  CHECK(glm::distance(full->handGripPoint(0, 'R', kContact), grip) < 0.005f);
}

}  // namespace

TEST_CASE("reach mechanics: settings parse, off by default") {
  CHECK(!reachMechanicsFromJson(nullptr).value().enabled);
  CHECK(!reachMechanicsFromJson(false).value().enabled);
  CHECK(reachMechanicsFromJson(true).value().enabled);
  const auto m = reachMechanicsFromJson(Json::parse(R"({"anticipation": false, "leanDeg": 2})"));
  REQUIRE(m);
  CHECK(m->enabled);
  CHECK(!m->anticipation);
  CHECK(m->leanDeg == 2);
  CHECK(!reachMechanicsFromJson(Json::parse(R"({"leanDeg": 90})")));
  CHECK(!reachMechanicsFromJson(Json::parse(R"({"ease": 1})")));
  CHECK(!reachMechanicsFromJson(3));
}

TEST_CASE("reach mechanics: ease and lead profiles") {
  ReachMechanics m;
  CHECK(reachEase(0, 0.45) == 0);
  CHECK(reachEase(1, 0.45) == 1);
  CHECK(reachEase(0.45, 0.45) == doctest::Approx(0.5));
  CHECK(reachEase(0.5, 0.5) == doctest::Approx(0.5));
  double peakAt = 0, peak = 0;
  for (double x = 0; x < 1; x += 0.01) {
    const double v = reachEase(x + 0.01, 0.45) - reachEase(x, 0.45);
    CHECK(v >= 0);
    if (v > peak) peak = v, peakAt = x;
  }
  CHECK(peakAt == doctest::Approx(0.45).epsilon(0.1));
  CHECK(reachEase(0.02, 0.45) < 0.001);
  CHECK(1 - reachEase(0.98, 0.45) < 0.001);
  // Lead: zero outside, a dip before the start, full from leadPeak to the contact, continuous.
  CHECK(reachLead(-0.5, 0.3, 0.8, m) == 0);
  CHECK(reachLead(2, 0.3, 0.8, m) == 0);
  CHECK(reachLead(-0.12, 0.3, 0.8, m) == doctest::Approx(-m.counter));
  CHECK(reachLead(m.leadPeak, 0.3, 0.8, m) == doctest::Approx(1));
  CHECK(reachLead(1, 0.3, 0.8, m) == doctest::Approx(1));
  for (double x = -0.4; x < 2; x += 0.01) CHECK(std::abs(reachLead(x + 0.01, 0.3, 0.8, m) - reachLead(x, 0.3, 0.8, m)) < 0.06);
  CHECK(reachLead(0.3, 0, 0.8, m) > 0);  // no room to anticipate: no counter move
}

TEST_CASE("reach mechanics: eased wrist and body lead (boy skeleton)") { easeAndAnticipation(kBoy); }
TEST_CASE("reach mechanics: eased wrist and body lead (girl skeleton)") { easeAndAnticipation(kGirl); }
TEST_CASE("reach mechanics: eased wrist and body lead (engine skeleton)") { easeAndAnticipation(kSdf); }
TEST_CASE("reach mechanics: a carry travels an arc (boy skeleton)") { carryArc(kBoy); }
TEST_CASE("reach mechanics: a carry travels an arc (girl skeleton)") { carryArc(kGirl); }
TEST_CASE("reach mechanics: a carry travels an arc (engine skeleton)") { carryArc(kSdf); }
