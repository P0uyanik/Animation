// Keyframe animation, skeletons and poses.
#pragma once
#include <map>
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
  const Track* find(std::string_view name) const;
  vec3 evaluate(std::string_view name, double frame, vec3 fallback) const;
};

struct Bone {
  std::string name;
  int parent = -1;
  vec3 head{0};  // rest-space pivot
};

struct Skeleton {
  std::vector<Bone> bones;  // parents always precede children
  int find(std::string_view name) const;
};

// Local bone rotations relative to the rest pose (rest frames are axis aligned).
struct Pose {
  std::vector<quat> local;
  vec3 rootOffset{0};
};

quat eulerDegreesToQuat(vec3 degrees);  // XYZ order
Pose restPose(const Skeleton& skeleton);
// Tracks "<prefix><bone>.rot" (euler degrees) and "<prefix>root.loc" (metres).
Pose evaluatePose(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame);
// Skinning matrices: world * boneGlobal * translate(-head).
std::vector<mat4> skinningMatrices(const Skeleton& skeleton, const Pose& pose, const mat4& world);

}  // namespace plush
