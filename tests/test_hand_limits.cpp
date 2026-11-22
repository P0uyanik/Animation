// T-190: finger and thumb joint limits (anim/animation.h HandLimits, applyHandLimits, HandPose::limits). Every path
// that poses a hand ends inside the ranges: keyed shapes are untouched (bit for bit), a joint bent the wrong way is
// brought back to its range, the per-finger grasp solves its thumb inside the range and holds it steady from frame to
// frame, and clip-driven fingers are clamped too. Track "hand.<s>.limits" 0 turns it all off.
#include <doctest/doctest.h>

#include <array>
#include <filesystem>
#include <format>
#include <memory>

#include "anim/animation.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* kPackages[] = {"boy_yellow_hoodie_1.0.0/character.json", "girl_auburn_bun_glasses_m3/character.json",
                           "../../../content/characters/girl_white_hair.character.json"};

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

Scene actorScene(const char* asset) {
  Scene s;
  s.name = "hand limits test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 40;
  CharacterDesc c;
  c.name = "who";
  c.asset = asset;
  s.characters.push_back(c);
  return s;
}

// The digit bones of one hand: thumb (a, b), then per finger (a, b, third segment or -1).
struct Digits {
  int thumbA = -1, thumbB = -1;
  std::array<std::array<int, 3>, 4> f{};
  std::vector<int> all;
};
Digits digitsOf(const Skeleton& sk, char side) {
  const std::string s = std::string(".") + side;
  Digits d;
  d.thumbA = sk.find("thumbA" + s), d.thumbB = sk.find("thumbB" + s);
  d.all = {d.thumbA, d.thumbB};
  for (int k = 0; k < 4; ++k) {
    const int a = sk.find(std::format("f{}a{}", k, s)), b = sk.find(std::format("f{}b{}", k, s));
    int c = -1, n = 0;
    for (size_t i = 0; i < sk.bones.size(); ++i)
      if (sk.bones[i].parent == b) c = int(i), ++n;
    d.f[size_t(k)] = {a, b, n == 1 ? c : -1};
    for (int x : d.f[size_t(k)])
      if (x >= 0) d.all.push_back(x);
  }
  return d;
}
bool same(const quat& a, const quat& b) { return a.w == b.w && a.x == b.x && a.y == b.y && a.z == b.z; }
float degBetween(const quat& a, const quat& b) {
  const quat r = glm::inverse(glm::normalize(a)) * glm::normalize(b);  // atan2: exact zero for equal rotations
  return glm::degrees(2.0f * std::atan2(glm::length(vec3(r.x, r.y, r.z)), std::abs(r.w)));
}
float deg(const quat& q) { return degBetween(q, quat(1, 0, 0, 0)); }
// Largest change of any digit joint between two poses, degrees.
float digitStep(const Digits& d, const Pose& a, const Pose& b) {
  float m = 0;
  for (int i : d.all) m = std::max(m, degBetween(a.local[size_t(i)], b.local[size_t(i)]));
  return m;
}
// A pose with limits off: the engine's own rotation of each joint, used as the reference axis and direction.
Pose posed(const Skeleton& sk, char side, HandPose hp, bool limits) {
  Pose p = restPose(sk);
  hp.limits = limits;
  applyHandPose(sk, p, mat4(1), side, hp);
  return p;
}
// A grasp on a box face in front of the palm (half thickness r) or on a cylinder across the palm with a band.
HandPose graspPose(const Skeleton& sk, char side, bool box) {
  const HandGrip g = handGrip(sk, sk.find(std::string("hand.") + side), side);
  HandPose hp;
  hp.curl = 0.03f, hp.thumb = 0.05f, hp.spread = 0.35f;
  hp.grasp = true;
  if (box) {
    hp.graspRadius = 0.2f * g.palmLength;
    hp.graspCentre = g.palm + g.palmNormal * hp.graspRadius;
    hp.graspFace = g.palmNormal;
  } else {
    hp.graspRadius = 0.55f * g.palmLength;
    hp.graspCentre = g.palm + g.palmNormal * hp.graspRadius;
    hp.graspAxis = glm::normalize(glm::cross(g.fingerDir, g.palmNormal));
    hp.band = true;
    hp.bandLo = -0.8f * g.palmLength, hp.bandHi = 0.8f * g.palmLength;
  }
  return hp;
}

}  // namespace

