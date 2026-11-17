// Hand-prop interaction actions (see interaction.h). Compiled into generated tracks and prop parent switches by
// SceneEvaluator::compileActions (actions.cpp); evaluated by the ordinary pose path (IK, hand pose, look) plus the
// orientation constraint below, which scene.cpp applies after IK.
#include "scene/interaction.h"

#include <algorithm>
#include <format>
#include <optional>

#include "scene/scene.h"

namespace plush {

// ------------------------------------------------------------------------------------------------ shared helpers
vec3 rotationVector(const quat& q0) {
  quat q = glm::normalize(q0);
  if (q.w < 0) q = -q;  // shortest arc, angle in [0, pi]
  const float s = std::sqrt(std::max(0.0f, 1.0f - q.w * q.w));
  const float angle = 2.0f * std::atan2(s, q.w);
  if (s < 1e-7f) return vec3(q.x, q.y, q.z) * 2.0f;
  return vec3(q.x, q.y, q.z) / s * angle;
}

quat fromRotationVector(vec3 v) {
  const float angle = glm::length(v);
  if (angle < 1e-8f) return quat(1, 0, 0, 0);
  return glm::angleAxis(angle, v / angle);
}

HandGrip handGrip(const Skeleton& sk, int handBone, char side) {
  HandGrip g;
  if (handBone < 0 || size_t(handBone) >= sk.bones.size()) return g;
  const vec3 head = sk.bones[size_t(handBone)].head;
  const std::string s = std::string(".") + side;
  vec3 sum(0);
  int n = 0;
  for (int k = 0; k < 4; ++k)
    if (int b = sk.find(std::format("f{}a{}", k, s)); b >= 0) sum += sk.bones[size_t(b)].head, ++n;
  if (n == 0)  // no finger roles: the hand's children stand in for the finger roots
    for (const Bone& b : sk.bones)
      if (b.parent == handBone) sum += b.head, ++n;
  const vec3 roots = n > 0 ? sum / float(n) : head;
  const HandFrame& f = side == 'L' ? sk.handL : sk.handR;
  vec3 d = glm::length(f.fingerDir) > 1e-6f ? glm::normalize(f.fingerDir)
           : glm::length(roots - head) > 1e-4f ? glm::normalize(roots - head)
                                                : vec3(0, -1, 0);
  vec3 nn = glm::length(f.palmNormal) > 1e-6f ? f.palmNormal : vec3(side == 'L' ? -1.0f : 1.0f, 0, 0);
  nn -= d * glm::dot(nn, d);
  nn = glm::length(nn) > 1e-6f ? glm::normalize(nn) : glm::normalize(glm::cross(d, vec3(0, 0, 1)));
  g.fingerDir = d;
  g.palmNormal = nn;
  g.palmLength = n > 0 ? std::max(0.02f, glm::dot(roots - head, d)) : 0.06f;
  // The contact point sits on the palm surface between the wrist and the finger roots.
  g.palm = d * (0.65f * g.palmLength) + nn * (0.22f * g.palmLength);
  return g;
}

void applyOrientConstraints(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame,
                            const mat4& world, Pose& pose) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    const std::string name = prefix + "orient." + sk.bones[i].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    const float w = std::clamp(clip.evaluate(name + ".weight", frame, vec3(1)).x, 0.0f, 1.0f);
    if (w <= 0) continue;
    const int parent = sk.bones[i].parent;
    const mat4 parentGlobal = parent >= 0 ? boneGlobals(sk, pose, world)[size_t(parent)] : world;
    const mat3 pm(glm::normalize(vec3(parentGlobal[0])), glm::normalize(vec3(parentGlobal[1])),
                  glm::normalize(vec3(parentGlobal[2])));
    const quat local = glm::normalize(glm::inverse(glm::normalize(glm::quat_cast(pm))) * fromRotationVector(t->evaluate(frame)));
    pose.local[i] = w >= 1.0f ? local : glm::normalize(glm::slerp(pose.local[i], local, w));
  }
}

// ------------------------------------------------------------------------------------- arm-body clearance (T-030)
namespace {

enum class Region { Other, Torso, ArmL, ArmR, Leg, Head };
enum class ArmPart { None, Upper, Fore, Hand };

bool startsWith(const std::string& s, const char* p) { return s.rfind(p, 0) == 0; }
bool isFingerName(const std::string& n) {
  return n.size() >= 4 && ((n[0] == 'f' && n[1] >= '0' && n[1] <= '9') || startsWith(n, "thumb"));
}

// Region of a bone: the nearest role on its way to the root decides (helpers belong to their role's region).
Region regionOf(const Skeleton& sk, int b) {
  for (int k = b; k >= 0; k = sk.bones[size_t(k)].parent) {
    const std::string& n = sk.bones[size_t(k)].name;
    const char side = n.empty() ? ' ' : n.back();
    if (startsWith(n, "upperArm.") || startsWith(n, "forearm.") || startsWith(n, "hand.") || (isFingerName(n) && n.find('.') != std::string::npos))
      return side == 'L' ? Region::ArmL : Region::ArmR;
    if (startsWith(n, "thigh.") || startsWith(n, "shin.") || startsWith(n, "foot.") || startsWith(n, "toe")) return Region::Leg;
    if (n == "neck" || n == "head" || startsWith(n, "eye.")) return Region::Head;
    if (n == "hips" || n == "spine" || n == "chest") return Region::Torso;
  }
  return Region::Other;
}
ArmPart armPartOf(const Skeleton& sk, int b) {
  for (int k = b; k >= 0; k = sk.bones[size_t(k)].parent) {
    const std::string& n = sk.bones[size_t(k)].name;
    if (startsWith(n, "hand.") || isFingerName(n)) return ArmPart::Hand;
    if (startsWith(n, "forearm.")) return ArmPart::Fore;
    if (startsWith(n, "upperArm.")) return ArmPart::Upper;
  }
  return ArmPart::None;
}

float percentile(std::vector<float> v, float q, float fallback) {
  if (v.size() < 20) return fallback;
  const size_t k = std::min(v.size() - 1, size_t(q * float(v.size() - 1)));
  std::nth_element(v.begin(), v.begin() + std::ptrdiff_t(k), v.end());
  return v[k];
}


// Signed gap of world point p to a body section whose owning bone has global Gb. The section is elliptical (radii
// r1 along e1, r2 along e2; round ends are half-ellipsoids with axial radius min(r1, r2)). The gap is the first-order
// distance to that surface, (F - 1) / |grad F| for the implicit F = |(ax / rc, y / r1, z / r2)| (T-040; T-030 used
// coordinates scaled to the smaller radius, which made a flat section read as deep as its narrow side everywhere:
// up to several centimetres too conservative in front of a wide, shallow pelvis). It is exact on the surface and
// along the axes, and its gradient is the outward normal. Past a joined (flat) end it is the distance to the end
// disc.
struct SectionGap {
  float gap;
  vec3 worldGrad;
};
SectionGap sectionGapInv(const BodyCapsule& C, const mat4& Gb, const mat4& invGb, vec3 p, char side) {
  vec3 u = C.p1 - C.p0;
  const float L = glm::length(u);
  u = L > 1e-6f ? u / L : glm::normalize(glm::cross(C.e1, C.e2));
  const float rc = std::min(C.r1, C.r2);
  const vec3 q0 = vec3(invGb * vec4(p, 1)) - C.p0;
  const float x = glm::dot(q0, u), y = glm::dot(q0, C.e1), z = glm::dot(q0, C.e2);
  const float ax = x < 0 ? -x : x > L ? x - L : 0.0f;
  const float axSign = x < 0 ? -1.0f : 1.0f;
  const bool round = (x < 0 && C.cap0) || (x > L && C.cap1);
  const vec3 sideDir = C.e1 * (side == 'L' ? 1.0f : -1.0f);
  float gap;
  vec3 local;
  if (ax <= 0 || round) {
    const vec3 a(ax / rc, y / C.r1, z / C.r2);
    const float F = glm::length(a);
    const vec3 grad(axSign * ax / (rc * rc), y / (C.r1 * C.r1), z / (C.r2 * C.r2));  // F * grad F
    const float gl = glm::length(grad);
    if (F < 1e-4f || gl < 1e-9f) {
      gap = -rc;
      local = sideDir;
    } else {
      gap = (F - 1) * F / gl;
      local = u * grad.x + C.e1 * grad.y + C.e2 * grad.z;
    }
  } else {
    const float rho = glm::length(vec2(y / C.r1, z / C.r2));
    const vec2 g2(y / (C.r1 * C.r1), z / (C.r2 * C.r2));
    const float gl = glm::length(g2);
    const float radialGap = rho > 1e-4f && gl > 1e-9f ? (rho - 1) * rho / gl : -rc;
    const float ro = std::max(radialGap, 0.0f);
    gap = std::sqrt(ro * ro + ax * ax);
    const vec3 rad = gl > 1e-9f ? (C.e1 * g2.x + C.e2 * g2.y) / gl : vec3(0);
    local = u * (axSign * ax) + ro * rad;
  }
  if (glm::length(local) < 1e-9f) local = sideDir;
  return {gap, glm::normalize(mat3(Gb) * glm::normalize(local))};
}
SectionGap sectionGap(const BodyCapsule& C, const mat4& Gb, vec3 p, char side) {
  return sectionGapInv(C, Gb, glm::inverse(Gb), p, side);
}

vec3 skinPoint(const ArmPoint& P, const std::vector<mat4>& G) {
  vec3 p(0);
  for (int k = 0; k < 4; ++k)
    if (P.weight[k] > 0) p += P.weight[k] * vec3(G[size_t(P.joint[k])] * vec4(P.local[k], 1));
  return p;
}

}  // namespace

