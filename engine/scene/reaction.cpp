// T-097B personality-driven reactions (scene/reaction.h).
#include "scene/reaction.h"

#include <algorithm>
#include <cmath>

#include "anim/personality.h"

namespace plush {

ReactionDefaults reactionDefaults(ReactionEvent::Kind kind) {
  using K = ReactionEvent::Kind;
  switch (kind) {
    case K::ObjectAppears: return {"curious", 0.7f, 1.5, 1.0f};
    case K::PartnerActs: return {"curious", 0.5f, 1.0, 0.8f};
    case K::Success: return {"happy", 0.8f, 1.6, 0.7f};
    case K::Failure: return {"sad", 0.6f, 1.5, 0.3f};
    case K::Custom: break;
  }
  return {"", 0.f, 1.0, 0.5f};
}

const char* reactionEventKey(ReactionEvent::Kind kind) {
  using K = ReactionEvent::Kind;
  switch (kind) {
    case K::ObjectAppears: return "object_appears";
    case K::PartnerActs: return "partner_acts";
    case K::Success: return "success";
    case K::Failure: return "failure";
    case K::Custom: break;
  }
  return "custom";
}

std::pair<float, float> emotionValenceArousal(const std::string& e) {
  // Circumplex placement of the shared emotion set (content/emotions): pleasantness, energy.
  static const std::pair<const char*, std::pair<float, float>> table[] = {
      {"happy", {0.8f, 0.5f}},   {"curious", {0.3f, 0.3f}},  {"surprised", {0.1f, 0.8f}}, {"sad", {-0.6f, -0.5f}},
      {"afraid", {-0.7f, 0.6f}}, {"angry", {-0.7f, 0.7f}},   {"confused", {-0.2f, 0.1f}}, {"sleepy", {0.0f, -0.8f}},
  };
  for (const auto& [n, va] : table)
    if (e == n) return va;
  return {0.f, 0.f};
}

EmotionState emotionStateFor(const std::string& emotion, float intensity) {
  EmotionState s;
  if (emotion.empty() || !(intensity > 0)) return s;
  const float w = std::clamp(intensity, 0.f, 1.f);
  s.weights.emplace_back(emotion, w);
  const auto [v, a] = emotionValenceArousal(emotion);
  s.pleasantness = v * w;
  s.energy = a * w;
  return s;
}

float expressedIntensity(const ReactionPlan& plan) {
  float w = 0;
  for (const auto& [n, x] : plan.target.weights) w = std::max(w, x);
  return std::clamp(w * plan.modulation.intensityScale, 0.f, 1.f);
}

ReactionPlan planReaction(const ReactionEvent& event, const PersonalityProfile* who, const ReactionContext& ctx) {
  ReactionPlan plan;
  const float s = std::isfinite(event.salience) ? std::clamp(event.salience, 0.f, 1.f) : 0.f;
  const PersonalityReaction* R = who ? &who->reaction : nullptr;
  PersonalityModulation& m = plan.modulation;
  if (R) {
    m.intensityScale = R->intensityScale.value_or(1.f);
    m.tempoScale = R->tempoScale.value_or(1.f);
    m.holdScale = R->holdScale.value_or(1.f);
  }

  ReactionDefaults d = reactionDefaults(event.kind);
  const PersonalityReactionEvent* ov = nullptr;
  if (R) {
    const std::string key = event.kind == ReactionEvent::Kind::Custom ? event.name : reactionEventKey(event.kind);
    if (auto it = R->events.find(key); it != R->events.end()) ov = &it->second;
  }
  if (ov) {
    if (!ov->emotion.empty()) d.emotion = ov->emotion;
    if (ov->intensity) d.intensity = *ov->intensity;
    if (ov->durationS) d.duration = *ov->durationS;
  }
  m.gazeShift = ov && ov->gazeShift ? *ov->gazeShift : R && R->gazeShift ? *R->gazeShift : d.gaze;
  if (s <= 0) return plan;  // not noticed

  double delayFrames = kReactionDelayFrames;
  if (R && R->delayFrames) delayFrames = R->delayFrames->mid();
  else if (ctx.timing) delayFrames = ctx.timing->frames("reaction_delay", kReactionDelayFrames);
  plan.noticeDelay = delayFrames / 24.0 * m.tempoScale * (2.0 - s);
  plan.target = emotionStateFor(d.emotion, d.intensity * s);
  plan.duration = plan.target.weights.empty() ? 0.0 : d.duration * (0.5 + 0.5 * s) * m.tempoScale * m.holdScale;

  if (ov)
    for (const auto& g : ov->gestures)
      if (ctx.availableGestures.empty() ||
          std::find(ctx.availableGestures.begin(), ctx.availableGestures.end(), g) != ctx.availableGestures.end())
        m.preferredGestures.push_back(g);
  const float minI = R && R->gestureMinIntensity ? *R->gestureMinIntensity : kReactionGestureMinIntensity;
  if (!m.preferredGestures.empty() && !plan.target.weights.empty() && expressedIntensity(plan) >= minI)
    plan.gesture = m.preferredGestures.front();
  return plan;
}

std::vector<CharacterReaction> planReactions(const ReactionEvent& event,
                                             const std::vector<std::pair<std::string, const PersonalityProfile*>>& cast,
                                             const ReactionContext& ctx) {
  std::vector<CharacterReaction> out;
  for (const auto& [id, who] : cast) {
    // A partner's action is not a reaction cue for the actor itself; success and failure are (its own result).
    if (event.kind == ReactionEvent::Kind::PartnerActs && !event.source.empty() && id == event.source) continue;
    out.push_back({id, planReaction(event, who, ctx)});
  }
  return out;
}

}  // namespace plush
