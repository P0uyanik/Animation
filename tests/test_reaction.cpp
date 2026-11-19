// T-097B: personality-driven reactions (scene/reaction.h). Event -> reaction plan per character (notice delay,
// emotion choice and intensity, preferred gesture, gaze habit, duration); the shared defaults, salience, the profile's
// reaction section (scales and per-event overrides), the timing profile's reaction delay, the cast helper, reader
// errors, and the calibration against the reference timing (T-104) and the reference performances (T-106).
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>

#include "anim/personality.h"
#include "scene/acting.h"
#include "scene/reaction.h"

using namespace plush;
namespace fs = std::filesystem;
using K = ReactionEvent::Kind;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;

PersonalityProfile profile(const char* body, const std::string& id = "test") {
  Json j = Json::parse(body);
  j["format"] = "plush.personality";
  j["version"] = 0;
  auto p = personalityFromJson(j, id);
  if (!p) FAIL(p.error().message);
  return *p;
}
std::string profileError(const char* body) {
  Json j = Json::parse(body);
  j["format"] = "plush.personality";
  j["version"] = 0;
  auto p = personalityFromJson(j, "bad");
  return p ? std::string() : p.error().message;
}
ReactionEvent event(K kind, float salience = 1.f, double time = 2.0, std::string source = {}, std::string name = {}) {
  ReactionEvent e;
  e.kind = kind;
  e.salience = salience;
  e.time = time;
  e.source = std::move(source);
  e.name = std::move(name);
  return e;
}
float weightOf(const EmotionState& s, const std::string& name) {
  for (const auto& [n, w] : s.weights)
    if (n == name) return w;
  return 0;
}
void checkSame(const ReactionPlan& a, const ReactionPlan& b) {
  CHECK(a.noticeDelay == doctest::Approx(b.noticeDelay));
  CHECK(a.duration == doctest::Approx(b.duration));
  CHECK(a.gesture == b.gesture);
  REQUIRE(a.target.weights.size() == b.target.weights.size());
  for (size_t i = 0; i < a.target.weights.size(); ++i) {
    CHECK(a.target.weights[i].first == b.target.weights[i].first);
    CHECK(a.target.weights[i].second == doctest::Approx(b.target.weights[i].second));
  }
  CHECK(a.target.pleasantness == doctest::Approx(b.target.pleasantness));
  CHECK(a.target.energy == doctest::Approx(b.target.energy));
  CHECK(a.modulation.intensityScale == doctest::Approx(b.modulation.intensityScale));
  CHECK(a.modulation.tempoScale == doctest::Approx(b.modulation.tempoScale));
  CHECK(a.modulation.holdScale == doctest::Approx(b.modulation.holdScale));
  CHECK(a.modulation.gazeShift == doctest::Approx(b.modulation.gazeShift));
  CHECK(a.modulation.preferredGestures == b.modulation.preferredGestures);
}
}  // namespace

TEST_CASE("reaction: acting interface defaults are neutral (T-097-0)") {
  PersonalityModulation m;
  CHECK(m.intensityScale == doctest::Approx(1.0));
  CHECK(m.tempoScale == doctest::Approx(1.0));
  CHECK(m.holdScale == doctest::Approx(1.0));
  ReactionPlan p;
  CHECK(p.noticeDelay == doctest::Approx(0.0));
  CHECK(p.target.weights.empty());
  CHECK(expressedIntensity(p) == doctest::Approx(0.0));
}