BodyClearanceModel bodyClearanceModel(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes) {
  BodyClearanceModel M;
  const int hips = sk.find("hips"), chest = sk.find("chest"), spine = sk.find("spine"), neck = sk.find("neck");
  if (hips < 0 || chest < 0) return M;
  auto head = [&](int b) { return sk.bones[size_t(b)].head; };
  for (int s = 0; s < 2; ++s) {
    const char side = s == 0 ? 'L' : 'R';
    ArmModel& A = M.arm[s];
    A.hand = sk.find(std::string("hand.") + side);
    if (A.hand < 0) return M;
    A.fore = sk.bones[size_t(A.hand)].parent;
    A.upper = A.fore >= 0 ? sk.bones[size_t(A.fore)].parent : -1;
    if (A.upper < 0) return M;
  }
  // Skinned rest vertices by region (a vertex counts when >= 90 % of its weight is in one region).
  std::vector<int> region(sk.bones.size()), part(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) region[b] = int(regionOf(sk, int(b))), part[b] = int(armPartOf(sk, int(b)));
  std::vector<vec3> torso, pelvisLegs;
  struct Cand { const SkinnedMesh* m; size_t v; };
  std::vector<Cand> armCand[2];
  for (const SkinnedMesh& m : meshes) {
    for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size() && v < m.weights.size(); ++v) {
      float w[6] = {0, 0, 0, 0, 0, 0};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j < 0 || size_t(j) >= sk.bones.size() || m.weights[v][k] <= 0) continue;
        w[region[size_t(j)]] += m.weights[v][k];
      }
      if (w[int(Region::Torso)] >= 0.9f) torso.push_back(m.rest.positions[v]);
      // At the pelvis the hips' sides are often carried by the thighs (shorts, a skirt, the skin of the hip): there
      // the body is torso and leg together (T-040; a torso-only fit found a 4 cm wide pelvis on some characters).
      else if (w[int(Region::Torso)] + w[int(Region::Leg)] >= 0.9f) pelvisLegs.push_back(m.rest.positions[v]);
      // Arm surface: carried at least half by that arm (a sleeve between shoulder and hand included), nothing of the
      // head or legs; torso garment vertices with a little weight bleed onto the arm stay body.
      for (int s = 0; s < 2; ++s)
        if (w[int(s == 0 ? Region::ArmL : Region::ArmR)] >= 0.5f && w[int(Region::Head)] + w[int(Region::Leg)] < 0.1f)
          armCand[s].push_back({&m, v});
    }
  }
  const bool fromMesh = torso.size() >= 200;
  M.source = fromMesh ? "mesh" : "skeleton";
  const int ua = sk.find("upperArm.L"), ub = sk.find("upperArm.R");
  const float shoulderHalf = ua >= 0 && ub >= 0 ? 0.5f * glm::distance(head(ua), head(ub)) : 0.12f;
  const float rDefault = 0.95f * shoulderHalf;
  // Body sections along the spine: pelvis (below the hips, carried by the hips), lower torso (hips -> chest, carried
  // by the spine or hips) and upper torso (chest -> neck, carried by the chest), each cut into short bands whose
  // radii fit the vertices of their own height slab (a waist is narrower than a belly). Bands meet with flat ends;
  // the lowest and highest are capsules with round ends.
  auto band = [&](std::string name, int bone, vec3 a, vec3 b, bool withLegs) {
    BodyCapsule C;
    C.name = std::move(name);
    C.bone = bone;
    C.p0 = a - head(bone);
    C.p1 = b - head(bone);
    const vec3 u = glm::normalize(b - a);
    C.e1 = glm::normalize(vec3(1, 0, 0) - u * u.x);
    C.e2 = glm::normalize(glm::cross(C.e1, u));  // forward (+Z) for an upright segment
    C.cap0 = C.cap1 = false;
    std::vector<float> side, front;
    for (size_t i = 0; i < torso.size() + (withLegs ? pelvisLegs.size() : 0); ++i) {
      const vec3& p = i < torso.size() ? torso[i] : pelvisLegs[i - torso.size()];
      const float t = glm::dot(p - a, b - a) / glm::dot(b - a, b - a);
      if (t < 0 || t > 1) continue;
      const vec3 d = p - (a + t * (b - a));
      if (glm::dot(d, C.e2) < 0) continue;  // front half only: hands work in front (hair, a backpack are not body)
      side.push_back(std::abs(glm::dot(d, C.e1)));
      front.push_back(glm::dot(d, C.e2));
    }
    C.r1 = std::clamp(percentile(side, 0.99f, rDefault), 0.02f, 0.5f);
    C.r2 = std::clamp(percentile(front, 0.99f, rDefault), 0.02f, 0.5f);
    M.body.push_back(C);
  };
  const vec3 top = neck >= 0 ? head(neck) : head(chest) + vec3(0, 0.6f * shoulderHalf, 0);
  const vec3 bottom = head(hips) + 0.4f * (head(hips) - head(chest));
  auto bands = [&](const char* name, int bone, vec3 a, vec3 b, int n, bool withLegs) {
    for (int i = 0; i < n; ++i)
      band(std::format("{}_{}", name, i + 1), bone, glm::mix(a, b, float(i) / float(n)), glm::mix(a, b, float(i + 1) / float(n)), withLegs);
  };
  bands("pelvis", hips, bottom, head(hips), 2, true);
  bands("torso_lower", spine >= 0 ? spine : hips, head(hips), head(chest), 3, false);
  bands("torso_upper", chest, head(chest), top, 2, false);
  M.body.front().cap0 = true;
  M.body.back().cap1 = true;
  // Arm points: an even subsample (at most 600 per arm) of the arm surface, with skin weights and joint offsets.
  for (int s = 0; s < 2; ++s) {
    ArmModel& A = M.arm[s];
    const char side = s == 0 ? 'L' : 'R';
    const HandGrip g = handGrip(sk, A.hand, side);
    const vec3 su = head(A.upper), sf = head(A.fore), sh = head(A.hand), st = sh + g.fingerDir * (1.5f * g.palmLength);
    auto segDist = [](vec3 p, vec3 a, vec3 b) {
      const float t = std::clamp(glm::dot(p - a, b - a) / std::max(1e-9f, glm::dot(b - a, b - a)), 0.0f, 1.0f);
      return glm::distance(p, a + t * (b - a));
    };
    const size_t stride = std::max<size_t>(1, armCand[s].size() / 600);
    for (size_t i = 0; i < armCand[s].size(); i += stride) {
      const SkinnedMesh& m = *armCand[s][i].m;
      const size_t v = armCand[s][i].v;
      ArmPoint P;
      const vec3 p = m.rest.positions[v];
      for (int k = 0; k < 4; ++k) {
        const int j = std::clamp(m.joints[v][k], 0, int(sk.bones.size()) - 1);
        P.joint[k] = j;
        P.weight[k] = m.weights[v][k];
        P.local[k] = p - sk.bones[size_t(j)].head;
        if (part[size_t(j)] == int(ArmPart::Fore) || part[size_t(j)] == int(ArmPart::Hand)) P.mobility += m.weights[v][k];
        const int pj = part[size_t(j)];
        if (pj != int(ArmPart::None)) P.followUpper += m.weights[v][k];
        if (pj == int(ArmPart::Fore) || pj == int(ArmPart::Hand)) P.followFore += m.weights[v][k];
        if (pj == int(ArmPart::Hand)) P.followHand += m.weights[v][k];
      }
      P.along = glm::dot(p - su, sf - su) / std::max(1e-9f, glm::dot(sf - su, sf - su));
      const float du = segDist(p, su, sf), df = segDist(p, sf, sh), dh = segDist(p, sh, st);
      // The elbow half of the forearm counts with the upper arm: an elbow rests against the body's side.
      const float tf = glm::dot(p - sf, sh - sf) / std::max(1e-9f, glm::dot(sh - sf, sh - sf));
      P.part = dh <= df && dh <= du ? 2 : (df <= du && tf >= 0.5f) ? 1 : 0;
      A.points.push_back(P);
    }
  }
  // Resting contact: an arm point already inside a body section at rest (a sleeve under a vest's armhole, a puff
  // pressed against the side) may stay as deep as it rests, never deeper; every other point keeps the margin.
  std::vector<mat4> rest(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) rest[b] = glm::translate(mat4(1), sk.bones[b].head);
  for (int s = 0; s < 2; ++s)
    for (ArmPoint& P : M.arm[s].points) {
      float g = 1e9f;
      for (const BodyCapsule& C : M.body) g = std::min(g, sectionGap(C, rest[size_t(C.bone)], skinPoint(P, rest), s == 0 ? 'L' : 'R').gap);
      P.allowance = std::min(0.0f, g - kArmBodyMargin);
    }
  M.valid = true;
  return M;
}

float bodySectionGap(const BodyCapsule& C, const mat4& Gb, vec3 p) { return sectionGap(C, Gb, p, 'L').gap; }

ArmClearance armClearance(const BodyClearanceModel& M, const std::vector<mat4>& G, char side) {
  ArmClearance out;
  if (!M.valid) return out;
  static const char* kPart[3] = {"upperArm", "forearm", "hand"};
  for (const ArmPoint& P : M.arm[side == 'L' ? 0 : 1].points) {
    const vec3 p = skinPoint(P, G);
    for (const BodyCapsule& C : M.body) {
      const SectionGap sg = sectionGap(C, G[size_t(C.bone)], p, side);
      const float gap = sg.gap - P.allowance;  // never deeper than at rest
      if (P.part == 0) {  // upper arm: reported only here (the T-040 post-pass clears it past the armpit band)
        out.upperGap = std::min(out.upperGap, gap);
        continue;
      }
      out.rawGap = std::min(out.rawGap, sg.gap);
      if (gap >= out.gap) continue;
      out.gap = gap;
      out.part = kPart[P.part];
      out.against = C.name;
      out.mobility = P.mobility;
      out.point = p;
      out.push = sg.worldGrad;
    }
  }
  return out;
}

