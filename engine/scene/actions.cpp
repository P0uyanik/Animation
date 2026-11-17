// Action compiler: turns a scene's high-level actions into generated animation tracks, so a shot is described as
// "B walks to the table, A picks up the boat, looks at it and puts it back" instead of keys on every bone.
// Actions adapt to the scene: reach targets, gaze and hand grip come from where the objects actually are
// (and how big they are) at the frames involved; footsteps come from the walk path. Keys an animator sets by hand
// always win over generated ones (Clip::generated is only a fallback).
//
// Action types (all frames are scene frames):
//   look       {character, start, object | target:[x,y,z] | camera:true, end?}  gaze (eyes; the head follows
//              through the life layer), following a moving object until `end`
//   expression {character, name, start, end?, weight=1, ramp=6}
//   reach      {character, hand:"L"|"R", object, start, contact?, lift=0.05, liftEnd?, place?, placeAt?, release?,
//               end?, graspRadius=0.012, graspAxis?, look=true}
//              hand opens on the way, fingers close on contact (contact search), object attached to the hand,
//              lifted towards the body, put down at `placeAt` (default: where it was), released, hand returns;
//              ripples where a floating object leaves and re-enters its water
//   walk       {character, start, end, to:[x,z], face?}  root path with ease in/out, turn to the path, planted
//              footsteps (foot IK), pelvis bob and sway, counter-swinging arms
//   touch      {character, hand, start, contact?, end?, target:[x,y,z]}  points and touches a spot with the index
//              fingertip (ripple when the spot is a water surface)
//   clip       {character, clip:<library name> | file:<path>, start?, end?, speed=1, weight=1, blendIn=6,
//               blendOut=6, loop?, mirror=false, base=false}  a body animation clip (plush.clip/1, model/clip.h)
//              retargeted to the character. base:true = the character's base layer for the whole shot (replaces
//              the default pose; generated action motion such as walk arm swing is added on top). Other clips
//              override their body-part mask with blending; walk keeps the legs, hips and root while walking;
//              IK (reach, touch, foot plants) and look are applied afterwards and keep priority. Library clips are
//              found in content/clips/<name>.clip.json above the scene file.
//   reach/grasp {.., prop, ..}, hold, place, handover  prop interactions at asset sockets (scene/interaction.h)
//   emotion    {character, name:<library name>[/<variant>], start, end?, intensity=1}  a shared emotion
//              (plush.emotion/1, scene/emotion.h, docs/EMOTIONS.md) found in content/emotions/<name>.emotion.json above
//              the scene file: its face mix becomes expression weights (generated per-frame keys added to the
//              morph's track; names the character lacks are skipped with one warning each), its posture and gesture
//              clips become clip layers above the base clip and below clip actions. `intensity` scales the face
//              weights and the layers' weights. Without `end` it lasts onset + hold + release.
//
// Director (scene "director": {minShot?, closeFocal?, closeFStop?, mediumFocal?, mediumFStop?}): plans camera shots
// from the action beats — establishing wide (the scene camera), medium on a character starting an action, insert
// close-ups on the hands/object at contact and at placement, reaction close-ups on faces, back to wide — places
// each camera on the master camera's side of the action (180-degree rule), turns it away from characters standing
// in the way, focuses on the subject with a shallow aperture for close-ups and pushes in gently during each shot.
// Any hand-keyed camera track overrides the director.
#include <algorithm>
#include <format>
#include <set>

#include "scene/emotion.h"
#include "scene/scene.h"

