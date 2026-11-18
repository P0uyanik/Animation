#include "anim/body_mechanics.h"

#include "anim/personality.h"

#include <algorithm>
#include <cmath>
#include <numbers>

namespace plush {

namespace {
constexpr float kPiF = std::numbers::pi_v<float>;

float clamp01(float x) { return std::clamp(x, 0.0f, 1.0f); }
float smoother(float x) {
  x = clamp01(x);
  return x * x * x * (x * (x * 6 - 15) + 10);
}
uint32_t mix32(uint32_t x) {
  x ^= x >> 16;
  x *= 0x7feb352dU;
  x ^= x >> 15;
  x *= 0x846ca68bU;
  x ^= x >> 16;
  return x;
}
float hashUnit(uint32_t a, uint32_t b) { return float(mix32(a * 0x9E3779B9U + mix32(b + 0x632BE5ABU)) >> 8) / float(1 << 24); }

vec3 pos(const mat4& m) { return vec3(m[3]); }
quat rotOf(const mat4& m) { return glm::normalize(glm::quat_cast(mat3(m))); }
quat eul(float x, float y, float z) { return eulerDegreesToQuat(vec3(x, y, z)); }
void post(Pose& pose, int b, const quat& q) {
  if (b >= 0) pose.local[size_t(b)] = glm::normalize(pose.local[size_t(b)] * q);
}
bool descendant(const Skeleton& sk, int b, int ancestor) {
  if (b < 0 || ancestor < 0) return false;
  for (int x = sk.bones[size_t(b)].parent; x >= 0; x = sk.bones[size_t(x)].parent)
    if (x == ancestor) return true;
  return false;
}
}  // namespace

Result<BodyMechanicsRigProfile> bodyMechanicsRigProfileFromJson(const Json& j) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.body_mechanics_rig")
    return fail("not a plush.body_mechanics_rig file");
  if (j.value("version", 0) != 1) return fail(std::format("body_mechanics_rig: unsupported version {}", j.value("version", 0)));
  BodyMechanicsRigProfile p;
  auto names = [&](const char* key, std::vector<std::string>& out) -> Result<void> {
    auto it = j.find(key);
    if (it == j.end()) return {};
    if (!it->is_array()) return fail(std::format("body_mechanics_rig: '{}' must be a list of names", key));
    out.clear();
    for (const auto& x : *it) {
      if (!x.is_string()) return fail(std::format("body_mechanics_rig: '{}' entries must be strings", key));
      out.push_back(x.get<std::string>());
    }
    return {};
  };
  if (auto r = names("clavicle", p.clavicle); !r) return std::unexpected(r.error());
  if (auto r = names("hip_helpers", p.hipHelpers); !r) return std::unexpected(r.error());
  if (auto it = j.find("limits"); it != j.end()) {
    if (!it->is_object()) return fail("body_mechanics_rig: 'limits' must be an object");
    p.limits = *it;
  }
  return p;
}

void applyBodyMechanicsLimits(BodyMechanicsParams& p, const Json& l) {
  if (!l.is_object()) return;
  p.shrugMaxDeg = readFloat(l, "shrug_max_deg", p.shrugMaxDeg);
  p.protractMaxDeg = readFloat(l, "protract_max_deg", p.protractMaxDeg);
  p.leanMaxDeg = readFloat(l, "lean_max_deg", p.leanMaxDeg);
  p.twistMaxDeg = readFloat(l, "twist_max_deg", p.twistMaxDeg);
  p.sideMaxDeg = readFloat(l, "side_max_deg", p.sideMaxDeg);
  p.pelvisShift = readFloat(l, "pelvis_shift", p.pelvisShift);
  p.pelvisRollDeg = readFloat(l, "pelvis_roll_deg", p.pelvisRollDeg);
  p.kneeSoften = readFloat(l, "knee_soften", p.kneeSoften);
}

