// T-097A: emotion blending (scene/emotion.h EmotionChannel / EmotionBlender, the "blend" emotion actions). Transition
// tests: continuity (value and velocity), no pops (also between frames, where secondary motion samples), bounded
// rates, cross-fades instead of switches, personality modulation applied, and plain emotions unchanged.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <random>

#include "anim/animation.h"
#include "scene/acting.h"
#include "scene/emotion.h"
#include "scene/scene.h"

using namespace plush;

namespace {
const char* const kGirl = "girl_auburn_bun_glasses_m3";

std::unique_ptr<SceneEvaluator> blendScene(const Json& actions, int end, bool life = true, const std::string& package = kGirl) {
  Scene s;
  s.rate = FrameRate{30, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  CharacterDesc cd;
  cd.name = "who";
  if (package.empty()) {
    s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "content/scenes/unit_test.scene.json";
    cd.asset = "../characters/boy_dark_hair.character.json";
  } else {
    s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
    cd.asset = package + "/character.json";
  }
  cd.life.enabled = life;
  s.characters.push_back(cd);
  s.actions = actions;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}

// Worst second difference of any bone position over [a, b] sampled every `step` frames, in metres per frame^2
// (a pop is a velocity jump: a large second difference at one sample).
double worstJerk(const SceneEvaluator& ev, double a, double b, double step) {
  std::vector<std::vector<vec3>> P;
  for (double f = a; f <= b + 1e-9; f += step) {
    auto g = ev.characterGlobals(0, f);
    std::vector<vec3> p;
    for (const auto& m : g) p.push_back(vec3(m[3]));
    P.push_back(std::move(p));
  }
  double worst = 0;
  for (size_t k = 1; k + 1 < P.size(); ++k)
    for (size_t j = 0; j < P[k].size(); ++j)
      worst = std::max(worst, double(glm::length(P[k + 1][j] - 2.f * P[k][j] + P[k - 1][j])) / (step * step));
  return worst;
}

// A channel's value / velocity sampled every dt seconds over [a, b].
struct Samples {
  std::vector<double> x, v;
};
Samples sample(const EmotionChannel& ch, double a, double b, double dt) {
  Samples s;
  for (double t = a; t <= b + 1e-12; t += dt) {
    s.x.push_back(ch.value(t));
    s.v.push_back(ch.velocity(t));
  }
  return s;
}
}  // namespace

TEST_CASE("emotion channel: a rise from rest is the plain smoothstep ramp, and it holds the target") {
  EmotionChannel ch;
  ch.retarget(1.0, 0.8f, 0.5, 2.0);
  CHECK(ch.value(0.5) == doctest::Approx(0.0));
  for (double u : {0.0, 0.25, 0.5, 0.75, 1.0}) CHECK(ch.value(1.0 + 0.5 * u) == doctest::Approx(0.8 * smoothstep01(float(u))).epsilon(1e-4));
  CHECK(ch.value(5.0) == doctest::Approx(0.8));
  CHECK(ch.velocity(5.0) == doctest::Approx(0.0));
  ch.retarget(6.0, 0.0f, 0.5, 2.0);  // decreasing: the decay time applies
  CHECK(ch.value(7.0) == doctest::Approx(0.4).epsilon(1e-4));
  CHECK(ch.value(8.0) == doctest::Approx(0.0));
  CHECK(ch.target(6.5) == doctest::Approx(0.0));
  CHECK(ch.target(3.0) == doctest::Approx(0.8));
}

TEST_CASE("emotion channel: re-targeted mid-way it keeps value and velocity (no jump, no kink)") {
  EmotionChannel ch;
  ch.retarget(0.0, 1.0f, 1.0, 1.0);
  const double t = 0.4;
  const float x0 = ch.value(t - 1e-6), v0 = ch.velocity(t - 1e-6);
  ch.retarget(t, 0.1f, 0.6, 0.6);  // reverse while rising fast
  CHECK(ch.value(t + 1e-6) == doctest::Approx(x0).epsilon(1e-4));
  CHECK(ch.velocity(t + 1e-6) == doctest::Approx(v0).epsilon(1e-3));
  CHECK(ch.value(t + 0.6) == doctest::Approx(0.1));
  // Values stay in range and the velocity changes smoothly everywhere (no step in velocity between samples).
  const Samples s = sample(ch, 0, 2, 1e-3);
  double dv = 0;
  for (size_t k = 1; k < s.v.size(); ++k) dv = std::max(dv, std::abs(s.v[k] - s.v[k - 1]));
  MESSAGE("largest velocity change per ms: " << dv);
  CHECK(dv < 0.03);  // a kink would be ~|v0| ~ 1.5 / s in one sample
  for (double x : s.x) CHECK((x >= 0.0 && x <= 1.0));
}

TEST_CASE("emotion channel: rates stay bounded under any re-target sequence") {
  std::mt19937 rng(97);
  std::uniform_real_distribution<double> U(0, 1);
  const double minT = 0.25;
  double worstV = 0, worstJump = 0;
  for (int trial = 0; trial < 200; ++trial) {
    EmotionChannel ch;
    double t = 0;
    for (int k = 0; k < 12; ++k) {
      ch.retarget(t, float(U(rng)), minT + U(rng), minT + U(rng));
      t += 0.02 + U(rng) * 0.8;  // often long before the previous move ends
    }
    const Samples s = sample(ch, 0, t + 2, 2e-3);
    for (size_t k = 0; k < s.v.size(); ++k) {
      worstV = std::max(worstV, std::abs(s.v[k]));
      if (k) worstJump = std::max(worstJump, std::abs(s.x[k] - s.x[k - 1]));
      CHECK((s.x[k] >= 0.0 && s.x[k] <= 1.0));
    }
  }
  MESSAGE("worst |rate| " << worstV << " /s (bound " << 2.5 / minT << "), worst step per 2 ms " << worstJump);
  CHECK(worstV <= 2.5 / minT);  // a full 0..1 smoothstep over the shortest time peaks at 1.5 / minT
  CHECK(worstJump <= 2.5 / minT * 2e-3 + 1e-6);
}

TEST_CASE("emotion blender: cross-fade instead of a switch; affect follows the weights") {
  EmotionBlender b;
  std::map<std::string, std::pair<float, float>> affect{{"happy", {0.8f, 0.5f}}, {"sad", {-0.7f, -0.6f}}};
  EmotionState happy{{{"happy", 1.f}}, 0.8f, 0.5f};
  b.retarget(0.0, happy, 0.4, 0.8);
  const auto [p, e] = impliedAffect({{"sad", 1.f}}, affect);
  CHECK(p == doctest::Approx(-0.7));
  EmotionState sad{{{"sad", 1.f}}, p, e};
  b.retarget(1.0, sad, 0.8, 0.8);
  CHECK(b.weight("happy", 0.9) == doctest::Approx(1.0));
  CHECK(b.weight("sad", 0.9) == doctest::Approx(0.0));
  double worstSum = 0, minSum = 2;
  for (double t = 1.0; t <= 1.8; t += 0.01) {
    const EmotionState s = b.evaluate(t);
    REQUIRE(s.weights.size() == 2);
    const double sum = s.weights[0].second + s.weights[1].second;
    worstSum = std::max(worstSum, sum);
    minSum = std::min(minSum, sum);
    CHECK(s.pleasantness <= 0.8f + 1e-5f);
    CHECK(s.pleasantness >= -0.7f - 1e-5f);
  }
  CHECK(worstSum <= 1.0 + 1e-5);  // equal times: the two ramps are mirror images, the sum stays 1
  CHECK(minSum >= 1.0 - 1e-5);
  const EmotionState mid = b.evaluate(1.4);
  CHECK(mid.weights[0].second == doctest::Approx(0.5).epsilon(1e-3));
  CHECK(mid.pleasantness == doctest::Approx(0.05).epsilon(1e-2));  // halfway between 0.8 and -0.7
  CHECK(b.evaluate(3.0).pleasantness == doctest::Approx(-0.7));
  CHECK(impliedAffect({{"happy", 0.5f}}, affect).first == doctest::Approx(0.4));  // a faint emotion is a faint affect
}

TEST_CASE("override weights give the normalized blend in any order") {
  for (const std::vector<float>& w : {std::vector<float>{0.3f, 0.5f}, {0.7f, 0.6f, 0.2f}, {0.f, 1.f}, {0.f, 0.f}}) {
    const std::vector<float> a = overrideWeights(w);
    // Scalar stand-in for poses: base 0, layer i = i + 1; sequential overrides x = lerp(x, layer, a_i).
    double x = 0, S = 0, want = 0;
    for (float v : w) S += v;
    const double k = S > 1 ? 1 / S : 1;
    for (size_t i = 0; i < w.size(); ++i) {
      x += (double(i + 1) - x) * a[i];
      want += w[i] * k * double(i + 1);
    }
    CHECK(x == doctest::Approx(want).epsilon(1e-5));
  }
}

TEST_CASE("personality modulation scales intensity, tempo and holds (applied, not chosen)") {
  auto m = modulationFromJson(Json::parse(R"({"intensityScale": 0.5, "tempoScale": 2, "holdScale": 1.5, "gazeShift": 1})"));
  REQUIRE(m);
  const EmotionTiming t = modulatedTiming(0.4, 1.0, 0.6, 1.f, *m);
  CHECK(t.rise == doctest::Approx(0.8));
  CHECK(t.decay == doctest::Approx(1.2));
  CHECK(t.hold == doctest::Approx(3.0));
  CHECK(t.intensity == doctest::Approx(0.5));
  CHECK(modulatedTiming(0.4, 1.0, 0.6, 0.9f, PersonalityModulation{2.f}).intensity == doctest::Approx(1.0));  // clamped
  CHECK(emotionTempo(0.f, PersonalityModulation{}) == doctest::Approx(1.0));
  CHECK(emotionTempo(1.f, PersonalityModulation{}) == doctest::Approx(1.0 + kEnergyTempo));
  CHECK(emotionTempo(0.f, *m) == doctest::Approx(0.5));
  CHECK_FALSE(modulationFromJson(Json::parse(R"({"tempoScale": 0})")));
  auto id = modulationFromJson(Json());
  REQUIRE(id);
  CHECK(id->tempoScale == doctest::Approx(1.0));
}

TEST_CASE("emotion files: blend and affect sections are optional and parse") {
  Json j = Json::parse(R"({"format": "plush.emotion", "version": 1, "name": "x", "face": {"smile": 1},
    "blend": {"rise": 0.3, "decay": 0.9}, "affect": {"pleasantness": 0.6, "energy": 2}})");
  auto e = emotionFromJson(j);
  REQUIRE(e);
  CHECK(e->rise == doctest::Approx(0.3));
  CHECK(e->decay == doctest::Approx(0.9));
  CHECK(e->pleasantness == doctest::Approx(0.6));
  CHECK(e->energy == doctest::Approx(1.0));  // clamped
  j.erase("blend");
  j.erase("affect");
  auto plain = emotionFromJson(j);
  REQUIRE(plain);
  CHECK(plain->rise < 0);
  CHECK(plain->energy == doctest::Approx(0.0));
}

