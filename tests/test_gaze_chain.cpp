// T-136 E3: gaze chain (opt-in gazeLegibility "chain"): the eyes lead, then head + neck and torso take over beyond the
// eye range so a look reaches its target; exact live targets (eye contact). Off = T-120 unchanged.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>

#include "geom/json_io.h"
#include "scene/scene.h"

using namespace plush;

namespace {
Skeleton chainSkeleton() {
  Skeleton sk;
  sk.bones = {{"spine", -1, vec3(0, 0.8f, 0)},          {"chest", 0, vec3(0, 1.0f, 0)},
              {"neck", 1, vec3(0, 1.3f, 0)},            {"head", 2, vec3(0, 1.4f, 0)},
              {"eye.L", 3, vec3(0.03f, 1.45f, 0.08f)}, {"eye.R", 3, vec3(-0.03f, 1.45f, 0.08f)}};
  return sk;
}
GazeLegibility legible(bool chain) {
  GazeLegibility lg;
  lg.enabled = true;
  lg.rangeDeg = vec2(16, 8);
  lg.headYawDeg = 15;
  lg.headPitchDeg = 10;
  lg.chain = chain;
  return lg;
}
Pose posed(const Skeleton& sk, const Clip& clip, double frame, const GazeLegibility& lg) {
  GazeLimits limits;
  limits.assistYawDeg = limits.assistPitchDeg = limits.assistBodyYawDeg = 0;
  limits.maxLeftDeg = limits.maxRightDeg = lg.rangeDeg.x;
  limits.maxUpDeg = limits.maxDownDeg = lg.rangeDeg.y;
  Pose pose = restPose(sk);
  if (lg.chain) turnChainForGaze(sk, clip, "a/", frame, 24, mat4(1), pose, lg, vec3(0));
  else turnHeadForGaze(sk, clip, "a/", frame, 24, mat4(1), pose, lg);
  applyConstraints(sk, clip, "a/", frame, mat4(1), pose, limits, 24);
  if (lg.chain) aimEyesAt(sk, mat4(1), pose, clip.find("a/lookAt")->evaluate(frame), 1.0f);
  clampEyesToGazeRange(sk, mat4(1), pose, lg.rangeDeg);
  return pose;
}
float aimError(const std::vector<mat4>& g, std::initializer_list<int> eyes, vec3 target) {
  float worst = 0;
  for (int e : eyes) {
    const vec3 fwd = glm::normalize(vec3(g[size_t(e)][2])), to = glm::normalize(target - vec3(g[size_t(e)][3]));
    worst = std::max(worst, glm::degrees(std::acos(std::clamp(glm::dot(fwd, to), -1.0f, 1.0f))));
  }
  return worst;
}
float turnDeg(const quat& q) { return glm::degrees(2.0f * std::acos(std::clamp(std::abs(q.w), 0.0f, 1.0f))); }

std::unique_ptr<SceneEvaluator> pairScene(const Json& gaze) {
  Scene s;
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 80;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
  const char* pkgs[2] = {"boy_yellow_hoodie_1.0.0", "girl_auburn_bun_glasses_m3"};
  const char* names[2] = {"boy", "girl"};
  // Side by side, both facing the camera (+Z): a partner look is ~70-90 degrees to the side.
  for (int i = 0; i < 2; ++i) {
    CharacterDesc cd;
    cd.name = names[i];
    cd.asset = std::string(pkgs[i]) + "/character.json";
    cd.position = vec3(i == 0 ? -0.3f : 0.3f, 0, 0);
    cd.life.enabled = true;
    s.characters.push_back(cd);
  }
  s.gazeLegibility = gaze;
  s.actions = Json::parse(R"([
    {"type": "look", "character": "boy", "start": 10, "end": 80, "atCharacter": "girl"},
    {"type": "look", "character": "girl", "start": 10, "end": 80, "atCharacter": "boy"}])");
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}
// Each eye of character c against the midpoint of the partner's eyes (eye contact), degrees (worst eye).
float contactError(const SceneEvaluator& ev, size_t c, double f) {
  auto eyes = [&](size_t k) {
    std::vector<int> out;
    const Skeleton& sk = ev.characters()[k].asset.skeleton;
    for (size_t b = 0; b < sk.bones.size(); ++b)
      if (sk.bones[b].name.rfind("eye.", 0) == 0) out.push_back(int(b));
    return out;
  };
  const auto g = ev.characterGlobals(c, f), go = ev.characterGlobals(1 - c, f);
  vec3 mid(0);
  for (int e : eyes(1 - c)) mid += vec3(go[size_t(e)][3]);
  mid /= float(eyes(1 - c).size());
  float worst = 0;
  for (int e : eyes(c)) {
    const vec3 fwd = glm::normalize(vec3(g[size_t(e)][2])), to = glm::normalize(mid - vec3(g[size_t(e)][3]));
    worst = std::max(worst, glm::degrees(std::acos(std::clamp(glm::dot(fwd, to), -1.0f, 1.0f))));
  }
  return worst;
}
}  // namespace

