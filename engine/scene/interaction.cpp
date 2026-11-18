// Hand-prop interaction actions (see interaction.h). Compiled into generated tracks and prop parent switches by
// SceneEvaluator::compileActions (actions.cpp); evaluated by the ordinary pose path (IK, hand pose, look) plus the
// orientation constraint below, which scene.cpp applies after IK.
#include "scene/interaction.h"

#include <algorithm>
#include <format>
#include <functional>
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



vec3 skinPoint(const ArmPoint& P, const std::vector<mat4>& G) {
  vec3 p(0);
  for (int k = 0; k < 4; ++k)
    if (P.weight[k] > 0) p += P.weight[k] * vec3(G[size_t(P.joint[k])] * vec4(P.local[k], 1));
  return p;
}

}  // namespace

BodyClearanceModel bodyClearanceModel(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes, const Json& collisionBlock) {
  BodyClearanceModel M;
  M.collision = collisionBodyFor(collisionBlock, sk, meshes);
  if (!M.collision.valid) return M;
  M.body = M.collision.sections;
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
  // Skinned rest vertices of each arm (upper-arm and elbow samples are reported against the body, not planned).
  std::vector<int> region(sk.bones.size()), part(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) region[b] = int(regionOf(sk, int(b))), part[b] = int(armPartOf(sk, int(b)));
  size_t torsoCount = 0;
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
      if (w[int(Region::Torso)] >= 0.9f) ++torsoCount;
      for (int s = 0; s < 2; ++s)
        if (w[int(s == 0 ? Region::ArmL : Region::ArmR)] >= 0.5f && w[int(Region::Head)] + w[int(Region::Leg)] < 0.1f)
          armCand[s].push_back({&m, v});
    }
  }
  M.source = torsoCount >= 200 ? "mesh" : "skeleton";
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
      }
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

ArmClearance armClearance(const BodyClearanceModel& M, const std::vector<mat4>& G, char side) {
  ArmClearance out;
  if (!M.valid) return out;
  for (const ArmPoint& P : M.arm[side == 'L' ? 0 : 1].points) {  // upper arm and elbow: reported only
    if (P.part != 0) continue;
    const vec3 p = skinPoint(P, G);
    for (const BodyCapsule& C : M.body) out.upperGap = std::min(out.upperGap, sectionGap(C, G[size_t(C.bone)], p, side).gap - P.allowance);
  }
  const Clearance c = limbClearance(M.collision, G, side);
  out.gap = out.rawGap = c.gap;
  out.push = c.push;
  out.point = c.point;
  out.part = c.part.substr(0, c.part.find('.'));
  out.against = c.against;
  out.mobility = out.part == "hand" ? 1.0f : 0.6f;
  return out;
}