// ---- In a scene (the girl package: full face library) ----

namespace {
// happy, then (mid-rise) surprised, then sad while surprised still rises; a loop posture (afraid) at the end.
Json transitionActions(bool blend, const char* extra = "") {
  std::string b = blend ? R"(, "blend": true)" : "";
  return Json::parse(std::string(R"([
    {"type": "emotion", "character": "who", "name": "happy", "start": 10, "affect": {"pleasantness": 0.8, "energy": 0.4})") + b + extra + R"(},
    {"type": "emotion", "character": "who", "name": "surprised", "start": 18, "affect": {"energy": 0.9})" + b + R"(},
    {"type": "emotion", "character": "who", "name": "sad", "start": 30, "affect": {"pleasantness": -0.7, "energy": -0.6})" + b + R"(},
    {"type": "emotion", "character": "who", "name": "afraid", "start": 110, "affect": {"pleasantness": -0.6, "energy": 0.8})" + b + R"(}])");
}
double morphAvg(const SceneEvaluator& ev, const std::string& morph, int a, int b) {
  double s = 0;
  for (int f = a; f < b; ++f) s += ev.morphControlWeight(0, morph, f);
  return s / (b - a);
}
}  // namespace

TEST_CASE("blended emotions in a scene: face and posture cross-fade without pops, also between frames") {
  // Life off: blinks and idle motion are not part of the transitions measured here.
  auto ev = blendScene(transitionActions(true), 200, false);
  for (const auto& w : ev->warnings()) MESSAGE(w);
  // The state reaches every emotion (face read through its morphs) ...
  const std::string smile = ev->characters()[0].asset.expressionMap.at("smile");
  CHECK(morphAvg(*ev, smile, 2, 9) < 0.02);
  CHECK(ev->morphControlWeight(0, smile, 16) > 0.2);  // happy rose for 6 frames before surprised took over
  CHECK(morphAvg(*ev, smile, 70, 100) < 0.02);         // ... and faded out (replaced)
  // ... without pops: per-frame face changes stay bounded and smooth (no second-difference spike).
  auto faceSteps = [](const SceneEvaluator& e, double* worst2) {
    double w1 = 0, w2 = 0;
    for (const auto& mt : e.characters()[0].rig.morphs)
      for (int f = 3; f < 200; ++f) {
        const double a = e.morphControlWeight(0, mt.name, f - 2), b = e.morphControlWeight(0, mt.name, f - 1),
                     c = e.morphControlWeight(0, mt.name, f);
        w1 = std::max(w1, std::abs(c - b));
        w2 = std::max(w2, std::abs(c - 2 * b + a));
      }
    *worst2 = w2;
    return w1;
  };
  double face2 = 0, plainFace2 = 0;
  const double face1 = faceSteps(*ev, &face2);
  // The same actions as plain emotions (the T-003 crossfade) and as hard cuts (rise and decay 0, a reference pop).
  auto plain = blendScene(transitionActions(false), 200, false);
  const double plainFace1 = faceSteps(*plain, &plainFace2);
  auto cut = blendScene(Json::parse(R"([
    {"type": "emotion", "character": "who", "name": "happy", "start": 10, "blend": {"rise": 0, "decay": 0}},
    {"type": "emotion", "character": "who", "name": "sad", "start": 30, "blend": {"rise": 0, "decay": 0}}])"), 200, false);
  // Body: second differences at quarter frames (secondary motion's sampling) through every transition.
  const double jerkBlend = worstJerk(*ev, 5, 150, 0.25), jerkPlain = worstJerk(*plain, 5, 150, 0.25),
               jerkCut = worstJerk(*cut, 5, 60, 0.25);
  // Reference smoothness: each emotion alone, as a plain emotion (its own smoothstep onset and release).
  double jerkSingle = 0;
  for (const char* n : {"happy", "surprised", "sad", "afraid"}) {
    auto one = blendScene(Json::parse(std::format(R"([{{"type": "emotion", "character": "who", "name": "{}", "start": 10}}])", n)), 200, false);
    jerkSingle = std::max(jerkSingle, worstJerk(*one, 5, 150, 0.25));
  }
  MESSAGE("face: worst step/frame blend " << face1 << " plain " << plainFace1 << "; worst 2nd diff blend " << face2 << " plain "
                                          << plainFace2);
  MESSAGE("body: worst jerk blend " << jerkBlend << " plain crossfade " << jerkPlain << " single emotions " << jerkSingle
                                    << " hard cut " << jerkCut << " m/frame^2");
  CHECK(face1 <= plainFace1 + 1e-3);  // no faster than the plain crossfade
  CHECK(face2 <= plainFace2 + 1e-3);
  // Re-targets mid-ramp keep their velocity: the transitions are no sharper than the sharpest single emotion's own
  // ramp (measured: equal), and far from a pop (the cut reference).
  CHECK(jerkBlend <= 1.05 * jerkSingle);
  CHECK(jerkCut > 10 * jerkBlend);  // the metric sees a pop
}

