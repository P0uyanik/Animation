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
//       T-112b optional keys (written by the verb expander from a prop's affordances; absent = today's tracks):
//         shape:"wrap"|"pinch"|"palm"|"hook"|"cradle" (non-wrap: open / closed hand poses of the shape instead of
//         kOpen and the contact search, also on release), approach:[x,y,z] (prop frame: the side the palm comes
//         from), band:[lo,hi] + thumb:"opposed"|"along"|"tucked" (Step keys "hand.<side>.band" = (lo, hi, thumb) at
//         start; lo / hi relative to the grasp centre along the grasp axis; read by T-051), follower:true (two-hand
//         follower: the prop must already be held by the same character's other hand, which stays its parent).
//       T-112c: the shape's poses come from the hand-shape table (content/hand_shapes above the scene; wrap = kOpen
//         and today's search); graspFace:true (verb grasps under the finger gate) on a socket on a box face keys the
//         per-finger face search (.grasp centre / .graspRadius half thickness / .graspFace inward normal, hand rest
//         frame) for wrap, pinch and palm.
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
#include "anim/hand_shape.h"
#include "anim/personality.h"
#include "model/character.h"
#include "scene/collision.h"

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

// ------------------------------------------------------------------------------------- arm-body clearance (T-030, T-047)
// The character's collision body (scene/collision.h, T-047) is what the arms are planned and measured against: torso
// sections (BodyCapsule = CollisionSection: short elliptical capsules along the spine, fitted to the skinned rest
// meshes, garments included) and per-bone limb capsules (the wrist half of each forearm and each hand). The rest pose
// is clear by construction. ArmPoint samples of the arm's skinned surface (T-030) remain for the upper arm and elbow
// half of the forearm, which rest against the body's side: they are reported (upperGap), not planned.
using BodyCapsule = CollisionSection;
struct ArmPoint {
  glm::ivec4 joint{0};
  vec4 weight{0};
  vec3 local[4];        // rest position relative to each joint's head
  float mobility = 0;   // skin weight on the IK chain's forearm and hand (how much the point follows the wrist)
  int part = 0;         // 0 upper arm and elbow half of the forearm, 1 wrist half of the forearm, 2 hand
  float allowance = 0;  // <= 0: how deep the point rests against the body at rest (minus the margin)
};
struct ArmModel {
  int upper = -1, fore = -1, hand = -1;
  std::vector<ArmPoint> points;
};
struct BodyClearanceModel {
  std::vector<BodyCapsule> body;  // = collision.sections
  ArmModel arm[2];  // 0 = L, 1 = R
  CollisionBody collision;
  bool valid = false;
  std::string source;  // "mesh" (fitted to skinned vertices) or "skeleton" (proportions only, no arm points)
};
// Builds the model: the collision body from the package's "collision" block when it has a valid one, else derived
// from the meshes (needs hips, chest and the arm chains; invalid otherwise).
BodyClearanceModel bodyClearanceModel(const Skeleton& skeleton, const std::vector<SkinnedMesh>& meshes,
                                      const Json& collisionBlock = Json());
// Smallest gap (metres; negative = inside) between one arm's limb capsules (forearm wrist half, hand) and the body
// sections for posed bone globals G. `push` is the unit world direction that moves the worst point out of the body
// (the gradient of the gap), `mobility` how much that point follows the wrist (hand 1, forearm 0.6); `part` /
// `against` name it. `upperGap` is the surface-sample gap of the upper arm and the elbow half of the forearm,
// reported only (relative to their rest depth).
struct ArmClearance {
  float gap = 1e9f, upperGap = 1e9f, mobility = 1;
  float rawGap = 1e9f;  // = gap (the collision body has no rest allowance)
  vec3 push{0}, point{0};  // point: the worst arm point (world)
  std::string part, against;
};
ArmClearance armClearance(const BodyClearanceModel& model, const std::vector<mat4>& G, char side);
// The arm's clearance after the smallest elbow swing (up to `limit`, < 0: the full range) that clears its forearm;
// the wrist and hand stay. Used to score candidate wrist positions before the swing is planned.
float swungArmGap(const BodyClearanceModel& model, const std::vector<mat4>& G, char side, float limit = -1.0f);
// Elbow swing tracks "<prefix>swing.<hand bone>" (x: radians about the shoulder -> wrist axis; planned by the T-047
// collision planner) and elbow pole tracks "<prefix>pole.<hand bone>" (world direction the elbow should point to) with ".weight": swing the
// upper arm about the shoulder -> wrist axis, so the wrist stays where IK put it and only the elbow moves (the hand keeps
// its world rotation; bone heads only, as G is built from pivots without scale). Runs after
// IK and before the orientation constraint (scene.cpp). It also applies the T-096 head clearance tilt
// "<prefix>headTilt" (applyHeadTilt) at the same point of the pose path; without that track nothing changes.
void applyArmPoles(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame,
                   const mat4& world, Pose& pose);
