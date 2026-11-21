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
  enum class Kind { Sphere, Capsule };
  std::string name;
  Kind kind = Kind::Sphere;
  std::string bone;  // the collider rides on this bone
  vec3 a{0}, b{0};   // rest-space centre (sphere) or segment ends (capsule)
  float radius = 0.05f;
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
// "presets": {...}, "attach": [...]}. More specific keys win: "*" first, then the group, then the chain name.
// "attach" adds accessory chains (resolveAccessoryChains) and switches the layer on unless "enabled" is false.
Result<void> applyDynamicsOverride(DynamicsSpec& spec, const Json& over);

// The evaluated spring-chain layer of one character. Thread safe (an internal cache guarded by a mutex).
class SpringChainSolver {
 public:
  // Kinematic bone globals (boneGlobals: column 3 = pivot) of the character at a (fractional) scene frame.
  using Driver = std::function<std::vector<mat4>(double frame)>;
  // simulate = false: no secondary motion; chains with an anchor are only posed at their (anchored) kinematic
  // targets, segment lengths kept (the static equivalent of the chain). Chains without an anchor stay kinematic.
  static Result<std::shared_ptr<SpringChainSolver>> create(const Skeleton& skeleton, const DynamicsSpec& spec,
                                                           bool simulate = true);
  // Replaces the chain bones' globals (and those of their non-chain descendants) for `frame`. `globals` are the
  // kinematic globals at `frame`. Frames before frameStart are left kinematic.
  void apply(double frame, double frameStart, double fps, const Driver& kinematic, std::vector<mat4>& globals) const;
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
  };
  struct Collider {
    DynamicsCollider::Kind kind;
    int bone;
    vec3 a, b, head;
    float radius;
  };
  struct State {
    std::vector<vec3> x, v, xk;  // per joint (all chains concatenated): position, velocity, kinematic position
  };
  void targets(const std::vector<mat4>& g, std::vector<vec3>& xk) const;
  void step(State& s, double dt, const std::vector<mat4>& g) const;
  void write(const State& s, std::vector<mat4>& globals) const;

  Skeleton skeleton_;
  std::vector<Chain> chains_;
  std::vector<Collider> colliders_;
  std::vector<size_t> offset_;  // first joint of each chain in State
  size_t joints_ = 0;
  bool simulate_ = true;
  double hz_ = 240, preroll_ = 1;
  // Cache: states on the step grid; key = step index since the first frame. Invalidated when the parameters
  // (frameStart, fps) change or when the driver no longer reproduces a checkpoint's kinematic joints.
  mutable std::mutex mutex_;
  mutable std::map<long long, State> checkpoints_;
  mutable double cacheStart_ = 0, cacheFps_ = 0;
};

}  // namespace plush
