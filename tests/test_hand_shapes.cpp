// T-051: per-finger grasps on the grasp sites (anim/animation.h applyHandPose with a band / face / per-digit tracks)
// and the hand-shape table (anim/hand_shape.h, content/hand_shapes/*.json). Measured on the boy and girl test
// packages and the engine (SDF) skeleton.
#include <doctest/doctest.h>

#include <array>
#include <filesystem>
#include <format>
#include <fstream>
#include <iterator>
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

Scene baseScene() {
  Scene s;
  s.name = "hand shape test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 60;
  return s;
}

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

vec3 bonePos(const SceneEvaluator& ev, size_t c, const char* bone, double f) {
  const int b = ev.characters()[c].asset.skeleton.find(bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(c, f)[size_t(b)][3]);
}

const PropAsset& cupAsset() {
  static const PropAsset a = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  return a;
}

// The cup in front of the right shoulder, its `socket` facing the right hand (as test_interaction's pick-up).
PropDesc cupFor(const SceneEvaluator& probe, size_t c, const std::string& socket, float yawCupDeg) {
  PropDesc cup;
  cup.name = "cup";
  cup.id = "prop.felt_cup";
  const vec3 shoulder = bonePos(probe, c, "upperArm.R", 1), elbow = bonePos(probe, c, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(probe, c, "hand.R", 1));
  const vec3 grip = shoulder + vec3(0.04f, -0.45f, 0.85f) * arm;
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, yawCupDeg, 0), vec3(1)});
  cup.transform.translation = grip - vec3(rot * vec4(cupAsset().sockets.at(socket).translation, 0));
  cup.transform.rotationDeg = {0, yawCupDeg, 0};
  return cup;
}

struct Digits {
  std::vector<vec3> tips, knuckles;  // thumb first, then fingers 0..3 (missing digits skipped)
};
Digits digitsAt(const SceneEvaluator& ev, size_t c, char side, double f) {
  const Skeleton& sk = ev.characters()[c].asset.skeleton;
  const auto g = ev.characterGlobals(c, f);
  Digits d;
  const std::string s = std::string(".") + side;
  std::vector<std::pair<std::string, std::string>> chains{{"thumbA", "thumbB"}};
  for (int k = 0; k < 4; ++k) chains.push_back({std::format("f{}a", k), std::format("f{}b", k)});
  for (auto& [a, b] : chains) {
    const int ia = sk.find(a + s), ib = sk.find(b + s);
    if (ia < 0 || ib < 0) continue;
    d.knuckles.push_back(vec3(g[size_t(ib)][3]));
    d.tips.push_back(vec3(g[size_t(ib)] * vec4(sk.bones[size_t(ib)].head - sk.bones[size_t(ia)].head, 1)));
  }
  return d;
}

// Band of a grasp site in the hand-rest-frame convention of the track contract (design section 5): distances from
// the grasp centre along the grasp axis. The cup's axis is its +y; the grasp centre sits at the socket's height.
vec3 bandTrack(const std::string& socket, vec2 bandProp, int thumb) {
  const float y = cupAsset().sockets.at(socket).translation.y;
  return vec3(bandProp.x - y, bandProp.y - y, float(thumb));
}

