// T-138 (E4): band fit for per-finger grasps (opt-in scene "interaction": {"graspFit": true} -> track
// "hand.<s>.bandFit"; anim/animation.cpp band step). Measured on the boy and girl test packages and the engine (SDF)
// skeleton, on felt_cup's `grip` socket with its own band and with a band too narrow for the hands.
#include <doctest/doctest.h>

#include <filesystem>
#include <format>
#include <memory>

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

const PropAsset& cup() {
  static const PropAsset a = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  return a;
}

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

// One actor grasping the cup's `grip` (turned 180 deg to face the right hand) at f20, as test_hand_shapes.
Scene graspScene(const char* asset) {
  Scene s;
  s.name = "grasp contact test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 40;
  CharacterDesc c;
  c.name = "actor";
  c.asset = asset;
  s.characters.push_back(c);
  auto probe = load(s);
  const vec3 shoulder = bonePos(*probe, "upperArm.R", 1), elbow = bonePos(*probe, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(*probe, "hand.R", 1));
  PropDesc p;
  p.name = "cup";
  p.id = "prop.felt_cup";
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
  p.transform.translation = shoulder + vec3(0.04f, -0.45f, 0.85f) * arm - vec3(rot * vec4(cup().sockets.at("grip").translation, 0));
  p.transform.rotationDeg = {0, 180, 0};
  s.props.push_back(p);
  s.actions = Json::parse(R"([{"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "socket": "grip", "start": 5, "contact": 20}])");
  return s;
}

void keyBand(Scene& s, vec2 band, bool fit) {
  const float y = cup().sockets.at("grip").translation.y;  // the grasp centre sits at the socket's height
  s.animation.tracks["actor/hand.R.band"].setKey(Key{5, vec3(band.x - y, band.y - y, 0), Interp::Step});
  if (fit) s.animation.tracks["actor/hand.R.bandFit"].setKey(Key{5, vec3(1), Interp::Step});
}

struct Measure {
  float gap = 0, deepest = 1, bandOut = -1, minTipApart = 1;  // m; bandOut < 0 = inside by that much
  vec3 wrist{0};
  std::vector<vec3> tips;
};
Measure measure(const SceneEvaluator& ev, double f, vec2 band) {
  const Skeleton& sk = ev.characters()[0].asset.skeleton;
  const auto g = ev.characterGlobals(0, f);
  const mat4 P = ev.propWorld(0, f);
  const vec3 axis = glm::normalize(vec3(P[1])), base = vec3(P[3]);
  const float R = cup().mesh.radius, r = fingertipRadius(sk, 'R');
  Measure m;
  std::vector<vec3> fingers;
  for (const char* d : {"thumb", "f0", "f1", "f2", "f3"}) {
    const std::string a = std::string(d) + (d[0] == 't' ? "A.R" : "a.R"), b = std::string(d) + (d[0] == 't' ? "B.R" : "b.R");
    const int ia = sk.find(a), ib = sk.find(b);
    if (ia < 0 || ib < 0) continue;
    const vec3 tip = vec3(g[size_t(ib)] * vec4(sk.bones[size_t(ib)].head - sk.bones[size_t(ia)].head, 1)), kn = vec3(g[size_t(ib)][3]);
    auto radial = [&](vec3 p) {
      const vec3 q = p - base;
      return glm::length(q - axis * glm::dot(q, axis));
    };
    m.gap = std::max(m.gap, std::abs(radial(tip) - R - r));
    m.deepest = std::min({m.deepest, radial(tip) - R, radial(kn) - R});
    const float h = glm::dot(tip - base, axis);
    m.bandOut = std::max({m.bandOut, band.x - h, h - band.y});
    m.tips.push_back(tip);
    if (d[0] == 'f') fingers.push_back(tip);
  }
  for (size_t i = 1; i < fingers.size(); ++i) m.minTipApart = std::min(m.minTipApart, glm::distance(fingers[i - 1], fingers[i]));
  m.wrist = bonePos(ev, "hand.R", f);
  return m;
}

}  // namespace

