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

struct PersonalityProfile {
  std::string id;                 // file stem (character id)
  std::string character, profileVersion, status;
  std::filesystem::path path;
  // tempo
  std::optional<float> actionSpeed, overshoot, carefulPlaceFrames;
  std::optional<PersonalityRange> reachFrames, anticipationFrames, settleFrames, holdFrames;
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
  PersonalityLimits limits;
};

// Parses a plush.personality/0 profile (strict on types of the fields it uses; unknown fields are ignored).
Result<PersonalityProfile> personalityFromJson(const Json& j, const std::string& id = {});
Result<PersonalityProfile> loadPersonality(const std::filesystem::path& file);
// Finds content/personality/<id>.json (then <id>.draft.json) by walking up from `from` (a scene file or directory).
std::filesystem::path findPersonalityFile(const std::filesystem::path& from, const std::string& id);
// Clamps the profile's own parameters into its limits; returns one warning per clamped value.
std::vector<std::string> clampPersonalityToLimits(PersonalityProfile& p);

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