// T-190: is the thumb as good as its joint range allows? `bad(root, knuckle, tip)` gives a pose's violations of the
// criteria (each >= 0, 0 = met; world positions of the thumb chain). Every thumb pose on a grid of the thumb's joint
// coordinates is tried (anim/animation.h thumbJointRotations: opposition, abduction and end flexion every 5 deg,
// flexion every 3 deg from the laid-back limit `backDeg` to full flexion; the rest of the hand and arm as evaluated
// at frame f). Returns whether some pose in range meets the first `Old` criteria (the ones the test had before; each
// within `tol`), and
// the dominance margin of the evaluated thumb: the most any pose that is no worse on every criterion is better on one
// (0 = nothing in range beats it).
struct ThumbFit {
  bool reachable = false;
  float margin = 0;
};
template <size_t N, size_t Old, class Bad>
ThumbFit thumbFit(const SceneEvaluator& ev, size_t c, char side, double f, float backDeg, const Bad& bad,
                  const std::array<float, Old>& tol = {}) {
  const Skeleton& sk = ev.characters()[c].asset.skeleton;
  const std::string s = std::string(".") + side;
  const int ia = sk.find("thumbA" + s), ib = sk.find("thumbB" + s);
  REQUIRE(ia >= 0);
  REQUIRE(ib >= 0);
  Pose pose;
  const auto g = ev.characterGlobals(c, f, &pose);
  const Bone &A = sk.bones[size_t(ia)], &B = sk.bones[size_t(ib)];
  REQUIRE(A.parent >= 0);
  REQUIRE(B.parent == ia);
  const mat4 P = g[size_t(A.parent)];
  auto offset = [&](int i) { return size_t(i) < pose.offset.size() ? pose.offset[size_t(i)] : vec3(0); };
  const mat4 toA = P * glm::translate(mat4(1), A.head - sk.bones[size_t(A.parent)].head + offset(ia));
  const mat4 toB = glm::translate(mat4(1), B.head - A.head + offset(ib));
  const vec4 tipB(B.head - A.head, 1);
  const vec3 root(toA[3]);
  const mat4 own = toA * glm::mat4_cast(pose.local[size_t(ia)]) * toB * glm::mat4_cast(pose.local[size_t(ib)]);
  REQUIRE(glm::distance(vec3(own * tipB), vec3(g[size_t(ib)] * tipB)) <= 1e-5f);  // the chain below is the evaluator's
  const std::array<float, N> mine = bad(root, vec3(own[3]), vec3(own * tipB));
  const HandLimits lim;
  ThumbFit fit;
  for (float opp = 0; opp <= lim.thumbOpposition + 1e-3f; opp += 5)
    for (float abd = -lim.thumbAbductionIn; abd <= lim.thumbAbductionOut + 1e-3f; abd += 5)
      for (float flex = -backDeg; flex <= lim.thumbFlex + 1e-3f; flex += 3)
        for (float end = 0; end <= lim.thumbEndFlex + 1e-3f; end += 5) {
          const auto r = thumbJointRotations(sk, side, opp, abd, flex, end);
          const mat4 gb = toA * glm::mat4_cast(r.first) * toB * glm::mat4_cast(r.second);
          const std::array<float, N> v = bad(root, vec3(gb[3]), vec3(gb * tipB));
          bool met = true, noWorse = true;
          float better = 0;
          for (size_t i = 0; i < N; ++i) {
            met &= i >= Old || v[i] <= tol[std::min(i, Old - 1)];
            noWorse &= v[i] <= mine[i];
            better = std::max(better, mine[i] - v[i]);
          }
          fit.reachable |= met;
          if (noWorse) fit.margin = std::max(fit.margin, better);
        }
  return fit;
}

struct CupMeasure {
  float worstGap = 0;       // max |tip skin - surface| (m)
  float deepest = 1;        // min (tip or knuckle centre radial distance - radius): < 0 = inside the proxy
  float bandOut = 0;        // max distance of a fingertip centre outside the band (m)
  float thumbSide = 0;      // thumb tip on the split plane, signed: < 0 = opposite half from the fingertips
  float fingerGap = 0, fingerBandOut = 0;  // worstGap, bandOut of the four fingers alone
  bool thumbReachable = true;  // T-190: some thumb pose inside the joint range meets the T-051 criteria
  float thumbMargin = 0;       // T-190: how far the best in-range thumb that is no worse anywhere beats this one (m)
  vec3 wrist{0}, palm{0};
};

