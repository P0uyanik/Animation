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
  // Retiming: a clip played faster or slower than authored is split into its movements (between the motion minima:
  // reversals, holds, extremes); each movement gets one constant rate from its peak motion, so the big actions absorb
  // the change while anticipations, settles and holds keep their authored spacing, and every movement keeps its own
  // ease shape (rates change only where the motion is at a minimum). At most retimeMaxRate x the requested rate.
  bool easePreservingRetime = true;
  double retimeMaxRate = 1.15;
  double retimeContrast = 1;  // exponent on a movement's normalised peak: > 1 keeps more of the smaller movements' spacing
  // Arcs: a blend whose wrist path deviates less than minArc (fraction of the chord) from a straight line gets a
  // breakdown: mid-blend the elbow opens or bends further (whichever curves the path; up to breakdownMaxDeg) so the
  // wrist travels on an arc instead of the straight chord.
  double minArc = 0.10;
  double breakdownMaxDeg = 35.0;
  double breakdownMinChordM = 0.05;  // shorter wrist moves are not given breakdowns
};

// true | false | {"enabled", "maxBlendDegPerSec", "minBlendSec", "maxBlendSec", "successionSec", "ikElbowLagSec",
// "easePreservingRetime", "retimeMaxRate", "retimeContrast", "minArc", "breakdownMaxDeg", "breakdownMinChordM"};
// null = defaults.
Result<AnimPrinciples> animPrinciplesFromJson(const Json& j);