void applyArmPoles(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                   Pose& pose) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    const std::string name = prefix + "pole." + sk.bones[i].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    const float w = std::clamp(clip.evaluate(name + ".weight", frame, vec3(1)).x, 0.0f, 1.0f);
    const int mid = sk.bones[i].parent, root = mid >= 0 ? sk.bones[size_t(mid)].parent : -1;
    if (w <= 0 || root < 0) continue;
    const std::vector<mat4> G = boneGlobals(sk, pose, world);
    const vec3 a(G[size_t(root)][3]), b(G[size_t(mid)][3]), c(G[i][3]);
    if (glm::length(c - a) < 1e-5f) continue;
    const vec3 u = glm::normalize(c - a), pole = t->evaluate(frame);
    vec3 e = (b - a) - u * glm::dot(b - a, u), p = pole - u * glm::dot(pole, u);
    const float le = glm::length(e), lp = glm::length(p), lpole = glm::length(pole);
    if (le < 1e-5f || lp < 1e-6f || lpole < 1e-6f) continue;
    e /= le;
    p /= lp;
    // A pole nearly along the arm has no meaningful plane: fade out instead of flipping.
    const float strength = std::clamp((lp / lpole) / 0.3f, 0.0f, 1.0f);
    const float angle = std::atan2(glm::dot(glm::cross(e, p), u), glm::dot(e, p));
    const quat R = glm::angleAxis(angle * w * strength, u);
    const int parent = sk.bones[size_t(root)].parent;
    const mat4 pg = parent >= 0 ? G[size_t(parent)] : world;
    const quat parentRot = glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(pg[0])), glm::normalize(vec3(pg[1])),
                                                              glm::normalize(vec3(pg[2])))));
    const quat handBefore = glm::normalize(glm::quat_cast(mat3(G[i])));
    pose.local[size_t(root)] = glm::normalize(glm::inverse(parentRot) * R * parentRot * pose.local[size_t(root)]);
    // Only the elbow moves: the hand keeps its world rotation (the forearm's swing is taken out of the hand's local).
    const quat midAfter = glm::normalize(glm::quat_cast(mat3(boneGlobals(sk, pose, world)[size_t(mid)])));
    pose.local[i] = glm::normalize(glm::inverse(midAfter) * handBefore);
  }
}

// ------------------------------------------------------------------------ always-on arm-body clearance (T-040)
namespace {

quat rotationOf(const mat4& m) {
  return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(m[0])), glm::normalize(vec3(m[1])), glm::normalize(vec3(m[2])))));
}

struct WorstPoint {
  float gap = 1e9f;
  const ArmPoint* point = nullptr;
  vec3 p{0}, n{0};
};
// The body sections are carried by torso bones, which the arm pass never moves: their inverses are computed once.
struct BodyFrames {
  std::vector<mat4> G, inv;
};
BodyFrames bodyFrames(const BodyClearanceModel& M, const std::vector<mat4>& G) {
  BodyFrames B;
  for (const BodyCapsule& C : M.body) B.G.push_back(G[size_t(C.bone)]), B.inv.push_back(glm::inverse(G[size_t(C.bone)]));
  return B;
}
bool postPassPoint(const ArmPoint& P, const ArmPostPassOptions& o) {
  return !(P.part == 0 && P.along < o.armpit) && P.followUpper >= 0.5f;
}
WorstPoint worstArmPoint(const BodyClearanceModel& M, const BodyFrames& B, const std::vector<mat4>& G, char side,
                         const ArmPostPassOptions& o) {
  WorstPoint w;
  for (const ArmPoint& P : M.arm[side == 'L' ? 0 : 1].points) {
    if (!postPassPoint(P, o)) continue;
    const vec3 p = skinPoint(P, G);
    for (size_t k = 0; k < M.body.size(); ++k) {
      const SectionGap sg = sectionGapInv(M.body[k], B.G[k], B.inv[k], p, side);
      const float gap = sg.gap - P.allowance;
      if (gap < w.gap) w = {gap, &P, p, sg.worldGrad};
    }
  }
  return w;
}
// C1 ramp of the target gap (see interaction.h).
float targetGap(float gap, const ArmPostPassOptions& o) {
  const float x = o.margin + o.band - gap, b = std::max(o.band, 1e-6f);
  if (x <= 0) return gap;
  return gap + (x < 2 * b ? x * x / (4 * b) : x - b);
}
void rotateBoneWorld(const Skeleton& sk, const std::vector<mat4>& G, const mat4& world, int bone, const quat& R, Pose& pose) {
  const int parent = sk.bones[size_t(bone)].parent;
  const quat pr = rotationOf(parent >= 0 ? G[size_t(parent)] : world);
  pose.local[size_t(bone)] = glm::normalize(glm::inverse(pr) * R * pr * pose.local[size_t(bone)]);
}
quat rotationFromVector(vec3 w) {
  const float a = glm::length(w);
  return a > 1e-9f ? glm::angleAxis(a, w / a) : quat(1, 0, 0, 0);
}

}  // namespace

float armBodyGap(const BodyClearanceModel& M, const std::vector<mat4>& G, char side, const ArmPostPassOptions& o) {
  if (!M.valid) return 1e9f;
  return worstArmPoint(M, bodyFrames(M, G), G, side, o).gap;
}

ArmPostPassResult applyArmBodyClearance(const Skeleton& sk, const BodyClearanceModel& M, const mat4& world, char side,
                                        float pin, float keepHand, Pose& pose, const ArmPostPassOptions& o) {
  ArmPostPassResult out;
  if (!M.valid) return out;
  const ArmModel& A = M.arm[side == 'L' ? 0 : 1];
  if (A.points.empty() || A.upper < 0 || A.fore < 0 || A.hand < 0) return out;
  pin = std::clamp(pin, 0.0f, 1.0f);
  keepHand = std::clamp(std::max(keepHand, pin), 0.0f, 1.0f);
  std::vector<mat4> G = boneGlobals(sk, pose, world);
  const BodyFrames B = bodyFrames(M, G);
  WorstPoint w = worstArmPoint(M, B, G, side, o);
  out.before = out.after = w.gap;
  if (w.gap >= o.margin + o.band) return out;  // already clear: the pose is not touched
  const float target = targetGap(w.gap, o);
  const quat handWorld = rotationOf(G[size_t(A.hand)]);
  const quat handLocal = pose.local[size_t(A.hand)];
  // Weights of the minimum-norm step: the shoulder carries most of a free arm's correction (the arm moves away as a
  // whole and keeps its acting shape), the elbow less; a pinned (IK) arm only swings about shoulder -> wrist.
  const float aS = 1 - pin, aE = 0.5f * (1 - pin), aT = pin;
  float totalS = 0, totalE = 0, totalT = 0;
  constexpr float kMaxTotal = 0.7f;  // radians per joint over the whole pass (a guard; real corrections are small)
  Pose best = pose;
  for (int it = 0; it < o.iterations && w.point && w.gap < target - 1e-4f; ++it) {
    const ArmPoint& P = *w.point;
    const vec3 s(G[size_t(A.upper)][3]), e(G[size_t(A.fore)][3]), h(G[size_t(A.hand)][3]);
    const vec3 rs = w.p - s, re = w.p - e;
    const float handFixed = P.followHand * keepHand;  // hand points keep their world rotation when the hand is kept
    const vec3 Js = P.followUpper * glm::cross(rs, w.n);
    const vec3 Je = P.followFore * glm::cross(re, w.n);
    vec3 u = h - s;
    u = glm::length(u) > 1e-6f ? glm::normalize(u) : vec3(0);
    const float Jt = std::max(0.0f, P.followUpper - handFixed) * glm::dot(u, glm::cross(rs, w.n));
    const float D = aS * glm::dot(Js, Js) + aE * glm::dot(Je, Je) + aT * Jt * Jt;
    if (D < 1e-10f) break;
    const float lambda = (target - w.gap) / D;
    auto capped = [&](vec3 v, float& total) {
      float a = glm::length(v);
      const float lim = std::min(o.maxStep, std::max(0.0f, kMaxTotal - total));
      if (a > lim) v *= lim / a, a = lim;
      total += a;
      return v;
    };
    const vec3 ws = capped(aS * lambda * Js, totalS), we = capped(aE * lambda * Je, totalE);
    float th = aT * lambda * Jt;
    {
      const float lim = std::min(o.maxStep, std::max(0.0f, kMaxTotal - totalT));
      th = std::clamp(th, -lim, lim);
      totalT += std::abs(th);
    }
    const quat Rs = glm::normalize(glm::angleAxis(th, u) * rotationFromVector(ws));
    if (glm::length(ws) + std::abs(th) + glm::length(we) < 1e-7f) break;
    rotateBoneWorld(sk, G, world, A.upper, Rs, pose);
    G = boneGlobals(sk, pose, world);
    if (glm::length(we) > 0) {
      rotateBoneWorld(sk, G, world, A.fore, rotationFromVector(we), pose);
      G = boneGlobals(sk, pose, world);
    }
    // The hand: its own local rotation (it follows the forearm), or its world rotation as far as `keepHand` asks.
    const quat kept = glm::normalize(glm::inverse(rotationOf(G[size_t(A.fore)])) * handWorld);
    pose.local[size_t(A.hand)] = keepHand >= 1 ? kept : glm::normalize(glm::slerp(handLocal, kept, keepHand));
    G = boneGlobals(sk, pose, world);
    const WorstPoint next = worstArmPoint(M, B, G, side, o);
    if (next.gap < w.gap - 1e-4f) {  // no progress (a point the free joints cannot move): keep the best pose
      pose = best;
      break;
    }
    w = next;
    best = pose;
  }
  out.after = w.gap;
  out.changed = true;
  return out;
}