TEST_CASE("reaction: each event kind maps to the shared default reaction without a profile") {
  struct Want {
    K kind;
    const char* key;
    const char* emotion;
    float intensity, gaze;
    double duration;
  };
  const Want table[] = {{K::ObjectAppears, "object_appears", "curious", 0.7f, 1.0f, 1.5},
                        {K::PartnerActs, "partner_acts", "curious", 0.5f, 0.8f, 1.0},
                        {K::Success, "success", "happy", 0.8f, 0.7f, 1.6},
                        {K::Failure, "failure", "sad", 0.6f, 0.3f, 1.5}};
  for (const auto& w : table) {
    CAPTURE(w.key);
    CHECK(std::string(reactionEventKey(w.kind)) == w.key);
    const ReactionPlan p = planReaction(event(w.kind), nullptr);
    CHECK(p.noticeDelay == doctest::Approx(kReactionDelayFrames / 24.0));
    REQUIRE(p.target.weights.size() == 1);
    CHECK(p.target.weights[0].first == w.emotion);
    CHECK(p.target.weights[0].second == doctest::Approx(w.intensity));
    CHECK(p.duration == doctest::Approx(w.duration));
    CHECK(p.gesture.empty());  // gestures are library names: only a profile names them
    CHECK(p.modulation.gazeShift == doctest::Approx(w.gaze));
    CHECK(p.modulation.intensityScale == doctest::Approx(1.0));
    CHECK(p.modulation.tempoScale == doctest::Approx(1.0));
    CHECK(p.modulation.holdScale == doctest::Approx(1.0));
    CHECK(expressedIntensity(p) == doctest::Approx(w.intensity));
    const auto [v, a] = emotionValenceArousal(w.emotion);
    CHECK(p.target.pleasantness == doctest::Approx(v * w.intensity));
    CHECK(p.target.energy == doctest::Approx(a * w.intensity));
  }
  // Valence: success is pleasant, failure unpleasant; a custom event without a profile entry is neutral.
  CHECK(planReaction(event(K::Success), nullptr).target.pleasantness > 0);
  CHECK(planReaction(event(K::Failure), nullptr).target.pleasantness < 0);
  const ReactionPlan custom = planReaction(event(K::Custom, 1.f, 0, {}, "door_slams"), nullptr);
  CHECK(custom.target.weights.empty());
  CHECK(custom.duration == doctest::Approx(0.0));
  CHECK(std::string(reactionEventKey(K::Custom)) == "custom");
  // Start / end in shot time.
  const ReactionEvent e = event(K::Success, 1.f, 3.0);
  const ReactionPlan p = planReaction(e, nullptr);
  CHECK(reactionStart(e, p) == doctest::Approx(3.0 + 0.25));
  CHECK(reactionEnd(e, p) == doctest::Approx(3.25 + 1.6));
}

TEST_CASE("reaction: profile defaults keep the neutral output (no reaction fields = no profile)") {
  // A profile with other sections but no reaction values behaves exactly like no profile.
  const PersonalityProfile p = profile(R"({"tempo": {"action_speed": 0.8, "beat_scale": 1.3},
                                           "energy": {"level": 0.2}, "gaze": {"fixation_on_task": 0.9},
                                           "reaction": {"channel_order": ["eyes", "mouth"], "positive_style": "text"}})");
  CHECK_FALSE(p.reaction.delayFrames);
  CHECK(p.reaction.events.empty());
  for (K k : {K::ObjectAppears, K::PartnerActs, K::Success, K::Failure, K::Custom})
    for (float s : {0.f, 0.3f, 1.f}) {
      CAPTURE(reactionEventKey(k));
      CAPTURE(s);
      checkSame(planReaction(event(k, s), &p), planReaction(event(k, s), nullptr));
    }
}

TEST_CASE("reaction: salience delays a faint event and weakens and shortens its reaction") {
  double lastDelay = 1e9, lastDur = -1;
  float lastI = -1;
  for (float s : {0.1f, 0.4f, 0.7f, 1.f}) {
    const ReactionPlan p = planReaction(event(K::ObjectAppears, s), nullptr);
    CHECK(p.noticeDelay < lastDelay);
    CHECK(expressedIntensity(p) > lastI);
    CHECK(p.duration > lastDur);
    lastDelay = p.noticeDelay, lastI = expressedIntensity(p), lastDur = p.duration;
  }
  const ReactionPlan faint = planReaction(event(K::ObjectAppears, 0.5f), nullptr);
  CHECK(faint.noticeDelay == doctest::Approx(kReactionDelayFrames / 24.0 * 1.5));
  CHECK(weightOf(faint.target, "curious") == doctest::Approx(0.35));
  CHECK(faint.duration == doctest::Approx(1.5 * 0.75));
  // Unnoticed: salience 0 (or out of range / not a number) gives no reaction.
  for (float s : {0.f, -1.f, std::nanf("")}) {
    const ReactionPlan p = planReaction(event(K::Success, s), nullptr);
    CHECK(p.target.weights.empty());
    CHECK(p.duration == doctest::Approx(0.0));
    CHECK(p.gesture.empty());
  }
  // Above 1 is clamped.
  checkSame(planReaction(event(K::Failure, 3.f), nullptr), planReaction(event(K::Failure, 1.f), nullptr));
}

