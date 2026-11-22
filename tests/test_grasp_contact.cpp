// T-138 (E4) / T-157: band fit for per-finger grasps (opt-in scene "interaction": {"graspFit": true} -> track
// "hand.<s>.bandFit"; anim/animation.cpp band step). Measured on the boy and girl test packages and the engine (SDF)
// skeleton, on felt_cup's `grip` socket with its own band and with a band too narrow for the hands.
#include <doctest/doctest.h>

#include <filesystem>
#include <initializer_list>
#include <format>
#include <memory>

#include "anim/hand_shape.h"
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"
#include "thumb_fit.h"

using namespace plush;
using plush::test::ThumbFit;
using plush::test::thumbFit;
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
  float fingerGap = 0, fingerBandOut = -1;  // gap, bandOut of the four fingers alone
  float thumbGap = 0, thumbBandOut = -1;    // the thumb's
  // T-190: a thumb inside its joint range (centres out of the cup, skin nowhere more than 2 mm in) can be on the surface
  // (tip skin within 2 mm) in the band; on the surface; clear (tip and knuckle skin within 2 mm); on the surface in the
  // band within 0.5 mm.
  bool thumbInBand = true, thumbOnSurface = true, thumbClear = true, thumbInBand05 = true;
  float thumbMargin = 0;  // T-190: how far the best in-range thumb that is no worse anywhere beats this one (m)
  bool outFingersAtLimit = true;  // T-190: every finger tip outside the band has its knuckle spread to the range limit
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
    (d[0] == 't' ? m.thumbGap : m.fingerGap) = std::max(d[0] == 't' ? m.thumbGap : m.fingerGap, std::abs(radial(tip) - R - r));
    m.deepest = std::min({m.deepest, radial(tip) - R, radial(kn) - R});
    const float h = glm::dot(tip - base, axis);
    m.bandOut = std::max({m.bandOut, band.x - h, h - band.y});
    float& out = d[0] == 't' ? m.thumbBandOut : m.fingerBandOut;
    out = std::max({out, band.x - h, h - band.y});
    m.tips.push_back(tip);
    m.clear.push_back(std::min(radial(tip), radial(kn)) - R - r);
    m.heights.push_back(h);
    if (d[0] == 'f') fingers.push_back(tip);
  }
  for (size_t i = 1; i < fingers.size(); ++i) m.minTipApart = std::min(m.minTipApart, glm::distance(fingers[i - 1], fingers[i]));
  m.wrist = bonePos(ev, "hand.R", f);
  // T-190: the thumb's criteria as violations: 0 tip skin within 2 mm of the surface, 1 tip and knuckle centres out of
  // the cup, 2 tip in the band, 3 tip and knuckle skin within 2 mm of the surface (`clear`), 4 tip on the far half from
  // the fingers (the grasp's opposed thumb), 5 no skin of the thumb chain more than 2 mm into the cup. thumbFit: which
  // sets of the old criteria a thumb inside its joint range can meet, and how far one beats this one.
  const int hb = sk.find("hand.R");
  REQUIRE(hb >= 0);
  const vec3 palmN = glm::normalize(mat3(g[size_t(hb)]) * handGrip(sk, hb, 'R').palmNormal);
  const vec3 split = glm::normalize(glm::cross(axis, palmN));
  float fingerSide = 0;
  for (const vec3& t : fingers) fingerSide += glm::dot(t - base, split);
  const float sideSign = fingerSide >= 0 ? 1.0f : -1.0f;
  auto radialOf = [&](vec3 p) {
    const vec3 q = p - base;
    return glm::length(q - axis * glm::dot(q, axis));
  };
  auto bad = [&](vec3 root, vec3 knuckle, vec3 tip) {
    float skin = 0;
    for (int k = 0; k <= 8; ++k) {
      const float t = float(k) / 8.0f;
      skin = std::max({skin, R + r - radialOf(glm::mix(root, knuckle, t)), R + r - radialOf(glm::mix(knuckle, tip, t))});
    }
    const float h = glm::dot(tip - base, axis);
    return std::array<float, 6>{std::max(0.0f, std::abs(radialOf(tip) - R - r) - 0.002f),
                                std::max({0.0f, R - radialOf(tip), R - radialOf(knuckle)}),
                                std::max({0.0f, band.x - h, h - band.y}),
                                std::max(0.0f, std::abs(std::min(radialOf(tip), radialOf(knuckle)) - R - r) - 0.002f),
                                std::max(0.0f, glm::dot(tip - base, split) * sideSign + 1e-6f), std::max(0.0f, skin - 0.002f)};
  };
  // Sets (each by a thumb whose centres are out of the cup and whose skin is nowhere more than 2 mm in): on the surface
  // in the band; on the surface; clear; on the surface in the band within 0.5 mm.
  const ThumbFit fit = thumbFit<6>(ev, 0, 'R', f, HandLimits{}.thumbBack, bad,
                                   {{0, 0, 0, -1, -1, 0}, {0, 0, -1, -1, -1, 0}, {-1, 0, -1, 0, -1, 0}, {0, 0, 0.0005f, -1, -1, 0}});
  m.thumbInBand = fit.reachable[0], m.thumbOnSurface = fit.reachable[1], m.thumbClear = fit.reachable[2];
  m.thumbInBand05 = fit.reachable[3];
  m.thumbMargin = fit.margin;
  {  // T-190: a finger whose tip is outside the band is spread to its range limit (a 0.1 deg tighter limit moves it)
    Pose pose;
    ev.characterGlobals(0, f, &pose);
    Pose tighter = pose;
    HandLimits lim;
    lim.knuckleSpread -= 0.1f;
    applyHandLimits(sk, tighter, 'R', lim);
    for (int k = 0; k < 4; ++k) {
      const int ia = sk.find(std::format("f{}a.R", k)), ib = sk.find(std::format("f{}b.R", k));
      if (ia < 0 || ib < 0) continue;
      const float h = glm::dot(vec3(g[size_t(ib)] * vec4(sk.bones[size_t(ib)].head - sk.bones[size_t(ia)].head, 1)) - base, axis);
      const quat d = glm::inverse(pose.local[size_t(ia)]) * tighter.local[size_t(ia)];
      if ((h < band.x || h > band.y) && glm::length(vec3(d.x, d.y, d.z)) < 1e-5f) m.outFingersAtLimit = false;
    }
  }
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
        CHECK(ma.fingerBandOut <= 0.0f);
        if (ma.thumbInBand) CHECK(ma.thumbBandOut <= 0.0f);  // T-190: the thumb too, wherever its range allows
        CHECK(ma.thumbMargin <= 0.002f);                     // T-190: no in-range thumb beats it by over 2 mm
        CHECK(mb.tips == ma.tips);
        continue;
      }
      CHECK(ma.bandOut > 0.002f);                  // T-051 alone leaves contacts outside this band
      // The fit pulls the finger contacts at least 1 mm further in, or every finger still outside is spread to its
      // joint limit (T-190: the knuckle spreads 30 deg at most), and never further out.
      CHECK((mb.fingerBandOut <= ma.fingerBandOut - 0.001f || mb.outFingersAtLimit));
      CHECK(mb.fingerBandOut <= ma.fingerBandOut + 1e-5f);
      if (mb.thumbInBand) CHECK(mb.thumbBandOut <= 0.0f);  // T-190: the thumb in the band wherever its range allows
      CHECK(mb.thumbMargin <= 0.002f);                     // T-190: no in-range thumb beats it by over 2 mm
      CHECK(mb.fingerGap <= 0.002f);                       // every finger tip still rests on the cup
      if (mb.thumbOnSurface) CHECK(mb.thumbGap <= 0.002f);  // T-190: the thumb too, wherever its range allows
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
      if (f >= 24) {  // held: every finger contact in the band; T-190: the thumb too wherever its range allows
        CHECK(ma.fingerBandOut <= 0.0f);
        if (ma.thumbInBand) CHECK(ma.thumbBandOut <= 0.0f);
        CHECK(ma.thumbMargin <= 0.002f);  // T-190: no in-range thumb beats it by over 2 mm
      }
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
    CHECK(mw.fingerGap <= 0.002f);
    if (mw.thumbOnSurface) CHECK(mw.thumbGap <= 0.002f);  // T-190: the thumb on the cup wherever its range allows
    CHECK(mw.thumbMargin <= 0.002f);                      // T-190: no in-range thumb beats it by over 2 mm
    CHECK(mw.deepest >= 0.0f);
    CHECK(glm::distance(mw.wrist, ma.wrist) <= 1e-5f);
    // (b) finger f0 (digit 1 after the thumb) clears the cup by half a skin radius (or opens fully); the others rest on
    // it, and the contacting digits are no further outside the band than with T-138.
    for (const Measure* m : {&mo, &mb}) {
      REQUIRE(m->clear.size() == 5);
      CHECK(m->clear[1] >= (asset == kSdf ? 0.0005f : 0.45f * r));  // the small SDF finger is fully open at ~1.8 mm
      CHECK(m->clear[1] <= 0.55f * r + 0.0005f);
      for (size_t i : {2u, 3u, 4u}) CHECK(std::abs(m->clear[i]) <= 0.002f);
      if (m->thumbClear) CHECK(std::abs(m->clear[0]) <= 0.002f);  // T-190: the thumb wherever its range allows
      CHECK(m->thumbMargin <= 0.002f);                            // T-190: no in-range thumb beats it by over 2 mm
      CHECK(m->deepest >= 0.0f);
      CHECK(glm::distance(m->wrist, ma.wrist) <= 1e-5f);
    }
    auto contactOut = [&](const Measure& m, vec2 bd, std::initializer_list<size_t> digits = {0u, 2u, 3u, 4u}) {
      float out = -1;
      for (size_t i : digits) out = std::max({out, bd.x - m.heights[i], m.heights[i] - bd.y});
      return out;
    };
    CHECK(contactOut(mo, narrow) <= std::max(0.0f, ma.bandOut) + 1e-4f);
    CHECK(contactOut(mb, wider, {2u, 3u, 4u}) <= 0.0005f);
    if (mb.thumbInBand05) CHECK(contactOut(mb, wider, {0u}) <= 0.0005f);  // T-190: the thumb wherever its range allows
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

