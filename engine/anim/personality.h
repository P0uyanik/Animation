// Personality profiles (T-053): one reader for content/personality/<id>.json (plush.personality/0,
// content/personality/SCHEMA.md). A profile is character data only: how a character moves and emotes (tempo, energy,
// posture, gaze, blinks, face rest / expression bias, limits). The shared layers receive the typed parameters from
// here and never read profile JSON themselves:
//   - life layer (scene.cpp lifeParams): blink interval and shape, breathing and idle sway amplitude, head lag;
//   - face (scene.cpp + face_layer.cpp applyPersonalityFace): rest offsets, expression bias, mouth while watching,
//     gaze pitch bias (look down);
//   - clip layers (clip_layers.cpp): tempo (clip clock multiplier) of gestures and clip actions;
//   - body mechanics (body_mechanics.cpp): settle, overshoot, lag, energy, gesture, posture.
// Every leaf is a value record {"value", "unit", "kind", "source"} (a plain value is accepted). Missing parameters are
// neutral: a layer keeps its shared default. A character without a profile (scene "personality" absent or false)
// is bit for bit what it was before T-053.
//
// "limits" (per profile): ranges the engine clamps the resolved parameters to (with a warning), and that the
// personality check (tools/animcheck/personality.py) measures on the baked motion.
#pragma once
#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include "geom/json_io.h"