TEST_CASE("gaze chain: parsing") {
  CHECK_FALSE(gazeLegibilityFromJson(Json::parse(R"({"rangeDeg": [16, 8]})")).value().chain);
  CHECK(gazeLegibilityFromJson(Json::parse(R"({"chain": true})")).value().chain);
  auto g = gazeLegibilityFromJson(Json::parse(R"({"chain": {"torsoYawDeg": 12, "neckPitchDeg": 33}})"));
  REQUIRE(g.has_value());
  CHECK(g->chain);
  CHECK(g->torsoYawDeg == 12);
  CHECK(g->neckPitchDeg == 33);
  CHECK_FALSE(gazeLegibilityFromJson(Json::parse(R"({"chain": {"enabled": false}})")).value().chain);
  CHECK_FALSE(gazeLegibilityFromJson(Json::parse(R"({"chain": {"bogus": 1}})")).has_value());
  CHECK_FALSE(gazeLegibilityFromJson(Json::parse(R"({"chain": {"torsoYawDeg": -1}})")).has_value());
  CHECK_FALSE(gazeLegibilityFromJson(Json::parse(R"({"chain": 3})")).has_value());
  // A character's chain settings sit on the scene's.
  auto base = gazeLegibilityFromJson(Json::parse(R"({"chain": true})")).value();
  CHECK(gazeLegibilityFromJson(Json::parse(R"({"headPitchDeg": 10})"), base).value().chain);
}

TEST_CASE("gaze chain: eyes lead, then neck / head and torso take a steep look to its target") {
  const Skeleton sk = chainSkeleton();
  const vec3 ahead(0, 1.45f, 3), steep(0.6f, 0.55f, 0.55f);  // ~45 deg to the side and ~45 deg down
  Clip clip;
  clip.tracks["a/lookAt"].setKey({0, ahead, Interp::Step});
  clip.tracks["a/lookAt"].setKey({20, steep, Interp::Step});
  // T-120 alone stops short (eyes 16 / 8, head 15 / 10).
  const float before = aimError(boneGlobals(sk, posed(sk, clip, 60, legible(false)), mat4(1)), {4, 5}, steep);
  // The chain reaches it.
  const Pose p = posed(sk, clip, 60, legible(true));
  const float after = aimError(boneGlobals(sk, p, mat4(1)), {4, 5}, steep);
  MESSAGE("steep look error: T-120 " << before << " deg, chain " << after << " deg; torso " << turnDeg(p.local[0]) + turnDeg(p.local[1])
                                     << " deg, neck + head " << turnDeg(p.local[2]) + turnDeg(p.local[3]) << " deg");
  CHECK(before > 15.0f);
  CHECK(after < 1.0f);
  CHECK(turnDeg(p.local[0]) + turnDeg(p.local[1]) > 2.0f);  // the torso took part
  // Eyes lead: right after the jump the body has not moved yet; the eyes have.
  const Pose early = posed(sk, clip, 21, legible(true));
  for (int b : {0, 1, 2, 3}) CHECK(turnDeg(early.local[size_t(b)]) < 0.5f);
  CHECK(turnDeg(early.local[4]) > 5.0f);
  // The torso follows after the head: a few frames into the turn, the neck has moved more than the torso.
  const Pose mid = posed(sk, clip, 28, legible(true));
  CHECK(turnDeg(mid.local[2]) + turnDeg(mid.local[3]) > turnDeg(mid.local[0]) + turnDeg(mid.local[1]));
  // A near target inside the eye range moves nothing but the eyes.
  Clip near;
  near.tracks["a/lookAt"].setKey({0, vec3(0.1f, 1.43f, 1.5f), Interp::Step});
  const Pose q = posed(sk, near, 40, legible(true));
  for (int b : {0, 1, 2, 3}) CHECK(turnDeg(q.local[size_t(b)]) < 0.05f);
}

TEST_CASE("gaze chain: held eye contact between two characters; chain false = T-120") {
  auto t120 = pairScene(Json::parse(R"({"rangeDeg": [16, 8], "headYawDeg": 15, "headPitchDeg": 10})"));
  auto off = pairScene(Json::parse(R"({"rangeDeg": [16, 8], "headYawDeg": 15, "headPitchDeg": 10, "chain": false})"));
  auto chain = pairScene(Json::parse(R"({"rangeDeg": [16, 8], "headYawDeg": 15, "headPitchDeg": 10, "chain": true})"));
  for (double f : {5.0, 30.0, 60.0}) {  // off is T-120 to the bit
    const auto a = t120->characterGlobals(0, f), b = off->characterGlobals(0, f);
    REQUIRE(a.size() == b.size());
    bool same = true;
    for (size_t i = 0; i < a.size(); ++i) same = same && a[i] == b[i];
    CHECK(same);
  }
  for (size_t c = 0; c < 2; ++c) {
    float worstBefore = 0, worstAfter = 0;
    for (double f = 40; f <= 80; f += 5) {
      worstBefore = std::max(worstBefore, contactError(*t120, c, f));
      worstAfter = std::max(worstAfter, contactError(*chain, c, f));
    }
    MESSAGE("character " << c << " eye contact error: T-120 " << worstBefore << " deg, chain " << worstAfter << " deg");
    CHECK(worstBefore > 10.0f);
    CHECK(worstAfter < 2.5f);  // eye darts (about 1.6 deg) stay on top
  }
}
