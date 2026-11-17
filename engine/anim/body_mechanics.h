// Body mechanics (T-045): shared, data-driven shoulder, torso and weight-shift motion layered on the keyed / clip pose,
// so arms, torso and legs move as one body instead of as separately keyed parts.
//
// Character independent: bones are found by the shared humanoid role names (hips, spine, chest, neck, head,
// upperArm/forearm/hand, thigh/shin/foot with .L/.R) and, for the clavicle and extra helper bones, by candidate names
// from the shared rig profile (content/rig_profiles/body_mechanics.json). Tuning comes from data only: shared defaults,
// a personality profile (content/personality/<id>[.draft].json: tempo, energy, posture) and scene overrides. A rig
// without clavicles, spine segments or legs skips those parts silently.
//
// What it does, per frame (deterministic, random access):
//  - drivers: arm elevation above rest, forward / sideways reach and extension per arm, measured from the clip pose
//    and the arm IK targets (ik.hand.*), and how upright the legs are (standing);
//  - follow-through: drivers pass through a delayed, damped spring response (settle time and overshoot from the
//    profile's tempo); the shoulders use a faster response than the torso, so the torso overlaps the arm, and the
//    weight shift a slower one without overshoot (the whole body's mass);
//  - clavicle: shrug (elevation) and protraction (forward reach) up to per-rig limits; the arm pivot rides on it;
//  - torso: spine and chest lean into forward reaches, twist toward the reaching arm (pelvis counter-rotates), bend
//    away from a raised arm; the neck counter-rotates part of it (head stabilisation);
//  - weight shift: a slow idle alternation between the legs and a shift toward a reaching arm: pelvis translation and
//    roll (free hip drops), spine counter-roll, knees soften; the feet stay planted (two-bone leg IK);
//  - posture (rest layer from the profile): slouch, shoulders forward, head pitch;
//  - carry: pivots of bones whose skeleton parent is not their anatomical carrier (unparented clavicles, arms and thighs
//    of imported rigs) follow the carrier through Pose::offset, so IK and skinning see the moved shoulders and hips.
#pragma once
#include <array>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct BodyMechanicsParams {
  bool enabled = false;
  // Participation scales (1 = shared default, 0 = off).
  float shoulder = 1.0f;       // clavicle shrug / protraction
  float torso = 1.0f;          // spine / chest follow
  float headStabilize = 0.6f;  // share of the torso rotation the neck takes back (0..1)
  float weightShift = 0.3f;    // idle weight-shift amount (0..1)
  float energy = 0.5f;         // 0..1: idle cadence (higher = more frequent weight changes)
  float gesture = 0.5f;        // 0..1: torso amplitude (0.5 = 1x)
  float leanTowardTask = 0.5f; // 0..1: forward lean into reaches (0.5 = 1x)
  // Posture rest layer (0 = neutral).
  float slouch = 0.0f, shouldersForward = 0.0f, headPitchDeg = 0.0f;
  // Follow-through (frames at 24 fps): torso delay, settle time (2 %) and overshoot (fraction of travel).
  float lagFrames = 2.0f, settleFrames = 12.0f, overshoot = 0.05f;
  // Limits (rig profile).
  float shrugMaxDeg = 12.0f, protractMaxDeg = 10.0f;
  float leanMaxDeg = 6.0f, twistMaxDeg = 8.0f, sideMaxDeg = 3.0f;
  float pelvisShift = 0.035f;  // lateral pelvis shift at full weight shift, fraction of leg length
  float pelvisRollDeg = 3.0f;  // free hip drop at full weight shift
  float kneeSoften = 0.008f;   // pelvis lowering at full weight shift, fraction of leg length
  uint32_t seed = 1;
};