namespace plush {
namespace {

double num(const Json& j, const char* k, double fallback) {
  auto it = j.find(k);
  return (it != j.end() && it->is_number()) ? it->get<double>() : fallback;
}
std::string str(const Json& j, const char* k, const std::string& fallback = {}) {
  auto it = j.find(k);
  return (it != j.end() && it->is_string()) ? it->get<std::string>() : fallback;
}
bool has(const Json& j, const char* k) { return j.contains(k); }
vec3 vec(const Json& j, const char* k, vec3 fallback) {
  auto it = j.find(k);
  if (it == j.end() || !it->is_array() || it->size() < 2) return fallback;
  if (it->size() == 2) return vec3((*it)[0].get<float>(), 0, (*it)[1].get<float>());
  return vec3((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
}
void key(Clip& c, const std::string& track, double f, vec3 v, Interp in = Interp::Smooth) {
  c.tracks[track].setKey({f, v, in});
}
struct Beat {
  enum class Kind { Reach, Touch, Expression, Walk } kind;
  int character = -1, object = -1;
  double start = 0, contact = 0, liftEnd = 0, place = 0, release = 0, end = 0;
  vec3 point{0}, placePoint{0};
};

void dropKeysAfter(Clip& c, const std::string& track, double f) {
  auto it = c.tracks.find(track);
  if (it == c.tracks.end()) return;
  auto& k = it->second.keys;
  k.erase(std::remove_if(k.begin(), k.end(), [&](const Key& x) { return x.frame > f; }), k.end());
}

struct Shot {
  const char* name = "wide";
  double start = 0, end = 0;
  int kind = 0;         // 0 wide, 1 object, 2 face, 3 point, 4 between face and object
  int character = -1, object = -1;
  vec3 point{0};
  float size = 0.3f, focal = 50, fStop = 4, elevDeg = 15;
};

// Plans camera shots from the beats and writes camera.position / camera.target / camera.lens into `gen`.
void planShots(const SceneEvaluator& ev, Clip& gen, const std::vector<Beat>& beats) {
  const Scene& sc = ev.scene();
  const Json& d = sc.director;
  const double fps = sc.rate.fps();
  const double minShot = num(d, "minShot", 1.2 * fps);
  const float closeF = float(num(d, "closeFocal", 70)), closeS = float(num(d, "closeFStop", 2.8));
  const float medF = float(num(d, "mediumFocal", 50)), medS = float(num(d, "mediumFStop", 4.0));
  auto face = [&](int c, double f) {
    const auto& sk = ev.characters()[size_t(c)].asset.skeleton;
    int head = sk.find("head");
    return vec3(ev.characterGlobals(size_t(c), f)[size_t(head)] * vec4(0, 0.11f, 0.09f, 1));
  };
  auto subject = [&](const Shot& s, double f) -> vec3 {
    switch (s.kind) {
      case 1: return vec3(ev.objectWorld(size_t(s.object), f)[3]);
      case 2: return face(s.character, f);
      case 4: return glm::mix(face(s.character, f), s.point, 0.5f);
      case 5: return glm::mix(face(s.character, f), vec3(ev.objectWorld(size_t(s.object), f)[3]), 0.5f);
      default: return s.point;
    }
  };
  std::vector<Shot> shots;
  for (const Beat& b : beats) {
    if (b.kind == Beat::Kind::Reach) {
      Shot m{"medium: reach", b.start - 14, b.contact - 8, 4, b.character, -1, b.point, 0.0f, medF, medS, 12};
      m.size = std::max(0.42f, 1.6f * glm::distance(face(b.character, b.start), b.point));
      shots.push_back(m);
      shots.push_back({"insert: grip", b.contact - 8, b.liftEnd + 2, 1, b.character, b.object, b.point, 0.2f, closeF, closeS, 28});
      // Reaction: the face together with the object being looked at.
      Shot r{"close-up: reaction with object", b.liftEnd + 2, b.place - 12, 5, b.character, b.object, b.point, 0.0f, closeF, closeS, 8};
      r.size = std::max(0.36f, 1.5f * glm::distance(face(b.character, b.liftEnd), vec3(ev.objectWorld(size_t(b.object), b.liftEnd)[3])));
      shots.push_back(r);
      shots.push_back({"insert: place", b.place - 12, b.release + 14, 3, b.character, -1, b.placePoint, 0.22f, closeF, closeS, 30});
    } else if (b.kind == Beat::Kind::Touch) {
      shots.push_back({"insert: touch", b.contact - 10, b.contact + 16, 3, b.character, -1, b.point, 0.2f, closeF, closeS, 30});
    } else if (b.kind == Beat::Kind::Expression) {
      shots.push_back({"close-up: expression", b.start - 2, b.start + std::max(minShot, 40.0), 2, b.character, -1, vec3(0), 0.3f, closeF, closeS, 6});
    }
  }
  std::stable_sort(shots.begin(), shots.end(), [](const Shot& a, const Shot& b) { return a.start < b.start; });
  // Resolve: drop shots too short to read, cut overlaps (the later action wins), skip expression close-ups that
  // would interrupt another shot, and never leave a wide gap shorter than minShot (hold the previous shot).
  std::vector<Shot> plan;
  for (Shot s : shots) {
    s.start = std::max(s.start, double(sc.frameStart));
    if (!plan.empty() && s.start < plan.back().end) {
      if (std::string(s.name) == "close-up: expression") continue;
      plan.back().end = s.start;
      if (plan.back().end - plan.back().start < minShot * 0.6) plan.pop_back();
    }
    if (s.end - s.start < minShot * 0.6) continue;
    if (!plan.empty() && s.start - plan.back().end < minShot) plan.back().end = s.start;
    plan.push_back(s);
  }
  // Master (wide) camera fills the gaps.
  std::vector<Shot> all;
  double t = sc.frameStart;
  for (const Shot& s : plan) {
    if (s.start > t) all.push_back({"wide", t, s.start, 0});
    all.push_back(s);
    t = s.end;
  }
  if (t < sc.frameEnd + 1) all.push_back({"wide", t, double(sc.frameEnd + 1), 0});

  const vec3 master = sc.camera.position;
  const float sensorH = sc.camera.sensorWidthMm * 9.0f / 16.0f;
  auto blocked = [&](vec3 cam, vec3 subj, int subjectChar) {
    for (size_t c = 0; c < ev.characters().size(); ++c) {
      if (int(c) == subjectChar) continue;
      auto G = ev.characterGlobals(c, 1);
      const auto& sk = ev.characters()[c].asset.skeleton;
      for (const char* bn : {"chest", "head"}) {
        int bi = sk.find(bn);
        if (bi < 0) continue;
        vec3 centre = vec3(G[size_t(bi)][3]) + vec3(0, std::string(bn) == "head" ? 0.1f : 0.0f, 0);
        float r = std::string(bn) == "head" ? 0.17f : 0.14f;
        for (float u = 0.05f; u < 0.95f; u += 0.02f)
          if (glm::distance(glm::mix(cam, subj, u), centre) < r) return true;
      }
    }
    return false;
  };
  Track pos, tgt, lens;
  for (const Shot& s : all) {
    const double last = s.end - 1;
    if (s.kind == 0) {
      pos.setKey({s.start, master, Interp::Step});
      tgt.setKey({s.start, sc.camera.target, Interp::Step});
      lens.setKey({s.start, vec3(sc.camera.focalMm, sc.camera.fStop, sc.camera.focusDistance), Interp::Step});
      logInfo("director: {:>6.1f}-{:<6.1f} {}", s.start, last, s.name);
      continue;
    }
    vec3 s0 = subject(s, s.start);
    float dist = s.size / (2.0f * (sensorH * 0.5f / s.focal));
    vec2 h = glm::normalize(vec2(master.x - s0.x, master.z - s0.z) + vec2(1e-6f));
    float el = glm::radians(s.elevDeg);
    vec3 off;
    float turn = 0;
    for (float tryDeg : {0.f, 15.f, -15.f, 30.f, -30.f, 45.f, -45.f, 60.f, -60.f, 75.f, -75.f}) {
      float a = glm::radians(tryDeg);
      vec2 hr(h.x * std::cos(a) - h.y * std::sin(a), h.x * std::sin(a) + h.y * std::cos(a));
      off = vec3(hr.x * std::cos(el), std::sin(el), hr.y * std::cos(el)) * dist;
      turn = tryDeg;
      if (!blocked(s0 + off, s0, s.character)) break;
    }
    for (double f = s.start;; f = std::min(last, f + 3)) {
      double u = (f - s.start) / std::max(1.0, last - s.start);
      vec3 sf = subject(s, f);
      vec3 p = sf + off * float(1.04 - 0.08 * u);  // gentle push-in
      Interp in = f >= last ? Interp::Step : Interp::Linear;
      pos.setKey({f, p, in});
      tgt.setKey({f, sf, in});
      lens.setKey({f, vec3(s.focal, s.fStop, glm::distance(p, sf)), in});
      if (f >= last) break;
    }
    logInfo("director: {:>6.1f}-{:<6.1f} {} ({} mm f/{:.1f}, {:.2f} m{})", s.start, last, s.name, s.focal, s.fStop, dist,
            turn != 0 ? std::format(", turned {:.0f} deg to clear a character", turn) : std::string());
  }
  gen.tracks["camera.position"] = pos;
  gen.tracks["camera.target"] = tgt;
  gen.tracks["camera.lens"] = lens;
}

}  // namespace

Result<void> SceneEvaluator::compileActions() {
  // Facial layer events (T-046) are gathered while the actions compile; the layers are built from them afterwards.
  faces_.clear();  // actions query poses while compiling: no face motion from a previous compile meanwhile
  faceTimelines_.assign(characters_.size(), {});
  faceLibrary_ = defaultFaceLibrary();
  for (auto d = std::filesystem::absolute(scene_.path).parent_path();; d = d.parent_path()) {
    const auto f = d / "content" / "emotions" / "face_motion.json";
    if (std::filesystem::exists(f)) {
      auto j = parseJsonFile(f);
      auto lib = j ? faceLibraryFromJson(*j) : Result<FaceLibrary>(std::unexpected(j.error()));
      if (lib) faceLibrary_ = std::move(*lib);
      else warnings_.push_back(std::format("{}: {} (built-in face defaults used)", f.string(), lib.error().message));
      break;
    }
    if (d == d.parent_path()) break;
  }
  buildBodyMechanics();  // T-045: actions see the body mechanics while they plan (reach poses, contacts)
  const std::vector<std::string> libraryWarnings = warnings_;
  bodyCacheOn_ = false;  // generated tracks change while compiling: no cached drivers meanwhile
  auto r = compileActionsBody();
  bodyCacheOn_ = true;
  {
    std::lock_guard<std::mutex> lock(*bodyMutex_);
    for (auto& m : bodyCache_) m.clear();
  }
  warnings_.insert(warnings_.begin(), libraryWarnings.begin(), libraryWarnings.end());
  buildFaceLayers();
  return r;
}

void SceneEvaluator::buildFaceLayers() {
  faces_.assign(characters_.size(), FaceLayer{});
  if (faceTimelines_.size() != characters_.size()) faceTimelines_.assign(characters_.size(), {});
  const double fps = scene_.rate.fps();
  std::map<const ClipData*, std::shared_ptr<const FaceCurves>> curveCache;
  for (size_t c = 0; c < characters_.size(); ++c) {
    FaceTimeline tl = faceTimelines_[c];
    if (const Json& fm = scene_.characters[c].faceMotion; !fm.is_null()) {  // the character's own face: a constant layer
      auto m = faceMotionFromJson(fm);
      if (m) tl.emotions.insert(tl.emotions.begin(), {FaceEnvelope{-1e30, 1e30, 0, 0, 1, false}, *m});
      else warnings_.push_back(std::format("character '{}': {} (its faceMotion is ignored)", scene_.characters[c].name, m.error().message));
    }
    // Clip face curves: every clip layer (base, emotion posture and gesture, clip actions) whose clip has a "face" block.
    for (const ClipLayer* L : activeClipLayers(c)) {
      if (!L->clip) continue;
      auto it = curveCache.find(L->clip.get());
      if (it == curveCache.end()) {
        auto cv = faceCurvesFromClipJson(L->clip->raw);
        if (!cv) warnings_.push_back(std::format("clip '{}': {} (face curves skipped)", L->clip->name, cv.error().message));
        it = curveCache.emplace(L->clip.get(), cv ? *cv : nullptr).first;
      }
      if (!it->second) continue;
      FaceTimeline::Curves fc;
      fc.env = L->base ? FaceEnvelope{-1e30, 1e30, 0, 0, L->weight, false}
                       : FaceEnvelope{L->start, L->end, L->blendIn, L->blendOut, L->weight, L->linear};
      fc.curves = it->second;
      fc.start = L->start;
      fc.speed = L->speed;
      fc.clipFps = L->clip->fps;
      tl.curves.push_back(std::move(fc));
    }
    std::vector<std::string> morphNames;
    for (auto& mt : characters_[c].rig.morphs) morphNames.push_back(mt.name);
    const CharacterAsset& asset = characters_[c].asset;
    auto resolve = [&](const std::string& name) { return resolveExpression(asset, name, morphNames); };
    faces_[c].build(faceLibrary_, resolve, std::move(tl), lifeParams(c), fps, scene_.frameStart, scene_.frameEnd);
  }
}

Result<void> SceneEvaluator::compileActionsBody() {
  auto gen = std::make_shared<Clip>();
  warnings_.clear();
  clipLayers_.assign(characters_.size(), {});
  walkSpans_.assign(characters_.size(), {});
  buildClearanceModels();  // arm-body clearance models (interaction.cpp, T-030)
  scene_.animation.generated = gen;  // later actions already see earlier ones (a reach after a walk)
  // Object fields that actions write are reset to what the scene author wrote, so compiling twice is harmless.
  if (authoredObjects_.size() == scene_.objects.size())
    for (size_t i = 0; i < scene_.objects.size(); ++i) {
      scene_.objects[i].attachTo = authoredObjects_[i].attachTo;
      scene_.objects[i].attachFrame = authoredObjects_[i].attachFrame;
      scene_.objects[i].releaseFrame = authoredObjects_[i].releaseFrame;
      scene_.objects[i].ripples = authoredObjects_[i].ripples;
    }
  else
    authoredObjects_ = scene_.objects;
  // Props likewise: interaction actions add parent switches, which are reset to the authored ones first.
  if (authoredProps_.size() == scene_.props.size())
    for (size_t i = 0; i < scene_.props.size(); ++i) {
      scene_.props[i].parent = authoredProps_[i].parent;
      scene_.props[i].parentSwitch = authoredProps_[i].parentSwitch;
    }
  else
    authoredProps_ = scene_.props;
  if (!scene_.actions.is_array() || scene_.actions.empty()) return {};
  InteractionContext interactions;

  std::vector<const Json*> actions;
  for (const Json& a : scene_.actions) actions.push_back(&a);
  auto startOf = [](const Json* a) { return num(*a, "start", num(*a, "frame", 0)); };
  std::stable_sort(actions.begin(), actions.end(), [&](const Json* a, const Json* b) { return startOf(a) < startOf(b); });

  auto charIndex = [&](const std::string& n) -> int {
    for (size_t c = 0; c < scene_.characters.size(); ++c)
      if (scene_.characters[c].name == n) return int(c);
    return -1;
  };
  auto objIndex = [&](const std::string& n) -> int {
    for (size_t o = 0; o < scene_.objects.size(); ++o)
      if (scene_.objects[o].name == n) return int(o);
    return -1;
  };
  auto objPos = [&](int o, double f) { return vec3(objectWorld(size_t(o), f)[3]); };
  const Clip& clip = scene_.animation;
  std::vector<Beat> beats;
  // Leans the upper body towards a point beyond arm's length (forward and sideways, up to ~25 degrees).
  auto leanToward = [&](int c, char side, vec3 p, float clearance, double startF, double reachF, double holdF, double endF,
                        const std::string& what) {
    const CharacterDesc& cd = scene_.characters[size_t(c)];
    const CharacterAsset& asset = characters_[size_t(c)].asset;
    const auto& B = asset.skeleton.bones;
    const int upper = asset.skeleton.find(std::string("upperArm.") + side), forearm = asset.skeleton.find(std::string("forearm.") + side),
              hand = asset.skeleton.find(std::string("hand.") + side), spine = asset.skeleton.find("spine");
    if (upper < 0 || forearm < 0 || hand < 0 || spine < 0) return;
    const float armLen = glm::distance(B[size_t(upper)].head, B[size_t(forearm)].head) + glm::distance(B[size_t(forearm)].head, B[size_t(hand)].head);
    const float need = glm::distance(vec3(characterGlobals(size_t(c), reachF)[size_t(upper)][3]), p) - clearance - 0.95f * armLen;
    if (need <= 0) return;
    const std::string who = cd.name, prefix = who + "/";
    const mat4 body = objectMatrix(clip.evaluate(who + ".position", reachF, cd.position), clip.evaluate(who + ".yaw", reachF, vec3(cd.yawDeg)).x, 1.0f);
    vec3 local = vec3(glm::inverse(body) * vec4(p, 1)) - B[size_t(spine)].head;
    vec2 dirXZ = glm::normalize(vec2(local.x, local.z) + vec2(1e-6f));
    float lean = glm::degrees(std::min(0.45f, need / 0.22f));
    vec3 rot(lean * std::max(0.0f, dirXZ.y), 0, -lean * dirXZ.x);
    const std::string t = prefix + "spine.rot";
    key(*gen, t, startF, clip.evaluate(t, startF, vec3(0)));
    key(*gen, t, reachF - 3, rot);
    key(*gen, t, holdF, rot);
    key(*gen, t, endF, vec3(0));
    const float still = glm::distance(vec3(characterGlobals(size_t(c), reachF)[size_t(upper)][3]), p) - clearance - armLen;
    if (still > 0.01f)
      logWarn("{}: '{}' cannot reach {} at frame {} even leaning ({:.0f} mm short); move them closer", what, who, what, reachF, still * 1000);
  };

  // Library files (content/<kind>/<file>) are found by walking up from the scene file.
  auto findLibrary = [&](const char* kind, const std::string& file) -> std::filesystem::path {
    for (auto d = std::filesystem::absolute(scene_.path).parent_path();; d = d.parent_path()) {
      auto cand = d / "content" / kind / file;
      if (std::filesystem::exists(cand)) return cand;
      if (d == d.parent_path()) return {};
    }
  };
  auto cachedClip = [&](const std::filesystem::path& file) -> Result<std::shared_ptr<const ClipData>> {
    const std::string key = std::filesystem::weakly_canonical(file).string();
    if (!clipCache_.count(key)) {
      auto cl = loadClip(file);
      if (!cl) return std::unexpected(cl.error());
      clipCache_[key] = std::make_shared<const ClipData>(std::move(*cl));
    }
    return clipCache_[key];
  };
  auto sortLayers = [&](int c) {  // base clip, emotion layers (by start), clip actions (in action order)
    std::stable_sort(clipLayers_[size_t(c)].begin(), clipLayers_[size_t(c)].end(), [](const ClipLayer& x, const ClipLayer& y) {
      if (x.tier != y.tier) return x.tier < y.tier;
      return x.tier == 1 && x.start < y.start;
    });
  };
  struct FaceContribution {
    int character;
    std::string morph;
    ClipLayer envelope;  // timing only (start, end, ramps, weight = intensity, curve)
    float weight;
  };
  std::vector<FaceContribution> emotionFace;
  std::set<std::string> missingFace;
  struct PendingEmotion {  // posture and face timing are final only after all emotions are known (crossfades)
    int character;
    ClipLayer envelope, posture;
    bool hasPosture = false;
    std::vector<std::pair<std::string, float>> face;  // resolved morph -> weight
    bool explicitEnd = false;
    FaceMotion faceMotion;  // living-face tunables (facial layer, T-046)
    bool hasFaceMotion = false;
  };
  std::vector<PendingEmotion> pending;

  for (const Json* ap : actions) {
    const Json& a = *ap;
    const std::string type = str(a, "type"), who = str(a, "character");
    const int c = charIndex(who);
    if (c < 0) return fail(std::format("action '{}': unknown character '{}'", type, who));
    const CharacterDesc& cd = scene_.characters[size_t(c)];
    const CharacterAsset& asset = characters_[size_t(c)].asset;
    const std::string prefix = who + "/";
    const double start = startOf(&a);

    // Prop interactions (reach/grasp a prop, hold, place, handover): interaction.cpp.
    auto interaction = compileInteraction(a, *gen, interactions);
    if (!interaction) return fail(interaction.error().message);
    if (*interaction) continue;

    if (type == "look") {
      faceTimelines_[size_t(c)].lookStarts.push_back(start);  // a gaze shift: brows lift a little, maybe a blink
      if (start > scene_.frameStart + 2)  // the look a shot opens with is the starting state, not a new focus
        faceTimelines_[size_t(c)].attention.push_back({start, faceLibrary_.neutral.lookAttention});
      const std::string track = prefix + "lookAt";
      const int o = has(a, "object") ? objIndex(str(a, "object")) : -1;
      if (has(a, "object") && o < 0) return fail(std::format("look: unknown object '{}'", str(a, "object")));
      auto target = [&](double f) {
        if (o >= 0) return objPos(o, f);
        if (num(a, "camera", 0) != 0 || (a.contains("camera") && a["camera"].is_boolean() && a["camera"].get<bool>()))
          return clip.evaluate("camera.position", f, scene_.camera.position);
        return vec(a, "target", vec3(0, 0.6f, 3));
      };
      vec3 prev = clip.evaluate(track, start, target(start));
      dropKeysAfter(*gen, track, start);
      key(*gen, track, start, prev, Interp::Linear);
      const double end = num(a, "end", start + 3);
      for (double f = start + 3; f <= std::max(start + 3, end); f += 3) key(*gen, track, f, target(f), Interp::Linear);
      continue;
    }

    if (type == "expression") {
      std::vector<std::string> morphNames;
      for (auto& mt : characters_[size_t(c)].rig.morphs) morphNames.push_back(mt.name);
      const std::string requested = str(a, "name"), name = resolveExpression(asset, requested, morphNames);
      if (name.empty()) {  // reported, not silently ignored: the scene still plays, without this expression
        warnings_.push_back(std::format("expression: character '{}' has no expression '{}'", who, requested));
        continue;
      }
      const std::string track = prefix + "expr." + name;
      auto d = asset.defaultExpressions.find(name);
      const float base = clip.evaluate(track, start, vec3(d == asset.defaultExpressions.end() ? 0.0f : d->second)).x;
      const double ramp = num(a, "ramp", 6);
      const float w = float(num(a, "weight", 1));
      key(*gen, track, start, vec3(base));
      key(*gen, track, start + ramp, vec3(w));
      beats.push_back({Beat::Kind::Expression, c, -1, start, start, 0, 0, 0, num(a, "end", start + 36), vec3(0), vec3(0)});
      if (has(a, "end")) {
        key(*gen, track, num(a, "end", 0), vec3(w));
        key(*gen, track, num(a, "end", 0) + ramp, vec3(base));
      }
      continue;
    }

    if (type == "reach") {
      const std::string sideStr = str(a, "hand", "R");
      const char side = sideStr.empty() ? 'R' : sideStr[0];
      const int o = objIndex(str(a, "object"));
      if (o < 0) return fail(std::format("reach: unknown object '{}'", str(a, "object")));
      const std::string hand = std::string("hand.") + side, H = prefix + hand;
      const int handBone = asset.skeleton.find(hand), upper = asset.skeleton.find(std::string("upperArm.") + side);
      if (handBone < 0 || upper < 0) return fail(std::format("reach: '{}' has no {} arm", who, side));
      const double contact = num(a, "contact", start + 14), liftEnd = num(a, "liftEnd", contact + 12);
      const double place = num(a, "place", liftEnd + 24), release = num(a, "release", place + 3), end = num(a, "end", release + 14);
      // Contact and put-down keep their exact wrist targets in the arm-body clearance pass (T-030).
      interactions.frozen.push_back({c, side, contact, contact});
      interactions.frozen.push_back({c, side, place, release});
      const float lift = float(num(a, "lift", 0.05)), radius = float(num(a, "graspRadius", 0.012));
      const vec3 p0 = objPos(o, contact);
      const vec3 placeP = vec(a, "placeAt", p0);
      leanToward(c, side, p0, 0.03f + radius, start, contact, release, end, "reach '" + str(a, "object") + "'");
      // Where the wrist goes so the object sits in front of the palm, along the line from the shoulder.
      const vec3 shoulder = vec3(characterGlobals(size_t(c), contact)[size_t(upper)][3]);
      auto wristFor = [&](vec3 p) {
        vec3 dir = p - shoulder;
        dir.y *= 0.5f;
        return p - glm::normalize(dir) * (0.03f + radius) + vec3(0, 0.014f, 0);
      };
      const vec3 toBody = glm::normalize(vec3(shoulder.x - p0.x, 0, shoulder.z - p0.z) + vec3(1e-6f));
      const vec3 held = wristFor(p0) + vec3(0, lift, 0) + toBody * 0.04f;
      const std::string ik = prefix + "ik." + hand;
      key(*gen, ik, start, wristFor(p0) + vec3(0, 0.045f, 0));
      key(*gen, ik, contact - 5, wristFor(p0) + vec3(0, 0.018f, 0));
      key(*gen, ik, contact, wristFor(p0));
      key(*gen, ik, liftEnd, held);
      key(*gen, ik, std::max(liftEnd, place - 8), held);
      key(*gen, ik, place - 4, wristFor(placeP) + vec3(0, 0.02f, 0));
      key(*gen, ik, place, wristFor(placeP));
      key(*gen, ik, end, wristFor(placeP) + vec3(0, 0.02f, 0));
      key(*gen, ik + ".weight", start, vec3(0));
      key(*gen, ik + ".weight", contact - 5, vec3(0.9f));
      key(*gen, ik + ".weight", contact, vec3(1));
      key(*gen, ik + ".weight", release, vec3(1));
      key(*gen, ik + ".weight", end, vec3(0));
      // Hand: opens in anticipation, then the grip closes on the object by contact search; opens on release.
      const vec3 relaxed(0.25f, 0.15f, 0), open(0.03f, 0.05f, 0.35f);
      key(*gen, H, start, relaxed);
      key(*gen, H, contact - 6, open);
      key(*gen, H, contact, open);
      key(*gen, H, release + 1, open);
      key(*gen, H, end, relaxed);
      // Grip centre in the hand's frame at contact (the object then rides with the hand, so it stays fixed).
      const mat4 handAtContact = characterGlobals(size_t(c), contact)[size_t(handBone)];
      const vec3 centre = vec3(glm::inverse(handAtContact) * vec4(p0, 1));
      key(*gen, H + ".grasp", start, centre, Interp::Step);
      key(*gen, H + ".graspRadius", start, vec3(radius), Interp::Step);
      if (has(a, "graspAxis")) {
        vec3 axisW = vec(a, "graspAxis", vec3(0, 0, 1));
        key(*gen, H + ".graspAxis", start, vec3(glm::inverse(handAtContact) * vec4(axisW, 0)), Interp::Step);
      }
      key(*gen, H + ".grasp.weight", start, vec3(0));
      key(*gen, H + ".grasp.weight", contact - 4, vec3(0));
      key(*gen, H + ".grasp.weight", contact, vec3(1));
      key(*gen, H + ".grasp.weight", release, vec3(1));
      key(*gen, H + ".grasp.weight", release + 5, vec3(0));
      ObjectDesc& od = scene_.objects[size_t(o)];
      od.attachTo = who + "/" + hand;
      od.attachFrame = contact;
      od.releaseFrame = release;
      // Gaze: on the object a little before the hand moves, following it while held, then back.
      if (!(a.contains("look") && a["look"].is_boolean() && !a["look"].get<bool>())) {
        const std::string track = prefix + "lookAt";
        vec3 prev = clip.evaluate(track, start - 4, vec3(cd.position + vec3(0, 0.6f, 3)));
        dropKeysAfter(*gen, track, start - 4);
        key(*gen, track, start - 4, prev, Interp::Linear);
        key(*gen, track, start - 1, p0, Interp::Linear);
        for (double f = contact; f <= release + 8; f += 3) key(*gen, track, f, objPos(o, f), Interp::Linear);
        key(*gen, track, end + 2, objPos(o, release + 8), Interp::Linear);
        key(*gen, track, end + 6, prev, Interp::Linear);
      }
      beats.push_back({Beat::Kind::Reach, c, o, start, contact, liftEnd, place, release, end, p0, placeP});
      // Ripples where a floating object leaves the water and where it goes back in.
      if (!od.floatOn.empty()) {
        int w = objIndex(od.floatOn);
        if (w >= 0) {
          auto local = [&](vec3 p, double f) { return vec3(glm::inverse(objectWorld(size_t(w), f)) * vec4(p, 1)); };
          vec3 a0 = local(p0, contact + 2), a1 = local(placeP, release);
          scene_.objects[size_t(w)].ripples.emplace_back(a0.x, a0.z, float(contact + 2), 0.0012f);
          scene_.objects[size_t(w)].ripples.emplace_back(a1.x, a1.z, float(release), 0.0018f);
        }
      }
      continue;
    }

    if (type == "touch") {
      const std::string sideStr = str(a, "hand", "R");
      const char side = sideStr.empty() ? 'R' : sideStr[0];
      const std::string hand = std::string("hand.") + side, H = prefix + hand, ik = prefix + "ik." + hand;
      const int upper = asset.skeleton.find(std::string("upperArm.") + side);
      if (upper < 0) return fail(std::format("touch: '{}' has no {} arm", who, side));
      const double contact = num(a, "contact", start + 14), end = num(a, "end", contact + 20);
      const vec3 T = vec(a, "target", vec3(0));
      interactions.frozen.push_back({c, side, contact - 4, contact + 8});  // the fingertip touch stays exact (T-030)
      leanToward(c, side, T, 0.05f, start, contact, contact + 8, end, "touch");
      const vec3 shoulder = vec3(characterGlobals(size_t(c), contact)[size_t(upper)][3]);
      vec3 dir = T - shoulder;
      dir.y *= 0.6f;
      dir = glm::normalize(dir);
      const vec3 wrist = T - dir * 0.05f;  // the index fingertip is ~5 cm beyond the wrist when pointing
      key(*gen, ik, start, wrist + vec3(0, 0.06f, 0));
      key(*gen, ik, contact - 4, wrist + vec3(0, 0.02f, 0));
      key(*gen, ik, contact, wrist - vec3(0, 0.004f, 0));
      key(*gen, ik, contact + 8, wrist + vec3(0, 0.015f, 0));
      key(*gen, ik, end, wrist + vec3(0, 0.04f, 0));
      key(*gen, ik + ".weight", start, vec3(0));
      key(*gen, ik + ".weight", contact - 6, vec3(1));
      key(*gen, ik + ".weight", contact + 10, vec3(1));
      key(*gen, ik + ".weight", end, vec3(0));
      key(*gen, H, start, vec3(0.25f, 0.15f, 0), Interp::Linear);
      key(*gen, H, contact - 8, vec3(1, 1, 0), Interp::Linear);
      key(*gen, H, end - 6, vec3(1, 1, 0), Interp::Linear);
      key(*gen, H, end, vec3(0.25f, 0.15f, 0), Interp::Linear);
      key(*gen, H + ".index", start, vec3(0.25f), Interp::Linear);
      key(*gen, H + ".index", contact - 8, vec3(0), Interp::Linear);
      key(*gen, H + ".index", end - 6, vec3(0), Interp::Linear);
      key(*gen, H + ".index", end, vec3(0.25f), Interp::Linear);
      // Correct the wrist targets so the posed index fingertip lands exactly on the target (hand orientation comes
      // from the solved arm, so the first estimate is off by a few centimetres).
      float tipErr = 0;
      for (int it = 0; it < 10; ++it) {
        Pose pose;
        characterGlobals(size_t(c), contact, &pose);
        const mat4 body = objectMatrix(clip.evaluate(who + ".position", contact, cd.position),
                                       clip.evaluate(who + ".yaw", contact, vec3(cd.yawDeg)).x, 1.0f);
        auto tips = fingertips(asset.skeleton, pose, body, side);
        if (tips.size() < 5) break;
        const vec3 err = T - tips[4];
        tipErr = glm::length(err);
        if (tipErr < 0.002f) break;
        for (auto& k : gen->tracks[ik].keys)
          if (k.frame >= start && k.frame <= end) k.value += err;  // only this action's keys
      }
      if (tipErr > 0.01f)
        logWarn("touch: '{}' fingertip stays {:.0f} mm from the target at frame {} (out of reach); move them closer", who,
                tipErr * 1000, contact);
      const std::string look = prefix + "lookAt";
      vec3 prev = clip.evaluate(look, start - 4, cd.position + vec3(0, 0.6f, 3));
      dropKeysAfter(*gen, look, start - 4);
      key(*gen, look, start - 4, prev, Interp::Linear);
      key(*gen, look, start, T, Interp::Linear);
      key(*gen, look, end + 4, T, Interp::Linear);
      // Ripples when the fingertip meets a water surface.
      for (size_t w = 0; w < scene_.objects.size(); ++w) {
        ObjectDesc& wo = scene_.objects[w];
        if (wo.kind != ObjectDesc::Kind::Water) continue;
        vec3 l = vec3(glm::inverse(objectWorld(w, contact)) * vec4(T, 1));
        if (std::abs(l.x) <= wo.waterHalfSize.x && std::abs(l.z) <= wo.waterHalfSize.y && std::abs(l.y) < 0.03f) {
          wo.ripples.emplace_back(l.x, l.z, float(contact), 0.0016f);
          wo.ripples.emplace_back(l.x, l.z, float(contact + 9), 0.0008f);
        }
      }
      beats.push_back({Beat::Kind::Touch, c, -1, start, contact, 0, 0, 0, end, T, T});
      continue;
    }

    if (type == "walk") {
      const double end = num(a, "end", start + 45);
      if (end <= start + 6) return fail("walk: end must be at least 6 frames after start");
      const std::string posT = who + ".position", yawT = who + ".yaw";
      const vec3 ps = clip.evaluate(posT, start, cd.position);
      const vec3 to = vec(a, "to", ps);
      const vec3 pe(to.x, ps.y, to.z);
      const vec3 dir = pe - ps;
      const float dist = glm::length(dir);
      const float yaw0 = clip.evaluate(yawT, start, vec3(cd.yawDeg)).x;
      const float yawWalk = dist > 1e-4f ? glm::degrees(std::atan2(dir.x, dir.z)) : yaw0;
      key(*gen, posT, start, ps);
      key(*gen, posT, end, pe);
      key(*gen, yawT, start, vec3(yaw0));
      key(*gen, yawT, start + 6, vec3(yawWalk));
      key(*gen, yawT, end, vec3(yawWalk));
      if (has(a, "face")) key(*gen, yawT, end + 8, vec3(float(num(a, "face", yawWalk))));
      // Footsteps: alternating swings, each landing where the body will be half a step later.
      const int footL = asset.skeleton.find("foot.L"), footR = asset.skeleton.find("foot.R");
      if (footL < 0 || footR < 0) continue;  // no legs to plant: the root still moves
      auto bodyAt = [&](double f) {
        return objectMatrix(clip.evaluate(posT, f, cd.position), clip.evaluate(yawT, f, vec3(cd.yawDeg)).x, 1.0f);
      };
      auto ankle = [&](char s, double f) {
        vec3 rest = asset.skeleton.bones[size_t(s == 'L' ? footL : footR)].head;
        return vec3(bodyAt(f) * vec4(rest, 1));
      };
      const float stepLen = walkStep(asset);          // from the character's legs (or its explicit setting)
      const float gaitScale = stepLen / 0.11f;           // lift and pelvis motion scale with the step
      const int steps = std::max(2, int(std::ceil(dist / stepLen)));
      const double dt = (end - start) / double(steps);
      vec3 last[2] = {ankle('L', start), ankle('R', start)};
      for (char s : {'L', 'R'}) {
        const std::string t = prefix + "ik.foot." + s;
        key(*gen, t, start, last[s == 'L' ? 0 : 1]);
        key(*gen, t + ".weight", start - 1, vec3(0));
        key(*gen, t + ".weight", start, vec3(1));
      }
      const std::string root = prefix + "root.loc";
      key(*gen, root, start, vec3(0));
      for (int k = 0; k <= steps; ++k) {
        const char s = k % 2 == 0 ? 'L' : 'R';
        const int si = s == 'L' ? 0 : 1;
        // Each swing uses ~85% of its interval, so both feet are briefly planted at every hand-over (double support).
        const double ds = 0.075 * dt;
        const double t0 = start + dt * (k == 0 ? 0.0 : k - 0.5) + (k == 0 ? 0.0 : ds), t1 = std::min(end, start + dt * (k + 0.5) - ds);
        const double land = std::min(end, t1 + dt * 0.5);
        const vec3 next = k >= steps - 1 ? ankle(s, end) : ankle(s, land);
        const std::string t = prefix + "ik.foot." + s;
        key(*gen, t, t0, last[si]);
        key(*gen, t, 0.5 * (t0 + t1), glm::mix(last[si], next, 0.5f) + vec3(0, 0.022f * gaitScale, 0));
        key(*gen, t, t1, next);
        last[si] = next;
        // Pelvis drops at each landing and leans over the standing foot mid-swing.
        const float lean = (s == 'L' ? -0.005f : 0.005f) * gaitScale;
        key(*gen, root, 0.5 * (t0 + t1), vec3(lean, 0.002f * gaitScale, 0));
        key(*gen, root, t1, vec3(0, -0.005f * gaitScale, 0));
        // Arms swing against the legs (forward = negative x rotation), keeping each arm's resting spread.
        for (char arm : {'L', 'R'}) {
          std::string bone = std::string("upperArm.") + arm;
          auto dp = asset.defaultPose.find(bone);
          vec3 rest = dp == asset.defaultPose.end() ? vec3(0) : dp->second;
          float swing = (arm != s) ? -11.0f : 9.0f;
          key(*gen, prefix + bone + ".rot", 0.5 * (t0 + t1), rest + vec3(swing, 0, 0));
          if (k == 0) key(*gen, prefix + bone + ".rot", start, rest);
          if (k == steps) key(*gen, prefix + bone + ".rot", end + 4, rest);
        }
      }
      key(*gen, root, end + 2, vec3(0));
      beats.push_back({Beat::Kind::Walk, c, -1, start, start, 0, 0, 0, end, pe, pe});
      walkSpans_[size_t(c)].push_back({start, end + 6});
      for (char s : {'L', 'R'}) {
        const std::string t = prefix + "ik.foot." + s;
        key(*gen, t + ".weight", end + 2, vec3(1));
        key(*gen, t + ".weight", end + 6, vec3(0));
      }
      continue;
    }
    if (type == "clip") {
      std::filesystem::path file;
      const std::string name = str(a, "clip");
      if (has(a, "file")) {
        file = scene_.path.parent_path() / str(a, "file");
      } else {
        if (name.empty()) return fail("clip: give 'clip' (library name) or 'file'");
        for (auto d = std::filesystem::absolute(scene_.path).parent_path();; d = d.parent_path()) {
          auto cand = d / "content" / "clips" / (name + ".clip.json");
          if (std::filesystem::exists(cand)) {
            file = cand;
            break;
          }
          if (d == d.parent_path()) break;
        }
        if (file.empty()) return fail(std::format("clip: '{}' not found in content/clips above {}", name, scene_.path.string()));
      }
      auto cl = cachedClip(file);
      if (!cl) return fail(cl.error().message);
      ClipLayer L;
      L.clip = *cl;
      L.base = a.value("base", false);
      L.tier = L.base ? 0 : 2;
      L.binding = bindClip(asset.skeleton, L.clip->reference, retargetData(size_t(c), L.clip->reference));
      L.start = has(a, "start") || has(a, "frame") ? start : double(scene_.frameStart);
      L.speed = num(a, "speed", 1.0);
      if (L.speed <= 0) return fail("clip: speed must be > 0");
      L.weight = num(a, "weight", 1.0);
      L.blendIn = num(a, "blendIn", L.base ? 0.0 : 6.0);
      L.blendOut = num(a, "blendOut", L.base ? 0.0 : 6.0);
      L.mirror = a.value("mirror", false);
      const bool loop = a.contains("loop") ? a.value("loop", false) : L.clip->loop;
      if (loop != L.clip->loop) {  // a per-action loop override plays a copy of the clip with that setting
        auto copy = std::make_shared<ClipData>(*L.clip);
        copy->loop = loop;
        L.clip = copy;
      }
      const double sceneLen = L.clip->duration() * scene_.rate.fps() / L.speed;
      L.end = has(a, "end") ? num(a, "end", 0) : (L.base || loop) ? 1e30 : L.start + sceneLen;
      if (L.end <= L.start) return fail("clip: end must be after start");
      for (const auto& r : L.binding.roles)
        if (r.bone < 0 && L.clip->tracks.count(r.name) && r.name.rfind("eye.", 0) != 0)
          warnings_.push_back(std::format("clip '{}': character '{}' has no role '{}' (not played)", L.clip->name, who, r.name));
      clipLayers_[size_t(c)].push_back(std::move(L));
      sortLayers(c);
      continue;
    }
    if (type == "emotion") {
      const std::string full = str(a, "name");
      const size_t slash = full.find('/');
      const std::string ename = full.substr(0, slash), variant = slash == std::string::npos ? "" : full.substr(slash + 1);
      if (ename.empty()) return fail("emotion: give 'name' (library name, optionally name/variant)");
      const auto file = findLibrary("emotions", ename + ".emotion.json");
      if (file.empty()) return fail(std::format("emotion: '{}' not found in content/emotions above {}", ename, scene_.path.string()));
      auto j = parseJsonFile(file);
      if (!j) return fail(j.error().message);
      auto e = emotionFromJson(*j, variant);
      if (!e) return fail(std::format("{}: {}", file.string(), e.error().message));
      const double fps = scene_.rate.fps();
      const double intensity = std::clamp(num(a, "intensity", 1.0), 0.0, 1.0);
      double onset = e->onset * fps, release = e->release * fps;
      const double end = has(a, "end") ? num(a, "end", 0) : start + onset + e->hold * fps + release;
      if (end <= start) return fail("emotion: end must be after start");
      if (onset + release > end - start) {  // a short emotion: the ramps share its length
        const double k = (end - start) / (onset + release);
        onset *= k;
        release *= k;
      }
      ClipLayer env;
      env.start = start;
      env.end = end;
      env.blendIn = onset;
      env.blendOut = release;
      env.weight = intensity;
      env.linear = e->linear;
      env.tier = 1;
      std::vector<std::string> morphNames;
      for (auto& mt : characters_[size_t(c)].rig.morphs) morphNames.push_back(mt.name);
      auto resolveFace = [&](const std::vector<std::pair<std::string, float>>& mix) {
        std::vector<std::pair<std::string, float>> out;
        for (const auto& [ename2, w] : mix) {
          const std::string morph = resolveExpression(asset, ename2, morphNames);
          if (morph.empty()) {  // nothing is invented for a missing morph: one warning, the body still plays
            if (missingFace.insert(who + "|" + full + "|" + ename2).second)
              warnings_.push_back(std::format("emotion '{}': character '{}' has no morph for expression '{}' (face part skipped, body plays)", full, who, ename2));
            continue;
          }
          out.push_back({morph, w});
        }
        return out;
      };
      PendingEmotion pe{c, env, {}, false, resolveFace(e->face), has(a, "end"), e->faceMotion, e->hasFaceMotion};
      auto addLayer = [&](const std::string& clipName, ClipLayer L, int loopOverride, const std::vector<std::string>& mask,
                          bool defer) -> Result<void> {
        const auto cf = findLibrary("clips", clipName + ".clip.json");
        if (cf.empty()) return fail(std::format("emotion '{}': clip '{}' not found in content/clips", full, clipName));
        auto cl = cachedClip(cf);
        if (!cl) return std::unexpected(cl.error());
        L.clip = *cl;
        const bool loop = loopOverride < 0 ? L.clip->loop : loopOverride == 1;
        if (loop != L.clip->loop || !mask.empty()) {  // overrides play a copy of the clip
          auto copy = std::make_shared<ClipData>(*L.clip);
          copy->loop = loop;
          if (!mask.empty()) copy->mask = mask;
          L.clip = copy;
        }
        if (L.end < 0) L.end = L.start + L.clip->duration() * fps;
        L.binding = bindClip(asset.skeleton, L.clip->reference, retargetData(size_t(c), L.clip->reference));
        for (const auto& r : L.binding.roles)
          if (r.bone < 0 && L.clip->tracks.count(r.name) && r.name.rfind("eye.", 0) != 0)
            warnings_.push_back(std::format("emotion '{}' clip '{}': character '{}' has no role '{}' (not played)", full, L.clip->name, who, r.name));
        if (defer) {
          pe.posture = std::move(L);
          pe.hasPosture = true;
        } else {
          clipLayers_[size_t(c)].push_back(std::move(L));
        }
        return {};
      };
      if (!e->bodyClip.empty())
        if (auto r = addLayer(e->bodyClip, env, e->bodyLoop, e->bodyMask, true); !r) return fail(r.error().message);
      if (e->hasGesture) {
        ClipLayer g;
        g.tier = 1;
        g.start = start + e->gesture.offset * fps;
        g.end = -1;  // the clip's length
        g.blendIn = e->gesture.blendIn * fps;
        g.blendOut = e->gesture.blendOut * fps;
        g.weight = intensity;
        g.linear = e->linear;
        g.mirror = e->gesture.mirror;
        if (auto r = addLayer(e->gesture.clip, g, 0, {}, false); !r) return fail(r.error().message);
        for (const auto& [morph, w] : resolveFace(e->gesture.face)) emotionFace.push_back({c, morph, clipLayers_[size_t(c)].back(), w});
        sortLayers(c);
      }
      pending.push_back(std::move(pe));
      beats.push_back({Beat::Kind::Expression, c, -1, start, start, 0, 0, 0, end, vec3(0), vec3(0)});
      continue;
    }
    return fail(std::format("unknown action type '{}'", type));
  }
  // Consecutive emotions of a character crossfade: when one starts before the previous one has ended, the previous
  // one releases from that start over (its release + the new onset), and the new one's onset takes the same time.
  // The sum keeps a transition no faster than the faster of the two ramps it replaces, whatever the two postures.
  // Without an explicit end the new one's end moves by the extra onset time (its hold keeps its length).
  for (size_t i = 0; i < pending.size(); ++i) {
    ClipLayer& cur = pending[i].envelope;
    for (size_t k = i + 1; k < pending.size(); ++k) {
      if (pending[k].character != pending[i].character) continue;
      ClipLayer& next = pending[k].envelope;
      if (next.start < cur.end && next.start > cur.start) {
        const double cross = cur.blendOut + next.blendIn;
        cur.end = next.start + cross;
        cur.blendOut = cross;
        if (!pending[k].explicitEnd) next.end += cross - next.blendIn;
        next.blendIn = std::max(0.0, std::min(cross, next.end - next.start - next.blendOut));
      }
      break;  // only the next emotion of the same character
    }
  }
  for (auto& pe : pending) {
    for (const auto& [morph, w] : pe.face) emotionFace.push_back({pe.character, morph, pe.envelope, w});
    if (pe.hasFaceMotion) {
      const ClipLayer& e = pe.envelope;
      faceTimelines_[size_t(pe.character)].emotions.push_back(
          {FaceEnvelope{e.start, e.end, e.blendIn, e.blendOut, e.weight, e.linear}, pe.faceMotion});
    }
    if (!pe.hasPosture) continue;
    pe.posture.start = pe.envelope.start;
    pe.posture.end = pe.envelope.end;
    pe.posture.blendIn = pe.envelope.blendIn;
    pe.posture.blendOut = pe.envelope.blendOut;
    clipLayers_[size_t(pe.character)].push_back(std::move(pe.posture));
    sortLayers(pe.character);
  }
  // Emotion faces: per morph, the track as compiled so far plus every emotion's weight x envelope, written as
  // per-frame keys over the scene range (hand keys on the morph still win: generated tracks are only a fallback).
  std::map<std::pair<int, std::string>, std::vector<const FaceContribution*>> faceByMorph;
  for (const auto& fc : emotionFace) faceByMorph[{fc.character, fc.morph}].push_back(&fc);
  for (const auto& [cm, list] : faceByMorph) {
    const auto& [c, morph] = cm;
    const std::string track = scene_.characters[size_t(c)].name + "/expr." + morph;
    const auto& defs = characters_[size_t(c)].asset.defaultExpressions;
    auto d = defs.find(morph);
    const float def = d == defs.end() ? 0.0f : d->second;
    const Track* old = gen->find(track);
    std::vector<Key> keys;
    for (int f = scene_.frameStart - 1; f <= scene_.frameEnd + 1; ++f) {
      double v = old && !old->keys.empty() ? old->evaluate(f).x : def;
      for (const FaceContribution* fc : list) v += fc->envelope.envelope(f) * fc->weight;
      keys.push_back({double(f), vec3(float(std::clamp(v, 0.0, 1.0))), Interp::Linear});
    }
    gen->tracks[track].keys = std::move(keys);
  }
  if (auto r = finishInteractions(*gen, interactions); !r) return r;
  if (scene_.director.is_object()) planShots(*this, *gen, beats);
  return {};
}

}  // namespace plush