TEST_CASE("reaction: profile values scale intensity and tempo") {
  const PersonalityProfile slow = profile(R"({"reaction": {"delay_frames": [4, 8], "tempo_scale": 1.5,
                                              "hold_scale": 1.2, "intensity_scale": 0.5}})");
  const PersonalityProfile lively = profile(R"({"reaction": {"delay_frames": {"value": [2, 4], "unit": "frames@24"},
                                                "tempo_scale": 0.8, "intensity_scale": 1.4}})");
  const ReactionEvent e = event(K::Success);
  const ReactionPlan n = planReaction(e, nullptr), a = planReaction(e, &slow), b = planReaction(e, &lively);
  CHECK(a.noticeDelay == doctest::Approx(6.0 / 24 * 1.5));
  CHECK(b.noticeDelay == doctest::Approx(3.0 / 24 * 0.8));
  CHECK(a.duration == doctest::Approx(n.duration * 1.5 * 1.2));
  CHECK(b.duration == doctest::Approx(n.duration * 0.8));
  // The event intensity is shared; the personality scale travels in the modulation and is applied once.
  CHECK(weightOf(a.target, "happy") == doctest::Approx(weightOf(n.target, "happy")));
  CHECK(a.modulation.intensityScale == doctest::Approx(0.5));
  CHECK(a.modulation.tempoScale == doctest::Approx(1.5));
  CHECK(a.modulation.holdScale == doctest::Approx(1.2));
  CHECK(expressedIntensity(a) == doctest::Approx(0.8 * 0.5));
  CHECK(expressedIntensity(b) == doctest::Approx(1.0));  // 0.8 x 1.4, clamped
  CHECK(expressedIntensity(a) < expressedIntensity(n));
  CHECK(expressedIntensity(n) < expressedIntensity(b));
  CHECK(a.noticeDelay > n.noticeDelay);
  CHECK(b.noticeDelay < n.noticeDelay);
}

TEST_CASE("reaction: per-event emotion, intensity, duration, gaze and preferred gesture") {
  const PersonalityProfile p = profile(R"({"reaction": {"gaze_shift": 0.2, "events": {
      "object_appears": {"emotion": "surprised", "intensity": 0.9, "duration_s": 2.0, "gaze_shift": 1.0,
                         "gestures": ["point", "hand_to_chin"]},
      "success": {"gestures": [{"name": "clap"}]},
      "failure": {"intensity": 0.2, "gestures": ["shrug"]},
      "door_slams": {"emotion": "afraid", "intensity": 0.6, "gestures": ["flinch"]}}}})");
  const ReactionPlan o = planReaction(event(K::ObjectAppears), &p);
  REQUIRE(o.target.weights.size() == 1);
  CHECK(o.target.weights[0].first == "surprised");
  CHECK(o.target.weights[0].second == doctest::Approx(0.9));
  CHECK(o.duration == doctest::Approx(2.0));
  CHECK(o.modulation.gazeShift == doctest::Approx(1.0));
  CHECK(o.gesture == "point");
  CHECK(o.modulation.preferredGestures == std::vector<std::string>{"point", "hand_to_chin"});
  // Only the override changes: the shared emotion and the profile's gaze habit stay for the rest.
  const ReactionPlan s = planReaction(event(K::Success), &p);
  CHECK(weightOf(s.target, "happy") == doctest::Approx(0.8));
  CHECK(s.gesture == "clap");
  CHECK(s.modulation.gazeShift == doctest::Approx(0.2));
  CHECK(planReaction(event(K::PartnerActs), &p).modulation.gazeShift == doctest::Approx(0.2));
  // A weak reaction keeps its preference but plays no gesture (below gesture_min_intensity).
  const ReactionPlan f = planReaction(event(K::Failure), &p);
  CHECK(f.modulation.preferredGestures == std::vector<std::string>{"shrug"});
  CHECK(f.gesture.empty());
  // Custom events are looked up by name.
  const ReactionPlan c = planReaction(event(K::Custom, 1.f, 0, {}, "door_slams"), &p);
  CHECK(weightOf(c.target, "afraid") == doctest::Approx(0.6));
  CHECK(c.target.pleasantness < 0);
  CHECK(c.gesture == "flinch");
  CHECK(c.duration == doctest::Approx(1.0));
  // Only clips the character has: the first available preference wins; none available = no gesture.
  ReactionContext ctx;
  ctx.availableGestures = {"hand_to_chin", "wave"};
  const ReactionPlan oa = planReaction(event(K::ObjectAppears), &p, ctx);
  CHECK(oa.gesture == "hand_to_chin");
  CHECK(oa.modulation.preferredGestures == std::vector<std::string>{"hand_to_chin"});
  CHECK(planReaction(event(K::Success), &p, ctx).gesture.empty());
  // The threshold is a profile value and is compared with the expressed intensity (after intensity_scale).
  const PersonalityProfile shy = profile(R"({"reaction": {"intensity_scale": 0.3, "events": {"success": {"gestures": ["clap"]}}}})");
  CHECK(planReaction(event(K::Success), &shy).gesture.empty());  // 0.8 x 0.3 = 0.24 < 0.35
  const PersonalityProfile eager = profile(R"({"reaction": {"intensity_scale": 0.3, "gesture_min_intensity": 0.2,
                                               "events": {"success": {"gestures": ["clap"]}}}})");
  CHECK(planReaction(event(K::Success), &eager).gesture == "clap");
}

