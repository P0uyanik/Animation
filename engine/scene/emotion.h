// Emotions (plush.emotion/1, docs/EMOTIONS.md): a shared, character-independent combination of a face (a weighted mix
// of engine expression names, resolved per character through its expression map), a body posture clip (hold or
// loop, with a body-part mask), an optional one-shot gesture clip and timing (onset, hold, release, intensity
// curve). Played by the "emotion" action (actions.cpp), which compiles it into expression weights and clip layers.
#pragma once
#include <string>
#include <utility>
#include <vector>

#include "geom/json_io.h"

namespace plush {

struct EmotionDef {
  std::string name, variant;  // variant: "" or a key of "variants" (applied as a JSON merge patch)
  int version = 1;
  std::vector<std::pair<std::string, float>> face;  // engine expression name -> weight at intensity 1
  std::string bodyClip;                             // posture clip (library name), "" = no body part
  std::vector<std::string> bodyMask;                // overrides the clip's mask when not empty
  int bodyLoop = -1;                                // -1: the clip's own setting, 0 / 1: override
  struct Gesture {
    std::string clip;
    double offset = 0, blendIn = 0.2, blendOut = 0.2;  // seconds (offset from the emotion's start)
    bool mirror = false;
    std::vector<std::pair<std::string, float>> face;  // optional face accent during the gesture
  };
  bool hasGesture = false;
  Gesture gesture;
  double onset = 0.4, hold = 1.5, release = 0.6;  // seconds
  bool linear = false;                            // intensity curve: "smooth" (smoothstep, default) or "linear"
  Json raw;                                       // the file as read (unknown fields are preserved by tools)
};

// Parses an emotion file; `variant` (e.g. "laugh") applies variants.<variant> as a JSON merge patch first.
Result<EmotionDef> emotionFromJson(const Json& j, const std::string& variant = "");

}  // namespace plush
