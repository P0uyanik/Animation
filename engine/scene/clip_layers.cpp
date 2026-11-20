// Clip layers of the scene evaluator (actions of type "clip", see actions.cpp and model/clip.h).
// Order of a character's pose: keyed / generated tracks -> base clip (generated action motion added on top as a
// delta; the legs follow a walk while it owns them) -> emotion postures and gestures (action "emotion", tier 1) -> clip actions on their masks (walk keeps legs, hips and root while it walks; hand keys always win) ->
// life layer -> constraints (IK, hand pose, look) -> clip finger tracks (unless a hand track owns that hand).
// Automatic base idle (T-027): a humanoid character with no base clip action plays the shared "idle_relaxed" clip as
// its base layer (scene character "autoIdle": false opts out), so no character stands frozen in its default pose.
// Locomotion style (T-175, anim/foot_lock.h): a clip action (tier 2) whose clip carries a "style" block (the mocap
// clips in content/clips/mocap) gets the chibi filter (lean, arm swing, stride, tempo) on its samples and, with
// "foot_lock", a two-bone leg IK pin on its foot_plant contacts. Clips without the block are untouched.
#include <algorithm>
#include <filesystem>
#include <format>
#include <functional>
#include <map>

#include "anim/foot_lock.h"
#include "scene/emotion.h"
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

double SceneEvaluator::ClipLayer::envelopeRank(double f, int rank) const {
  if (base) return weight;
  // Successive breaking: each rank blends in `succession` frames after the previous one, and blends out the same
  // amount later (the trunk leads, the extremities trail past `end` by at most 4 x succession). A cut (ramp 0) has
  // no offset at that end.
  const double din = principles && blendIn > 0 ? rank * succession : 0.0;
  const double dout = principles && blendOut > 0 ? std::clamp(rank, 0, 4) * succession : 0.0;
  if (f < start + din || f > end + dout) return 0;
  auto ramp = [this](double x) { return principles ? easeInOut(x) : linear ? std::clamp(x, 0.0, 1.0) : smooth01(x); };
  double in = blendIn > 0 ? ramp((f - start - din) / blendIn) : 1.0;
  double out = blendOut > 0 && end < 1e29 ? ramp((end + dout - f) / blendOut) : 1.0;
  return weight * in * out;
}

double SceneEvaluator::ClipLayer::envelope(double f) const {
  if (sampled) return envelopeRank(f, 0) * sampled->weightAt(f);
  if (!principles) return envelopeRank(f, 0);
  return std::max(envelopeRank(f, 0), envelopeRank(f, 4));  // rank 0 leads the blend in, rank 4 trails the blend out
}

double SceneEvaluator::ClipLayer::clipFrame(double f, double sceneFps) const {
  if (sampled && !sampled->clock.empty()) return sampled->clockAt(f);
  if (clockIn > 0 || clockOut > 0) {
    // Slow-in / slow-out that survives blending: the clip's clock accelerates with the blend in and decelerates with
    // the blend out, so a clip that starts or ends in motion still leaves and arrives with zero velocity.
    const double length = end < 1e29 ? end - start : 1e30;
    const double t = plush::easedClock(f - start, length, clockIn, end < 1e29 ? clockOut : 0.0);
    if (warp) return warp->clipFrame(t, clip->loop);
    return std::max(0.0, t) * speed * clip->fps / std::max(1e-9, sceneFps);
  }
  if (warp) return warp->clipFrame(f - start, clip->loop);
  return std::max(0.0, f - start) * speed * clip->fps / std::max(1e-9, sceneFps);
}

// Personality tempo (T-053): gestures and clip actions (not base clips or the automatic idle) play their clock
// `tempo` x faster, the effective speed (scene speed x tempo) kept inside the profile's limits.action_speed. A
// one-shot clip that finishes early holds its last frame until the layer blends out. Tempo 1 = the plain clock.
double SceneEvaluator::layerClipFrame(size_t c, const ClipLayer& L, double frame) const {
  const double f = L.clipFrame(frame, scene_.rate.fps());
  // Locomotion style tempo (T-175): clip actions only; 1 for every clip without a "style" block.
  const double styleTempo = !L.base && L.tier == 2 && L.clip ? locomotionTempo(L.clip->raw) : 1.0;
  double tempo = 1.0;
  if (!(L.base || L.tier == 0 || c >= persona_.size() || !persona_[c].profile)) {
    const PersonaSetup& ps = persona_[c];
    tempo = ps.tempo;
    if (ps.speedLimit && L.speed > 0) tempo = double(ps.speedLimit->clamp(float(L.speed * tempo))) / L.speed;
  }
  if (styleTempo != 1.0) tempo *= styleTempo;
  if (tempo == 1.0) return f;
  const double t = f * tempo;
  if (L.clip->loop) return t;
  return std::min(t, L.clip->duration() * L.clip->fps);
}

