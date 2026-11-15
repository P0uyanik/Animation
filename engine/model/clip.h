// Animation clips (plush.clip/1, docs/ANIMATION_CLIPS.md): character-independent body motion authored once on the
// neutral mannequin (or converted from motion capture), retargeted to any humanoid at playback.
//
// A clip stores, per shared humanoid ROLE (never a character's bone name), local rotations relative to the neutral
// REFERENCE POSE (pipeline/charsys/rig_profiles/humanoid_rigify.json "reference_pose", embedded in every clip):
//   posed frame of a role  P = R · Fref        (Fref: reference frame from ref_dir / ref_twist)
//   local clip rotation    L = R_parent⁻¹ · R  (parent = the role's semantic parent)
// A character is described by generated RETARGET DATA (its rest direction and twist reference per role, written by
// export_engine.py into the package, or derived from the package skeleton with the same rules). With the character's
// rest frame C, the per-role correction A = Fref · C⁻¹ gives the bone's rotation relative to its axis-aligned rest:
//   G_role = G_semanticParent · A_parent⁻¹ · L · A_role
// One algorithm for every character; no per-character code or data.
#pragma once
#include <filesystem>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

// ------------------------------------------------------------------ reference pose (shared, from the rig profile)
struct ReferenceRole {
  std::string name, parent;  // parent: semantic parent role ("" = character space)
  std::string end;           // rest direction: towards this role's head ...
  vec3 endDir{0};            // ... or this fixed direction (non-zero)
  bool continueFromParent = false;  // ... or from the parent role's head through this head
  bool fallbackParentDir = false;   // if `end` is missing: the parent's direction
  std::string twistFrom[2];         // twist reference: head(twistFrom[0]) - head(twistFrom[1]) ...
  vec3 twistHint{0, 0, 1};          // ... else this hint (made perpendicular to the direction)
  vec3 refDir{0, 1, 0}, refTwist{0, 0, 1};
};
struct ReferencePose {
  int version = 0;
  std::vector<ReferenceRole> roles;  // semantic parents precede children; '.L' roles mirrored to '.R'
  std::map<std::string, int> index;
  bool valid() const { return version > 0 && !roles.empty(); }
  const ReferenceRole* find(const std::string& role) const;
};
// From a "reference_pose" block (rig profile or clip).
Result<ReferencePose> referencePoseFromJson(const Json& j);

// ------------------------------------------------------------------ character retarget data (generated)
struct RetargetRole {
  vec3 dir{0, 1, 0}, twist{0, 0, 1};  // rest direction and twist reference (engine axes, unit, perpendicular)
  float length = 0;
};
struct RetargetData {
  int referenceVersion = 0;
  std::map<std::string, RetargetRole> roles;  // roles the character has
  float height = 0;     // head-role pivot height above the ground (y = 0)
  float legLength = 0;  // thigh -> shin -> foot pivots
  std::string source;   // "package" or "derived"
};
// The same rules as export_engine.py: directions and twist references from the role pivots of the skeleton.
RetargetData deriveRetarget(const Skeleton& skeleton, const ReferencePose& ref);
// From a package "retarget" block (export_engine.py); fails on a malformed block.
Result<RetargetData> retargetFromJson(const Json& block);
Json retargetToJson(const RetargetData& r);
// Largest angle (degrees) between corresponding direction / twist vectors of two retarget data sets (roles of `a`).
float retargetMaxDifferenceDeg(const RetargetData& a, const RetargetData& b);

// ------------------------------------------------------------------ clips
struct ClipTrack {
  std::vector<double> frames;  // clip frames (sorted); dense samples have frames 0, 1, 2, ...
  std::vector<quat> values;
};
struct ClipData {
  std::string name;
  double fps = 30;
  int frameCount = 1;  // frames 0 .. frameCount-1
  bool loop = false;
  std::map<std::string, ClipTrack> tracks;  // role -> local rotations (reference space)
  std::vector<std::string> mask;            // roles the clip drives (default: its track roles)
  std::string mirrorL = ".L", mirrorR = ".R";
  // Root motion: translation in character space divided by the leg length (scaled per character), heading (degrees).
  std::vector<double> rootFrames, headingFrames;
  std::vector<vec3> rootValues;
  std::vector<float> headingValues;
  std::string rootScale = "leg_length";
  ReferencePose reference;
  Json raw;  // the file as read (unknown fields are preserved by tools)
  double duration() const { return loop ? frameCount / fps : (frameCount - 1) / fps; }  // seconds
  bool hasRoot() const { return !rootFrames.empty(); }
  bool hasHeading() const { return !headingFrames.empty(); }
};
Result<ClipData> clipFromJson(const Json& j, const std::string& name = "");
Result<ClipData> loadClip(const std::filesystem::path& path);
std::string mirrorRole(const ClipData& c, const std::string& role);