// T-171 round 3 (owner review 2026-11-21): the opt-in fingerClose keys "wrap", "grip" and "clear". Measured on the
// character's own mesh: every vertex the hand bone (or a bone below it) carries, against the cup as a capped solid.
namespace {
struct HandOnCup {
  float deepest = 0;       // deepest hand vertex inside the solid (m, >= 0)
  float thumbTurn = 0;     // total rotation of thumbA from rest (deg)
  float minFlex = 1e9f;    // smallest signed bend of a finger joint about the hand's curl axis (deg; < 0 = backwards)
  float thumbUp = 0;       // dot(thumb side of the hand, world up)
  float wristBend = 0;     // angle between the forearm and the fingers (deg)
};
HandOnCup handOnCup(const SceneEvaluator& ev, double f) {
  const auto& ci = ev.characters()[0];
  const Skeleton& sk = ci.asset.skeleton;
  const auto g = ev.characterGlobals(0, f);
  const int hand = sk.find("hand.R");
  std::vector<char> under(sk.bones.size(), 0);
  under[size_t(hand)] = 1;
  for (size_t b = 0; b < sk.bones.size(); ++b)
    if (sk.bones[b].parent >= 0 && under[size_t(sk.bones[b].parent)]) under[b] = 1;
  const mat4 Pi = glm::inverse(ev.propWorld(0, f));
  const float R = cup().mesh.radius, H = cup().mesh.height;
  HandOnCup out;
  for (const SkinnedMesh& m : ci.rig.meshes)
    for (size_t i = 0; i < m.rest.positions.size(); ++i) {
      int top = 0;
      for (int j = 1; j < 4; ++j)
        if (m.weights[i][j] > m.weights[i][top]) top = j;
      if (!under[size_t(m.joints[i][top])]) continue;
      vec3 q(0);
      for (int j = 0; j < 4; ++j)
        if (m.weights[i][j] > 0)
          q += m.weights[i][j] * vec3(g[size_t(m.joints[i][j])] * vec4(m.rest.positions[i] - sk.bones[size_t(m.joints[i][j])].head, 1));
      const vec3 l = vec3(Pi * vec4(q, 1));
      const float dr = std::sqrt(l.x * l.x + l.z * l.z) - R, dy = std::abs(l.y - 0.5f * H) - 0.5f * H;
      out.deepest = std::max(out.deepest, -std::max(dr, dy));
    }
  auto local = [&](int child, int parent) {
    const mat3 m = glm::transpose(mat3(g[size_t(parent)])) * mat3(g[size_t(child)]);
    quat q = glm::normalize(glm::quat_cast(mat3(glm::normalize(m[0]), glm::normalize(m[1]), glm::normalize(m[2]))));
    return q.w < 0 ? -q : q;
  };
  const HandGrip grip = handGrip(sk, hand, 'R');
  const vec3 curl = glm::normalize(glm::cross(grip.fingerDir, grip.palmNormal));
  for (int k = 0; k < 4; ++k) {
    const int a = sk.find(std::format("f{}a.R", k)), b = sk.find(std::format("f{}b.R", k));
    if (a < 0 || b < 0) continue;
    for (auto [child, parent] : {std::pair{a, hand}, std::pair{b, a}}) {
      const quat q = local(child, parent);
      out.minFlex = std::min(out.minFlex, glm::degrees(2.0f * std::atan2(glm::dot(vec3(q.x, q.y, q.z), curl), q.w)));
    }
  }
  if (const int t = sk.find("thumbA.R"); t >= 0) out.thumbTurn = glm::degrees(glm::angle(local(t, sk.bones[size_t(t)].parent)));
  out.thumbUp = glm::normalize(mat3(g[size_t(hand)]) * glm::cross(grip.fingerDir, grip.palmNormal)).y;
  const vec3 fore = glm::normalize(vec3(g[size_t(hand)][3]) - vec3(g[size_t(sk.bones[size_t(hand)].parent)][3]));
  out.wristBend = glm::degrees(std::acos(std::clamp(glm::dot(fore, glm::normalize(mat3(g[size_t(hand)]) * grip.fingerDir)), -1.0f, 1.0f)));
  return out;
}
}  // namespace