void SceneEvaluator::applyBreakdowns(size_t c, const ClipLayer& L, double f, Pose& pose) const {
  const Skeleton& sk = characters_[c].asset.skeleton;
  auto bone = [&](const std::string& role) {
    auto it = L.binding.roleIndex.find(role);
    return it == L.binding.roleIndex.end() ? -1 : L.binding.roles[size_t(it->second)].bone;
  };
  for (int s = 0; s < 2; ++s) {
    if (L.breakIn[s] == 0 && L.breakOut[s] == 0) continue;
    const std::string side = s == 0 ? ".L" : ".R";
    if (!inMask(*L.clip, "forearm" + side, L.mirror)) continue;
    // The elbow's own blend progress (rank 2): the breakdown peaks halfway through it.
    const double d = 2 * L.succession;
    double deg = 0;
    if (L.blendIn > 0) {
      const double x = (f - L.start - d) / L.blendIn;
      if (x > 0 && x < 1) deg += L.breakIn[s] * 4 * x * (1 - x);
    }
    if (L.blendOut > 0 && L.end < 1e29) {
      const double x = (L.end + d - f) / L.blendOut;
      if (x > 0 && x < 1) deg += L.breakOut[s] * 4 * x * (1 - x);
    }
    if (deg == 0) continue;
    const int fore = bone("forearm" + side);
    if (fore < 0) continue;
    const quat q = elbowOpening(sk, pose, bone("upperArm" + side), fore, bone("hand" + side), float(deg * L.weight));
    pose.local[size_t(fore)] = glm::normalize(q * pose.local[size_t(fore)]);
  }
}

std::vector<SceneEvaluator::ClipLayerPlan> SceneEvaluator::clipLayerPlans(size_t c) const {
  std::vector<ClipLayerPlan> out;
  if (c >= clipLayers_.size()) return out;
  for (const ClipLayer& L : clipLayers_[c]) {
    if (L.base || L.tier != 2) continue;
    ClipLayerPlan p;
    p.clip = L.clip ? L.clip->name : "";
    p.start = L.start;
    p.end = L.end;
    p.blendIn = L.blendIn;
    p.blendOut = L.blendOut;
    p.succession = L.succession;
    p.clockIn = L.clockIn;
    p.clockOut = L.clockOut;
    p.principles = L.principles;
    p.warped = L.warp && !L.warp->isLinear();
    for (int s = 0; s < 2; ++s) {
      p.breakIn[s] = L.breakIn[s];
      p.breakOut[s] = L.breakOut[s];
    }
    out.push_back(p);
  }
  return out;
}

RetargetData SceneEvaluator::retargetData(size_t c, const ReferencePose& ref) const {
  const CharacterAsset& asset = characters_[c].asset;
  if (asset.retargetBlock.is_object()) {
    auto r = retargetFromJson(asset.retargetBlock);
    if (r && r->referenceVersion == ref.version) return *r;
  }
  return deriveRetarget(asset.skeleton, ref);
}

