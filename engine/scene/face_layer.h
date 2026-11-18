// Facial layer (T-046): the living face. While a character's life layer is on, the face is never frozen: blinks
// with varying rhythm (double blinks, blinks on gaze shifts, rate and speed changing with the emotion), eye darts
// (saccades) and gaze holds, emotion gaze bias (sad looks down), brow raise on attention (look starts, emotion
// onsets), mouth corners and brows following the emotion, small breathing-linked jaw motion and slow micro motion.
//
// Data-driven and shared: the engine knows no character. Face *channels* (browUp, mouthDown ...) resolve per
// character to the controls it exports today (engine expression names through its expression map, else morph
// names), from candidate lists in content/emotions/face_motion.json; a character without a control simply skips
// that channel. Emotions carry an optional "faceMotion" section (plush.emotion/1, docs/EMOTIONS.md); clips may carry
// a "face" block of channel curves. Everything is a function of the frame and the seed (random access, no state).
#pragma once
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

// Tunables of the living face. In data every field is optional: an emotion changes only what it names, the rest
// keeps the neutral value (face_motion.json "neutral", else the built-in defaults below).
struct FaceMotion {
  std::optional<float> blinkRate;      // blink frequency multiplier (1 = the character's own interval)
  std::optional<float> doubleBlink;    // chance that a blink is followed by a second one
  std::optional<float> blinkDuration;  // blink length multiplier (sleepy: slow, heavy blinks)
  std::optional<float> gazeShiftBlink; // chance of a blink when a look starts (a large gaze shift)
  std::optional<float> saccadeRate;    // eye-dart frequency multiplier
  std::optional<float> saccadeDeg;     // eye-dart amplitude (degrees, yaw; pitch is 0.55 x)
  std::optional<float> longHold;       // chance that a gaze hold lasts 2.5 x longer
  std::optional<vec2> gazeBiasDeg;     // eye offset (yaw: + = the character's left, pitch: + = up), degrees
  std::optional<float> attention;      // brow raise / eye widen pulse at the emotion's onset (0..1)
  std::optional<float> breath;         // breathing-linked jaw motion multiplier
  std::optional<float> micro;          // slow micro motion of brows and mouth corners multiplier
  std::map<std::string, float> channels;  // face channel -> weight held while the emotion plays (x its envelope)
};
Result<FaceMotion> faceMotionFromJson(const Json& j);

// Resolved neutral values (no optionals).
struct FaceNeutral {
  float blinkRate = 1.0f, doubleBlink = 0.12f, blinkDuration = 1.0f, gazeShiftBlink = 0.5f;
  float saccadeInterval = 0.9f;  // mean seconds between eye darts at rate 1
  float saccadeRate = 1.0f, saccadeDeg = 1.6f, longHold = 0.25f;
  vec2 gazeBiasDeg{0};
  float lookAttention = 0.3f;    // brow pulse when a look starts
  float breath = 1.0f, micro = 1.0f;
  // Amplitudes of the built-in motions (channel weights).
  float breathJaw = 0.025f;      // jaw opening at the top of an inhale
  float microBrow = 0.04f, microMouth = 0.045f;
  float attentionBrow = 0.45f, attentionWide = 0.3f;
};

// The shared face library (content/emotions/face_motion.json, format plush.face_motion/1).
struct FaceLibrary {
  // channel -> candidates in order; a candidate is a list of control names driven together (e.g. left + right brow).
  std::map<std::string, std::vector<std::vector<std::string>>> channels;
  // Controls (channel, expression or morph names) that open the eyes: they fade out while the lids close, so a blink
  // closes the eye whatever the expression (additive lid shapes do not compose: a wide-eyed lid stays open).
  std::vector<std::string> blinkClears;
  FaceNeutral neutral;
};
FaceLibrary defaultFaceLibrary();  // engine expression names only (used when no library file is found)
Result<FaceLibrary> faceLibraryFromJson(const Json& j);

// Envelope of an emotion or clip layer in scene frames (same shape as clip layers: smoothstep or linear ramps).
// Blended emotions (T-097A, scene/emotion.h) instead give a sampled weight curve: one value per scene frame from
// `curveStart`, linearly interpolated (0 outside), multiplied into the envelope. Null = the ramps only.
struct FaceEnvelope {
  double start = 0, end = 1e30, blendIn = 0, blendOut = 0, weight = 1;
  bool linear = false;
  std::shared_ptr<const std::vector<float>> curve;
  double curveStart = 0;
  double at(double frame) const;
};
// A per-frame sampled curve (values at start, start + 1, ...) at a scene frame: linear between samples, 0 outside.
double sampledCurve(const std::vector<float>& values, double start, double frame);

