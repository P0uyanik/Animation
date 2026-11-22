#include "anim/animation.h"

#include <format>
#include <span>

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
    const vec3 off = i < pose.offset.size() ? pose.offset[i] : vec3(0);
    if (b.parent < 0) global[i] = world * glm::translate(mat4(1), b.head + pose.rootOffset + off) * rot;
    else global[i] = global[size_t(b.parent)] * glm::translate(mat4(1), b.head - skeleton.bones[size_t(b.parent)].head + off) * rot;
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
  solveTwoBoneIK(sk, pose, world, end, target, weight, weight);
}

void solveTwoBoneIK(const Skeleton& sk, Pose& pose, const mat4& world, int end, vec3 target, float weight, float midWeight) {
  if (end < 0 || (weight <= 0 && midWeight <= 0)) return;
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
  pose.local[size_t(mid)] = glm::slerp(pose.local[size_t(mid)], bNew, std::clamp(midWeight, 0.0f, 1.0f));
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
// Leaves the central range untouched, then approaches the limit exponentially. The value and first derivative are
// continuous where the soft zone begins, and there is no hard plateau to pop against at the nominal limit.
float softLimit(float angleDeg, float negativeLimitDeg, float positiveLimitDeg) {
  const float limit = std::max(0.0f, angleDeg < 0 ? negativeLimitDeg : positiveLimitDeg);
  const float magnitude = std::abs(angleDeg);
  const float softness = std::min(5.0f, limit * 0.25f);
  const float onset = limit - softness;
  if (magnitude <= onset || softness <= 1e-6f) return std::copysign(std::min(magnitude, limit), angleDeg);
  const float limited = onset + softness * (1.0f - std::exp(-(magnitude - onset) / softness));
  return std::copysign(limited, angleDeg);
}

vec3 limitGazeDirection(vec3 headDirection, const GazeLimits& limits) {
  headDirection = glm::normalize(headDirection);
  const float yaw = glm::degrees(std::atan2(headDirection.x, headDirection.z));
  const float pitch = glm::degrees(std::atan2(headDirection.y, glm::length(vec2(headDirection.x, headDirection.z))));
  // Positive yaw is character-left (+X); positive pitch is up (+Y).
  const float y = glm::radians(softLimit(yaw, limits.maxRightDeg, limits.maxLeftDeg));
  const float p = glm::radians(softLimit(pitch, limits.maxDownDeg, limits.maxUpDeg));
  const float cp = std::cos(p);
  return vec3(std::sin(y) * cp, std::sin(p), std::cos(y) * cp);
}

void aimEye(const Skeleton& sk, Pose& pose, const std::vector<mat4>& globals, const mat4& world, int eye, int head,
            vec3 target, float weight, const GazeLimits& limits) {
  const vec3 pivot(globals[size_t(eye)][3]);
  vec3 worldDirection = target - pivot;
  if (glm::length2(worldDirection) < 1e-12f) return;
  const int parent = sk.bones[size_t(eye)].parent;
  const mat3 headRotation = head >= 0 ? mat3(globals[size_t(head)])
                                      : parent >= 0 ? mat3(globals[size_t(parent)]) : mat3(world);
  const vec3 limitedHeadDirection = limitGazeDirection(glm::transpose(headRotation) * glm::normalize(worldDirection), limits);
  const vec3 limitedWorldDirection = glm::normalize(headRotation * limitedHeadDirection);
  const mat3 parentRotation = parent >= 0 ? mat3(globals[size_t(parent)]) : mat3(world);
  const vec3 localDirection = glm::normalize(glm::transpose(parentRotation) * limitedWorldDirection);
  const vec3 z(0, 0, 1);
  const vec3 axis = glm::cross(z, localDirection);
  const float s = glm::length(axis);
  const quat q = s < 1e-7f ? quat(1, 0, 0, 0)
                           : glm::angleAxis(std::atan2(s, glm::dot(z, localDirection)), axis / s);
  pose.local[size_t(eye)] = glm::slerp(pose.local[size_t(eye)], q, std::clamp(weight, 0.0f, 1.0f));
}
}  // namespace

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

float lifeHash01(uint32_t a, uint32_t b) { return hash01(a, b); }

float breathSignal(double t, uint32_t seed) {
  const float ph = hash01(seed, 1) * 6.283f;
  const float breathT = 3.4f + 0.6f * hash01(seed, 4);
  return float(std::sin(kTwoPi * t / breathT + ph));
}