CupMeasure measureCup(const SceneEvaluator& ev, char side, double f, vec2 bandProp, bool withBand) {
  const Skeleton& sk = ev.characters()[0].asset.skeleton;
  const mat4 P = ev.propWorld(0, f);
  const vec3 axis = glm::normalize(vec3(P[1])), base = vec3(P[3]);
  const float R = cupAsset().mesh.radius;
  const float r = fingertipRadius(sk, side);
  const Digits d = digitsAt(ev, 0, side, f);
  CupMeasure m;
  auto radial = [&](vec3 p) {
    vec3 q = p - base;
    return glm::length(q - axis * glm::dot(q, axis));
  };
  for (size_t i = 0; i < d.tips.size(); ++i) {
    m.worstGap = std::max(m.worstGap, std::abs(radial(d.tips[i]) - R - r));
    if (i > 0) m.fingerGap = std::max(m.fingerGap, std::abs(radial(d.tips[i]) - R - r));
    m.deepest = std::min({m.deepest, radial(d.tips[i]) - R, radial(d.knuckles[i]) - R});
    if (withBand) {  // the thumb (opposed) too
      const float h = glm::dot(d.tips[i] - base, axis);
      m.bandOut = std::max({m.bandOut, bandProp.x - h, h - bandProp.y});
      if (i > 0) m.fingerBandOut = std::max({m.fingerBandOut, bandProp.x - h, h - bandProp.y});
    }
  }
  const int hb = sk.find(std::string("hand.") + side);
  const mat4 hg = ev.characterGlobals(0, f)[size_t(hb)];
  const HandGrip grip = handGrip(sk, hb, side);
  const vec3 palmN = glm::normalize(mat3(hg) * grip.palmNormal);
  const vec3 split = glm::normalize(glm::cross(axis, palmN));
  float fingers = 0;
  for (size_t i = 1; i < d.tips.size(); ++i) fingers += glm::dot(d.tips[i] - base, split);
  const float sideSign = fingers >= 0 ? 1.0f : -1.0f;
  m.thumbSide = glm::dot(d.tips[0] - base, split) * sideSign;
  // T-190: the T-051 criteria for the thumb as violations (tip skin within 2 mm of the surface, tip and knuckle
  // centres out of the cup, tip in the band, tip on the far half from the fingers), and no skin of the thumb chain
  // more than 2 mm into the cup; thumbFit: whether a thumb in range meets them all, and how far one beats this one.
  const ThumbFit fit = thumbFit<5, 4>(ev, 0, side, f, HandLimits{}.thumbBack, [&](vec3 root, vec3 knuckle, vec3 tip) {
    float skin = 0;
    for (int k = 0; k <= 8; ++k) {
      const float t = float(k) / 8.0f;
      skin = std::max({skin, R + r - radial(glm::mix(root, knuckle, t)), R + r - radial(glm::mix(knuckle, tip, t))});
    }
    const float h = glm::dot(tip - base, axis);
    return std::array<float, 5>{std::max(0.0f, std::abs(radial(tip) - R - r) - 0.002f),
                                std::max({0.0f, R - radial(tip), R - radial(knuckle)}),
                                withBand ? std::max({0.0f, bandProp.x - h, h - bandProp.y}) : 0.0f,
                                std::max(0.0f, glm::dot(tip - base, split) * sideSign + 1e-6f), std::max(0.0f, skin - 0.002f)};
  });
  m.thumbReachable = fit.reachable;
  m.thumbMargin = fit.margin;
  m.wrist = vec3(hg[3]);
  m.palm = ev.handGripPoint(0, side, f);
  return m;
}

}  // namespace

