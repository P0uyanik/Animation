// T-138 (E4) / T-157: band fit for per-finger grasps (opt-in scene "interaction": {"graspFit": true} -> track
// "hand.<s>.bandFit"; anim/animation.cpp band step). Measured on the boy and girl test packages and the engine (SDF)
// skeleton, on felt_cup's `grip` socket with its own band and with a band too narrow for the hands.
#include <doctest/doctest.h>

#include <filesystem>
#include <format>
#include <memory>

#include "anim/hand_shape.h"
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

void keyFit(Scene& s, vec2 band, vec2 options) {  // T-157: band fit with its options (widen at both ends, off-band bits)
  keyBand(s, band, true);
  s.animation.tracks["actor/hand.R.bandFitOptions"].setKey(Key{5, vec3(options.x, options.y, options.x), Interp::Step});
}

struct Measure {
  float gap = 0, deepest = 1, bandOut = -1, minTipApart = 1;  // m; bandOut < 0 = inside by that much
  vec3 wrist{0};
  std::vector<vec3> tips;
  std::vector<float> clear, heights;  // T-157 per digit (thumb first): tip skin to surface, tip height (m)
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
    m.clear.push_back(std::min(radial(tip), radial(kn)) - R - r);
    m.heights.push_back(h);
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

TEST_CASE("grasp band options: a wider band and off-band fingers, opt-in track hand.<s>.bandFitOptions (T-157)") {
  const vec2 narrow{0.058f, 0.077f};  // 19 mm, as the T-138 case
  const float widen = 0.008f;         // T-157 option (a): 8 mm more at each end
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    CAPTURE(asset);
    Scene fit = graspScene(asset), zero = fit, wide = fit, off = fit, both = fit;
    keyBand(fit, narrow, true);
    keyFit(zero, narrow, vec2(0, 0));
    keyFit(wide, narrow, vec2(widen, 0));
    keyFit(off, narrow, vec2(0, 1));  // bit 0: finger bone f0 leaves the band
    keyFit(both, narrow, vec2(widen, 1));
    auto a = load(fit), z = load(zero), w = load(wide), o = load(off), b = load(both);
    const vec2 wider = narrow + vec2(-widen, widen);
    const Measure ma = measure(*a, 30, narrow), mz = measure(*z, 30, narrow), mw = measure(*w, 30, wider),
                  mo = measure(*o, 30, narrow), mb = measure(*b, 30, wider);
    const float r = fingertipRadius(a->characters()[0].asset.skeleton, 'R');
    // Options at 0: T-138 exactly.
    CHECK(mz.tips == ma.tips);
    // (a) every digit in the wider band, on the surface, nothing inside the cup, the wrist untouched.
    MESSAGE(std::format("{}: band out (T-138) {:.2f} mm, wider band {:.2f} mm; f0 off: clearance {:.2f} mm (skin r {:.2f})",
                        asset, ma.bandOut * 1e3, mw.bandOut * 1e3, mo.clear[1] * 1e3, r * 1e3));
    CHECK(mw.bandOut <= std::max(0.0f, ma.bandOut - 0.001f));
    CHECK(mw.gap <= 0.002f);
    CHECK(mw.deepest >= 0.0f);
    CHECK(glm::distance(mw.wrist, ma.wrist) <= 1e-5f);
    // (b) finger f0 (digit 1 after the thumb) clears the cup by half a skin radius (or opens fully); the others rest on
    // it, and the contacting digits are no further outside the band than with T-138.
    for (const Measure* m : {&mo, &mb}) {
      REQUIRE(m->clear.size() == 5);
      CHECK(m->clear[1] >= (asset == kSdf ? 0.0005f : 0.45f * r));  // the small SDF finger is fully open at ~1.8 mm
      CHECK(m->clear[1] <= 0.55f * r + 0.0005f);
      for (size_t i : {0u, 2u, 3u, 4u}) CHECK(std::abs(m->clear[i]) <= 0.002f);
      CHECK(m->deepest >= 0.0f);
      CHECK(glm::distance(m->wrist, ma.wrist) <= 1e-5f);
    }
    auto contactOut = [&](const Measure& m, vec2 bd) {
      float out = -1;
      for (size_t i : {0u, 2u, 3u, 4u}) out = std::max({out, bd.x - m.heights[i], m.heights[i] - bd.y});
      return out;
    };
    CHECK(contactOut(mo, narrow) <= std::max(0.0f, ma.bandOut) + 1e-4f);
    CHECK(contactOut(mb, wider) <= 0.0005f);
  }
}

