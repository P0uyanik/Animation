// T-097B: personality-driven reactions. A ReactionEvent (object appears, partner acts, success, failure, custom) is
// mapped to a ReactionPlan per character: notice delay, emotion choice and intensity, preferred gesture, gaze habit
// and duration. Uses only the plain types of scene/acting.h (T-097-0) and the typed personality profile
// (anim/personality.h); no emotion files are read and no actions are scheduled here.
//
// Shared defaults (character independent, docs/evaluation/animation/T-097B/README.md for the calibration):
//   event           emotion    intensity  duration  gaze toward the source
//   object_appears  curious    0.7        1.5 s     1.0
//   partner_acts    curious    0.5        1.0 s     0.8
//   success         happy      0.8        1.6 s     0.7
//   failure         sad        0.6        1.5 s     0.3
//   custom          (none)     0          1.0 s     0.5   (a profile "events" entry under the event name gives one)
//   notice delay 6 frames at 24 fps (the timing profile's reaction_delay when one is given, T-104)
//   gesture needs an expressed intensity of 0.35
// With salience s (0..1): notice delay = base x tempo x (2 - s); event intensity = intensity x s;
// duration = duration x (0.5 + 0.5 s) x tempo x hold. s <= 0: the event is not noticed (empty plan).
// Personality (profile "reaction" section, all optional; missing = the neutral values above, PersonalityModulation
// defaults): delay_frames, intensity_scale, tempo_scale, hold_scale, gaze_shift, gesture_min_intensity and per-event
// overrides (emotion, intensity, duration_s, gaze_shift, gestures).
//
// Division of work with T-097A (acting.h): the plan's timing (noticeDelay, duration) is final (tempo and hold scales
// are applied here); the emotional target holds the event intensity before the personality's intensity scale, which
// travels in plan.modulation.intensityScale for the emotion system to apply once (expressedIntensity() below).
#pragma once
#include <string>
#include <utility>
#include <vector>

#include "scene/acting.h"

namespace plush {

struct PersonalityProfile;
struct TimingProfile;

// Shared defaults for one event kind (the table above).
struct ReactionDefaults {
  std::string emotion;
  float intensity = 0;
  double duration = 1.0;
  float gaze = 0.5f;
};
ReactionDefaults reactionDefaults(ReactionEvent::Kind kind);
// "object_appears", "partner_acts", "success", "failure", "custom" (the keys of a profile's reaction.events).
const char* reactionEventKey(ReactionEvent::Kind kind);
constexpr double kReactionDelayFrames = 6;       // shared notice delay at salience 1 (frames at 24 fps)
constexpr float kReactionGestureMinIntensity = 0.35f;

// Pleasantness and energy of a named emotion at intensity 1 (shared emotion names, content/emotions; an unknown
// name is neutral 0 / 0).
std::pair<float, float> emotionValenceArousal(const std::string& emotion);
// A one-emotion state at `intensity` (pleasantness / energy scaled by it); empty name = the neutral state.
EmotionState emotionStateFor(const std::string& emotion, float intensity);

struct ReactionContext {
  const TimingProfile* timing = nullptr;         // optional: reaction_delay beat (T-104); the profile's own wins
  std::vector<std::string> availableGestures;    // optional: clips the character can play (empty = no filter)
};

// The reaction of one character (`who` = nullptr: no profile, the shared defaults).
ReactionPlan planReaction(const ReactionEvent& event, const PersonalityProfile* who, const ReactionContext& ctx = {});

// The intensity the emotion is expressed with: the plan's strongest emotion weight x modulation.intensityScale,
// clamped to [0, 1].
float expressedIntensity(const ReactionPlan& plan);
// Seconds in the shot when the reaction starts (event time + notice delay) and ends (start + duration).
inline double reactionStart(const ReactionEvent& e, const ReactionPlan& p) { return e.time + p.noticeDelay; }
inline double reactionEnd(const ReactionEvent& e, const ReactionPlan& p) { return reactionStart(e, p) + p.duration; }

// Every character's reaction to one event. `cast`: character id -> profile (nullptr = none). The character named
// by event.source is skipped for PartnerActs (no reaction to one's own action); for every other kind it reacts too
// (its own success or failure).
struct CharacterReaction {
  std::string character;
  ReactionPlan plan;
};
std::vector<CharacterReaction> planReactions(const ReactionEvent& event,
                                             const std::vector<std::pair<std::string, const PersonalityProfile*>>& cast,
                                             const ReactionContext& ctx = {});

}  // namespace plush