namespace {

double num(const Json& j, const char* k, double fallback) {
  auto it = j.find(k);
  return (it != j.end() && it->is_number()) ? it->get<double>() : fallback;
}
std::string str(const Json& j, const char* k, const std::string& fallback = {}) {
  auto it = j.find(k);
  return (it != j.end() && it->is_string()) ? it->get<std::string>() : fallback;
}
bool flag(const Json& j, const char* k, bool fallback) {
  auto it = j.find(k);
  return (it != j.end() && it->is_boolean()) ? it->get<bool>() : fallback;
}
std::optional<vec3> vecOpt(const Json& j, const char* k) {
  auto it = j.find(k);
  if (it == j.end() || !it->is_array() || it->size() != 3) return std::nullopt;
  for (const auto& x : *it)
    if (!x.is_number()) return std::nullopt;
  return vec3((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
}
void key(Clip& c, const std::string& track, double f, vec3 v, Interp in = Interp::Smooth) {
  c.tracks[track].setKey({f, v, in});
}
void dropKeysAfter(Clip& c, const std::string& track, double f) {
  auto it = c.tracks.find(track);
  if (it == c.tracks.end()) return;
  auto& k = it->second.keys;
  k.erase(std::remove_if(k.begin(), k.end(), [&](const Key& x) { return x.frame > f; }), k.end());
}
char sideOf(const Json& a, const char* k) {
  const std::string s = str(a, k, "R");
  return !s.empty() && (s[0] == 'L' || s[0] == 'l') ? 'L' : 'R';
}

// Where a hand closes on a prop, in the prop's local frame (metres): the grasp centre (on the object's axis or
// mid-plane next to the socket), the inward direction (from the socket into the object), the cylinder axis (zero for
// a sphere-like grasp) and the radius the fingers close on. Primitive cylinders stand on their base at the origin
// along +Y; boxes and spheres are centred (docs/ASSET_LIBRARY.md).
struct GraspShape {
  vec3 centre{0}, inward{0, -1, 0}, axis{0}, middle{0};
  float radius = 0.03f;
};

GraspShape graspShape(const PropAsset& asset, vec3 s) {
  enum class Kind { Box, Sphere, Cylinder } kind = Kind::Sphere;
  vec3 size(0.06f);
  float radius = 0.03f, y0 = 0, y1 = 0;
  mat4 frame(1);  // proxy frame inside the prop
  const float k = asset.scaleMetres > 0 ? asset.scaleMetres : 1.0f;
  if (asset.mesh.kind == AssetMeshSource::Kind::Primitive) {
    using P = AssetMeshSource::Primitive;
    kind = asset.mesh.primitive == P::Box ? Kind::Box : asset.mesh.primitive == P::Sphere ? Kind::Sphere : Kind::Cylinder;
    size = asset.mesh.size * k;
    radius = asset.mesh.radius * k;
    y0 = 0;
    y1 = asset.mesh.height * k;
  } else if (asset.collision) {
    using T = AssetCollisionProxy::Type;
    const auto& c = *asset.collision;
    kind = c.type == T::Box ? Kind::Box : c.type == T::Sphere ? Kind::Sphere : Kind::Cylinder;
    size = c.size;
    radius = c.radius;
    y0 = -0.5f * c.height;  // capsules are centred
    y1 = 0.5f * c.height;
    frame = assetTransformMatrix(c.transform);
  }
  const mat4 inv = glm::inverse(frame);
  const vec3 p = vec3(inv * vec4(s, 1));
  GraspShape g;
  switch (kind) {
    case Kind::Cylinder: {
      const vec3 radial(p.x, 0, p.z);
      g.middle = vec3(0, 0.5f * (y0 + y1), 0);
      if (glm::length(radial) >= 0.5f * radius && p.y >= y0 - 1e-4f && p.y <= y1 + 1e-4f) {
        g.centre = vec3(0, std::clamp(p.y, y0, y1), 0);
        g.inward = -glm::normalize(radial);
        g.axis = vec3(0, 1, 0);
        g.radius = radius;
      } else {  // on a cap: a sphere-like grasp across the cap
        g.inward = vec3(0, p.y > g.middle.y ? -1.0f : 1.0f, 0);
        g.centre = vec3(p.x, g.middle.y, p.z);
        g.radius = std::min(radius, 0.5f * (y1 - y0));
      }
      break;
    }
    case Kind::Box: {
      const vec3 half = 0.5f * glm::max(size, vec3(1e-5f));
      const vec3 r = glm::abs(p) / half;
      const int i = r.x >= r.y && r.x >= r.z ? 0 : r.y >= r.z ? 1 : 2;
      vec3 out(0);
      out[i] = p[i] >= 0 ? 1.0f : -1.0f;
      g.inward = -out;
      g.centre = p;
      g.centre[i] = 0;
      g.radius = half[i];
      break;
    }
    case Kind::Sphere:
      g.inward = glm::length(p) > 1e-6f ? -glm::normalize(p) : vec3(0, -1, 0);
      g.radius = radius;
      break;
  }
  g.centre = vec3(frame * vec4(g.centre, 1));
  g.middle = vec3(frame * vec4(g.middle, 1));
  g.inward = glm::normalize(vec3(frame * vec4(g.inward, 0)));
  if (glm::length(g.axis) > 0) g.axis = glm::normalize(vec3(frame * vec4(g.axis, 0)));
  return g;
}

// Moves a wrist key at frame f until `error()` (target - measured) is below 0.3 mm: the arm solve, the life layer and
// clip layers make the first estimate a little off. Keeps the best key and stops when a step no longer helps (a
// target out of reach), so the key never runs away. Returns the remaining error.
template <class F>
float correctKey(Track& track, double f, F error) {
  Key* key = nullptr;
  for (auto& k : track.keys)
    if (std::abs(k.frame - f) < 1e-6) key = &k;
  vec3 d = error();
  float e = glm::length(d);
  if (!key) return e;
  vec3 best = key->value;
  float bestE = e;
  for (int it = 0; it < 12 && bestE >= 0.0003f; ++it) {
    key->value = best + d;
    d = error();
    e = glm::length(d);
    if (e >= bestE) break;
    best = key->value;
    bestE = e;
  }
  key->value = best;
  return bestE;
}

constexpr vec3 kUp(0, 1, 0);
const vec3 kRelaxed(0.25f, 0.15f, 0), kOpen(0.03f, 0.05f, 0.35f);

}  // namespace

vec3 SceneEvaluator::handGripPoint(size_t c, char side, double frame) const {
  const int hb = characterSocketBone(c, std::string("hand.") + side);
  if (hb < 0) return vec3(0);
  const HandGrip g = handGrip(characters_[c].asset.skeleton, hb, side);
  return vec3(characterGlobals(c, frame)[size_t(hb)] * vec4(g.palm, 1));
}

Result<bool> SceneEvaluator::compileInteraction(const Json& a, Clip& gen, InteractionContext& ctx) {
  const std::string type = str(a, "type");
  const bool reach = (type == "reach" || type == "grasp") && a.contains("prop");
  if (type == "grasp" && !a.contains("prop")) return fail("grasp: give 'prop' (a scene prop instance)");
  if (!reach && type != "hold" && type != "place" && type != "handover") return false;
  const Clip& clip = scene_.animation;

  auto charIndex = [&](const std::string& n) -> int {
    for (size_t c = 0; c < scene_.characters.size(); ++c)
      if (scene_.characters[c].name == n) return int(c);
    return -1;
  };
  auto propIndex = [&](const std::string& n) -> int {
    for (size_t p = 0; p < scene_.props.size(); ++p)
      if (scene_.props[p].name == n) return int(p);
    return -1;
  };

  struct Hand {
    int c = -1;
    char side = 'R';
    int bone = -1, mid = -1, root = -1;
    std::string who, prefix, ik, orient, pose;
    HandGrip grip;
    float armLength = 0;
  };
  auto handOf = [&](int c, char side, const std::string& what) -> Result<Hand> {
    Hand h;
    h.c = c;
    h.side = side;
    h.bone = characterSocketBone(size_t(c), std::string("hand.") + side);
    const Skeleton& sk = characters_[size_t(c)].asset.skeleton;
    if (h.bone >= 0) h.mid = sk.bones[size_t(h.bone)].parent;
    if (h.mid >= 0) h.root = sk.bones[size_t(h.mid)].parent;
    h.who = scene_.characters[size_t(c)].name;
    if (h.root < 0) return fail(std::format("{}: character '{}' has no hand.{} arm chain", what, h.who, side));
    h.prefix = h.who + "/";
    h.ik = h.prefix + "ik." + sk.bones[size_t(h.bone)].name;
    h.orient = h.prefix + "orient." + sk.bones[size_t(h.bone)].name;
    h.pose = h.prefix + "hand." + side;
    h.grip = handGrip(sk, h.bone, side);
    const auto& B = sk.bones;
    h.armLength = glm::distance(B[size_t(h.root)].head, B[size_t(h.mid)].head) + glm::distance(B[size_t(h.mid)].head, B[size_t(h.bone)].head);
    return h;
  };
  auto boneAt = [&](const Hand& h, int bone, double f) { return vec3(characterGlobals(size_t(h.c), f)[size_t(bone)][3]); };
  auto socketWorld = [&](int p, const std::string& socket, double f) {
    return propWorld(size_t(p), f) * assetTransformMatrix(propAssets_[size_t(p)].sockets.at(socket));
  };
  auto propMiddle = [&](int p, double f) {
    return vec3(propWorld(size_t(p), f) * vec4(graspShape(propAssets_[size_t(p)], vec3(0)).middle, 1));
  };
  auto requireSocket = [&](int p, const std::string& socket, const std::string& what) -> Result<void> {
    if (!propAssets_[size_t(p)].sockets.count(socket))
      return fail(std::format("{}: prop '{}' (asset '{}') has no socket '{}'", what, scene_.props[size_t(p)].name,
                              propAssets_[size_t(p)].id, socket));
    return {};
  };
  auto addSwitch = [&](int p, double f, std::optional<PropParent> parent, const std::string& what) -> Result<void> {
    auto& sw = scene_.props[size_t(p)].parentSwitch;
    for (const auto& e : sw)
      if (e.frame == f) return fail(std::format("{}: prop '{}' already switches parent at frame {}", what, scene_.props[size_t(p)].name, f));
    sw.push_back({f, std::move(parent)});
    std::stable_sort(sw.begin(), sw.end(), [](const PropParentSwitch& x, const PropParentSwitch& y) { return x.frame < y.frame; });
    key(gen, scene_.props[size_t(p)].name + ".parent.weight", f, vec3(1), Interp::Step);  // explicit: fully attached
    return {};
  };
  // Moves the wrist key at frame f until `error()` (target - measured) is below 0.3 mm (the arm solve, life layer
  // and clip layers make the first estimate a little off).
  auto correct = [&](const Hand& h, double f, auto error) { return correctKey(gen.tracks[h.ik], f, error); };
  auto warnReach = [&](const Hand& h, vec3 wrist, double f, const std::string& what) {
    const float d = glm::distance(boneAt(h, h.root, f), wrist) - 0.98f * h.armLength;
    if (d > 0.005f)
      warnings_.push_back(std::format("{}: '{}' cannot reach with hand.{} at frame {} ({:.0f} mm short); move them closer",
                                      what, h.who, h.side, f, d * 1000));
  };
  auto gazeOn = [&](const Hand& h, int p, double from, double to) {
    const std::string track = h.prefix + "lookAt";
    const vec3 prev = clip.evaluate(track, from - 4, propMiddle(p, from));
    dropKeysAfter(gen, track, from - 4);
    key(gen, track, from - 4, prev, Interp::Linear);
    for (double f = from; f < to; f += 3) key(gen, track, f, propMiddle(p, f), Interp::Linear);
    key(gen, track, to, propMiddle(p, to), Interp::Linear);
  };
  auto gazeAt = [&](const Hand& h, vec3 target, double f) { key(gen, h.prefix + "lookAt", f, target, Interp::Linear); };
  auto forwardPoint = [&](const Hand& h, double f) {  // a point ahead of the character at eye height
    const CharacterDesc& cd = scene_.characters[size_t(h.c)];
    const vec3 pos = clip.evaluate(cd.name + ".position", f, cd.position);
    const float yaw = glm::radians(clip.evaluate(cd.name + ".yaw", f, vec3(cd.yawDeg)).x);
    const int head = characterSocketBone(size_t(h.c), "head");
    const float y = head >= 0 ? vec3(characterGlobals(size_t(h.c), f)[size_t(head)][3]).y + 0.05f : pos.y + 0.6f;
    return vec3(pos.x + 2.0f * std::sin(yaw), y, pos.z + 2.0f * std::cos(yaw));
  };
  auto headPoint = [&](int c, double f) {
    const int head = characterSocketBone(size_t(c), "head");
    if (head < 0) return vec3(scene_.characters[size_t(c)].position + vec3(0, 0.6f, 0));
    return vec3(characterGlobals(size_t(c), f)[size_t(head)] * vec4(0, 0.06f, 0.04f, 1));
  };

  // Grasp plan at frame f: the hand's world orientation (palm towards the prop, fingers away from the body, thumb
  // along the prop's axis), the wrist position that puts the palm point on the socket, and the grasp sphere/cylinder
  // in the hand's rest frame.
  struct Plan {
    quat orient{1, 0, 0, 0};
    mat3 R{1};
    vec3 wrist{0}, socket{0}, inward{0, 0, 1}, centre{0}, axis{0};
    float radius = 0.03f;
  };
  auto plan = [&](const Hand& h, int p, const std::string& socket, double f) {
    const mat4 P = propWorld(size_t(p), f);
    const AssetTransform& st = propAssets_[size_t(p)].sockets.at(socket);
    const GraspShape gs = graspShape(propAssets_[size_t(p)], st.translation);
    const mat3 PR(P);
    Plan pl;
    pl.socket = vec3(P * vec4(st.translation, 1));
    const vec3 n = glm::normalize(PR * gs.inward);
    const vec3 centreW = vec3(P * vec4(gs.centre, 1));
    const vec3 axisW = glm::length(gs.axis) > 0 ? glm::normalize(PR * gs.axis) : vec3(0);
    pl.radius = gs.radius * glm::length(vec3(P[0]));
    const vec3 out = pl.socket - boneAt(h, h.root, f);
    const float sgn = h.side == 'R' ? 1.0f : -1.0f;  // thumb = sgn * (fingers x palm normal)
    vec3 d, t;
    if (glm::length(axisW) > 0 && std::abs(glm::dot(axisW, n)) < 0.95f) {
      t = axisW * (axisW.y >= 0 ? 1.0f : -1.0f);
      t = glm::normalize(t - n * glm::dot(t, n));
      d = sgn * glm::cross(n, t);
      if (glm::dot(d, out) < 0) d = -d, t = -t;  // fingers never point back at the body
    } else {
      vec3 o = out - n * glm::dot(out, n);
      if (glm::length(o) < 1e-4f) o = glm::cross(n, std::abs(n.y) < 0.9f ? kUp : vec3(1, 0, 0));
      d = glm::normalize(o);
      t = sgn * glm::cross(d, n);
    }
    const mat3 W(d, n, glm::cross(d, n));
    const mat3 B(h.grip.fingerDir, h.grip.palmNormal, glm::cross(h.grip.fingerDir, h.grip.palmNormal));
    pl.R = W * glm::transpose(B);
    pl.orient = glm::normalize(glm::quat_cast(pl.R));
    pl.R = glm::mat3_cast(pl.orient);
    pl.wrist = pl.socket - pl.R * h.grip.palm;
    pl.inward = n;
    pl.centre = glm::transpose(pl.R) * (centreW - pl.wrist);
    pl.axis = glm::length(axisW) > 0 ? glm::transpose(pl.R) * axisW : vec3(0);
    return pl;
  };
  // Reach + grasp of `socket` on prop p, arriving at `contact` (shared by reach/grasp and the hand-over receiver).
  auto reachTo = [&](const Hand& h, int p, const std::string& socket, double start, double contact, bool grasp,
                     const std::string& what) -> Result<Plan> {
    if (contact < start + 6) return fail(std::format("{}: contact must be at least 6 frames after start", what));
    Plan pl = plan(h, p, socket, contact);
    const vec3 natural = boneAt(h, h.bone, start);
    const vec3 approach = pl.wrist - pl.inward * 0.05f + kUp * 0.02f;
    const double pre = contact - std::min(6.0, 0.4 * (contact - start));
    warnReach(h, pl.wrist, contact, what);
    key(gen, h.ik, start, clip.evaluate(h.ik + ".weight", start, vec3(0)).x > 0 ? clip.evaluate(h.ik, start, natural) : natural);
    key(gen, h.ik, pre, approach);
    key(gen, h.ik, contact, pl.wrist);
    key(gen, h.ik + ".weight", start, vec3(clip.evaluate(h.ik + ".weight", start, vec3(0)).x));
    key(gen, h.ik + ".weight", pre, vec3(1));
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, start, rotationVector(pl.orient), Interp::Linear);
    key(gen, h.orient, contact, rotationVector(pl.orient), Interp::Linear);
    key(gen, h.orient + ".weight", start, vec3(clip.evaluate(h.orient + ".weight", start, vec3(0)).x));
    key(gen, h.orient + ".weight", pre + 1, vec3(1));
    key(gen, h.orient + ".weight", contact, vec3(1));
    key(gen, h.pose, start, clip.evaluate(h.pose, start, kRelaxed));
    key(gen, h.pose, pre, kOpen);
    key(gen, h.pose, contact, kOpen);
    if (grasp) {  // fingers close on the prop's size by contact search (anim: applyHandPose)
      key(gen, h.pose + ".grasp", start, pl.centre, Interp::Step);
      key(gen, h.pose + ".graspRadius", start, vec3(pl.radius), Interp::Step);
      key(gen, h.pose + ".graspAxis", start, pl.axis, Interp::Step);
      key(gen, h.pose + ".grasp.weight", start, vec3(0));
      key(gen, h.pose + ".grasp.weight", contact - 4, vec3(0));
      key(gen, h.pose + ".grasp.weight", contact, vec3(1));
    }
    correct(h, contact, [&] { return socketWorld(p, socket, contact)[3] - vec4(handGripPoint(size_t(h.c), h.side, contact), 1); });
    return pl;
  };
  // Lets go: fingers open, the wrist backs away from the prop and the arm returns to its own animation by `end`.
  auto release = [&](const Hand& h, const quat& orient, double from, double end, vec3 retreat) {
    const vec3 wrist = clip.evaluate(h.ik, from, vec3(0));
    key(gen, h.pose + ".grasp.weight", from, vec3(1));
    key(gen, h.pose + ".grasp.weight", from + 5, vec3(0));
    key(gen, h.pose, from, kOpen);
    key(gen, h.pose, from + 3, kOpen);
    key(gen, h.pose, end, kRelaxed);
    key(gen, h.ik, from + 1, wrist);
    key(gen, h.ik, std::max(from + 6, end - 4), wrist + retreat);
    key(gen, h.ik, end, wrist + retreat);
    key(gen, h.ik + ".weight", from + 1, vec3(1));
    key(gen, h.ik + ".weight", end, vec3(0));
    key(gen, h.orient, end, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", from + 1, vec3(1));
    key(gen, h.orient + ".weight", end, vec3(0));
  };
  auto held = [&](const Hand& h, const std::string& what) -> Result<int> {
    auto it = ctx.hands.find({h.c, h.side});
    const int p = it == ctx.hands.end() ? -1 : it->second.prop;
    if (p < 0) return fail(std::format("{}: '{}' holds nothing in hand.{} at this point", what, h.who, h.side));
    if (a.contains("prop") && str(a, "prop") != scene_.props[size_t(p)].name)
      return fail(std::format("{}: '{}' holds '{}', not '{}'", what, h.who, scene_.props[size_t(p)].name, str(a, "prop")));
    return p;
  };

  if (!ctx.parentsChecked) {  // props are evaluated while compiling: their authored parents must resolve first
    for (const PropDesc& prop : scene_.props) {
      std::vector<PropParent> parents;
      if (prop.parent) parents.push_back(*prop.parent);
      for (const auto& sw : prop.parentSwitch)
        if (sw.parent) parents.push_back(*sw.parent);
      for (const PropParent& pp : parents) {
        const bool ok = pp.kind == PropParent::Kind::Character
                            ? charIndex(pp.name) >= 0 && characterSocketBone(size_t(charIndex(pp.name)), pp.socket) >= 0
                            : propIndex(pp.name) >= 0 && propAssets_[size_t(propIndex(pp.name))].sockets.count(pp.socket) > 0;
        if (!ok) return fail(std::format("prop '{}': parent '{}' socket '{}' does not resolve", prop.name, pp.name, pp.socket));
      }
    }
    ctx.parentsChecked = true;
  }
  const std::string who = str(a, "character");
  const int c = charIndex(who);
  if (c < 0) return fail(std::format("{}: unknown character '{}'", type, who));
  const double start = num(a, "start", num(a, "frame", 0));
  const bool look = flag(a, "look", true);
  auto h0 = handOf(c, sideOf(a, "hand"), type);
  if (!h0) return std::unexpected(h0.error());
  const Hand& h = *h0;

  if (reach) {
    const std::string what = std::format("{} '{}'", type, str(a, "prop"));
    const int p = propIndex(str(a, "prop"));
    if (p < 0) return fail(std::format("{}: unknown prop '{}'", type, str(a, "prop")));
    const std::string socket = str(a, "socket", "grip");
    if (auto r = requireSocket(p, socket, what); !r) return std::unexpected(r.error());
    if (auto it = ctx.hands.find({c, h.side}); it != ctx.hands.end() && it->second.prop >= 0)
      return fail(std::format("{}: '{}' already holds '{}' in hand.{}", what, who, scene_.props[size_t(it->second.prop)].name, h.side));
    const double contact = num(a, "contact", start + 14);
    const bool grasp = flag(a, "grasp", true);
    auto pl = reachTo(h, p, socket, start, contact, grasp, what);
    if (!pl) return std::unexpected(pl.error());
    ctx.contacts.push_back({c, h.side, contact, p, socket, false, vec3(0)});
    if (grasp) {
      if (auto r = addSwitch(p, contact, PropParent{PropParent::Kind::Character, who, std::string("hand.") + h.side}, what); !r)
        return std::unexpected(r.error());
      ctx.hands[{c, h.side}] = {p, pl->orient};
      if (look) gazeOn(h, p, start, contact + 8);
    } else {
      const double end = num(a, "end", contact + 12);
      key(gen, h.ik, contact + 2, clip.evaluate(h.ik, contact, vec3(0)));
      release(h, pl->orient, contact + 2, std::max(end, contact + 10), -pl->inward * 0.05f + kUp * 0.02f);
      if (look) {
        gazeOn(h, p, start, contact + 6);
        gazeAt(h, forwardPoint(h, end), end + 6);
      }
    }
    return true;
  }

  if (type == "hold") {
    auto p = held(h, "hold");
    if (!p) return std::unexpected(p.error());
    const double end = num(a, "end", start + 16);
    if (end <= start) return fail("hold: end must be after start");
    const quat orient = ctx.hands[{c, h.side}].orient;
    const vec3 origin = vec3(propWorld(size_t(*p), start)[3]);
    const auto at = vecOpt(a, "at"), by = vecOpt(a, "by");
    const vec3 target = at ? *at : origin + (by ? *by : vec3(0));
    const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, end, wrist + (target - origin));
    key(gen, h.ik + ".weight", end, vec3(1));
    key(gen, h.orient, end, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", end, vec3(1));
    warnReach(h, wrist + (target - origin), end, "hold");
    correct(h, end, [&] { return target - vec3(propWorld(size_t(*p), end)[3]); });
    if (look) gazeOn(h, *p, start, end);
    return true;
  }

  if (type == "place") {
    auto p = held(h, "place");
    if (!p) return std::unexpected(p.error());
    const std::string socket = str(a, "socket", "place");
    if (auto r = requireSocket(*p, socket, "place"); !r) return std::unexpected(r.error());
    const double contact = num(a, "contact", start + 16), end = num(a, "end", contact + 14);
    if (contact < start + 6 || end < contact + 8) return fail("place: needs contact >= start + 6 and end >= contact + 8");
    std::optional<PropParent> onto;
    vec3 target(0);
    if (auto it = a.find("onto"); it != a.end() && it->is_object()) {
      const int q = propIndex(str(*it, "prop"));
      const std::string s = str(*it, "socket", "place");
      if (q < 0) return fail(std::format("place: unknown prop '{}' in onto", str(*it, "prop")));
      if (auto r = requireSocket(q, s, "place onto"); !r) return std::unexpected(r.error());
      onto = PropParent{PropParent::Kind::Prop, scene_.props[size_t(q)].name, s};
      target = vec3(socketWorld(q, s, contact)[3]);
    } else if (auto at = vecOpt(a, "at")) {
      target = *at;
    } else {
      return fail("place: give 'at' [x,y,z] or 'onto' {prop, socket}");
    }
    const quat orient = ctx.hands[{c, h.side}].orient;
    const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
    const vec3 wristC = wrist + (target - vec3(socketWorld(*p, socket, start)[3]));
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, contact - 5, wristC + kUp * 0.03f);
    key(gen, h.ik, contact, wristC);
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, contact, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", contact, vec3(1));
    warnReach(h, wristC, contact, "place");
    correct(h, contact, [&] { return target - vec3(socketWorld(*p, socket, contact)[3]); });
    if (auto r = addSwitch(*p, contact, onto, "place"); !r) return std::unexpected(r.error());
    ctx.contacts.push_back({c, h.side, contact, *p, socket, true, target});
    ctx.hands[{c, h.side}].prop = -1;
    release(h, orient, contact, end, -(glm::mat3_cast(orient) * h.grip.palmNormal) * 0.05f + kUp * 0.03f);
    if (look) {
      gazeOn(h, *p, start, contact + 6);
      gazeAt(h, forwardPoint(h, end), end + 6);
    }
    return true;
  }

  // handover
  const std::string to = str(a, "to");
  const int rc = charIndex(to);
  if (rc < 0) return fail(std::format("handover: unknown receiver '{}'", to));
  auto r0 = handOf(rc, sideOf(a, "toHand"), "handover");
  if (!r0) return std::unexpected(r0.error());
  const Hand& r = *r0;
  if (rc == c && r.side == h.side) return fail("handover: the receiving hand is the giving hand");
  auto p = held(h, "handover");
  if (!p) return std::unexpected(p.error());
  if (auto it = ctx.hands.find({rc, r.side}); it != ctx.hands.end() && it->second.prop >= 0)
    return fail(std::format("handover: '{}' already holds '{}' in hand.{}", to, scene_.props[size_t(it->second.prop)].name, r.side));
  const std::string toSocket = str(a, "toSocket", "grip_b");
  if (auto rs = requireSocket(*p, toSocket, "handover"); !rs) return std::unexpected(rs.error());
  const double contact = num(a, "contact", start + 18), rStart = num(a, "receiverStart", start + 4);
  const double rel = num(a, "release", contact + 4), end = num(a, "end", rel + 12);
  if (contact < start + 6 || contact < rStart + 6 || rel < contact + 1 || end < rel + 8)
    return fail("handover: needs contact >= start + 6, contact >= receiverStart + 6, release > contact, end >= release + 8");
  // Giver: brings the prop to the meeting point a little before contact and holds it still until it lets go.
  const quat gOrient = ctx.hands[{c, h.side}].orient;
  const vec3 origin = vec3(propWorld(size_t(*p), start)[3]);
  vec3 meet;
  if (auto at = vecOpt(a, "at")) {
    meet = *at;
  } else {
    meet = 0.5f * (boneAt(h, h.root, contact) + boneAt(r, r.root, contact)) - kUp * (0.35f * h.armLength);
  }
  const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
  const double still = contact - std::min(4.0, 0.3 * (contact - start));
  const std::string what = std::format("handover '{}' to '{}'", scene_.props[size_t(*p)].name, to);
  vec3 wristM(0);
  // Giver brings the prop to `meet` and holds it still; the receiver reaches its socket there (compiled together,
  // so the meeting point can move).
  auto meetAt = [&](vec3 m) -> Result<Plan> {
    wristM = wrist + (m - origin);
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, still, wristM);
    key(gen, h.ik, contact, wristM);
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, contact, rotationVector(gOrient), Interp::Linear);
    key(gen, h.orient + ".weight", contact, vec3(1));
    correct(h, still, [&] { return m - vec3(propWorld(size_t(*p), still)[3]); });
    for (auto& k : gen.tracks[h.ik].keys)  // still means still: contact repeats the corrected meeting key
      if (std::abs(k.frame - contact) < 1e-6) k.value = clip.evaluate(h.ik, still, wristM);
    return reachTo(r, *p, toSocket, rStart, contact, true, what);
  };
  // T-030: the meeting point must leave both arms (forearm and hand surface) outside their own bodies and within
  // both reaches. Candidates on a grid around the requested point (3 cm steps, then 1 cm steps around the best); the
  // closest one that keeps both arms at the margin wins, else the one with the largest clearance (the depth left is
  // reported).
  auto shortfall = [&](const Hand& x, vec3 target) {
    return glm::distance(boneAt(x, x.root, contact), target) - 0.98f * x.armLength;
  };
  auto score = [&](vec3 m) -> Result<float> {
    auto pl = meetAt(m);
    if (!pl) return std::unexpected(pl.error());
    const float sg = shortfall(h, wristM), sr = shortfall(r, pl->wrist);
    if (std::max(sg, sr) > 0.003f) return -1.0f - std::max(sg, sr);  // out of reach: never chosen over a reachable point
    const float g = armClearance(clearance_[size_t(c)], characterGlobals(size_t(c), contact), h.side).gap;
    const float q = armClearance(clearance_[size_t(rc)], characterGlobals(size_t(rc), contact), r.side).gap;
    return std::min(g, q);
  };
  const bool canClear = c < int(clearance_.size()) && rc < int(clearance_.size()) && clearance_[size_t(c)].valid &&
                        clearance_[size_t(rc)].valid;
  if (canClear) {
    const size_t warningsBefore = warnings_.size();  // trial reaches report nothing
    if (auto pl = meetAt(meet); !pl) return std::unexpected(pl.error());
    writeArmPole(gen, size_t(c), h.side);  // poles first: the elbows they set are part of the clearance
    writeArmPole(gen, size_t(rc), r.side);
    const vec3 across = glm::normalize(vec3(boneAt(r, r.root, contact) - boneAt(h, h.root, contact)) * vec3(1, 0, 1));
    const vec3 side = glm::cross(kUp, across);
    const vec3 asked = meet;
    vec3 best = asked;
    float bestScore = -1e9f, bestDist = 1e9f;
    auto consider = [&](vec3 m) -> Result<void> {
      auto sc = score(m);
      if (!sc) return std::unexpected(sc.error());
      const float d = glm::distance(m, asked);
      const bool clear = *sc >= kArmBodyMargin - 0.0005f, bestClear = bestScore >= kArmBodyMargin - 0.0005f;
      if ((clear && (!bestClear || d < bestDist)) || (!clear && !bestClear && *sc > bestScore))
        best = m, bestScore = *sc, bestDist = d;
      return {};
    };
    for (int i = -4; i <= 4; ++i)  // coarse: 3 cm steps, +-12 cm across and sideways, +-9 cm up and down
      for (int j = -4; j <= 4; ++j)
        for (int k = -3; k <= 3; ++k)
          if (auto e = consider(asked + across * (0.03f * float(i)) + side * (0.03f * float(j)) + kUp * (0.03f * float(k))); !e)
            return std::unexpected(e.error());
    const vec3 coarse = best;
    for (int i = -2; i <= 2; ++i)  // fine: 1 cm steps around the best coarse point
      for (int j = -2; j <= 2; ++j)
        for (int k = -2; k <= 2; ++k)
          if (auto e = consider(coarse + across * (0.01f * float(i)) + side * (0.01f * float(j)) + kUp * (0.01f * float(k))); !e)
            return std::unexpected(e.error());
    meet = best;
    warnings_.resize(warningsBefore);
    if (bestScore < 0)
      warnings_.push_back(std::format("{}: no meeting point keeps both arms outside the bodies ({:.0f} mm inside); move them apart",
                                      what, -bestScore * 1000));
  }
  auto pl = meetAt(meet);
  if (!pl) return std::unexpected(pl.error());
  warnReach(h, wristM, contact, "handover (giver)");
  ctx.frozen.push_back({c, h.side, still, rel});  // the giver holds still: the clearance pass leaves it there
  if (auto rs = addSwitch(*p, contact, PropParent{PropParent::Kind::Character, to, std::string("hand.") + r.side}, what); !rs)
    return std::unexpected(rs.error());
  ctx.contacts.push_back({rc, r.side, contact, *p, toSocket, false, vec3(0)});
  ctx.hands[{rc, r.side}] = {*p, pl->orient};
  ctx.hands[{c, h.side}].prop = -1;
  // Giver lets go after the receiver holds it and draws the hand back towards its own shoulder.
  key(gen, h.ik, rel, clip.evaluate(h.ik, contact, wristM));
  key(gen, h.ik + ".weight", rel, vec3(1));
  key(gen, h.orient, rel, rotationVector(gOrient), Interp::Linear);
  key(gen, h.orient + ".weight", rel, vec3(1));
  const vec3 back = boneAt(h, h.root, rel) - wristM;
  release(h, gOrient, rel, end, glm::normalize(back) * 0.08f - (glm::mat3_cast(gOrient) * h.grip.palmNormal) * 0.03f);
  if (look) {
    gazeOn(h, *p, start, rel);
    gazeAt(h, headPoint(rc, end), end);
    gazeOn(r, *p, rStart, contact + 8);
  }
  return true;
}