void applyLidBlink(const Skeleton& sk, Pose& pose, float amount) {
  if (amount <= 0 || pose.local.size() != sk.bones.size()) return;
  for (const char* name : {"lid.L", "lid.R"}) {
    int lid = sk.find(name);
    if (lid >= 0) pose.local[size_t(lid)] = glm::slerp(pose.local[size_t(lid)], eulerDegreesToQuat(vec3(86, 0, 0)), amount);
  }
}

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
  const float swayT = 6.5f + 2.0f * hash01(life.seed, 5);
  const float b = life.breathing * breathSignal(t, life.seed);
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
  if (life.blinkLids) applyLidBlink(sk, pose, bl);
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
  vec3 dir{0, -1, 0}, normal{1, 0, 0};  // finger direction and palm normal (rest frame, orthonormal)
};
HandAxes handAxes(const Skeleton& sk, char side) {
  const HandFrame& f = side == 'L' ? sk.handL : sk.handR;
  vec3 d = glm::length(f.fingerDir) > 1e-6f ? glm::normalize(f.fingerDir) : vec3(0, -1, 0);
  vec3 n = glm::length(f.palmNormal) > 1e-6f ? f.palmNormal : vec3(side == 'L' ? -1.0f : 1.0f, 0, 0);
  n = glm::normalize(n - d * glm::dot(n, d));
  vec3 c = glm::cross(d, n), e = side == 'L' ? -n : n;
  return {c, e, glm::normalize(0.35f * e + c), d, n};
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
float tipRadius(const Skeleton& sk, const HandBones& h) {
  std::vector<vec3> roots;
  for (const auto& f : h.fingers)
    if (HandBones::ok(f)) roots.push_back(sk.bones[size_t(f.a)].head);
  if (roots.size() < 2) return 0;
  float sum = 0;
  for (size_t i = 1; i < roots.size(); ++i) sum += glm::distance(roots[i - 1], roots[i]);
  return 0.5f * sum / float(roots.size() - 1);
}

// The thumb's opposition axis (the finger direction) and abduction axis (the palm normal), signed for this hand:
// opposition takes the thumb tip in front of the palm, positive abduction towards the fingers.
struct ThumbAxes {
  vec3 opp, abd;
};
ThumbAxes thumbAxes(const Skeleton& sk, const HandBones& h, const HandAxes& ax) {
  ThumbAxes t{ax.dir, ax.normal};
  if (!HandBones::ok(h.thumb)) return t;
  const vec3 u = sk.bones[size_t(h.thumb.b)].head - sk.bones[size_t(h.thumb.a)].head;
  if (glm::dot(glm::cross(ax.dir, u), ax.normal) < 0) t.opp = -t.opp;
  vec3 m(0);
  int n = 0;
  for (const auto& f : h.fingers)
    if (HandBones::ok(f)) m += sk.bones[size_t(f.a)].head, ++n;
  if (n > 0 && glm::dot(glm::cross(ax.normal, u), m / float(n) - sk.bones[size_t(h.thumb.a)].head) < 0) t.abd = -t.abd;
  return t;
}
constexpr float kLimitEps = 0.05f;  // degrees: inside a range by this much counts as inside (float noise of the angles)
// An angle (degrees, any multiple of 360 away) clamped to [lo, hi]: the nearer limit when it is outside.
bool clampAngle(float& a, float lo, float hi) {
  while (a > 180.0f) a -= 360.0f;
  while (a < -180.0f) a += 360.0f;
  if (a >= lo - kLimitEps && a <= hi + kLimitEps) return false;
  const float toLo = a < lo ? lo - a : lo + 360.0f - a, toHi = a > hi ? a - hi : a + 360.0f - hi;
  a = toLo <= toHi ? lo : hi;
  return true;
}
float angleAbout(quat q, vec3 axis) {  // signed angle (degrees) of q's twist about a unit axis
  if (q.w < 0) q = -q;
  return glm::degrees(2.0f * std::atan2(glm::dot(vec3(q.x, q.y, q.z), axis), q.w));
}
// A finger joint as flex about the curl axis, then spread about the spread axis, then roll about the third axis of
// that frame (the finger direction): exactly fingerRot's (curl, spread) when there is no roll.
bool limitFingerJoint(quat& q, const HandAxes& ax, float flexLo, float flexHi, float spreadMax, float rollMax) {
  const vec3 z = glm::cross(ax.curl, ax.spread);
  const mat3 B(ax.curl, ax.spread, z);
  const mat3 M = glm::transpose(B) * glm::mat3_cast(q) * B;  // M[col][row]
  float spread = glm::degrees(std::asin(std::clamp(M[2][0], -1.0f, 1.0f)));
  float flex = glm::degrees(std::atan2(-M[2][1], M[2][2])), roll = glm::degrees(std::atan2(-M[1][0], M[0][0]));
  bool changed = clampAngle(flex, flexLo, flexHi);
  changed |= clampAngle(spread, -spreadMax, spreadMax);
  changed |= clampAngle(roll, -rollMax, rollMax);
  if (changed)
    q = glm::angleAxis(glm::radians(flex), ax.curl) * glm::angleAxis(glm::radians(spread), ax.spread) * glm::angleAxis(glm::radians(roll), z);
  return changed;
}
// The thumb base as abduction * opposition * flex (the per-finger thumb controls; the opposition axis is
// perpendicular to the other two, so every rotation has these three angles).
bool limitThumbBase(quat& q, const HandAxes& ax, const ThumbAxes& ta, float backMax, const HandLimits& lim) {
  const vec3 a = ax.thumb, o = ta.opp, n = ta.abd, oa = glm::cross(o, a);
  const float p = glm::dot(n, a), s = glm::dot(n, oa);
  if (std::abs(s) < 1e-4f) return false;  // degenerate hand frame: no decomposition, leave the joint alone
  const vec3 w = q * a;
  const float b0 = std::atan2(s, p);
  float opp = b0 - (s > 0 ? 1.0f : -1.0f) * std::acos(std::clamp(glm::dot(n, w), -1.0f, 1.0f));
  const vec3 v = std::cos(opp) * a + std::sin(opp) * oa;
  float abd = std::atan2(glm::dot(n, glm::cross(v, w)), glm::dot(v, w) - glm::dot(n, v) * glm::dot(n, w));
  float flex = angleAbout(glm::inverse(glm::angleAxis(abd, n) * glm::angleAxis(opp, o)) * q, a);
  opp = glm::degrees(opp), abd = glm::degrees(abd);
  bool changed = clampAngle(opp, 0.0f, lim.thumbOpposition);
  changed |= clampAngle(abd, -lim.thumbAbductionIn, lim.thumbAbductionOut);
  changed |= clampAngle(flex, -backMax, lim.thumbFlex);
  if (changed) q = glm::angleAxis(glm::radians(abd), n) * glm::angleAxis(glm::radians(opp), o) * glm::angleAxis(glm::radians(flex), a);
  return changed;
}
// A hinge about `axis`: flex in [0, flexMax], anything off the axis at most `play`.
bool limitHinge(quat& q, vec3 axis, float flexMax, float play) {
  float flex = angleAbout(q, axis);
  quat rest = glm::normalize(q * glm::angleAxis(glm::radians(-flex), axis));  // q = rest * hinge(flex)
  if (rest.w < 0) rest = -rest;
  const float off = glm::degrees(2.0f * std::acos(std::clamp(rest.w, -1.0f, 1.0f)));
  bool changed = clampAngle(flex, 0.0f, flexMax);
  if (off > play + kLimitEps) {
    const vec3 v(rest.x, rest.y, rest.z);
    rest = glm::length(v) > 1e-9f ? glm::angleAxis(glm::radians(play), glm::normalize(v)) : quat(1, 0, 0, 0);
    changed = true;
  }
  if (changed) q = rest * glm::angleAxis(glm::radians(flex), axis);
  return changed;
}
void limitHand(const Skeleton& sk, Pose& pose, char side, const HandBones& h, const HandLimits& lim) {
  const HandAxes ax = handAxes(sk, side);
  for (const FingerChain& f : h.fingers) {
    if (!HandBones::ok(f)) continue;
    limitFingerJoint(pose.local[size_t(f.a)], ax, -lim.knuckleBack, lim.knuckleFlex, lim.knuckleSpread, lim.play);
    limitFingerJoint(pose.local[size_t(f.b)], ax, 0.0f, lim.middleFlex, lim.play, lim.play);
    int c = -1, n = 0;
    for (size_t i = 0; i < sk.bones.size(); ++i)
      if (sk.bones[i].parent == f.b) c = int(i), ++n;
    if (n == 1) limitFingerJoint(pose.local[size_t(c)], ax, 0.0f, lim.endFlex, lim.play, lim.play);
  }
  if (!HandBones::ok(h.thumb)) return;
  limitThumbBase(pose.local[size_t(h.thumb.a)], ax, thumbAxes(sk, h, ax), lim.thumbBack, lim);
  limitHinge(pose.local[size_t(h.thumb.b)], ax.thumb, lim.thumbEndFlex, lim.play);
}

// The thumb of a grasp, solved inside its range (T-171 round 3, the wrap branch's thumb; T-190: the thumb of every
// per-finger grasp with HandPose::limits): the best pose over opposition 0..1 and abduction -20..30 deg. For each,
// the first segment starts where it is clear of the object (laid back by at most `backMax` of a curl on a wide
// object; never turned round), flexes onto the surface, then the second segment. Cost: tip off the surface, inside
// the object when laid back, outside the band, on the fingers' side of the object (opposed), and a small price on
// opposition, abduction and lying back, so equal contacts give the same, nearest pose on every frame. returns
// the grasp pose (the caller blends it from the thumb's base pose by the grasp weight).
struct ThumbControls {
  float opp = 0, abd = 0, a = 0, b = 0;  // opposition 0..1, abduction (deg), flexion of the two segments (curl units)
};
// The thumb's own controls (as the per-finger pose): opposition about the finger direction, abduction about the palm
// normal (positive towards the fingers), flexion of its two segments about the thumb axis.
std::pair<quat, quat> thumbControlRots(const HandAxes& ax, const ThumbAxes& ta, const ThumbControls& t) {
  return std::pair{glm::angleAxis(glm::radians(t.abd), ta.abd) * glm::angleAxis(glm::radians(t.opp * 60.0f), ta.opp) * thumbRot(ax, t.a * 55.0f),
                   thumbRot(ax, t.b * 45.0f)};
}
ThumbControls thumbBaseControls(const HandPose& hp) {  // the keyed thumb: its opposition and curl
  const float curl = std::clamp(hp.thumbPose ? hp.thumbPose->y : hp.thumb, 0.0f, 1.0f);
  return ThumbControls{hp.thumbPose ? std::clamp(hp.thumbPose->x, 0.0f, 1.0f) : 0.0f, 0, curl, curl};
}
template <class Surf, class Height>
std::pair<quat, quat> rangeThumb(const Skeleton& sk, const HandBones& h, const HandAxes& ax, const HandPose& hp, const mat4& handGlobal,
                                 vec3 centre, float scale, const Surf& surf, const Height& height, bool band, float lo, float hi,
                                 float edge, float skinT, float sideSign, vec3 split, float backMax, bool strictBack) {
  const ThumbAxes ta = thumbAxes(sk, h, ax);
  using Thumb = ThumbControls;
  auto thumbRots = [&](const Thumb& t) { return thumbControlRots(ax, ta, t); };
  struct Chain {
    vec3 p[3];  // root, second joint, tip centre
  };
  const vec3 handHead = sk.bones[size_t(h.hand)].head;
  auto thumbChain = [&](const Thumb& t) {
    const auto r = thumbRots(t);
    const vec3 ha = sk.bones[size_t(h.thumb.a)].head, hb = sk.bones[size_t(h.thumb.b)].head;
    const mat4 ga = handGlobal * glm::translate(mat4(1), ha - handHead) * glm::mat4_cast(r.first);
    const mat4 gb = ga * glm::translate(mat4(1), hb - ha) * glm::mat4_cast(r.second);
    Chain ch;
    ch.p[0] = vec3(ga[3]), ch.p[1] = vec3(gb[3]), ch.p[2] = vec3(gb * vec4(hb - ha, 1));
    return ch;
  };
  auto gapFrom = [&](const Chain& ch, int from, float skin) {
    float g = 1e9f;
    for (int i = from; i < 2; ++i) g = std::min({g, surf(0.5f * (ch.p[i] + ch.p[i + 1])), surf(ch.p[i + 1])});
    return g - skin;
  };
  auto firstContact = [](auto g, float lo, float hi) {  // smallest x in [lo, hi] with g(x) <= 0; hi if never
    if (g(lo) <= 0) return lo;
    if (g(hi) > 0) return hi;
    for (int it = 0; it < 16; ++it) {
      const float mid = 0.5f * (lo + hi);
      (g(mid) <= 0 ? hi : lo) = mid;
    }
    return hi;
  };
  Thumb best = thumbBaseControls(hp);
  const float thumbOpp = best.opp;
  float bestCost = 1e9f;
  const bool tucked = hp.thumbMode == HandPose::Thumb::Tucked;
  for (int io = 0; io <= (tucked ? 0 : 4); ++io)
    for (int ia = 0; ia <= (tucked ? 0 : 5); ++ia) {
      Thumb t{tucked ? thumbOpp : 0.25f * float(io), tucked ? 0.0f : -20.0f + 10.0f * float(ia), 0, 0};
      auto ga = [&](float x) {
        t.a = x;
        return gapFrom(thumbChain(t), 0, skinT);
      };
      float back = 0;
      while (ga(back) <= 0 && back > -backMax) back -= 0.05f;
      if (strictBack) back = std::max(back, -backMax);  // T-190: the last step stops at the limit
      const float open = ga(back);
      t.a = back;
      if (open > 0) {
        t.a = firstContact(ga, back, tucked ? 0.6f : 1.2f);
        t.b = firstContact([&](float x) { t.b = x; return gapFrom(thumbChain(t), 1, skinT); }, 0.0f, 1.25f);
      }
      const Chain ch = thumbChain(t);
      const float tipGap = surf(ch.p[2]) - skinT;
      float cost = 4.0f * std::max(0.0f, tipGap) + 8.0f * std::max(0.0f, -open);  // off the surface; inside it when laid back
      if (band) cost += 4.0f * std::max({0.0f, lo + 0.5f * edge - height(ch.p[2]), height(ch.p[2]) - (hi - 0.5f * edge)});
      if (hp.thumbMode == HandPose::Thumb::Opposed) cost += 0.15f * sideSign * glm::dot(ch.p[2] - centre, split);
      cost += 0.002f * scale * (std::abs(t.abd) / 30.0f + t.opp) + 0.01f * scale * std::max(0.0f, -t.a);
      if (cost < bestCost) bestCost = cost, best = t;
    }
  return thumbRots(best);
}

// T-171 round 3 wrap (HandPose::wrap, opt-in): the grasp of a hand whose fingers have to lie round the object. Each
// finger is a chain of two or three segments (f<k>a, f<k>b and the rig's own distal bone when f<k>b has exactly one
// child) with one skin radius; from the open finger all joints flex together (an arched finger) until a part of it
// touches, then the joints beyond the touching segment go on until they touch. Joints only flex (the first may
// extend up to 15 deg to rest on a surface it already touches). With a band the spread is searched so the contact
// stays inside it. The thumb takes the best pose of its anatomical range (opposition 0..1, abduction -20..30 deg,
// flexion, laid back into the palm's plane where the object needs the room): tip on the surface, inside the band, as
// far round the object from the fingers as it gets. Every digit is blended from its base pose by its grasp weight;
// the distal bone only moves with that weight.
void applyHandWrap(const Skeleton& sk, Pose& pose, const mat4& world, char side, const HandBones& h, const HandPose& hp) {
  const HandAxes ax = handAxes(sk, side);
  constexpr float kA = 75.0f, kB = 95.0f;                        // base curl angles (as the other searches)
  constexpr float kMaxA = 90.0f, kMaxB = 100.0f, kMaxC = 80.0f;  // joint limits of the wrap (degrees)
  struct Joints {
    float a = 0, b = 0, c = 0, spread = 0;  // degrees
  };
  auto distalOf = [&](const FingerChain& f) {
    int c = -1, n = 0;
    for (size_t i = 0; i < sk.bones.size(); ++i)
      if (sk.bones[i].parent == f.b) c = int(i), ++n;
    return n == 1 ? c : -1;
  };
  auto baseOf = [&](int k) {
    float c = hp.curl;
    if (k == 3 && hp.index >= 0) c = hp.index;
    float sp = hp.spread;
    if (hp.finger[size_t(k)]) c = hp.finger[size_t(k)]->x, sp = hp.finger[size_t(k)]->y;
    c = std::clamp(c, 0.0f, 1.0f);
    return Joints{c * kA, c * kB, 0, sp * 7.0f * (float(k) - 1.5f)};
  };
  auto weightOf = [&](int k) {
    const auto& w = hp.digitWeight[size_t(k)];
    return std::clamp(w ? *w : hp.graspWeight, 0.0f, 1.0f);
  };
  const mat4 handGlobal = boneGlobals(sk, pose, world)[size_t(h.hand)];
  const vec3 handHead = sk.bones[size_t(h.hand)].head;
  const vec3 centre = vec3(handGlobal * vec4(hp.graspCentre, 1));
  const float scale = glm::length(vec3(handGlobal[0]));
  const float R = hp.graspRadius * scale;
  const float tipR = std::max(tipRadius(sk, h), 0.001f);
  const float skinF = (hp.wrapSkin > 0 ? hp.wrapSkin : tipR) * scale, skinT = (hp.wrapThumbSkin > 0 ? hp.wrapThumbSkin : tipR) * scale;
  const bool face = glm::length(hp.graspFace) > 1e-6f;
  const vec3 faceN = face ? glm::normalize(vec3(handGlobal * vec4(hp.graspFace, 0))) : vec3(0);
  const vec3 axis = glm::length(hp.graspAxis) > 1e-6f ? glm::normalize(vec3(handGlobal * vec4(hp.graspAxis, 0))) : vec3(0);
  const bool cyl = !face && glm::length(axis) > 0;
  auto surf = [&](vec3 p) {  // signed distance to the object's surface (negative inside)
    vec3 q = p - centre;
    if (face) return std::abs(glm::dot(q, faceN)) - R;
    if (cyl) q -= axis * glm::dot(q, axis);
    return glm::length(q) - R;
  };
  auto height = [&](vec3 p) { return glm::dot(p - centre, axis); };
  auto firstContact = [](auto g, float lo, float hi) {  // smallest x in [lo, hi] with g(x) <= 0; hi if never
    if (g(lo) <= 0) return lo;
    if (g(hi) > 0) return hi;
    for (int it = 0; it < 16; ++it) {
      const float mid = 0.5f * (lo + hi);
      (g(mid) <= 0 ? hi : lo) = mid;
    }
    return hi;
  };
  // Joint positions of a chain: root, second joint, third joint (= tip centre without a distal bone), tip centre (one
  // more length of the last segment beyond the last joint).
  struct Chain {
    vec3 p[4];
    int segments = 2;
  };
  auto chainOf = [&](const FingerChain& f, int c, quat ra, quat rb, quat rc) {
    const vec3 ha = sk.bones[size_t(f.a)].head, hb = sk.bones[size_t(f.b)].head;
    const mat4 ga = handGlobal * glm::translate(mat4(1), ha - handHead) * glm::mat4_cast(ra);
    const mat4 gb = ga * glm::translate(mat4(1), hb - ha) * glm::mat4_cast(rb);
    Chain ch;
    ch.p[0] = vec3(ga[3]), ch.p[1] = vec3(gb[3]);
    if (c >= 0) {
      const vec3 hc = sk.bones[size_t(c)].head;
      const mat4 gc = gb * glm::translate(mat4(1), hc - hb) * glm::mat4_cast(rc);
      ch.p[2] = vec3(gc[3]), ch.p[3] = vec3(gc * vec4(hc - hb, 1)), ch.segments = 3;
    } else {
      ch.p[2] = ch.p[3] = vec3(gb * vec4(hb - ha, 1));
    }
    return ch;
  };
  // Skin clearance of the chain from segment `from` on (segment middles and ends; the root pivot is the palm's).
  auto gapFrom = [&](const Chain& ch, int from, float skin) {
    float g = 1e9f;
    for (int i = from; i < ch.segments; ++i) g = std::min({g, surf(0.5f * (ch.p[i] + ch.p[i + 1])), surf(ch.p[i + 1])});
    return g - skin;
  };
  auto fingerChain = [&](const FingerChain& f, int c, const Joints& j) {
    return chainOf(f, c, fingerRot(ax, j.a, j.spread), fingerRot(ax, j.b, 0), fingerRot(ax, j.c, 0));
  };
  // Closes one finger from open. All joints flex together in the ratio of a natural curl (an arched finger) until
  // any part touches; when it was the first segment that touched, the joints beyond it go on together until one of
  // their segments touches. A finger that curls up without reaching the surface (a short finger on a thick palm)
  // tries again with its outer joints flexing half, a quarter and not at all: the most arched finger that touches.
  auto wrapFinger = [&](const FingerChain& f, int c, float spread) {
    Joints j, nearest;
    float nearestGap = 1e9f;
    const int segments = c >= 0 ? 3 : 2;
    for (float outer : {1.0f, 0.5f, 0.25f, 0.0f}) {
      j = Joints{};
      j.spread = spread;
      auto pose = [&](int from, float x) {  // joints `from`.. at curl x (0..1 of their limits), earlier ones kept
        if (from <= 0) j.a = x * kMaxA;
        if (from <= 1) j.b = (from == 0 ? outer : 1.0f) * x * kMaxB;
        if (from <= 2) j.c = (from == 0 ? outer : 1.0f) * x * kMaxC;
      };
      auto all = [&](float x) {
        pose(0, x);
        return gapFrom(fingerChain(f, c, j), 0, skinF);
      };
      if (all(0) <= 0) {  // touching when open: the first joint alone may extend a little
        float lo = 0;
        auto ga = [&](float x) {
          j.a = x;
          return gapFrom(fingerChain(f, c, j), 0, skinF);
        };
        while (ga(lo) <= 0 && lo > -15.0f) lo -= 2.5f;
        j.a = lo;
        return j;
      }
      float x = firstContact(all, 0.0f, 1.0f);
      const float g = all(x);
      if (g > 0.0005f * scale) {  // never touched: remember the nearest approach of this ratio
        for (int i = 0; i <= 20; ++i)
          if (const float gi = all(0.05f * float(i)); gi < nearestGap) nearestGap = gi, nearest = j;
        continue;
      }
      for (int from = 1; from < segments; ++from) {
        if (gapFrom(fingerChain(f, c, j), from, skinF) <= 0.0002f * scale) break;  // a segment beyond already rests on it
        const float x0 = from == 1 ? j.b / kMaxB : j.c / kMaxC;
        const float y = firstContact([&](float t) { pose(from, t); return gapFrom(fingerChain(f, c, j), from, skinF); }, x0, 1.0f);
        pose(from, y);
      }
      return j;
    }
    return nearest;
  };
  std::array<Joints, 4> base{}, fin{};
  std::array<int, 4> distal{-1, -1, -1, -1};
  std::array<bool, 4> searched{};
  std::vector<int> ks;
  for (int k = 0; k < 4; ++k) {
    base[size_t(k)] = fin[size_t(k)] = baseOf(k);
    if (!HandBones::ok(h.fingers[k])) continue;
    distal[size_t(k)] = distalOf(h.fingers[k]);
    if (weightOf(k) <= 0 || (hp.finger[size_t(k)] && hp.finger[size_t(k)]->z >= 0.5f)) continue;  // free: keeps its curl
    fin[size_t(k)] = wrapFinger(h.fingers[k], distal[size_t(k)], base[size_t(k)].spread);
    searched[size_t(k)] = true;
    ks.push_back(k);
  }
  const bool band = hp.band && cyl;
  const vec2 widen = hp.bandFit ? hp.bandWiden : vec2(0);
  const float lo = (hp.bandLo - widen.x) * scale, hi = (hp.bandHi + widen.y) * scale;
  // As much of the skin inside the band as side-by-side fingers allow (at least 1 mm of it).
  const float edge = std::clamp(0.5f * ((hi - lo) - float(std::max<size_t>(ks.size(), 1) - 1) * 2.0f * skinF), 0.001f * scale, skinF);
  if (band) {
    for (int k : ks) {
      const FingerChain& f = h.fingers[k];
      const int c = distal[size_t(k)];
      auto tipHeight = [&](float sp) { return height(fingerChain(f, c, wrapFinger(f, c, sp)).p[3]); };
      const float sp0 = base[size_t(k)].spread, h0 = tipHeight(sp0), target = std::clamp(h0, lo + edge, std::max(lo + edge, hi - edge));
      if (std::abs(h0 - target) < 0.0002f * scale) continue;
      // The spread that moves the tip to the band's edge, within 25 deg either way (the nearer end if none does).
      float best = sp0, bestE = std::abs(h0 - target);
      for (float sgn : {1.0f, -1.0f}) {
        float a = sp0, b = sp0 + sgn * 25.0f;
        const float ea = h0 - target, eb = tipHeight(b) - target;
        if (std::abs(eb) < bestE) bestE = std::abs(eb), best = b;
        if ((ea > 0) == (eb > 0)) continue;
        for (int it = 0; it < 14; ++it) {
          const float m = 0.5f * (a + b);
          ((tipHeight(m) - target > 0) == (ea > 0) ? a : b) = m;
        }
        best = b, bestE = 0;
        break;
      }
      fin[size_t(k)] = wrapFinger(f, c, best);
    }
  }
  for (int k = 0; k < 4; ++k) {
    if (!HandBones::ok(h.fingers[k])) continue;
    const float w = searched[size_t(k)] ? weightOf(k) : 0.0f;
    const Joints &b0 = base[size_t(k)], &g = fin[size_t(k)];
    setChain(pose, h.fingers[k], fingerRot(ax, glm::mix(b0.a, g.a, w), glm::mix(b0.spread, g.spread, w)), fingerRot(ax, glm::mix(b0.b, g.b, w), 0));
    if (w > 0 && distal[size_t(k)] >= 0) pose.local[size_t(distal[size_t(k)])] = fingerRot(ax, w * g.c, 0);
  }
  if (!HandBones::ok(h.thumb)) return;
  const auto b0 = thumbControlRots(ax, thumbAxes(sk, h, ax), thumbBaseControls(hp));
  const float wt = weightOf(4);
  if (wt <= 0) {
    setChain(pose, h.thumb, b0.first, b0.second);
    return;
  }
  const vec3 palmN = glm::normalize(vec3(handGlobal * vec4(ax.normal, 0)));
  vec3 split = cyl ? glm::cross(axis, palmN) : glm::cross(palmN, glm::normalize(vec3(handGlobal * vec4(ax.curl, 0))));
  split = glm::length(split) > 1e-6f ? glm::normalize(split) : vec3(1, 0, 0);
  float fingerSide = 0;
  for (int k = 0; k < 4; ++k)
    if (HandBones::ok(h.fingers[k])) fingerSide += glm::dot(fingerChain(h.fingers[k], distal[size_t(k)], fin[size_t(k)]).p[3] - centre, split);
  const float sideSign = fingerSide >= 0 ? 1.0f : -1.0f;
  // The thumb lies back at most kThumbBack of a curl (about 33 deg = HandLimits::thumbBack).
  constexpr float kThumbBack = 0.6f;
  const float backMax = hp.limits ? std::min(kThumbBack, HandLimits{}.thumbBack / 55.0f) : kThumbBack;
  const auto g1 = rangeThumb(sk, h, ax, hp, handGlobal, centre, scale, surf, height, band, lo, hi, edge, skinT, sideSign, split,
                             backMax, hp.limits);
  setChain(pose, h.thumb, glm::slerp(b0.first, g1.first, wt), glm::slerp(b0.second, g1.second, wt));
}

// T-051 per-finger pose and grasp. Each digit is a two-segment chain driven by (curl of segment a, curl of segment b,
// spread); the thumb by (curl, opposition, abduction). With a grasp, every digit is searched on its own against the
// object's surface (cylinder, sphere or box-face slab): the curl closes until a finger point (knuckle, segment
// middles, tip; skin radius from the skeleton) touches; when the knuckle stops it first the distal segment closes on
// until the tip touches. With a band, the spread (thumb: abduction) is searched so the tip lies inside the band.
void applyHandPosePerFinger(const Skeleton& sk, Pose& pose, const mat4& world, char side, const HandBones& h,
                            const HandPose& hp) {
  const HandAxes ax = handAxes(sk, side);
  const float kA = 75.0f, kB = 95.0f;  // full-curl angles of the first and second segment (as the single search)
  struct Digit {
    float a = 0, b = 0, spread = 0;  // finger: curls of the two segments, spread (deg); thumb: curl, curl, abduction
    float opp = 0;                   // thumb only: opposition 0..1
  };
  auto fingerBase = [&](int k) {
    float c = hp.curl;
    if (k == 3 && hp.index >= 0) c = hp.index;
    float sp = hp.spread;
    if (hp.finger[size_t(k)]) c = hp.finger[size_t(k)]->x, sp = hp.finger[size_t(k)]->y;
    c = std::clamp(c, 0.0f, 1.0f);
    return Digit{c, c, sp * 7.0f * (float(k) - 1.5f), 0};
  };
  Digit thumbBase;
  thumbBase.a = thumbBase.b = std::clamp(hp.thumbPose ? hp.thumbPose->y : hp.thumb, 0.0f, 1.0f);
  thumbBase.opp = hp.thumbPose ? std::clamp(hp.thumbPose->x, 0.0f, 1.0f) : 0.0f;
  // Opposition turns the thumb about the finger direction so its tip moves in front of the palm; abduction turns it
  // about the palm normal (positive towards the fingers).
  vec3 oppAxis = ax.dir, abdAxis = ax.normal;
  if (HandBones::ok(h.thumb)) {
    const vec3 u = sk.bones[size_t(h.thumb.b)].head - sk.bones[size_t(h.thumb.a)].head;
    if (glm::dot(glm::cross(ax.dir, u), ax.normal) < 0) oppAxis = -oppAxis;
    vec3 m(0);
    int n = 0;
    for (const auto& f : h.fingers)
      if (HandBones::ok(f)) m += sk.bones[size_t(f.a)].head, ++n;
    if (n > 0 && glm::dot(glm::cross(ax.normal, u), m / float(n) - sk.bones[size_t(h.thumb.a)].head) < 0) abdAxis = -abdAxis;
  }
  const HandLimits lim;  // T-190 (hp.limits): the searches below only ever see poses inside the joint ranges
  auto fingerRots = [&](const Digit& d) {
    if (hp.limits)
      return std::pair{fingerRot(ax, std::clamp(d.a * kA, -lim.knuckleBack, lim.knuckleFlex), std::clamp(d.spread, -lim.knuckleSpread, lim.knuckleSpread)),
                       fingerRot(ax, std::clamp(d.b * kB, 0.0f, lim.middleFlex), 0)};
    return std::pair{fingerRot(ax, d.a * kA, d.spread), fingerRot(ax, d.b * kB, 0)};
  };
  auto thumbRots = [&](const Digit& d) {
    const quat ra = glm::angleAxis(glm::radians(d.spread), abdAxis) * glm::angleAxis(glm::radians(d.opp * 60.0f), oppAxis) *
                    thumbRot(ax, d.a * 55.0f);
    return std::pair{ra, thumbRot(ax, d.b * 45.0f)};
  };
  auto set = [&](const FingerChain& f, std::pair<quat, quat> r) { setChain(pose, f, r.first, r.second); };
  std::array<Digit, 4> base{};
  for (int k = 0; k < 4; ++k) base[size_t(k)] = fingerBase(k);
  auto weightOf = [&](int k) {
    const auto& w = hp.digitWeight[size_t(k)];
    return std::clamp(w ? *w : hp.graspWeight, 0.0f, 1.0f);
  };
  const bool grasping = hp.grasp && [&] {
    for (int k = 0; k < 5; ++k)
      if (weightOf(k) > 0) return true;
    return false;
  }();
  if (!grasping) {
    for (int k = 0; k < 4; ++k)
      if (HandBones::ok(h.fingers[k])) set(h.fingers[k], fingerRots(base[size_t(k)]));
    if (HandBones::ok(h.thumb)) set(h.thumb, thumbRots(thumbBase));
    return;
  }
  if (hp.wrap) {  // T-171 (opt-in): joint-by-joint wrap, anatomical thumb
    applyHandWrap(sk, pose, world, side, h, hp);
    return;
  }
  // Pose the base first: the hand bone's global frame does not depend on the digits.
  const mat4 handGlobal = boneGlobals(sk, pose, world)[size_t(h.hand)];
  const vec3 centre = vec3(handGlobal * vec4(hp.graspCentre, 1));
  const float scale = glm::length(vec3(handGlobal[0]));
  const float R = hp.graspRadius * scale;
  const float tipR = std::max(tipRadius(sk, h), 0.001f) * scale;
  const bool face = glm::length(hp.graspFace) > 1e-6f;
  const vec3 faceN = face ? glm::normalize(vec3(handGlobal * vec4(hp.graspFace, 0))) : vec3(0);
  const vec3 axis = glm::length(hp.graspAxis) > 1e-6f ? glm::normalize(vec3(handGlobal * vec4(hp.graspAxis, 0))) : vec3(0);
  const bool cyl = !face && glm::length(axis) > 0;
  auto surf = [&](vec3 p) {  // signed distance to the object's surface (negative inside)
    vec3 q = p - centre;
    if (face) return std::abs(glm::dot(q, faceN)) - R;
    if (cyl) q -= axis * glm::dot(q, axis);
    return glm::length(q) - R;
  };
  struct Points {
    vec3 knuckle, tip, mid1, mid2;
  };
  auto points = [&](const FingerChain& f, std::pair<quat, quat> r) {
    const vec3 ha = sk.bones[size_t(f.a)].head, hb = sk.bones[size_t(f.b)].head;
    const mat4 ga = handGlobal * glm::translate(mat4(1), ha - sk.bones[size_t(h.hand)].head) * glm::mat4_cast(r.first);
    const mat4 gb = ga * glm::translate(mat4(1), hb - ha) * glm::mat4_cast(r.second);
    Points p;
    p.knuckle = vec3(gb[3]);
    p.tip = vec3(gb * vec4(hb - ha, 1));
    p.mid1 = 0.5f * (vec3(ga[3]) + p.knuckle);
    p.mid2 = 0.5f * (p.knuckle + p.tip);
    return p;
  };
  auto gapAll = [&](const Points& p) {
    return std::min({surf(p.knuckle), surf(p.tip), surf(p.mid1), surf(p.mid2)}) - tipR;
  };
  // Smallest t in [lo, hi] with g(t) <= 0 (bisection; g decreasing towards contact); hi if never.
  auto firstContact = [](auto g, float lo, float hi) {
    if (g(lo) <= 0) return lo;
    if (g(hi) > 0) return hi;
    for (int it = 0; it < 16; ++it) {
      const float mid = 0.5f * (lo + hi);
      (g(mid) <= 0 ? hi : lo) = mid;
    }
    return hi;
  };
  // Close one digit on the surface from its base: both segments together until any point touches, then (the knuckle
  // or a segment touched first) the distal segment alone until the tip touches.
  auto close = [&](const FingerChain& f, Digit d, auto rots) {
    Digit t = d;
    auto g = [&](float x) {
      t.a = t.b = x;
      return gapAll(points(f, rots(t)));
    };
    // Already touching open (a flat face on the palm): extend a little (at most 0.3 of a full curl) until clear.
    float lo0 = 0;
    while (g(lo0) <= 0 && lo0 > -0.3f) lo0 -= 0.05f;
    const float c = firstContact(g, lo0, 1.0f);
    t.a = t.b = c;
    auto tipGap = [&](const Digit& x) { return surf(points(f, rots(x)).tip) - tipR; };
    if (tipGap(t) > 0.0005f * scale) {
      const float cb = firstContact([&](float x) { t.b = x; return tipGap(t); }, c, 1.25f);
      t.b = cb;
    }
    if (c >= 1.0f && tipGap(t) > 0.0005f * scale) {
      // Never touched closing both segments together (a short finger): the proximal curl that lets the distal
      // segment reach the surface, least curl first; else the closest approach.
      Digit best = t;
      float bestGap = tipGap(t);
      for (int i = 0; i <= 20; ++i) {
        Digit x = d;
        x.a = 0.05f * float(i);
        x.b = x.a;
        if (gapAll(points(f, rots(x))) <= 0) break;  // the proximal segment would enter the object
        for (int j = 0; j <= 25; ++j) {
          x.b = x.a + (1.25f - x.a) * float(j) / 25.0f;
          const Points p = points(f, rots(x));
          const float g = surf(p.tip) - tipR;
          if (std::min({surf(p.knuckle), surf(p.mid1), surf(p.mid2)}) - tipR < -0.0002f * scale) break;
          if (g < bestGap) bestGap = g, best = x;
          if (g <= 0) break;
        }
        if (bestGap <= 0.0005f * scale) break;
      }
      t = best;
    }
    return t;
  };
  // Band: the tip's distance from the centre along the axis, shifted into [lo, hi] by the spread (abduction).
  const bool band = hp.band && cyl;
  const vec2 widen = hp.bandFit ? hp.bandWiden : vec2(0);  // T-157 (opt-in): the band grows at its ends
  const float lo = (hp.bandLo - widen.x) * scale, hi = (hp.bandHi + widen.y) * scale;
  auto height = [&](vec3 p) { return glm::dot(p - centre, axis); };
  bool wideBracket = false;  // T-138 band fit, second pass
  auto intoBand = [&](const FingerChain& f, Digit d, auto rots, float target) {
    auto solved = [&](float s) {
      Digit t = d;
      t.spread = d.spread + s;
      return close(f, t, rots);
    };
    auto err = [&](float s) {
      const Digit t = solved(s);
      return height(points(f, rots(t)).tip) - target;
    };
    // Grow a bracket outwards from no extra spread (the nearest solution, never a far one), then bisect.
    const float e0 = err(0);
    if (std::abs(e0) < 0.0002f * scale) return solved(0);
    float bestS = 0, bestE = std::abs(e0);
    auto touches = [&](float sp) { return surf(points(f, rots(solved(sp))).tip) - tipR <= 0.001f * scale; };
    // T-138 band fit: the bracket may grow to 60 deg (a wide hand's outer fingers need more than 30 to reach).
    static constexpr std::array<float, 7> kFitSteps{2.0f, 4.0f, 8.0f, 16.0f, 30.0f, 45.0f, 60.0f};
    for (float step : std::span<const float>(kFitSteps).first(wideBracket ? 7 : 5)) {
      for (float sgn : {1.0f, -1.0f}) {
        const float sb = sgn * step;
        if (!touches(sb)) continue;  // a spread that misses the object is no solution
        const float eb = err(sb);
        if (std::abs(eb) < bestE) bestE = std::abs(eb), bestS = sb;
        if ((eb > 0) == (e0 > 0)) continue;
        float a = sgn * (step == 2.0f ? 0.0f : 0.5f * step), b = sb, ea = err(a);
        if ((ea > 0) != (e0 > 0)) a = 0, ea = e0;
        for (int it = 0; it < 14; ++it) {
          const float m = 0.5f * (a + b), em = err(m);
          if ((em > 0) == (ea > 0)) a = m, ea = em;
          else b = m;
        }
        return solved(a);
      }
    }
    return solved(bestS);
  };
  std::array<Digit, 4> fin = base;
  std::array<bool, 4> searched{}, off{};
  float edge = tipR;  // how far the contact centres stay inside the band's ends (T-051: the skin radius)
  for (int k = 0; k < 4; ++k) {
    if (!HandBones::ok(h.fingers[k]) || weightOf(k) <= 0) continue;
    if (hp.finger[size_t(k)] && hp.finger[size_t(k)]->z >= 0.5f) continue;  // free: keeps its curl
    Digit start = base[size_t(k)];
    start.a = start.b = 0;
    fin[size_t(k)] = close(h.fingers[k], start, fingerRots);
    if (hp.band && cyl && hp.bandFit && (hp.bandOff >> k & 1)) {
      // T-157 off-band finger: from the touching pose, open both curls together (fraction x of the touching curls)
      // until every finger point's skin is at least half a skin radius off the surface.
      const Digit touch = fin[size_t(k)];
      auto clear = [&](float x) {
        Digit t = touch;
        t.a *= x, t.b *= x;
        return gapAll(points(h.fingers[k], fingerRots(t))) - 0.5f * tipR;
      };
      float a = 0, b = 1;
      if (clear(1) < 0 && clear(0) >= 0) {
        for (int it = 0; it < 16; ++it) {
          const float m = 0.5f * (a + b);
          (clear(m) >= 0 ? a : b) = m;
        }
      } else if (clear(1) >= 0) {
        a = 1;
      }
      fin[size_t(k)].a = touch.a * a, fin[size_t(k)].b = touch.b * a;
      off[size_t(k)] = true;
      continue;
    }
    searched[size_t(k)] = true;
  }
  // Target heights: the natural contact heights moved as a whole into [lo + edge, hi - edge]; if the fingers span more
  // than that, spaced evenly across it in their order. T-051: edge = the skin radius (the finger skin inside the band).
  auto bandStep = [&] {
    std::vector<int> ks;
    std::vector<float> hs;
    for (int k = 0; k < 4; ++k)
      if (searched[size_t(k)]) ks.push_back(k), hs.push_back(height(points(h.fingers[k], fingerRots(fin[size_t(k)])).tip));
    if (wideBracket)  // T-138 fit: as much of the skin inside the band as side-by-side fingers allow, at least 1 mm
      edge = std::clamp(0.5f * ((hi - lo) - float(std::max<size_t>(ks.size(), 1) - 1) * 2.0f * tipR), 0.001f * scale, tipR);
    const float bl = lo + edge, bh = std::max(lo + edge, hi - edge);
    if (!ks.empty()) {
      const float mn = *std::min_element(hs.begin(), hs.end()), mx = *std::max_element(hs.begin(), hs.end());
      std::vector<float> target(hs.size());
      if (mx - mn <= bh - bl) {
        const float shift = mn < bl ? bl - mn : mx > bh ? bh - mx : 0.0f;
        for (size_t i = 0; i < hs.size(); ++i) target[i] = hs[i] + shift;
      } else {
        for (size_t i = 0; i < hs.size(); ++i) target[i] = bl + (hs[i] - mn) / (mx - mn) * (bh - bl);
      }
      for (size_t i = 0; i < ks.size(); ++i) {
        if (std::abs(target[i] - hs[i]) < 0.0002f * scale) continue;
        Digit start = base[size_t(ks[i])];
        start.a = start.b = 0;
        fin[size_t(ks[i])] = intoBand(h.fingers[ks[i]], start, fingerRots, target[i]);
      }
    }
  };
  if (band) {
    const std::array<Digit, 4> touching = fin;
    bandStep();
    // T-138 band fit (opt-in): a finger touches the cylinder at its centre's height, so it is the contact centres that
    // must lie in the band. When the T-051 step leaves one outside [lo, hi] (a hand too wide for the band), the step
    // runs again from the touching pose with a smaller edge and a spread bracket of up to 60 deg.
    if (hp.bandFit) {
      bool outside = false;
      for (int k = 0; k < 4; ++k)
        if (searched[size_t(k)]) {
          const float t = height(points(h.fingers[k], fingerRots(fin[size_t(k)])).tip);
          outside = outside || t < lo || t > hi;
        }
      if (outside) {
        fin = touching;
        wideBracket = true;
        bandStep();
      }
    }
  }
  for (int k = 0; k < 4; ++k) {
    if (!HandBones::ok(h.fingers[k])) continue;
    const float w = searched[size_t(k)] || off[size_t(k)] ? weightOf(k) : 0.0f;
    const Digit &b0 = base[size_t(k)], &g = fin[size_t(k)];
    set(h.fingers[k], fingerRots(Digit{glm::mix(b0.a, g.a, w), glm::mix(b0.b, g.b, w), glm::mix(b0.spread, g.spread, w), 0}));
  }
  if (!HandBones::ok(h.thumb)) return;
  const float wt = weightOf(4);
  if (wt <= 0) {
    set(h.thumb, thumbRots(thumbBase));
    return;
  }
  if (hp.limits) {  // T-190: the thumb is solved inside its range (the wrap branch's search), never aimed round the object
    const vec3 pn = glm::normalize(vec3(handGlobal * vec4(ax.normal, 0)));
    vec3 sp = cyl ? glm::cross(axis, pn) : glm::cross(pn, glm::normalize(vec3(handGlobal * vec4(ax.curl, 0))));
    sp = glm::length(sp) > 1e-6f ? glm::normalize(sp) : vec3(1, 0, 0);
    float fs = 0;
    for (int k = 0; k < 4; ++k)
      if (HandBones::ok(h.fingers[k])) fs += glm::dot(points(h.fingers[k], fingerRots(fin[size_t(k)])).tip - centre, sp);
    const auto b0 = thumbRots(thumbBase);
    const auto g1 = rangeThumb(sk, h, ax, hp, handGlobal, centre, scale, surf, height, band, lo, hi, edge, tipR, fs >= 0 ? 1.0f : -1.0f, sp,
                               (face ? lim.thumbBackFace : lim.thumbBack) / 55.0f, true);
    setChain(pose, h.thumb, glm::slerp(b0.first, g1.first, wt), glm::slerp(b0.second, g1.second, wt));
    return;
  }
  // Thumb grasp: the thumb is aimed at a direction g(phi) in the plane of the grasp axis and the finger direction
  // (phi = 0: along the axis, on the thumb's side; phi > 0: turned away from the fingers, round the object's other
  // side), then curled onto the surface about the axis across g and the palm normal (its tip moves towards the
  // object). Opposed: the smallest phi that puts the tip on the other half of the object from the fingertips (split
  // by the plane through the axis and the palm normal), on the surface and inside the band; along: the phi nearest 0
  // that is on the surface and inside the band; tucked: aimed along the fingers, curl at most 0.6.
  const vec3 ha = sk.bones[size_t(h.thumb.a)].head, u0 = sk.bones[size_t(h.thumb.b)].head - ha;
  const mat3 toRest = glm::transpose(mat3(handGlobal)) / (scale * scale);  // world direction -> hand rest frame
  vec3 up = cyl ? glm::normalize(toRest * axis) : ax.curl;  // the grasp axis in the rest frame (box / sphere: across)
  if (glm::dot(up, u0) < 0) up = -up;
  vec3 away = -ax.dir;  // away from the fingers, kept perpendicular to `up`
  away = away - up * glm::dot(away, up);
  away = glm::length(away) > 1e-6f ? glm::normalize(away) : glm::normalize(glm::cross(up, ax.normal));
  struct ThumbG {
    float phi = 0, c = 0, cb = 0;
  };
  auto aimAt = [&](float phi) {
    const vec3 g = hp.thumbMode == HandPose::Thumb::Tucked ? ax.dir
                                                            : std::cos(glm::radians(phi)) * up + std::sin(glm::radians(phi)) * away;
    const quat q = glm::rotation(glm::normalize(u0), glm::normalize(g));
    vec3 kk = glm::cross(glm::normalize(g), ax.normal);
    kk = glm::length(kk) > 1e-6f ? glm::normalize(kk) : ax.curl;
    return std::pair{q, kk};
  };
  auto graspRots = [&](const ThumbG& t) {
    const auto [q, kk] = aimAt(t.phi);
    return std::pair{glm::angleAxis(glm::radians(t.c * 80.0f), kk) * q,
                     glm::angleAxis(glm::radians(t.cb * 70.0f), glm::inverse(q) * kk)};
  };
  // Curl from the most extended position that is clear of the object to the first contact, then the distal segment
  // on until the tip touches.
  auto closeThumb = [&](float phi, float cMax) {
    ThumbG t{phi, 0, 0};
    auto g = [&](float c) {
      t.c = t.cb = c;
      return gapAll(points(h.thumb, graspRots(t)));
    };
    float lo0 = 0;
    while (g(lo0) <= 0 && lo0 > -0.6f) lo0 -= 0.1f;
    t.c = t.cb = firstContact(g, lo0, cMax);
    if (surf(points(h.thumb, graspRots(t)).tip) - tipR > 0.0005f * scale)
      t.cb = firstContact([&](float x) { t.cb = x; return surf(points(h.thumb, graspRots(t)).tip) - tipR; }, t.c, 1.25f);
    return t;
  };
  const vec3 palmN = glm::normalize(vec3(handGlobal * vec4(ax.normal, 0)));
  vec3 split = cyl ? glm::cross(axis, palmN) : glm::cross(palmN, glm::normalize(vec3(handGlobal * vec4(ax.curl, 0))));
  split = glm::length(split) > 1e-6f ? glm::normalize(split) : vec3(1, 0, 0);
  float fingerSide = 0;
  for (int k = 0; k < 4; ++k)
    if (HandBones::ok(h.fingers[k])) fingerSide += glm::dot(points(h.fingers[k], fingerRots(fin[size_t(k)])).tip - centre, split);
  const float sideSign = fingerSide >= 0 ? 1.0f : -1.0f;
  const float bl = lo + edge, bh = std::max(lo + edge, hi - edge);
  auto score = [&](const ThumbG& t) {  // 0 = an acceptable thumb; else how far from one (metres)
    const vec3 tip = points(h.thumb, graspRots(t)).tip;
    float e = std::abs(surf(tip) - tipR);
    if (band) e += std::max({0.0f, bl - height(tip), height(tip) - bh});
    if (hp.thumbMode == HandPose::Thumb::Opposed) e += std::max(0.0f, sideSign * glm::dot(tip - centre, split) + tipR);
    return e;
  };
  ThumbG gt;
  if (hp.thumbMode == HandPose::Thumb::Tucked) {
    gt = closeThumb(0, 0.6f);
  } else {
    float best = 1e9f;
    for (int i = 0; i <= 72; ++i) {  // opposed: 0 .. 180 deg; along: 0, +-2.5, +-5 .. +-90 deg
      const float phi = hp.thumbMode == HandPose::Thumb::Along ? 2.5f * float((i + 1) / 2) * (i % 2 ? 1.0f : -1.0f)
                                                                : 2.5f * float(i);
      if (std::abs(phi) > 180.0f) break;
      const ThumbG t = closeThumb(phi, 1.0f);
      const float e = score(t);
      if (e < 0.0005f * scale) {
        gt = t;
        break;
      }
      if (e < best) best = e, gt = t;
    }
  }
  const auto b0 = thumbRots(thumbBase), g1 = graspRots(gt);
  setChain(pose, h.thumb, glm::slerp(b0.first, g1.first, wt), glm::slerp(b0.second, g1.second, wt));
}
}  // namespace