// Personality (T-053): the shared reader (anim/personality.h) resolves the profile; this maps its tempo, energy and
// posture onto the layer. Missing parameters keep the shared defaults.
void applyPersonalityToBodyMechanics(BodyMechanicsParams& p, const PersonalityProfile& pr) {
  auto setIf = [](float& dst, const std::optional<float>& v) {
    if (v && std::isfinite(*v)) dst = *v;
  };
  // Frame values in profiles are at 24 fps; the layer keeps them at 24 fps too (converted where used).
  if (pr.settleFrames) p.settleFrames = pr.settleFrames->mid();
  setIf(p.overshoot, pr.overshoot);
  if (pr.anticipationFrames) p.lagFrames = std::clamp(pr.anticipationFrames->mid() * 0.35f, 1.0f, 4.0f);
  setIf(p.energy, pr.energyLevel);
  setIf(p.gesture, pr.gestureAmplitude);
  setIf(p.slouch, pr.slouch);
  setIf(p.headPitchDeg, pr.headPitchDeg);
  setIf(p.shouldersForward, pr.shouldersForward);
  setIf(p.weightShift, pr.weightShift);
  setIf(p.leanTowardTask, pr.leanTowardTask);
}

// JSON form (kept for callers that hold a parsed profile): read through the same reader; a section-only object
// (no "format") is accepted as a profile. An unreadable profile changes nothing.
void applyPersonalityToBodyMechanics(BodyMechanicsParams& p, const Json& j) {
  if (!j.is_object()) return;
  Json copy = j;
  if (!copy.contains("format")) copy["format"] = "plush.personality";
  if (!copy.contains("version")) copy["version"] = 0;
  if (auto pr = personalityFromJson(copy)) applyPersonalityToBodyMechanics(p, *pr);
}

void applyBodyMechanicsOverrides(BodyMechanicsParams& p, const Json& o) {
  if (!o.is_object()) return;
  p.enabled = readBool(o, "enabled", true);
  p.shoulder = readFloat(o, "shoulder", p.shoulder);
  p.torso = readFloat(o, "torso", p.torso);
  p.headStabilize = readFloat(o, "headStabilize", p.headStabilize);
  p.weightShift = readFloat(o, "weightShift", p.weightShift);
  p.energy = readFloat(o, "energy", p.energy);
  p.gesture = readFloat(o, "gesture", p.gesture);
  p.leanTowardTask = readFloat(o, "leanTowardTask", p.leanTowardTask);
  p.slouch = readFloat(o, "slouch", p.slouch);
  p.shouldersForward = readFloat(o, "shouldersForward", p.shouldersForward);
  p.headPitchDeg = readFloat(o, "headPitchDeg", p.headPitchDeg);
  p.lagFrames = readFloat(o, "lagFrames", p.lagFrames);
  p.settleFrames = readFloat(o, "settleFrames", p.settleFrames);
  p.overshoot = readFloat(o, "overshoot", p.overshoot);
  if (auto it = o.find("limits"); it != o.end()) applyBodyMechanicsLimits(p, *it);
}

BodyMechanicsRig bindBodyMechanics(const Skeleton& sk, const BodyMechanicsRigProfile& profile) {
  BodyMechanicsRig r;
  r.hips = sk.find("hips");
  r.spine = sk.find("spine");
  r.chest = sk.find("chest");
  r.neck = sk.find("neck");
  r.head = sk.find("head");
  const char* sfx[2] = {".L", ".R"};
  for (int s = 0; s < 2; ++s) {
    const std::string x = sfx[s];
    for (const auto& c : profile.clavicle)
      if (int b = sk.find(c + x); b >= 0) {
        r.clavicle[size_t(s)] = b;
        break;
      }
    r.upper[size_t(s)] = sk.find("upperArm" + x);
    r.fore[size_t(s)] = sk.find("forearm" + x);
    r.hand[size_t(s)] = sk.find("hand" + x);
    r.thigh[size_t(s)] = sk.find("thigh" + x);
    r.shin[size_t(s)] = sk.find("shin" + x);
    r.foot[size_t(s)] = sk.find("foot" + x);
    for (const auto& h : profile.hipHelpers)
      if (int b = sk.find(h + x); b >= 0) r.hipHelpers.push_back(b);
    // A clavicle must sit between the chest and the arm and must not be part of the arm chain.
    const int cl = r.clavicle[size_t(s)];
    if (cl >= 0 && (r.chest < 0 || cl == r.upper[size_t(s)] || descendant(sk, cl, r.upper[size_t(s)]))) r.clavicle[size_t(s)] = -1;
    if (r.upper[size_t(s)] >= 0 && r.fore[size_t(s)] >= 0 && r.hand[size_t(s)] >= 0) {
      const vec3 a = sk.bones[size_t(r.upper[size_t(s)])].head, b = sk.bones[size_t(r.fore[size_t(s)])].head,
                 c = sk.bones[size_t(r.hand[size_t(s)])].head;
      r.armLength[size_t(s)] = glm::distance(a, b) + glm::distance(b, c);
      const vec3 d = c - a;
      if (glm::length(d) > 1e-6f)
        r.restElevDeg[size_t(s)] = glm::degrees(std::acos(std::clamp(glm::dot(glm::normalize(d), vec3(0, -1, 0)), -1.0f, 1.0f)));
    }
  }
  r.legLength = legLength(sk);
  return r;
}