void applyArmPoles(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                   Pose& pose) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    const std::string name = prefix + "pole." + sk.bones[i].name, swingName = prefix + "swing." + sk.bones[i].name;
    const Track* t = clip.find(name);
    const Track* sw = clip.find(swingName);
    const bool hasPole = t && !t->keys.empty(), hasSwing = sw && !sw->keys.empty();
    if (!hasPole && !hasSwing) continue;
    const int mid = sk.bones[i].parent, root = mid >= 0 ? sk.bones[size_t(mid)].parent : -1;
    if (root < 0) continue;
    // Swings the upper arm by `angle` about the shoulder -> wrist axis; only the elbow moves: the hand keeps its world
    // rotation (the forearm's swing is taken out of the hand's local).
    auto swing = [&](auto angleOf) {
      const std::vector<mat4> G = boneGlobals(sk, pose, world);
      const vec3 a(G[size_t(root)][3]), b(G[size_t(mid)][3]), c(G[i][3]);
      if (glm::length(c - a) < 1e-5f) return;
      const vec3 u = glm::normalize(c - a);
      const float angle = angleOf(a, b, u);
      if (angle == 0.0f) return;
      const quat R = glm::angleAxis(angle, u);
      const int parent = sk.bones[size_t(root)].parent;
      const mat4 pg = parent >= 0 ? G[size_t(parent)] : world;
      const quat parentRot = glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(pg[0])), glm::normalize(vec3(pg[1])),
                                                                glm::normalize(vec3(pg[2])))));
      const quat handBefore = glm::normalize(glm::quat_cast(mat3(G[i])));
      pose.local[size_t(root)] = glm::normalize(glm::inverse(parentRot) * R * parentRot * pose.local[size_t(root)]);
      const quat midAfter = glm::normalize(glm::quat_cast(mat3(boneGlobals(sk, pose, world)[size_t(mid)])));
      pose.local[i] = glm::normalize(glm::inverse(midAfter) * handBefore);
    };
    if (hasPole) {
      const float w = std::clamp(clip.evaluate(name + ".weight", frame, vec3(1)).x, 0.0f, 1.0f);
      if (w > 0)
        swing([&](vec3 a, vec3 b, vec3 u) {
          const vec3 pole = t->evaluate(frame);
          vec3 e = (b - a) - u * glm::dot(b - a, u), p = pole - u * glm::dot(pole, u);
          const float le = glm::length(e), lp = glm::length(p), lpole = glm::length(pole);
          if (le < 1e-5f || lp < 1e-6f || lpole < 1e-6f) return 0.0f;
          e /= le;
          p /= lp;
          // A pole nearly along the arm has no meaningful plane: fade out instead of flipping.
          const float strength = std::clamp((lp / lpole) / 0.3f, 0.0f, 1.0f);
          return std::atan2(glm::dot(glm::cross(e, p), u), glm::dot(e, p)) * w * strength;
        });
    }
    if (hasSwing) swing([&](vec3, vec3, vec3) { return sw->evaluate(frame).x; });  // planned elbow swing (T-047)
  }
  // Planned arm lift (T-047): "<prefix>abduct.<hand bone>" rotates the whole arm about its shoulder by a rotation
  // vector given in the chest frame (so it moves with the body); the hand turns with it.
  const int chest = sk.find("chest");
  for (size_t i = 0; i < sk.bones.size() && chest >= 0; ++i) {
    const Track* t = clip.find(prefix + "abduct." + sk.bones[i].name);
    if (!t || t->keys.empty()) continue;
    const vec3 v = t->evaluate(frame);
    const int mid = sk.bones[i].parent, root = mid >= 0 ? sk.bones[size_t(mid)].parent : -1;
    if (root < 0 || glm::length(v) < 1e-7f) continue;
    const std::vector<mat4> G = boneGlobals(sk, pose, world);
    auto rotOf = [](const mat4& M) {
      return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(M[0])), glm::normalize(vec3(M[1])), glm::normalize(vec3(M[2])))));
    };
    const quat chestRot = rotOf(G[size_t(chest)]);
    const quat R = chestRot * fromRotationVector(v) * glm::inverse(chestRot);
    const int parent = sk.bones[size_t(root)].parent;
    const quat parentRot = rotOf(parent >= 0 ? G[size_t(parent)] : world);
    pose.local[size_t(root)] = glm::normalize(glm::inverse(parentRot) * R * parentRot * pose.local[size_t(root)]);
  }
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
    // each arm with the elbow swing the planner will give it (writeArmPole): the wrist and hand cannot move here
    const float g = swungArmGap(clearance_[size_t(c)], characterGlobals(size_t(c), contact), h.side);
    const float q = swungArmGap(clearance_[size_t(rc)], characterGlobals(size_t(rc), contact), r.side);
    return std::min(g, q);
  };
  const bool canClear = c < int(clearance_.size()) && rc < int(clearance_.size()) && clearance_[size_t(c)].valid &&
                        clearance_[size_t(rc)].valid;
  if (canClear) {
    const size_t warningsBefore = warnings_.size();  // trial reaches report nothing
    // Scored on the pose as it plays back (with the automatic base idle, see finishInteractions).
    const bool idleNotPrepared = autoIdle_.empty();
    if (idleNotPrepared) prepareAutoIdle();
    struct Restore {
      SceneEvaluator* ev;
      bool clear;
      ~Restore() {
        if (clear) ev->autoIdle_.clear();
      }
    } restore{this, idleNotPrepared};
    if (auto pl = meetAt(meet); !pl) return std::unexpected(pl.error());
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
  for (size_t c = 0; c < characters_.size(); ++c) {
    const auto& ci = characters_[c];
    if (ci.asset.collisionBlock.is_object())  // a package block that does not fit the skeleton: derived instead, said once
      if (auto b = collisionBodyFromJson(ci.asset.collisionBlock, ci.asset.skeleton); !b)
        warnings_.push_back(std::format("character '{}': {} (collision body derived from the meshes instead)",
                                        c < scene_.characters.size() ? scene_.characters[c].name : ci.asset.name, b.error().message));
    clearance_.push_back(bodyClearanceModel(ci.asset.skeleton, ci.rig.meshes, ci.asset.collisionBlock));
  }
}