TEST_CASE("per-finger grasp: cup, both bands, three skeletons - tips on the surface, in the band, thumb opposed (T-051)") {
  struct Site {
    const char* socket;
    vec2 band;  // prop frame, from felt_cup's affordances
  };
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    for (Site site : {Site{"grip", {0.045f, 0.09f}}, Site{"grip_b", {0.01f, 0.055f}}}) {
      CAPTURE(asset);
      CAPTURE(site.socket);
      Scene scene = baseScene();
      CharacterDesc c;
      c.name = "actor";
      c.asset = asset;
      scene.characters.push_back(c);
      auto probe = load(scene);
      scene.props.push_back(cupFor(*probe, 0, site.socket, site.socket == std::string("grip") ? 180.0f : 0.0f));
      scene.actions = Json::parse(std::format(
          R"([{{"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "socket": "{}", "start": 5, "contact": 20}}])",
          site.socket));
      auto plain = load(scene);
      Scene banded = scene;
      banded.animation.tracks["actor/hand.R.band"].setKey(Key{5, bandTrack(site.socket, site.band, 0), Interp::Step});
      auto ev = load(banded);
      for (double f : {24.0, 30.0}) {
        const CupMeasure a = measureCup(*plain, 'R', f, site.band, false), b = measureCup(*ev, 'R', f, site.band, true);
        MESSAGE(std::format("{} {} f{}: thumb criteria reachable in range {}, beaten by {:.2f} mm", asset, site.socket, f, b.thumbReachable, b.thumbMargin * 1e3));
        MESSAGE(std::format("{} {} f{}: tip gap {:.2f} mm (single search {:.2f}), deepest {:.2f} mm, band out {:.2f} mm, "
                            "thumb side {:.1f} mm (single search {:.1f}), wrist moved {:.4f} mm, palm moved {:.4f} mm",
                            asset, site.socket, f, b.worstGap * 1e3, a.worstGap * 1e3, b.deepest * 1e3, b.bandOut * 1e3,
                            b.thumbSide * 1e3, a.thumbSide * 1e3, glm::distance(a.wrist, b.wrist) * 1e3,
                            glm::distance(a.palm, b.palm) * 1e3));
        CHECK(b.fingerGap <= 0.002f);  // every finger tip on the cup
        CHECK(b.deepest >= 0.0f);
        CHECK(b.fingerBandOut <= 0.0f);  // every finger tip in the band
        if (b.thumbReachable) {  // T-190: a thumb inside its joint range can meet the T-051 criteria: this one does
          CHECK(b.worstGap <= 0.002f);
          CHECK(b.bandOut <= 0.0f);
          CHECK(b.thumbSide < 0.0f);
        }
        // T-190: and no thumb in range is at least as good on every criterion (contact, out of the cup, band, far side,
        // no skin 2 mm into the cup) and more than the 2 mm contact tolerance better on one: opposed as far as it goes.
        CHECK(b.thumbMargin <= 0.002f);
        CHECK(glm::distance(a.wrist, b.wrist) <= 1e-5f);
        CHECK(glm::distance(a.palm, b.palm) <= 1e-5f);
      }
    }
  }
}

namespace {

std::unique_ptr<SceneEvaluator> probeFor(const char* asset) {
  Scene scene = baseScene();
  CharacterDesc c;
  c.name = "actor";
  c.asset = asset;
  scene.characters.push_back(c);
  return load(scene);
}

}  // namespace

TEST_CASE("per-finger grasp: box face, three skeletons - tips on the face, none inside the box (T-051)") {
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    CAPTURE(asset);
    auto probe = probeFor(asset);
    const Skeleton& sk = probe->characters()[0].asset.skeleton;
    for (char side : {'L', 'R'}) {
      const int hb = sk.find(std::string("hand.") + side);
      REQUIRE(hb >= 0);
      const HandGrip grip = handGrip(sk, hb, side);
      const vec3 n = glm::normalize(grip.palmNormal);
      const float half = 0.03f;  // a 6 cm deep box with its face on the palm point
      HandPose hp;
      hp.curl = 0.08f, hp.thumb = 0.3f, hp.spread = 0.0f;  // palm approach
      hp.grasp = true;
      hp.graspCentre = grip.palm + n * half;
      hp.graspRadius = half;
      hp.graspFace = n;
      Pose p = restPose(sk);
      applyHandPose(sk, p, mat4(1), side, hp);
      const vec3 head = sk.bones[size_t(hb)].head, centre = head + hp.graspCentre;
      const float r = fingertipRadius(sk, side);
      float worst = 0, deepest = 1;
      for (const vec3& t : fingertips(sk, p, mat4(1), side)) {
        const float sd = std::abs(glm::dot(t - centre, n)) - half;
        worst = std::max(worst, std::abs(sd - r));
        deepest = std::min(deepest, sd);
      }
      MESSAGE(std::format("{} {}: box face, tip skin gap worst {:.2f} mm, deepest tip centre {:.2f} mm (skin radius {:.2f} mm)",
                          asset, side, worst * 1e3, deepest * 1e3, r * 1e3));
      CHECK(worst <= 0.002f);
      CHECK(deepest >= 0.0f);
    }
  }
}

