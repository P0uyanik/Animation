#include "anim/animation.h"

#include <format>

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

Pose evaluatePose(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                  const std::map<std::string, vec3>* defaults) {
  Pose p = restPose(skeleton);
  for (size_t i = 0; i < skeleton.bones.size(); ++i) {
    const Track* t = clip.find(prefix + skeleton.bones[i].name + ".rot");
    if (t && !t->keys.empty()) {
      p.local[i] = eulerDegreesToQuat(t->evaluate(frame));
    } else if (defaults) {
      auto it = defaults->find(skeleton.bones[i].name);
      if (it != defaults->end()) p.local[i] = eulerDegreesToQuat(it->second);
    }
  }
  p.rootOffset = clip.evaluate(prefix + "root.loc", frame, vec3(0));
  return p;
}

std::vector<mat4> boneGlobals(const Skeleton& skeleton, const Pose& pose, const mat4& world) {
  size_t n = skeleton.bones.size();
  std::vector<mat4> global(n);
  for (size_t i = 0; i < n; ++i) {
    const Bone& b = skeleton.bones[i];
    mat4 rot = glm::mat4_cast(i < pose.local.size() ? pose.local[i] : quat(1, 0, 0, 0));
    if (b.parent < 0) global[i] = world * glm::translate(mat4(1), b.head + pose.rootOffset) * rot;
    else global[i] = global[size_t(b.parent)] * glm::translate(mat4(1), b.head - skeleton.bones[size_t(b.parent)].head) * rot;
  }
  return global;
}

std::vector<mat4> skinningMatrices(const Skeleton& skeleton, const Pose& pose, const mat4& world) {
  std::vector<mat4> skin = boneGlobals(skeleton, pose, world);
  for (size_t i = 0; i < skin.size(); ++i) skin[i] = skin[i] * glm::translate(mat4(1), -skeleton.bones[i].head);
  return skin;
}

namespace {
float angleBetween(vec3 x, vec3 y) {
  float lx = glm::length(x), ly = glm::length(y);
  if (lx < 1e-9f || ly < 1e-9f) return 0;
  return std::acos(std::clamp(glm::dot(x / lx, y / ly), -1.0f, 1.0f));
}
}  // namespace

void solveTwoBoneIK(const Skeleton& sk, Pose& pose, const mat4& world, int end, vec3 target, float weight) {
  if (end < 0 || weight <= 0) return;
  int mid = sk.bones[size_t(end)].parent;
  if (mid < 0) return;
  int root = sk.bones[size_t(mid)].parent;
  if (root < 0) return;
  auto G = boneGlobals(sk, pose, world);
  vec3 a(G[size_t(root)][3]), b(G[size_t(mid)][3]), c(G[size_t(end)][3]);
  quat aGr = glm::normalize(glm::quat_cast(mat3(G[size_t(root)]))), bGr = glm::normalize(glm::quat_cast(mat3(G[size_t(mid)])));
  float lab = glm::length(b - a), lcb = glm::length(c - b);
  float lat = std::clamp(glm::length(target - a), 1e-4f, (lab + lcb) * 0.999f);
  float acab0 = angleBetween(c - a, b - a), babc0 = angleBetween(a - b, c - b), acat0 = angleBetween(c - a, target - a);
  float acab1 = std::acos(std::clamp((lcb * lcb - lab * lab - lat * lat) / (-2 * lab * lat), -1.0f, 1.0f));
  float babc1 = std::acos(std::clamp((lat * lat - lab * lab - lcb * lcb) / (-2 * lab * lcb), -1.0f, 1.0f));
  vec3 axis0 = glm::cross(c - a, b - a);
  if (glm::length2(axis0) < 1e-12f) axis0 = glm::cross(c - a, vec3(0, 0, -1));
  axis0 = glm::normalize(axis0);
  vec3 axis1 = glm::cross(c - a, target - a);
  axis1 = glm::length2(axis1) < 1e-12f ? axis0 : glm::normalize(axis1);
  quat r0 = glm::angleAxis(acab1 - acab0, glm::inverse(aGr) * axis0);
  quat r1 = glm::angleAxis(babc1 - babc0, glm::inverse(bGr) * axis0);
  quat r2 = glm::angleAxis(acat0, glm::inverse(aGr) * axis1);
  // World order: bend the elbow (r1), restore the shoulder-to-wrist direction (r0), then swing it onto the target (r2).
  quat aNew = pose.local[size_t(root)] * (r2 * r0), bNew = pose.local[size_t(mid)] * r1;
  pose.local[size_t(root)] = glm::slerp(pose.local[size_t(root)], aNew, std::clamp(weight, 0.0f, 1.0f));
  pose.local[size_t(mid)] = glm::slerp(pose.local[size_t(mid)], bNew, std::clamp(weight, 0.0f, 1.0f));
}

