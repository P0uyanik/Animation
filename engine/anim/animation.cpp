#include "anim/animation.h"

#include <algorithm>

namespace plush {

void Track::setKey(Key key) {
  auto it = std::lower_bound(keys.begin(), keys.end(), key.frame,
                             [](const Key& k, double f) { return k.frame < f; });
  if (it != keys.end() && std::abs(it->frame - key.frame) < 1e-6) {
    *it = key;
  } else {
    keys.insert(it, key);
  }
}

bool Track::removeKey(double frame, double tolerance) {
  for (auto it = keys.begin(); it != keys.end(); ++it) {
    if (std::abs(it->frame - frame) <= tolerance) {
      keys.erase(it);
      return true;
    }
  }
  return false;
}

namespace {
// Slope at key i (per frame), clamped to avoid overshoot at local extrema.
float keySlope(const std::vector<Key>& keys, size_t i, int c) {
  if (i == 0 || i + 1 >= keys.size()) return 0.0f;  // ease in/out at the ends
  float vp = keys[i - 1].value[c], v = keys[i].value[c], vn = keys[i + 1].value[c];
  if ((v - vp) * (vn - v) <= 0.0f) return 0.0f;  // local extremum: flat tangent
  double dt = keys[i + 1].frame - keys[i - 1].frame;
  return dt > 0 ? float((vn - vp) / dt) : 0.0f;
}
}  // namespace

vec3 Track::evaluate(double frame) const {
  if (keys.empty()) return vec3(0);
  if (frame <= keys.front().frame) return keys.front().value;
  if (frame >= keys.back().frame) return keys.back().value;
  auto it = std::upper_bound(keys.begin(), keys.end(), frame, [](double f, const Key& k) { return f < k.frame; });
  size_t i1 = size_t(it - keys.begin()), i0 = i1 - 1;
  const Key& k0 = keys[i0];
  const Key& k1 = keys[i1];
  double h = k1.frame - k0.frame;
  float t = h > 0 ? float((frame - k0.frame) / h) : 0.0f;
  switch (k0.interp) {
    case Interp::Step: return k0.value;
    case Interp::Linear: return glm::mix(k0.value, k1.value, t);
    case Interp::Smooth: break;
  }
  float t2 = t * t, t3 = t2 * t;
  float h00 = 2 * t3 - 3 * t2 + 1, h10 = t3 - 2 * t2 + t, h01 = -2 * t3 + 3 * t2, h11 = t3 - t2;
  vec3 out;
  for (int c = 0; c < 3; ++c) {
    float m0 = keySlope(keys, i0, c) * float(h), m1 = keySlope(keys, i1, c) * float(h);
    out[c] = h00 * k0.value[c] + h10 * m0 + h01 * k1.value[c] + h11 * m1;
  }
  return out;
}

const Track* Clip::find(std::string_view name) const {
  auto it = tracks.find(std::string(name));
  return it == tracks.end() ? nullptr : &it->second;
}

vec3 Clip::evaluate(std::string_view name, double frame, vec3 fallback) const {
  const Track* t = find(name);
  return (t && !t->keys.empty()) ? t->evaluate(frame) : fallback;
}

int Skeleton::find(std::string_view name) const {
  for (size_t i = 0; i < bones.size(); ++i)
    if (bones[i].name == name) return int(i);
  return -1;
}

quat eulerDegreesToQuat(vec3 d) {
  vec3 r = glm::radians(d);
  quat qx = glm::angleAxis(r.x, vec3(1, 0, 0));
  quat qy = glm::angleAxis(r.y, vec3(0, 1, 0));
  quat qz = glm::angleAxis(r.z, vec3(0, 0, 1));
  return qz * qy * qx;  // apply X first, then Y, then Z
}

Pose restPose(const Skeleton& skeleton) {
  Pose p;
  p.local.assign(skeleton.bones.size(), quat(1, 0, 0, 0));
  return p;
}

Pose evaluatePose(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame) {
  Pose p = restPose(skeleton);
  for (size_t i = 0; i < skeleton.bones.size(); ++i) {
    const Track* t = clip.find(prefix + skeleton.bones[i].name + ".rot");
    if (t && !t->keys.empty()) p.local[i] = eulerDegreesToQuat(t->evaluate(frame));
  }
  p.rootOffset = clip.evaluate(prefix + "root.loc", frame, vec3(0));
  return p;
}

std::vector<mat4> skinningMatrices(const Skeleton& skeleton, const Pose& pose, const mat4& world) {
  size_t n = skeleton.bones.size();
  std::vector<mat4> global(n), skin(n);
  for (size_t i = 0; i < n; ++i) {
    const Bone& b = skeleton.bones[i];
    mat4 rot = glm::mat4_cast(i < pose.local.size() ? pose.local[i] : quat(1, 0, 0, 0));
    if (b.parent < 0) {
      global[i] = glm::translate(mat4(1), b.head + pose.rootOffset) * rot;
    } else {
      global[i] = global[size_t(b.parent)] * glm::translate(mat4(1), b.head - skeleton.bones[size_t(b.parent)].head) * rot;
    }
    skin[i] = world * global[i] * glm::translate(mat4(1), -b.head);
  }
  return skin;
}

}  // namespace plush