TEST_CASE("per-finger grasp: fingers close index -> little and open little -> index, 1 f apart (T-051)") {
  auto probe = probeFor(kSdf);
  const Skeleton& sk = probe->characters()[0].asset.skeleton;
  const HandGrip grip = handGrip(sk, sk.find("hand.R"), 'R');
  Clip clip;
  auto key = [&](const std::string& n, double f, vec3 v, Interp i = Interp::Linear) { clip.tracks[n].setKey(Key{f, v, i}); };
  // A stick across the hand (its axis = the across direction), closing over frames 10..14, opening 30..34.
  const vec3 across = glm::normalize(glm::cross(grip.fingerDir, grip.palmNormal));
  key("hand.R", 0, vec3(0.03f, 0.05f, 0.35f), Interp::Step);
  key("hand.R.grasp", 0, grip.palm + glm::normalize(grip.palmNormal) * 0.02f, Interp::Step);
  key("hand.R.graspRadius", 0, vec3(0.02f), Interp::Step);
  key("hand.R.graspAxis", 0, across, Interp::Step);
  key("hand.R.grasp.weight", 10, vec3(0));
  key("hand.R.grasp.weight", 14, vec3(1));
  key("hand.R.grasp.weight", 30, vec3(1));
  key("hand.R.grasp.weight", 34, vec3(0));
  Clip banded = clip;
  banded.tracks["hand.R.band"].setKey(Key{0, vec3(-0.05f, 0.05f, 0), Interp::Step});
  // Closure of finger k at frame f: its first segment's rotation away from the open pose (frame 0).
  auto closure = [&](const Clip& c, double f, int k) {
    Pose p = restPose(sk), p0 = restPose(sk);
    applyConstraints(sk, c, "", f, mat4(1), p);
    applyConstraints(sk, c, "", 0, mat4(1), p0);
    const int b = sk.find(std::format("f{}a.R", k));
    return glm::degrees(2.0f * std::acos(std::min(1.0f, std::abs(glm::dot(glm::normalize(p.local[size_t(b)]),
                                                                          glm::normalize(p0.local[size_t(b)]))))));
  };
  // Closing at frame 13 (weight 0.75): index 0.75, middle 0.5, ring 0.25, little 0 (it starts 3 f late).
  CHECK(closure(banded, 13, 3) > closure(banded, 13, 2));
  CHECK(closure(banded, 13, 2) > closure(banded, 13, 1));
  CHECK(closure(banded, 13, 1) > closure(banded, 13, 0));
  CHECK(closure(banded, 13, 0) < 0.01f);
  CHECK(closure(banded, 15, 0) < closure(banded, 16, 0));                    // the little finger closes after 14
  CHECK(closure(banded, 17, 0) == doctest::Approx(closure(banded, 20, 0)));  // and is done 3 f after it
  // Opening at frame 32 (weight 0.5): the little finger leads, the index is still closed (it follows 3 f later).
  CHECK(closure(banded, 32, 0) < closure(banded, 32, 3));
  CHECK(closure(banded, 32, 3) == doctest::Approx(closure(banded, 25, 3)));
  CHECK(closure(banded, 35, 3) > closure(banded, 37, 3));
  CHECK(closure(banded, 37, 3) < 0.01f);
  // Without a band (or a stagger track) every finger follows the one weight, as before.
  MESSAGE(std::format("frame 13 closure (deg): banded index {:.1f}, middle {:.1f}, ring {:.1f}, little {:.1f}; single "
                      "search index {:.1f}, little {:.1f}",
                      closure(banded, 13, 3), closure(banded, 13, 2), closure(banded, 13, 1), closure(banded, 13, 0),
                      closure(clip, 13, 3), closure(clip, 13, 0)));
  CHECK(closure(clip, 13, 0) > 0.5f);  // single search: no stagger, the little finger closes with the others
  Clip noStagger = banded;            // a stagger track of 0 turns it off under a band too
  noStagger.tracks["hand.R.stagger"].setKey(Key{0, vec3(0), Interp::Step});
  CHECK(closure(noStagger, 13, 0) > 0.5f);
}