TEST_CASE("fingerClose wrap (T-171 r3): seated palm, no vertex of the hand in the cup, thumb not turned round, joints only flex") {
  for (const char* bad : {R"({"wrap": 1})", R"({"grip": "up"})", R"({"grip": true})", R"({"clear": 1})", R"({"clear": "yes"})"}) {
    CAPTURE(bad);
    Scene b = graspScene(kBoy);
    b.actions[0]["fingerClose"] = Json::parse(bad);
    SceneEvaluator ev;
    CHECK_FALSE(ev.load(b, EvalOptions{2.5f, 1.0f, false, 0}));
  }
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    Scene s = graspScene(asset);
    s.actions[0]["band"] = {0.0, 0.1};
    Scene soft = s, wrap = s;
    soft.actions[0]["fingerClose"] = true;
    wrap.actions[0]["fingerClose"] = {{"wrap", true}};
    auto a = load(soft), b = load(wrap);
    CHECK_FALSE(generated(*a).find("actor/hand.R.wrap"));  // not implied by fingerClose: true
    CHECK_FALSE(generated(*a).find("actor/hand.R.seat"));
    const Track* w = generated(*b).find("actor/hand.R.wrap");
    const Track* seat = generated(*b).find("actor/hand.R.seat");
    REQUIRE(w);
    REQUIRE(seat);
    const float r = fingertipRadius(b->characters()[0].asset.skeleton, 'R');
    CHECK(w->evaluate(20).x == 1.0f);
    CHECK(w->evaluate(20).y > 0.4f * r);  // the measured finger and thumb thickness: of the order of the skeleton's guess
    CHECK(w->evaluate(20).y < 1.6f * r);
    CHECK(w->evaluate(20).z > 0.4f * r);
    CHECK(seat->evaluate(20).x > 0);
    // The palm's grip point (the seat) is on the socket at the contact.
    const vec3 socket = vec3((b->propWorld(0, 20) * assetTransformMatrix(cup().sockets.at("grip")))[3]);
    CHECK(glm::distance(b->handGripPoint(0, 'R', 20), socket) <= 0.0005f);
    const HandOnCup ha = handOnCup(*a, 32), hb = handOnCup(*b, 32);
    MESSAGE(std::format("{}: deepest hand vertex in the cup {:.2f} -> {:.2f} mm, thumb turned {:.0f} -> {:.0f} deg, least joint bend "
                        "{:.1f} -> {:.1f} deg", asset, ha.deepest * 1e3, hb.deepest * 1e3, ha.thumbTurn, hb.thumbTurn, ha.minFlex, hb.minFlex));
    CHECK(hb.deepest <= 0.003f);  // boy 0.0 mm; the girl's test hand keeps 2.7 mm at the thumb (3.2 without wrap)
    CHECK(hb.deepest <= ha.deepest + 1e-4f);
    CHECK(hb.thumbTurn <= 80.0f);
    CHECK(hb.minFlex >= -15.5f);
  }
}