// Planned elbow swing (T-047; replaces T-030's fixed outward pole): per frame, the smallest swing of the elbow about
// the shoulder -> wrist axis (the wrist, the hand and a held prop stay) that keeps the forearm capsule outside the
// collision body, measured on the pose as it is (clip, IK and every other layer). Frames where the arm is clear get
// no swing, so a clear clip or IK arm is unchanged. The required margin follows the IK weight: kArmBodyMargin at full
// IK, contact-but-not-inside (0) for a clip arm. One swing direction per contiguous span (the one needing the smaller
// angle), then the smallest envelope above the need whose rate is at most kSwingRate per frame: the elbow starts
// moving before the forearm gets close and never steps. The swing never exceeds the character's limit
// (CollisionBody::maxElbowSwing, T-082): the elbow stays low and the arm calm; what the limited swing cannot clear
// is left to the hand-over point choice and the wrist push (armClearancePass).
namespace {
constexpr float kSwingRate = 0.02618f;  // 1.5 deg per frame
constexpr float kSwingMax = 2.1f;      // 120 deg

// The forearm limb's clearance for globals G with the elbow swung by theta (forearm rotated about the shoulder ->
// wrist axis through the shoulder; the hand does not move).
float forearmGap(const CollisionBody& M, std::vector<mat4>& G, const mat4& fore0, int upper, int fore, int hand, char side, float theta) {
  const vec3 a(G[size_t(upper)][3]), w(G[size_t(hand)][3]);
  const vec3 u = glm::length(w - a) > 1e-6f ? glm::normalize(w - a) : vec3(0, -1, 0);
  G[size_t(fore)] = glm::translate(mat4(1), a) * glm::mat4_cast(glm::angleAxis(theta, u)) * glm::translate(mat4(1), -a) * fore0;
  float g = 1e9f;
  for (const CollisionLimb& l : M.limbs) {
    if (l.side != side || l.bone != fore) continue;
    vec3 p, q;
    limbSegment(l, G, p, q);
    g = std::min(g, segmentClearance(M, G, p, q, l.r, side).gap - l.allowance);
  }
  G[size_t(fore)] = fore0;
  return g;
}
// Smallest positive and negative swings up to `limit` (<= kSwingMax) that reach `need` (out: +-kSwingMax * 1.5
// marks "none reaches it"; then `best` is the angle within the limit with the largest gap).
struct SwingNeed {
  float pos = 0, neg = 0, best = 0;
  bool needed = false, reachable = true;
};
SwingNeed swingNeed(const CollisionBody& M, std::vector<mat4> G, int upper, int fore, int hand, char side, float need, float limit) {
  const float maxAngle = std::clamp(limit, 0.0f, kSwingMax);
  SwingNeed out;
  const mat4 fore0 = G[size_t(fore)];
  float bestGap = forearmGap(M, G, fore0, upper, fore, hand, side, 0);
  if (bestGap >= need) return out;
  out.needed = true;
  out.pos = out.neg = 1.5f * kSwingMax;
  constexpr float step = 0.0218f;  // 1.25 deg
  const int steps = maxAngle > 0 ? int(std::ceil(maxAngle / step - 1e-4f)) : 0;  // the last step lands on the limit
  for (int k = 1; k <= steps; ++k) {
    const float t = std::min(float(k) * step, maxAngle);
    for (float sgn : {1.0f, -1.0f}) {
      float& slot = sgn > 0 ? out.pos : out.neg;
      if (slot <= kSwingMax) continue;  // found already
      const float g = forearmGap(M, G, fore0, upper, fore, hand, side, sgn * t);
      if (g >= need) slot = t;
      if (g > bestGap) bestGap = g, out.best = sgn * t;
    }
    if (out.pos <= kSwingMax && out.neg <= kSwingMax) break;
  }
  out.reachable = out.pos <= kSwingMax || out.neg <= kSwingMax;
  return out;
}
}  // namespace

// Clearance of an arm for globals G after the best elbow swing up to `limit` (planning scores: the swing is planned
// later for the final motion, so a candidate is judged with the swing it will get). The hand-over point is scored
// with the full range (limit < 0: kSwingMax, as in T-047): a point the full swing would clear is one the limited
// swing, the wrist push and the torso turn clear together, and the receiver's reach stays as T-047 planned it.
float swungArmGap(const BodyClearanceModel& model, const std::vector<mat4>& G, char side, float limit) {
  if (!model.valid) return 1e9f;
  const ArmModel& A = model.arm[side == 'L' ? 0 : 1];
  const SwingNeed n = swingNeed(model.collision, G, A.upper, A.fore, A.hand, side, kArmBodyMargin + 0.0005f, limit < 0 ? kSwingMax : limit);
  float theta = 0;
  if (n.needed) theta = !n.reachable ? n.best : n.pos <= n.neg ? n.pos : -n.neg;
  std::vector<mat4> H = G;
  const vec3 a(H[size_t(A.upper)][3]), w(H[size_t(A.hand)][3]);
  const vec3 u = glm::length(w - a) > 1e-6f ? glm::normalize(w - a) : vec3(0, -1, 0);
  H[size_t(A.fore)] = glm::translate(mat4(1), a) * glm::mat4_cast(glm::angleAxis(theta, u)) * glm::translate(mat4(1), -a) * H[size_t(A.fore)];
  return limbClearance(model.collision, H, side).gap;
}