TEST_CASE("per-finger grasp: without T-051 tracks the hand pose is the single search, bit for bit (T-051)") {
  CHECK_FALSE(HandPose{}.perFinger());
  auto probe = probeFor(kGirl);
  const Skeleton& sk = probe->characters()[0].asset.skeleton;
  Clip clip;
  clip.tracks["hand.L"].setKey(Key{0, vec3(0.4f, 0.3f, 0.2f), Interp::Step});
  clip.tracks["hand.L.grasp"].setKey(Key{0, vec3(0.01f, -0.04f, 0.02f), Interp::Step});
  clip.tracks["hand.L.graspRadius"].setKey(Key{0, vec3(0.015f), Interp::Step});
  Clip withEmpty = clip;  // tracks without keys are absent tracks
  for (const char* t : {"hand.L.band", "hand.L.f0", "hand.L.thumb", "hand.L.stagger", "hand.L.graspFace"}) withEmpty.tracks[t];
  Pose a = restPose(sk), b = restPose(sk);
  applyConstraints(sk, clip, "", 5, mat4(1), a);
  applyConstraints(sk, withEmpty, "", 5, mat4(1), b);
  bool same = true;
  for (size_t i = 0; i < a.local.size(); ++i)
    for (int k = 0; k < 4; ++k) same &= a.local[i][k] == b.local[i][k];
  CHECK(same);
}

TEST_CASE("hand-shape table: loads every shape of content/hand_shapes with the design 2.3 values (T-051)") {
  const fs::path dir = findHandShapeDir(kRoot / "episodes");
  REQUIRE(dir == kRoot / "content/hand_shapes");
  auto t = loadHandShapeTable(dir);
  REQUIRE_MESSAGE(t, (t ? "" : t.error().message));
  for (const char* id : {"wrap", "pinch", "palm", "hook", "cradle", "relaxed", "point", "count_1", "count_2", "count_3", "chin_touch"})
    CHECK_MESSAGE(t->find(id), id);
  CHECK(t->shapes.size() == 11);
  struct Row {
    const char* id;
    vec3 approach;
    vec3 closed;
    HandShapeSearch search;
  };
  for (const Row& r : {Row{"wrap", {0.03f, 0.05f, 0.35f}, {0.03f, 0.05f, 0.35f}, HandShapeSearch::All},
                       Row{"pinch", {0.1f, 0.2f, 0.1f}, {0.6f, 0.2f, 0.1f}, HandShapeSearch::Pinch},
                       Row{"palm", {0.08f, 0.3f, 0.0f}, {0.15f, 0.35f, 0.0f}, HandShapeSearch::None},
                       Row{"hook", {0.2f, 0.1f, 0.0f}, {0.7f, 0.1f, 0.0f}, HandShapeSearch::None},
                       Row{"cradle", {0.1f, 0.25f, 0.2f}, {0.3f, 0.25f, 0.2f}, HandShapeSearch::None}}) {
    CAPTURE(r.id);
    const HandShape& s = *t->find(r.id);
    CHECK(s.kind == "grasp");
    REQUIRE(s.approach);
    CHECK(vec3(s.approach->curl, s.approach->thumb, s.approach->spread) == r.approach);
    CHECK(vec3(s.pose.curl, s.pose.thumb, s.pose.spread) == r.closed);
    CHECK(s.search == r.search);
  }
  CHECK(*t->find("pinch")->pose.index == doctest::Approx(0.1f));
  CHECK(*t->find("pinch")->pinchRadius == doctest::Approx(0.01f));
  CHECK(t->find("cradle")->palmUp);
  CHECK(t->find("wrap")->thumb == HandPose::Thumb::Opposed);
  // relaxed = the engine's rest hand (HandPose defaults, interaction kRelaxed)
  const HandShape& relaxed = *t->find("relaxed");
  CHECK(relaxed.kind == "rest");
  CHECK(vec3(relaxed.pose.curl, relaxed.pose.thumb, relaxed.pose.spread) == vec3(HandPose{}.curl, HandPose{}.thumb, HandPose{}.spread));
  // Shared data only: no character id or name in any shape file.
  std::vector<std::string> names{"boy", "girl"};
  for (const auto& e : fs::directory_iterator(kRoot / "assets/characters")) names.push_back(e.path().filename().string());
  for (const auto& [id, s] : t->shapes) {
    std::ifstream in(s.path);
    const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    for (const auto& n : names) CHECK_MESSAGE(text.find(n) == std::string::npos, id << " names " << n);
  }
  // Personality bias: the rest curl moves, clamped.
  CHECK(biased(relaxed, 0.1f).pose.curl == doctest::Approx(0.35f));
  CHECK(biased(relaxed, 2.0f).pose.curl == doctest::Approx(1.0f));
}