// Reach mechanics (T-134): slow-in / slow-out, anticipation, arcs and overlap for the prop reaches of the hand-prop
// interactions (scene/interaction.cpp: reach / grasp and the hand-over receiver, so also the verbs pick_up and pass).
// Scene setting "reachMechanics" (scene/scene.h): absent / null / false = off (the tracks before T-134, bit for bit),
// true = on with these defaults, an object = field overrides ("enabled" defaults to true in an object).
struct ReachMechanics {
  bool enabled = false;
  // E1a ease: the wrist target travels one curve through the reach's three points (start, approach, contact) on a
  // slow-in / slow-out profile (zero speed and acceleration at the start and at the contact), keyed every frame,
  // instead of the three smooth keys, whose path has a corner at the approach point. easePeak: the fraction of the
  // reach at which the wrist is fastest (< 0.5: a longer slow-out into the contact). The IK weight comes in on the
  // same curve (weightPeak) and is full at weightFull of the reach instead of at the approach point, where it would
  // stop rising while the target is still fast and brake the wrist. With the mechanics on, the
  // collision planner's wrist push also stops at pinned frames (a ramp no longer resumes right after a contact).
  bool ease = true;
  double easePeak = 0.45;
  double weightPeak = 0.4, weightFull = 0.85;  // the IK weight comes in on the same curve, full at this share of the reach
  // E1a anticipation: the body leads the hand. From anticipationSec before the reach starts the torso first moves a
  // little away from the prop (counter, fraction of the lead) and then leans and turns towards it (leanDeg about the
  // horizontal axis across the reach, twistDeg about the vertical: the reaching shoulder comes forward; both scaled
  // down for props close to the shoulder), each link successionSec before the next (hips -> spine -> chest ->
  // shoulder -> wrist); the hips take hipShare of it and the shoulder joint advances shoulderM towards the prop. The
  // lead is full at leadPeak of the reach, is held to the contact and is given back over recoverSec. The wrists of
  // IK-driven arms stay on their targets (the arm is solved again from the moved shoulder); an arm that has an IK
  // track but is not on it yet rides only half way with the torso, so the body leads and the hand hangs back. The
  // reaching arm's clavicle turns towards the prop (clavicleDeg) and the pelvis shifts towards it (hipShiftM). A lead that would cost
  // the reaching arm its room against the body at the contact is reduced (quarter steps) until it does not.
  bool anticipation = true;
  double anticipationSec = 0.42;
  double counter = 0.15;
  double leanDeg = 8.0, twistDeg = 10.0;
  double shoulderM = 0.02;
  double clavicleDeg = 10.0;  // the reaching arm's clavicle turns its outer end this far towards the prop
  double hipShiftM = 0.012;   // the pelvis shifts this far towards the prop (legs keep their hip joints)
  double hipShare = 0.3;
  double successionSec = 0.06;
  double leadPeak = 0.6;
  double recoverSec = 0.6;
  double headStabilize = 0.7;  // share of the torso lead the neck takes back (the eyes keep their aim)
  // E1b arcs: no wrist move is a straight chord. A carry (hold) and the giver's way to a hand-over point travel a
  // shallow arc with their own timing: the mid point is `arc` x chord away from the chord, bowing upward (a move that
  // is itself nearly vertical bows away from the shoulder; less when the arm could not reach that far). The hand's
  // way back after a release is arced the same way. A reach's eased curve (needs "ease") takes the approach
  // point as the direction the hand arrives from instead of a point to pass, so its bend is spread over the whole
  // reach, and is bent to at least `arc`. Moves shorter than arcMinChordM stay as they are.
  bool arcs = true;
  double arc = 0.2;
  double approachReach = 2.0;  // reach: the curve's control point, in approach distances out from the contact
  double arcMinChordM = 0.03;
  // E1c overlap and settle (needs "anticipation"): the torso and the shoulder follow the lead through a damped
  // response (anim/body_mechanics.h followKernel: settles within torsoSettleSec, overshoots by torsoOvershoot of a
  // step), so they run a little past the lead and settle, and again when the lead is given back after the contact.
  // The head's counter turn has its own response, headLagSec later and looser (headSettleSec, headOvershoot): the
  // head first goes with the torso, then catches up and settles after it. Hair and other spring chains (the
  // character's "dynamics", anim/secondary.h) follow the head as they do any motion.
  bool overlap = true;
  double torsoSettleSec = 0.33, torsoOvershoot = 0.12;
  double headLagSec = 0.08, headSettleSec = 0.5, headOvershoot = 0.2;
  // Settle at the contact: when the hand stops, the body runs on past its lead by settleAmount of it, swings back
  // and comes to rest (a damped swing with the period settleSec); the head does the same through its later response.
  double settleAmount = 0.25, settleSec = 0.5;
};
// null | true | false | {"enabled", "ease", "easePeak", "anticipation", "anticipationSec", "counter", "leanDeg",
// "twistDeg", "shoulderM", "hipShare", "successionSec", "leadPeak", "recoverSec", "headStabilize", "arcs", "arc", "arcMinChordM",
// "overlap", "torsoSettleSec", "torsoOvershoot", "headLagSec", "headSettleSec", "headOvershoot", "settleAmount", "settleSec",
// "clavicleDeg", "hipShiftM", "weightPeak", "weightFull", "approachReach"}.
Result<ReachMechanics> reachMechanicsFromJson(const Json& j);
// Slow-in / slow-out travel fraction at x in [0, 1] with the peak speed at `peak` (0.5 = easeInOut).
double reachEase(double x, double peak);
// Body lead envelope at x = (frame - reach start) / (contact - reach start): 0 before -a (a = anticipation / reach
// length), dips to -counter, crosses 0 near x = 0, 1 from leadPeak to the contact (x = 1), back to 0 by 1 + r.
double reachLead(double x, double a, double r, const ReachMechanics& m);

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

// Rotation (applied to the forearm's local rotation) that opens the elbow by `degrees` in the current pose (negative:
// bends it further, up to 150 degrees); identity when the arm is (nearly) straight or the bones are missing.
quat elbowOpening(const Skeleton& sk, const Pose& pose, int upperArm, int forearm, int hand, float degrees);

// Wrist-path measures used for breakdowns and by the tests: deviation of a polyline from its chord / chord length.
float arcDeviation(const std::vector<vec3>& path, float* chord = nullptr);

}  // namespace plush