void SceneEvaluator::buildClearanceModels() {
  clearance_.clear();
  for (const auto& ci : characters_) clearance_.push_back(bodyClearanceModel(ci.asset.skeleton, ci.rig.meshes));
}

// Elbow pole of an IK-driven arm, per frame over the scene: out of the body (the character's side, down and a little
// back, in the chest frame), weighted by the arm's IK weight so it fades with the IK and leaves the clip arm alone.
void SceneEvaluator::writeArmPole(Clip& gen, size_t c, char side) {
  const Skeleton& sk = characters_[c].asset.skeleton;
  const int hand = characterSocketBone(c, std::string("hand.") + side), chest = sk.find("chest");
  if (hand < 0 || chest < 0) return;
  const std::string who = scene_.characters[c].name, ik = who + "/ik." + sk.bones[size_t(hand)].name;
  const std::string pole = who + "/pole." + sk.bones[size_t(hand)].name;
  if (!gen.find(ik)) return;
  const float out = side == 'L' ? 1.0f : -1.0f;  // engine +X is the character's left
  gen.tracks.erase(pole);
  gen.tracks.erase(pole + ".weight");  // the chest frame below is the pose without this arm's pole
  std::vector<Key> dir, wt;
  for (int f = scene_.frameStart - 1; f <= scene_.frameEnd + 1; ++f) {
    const mat4 Gc = characterGlobals(c, f)[size_t(chest)];
    const vec3 X = glm::normalize(vec3(Gc[0])), Y = glm::normalize(vec3(Gc[1])), Z = glm::normalize(vec3(Gc[2]));
    dir.push_back({double(f), glm::normalize(out * 0.8f * X - 1.0f * Y - 0.25f * Z), Interp::Linear});
    wt.push_back({double(f), vec3(std::clamp(scene_.animation.evaluate(ik + ".weight", f, vec3(1)).x, 0.0f, 1.0f)), Interp::Linear});
  }
  gen.tracks[pole].keys = std::move(dir);
  gen.tracks[pole + ".weight"].keys = std::move(wt);
}

