// Animation principles (T-061): slow-in / slow-out that survives retiming and blending, arcs through successive
// breaking and automatic breakdowns. Shared and data driven: no character data, only role names of the clip system.
//
// Used by the clip layers (scene/clip_layers.cpp: blend ramps, per-role timing offsets, retiming, breakdowns) and the
// IK gestures (scene/actions.cpp: weight ramps and the elbow lag of two-bone IK). Scene setting "animPrinciples"
// (scene/scene.h): true (default) | false | {field overrides}. Off = the behaviour before T-061, bit for bit.
#pragma once
#include <string_view>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct AnimPrinciples {
  bool enabled = true;
  // Blends (clip layers and IK weight ramps). Blend duration = max(authored, minimum), the minimum derived from the
  // amplitude A (largest global rotation change of a driven arm / torso bone between the underlying and the target
  // pose): with the quintic ease the peak angular speed is 1.875 A / T, so T = 1.875 A / maxBlendDegPerSec, clamped
  // to [minBlendSec, maxBlendSec]. An authored 0 (a cut) is kept.
  double maxBlendDegPerSec = 150.0;
  double minBlendSec = 0.35;
  double maxBlendSec = 0.8;
  // Successive breaking: each link further from the body starts (and ends) its blend this much later
  // (shoulder -> elbow -> wrist -> fingers; spine -> neck -> head; hips -> thigh -> shin -> foot).
  double successionSec = 0.06;
  // IK gestures (touch, reach): the elbow's IK weight trails the shoulder's by this much (two-bone IK ".lag").
  double ikElbowLagSec = 0.1;
  // Retiming: a clip played faster or slower than authored keeps the spacing around its extremes (slow parts) and
  // changes the fast in-betweens more, instead of a linear scale. Local rate at most retimeMaxRate x the request.
  bool easePreservingRetime = true;
  double retimeMaxRate = 1.15;
  // Arcs: a blend whose wrist path deviates less than minArc (fraction of the chord) from a straight line gets a
  // breakdown: the elbow opens mid-blend (up to breakdownMaxDeg) so the wrist travels round the shoulder.
  double minArc = 0.10;
  double breakdownMaxDeg = 35.0;
  double breakdownMinChordM = 0.05;  // shorter wrist moves are not given breakdowns
};

// true | false | {"enabled", "maxBlendDegPerSec", "minBlendSec", "maxBlendSec", "successionSec", "ikElbowLagSec",
// "easePreservingRetime", "retimeMaxRate", "minArc", "breakdownMaxDeg", "breakdownMinChordM"}; null = defaults.
Result<AnimPrinciples> animPrinciplesFromJson(const Json& j);

// Quintic ease in/out (smootherstep): zero velocity and acceleration at both ends; peak slope 1.875 at x = 0.5.
double easeInOut(double x);
constexpr double kEasePeakSlope = 1.875;
// Integral of easeInOut from 0 to x (0.5 at x = 1): the clock of a layer whose playback rate eases with its blend.
double easeInOutIntegral(double x);
// Eased layer clock (scene frames of clip playback since the start) at `offset` frames after the layer start, for a
// layer of `length` scene frames whose rate ramps from 0 over clockIn and to 0 over clockOut: the clip still plays
// exactly `length` frames between start and end (its middle runs a little faster). Infinite length: no clockOut.
double easedClock(double offset, double length, double clockIn, double clockOut);
// Minimum blend length in scene frames for an amplitude in degrees.
double minBlendFrames(double amplitudeDeg, double fps, const AnimPrinciples& p);

// Successive-breaking rank of a clip role: 0 hips/spine/chest/clavicle, 1 neck/upperArm/thigh, 2 head/forearm/shin,
// 3 hand/foot/toe, 4 fingers. Unknown roles: 0.
int successionRank(std::string_view role);

// Time warp of a clip layer: scene frames since the layer start -> clip frame. Linear (speed x clipFps / sceneFps)
// or ease preserving (built from the clip's motion speed per clip frame).
class TimeWarp {
 public:
  static TimeWarp linear(double speed, double clipFps, double sceneFps);
  // clipMotion[k]: motion amount between clip frames k and k + 1 (any unit, >= 0); frames = clipMotion.size() + 1.
  // Total scene length equals the linear one (duration / speed), so ends and loops keep their timing.
  static TimeWarp easePreserving(const std::vector<double>& clipMotion, double speed, double clipFps, double sceneFps,
                                 const AnimPrinciples& p);
  double clipFrame(double sceneOffset, bool loop) const;
  double sceneLength() const { return linear_ ? clipLength_ / rate_ : sceneAt_.empty() ? 0.0 : sceneAt_.back(); }
  bool isLinear() const { return linear_; }

 private:
  bool linear_ = true;
  double rate_ = 1;        // clip frames per scene frame (linear)
  double clipLength_ = 0;  // clip frames (last frame index)
  std::vector<double> sceneAt_;  // scene offset of clip frame k (ease preserving)
};

// Rotation (applied to the forearm's local rotation) that opens the elbow by `degrees` in the current pose; identity
// when the arm is (nearly) straight or the bones are missing.
quat elbowOpening(const Skeleton& sk, const Pose& pose, int upperArm, int forearm, int hand, float degrees);

// Wrist-path measures used for breakdowns and by the tests: deviation of a polyline from its chord / chord length.
float arcDeviation(const std::vector<vec3>& path, float* chord = nullptr);

}  // namespace plush