TEST_CASE("hand limits (T-190): keyed hand poses are inside the ranges and stay bit for bit") {
  for (const char* pkg : kPackages) {
    auto ev = load(actorScene(pkg));
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    for (char side : {'L', 'R'}) {
      const Digits d = digitsOf(sk, side);
      REQUIRE(d.thumbA >= 0);
      for (float curl : {0.0f, 0.25f, 0.6f, 1.0f})
        for (float thumb : {0.0f, 0.15f, 1.0f})
          for (float spread : {-1.0f, 0.0f, 1.0f})
            for (int mode = 0; mode < 3; ++mode) {
              HandPose hp;
              hp.curl = curl, hp.thumb = thumb, hp.spread = spread;
              if (mode == 1) hp.index = 0.0f;                    // pointing
              if (mode == 2) hp.thumbPose = vec2(1.0f, thumb);  // per-finger pose, thumb fully opposed
              const Pose off = posed(sk, side, hp, false), on = posed(sk, side, hp, true);
              Pose again = off;
              applyHandLimits(sk, again, side);
              for (int i : d.all) {
                INFO(pkg << " " << side << " " << sk.bones[size_t(i)].name << " curl " << curl << " thumb " << thumb << " spread " << spread << " mode " << mode);
                CHECK(same(off.local[size_t(i)], on.local[size_t(i)]));
                CHECK(same(off.local[size_t(i)], again.local[size_t(i)]));
              }
            }
    }
  }
}

TEST_CASE("hand limits (T-190): joints bent the wrong way come back into their range") {
  for (const char* pkg : kPackages) {
    auto ev = load(actorScene(pkg));
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    const HandLimits lim;
    for (char side : {'L', 'R'}) {
      INFO(pkg << " " << side);
      const Digits d = digitsOf(sk, side);
      HandPose fist;
      fist.curl = 1.0f, fist.thumb = 1.0f;
      const Pose f = posed(sk, side, fist, false);  // every joint flexed: 75 / 95 deg fingers, 55 / 45 deg thumb
      // 1. Everything bent backwards by its full flexion.
      Pose p = restPose(sk);
      for (int i : d.all) p.local[size_t(i)] = glm::inverse(f.local[size_t(i)]);
      applyHandLimits(sk, p, side);
      for (int k = 0; k < 4; ++k) {
        const auto [a, b, c] = d.f[size_t(k)];
        if (a < 0 || b < 0) continue;
        CHECK(deg(p.local[size_t(a)]) == doctest::Approx(lim.knuckleBack).epsilon(0.01));  // knuckle: 15 deg back at most
        CHECK(degBetween(p.local[size_t(a)], f.local[size_t(a)]) == doctest::Approx(75.0f + lim.knuckleBack).epsilon(0.01));
        CHECK(deg(p.local[size_t(b)]) < 0.1f);  // a hinge never bends backwards
        if (c >= 0) CHECK(deg(p.local[size_t(c)]) < 0.1f);
      }
      CHECK(deg(p.local[size_t(d.thumbA)]) <= lim.thumbBack + 0.1f);  // laid back to the palm's plane at most
      CHECK(deg(p.local[size_t(d.thumbB)]) < 0.1f);
      Pose q = p;
      applyHandLimits(sk, q, side);  // a clamped pose is inside the range: clamping again changes nothing
      for (int i : d.all) CHECK(same(p.local[size_t(i)], q.local[size_t(i)]));
      // 2. Over-flexed (twice the full curl) and a thumb turned round (180 deg about its own flexion).
      p = restPose(sk);
      for (int i : d.all) p.local[size_t(i)] = f.local[size_t(i)] * f.local[size_t(i)];
      p.local[size_t(d.thumbA)] = f.local[size_t(d.thumbA)] * f.local[size_t(d.thumbA)] * f.local[size_t(d.thumbA)] * f.local[size_t(d.thumbA)];
      applyHandLimits(sk, p, side);
      for (int k = 0; k < 4; ++k) {
        const auto [a, b, c] = d.f[size_t(k)];
        if (a < 0 || b < 0) continue;
        CHECK(deg(p.local[size_t(a)]) == doctest::Approx(lim.knuckleFlex).epsilon(0.01));
        CHECK(deg(p.local[size_t(b)]) == doctest::Approx(lim.middleFlex).epsilon(0.01));
      }
      CHECK(deg(p.local[size_t(d.thumbA)]) <= lim.thumbFlex + 0.1f);
      CHECK(deg(p.local[size_t(d.thumbB)]) == doctest::Approx(lim.thumbEndFlex).epsilon(0.01));
      // 3. Rolled about its own length and bent sideways: a hinge keeps only its play.
      const vec3 along = glm::normalize(sk.bones[size_t(d.f[3][1])].head - sk.bones[size_t(d.f[3][0])].head);
      p = restPose(sk);
      p.local[size_t(d.f[3][0])] = glm::angleAxis(glm::radians(70.0f), along);
      p.local[size_t(d.f[3][1])] = glm::angleAxis(glm::radians(70.0f), along);
      p.local[size_t(d.thumbB)] = glm::angleAxis(glm::radians(-80.0f), glm::normalize(vec3(0.3f, 0.5f, 0.8f)));
      applyHandLimits(sk, p, side);
      auto rollAbout = [&](const quat& q) { return std::abs(glm::degrees(2.0f * std::atan2(glm::dot(vec3(q.x, q.y, q.z), along), q.w))); };
      CHECK(rollAbout(p.local[size_t(d.f[3][0])]) <= 2.0f * lim.play);  // 70 deg of roll: only the play is left
      CHECK(rollAbout(p.local[size_t(d.f[3][1])]) <= 2.0f * lim.play);
      CHECK(deg(p.local[size_t(d.f[3][1])]) <= 30.0f);
      CHECK(deg(p.local[size_t(d.thumbB)]) <= lim.thumbEndFlex + lim.play + 0.1f);
    }
  }
}

