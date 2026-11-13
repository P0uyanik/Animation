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
//
// Director (scene "director": {minShot?, closeFocal?, closeFStop?, mediumFocal?, mediumFStop?}): plans camera shots
// from the action beats — establishing wide (the scene camera), medium on a character starting an action, insert
// close-ups on the hands/object at contact and at placement, reaction close-ups on faces, back to wide — places
// each camera on the master camera's side of the action (180-degree rule), turns it away from characters standing
// in the way, focuses on the subject with a shallow aperture for close-ups and pushes in gently during each shot.
// Any hand-keyed camera track overrides the director.
#include <algorithm>
#include <format>

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
  auto gen = std::make_shared<Clip>();
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
  if (!scene_.actions.is_array() || scene_.actions.empty()) return {};

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

  for (const Json* ap : actions) {
    const Json& a = *ap;
    const std::string type = str(a, "type"), who = str(a, "character");
    const int c = charIndex(who);
    if (c < 0) return fail(std::format("action '{}': unknown character '{}'", type, who));
    const CharacterDesc& cd = scene_.characters[size_t(c)];
    const CharacterAsset& asset = characters_[size_t(c)].asset;
    const std::string prefix = who + "/";
    const double start = startOf(&a);

    if (type == "look") {
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
      const std::string name = str(a, "name");
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
        for (auto& k : gen->tracks[ik].keys) k.value += err;
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
      const int steps = std::max(2, int(std::ceil(dist / 0.11f)));
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
        const double t0 = start + dt * (k == 0 ? 0.0 : k - 0.5), t1 = std::min(end, start + dt * (k + 0.5));
        const double land = std::min(end, t1 + dt * 0.5);
        const vec3 next = k >= steps - 1 ? ankle(s, end) : ankle(s, land);
        const std::string t = prefix + "ik.foot." + s;
        key(*gen, t, t0, last[si]);
        key(*gen, t, 0.5 * (t0 + t1), glm::mix(last[si], next, 0.5f) + vec3(0, 0.022f, 0));
        key(*gen, t, t1, next);
        last[si] = next;
        // Pelvis drops at each landing and leans over the standing foot mid-swing.
        const float lean = s == 'L' ? -0.005f : 0.005f;
        key(*gen, root, 0.5 * (t0 + t1), vec3(lean, 0.002f, 0));
        key(*gen, root, t1, vec3(0, -0.005f, 0));
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
      for (char s : {'L', 'R'}) {
        const std::string t = prefix + "ik.foot." + s;
        key(*gen, t + ".weight", end + 2, vec3(1));
        key(*gen, t + ".weight", end + 6, vec3(0));
      }
      continue;
    }
    return fail(std::format("unknown action type '{}'", type));
  }
  if (scene_.director.is_object()) planShots(*this, *gen, beats);
  return {};
}

}  // namespace plush