void SceneEvaluator::writeArmPole(Clip& gen, size_t c, char side) {
  if (c >= clearance_.size() || !clearance_[c].valid) return;
  const BodyClearanceModel& M = clearance_[c];
  const ArmModel& A = M.arm[side == 'L' ? 0 : 1];
  const Skeleton& sk = characters_[c].asset.skeleton;
  const std::string who = scene_.characters[c].name, bone = sk.bones[size_t(A.hand)].name;
  const std::string ik = who + "/ik." + bone, swingTrack = who + "/swing." + bone, pole = who + "/pole." + bone;
  gen.tracks.erase(swingTrack);  // the need is measured on the pose without this arm's swing
  gen.tracks.erase(pole);
  gen.tracks.erase(pole + ".weight");
  const int fs = scene_.frameStart - 1, n = scene_.frameEnd - scene_.frameStart + 3;
  std::vector<float> v(static_cast<size_t>(n), 0.0f);
  std::vector<SwingNeed> need(static_cast<size_t>(n));
  bool any = false;
  for (int i = 0; i < n; ++i) {
    const double f = double(fs + i);
    const Track* t = scene_.animation.find(ik);
    const float w = t && !t->keys.empty() ? std::clamp(scene_.animation.evaluate(ik + ".weight", f, vec3(1)).x, 0.0f, 1.0f) : 0.0f;
    const std::vector<mat4> G = characterGlobals(c, f);
    need[size_t(i)] = swingNeed(M.collision, G, A.upper, A.fore, A.hand, side, w * (kArmBodyMargin + 0.0005f), M.collision.maxElbowSwing);
    // Beyond the limit (T-082) the swing only goes as far as keeping the forearm out of the body (contact, not the
    // margin): the last resort once the hand-over point, the wrist push and the torso turn have done what they can.
    if (const SwingNeed& s = need[size_t(i)]; s.needed && !s.reachable && w > 0) {
      const SwingNeed out = swingNeed(M.collision, G, A.upper, A.fore, A.hand, side, 0.0005f, kSwingMax);
      if (out.reachable && std::min(out.pos, out.neg) > M.collision.maxElbowSwing) need[size_t(i)] = out;
    }
    any |= need[size_t(i)].needed;
  }
  if (!any) return;
  // One direction per contiguous span of frames that need a swing: the one with the smaller largest angle.
  for (int i = 0; i < n;) {
    if (!need[size_t(i)].needed) {
      ++i;
      continue;
    }
    int j = i;
    float maxPos = 0, maxNeg = 0;
    for (; j < n && need[size_t(j)].needed; ++j) {
      const SwingNeed& s = need[size_t(j)];
      maxPos = std::max(maxPos, s.reachable ? s.pos : (s.best > 0 ? std::abs(s.best) : 1.5f * kSwingMax));
      maxNeg = std::max(maxNeg, s.reachable ? s.neg : (s.best < 0 ? std::abs(s.best) : 1.5f * kSwingMax));
    }
    const float sgn = maxPos <= maxNeg ? 1.0f : -1.0f;
    for (int k = i; k < j; ++k) {
      const SwingNeed& s = need[size_t(k)];
      const float mag = sgn > 0 ? s.pos : s.neg;
      v[size_t(k)] = sgn * std::min(mag, kSwingMax);
      if (!s.reachable) v[size_t(k)] = (s.best * sgn > 0) ? s.best : 0.0f;  // best effort, reported by the final check
    }
    i = j;
  }
  // Rate-limited envelope per direction: env(f) = max_k(|v(k)| - kSwingRate |f - k|).
  std::vector<float> out(static_cast<size_t>(n), 0.0f);
  for (float sgn : {1.0f, -1.0f}) {
    std::vector<float> e(static_cast<size_t>(n), 0.0f);
    for (int i = 0; i < n; ++i) e[size_t(i)] = std::max(0.0f, sgn * v[size_t(i)]);
    for (int i = 1; i < n; ++i) e[size_t(i)] = std::max(e[size_t(i)], e[size_t(i - 1)] - kSwingRate);
    for (int i = n - 2; i >= 0; --i) e[size_t(i)] = std::max(e[size_t(i)], e[size_t(i + 1)] - kSwingRate);
    for (int i = 0; i < n; ++i) out[size_t(i)] += sgn * e[size_t(i)];
  }
  std::vector<Key> keys;
  for (int i = 0; i < n; ++i) keys.push_back({double(fs + i), vec3(out[size_t(i)], 0, 0), Interp::Linear});
  gen.tracks[swingTrack].keys = std::move(keys);
}