BodyDrivers operator+(const BodyDrivers& a, const BodyDrivers& b) {
  BodyDrivers o;
  for (size_t s = 0; s < 2; ++s) {
    o.elev[s] = a.elev[s] + b.elev[s];
    o.fwd[s] = a.fwd[s] + b.fwd[s];
    o.lat[s] = a.lat[s] + b.lat[s];
  }
  o.standing = a.standing + b.standing;
  o.walk = a.walk + b.walk;
  return o;
}
BodyDrivers operator*(const BodyDrivers& a, float k) {
  BodyDrivers o;
  for (size_t s = 0; s < 2; ++s) {
    o.elev[s] = a.elev[s] * k;
    o.fwd[s] = a.fwd[s] * k;
    o.lat[s] = a.lat[s] * k;
  }
  o.standing = a.standing * k;
  o.walk = a.walk * k;
  return o;
}

BodyDrivers measureBodyDrivers(const Skeleton& sk, const BodyMechanicsRig& rig, const Pose& pose, const std::array<vec4, 2>& ik) {
  BodyDrivers d;
  if (pose.local.size() != sk.bones.size()) return d;
  const std::vector<mat4> G = boneGlobals(sk, pose, mat4(1));
  for (int s = 0; s < 2; ++s) {
    if (!rig.arm(s)) continue;
    const size_t i = size_t(s);
    const float sigma = s == 0 ? 1.0f : -1.0f;  // +x is the character's left
    const vec3 sh = pos(G[size_t(rig.upper[i])]);
    vec3 dc = pos(G[size_t(rig.hand[i])]) - sh;
    float ext = glm::length(dc) / rig.armLength[i];
    vec3 dir = glm::length(dc) > 1e-6f ? glm::normalize(dc) : vec3(0, -1, 0);
    const float w = clamp01(ik[i].w);
    if (w > 0) {
      const vec3 dt = vec3(ik[i]) - sh;
      if (glm::length(dt) > 1e-6f) {
        const vec3 m = glm::mix(dir, glm::normalize(dt), w);
        if (glm::length(m) > 1e-6f) dir = glm::normalize(m);
        ext = glm::mix(ext, glm::length(dt) / rig.armLength[i], w);
      }
    }
    ext = clamp01(ext);
    const float elev = glm::degrees(std::acos(std::clamp(glm::dot(dir, vec3(0, -1, 0)), -1.0f, 1.0f)));
    d.elev[i] = std::max(0.0f, elev - rig.restElevDeg[i]);
    d.fwd[i] = clamp01((dir.z - 0.25f) / 0.75f) * clamp01((ext - 0.3f) / 0.6f);  // hanging arms are not a reach
    d.lat[i] = clamp01(sigma * dir.x) * clamp01(d.elev[i] / 60.0f) * clamp01((ext - 0.3f) / 0.6f);
  }
  // Standing: both thighs close to vertical (sitting / crouching turns the weight shift and leg IK off).
  float stand = 1;
  int legs = 0;
  for (int s = 0; s < 2; ++s) {
    if (!rig.leg(s)) continue;
    const vec3 t = pos(G[size_t(rig.shin[size_t(s)])]) - pos(G[size_t(rig.thigh[size_t(s)])]);
    if (glm::length(t) < 1e-6f) continue;
    const float a = glm::degrees(std::acos(std::clamp(glm::dot(glm::normalize(t), vec3(0, -1, 0)), -1.0f, 1.0f)));
    stand = std::min(stand, 1.0f - smoother((a - 25.0f) / 25.0f));
    ++legs;
  }
  d.standing = legs == 2 ? stand : 0.0f;
  return d;
}

