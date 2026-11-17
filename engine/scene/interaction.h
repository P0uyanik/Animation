// Hand-prop interaction (T-022): shared timeline actions that make a character's hand meet a plush.asset/1 prop at
// its sockets and carry it — reach / grasp, hold, place and hand-over between two characters. Everything comes from
// shared data: the hand is the character's "hand.L" / "hand.R" role (bone or clip-binding role), the palm contact
// point and hand axes come from the skeleton (finger roles and the HandFrame), and the grasp size comes from the prop
// asset's primitive mesh or collision proxy. Nothing here knows a character by name.
//
// Actions (scene "actions"; frames are scene frames; see docs/ACTIONS_AND_DIRECTOR.md):
//   reach / grasp {character, hand="R", prop, socket="grip", start, contact=start+14, grasp=true, end?, look=true}
//       the arm reaches (IK) so the palm contact point lands exactly on the prop socket at `contact`; the hand turns
//       its palm towards the prop, opens on the way and closes by contact search sized to the prop; at `contact` the
//       prop's parent switches to the hand (rebased, so it does not move) and the hand holds it. grasp:false only
//       touches the socket and lets go of the arm again at `end`.
//   hold     {character, hand="R", prop?, start, end, at:[x,y,z] | by:[dx,dy,dz], look=true}
//       moves a held prop so its origin arrives at `at` (or moves by `by`), keeping its world orientation.
//   place    {character, hand="R", prop?, start, contact=start+16, end=contact+14, at:[x,y,z] | onto:{prop, socket},
//             socket="place", look=true}
//       puts the held prop down so its `socket` lands on `at` (or on another prop's socket) at `contact`, detaches it
//       there (or re-parents it to that prop), opens the hand and returns the arm.
//   handover {character (giver), hand="R", to (receiver), toHand="R", prop?, toSocket="grip_b", start,
//             contact=start+18, receiverStart=start+4, release=contact+4, end=release+12, at:[x,y,z]?, look=true}
//       the giver brings the held prop to `at` (default: between the two characters) and holds it still; the
//       receiver reaches its own socket on the prop and grasps it at `contact`, where the prop's parent switches to
//       the receiver; the giver lets go at `release` and returns its arm by `end`.
//
// Generated tracks per hand ("<who>/"): ik.<hand bone> (+.weight) wrist target, orient.<hand bone> (+.weight) the
// hand's world orientation (rotation vector, applied after IK by applyOrientConstraints), hand.<side> curl,
// hand.<side>.grasp / .graspRadius / .graspAxis / .grasp.weight, lookAt; per prop: <prop>.parent.weight and
// parentSwitch entries at the contact frames.
#pragma once
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "anim/animation.h"
#include "model/character.h"