// One sampled pose of a clip (reference-space local rotations per role, root motion in clip units).
struct ClipSample {
  std::map<std::string, quat> local;
  vec3 root{0};
  float heading = 0;
};
// Samples at a clip frame (fractional; wraps when the clip loops, holds the ends otherwise). Root motion of a loop
// accumulates its per-cycle displacement (no reset jump). `mirror` swaps L/R roles and reflects across x = 0.
ClipSample sampleClip(const ClipData& clip, double clipFrame, bool mirror = false);

// Per-character playback data for one clip (reference) and one skeleton: role -> bone, A = Fref · C⁻¹.
struct ClipBinding {
  struct Role {
    std::string name;
    int bone = -1, parentRole = -1;  // parentRole: index into roles (-1 = character space)
    quat A{1, 0, 0, 0};
  };
  std::vector<Role> roles;  // semantic order
  std::map<std::string, int> roleIndex;
  float legLength = 0;
  std::string retargetSource;
};
ClipBinding bindClip(const Skeleton& skeleton, const ReferencePose& ref, const RetargetData& data);
// Target local rotations (engine, relative to each bone's parent) for a sample, given the pose so far. Roles the clip
// does not drive keep their current rotation (layering in local space); `weight(role)` in [0, 1] blends each role.
template <class WeightFn>
void applyClipSample(const Skeleton& skeleton, const ClipBinding& b, const ClipSample& s, Pose& pose, WeightFn weight);
// Rotation-only global frames of the pose (rest frames are axis aligned).
quat globalRotation(const Skeleton& skeleton, const Pose& pose, int bone);

// Posed world direction / twist reference of a role (for measurements): G · restDir, G · restTwist.
vec3 posedRoleDirection(const Skeleton& skeleton, const std::vector<mat4>& globals, const RetargetData& data, const std::string& role);
vec3 posedRoleTwist(const Skeleton& skeleton, const std::vector<mat4>& globals, const RetargetData& data, const std::string& role);

// ------------------------------------------------------------------ template implementation
template <class WeightFn>
void applyClipSample(const Skeleton& sk, const ClipBinding& b, const ClipSample& s, Pose& pose, WeightFn weight) {
  // Global rotations of the roles as they are posed after this layer (semantic order: parents first).
  std::vector<quat> G(b.roles.size(), quat(1, 0, 0, 0));
  for (size_t r = 0; r < b.roles.size(); ++r) {
    const auto& role = b.roles[r];
    if (role.bone < 0) continue;
    auto it = s.local.find(role.name);
    float w = it == s.local.end() ? 0.0f : weight(role.name);
    if (w > 0) {
      const quat Gp = role.parentRole >= 0 ? G[size_t(role.parentRole)] : quat(1, 0, 0, 0);
      const quat Ap = role.parentRole >= 0 ? b.roles[size_t(role.parentRole)].A : quat(1, 0, 0, 0);
      const quat Gt = glm::normalize(Gp * glm::inverse(Ap) * it->second * role.A);
      const int ep = sk.bones[size_t(role.bone)].parent;
      const quat Gep = ep >= 0 ? globalRotation(sk, pose, ep) : quat(1, 0, 0, 0);
      const quat target = glm::normalize(glm::inverse(Gep) * Gt);
      quat& cur = pose.local[size_t(role.bone)];
      cur = w >= 1.0f ? target : glm::normalize(glm::slerp(cur, target, w));
    }
    G[r] = globalRotation(sk, pose, role.bone);
  }
}

}  // namespace plush
