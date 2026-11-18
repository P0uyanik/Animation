// Emotions (plush.emotion/1, docs/EMOTIONS.md): a shared, character-independent combination of a face (a weighted mix
// of engine expression names, resolved per character through its expression map), a body posture clip (hold or
// loop, with a body-part mask), an optional one-shot gesture clip and timing (onset, hold, release, intensity
// curve). Played by the "emotion" action (actions.cpp), which compiles it into expression weights and clip layers.
#pragma once
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "geom/json_io.h"
#include "scene/acting.h"
#include "scene/face_layer.h"

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
  // Living-face tunables while the emotion plays (T-046, optional "faceMotion" section, scene/face_layer.h): blink
  // rhythm, eye darts, gaze bias, attention, brows and mouth corners as face channels. Used while life is on.
  FaceMotion faceMotion;
  bool hasFaceMotion = false;
  // Blended play (T-097A, optional, read only by emotion actions with "blend"): rise / decay times in seconds
  // (< 0: onset / release) and the emotion's affect (pleasantness, energy; -1..1) in the continuous state.
  double rise = -1, decay = -1;
  float pleasantness = 0, energy = 0;
  Json raw;                                       // the file as read (unknown fields are preserved by tools)
};

// Parses an emotion file; `variant` (e.g. "laugh") applies variants.<variant> as a JSON merge patch first.
Result<EmotionDef> emotionFromJson(const Json& j, const std::string& variant = "");

// ---- Emotion blending (T-097A) --------------------------------------------------------------------------------------
// A continuous emotional state (scene/acting.h EmotionState): every emotion weight and the pleasantness / energy are
// channels that move towards a target over a rise time (when the value increases) or a decay time (when it
// decreases). A move is a cubic Hermite segment from the current value *and velocity* to the target, arriving with
// zero velocity, so a channel re-targeted mid-way never jumps or kinks (C1); with no motion in progress it is the
// smoothstep ramp of plain emotions. Times are seconds; random access (no state is advanced by evaluation).
class EmotionChannel {
 public:
  EmotionChannel(float lo = 0.f, float hi = 1.f, float initial = 0.f) : lo_(lo), hi_(hi), initial_(initial) {}
  // Move to `target` from time t (re-targets must come in time order; a later one replaces what follows t).
  void retarget(double t, float target, double rise, double decay);
  float value(double t) const;
  float velocity(double t) const;  // units per second
  float target(double t) const;    // the target in effect at t
  double lastRetarget() const { return segs_.empty() ? -1e30 : segs_.back().t0; }
  bool empty() const { return segs_.empty(); }

 private:
  struct Seg {
    double t0, T;
    float x0, v0, x1;
  };
  float raw(double t, float* v) const;
  float lo_, hi_, initial_;
  std::vector<Seg> segs_;
};

class EmotionBlender {
 public:
  // One emotion's weight (0..1).
  void retargetEmotion(double t, const std::string& name, float weight, double rise, double decay);
  // Pleasantness and energy (-1..1).
  void retargetAffect(double t, float pleasantness, float energy, double rise, double decay);
  // A whole target state: named weights, every other emotion of the blender to 0; affect as given.
  void retarget(double t, const EmotionState& target, double rise, double decay);
  EmotionState evaluate(double t) const;  // weights of every emotion the blender knows (in first-use order)
  float weight(const std::string& name, double t) const;
  const std::vector<std::string>& names() const { return order_; }
  const EmotionChannel* channel(const std::string& name) const;
  const EmotionChannel& pleasantness() const { return p_; }
  const EmotionChannel& energy() const { return e_; }

 private:
  std::map<std::string, EmotionChannel> weights_;
  std::vector<std::string> order_;
  EmotionChannel p_{-1.f, 1.f}, e_{-1.f, 1.f};
};

// Affect a state's weights imply: the weight-averaged affect of its emotions, scaled down when the weights sum to
// less than 1 (a faint emotion is a faint affect); `affect` maps emotion name -> (pleasantness, energy).
std::pair<float, float> impliedAffect(const std::vector<std::pair<std::string, float>>& weights,
                                      const std::map<std::string, std::pair<float, float>>& affect);

// Personality modulation (scene/acting.h; chosen by T-097B, applied here). Intensity scales face and body
// amplitude (clamped to 1), tempoScale multiplies every duration (rise, decay, hold, gesture blends; > 1 slower),
// holdScale multiplies holds on top, gazeShift 1 removes the emotion's averted-gaze bias (0 keeps it).
Result<PersonalityModulation> modulationFromJson(const Json& j);
struct EmotionTiming {
  double rise = 0, hold = 0, decay = 0;  // seconds
  float intensity = 1;
};
EmotionTiming modulatedTiming(double rise, double hold, double decay, float intensity, const PersonalityModulation& m);
// Movement tempo of the state: clip clocks run (1 + energyTempo x energy) / tempoScale times the plain speed.
constexpr float kEnergyTempo = 0.25f;
double emotionTempo(float energy, const PersonalityModulation& m, float energyTempo = kEnergyTempo);
// Sequential override weights that give a normalized blend: layers applied in order with these weights yield
// (1 - S) x base + sum W_i x layer_i (S = sum W_i, normalized when it exceeds 1).
std::vector<float> overrideWeights(const std::vector<float>& weights);

// Per-frame curves of a blended emotion posture layer (SceneEvaluator::ClipLayer::sampled): from scene frame
// `start` on, the layer weight (multiplies its envelope; 0 outside) and the clip clock in clip frames (it integrates
// the state's tempo, so a loop changes speed without a phase jump). Linear between frames.
struct SampledLayerCurves {
  double start = 0;
  std::vector<float> weight;
  std::vector<double> clock;
  double weightAt(double frame) const { return sampledCurve(weight, start, frame); }
  double clockAt(double frame) const;
};

}  // namespace plush
