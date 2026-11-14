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
  if (it != tracks.end() && !it->second.keys.empty()) return &it->second;
  if (generated) return generated->find(name);
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
uint32_t hashMix(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
  return x;
}
float hash01(uint32_t a, uint32_t b) { return float(hashMix(a * 0x9E3779B9U + hashMix(b)) >> 8) / float(1 << 24); }
void rotateLocal(Pose& pose, int bone, vec3 eulerDeg) {
  if (bone >= 0) pose.local[size_t(bone)] = pose.local[size_t(bone)] * eulerDegreesToQuat(eulerDeg);
}
}  // namespace

float blinkAmount(double t, float interval, uint32_t seed, float closeS, float holdS, float openS) {
  if (interval <= 0 || t < 0) return 0.0f;
  // Blink k happens at the sum of k jittered intervals (0.55..1.45 of the mean); a blink closes in `close` s
  // (default 0.07), stays shut `hold` s (0.03) and opens in `open` s (0.12). Walk forward from a coarse index so long
  // shots stay cheap.
  const double close = std::max(1e-3f, closeS), hold = std::max(0.0f, holdS), open = std::max(1e-3f, openS);
  long k = std::max(0L, long(t / (interval * 1.45)) - 1);
  double start = 0;
  for (long i = 0; i < k; ++i) start += interval * (0.55 + 0.9 * hash01(seed, uint32_t(i)));
  for (long i = k;; ++i) {
    start += interval * (0.55 + 0.9 * hash01(seed, uint32_t(i)));
    if (start > t) return 0.0f;
    double u = t - start;
    if (u < close) return float(smoothstep01(float(u / close)));
    if (u < close + hold) return 1.0f;
    if (u < close + hold + open) return 1.0f - float(smoothstep01(float((u - close - hold) / open)));
  }
}

float legLength(const Skeleton& sk) {
  for (const char* s : {".L", ".R"}) {
    int t = sk.find(std::string("thigh") + s), k = sk.find(std::string("shin") + s), f = sk.find(std::string("foot") + s);
    if (t >= 0 && k >= 0 && f >= 0)
      return glm::distance(sk.bones[size_t(t)].head, sk.bones[size_t(k)].head) + glm::distance(sk.bones[size_t(k)].head, sk.bones[size_t(f)].head);
  }
  return 0.0f;
}

void applyLife(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, double fps,
               const mat4& world, const LifeParams& life, Pose& pose) {
  if (!life.enabled || pose.local.size() != sk.bones.size()) return;
  const double t = frame / std::max(1.0, fps);
  const float ph = hash01(life.seed, 1) * 6.283f, ph2 = hash01(life.seed, 2) * 6.283f, ph3 = hash01(life.seed, 3) * 6.283f;
  const float breathT = 3.4f + 0.6f * hash01(life.seed, 4), swayT = 6.5f + 2.0f * hash01(life.seed, 5);
  const float b = life.breathing * float(std::sin(kTwoPi * t / breathT + ph));
  const float w = life.sway * float(std::sin(kTwoPi * t / swayT + ph2));
  const int hips = sk.find("hips"), spine = sk.find("spine"), chest = sk.find("chest"), neck = sk.find("neck"),
            head = sk.find("head");
  // Head following the gaze, with lag: aim at the look target averaged over the last ~2 lag periods.
  if (const Track* lt = clip.find(prefix + "lookAt"); lt && !lt->keys.empty() && head >= 0 && life.headFollow > 0) {
    float lag = life.headLagSec * float(fps);
    vec3 target(0);
    for (int i = 0; i < 6; ++i) target += lt->evaluate(frame - lag * (0.5 + 0.3 * i));
    target /= 6.0f;
    float wgt = clip.evaluate(prefix + "lookAt.weight", frame, vec3(1)).x * life.headFollow;
    if (neck >= 0) aimBone(sk, pose, world, neck, target, 0.35f * wgt, 35.0f);
    aimBone(sk, pose, world, head, target, 0.6f * wgt, 45.0f);
  }
  // Breathing: chest and spine expand (lean back slightly), shoulders rise a little; the neck compensates.
  rotateLocal(pose, chest, vec3(-1.1f * b, 0, 0));
  rotateLocal(pose, spine, vec3(-0.4f * b, 0, 0));
  rotateLocal(pose, neck, vec3(1.0f * b, 0, 0));
  rotateLocal(pose, sk.find("upperArm.L"), vec3(0, 0, 0.7f * b));
  rotateLocal(pose, sk.find("upperArm.R"), vec3(0, 0, -0.7f * b));
  // Weight shift: the hips tilt and the spine counter-tilts; the thighs compensate so the feet stay put.
  rotateLocal(pose, hips, vec3(0, 0, 1.3f * w));
  rotateLocal(pose, spine, vec3(0, 0, -0.9f * w));
  rotateLocal(pose, chest, vec3(0, 0, -0.35f * w));
  rotateLocal(pose, sk.find("thigh.L"), vec3(0, 0, -1.3f * w));
  rotateLocal(pose, sk.find("thigh.R"), vec3(0, 0, -1.3f * w));
  // Small head drift (two slow incommensurate waves).
  float hd = life.headDrift;
  rotateLocal(pose, head, vec3(0.8f * hd * float(std::sin(kTwoPi * t / 7.3 + ph3)), 1.4f * hd * float(std::sin(kTwoPi * t / 11.1 + ph)),
                               0.6f * hd * float(std::sin(kTwoPi * t / 9.7 + ph2))));
  // Automatic blinks: the upper lids close over whatever the lid pose is.
  float bl = blinkAmount(t, life.blinkInterval, life.seed, life.blinkClose, life.blinkHold, life.blinkOpen);
  if (bl > 0 && life.blinkLids)
    for (const char* name : {"lid.L", "lid.R"}) {
      int lid = sk.find(name);
      if (lid >= 0) pose.local[size_t(lid)] = glm::slerp(pose.local[size_t(lid)], eulerDegreesToQuat(vec3(86, 0, 0)), bl);
    }
}

