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
//   "collision": {"format": "plush.collision_body", "version": 1, "margin": 0.005, "max_elbow_swing_deg": 30 (optional),
//     "sections": [{"name", "bone", "p0":[3], "p1":[3], "e1":[3], "e2":[3], "r1", "r2", "cap0", "cap1"}...],
//     "limbs": [{"name": "forearm.L"|"hand.L"|..., "bone", "side": "L"|"R", "a":[3], "b":[3], "r", "allowance"}...]}
#pragma once
#include <string>
#include <utility>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct SkinnedMesh;

constexpr float kCollisionMargin = 0.005f;  // clearance planned between a limb capsule and the body (metres)
// Largest elbow swing the arm planner may use to clear a forearm (T-082): beyond it the elbow would rise beside the
// head (a "wing" elbow, T-047 e905: 84 deg), so the planner moves the hand-over point or pushes the wrist instead.
// Character data: the package block's "max_elbow_swing_deg", overridden per shot by the scene's collision action
// ("maxElbowSwingDeg"); this shared default applies when neither gives one.
constexpr float kDefaultMaxElbowSwingDeg = 30.0f;

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
// A head volume (T-096): a sphere carried rigidly by one bone (centre relative to the bone's rest head).
struct CollisionSphere {
  int bone = -1;
  vec3 centre{0};
  float r = 0.05f;
};
// T-191 body parts (fitted below, deriveBodyParts).
struct BodyPartCapsule {
  std::string part;  // role name ("chest", "thigh.L", ...)
  int bone = -1;
  vec3 a{0}, b{0};  // relative to the bone's rest head
  float r = 0.05f;
};
struct BodyParts {
  std::vector<BodyPartCapsule> capsules;
  bool valid = false;  // at least one capsule
};
// T-191 body clearance (opt-in per character: the collision action's "bodyClearance"): the gap kept to other
// characters' body parts and the largest upper-body lean used to keep it.
constexpr float kBodyClearance = 0.01f;       // metres
constexpr float kDefaultBodyLeanMaxDeg = 12.0f;
struct CollisionBody {
  std::vector<CollisionSection> sections;
  std::vector<CollisionLimb> limbs;
  // Head and hair volumes (T-096, opt-in): empty unless addHeadVolumes() ran. Never written to or read from the
  // package block (export/6 is unchanged); always derived here from the character's own meshes.
  std::vector<CollisionSphere> heads;
  float margin = kCollisionMargin;
  float maxElbowSwing = glm::radians(kDefaultMaxElbowSwingDeg);  // radians (T-082)
  // T-191 (opt-in): body-part capsules (derived from the meshes when bodyClearance is on; never in the package block).
  BodyParts parts;
  bool bodyClearance = false;
  float bodyClearanceGap = kBodyClearance;                     // metres
  float bodyLeanMax = glm::radians(kDefaultBodyLeanMaxDeg);  // radians
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

// Head and hair volumes (T-096): a shell of small spheres over the rest vertices carried by the head bone and its
// descendants (>= 50 % of the weight: skin, hair, ears, eyes, glasses; not the neck), all carried by the head bone:
// the vertices are grouped in kHeadCell voxels, each group one sphere (centre: the middle of the group's bounding box,
// radius: its farthest vertex, at least kHeadMinRadius; so at most half a voxel diagonal, 13 mm). The union covers
// every one of those vertices and follows the surface within about one sphere radius (a few millimetres; the hair
// mass, a bun or curls included): head shapes are not convex and long hair reaches the shoulders, so no single round
// volume fits them. The union is a shell over the surface, so headGap() is exact while the heads are apart and
// negative (but not a depth) once the shells overlap. No-op (heads stay empty) without a
// "head" bone or with fewer than 50 such vertices.
constexpr float kHeadCell = 0.015f;       // metres
constexpr float kHeadMinRadius = 0.002f;  // metres
constexpr float kHeadNearGap = 0.05f;     // metres: gaps below this are found through a grid (exact either way)
void addHeadVolumes(CollisionBody& body, const Skeleton& skeleton, const std::vector<SkinnedMesh>& meshes);
// Head volumes of a body for bone globals G, in world space (centre, radius).
std::vector<std::pair<vec3, float>> headSpheres(const CollisionBody& body, const std::vector<mat4>& G);
// Signed gap between two characters' head volumes (metres; negative = overlapping), the closest points on each
// (world) and the unit direction from b's point towards a's (moving a along it, or b against it, opens the gap).
// 1e9 when either body has no head volumes.
struct HeadGap {
  float gap = 1e9f;
  vec3 pointA{0}, pointB{0}, dir{0};
};
HeadGap headGap(const CollisionBody& a, const std::vector<mat4>& Ga, const CollisionBody& b, const std::vector<mat4>& Gb);

// T-191 body parts: the whole character as capsules, for character-character contact (bodies passing through each
// other: seated neighbours, a hand-over, standing up, walking off). One part per body role (hips, spine, chest, neck,
// head, upperArm / forearm / hand / thigh / shin / foot .L/.R); a rest vertex belongs to the part of its heaviest
// role (helper, finger, toe and hair bones count for their nearest role ancestor) and only with >= 50 % of its weight
// there. Each part is fitted to its own rest vertices, garments and hair included: the axis is their principal
// direction through their centroid, the cross-section their kBodyPartRadiusQuantile distances along the two other
// principal directions; a flat part (wide over deep by more than kBodyPartFlat, a torso, a hand, a foot) is two
// parallel capsules of the smaller radius side by side, so the width and the depth are both close (a stadium over an
// ellipse), at least kBodyPartMinRadius. The ends cover the vertices from the 1st to the 99th percentile along the axis. A part with fewer than
// 20 vertices has no capsule. Carried rigidly by the role bone (relative to its rest head, character axes). Never
// read from or written to the package (export/6 is unchanged).
constexpr float kBodyPartRadiusQuantile = 0.9f;
constexpr float kBodyPartFlat = 1.25f;
constexpr float kBodyPartMinRadius = 0.004f;  // metres (a paper-thin part still has a little volume)
BodyParts deriveBodyParts(const Skeleton& skeleton, const std::vector<SkinnedMesh>& meshes);
// World segment of a part capsule for bone globals G.
void bodyPartSegment(const BodyPartCapsule& c, const std::vector<mat4>& G, vec3& a, vec3& b);
// Closest points of two segments (exact): returns the distance, ca on [a0, a1], cb on [b0, b1].
float segmentSegment(vec3 a0, vec3 a1, vec3 b0, vec3 b1, vec3& ca, vec3& cb);
// Signed gap between two characters' body parts (metres; negative = the capsules overlap that deep, the
// penetration depth along the closest-point line): the smallest over all capsule pairs, the parts, the closest points
// (world, on the capsule surfaces) and the unit direction from b's point towards a's (moving a along it opens the
// gap). `skip(partA, partB)` excludes pairs (e.g. hand-hand in a hand-over). 1e9 when either has no capsules.
struct BodyGap {
  float gap = 1e9f;
  std::string partA, partB;
  vec3 pointA{0}, pointB{0}, dir{0};
};
BodyGap bodyGap(const BodyParts& a, const std::vector<mat4>& Ga, const BodyParts& b, const std::vector<mat4>& Gb,
                bool (*skip)(const std::string&, const std::string&) = nullptr);
// Signed gap of a world point to a character's body parts (negative = inside that deep) and the part.
float pointBodyGap(const BodyParts& body, const std::vector<mat4>& G, vec3 p, std::string* part = nullptr);

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
