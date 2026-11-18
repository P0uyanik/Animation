// T-097-0 (round 2 Phase D): shared acting interface between the emotion-blending system (T-097A, scene/emotion.*,
// the emotion part of scene/actions.cpp) and the personality-driven reaction system (T-097B, anim/personality.*,
// scene/reaction.*). Both tasks depend only on these plain types, so they can be built in parallel. Character
// independent: no character names or tuning here; values come from emotion files and personality profiles.
#pragma once
#include <string>
#include <utility>
#include <vector>

namespace plush {

// A continuous emotional state (T-097A blends between these instead of switching emotions).
struct EmotionState {
  std::vector<std::pair<std::string, float>> weights;  // named emotion (EmotionDef::name) -> weight, 0..1
  float pleasantness = 0.f;                            // valence, -1 (unpleasant) .. +1 (pleasant)
  float energy = 0.f;                                  // arousal, -1 (calm, low energy) .. +1 (excited)
};

// How a personality profile shapes the expression of an emotion (T-097B fills it, T-097A applies it).
struct PersonalityModulation {
  float intensityScale = 1.f;  // multiplies emotion intensity (face, posture, gesture amplitude)
  float tempoScale = 1.f;      // multiplies durations (>1 slower: onset, hold, release, gesture timing)
  float holdScale = 1.f;       // multiplies holds only (on top of tempoScale)
  float gazeShift = 0.f;       // tendency to look away (0) .. to look at the target (1); habit, not a target
  std::vector<std::string> preferredGestures;  // clip library names, most preferred first
};

// Something a character can react to (T-097B maps it to an EmotionState over time).
struct ReactionEvent {
  enum class Kind { ObjectAppears, PartnerActs, Success, Failure, Custom };
  Kind kind = Kind::Custom;
  std::string name;         // for Custom, or a label for logs
  std::string source;       // the actor or object that caused the event ("" = scene)
  double time = 0.0;        // seconds in the shot when the event happens
  float salience = 1.f;     // 0..1, how noticeable the event is
};

// The planned reaction of one character to one event (T-097B output; consumed by actions and acting checks).
struct ReactionPlan {
  double noticeDelay = 0.0;  // seconds from the event until the character notices it
  EmotionState target;       // the emotional state the character moves to
  double duration = 0.0;     // seconds the reaction lasts before decaying
  std::string gesture;       // chosen gesture clip ("" = none)
  PersonalityModulation modulation;
};

}  // namespace plush