namespace {
struct FingerChain {
  int a = -1, b = -1;
};
struct HandBones {
  int hand = -1;
  FingerChain thumb, fingers[4];  // fingers[3] is the index finger (next to the thumb)
  static bool ok(const FingerChain& f) { return f.a >= 0 && f.b >= 0; }
  bool valid() const {  // a hand bone and at least two complete digits
    int n = ok(thumb) ? 1 : 0;
    for (auto& f : fingers) n += ok(f) ? 1 : 0;
    return hand >= 0 && n >= 2;
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
// Curl rotations from the hand frame. Engine convention (zero HandFrame): fingers hang along -y with the palm facing
// the body (-x for the left hand), so they curl about -z (left) / +z (right); the thumb folds about a tilted axis
// across the palm. A general frame (finger direction d, palm normal n) gives curl axis d x n, spread axis e
// (= -n left, n right) and thumb axis normalize(0.35 e + curl axis), which reduce exactly to the convention.
struct HandAxes {
  vec3 curl, spread, thumb;
};
HandAxes handAxes(const Skeleton& sk, char side) {
  const HandFrame& f = side == 'L' ? sk.handL : sk.handR;
  vec3 d = glm::length(f.fingerDir) > 1e-6f ? glm::normalize(f.fingerDir) : vec3(0, -1, 0);
  vec3 n = glm::length(f.palmNormal) > 1e-6f ? f.palmNormal : vec3(side == 'L' ? -1.0f : 1.0f, 0, 0);
  n = glm::normalize(n - d * glm::dot(n, d));
  vec3 c = glm::cross(d, n), e = side == 'L' ? -n : n;
  return {c, e, glm::normalize(0.35f * e + c)};
}
quat fingerRot(const HandAxes& ax, float angleDeg, float spreadDeg) {
  return glm::angleAxis(glm::radians(angleDeg), ax.curl) * glm::angleAxis(glm::radians(spreadDeg), ax.spread);
}
quat thumbRot(const HandAxes& ax, float angleDeg) { return glm::angleAxis(glm::radians(angleDeg), ax.thumb); }
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
  const HandAxes ax = handAxes(sk, side);
  const float kA = 75.0f, kB = 95.0f;  // full-curl angles of the first and second segment
  auto fingerCurl = [&](int k) { return k == 3 && hp.index >= 0 ? hp.index : hp.curl; };
  for (int k = 0; k < 4; ++k) {
    if (!HandBones::ok(h.fingers[k])) continue;
    float c = std::clamp(fingerCurl(k), 0.0f, 1.0f), spread = hp.spread * 7.0f * (float(k) - 1.5f);
    setChain(pose, h.fingers[k], fingerRot(ax, c * kA, spread), fingerRot(ax, c * kB, 0));
  }
  float tc = std::clamp(hp.thumb, 0.0f, 1.0f);
  if (HandBones::ok(h.thumb)) setChain(pose, h.thumb, thumbRot(ax, tc * 55.0f), thumbRot(ax, tc * 45.0f));
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
    if (!HandBones::ok(h.fingers[k])) continue;
    float c0 = std::clamp(fingerCurl(k), 0.0f, 1.0f), spread = hp.spread * 7.0f * (float(k) - 1.5f);
    auto ra = [&](float c) { return fingerRot(ax, c * kA, spread); };
    auto rb = [&](float c) { return fingerRot(ax, c * kB, 0); };
    float c = glm::mix(c0, search(h.fingers[k], ra, rb, 0.0f), w);
    setChain(pose, h.fingers[k], ra(c), rb(c));
  }
  if (!HandBones::ok(h.thumb)) return;
  auto ta = [&](float c) { return thumbRot(ax, c * 55.0f); };
  auto tb = [&](float c) { return thumbRot(ax, c * 45.0f); };
  float t = glm::mix(tc, search(h.thumb, ta, tb, 0.0f), w);
  setChain(pose, h.thumb, ta(t), tb(t));
}

std::vector<vec3> fingertips(const Skeleton& sk, const Pose& pose, const mat4& world, char side) {
  HandBones h = findHand(sk, side);
  if (!h.valid()) return {};
  mat4 hg = boneGlobals(sk, pose, world)[size_t(h.hand)];
  std::vector<vec3> tips;  // thumb first, then fingers 0..3 (missing digits skipped)
  if (HandBones::ok(h.thumb)) tips.push_back(chainTip(sk, hg, h.hand, h.thumb, pose.local[size_t(h.thumb.a)], pose.local[size_t(h.thumb.b)]));
  for (auto& f : h.fingers)
    if (HandBones::ok(f)) tips.push_back(chainTip(sk, hg, h.hand, f, pose.local[size_t(f.a)], pose.local[size_t(f.b)]));
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
