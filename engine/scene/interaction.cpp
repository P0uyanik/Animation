// Hand-prop interaction actions (see interaction.h). Compiled into generated tracks and prop parent switches by
// SceneEvaluator::compileActions (actions.cpp); evaluated by the ordinary pose path (IK, hand pose, look) plus the
// orientation constraint below, which scene.cpp applies after IK.
#include "scene/interaction.h"

#include "anim/body_mechanics.h"
#include "anim/hand_shape.h"
#include "anim/principles.h"

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

// T-096: the head clearance tilt "<prefix>headTilt" (world rotation vector, radians) turns the neck about its own head
// (the joint), after IK and look-at; the eyes keep their world rotation, so the gaze stays on its target.
void applyHeadTilt(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world, Pose& pose) {
  const Track* t = clip.find(prefix + "headTilt");
  if (!t || t->keys.empty()) return;
  const vec3 rv = t->evaluate(frame);
  const int neck = sk.find("neck");
  if (neck < 0 || glm::length(rv) < 1e-7f) return;
  auto rotOf = [](const mat4& M) {
    return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(M[0])), glm::normalize(vec3(M[1])), glm::normalize(vec3(M[2])))));
  };
  std::vector<mat4> G = boneGlobals(sk, pose, world);
  std::vector<std::pair<int, quat>> eyes;
  for (size_t b = 0; b < sk.bones.size(); ++b)
    if (sk.bones[b].name.rfind("eye.", 0) == 0) eyes.push_back({int(b), rotOf(G[b])});
  const int parent = sk.bones[size_t(neck)].parent;
  const quat parentRot = rotOf(parent >= 0 ? G[size_t(parent)] : world);
  pose.local[size_t(neck)] = glm::normalize(glm::inverse(parentRot) * fromRotationVector(rv) * parentRot * pose.local[size_t(neck)]);
  for (const auto& [e, before] : eyes) {  // bones come parent first: an eye's parent is already where it ends up
    G = boneGlobals(sk, pose, world);
    const int ep = sk.bones[size_t(e)].parent;
    pose.local[size_t(e)] = glm::normalize(glm::inverse(rotOf(ep >= 0 ? G[size_t(ep)] : world)) * before);
  }
}

// T-134 reach mechanics (opt-in scene key "reachMechanics"): the body lead of a reach. "<prefix>reach.lead" (world
// rotation vector, radians: lean towards the prop + turn of the reaching shoulder) is spread over hips, spine and
// chest, each link `succession` frames ahead of the next ("<prefix>reach.lead.params": succession frames, hip share,
// head stabilisation), and "<prefix>reach.shoulder.<upper arm>" (world offset, metres) advances a shoulder joint.
// Root bones that anatomically ride on the torso (the unparented arms and eyes of imported rigs) are carried with
// the chest / head. The legs, the head (by its share) and the eyes keep their world rotation, and every IK-driven arm
// is solved again from the moved shoulder, so its wrist stays on the IK target (by the IK weight) and the hand keeps
// its rotation. Without the track nothing changes.
void applyReachLead(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world, Pose& pose) {
  const Track* t = clip.find(prefix + "reach.lead");
  if (!t || t->keys.empty()) return;
  const vec3 par = clip.evaluate(prefix + "reach.lead.params", frame, vec3(0));
  const double succ = par.x;
  const float hipShare = par.y, headStab = par.z;
  auto rotOf = [](const mat4& M) {
    return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(M[0])), glm::normalize(vec3(M[1])), glm::normalize(vec3(M[2])))));
  };
  const std::vector<mat4> G0 = boneGlobals(sk, pose, world);
  struct Kept {
    int bone;
    quat rot;
    vec3 pos;
    float w;
  };
  std::vector<Kept> arms, legs, eyes;
  const int hips = sk.find("hips"), spine = sk.find("spine"), neck = sk.find("neck"), head = sk.find("head");
  const int chest = sk.find("chest") >= 0 ? sk.find("chest") : spine;
  std::vector<std::pair<int, vec3>> shoulders, clavicles;
  std::vector<std::pair<int, int>> riders;  // root bone, its carrier
  for (size_t b = 0; b < sk.bones.size(); ++b) {
    const std::string& n = sk.bones[b].name;
    const bool eye = n.rfind("eye.", 0) == 0;
    if (eye) eyes.push_back({int(b), rotOf(G0[b]), vec3(0), 1});
    if (n.rfind("thigh", 0) == 0 && sk.bones[b].parent >= 0) legs.push_back({int(b), rotOf(G0[b]), vec3(0), 1});
    if (n.rfind("hand", 0) == 0) {
      const Track* ik = clip.find(prefix + "ik." + n);
      if (ik && !ik->keys.empty())
        arms.push_back({int(b), rotOf(G0[b]), vec3(G0[b][3]), std::clamp(clip.evaluate(prefix + "ik." + n + ".weight", frame, vec3(1)).x, 0.0f, 1.0f)});
    }
    if (const Track* sh = clip.find(prefix + "reach.shoulder." + n); sh && !sh->keys.empty())
      shoulders.push_back({int(b), sh->evaluate(frame - succ)});
    if (const Track* cl = clip.find(prefix + "reach.clavicle." + n); cl && !cl->keys.empty())
      clavicles.push_back({int(b), cl->evaluate(frame - 0.5 * succ)});
    if (sk.bones[b].parent < 0 && int(b) != hips) {
      if (eye && head >= 0) riders.push_back({int(b), head});
      else if (chest >= 0 && (n.find("upperArm") != std::string::npos || n.find("shoulder") != std::string::npos || n.find("clavicle") != std::string::npos))
        riders.push_back({int(b), chest});
      else if (hips >= 0 && n.find("pelvis") != std::string::npos) riders.push_back({int(b), hips});
    }
  }
  // Turns a bone about its own pivot by the world rotation vector rv.
  auto turn = [&](int bone, vec3 rv) {
    if (bone < 0 || glm::length(rv) < 1e-7f) return;
    const quat q = rotOf(boneGlobals(sk, pose, world)[size_t(bone)]);
    pose.local[size_t(bone)] = glm::normalize(pose.local[size_t(bone)] * (glm::inverse(q) * fromRotationVector(rv) * q));
  };
  // Puts a bone back on a world rotation (by weight w).
  auto restore = [&](const Kept& k, float w) {
    if (w <= 0) return;
    const quat q = rotOf(boneGlobals(sk, pose, world)[size_t(k.bone)]);
    const quat back = glm::normalize(pose.local[size_t(k.bone)] * (glm::inverse(q) * k.rot));
    pose.local[size_t(k.bone)] = glm::normalize(glm::slerp(pose.local[size_t(k.bone)], back, std::min(w, 1.0f)));
  };
  const float hs = hips >= 0 ? hipShare : 0.0f;
  const float ss = spine >= 0 && chest != spine ? 0.45f * (1 - hs) : 0.0f;
  const float cs = 1 - hs - ss;
  const vec3 hipTurn = hs * t->evaluate(frame + 2 * succ), spineTurn = ss * t->evaluate(frame + succ), chestTurn = cs * t->evaluate(frame);
  if (pose.offset.size() != sk.bones.size()) pose.offset.resize(sk.bones.size(), vec3(0));
  const mat4 toRoot = glm::inverse(world);
  // Hip shift ("<prefix>reach.hip", world metres, with the hips' lead): the pelvis moves towards the prop; legs that
  // hang on the hips keep their hip joints where they were (the feet stay planted).
  if (const Track* hipShift = clip.find(prefix + "reach.hip"); hips >= 0 && sk.bones[size_t(hips)].parent < 0 && hipShift && !hipShift->keys.empty()) {
    const vec3 v = hipShift->evaluate(frame + 2 * succ);
    pose.offset[size_t(hips)] += vec3(toRoot * vec4(v, 0));
    const mat4 toHips = glm::inverse(boneGlobals(sk, pose, world)[size_t(hips)]);
    for (const Kept& k : legs)
      if (sk.bones[size_t(k.bone)].parent == hips) pose.offset[size_t(k.bone)] -= vec3(toHips * vec4(v, 0));
  }
  turn(hips, hipTurn);
  for (const Kept& k : legs) restore(k, 1);
  turn(spine, spineTurn);
  turn(chest, chestTurn);
  // E1c overlap: the head has its own, later response ("<prefix>reach.head"); else it takes back its share at once.
  const Track* headTrack = clip.find(prefix + "reach.head");
  turn(neck, headTrack && !headTrack->keys.empty() ? headTrack->evaluate(frame) : -headStab * (hipTurn + spineTurn + chestTurn));
  if (!riders.empty()) {
    const std::vector<mat4> G1 = boneGlobals(sk, pose, world);
    const quat worldRot = rotOf(world);
    for (const auto& [bone, carrier] : riders) {
      const mat4 D = G1[size_t(carrier)] * glm::inverse(G0[size_t(carrier)]);
      pose.offset[size_t(bone)] += vec3(toRoot * vec4(vec3(D * G0[size_t(bone)][3]) - vec3(G0[size_t(bone)][3]), 0));
      pose.local[size_t(bone)] = glm::normalize(glm::inverse(worldRot) * rotOf(D) * worldRot * pose.local[size_t(bone)]);
    }
  }
  if (!shoulders.empty()) {
    const std::vector<mat4> G1 = boneGlobals(sk, pose, world);
    for (const auto& [bone, v] : shoulders) {
      const int parent = sk.bones[size_t(bone)].parent;
      pose.offset[size_t(bone)] += vec3((parent >= 0 ? glm::inverse(G1[size_t(parent)]) : toRoot) * vec4(v, 0));
    }
  }
  for (const auto& [bone, rv] : clavicles) turn(bone, rv);  // after the carry: the clavicle turns about its own pivot
  for (const Kept& k : eyes) restore(k, 1);  // bones come parent first
  for (const Kept& k : arms) {
    // An arm that is not on its IK target yet rides only half way with the torso: the body leads and the hand
    // hangs back, without the torso's turn swinging it about before its own reach starts.
    const vec3 carried(boneGlobals(sk, pose, world)[size_t(k.bone)][3]);
    const float hold = std::max(k.w, 0.5f);
    solveTwoBoneIK(sk, pose, world, k.bone, glm::mix(carried, k.pos, hold), 1.0f);
    restore(k, hold);
  }
}