ArmClearance SceneEvaluator::armClearanceAt(size_t c, char side, double frame) const {
  if (c >= clearance_.size() || !clearance_[c].valid) return {};
  return armClearance(clearance_[c], characterGlobals(c, frame), side);
}

// For every arm driven by an IK track ("<who>/ik.<hand>"):
//  1. elbow pole: per frame, the elbow is swung (about the shoulder -> wrist axis, so the wrist does not move) to
//     point out of the body: the character's side, down and a little back in the chest frame. Its weight is the IK
//     weight, so it fades in and out with the IK and the clip arm is untouched;
//  2. wrist target: per frame, the target is pushed out of the body capsules along the gap gradient until hand,
//     forearm and the elbow half of the upper arm keep kArmBodyMargin (a few re-solves: the elbow moves with the
//     wrist); the per-frame pushes are then eased in time (cosine-weighted max over +-5 frames for the size, weighted
//     mean for the direction), so the correction starts before the arm gets close and never pops. Contact frames keep
//     their exact target (the push fades out over 4 frames towards a contact), and a contact inside the body is
//     reported. The IK track becomes per-frame keys only when some push is needed.
void SceneEvaluator::armClearancePass(Clip& gen, const InteractionContext& ctx) {
  const Clip& clip = scene_.animation;
  const int fs = scene_.frameStart, fe = scene_.frameEnd;
  if (clearance_.size() != characters_.size()) buildClearanceModels();
  for (size_t c = 0; c < characters_.size(); ++c) {
    const Skeleton& sk = characters_[c].asset.skeleton;
    if (!clearance_[c].valid) continue;
    const std::string who = scene_.characters[c].name;
    for (char side : {'L', 'R'}) {
      const ArmModel& A = clearance_[c].arm[side == 'L' ? 0 : 1];
      const std::string ik = who + "/ik." + sk.bones[size_t(A.hand)].name;
      auto it = gen.tracks.find(ik);
      if (it == gen.tracks.end() || it->second.keys.empty()) continue;
      auto weight = [&](double f) { return std::clamp(clip.evaluate(ik + ".weight", f, vec3(1)).x, 0.0f, 1.0f); };
      std::vector<double> contacts;
      for (const auto& k : ctx.contacts)
        if (size_t(k.character) == c && k.side == side) contacts.push_back(k.frame);
      // 1. pole
      const std::string pole = who + "/pole." + sk.bones[size_t(A.hand)].name;
      writeArmPole(gen, c, side);
      for (const auto& fz : ctx.frozen)
        if (size_t(fz.character) == c && fz.side == side) contacts.push_back(fz.from), contacts.push_back(fz.to);
      // 2. wrist target
      Track& T = gen.tracks[ik];
      const Track original = T;
      const int n = fe - fs + 3;
      std::vector<vec3> base(static_cast<size_t>(n)), raw(static_cast<size_t>(n), vec3(0));
      std::vector<float> w(static_cast<size_t>(n));
      for (int i = 0; i < n; ++i) base[size_t(i)] = original.evaluate(fs - 1 + i), w[size_t(i)] = weight(fs - 1 + i);
      auto setDense = [&](const std::vector<vec3>& push) {
        T.keys.clear();
        for (int i = 0; i < n; ++i) T.keys.push_back({double(fs - 1 + i), base[size_t(i)] + push[size_t(i)], Interp::Linear});
      };
      auto keyAt = [&](int f) -> Key& { return T.keys[size_t(f - (fs - 1))]; };
      // The clip arm's own gap per frame (IK and pole off): while the IK fades in or out the arm may rest as deep as
      // the clip puts it (a sleeve hanging against the side), never deeper; at full IK weight it keeps the margin.
      std::vector<float> idle(static_cast<size_t>(n), 1e9f);
      {
        const std::string wk = ik + ".weight", pk = pole + ".weight";
        const std::optional<Track> savedW = gen.tracks.count(wk) ? std::optional<Track>(gen.tracks[wk]) : std::nullopt;
        const Track savedP = gen.tracks[pk];
        gen.tracks[wk].keys = {{0.0, vec3(0), Interp::Step}};
        gen.tracks[pk].keys = {{0.0, vec3(0), Interp::Step}};
        for (int i = 0; i < n; ++i)
          if (w[size_t(i)] > 1e-3f) idle[size_t(i)] = armClearance(clearance_[c], characterGlobals(c, fs - 1 + i), side).gap;
        if (savedW) gen.tracks[wk] = *savedW;
        else gen.tracks.erase(wk);
        gen.tracks[pk] = savedP;
      }
      auto required = [&](int f) {
        const size_t i = size_t(f - (fs - 1));
        return std::min(kArmBodyMargin, w[i] * kArmBodyMargin + (1 - w[i]) * std::min(kArmBodyMargin, idle[i]));
      };
      // Pushes `f`'s key until the arm clears; returns the push added. Steps are capped (3 cm) so a point that follows
      // the wrist only partly (a sleeve) does not throw the hand away.
      auto clear = [&](int f, int iterations) {
        vec3 added(0);
        const float wf = w[size_t(f - (fs - 1))];
        if (wf <= 1e-3f) return added;
        const float req = required(f);
        for (int k = 0; k < iterations; ++k) {
          const ArmClearance s = armClearance(clearance_[c], characterGlobals(c, f), side);
          if (s.gap >= req - 0.0005f) break;
          vec3 step = s.push * ((req - s.gap) * 1.1f / (std::max(wf, 0.3f) * std::max(s.mobility, 0.5f)));
          if (glm::length(step) > 0.03f) step = glm::normalize(step) * 0.03f;
          keyAt(f).value += step;
          added += step;
        }
        return added;
      };
      auto gapAt = [&](int f) { return armClearance(clearance_[c], characterGlobals(c, f), side).gap; };
      setDense(raw);
      bool any = false;
      // Frame by frame, starting from the previous frame's push (coherent in time: the worst point or its direction
      // may change between frames, the push should not), then shrunk to the smallest quarter that still clears.
      vec3 prev(0);
      for (int f = fs; f <= fe; ++f) {
        const size_t i = size_t(f - (fs - 1));
        if (w[i] <= 1e-3f) {
          prev = vec3(0);
          continue;
        }
        keyAt(f).value = base[i] + prev;
        vec3 push = prev + clear(f, 12);
        const float req = required(f);
        for (float k : {0.0f, 0.25f, 0.5f, 0.75f}) {
          keyAt(f).value = base[i] + push * k;
          if (gapAt(f) >= req - 0.0005f) {
            push *= k;
            break;
          }
          keyAt(f).value = base[i] + push;
        }
        keyAt(f).value = base[i] + push;
        raw[i] = prev = push;
        any |= glm::length(push) > 1e-6f;
      }
      if (!any) {
        T = original;
        continue;
      }
      constexpr int R = 5;
      std::vector<vec3> eased(static_cast<size_t>(n), vec3(0));
      for (int i = 0; i < n; ++i) {
        float mag = 0;
        vec3 dir(0);
        for (int k = -R; k <= R; ++k) {
          const int j = i + k;
          if (j < 0 || j >= n) continue;
          const float cw = 0.5f * (1.0f + std::cos(glm::pi<float>() * float(k) / float(R + 1)));
          mag = std::max(mag, cw * glm::length(raw[size_t(j)]));
          dir += cw * raw[size_t(j)];
        }
        float fade = 1.0f;  // contact frames and held-still spans keep their exact target
        const double fi = double(fs - 1 + i);
        for (double cf : contacts) {
          const float d = float(std::abs(fi - cf));
          if (d < 4.0f) fade = std::min(fade, 0.5f - 0.5f * std::cos(glm::pi<float>() * d / 4.0f));
        }
        for (const auto& fz : ctx.frozen)
          if (size_t(fz.character) == c && fz.side == side && fi >= fz.from && fi <= fz.to) fade = 0;
        if (glm::length(dir) > 1e-9f) eased[size_t(i)] = glm::normalize(dir) * mag * fade;
      }
      setDense(eased);
      for (int f = fs; f <= fe; ++f) {  // residuals (direction mixing in the easing): small, local top-ups
        bool nearContact = false;
        for (double cf : contacts) nearContact |= std::abs(double(f) - cf) < 4.0;
        for (const auto& fz : ctx.frozen)
          nearContact |= size_t(fz.character) == c && fz.side == side && f >= fz.from - 4 && f <= fz.to + 4;
        if (!nearContact) clear(f, 4);
      }
    }
  }
}