void SceneEvaluator::prepareAutoIdle() {
  autoIdle_.assign(characters_.size(), std::nullopt);
  std::filesystem::path file;  // the shared library clip, found by walking up from the scene file like clip actions
  for (auto d = std::filesystem::absolute(scene_.path).parent_path();; d = d.parent_path()) {
    auto cand = d / "content" / "clips" / "idle_relaxed.clip.json";
    if (std::filesystem::exists(cand)) {
      file = cand;
      break;
    }
    if (d == d.parent_path()) break;
  }
  if (file.empty()) return;
  std::shared_ptr<const ClipData> clip;
  for (size_t c = 0; c < characters_.size() && c < scene_.characters.size(); ++c) {
    const CharacterInstance& ci = characters_[c];
    // Humanoid engine packages with generated retarget data only (the production path, exporter version >= 2);
    // procedural characters and legacy packages without the block keep their default pose.
    if (!scene_.characters[c].autoIdle || !ci.imported || !ci.asset.retargetBlock.is_object()) continue;
    if (!clip) {
      auto cl = loadClip(file);
      if (!cl) {
        warnings_.push_back(std::format("auto idle: {}", cl.error().message));
        return;
      }
      clip = std::make_shared<const ClipData>(std::move(*cl));
    }
    ClipLayer L;
    L.clip = clip;
    L.base = true;
    L.tier = 0;
    L.binding = bindClip(ci.asset.skeleton, clip->reference, retargetData(c, clip->reference));
    bool humanoid = true;
    for (const char* role : {"hips", "spine", "chest", "head", "upperArm.L", "upperArm.R", "thigh.L", "thigh.R"}) {
      auto it = L.binding.roleIndex.find(role);
      humanoid = humanoid && it != L.binding.roleIndex.end() && L.binding.roles[size_t(it->second)].bone >= 0;
    }
    if (!humanoid) continue;
    // A per-character phase (from the name, deterministic) so characters sharing the idle do not breathe in sync.
    const double period = clip->duration() * scene_.rate.fps();
    const double phase = period > 0 ? double(std::hash<std::string>{}(scene_.characters[c].name) % 997) / 997.0 * period : 0.0;
    L.start = double(scene_.frameStart) - phase;
    L.blendIn = L.blendOut = 0;
    autoIdle_[c] = std::move(L);
  }
}

const SceneEvaluator::ClipLayer* SceneEvaluator::autoIdleLayer(size_t c) const {
  if (c >= autoIdle_.size() || !autoIdle_[c]) return nullptr;
  if (c < clipLayers_.size())
    for (const ClipLayer& L : clipLayers_[c])
      if (L.base) return nullptr;  // a base clip action replaces the automatic idle
  return &*autoIdle_[c];
}

std::vector<const SceneEvaluator::ClipLayer*> SceneEvaluator::activeClipLayers(size_t c) const {
  std::vector<const ClipLayer*> out;
  if (const ClipLayer* a = autoIdleLayer(c)) out.push_back(a);  // tier 0: under every other layer
  if (c < clipLayers_.size())
    for (const ClipLayer& L : clipLayers_[c]) out.push_back(&L);
  return out;
}