std::vector<float> followKernel(float delay, float settle, float overshoot) {
  delay = std::max(0.0f, delay);
  settle = std::max(1.0f, settle);
  overshoot = std::clamp(overshoot, 0.0f, 0.5f);
  // Damping ratio from the overshoot of a step response; natural frequency from the 2 % settle time.
  const float lnOs = overshoot > 1e-4f ? std::log(overshoot) : 0.0f;
  const float zeta = overshoot > 1e-4f ? -lnOs / std::sqrt(kPiF * kPiF + lnOs * lnOs) : 1.0f;
  const float omega = (zeta < 1.0f ? 4.0f : 5.8f) / (zeta * settle);
  const int n = int(std::ceil(delay + 1.4f * settle)) + 2;
  std::vector<float> w(size_t(n), 0.0f);
  float sum = 0;
  for (int k = 0; k < n; ++k) {
    const float t = float(k) + 0.5f - delay;  // bin centre, time since the delayed impulse
    if (t <= 0) continue;
    float h;
    if (zeta < 1.0f) {
      const float wd = omega * std::sqrt(1 - zeta * zeta);
      h = std::exp(-zeta * omega * t) * std::sin(wd * t);
    } else {
      h = t * std::exp(-omega * t);
    }
    w[size_t(k)] = h;
    sum += h;
  }
  if (std::abs(sum) < 1e-9f) {
    w.assign(1, 1.0f);
    return w;
  }
  for (float& x : w) x /= sum;
  return w;
}

float idleWeightShift(double t, const BodyMechanicsParams& p) {
  if (p.weightShift <= 0) return 0;
  // Hold one leg for a while, then move the weight over (low energy = longer holds); per-hold amounts vary.
  const double period = 9.0 - 4.5 * double(clamp01(p.energy));
  const double u = t / period + double(hashUnit(p.seed, 101));
  const long long k = (long long)std::floor(u);
  const float frac = float(u - double(k));
  auto value = [&](long long i) {
    const float sgn = ((i % 2) + 2) % 2 == 0 ? 1.0f : -1.0f;
    return sgn * (0.65f + 0.35f * hashUnit(p.seed, uint32_t(i & 0xffffffff)));
  };
  const float transition = std::clamp(float(1.3 / period), 0.1f, 0.4f);
  return glm::mix(value(k - 1), value(k), smoother(frac / transition));
}