TEST_CASE("fingerClose grip natural / clear (T-171 r3): thumb up with a keyed elbow; the way in stays out of the cup") {
  // The cup turned so that the authored grasp point makes the planner turn the right hand thumb down.
  Scene s = graspScene(kBoy);
  s.actions[0]["band"] = {0.0, 0.1};
  s.actions[0]["fingerClose"] = {{"wrap", true}};
  if (handOnCup(*load(s), 20).thumbUp > 0) {
    const vec3 socketWas = s.props[0].transform.translation + vec3(assetTransformMatrix({vec3(0), s.props[0].transform.rotationDeg, vec3(1)}) *
                                                                   vec4(cup().sockets.at("grip").translation, 0));
    s.props[0].transform.rotationDeg = {0, 0, 0};
    s.props[0].transform.translation = socketWas - cup().sockets.at("grip").translation;
  }
  auto site = load(s);
  REQUIRE(handOnCup(*site, 20).thumbUp < -0.9f);
  Scene n = s;
  n.actions[0]["fingerClose"] = {{"wrap", true}, {"grip", "natural"}};
  auto nat = load(n);
  const HandOnCup hs = handOnCup(*site, 32), hn = handOnCup(*nat, 32);
  MESSAGE(std::format("thumb side up {:.2f} -> {:.2f}; wrist bend {:.0f} -> {:.0f} deg; deepest vertex {:.2f} -> {:.2f} mm", hs.thumbUp, hn.thumbUp,
                      hs.wristBend, hn.wristBend, hs.deepest * 1e3, hn.deepest * 1e3));
  CHECK(hn.thumbUp > 0.9f);
  CHECK(hn.deepest <= 0.0015f);
  CHECK_FALSE(generated(*site).find("actor/elbow.hand.R"));
  REQUIRE(generated(*nat).find("actor/elbow.hand.R"));
  CHECK(glm::length(generated(*nat).find("actor/elbow.hand.R")->evaluate(20)) == doctest::Approx(1.0f).epsilon(0.01));
  CHECK(glm::length(generated(*nat).find("actor/elbow.hand.R")->evaluate(5)) == doctest::Approx(0.0f));
  // "site" is the default: the same keys as without the key.
  Scene sv = s;
  sv.actions[0]["fingerClose"] = {{"wrap", true}, {"grip", "site"}};
  CHECK(sameKeys(generated(*site), generated(*load(sv))));
  // clear: the hand rises with hanging fingers (an orientation waypoint) and is never deeper in the cup on the way in.
  Scene c = n;
  c.actions[0]["fingerClose"] = {{"wrap", true}, {"grip", "natural"}, {"clear", 0.006}};
  auto clr = load(c);
  CHECK(generated(*clr).find("actor/orient.hand.R")->keys.size() > generated(*nat).find("actor/orient.hand.R")->keys.size());
  float worstN = 0, worstC = 0;
  for (double f = 5; f <= 19; ++f) worstN = std::max(worstN, handOnCup(*nat, f).deepest), worstC = std::max(worstC, handOnCup(*clr, f).deepest);
  MESSAGE(std::format("deepest hand vertex in the cup on the way in: {:.2f} -> {:.2f} mm", worstN * 1e3, worstC * 1e3));
  CHECK(worstC <= worstN + 1e-4f);
  CHECK(glm::distance(bonePos(*clr, "hand.R", 20), bonePos(*nat, "hand.R", 20)) <= 0.0005f);  // the contact is the same
}