TEST_CASE("reaction: the timing profile's reaction delay is the base; the profile's own delay wins") {
  TimingProfile t;
  t.beats["reaction_delay"] = 9;
  ReactionContext ctx;
  ctx.timing = &t;
  CHECK(planReaction(event(K::Success), nullptr, ctx).noticeDelay == doctest::Approx(9.0 / 24));
  const PersonalityProfile own = profile(R"({"reaction": {"delay_frames": [2, 4]}})");
  CHECK(planReaction(event(K::Success), &own, ctx).noticeDelay == doctest::Approx(3.0 / 24));
  // A timing profile without the beat keeps the shared delay.
  TimingProfile empty;
  ctx.timing = &empty;
  CHECK(planReaction(event(K::Success), nullptr, ctx).noticeDelay == doctest::Approx(kReactionDelayFrames / 24));
  // The shipped calibrated timing profile.
  auto cal = loadTimingProfile(kRoot / "content/timing/calibrated.timing.json");
  REQUIRE(cal.has_value());
  ctx.timing = &*cal;
  CHECK(planReaction(event(K::Success), nullptr, ctx).noticeDelay == doctest::Approx(cal->beats.at("reaction_delay") / 24.0));
}

TEST_CASE("reaction: every character of the cast reacts; the actor does not react to its own action") {
  const PersonalityProfile quick = profile(R"({"reaction": {"delay_frames": 2}})", "a");
  const PersonalityProfile slow = profile(R"({"reaction": {"delay_frames": 12, "tempo_scale": 1.25}})", "b");
  const std::vector<std::pair<std::string, const PersonalityProfile*>> cast = {{"a", &quick}, {"b", &slow}, {"c", nullptr}};
  auto acts = planReactions(event(K::PartnerActs, 1.f, 1.0, "a"), cast);
  REQUIRE(acts.size() == 2);
  CHECK(acts[0].character == "b");
  CHECK(acts[1].character == "c");
  CHECK(acts[0].plan.noticeDelay > acts[1].plan.noticeDelay);
  auto win = planReactions(event(K::Success, 1.f, 1.0, "a"), cast);  // its own success: everyone, the actor too
  REQUIRE(win.size() == 3);
  CHECK(win[0].plan.noticeDelay < win[2].plan.noticeDelay);
  CHECK(win[2].plan.noticeDelay < win[1].plan.noticeDelay);
  CHECK(planReactions(event(K::ObjectAppears, 1.f, 0, "boat"), cast).size() == 3);
  CHECK(planReactions(event(K::ObjectAppears), {}).empty());
}

TEST_CASE("reaction: character independent and deterministic") {
  // The same data under another id gives the same plan; the same input always gives the same plan.
  const char* body = R"({"reaction": {"delay_frames": [4, 8], "tempo_scale": 1.1, "events": {"success": {"gestures": ["nod"]}}}})";
  const PersonalityProfile a = profile(body, "first"), b = profile(body, "second");
  for (K k : {K::ObjectAppears, K::PartnerActs, K::Success, K::Failure}) {
    checkSame(planReaction(event(k, 0.6f), &a), planReaction(event(k, 0.6f), &b));
    checkSame(planReaction(event(k, 0.6f), &a), planReaction(event(k, 0.6f), &a));
  }
  // The event time and source never change the plan itself, only where it sits in the shot.
  checkSame(planReaction(event(K::Failure, 1.f, 0.0, "x"), &a), planReaction(event(K::Failure, 1.f, 7.5, "y"), &a));
}