bool HandPose::perFinger() const {
  if (wrap) return true;  // T-171 (opt-in)
  if (band || glm::length(graspFace) > 0 || thumbPose) return true;
  for (const auto& f : finger)
    if (f) return true;
  for (const auto& w : digitWeight)
    if (w) return true;
  return false;
}

float fingertipRadius(const Skeleton& sk, char side) {
  HandBones h = findHand(sk, side);
  return h.valid() ? tipRadius(sk, h) : 0.0f;
}

void applyHandLimits(const Skeleton& sk, Pose& pose, char side, const HandLimits& limits) {
  const HandBones h = findHand(sk, side);
  if (h.valid()) limitHand(sk, pose, side, h, limits);
}

std::pair<quat, quat> thumbJointRotations(const Skeleton& sk, char side, float opp, float abd, float flex, float endFlex) {
  const HandBones h = findHand(sk, side);
  if (!h.valid() || !HandBones::ok(h.thumb)) return {quat(1, 0, 0, 0), quat(1, 0, 0, 0)};
  const HandAxes ax = handAxes(sk, side);
  const ThumbAxes ta = thumbAxes(sk, h, ax);
  return {glm::angleAxis(glm::radians(abd), ta.abd) * glm::angleAxis(glm::radians(opp), ta.opp) * thumbRot(ax, flex), thumbRot(ax, endFlex)};
}