TEST_CASE("fingerClose grip natural (T-186): the prop stays where it is from the contact until the lift starts") {
  // The r3 grasp (wrap, grip natural, clear) of a cup close in front of the body, then a lift 8 frames after the
  // contact. The cup is the hand's from the contact on, so a hand that moves before the lift moves the cup with it:
  // here the arm-body pass pushed the wrist out of the body on the way in, and that push's ramp crossed the contact
  // and came back while the hand held the cup on the table (7 mm before T-186).
  Scene s = graspScene(kBoy);
  s.frameEnd = 60;
  auto probe = load(s);
  const vec3 shoulder = bonePos(*probe, "upperArm.R", 1), elbow = bonePos(*probe, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(*probe, "hand.R", 1));
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
  s.props[0].transform.translation = shoulder + vec3(0, -0.45f, 0.45f) * arm - vec3(rot * vec4(cup().sockets.at("grip").translation, 0));
  s.actions = Json::parse(R"([{"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "socket": "grip", "start": 5, "contact": 20,
      "band": [0.0, 0.1], "fingerClose": {"wrap": true, "grip": "natural", "clear": 0.006}},
    {"type": "hold", "character": "actor", "hand": "R", "by": [0, 0.12, 0], "start": 28, "end": 46}])");
  auto ev = load(s);
  REQUIRE(generated(*ev).find("actor/collision.push.hand.R"));  // the pass pushes this arm on the way in
  const mat4 P0 = ev->propWorld(0, 1);
  float moved = 0, turned = 0, armIn = 0;
  for (double f = 20; f <= 28; f += 0.5) {
    const mat4 P = ev->propWorld(0, f);
    moved = std::max(moved, glm::distance(vec3(P[3]), vec3(P0[3])));
    for (int k = 0; k < 3; ++k) turned = std::max(turned, glm::distance(vec3(P[k]), vec3(P0[k])));
    armIn = std::max(armIn, -ev->armClearanceAt(0, 'R', f).gap);
  }
  MESSAGE(std::format("cup from the contact f20 to the lift f28: moved {:.4f} mm, axes {:.6f}; arm into the body {:.2f} mm", moved * 1e3, turned,
                      armIn * 1e3));
  CHECK(moved <= 1e-5f);
  CHECK(turned <= 1e-5f);
  CHECK(armIn <= 0.0f);  // the arm stays out of the body while the hand holds still
  CHECK(glm::distance(vec3(ev->propWorld(0, 46)[3]), vec3(P0[3]) + vec3(0, 0.12f, 0)) <= 0.003f);  // and the lift still lifts
  // The span: from the contact to the lift's first frame.
  const Track* still = generated(*ev).find("actor/collision.still.hand.R");
  REQUIRE(still);
  CHECK(still->evaluate(19).x == 0.0f);
  CHECK(still->evaluate(20).x == 1.0f);
  CHECK(still->evaluate(28).x == 1.0f);
  CHECK(still->evaluate(29).x == 0.0f);
  // Without "grip": "natural" no span is written (the default path is unchanged).
  Scene d = s;
  d.actions[0]["fingerClose"] = {{"wrap", true}, {"clear", 0.006}};
  CHECK_FALSE(generated(*load(d)).find("actor/collision.still.hand.R"));
}