ArmClearance SceneEvaluator::armClearanceAt(size_t c, char side, double frame) const {
  if (c >= clearance_.size() || !clearance_[c].valid) return {};
  return armClearance(clearance_[c], characterGlobals(c, frame), side);
}

// Planned arm lift for the clip part of an arm (T-047): a clip arm (or the clip share of an arm whose IK is fading)
// whose forearm or hand capsule would enter the collision body is turned about its shoulder, away from the body along
// the gap gradient, just as much as it needs to touch at most. Per frame the smallest such rotation is found (the
// arm is rigid: the hand turns with it); its size is then the smallest envelope above the need whose rate is at most
// kSwingRate per frame, its direction the need-weighted mean of the frames that shape the envelope. Written as
// "<who>/abduct.<hand>" (rotation vector in the chest frame) only when some frame needs it. IK frames (weight 1) need
// nothing here: the wrist push and the swing handle them.
void planArmLift(const BodyClearanceModel& M, char side, int fs, int fe, const std::function<std::vector<mat4>(double)>& globalsAt,
                 const std::function<float(double)>& ikWeight, const std::string& trackName, Clip& gen) {
  const ArmModel& A = M.arm[side == 'L' ? 0 : 1];
  const int n = fe - fs + 3;
  std::vector<vec3> need(static_cast<size_t>(n), vec3(0));  // chest-frame rotation vectors
  bool any = false;
  auto rotOf = [](const mat4& Mx) {
    return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(Mx[0])), glm::normalize(vec3(Mx[1])), glm::normalize(vec3(Mx[2])))));
  };
  int chest = -1;
  for (const CollisionSection& sct : M.collision.sections)
    if (sct.name.rfind("torso_upper", 0) == 0) chest = sct.bone;
  if (chest < 0) return;
  for (int i = 0; i < n; ++i) {
    const double f = double(fs - 1 + i);
    if (ikWeight(f) >= 0.999f) continue;
    const std::vector<mat4> G = globalsAt(f);
    const Clearance c0 = limbClearance(M.collision, G, side);
    constexpr float need0 = 0.001f;  // a clip arm may touch the body, never enter it (1 mm numerical headroom)
    if (c0.gap >= need0) continue;
    // Rotate the arm rigidly about the shoulder: every bone below the upper arm (forearm, hand, fingers) moves with it.
    const vec3 S(G[size_t(A.upper)][3]);
    const vec3 lever = c0.point - S;
    vec3 axis = glm::cross(lever, c0.push);
    if (glm::length(axis) < 1e-6f) continue;
    axis = glm::normalize(axis);
    auto rotated = [&](float ang) {
      std::vector<mat4> H = G;
      const mat4 R = glm::translate(mat4(1), S) * glm::mat4_cast(glm::angleAxis(ang, axis)) * glm::translate(mat4(1), -S);
      for (const CollisionLimb& l : M.collision.limbs)
        if (l.side == side) H[size_t(l.bone)] = R * G[size_t(l.bone)];
      return limbClearance(M.collision, H, side).gap;
    };
    float ang = 0;
    for (float a = 0.0087f; a <= 1.2f; a += 0.0087f)  // 0.5 deg steps up to ~70 deg
      if (rotated(a) >= need0) {
        ang = a;
        break;
      }
    if (ang == 0) ang = 1.2f;
    const quat cr = rotOf(G[size_t(chest)]);
    need[size_t(i)] = (glm::inverse(cr) * axis) * ang;
    any = true;
  }
  gen.tracks.erase(trackName);
  if (!any) return;
  std::vector<float> mag(static_cast<size_t>(n), 0.0f);
  for (int i = 0; i < n; ++i) mag[size_t(i)] = glm::length(need[size_t(i)]);
  std::vector<float> env = mag;
  for (int i = 1; i < n; ++i) env[size_t(i)] = std::max(env[size_t(i)], env[size_t(i - 1)] - kSwingRate);
  for (int i = n - 2; i >= 0; --i) env[size_t(i)] = std::max(env[size_t(i)], env[size_t(i + 1)] - kSwingRate);
  // Full-IK frames keep their wrist (the lift turns the arm after IK): the lift is 0 there and grows by at most
  // kSwingRate per frame away from them; the wrist push and the swing cover the IK ramps.
  std::vector<float> cap(static_cast<size_t>(n), 1e9f);
  for (int i = 0, last = -1000000; i < n; ++i) {
    if (ikWeight(double(fs - 1 + i)) >= 0.999f) last = i;
    cap[size_t(i)] = kSwingRate * float(i - last);
  }
  for (int i = n - 1, next = 1000000; i >= 0; --i) {
    if (ikWeight(double(fs - 1 + i)) >= 0.999f) next = i;
    cap[size_t(i)] = std::min(cap[size_t(i)], kSwingRate * float(next - i));
  }
  for (int i = 0; i < n; ++i) env[size_t(i)] = std::min(env[size_t(i)], cap[size_t(i)]);
  std::vector<Key> keys;
  for (int i = 0; i < n; ++i) {
    vec3 dir(0);
    for (int k = 0; k < n; ++k) {
      const float w = mag[size_t(k)] - kSwingRate * float(std::abs(i - k));
      if (w > 0 && mag[size_t(k)] > 0) dir += w * need[size_t(k)] / mag[size_t(k)];
    }
    const vec3 v = glm::length(dir) > 1e-9f ? glm::normalize(dir) * env[size_t(i)] : vec3(0);
    keys.push_back({double(fs - 1 + i), v, Interp::Linear});
  }
  gen.tracks[trackName].keys = std::move(keys);
}