void applyArmPoles(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                   Pose& pose) {
  applyReachLead(sk, clip, prefix, frame, world, pose);  // T-134 (no track: no-op)
  applyHeadTilt(sk, clip, prefix, frame, world, pose);  // T-096 (runs at the same point of the pose path; no track: no-op)
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    const std::string name = prefix + "pole." + sk.bones[i].name, swingName = prefix + "swing." + sk.bones[i].name;
    const Track* t = clip.find(name);
    const Track* sw = clip.find(swingName);
    const Track* el = clip.find(prefix + "elbow." + sk.bones[i].name);  // T-171 (opt-in "grip": "natural")
    const bool hasPole = t && !t->keys.empty(), hasSwing = sw && !sw->keys.empty(), hasElbow = el && !el->keys.empty();
    if (!hasPole && !hasSwing && !hasElbow) continue;
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
    // T-171: the elbow a natural grip asks for, "<prefix>elbow.<hand bone>" = the world direction the elbow points
    // in from the shoulder -> wrist line, times a weight 0..1 (its length). Before the planned swing, which is
    // measured on top of it.
    if (hasElbow)
      swing([&](vec3 a, vec3 b, vec3 u) {
        const vec3 pole = el->evaluate(frame);
        const float lpole = glm::length(pole);
        vec3 e = (b - a) - u * glm::dot(b - a, u), p = pole - u * glm::dot(pole, u);
        const float le = glm::length(e), lp = glm::length(p);
        if (lpole < 1e-4f || le < 1e-5f || lp < 1e-6f) return 0.0f;
        e /= le;
        p /= lp;
        const float strength = std::clamp((lp / lpole) / 0.3f, 0.0f, 1.0f);  // a direction along the arm has no plane
        return std::atan2(glm::dot(glm::cross(e, p), u), glm::dot(e, p)) * std::min(lpole, 1.0f) * strength;
      });
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
  bool face = false;  // T-112c: a box face (the solid is the slab |dot(p - centre, inward)| <= radius)
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
      g.face = true;
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

// T-171 (opt-in "clear"): signed distance (metres, prop frame) from a point to the prop as a solid: the primitive it is
// made of, else its collision proxy (cylinders capped, a cup's opening closed; negative inside).
float propSolidDistance(const PropAsset& asset, vec3 s) {
  enum class Kind { Box, Sphere, Cylinder } kind = Kind::Sphere;
  vec3 size(0.06f);
  float radius = 0.03f, y0 = 0, y1 = 0;
  mat4 frame(1);
  const float k = asset.scaleMetres > 0 ? asset.scaleMetres : 1.0f;
  if (asset.mesh.kind == AssetMeshSource::Kind::Primitive) {
    using P = AssetMeshSource::Primitive;
    kind = asset.mesh.primitive == P::Box ? Kind::Box : asset.mesh.primitive == P::Sphere ? Kind::Sphere : Kind::Cylinder;
    size = asset.mesh.size * k, radius = asset.mesh.radius * k, y1 = asset.mesh.height * k;
  } else if (asset.collision) {
    using T = AssetCollisionProxy::Type;
    const auto& c = *asset.collision;
    kind = c.type == T::Box ? Kind::Box : c.type == T::Sphere ? Kind::Sphere : Kind::Cylinder;
    size = c.size, radius = c.radius, y0 = -0.5f * c.height, y1 = 0.5f * c.height;
    frame = assetTransformMatrix(c.transform);
  }
  const vec3 p = vec3(glm::inverse(frame) * vec4(s, 1));
  if (kind == Kind::Sphere) return glm::length(p) - radius;
  vec2 q;
  if (kind == Kind::Cylinder) {
    q = vec2(std::sqrt(p.x * p.x + p.z * p.z) - radius, std::abs(p.y - 0.5f * (y0 + y1)) - 0.5f * (y1 - y0));
  } else {
    const vec3 b = glm::abs(p) - 0.5f * size;
    q = vec2(std::max(b.x, b.z), b.y);
    if (b.x > 0 && b.z > 0) q.x = std::sqrt(b.x * b.x + b.z * b.z);
  }
  return glm::length(glm::max(q, vec2(0))) + std::min(std::max(q.x, q.y), 0.0f);
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

// Hand shapes other than "wrap" (T-112b keys, T-112c values): the shared hand-shape table of T-051
// (content/hand_shapes, anim/hand_shape.h). A grasp keys the shape's approach pose on the way and its pose at contact
// (keyHandShape: hand.<s>, .index, .f<k>, .thumb, .stagger where the shape sets them) and runs the shape's contact
// search: "none" rests the hand on the prop as posed (palm, hook, cradle), "pinch" closes index and thumb on a sphere
// of the shape's pinch_radius at the socket (the other fingers keyed free). "wrap" stays kOpen and the contact search
// below (the table's wrap is the same pose, checked by tests/test_verbs.cpp), so a grasp without "shape" is unchanged.
// The extra per-finger tracks a shape keys, set back to the relaxed hand (`rest` = hand.<s> at that frame).
void keyShapeRest(Clip& gen, const std::string& pose, double f, const HandShape& s, vec3 rest) {
  const bool pinch = s.search == HandShapeSearch::Pinch;
  for (const HandShapePose* p : {&s.pose, s.approach ? &*s.approach : &s.pose}) {
    if (p->index) key(gen, pose + ".index", f, vec3(rest.x));
    for (int k = 0; k < 4; ++k)
      if (p->fingers[size_t(k)] || (pinch && k != 3)) key(gen, std::format("{}.f{}", pose, k), f, vec3(rest.x, rest.z, pinch && k != 3 ? 1.0f : 0.0f));
    if (p->thumbOpposition) key(gen, pose + ".thumb", f, vec3(0, rest.y, 0));
  }
}
// T-171 hands round 2 (opt-in, action key "fingerClose": true | {...} on reach / grasp / place / handover and on the
// verbs that lower to them; absent = every key as before, byte for byte). Only keys change, the solver does not:
//   "preshape": 0..1      grasp weight held on the way in (default 0.5): the opening hand already takes the object's
//                         shape, each finger part of the way from the open pose to its contact pose (0 = none)
//   "stagger": frames     between fingers landing, index first, little last; opening in reverse (default 2; track
//                         hand.<s>.stagger of T-051)
//   "close": frames       the final close, ending at contact for the index (default 6, at most half the reach)
//   "settle": [share, frames]  soft contact: the last `share` of the close takes `frames` (default [0.12, 3]), so
//                         each finger lands slowly instead of stopping dead; the weight never passes 1 (no press-in)
//   "widen": [lo, hi]     metres: a banded grasp keys the T-138 band fit and the T-157 (a) wider band
//   "rest": {pose}        a hand-shape pose (anim/hand_shape.h: curl, thumb, spread, fingers ...) for the hand before
//                         the reach and after the release instead of the relaxed hand (wrap grasps: its per-finger
//                         curls and spreads too)
//   Round 3 (owner review 2026-11-21; each its own key, none implied by the others):
//   "wrap": true          the grasp keys the wrap search (anim: HandPose::wrap, track hand.<s>.wrap) with the finger and
//                         thumb thickness measured on the character's mesh, and seats the prop where the palm ends and
//                         the fingers begin, as far off the hand as the palm's measured surface needs (track
//                         hand.<s>.seat): the fingers arch onto the prop with all three joints, the thumb opposes them
//                         inside its anatomical range, the palm does not sink in
//   "grip": "natural"     on an upright round prop the hand takes the prop thumb up with a straight wrist: the grasp
//                         point turns about the prop's axis by the smallest angle at which some elbow position (never
//                         above the shoulder-wrist line, clear of the body) leaves the fingers within 30 deg of the
//                         forearm, and that elbow is keyed ("<who>/elbow.<hand bone>": the direction it points in, eased
//                         in early in the reach, back to the arm solve's own elbow after the release). The planner otherwise turns the hand thumb down
//                         when the authored point faces the wrong way for this hand. "site" (default): as before
//   "clear": metres       the way in keeps the hand at least this far from the prop (default 0 = the path as it was):
//                         a hand taking an upright prop rises with its fingers hanging and swings them level in the
//                         palm's own plane; where the digits or the palm still come closer, the wrist moves out, level, away
//                         from the prop, eased in time and gone by the contact
struct FingerClose {
  float preshape = 0.5f, stagger = 2.0f, settleShare = 0.12f;
  double closeFrames = 6, settleFrames = 3;
  bool wrap = false, natural = false;
  float clear = 0;
  std::optional<vec2> widen;
  std::optional<HandShape> restShape;
  const HandShape* rest() const { return restShape ? &*restShape : nullptr; }
};
Result<std::optional<FingerClose>> fingerCloseFromJson(const Json& a, const std::string& what) {
  auto it = a.find("fingerClose");
  if (it == a.end() || it->is_null() || (it->is_boolean() && !it->get<bool>())) return std::optional<FingerClose>{};
  FingerClose fc;
  if (it->is_boolean()) return std::optional<FingerClose>{fc};
  if (!it->is_object()) return fail(std::format("{}: 'fingerClose' must be true, false or an object", what));
  auto bad = [&](const std::string& why) { return fail(std::format("{}: fingerClose.{}", what, why)); };
  for (const auto& [k, v] : it->items()) {
    auto in = [&](double lo, double hi) { return v.is_number() && v.get<double>() >= lo && v.get<double>() <= hi; };
    auto pair = [&](double lo0, double hi0, double lo1, double hi1) {
      return v.is_array() && v.size() == 2 && v[0].is_number() && v[1].is_number() && v[0].get<double>() >= lo0 &&
             v[0].get<double>() <= hi0 && v[1].get<double>() >= lo1 && v[1].get<double>() <= hi1;
    };
    if (k == "preshape") {
      if (!in(0, 1)) return bad("preshape must be in [0, 1]");
      fc.preshape = v.get<float>();
    } else if (k == "stagger") {
      if (!in(0, 6)) return bad("stagger must be in [0, 6] frames");
      fc.stagger = v.get<float>();
    } else if (k == "close") {
      if (!in(2, 24)) return bad("close must be in [2, 24] frames");
      fc.closeFrames = v.get<double>();
    } else if (k == "settle") {
      if (!pair(0, 0.5, 1, 12)) return bad("settle must be [share in 0..0.5, frames in 1..12]");
      fc.settleShare = v[0].get<float>(), fc.settleFrames = v[1].get<double>();
    } else if (k == "widen") {
      if (!pair(0, 0.1, 0, 0.1)) return bad("widen must be [lo, hi], metres in [0, 0.1]");
      fc.widen = vec2(v[0].get<float>(), v[1].get<float>());
    } else if (k == "wrap") {
      if (!v.is_boolean()) return bad("wrap must be true or false");
      fc.wrap = v.get<bool>();
    } else if (k == "grip") {
      if (!v.is_string() || (v.get<std::string>() != "natural" && v.get<std::string>() != "site")) return bad("grip must be \"natural\" or \"site\"");
      fc.natural = v.get<std::string>() == "natural";
    } else if (k == "clear") {
      if (!in(0, 0.05)) return bad("clear must be in [0, 0.05] metres");
      fc.clear = v.get<float>();
    } else if (k == "rest") {
      auto r = handShapeFromJson(Json{{"format", "plush.hand_shape"}, {"version", 1}, {"id", "rest"}, {"kind", "rest"}, {"pose", v}});
      if (!r) return bad("rest: " + r.error().message);
      fc.restShape = std::move(*r);
    } else {
      return bad(std::format("{}: unknown key", k));
    }
  }
  return std::optional<FingerClose>{fc};
}
// The per-finger tracks of a rest shape (T-171 "rest"), keyed to `v` = (curl, thumb, spread) instead (the open hand).
void keyRestFingers(Clip& gen, const std::string& pose, double f, const HandShape& rest, vec3 v) {
  for (int k = 0; k < 4; ++k)
    if (rest.pose.fingers[size_t(k)] || (k == 3 && rest.pose.index)) key(gen, std::format("{}.f{}", pose, k), f, vec3(v.x, v.z, 0));
  if (rest.pose.thumbOpposition) key(gen, pose + ".thumb", f, vec3(0, v.y, 0));
}
// The rest shape itself: hand.<s> and its per-finger tracks (the index override as an f3 key, so no .index track).
void keyRest(Clip& gen, const std::string& pose, double f, const HandShape& rest) {
  const HandShapePose& p = rest.pose;
  key(gen, pose, f, vec3(p.curl, p.thumb, p.spread));
  for (int k = 0; k < 4; ++k) {
    if (p.fingers[size_t(k)]) key(gen, std::format("{}.f{}", pose, k), f, vec3(*p.fingers[size_t(k)], 0.0f));
    else if (k == 3 && p.index) key(gen, std::format("{}.f{}", pose, k), f, vec3(*p.index, p.spread, 0));
  }
  if (p.thumbOpposition) key(gen, pose + ".thumb", f, vec3(*p.thumbOpposition, p.thumb, 0));
}
// T-171 (opt-in "wrap"): what the hand really measures, from the rest mesh. profile: the palm's surface, the highest
// vertex along the palm normal per 2 mm station along the finger direction (every vertex the hand bone carries
// rigidly: the palm, the knuckles, the ball of the thumb; not the digits the hand pose moves); finger / thumb: the
// thickness of a digit's last segment (80th percentile of its vertices' distance from the segment's axis; fingers
// averaged). 0 / empty = not measurable (no such vertices).
struct HandSkin {
  std::vector<vec2> profile;  // (station along the finger direction, height along the palm normal), metres
  float finger = 0, thumb = 0;
  // How far a round prop of `radius` stands off the hand bone's axis when it rests on the palm with its nearest line
  // at `station`: the lowest position at which no palm vertex is inside it (radius <= 0: a flat face). 0 = unknown.
  float seat(float radius, float station) const {
    float q = 0;
    for (const vec2& v : profile) {
      if (radius <= 0) {
        q = std::max(q, v.y);
        continue;
      }
      const float dx = v.x - station;
      if (std::abs(dx) < radius) q = std::max(q, v.y + std::sqrt(radius * radius - dx * dx) - radius);
    }
    return q;
  }
};
HandSkin handSkin(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes, int handBone, char side, const HandGrip& grip) {
  HandSkin out;
  if (handBone < 0) return out;
  const std::string s = std::string(".") + side;
  const size_t n = sk.bones.size();
  enum : char { Other = 0, Palm = 1, Digit = 2 };
  std::vector<char> kind(n, Other);
  std::vector<int> digitOf(n, -1);  // last segment of finger k (0..3) or the thumb (4)
  kind[size_t(handBone)] = Palm;
  const int thumbA = sk.find("thumbA" + s), thumbB = sk.find("thumbB" + s);
  for (size_t b = 0; b < n; ++b) {  // parents precede children
    const int p = sk.bones[b].parent;
    if (p < 0 || kind[size_t(p)] == Other) continue;
    const std::string& nm = sk.bones[b].name;
    const bool fingerRoot = nm.size() == 5 && nm[0] == 'f' && nm[2] == 'a' && nm.ends_with(s);
    kind[b] = kind[size_t(p)] == Digit || fingerRoot || int(b) == thumbA ? Digit : Palm;
  }
  std::array<int, 5> last{-1, -1, -1, -1, thumbB};
  for (int k = 0; k < 4; ++k) {
    const int b = sk.find(std::format("f{}b{}", k, s));
    if (b < 0) continue;
    int c = -1, cn = 0;
    for (size_t i = 0; i < n; ++i)
      if (sk.bones[i].parent == b) c = int(i), ++cn;
    last[size_t(k)] = cn == 1 ? c : b;
  }
  for (int k = 0; k < 5; ++k)
    if (last[size_t(k)] >= 0) digitOf[size_t(last[size_t(k)])] = k;
  std::array<std::vector<float>, 5> radial;
  std::map<int, float> palm;  // 2 mm station -> highest vertex
  const vec3 head = sk.bones[size_t(handBone)].head;
  for (const SkinnedMesh& m : meshes)
    for (size_t i = 0; i < m.rest.positions.size(); ++i) {
      int top = 0;
      for (int j = 1; j < 4; ++j)
        if (m.weights[i][j] > m.weights[i][top]) top = j;
      const int b = m.joints[i][top];
      if (b < 0 || size_t(b) >= n) continue;
      const vec3 q = m.rest.positions[i];
      if (kind[size_t(b)] == Palm) {
        const float t = glm::dot(q - head, grip.fingerDir), hgt = glm::dot(q - head, grip.palmNormal);
        if (hgt <= 0) continue;
        const int bin = int(std::floor(t / 0.002f));
        if (auto it = palm.find(bin); it == palm.end() || it->second < hgt) palm[bin] = hgt;
      } else if (const int k = digitOf[size_t(b)]; k >= 0) {
        const vec3 h0 = sk.bones[size_t(b)].head, u = h0 - sk.bones[size_t(sk.bones[size_t(b)].parent)].head;
        if (glm::length(u) < 1e-6f) continue;
        const vec3 d = q - h0, un = glm::normalize(u);
        radial[size_t(k)].push_back(glm::length(d - un * glm::dot(d, un)));
      }
    }
  auto quantile = [](std::vector<float>& v, float x) {
    if (v.size() < 8) return 0.0f;
    const size_t i = std::min(v.size() - 1, size_t(x * float(v.size())));
    std::nth_element(v.begin(), v.begin() + std::ptrdiff_t(i), v.end());
    return v[i];
  };
  for (const auto& [bin, hgt] : palm) out.profile.push_back(vec2((float(bin) + 0.5f) * 0.002f, hgt));
  float sum = 0;
  int cnt = 0;
  for (int k = 0; k < 4; ++k)
    if (const float r = quantile(radial[size_t(k)], 0.8f); r > 0) sum += r, ++cnt;
  out.finger = cnt > 0 ? sum / float(cnt) : 0.0f;
  out.thumb = quantile(radial[4], 0.8f);
  return out;
}
// How one grasp is made (T-112b): the hand shape, the side the palm comes from, the finger contact band.
struct GraspStyle {
  std::optional<FingerClose> soft;  // T-171 (opt-in)
  bool naturalElbow = false;        // T-171 "grip": "natural": key the elbow that keeps the wrist straight
  std::string shape = "wrap";
  const HandShape* hs = nullptr;  // T-112c: the table entry of a non-wrap shape
  std::optional<vec3> approach;  // prop frame
  std::optional<vec2> band;      // prop frame, along the grasp axis
  float thumb = 0;               // 0 opposed, 1 along, 2 tucked
  bool face = false;             // T-112c "graspFace": per-finger search on the box face the socket is on
};

}  // namespace

vec3 SceneEvaluator::handGripPoint(size_t c, char side, double frame) const {
  const int hb = characterSocketBone(c, std::string("hand.") + side);
  if (hb < 0) return vec3(0);
  HandGrip g = handGrip(characters_[c].asset.skeleton, hb, side);
  // T-171 (opt-in "wrap"): a seated grasp keyed where the prop rests on the hand ("hand.<s>.seat" = (stand-off, station
  // along the fingers), from its first key on).
  if (const Track* t = scene_.animation.find(std::format("{}/hand.{}.seat", scene_.characters[c].name, side));
      t && !t->keys.empty() && frame >= t->keys.front().frame - 1e-6 && t->evaluate(frame).x > 0)
    g.palm = g.fingerDir * t->evaluate(frame).y + g.palmNormal * t->evaluate(frame).x;
  return vec3(characterGlobals(c, frame)[size_t(hb)] * vec4(g.palm, 1));
}

Result<bool> SceneEvaluator::compileInteraction(const Json& a, Clip& gen, InteractionContext& ctx) {
  const std::string type = str(a, "type");
  const bool reach = (type == "reach" || type == "grasp") && a.contains("prop");
  if (type == "grasp" && !a.contains("prop")) return fail("grasp: give 'prop' (a scene prop instance)");
  if (!reach && type != "hold" && type != "place" && type != "handover") return false;
  const Clip& clip = scene_.animation;
  if (!ctx.timingResolved) {  // T-104: the scene's timing profile (T-104d: calibrated unless the scene says otherwise)
    ctx.timingResolved = true;
    if (const std::string name = scene_.timingProfile(); !name.empty()) {
      const auto file = findTimingProfileFile(scene_.path, name);
      // A profile the scene names must exist; the implicit default may be missing (a scene outside a content tree),
      // and then the shared defaults apply, as a missing personality profile does.
      if (file.empty() && !scene_.timing.is_null())
        return fail(std::format("timing profile '{}' not found in content/timing", name));
      if (!file.empty()) {
        auto t = loadTimingProfile(file);
        if (!t) return std::unexpected(t.error());
        ctx.timing = std::move(*t);
      }
    }
  }
  // Default length of a beat for character `who` (the shared default `fallback` without a timing profile).
  auto beat = [&](const char* name, double fallback, int who) {
    return ctx.timing ? ctx.timing->frames(name, fallback, personality(size_t(who))) : fallback;
  };

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
  // T-134 E1b arcs (opt-in "reachMechanics"): a wrist move keyed as a straight line from the key at f0 to the key at
  // f1 (a carry, the giver's way to the hand-over point) travels a shallow arc instead, with the same timing: the
  // mid point is moved by arc x chord across the chord, away from the shoulder (the hand swings round its arm's
  // joints), or by less when the arm could not reach that far. Keys between f0 and f1 are replaced, the end keys
  // stay, so doing it again for the same move (hand-over trials) gives the same keys.
  const ReachMechanics reachMech = reachMechanicsFromJson(scene_.reachMechanics).value_or(ReachMechanics{});
  auto arcMove = [&](const Hand& h, double f0, double f1) {
    if (!reachMech.enabled || !reachMech.arcs || f1 < f0 + 3) return;
    Track& T = gen.tracks[h.ik];
    std::erase_if(T.keys, [&](const Key& k) { return k.frame > f0 + 1e-6 && k.frame < f1 - 1e-6; });
    const vec3 p0 = T.evaluate(f0), p2 = T.evaluate(f1);
    const float L = glm::distance(p0, p2);
    if (L < float(reachMech.arcMinChordM)) return;
    const vec3 c = (p2 - p0) / L, mid = 0.5f * (p0 + p2), shoulder = boneAt(h, h.root, 0.5 * (f0 + f1));
    // Upward bow first; a move that is itself (nearly) vertical has no "up" across it and bows away from the shoulder.
    vec3 away = (mid - shoulder) - c * glm::dot(mid - shoulder, c);
    if (glm::length(away) > 1e-4f) away = glm::normalize(away);
    vec3 n = (kUp - c * c.y) + 0.35f * away;
    if (glm::length(n) < 1e-4f) return;
    n = glm::normalize(n);
    float dev = 0;
    for (float k : {1.0f, 0.5f, 0.25f})
      if (dev == 0 && glm::distance(shoulder, mid + n * (float(reachMech.arc) * L * k)) <= 0.95f * h.armLength) dev = float(reachMech.arc) * L * k;
    if (dev == 0) return;
    const vec3 p1 = mid + n * (2 * dev);  // a quadratic Bezier is half its control point's offset away from the chord
    const int steps = int(std::ceil(f1 - f0 - 1e-6));
    for (int j = 0; j < steps; ++j) {
      const double f = f0 + j;
      const float x = float((f - f0) / (f1 - f0)), u = x * x * (3 - 2 * x);  // the timing of the two smooth keys
      T.setKey({f, (1 - u) * (1 - u) * p0 + 2 * u * (1 - u) * p1 + u * u * p2, Interp::Linear});
    }
  };
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
    bool face = false;  // T-112c: the socket is on a box face
    bool faceGrasp = false;  // T-112c: the grasp keyed the box-face search
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
    pl.face = gs.face;
    return pl;
  };
  // T-112c: a grasp's hand shape from the shared table (content/hand_shapes above the scene, loaded once per compile).
  auto graspHandShape = [&](const std::string& name, const std::string& what) -> Result<const HandShape*> {
    if (!ctx.handShapesResolved) {
      ctx.handShapesResolved = true;
      const auto dir = findHandShapeDir(scene_.path);
      if (dir.empty()) {
        ctx.handShapesError = std::format("no content/hand_shapes above '{}'", scene_.path.string());
      } else if (auto t = loadHandShapeTable(dir); t) {
        ctx.handShapes = std::move(*t);
      } else {
        ctx.handShapesError = t.error().message;
      }
    }
    if (!ctx.handShapes) return fail(std::format("{}: hand shape '{}': {}", what, name, ctx.handShapesError));
    const HandShape* s = ctx.handShapes->find(name);
    if (!s || s->kind != "grasp") {
      std::string list = "wrap";
      for (const auto& [id, hs] : ctx.handShapes->shapes)
        if (hs.kind == "grasp" && id != "wrap") list += ", " + id;
      return fail(std::format("{}: unknown hand shape '{}' (grasp shapes: {})", what, name, list));
    }
    return s;
  };
  // The grasp weight of a reach: 0 until four frames before contact, 1 at contact. T-171 (opt-in): the weight rises
  // to the pre-shape on the way in, closes fast and lands slowly; the fingers land one stagger step apart.
  auto keyClose = [&](const Hand& h, double start, double contact, const GraspStyle& style) {
    const std::string w = h.pose + ".grasp.weight";
    key(gen, w, start, vec3(0));
    if (!style.soft) {
      key(gen, w, contact - 4, vec3(0));
      key(gen, w, contact, vec3(1));
      return;
    }
    const FingerClose& fc = *style.soft;
    const double T = contact - start, c0 = contact - std::min(fc.closeFrames, 0.5 * T);
    const double cs = contact - std::min(fc.settleFrames, 0.5 * (contact - c0));
    if (fc.preshape > 0) key(gen, w, start + 0.3 * T, vec3(0));
    key(gen, w, c0, vec3(fc.preshape));
    key(gen, w, cs, vec3(std::max(fc.preshape, 1.0f - fc.settleShare)));
    key(gen, w, contact, vec3(1));
    key(gen, h.pose + ".stagger", start, vec3(fc.stagger), Interp::Step);
  };
  // The table entry of a shape already accepted by a grasp (nullptr: wrap).
  auto tableShape = [&](const std::string& name) -> const HandShape* {
    return name == "wrap" || !ctx.handShapes ? nullptr : ctx.handShapes->find(name);
  };
  // T-171 (opt-in, fingerClose "grip": "natural"). The elbow of a two-bone arm lies on a circle about the shoulder ->
  // wrist line; wristBend is the smallest angle between the forearm and the hand's fingers over the elbows that are
  // allowed: not above that line by more than kElbowRise, forearm and hand clear of the body (the planner's limb
  // capsules, at least the margin). Returns the angle (radians; 4 = none allowed) and the elbow's direction from the
  // line (unit, world).
  constexpr float kElbowRise = 0.35f;  // sine: about 20 deg
  auto wristBend = [&](const Hand& hh, double f, vec3 W, const mat3& R, vec3* elbowDir) {
    const Skeleton& sk = characters_[size_t(hh.c)].asset.skeleton;
    const BodyClearanceModel* M = size_t(hh.c) < clearance_.size() && clearance_[size_t(hh.c)].valid ? &clearance_[size_t(hh.c)] : nullptr;
    std::vector<mat4> G = characterGlobals(size_t(hh.c), f);
    const vec3 S(G[size_t(hh.root)][3]);
    const float a = glm::distance(sk.bones[size_t(hh.root)].head, sk.bones[size_t(hh.mid)].head);
    const float b = glm::distance(sk.bones[size_t(hh.mid)].head, sk.bones[size_t(hh.bone)].head);
    const float d = std::clamp(glm::distance(S, W), 1e-4f, a + b - 1e-5f);
    const vec3 u = glm::normalize(W - S);
    const float x = (a * a - b * b + d * d) / (2 * d), r = std::sqrt(std::max(0.0f, a * a - x * x));
    vec3 e1 = -kUp - u * glm::dot(-kUp, u);  // down, off the line
    e1 = glm::length(e1) > 1e-4f ? glm::normalize(e1) : glm::normalize(glm::cross(u, vec3(0, 0, 1)));
    const vec3 e2 = glm::cross(u, e1), fingers = R * hh.grip.fingerDir;
    const vec3 restDir = glm::normalize(sk.bones[size_t(hh.bone)].head - sk.bones[size_t(hh.mid)].head);
    float best = 4.0f;
    for (int i = 0; i < 72; ++i) {
      const float th = glm::radians(5.0f * float(i));
      const vec3 dir = std::cos(th) * e1 + std::sin(th) * e2;
      if (dir.y > kElbowRise) continue;
      const vec3 E = S + u * x + dir * r, fd = W - E;
      if (glm::length(fd) < 1e-6f) continue;
      const float bend = std::acos(std::clamp(glm::dot(glm::normalize(fd), fingers), -1.0f, 1.0f));
      if (bend >= best) continue;
      if (M) {
        G[size_t(hh.mid)] = glm::translate(mat4(1), E) * glm::mat4_cast(glm::rotation(restDir, glm::normalize(fd)));
        G[size_t(hh.bone)] = glm::translate(mat4(1), W) * mat4(R);
        if (limbClearance(M->collision, G, hh.side).gap < kArmBodyMargin) continue;
      }
      best = bend;
      if (elbowDir) *elbowDir = dir;
    }
    return best;
  };
  // Reach + grasp of `socket` on prop p, arriving at `contact` (shared by reach/grasp and the hand-over receiver).
  auto reachTo = [&](const Hand& hand, int p, const std::string& socket, double start, double contact, bool grasp,
                     const std::string& what, bool turnedGrip = false, const GraspStyle& style = {}) -> Result<Plan> {
    if (contact < start + 6) return fail(std::format("{}: contact must be at least 6 frames after start", what));
    // T-171 (opt-in "wrap"): the prop rests where the palm ends and the fingers begin (its nearest line over the finger
    // roots), as far off the hand as the palm's measured surface needs for a prop of this radius; not on the middle of
    // the palm at a stand-off guessed from the palm's length. The fingers start on the prop and the thumb opposes them.
    Hand seated = hand;
    HandSkin skin;
    vec2 seat(0);  // (stand-off, station)
    const bool wrap = grasp && style.soft && style.soft->wrap && style.shape == "wrap";
    if (wrap) {
      skin = handSkin(characters_[size_t(hand.c)].asset.skeleton, characters_[size_t(hand.c)].rig.meshes, hand.bone, hand.side, hand.grip);
      const Plan rough = plan(hand, p, socket, contact);
      const float scale = glm::length(vec3(characterGlobals(size_t(hand.c), contact)[size_t(hand.bone)][0]));
      seat = vec2(skin.seat(rough.face ? 0.0f : rough.radius / std::max(scale, 1e-6f), hand.grip.palmLength), hand.grip.palmLength);
      if (seat.x > 0) seated.grip.palm = hand.grip.fingerDir * seat.y + hand.grip.palmNormal * seat.x;
    }
    const Hand& h = seated;
    if (style.soft && style.soft->clear > 0)  // T-171 "clear": a reach compiled again starts from its three keys
      if (auto it = gen.tracks.find(h.ik); it != gen.tracks.end())
        std::erase_if(it->second.keys, [&](const Key& k) { return k.frame > start + 1e-6 && k.frame < contact - 1e-6; });
    Plan pl = plan(h, p, socket, contact);
    const vec3 natural = boneAt(h, h.bone, start);
    vec3 back = -pl.inward * 0.05f;
    if (style.approach && glm::length(*style.approach) > 1e-6f)  // T-112b: the palm comes from the site's side
      back = glm::normalize(mat3(propWorld(size_t(p), contact)) * *style.approach) * 0.05f;
    // T-171: a natural grip comes in palm first (its elbow is planned for that side of the body), so it backs off
    // along the palm's normal like an authored grip.
    if (turnedGrip && !style.naturalElbow) {  // T-096 visibleGrip: never back off towards the body (the forearm would enter it)
      vec3 toBody = boneAt(h, h.root, contact) - pl.socket;
      toBody.y = 0;
      if (glm::length(toBody) > 1e-6f) {
        toBody = glm::normalize(toBody);
        back -= toBody * std::max(0.0f, glm::dot(back, toBody));
        back = glm::length(back) > 1e-6f ? glm::normalize(back) * 0.05f : vec3(0);
      }
    }
    const vec3 approach = pl.wrist + back + kUp * (turnedGrip && !style.naturalElbow && glm::length(back) < 0.025f ? 0.05f : 0.02f);
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
    // T-171 "clear": a hand that holds an upright prop (thumb up or down) rises with its palm already towards the prop
    // and its fingers hanging (the final rotation turned a quarter about the palm's normal), then swings its fingers level in the palm's own plane on
    // the way to the approach point. The shortest turn from a hanging hand points the fingers at the prop on the way.
    if (const vec3 thumb = pl.R * ((h.side == 'R' ? 1.0f : -1.0f) * glm::cross(h.grip.fingerDir, h.grip.palmNormal));
        grasp && style.soft && style.soft->clear > 0 && std::abs(thumb.y) > 0.7f) {
      const quat qa = glm::normalize(pl.orient * glm::angleAxis(1.5707963f, h.grip.palmNormal));
      const quat qb = glm::normalize(pl.orient * glm::angleAxis(-1.5707963f, h.grip.palmNormal));
      const quat hang = (qa * h.grip.fingerDir).y < (qb * h.grip.fingerDir).y ? qa : qb;  // the quarter turn that hangs the fingers
      const double fm = std::round(start + 0.55 * (pre - start)), fe = std::round(pre + 1);
      dropKeysAfter(gen, h.orient, start);
      key(gen, h.orient, start, rotationVector(hang), Interp::Linear);
      key(gen, h.orient, fm, rotationVector(hang), Interp::Linear);
      for (double f = fm + 1; f < fe; f += 1)
        key(gen, h.orient, f, rotationVector(glm::slerp(hang, pl.orient, float((f - fm) / (fe - fm)))), Interp::Linear);
      key(gen, h.orient, fe, rotationVector(pl.orient), Interp::Linear);
      key(gen, h.orient, contact, rotationVector(pl.orient), Interp::Linear);
      dropKeysAfter(gen, h.orient + ".weight", start);
      key(gen, h.orient + ".weight", fm, vec3(1));
      key(gen, h.orient + ".weight", contact, vec3(1));
    }
    const HandShape* rest = style.soft ? style.soft->rest() : nullptr;  // T-171 (opt-in)
    if (rest) keyRest(gen, h.pose, start, *rest);
    else key(gen, h.pose, start, clip.evaluate(h.pose, start, kRelaxed));
    if (style.band) {  // T-112b: the finger contact band of the grasp site (track contract with T-051, design 5)
      const PropAsset& A = propAssets_[size_t(p)];
      const GraspShape gs = graspShape(A, A.sockets.at(socket).translation);
      const float k = glm::length(vec3(propWorld(size_t(p), contact)[0]));
      const float c0 = glm::length(gs.axis) > 0 ? glm::dot(gs.centre, glm::normalize(gs.axis)) : 0.0f;
      key(gen, h.pose + ".band", start, vec3((style.band->x - c0) * k, (style.band->y - c0) * k, style.thumb), Interp::Step);
      if (interactionOptionsFromJson(scene_.interaction).value_or(InteractionOptions{}).graspFit)  // T-138 (opt-in)
        key(gen, h.pose + ".bandFit", start, vec3(1), Interp::Step);
      if (style.soft && style.soft->widen) {  // T-171 (opt-in): T-138 fit + T-157 (a) wider band
        key(gen, h.pose + ".bandFit", start, vec3(1), Interp::Step);
        key(gen, h.pose + ".bandFitOptions", start, vec3(style.soft->widen->x, 0, style.soft->widen->y), Interp::Step);
      }
    }
    // T-112c: on a box face (verb grasps with the finger gate, "graspFace": true) the fingers search the face slab:
    // wrap, pinch and palm (the flat hand's fingers rest on the face instead of standing in it or off it).
    const bool faceSearch = grasp && style.face && pl.face &&
                            (!style.hs || style.hs->search != HandShapeSearch::None || style.hs->id == "palm");
    if (style.hs) {  // T-112b / T-112c: the table shape's approach and held poses, and its contact search
      const HandShape& sh = *style.hs;
      keyShapeRest(gen, h.pose, start, sh, clip.evaluate(h.pose, start, kRelaxed));
      keyHandShape(gen, h.pose, pre, sh, true);
      if (contact - 4 > pre + 1e-6) keyHandShape(gen, h.pose, contact - 4, sh, true);
      keyHandShape(gen, h.pose, contact, sh, !grasp);
      if (grasp && sh.search == HandShapeSearch::Pinch && !faceSearch) {  // index + thumb on a small sphere just inside the socket
        const float r = *sh.pinchRadius;
        key(gen, h.pose + ".grasp", start, h.grip.palm + glm::transpose(pl.R) * pl.inward * r, Interp::Step);
        key(gen, h.pose + ".graspRadius", start, vec3(r), Interp::Step);
        key(gen, h.pose + ".graspAxis", start, vec3(0), Interp::Step);
        keyClose(h, start, contact, style);
      }
    } else {
      // T-171 (opt-in): the stagger reads each finger's pose late (the little finger three steps), so the open hand is
      // keyed that much earlier: the last finger opens when the hand opened before, the others lead it.
      const double open = style.soft ? std::max(start + 0.15 * (contact - start), pre - 3.0 * double(style.soft->stagger)) : pre;
      key(gen, h.pose, open, kOpen);
      key(gen, h.pose, contact, kOpen);
      if (rest) keyRestFingers(gen, h.pose, open, *rest, kOpen), keyRestFingers(gen, h.pose, contact, *rest, kOpen);
    }
    pl.faceGrasp = faceSearch;
    if (faceSearch) {  // T-112c: the per-finger grasp on the box face (T-051 slab: centre, half thickness, inward normal)
      key(gen, h.pose + ".grasp", start, pl.centre, Interp::Step);
      key(gen, h.pose + ".graspRadius", start, vec3(pl.radius), Interp::Step);
      key(gen, h.pose + ".graspAxis", start, vec3(0), Interp::Step);
      key(gen, h.pose + ".graspFace", start, glm::transpose(pl.R) * pl.inward, Interp::Step);
      keyClose(h, start, contact, style);
    } else if (grasp && style.shape == "wrap") {  // fingers close on the prop's size by contact search (anim: applyHandPose)
      key(gen, h.pose + ".grasp", start, pl.centre, Interp::Step);
      key(gen, h.pose + ".graspRadius", start, vec3(pl.radius), Interp::Step);
      key(gen, h.pose + ".graspAxis", start, pl.axis, Interp::Step);
      if (wrap) {  // T-171 (opt-in): the joint-by-joint wrap with the measured skin; the seat the wrist was planned with
        key(gen, h.pose + ".wrap", start, vec3(1, skin.finger, skin.thumb), Interp::Step);
        if (seat.x > 0) key(gen, h.pose + ".seat", start, vec3(seat, 0), Interp::Step);
      }
      keyClose(h, start, contact, style);
    }
    const ReachMechanics rm = reachMechanicsFromJson(scene_.reachMechanics).value_or(ReachMechanics{});
    // T-134 E1a ease: the same path (start -> approach -> contact), keyed every frame on a slow-in / slow-out profile.
    std::vector<vec3> planned;
    if (rm.enabled && rm.ease) {
      Track& T = gen.tracks[h.ik];
      // One curve through the three points of this reach only (a reach compiled again, as the hand-over trials do,
      // gives the same keys): a quadratic Bezier that passes the approach point at its chord fraction. The smooth
      // keys stop at the approach point (clamped tangents), which is a corner for a wrist that does not slow there.
      const vec3 p0 = T.evaluate(start), p2 = pl.wrist;
      const float d1 = glm::distance(p0, approach), d2 = glm::distance(approach, p2);
      const float tA = std::clamp(d1 / std::max(d1 + d2, 1e-6f), 0.15f, 0.85f);
      vec3 p1 = (approach - (1 - tA) * (1 - tA) * p0 - tA * tA * p2) / (2 * tA * (1 - tA));
      // T-134 E1b: the approach point gives the direction the hand arrives from, not a point to pass: the control
      // point lies on the line contact -> approach, twice as far out, so the bend is spread over the whole reach
      // instead of sitting just before the contact.
      if (rm.arcs) p1 = p2 + float(rm.approachReach) * (approach - p2);
      if (rm.arcs && glm::distance(p0, p2) >= float(rm.arcMinChordM)) {  // T-134 E1b: never (nearly) a straight chord
        const float L = glm::distance(p0, p2);
        const vec3 c = (p2 - p0) / L, mid = 0.5f * (p0 + p2);
        vec3 off = (p1 - mid) - c * glm::dot(p1 - mid, c);  // the curve is half of this away from the chord
        if (0.5f * glm::length(off) < float(rm.arc) * L) {
          vec3 n = glm::length(off) > 1e-4f ? off : kUp - c * c.y;
          if (glm::length(n) > 1e-4f) p1 += glm::normalize(n) * (2 * float(rm.arc) * L - glm::length(off));
        }
      }
      std::erase_if(T.keys, [&](const Key& k) { return k.frame > start + 1e-6 && k.frame < contact - 1e-6; });
      constexpr int kSamples = 96;
      std::vector<vec3> P(kSamples + 1);
      std::vector<double> len(kSamples + 1, 0.0);
      for (int i = 0; i <= kSamples; ++i) {
        const float u = float(i) / kSamples;
        P[size_t(i)] = (1 - u) * (1 - u) * p0 + 2 * u * (1 - u) * p1 + u * u * p2;
        if (i > 0) len[size_t(i)] = len[size_t(i - 1)] + double(glm::distance(P[size_t(i)], P[size_t(i - 1)]));
      }
      const int n = int(std::ceil(contact - start - 1e-6));
      for (int j = 0; j <= n; ++j) {
        const double f = std::min(start + j, contact);
        const double want = reachEase((f - start) / (contact - start), rm.easePeak) * len.back();
        const size_t i = std::min(size_t(std::upper_bound(len.begin(), len.end(), want) - len.begin()), size_t(kSamples));
        const double seg = i > 0 ? len[i] - len[i - 1] : 0.0;
        const vec3 v = j == n ? P.back() : i == 0 ? P[0] : glm::mix(P[i - 1], P[i], float(seg > 1e-12 ? (want - len[i - 1]) / seg : 1.0));
        T.setKey({f, v, j == n ? Interp::Smooth : Interp::Linear});  // after the contact: the smooth key it was
        planned.push_back(v);
      }
      // The IK weight comes in on the same curve as the target travels, reaching 1 at the contact. A weight that is
      // already full at the approach point stops rising while the target is still fast, and the wrist brakes hard.
      Track& W = gen.tracks[h.ik + ".weight"];
      const float w0 = W.evaluate(start).x;
      std::erase_if(W.keys, [&](const Key& k) { return k.frame > start + 1e-6 && k.frame < contact - 1e-6; });
      for (int j = 1; j < n; ++j)
        W.setKey({start + j, vec3(w0 + (1 - w0) * float(reachEase(std::min(1.0, double(j) / (rm.weightFull * (contact - start))), rm.weightPeak))),
                  Interp::Linear});
      W.setKey({start, vec3(w0), Interp::Linear});
    }
    // T-134 E1a anticipation: the body lead (applyReachLead), added to the leads other reaches of this character keyed.
    if (rm.enabled && rm.anticipation) {
      const Skeleton& sk = characters_[size_t(h.c)].asset.skeleton;
      const double fps = scene_.rate.fps(), N = contact - start;
      const double A = std::min(std::round(rm.anticipationSec * fps), std::max(0.0, start - double(scene_.frameStart)));
      const double R = std::max(2.0, std::round(rm.recoverSec * fps));
      const vec3 shoulder = boneAt(h, h.root, start);
      const vec3 reachDir = pl.wrist - shoulder;
      vec3 d(reachDir.x, 0, reachDir.z);
      if (glm::length(d) > 1e-4f && glm::length(reachDir) > 1e-4f) {
        d = glm::normalize(d);
        // Near props need less of the body: the lead scales with how far along the arm the prop is.
        const float k = std::clamp((glm::length(reachDir) / std::max(h.armLength, 1e-4f) - 0.4f) / 0.5f, 0.25f, 1.0f);
        const int chest = sk.find("chest") >= 0 ? sk.find("chest") : sk.find("spine");
        vec3 o = chest >= 0 ? shoulder - boneAt(h, chest, start) : vec3(0);
        o.y = 0;
        const float side = glm::length(o) > 1e-4f ? glm::dot(glm::cross(kUp, glm::normalize(o)), d) : 0.0f;
        const vec3 lead = k * (glm::cross(kUp, d) * glm::radians(float(rm.leanDeg)) + kUp * glm::radians(float(rm.twistDeg)) * side);
        // One record per reach (a reach compiled again replaces its own); the character's tracks are the sum of them.
        const std::string shoulderTrack = h.prefix + "reach.shoulder." + sk.bones[size_t(h.root)].name;
        // The clavicle of this arm (rig names as in content/rig_profiles/body_mechanics.json) turns its outer end
        // towards the prop; the hips shift towards it.
        std::string clavicleTrack;
        vec3 clavicleLead(0);
        for (const char* base : {"clavicle.", "shoulder.", "DEF-shoulder."})
          if (const int cb = sk.find(std::string(base) + h.side); cb >= 0 && clavicleTrack.empty()) {
            const vec3 arm = shoulder - boneAt(h, cb, start);
            const vec3 axis = glm::cross(arm, reachDir);
            if (glm::length(axis) > 1e-8f) {
              clavicleTrack = h.prefix + "reach.clavicle." + sk.bones[size_t(cb)].name;
              clavicleLead = glm::normalize(axis) * (k * glm::radians(float(rm.clavicleDeg)));
            }
          }
        const vec3 hipLead = d * (k * float(rm.hipShiftM));
        std::erase_if(ctx.reachLeads, [&](const InteractionContext::ReachLead& l) { return l.character == h.c && l.side == h.side && l.start == start; });
        const vec3 shoulderLead = glm::normalize(reachDir) * (k * float(rm.shoulderM));
        // E1c overlap: the torso follows its lead through a damped response (it overshoots a little and settles, also
        // after the lead is given back); the head's counter turn has a later, looser one, so the head first goes
        // with the torso and then catches up. Without overlap both follow the plain envelope.
        std::vector<float> torsoKernel{1.0f}, headKernel{1.0f};
        double shift = 0;
        if (rm.overlap) {
          torsoKernel = followKernel(0.0f, float(rm.torsoSettleSec * fps), float(rm.torsoOvershoot));
          for (size_t i = 0; i < torsoKernel.size(); ++i) shift += double(i) * double(torsoKernel[i]);
          headKernel = followKernel(float(rm.headLagSec * fps), float(rm.headSettleSec * fps), float(rm.headOvershoot));
        }
        // Settle: when the hand stops at the contact the body runs on a little past its lead, swings back and comes
        // to rest (a damped swing of settleAmount of the lead, period settleSec), on top of the lead being given back.
        auto settle = [&](double t) {
          if (!rm.overlap || t <= 0) return 0.0;
          const double period = std::max(2.0, rm.settleSec * fps);
          return rm.settleAmount * std::exp(-2.0 * t / period) * std::sin(6.283185307179586 * t / period);
        };
        auto write = [&](float scale) {
          std::erase_if(ctx.reachLeads, [&](const InteractionContext::ReachLead& l) { return l.character == h.c && l.side == h.side && l.start == start; });
          if (scale > 0)
            ctx.reachLeads.push_back({h.c, h.side, start, contact, A, R, scale * lead, scale * shoulderLead, shoulderTrack, scale * clavicleLead,
                                      clavicleTrack, scale * hipLead});
          gen.tracks[h.prefix + "reach.lead"].keys.clear();
          gen.tracks[shoulderTrack].keys.clear();
          gen.tracks.erase(h.prefix + "reach.head");
          gen.tracks.erase(h.prefix + "reach.hip");
          if (!clavicleTrack.empty()) gen.tracks.erase(clavicleTrack);
          for (const auto& l : ctx.reachLeads)
            if (l.character == h.c) {
              gen.tracks[l.shoulderTrack].keys.clear();
              if (!l.clavicleTrack.empty()) gen.tracks.erase(l.clavicleTrack);
            }
          for (const auto& l : ctx.reachLeads) {
            if (l.character != h.c) continue;
            const double n = l.contact - l.start;
            // The envelope through a follow-through response (kernel[k]: weight of the envelope k frames ago),
            // read `shift` frames ahead so the torso's own timing stays where the plain envelope has it.
            auto addKeys = [&](const std::string& track, vec3 full, const std::vector<float>& kernel) {
              Track& T = gen.tracks[track];
              const Track before = T;
              const double tail = double(kernel.size()) - 1;
              for (double f = l.start - l.anticipation - std::ceil(shift); f <= l.contact + l.recover + tail + 1e-6; f += 1) {
                double e = 0;
                for (size_t k = 0; k < kernel.size(); ++k) {
                  const double at = f + shift - double(k);
                  e += double(kernel[k]) * (reachLead((at - l.start) / n, l.anticipation / n, l.recover / n, rm) + settle(at - l.contact));
                }
                T.setKey({f, (before.keys.empty() ? vec3(0) : before.evaluate(f)) + full * float(e), Interp::Linear});
              }
            };
            addKeys(h.prefix + "reach.lead", l.lead, torsoKernel);
            addKeys(l.shoulderTrack, l.shoulder, torsoKernel);
            if (!l.clavicleTrack.empty()) addKeys(l.clavicleTrack, l.clavicle, torsoKernel);
            if (glm::length(l.hip) > 0) addKeys(h.prefix + "reach.hip", l.hip, torsoKernel);
            if (rm.overlap) addKeys(h.prefix + "reach.head", -float(rm.headStabilize) * l.lead, headKernel);
          }
          if (gen.tracks[h.prefix + "reach.lead"].keys.empty()) gen.tracks[h.prefix + "reach.lead"].keys = {{start, vec3(0), Interp::Linear}};
        };
        // The lead must not cost the arm its room: a torso that leans into its own reaching arm would have the
        // collision planner push the wrist away around the contact. The largest share of the lead is kept that leaves
        // the arm (after the planner's elbow swing) as clear of the body at the contact as it is without the lead,
        // or at the planner's margin.
        const bool canClear = size_t(h.c) < clearance_.size() && clearance_[size_t(h.c)].valid;
        auto gapAtContact = [&] { return swungArmGap(clearance_[size_t(h.c)], characterGlobals(size_t(h.c), contact), h.side); };
        write(0);
        const float gap0 = canClear ? gapAtContact() : 0.0f;
        for (float scale : {1.0f, 0.75f, 0.5f, 0.25f}) {
          write(scale);
          if (!canClear || gapAtContact() >= std::min(gap0, kArmBodyMargin) - 0.0002f) break;
          write(0);
        }
        key(gen, h.prefix + "reach.lead.params", double(scene_.frameStart),
            vec3(float(rm.successionSec * fps), float(rm.hipShare), float(rm.headStabilize)), Interp::Step);
      }
    }
    if (style.naturalElbow) {  // T-171 (opt-in): the elbow that keeps the wrist straight at the contact
      vec3 want(0);
      if (wristBend(h, contact, pl.wrist, pl.R, &want) < 3.5f) {
        // It comes round early, while the arm is still long (the circle the elbow moves on is small): the forearm then
        // rises on its own side of the body instead of crossing the flank late.
        const std::string track = h.prefix + "elbow." + characters_[size_t(h.c)].asset.skeleton.bones[size_t(h.bone)].name;
        key(gen, track, start, clip.evaluate(track, start, vec3(0)));
        dropKeysAfter(gen, track, start);
        key(gen, track, start + 0.35 * (contact - start), want);
        key(gen, track, contact, want);
      }
    }
    // T-171 (opt-in "clear"): the way in keeps the hand off the prop. Per frame the digits (joints and tips, with the
    // measured skin) and the palm are checked against the prop as a solid; where they come closer than `clear` the
    // wrist target moves out, level, away from the prop's axis (centre), by what is missing. The pushes are eased in
    // time (cosine-weighted maximum over +-4 frames) and fade to nothing over the last 3 frames, so the contact
    // stays exact. The wrist track becomes per-frame keys over the reach only when some push is needed.
    if (grasp && style.soft && style.soft->clear > 0) {
      const Skeleton& sk = characters_[size_t(h.c)].asset.skeleton;
      const HandSkin hs = wrap ? skin : handSkin(sk, characters_[size_t(h.c)].rig.meshes, h.bone, h.side, h.grip);
      const float tipR = fingertipRadius(sk, h.side);
      struct Sample {
        int bone;
        vec3 local;  // from the bone's rest head
        float r;
      };
      std::vector<Sample> samples;
      const std::string sd = std::string(".") + h.side;
      auto digit = [&](int a, int b, float r) {
        if (a < 0 || b < 0) return;
        const vec3 ha = sk.bones[size_t(a)].head, hb = sk.bones[size_t(b)].head;
        samples.push_back({a, vec3(0), r});
        samples.push_back({b, vec3(0), r});
        int c = -1, cn = 0;
        for (size_t i = 0; i < sk.bones.size(); ++i)
          if (sk.bones[i].parent == b) c = int(i), ++cn;
        if (cn == 1) samples.push_back({c, vec3(0), r}), samples.push_back({c, sk.bones[size_t(c)].head - hb, r});
        else samples.push_back({b, hb - ha, r});
      };
      for (int k = 0; k < 4; ++k) digit(sk.find(std::format("f{}a{}", k, sd)), sk.find(std::format("f{}b{}", k, sd)), hs.finger > 0 ? hs.finger : tipR);
      digit(sk.find("thumbA" + sd), sk.find("thumbB" + sd), hs.thumb > 0 ? hs.thumb : tipR);
      for (float t : {0.35f, 0.65f, 0.9f}) {  // the palm: spheres under its surface
        float top = 0.22f * h.grip.palmLength;
        for (const vec2& v : hs.profile)
          if (std::abs(v.x - t * h.grip.palmLength) < 0.004f) top = std::max(top, v.y);
        samples.push_back({h.bone, h.grip.fingerDir * (t * h.grip.palmLength), top});
      }
      const PropAsset& A = propAssets_[size_t(p)];
      const GraspShape gs0 = graspShape(A, A.sockets.at(socket).translation);
      const int f0 = int(std::ceil(start + 1e-6)), f1 = int(std::floor(contact - 1e-6));
      const int n = f1 - f0 + 1;
      Track& T = gen.tracks[h.ik];
      for (int pass = 0; pass < 2 && n > 0; ++pass) {
        std::vector<vec3> raw(size_t(n), vec3(0));
        bool any = false;
        for (int i = 0; i < n; ++i) {
          const double f = double(f0 + i);
          const std::vector<mat4> G = characterGlobals(size_t(h.c), f);
          const mat4 P = propWorld(size_t(p), f), Pi = glm::inverse(P);
          const float ps = glm::length(vec3(P[0]));
          float gap = 1e9f;
          for (const Sample& sm : samples)
            gap = std::min(gap, propSolidDistance(A, vec3(Pi * G[size_t(sm.bone)] * vec4(sm.local, 1))) * ps - sm.r * glm::length(vec3(G[size_t(sm.bone)][0])));
          if (gap >= style.soft->clear) continue;
          const vec3 centre = vec3(P * vec4(gs0.centre, 1));
          vec3 out = vec3(G[size_t(h.bone)][3]) - centre;
          if (glm::length(gs0.axis) > 0) {
            const vec3 ax = glm::normalize(mat3(P) * gs0.axis);
            out -= ax * glm::dot(out, ax);
          }
          if (glm::length(out) < 1e-5f) continue;
          raw[size_t(i)] = glm::normalize(out) * (style.soft->clear - gap);
          any = true;
        }
        if (!any) break;
        std::vector<vec3> at(size_t(n), vec3(0));
        for (int i = 0; i < n; ++i) at[size_t(i)] = T.evaluate(double(f0 + i));
        for (int i = 0; i < n; ++i) {
          float size = 0, wsum = 0;
          vec3 dir(0);
          for (int j = std::max(0, i - 4); j <= std::min(n - 1, i + 4); ++j) {
            const float w = 0.5f * (1.0f + std::cos(3.14159265f * float(j - i) / 5.0f)), l = glm::length(raw[size_t(j)]);
            size = std::max(size, w * l);
            dir += w * raw[size_t(j)], wsum += w * l;
          }
          if (size <= 0 || glm::length(dir) < 1e-9f) continue;
          const float fade = std::clamp(float(contact - double(f0 + i)) / 3.0f, 0.0f, 1.0f);
          at[size_t(i)] += glm::normalize(dir) * (size * fade);
        }
        std::erase_if(T.keys, [&](const Key& k) { return k.frame > start + 1e-6 && k.frame < contact - 1e-6; });
        for (int i = 0; i < n; ++i) T.setKey({double(f0 + i), at[size_t(i)], Interp::Linear});
      }
    }
    correct(h, contact, [&] { return socketWorld(p, socket, contact)[3] - vec4(handGripPoint(size_t(h.c), h.side, contact), 1); });
    if (!planned.empty()) {  // spread the contact correction along the eased path (no step into the last frame)
      Track& T = gen.tracks[h.ik];
      const vec3 delta = T.evaluate(contact) - planned.back();
    }
    return pl;
  };
  // T-096 visibleGrip (interaction option, opt-in): on a round prop (a cylinder's side: the grasp shape has an axis)
  // the same grip fits anywhere around the axis, so the palm may meet the prop at the socket turned about it. The
  // grasp takes the smallest turn (kGripStep steps, at most kGripTurnMax either way) that puts the palm's side of the
  // prop at least kGripHide away from the shot camera (seen from above), so the hand is beside or behind the prop and
  // the prop stays in view; when no allowed turn gets there, the allowed turn that gets furthest. Allowed: the palm's
  // side within kGripFaceMax of the direction to the character's shoulder (a hand never grips the far side of a prop)
  // and, for a hand-over receiver, at least kGripApart from the giver's socket (the hands do not meet), and an arm that
  // stays clear of the body (the planner's limb capsules for that grip, elbow within its swing limit: at least the
  // margin, or as clear as the authored grip). An authored grip that already keeps the prop in view, or a box or
  // sphere, keeps the authored socket. A turned grip often
  // holds the prop's near side (palm away from the body, as one takes a glass): its approach backs off sideways and
  // up, never towards the body (reachTo), so the short forearm does not enter it. The turned socket is added to
  // this scene's copy of the prop asset as "<socket>@<character>.<hand>" (the asset file is unchanged); a grasp uses
  // only its position.
  const bool visibleGrip = interactionOptionsFromJson(scene_.interaction).value_or(InteractionOptions{}).visibleGrip;
  auto visibleSocket = [&](const Hand& hh, int p, const std::string& socket, double f, const std::string& avoid) -> std::string {
    constexpr float kGripTurnMax = 90.0f, kGripStep = 5.0f, kGripHide = 65.0f, kGripFaceMax = 100.0f, kGripApart = 90.0f;  // degrees
    PropAsset& A = propAssets_[size_t(p)];
    const AssetTransform st = A.sockets.at(socket);
    const GraspShape gs = graspShape(A, st.translation);
    if (glm::length(gs.axis) < 1e-6f) return socket;
    const vec3 ax = glm::normalize(gs.axis);
    const mat4 P = propWorld(size_t(p), f);
    auto turned = [&](vec3 t, float deg) { return gs.centre + glm::angleAxis(glm::radians(deg), ax) * (t - gs.centre); };
    auto outward = [&](vec3 t) {  // horizontal world direction from the prop's axis to the point
      const vec3 onAxis = gs.centre + ax * glm::dot(t - gs.centre, ax);
      vec3 o = vec3(P * vec4(t, 1)) - vec3(P * vec4(onAxis, 1));
      o.y = 0;
      return glm::length(o) > 1e-6f ? glm::normalize(o) : vec3(0);
    };
    const vec3 c0 = vec3(P * vec4(gs.centre, 1));
    auto flat = [](vec3 v) {
      v.y = 0;
      return glm::length(v) > 1e-6f ? glm::normalize(v) : vec3(0);
    };
    const vec3 toCam = flat(cameraAt(f).position - c0), toChar = flat(boneAt(hh, hh.root, f) - c0);
    const vec3 avoidDir = avoid.empty() || !A.sockets.count(avoid) ? vec3(0) : outward(A.sockets.at(avoid).translation);
    if (toCam == vec3(0) || toChar == vec3(0)) return socket;
    const float cosHide = std::cos(glm::radians(kGripHide)), cosFace = std::cos(glm::radians(kGripFaceMax)),
                cosApart = std::cos(glm::radians(kGripApart));
    if (glm::dot(outward(st.translation), toCam) <= cosHide) return socket;  // the authored grip already keeps it in view
    // The arm's clearance for a grip (the planner's own measure: forearm and hand capsules against the body), with the
    // elbow from a two-bone solve in the arm's present plane, swung within the character's limit as the planner would.
    const BodyClearanceModel* M = size_t(hh.c) < clearance_.size() && clearance_[size_t(hh.c)].valid ? &clearance_[size_t(hh.c)] : nullptr;
    auto armGap = [&](vec3 t) -> float {
      if (!M) return 1e9f;
      AssetTransform probe = st;
      probe.translation = t;
      const std::string tmp = socket + "@probe";
      A.sockets[tmp] = probe;
      const Plan pl = plan(hh, p, tmp, f);
      A.sockets.erase(tmp);
      const Skeleton& sk = characters_[size_t(hh.c)].asset.skeleton;
      std::vector<mat4> G = characterGlobals(size_t(hh.c), f);
      const vec3 S(G[size_t(hh.root)][3]), E0(G[size_t(hh.mid)][3]), W = pl.wrist;
      const float a = glm::distance(sk.bones[size_t(hh.root)].head, sk.bones[size_t(hh.mid)].head);
      const float b = glm::distance(sk.bones[size_t(hh.mid)].head, sk.bones[size_t(hh.bone)].head);
      const float d = std::clamp(glm::distance(S, W), 1e-4f, a + b - 1e-5f);
      const vec3 u = glm::normalize(W - S);
      vec3 pole = (E0 - S) - u * glm::dot(E0 - S, u);
      pole = glm::length(pole) > 1e-6f ? glm::normalize(pole) : glm::normalize(glm::cross(u, kUp));
      const float x = (a * a - b * b + d * d) / (2 * d), r = std::sqrt(std::max(0.0f, a * a - x * x));
      const vec3 restDir = glm::normalize(sk.bones[size_t(hh.bone)].head - sk.bones[size_t(hh.mid)].head);
      float bestGap = -1e9f;
      const float lim = std::min(M->collision.maxElbowSwing, glm::radians(30.0f));
      for (float th = -lim; th <= lim + 1e-4f; th += glm::radians(5.0f)) {
        const vec3 E = S + u * x + (glm::angleAxis(th, u) * pole) * r;
        const vec3 fd = W - E;
        if (glm::length(fd) < 1e-6f) continue;
        G[size_t(hh.mid)] = glm::translate(mat4(1), E) * glm::mat4_cast(glm::rotation(restDir, glm::normalize(fd)));
        G[size_t(hh.bone)] = glm::translate(mat4(1), W) * mat4(pl.R);
        bestGap = std::max(bestGap, limbClearance(M->collision, G, hh.side).gap);
      }
      return bestGap;
    };
    const float need = std::min(kArmBodyMargin, armGap(st.translation));  // never worse than the margin (or the authored)
    float best = 0, bestCam = glm::dot(outward(st.translation), toCam);
    for (float t = kGripStep; t <= kGripTurnMax + 1e-3f; t += kGripStep) {
      bool hit = false;
      for (float deg : {t, -t}) {
        const vec3 o = outward(turned(st.translation, deg));
        const float onChar = glm::dot(o, toChar);
        if (o == vec3(0) || onChar < cosFace || (avoidDir != vec3(0) && glm::dot(o, avoidDir) > cosApart)) continue;
        const float onCam = glm::dot(o, toCam);
        if (onCam >= bestCam - 1e-4f || armGap(turned(st.translation, deg)) < need) continue;
        best = deg, bestCam = onCam;  // the best so far (smallest turn first)
        if (onCam <= cosHide) {
          hit = true;
          break;
        }
      }
      if (hit) break;
    }
    if (best == 0) return socket;
    AssetTransform t = st;
    t.translation = turned(st.translation, best);
    const std::string name = std::format("{}@{}.{}", socket, hh.who, hh.side);
    A.sockets[name] = t;
    return name;
  };
  // The grasp point of an upright round prop, turned about the prop's axis by the smallest angle (kNaturalStep steps,
  // never to the far side of the prop from the shoulder: kNaturalFace) at which this hand takes it thumb up with a
  // wrist bend of at most kNaturalWrist; when no turn gets there, the turn with the smallest bend. The authored point
  // is kept when it already does, when the prop is not round or its axis is not near the vertical. Added to this
  // scene's copy of the prop asset as "<socket>@<character>.<hand>", as a visibleGrip turn is (the asset file is
  // unchanged).
  auto naturalSocket = [&](const Hand& hh, int p, const std::string& socket, double f) -> std::string {
    constexpr float kNaturalWrist = 30.0f, kNaturalStep = 5.0f, kNaturalFace = 100.0f;  // degrees
    PropAsset& A = propAssets_[size_t(p)];
    const AssetTransform st = A.sockets.at(socket);
    const GraspShape gs = graspShape(A, st.translation);
    if (glm::length(gs.axis) < 1e-6f) return socket;
    const vec3 ax = glm::normalize(gs.axis);
    const mat4 P = propWorld(size_t(p), f);
    const vec3 up = glm::normalize(mat3(P) * ax);
    if (std::abs(up.y) < 0.7f) return socket;
    const vec3 c0 = vec3(P * vec4(gs.centre, 1));
    vec3 toChar = boneAt(hh, hh.root, f) - c0;
    toChar.y = 0;
    if (glm::length(toChar) < 1e-4f) return socket;
    toChar = glm::normalize(toChar);
    auto turned = [&](float deg) { return gs.centre + glm::angleAxis(glm::radians(deg), ax) * (st.translation - gs.centre); };
    auto bendAt = [&](float deg) {  // the wrist bend of the grip at this turn; 4 = not a grip this hand can take
      vec3 o = vec3(P * vec4(turned(deg), 1)) - c0;
      o.y = 0;
      if (glm::length(o) < 1e-6f || glm::dot(glm::normalize(o), toChar) < std::cos(glm::radians(kNaturalFace))) return 4.0f;
      AssetTransform probe = st;
      probe.translation = turned(deg);
      const std::string tmp = socket + "@probe";
      A.sockets[tmp] = probe;
      const Plan pl = plan(hh, p, tmp, f);
      A.sockets.erase(tmp);
      const vec3 thumb = pl.R * ((hh.side == 'R' ? 1.0f : -1.0f) * glm::cross(hh.grip.fingerDir, hh.grip.palmNormal));
      if (thumb.y < 0.7f) return 4.0f;  // the planner would turn the hand thumb down here
      return wristBend(hh, f, pl.wrist, pl.R, nullptr);
    };
    float best = 0, bestBend = bendAt(0);
    const float limit = glm::radians(kNaturalWrist);
    for (float t = kNaturalStep; t <= 180.0f + 1e-3f && bestBend > limit; t += kNaturalStep)
      for (float deg : {t, -t}) {
        const float bend = bendAt(deg);
        if (bend < bestBend - 1e-4f) best = deg, bestBend = bend;
        if (bestBend <= limit) break;
      }
    if (best == 0) return socket;
    AssetTransform t = st;
    t.translation = turned(best);
    const std::string name = std::format("{}@{}.{}", socket, hh.who, hh.side);
    A.sockets[name] = t;
    return name;
  };
  // Lets go: fingers open, the wrist backs away from the prop and the arm returns to its own animation by `end`.
  auto release = [&](const Hand& h, const quat& orient, double from, double end, vec3 retreat, const std::string& shape = "wrap",
                     bool faceGrasp = false, const HandShape* rest = nullptr) {
    const vec3 wrist = clip.evaluate(h.ik, from, vec3(0));
    {  // T-171 (opt-in): a natural grip's elbow goes back to the arm solve's own by `end`
      const std::string track = h.prefix + "elbow." + characters_[size_t(h.c)].asset.skeleton.bones[size_t(h.bone)].name;
      if (const Track* t = clip.find(track); t && !t->keys.empty()) {
        const vec3 now = t->evaluate(from);
        key(gen, track, from, now);
        key(gen, track, end, vec3(0));
      }
    }
    if (const HandShape* sh = tableShape(shape)) {  // T-112b / T-112c: the shape opens (slow-out of its held pose)
      keyHandShape(gen, h.pose, from, *sh, false);
      keyHandShape(gen, h.pose, from + 3, *sh, true);
      key(gen, h.pose, end, kRelaxed);
      keyShapeRest(gen, h.pose, end, *sh, kRelaxed);
      if (sh->search != HandShapeSearch::None || faceGrasp) {  // a contact search (or a box-face search) lets go
        key(gen, h.pose + ".grasp.weight", from, vec3(1));
        key(gen, h.pose + ".grasp.weight", from + 5, vec3(0));
      }
    } else {
      key(gen, h.pose + ".grasp.weight", from, vec3(1));
      key(gen, h.pose + ".grasp.weight", from + 5, vec3(0));
      key(gen, h.pose, from, kOpen);
      key(gen, h.pose, from + 3, kOpen);
      if (rest) {  // T-171 (opt-in): back to the rest shape
        keyRestFingers(gen, h.pose, from, *rest, kOpen), keyRestFingers(gen, h.pose, from + 3, *rest, kOpen);
        keyRest(gen, h.pose, end, *rest);
      } else {
        key(gen, h.pose, end, kRelaxed);
      }
    }
    key(gen, h.ik, from + 1, wrist);
    key(gen, h.ik, std::max(from + 6, end - 4), wrist + retreat);
    key(gen, h.ik, end, wrist + retreat);
    arcMove(h, from + 1, std::max(from + 6, end - 4));  // T-134 E1b: the hand's way back is an arc too
    key(gen, h.ik + ".weight", from + 1, vec3(1));
    key(gen, h.ik + ".weight", end, vec3(0));
    key(gen, h.orient, end, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", from + 1, vec3(1));
    key(gen, h.orient + ".weight", end, vec3(0));
  };
  // T-186 (only after a fingerClose "grip": "natural" grasp): "<who>/collision.still.<hand>" is 1 from the contact to
  // the start of the hand's next move (lift, place or hand-over), 0 after it. The prop still stands where it was when
  // the hand took it, so the clearance pass does not move the wrist in that span (as in a frozen span), no push ramp
  // crosses it (as T-134 reachMechanics does at its pinned frames; a ramp that crossed it moved the hand, and the prop
  // with it, into the table) and the elbow swing keeps the forearm out there (writeArmPole). Nothing evaluates the
  // track itself; written only by natural grips.
  auto stillTrack = [&](const Hand& hh) {
    return hh.prefix + "collision.still." + characters_[size_t(hh.c)].asset.skeleton.bones[size_t(hh.bone)].name;
  };
  auto endStill = [&](const Hand& hh, double from) {
    auto it = gen.tracks.find(stillTrack(hh));
    if (it == gen.tracks.end() || it->second.keys.empty() || it->second.keys.back().value.x < 0.5f || it->second.keys.back().frame > from) return;
    key(gen, it->first, from + 0.5, vec3(0), Interp::Step);  // the move's first frame keeps the contact's wrist: still in the span
  };
  auto held = [&](const Hand& h, const std::string& what) -> Result<int> {
    auto it = ctx.hands.find({h.c, h.side});
    const int p = it == ctx.hands.end() ? -1 : it->second.prop;
    if (p < 0) return fail(std::format("{}: '{}' holds nothing in hand.{} at this point", what, h.who, h.side));
    if (it->second.follower)
      return fail(std::format("{}: hand.{} of '{}' is the second hand of a two-hand grasp of '{}': act with the leading hand", what,
                              h.side, h.who, scene_.props[size_t(p)].name));
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
    const std::string authoredSocket = str(a, "socket", "grip");
    if (auto r = requireSocket(p, authoredSocket, what); !r) return std::unexpected(r.error());
    if (auto it = ctx.hands.find({c, h.side}); it != ctx.hands.end() && it->second.prop >= 0)
      return fail(std::format("{}: '{}' already holds '{}' in hand.{}", what, who, scene_.props[size_t(it->second.prop)].name, h.side));
    const double contact = num(a, "contact", start + beat("reach", 14, c));
    const bool grasp = flag(a, "grasp", true);
    // T-112b grasp style (keys written by the verb expander; absent: today's wrap grasp, unchanged)
    GraspStyle style;
    style.shape = str(a, "shape", "wrap");
    if (style.shape != "wrap") {
      auto hs = graspHandShape(style.shape, what);
      if (!hs) return std::unexpected(hs.error());
      style.hs = *hs;
    }
    style.approach = vecOpt(a, "approach");
    style.face = flag(a, "graspFace", false);
    if (auto fc = fingerCloseFromJson(a, what); !fc) return std::unexpected(fc.error());  // T-171 (opt-in)
    else style.soft = *fc;
    if (auto b = a.find("band"); b != a.end()) {
      if (!b->is_array() || b->size() != 2 || !(*b)[0].is_number() || !(*b)[1].is_number())
        return fail(std::format("{}: 'band' must be [lo, hi] (metres along the grasp axis)", what));
      style.band = vec2((*b)[0].get<float>(), (*b)[1].get<float>());
      const std::string th = str(a, "thumb", "opposed");
      if (th != "opposed" && th != "along" && th != "tucked") return fail(std::format("{}: thumb must be opposed, along or tucked", what));
      style.thumb = th == "opposed" ? 0.0f : th == "along" ? 1.0f : 2.0f;
    }
    const bool follower = flag(a, "follower", false);
    if (follower) {  // T-112b: the second hand of a two-hand grasp; the character's other hand holds (and parents) it
      auto o = ctx.hands.find({c, h.side == 'L' ? 'R' : 'L'});
      if (!grasp || o == ctx.hands.end() || o->second.prop != p || o->second.follower)
        return fail(std::format("{}: a follower grasp needs '{}' to hold '{}' in the other hand first", what, who, scene_.props[size_t(p)].name));
    }
    const bool naturalGrip = grasp && !follower && style.shape == "wrap" && style.soft && style.soft->natural;  // T-171 (opt-in)
    style.naturalElbow = naturalGrip;
    const std::string socket =
        naturalGrip ? naturalSocket(h, p, authoredSocket, contact)
        : grasp && visibleGrip && !follower && style.shape == "wrap" ? visibleSocket(h, p, authoredSocket, contact, "") : authoredSocket;
    auto pl = reachTo(h, p, socket, start, contact, grasp, what, socket != authoredSocket, style);
    if (!pl) return std::unexpected(pl.error());
    ctx.contacts.push_back({c, h.side, contact, p, socket, false, vec3(0)});
    if (follower) {
      ctx.hands[{c, h.side}] = {p, pl->orient, socket, style.shape, true, pl->faceGrasp};
      ctx.followers.push_back({c, h.side, p, socket, contact});
      return true;
    }
    if (grasp) {
      if (auto r = addSwitch(p, contact, PropParent{PropParent::Kind::Character, who, std::string("hand.") + h.side}, what); !r)
        return std::unexpected(r.error());
      ctx.hands[{c, h.side}] = {p, pl->orient, socket, style.shape, false, pl->faceGrasp};
      if (naturalGrip) {  // T-186: held still from the contact until the hand's next move (0 before: tracks hold their ends)
        key(gen, stillTrack(h), contact - 0.5, vec3(0), Interp::Step);
        key(gen, stillTrack(h), contact, vec3(1), Interp::Step);
      }
      if (look) gazeOn(h, p, start, contact + 8);
    } else {
      const double end = num(a, "end", contact + beat("hold", 12, c));
      key(gen, h.ik, contact + 2, clip.evaluate(h.ik, contact, vec3(0)));
      release(h, pl->orient, contact + 2, std::max(end, contact + 10), -pl->inward * 0.05f + kUp * 0.02f, style.shape, pl->faceGrasp,
              style.soft ? style.soft->rest() : nullptr);
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
    endStill(h, start);  // T-186
    const vec3 origin = vec3(propWorld(size_t(*p), start)[3]);
    const auto at = vecOpt(a, "at"), by = vecOpt(a, "by");
    const vec3 target = at ? *at : origin + (by ? *by : vec3(0));
    double hold = 16;
    if (ctx.timing)  // T-104: long enough to read and to carry the prop at the profile's arm-relative speed
      hold = std::max(beat("hold", 16, c), ctx.timing->travelFrames(glm::length(target - origin), h.armLength, personality(size_t(c))));
    const double end = num(a, "end", start + hold);
    if (end <= start) return fail("hold: end must be after start");
    const quat orient = ctx.hands[{c, h.side}].orient;
    const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, end, wrist + (target - origin));
    key(gen, h.ik + ".weight", end, vec3(1));
    key(gen, h.orient, end, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", end, vec3(1));
    warnReach(h, wrist + (target - origin), end, "hold");
    correct(h, end, [&] { return target - vec3(propWorld(size_t(*p), end)[3]); });
    arcMove(h, start, end);  // T-134 E1b
    if (look) gazeOn(h, *p, start, end);
    return true;
  }

  if (type == "place") {
    auto p = held(h, "place");
    if (!p) return std::unexpected(p.error());
    endStill(h, start);  // T-186
    const std::string socket = str(a, "socket", "place");
    if (auto r = requireSocket(*p, socket, "place"); !r) return std::unexpected(r.error());
    const double contact = num(a, "contact", start + beat("place", 16, c)), end = num(a, "end", contact + beat("release", 14, c));
    if (contact < start + 6 || end < contact + 8) return fail("place: needs contact >= start + 6 and end >= contact + 8");
    const auto placeSoft = fingerCloseFromJson(a, "place");  // T-171 (opt-in): the rest shape the hand returns to
    if (!placeSoft) return std::unexpected(placeSoft.error());
    const HandShape* placeRest = *placeSoft ? (*placeSoft)->rest() : nullptr;
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
    release(h, orient, contact, end, -(glm::mat3_cast(orient) * h.grip.palmNormal) * 0.05f + kUp * 0.03f, ctx.hands[{c, h.side}].shape,
            ctx.hands[{c, h.side}].faceGrasp, placeRest);
    // T-112b: the second hand of a two-hand grasp lets go with the leading hand, its wrist where the prop frame puts it
    for (auto& fl : ctx.followers) {
      if (fl.prop != *p || fl.to < 1e29) continue;
      fl.to = contact;
      auto fh = handOf(fl.character, fl.side, "place");
      if (!fh) return std::unexpected(fh.error());
      const vec4 local = glm::inverse(propWorld(size_t(*p), fl.from)) * vec4(clip.evaluate(fh->ik, fl.from, vec3(0)), 1);
      const InteractionContext::Hold fhold = ctx.hands[{fl.character, fl.side}];
      key(gen, fh->ik, contact, vec3(propWorld(size_t(*p), contact) * local));
      key(gen, fh->ik + ".weight", contact, vec3(1));
      key(gen, fh->orient, contact, rotationVector(fhold.orient), Interp::Linear);
      key(gen, fh->orient + ".weight", contact, vec3(1));
      ctx.hands[{fl.character, fl.side}].prop = -1;
      ctx.hands[{fl.character, fl.side}].follower = false;
      release(*fh, fhold.orient, contact, end, -(glm::mat3_cast(fhold.orient) * fh->grip.palmNormal) * 0.05f + kUp * 0.03f, fhold.shape, fhold.faceGrasp, placeRest);
    }
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
  endStill(h, start);  // T-186
  for (const auto& fl : ctx.followers)
    if (fl.prop == *p && fl.to > 1e29) return fail("handover: a prop held in two hands cannot be handed over (T-112b)");
  if (auto it = ctx.hands.find({rc, r.side}); it != ctx.hands.end() && it->second.prop >= 0)
    return fail(std::format("handover: '{}' already holds '{}' in hand.{}", to, scene_.props[size_t(it->second.prop)].name, r.side));
  const std::string authoredToSocket = str(a, "toSocket", "grip_b");
  if (auto rs = requireSocket(*p, authoredToSocket, "handover"); !rs) return std::unexpected(rs.error());
  // T-112c: the receiver's finger band and box face (written by the pass verb under the finger gate; absent: today's)
  GraspStyle rStyle;
  if (auto b = a.find("toBand"); b != a.end()) {
    if (!b->is_array() || b->size() != 2 || !(*b)[0].is_number() || !(*b)[1].is_number())
      return fail("handover: 'toBand' must be [lo, hi] (metres along the grasp axis)");
    rStyle.band = vec2((*b)[0].get<float>(), (*b)[1].get<float>());
    const std::string th = str(a, "toThumb", "opposed");
    if (th != "opposed" && th != "along" && th != "tucked") return fail("handover: toThumb must be opposed, along or tucked");
    rStyle.thumb = th == "opposed" ? 0.0f : th == "along" ? 1.0f : 2.0f;
  }
  rStyle.face = flag(a, "toGraspFace", false);
  if (auto fc = fingerCloseFromJson(a, "handover"); !fc) return std::unexpected(fc.error());  // T-171 (opt-in): the receiver's close
  else rStyle.soft = *fc;
  const double rStart = num(a, "receiverStart", start + beat("reaction_delay", 4, rc));
  const double contact = num(a, "contact", ctx.timing ? rStart + beat("reach", 18, rc) : start + 18);
  const double rel = num(a, "release", contact + beat("shared_hold", 4, c)), end = num(a, "end", rel + beat("release", 12, c));
  if (contact < start + 6 || contact < rStart + 6 || rel < contact + 1 || end < rel + 8)
    return fail("handover: needs contact >= start + 6, contact >= receiverStart + 6, release > contact, end >= release + 8");
  // Giver: brings the prop to the meeting point a little before contact and holds it still until it lets go.
  const quat gOrient = ctx.hands[{c, h.side}].orient;
  const std::string gShape = ctx.hands[{c, h.side}].shape;
  const bool gFace = ctx.hands[{c, h.side}].faceGrasp;
  const vec3 origin = vec3(propWorld(size_t(*p), start)[3]);
  // T-096 visibleGrip: the receiver's grip turned to keep the prop in view, away from the giver's (the prop keeps its
  // orientation from the start of the hand-over to the contact, so its sides are known now).
  const std::string toSocket = visibleGrip ? visibleSocket(r, *p, authoredToSocket, contact, ctx.hands[{c, h.side}].socket) : authoredToSocket;
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
    arcMove(h, start, still);  // T-134 E1b
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, contact, rotationVector(gOrient), Interp::Linear);
    key(gen, h.orient + ".weight", contact, vec3(1));
    correct(h, still, [&] { return m - vec3(propWorld(size_t(*p), still)[3]); });
    for (auto& k : gen.tracks[h.ik].keys)  // still means still: contact repeats the corrected meeting key
      if (std::abs(k.frame - contact) < 1e-6) k.value = clip.evaluate(h.ik, still, wristM);
    return reachTo(r, *p, toSocket, rStart, contact, true, what, toSocket != authoredToSocket, rStyle);
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
  ctx.shared.push_back({c, h.side, *p, ctx.hands[{c, h.side}].socket, contact, rel, end});
  ctx.hands[{rc, r.side}] = {*p, pl->orient, toSocket, "wrap", false, pl->faceGrasp};
  ctx.hands[{c, h.side}].prop = -1;
  // Giver lets go after the receiver holds it and draws the hand back towards its own shoulder.
  key(gen, h.ik, rel, clip.evaluate(h.ik, contact, wristM));
  key(gen, h.ik + ".weight", rel, vec3(1));
  key(gen, h.orient, rel, rotationVector(gOrient), Interp::Linear);
  key(gen, h.orient + ".weight", rel, vec3(1));
  const vec3 back = boneAt(h, h.root, rel) - wristM;
  release(h, gOrient, rel, end, glm::normalize(back) * 0.08f - (glm::mat3_cast(gOrient) * h.grip.palmNormal) * 0.03f, gShape, gFace, rStyle.soft ? rStyle.soft->rest() : nullptr);
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
  // T-096 (opt-in): head and hair volumes, always derived from the character's own meshes (never from the package).
  if (auto io = interactionOptionsFromJson(scene_.interaction); io && io->headVolumes)
    for (size_t c = 0; c < characters_.size(); ++c) addHeadVolumes(clearance_[c].collision, characters_[c].asset.skeleton, characters_[c].rig.meshes);
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
  // T-186: through a natural grip's held-still span (collision.still: the hand and the prop do not move, the wrist
  // push leaves it alone) the envelope alone may turn the forearm into the body (its decay from a large swing on the
  // way in, while the body moves towards the held arm). There the swing goes on from the previous frame by at most
  // kSwingRate: the angle in that step nearest the envelope's that keeps the forearm at the margin, else the one with
  // the largest gap. After the span it joins the envelope again at most kSwingRate per frame.
  if (const Track* st = gen.find(who + "/collision.still." + bone); st && !st->keys.empty()) {
    std::vector<char> still(static_cast<size_t>(n), 0);
    for (int i = 0; i < n; ++i) still[size_t(i)] = st->evaluate(double(fs + i)).x > 0.5f;
    for (int i = 1; i < n; ++i) {
      if (!still[size_t(i)] || !still[size_t(i - 1)]) continue;
      std::vector<mat4> G = characterGlobals(c, double(fs + i));  // without this arm's swing (erased above)
      const mat4 fore0 = G[size_t(A.fore)];
      const float from = out[size_t(i - 1)], target = out[size_t(i)], want = kArmBodyMargin + 0.0005f;
      if (std::abs(target - from) <= kSwingRate + 1e-6f && forearmGap(M.collision, G, fore0, A.upper, A.fore, A.hand, side, target) >= want)
        continue;  // the envelope's own swing is within the step and keeps the margin
      float best = from, bestGap = -1e9f, bestOff = 1e9f;
      bool clear = false;
      for (int k = -8; k <= 8; ++k) {
        const float a = from + kSwingRate * float(k) / 8.0f, g = forearmGap(M.collision, G, fore0, A.upper, A.fore, A.hand, side, a);
        const bool ok = g >= want;
        if ((ok && (!clear || std::abs(a - target) < bestOff)) || (!ok && !clear && g > bestGap))
          best = a, bestGap = g, bestOff = std::abs(a - target), clear = ok;
      }
      out[size_t(i)] = best;
    }
    for (int i = 1; i < n; ++i)
      if (!still[size_t(i)] && still[size_t(i - 1)])
        for (int k = i; k < n && !still[size_t(k)]; ++k) {
          const float from = out[size_t(i - 1)], lim = kSwingRate * float(k - i + 1);
          const float lo = from - lim, hi = from + lim;
          if (out[size_t(k)] >= lo && out[size_t(k)] <= hi) break;
          out[size_t(k)] = std::clamp(out[size_t(k)], lo, hi);
        }
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
  const bool stopAtPinned = reachMechanicsFromJson(scene_.reachMechanics).value_or(ReachMechanics{}).enabled;  // T-134
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
      // T-186: a natural grip's hand holds still from its contact to its next move (collision.still, compileInteraction):
      // no push there, no ramp is carried across it, and the push grows from 0 away from the span: before it (the way
      // in) as towards any contact; after it eased in over kStillEase frames (then kPushRate per frame), as the lift
      // that ends the span starts slowly: a full-rate push would drag the prop along the table in the lift's first
      // frames.
      std::vector<char> still(static_cast<size_t>(n), 0);
      if (const Track* st = gen.find(who + "/collision.still." + sk.bones[size_t(A.hand)].name); st && !st->keys.empty()) {
        constexpr float kStillEase = 6.0f;  // frames
        for (int i = 0; i < n; ++i) still[size_t(i)] = st->evaluate(double(fs - 1 + i)).x > 0.5f;
        for (int i = 0, last = -1000000; i < n; ++i) {  // frames since the last still frame
          if (still[size_t(i)]) last = i;
          const float d = float(i - last);
          cap[size_t(i)] = std::min(cap[size_t(i)], kPushRate * (d < kStillEase ? d * d / (2 * kStillEase) : d - kStillEase / 2));
        }
        for (int i = n - 1, next = 1000000; i >= 0; --i) {
          if (still[size_t(i)]) next = i;
          cap[size_t(i)] = std::min(cap[size_t(i)], kPushRate * float(next - i));
        }
      }
      auto ease = [&](const std::vector<vec3>& need) {
        std::vector<float> mag(static_cast<size_t>(n)), env(static_cast<size_t>(n));
        for (int i = 0; i < n; ++i) env[size_t(i)] = mag[size_t(i)] = glm::length(need[size_t(i)]);
        // T-134 (opt-in): a ramp does not carry across a pinned frame. The push is 0 there anyway; without this the
        // ramp of a need before a contact comes back right after it and moves the hand that has just arrived.
        auto carried = [&](int i) { return (stopAtPinned || still[size_t(i)]) && cap[size_t(i)] <= 0 ? 0.0f : env[size_t(i)]; };
        for (int i = 1; i < n; ++i) env[size_t(i)] = std::max(env[size_t(i)], carried(i - 1) - kPushRate);
        for (int i = n - 2; i >= 0; --i) env[size_t(i)] = std::max(env[size_t(i)], carried(i + 1) - kPushRate);
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
  // T-112b two-hand followers: the wrist keyed in the prop frame at every frame of the span (as it was at the
  // follower's contact), held there by the clearance pass (a frozen span) and corrected per frame below.
  for (const auto& fl : ctx.followers) {
    const int hb = characterSocketBone(size_t(fl.character), std::string("hand.") + fl.side);
    if (hb < 0) continue;
    const std::string ik = scene_.characters[size_t(fl.character)].name + "/ik." + characters_[size_t(fl.character)].asset.skeleton.bones[size_t(hb)].name;
    const double to = std::min(fl.to, double(scene_.frameEnd));
    const vec4 local = glm::inverse(propWorld(size_t(fl.prop), fl.from)) * vec4(gen.tracks[ik].evaluate(fl.from), 1);
    for (double f = std::floor(fl.from) + 1; f <= to + 1e-9; f += 1) key(gen, ik, f, vec3(propWorld(size_t(fl.prop), f) * local), Interp::Linear);
    ctx.frozen.push_back({fl.character, fl.side, fl.from, to});
  }
  armClearancePass(gen, ctx);
  for (const auto& fl : ctx.followers)
    for (double f = std::floor(fl.from) + 1; f <= std::min(fl.to, double(scene_.frameEnd)) + 1e-9; f += 1)
      ctx.contacts.push_back({fl.character, fl.side, f, fl.prop, fl.socket, false, vec3(0)});
  const InteractionOptions io = interactionOptionsFromJson(scene_.interaction).value_or(InteractionOptions{});
  // T-096 followSharedProp: while giver and receiver both hold the prop, the receiver's hand carries it (its parent)
  // and may still move a little (an arm near full reach follows the shoulder's idle sway): the giver's palm follows
  // its own socket at every frame of the shared span (contact corrections below, in time order after the receiver's
  // contact), and the giver's return path takes the last offset out gradually, so the release does not step.
  struct SharedFix {
    const InteractionContext::Shared* s;
    std::string ik;
    vec3 before{0};
  };
  std::vector<SharedFix> sharedFix;
  if (io.followSharedProp)
    for (const auto& sh : ctx.shared) {
      if (sh.socket.empty() || sh.prop < 0) continue;
      const int hb = characterSocketBone(size_t(sh.character), std::string("hand.") + sh.side);
      if (hb < 0) continue;
      const std::string ik = scene_.characters[size_t(sh.character)].name + "/ik." + characters_[size_t(sh.character)].asset.skeleton.bones[size_t(hb)].name;
      Track& t = gen.tracks[ik];
      if (t.keys.empty()) continue;
      for (double f = std::floor(sh.from) + 1; f <= sh.to + 1e-9; f += 1) {
        bool has = false;
        for (const Key& k : t.keys) has |= std::abs(k.frame - f) < 1e-6;
        if (!has) {
          const vec3 v = t.evaluate(f);
          auto at = std::lower_bound(t.keys.begin(), t.keys.end(), f, [](const Key& k, double x) { return k.frame < x; });
          t.keys.insert(at, Key{f, v, Interp::Linear});
        }
        ctx.contacts.push_back({sh.character, sh.side, f, sh.prop, sh.socket, false, vec3(0)});
      }
      sharedFix.push_back({&sh, ik, t.evaluate(sh.to)});
    }
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
  for (const SharedFix& sf : sharedFix) {  // fade the release offset out over the giver's return
    Track& t = gen.tracks[sf.ik];
    const vec3 off = t.evaluate(sf.s->to) - sf.before;
    for (Key& k : t.keys)
      if (k.frame > sf.s->to + 1e-6 && k.frame < sf.s->end - 1e-6) {
        const float u = float((k.frame - sf.s->to) / (sf.s->end - sf.s->to));
        k.value += off * (1.0f - u * u * (3.0f - 2.0f * u));
      }
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
  if (io.headVolumes) {
    // T-096 head clearance (interaction option headVolumes): every pair of characters with head volumes keeps
    // headClearance between them. Per frame where the volumes come closer, both heads tilt away from each other about
    // their neck (the same angle each: the smallest kHeadTiltStep multiple up to kHeadTiltMax that opens the gap, as
    // the pose plays back); then the smallest envelope above those angles whose rate is at most kHeadTiltRate per
    // frame, so a head eases away and back. The tilt is a generated "<who>/headTilt" track (applyHeadTilt: after IK
    // and look-at, so the head follow and the neck assist do not aim it back; the eyes keep their gaze), axis per frame
    // the one that moves the closest head point horizontally away from the other head. Neck only: arms, hands and held
    // props stay where they are. "<who>/collision.headTilt.<other>" records the angle (degrees) for measurements.
    const float need = io.headClearance;
    constexpr float kHeadTiltMax = 15.0f, kHeadTiltStep = 0.5f, kHeadTiltRate = 0.6f;  // degrees, degrees per frame
    const int fs = scene_.frameStart - 1, n = scene_.frameEnd - scene_.frameStart + 3;
    for (size_t a = 0; a < characters_.size(); ++a)
      for (size_t b = a + 1; b < characters_.size(); ++b) {
        if (a >= clearance_.size() || b >= clearance_.size() || clearance_[a].collision.heads.empty() || clearance_[b].collision.heads.empty()) continue;
        const size_t who[2] = {a, b};
        int neck[2], head[2];
        std::string track[2];
        std::vector<vec3> base[2];
        std::optional<Track> saved[2];
        bool ok = true;
        for (int k = 0; k < 2; ++k) {
          const Skeleton& sk = characters_[who[k]].asset.skeleton;
          neck[k] = sk.find("neck");
          head[k] = sk.find("head");
          ok = ok && neck[k] >= 0 && head[k] >= 0;
          track[k] = scene_.characters[who[k]].name + "/headTilt";
          if (auto it = gen.tracks.find(track[k]); it != gen.tracks.end() && !it->second.keys.empty()) saved[k] = it->second;
          for (int i = 0; i < n; ++i) base[k].push_back(saved[k] ? saved[k]->evaluate(fs + i) : vec3(0));
        }
        if (!ok) continue;
        std::vector<float> needDeg(size_t(n), 0.0f);
        std::vector<vec3> axis[2] = {std::vector<vec3>(size_t(n), vec3(0)), std::vector<vec3>(size_t(n), vec3(0))};
        std::vector<char> hasAxis(size_t(n), 0);
        auto setTilt = [&](int k, const std::vector<float>& deg) {
          std::vector<Key> keys;
          for (int i = 0; i < n; ++i)
            keys.push_back({double(fs + i), base[k][size_t(i)] + axis[k][size_t(i)] * glm::radians(deg[size_t(i)]), Interp::Linear});
          gen.tracks[track[k]].keys = std::move(keys);
        };
        const std::vector<float> zero(size_t(n), 0.0f);
        for (int k = 0; k < 2; ++k) setTilt(k, zero);
        auto gapAt = [&](int i) {
          return headGap(clearance_[a].collision, characterGlobals(a, fs + i), clearance_[b].collision, characterGlobals(b, fs + i));
        };
        bool any = false;
        for (int i = 0; i < n; ++i) {
          const std::vector<mat4> GG[2] = {characterGlobals(a, fs + i), characterGlobals(b, fs + i)};
          const HeadGap g = headGap(clearance_[a].collision, GG[0], clearance_[b].collision, GG[1]);
          // Away from the other head: horizontally, head bone to head bone (inside an overlap the closest spheres'
          // direction says little about how the heads separate).
          vec3 away = vec3(GG[0][size_t(head[0])][3]) - vec3(GG[1][size_t(head[1])][3]);
          away.y = 0;
          away = glm::length(away) > 1e-6f ? glm::normalize(away) : g.dir;
          const vec3 dirs[2] = {away, -away}, pts[2] = {g.pointA, g.pointB};
          for (int k = 0; k < 2; ++k) {
            const vec3 ax = glm::cross(pts[k] - vec3(GG[k][size_t(neck[k])][3]), dirs[k]);
            if (glm::length(ax) > 1e-6f) axis[k][size_t(i)] = glm::normalize(ax);
          }
          hasAxis[size_t(i)] = axis[0][size_t(i)] != vec3(0) && axis[1][size_t(i)] != vec3(0);
          if (g.gap >= need || !hasAxis[size_t(i)]) continue;
          any = true;
          float best = 0, bestGap = g.gap;
          std::vector<float> one(size_t(n), 0.0f);
          for (float t = kHeadTiltStep; t <= kHeadTiltMax + 1e-4f; t += kHeadTiltStep) {
            one[size_t(i)] = t;
            for (int k = 0; k < 2; ++k) setTilt(k, one);
            const float gg = gapAt(i).gap;
            if (gg > bestGap) bestGap = gg, best = t;
            if (gg >= need) break;
          }
          needDeg[size_t(i)] = best;
          for (int k = 0; k < 2; ++k) setTilt(k, zero);
        }
        if (!any) {
          for (int k = 0; k < 2; ++k)  // nothing to do: the tracks are as they were
            if (saved[k]) gen.tracks[track[k]] = *saved[k];
            else gen.tracks.erase(track[k]);
          continue;
        }
        // Frames without their own axis (ramps) take the nearest frame's.
        for (int k = 0; k < 2; ++k)
          for (int i = 0; i < n; ++i) {
            if (hasAxis[size_t(i)]) continue;
            for (int d = 1; d < n; ++d) {
              if (i - d >= 0 && hasAxis[size_t(i - d)]) {
                axis[k][size_t(i)] = axis[k][size_t(i - d)];
                break;
              }
              if (i + d < n && hasAxis[size_t(i + d)]) {
                axis[k][size_t(i)] = axis[k][size_t(i + d)];
                break;
              }
            }
          }
        std::vector<float> env = needDeg;
        for (int i = 1; i < n; ++i) env[size_t(i)] = std::max(env[size_t(i)], env[size_t(i - 1)] - kHeadTiltRate);
        for (int i = n - 2; i >= 0; --i) env[size_t(i)] = std::max(env[size_t(i)], env[size_t(i + 1)] - kHeadTiltRate);
        for (int k = 0; k < 2; ++k) setTilt(k, env);
        for (int k = 0; k < 2; ++k) {
          std::vector<Key> keys;
          for (int i = 0; i < n; ++i) keys.push_back({double(fs + i), vec3(env[size_t(i)]), Interp::Linear});
          gen.tracks[scene_.characters[who[k]].name + "/collision.headTilt." + scene_.characters[who[1 - k]].name].keys = std::move(keys);
        }
        float worst = 1e9f;
        int at = 0;
        for (int i = 1; i < n - 1; ++i)
          if (const float g = gapAt(i).gap; g < worst) worst = g, at = fs + i;
        if (worst < need - 0.0005f)
          warnings_.push_back(std::format("interaction: the heads of '{}' and '{}' come within {:.1f} mm at frame {} (head clearance {:.0f} mm, "
                                          "head tilt limit {:.0f} deg): move them apart",
                                          scene_.characters[a].name, scene_.characters[b].name, worst * 1000, at, need * 1000, kHeadTiltMax));
      }
  }
  return {};
}

}  // namespace plush
