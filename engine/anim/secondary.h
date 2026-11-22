// Secondary motion: spring chains (hair locks, ears, tails, bows ...) layered on top of the evaluated pose.
//
// Character independent and data driven. A character package may carry a "dynamics" block (written by the
// pipeline, e.g. groom/1 chain bones; format in docs/SECONDARY_MOTION.md) listing chains of bones and collision
// shapes; a scene may override it per character. Without a block nothing changes: the layer is off.
//
// Model: every chain joint is a point mass that follows its kinematic target (the joint where the clips, life and
// constraints put it) through a damped spring (stiffness, damping), with air drag and gravity relative to the
// modelled rest shape (no sag in the rest pose; when the parent tilts, gravity pulls the chain back down). Segment
// lengths are kept, each segment stays within limitDeg of its kinematic direction, and joints are pushed out of the
// colliders (spheres and capsules that ride on bones). The root joint is the chain's first bone pivot and is kinematic.
//
// Deterministic and frame-rate independent: the state advances on a fixed time grid (substepHz, seconds since the
// scene's first frame; a preroll before it settles the start pose), and the kinematic driver is sampled at the grid
// times. Any frame is the same value whatever order frames are asked in (cached checkpoints on the same grid).
//
// Contact (T-183, opt-in per chain, "contact" block): colliders named "solid" push to their full radius (moving body
// parts such as hands, forearms and ears: no exemption for a kinematic target that lies inside them), the segments
// between joints collide as capsules (not only the joints), and gravity is scaled by (1 - anchor weight) per joint
// (a joint whose target an anchor bone carries already hangs where that bone puts it). A chain without the block
// takes exactly the path it took before.
// Round 2 keys of the same block: "radii" (one collision radius per joint: the real thickness of what the chain
// carries, e.g. a coiled lock; segments are tapered capsules) and "rest" (resting contact: every collider of the chain
// pushes to its full radius, a pushed joint takes the collider's own velocity along the contact normal and loses
// tangential speed by "friction", so hair that lies on a moving shoulder or sleeve stays on it quietly).
#pragma once
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct SpringParams {
  float stiffness = 60.0f;      // 1/s^2: spring towards the kinematic joint (higher = stiffer, faster)
  float stiffnessTip = -1.0f;   // < 0: same as stiffness; else linear from the first to the last moving joint
  float damping = 6.0f;         // 1/s: damping of the velocity relative to the kinematic joint (overshoot vs settle)
  float gravity = 1.0f;         // scale of 9.81 m/s^2, relative to the rest shape
  float drag = 0.5f;            // 1/s: air drag on the absolute velocity
  float limitDeg = 60.0f;       // max angle between a segment and its kinematic direction
  float radius = 0.01f;         // joint radius for collisions (m)
};

// Opt-in contact behaviour of one chain (T-183; chain key "contact"). Default: off, the solver path is unchanged.
struct ChainContact {
  bool set = false;                // the chain carries a "contact" block (written back by dynamicsToJson)
  std::vector<std::string> solid;  // collider names pushed to their full radius; joined to the chain's colliders
  bool segments = false;           // segments (capsules of the chain radius) collide, not only the joints
  bool anchoredGravity = false;    // gravity scaled by (1 - anchor weight) per joint
  std::vector<float> radii;        // collision radius per joint (root first, bones + 1 values); empty = params.radius
  bool rest = false;               // resting contact: all colliders at full radius, inelastic, with friction
  float friction = 40.0f;          // 1/s: decay of the sliding speed of a joint in contact (rest only)
  float maxSwing = 12.0f;          // rad/s: how much faster than its kinematic direction a segment may turn (rest only; 0 = no cap)
  bool carry = false;              // rest + max_swing: the cap yields to the speed of the collider that pushes the joint
  bool clearTargets = false;       // rest: a joint's spring target is taken out of the chain's colliders first
  float locks = 0.0f;              // > 0: joints keep off the joints of the other chains with the key by locks x (sum of the two radii)
};

struct SpringChain {
  std::string name;
  std::string group;               // e.g. the groom structure it came from (overrides may address a group)
  std::string preset;              // spring preset the parameters started from ("" = the block's defaults)
  std::vector<std::string> bones;  // root first; each bone is the child of the previous one
  vec3 tip{0};                     // rest-space end point of the last bone
  SpringParams params;
  std::vector<std::string> colliders;  // collider names; empty = all
  // Optional anchor: the kinematic target of joint k is blended towards where `anchorBone` carries its rest
  // position, by anchorWeights[k] (one per joint, root first; e.g. long hair that rests on the back follows the
  // chest more than the head, like its static skin binding).
  std::string anchorBone;
  std::vector<float> anchorWeights;
  ChainContact contact;
};