void aimBone(const Skeleton& sk, Pose& pose, const mat4& world, int bone, vec3 target, float weight, float maxAngleDeg) {
  if (bone < 0 || weight <= 0) return;
  auto G = boneGlobals(sk, pose, world);
  int parent = sk.bones[size_t(bone)].parent;
  mat3 parentRot = parent >= 0 ? mat3(G[size_t(parent)]) : mat3(world);
  vec3 pivot(G[size_t(bone)][3]);
  vec3 dir = target - pivot;
  if (glm::length2(dir) < 1e-12f) return;
  vec3 d = glm::normalize(glm::transpose(parentRot) * glm::normalize(dir));
  float maxA = glm::radians(maxAngleDeg), ang = std::acos(std::clamp(d.z, -1.0f, 1.0f));
  if (ang > maxA) {
    vec2 perp(d.x, d.y);
    float lp = glm::length(perp);
    perp = lp > 1e-6f ? perp / lp : vec2(0, 1);
    d = vec3(perp * std::sin(maxA), std::cos(maxA));
  }
  vec3 z(0, 0, 1);
  vec3 axis = glm::cross(z, d);
  float s = glm::length(axis);
  quat q = s < 1e-7f ? quat(1, 0, 0, 0) : glm::angleAxis(std::atan2(s, glm::dot(z, d)), axis / s);
  pose.local[size_t(bone)] = glm::slerp(pose.local[size_t(bone)], q, std::clamp(weight, 0.0f, 1.0f));
}

namespace {
struct FingerChain {
  int a = -1, b = -1;
};
struct HandBones {
  int hand = -1;
  FingerChain thumb, fingers[4];  // fingers[3] is the index finger (next to the thumb)
  bool valid() const {
    if (hand < 0 || thumb.a < 0 || thumb.b < 0) return false;
    for (auto& f : fingers)
      if (f.a < 0 || f.b < 0) return false;
    return true;
  }
};
HandBones findHand(const Skeleton& sk, char side) {
  std::string s = std::string(".") + side;
  HandBones h;
  h.hand = sk.find("hand" + s);
  h.thumb = {sk.find("thumbA" + s), sk.find("thumbB" + s)};
  for (int k = 0; k < 4; ++k) h.fingers[k] = {sk.find(std::format("f{}a{}", k, s)), sk.find(std::format("f{}b{}", k, s))};
  return h;
}
// Curl rotations in the hand's rest frame. Fingers hang along -y with the palm facing the body (-x for the left
// hand), so they curl about -z (left) / +z (right); the thumb folds about a tilted axis across the palm.
quat fingerRot(char side, float angleDeg, float spreadDeg) {
  float sz = side == 'L' ? -1.0f : 1.0f;
  return glm::angleAxis(glm::radians(angleDeg), vec3(0, 0, sz)) * glm::angleAxis(glm::radians(spreadDeg), vec3(1, 0, 0));
}
quat thumbRot(char side, float angleDeg) {
  // Left: about (0.35, 0, -1) = towards the palm (-x) and across it (-z). A rotation axis mirrors across x = 0 as
  // (x, -y, -z), so the right hand uses (0.35, 0, 1).
  float sz = side == 'L' ? -1.0f : 1.0f;
  return glm::angleAxis(glm::radians(angleDeg), glm::normalize(vec3(0.35f, 0.0f, sz)));
}
void setChain(Pose& pose, const FingerChain& f, quat ra, quat rb) {
  pose.local[size_t(f.a)] = ra;
  pose.local[size_t(f.b)] = rb;
}
vec3 chainTip(const Skeleton& sk, const mat4& handGlobal, int handBone, const FingerChain& f, quat ra, quat rb) {
  vec3 ha = sk.bones[size_t(f.a)].head, hb = sk.bones[size_t(f.b)].head;
  mat4 ga = handGlobal * glm::translate(mat4(1), ha - sk.bones[size_t(handBone)].head) * glm::mat4_cast(ra);
  mat4 gb = ga * glm::translate(mat4(1), hb - ha) * glm::mat4_cast(rb);
  return vec3(gb * vec4(hb - ha, 1));  // tip: one more segment of the same length beyond b's head
}
}  // namespace