TEST_CASE("hand-shape table: validation reports every problem (T-051)") {
  auto bad = [](const char* text) {
    auto r = handShapeFromJson(Json::parse(text), "x");
    return r ? std::string() : r.error().message;
  };
  CHECK(bad(R"({"format": "plush.hand_shape", "version": 1, "id": "x", "kind": "rest", "pose": {"curl": 0.2}})").empty());
  CHECK(bad(R"({"format": "plush.hand_shape", "version": 2, "id": "x", "kind": "rest", "pose": {}})").find("version") != std::string::npos);
  const std::string e = bad(R"({"format": "plush.hand_shape", "version": 1, "id": "y", "kind": "grasp", "character": "boy",
      "pose": {"curl": 1.5, "fingers": {"thumb": {}}}, "search": "pinch", "thumb": "sideways"})");
  for (const char* what : {"does not match", "character is not a hand-shape key", "pose.curl must be in", "fingers.thumb",
                           "approach is required", "thumb must be one of", "pinch_radius is required"})
    CHECK_MESSAGE(e.find(what) != std::string::npos, what << " in: " << e);
  CHECK(bad(R"({"format": "plush.hand_shape", "version": 1, "id": "x", "kind": "gesture", "pose": {}, "search": "all"})")
            .find("only for grasp shapes") != std::string::npos);
}

TEST_CASE("hand-shape table: gesture shapes pose the hand through its tracks on three skeletons (T-051)") {
  auto t = loadHandShapeTable(kRoot / "content/hand_shapes");
  REQUIRE(t);
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    CAPTURE(asset);
    auto probe = probeFor(asset);
    const Skeleton& sk = probe->characters()[0].asset.skeleton;
    const int hb = sk.find("hand.R");
    const vec3 wrist = sk.bones[size_t(hb)].head;
    auto reach = [&](const char* shape) {  // fingertip distance from the wrist, little .. index
      Clip clip;
      keyHandShape(clip, "hand.R", 0, *t->find(shape));
      Pose p = restPose(sk);
      applyConstraints(sk, clip, "", 0, mat4(1), p);
      std::vector<float> d;
      auto tips = fingertips(sk, p, mat4(1), 'R');
      for (size_t i = 1; i < tips.size(); ++i) d.push_back(glm::distance(tips[i], wrist));
      return d;  // fingers 0..3 (thumb dropped)
    };
    const auto point = reach("point"), relaxed = reach("relaxed"), two = reach("count_2"), three = reach("count_3");
    REQUIRE(point.size() == 4);
    // point / count_1: the index is the only extended finger; count_2: index + middle; count_3: index + middle + ring.
    for (int k = 0; k < 3; ++k) CHECK(point[3] > point[size_t(k)] * 1.15f);
    CHECK(point[3] > relaxed[3]);
    CHECK(two[2] > two[1] * 1.15f);
    CHECK(three[1] > three[0] * 1.15f);
    MESSAGE(std::format("{}: point index/little reach {:.1f}/{:.1f} mm, count_3 ring/little {:.1f}/{:.1f} mm", asset,
                        point[3] * 1e3, point[0] * 1e3, three[1] * 1e3, three[0] * 1e3));
    // chin_touch loads and poses (index less curled than the others).
    const auto chin = reach("chin_touch");
    CHECK(chin[3] > chin[0]);
  }
}