TEST_CASE("blended emotions: face, posture, gaze and tempo read one state") {
  auto ev = blendScene(transitionActions(true), 200);
  const FaceLayer* face = ev->faceLayer(0);
  REQUIRE(face);
  // Gaze: sad looks down in its hold (its faceMotion gaze bias x the state weight).
  auto eyePitch = [&](const SceneEvaluator& e, int a, int b) {
    double s = 0;
    for (int f = a; f < b; ++f) s += e.faceState(0, f).eyeOffsetDeg.y;
    return s / (b - a);
  };
  CHECK(eyePitch(*ev, 80, 105) < eyePitch(*ev, 2, 9) - 5.0);
  // gazeShift 1 (a character that looks at things) removes that averted gaze, the face itself still plays.
  auto shifted = blendScene(Json::parse(R"([{"type": "emotion", "character": "who", "name": "sad", "start": 30, "blend": true,
    "modulation": {"gazeShift": 1}}])"), 120);
  auto plainSad = blendScene(Json::parse(R"([{"type": "emotion", "character": "who", "name": "sad", "start": 30, "blend": true}])"), 120);
  MESSAGE("sad eye pitch " << eyePitch(*plainSad, 80, 105) << " with gazeShift 1 " << eyePitch(*shifted, 80, 105));
  CHECK(eyePitch(*shifted, 80, 105) > eyePitch(*plainSad, 80, 105) + 4.0);
}

