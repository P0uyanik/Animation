// Clip layers of the scene evaluator (actions of type "clip", see actions.cpp and model/clip.h).
// Order of a character's pose: keyed / generated tracks -> base clip (generated action motion added on top as a
// delta) -> emotion postures and gestures (action "emotion", tier 1) -> clip actions on their masks (walk keeps legs, hips and root while it walks; hand keys always win) ->
// life layer -> constraints (IK, hand pose, look) -> clip finger tracks (unless a hand track owns that hand).
#include <algorithm>
#include <map>

#include "scene/scene.h"

namespace plush {

namespace {
double smooth01(double x) {
  x = std::clamp(x, 0.0, 1.0);
  return x * x * (3 - 2 * x);
}
bool startsWith(const std::string& s, const char* p) { return s.rfind(p, 0) == 0; }
bool isFingerRole(const std::string& r) {
  return startsWith(r, "thumb") || (r.size() > 2 && r[0] == 'f' && r[1] >= '0' && r[1] <= '9');
}
bool isWalkRole(const std::string& r) {
  return r == "hips" || startsWith(r, "thigh.") || startsWith(r, "shin.") || startsWith(r, "foot.");
}
bool inMask(const ClipData& c, const std::string& role, bool mirror) {
  const std::string r = mirror ? mirrorRole(c, role) : role;
  return std::find(c.mask.begin(), c.mask.end(), r) != c.mask.end();
}
}  // namespace

double SceneEvaluator::ClipLayer::envelope(double f) const {
  if (base) return weight;
  if (f < start || f > end) return 0;
  auto ramp = [this](double x) { return linear ? std::clamp(x, 0.0, 1.0) : smooth01(x); };
  double in = blendIn > 0 ? ramp((f - start) / blendIn) : 1.0;
  double out = blendOut > 0 && end < 1e29 ? ramp((end - f) / blendOut) : 1.0;
  return weight * in * out;
}

double SceneEvaluator::ClipLayer::clipFrame(double f, double sceneFps) const {
  return std::max(0.0, f - start) * speed * clip->fps / std::max(1e-9, sceneFps);
}

RetargetData SceneEvaluator::retargetData(size_t c, const ReferencePose& ref) const {
  const CharacterAsset& asset = characters_[c].asset;
  if (asset.retargetBlock.is_object()) {
    auto r = retargetFromJson(asset.retargetBlock);
    if (r && r->referenceVersion == ref.version) return *r;
  }
  return deriveRetarget(asset.skeleton, ref);
}

void SceneEvaluator::applyClips(size_t c, double frame, Pose& pose, float& yawOffset) const {
  const auto& layers = clipLayers_[c];
  const Skeleton& sk = characters_[c].asset.skeleton;
  const CharacterAsset& asset = characters_[c].asset;
  const std::string prefix = scene_.characters[c].name + "/";
  const Clip& anim = scene_.animation;
  const double fps = scene_.rate.fps();
  // walk ownership of legs, hips and root (ramps over 4 frames at each end)
  double walk = 0;
  for (auto [s, e] : walkSpans_[c]) {
    double w = frame < s ? smooth01((frame - (s - 4)) / 4) : frame > e ? smooth01((e + 4 - frame) / 4) : 1.0;
    walk = std::max(walk, w);
  }
  auto handKeyed = [&](const std::string& role) {
    auto it = anim.tracks.find(prefix + role + ".rot");
    return it != anim.tracks.end() && !it->second.keys.empty();
  };
  for (const ClipLayer& L : layers) {
    const double env = L.envelope(frame);
    if (env <= 0) continue;
    const ClipSample s = sampleClip(*L.clip, L.clipFrame(frame, fps), L.mirror);
    if (L.base) {
      // Generated action motion (walk arm swing, reach lean) is kept as a change relative to the default pose.
      std::vector<std::pair<int, quat>> deltas;
      for (const auto& r : L.binding.roles) {
        if (r.bone < 0 || handKeyed(r.name) || !anim.generated) continue;
        const Track* t = anim.generated->find(prefix + r.name + ".rot");
        if (!t || t->keys.empty()) continue;
        auto d = asset.defaultPose.find(r.name);
        const quat q0 = d == asset.defaultPose.end() ? quat(1, 0, 0, 0) : eulerDegreesToQuat(d->second);
        deltas.push_back({r.bone, glm::inverse(q0) * pose.local[size_t(r.bone)]});
      }
      applyClipSample(sk, L.binding, s, pose, [&](const std::string& role) {
        return (isFingerRole(role) || handKeyed(role) || !inMask(*L.clip, role, L.mirror)) ? 0.0f : float(env);
      });
      for (auto& [b, d] : deltas) pose.local[size_t(b)] = glm::normalize(pose.local[size_t(b)] * d);
      const float wr = float(env * (1 - walk));
      pose.rootOffset += s.root * L.binding.legLength * wr;
      yawOffset += s.heading * wr;
      continue;
    }
    auto weightOf = [&](const std::string& role) {
      if (isFingerRole(role) || handKeyed(role) || !inMask(*L.clip, role, L.mirror)) return 0.0f;
      return float(isWalkRole(role) ? env * (1 - walk) : env);
    };
    if (L.tier == 1) {
      // Emotion layers blend in the clip's own (semantic, reference-space) rotations: each driven role's local
      // rotation goes from the underlying one to the clip's by the weight, so intensity k gives k x the deviation
      // from the underlying pose on every role (also on roles whose engine parent is not their semantic parent).
      ClipSample t = s;
      std::map<std::string, float> on;
      for (const auto& r : L.binding.roles) {
        auto it = t.local.find(r.name);
        if (r.bone < 0 || it == t.local.end()) continue;
        const float w = weightOf(r.name);
        if (w <= 0) continue;
        const quat Gp = r.parentRole >= 0 && L.binding.roles[size_t(r.parentRole)].bone >= 0
                            ? globalRotation(sk, pose, L.binding.roles[size_t(r.parentRole)].bone) : quat(1, 0, 0, 0);
        const quat Ap = r.parentRole >= 0 ? L.binding.roles[size_t(r.parentRole)].A : quat(1, 0, 0, 0);
        const quat under = glm::normalize(Ap * glm::inverse(Gp) * globalRotation(sk, pose, r.bone) * glm::inverse(r.A));
        it->second = w >= 1.0f ? it->second : glm::normalize(glm::slerp(under, it->second, w));
        on[r.name] = 1.0f;
      }
      applyClipSample(sk, L.binding, t, pose, [&](const std::string& role) { return on.count(role) ? 1.0f : 0.0f; });
      continue;
    }
    applyClipSample(sk, L.binding, s, pose, weightOf);
    if (L.clip->hasRoot() || L.clip->hasHeading()) {
      const float wr = float(env * (1 - walk));
      pose.rootOffset = glm::mix(pose.rootOffset, s.root * L.binding.legLength, wr);
      yawOffset = glm::mix(yawOffset, s.heading, wr);
    }
  }
}

void SceneEvaluator::applyClipFingers(size_t c, double frame, Pose& pose) const {
  const Skeleton& sk = characters_[c].asset.skeleton;
  const std::string prefix = scene_.characters[c].name + "/";
  const Clip& anim = scene_.animation;
  // A hand track (reach, touch or hand keys) gives that hand to the hand-pose system.
  auto handOwned = [&](const std::string& role) {
    const char side = role.empty() ? 'L' : role.back();
    const Track* t = anim.find(prefix + "hand." + side);
    return t && !t->keys.empty();
  };
  for (const ClipLayer& L : clipLayers_[c]) {
    const double env = L.envelope(frame);
    if (env <= 0) continue;
    bool any = false;
    for (const auto& r : L.binding.roles) any |= r.bone >= 0 && isFingerRole(r.name) && inMask(*L.clip, r.name, L.mirror);
    if (!any) continue;
    const ClipSample s = sampleClip(*L.clip, L.clipFrame(frame, scene_.rate.fps()), L.mirror);
    applyClipSample(sk, L.binding, s, pose, [&](const std::string& role) {
      return (isFingerRole(role) && inMask(*L.clip, role, L.mirror) && !handOwned(role)) ? float(env) : 0.0f;
    });
  }
}

}  // namespace plush
