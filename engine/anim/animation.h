// Keyframe animation, skeletons and poses.
#pragma once
#include <map>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "core/math.h"

namespace plush {

enum class Interp { Smooth, Linear, Step };

struct Key {
  double frame = 0;
  vec3 value{0};
  Interp interp = Interp::Smooth;  // interpolation towards the next key
};

// A 3-component animation curve. Smooth keys use clamped cubic Hermite
// interpolation (no overshoot past neighbouring key values).
struct Track {
  std::vector<Key> keys;  // sorted by frame
  void setKey(Key key);
  bool removeKey(double frame, double tolerance = 1e-6);
  vec3 evaluate(double frame) const;
};

// Named tracks, e.g. "camera.position", "girl/head.rot", "girl/root.loc".
struct Clip {
  std::map<std::string, Track> tracks;
  // Tracks compiled from higher-level actions. Used only where `tracks` has no keys of its own (keys made by hand
  // always win) and never saved with the scene; the actions themselves are saved.
  std::shared_ptr<const Clip> generated;
  const Track* find(std::string_view name) const;
  vec3 evaluate(std::string_view name, double frame, vec3 fallback) const;
};

struct Bone {
  std::string name;
  int parent = -1;
  vec3 head{0};  // rest-space pivot
};

// Orientation of a hand in the rest pose: the direction its fingers point and the palm normal (unit vectors in the
// rest frame). Zero = the engine's own convention (fingers hang along -y, palm faces the body: -x left, +x right).
// Imported characters derive it from their finger geometry or take it from package metadata.
struct HandFrame {
  vec3 fingerDir{0};
  vec3 palmNormal{0};
};
struct Skeleton {
  std::vector<Bone> bones;  // parents always precede children
  HandFrame handL, handR;
  int find(std::string_view name) const;
};
// Leg length (thigh -> shin -> foot pivots, left side, else right); 0 if the skeleton has no legs.
float legLength(const Skeleton& skeleton);

// Local bone rotations relative to the rest pose (rest frames are axis aligned).
struct Pose {
  std::vector<quat> local;
  vec3 rootOffset{0};
};

quat eulerDegreesToQuat(vec3 degrees);  // XYZ order
Pose restPose(const Skeleton& skeleton);
// Tracks "<prefix><bone>.rot" (euler degrees) and "<prefix>root.loc" (metres).
Pose evaluatePose(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                  const std::map<std::string, vec3>* defaultRotations = nullptr);
// Skinning matrices: world * boneGlobal * translate(-head).
std::vector<mat4> skinningMatrices(const Skeleton& skeleton, const Pose& pose, const mat4& world);
// Global bone frames (world * parent chain); column 3 is the bone pivot in world space.
std::vector<mat4> boneGlobals(const Skeleton& skeleton, const Pose& pose, const mat4& world);
// Analytic two-bone IK: rotates the end bone's parent and grandparent so the end pivot reaches `target`.
void solveTwoBoneIK(const Skeleton& skeleton, Pose& pose, const mat4& world, int endBone, vec3 target, float weight);
// Points a bone's rest +Z axis at a world target (eyes), limited to maxAngleDeg.
void aimBone(const Skeleton& skeleton, Pose& pose, const mat4& world, int bone, vec3 target, float weight, float maxAngleDeg);
// Constraint tracks: "<prefix>ik.<bone>" (+ ".weight"), "<prefix>lookAt" (+ ".weight", aims every "eye.*" bone).
// Procedural "life" layered on top of the keyed pose, so a character never stands frozen and nobody has to key
// breathing or blinks: breathing (chest/spine/shoulders), slow weight shift (hips with leg compensation), small
// head drift, automatic blinks, and the head following the gaze ("<prefix>lookAt") with a lag. Deterministic:
// everything is a function of the frame and the seed, so any frame renders identically on its own.
struct LifeParams {
  bool enabled = false;
  float breathing = 1.0f;      // amplitude scale
  float sway = 1.0f;           // weight-shift amplitude scale
  float headDrift = 1.0f;      // small idle head motion
  float blinkInterval = 3.6f;  // mean seconds between blinks (0 = no automatic blinks)
  float headFollow = 0.55f;    // share of a gaze turn taken by neck + head
  float headLagSec = 0.2f;     // the head follows the eyes this much later
  bool blinkLids = true;       // false: blinks are a morph (character expression map), lid bones are not rotated
  uint32_t seed = 1;
};
void applyLife(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame, double fps,
               const mat4& world, const LifeParams& life, Pose& pose);
// Blink closure in [0, 1] at time t (seconds) for an average interval; exposed for tests.
float blinkAmount(double t, float interval, uint32_t seed);

// Fingers (bones thumbA/thumbB and f0a..f3a / f0b..f3b with .L/.R). Any subset of at least two digits works (missing
// digits are skipped); hands with fewer digits are left alone. Curl, spread and thumb axes come from the hand's
// HandFrame (Skeleton::handL/handR).
struct HandPose {
  float curl = 0.25f;    // 0 open .. 1 fist (all fingers)
  float thumb = 0.15f;   // 0 open .. 1 folded over the palm
  float spread = 0.0f;   // -1 together .. 1 fanned out
  float index = -1.0f;   // >= 0 overrides the index finger's curl (pointing = curl 1, index 0)
  bool grasp = false;    // curl each finger until its tip touches the sphere below
  vec3 graspCentre{0};   // in the hand bone's rest frame, relative to its head
  float graspRadius = 0.02f;
  vec3 graspAxis{0};     // non-zero: the object is a cylinder along this axis (hand rest frame), else a sphere
  float graspWeight = 1.0f;
};
// Poses one hand ('L' or 'R'). With grasp, each finger's curl is searched (bisection) so that its tip rests on the
// sphere surface: a small object closes the hand further than a large one.
void applyHandPose(const Skeleton& skeleton, Pose& pose, const mat4& world, char side, const HandPose& hp);
// Fingertip positions (world) of one hand, thumb first; empty if the skeleton has no finger bones.
std::vector<vec3> fingertips(const Skeleton& skeleton, const Pose& pose, const mat4& world, char side);

// Tracks: "<prefix>hand.L" = (curl, thumb, spread), "<prefix>hand.L.index" (x), "<prefix>hand.L.grasp" = sphere
// centre (hand rest frame), "<prefix>hand.L.graspRadius" (x), "<prefix>hand.L.grasp.weight" (x). Same for R.
void applyConstraints(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                      const mat4& world, Pose& pose);

}  // namespace plush