void applyHandPose(const Skeleton& sk, Pose& pose, const mat4& world, char side, const HandPose& hp) {
  HandBones h = findHand(sk, side);
  if (!h.valid()) return;
  const float kA = 75.0f, kB = 95.0f;  // full-curl angles of the first and second segment
  auto fingerCurl = [&](int k) { return k == 3 && hp.index >= 0 ? hp.index : hp.curl; };
  for (int k = 0; k < 4; ++k) {
    float c = std::clamp(fingerCurl(k), 0.0f, 1.0f), spread = hp.spread * 7.0f * (float(k) - 1.5f);
    setChain(pose, h.fingers[k], fingerRot(side, c * kA, spread), fingerRot(side, c * kB, 0));
  }
  float tc = std::clamp(hp.thumb, 0.0f, 1.0f);
  setChain(pose, h.thumb, thumbRot(side, tc * 55.0f), thumbRot(side, tc * 45.0f));
  if (!hp.grasp || hp.graspWeight <= 0) return;
  // Contact search in the hand's own frame (the hand bone's global transform does not depend on the fingers).
  mat4 handGlobal = boneGlobals(sk, pose, world)[size_t(h.hand)];
  vec3 centre = vec3(handGlobal * vec4(hp.graspCentre, 1));
  float scale = glm::length(vec3(handGlobal[0]));
  float reach = (hp.graspRadius + 0.0045f) * scale;  // finger tube radius: the skin rests on the object
  vec3 axis = glm::length(hp.graspAxis) > 1e-6f ? glm::normalize(vec3(handGlobal * vec4(hp.graspAxis, 0))) : vec3(0);
  auto touching = [&](const FingerChain& f, quat ra, quat rb) {
    vec3 d = chainTip(sk, handGlobal, h.hand, f, ra, rb) - centre;
    d -= axis * glm::dot(d, axis);  // cylinder: distance to the axis
    return glm::length(d) <= reach;
  };
  auto search = [&](const FingerChain& f, auto rotA, auto rotB, float c0) {
    if (touching(f, rotA(c0), rotB(c0))) return c0;
    float lo = c0, hi = 1.0f;
    if (!touching(f, rotA(hi), rotB(hi))) return hi;
    for (int it = 0; it < 14; ++it) {
      float mid = 0.5f * (lo + hi);
      (touching(f, rotA(mid), rotB(mid)) ? hi : lo) = mid;
    }
    return hi;
  };
  float w = std::clamp(hp.graspWeight, 0.0f, 1.0f);
  for (int k = 0; k < 4; ++k) {
    float c0 = std::clamp(fingerCurl(k), 0.0f, 1.0f), spread = hp.spread * 7.0f * (float(k) - 1.5f);
    auto ra = [&](float c) { return fingerRot(side, c * kA, spread); };
    auto rb = [&](float c) { return fingerRot(side, c * kB, 0); };
    float c = glm::mix(c0, search(h.fingers[k], ra, rb, 0.0f), w);
    setChain(pose, h.fingers[k], ra(c), rb(c));
  }
  auto ta = [&](float c) { return thumbRot(side, c * 55.0f); };
  auto tb = [&](float c) { return thumbRot(side, c * 45.0f); };
  float t = glm::mix(tc, search(h.thumb, ta, tb, 0.0f), w);
  setChain(pose, h.thumb, ta(t), tb(t));
}

std::vector<vec3> fingertips(const Skeleton& sk, const Pose& pose, const mat4& world, char side) {
  HandBones h = findHand(sk, side);
  if (!h.valid()) return {};
  mat4 hg = boneGlobals(sk, pose, world)[size_t(h.hand)];
  std::vector<vec3> tips{chainTip(sk, hg, h.hand, h.thumb, pose.local[size_t(h.thumb.a)], pose.local[size_t(h.thumb.b)])};
  for (auto& f : h.fingers) tips.push_back(chainTip(sk, hg, h.hand, f, pose.local[size_t(f.a)], pose.local[size_t(f.b)]));
  return tips;
}

void applyConstraints(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                      Pose& pose) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    std::string name = prefix + "ik." + sk.bones[i].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    float w = clip.evaluate(name + ".weight", frame, vec3(1)).x;
    solveTwoBoneIK(sk, pose, world, int(i), t->evaluate(frame), w);
  }
  for (char side : {'L', 'R'}) {
    std::string base = prefix + "hand." + side;
    HandPose hp;
    vec3 v = clip.evaluate(base, frame, vec3(hp.curl, hp.thumb, hp.spread));
    hp.curl = v.x;
    hp.thumb = v.y;
    hp.spread = v.z;
    if (const Track* t = clip.find(base + ".index"); t && !t->keys.empty()) hp.index = t->evaluate(frame).x;
    if (const Track* t = clip.find(base + ".grasp"); t && !t->keys.empty()) {
      hp.grasp = true;
      hp.graspCentre = t->evaluate(frame);
      hp.graspRadius = clip.evaluate(base + ".graspRadius", frame, vec3(hp.graspRadius)).x;
      hp.graspAxis = clip.evaluate(base + ".graspAxis", frame, vec3(0));
      hp.graspWeight = clip.evaluate(base + ".grasp.weight", frame, vec3(1)).x;
    }
    applyHandPose(sk, pose, world, side, hp);
  }
  if (const Track* t = clip.find(prefix + "lookAt"); t && !t->keys.empty()) {
    vec3 target = t->evaluate(frame);
    float w = clip.evaluate(prefix + "lookAt.weight", frame, vec3(1)).x;
    for (size_t i = 0; i < sk.bones.size(); ++i)
      if (sk.bones[i].name.rfind("eye.", 0) == 0) aimBone(sk, pose, world, int(i), target, w, 38.0f);
  }
}

}  // namespace plush