struct DynamicsCollider {
  enum class Kind { Sphere, Capsule, Box, Cylinder };
  std::string name;
  Kind kind = Kind::Sphere;
  std::string bone;  // the collider rides on this bone; empty for a box (world space)
  vec3 a{0}, b{0};   // rest-space centre (sphere) or segment ends (capsule); min and max corner (box, world space)
  float radius = 0.05f;  // box: the rounding of its edges (at most its smallest half extent)
  // Scene colliders that move with something outside the character (T-183 round 3; scene override only):
  std::string character;  // `bone` is a bone of this other scene character; a, b in that character's rest space
  std::string prop;       // the collider rides on this scene prop; a, b (any kind) in the prop's own frame
  // Cylinder (on a prop only): a, b = the centres of its two end faces, radius = its radius, round = the rounding of
  // its rims (at most the radius and half the height)
  float round = 0.003f;
};

struct DynamicsSpec {
  bool enabled = false;  // true when a package block is present (a scene may switch it off)
  float substepHz = 240.0f;
  float prerollSec = 1.0f;
  std::vector<SpringChain> chains;
  std::vector<DynamicsCollider> colliders;
  // Accessory secondary motion (T-061): named spring presets (added to / replacing the built-in ones) and chains
  // attached to garment or accessory bones by name, resolved against the skeleton (resolveAccessoryChains).
  std::map<std::string, SpringParams> presets;
  std::vector<Json> attach;
};

// Built-in spring presets for accessory chains (T-061; values and rationale in docs/SECONDARY_MOTION.md):
// "drawstring" (a light cord: soft, swings, settles slowly), "strap" (a heavier band: stiffer, little swing),
// "bow_tail" (ribbon ends: soft, high air drag), "tassel" (a short heavy tip: soft, gravity dominated).
const std::map<std::string, SpringParams>& builtinSpringPresets();
// Turns the spec's "attach" entries into chains: {"name", "bones": [...] | "prefix": "<p>" (bones named <p><n>,
// <p>.<n>, <p>_<n> or <p>-<n>, in number order, each the child of the previous), "preset"?, "group"? (default: the
// preset), "tip"? (default: the last segment extended by its own length, or 3 cm along the bone from its parent for
// a single bone), "colliders"?, "anchor"?, spring keys as for chains}. The entries are consumed. A missing bone,
// prefix without bones, unknown preset or a bone already in a chain is an error.
Result<void> resolveAccessoryChains(DynamicsSpec& spec, const Skeleton& skeleton);

// Package "dynamics" block (engine axes, rest space). A null/absent block gives a disabled spec.
Result<DynamicsSpec> dynamicsFromJson(const Json& j);
Json dynamicsToJson(const DynamicsSpec& spec);
// Scene override (scene character "dynamics"): false | true | {"enabled", "substep_hz", "preroll_s",
// "chains": {"<chain name>" | "<group>" | "*": {stiffness, stiffness_tip, damping, gravity, drag, limit_deg, radius}},
// "presets": {...}, "attach": [...], "colliders": [...]}. More specific keys win: "*" first, then the group, then
// the chain name. "colliders" (T-183 round 3) adds colliders in the package format, or boxes of the scene:
// {"name", "type": "box", "space": "world", "min": [x, y, z], "max": [x, y, z], "radius"? (edge rounding, 0.01)};
// or shapes that ride on another character's bone ({..., "character": "<scene name>", "bone": "<its bone>"}) or on a
// scene prop ({..., "prop": "<name>"}; a box then needs no "space"); the scene passes their frames per step
// (SpringChainSolver::External; without it they are not there). A new collider joins every chain. A chain is pushed to a collider's full radius only with contact.rest or when
// contact.solid names it; otherwise never farther than its kinematic joint is (a table then holds nothing).
// "attach" adds accessory chains (resolveAccessoryChains) and switches the layer on unless "enabled" is false.
Result<void> applyDynamicsOverride(DynamicsSpec& spec, const Json& over);