void applyBodyMechanics(const Skeleton& sk, const BodyMechanicsRig& rig, const BodyMechanicsParams& p,
                        const BodyMechanicsInput& in, Pose& pose) {
  if (!p.enabled || pose.local.size() != sk.bones.size()) return;
  const size_t n = sk.bones.size();
  if (pose.offset.size() != n) pose.offset.assign(n, vec3(0));
  const mat4 I(1);
  const std::vector<mat4> G0 = boneGlobals(sk, pose, I);  // feet stay where the pose before the layer put them

  // 1. Posture rest layer.
  if (p.slouch != 0) {
    post(pose, rig.spine, eul(5.0f * p.slouch, 0, 0));
    post(pose, rig.chest, eul(6.0f * p.slouch, 0, 0));
    post(pose, rig.neck, eul(-4.0f * p.slouch, 0, 0));
  }
  if (p.headPitchDeg != 0) {
    post(pose, rig.neck, eul(0.4f * p.headPitchDeg, 0, 0));
    post(pose, rig.head, eul(0.6f * p.headPitchDeg, 0, 0));
  }

  // 2. Torso follow (slow drivers): lean into forward reaches, twist toward the reaching arm, bend away from a
  // raised arm and into a sideways reach. The pelvis counter-rotates; the neck takes part of it back.
  const BodyDrivers& S = in.slow;
  const float g = std::max(0.0f, p.torso) * (0.5f + p.gesture);
  const float lean = p.leanMaxDeg * g * (0.5f + p.leanTowardTask) * std::max(S.fwd[0], S.fwd[1]);
  const float twist = p.twistMaxDeg * g * std::clamp(S.fwd[1] - S.fwd[0], -1.0f, 1.0f);
  const float raise = std::clamp(S.elev[0] / 120.0f, 0.0f, 1.0f) - std::clamp(S.elev[1] / 120.0f, 0.0f, 1.0f);
  const float side = p.sideMaxDeg * g * std::clamp(raise - (S.lat[0] - S.lat[1]), -1.0f, 1.0f);
  if (rig.spine >= 0 || rig.chest >= 0) {
    const float sSpine = rig.chest >= 0 ? 0.4f : 1.0f, sChest = rig.spine >= 0 ? 0.6f : 1.0f;
    post(pose, rig.hips, eul(0, -0.3f * twist, 0));
    post(pose, rig.spine, eul(sSpine * lean, sSpine * twist + 0.3f * twist, sSpine * side));
    post(pose, rig.chest, eul(sChest * lean, sChest * twist, sChest * side));
    if (rig.neck >= 0 && p.headStabilize > 0)
      post(pose, rig.neck, glm::slerp(quat(1, 0, 0, 0), glm::inverse(eul(lean, twist, side)), clamp01(p.headStabilize)));
  }

  // 3. Weight shift: idle alternation, toward a reaching arm while reaching; only while standing and not walking.
  // The weight follows the slower, non-overshooting response (whole-body mass, no wobble with a waving hand).
  const BodyDrivers& W = in.weight;
  const float stand = clamp01(W.standing) * (1.0f - clamp01(std::max(W.walk, S.walk)));
  const float rL = std::max(W.fwd[0], W.lat[0]), rR = std::max(W.fwd[1], W.lat[1]);
  const float reach = clamp01(std::max(rL, rR));
  const float reachBias = std::clamp((rL - rR) * 1.5f, -1.0f, 1.0f);
  const float shift = stand * glm::mix(in.idle * clamp01(p.weightShift), 0.7f * reachBias, reach);
  if (shift != 0 && rig.hips >= 0 && rig.legLength > 0) {
    pose.rootOffset.x += shift * p.pelvisShift * rig.legLength;
    pose.rootOffset.y -= p.kneeSoften * rig.legLength * std::abs(shift);
    const float roll = p.pelvisRollDeg * shift;  // + about z lifts the left hip: the free (right) hip drops
    post(pose, rig.hips, eul(0, 0, roll));
    post(pose, rig.spine, eul(0, 0, -0.7f * roll));
    post(pose, rig.chest, eul(0, 0, -0.3f * roll));
  }

  // 4. Clavicles (fast drivers): shrug with arm elevation, protraction with forward reach; posture bias.
  std::array<quat, 2> clav{quat(1, 0, 0, 0), quat(1, 0, 0, 0)};
  for (int s = 0; s < 2; ++s) {
    if (rig.clavicle[size_t(s)] < 0) continue;
    const float sigma = s == 0 ? 1.0f : -1.0f;
    const float shrug = p.shrugMaxDeg * std::max(0.0f, p.shoulder) * clamp01((in.fast.elev[size_t(s)] - 25.0f) / 110.0f);
    const float protract = std::min(p.protractMaxDeg,
                                    p.protractMaxDeg * (std::max(0.0f, p.shoulder) * in.fast.fwd[size_t(s)] + 0.6f * p.shouldersForward));
    clav[size_t(s)] = glm::angleAxis(glm::radians(sigma * shrug), vec3(0, 0, 1)) *
                      glm::angleAxis(glm::radians(-sigma * protract), vec3(0, 1, 0));
  }

  // 5. Carry: pivots whose skeleton parent is not their anatomical carrier follow the carrier's motion relative to
  // the rest pose (rest frames are axis aligned, so a carrier's rest frame is a translation to its pivot).
  const vec3 ro = pose.rootOffset;
  auto carrierDelta = [&](const std::vector<mat4>& G, int carrier) {
    return G[size_t(carrier)] * glm::translate(mat4(1), -(sk.bones[size_t(carrier)].head + ro));
  };
  auto carry = [&](const std::vector<mat4>& G, int bone, int carrier, bool rotate) {
    if (bone < 0 || carrier < 0 || descendant(sk, bone, carrier)) return;
    const mat4 D = carrierDelta(G, carrier);
    const Bone& B = sk.bones[size_t(bone)];
    const vec3 want = vec3(D * vec4(B.head + ro, 1.0f));  // where the carrier takes the rest pivot
    if (B.parent < 0) {
      pose.offset[size_t(bone)] = want - (B.head + ro);
    } else {  // offset in the parent's frame
      const mat4& PG = G[size_t(B.parent)];
      pose.offset[size_t(bone)] = vec3(glm::inverse(PG) * vec4(want, 1.0f)) - (B.head - sk.bones[size_t(B.parent)].head);
    }
    if (rotate) {
      const quat parentR = B.parent >= 0 ? rotOf(G[size_t(B.parent)]) : quat(1, 0, 0, 0);
      pose.local[size_t(bone)] = glm::normalize(glm::inverse(parentR) * rotOf(D) * parentR * pose.local[size_t(bone)]);
    }
  };
  std::vector<mat4> G = boneGlobals(sk, pose, I);
  for (int s = 0; s < 2; ++s) {
    const int cl = rig.clavicle[size_t(s)];
    if (cl < 0) continue;
    carry(G, cl, rig.chest, true);
    // The shrug turns the clavicle about its own pivot, in character axes.
    const int parent = sk.bones[size_t(cl)].parent;
    const std::vector<mat4> Gc = boneGlobals(sk, pose, I);
    const quat parentR = parent >= 0 ? rotOf(Gc[size_t(parent)]) : quat(1, 0, 0, 0);
    pose.local[size_t(cl)] = glm::normalize(glm::inverse(parentR) * clav[size_t(s)] * parentR * pose.local[size_t(cl)]);
  }
  G = boneGlobals(sk, pose, I);
  for (int s = 0; s < 2; ++s) {
    const int carrier = rig.clavicle[size_t(s)] >= 0 ? rig.clavicle[size_t(s)] : rig.chest;
    carry(G, rig.upper[size_t(s)], carrier, false);
    carry(G, rig.thigh[size_t(s)], rig.hips, false);
  }
  for (int h : rig.hipHelpers) carry(G, h, rig.hips, true);

  // The support leg must still reach its foot: lower the pelvis by what the longest leg lacks (knees soften).
  if (stand > 1e-3f) {
    G = boneGlobals(sk, pose, I);
    float excess = 0;
    for (int s = 0; s < 2; ++s) {
      if (!rig.leg(s)) continue;
      const int th = rig.thigh[size_t(s)], sh = rig.shin[size_t(s)], ft = rig.foot[size_t(s)];
      const float chain = glm::distance(sk.bones[size_t(th)].head, sk.bones[size_t(sh)].head) +
                          glm::distance(sk.bones[size_t(sh)].head, sk.bones[size_t(ft)].head);
      const vec3 hip = pos(G[size_t(th)]), foot = pos(G0[size_t(ft)]);
      const float vertical = std::max(1e-4f, hip.y - foot.y);
      // Only what the layer adds: a leg the pose before already had straight stays straight (not bent by lowering).
      const float before = glm::distance(pos(G0[size_t(th)]), foot) - 0.999f * chain;
      const float need = glm::distance(hip, foot) - 0.999f * chain - std::max(0.0f, before);
      if (need > 0) excess = std::max(excess, need * glm::distance(hip, foot) / vertical);
    }
    pose.rootOffset.y -= excess * stand;
  }

  // 6. Feet stay planted: two-bone leg IK back to the feet of the pose before the layer, sole orientation kept.
  if (stand > 1e-3f)
    for (int s = 0; s < 2; ++s) {
      if (!rig.leg(s) || sk.bones[size_t(rig.foot[size_t(s)])].parent != rig.shin[size_t(s)] ||
          sk.bones[size_t(rig.shin[size_t(s)])].parent != rig.thigh[size_t(s)])
        continue;
      const int th = rig.thigh[size_t(s)], sh = rig.shin[size_t(s)], ft = rig.foot[size_t(s)];
      G = boneGlobals(sk, pose, I);
      // A straight knee has no bend plane: pre-bend it slightly forward so the IK bends the knee the natural way.
      const vec3 a = pos(G[size_t(th)]), b = pos(G[size_t(sh)]), c = pos(G[size_t(ft)]);
      const float bend = glm::degrees(std::acos(std::clamp(glm::dot(glm::normalize(b - a), glm::normalize(c - b)), -1.0f, 1.0f)));
      if (bend < 4.0f) {
        const quat shinR = rotOf(G[size_t(sh)]);
        const vec3 axis = glm::normalize(glm::cross(c - a, vec3(0, 0, 1)) + vec3(1e-6f, 0, 0));  // knee toward +z
        pose.local[size_t(sh)] = glm::normalize(pose.local[size_t(sh)] * glm::angleAxis(glm::radians(4.0f - bend), glm::inverse(shinR) * -axis));
      }
      solveTwoBoneIK(sk, pose, I, ft, pos(G0[size_t(ft)]), stand);
      const std::vector<mat4> G1 = boneGlobals(sk, pose, I);
      const quat want = glm::inverse(rotOf(G1[size_t(sh)])) * rotOf(G0[size_t(ft)]);
      pose.local[size_t(ft)] = glm::normalize(glm::slerp(pose.local[size_t(ft)], want, stand));
    }
}

}  // namespace plush