// T-171 hands round 2: the opt-in action key "fingerClose" (scene/interaction.cpp). Only keys change.
namespace {
const Clip& generated(const SceneEvaluator& ev) {
  REQUIRE(ev.scene().animation.generated);
  return *ev.scene().animation.generated;
}
bool sameKeys(const Clip& a, const Clip& b) {
  if (a.tracks.size() != b.tracks.size()) return false;
  for (const auto& [name, t] : a.tracks) {
    const Track* o = b.find(name);
    if (!o || o->keys.size() != t.keys.size()) return false;
    for (size_t i = 0; i < t.keys.size(); ++i)
      if (t.keys[i].frame != o->keys[i].frame || t.keys[i].value != o->keys[i].value || t.keys[i].interp != o->keys[i].interp) return false;
  }
  return true;
}
}  // namespace

TEST_CASE("fingerClose (T-171): absent or false leaves every generated key as it was; bad values are load errors") {
  Scene s = graspScene(kBoy);
  s.actions[0]["band"] = {0.045, 0.09};
  auto plain = load(s);
  CHECK_FALSE(generated(*plain).find("actor/hand.R.stagger"));
  Scene off = s;
  off.actions[0]["fingerClose"] = false;
  CHECK(sameKeys(generated(*plain), generated(*load(off))));
  for (const char* bad : {R"(1)", R"({"preshape": 2})", R"({"stagger": -1})", R"({"settle": [0.9, 3]})", R"({"widen": [0.5, 0]})",
                          R"({"close": 1})", R"({"speed": 1})", R"({"rest": "relaxed"})", R"({"rest": {"curl": 2}})", R"({"rest": {"wrist": 1}})"}) {
    CAPTURE(bad);
    Scene b = s;
    b.actions[0]["fingerClose"] = Json::parse(bad);
    SceneEvaluator ev;
    CHECK_FALSE(ev.load(b, EvalOptions{2.5f, 1.0f, false, 0}));
  }
}

TEST_CASE("fingerClose (T-171): pre-shape, fingers land one by one and slowly, same held grasp, nothing enters the cup") {
  const vec2 band{0.045f, 0.09f};
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    Scene s = graspScene(asset);
    s.actions[0]["band"] = {band.x, band.y};
    Scene soft = s;
    soft.actions[0]["fingerClose"] = true;
    auto a = load(s), b = load(soft);
    // Keys: the weight rises to the pre-shape before the close, never passes 1 and never falls on the way in.
    const Track* w = generated(*b).find("actor/hand.R.grasp.weight");
    REQUIRE(w);
    CHECK(w->evaluate(14).x == doctest::Approx(0.5));  // close begins 6 frames before contact (f20) at the pre-shape
    CHECK(w->evaluate(17).x == doctest::Approx(0.88));  // the last 12 % takes the last 3 frames
    float prev = 0;
    for (double f = 5; f <= 20; f += 0.25) {
      const float x = w->evaluate(f).x;
      CHECK(x >= prev - 1e-6f);
      CHECK(x <= 1.0f);
      prev = x;
    }
    REQUIRE(generated(*b).find("actor/hand.R.stagger"));
    CHECK(generated(*b).find("actor/hand.R.stagger")->evaluate(20).x == doctest::Approx(2.0));
    // The held grasp is the same one (fingertips to 0.01 mm), the wrist does not move at all.
    const Measure ha = measure(*a, 32, band), hb = measure(*b, 32, band);
    REQUIRE(ha.tips.size() == hb.tips.size());
    for (size_t i = 0; i < ha.tips.size(); ++i) CHECK(glm::distance(ha.tips[i], hb.tips[i]) <= 1e-5f);
    for (double f = 5; f <= 32; ++f) CHECK(glm::distance(bonePos(*a, "hand.R", f), bonePos(*b, "hand.R", f)) <= 1e-6f);
    // Per frame: no digit deeper in the cup than the default path puts it (0.1 mm), and the largest fingertip step
    // (relative to the wrist, over the close f16-f32) is under half: the close is spread over more frames.
    const float r = fingertipRadius(a->characters()[0].asset.skeleton, 'R');
    std::array<double, 5> landA{}, landB{};
    float stepA = 0, stepB = 0;
    Measure pa, pb;
    for (double f = 5; f <= 32; ++f) {
      const Measure ma = measure(*a, f, band), mb = measure(*b, f, band);
      REQUIRE(mb.clear.size() == 5);
      for (size_t i = 0; i < 5; ++i) {
        CHECK(mb.clear[i] >= std::min(ma.clear[i], 0.0f) - 1e-4f);
        if (landA[i] == 0 && ma.clear[i] <= 0.0005f) landA[i] = f;
        if (landB[i] == 0 && mb.clear[i] <= 0.0005f) landB[i] = f;
      }
      if (f >= 17)  // the hand's orientation is set from f16.4 on: the fingertips move in the hand only
        for (size_t i = 0; i < 5; ++i) {
          stepA = std::max(stepA, glm::distance(ma.tips[i] - ma.wrist, pa.tips[i] - pa.wrist));
          stepB = std::max(stepB, glm::distance(mb.tips[i] - mb.wrist, pb.tips[i] - pb.wrist));
        }
      pa = ma, pb = mb;
    }
    MESSAGE(std::format("{}: largest fingertip step per frame {:.2f} -> {:.2f} mm (skin r {:.2f}); landing frames index..little "
                        "{:g} {:g} {:g} {:g} -> {:g} {:g} {:g} {:g}",
                        asset, stepA * 1e3, stepB * 1e3, r * 1e3, landA[4], landA[3], landA[2], landA[1], landB[4], landB[3], landB[2], landB[1]));
    CHECK(stepB < 0.5f * stepA);
    // Digits: thumb, f0 little .. f3 index. The index lands first, then one finger after the other.
    for (size_t i = 1; i < 5; ++i) CHECK(landB[i] > 0);
    CHECK(landB[4] <= landB[3]);
    CHECK(landB[3] <= landB[2]);
    CHECK(landB[2] <= landB[1]);
    CHECK(landB[1] - landB[4] >= 4);
    CHECK(landB[1] <= 20 + 3 * 2 + 1);
  }
}