namespace plush {

struct BodyMechanicsParams;

// Closed range [lo, hi]; a single number gives lo = hi.
struct PersonalityRange {
  float lo = 0, hi = 0;
  float mid() const { return 0.5f * (lo + hi); }
  float clamp(float x) const { return x < lo ? lo : x > hi ? hi : x; }
  bool contains(float x, float tol = 0) const { return x >= lo - tol && x <= hi + tol; }
};

struct PersonalityLimits {
  std::optional<PersonalityRange> blinkIntervalFrames;   // start-to-start, frames at 24 fps
  std::optional<PersonalityRange> blinkDurationFrames;   // whole blink (close + shut + open), frames at 24 fps
  std::optional<PersonalityRange> reachFrames;           // entry move of a gesture / reach, frames at 24 fps
  std::optional<PersonalityRange> holdFrames;            // hold between a gesture's entry and exit, frames at 24 fps
  std::optional<PersonalityRange> actionSpeed;           // effective clip speed of gestures (scene speed x tempo)
  std::optional<float> idleMotionMaxHPerFrame;           // head centroid speed outside gestures (head widths / frame)
  std::optional<float> faceOffsetMax;                    // |rest / bias / watching offset| per control
  std::optional<PersonalityRange> headPitchDeg;          // posture head pitch
};

// T-097B: how a character reacts to events (optional section "reaction", content/personality/SCHEMA.md). Every field
// is optional; a missing field keeps the shared, character-independent reaction defaults (scene/reaction.h).
struct PersonalityReactionEvent {
  std::string emotion;                // emotion name (content/emotions/<name>.emotion.json); "" = the shared default
  std::optional<float> intensity;     // 0..1 at salience 1 (replaces the shared default of the event)
  std::optional<float> durationS;     // seconds at salience 1 (replaces the shared default of the event)
  std::optional<float> gazeShift;     // 0 (looks away) .. 1 (looks at the source) for this event
  std::vector<std::string> gestures;  // clip library names, most preferred first
};
struct PersonalityReaction {
  std::optional<PersonalityRange> delayFrames;  // notice delay at salience 1 (frames at 24 fps; middle used)
  std::optional<float> intensityScale;          // multiplies emotion intensity (PersonalityModulation)
  std::optional<float> tempoScale;              // multiplies notice delay and reaction duration (> 1 = slower)
  std::optional<float> holdScale;               // multiplies the reaction duration only (on top of tempo)
  std::optional<float> gazeShift;               // gaze habit for every event without its own
  std::optional<float> gestureMinIntensity;     // expressed intensity a gesture needs
  std::map<std::string, PersonalityReactionEvent> events;  // object_appears, partner_acts, success, failure, <custom>
};

struct PersonalityProfile {
  std::string id;                 // file stem (character id)
  std::string character, profileVersion, status;
  std::filesystem::path path;
  // tempo
  std::optional<float> actionSpeed, overshoot, carefulPlaceFrames;
  std::optional<PersonalityRange> reachFrames, anticipationFrames, settleFrames, holdFrames;
  // T-104: multipliers on the beat durations of a timing profile (TimingProfile below; > 1 = slower / longer). Read
  // only when a scene uses a timing profile (the default, T-104d); missing = 1.
  std::optional<float> beatScale, holdScale;
  // energy
  std::optional<float> energyLevel, idleMotionAmplitudeH, gestureAmplitude;
  // posture
  std::optional<float> slouch, headPitchDeg, headTiltDeg, shouldersForward, weightShift, leanTowardTask;
  std::vector<std::string> restHands;
  // attention / boredom (read for tools and future directors; no engine layer uses them yet)
  std::string primaryTarget;
  std::optional<float> attentionSpanS, glanceAtOthersPerMin;
  std::optional<PersonalityRange> glanceHoldFrames;
  bool boredom = false;
  std::optional<float> boredomOnsetS;
  std::optional<PersonalityRange> fidgetIntervalS;
  std::vector<std::string> fidgetSet;
  // gaze
  std::optional<PersonalityRange> saccadeIntervalS, eyesLeadHeadFrames;
  std::optional<float> fixationOnTask, lookDownBias;
  // blink (frames at 24 fps)
  std::optional<float> blinkIntervalMean;
  std::optional<PersonalityRange> blinkIntervalRange, blinkDurationFrames, blinkClosedFrames;
  bool blinkOnActionChange = false;
  std::optional<float> longBlinkFrames;  // long blink on a gaze drop (false = none)
  // face: offsets on top of the character model's own neutral (shared action-unit names)
  std::map<std::string, float> faceRestOffset;      // constant offsets at rest
  std::map<std::string, float> faceExpressionBias;  // added in proportion to expression activity (0..1)
  std::map<std::string, float> faceWatching;        // added while a look action of the character plays
  std::optional<float> lidRest, faceAsymmetry;
  // smile
  std::optional<float> smileFrequency, openSmileShare;
  std::string defaultMouth;
  std::vector<std::string> gestures;
  PersonalityReaction reaction;  // T-097B
  PersonalityLimits limits;
};

// Parses a plush.personality/0 profile (strict on types of the fields it uses; unknown fields are ignored).
Result<PersonalityProfile> personalityFromJson(const Json& j, const std::string& id = {});
Result<PersonalityProfile> loadPersonality(const std::filesystem::path& file);
// Finds content/personality/<id>.json (then <id>.draft.json) by walking up from `from` (a scene file or directory).
std::filesystem::path findPersonalityFile(const std::filesystem::path& from, const std::string& id);
// Clamps the profile's own parameters into its limits; returns one warning per clamped value.
std::vector<std::string> clampPersonalityToLimits(PersonalityProfile& p);

// Timing profile (T-104): calibrated beat durations as data (content/timing/<name>.timing.json,
// plush.timing_profile/1, content/timing/README.md), derived from the reference timing table
// (content/timing/reference_timing.json). Named per scene ("timing": "<name>"); a scene without the key uses "calibrated" (T-104d), and
// "timing": "none" keeps every shared default as it was. Frames at 24 fps.
//   beats:  reach, anticipation, settle, hold, shared_hold, place, release, return, reaction_delay (frames)
//   travel: scale-aware carry speed in arm lengths per frame (mean over an eased move): a carry over distance d with
//           an arm of length L takes d / (L * arm_lengths_per_frame) frames, clamped into [min_frames, max_frames];
//           doll-sized and human-sized characters then take the same time for the same move relative to their arms.
// A character's personality scales it: beat durations x tempo.beat_scale, holds x tempo.hold_scale.
struct TimingProfile {
  std::string name, status;
  std::filesystem::path path;
  std::map<std::string, float> beats;  // frames at 24 fps
  float armLengthsPerFrame = 0.06f, travelMinFrames = 10, travelMaxFrames = 24;
  // Beat duration in frames (`fallback` when the profile has no such beat), scaled by the personality: holds
  // (hold, shared_hold) by tempo.hold_scale, every other beat by tempo.beat_scale.
  double frames(const std::string& beat, double fallback, const PersonalityProfile* who = nullptr) const;
  // Scale-aware travel time of a carry over `distance` metres by an arm of `armLength` metres (see above), scaled by
  // tempo.beat_scale, then clamped into [min_frames, max_frames].
  double travelFrames(double distance, double armLength, const PersonalityProfile* who = nullptr) const;
};
Result<TimingProfile> timingProfileFromJson(const Json& j, const std::string& name = {});
Result<TimingProfile> loadTimingProfile(const std::filesystem::path& file);
// Finds content/timing/<name>.timing.json by walking up from `from` (a scene file or directory); empty if none.
std::filesystem::path findTimingProfileFile(const std::filesystem::path& from, const std::string& name);

// Body mechanics (defined in body_mechanics.cpp): tempo, energy and posture of the typed profile; missing = neutral.
void applyPersonalityToBodyMechanics(BodyMechanicsParams& p, const PersonalityProfile& profile);

// Shared action-unit aliases (content/personality/action_units.json, plush.personality_action_units/1): AU name ->
// candidate control names in order; a character uses the first candidate it has (expression or morph).
struct PersonalityActionUnits {
  std::map<std::string, std::vector<std::string>> aliases;
};
PersonalityActionUnits defaultPersonalityActionUnits();
Result<PersonalityActionUnits> personalityActionUnitsFromJson(const Json& j);

}  // namespace plush