// For every arm driven by an IK track ("<who>/ik.<hand>"), planned against the character's collision body (T-047):
//  1. elbow swing (writeArmPole): the elbow turns about the shoulder -> wrist axis just as much as the forearm needs to
//     stay outside, rate-limited; the wrist, the hand and a held prop do not move, so contacts and holds keep it;
//  2. wrist target: where the swing is not enough (the hand itself, or a forearm the swing cannot free) the target is
//     pushed out of the body along the gap gradient until hand and forearm keep kArmBodyMargin (a few re-solves);
//     the per-frame pushes are then eased in time (cosine-weighted max over +-5 frames for the size, weighted mean
//     for the direction), so the correction starts before the arm gets close and never pops. Contact frames keep
//     their exact target (the push fades out over 4 frames towards a contact; the swing still acts there), and a
//     contact inside the body is reported. The swing is then re-planned for the pushed path. The IK track becomes
//     per-frame keys only when some push is needed.
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
      const bool hasIk = it != gen.tracks.end() && !it->second.keys.empty();
      auto weight = [&](double f) {
        return hasIk ? std::clamp(clip.evaluate(ik + ".weight", f, vec3(1)).x, 0.0f, 1.0f) : 0.0f;
      };
      // 0. the clip part of the arm (planned on the pose without this lift)
      const std::string lift = who + "/abduct." + sk.bones[size_t(A.hand)].name;
      gen.tracks.erase(lift);
      planArmLift(clearance_[c], side, fs, fe, [&](double f) { return characterGlobals(c, f); }, weight, lift, gen);
      if (!hasIk) continue;
      std::vector<double> contacts;
      for (const auto& k : ctx.contacts)
        if (size_t(k.character) == c && k.side == side) contacts.push_back(k.frame);
      // 1. elbow swing (planned; wrist and hand stay)
      const std::string swing = who + "/swing." + sk.bones[size_t(A.hand)].name;
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
        const std::string wk = ik + ".weight";
        const std::optional<Track> savedW = gen.tracks.count(wk) ? std::optional<Track>(gen.tracks[wk]) : std::nullopt;
        const std::optional<Track> savedS = gen.tracks.count(swing) ? std::optional<Track>(gen.tracks[swing]) : std::nullopt;
        gen.tracks[wk].keys = {{0.0, vec3(0), Interp::Step}};
        gen.tracks.erase(swing);
        for (int i = 0; i < n; ++i)
          if (w[size_t(i)] > 1e-3f) idle[size_t(i)] = armClearance(clearance_[c], characterGlobals(c, fs - 1 + i), side).gap;
        if (savedW) gen.tracks[wk] = *savedW;
        else gen.tracks.erase(wk);
        if (savedS) gen.tracks[swing] = *savedS;
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
      // Easing (T-047): the push size is the smallest envelope above the per-frame need whose rate is at most
      // kPushRate per frame, capped near pinned frames (a contact, a held-still span) by kPushRate per frame of distance
      // to them, so it reaches 0 there; its direction is the need-weighted mean of the frames that shape the
      // envelope. The push therefore starts before the arm gets close and never steps.
      constexpr float kPushRate = 0.004f;  // metres per frame (about 1 degree of arm rotation)
      std::vector<float> cap(static_cast<size_t>(n), 1e9f);
      for (int i = 0; i < n; ++i) {
        const double fi = double(fs - 1 + i);
        for (double cf : contacts) cap[size_t(i)] = std::min(cap[size_t(i)], kPushRate * float(std::abs(fi - cf)));
        for (const auto& fz : ctx.frozen) {
          if (size_t(fz.character) != c || fz.side != side) continue;
          const double d = fi < fz.from ? fz.from - fi : fi > fz.to ? fi - fz.to : 0.0;
          cap[size_t(i)] = std::min(cap[size_t(i)], kPushRate * float(d));
        }
      }
      auto ease = [&](const std::vector<vec3>& need) {
        std::vector<float> mag(static_cast<size_t>(n)), env(static_cast<size_t>(n));
        for (int i = 0; i < n; ++i) env[size_t(i)] = mag[size_t(i)] = glm::length(need[size_t(i)]);
        for (int i = 1; i < n; ++i) env[size_t(i)] = std::max(env[size_t(i)], env[size_t(i - 1)] - kPushRate);
        for (int i = n - 2; i >= 0; --i) env[size_t(i)] = std::max(env[size_t(i)], env[size_t(i + 1)] - kPushRate);
        std::vector<vec3> out(static_cast<size_t>(n), vec3(0));
        for (int i = 0; i < n; ++i) {
          vec3 dir(0);
          for (int k = 0; k < n; ++k) {
            const float wk = mag[size_t(k)] - kPushRate * float(std::abs(i - k));
            if (wk > 0) dir += wk * need[size_t(k)] / mag[size_t(k)];
          }
          if (glm::length(dir) > 1e-9f) out[size_t(i)] = glm::normalize(dir) * std::min(env[size_t(i)], cap[size_t(i)]);
        }
        return out;
      };
      std::vector<vec3> push = ease(raw);
      setDense(push);
      writeArmPole(gen, c, side);  // the swing for the pushed wrist path
      // Refinement: frames still short of the requirement (direction mixing, the swing re-planned) get their deficit
      // added to the need and the whole push is eased again.
      for (int round = 0; round < 3; ++round) {
        std::vector<vec3> need = push;
        bool shortOf = false;
        for (int f = fs; f <= fe; ++f) {
          const size_t i = size_t(f - (fs - 1));
          if (cap[i] <= 0 || w[i] <= 1e-3f) continue;
          const vec3 added = clear(f, 6);
          keyAt(f).value = base[i] + push[i];
          if (glm::length(added) > 1e-5f) need[i] = push[i] + added, shortOf = true;
        }
        if (!shortOf) break;
        push = ease(need);
        setDense(push);
        writeArmPole(gen, c, side);
      }
      // The planned wrist push itself (world metres), for measurements; nothing evaluates it.
      std::vector<Key> pk;
      for (int i = 0; i < n; ++i) pk.push_back({double(fs - 1 + i), push[size_t(i)], Interp::Linear});
      gen.tracks[who + "/collision.push." + sk.bones[size_t(A.hand)].name].keys = std::move(pk);
      // 3. torso turn (T-082): frames the limited swing and the wrist push leave short (a held-still hand-over, where
      // the wrist may not move) get a small turn of the upper body about its own vertical axis, so the arm's shoulder
      // leads towards the hand (as a person turns into a hand-over at close range). Never a lean: leaning back away
      // from a held object reads wrong for every character reference. Per frame the smallest turn (kLeanStep steps up
      // to kLeanMax, either way) whose limited swing clears the arm; then, per span of such frames, one direction and
      // the smallest envelope above the needs with a rate of at most kLeanRate per frame. The IK keeps the wrists where
      // they are, so contacts and holds stay exact.
      if (const int spine = sk.find("spine"); spine >= 0) {
        constexpr float kLeanMax = 15.0f, kLeanStep = 0.25f, kLeanRate = 0.5f;  // degrees, degrees per frame
        const std::string leanTrack = who + "/spine.rot";
        const std::optional<Track> savedLean = gen.tracks.count(leanTrack) ? std::optional<Track>(gen.tracks[leanTrack]) : std::nullopt;
        const auto dp = characters_[c].asset.defaultPose.find("spine");
        const vec3 rest0 = dp == characters_[c].asset.defaultPose.end() ? vec3(0) : dp->second;
        std::vector<vec3> leanBase(static_cast<size_t>(n));
        for (int i = 0; i < n; ++i) leanBase[size_t(i)] = savedLean ? savedLean->evaluate(fs - 1 + i) : rest0;
        auto setLean = [&](const std::vector<vec3>& lean) {
          std::vector<Key> keys;
          for (int i = 0; i < n; ++i) keys.push_back({double(fs - 1 + i), leanBase[size_t(i)] + lean[size_t(i)], Interp::Linear});
          gen.tracks[leanTrack].keys = std::move(keys);
        };
        std::vector<vec3> lean(static_cast<size_t>(n), vec3(0)), needLean(static_cast<size_t>(n), vec3(0));
        bool anyLean = false;
        const std::optional<Track> savedS = gen.tracks.count(swing) ? std::optional<Track>(gen.tracks[swing]) : std::nullopt;
        for (int f = fs; f <= fe; ++f) {
          const size_t i = size_t(f - (fs - 1));
          if (w[i] <= 1e-3f || gapAt(f) >= required(f) - 0.0005f) continue;
          gen.tracks.erase(swing);  // the turn is judged with the swing it will get (limited), not the current one
          setLean(lean);
          const float req = required(f) - 0.0005f;
          float best = swungArmGap(clearance_[c], characterGlobals(c, f), side, clearance_[c].collision.maxElbowSwing);
          vec3 found(0), bestLean(0);
          // The turn (euler degrees about the spine's local Y), both ways; the smallest that clears wins, else the one
          // with the largest gap.
          for (float L = kLeanStep; L <= kLeanMax + 1e-4f && found == vec3(0); L += kLeanStep)
            for (float sgn : {1.0f, -1.0f}) {
              const vec3 e(0, sgn * L, 0);
              lean[i] = e;
              setLean(lean);
              const float g = swungArmGap(clearance_[c], characterGlobals(c, f), side, clearance_[c].collision.maxElbowSwing);
              if (g > best) best = g, bestLean = e;
              if (g >= req) {
                found = e;
                break;
              }
            }
          lean[i] = vec3(0);
          needLean[i] = found != vec3(0) ? found : bestLean;  // best effort; the final check reports what is left
          anyLean |= needLean[i] != vec3(0);
        }
        if (anyLean) {
          // One direction per contiguous span of frames that need a turn (the need-weighted mean, so the direction
          // never turns between frames); its size is the smallest envelope above the span's needs with a rate of at
          // most kLeanRate per frame.
          std::fill(lean.begin(), lean.end(), vec3(0));
          for (int i = 0; i < n;) {
            if (needLean[size_t(i)] == vec3(0)) {
              ++i;
              continue;
            }
            int j = i;
            vec3 dir(0);
            for (; j < n && needLean[size_t(j)] != vec3(0); ++j) dir += needLean[size_t(j)];
            if (glm::length(dir) > 1e-6f) {
              dir = glm::normalize(dir);
              std::vector<float> env(static_cast<size_t>(n), 0.0f);
              for (int k = i; k < j; ++k) env[size_t(k)] = std::max(0.0f, glm::dot(needLean[size_t(k)], dir));
              for (int k = 1; k < n; ++k) env[size_t(k)] = std::max(env[size_t(k)], env[size_t(k - 1)] - kLeanRate);
              for (int k = n - 2; k >= 0; --k) env[size_t(k)] = std::max(env[size_t(k)], env[size_t(k + 1)] - kLeanRate);
              for (int k = 0; k < n; ++k) lean[size_t(k)] += dir * env[size_t(k)];
            }
            i = j;
          }
          setLean(lean);
          // The planned turn itself (euler degrees), for measurements; nothing evaluates it.
          std::vector<Key> lk;
          for (int i = 0; i < n; ++i) lk.push_back({double(fs - 1 + i), lean[size_t(i)], Interp::Linear});
          gen.tracks[who + "/collision.turn." + sk.bones[size_t(A.hand)].name].keys = std::move(lk);
        } else if (savedLean) {
          gen.tracks[leanTrack] = *savedLean;
        } else {
          gen.tracks.erase(leanTrack);
        }
        if (savedS) gen.tracks[swing] = *savedS;
        if (anyLean) writeArmPole(gen, c, side);  // the swing for the turned body
      }
    }
  }
}

Result<void> SceneEvaluator::finishInteractions(Clip& gen, InteractionContext& ctx) {
  // The final arms are planned, corrected and checked on the pose as it plays back: with the automatic base idle
  // (prepared after the actions compile, clip_layers.cpp), which moves the shoulders and clip arms (T-047).
  const bool idleNotPrepared = autoIdle_.empty();
  if (idleNotPrepared) {
    const auto saved = warnings_;
    prepareAutoIdle();
    warnings_ = saved;
  }
  struct Restore {
    SceneEvaluator* ev;
    bool clear;
    ~Restore() {
      if (clear) ev->autoIdle_.clear();
    }
  } restore{this, idleNotPrepared};
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
  // The contact corrections moved some wrists a little: the swings follow (they do not move wrists or hands).
  for (size_t c = 0; c < clearance_.size(); ++c) {
    if (!clearance_[c].valid) continue;
    for (char side : {'L', 'R'}) {
      const std::string ik = scene_.characters[c].name + "/ik." + characters_[c].asset.skeleton.bones[size_t(clearance_[c].arm[side == 'L' ? 0 : 1].hand)].name;
      if (gen.find(ik)) writeArmPole(gen, c, side);
    }
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