TEST_CASE("blended emotions: the state's energy sets the loop tempo without a phase jump") {
  // afraid (loop 0.4 s) entered from a calm state; energy +0.8 plays its clock 1.2 x, -0.8 plays it 0.8 x.
  auto loop = [](float energy) {
    return blendScene(Json::parse(std::format(R"([
      {{"type": "emotion", "character": "who", "name": "sad", "start": 5, "blend": true, "affect": {{"energy": -0.8}}}},
      {{"type": "emotion", "character": "who", "name": "afraid", "start": 40, "end": 200, "blend": true, "affect": {{"energy": {}}}}}])", energy)),
                      200, false);
  };
  auto fast = loop(0.8f), slow = loop(-0.8f);
  auto head = [](const SceneEvaluator& e, double f) {
    const int h = e.characters()[0].asset.skeleton.find("head");
    REQUIRE(h >= 0);
    return vec3(e.characterGlobals(0, f)[size_t(h)][3]);
  };
  // Tremble period from the head's height crossings over the hold (frames 90..180).
  auto crossings = [&](const SceneEvaluator& e) {
    double mean = 0;
    for (int f = 90; f < 180; ++f) mean += head(e, f).y;
    mean /= 90;
    int n = 0;
    for (int f = 91; f < 180; ++f) n += (head(e, f - 1).y - mean) * (head(e, f).y - mean) < 0;
    return n;
  };
  const int nf = crossings(*fast), ns = crossings(*slow);
  const double jf = worstJerk(*fast, 30, 120, 0.25), js = worstJerk(*slow, 30, 120, 0.25);
  MESSAGE("head crossings over 3 s: energy +0.8 " << nf << ", -0.8 " << ns << "; jerk " << jf << " / " << js);
  CHECK(nf > ns);  // the energetic state trembles faster
  CHECK(double(nf) / std::max(1, ns) == doctest::Approx(1.2 / 0.8).epsilon(0.25));
  // A plain (unblended) afraid with the same envelope as the reference for smoothness.
  auto plain = blendScene(Json::parse(R"([{"type": "emotion", "character": "who", "name": "afraid", "start": 40, "end": 200}])"), 200, false);
  const double jp = worstJerk(*plain, 30, 120, 0.25);
  MESSAGE("plain afraid jerk " << jp);
  CHECK(jf <= 1.2 * 1.2 * 1.05 * jp);  // tempo 1.2 scales the loop's accelerations by 1.2^2 at most
  CHECK(js <= 1.05 * jp);
}