namespace plush {

// Palm contact geometry of one hand in the hand bone's rest frame (relative to the bone head).
struct HandGrip {
  vec3 palm{0};             // palm contact point
  vec3 fingerDir{0, -1, 0}; // unit
  vec3 palmNormal{1, 0, 0}; // unit, perpendicular to fingerDir, pointing out of the palm
  float palmLength = 0.06f; // wrist to finger roots along fingerDir
};
// From the finger roles (f0a..f3a, thumbA with .L/.R) and the skeleton's HandFrame; works for any finger subset.
HandGrip handGrip(const Skeleton& skeleton, int handBone, char side);

// Orientation constraint tracks "<prefix>orient.<bone>" (rotation vector: world-space rotation of the bone's rest
// frame) with "<prefix>orient.<bone>.weight" (default 1): sets the bone's local rotation so its world rotation is the
// keyed one (slerped by the weight). Runs after IK, so the hand keeps its orientation wherever the arm goes.
void applyOrientConstraints(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                            const mat4& world, Pose& pose);

// Rotation vector <-> quaternion (the orient track's value).
vec3 rotationVector(const quat& q);
quat fromRotationVector(vec3 v);

// ------------------------------------------------------------------------------------- arm-body clearance (T-030)
// Body: a stack of short collision capsules (sections) along the spine from the shared roles (hips, spine?, chest,
// neck?), each fitted to its own height slab of the skinned rest meshes (garments included). Points are stored relative to the owning bone's head (engine rest frames have identity
// rotation, so the axes are character axes: +X the character's left, +Y up, +Z forward). A body capsule has an
// elliptical cross-section (radii r1 along e1, r2 along e2): torso sections are wider than deep, so a round capsule
// would either cut into the sides or float off the belly.
// Arm: samples of the arm's own skinned surface (sleeve, cuff, hand; with their real skin weights), not bone
// capsules. Garments do not always follow the arm bones the way skin does (a sleeve weighted between shoulder and
// hand stretches along the shoulder-wrist chord when the elbow bends), and that surface is what must stay outside.
struct BodyCapsule {
  std::string name;  // "pelvis_<i>", "torso_lower_<i>", "torso_upper_<i>"
  int bone = -1;
  vec3 p0{0}, p1{0};             // axis segment (relative to the bone head, rest frame)
  vec3 e1{1, 0, 0}, e2{0, 0, 1}; // cross-section axes (unit, perpendicular to the segment)
  float r1 = 0.1f, r2 = 0.1f;
  bool cap0 = true, cap1 = true;  // round ends (false: a flat end where the next section joins)
};
struct ArmPoint {
  glm::ivec4 joint{0};
  vec4 weight{0};
  vec3 local[4];        // rest position relative to each joint's head
  float mobility = 0;   // skin weight on the IK chain's forearm and hand (how much the point follows the wrist)
  int part = 0;         // 0 upper arm and elbow half of the forearm, 1 wrist half of the forearm, 2 hand
  float allowance = 0;  // <= 0: how deep the point rests against the body at rest (minus the margin)
  // Pose post-pass (T-040): skin weight carried by the upper arm's subtree, by the forearm's subtree and by the
  // hand's subtree (a sleeve weighted to the shoulder or spine follows the arm only partly), and the point's position
  // along shoulder -> elbow (0 at the shoulder pivot, 1 at the elbow; > 1 past it).
  float followUpper = 0, followFore = 0, followHand = 0;
  float along = 1;
  float restGap = 1e9f;  // gap to the body sections at rest (without allowance or margin)
};
struct ArmModel {
  int upper = -1, fore = -1, hand = -1;
  std::vector<ArmPoint> points;
};
struct BodyClearanceModel {
  std::vector<BodyCapsule> body;
  ArmModel arm[2];  // 0 = L, 1 = R
  bool valid = false;
  std::string source;  // "mesh" (fitted to skinned vertices) or "skeleton" (proportions only, no arm points)
};
// Fits the model to the character (needs hips, chest and the arm chains; invalid otherwise). The body fit uses the
// 99th percentile of the offsets of torso-dominant vertices in the front half of each band (hands work in front; a
// backpack or long hair behind is not body to a hand).
BodyClearanceModel bodyClearanceModel(const Skeleton& skeleton, const std::vector<SkinnedMesh>& meshes);
// Smallest gap (metres; negative = inside) between one arm's hand and wrist-half forearm surface and the body capsules for posed
// bone globals G, relative to the rest pose: a point that rests against the body (allowance) counts from its rest
// depth, so the gap says how much deeper than at rest it is; every other point is measured from the body surface. `push` is the unit world direction that moves the worst point out of the body (the gradient of the
// gap), `mobility` how much that point follows the wrist; `part` / `against` name it. `upperGap` is the same for the
// upper arm and the elbow half of the forearm, reported only: a plush upper arm and elbow rest against the body's
// side (the elbow pole keeps them outward).
struct ArmClearance {
  float gap = 1e9f, upperGap = 1e9f, mobility = 1;
  float rawGap = 1e9f;  // forearm/hand surface to the body without the rest-contact allowance
  vec3 push{0}, point{0};  // point: the worst arm point (world)
  std::string part, against;
};
ArmClearance armClearance(const BodyClearanceModel& model, const std::vector<mat4>& G, char side);
// Signed gap (metres, < 0 inside) of world point p to one body section whose bone has global Gb (T-040: exposed for
// fit checks against the mesh).
float bodySectionGap(const BodyCapsule& section, const mat4& Gb, vec3 p);
// Elbow pole tracks "<prefix>pole.<hand bone>" (world direction the elbow should point to) with ".weight": swings the
// upper arm about the shoulder -> wrist axis, so the wrist stays where IK put it and only the elbow moves (the hand keeps
// its world rotation; bone heads only, as G is built from pivots without scale). Runs after
// IK and before the orientation constraint (scene.cpp).
void applyArmPoles(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                   const mat4& world, Pose& pose);
constexpr float kArmBodyMargin = 0.005f;  // clearance kept between the arm and the body capsules (metres)

// ------------------------------------------------------------------------ always-on arm-body clearance (T-040)
// A pose post-pass for every character and every source of arm motion (clips, base/auto idle, emotions, IK,
// interactions): after the full pose is evaluated, upper arm (past the armpit band), forearm and hand are pushed out
// of the body sections by the smallest change of the shoulder and elbow rotations along one rotation path (it moves
// the penetrating points' deficit-weighted centroid radially away from the spine axis; the angle is the smallest that
// reaches the target). The result is a pure function of the evaluated pose (no state): deterministic and
// frame-rate independent, and continuous in time because the path direction varies continuously with the pose and
// the target gap is a C1 ramp of the arm's own gap:
//   gap >= margin + band: untouched (points resting nearer than that at rest count from their rest gap);
//   below that: target = gap + s(margin + band - gap), s(x) = x^2 / 4band (x < 2band), x - band (beyond),
// so the output gap is >= margin everywhere and its slope is continuous (no pop when the arm starts to touch).
// `pin` (the arm's IK weight) keeps the wrist where IK put it: at pin 1 only the elbow swings about the shoulder ->
// wrist axis, so contacts and held props stay exact; `keepHand` (IK or orientation-constraint weight) keeps the
// hand's world rotation (a held cup stays upright).
struct ArmPostPassOptions {
  // Output floor above the body sections. Larger than the interaction margin: measured against the skinned mesh the
  // fitted sections run up to ~7 mm inside the surface where an arm meets it (T-040 evidence), so 9 mm keeps the
  // mesh itself clear.
  float margin = 0.009f;
  float band = 0.004f;      // width of the C1 blend above the margin (metres)
  float armpit = 0.4f;      // upper-arm points nearer the shoulder pivot than this fraction are the armpit band:
                            // they fold with the shoulder joint and are not moved for (reported in armClearance only)
  float step = 0.01f;       // coarse search step along the correction path (radians), then bisection
  float maxAngle = 1.2f;    // longest correction searched (radians)
};
struct ArmPostPassResult {
  float before = 1e9f, after = 1e9f;  // worst gap (with the rest allowance) of the considered arm points
  bool changed = false;
};
// Worst gap of one arm over the post-pass's points (all parts; the armpit band excluded).
float armBodyGap(const BodyClearanceModel& model, const std::vector<mat4>& G, char side,
                 const ArmPostPassOptions& options = {});
ArmPostPassResult applyArmBodyClearance(const Skeleton& skeleton, const BodyClearanceModel& model, const mat4& world,
                                        char side, float pin, float keepHand, Pose& pose,
                                        const ArmPostPassOptions& options = {});

// Compile state shared by the interaction actions of one compileActions() pass.
struct InteractionContext {
  struct Hold {
    int prop = -1;            // held prop, -1 = empty hand
    quat orient{1, 0, 0, 0};  // the hand's world orientation while holding
  };
  std::map<std::pair<int, char>, Hold> hands;  // (character, side)
  // Exact contacts, re-corrected after all actions are compiled (later actions can change the body at a contact).
  struct Contact {
    int character = -1;
    char side = 'R';
    double frame = 0;
    int prop = -1;
    std::string socket;
    bool placeTarget = false;  // false: palm -> prop socket; true: prop socket -> `target`
    vec3 target{0};
  };
  std::vector<Contact> contacts;
  // Spans in which a hand holds still for someone else (hand-over giver): the clearance pass does not move them.
  struct Freeze {
    int character = -1;
    char side = 'R';
    double from = 0, to = 0;
  };
  std::vector<Freeze> frozen;
  bool parentsChecked = false;  // authored prop parents are checked before the first interaction evaluates props
};

}  // namespace plush
