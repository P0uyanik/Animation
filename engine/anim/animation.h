// Keyframe animation, skeletons and poses.
#pragma once
#include <array>
#include <map>
#include <optional>
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
  // Optional per-bone pivot translation (empty = none, the default): added to a bone's pivot in its parent's frame
  // (character space for root bones). Body mechanics (anim/body_mechanics.h) use it to carry bones whose skeleton
  // parent is not their anatomical carrier, e.g. unparented arm and thigh pivots that should follow the torso.
  std::vector<vec3> offset;
};

// Natural eye travel relative to the head. Engine +X is the character's left and +Y is up.
// Values are degrees and may be overridden for each character through its life parameters.
struct GazeLimits {
  float maxUpDeg = 20.0f;
  float maxDownDeg = 25.0f;
  float maxLeftDeg = 30.0f;
  float maxRightDeg = 30.0f;
  // Neck assist (T-046): when a look target lies beyond the eyes' comfortable range (the soft limit's onset), the neck
  // turns by the excess, up to these angles, so the eyes still reach it. 0 disables. A hand-keyed neck is left alone.
  float assistYawDeg = 70.0f;
  float assistPitchDeg = 35.0f;
  float assistBodyYawDeg = 35.0f;  // beyond the neck's share the chest twists (yaw only), up to this angle
  float assistLagSec = 0.2f;       // the assist follows the target this much later than the eyes (eyes lead)
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
// Same with separate blend weights for the root (shoulder) and the middle joint (elbow): a middle weight that trails
// the root weight gives successive breaking (the shoulder leads, the elbow follows; T-061). Equal weights = above.
void solveTwoBoneIK(const Skeleton& skeleton, Pose& pose, const mat4& world, int endBone, vec3 target, float weight,
                    float midWeight);
// Points a bone's rest +Z axis at a world target (eyes), limited to maxAngleDeg.
void aimBone(const Skeleton& skeleton, Pose& pose, const mat4& world, int bone, vec3 target, float weight, float maxAngleDeg);
// Constraint tracks: "<prefix>ik.<bone>" (+ ".weight"; optional ".lag" = x frames the middle joint's weight trails
// the root's, T-061), "<prefix>lookAt" (+ ".weight", aims every "eye.*" bone).
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
  bool blinkIntervalSet = false;  // the scene gave blinkInterval explicitly (wins over the character's own timing)
  // Blink shape in seconds (close, stay shut, open). Defaults are the original global timing; a character package
  // may supply its own (CharacterAsset::blinkTiming).
  float blinkClose = 0.07f, blinkHold = 0.03f, blinkOpen = 0.12f;
  float headFollow = 0.55f;    // share of a gaze turn taken by neck + head
  float headLagSec = 0.2f;     // the head follows the eyes this much later
  GazeLimits gaze;             // eye travel relative to the final head pose
  bool blinkLids = true;       // false: blinks are a morph (character expression map), lid bones are not rotated
  bool face = true;            // facial layer (scene/face_layer.h): living face while life is enabled (T-046)
  uint32_t seed = 1;
};
// Deterministic hash in [0, 1) used by the life and face layers.
float lifeHash01(uint32_t a, uint32_t b);
// Breathing signal in [-1, 1] at time t (seconds) for a life seed: the same breath cycle the life layer moves the
// chest with (the face layer follows it).
float breathSignal(double t, uint32_t seed);
// Closes the upper lid bones ("lid.L", "lid.R") by `amount` (0..1); skeletons without lid bones are unchanged.
void applyLidBlink(const Skeleton& skeleton, Pose& pose, float amount);
void applyLife(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame, double fps,
               const mat4& world, const LifeParams& life, Pose& pose);
// Blink closure in [0, 1] at time t (seconds) for an average interval; exposed for tests.
float blinkAmount(double t, float interval, uint32_t seed, float close = 0.07f, float hold = 0.03f, float open = 0.12f);

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
  // T-051 per-finger pose and grasp (docs/architecture/INTERACTION_AFFORDANCES.md section 5). All optional: when none
  // is set (perFinger() false) applyHandPose is exactly the single-search pose above, bit for bit.
  bool band = false;     // contact band along graspAxis: every finger's contact lies in [bandLo, bandHi]
  float bandLo = 0, bandHi = 0;  // distances from graspCentre along graspAxis (metres, hand rest frame)
  enum class Thumb { Opposed = 0, Along = 1, Tucked = 2 } thumbMode = Thumb::Opposed;
  vec3 graspFace{0};     // non-zero (per-finger grasp only): a box face, the face's inward normal (hand rest frame);
                         // the solid is the slab |dot(p - graspCentre, normal)| <= graspRadius
  // Per-digit overrides, fingers 0..3 (bones f<k>a/b; 3 = index, 0 = little): (curl, spread, free), spread in the
  // units of `spread` (fans the finger by spread * 7 deg * (k - 1.5)); free >= 0.5 keeps the finger out of the grasp
  // search (it holds its curl, e.g. the curled fingers of a pinch). Unset = curl / index and spread above.
  std::array<std::optional<vec3>, 4> finger{};
  std::optional<vec2> thumbPose;  // (opposition 0..1, curl): opposition turns the thumb in front of the palm
  // Grasp weight per digit (fingers 0..3, thumb = 4), e.g. staggered closing; unset = graspWeight.
  std::array<std::optional<float>, 5> digitWeight{};
  bool perFinger() const;
};
// Fingertip (skin) radius of a hand from its skeleton: half the mean spacing of neighbouring finger roots; 0 if the
// hand has fewer than two fingers.
float fingertipRadius(const Skeleton& skeleton, char side);
// Poses one hand ('L' or 'R'). With grasp, each finger's curl is searched (bisection) so that its tip rests on the
// sphere surface: a small object closes the hand further than a large one. With perFinger() (T-051), each digit is
// posed and searched on its own: fingertips (skin radius fingertipRadius) on the cylinder / sphere / box-face surface,
// no finger segment inside it, contacts inside the band, the thumb opposed, along the axis or tucked.
void applyHandPose(const Skeleton& skeleton, Pose& pose, const mat4& world, char side, const HandPose& hp);
// Fingertip positions (world) of one hand, thumb first; empty if the skeleton has no finger bones.
std::vector<vec3> fingertips(const Skeleton& skeleton, const Pose& pose, const mat4& world, char side);

// Tracks: "<prefix>hand.L" = (curl, thumb, spread), "<prefix>hand.L.index" (x), "<prefix>hand.L.grasp" = sphere
// centre (hand rest frame), "<prefix>hand.L.graspRadius" (x), "<prefix>hand.L.grasp.weight" (x). Same for R.
// T-051 (all optional; absent = the pose above, unchanged): "hand.L.band" = (lo, hi, thumb 0 opposed / 1 along /
// 2 tucked), "hand.L.graspFace" (box-face normal), "hand.L.f<k>" = (curl, spread, free) for finger k (0 little .. 3 index),
// "hand.L.thumb" = (opposition, curl), "hand.L.stagger" (x = frames per finger; default 1 with a band, else 0):
// fingers close index -> little and open little -> index, one stagger step apart.
void applyConstraints(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                      const mat4& world, Pose& pose, const GazeLimits& gaze = {}, double fps = 30.0);

}  // namespace plush
