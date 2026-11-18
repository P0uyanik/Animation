// T-047 collision system: one collision body per character, used both to plan arm / hand / prop motion and to measure
// it (one inside/outside definition for the solver and the evidence).
//
// The body is a closed, simplified volume of the character's torso and its garment shell: a stack of short sections
// along the spine (pelvis, lower torso, upper torso; elliptical cross-sections fitted to the skinned rest meshes,
// garments included), each carried rigidly by one torso bone. The moving parts that must stay outside are per-bone
// capsules: the wrist half of each forearm (sleeve included) and each hand (palm and fingers). A capsule is convex and
// carried by one bone, so its clearance is a continuous, piecewise smooth function of the pose: no surface sampling
// noise, no sign ambiguity of layered open garments (the T-040r1 root causes).
//
// Source: the package's "collision" block (written by pipeline/charsys/export_engine.py, export/6) when present, else
// derived here from the skinned rest meshes with the same rules (legacy packages and engine SDF characters). Both
// carry the same data; the block only freezes it with the character version. Everything comes from shared roles
// (hips, spine, chest, neck, upperArm/forearm/hand.L/R, finger roles): no character names.
//
// Package block (engine axes, metres, points relative to the carrying bone's rest head):
//   "collision": {"format": "plush.collision_body", "version": 1, "margin": 0.005,
//     "sections": [{"name", "bone", "p0":[3], "p1":[3], "e1":[3], "e2":[3], "r1", "r2", "cap0", "cap1"}...],
//     "limbs": [{"name": "forearm.L"|"hand.L"|..., "bone", "side": "L"|"R", "a":[3], "b":[3], "r", "allowance"}...]}
#pragma once
#include <string>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct SkinnedMesh;

constexpr float kCollisionMargin = 0.005f;  // clearance planned between a limb capsule and the body (metres)

// A body section: axis p0 -> p1 (relative to the carrying bone's rest head; engine rest frames have identity rotation,
// so these are character axes: +X the character's left, +Y up, +Z forward) with an elliptical cross-section (r1
// along e1, r2 along e2). Sections meet with flat ends; the lowest and highest have round ends (cap0 / cap1).
struct CollisionSection {
  std::string name;
  int bone = -1;
  vec3 p0{0}, p1{0};
  vec3 e1{1, 0, 0}, e2{0, 0, 1};
  float r1 = 0.1f, r2 = 0.1f;
  bool cap0 = true, cap1 = true;
};
// A limb capsule carried rigidly by one bone (segment a -> b relative to the bone's rest head, radius r).
struct CollisionLimb {
  std::string name;  // "forearm.L", "hand.R", ...
  int bone = -1;
  char side = 'L';
  vec3 a{0}, b{0};
  float r = 0.02f;
  float allowance = 0;  // <= 0: how deep the limb rests against the body at rest, minus the margin (it may rest that
                        // deep, never deeper; 0 for a limb that is clear at rest)
};
struct CollisionBody {
  std::vector<CollisionSection> sections;
  std::vector<CollisionLimb> limbs;
  float margin = kCollisionMargin;
  bool valid = false;
  std::string source;  // "package" (the package's collision block) or "derived" (fitted here from the rest meshes)
};

// Fits the body to the character: sections from the torso-carried rest vertices (front half, 99th percentile; hands
// work in front, long hair or a backpack behind is not body to a hand), limbs from the arm-carried vertices (90th
// percentile radius). A limb that would touch the body at rest is shortened (forearm) and thinned (to 60 %) until the
// rest pose keeps the margin; what remains is its rest-contact allowance, so the rest pose is clear by construction.
// Invalid without hips, chest and both arm chains.
CollisionBody deriveCollisionBody(const Skeleton& skeleton, const std::vector<SkinnedMesh>& meshes);
// The package block (format above); bone names are resolved against the skeleton.
Result<CollisionBody> collisionBodyFromJson(const Json& j, const Skeleton& skeleton);
Json collisionBodyToJson(const CollisionBody& body, const Skeleton& skeleton);
// The package's block if it has one (and it is valid for this skeleton), else derived from the meshes.
CollisionBody collisionBodyFor(const Json& packageBlock, const Skeleton& skeleton, const std::vector<SkinnedMesh>& meshes);

// Signed gap of a world point to one section whose bone has global Gb, and the unit world direction that increases
// it. Elliptical sections are measured in scaled coordinates that make them round (radius min(r1, r2)); the map only
// shrinks distances, so a gap here never overstates the true gap.
struct SectionGap {
  float gap = 1e9f;
  vec3 grad{0};
};
SectionGap sectionGap(const CollisionSection& s, const mat4& Gb, vec3 p, char side);

// Clearance of a set of moving parts against the body: the smallest gap (metres, negative = inside), the world point
// of the moving part where it occurs, and the unit direction that moves that point out.
struct Clearance {
  float gap = 1e9f;
  vec3 point{0}, push{0};
  std::string part, against;
};
// A world segment a -> b of radius r against the body (sampled along the segment; exact at the samples).
Clearance segmentClearance(const CollisionBody& body, const std::vector<mat4>& G, vec3 a, vec3 b, float r, char side);
// One arm's limb capsules (forearm wrist half and hand) for bone globals G (each counted from its rest allowance).
Clearance limbClearance(const CollisionBody& body, const std::vector<mat4>& G, char side);
// World segment of a limb for bone globals G.
void limbSegment(const CollisionLimb& limb, const std::vector<mat4>& G, vec3& a, vec3& b);

// Elbow swing that clears a two-bone arm with a fixed wrist (the planner's first resort: the wrist, the hand and a
// held prop stay where the action put them). `angleOf(theta)` returns the arm's clearance with the elbow swung by
// theta (radians, about the shoulder -> wrist axis) from where it is. Returns the smallest |theta| (searched both ways
// up to `maxAngle`) whose clearance reaches `need`, else the theta with the largest clearance.
template <class F>
float clearingSwing(F angleOf, float need, float maxAngle, float step = 0.0436f /* 2.5 deg */) {
  float best = 0, bestGap = angleOf(0.0f);
  if (bestGap >= need) return 0;
  for (float t = step; t <= maxAngle + 1e-6f; t += step)
    for (float s : {t, -t}) {
      const float g = angleOf(s);
      if (g >= need) return s;
      if (g > bestGap) best = s, bestGap = g;
    }
  return best;
}

}  // namespace plush