TEST_CASE("reaction: reader errors for bad reaction values") {
  CHECK(profileError(R"({"reaction": {"tempo_scale": 0}})").find("reaction.tempo_scale") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"intensity_scale": -1}})").find("reaction.intensity_scale") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"hold_scale": 9}})").find("reaction.hold_scale") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"gaze_shift": 1.5}})").find("reaction.gaze_shift") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"gesture_min_intensity": 2}})").find("reaction.gesture_min_intensity") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"delay_frames": [8, 4]}})").find("reaction.delay_frames") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"delay_frames": -2}})").find("reaction.delay_frames") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": []}})").find("reaction.events") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": {"success": 1}}})").find("reaction.events") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": {"success": {"intensity": 2}}}})").find("reaction.events.success.intensity") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": {"success": {"duration_s": 0}}}})").find("reaction.events.success.duration_s") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": {"success": {"gaze_shift": -0.1}}}})").find("reaction.events.success.gaze_shift") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": {"success": {"gestures": "clap"}}}})").find("reaction.events.success.gestures") != std::string::npos);
  CHECK(profileError(R"({"reaction": {"events": {"success": {"emotion": "happy", "gestures": ["clap"]}}}})").empty());
}

TEST_CASE("reaction: shipped profiles plan within their own reaction delay; shared defaults match the references") {
  // Shipped profiles (T-097-0 Supervisor update, 2026-11-19): per-character tuning (T-097-boy/girl) may add reaction
  // fields; the invariant kept is that every event kind plans a notice delay no earlier than the profile's own
  // delay_frames lower bound (what tools/animcheck acting.py checks) and, at full salience with no tempo slow-down,
  // within its upper bound.
  for (const char* id : {"boy_yellow_hoodie", "girl_auburn_bun_glasses", "girl_white_hair_blue_dress"}) {
    CAPTURE(id);
    auto p = loadPersonality(kRoot / "content/personality" / (std::string(id) + ".json"));
    REQUIRE(p.has_value());
    REQUIRE(p->reaction.delayFrames.has_value());
    for (K kind : {K::ObjectAppears, K::PartnerActs, K::Success, K::Failure}) {
      CAPTURE(static_cast<int>(kind));
      const ReactionPlan r = planReaction(event(kind), &*p);
      CHECK(r.noticeDelay * 24 >= p->reaction.delayFrames->lo - 1e-6);
      if (!p->reaction.tempoScale || *p->reaction.tempoScale <= 1.0)
        CHECK(r.noticeDelay * 24 <= p->reaction.delayFrames->hi + 1e-6);
    }
  }
  // T-104 reference timing: the shared notice delay lies in the measured reaction_delay range.
  auto ref = parseJsonFile(kRoot / "content/timing/reference_timing.json");
  REQUIRE(ref.has_value());
  const Json& rd = (*ref)["beats"]["reaction_delay"]["frames"];
  CHECK(kReactionDelayFrames >= rd[0].get<double>());
  CHECK(kReactionDelayFrames <= rd[1].get<double>());
  // T-106 reference performances (docs/evaluation/animation/T-097B/README.md, calibration):
  auto perf = parseJsonFile(kRoot / "docs/evaluation/animation/T-106/performance.json");
  REQUIRE(perf.has_value());
  REQUIRE((*perf).contains("intervals"));
  auto beat = [&](const char* clip, const char* who, int first) -> double {
    for (const auto& r : (*perf)["intervals"])
      if (r["clip"] == clip && r["character"].get<std::string>().starts_with(who) && r["kind"] == "acting_beat" &&
          r["first_frame"].get<int>() == first)
        return r["duration_s"].get<double>();
    FAIL("no T-106 acting beat " << clip << " " << who << " f" << first);
    return 0;
  };
  // Reacting to what appears / is revealed: the reveal reactions (boy, girl with glasses) and the boy's watch while
  // the girl points span the object_appears duration.
  const double reveal[] = {beat("paperboat", "boy", 259), beat("paperboat", "girl", 255), beat("watertable", "boy", 27)};
  CHECK(reactionDefaults(K::ObjectAppears).duration >= *std::min_element(std::begin(reveal), std::end(reveal)) - 0.01);
  CHECK(reactionDefaults(K::ObjectAppears).duration <= *std::max_element(std::begin(reveal), std::end(reveal)) + 0.15);
  // Reacting to a partner: the small eye adjustment plus its hold (paperboat, girl with glasses).
  CHECK(reactionDefaults(K::PartnerActs).duration ==
        doctest::Approx(beat("paperboat", "girl", 125) + beat("paperboat", "girl", 132)).epsilon(0.1));
  // Success (the boat lights up): the clasped-hands, wide-eyed hold of the reveal.
  CHECK(reactionDefaults(K::Success).duration == doctest::Approx(beat("paperboat", "white", 250)).epsilon(0.03));
  // Failure is not shown in the references (extrapolation): the same scale as the others.
  CHECK(reactionDefaults(K::Failure).duration >= reactionDefaults(K::PartnerActs).duration);
  CHECK(reactionDefaults(K::Failure).duration <= reactionDefaults(K::Success).duration);
}