// Shared rig profile: clavicle / helper candidate names and limits (content/rig_profiles/body_mechanics.json).
struct BodyMechanicsRigProfile {
  std::vector<std::string> clavicle{"clavicle", "shoulder"};  // base names, ".L" / ".R" appended
  std::vector<std::string> hipHelpers;                         // carried (with rotation) by the hips, ".L" / ".R"
  Json limits;                                                 // overrides of the *_max_deg / pelvis_* limits
};
Result<BodyMechanicsRigProfile> bodyMechanicsRigProfileFromJson(const Json& j);

// Applies a personality profile (plush.personality: tempo, energy, posture records; missing = neutral) and then a
// scene "bodyMechanics" object (explicit keys, same names as the fields) to `p`. Unknown keys are ignored.
void applyPersonalityToBodyMechanics(BodyMechanicsParams& p, const Json& personality);
void applyBodyMechanicsOverrides(BodyMechanicsParams& p, const Json& over);
void applyBodyMechanicsLimits(BodyMechanicsParams& p, const Json& limits);

// Bones of one skeleton (-1 = missing). Index 0 = left, 1 = right.
struct BodyMechanicsRig {
  int hips = -1, spine = -1, chest = -1, neck = -1, head = -1;
  std::array<int, 2> clavicle{-1, -1}, upper{-1, -1}, fore{-1, -1}, hand{-1, -1}, thigh{-1, -1}, shin{-1, -1}, foot{-1, -1};
  std::vector<int> hipHelpers;
  std::array<float, 2> armLength{0, 0}, restElevDeg{0, 0};
  float legLength = 0;
  bool arm(int s) const { return upper[size_t(s)] >= 0 && fore[size_t(s)] >= 0 && hand[size_t(s)] >= 0 && armLength[size_t(s)] > 0; }
  bool leg(int s) const { return thigh[size_t(s)] >= 0 && shin[size_t(s)] >= 0 && foot[size_t(s)] >= 0; }
};
BodyMechanicsRig bindBodyMechanics(const Skeleton& skeleton, const BodyMechanicsRigProfile& profile);

// Per-frame drivers measured from the pose before the layer.
struct BodyDrivers {
  std::array<float, 2> elev{0, 0};  // arm elevation above its rest elevation (degrees)
  std::array<float, 2> fwd{0, 0};   // forward reach 0..1 (forward component x extension)
  std::array<float, 2> lat{0, 0};   // sideways (outward) reach 0..1
  float standing = 1;               // 1 = legs upright, 0 = sitting / crouching
  float walk = 0;                   // 1 = a walk owns the legs
};
BodyDrivers operator+(const BodyDrivers& a, const BodyDrivers& b);
BodyDrivers operator*(const BodyDrivers& a, float k);

// Measures the drivers in character space. `ik[s]` = arm IK target (character space, xyz) and weight (w).
BodyDrivers measureBodyDrivers(const Skeleton& skeleton, const BodyMechanicsRig& rig, const Pose& pose,
                               const std::array<vec4, 2>& ik);

// Follow-through kernel: weights for the driver k frames ago (k = 0..n-1), sum 1. A delayed second-order (damped
// spring) impulse response with the given settle time (2 %) and overshoot; all in frames at the scene rate.
std::vector<float> followKernel(float delayFrames, float settleFrames, float overshoot);

// Idle weight-shift signal in [-1, 1] (+ = weight on the left leg) at time t (seconds).
float idleWeightShift(double t, const BodyMechanicsParams& p);

struct BodyMechanicsInput {
  BodyDrivers fast;  // shoulders (short response)
  BodyDrivers slow;  // torso (delayed, damped response)
  BodyDrivers weight;  // weight shift (delayed, slower, no overshoot)
  float idle = 0;    // idleWeightShift
};
// Applies the layer to `pose` (character space; call before constraints so IK and look-at work on the result).
void applyBodyMechanics(const Skeleton& skeleton, const BodyMechanicsRig& rig, const BodyMechanicsParams& p,
                        const BodyMechanicsInput& in, Pose& pose);

}  // namespace plush