TEST_CASE("blended emotions: modulation stretches rise and scales intensity") {
  const std::string base = R"([{"type": "emotion", "character": "who", "name": "happy", "start": 10, "blend": true)";
  auto plain = blendScene(Json::parse(base + "}]"), 120);
  auto slow = blendScene(Json::parse(base + R"(, "modulation": {"tempoScale": 2, "intensityScale": 0.5}}])"), 120);
  const std::string smile = plain->characters()[0].asset.expressionMap.at("smile");
  // happy: onset 0.4 s = 12 frames; tempoScale 2 -> 24 frames; intensity 0.5 halves the held weight.
  const double full = plain->morphControlWeight(0, smile, 30), half = slow->morphControlWeight(0, smile, 40);
  MESSAGE("smile hold " << full << " modulated " << half);
  CHECK(half == doctest::Approx(0.5 * full).epsilon(0.05));
  CHECK(plain->morphControlWeight(0, smile, 16) / full == doctest::Approx(0.5).epsilon(0.05));  // midpoint of 12 frames
  CHECK(slow->morphControlWeight(0, smile, 22) / half == doctest::Approx(0.5).epsilon(0.05));  // midpoint of 24 frames
  // holdScale lengthens the hold: still on at 0.4 + 1.5 x 2 s after the start, gone with holdScale 1.
  auto held = blendScene(Json::parse(base + R"(, "modulation": {"holdScale": 2}}])"), 200);
  CHECK(held->morphControlWeight(0, smile, 10 + 12 + 70) > 0.9 * full);
  CHECK(plain->morphControlWeight(0, smile, 10 + 12 + 45 + 18 + 2) < 0.02);
}