TEST_CASE("hand limits (T-190): a per-finger grasp keeps its thumb in range and steady from frame to frame") {
  for (const char* pkg : kPackages) {
    auto ev = load(actorScene(pkg));
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    for (char side : {'L', 'R'})
      for (bool box : {true, false}) {
        INFO(pkg << " " << side << (box ? " box face" : " cylinder band"));
        const Digits d = digitsOf(sk, side);
        HandPose hp = graspPose(sk, side, box);
        REQUIRE(hp.perFinger());
        // A held grasp carried through the scene: the hand's world frame moves and turns a little every frame.
        Pose prev;
        float worst = 0, turned = 0;
        for (int f = 0; f < 60; ++f) {
          const float t = float(f) / 59.0f;
          const mat4 world = glm::translate(mat4(1), vec3(0.3f * t, 0.05f * std::sin(6.0f * t), -0.2f * t)) *
                             glm::mat4_cast(glm::angleAxis(1.2f * t, glm::normalize(vec3(0.2f, 1.0f, 0.1f))));
          Pose p = restPose(sk);
          applyHandPose(sk, p, world, side, hp);
          Pose again = p;
          applyHandLimits(sk, again, side);
          for (int i : d.all) CHECK(same(p.local[size_t(i)], again.local[size_t(i)]));  // solved inside the range
          if (f > 0) worst = std::max(worst, digitStep(d, prev, p));
          turned = std::max(turned, deg(p.local[size_t(d.thumbA)]));
          prev = p;
        }
        CHECK(worst <= 25.0f);  // no digit joint jumps in a held grasp (the owner's flipping thumb, T-187 s020)
        CHECK(worst <= 3.0f);   // in fact the grasp is the hand's own: the same pose wherever the hand is
        CHECK(turned <= 100.0f);  // thumb base: opposition 60 + abduction 30 + flexion 66 at the very most, never turned round
        // Closing: the grasp weight rises, every joint moves a little per frame.
        worst = 0;
        for (int f = 0; f <= 20; ++f) {
          hp.graspWeight = float(f) / 20.0f;
          Pose p = restPose(sk);
          applyHandPose(sk, p, mat4(1), side, hp);
          if (f > 0) worst = std::max(worst, digitStep(d, prev, p));
          prev = p;
        }
        CHECK(worst <= 25.0f);
        // Fingers: no knuckle further back than its limit, no middle joint backwards (direction from the fist).
        HandPose fist;
        fist.curl = 1.0f;
        const Pose fp = posed(sk, side, fist, false);
        for (int k = 0; k < 4; ++k) {
          const int b = d.f[size_t(k)][1];
          if (b < 0) continue;
          const float angle = deg(prev.local[size_t(b)]);
          if (angle > 0.5f) CHECK(degBetween(prev.local[size_t(b)], fp.local[size_t(b)]) < 95.0f + 0.5f);  // flexed, not extended
        }
      }
  }
}