void SceneEvaluator::applyClips(size_t c, double frame, Pose& pose, float& yawOffset) const {
  const auto layers = activeClipLayers(c);
  const Skeleton& sk = characters_[c].asset.skeleton;
  const CharacterAsset& asset = characters_[c].asset;
  const std::string prefix = scene_.characters[c].name + "/";
  const Clip& anim = scene_.animation;
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
  for (const ClipLayer* layer : layers) {
    const ClipLayer& L = *layer;
    const double env = L.envelope(frame);
    if (env <= 0) continue;
    const double clipFrame = layerClipFrame(c, L, frame);
    ClipSample s = sampleClip(*L.clip, clipFrame, L.mirror);
    const LocomotionStyle style = !L.base && L.tier == 2 ? locomotionStyle(L.clip->raw) : LocomotionStyle{};
    if (style.enabled) applyLocomotionStyle(style, s.local, s.root, L.mirror);
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
      // While a walk owns the legs they follow the walk itself, as under every other clip layer (T-027: a base idle
      // with a real weight shift, e.g. a bent free knee, must not leak into the walk's legs). The hips keep the base
      // pose plus the walk's change, as before.
      std::vector<std::pair<int, quat>> walkOwned;
      if (walk > 0)
        for (const auto& r : L.binding.roles)
          if (r.bone >= 0 && isWalkRole(r.name) && r.name != "hips" && !handKeyed(r.name) && inMask(*L.clip, r.name, L.mirror))
            walkOwned.push_back({r.bone, pose.local[size_t(r.bone)]});
      applyClipSample(sk, L.binding, s, pose, [&](const std::string& role) {
        return (isFingerRole(role) || handKeyed(role) || !inMask(*L.clip, role, L.mirror)) ? 0.0f : float(env);
      });
      for (auto& [b, d] : deltas) pose.local[size_t(b)] = glm::normalize(pose.local[size_t(b)] * d);
      for (auto& [b, q] : walkOwned) pose.local[size_t(b)] = glm::normalize(glm::slerp(pose.local[size_t(b)], q, float(walk)));
      const float wr = float(env * (1 - walk));
      pose.rootOffset += s.root * L.binding.legLength * wr;
      yawOffset += s.heading * wr;
      continue;
    }
    auto weightOf = [&](const std::string& role) {
      if (isFingerRole(role) || handKeyed(role) || !inMask(*L.clip, role, L.mirror)) return 0.0f;
      const double e = L.principles ? L.envelopeRank(frame, successionRank(role)) : env;
      return float(isWalkRole(role) ? e * (1 - walk) : e);
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
    if (L.principles) applyBreakdowns(c, L, frame, pose);
    const vec3 rootUnder = pose.rootOffset;
    const float wr = float((L.principles ? L.envelopeRank(frame, 0) : env) * (1 - walk));
    // Foot-lock (T-175), part 1: the ground offset. Root motion is in leg lengths, so on a character whose leg and
    // hip proportions differ from the source the planted ankles end a little above or below their rest height. The
    // clip's root is shifted vertically so that every plant begins with its ankle at the rest height: the offset a
    // plant needs (rest ankle height - ankle height where its pin is taken) is keyed at that clip frame and
    // interpolated linearly between plants (periodic for a loop, held before the first and after the last).
    std::vector<FootPlant> plants;
    auto footBone = [&](const std::string& role) {
      auto ri = L.binding.roleIndex.find(role);
      return ri == L.binding.roleIndex.end() ? -1 : L.binding.roles[size_t(ri->second)].bone;
    };
    std::vector<std::pair<double, float>> groundKeys;  // (clip frame, vertical offset in metres)
    if (style.footLock && L.clip->hasRoot()) {
      plants = footPlants(L.clip->raw);
      auto full = [&](const std::string& role) { return (isFingerRole(role) || !inMask(*L.clip, role, L.mirror)) ? 0.0f : 1.0f; };
      for (const FootPlant& p : plants) {
        const int foot = footBone(L.mirror ? mirrorRole(*L.clip, p.role) : p.role);
        if (foot < 0) continue;
        const double at0 = p.a <= 0 ? 0.0 : p.a + std::min(style.footEaseIn, p.b - p.a);
        ClipSample s0 = sampleClip(*L.clip, at0, L.mirror);
        applyLocomotionStyle(style, s0.local, s0.root, L.mirror);
        Pose at = pose;
        applyClipSample(sk, L.binding, s0, at, full);
        at.rootOffset = s0.root * L.binding.legLength;
        groundKeys.push_back({at0, sk.bones[size_t(foot)].head.y - boneGlobals(sk, at, mat4(1))[size_t(foot)][3].y});
      }
      std::sort(groundKeys.begin(), groundKeys.end());
      std::vector<std::pair<double, float>> merged;  // plants that begin together share one key (their mean)
      for (size_t i = 0; i < groundKeys.size();) {
        size_t j = i;
        float sum = 0;
        for (; j < groundKeys.size() && groundKeys[j].first - groundKeys[i].first < 1e-6; ++j) sum += groundKeys[j].second;
        merged.push_back({groundKeys[i].first, sum / float(j - i)});
        i = j;
      }
      groundKeys = std::move(merged);
    }
    auto groundAt = [&](double cf) {
      if (groundKeys.empty()) return vec3(0);
      const double N = std::max(1, L.clip->frameCount);
      const size_t n = groundKeys.size();
      if (L.clip->loop) {
        cf -= std::floor(cf / N) * N;
        for (size_t i = 0; i < n; ++i) {  // segment from key i to the next one (the last wraps to the first + N)
          const double t0 = groundKeys[i].first, t1 = i + 1 < n ? groundKeys[i + 1].first : groundKeys[0].first + N;
          const float v1 = groundKeys[(i + 1) % n].second;
          const double x = cf >= t0 ? cf : cf + N;
          if (x >= t0 && x <= t1) return vec3(0, glm::mix(groundKeys[i].second, v1, float(t1 > t0 ? (x - t0) / (t1 - t0) : 0.0)), 0);
        }
        return vec3(0, groundKeys[0].second, 0);
      }
      if (cf <= groundKeys.front().first) return vec3(0, groundKeys.front().second, 0);
      for (size_t i = 0; i + 1 < n; ++i)
        if (cf <= groundKeys[i + 1].first) {
          const double t0 = groundKeys[i].first, t1 = groundKeys[i + 1].first;
          return vec3(0, glm::mix(groundKeys[i].second, groundKeys[i + 1].second, float(t1 > t0 ? (cf - t0) / (t1 - t0) : 1.0)), 0);
        }
      return vec3(0, groundKeys.back().second, 0);
    };
    const vec3 ground = groundAt(clipFrame);
    if (L.clip->hasRoot() || L.clip->hasHeading()) {
      pose.rootOffset = glm::mix(pose.rootOffset, s.root * L.binding.legLength + ground, wr);
      yawOffset = glm::mix(yawOffset, s.heading, wr);
    }
    if (style.footLock) {
      // Part 2: while a foot_plant contact holds a foot, its ankle stays where it was when the plant began (this
      // layer's pose at that clip frame, root motion included; character space, so the character's own scene
      // placement is assumed to rest during a plant). Two-bone leg IK; the foot keeps its orientation.
      if (plants.empty()) plants = footPlants(L.clip->raw);
      struct Pin {
        int foot;
        vec3 target;
        float weight;
      };
      std::vector<Pin> pins;
      for (const char* side : {".L", ".R"}) {
        const std::string role = std::string("foot") + side;
        const int foot = footBone(role);
        if (foot < 0) continue;
        const PlantState ps = plantAt(plants, L.mirror ? mirrorRole(*L.clip, role) : role, clipFrame, L.clip->frameCount,
                                      L.clip->loop, style.footRelease, style.footEaseIn, style.footLead);
        const float w = ps.weight * weightOf(std::string("shin") + side);
        if (!ps.active || w <= 0) continue;
        ClipSample s0 = sampleClip(*L.clip, ps.start, L.mirror);
        applyLocomotionStyle(style, s0.local, s0.root, L.mirror);
        Pose at = pose;
        applyClipSample(sk, L.binding, s0, at, weightOf);
        at.rootOffset = L.clip->hasRoot() ? glm::mix(rootUnder, s0.root * L.binding.legLength + groundAt(ps.start), wr) : pose.rootOffset;
        pins.push_back({foot, vec3(boneGlobals(sk, at, mat4(1))[size_t(foot)][3]), w});
      }
      // While a pin lets go (or eases in) its target moves between the pinned point and the clip's own ankle. A pinned
      // ankle must also stay within the leg's reach: late in a stance the short leg of a chibi runs out before the
      // source's does, so the pelvis drops by what the furthest foot needs.
      if (!pins.empty()) {
        const auto G = boneGlobals(sk, pose, mat4(1));
        float drop = 0;
        for (Pin& p : pins) {
          p.target = glm::mix(vec3(G[size_t(p.foot)][3]), p.target, p.weight);
          drop = std::max(drop, footReachDrop(sk, G, p.foot, p.target));
        }
        pose.rootOffset.y -= drop;
        for (const Pin& p : pins) pinFoot(sk, pose, p.foot, p.target, 1.0f);
      }
      // The floor: no ankle goes under its rest height (a swinging foot while the pelvis is lowered for the other).
      if (L.clip->hasRoot()) {
        const auto G = boneGlobals(sk, pose, mat4(1));
        for (const char* side : {".L", ".R"}) {
          const int foot = footBone(std::string("foot") + side);
          if (foot < 0) continue;
          const vec3 p(G[size_t(foot)][3]);
          const float floorY = sk.bones[size_t(foot)].head.y;
          const float w = weightOf(std::string("shin") + side);
          if (p.y < floorY - 1e-5f && w > 0) pinFoot(sk, pose, foot, vec3(p.x, glm::mix(p.y, floorY, w), p.z), 1.0f);
        }
      }
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
  for (const ClipLayer* layer : activeClipLayers(c)) {
    const ClipLayer& L = *layer;
    const double env = L.envelope(frame);
    if (env <= 0) continue;
    bool any = false;
    for (const auto& r : L.binding.roles) any |= r.bone >= 0 && isFingerRole(r.name) && inMask(*L.clip, r.name, L.mirror);
    if (!any) continue;
    const ClipSample s = sampleClip(*L.clip, layerClipFrame(c, L, frame), L.mirror);
    const float fe = float(L.principles ? L.envelopeRank(frame, successionRank("f0a")) : env);
    applyClipSample(sk, L.binding, s, pose, [&](const std::string& role) {
      return (isFingerRole(role) && inMask(*L.clip, role, L.mirror) && !handOwned(role)) ? fe : 0.0f;
    });
  }
}

}  // namespace plush