// T-096 head clearance tilt: "<prefix>headTilt" (world rotation vector, radians; planned by the interaction option
// headVolumes) turns the neck about its joint after IK and look-at (the head follow and the neck assist would aim it
// back); the eye bones keep their world rotation, so the gaze stays on its target.
void applyHeadTilt(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                   Pose& pose);
// T-134 reach mechanics: the body lead of a reach ("<prefix>reach.lead" and its companions, keyed by the reaches when
// the scene sets "reachMechanics"); applied by applyArmPoles before everything else. No track: nothing changes.
void applyReachLead(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                    Pose& pose);
constexpr float kArmBodyMargin = kCollisionMargin;  // clearance kept between the arm and the body (metres)

// Compile state shared by the interaction actions of one compileActions() pass.
struct InteractionContext {
  struct Hold {
    int prop = -1;            // held prop, -1 = empty hand
    quat orient{1, 0, 0, 0};  // the hand's world orientation while holding
    std::string socket;       // the prop socket the palm holds (T-096)
    std::string shape = "wrap";  // hand shape of the grasp (T-112b): wrap | pinch | palm | hook | cradle
    bool follower = false;       // T-112b two-hand follower: holds the prop without being its parent
    bool faceGrasp = false;      // T-112c: the grasp searches a box face (hand.<s>.graspFace); its release lets go of it
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
  // Hand-overs (T-096): the giver still holds the prop by `socket` while the receiver already carries it (receiver's
  // contact -> giver's release). With the scene's interaction option followSharedProp the giver's palm follows.
  struct Shared {
    int character = -1;
    char side = 'R';
    int prop = -1;
    std::string socket;
    double from = 0, to = 0, end = 0;  // contact, release, end of the giver's return
  };
  std::vector<Shared> shared;
  // T-112b two-handed grasps: the second hand of a grasp set holds the prop without being its parent; from its
  // contact to `to` (the leading hand's place contact, or the shot end) its wrist is keyed in the prop frame at every
  // frame and its palm contact is corrected per frame with the other contacts (finishInteractions).
  struct Follower {
    int character = -1;
    char side = 'R';
    int prop = -1;
    std::string socket;
    double from = 0, to = 1e30;
  };
  std::vector<Follower> followers;
  // T-134 reach mechanics: the body lead of each reach (scene key "reachMechanics"); the "<who>/reach.lead" and
  // "<who>/reach.shoulder.<upper arm>" tracks are the sum of a character's records.
  struct ReachLead {
    int character = -1;
    char side = 'R';
    double start = 0, contact = 0, anticipation = 0, recover = 0;  // frames
    vec3 lead{0}, shoulder{0};  // full torso lead (world rotation vector) and shoulder advance (world, metres)
    std::string shoulderTrack;
    vec3 clavicle{0};           // clavicle turn (world rotation vector); track "" = the rig has no clavicle
    std::string clavicleTrack;
    vec3 hip{0};                // hip shift (world, metres)
  };
  std::vector<ReachLead> reachLeads;
  bool parentsChecked = false;  // authored prop parents are checked before the first interaction evaluates props
  // Timing profile (T-104, the scene's "timing" key, calibrated by default since T-104d; anim/personality.h TimingProfile), resolved at the first
  // interaction action. It changes only the defaults of frames an action leaves out (without it: the defaults listed
  // at the top of this file):
  //   reach / grasp  contact = start + reach;  grasp:false end = contact + hold
  //   hold           end = start + max(hold, travel frames of the carry distance for this arm)
  //   place          contact = start + place;  end = contact + release
  //   handover       receiverStart = start + reaction_delay (receiver); contact = receiverStart + reach (receiver);
  //                  release = contact + shared_hold; end = release + release (giver)
  // each scaled by the acting character's personality (tempo.beat_scale / tempo.hold_scale) when it has one.
  std::optional<TimingProfile> timing;
  bool timingResolved = false;
  // T-112c: the shared hand-shape table (content/hand_shapes above the scene), loaded at the first non-wrap grasp.
  std::optional<HandShapeTable> handShapes;
  std::string handShapesError;
  bool handShapesResolved = false;
};

}  // namespace plush
