// Locomotion layer for mocap clips (T-175): the per-clip chibi "style" filter and the foot-lock pin.
// Both are opt-in per clip: a clip without a "style" block plays exactly as before (scene/clip_layers.cpp).
//
// Clip "style" block (written by pipeline/clips/import_bvh.py, docs/evaluation/animation/T-175/README.md):
//   {"version": 1, "lean": 0.6, "head_level": 0.5, "stride": 1.0, "arm_swing": 0.85, "arm_center": {role: [w, x, y, z]},
//    "tempo": 1.15, "foot_lock": true, "foot_lead": 3, "foot_in": 2, "foot_release": 6}
//   lean        share of the trunk lean kept on hips, spine, chest and neck (swing away from upright; the turn about
//               the vertical axis is kept). The thighs are compensated, so the legs keep their own directions.
//   head_level  share of the trunk's remaining lean that the head undoes (0 = the clip's own head; 1 = the head keeps
//               the orientation it would have on an upright trunk), so a big head stays up while the body leans.
//   stride      scale of the horizontal root motion (root motion is already in leg lengths, so 1 = the source's stride
//               in the character's own leg lengths).
//   arm_swing   scale of the arm motion around arm_center (the clip's mean arm pose).
//   tempo       clock multiplier (short legs step quicker).
//   foot_lock   pin each foot with two-bone leg IK on the clip's contacts {"type": "foot_plant", "role", "frames": [a, b]}
//               (b may run past the last frame of a loop: the plant crosses the seam). The pin eases in from foot_lead clip
//               frames before the plant to foot_in frames into it (the landing foot settles on where it is at
//               a + foot_in) and lets go over foot_release clip frames after b. With root motion the clip's root is also shifted vertically by one
//               constant per clip and character, so planted ankles sit at their rest height (scene/clip_layers.cpp).
#pragma once
#include <map>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct LocomotionStyle {
  bool enabled = false;  // the clip has a "style" object
  float lean = 1, stride = 1, armSwing = 1, headLevel = 0;
  double tempo = 1;
  bool footLock = false;
  double footRelease = 6, footEaseIn = 2, footLead = 3;
  std::map<std::string, quat> armCenter;
};
// From a clip's raw JSON (ClipData::raw). No or malformed "style": disabled, every value neutral.
LocomotionStyle locomotionStyle(const Json& clip);
// The tempo alone (1 when the clip has no style block).
double locomotionTempo(const Json& clip);

// Applies lean, arm swing and stride to one sample: `local` = reference-space local rotations per role (ClipSample),
// `root` = root translation in leg lengths. `mirror`: the sample is mirrored (L/R swapped, reflected across x = 0).
void applyLocomotionStyle(const LocomotionStyle& style, std::map<std::string, quat>& local, vec3& root, bool mirror);

struct FootPlant {
  std::string role;  // "foot.L" / "foot.R"
  double a = 0, b = 0;  // clip frames, inclusive
};
std::vector<FootPlant> footPlants(const Json& clip);

// The plant that holds a foot at a clip frame. `clipFrame` is the layer's running clip frame (not wrapped; a
// non-looping clip holds its last frame). start = the running clip frame whose pose gives the pin position (the plant's
// first frame + easeIn), weight = the pin weight: easing in from `lead` frames before the plant to `easeIn` frames
// into it (at once when the plant is there from the clip's first frame), 1 while planted, easing to 0 over `release`
// frames after the plant.
struct PlantState {
  bool active = false;
  double start = 0;
  float weight = 0;
};
PlantState plantAt(const std::vector<FootPlant>& plants, const std::string& role, double clipFrame, int frameCount, bool loop,
                   double release, double easeIn = 0, double lead = 0);

// Pins the pivot of `footBone` at `target` (character space, the space of boneGlobals with an identity world) with
// two-bone IK on its parent and grandparent, and keeps the foot's own orientation. weight in [0, 1].
void pinFoot(const Skeleton& skeleton, Pose& pose, int footBone, vec3 target, float weight);
// How far the hip of `footBone`'s leg (its grandparent's pivot in `globals`, see boneGlobals) has to move straight
// down so that the ankle can reach `target` with the leg at most `stretch` of its full length; 0 when it already can.
float footReachDrop(const Skeleton& skeleton, const std::vector<mat4>& globals, int footBone, vec3 target, float stretch = 0.995f);

}  // namespace plush