TEST_CASE("plain emotions are unchanged: blend:false is the old path, and the old path keeps its crossfade") {
  auto a = blendScene(transitionActions(false), 200);
  auto b = blendScene(Json::parse(R"([
    {"type": "emotion", "character": "who", "name": "happy", "start": 10, "blend": false},
    {"type": "emotion", "character": "who", "name": "surprised", "start": 18, "blend": false},
    {"type": "emotion", "character": "who", "name": "sad", "start": 30, "blend": false},
    {"type": "emotion", "character": "who", "name": "afraid", "start": 110, "blend": false}])"), 200);
  for (int f = 1; f <= 200; f += 7) {
    const auto ga = a->characterGlobals(0, f), gb = b->characterGlobals(0, f);
    for (size_t j = 0; j < ga.size(); ++j) CHECK(glm::length(vec3(ga[j][3]) - vec3(gb[j][3])) < 1e-6f);
    for (const auto& mt : a->characters()[0].rig.morphs) CHECK(a->morphControlWeight(0, mt.name, f) == b->morphControlWeight(0, mt.name, f));
  }
}

// Evidence (docs/evaluation/animation/T-097A): with PLUSH_T097A_EVIDENCE=<dir>, writes the transition curves of the
// blended and the plain (T-003 crossfade) versions of the same actions as CSV. Without the variable it does nothing.
TEST_CASE("emotion blend evidence curves (opt-in)") {
  const char* dir = std::getenv("PLUSH_T097A_EVIDENCE");
  if (!dir) return;
  auto blend = blendScene(transitionActions(true), 200, false), plain = blendScene(transitionActions(false), 200, false);
  const auto& map = blend->characters()[0].asset.expressionMap;
  const std::vector<std::string> morphs{map.at("smile"), map.at("surprised"), map.at("sad")};
  const int head = blend->characters()[0].asset.skeleton.find("head");
  REQUIRE(head >= 0);
  FILE* f = std::fopen((std::filesystem::path(dir) / "curves.csv").string().c_str(), "w");
  REQUIRE(f);
  std::fprintf(f, "frame");
  for (const char* v : {"blend", "plain"}) {
    for (const auto& m : morphs) std::fprintf(f, ",%s_%s", v, m.c_str());
    std::fprintf(f, ",%s_head_y_mm,%s_head_z_mm", v, v);
  }
  std::fprintf(f, "\n");
  for (double fr = 1; fr <= 200; fr += 0.25) {
    std::fprintf(f, "%.2f", fr);
    for (const SceneEvaluator* e : {blend.get(), plain.get()}) {
      for (const auto& m : morphs) std::fprintf(f, ",%.5f", e->morphControlWeight(0, m, fr));
      const vec3 p(e->characterGlobals(0, fr)[size_t(head)][3]);
      std::fprintf(f, ",%.4f,%.4f", 1000 * p.y, 1000 * p.z);
    }
    std::fprintf(f, "\n");
  }
  std::fclose(f);
}