TEST_CASE("hand limits (T-190): track hand.<s>.limits 0 gives the pose before the limits; clip-driven thumbs are clamped") {
  // 1. The switch on a grasping hand (the tracks, through applyConstraints): 0 = exactly HandPose::limits false.
  {
    auto ev = load(actorScene(kPackages[0]));
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    const HandPose hp = graspPose(sk, 'R', true);
    Clip clip;
    auto key = [&](const std::string& name, vec3 v) { clip.tracks["who/hand.R" + name].setKey(Key{1, v, Interp::Step}); };
    key("", vec3(hp.curl, hp.thumb, hp.spread));
    key(".grasp", hp.graspCentre);
    key(".graspRadius", vec3(hp.graspRadius));
    key(".graspFace", hp.graspFace);
    Pose pOn = restPose(sk), pOff = restPose(sk);
    applyConstraints(sk, clip, "who/", 10, mat4(1), pOn);
    key(".limits", vec3(0));
    applyConstraints(sk, clip, "who/", 10, mat4(1), pOff);
    const Digits d = digitsOf(sk, 'R');
    const Pose expectOn = posed(sk, 'R', hp, true), expectOff = posed(sk, 'R', hp, false);
    for (int i : d.all) {
      INFO(sk.bones[size_t(i)].name);
      CHECK(same(pOn.local[size_t(i)], expectOn.local[size_t(i)]));
      CHECK(same(pOff.local[size_t(i)], expectOff.local[size_t(i)]));
    }
    CHECK(digitStep(d, pOn, pOff) > 5.0f);  // the search before T-190 leaves the range on this grasp: the switch is not a no-op
  }
  // 2. Clip layers: the idle clip's retargeted thumbs (laid back and rolled before T-190) end inside the range.
  for (const char* pkg : {kPackages[0], kPackages[1]}) {
    Scene s = actorScene(pkg);
    s.actions = Json::array({{{"type", "clip"}, {"character", "who"}, {"file", (kRoot / "content/clips/idle_relaxed.clip.json").string()}, {"base", true}}});
    Scene offScene = s;
    for (char side : {'L', 'R'}) offScene.animation.tracks[std::string("who/hand.") + side + ".limits"].setKey(Key{1, vec3(0), Interp::Step});
    auto on = load(s), off = load(offScene);
    const Skeleton& sk = on->characters()[0].asset.skeleton;
    for (char side : {'L', 'R'}) {
      INFO(pkg << " " << side);
      const Digits d = digitsOf(sk, side);
      Pose pOn, pOff;
      on->characterGlobals(0, 20, &pOn);
      off->characterGlobals(0, 20, &pOff);
      Pose again = pOn, clamped = pOff;
      applyHandLimits(sk, again, side);
      applyHandLimits(sk, clamped, side);
      for (int i : d.all) {
        INFO(sk.bones[size_t(i)].name << " " << degBetween(pOn.local[size_t(i)], again.local[size_t(i)]));
        CHECK(same(pOn.local[size_t(i)], again.local[size_t(i)]));  // inside the range
      }
      CHECK(digitStep(d, pOn, clamped) < 0.05f);  // = the unlimited clip pose, clamped
      CHECK(digitStep(d, pOn, pOff) > 5.0f);      // and the unlimited pose was outside it
    }
  }
}