// The evaluated spring-chain layer of one character. Thread safe (an internal cache guarded by a mutex).
class SpringChainSolver {
 public:
  // Kinematic bone globals (boneGlobals: column 3 = pivot) of the character at a (fractional) scene frame.
  using Driver = std::function<std::vector<mat4>(double frame)>;
  // Scene colliders (T-183 round 3): what a collider outside the character rides on, and the callback that gives the
  // frame of each at a (fractional) scene frame, one per externals() entry in that order: rest space of the other
  // character's bone (its skinning frame: bone global x translate(-rest head)) or the prop's own frame -> world.
  // It must not evaluate this solver (the scene passes kinematic frames).
  struct ExternalRef {
    std::string character, bone, prop;
  };
  using External = std::function<std::vector<mat4>(double frame)>;
  const std::vector<ExternalRef>& externals() const { return externals_; }
  // simulate = false: no secondary motion; chains with an anchor are only posed at their (anchored) kinematic
  // targets, segment lengths kept (the static equivalent of the chain). Chains without an anchor stay kinematic.
  static Result<std::shared_ptr<SpringChainSolver>> create(const Skeleton& skeleton, const DynamicsSpec& spec,
                                                           bool simulate = true);
  // Replaces the chain bones' globals (and those of their non-chain descendants) for `frame`. `globals` are the
  // kinematic globals at `frame`. Frames before frameStart are left kinematic.
  // `external`: the frames of externals(); empty = the colliders that ride on them are left out.
  void apply(double frame, double frameStart, double fps, const Driver& kinematic, std::vector<mat4>& globals,
             const External& external = {}) const;
  // Drops cached states (call when anything that drives the character changes).
  void reset() const;
  size_t chainCount() const { return chains_.size(); }

 private:
  struct Chain {
    std::vector<int> bones;     // skeleton indices, root first
    std::vector<vec3> rest;     // rest joint positions: heads of the bones, then the tip
    std::vector<float> length;  // segment lengths (rest)
    std::vector<int> colliders;
    SpringParams p;
    int anchor = -1;
    std::vector<float> anchorW;
    std::vector<char> solid;  // per entry of `colliders`: full-radius push (contact.solid); empty = none
    bool segments = false, anchoredGravity = false;
    std::vector<float> radii;  // per joint (contact.radii); empty = p.radius
    bool restContact = false;  // contact.rest
    float friction = 0, maxSwing = 0;
    float locks = 0;  // contact.locks
    bool carry = false;  // contact.carry
    bool clearTargets = false;  // contact.clear_targets
  };
  struct Collider {
    DynamicsCollider::Kind kind;
    int bone;  // -1: world space (box; a, b = the core's min and max corner, radius = its rounding)
    vec3 a, b, head;
    float radius;
    int ext = -1;  // >= 0: rides on externals_[ext] (a, b in that frame; a box: its min and max corner, not shrunk)
    float round = 0;  // cylinder: the rounding of its rims
  };
  struct State {
    std::vector<vec3> x, v, xk;  // per joint (all chains concatenated): position, velocity, kinematic position
    std::vector<vec3> ca, cb;    // collider ends at the end of the last step (only kept for contact.rest chains)
    std::vector<char> hit;       // per joint: a collider pushed it in the last step (only kept for contact.rest chains)
    std::vector<mat4> ext;       // the external frames of the last step (only with external colliders)
    bool fresh = false;          // the first step from the preroll's start (contact.clear_targets starts outside)
  };
  void targets(const std::vector<mat4>& g, std::vector<vec3>& xk) const;
  void step(State& s, double dt, const std::vector<mat4>& g, const std::vector<mat4>& ext) const;
  void write(const State& s, std::vector<mat4>& globals) const;

  Skeleton skeleton_;
  std::vector<Chain> chains_;
  std::vector<Collider> colliders_;
  std::vector<ExternalRef> externals_;
  std::vector<size_t> offset_;  // first joint of each chain in State
  size_t joints_ = 0;
  bool simulate_ = true;
  bool keepShapes_ = false;  // a contact.rest chain needs the colliders' previous positions (State::ca, cb)
  double hz_ = 240, preroll_ = 1;
  // Cache: states on the step grid; key = step index since the first frame. Invalidated when the parameters
  // (frameStart, fps) change or when the driver no longer reproduces a checkpoint's kinematic joints.
  mutable std::mutex mutex_;
  mutable std::map<long long, State> checkpoints_;
  mutable double cacheStart_ = 0, cacheFps_ = 0;
};

}  // namespace plush