TEST_CASE("fingerClose (T-171): widen keys the band fit and the T-157 wider band; rest keys the rest shape and returns to it") {
  Scene s = graspScene(kBoy);
  s.actions[0]["band"] = {0.045, 0.09};
  const Json restPose = Json::parse(R"({"curl": 0.25, "thumb": 0.12, "spread": 0.6, "fingers": {"index": {"curl": 0.14, "spread": 0.9}, "middle": {"curl": 0.22, "spread": 0.6}, "ring": {"curl": 0.29, "spread": 0.6}, "little": {"curl": 0.35, "spread": 0.9}}})");
  s.actions[0]["fingerClose"] = {{"widen", {0.005, 0.004}}, {"rest", restPose}};
  auto ev = load(s);
  const Clip& g = generated(*ev);
  REQUIRE(g.find("actor/hand.R.bandFit"));
  REQUIRE(g.find("actor/hand.R.bandFitOptions"));
  const vec3 o = g.find("actor/hand.R.bandFitOptions")->evaluate(20);
  CHECK(o.x == doctest::Approx(0.005));
  CHECK(o.y == 0.0f);
  CHECK(o.z == doctest::Approx(0.004));
  const auto rest = handShapeFromJson(Json{{"format", "plush.hand_shape"}, {"version", 1}, {"id", "rest"}, {"kind", "rest"}, {"pose", restPose}});
  REQUIRE(rest);
  for (int k = 0; k < 4; ++k) {
    const Track* t = g.find(std::format("actor/hand.R.f{}", k));
    REQUIRE(t);
    REQUIRE(rest->pose.fingers[size_t(k)]);
    CHECK(vec2(t->evaluate(5)) == *rest->pose.fingers[size_t(k)]);  // the rest shape before the reach
    CHECK(t->evaluate(20).x == doctest::Approx(0.03));              // the open hand at contact (the search closes it)
  }
  // Neighbouring fingers of the rest shape differ in curl (the cascade that tells them apart).
  for (int k = 1; k < 4; ++k) CHECK(rest->pose.fingers[size_t(k - 1)]->x - rest->pose.fingers[size_t(k)]->x >= 0.05f);
  // A reach without a grasp lets go again: the hand ends on the rest shape.
  Scene r = graspScene(kBoy);
  r.actions[0]["type"] = "reach";
  r.actions[0]["grasp"] = false;
  r.actions[0]["end"] = 34;
  r.actions[0]["fingerClose"] = {{"rest", restPose}};
  auto er = load(r);
  const Track* t = generated(*er).find("actor/hand.R.f0");
  REQUIRE(t);
  CHECK(vec2(t->evaluate(34)) == *rest->pose.fingers[0]);
}