Result<void> SceneEvaluator::finishInteractions(Clip& gen, InteractionContext& ctx) {
  armClearancePass(gen, ctx);
  // Later actions (clips, walks, other interactions) may change the body at an earlier contact: re-correct every
  // contact in time order, so each one is exact in the final animation.
  std::stable_sort(ctx.contacts.begin(), ctx.contacts.end(),
                   [](const InteractionContext::Contact& x, const InteractionContext::Contact& y) { return x.frame < y.frame; });
  for (const auto& k : ctx.contacts) {
    const int hb = characterSocketBone(size_t(k.character), std::string("hand.") + k.side);
    const std::string ik = scene_.characters[size_t(k.character)].name + "/ik." + characters_[size_t(k.character)].asset.skeleton.bones[size_t(hb)].name;
    auto measure = [&]() -> vec3 {
      const mat4 S = propWorld(size_t(k.prop), k.frame) * assetTransformMatrix(propAssets_[size_t(k.prop)].sockets.at(k.socket));
      if (k.placeTarget) return k.target - vec3(S[3]);
      return vec3(S[3]) - handGripPoint(size_t(k.character), k.side, k.frame);
    };
    const float e = correctKey(gen.tracks[ik], k.frame, measure);
    if (e > 0.005f)
      warnings_.push_back(std::format("interaction: '{}' hand.{} misses '{}' socket '{}' by {:.1f} mm at frame {} (out of reach?)",
                                      scene_.characters[size_t(k.character)].name, k.side, scene_.props[size_t(k.prop)].name,
                                      k.socket, e * 1000, k.frame));
  }
  // The final arms (after the contact corrections): an IK-driven arm inside the body is reported.
  for (size_t c = 0; c < clearance_.size(); ++c) {
    if (!clearance_[c].valid) continue;
    const std::string who = scene_.characters[c].name;
    for (char side : {'L', 'R'}) {
      const std::string ik = who + "/ik." + characters_[c].asset.skeleton.bones[size_t(clearance_[c].arm[side == 'L' ? 0 : 1].hand)].name;
      if (!gen.find(ik)) continue;
      float worst = 1e9f;
      double at = 0;
      for (int f = scene_.frameStart; f <= scene_.frameEnd; ++f) {  // full IK weight: the margin is required
        if (scene_.animation.evaluate(ik + ".weight", f, vec3(1)).x < 0.99f) continue;
        const float g = armClearanceAt(c, side, f).gap;
        if (g < worst) worst = g, at = f;
      }
      if (worst < 0)
        warnings_.push_back(std::format("interaction: '{}' arm {} passes {:.1f} mm into the body at frame {} (target inside the body?)",
                                        who, side, -worst * 1000, at));
    }
  }
  return {};
}

}  // namespace plush