HandLimits handLimitsFor(const HandPose& hp) {
  HandLimits lim;
  if (hp.grasp && !hp.wrap && glm::length(hp.graspFace) > 1e-6f) lim.thumbBack = lim.thumbBackFace;  // flat hand on a box face
  return lim;
}

static void poseHand(const Skeleton& sk, Pose& pose, const mat4& world, char side, const HandPose& hp);
void applyHandPose(const Skeleton& sk, Pose& pose, const mat4& world, char side, const HandPose& hp) {
  poseHand(sk, pose, world, side, hp);
  if (hp.limits) applyHandLimits(sk, pose, side, handLimitsFor(hp));  // T-190: whatever posed the hand, every joint ends inside its range
}

static void poseHand(const Skeleton& sk, Pose& pose, const mat4& world, char side, const HandPose& hp) {
  HandBones h = findHand(sk, side);
  if (!h.valid()) return;
  if (hp.perFinger()) {
    applyHandPosePerFinger(sk, pose, world, side, h, hp);
    return;
  }
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

namespace {
// Neck assist (T-046): the eyes keep a comfortable range and the neck takes the rest. Measured from the eyes' midpoint
// in the head frame: whatever the target lies beyond the soft limit's onset (yaw and pitch separately) turns the neck
// about the head's own axes, capped by the assist limits. Two passes absorb the small shift of the eye pivots. The
// result depends only on where the target is relative to the body, so a posture layer (an emotion bowing the head)
// no longer changes where the eyes end up looking (test_emotions AC5 look_keeps_gaze).
void assistGazeWithNeck(const Skeleton& sk, const Clip& clip, const std::string& prefix, const mat4& world, Pose& pose,
                        int head, vec3 target, float weight, const GazeLimits& limits) {
  const int neck = sk.find("neck");
  if (neck < 0 || head < 0 || weight <= 0 || (limits.assistYawDeg <= 0 && limits.assistPitchDeg <= 0)) return;
  {
    auto it = clip.tracks.find(prefix + "neck.rot");
    if (it != clip.tracks.end() && !it->second.keys.empty()) return;  // a hand-keyed neck wins
  }
  std::vector<int> eyes;
  for (size_t i = 0; i < sk.bones.size(); ++i)
    if (sk.bones[i].name.rfind("eye.", 0) == 0) eyes.push_back(int(i));
  if (eyes.empty()) return;
  auto onset = [](float limit) { return limit - std::min(5.0f, limit * 0.25f) - 0.25f; };
  auto handKeyed = [&](int bone) {
    auto it = clip.tracks.find(prefix + sk.bones[size_t(bone)].name + ".rot");
    return it != clip.tracks.end() && !it->second.keys.empty();
  };
  const int chest = sk.find("chest") >= 0 ? sk.find("chest") : sk.find("spine");
  const bool chestFree = chest >= 0 && chest != neck && !handKeyed(chest) && limits.assistBodyYawDeg > 0;
  float usedYaw = 0, usedPitch = 0, usedBody = 0;
  const float w = std::clamp(weight, 0.0f, 1.0f);
  auto rotateBone = [&](const std::vector<mat4>& g, int bone, const quat& r) {
    const int parent = sk.bones[size_t(bone)].parent;
    const quat parentRot = glm::normalize(glm::quat_cast(parent >= 0 ? mat3(g[size_t(parent)]) : mat3(world)));
    pose.local[size_t(bone)] = glm::normalize(glm::inverse(parentRot) * r * parentRot * pose.local[size_t(bone)]);
  };
  for (int pass = 0; pass < 4; ++pass) {
    const std::vector<mat4> g = boneGlobals(sk, pose, world);
    vec3 pivot(0);
    for (int e : eyes) pivot += vec3(g[size_t(e)][3]);
    pivot /= float(eyes.size());
    const vec3 toTarget = target - pivot;
    if (glm::length2(toTarget) < 1e-10f) return;
    const mat3 headRot(g[size_t(head)]);
    const vec3 d = glm::normalize(glm::transpose(headRot) * glm::normalize(toTarget));
    const float yaw = glm::degrees(std::atan2(d.x, d.z));
    const float pitch = glm::degrees(std::atan2(d.y, glm::length(vec2(d.x, d.z))));
    const float yawOn = onset(yaw >= 0 ? limits.maxLeftDeg : limits.maxRightDeg);
    const float pitchOn = onset(pitch >= 0 ? limits.maxUpDeg : limits.maxDownDeg);
    const float exYaw = std::copysign(std::max(0.0f, std::abs(yaw) - yawOn), yaw) * w;
    float exPitch = std::copysign(std::max(0.0f, std::abs(pitch) - pitchOn), pitch) * w;
    float neckYaw = std::clamp(usedYaw + exYaw, -limits.assistYawDeg, limits.assistYawDeg) - usedYaw;
    exPitch = std::clamp(usedPitch + exPitch, -limits.assistPitchDeg, limits.assistPitchDeg) - usedPitch;
    float bodyYaw = 0;
    if (chest >= 0 && chestFree)
      bodyYaw = std::clamp(usedBody + (exYaw - neckYaw), -limits.assistBodyYawDeg, limits.assistBodyYawDeg) - usedBody;
    if (std::abs(neckYaw) < 1e-4f && std::abs(exPitch) < 1e-4f && std::abs(bodyYaw) < 1e-4f) return;
    usedYaw += neckYaw;
    usedPitch += exPitch;
    usedBody += bodyYaw;
    std::vector<mat4> gn = g;
    if (std::abs(bodyYaw) >= 1e-4f) {  // the chest twists about its own up axis; it carries the neck and head
      rotateBone(g, chest, glm::angleAxis(glm::radians(bodyYaw), glm::normalize(mat3(g[size_t(chest)]) * vec3(0, 1, 0))));
      gn = boneGlobals(sk, pose, world);
    }
    // World rotation about the head's up axis (yaw toward +X) and right axis (positive pitch looks up = -X rotation).
    const mat3 hr(gn[size_t(head)]);
    const vec3 up = glm::normalize(hr * vec3(0, 1, 0)), right = glm::normalize(hr * vec3(1, 0, 0));
    rotateBone(gn, neck, glm::angleAxis(glm::radians(neckYaw), up) * glm::angleAxis(glm::radians(-exPitch), right));
  }
}
}  // namespace

namespace {
// T-051 optional per-finger tracks of one hand ("<prefix>hand.<s>"): band, box face, finger / thumb overrides and the
// stagger. Nothing is set when none of them has keys, so the hand pose stays the single search (byte-identical).
void perFingerTracks(const Clip& clip, const std::string& base, double frame, HandPose& hp) {
  auto keyed = [&](const std::string& name) {
    const Track* t = clip.find(name);
    return t && !t->keys.empty() ? t : nullptr;
  };
  const Track* band = keyed(base + ".band");
  if (band) {
    const vec3 b = band->evaluate(frame);
    hp.band = true;
    hp.bandLo = std::min(b.x, b.y);
    hp.bandHi = std::max(b.x, b.y);
    const int m = int(std::lround(b.z));
    hp.thumbMode = m == 1 ? HandPose::Thumb::Along : m == 2 ? HandPose::Thumb::Tucked : HandPose::Thumb::Opposed;
  }
  if (const Track* t = keyed(base + ".bandFit"); t && band) hp.bandFit = t->evaluate(frame).x >= 0.5f;  // T-138
  if (const Track* t = keyed(base + ".bandFitOptions"); t && hp.bandFit) {  // T-157 (opt-in): (widen lo, off bits, widen hi)
    const vec3 v = t->evaluate(frame);
    hp.bandWiden = glm::max(vec2(v.x, v.z), vec2(0));
    hp.bandOff = std::clamp(int(std::lround(v.y)), 0, 15);
  }
  if (const Track* t = keyed(base + ".graspFace")) hp.graspFace = t->evaluate(frame);
  if (const Track* t = keyed(base + ".wrap")) {  // T-171 (opt-in): (on, finger skin radius, thumb skin radius)
    const vec3 v = t->evaluate(frame);
    hp.wrap = v.x >= 0.5f;
    hp.wrapSkin = std::max(v.y, 0.0f), hp.wrapThumbSkin = std::max(v.z, 0.0f);
  }
  std::array<const Track*, 4> fk{};
  for (int k = 0; k < 4; ++k) fk[size_t(k)] = keyed(std::format("{}.f{}", base, k));
  const Track* thumb = keyed(base + ".thumb");
  // Stagger (frames per finger): with a band 1 unless a stagger track says otherwise; without one only on request.
  const Track* st = keyed(base + ".stagger");
  const float step = st ? std::max(0.0f, st->evaluate(frame).x) : band ? 1.0f : 0.0f;
  if (step <= 0) {
    for (int k = 0; k < 4; ++k)
      if (fk[size_t(k)]) hp.finger[size_t(k)] = fk[size_t(k)]->evaluate(frame);
    if (thumb) hp.thumbPose = vec2(thumb->evaluate(frame));
    return;
  }
  // Closing (grasp weight, else curl, not falling): index first, little last; opening: little first, index last.
  // Each finger reads its curl and grasp weight `lag` frames late; the thumb goes with the index.
  const vec3 rest(0.25f, 0.15f, 0.0f);
  auto signal = [&](double f) {
    return hp.grasp ? clip.evaluate(base + ".grasp.weight", f, vec3(1)).x : clip.evaluate(base, f, rest).x;
  };
  // Direction over the whole stagger window (flat over it: every lag reads the same value either way).
  const bool closing = signal(frame) >= signal(frame - 3.0 * double(step) - 1.0);
  auto lagOf = [&](int k) {  // k = 0..3 finger (3 = index), 4 = thumb
    const int order = k == 4 ? 0 : 3 - k;  // index 0 .. little 3
    return double(step) * double(closing ? order : 3 - order);
  };
  for (int k = 0; k < 4; ++k) {
    const double f = frame - lagOf(k);
    vec3 v;
    if (fk[size_t(k)]) {
      v = fk[size_t(k)]->evaluate(f);
    } else {
      const vec3 hv = clip.evaluate(base, f, rest);
      float c = hv.x;
      if (k == 3)
        if (const Track* ti = keyed(base + ".index")) c = ti->evaluate(f).x;
      v = vec3(c, hv.z, 0);
    }
    hp.finger[size_t(k)] = v;
    if (hp.grasp) hp.digitWeight[size_t(k)] = clip.evaluate(base + ".grasp.weight", f, vec3(1)).x;
  }
  const double ft = frame - lagOf(4);
  hp.thumbPose = thumb ? vec2(thumb->evaluate(ft)) : vec2(0.0f, clip.evaluate(base, ft, rest).y);
  if (hp.grasp) hp.digitWeight[4] = clip.evaluate(base + ".grasp.weight", ft, vec3(1)).x;
}
}  // namespace

void applyConstraints(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                      Pose& pose, const GazeLimits& gaze, double fps) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    std::string name = prefix + "ik." + sk.bones[i].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    float w = clip.evaluate(name + ".weight", frame, vec3(1)).x;
    if (const Track* lag = clip.find(name + ".lag"); lag && !lag->keys.empty()) {
      const float wm = clip.evaluate(name + ".weight", frame - double(lag->evaluate(frame).x), vec3(1)).x;
      solveTwoBoneIK(sk, pose, world, int(i), t->evaluate(frame), w, wm);
    } else {
      solveTwoBoneIK(sk, pose, world, int(i), t->evaluate(frame), w);
    }
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
    perFingerTracks(clip, base, frame, hp);
    if (const Track* t = clip.find(base + ".limits"); t && !t->keys.empty()) hp.limits = t->evaluate(frame).x >= 0.5f;  // T-190
    applyHandPose(sk, pose, world, side, hp);
  }
  if (const Track* t = clip.find(prefix + "lookAt"); t && !t->keys.empty()) {
    vec3 target = t->evaluate(frame);
    float w = clip.evaluate(prefix + "lookAt.weight", frame, vec3(1)).x;
    const int head = sk.find("head");
    // The assist aims at the target as it was a moment ago (averaged like the life layer's head follow): eyes lead.
    vec3 lagged = target;
    if (const double lag = gaze.assistLagSec * std::max(1.0, fps); lag > 0) {
      lagged = vec3(0);
      for (int i = 0; i < 6; ++i) lagged += t->evaluate(frame - lag * (0.5 + 0.3 * i));
      lagged /= 6.0f;
    }
    assistGazeWithNeck(sk, clip, prefix, world, pose, head, lagged, w, gaze);
    const std::vector<mat4> globals = boneGlobals(sk, pose, world);
    for (size_t i = 0; i < sk.bones.size(); ++i)
      if (sk.bones[i].name.rfind("eye.", 0) == 0) aimEye(sk, pose, globals, world, int(i), head, target, w, gaze);
  }
}

}  // namespace plush