TEST_CASE("grasp band fit: a band too narrow for the hand - contacts pulled into it, still on the surface (T-138)") {
  const vec2 narrow{0.058f, 0.077f};  // 19 mm, inside felt_cup's grip band (45-90 mm)
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    CAPTURE(asset);
    Scene plain = graspScene(asset), fit = plain;
    keyBand(plain, narrow, false);
    keyBand(fit, narrow, true);
    auto a = load(plain), b = load(fit);
    for (double f : {24.0, 30.0}) {
      const Measure ma = measure(*a, f, narrow), mb = measure(*b, f, narrow);
      MESSAGE(std::format("{} f{}: band out {:.2f} -> {:.2f} mm, tip gap {:.2f} -> {:.2f} mm, deepest {:.2f} mm, "
                          "closest fingertips {:.1f} -> {:.1f} mm, wrist moved {:.4f} mm",
                          asset, f, ma.bandOut * 1e3, mb.bandOut * 1e3, ma.gap * 1e3, mb.gap * 1e3, mb.deepest * 1e3,
                          ma.minTipApart * 1e3, mb.minTipApart * 1e3, glm::distance(ma.wrist, mb.wrist) * 1e3));
      if (asset == kSdf) {  // the small engine hand fits even this band: nothing changes
        CHECK(ma.bandOut <= 0.0f);
        CHECK(mb.tips == ma.tips);
        continue;
      }
      CHECK(ma.bandOut > 0.002f);                  // T-051 alone leaves contacts outside this band
      CHECK(mb.bandOut <= ma.bandOut - 0.001f);    // the fit pulls them at least 1 mm further in
      CHECK(mb.gap <= 0.002f);                     // every tip still rests on the cup
      CHECK(mb.deepest >= 0.0f);                   // nothing inside it
      CHECK(glm::distance(ma.wrist, mb.wrist) <= 1e-5f);  // the wrist and arm are untouched
    }
  }
}

TEST_CASE("grasp band fit: a hand that fits the band poses exactly as without the fit (T-138)") {
  const vec2 band{0.045f, 0.09f};  // felt_cup's grip band
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    CAPTURE(asset);
    Scene plain = graspScene(asset), fit = plain;
    keyBand(plain, band, false);
    keyBand(fit, band, true);
    auto a = load(plain), b = load(fit);
    for (double f : {14.0, 20.0, 24.0, 30.0}) {
      const Measure ma = measure(*a, f, band), mb = measure(*b, f, band);
      if (f >= 24) CHECK(ma.bandOut <= 0.0f);  // held: every contact in the band
      REQUIRE(ma.tips.size() == mb.tips.size());
      for (size_t i = 0; i < ma.tips.size(); ++i) CHECK(ma.tips[i] == mb.tips[i]);
    }
  }
}

TEST_CASE("grasp band fit: scene option interaction.graspFit keys hand.<s>.bandFit on banded grasps only (T-138)") {
  auto parsed = interactionOptionsFromJson(Json::parse(R"({"graspFit": true})"));
  REQUIRE(parsed);
  CHECK(parsed->graspFit);
  CHECK_FALSE(interactionOptionsFromJson(Json::object()).value().graspFit);
  CHECK_FALSE(interactionOptionsFromJson(Json::parse(R"({"graspFit": 1})")));
  auto hasFit = [](const SceneEvaluator& ev) {
    const Clip& clip = ev.scene().animation;
    for (const Clip* c : {&clip, clip.generated.get()})
      if (c && c->find("actor/hand.R.bandFit")) return true;
    return false;
  };
  Scene s = graspScene(kBoy);
  s.actions[0]["band"] = {0.045, 0.09};
  CHECK_FALSE(hasFit(*load(s)));  // off by default
  s.interaction = Json::parse(R"({"graspFit": true})");
  CHECK(hasFit(*load(s)));
  s.actions[0].erase("band");
  CHECK_FALSE(hasFit(*load(s)));  // no band, nothing to fit
}