// Channel curves of a clip ("face": {"tracks": {"<channel>": [[clipFrame, value], ...]}}).
struct FaceCurves {
  std::map<std::string, Track> tracks;
};
// Returns null when the clip JSON has no face block.
Result<std::shared_ptr<const FaceCurves>> faceCurvesFromClipJson(const Json& clip);

// What happens to one character's face over a shot (gathered when actions compile).
struct FaceTimeline {
  struct Emotion {
    FaceEnvelope env;
    FaceMotion motion;
  };
  struct Curves {
    FaceEnvelope env;
    std::shared_ptr<const FaceCurves> curves;
    double start = 0, speed = 1, clipFps = 30;  // clip frame = (frame - start) x speed x clipFps / scene fps
  };
  struct Pulse {
    double frame = 0;
    float amount = 0;
  };
  std::vector<Emotion> emotions;
  std::vector<Curves> curves;
  std::vector<Pulse> attention;   // brow raise pulses
  std::vector<double> lookStarts; // frames where a new look starts (possible gaze-shift blinks)
};

struct FaceState {
  float blink = 0;                        // lid closure 0..1
  vec2 eyeOffsetDeg{0};                   // eye darts + gaze bias (yaw +: character's left, pitch +: up)
  std::map<std::string, float> controls;  // resolved control (morph) -> weight added to its animated value
};

// Personality face (T-053, anim/personality.h), resolved to one character's controls (morph names): constant rest
// offsets, an expression bias added in proportion to the expression activity (0..1) and the mouth while the character
// watches (look actions, 0..1 envelope). Offsets add to the control's animated weight (the result is clamped to 0..1).
struct PersonalityFace {
  std::map<std::string, float> rest, bias, watching;
  bool empty() const { return rest.empty() && bias.empty() && watching.empty(); }
};
float personalityFaceOffset(const PersonalityFace& f, const std::string& control, float activity, float watching);
// Resolves action-unit offsets to controls: `resolve` maps a name to the character's morph ("" = none). Several
// action units on one control keep the offset of largest magnitude (e.g. Blink.L and Blink.R on a single Blink).
std::map<std::string, float> resolvePersonalityOffsets(const std::map<std::string, float>& au,
                                                       const std::map<std::string, std::vector<std::string>>& aliases,
                                                       const std::function<std::string(const std::string&)>& resolve);

class FaceLayer {
 public:
  // `resolve` maps a control name (expression or morph) to the character's morph, or "" if it has none.
  void build(const FaceLibrary& lib, const std::function<std::string(const std::string&)>& resolve, FaceTimeline timeline,
             const LifeParams& life, double fps, int frameStart, int frameEnd);
  FaceState evaluate(double frame) const;
  bool built() const { return built_; }
  // Channel -> morphs it drives on this character (empty list: skipped). For tests and reports.
  const std::map<std::string, std::vector<std::string>>& channels() const { return channels_; }
  // Blink closure only (cheaper than evaluate).
  float blink(double frame) const;
  // Morphs that fade out with a blink (FaceLibrary::blinkClears resolved for this character).
  const std::vector<std::string>& blinkClears() const { return blinkClears_; }
  bool clearsWithBlink(const std::string& morph) const;

 private:
  struct Params {  // blended at a frame
    float blinkRate, doubleBlink, blinkDuration, gazeShiftBlink, saccadeRate, saccadeDeg, longHold, attention, breath, micro;
    vec2 bias;
  };
  Params params(double frame) const;
  double clock(const std::vector<double>& table, double frame) const;       // warped seconds at a frame
  double clockInverse(const std::vector<double>& table, double tau) const;  // frame at warped seconds
  vec2 saccade(double frame) const;
  void addChannel(std::map<std::string, float>& out, const std::string& channel, float w) const;

  bool built_ = false;
  FaceNeutral n_;
  std::map<std::string, std::vector<std::string>> channels_;
  std::vector<std::string> blinkClears_;
  FaceTimeline tl_;
  LifeParams life_;
  double fps_ = 30;
  int f0_ = 0, frameStart_ = 1;
  std::vector<double> blinkClock_, saccadeClock_;  // per frame from f0_ (seconds of warped time)
};

}  // namespace plush
