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
//   collision  {character, enabled=true}  enabled:false plans this character's arms without its collision body
//              (scene/collision.h; for A/B measurements); bodyClearance (T-191, opt-in): lean away from other
//              characters' bodies, bodyClearanceMm (10), bodyLeanMaxDeg (12)
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
//
// Framing rules (T-140, opt-in: director "framing": true | {headroom?, safeMargin?, reachCrop?}; absent / false = the
// framing before T-140, unchanged): after a shot is planned its camera keeps its direction and lens, but backs off
// (never pushes in further) and shifts its target until the shot's required points stay inside the safe area over
// the whole shot, push-in included:
//   - headroom: the top of each framed head keeps `headroom` (fraction of the frame height, default 0.05) below the
//     top edge. The head is measured from the skinned geometry carried by the head bone and its children, so hair, a
//     bun and hair accessories count, not just the head bone;
//   - safe margins: every required point keeps `safeMargin` (fraction of the frame, default 0.04) from each edge;
//   - crop choice for reach acting, `reachCrop`: "hands" (default) keeps the reaching character's head, both hands
//     and the object in the medium shot, and every head, hand and prop in wide shots; "face" keeps only the heads and
//     the object/props (hands may leave the frame). Close-ups keep the whole head; inserts keep their subject.
// The fit measures the kinematic pose, as all action planning does (secondary motion is built after the actions
// compile): a spring-driven bun or hair can swing a few millimetres past it (6 mm on e910, T-140 README).
// Director "cuts": false keeps only the master (wide) camera, refitted by the framing rules when they are on. It
// defaults to false when framing is on and to true (the planned cuts, as before T-140) when framing is off.
#include <algorithm>
#include <array>
#include <format>
#include <map>
#include <set>

#include "scene/emotion.h"
#include "scene/reaction.h"
#include "scene/scene.h"
#include "scene/verbs.h"

namespace plush {
namespace {

// Local bounds of each prop (min, max) in the prop's frame, for framing (T-140).
using PropBox = std::array<vec3, 2>;

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
// Extreme points of the skinned geometry carried by bone `root` and its descendants (hair, a bun, accessories and
// their spring bones included), each vertex counted for its most weighted joint: per carrying bone, the furthest
// vertex along each of 124 directions in that bone's rest-aligned local frame, a tight sample of the hull. Empty when
// the bone is missing or carries nothing.
using Carried = std::vector<std::pair<int, vec3>>;  // (bone, point in the bone's local frame)
Carried carriedPoints(const SceneEvaluator::CharacterInstance& ci, int root) {
  const auto& sk = ci.asset.skeleton;
  if (root < 0) return {};
  std::vector<char> in(sk.bones.size(), 0);
  for (size_t b = 0; b < sk.bones.size(); ++b)
    in[b] = int(b) == root || (sk.bones[b].parent >= 0 && in[size_t(sk.bones[b].parent)]);
  std::vector<vec3> dirs;
  for (int x = -2; x <= 2; ++x)
    for (int y = -2; y <= 2; ++y)
      for (int z = -2; z <= 2; ++z)
        if (x || y || z) dirs.push_back(glm::normalize(vec3(x, y, z)));
  std::map<int, std::vector<std::pair<float, vec3>>> best;  // bone -> per direction (extent, point)
  auto add = [&](int j, vec3 restPos) {
    if (j < 0 || size_t(j) >= in.size() || !in[size_t(j)]) return;
    // Rest frames are axis aligned (anim/animation.h): the local point is the rest position minus the bone's pivot.
    const vec3 q = restPos - sk.bones[size_t(j)].head;
    auto& e = best.try_emplace(j, dirs.size(), std::pair<float, vec3>{-1e9f, vec3(0)}).first->second;
    for (size_t k = 0; k < dirs.size(); ++k)
      if (float v = glm::dot(q, dirs[k]); v > e[k].first) e[k] = {v, q};
  };
  for (const auto& m : ci.rig.meshes)
    for (size_t i = 0; i < m.rest.positions.size() && i < m.joints.size(); ++i) {
      int j = m.joints[i].x;
      float w = m.weights[i].x;
      for (int k = 1; k < 4; ++k)
        if (m.weights[i][k] > w) w = m.weights[i][k], j = m.joints[i][k];
      add(j, m.rest.positions[i]);
    }
  for (const auto& l : ci.rig.locks)
    for (const vec4& p : l.rest.points) add(l.bone, vec3(p));
  Carried out;
  for (const auto& [bone, e] : best) {
    std::set<std::array<float, 3>> seen;
    for (const auto& [v, q] : e)
      if (seen.insert({q.x, q.y, q.z}).second) out.push_back({bone, q});
  }
  return out;
}

void planShots(const SceneEvaluator& ev, Clip& gen, const std::vector<Beat>& beats, const std::vector<PropBox>& propBoxes) {
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
  // Framing rules (T-140, opt-in; see the header comment).
  const auto fit = d.find("framing");
  const bool framing = fit != d.end() && (fit->is_object() || (fit->is_boolean() && fit->get<bool>()));
  const Json fj = fit != d.end() && fit->is_object() ? *fit : Json::object();
  const float headroom = float(num(fj, "headroom", 0.05)), margin = float(num(fj, "safeMargin", 0.04));
  const bool keepHands = str(fj, "reachCrop", "hands") != "face";
  // "cuts": with framing on it defaults to false (the master camera only, refitted); without framing to true (as before).
  const bool cuts = d.contains("cuts") && d["cuts"].is_boolean() ? d["cuts"].get<bool>() : !framing;
  std::vector<Carried> headBox, handBox[2];
  std::vector<int> headBone, handBone[2];
  if (framing)
    for (const auto& ci : ev.characters()) {
      const auto& sk = ci.asset.skeleton;
      headBone.push_back(sk.find("head"));
      headBox.push_back(carriedPoints(ci, headBone.back()));
      for (int h = 0; h < 2; ++h) {
        handBone[h].push_back(sk.find(h ? "hand.R" : "hand.L"));
        handBox[h].push_back(carriedPoints(ci, handBone[h].back()));
      }
    }
  // Required points of a shot at a frame; `true` marks head points (they keep the headroom at the top).
  auto required = [&](const Shot& s, double f, std::vector<std::pair<vec3, bool>>& out) {
    out.clear();
    auto carried = [&](size_t c, int bone, const Carried& pts, bool head) {
      if (bone < 0 || pts.empty()) return;
      const auto G = ev.characterGlobals(c, f);
      for (const auto& [b, q] : pts) out.push_back({vec3(G[size_t(b)] * vec4(q, 1)), head});
    };
    auto character = [&](size_t c, bool hands) {
      carried(c, headBone[c], headBox[c], true);
      if (hands)
        for (int h = 0; h < 2; ++h) carried(c, handBone[h][c], handBox[h][c], false);
    };
    auto object = [&](int o) { out.push_back({vec3(ev.objectWorld(size_t(o), f)[3]), false}); };
    switch (s.kind) {
      case 0:
        for (size_t c = 0; c < ev.characters().size(); ++c) character(c, keepHands);
        for (size_t p = 0; p < sc.props.size() && p < propBoxes.size(); ++p) {
          const mat4 W = ev.propWorld(p, f);
          for (int k = 0; k < 8; ++k) {
            const PropBox& b = propBoxes[p];
            out.push_back({vec3(W * vec4(k & 1 ? b[1].x : b[0].x, k & 2 ? b[1].y : b[0].y, k & 4 ? b[1].z : b[0].z, 1)), false});
          }
        }
        break;  // scene objects are the set (floor, walls, tables): the wide shot does not chase their origins
      case 1: object(s.object); break;
      case 2: character(size_t(s.character), false); break;
      case 4:
        character(size_t(s.character), keepHands);
        out.push_back({s.point, false});
        break;
      case 5:
        character(size_t(s.character), false);
        object(s.object);
        break;
      default: out.push_back({s.point, false});
    }
  };
  std::vector<Shot> shots;
  for (const Beat& b : beats) {
    if (!cuts) break;
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
  // Fits a shot (T-140): the camera looks along `fw` at subject + shift from `dist` * push. Backs off (never pushes in)
  // and shifts until every required point stays inside the safe area at every sampled frame. Returns the distance
  // and sets `shift`.
  struct Sample {
    vec3 subject;
    float push;
    std::vector<std::pair<vec3, bool>> pts;
  };
  auto fitShot = [&](vec3 fw, float dist, float focal, const std::vector<Sample>& samples, vec3& shift) {
    const vec3 rt = glm::normalize(glm::cross(fw, vec3(0, 1, 0))), up = glm::cross(rt, fw);
    const float tx = sc.camera.sensorWidthMm * 0.5f / focal, ty = sensorH * 0.5f / focal;
    const float side = 1 - 2 * margin, top = 1 - 2 * headroom;
    shift = vec3(0);
    const float d0 = dist;
    for (int it = 0; it < 24; ++it) {
      float r = -1e9f, l = -1e9f, t = -1e9f, b = -1e9f;
      for (const Sample& sm : samples) {
        const vec3 cam = sm.subject + shift - fw * dist * sm.push;
        for (const auto& [p, head] : sm.pts) {
          const vec3 v = p - cam;
          const float z = std::max(1e-3f, glm::dot(v, fw));
          const float x = glm::dot(v, rt) / z / tx, y = glm::dot(v, up) / z / ty;
          r = std::max(r, x / side), l = std::max(l, -x / side);
          t = std::max(t, y / (head ? top : side)), b = std::max(b, -y / side);
        }
      }
      if (r <= 1.001f && l <= 1.001f && t <= 1.001f && b <= 1.001f) break;
      const float grow = std::max((r + l) * 0.5f, (t + b) * 0.5f);
      if (grow > 1.0f) {
        dist = std::min(dist * grow * 1.01f, d0 * 4);
        continue;
      }
      // Fits in size: slide the frame towards the side that is out (by the overshoot, in world units at `dist`).
      if (r > 1) shift += rt * ((r - 1) * side * tx * dist);
      if (l > 1) shift -= rt * ((l - 1) * side * tx * dist);
      if (t > 1) shift += up * ((t - 1) * top * ty * dist);
      if (b > 1) shift -= up * ((b - 1) * side * ty * dist);
    }
    return dist;
  };
  Track pos, tgt, lens;
  for (const Shot& s : all) {
    const double last = s.end - 1;
    if (s.kind == 0) {
      vec3 camPos = master, camTgt = sc.camera.target;
      float focus = sc.camera.focusDistance;
      std::string note;
      if (framing) {
        std::vector<Sample> samples;
        for (double f = s.start;; f = std::min(last, f + 1)) {  // every frame: a static camera has no keys to hide in
          samples.push_back({camTgt, 1.0f, {}});
          required(s, f, samples.back().pts);
          if (f >= last) break;
        }
        const vec3 fw = glm::normalize(camTgt - master);
        const float d0 = glm::distance(master, camTgt);
        vec3 shift;
        const float dist = fitShot(fw, d0, sc.camera.focalMm, samples, shift);
        camTgt += shift;
        camPos = camTgt - fw * dist;
        if (focus > 0) focus += dist - d0;
        note = std::format(" (framed: {:+.0f}% distance, target {:+.3f} {:+.3f} {:+.3f} m)", 100 * (dist / d0 - 1), shift.x, shift.y, shift.z);
      }
      pos.setKey({s.start, camPos, Interp::Step});
      tgt.setKey({s.start, camTgt, Interp::Step});
      lens.setKey({s.start, vec3(sc.camera.focalMm, sc.camera.fStop, focus), Interp::Step});
      logInfo("director: {:>6.1f}-{:<6.1f} {}{}", s.start, last, s.name, note);
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
    vec3 shift(0);
    std::string note;
    if (framing) {
      std::vector<Sample> samples;
      for (double f = s.start;; f = std::min(last, f + 1)) {
        double u = (f - s.start) / std::max(1.0, last - s.start);
        samples.push_back({subject(s, f), float(1.04 - 0.08 * u), {}});
        required(s, f, samples.back().pts);
        if (f >= last) break;
      }
      const float d0 = dist;
      dist = fitShot(-glm::normalize(off), dist, s.focal, samples, shift);
      off *= dist / d0;
      note = std::format(", framed: {:+.0f}% distance", 100 * (dist / d0 - 1));
    }
    for (double f = s.start;; f = std::min(last, f + 3)) {
      double u = (f - s.start) / std::max(1.0, last - s.start);
      vec3 sf = subject(s, f) + shift;
      vec3 p = sf + off * float(1.04 - 0.08 * u);  // gentle push-in
      Interp in = f >= last ? Interp::Step : Interp::Linear;
      pos.setKey({f, p, in});
      tgt.setKey({f, sf, in});
      lens.setKey({f, vec3(s.focal, s.fStop, glm::distance(p, sf)), in});
      if (f >= last) break;
    }
    logInfo("director: {:>6.1f}-{:<6.1f} {} ({} mm f/{:.1f}, {:.2f} m{}{})", s.start, last, s.name, s.focal, s.fStop, dist,
            turn != 0 ? std::format(", turned {:.0f} deg to clear a character", turn) : std::string(), note);
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

// Reaction events (T-097D, docs/PRODUCTION_PIPELINE.md "Scene events"): every event of the scene's opt-in "events"
// list is planned per reacting character (scene/reaction.h, the character's personality profile or the shared
// defaults) and becomes, at event time + notice delay, a look at the source (gaze habit: held for gazeShift of the
// reaction, then back), a blended emotion (T-097A, held for the plan's duration, the personality's intensity scale and
// gaze shift as its modulation) and the chosen gesture clip. Generated in event order, then scene character order.
Result<Json> SceneEvaluator::planReactionActions() {
  Json out = Json::array();
  auto evs = reactionEventsFromJson(scene_.events);
  if (!evs) return std::unexpected(evs.error());
  if (evs->empty()) return out;
  const double fps = scene_.rate.fps();
  auto library = [&](const char* kind) -> std::filesystem::path {
    for (auto d = std::filesystem::absolute(scene_.path).parent_path();; d = d.parent_path()) {
      if (std::filesystem::is_directory(d / "content" / kind)) return d / "content" / kind;
      if (d == d.parent_path()) return {};
    }
  };
  ReactionContext ctx;
  std::optional<TimingProfile> timing;
  if (const std::string name = scene_.timingProfile(); !name.empty()) {  // T-104: the timing profile's notice delay
    const auto file = findTimingProfileFile(scene_.path, name);
    if (auto t = file.empty() ? Result<TimingProfile>(fail("not found")) : loadTimingProfile(file)) timing = std::move(*t);
  }
  if (timing) ctx.timing = &*timing;
  if (const auto dir = library("clips"); !dir.empty()) {  // gestures the scene can play (sorted: deterministic)
    for (const auto& f : std::filesystem::directory_iterator(dir)) {
      const std::string n = f.path().filename().string(), ext = ".clip.json";
      if (n.size() > ext.size() && n.ends_with(ext)) ctx.availableGestures.push_back(n.substr(0, n.size() - ext.size()));
    }
    std::sort(ctx.availableGestures.begin(), ctx.availableGestures.end());
  }
  const auto emotions = library("emotions");
  std::vector<SceneEvent> order = *evs;
  std::stable_sort(order.begin(), order.end(), [](const SceneEvent& a, const SceneEvent& b) { return a.event.time < b.event.time; });
  for (const SceneEvent& se : order) {
    const ReactionEvent& ev = se.event;
    std::vector<std::pair<std::string, const PersonalityProfile*>> cast;
    for (size_t c = 0; c < scene_.characters.size(); ++c) {
      const std::string& n = scene_.characters[c].name;
      if (se.characters.empty() || std::find(se.characters.begin(), se.characters.end(), n) != se.characters.end())
        cast.push_back({n, personality(c)});
    }
    const std::string label = ev.name.empty() ? reactionEventKey(ev.kind) : ev.name;
    for (const CharacterReaction& r : planReactions(ev, cast, ctx)) {
      const ReactionPlan& p = r.plan;
      if (p.target.weights.empty()) continue;  // not noticed, or no emotion for this event
      // Never before the profile's shortest notice delay (reaction.delay_frames[0], what animcheck's acting rule
      // requires): the planner's mid delay x tempo_scale < 1 could otherwise undercut it.
      double delay = p.noticeDelay;
      for (size_t c = 0; c < scene_.characters.size(); ++c)
        if (const PersonalityProfile* P = personality(c); P && scene_.characters[c].name == r.character && P->reaction.delayFrames)
          delay = std::max(delay, double(P->reaction.delayFrames->lo) / 24.0);
      const double start = scene_.frameStart + (ev.time + delay) * fps, length = p.duration * fps;
      // Gaze: at the source's face (a character) or the object; a source of the character itself or "" = no look.
      if (!ev.source.empty() && ev.source != r.character) {
        Json look = {{"type", "look"}, {"character", r.character}, {"start", start},
                     {"end", start + std::max(3.0, double(p.modulation.gazeShift) * length)}, {"back", true}};
        const bool isChar = std::any_of(scene_.characters.begin(), scene_.characters.end(),
                                        [&](const CharacterDesc& d) { return d.name == ev.source; });
        const bool isObj = std::any_of(scene_.objects.begin(), scene_.objects.end(), [&](const ObjectDesc& o) { return o.name == ev.source; });
        if (isChar) look["atCharacter"] = ev.source;
        else if (isObj) look["object"] = ev.source;
        else warnings_.push_back(std::format("event '{}': source '{}' is no character or object (no look)", label, ev.source));
        if (isChar || isObj) out.push_back(std::move(look));
      }
      // Emotion: blended, released after the plan's duration (end = start + duration + the emotion's decay).
      const std::string emo = p.target.weights.front().first;
      const auto file = emotions.empty() ? std::filesystem::path() : emotions / (emo + ".emotion.json");
      auto j = file.empty() || !std::filesystem::exists(file) ? Result<Json>(fail("not found")) : parseJsonFile(file);
      auto e = j ? emotionFromJson(*j) : Result<EmotionDef>(std::unexpected(j.error()));
      if (!e) {
        warnings_.push_back(std::format("event '{}': character '{}': emotion '{}': {} (no emotion played)", label, r.character, emo,
                                        e.error().message));
      } else {
        const double decay = e->decay >= 0 ? e->decay : e->release;
        out.push_back({{"type", "emotion"}, {"character", r.character}, {"name", emo}, {"start", start},
                       {"end", start + length + decay * fps}, {"intensity", p.target.weights.front().second}, {"blend", true},
                       {"modulation", {{"intensityScale", p.modulation.intensityScale}, {"gazeShift", p.modulation.gazeShift}}}});
      }
      if (!p.gesture.empty()) out.push_back({{"type", "clip"}, {"character", r.character}, {"clip", p.gesture}, {"start", start}});
    }
  }
  return out;
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
  {  // T-061: the scene's animation-principles setting (validated when the scene loaded)
    auto pr = animPrinciplesFromJson(scene_.animPrinciples);
    principles_ = pr ? *pr : AnimPrinciples{};
  }
  // T-112a: verb actions (pick_up, carry, place with "verb": true) expand into primitive actions first
  // (scene/verbs.h, a pure pre-pass); a scene without one never enters it and compiles its authored list.
  std::optional<VerbExpansion> verbs;
  std::optional<TimingProfile> verbTiming;
  if (hasVerbAction(scene_.actions)) {
    VerbContext vc;
    vc.frameStart = scene_.frameStart;
    vc.fps = scene_.rate.fps();
    vc.events = !scene_.events.is_null();  // T-112b: "react" adds events only when the scene opted into them
    // The scene's timing profile, resolved as the interaction compile does (T-104d: calibrated unless the scene says
    // "none"; a named profile must exist, the implicit default may be missing outside a content tree).
    if (const std::string name = scene_.timingProfile(); !name.empty()) {
      const auto file = findTimingProfileFile(scene_.path, name);
      if (file.empty() && !scene_.timing.is_null())
        return fail(std::format("timing profile '{}' not found in content/timing", name));
      if (!file.empty()) {
        auto t = loadTimingProfile(file);
        if (!t) return std::unexpected(t.error());
        verbTiming = std::move(*t);
        vc.timing = &*verbTiming;
      }
    }
    for (size_t c = 0; c < scene_.characters.size(); ++c) {
      VerbContext::Character vch{scene_.characters[c].name, personality(c)};
      const Skeleton& sk = characters_[c].asset.skeleton;
      for (char side : {'L', 'R'}) {
        const int hb = characterSocketBone(c, std::string("hand.") + side);
        const int mb = hb >= 0 ? sk.bones[size_t(hb)].parent : -1, rb = mb >= 0 ? sk.bones[size_t(mb)].parent : -1;
        if (rb >= 0)
          vch.armLength[side == 'L' ? 0 : 1] = glm::distance(sk.bones[size_t(rb)].head, sk.bones[size_t(mb)].head) +
                                               glm::distance(sk.bones[size_t(mb)].head, sk.bones[size_t(hb)].head);
      }
      vc.characters.push_back(vch);
    }
    for (size_t p = 0; p < scene_.props.size(); ++p)
      vc.props.push_back({scene_.props[p].name, p < propAssets_.size() ? &propAssets_[p] : nullptr, scene_.props[p].transform,
                          scene_.props[p].parent});
    vc.verb = [&](const std::string& id) -> Result<VerbDef> {
      const auto file = findVerbFile(scene_.path, id);
      if (file.empty()) return fail(std::format("verb '{}' not found in content/verbs", id));
      return loadVerb(file);
    };
    auto x = expandVerbs(scene_.actions, vc);
    if (!x) return fail(x.error().message());
    verbs = std::move(*x);
  }
  const Json& authoredActions = verbs ? verbs->actions : scene_.actions;
  reactionActions_ = Json::array();
  if (!scene_.events.is_null()) {  // T-097D: opt-in reaction events, played as generated actions
    // T-112b: the verbs' reaction events ("react": true) are planned with the scene's own, then the list is restored
    const Json authoredEvents = scene_.events;
    if (verbs && scene_.events.is_array())
      for (const Json& e : verbs->events) scene_.events.push_back(e);
    auto ra = planReactionActions();
    scene_.events = authoredEvents;
    if (!ra) return std::unexpected(ra.error());
    reactionActions_ = std::move(*ra);
  }
  if ((!scene_.actions.is_array() || scene_.actions.empty()) && reactionActions_.empty()) return {};
  InteractionContext interactions;

  std::vector<const Json*> actions;
  if (authoredActions.is_array())
    for (const Json& a : authoredActions) actions.push_back(&a);
  for (const Json& a : reactionActions_) actions.push_back(&a);  // after the authored ones: ties keep authored first
  auto startOf = [](const Json* a) { return num(*a, "start", num(*a, "frame", 0)); };
  std::stable_sort(actions.begin(), actions.end(), [&](const Json* a, const Json* b) { return startOf(a) < startOf(b); });

  auto charIndex = [&](const std::string& n) -> int {
    for (size_t c = 0; c < scene_.characters.size(); ++c)
      if (scene_.characters[c].name == n) return int(c);
    return -1;
  };
  // Collision planning switch (T-047): {"type": "collision", "character", "enabled": false} plans that character's
  // arms without its collision body (for A/B measurements); applies to the whole shot, whatever its frame.
  // "maxElbowSwingDeg" (T-082, 0..120) overrides the character's elbow swing limit (collision.h) for this shot.
  for (const Json* ap : actions) {
    if (str(*ap, "type") != "collision") continue;
    const int c = charIndex(str(*ap, "character"));
    if (c < 0) return fail(std::format("action 'collision': unknown character '{}'", str(*ap, "character")));
    const auto en = ap->find("enabled");
    if (en != ap->end() && en->is_boolean() && !en->get<bool>() && size_t(c) < clearance_.size()) clearance_[size_t(c)].valid = false;
    if (const auto ms = ap->find("maxElbowSwingDeg"); ms != ap->end()) {
      if (!ms->is_number() || !(ms->get<float>() >= 0 && ms->get<float>() <= 120))
        return fail("action 'collision': maxElbowSwingDeg must be a number in [0, 120]");
      if (size_t(c) < clearance_.size()) clearance_[size_t(c)].collision.maxElbowSwing = glm::radians(ms->get<float>());
    }
    // T-191 (opt-in): "bodyClearance": true makes this character lean away from other characters' bodies
    // (interaction.cpp, finishInteractions), keeping "bodyClearanceMm" (0..50, default 10) with at most
    // "bodyLeanMaxDeg" (0..30, default 12) of upper-body lean.
    CollisionBody* cb = size_t(c) < clearance_.size() ? &clearance_[size_t(c)].collision : nullptr;
    if (const auto bc = ap->find("bodyClearance"); bc != ap->end()) {
      if (!bc->is_boolean()) return fail("action 'collision': bodyClearance must be true or false");
      if (cb) cb->bodyClearance = bc->get<bool>();
    }
    if (const auto bm = ap->find("bodyClearanceMm"); bm != ap->end()) {
      if (!bm->is_number() || !(bm->get<float>() >= 0 && bm->get<float>() <= 50))
        return fail("action 'collision': bodyClearanceMm must be a number in [0, 50]");
      if (cb) cb->bodyClearanceGap = bm->get<float>() / 1000;
    }
    if (const auto bl = ap->find("bodyLeanMaxDeg"); bl != ap->end()) {
      if (!bl->is_number() || !(bl->get<float>() >= 0 && bl->get<float>() <= 30))
        return fail("action 'collision': bodyLeanMaxDeg must be a number in [0, 30]");
      if (cb) cb->bodyLeanMax = glm::radians(bl->get<float>());
    }
  }
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
  // --- Animation principles (T-061, anim/principles.h): measurements for clip-layer blends and IK weight ramps. ---
  // Poses are measured with the automatic base idle present (as at playback), whether or not it is prepared yet, so
  // a first load and a recompile plan the same blends; nothing else the actions plan sees it.
  auto measured = [&](auto&& fn) {
    if (!autoIdle_.empty()) return fn();
    const auto savedWarnings = warnings_;
    prepareAutoIdle();
    auto r = fn();
    autoIdle_.clear();
    warnings_ = savedWarnings;
    return r;
  };
  auto globalsWith = [&](size_t c, const ClipLayer* extra, double f) {
    if (extra) clipLayers_[c].push_back(*extra);
    auto g = kinematicGlobals(c, f, nullptr);
    if (extra) clipLayers_[c].pop_back();
    return g;
  };
  auto rotDeg = [](const mat4& a, const mat4& b) {
    const quat qa = glm::normalize(glm::quat_cast(mat3(a))), qb = glm::normalize(glm::quat_cast(mat3(b)));
    return glm::degrees(2.0f * std::acos(std::min(1.0f, std::abs(glm::dot(qa, qb)))));
  };
  auto isFinger = [](const std::string& r) { return successionRank(r) == 4; };
  auto layerInMask = [](const ClipLayer& L, const std::string& role) {
    const std::string r = L.mirror ? mirrorRole(*L.clip, role) : role;
    return std::find(L.clip->mask.begin(), L.clip->mask.end(), r) != L.clip->mask.end();
  };
  // Largest global rotation change of a driven (non-finger) bone between the pose without the layer and with it at
  // full weight, at frame f: the amplitude a blend at f has to cover.
  auto blendAmplitude = [&](size_t c, const ClipLayer& L, double f) {
    ClipLayer full = L;
    full.principles = false;
    full.blendIn = full.blendOut = 0;
    const auto g0 = globalsWith(c, nullptr, f), g1 = globalsWith(c, &full, f);
    float a = 0;
    for (const auto& r : L.binding.roles)
      if (r.bone >= 0 && !isFinger(r.name) && layerInMask(L, r.name)) a = std::max(a, rotDeg(g0[size_t(r.bone)], g1[size_t(r.bone)]));
    return double(a);
  };
  auto wristPath = [&](size_t c, const ClipLayer& L, int hand, double f0, double f1) {
    std::vector<vec3> path;
    clipLayers_[c].push_back(L);
    for (double f = std::floor(f0); f <= std::ceil(f1); f += 1) path.push_back(vec3(kinematicGlobals(c, f, nullptr)[size_t(hand)][3]));
    clipLayers_[c].pop_back();
    return path;
  };
  // Clip action blends: minimum lengths from the amplitude, then elbow breakdowns where the wrist path of a blend
  // would be near-linear (bisection on the breakdown angle until the path deviates minArc from its chord).
  auto planClipBlends = [&](size_t c, ClipLayer& L, bool explicitEnd, bool movingIn, bool movingOut) {
    const double fps = scene_.rate.fps();
    measured([&] {
      const bool finite = L.end < 1e29;
      const double inMin = L.blendIn > 0 ? minBlendFrames(blendAmplitude(c, L, L.start), fps, principles_) : 0.0;
      const double outMin = L.blendOut > 0 && finite ? minBlendFrames(blendAmplitude(c, L, L.end), fps, principles_) : 0.0;
      double in = std::max(L.blendIn, inMin), out = std::max(L.blendOut, outMin);
      // The lengthened blends take at most half of a finite layer (never less than authored), so a short clip keeps
      // a part at full weight.
      if (const double room = std::max(L.blendIn + L.blendOut, 0.5 * (L.end - L.start)); finite && in + out > room) {
        const double extra = in + out - (L.blendIn + L.blendOut), allowed = room - (L.blendIn + L.blendOut);
        const double k = extra > 0 ? std::max(0.0, allowed) / extra : 0.0;
        in = L.blendIn + (in - L.blendIn) * k;
        out = L.blendOut + (out - L.blendOut) * k;
      }
      L.blendIn = in;
      L.blendOut = out;
      // Eased clock (clip_layers.cpp) at the ends where the clip is moving; the layer keeps its length, so its middle
      // plays faster by length / (length - ramps / 2): only where that stays <= 1.25 (ramps <= 40 % of the layer).
      L.clockIn = movingIn ? in : 0.0;
      L.clockOut = movingOut && finite && !explicitEnd ? out : 0.0;
      if (finite && L.clockIn + L.clockOut > 0.4 * (L.end - L.start)) L.clockIn = L.clockOut = 0.0;
      for (int s = 0; s < 2; ++s) {
        const std::string side = s == 0 ? ".L" : ".R";
        auto roleBone = [&](const std::string& role) {
          auto it = L.binding.roleIndex.find(role);
          return it == L.binding.roleIndex.end() ? -1 : L.binding.roles[size_t(it->second)].bone;
        };
        const int hand = roleBone("hand" + side);
        if (hand < 0 || roleBone("forearm" + side) < 0 || !layerInMask(L, "forearm" + side)) continue;
        for (int phase = 0; phase < 2; ++phase) {
          const double len = phase == 0 ? L.blendIn : L.blendOut;
          if (len < 2 || (phase == 1 && !finite)) continue;
          const double tail = 4 * L.succession;  // the ranks' offsets (succession)
          const double f0 = phase == 0 ? L.start : L.end - len, f1 = phase == 0 ? L.start + len + tail : L.end + tail;
          float* slot = phase == 0 ? &L.breakIn[s] : &L.breakOut[s];
          auto arcWith = [&](float deg, float* chord) {
            ClipLayer T = L;
            (phase == 0 ? T.breakIn : T.breakOut)[s] = deg;
            return arcDeviation(wristPath(c, T, hand, f0, f1), chord);
          };
          float chord = 0;
          const float arc0 = arcWith(0, &chord);
          if (chord < principles_.breakdownMinChordM || arc0 >= principles_.minArc) continue;
          // the direction (open or bend the elbow) that curves the path more; then the smallest angle reaching minArc
          const float maxDeg = float(principles_.breakdownMaxDeg);
          const float aOpen = arcWith(maxDeg, nullptr), aBend = arcWith(-maxDeg, nullptr);
          const float sign = aOpen >= aBend ? 1.0f : -1.0f, best = std::max(aOpen, aBend);
          if (best <= arc0 + 1e-4f) continue;  // neither helps: leave the blend as it is
          if (best < principles_.minArc) {
            *slot = sign * maxDeg;
            continue;
          }
          float lo = 0, hi = maxDeg;
          for (int it = 0; it < 7; ++it) {
            const float mid = 0.5f * (lo + hi);
            (arcWith(sign * mid, nullptr) >= principles_.minArc ? hi : lo) = mid;
          }
          *slot = sign * hi;
        }
      }
      return 0;
    });
  };
  // IK gesture weight ramps (touch, reach): quintic ease, at least as long as the arm's rotation needs (the ramp in
  // starts earlier when the authored one is too short, never before the hand's previous IK keys), and the elbow
  // trailing the shoulder by ikElbowLagSec (".lag"), both reaching full weight / zero at the authored frames.
  // in: weight 0 -> 1, reaching 1 at `full`; out: 1 -> 0 from `from` to `zero`.
  auto easedKeys = [&](const std::string& track, double f0, double f1, float v0, float v1) {
    const int n = std::max(1, int(std::ceil(f1 - f0)));
    for (int k = 0; k <= n; ++k) {
      const double x = double(k) / n;
      key(*gen, track, f0 + (f1 - f0) * x, vec3(v0 + (v1 - v0) * float(easeInOut(x))), Interp::Linear);
    }
  };
  auto ikRamps = [&](size_t c, char side, const std::string& ik, double inStart, double full, double outStart, double zero) {
    const double fps = scene_.rate.fps(), lag = principles_.ikElbowLagSec * fps;
    const int upper = characters_[c].asset.skeleton.find(std::string("upperArm.") + side);
    const int fore = characters_[c].asset.skeleton.find(std::string("forearm.") + side);
    const int handB = characters_[c].asset.skeleton.find(std::string("hand.") + side);
    Track& w = gen->tracks[ik + ".weight"];
    const double prevKey = w.keys.empty() ? -1e30 : w.keys.back().frame;
    w.keys.erase(std::remove_if(w.keys.begin(), w.keys.end(), [&](const Key& k) { return k.frame >= inStart - 1e-9 && k.frame <= zero + 1e-9; }), w.keys.end());
    // In: the shoulder leads and the elbow trails by `lag` (weight track shifted). Out: the elbow opens first and the
    // shoulder follows (the ".lag" key turns negative), so the hand swings back round the shoulder instead of
    // dropping straight down; both end at the authored frames.
    double inEnd = full - lag, outBegin = outStart + lag;
    if (inEnd <= inStart + 1) inEnd = full;  // no room for the lag
    if (outBegin >= zero - 1) outBegin = outStart;
    const double outEnd = zero;
    // amplitude: arm rotation between the pose without the IK and with it (measured with plain ramps first)
    easedKeys(ik + ".weight", inStart, inEnd, 0, 1);
    easedKeys(ik + ".weight", outBegin, outEnd, 1, 0);
    const auto [ampIn, ampOut] = measured([&] {
      const auto a = kinematicGlobals(c, inStart, nullptr), b = kinematicGlobals(c, full, nullptr);
      const auto d = kinematicGlobals(c, zero, nullptr), e = kinematicGlobals(c, outStart, nullptr);
      double ai = 0, ao = 0;
      for (int bone : {upper, fore, handB})
        if (bone >= 0) {
          ai = std::max(ai, double(rotDeg(a[size_t(bone)], b[size_t(bone)])));
          ao = std::max(ao, double(rotDeg(d[size_t(bone)], e[size_t(bone)])));
        }
      return std::pair<double, double>(ai, ao);
    });
    const double needIn = minBlendFrames(ampIn, fps, principles_), needOut = minBlendFrames(ampOut, fps, principles_);
    if (inEnd - inStart < needIn) {  // start earlier (the contact frame is the authored constraint)
      // at most 50 % earlier than authored: the gesture's timing stays the author's
      const double earliest = std::max({prevKey + 1, double(scene_.frameStart), inEnd - needIn, inStart - 0.5 * (inEnd - inStart)});
      if (earliest < inStart) {
        w.keys.erase(std::remove_if(w.keys.begin(), w.keys.end(), [&](const Key& k) { return k.frame >= inStart - 1e-9 && k.frame <= inEnd + 1e-9; }), w.keys.end());
        inStart = earliest;
        easedKeys(ik + ".weight", inStart, inEnd, 0, 1);
      }
    }
    (void)needOut;  // the ramp out keeps its authored frames: the next action may own the arm right after `zero`
    if (lag > 0) {
      key(*gen, ik + ".lag", inStart, vec3(float(lag)), Interp::Step);
      key(*gen, ik + ".lag", outStart, vec3(float(outBegin > outStart ? -lag : 0.0)), Interp::Step);
    }
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
    std::shared_ptr<const SampledLayerCurves> curve = nullptr;  // blended emotions (T-097A): the state's weight instead
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
  struct BlendedEmotion {  // emotion actions with "blend" (T-097A): played from a continuous state per character
    int character;
    std::string key;  // state name: the library name, with "/variant" for a variant
    EmotionDef def;
    double start, end;  // scene frames (end < 0: rise + hold)
    float intensity;
    PersonalityModulation mod;
    double rise, decay, hold;  // seconds, modulated
    bool keep;                 // true: plays on top, false: fades the character's other blended emotions out
    float pleasantness, energy;
  };
  std::vector<BlendedEmotion> blended;

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

    if (type == "collision") continue;  // read above

    if (type == "look") {
      faceTimelines_[size_t(c)].lookStarts.push_back(start);  // a gaze shift: brows lift a little, maybe a blink
      if (start > scene_.frameStart + 2)  // the look a shot opens with is the starting state, not a new focus
        faceTimelines_[size_t(c)].attention.push_back({start, faceLibrary_.neutral.lookAttention});
      const std::string track = prefix + "lookAt";
      const int o = has(a, "object") ? objIndex(str(a, "object")) : -1;
      if (has(a, "object") && o < 0) return fail(std::format("look: unknown object '{}'", str(a, "object")));
      // "atCharacter" (T-097D): another character's face (its head bone, as the director frames it).
      const int oc = has(a, "atCharacter") ? charIndex(str(a, "atCharacter")) : -1;
      if (has(a, "atCharacter") && oc < 0) return fail(std::format("look: unknown character '{}'", str(a, "atCharacter")));
      const int ocHead = oc >= 0 ? characters_[size_t(oc)].asset.skeleton.find("head") : -1;
      // "atProp" (T-112a): a prop's middle (the centre of its primitive mesh or collision proxy), as it moves.
      int op = -1;
      if (has(a, "atProp")) {
        for (size_t p = 0; p < scene_.props.size(); ++p)
          if (scene_.props[p].name == str(a, "atProp")) op = int(p);
        if (op < 0) return fail(std::format("look: unknown prop '{}'", str(a, "atProp")));
      }
      vec3 propMiddle(0);
      if (op >= 0 && size_t(op) < propAssets_.size()) {
        const PropAsset& pa = propAssets_[size_t(op)];
        if (pa.mesh.kind == AssetMeshSource::Kind::Primitive) {
          if (pa.mesh.primitive == AssetMeshSource::Primitive::Cylinder) propMiddle = vec3(0, 0.5f * pa.mesh.height * pa.scaleMetres, 0);
        } else if (pa.collision) {
          propMiddle = pa.collision->transform.translation;
        }
      }
      auto target = [&](double f) {
        if (op >= 0) return vec3(propWorld(size_t(op), f) * vec4(propMiddle, 1));
        if (o >= 0) return objPos(o, f);
        if (oc >= 0) {
          if (ocHead < 0) return scene_.characters[size_t(oc)].position + vec3(0, 0.6f, 0);
          return vec3(characterGlobals(size_t(oc), f)[size_t(ocHead)] * vec4(0, 0.11f, 0.09f, 1));
        }
        if (num(a, "camera", 0) != 0 || (a.contains("camera") && a["camera"].is_boolean() && a["camera"].get<bool>()))
          return clip.evaluate("camera.position", f, scene_.camera.position);
        return vec(a, "target", vec3(0, 0.6f, 3));
      };
      const bool hadGaze = clip.find(track) != nullptr;
      vec3 prev = clip.evaluate(track, start, target(start));
      dropKeysAfter(*gen, track, start);
      key(*gen, track, start, prev, Interp::Linear);
      const double end = num(a, "end", start + 3);
      for (double f = start + 3; f <= std::max(start + 3, end); f += 3) key(*gen, track, f, target(f), Interp::Linear);
      // Gaze weight (T-097D): only generated reaction looks key it ("back" below); a later look restores full weight.
      const std::string wtrack = track + ".weight";
      constexpr double kGazeTurn = 12;  // frames a generated gaze takes to turn in / out
      const bool back = a.value("back", false);
      const float w0 = hadGaze ? std::min(1.f, clip.evaluate(wtrack, start, vec3(1)).x) : 0.f;
      if (back || gen->tracks.count(wtrack)) {
        if (w0 < 1.f || back) {
          dropKeysAfter(*gen, wtrack, start);
          key(*gen, wtrack, start, vec3(w0));  // smooth: the head turns in as an authored look's lagged gaze does
          key(*gen, wtrack, start + kGazeTurn, vec3(1));
        }
      }
      // "back" (T-097D): over kGazeTurn frames after the look's end the gaze returns to where it was before (without an
      // earlier gaze, or one already released: the gaze is released again, its weight back to what it was).
      if (back) {
        const double last = start + 3 + 3 * std::floor((std::max(start + 3, end) - (start + 3)) / 3);
        key(*gen, wtrack, std::max(last, start + kGazeTurn), vec3(1));
        key(*gen, wtrack, std::max(last, start + kGazeTurn) + kGazeTurn, vec3(w0));
        if (w0 > 0.f) key(*gen, track, last + kGazeTurn, prev, Interp::Linear);
      }
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
      if (principles_.enabled) {
        ikRamps(size_t(c), side, ik, start, contact, release, end);
      } else {
        key(*gen, ik + ".weight", start, vec3(0));
        key(*gen, ik + ".weight", contact - 5, vec3(0.9f));
        key(*gen, ik + ".weight", contact, vec3(1));
        key(*gen, ik + ".weight", release, vec3(1));
        key(*gen, ik + ".weight", end, vec3(0));
      }
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
      if (principles_.enabled) {
        ikRamps(size_t(c), side, ik, start, contact - 6, contact + 10, end);
      } else {
        key(*gen, ik + ".weight", start, vec3(0));
        key(*gen, ik + ".weight", contact - 6, vec3(1));
        key(*gen, ik + ".weight", contact + 10, vec3(1));
        key(*gen, ik + ".weight", end, vec3(0));
      }
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
      if (principles_.enabled && !L.base) {  // T-061: eased, successive blends; ease-preserving retiming; breakdowns
        L.principles = true;
        L.succession = principles_.successionSec * scene_.rate.fps();
        // Motion of the clip per clip frame (driven non-finger roles, degrees): retiming and the eased clock use it.
        std::vector<double> motion;
        if (L.clip->frameCount > 2) {
          const int n = L.clip->loop ? L.clip->frameCount : L.clip->frameCount - 1;
          motion.assign(size_t(n), 0.0);
          ClipSample prev = sampleClip(*L.clip, 0);
          for (int k = 0; k < n; ++k) {
            ClipSample next = sampleClip(*L.clip, double((k + 1) % L.clip->frameCount));
            for (const auto& [role, q] : next.local) {
              if (isFinger(role) || std::find(L.clip->mask.begin(), L.clip->mask.end(), role) == L.clip->mask.end()) continue;
              auto p0 = prev.local.find(role);
              if (p0 != prev.local.end())
                motion[size_t(k)] += glm::degrees(2.0 * std::acos(std::min(1.0, double(std::abs(glm::dot(p0->second, q))))));
            }
            prev = std::move(next);
          }
        }
        if (principles_.easePreservingRetime && std::abs(L.speed - 1.0) > 1e-9 && !motion.empty())
          L.warp = std::make_shared<const TimeWarp>(TimeWarp::easePreserving(motion, L.speed, L.clip->fps, scene_.rate.fps(), principles_));
        // A clip "moves" at an end when its motion over the first / last 3 frames averages > 15 % of its peak.
        bool movingIn = false, movingOut = false;
        if (motion.size() >= 6) {
          const double peak = *std::max_element(motion.begin(), motion.end());
          const size_t n = motion.size();
          movingIn = (motion[0] + motion[1] + motion[2]) / 3 > 0.15 * peak;
          movingOut = !L.clip->loop && (motion[n - 1] + motion[n - 2] + motion[n - 3]) / 3 > 0.15 * peak;
        }
        planClipBlends(size_t(c), L, has(a, "end") || L.clip->loop, movingIn, movingOut);
      }
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
      if (const Json bl = a.value("blend", Json()); !bl.is_null() && !(bl.is_boolean() && !bl.get<bool>())) {
        // Blended play (T-097A): compiled after all actions, from the character's continuous emotion state.
        if (!bl.is_boolean() && !bl.is_object()) return fail(std::format("emotion '{}': 'blend' must be true or an object", full));
        const Json bo = bl.is_object() ? bl : Json::object();
        auto mod = modulationFromJson(a.value("modulation", Json()));
        if (!mod) return fail(std::format("emotion '{}': {}", full, mod.error().message));
        const double rise = num(bo, "rise", e->rise >= 0 ? e->rise : e->onset);
        const double decay = num(bo, "decay", e->decay >= 0 ? e->decay : e->release);
        if (rise < 0 || decay < 0) return fail(std::format("emotion '{}': negative rise or decay", full));
        const EmotionTiming tm = modulatedTiming(rise, e->hold, decay, float(std::clamp(num(a, "intensity", 1.0), 0.0, 1.0)), *mod);
        const Json af = a.value("affect", Json::object());
        BlendedEmotion b{c, full, *e, start, has(a, "end") ? num(a, "end", 0) : -1.0, tm.intensity, *mod, tm.rise, tm.decay,
                         tm.hold, bo.value("keep", false),
                         std::clamp(float(num(af, "pleasantness", e->pleasantness)), -1.f, 1.f),
                         std::clamp(float(num(af, "energy", e->energy)), -1.f, 1.f)};
        if (b.end >= 0 && b.end <= start) return fail("emotion: end must be after start");
        blended.push_back(std::move(b));
        beats.push_back({Beat::Kind::Expression, c, -1, start, start, 0, 0, 0,
                         has(a, "end") ? num(a, "end", 0) : start + (tm.rise + tm.hold + tm.decay) * scene_.rate.fps(), vec3(0), vec3(0)});
        continue;
      }
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
  // Blended emotions (T-097A, docs/EMOTIONS.md section 3b): per character, one continuous state (EmotionBlender) fed
  // by the blended emotion actions in time order; face, faceMotion (gaze), posture weights and clip tempo all read it.
  auto compileBlended = [&]() -> Result<void> {
    const double fps = scene_.rate.fps();
    const int f0 = scene_.frameStart - 1, f1 = scene_.frameEnd + 1;
    const size_t frames = size_t(f1 - f0 + 1);
    std::vector<int> chars;
    for (const auto& b : blended)
      if (std::find(chars.begin(), chars.end(), b.character) == chars.end()) chars.push_back(b.character);
    for (int c : chars) {
      const std::string who = scene_.characters[size_t(c)].name;
      const CharacterAsset& asset = characters_[size_t(c)].asset;
      std::vector<const BlendedEmotion*> list;
      for (const auto& b : blended)
        if (b.character == c) list.push_back(&b);
      std::stable_sort(list.begin(), list.end(), [](const BlendedEmotion* x, const BlendedEmotion* y) { return x->start < y->start; });
      // Events in time order: each action starts (rise to its intensity) and releases (decay to 0) after its hold, or
      // `decay` before its explicit end. A release is skipped once something else re-targeted that emotion.
      struct Event {
        double t;
        int kind;  // 0 start, 1 release
        const BlendedEmotion* b;
      };
      std::vector<Event> events;
      for (const BlendedEmotion* b : list) {
        const double t = b->start / fps;
        events.push_back({t, 0, b});
        events.push_back({std::max(t, b->end >= 0 ? b->end / fps - b->decay : t + b->rise + b->hold), 1, b});
      }
      std::stable_sort(events.begin(), events.end(), [](const Event& x, const Event& y) { return x.t < y.t; });
      EmotionBlender B;
      std::map<std::string, float> target;
      std::map<std::string, const BlendedEmotion*> latest;  // key -> the action that last set it
      std::map<std::string, std::pair<float, float>> affect;
      auto retargetAffect = [&](double t, double rise, double decay) {
        std::vector<std::pair<std::string, float>> w(target.begin(), target.end());
        const auto [p, e] = impliedAffect(w, affect);
        B.retargetAffect(t, p, e, rise, decay);
      };
      for (const Event& ev : events) {
        const BlendedEmotion& b = *ev.b;
        if (ev.kind == 0) {
          if (!b.keep)
            for (auto& [k, w] : target)
              if (k != b.key && w > 0) {
                B.retargetEmotion(ev.t, k, 0.f, latest[k]->rise, latest[k]->decay);
                w = 0;
              }
          B.retargetEmotion(ev.t, b.key, b.intensity, b.rise, b.decay);
          target[b.key] = b.intensity;
          latest[b.key] = &b;
          affect[b.key] = {b.pleasantness, b.energy};
          retargetAffect(ev.t, b.rise, b.decay);
        } else {
          const EmotionChannel* ch = B.channel(b.key);
          if (!ch || ch->lastRetarget() > b.start / fps + 1e-9) continue;
          B.retargetEmotion(ev.t, b.key, 0.f, b.rise, b.decay);
          target[b.key] = 0;
          retargetAffect(ev.t, b.rise, b.decay);
        }
      }
      // Sample the state per scene frame.
      const std::vector<std::string>& keys = B.names();
      std::vector<std::vector<float>> w(keys.size(), std::vector<float>(frames, 0.f));
      std::vector<float> energy(frames, 0.f);
      for (size_t k = 0; k < frames; ++k) {
        const EmotionState st = B.evaluate(double(f0 + int(k)) / fps);
        for (size_t i = 0; i < keys.size(); ++i) w[i][k] = st.weights[i].second;
        energy[k] = st.energy;
      }
      std::vector<std::string> morphNames;
      for (auto& mt : characters_[size_t(c)].rig.morphs) morphNames.push_back(mt.name);
      double firstStart = 1e30;
      for (const BlendedEmotion* b : list) firstStart = std::min(firstStart, b->start);
      std::vector<size_t> postureKeys;
      std::vector<ClipLayer> postures;
      std::vector<std::shared_ptr<SampledLayerCurves>> postureCurves;
      for (size_t i = 0; i < keys.size(); ++i) {
        const BlendedEmotion& b = *latest.at(keys[i]);
        const EmotionDef& e = b.def;
        auto curve = std::make_shared<SampledLayerCurves>();
        curve->start = f0;
        curve->weight = w[i];
        // Face: the emotion's mix x its state weight (missing morphs: one warning, as for plain emotions).
        for (const auto& [ename2, fw] : e.face) {
          const std::string morph = resolveExpression(asset, ename2, morphNames);
          if (morph.empty()) {
            if (missingFace.insert(who + "|" + keys[i] + "|" + ename2).second)
              warnings_.push_back(std::format("emotion '{}': character '{}' has no morph for expression '{}' (face part skipped, body plays)", keys[i], who, ename2));
            continue;
          }
          emotionFace.push_back({c, morph, ClipLayer{}, fw, curve});
        }
        // Living face and gaze: the faceMotion section x the state weight; gazeShift removes the averted-gaze bias;
        // attention pulses at every start of the emotion.
        if (e.hasFaceMotion) {
          FaceMotion m = e.faceMotion;
          if (m.gazeBiasDeg) m.gazeBiasDeg = *m.gazeBiasDeg * (1.f - b.mod.gazeShift);
          const std::optional<float> att = m.attention;
          m.attention.reset();
          FaceEnvelope env{-1e30, 1e30, 0, 0, 1, false};
          env.curve = std::make_shared<const std::vector<float>>(w[i]);
          env.curveStart = f0;
          faceTimelines_[size_t(c)].emotions.push_back({env, m});
          if (att && *att > 0)
            for (const BlendedEmotion* x : list)
              if (x->key == keys[i]) faceTimelines_[size_t(c)].attention.push_back({x->start, *att * x->intensity});
        }
        // Posture: one layer per emotion over the whole range; its weight and clock come from the state.
        if (!e.bodyClip.empty()) {
          const auto cf = findLibrary("clips", e.bodyClip + ".clip.json");
          if (cf.empty()) return fail(std::format("emotion '{}': clip '{}' not found in content/clips", keys[i], e.bodyClip));
          auto cl = cachedClip(cf);
          if (!cl) return std::unexpected(cl.error());
          ClipLayer L;
          L.clip = *cl;
          const bool loop = e.bodyLoop < 0 ? L.clip->loop : e.bodyLoop == 1;
          if (loop != L.clip->loop || !e.bodyMask.empty()) {
            auto copy = std::make_shared<ClipData>(*L.clip);
            copy->loop = loop;
            if (!e.bodyMask.empty()) copy->mask = e.bodyMask;
            L.clip = copy;
          }
          L.tier = 1;
          L.start = firstStart;  // all blended postures share a start: they apply in state order, below later gestures
          L.end = f1;
          L.blendIn = L.blendOut = 0;
          L.weight = 1;
          L.binding = bindClip(asset.skeleton, L.clip->reference, retargetData(size_t(c), L.clip->reference));
          for (const auto& r : L.binding.roles)
            if (r.bone < 0 && L.clip->tracks.count(r.name) && r.name.rfind("eye.", 0) != 0)
              warnings_.push_back(std::format("emotion '{}' clip '{}': character '{}' has no role '{}' (not played)", keys[i], L.clip->name, who, r.name));
          auto pc = std::make_shared<SampledLayerCurves>();
          pc->start = f0;
          pc->weight.assign(frames, 0.f);
          pc->clock.assign(frames, 0.0);
          const double rate = L.clip->fps / fps;  // clip frames per scene frame at tempo 1
          for (size_t k = 1; k < frames; ++k) {
            const double tempo = 0.5 * (emotionTempo(energy[k - 1], b.mod) + emotionTempo(energy[k], b.mod));
            pc->clock[k] = pc->clock[k - 1] + (double(f0) + double(k) > firstStart ? tempo * rate : 0.0);
          }
          L.sampled = pc;
          postureCurves.push_back(pc);
          postureKeys.push_back(i);
          postures.push_back(std::move(L));
        }
        // Gesture of each action of this emotion: one-shot at its offset (x tempoScale), clock at the state's tempo then.
        for (const BlendedEmotion* x : list) {
          if (x->key != keys[i] || !x->def.hasGesture) continue;
          const auto& g = x->def.gesture;
          const auto gf = findLibrary("clips", g.clip + ".clip.json");
          if (gf.empty()) return fail(std::format("emotion '{}': clip '{}' not found in content/clips", keys[i], g.clip));
          auto gl = cachedClip(gf);
          if (!gl) return std::unexpected(gl.error());
          ClipLayer G;
          G.clip = *gl;
          G.tier = 1;
          G.start = x->start + g.offset * x->mod.tempoScale * fps;
          const size_t gk = size_t(std::clamp(G.start - f0, 0.0, double(frames - 1)));
          G.speed = emotionTempo(energy[gk], x->mod);
          G.end = G.start + G.clip->duration() * fps / G.speed;
          G.blendIn = g.blendIn * x->mod.tempoScale * fps;
          G.blendOut = g.blendOut * x->mod.tempoScale * fps;
          G.weight = x->intensity;
          G.linear = x->def.linear;
          G.mirror = g.mirror;
          G.binding = bindClip(asset.skeleton, G.clip->reference, retargetData(size_t(c), G.clip->reference));
          for (const auto& [ename2, fw] : g.face) {
            const std::string morph = resolveExpression(asset, ename2, morphNames);
            if (!morph.empty()) emotionFace.push_back({c, morph, G, fw});
          }
          clipLayers_[size_t(c)].push_back(std::move(G));
        }
      }
      // Posture weights: the state weights as sequential override weights, so the layers give the normalized blend
      // (1 - S) x underlying pose + sum w_i x posture_i, whatever the order.
      for (size_t k = 0; k < frames; ++k) {
        std::vector<float> ws;
        for (size_t p : postureKeys) ws.push_back(w[p][k]);
        const std::vector<float> ow = overrideWeights(ws);
        for (size_t p = 0; p < postureCurves.size(); ++p) postureCurves[p]->weight[k] = ow[p];
      }
      for (auto& L : postures) clipLayers_[size_t(c)].push_back(std::move(L));
      sortLayers(c);
    }
    return {};
  };
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
  if (auto r = compileBlended(); !r) return r;
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
      for (const FaceContribution* fc : list)
        v += (fc->curve ? fc->curve->weightAt(f) : fc->envelope.envelope(f)) * fc->weight;
      keys.push_back({double(f), vec3(float(std::clamp(v, 0.0, 1.0))), Interp::Linear});
    }
    gen->tracks[track].keys = std::move(keys);
  }
  if (auto r = finishInteractions(*gen, interactions); !r) return r;
  if (verbs) {  // T-112a: the verbs' constraints on the compiled motion (read only); under a verb they are errors
    auto ci = [&](const std::string& n) {
      for (size_t c = 0; c < scene_.characters.size(); ++c)
        if (scene_.characters[c].name == n) return c;
      return size_t(0);
    };
    auto pi = [&](const std::string& n) {
      for (size_t p = 0; p < scene_.props.size(); ++p)
        if (scene_.props[p].name == n) return p;
      return size_t(0);
    };
    auto chain = [&](const std::string& who, char side) {  // hand, forearm, upper arm bones
      const int hb = characterSocketBone(ci(who), std::string("hand.") + side);
      const auto& B = characters_[ci(who)].asset.skeleton.bones;
      const int mb = hb >= 0 ? B[size_t(hb)].parent : -1;
      return std::array<int, 3>{hb, mb, mb >= 0 ? B[size_t(mb)].parent : -1};
    };
    VerbGeometry g;
    g.shoulder = [&](const std::string& who, char side, double f) {
      const int rb = chain(who, side)[2];
      return rb < 0 ? vec3(0) : vec3(characterGlobals(ci(who), f)[size_t(rb)][3]);
    };
    g.wristTarget = [&](const std::string& who, char side, double f) {
      const int hb = chain(who, side)[0];
      if (hb < 0) return vec3(0);
      return scene_.animation.evaluate(who + "/ik." + characters_[ci(who)].asset.skeleton.bones[size_t(hb)].name, f, vec3(0));
    };
    g.armLength = [&](const std::string& who, char side) {
      const auto k = chain(who, side);
      if (k[2] < 0) return 0.0f;
      const auto& B = characters_[ci(who)].asset.skeleton.bones;
      return glm::distance(B[size_t(k[2])].head, B[size_t(k[1])].head) + glm::distance(B[size_t(k[1])].head, B[size_t(k[0])].head);
    };
    g.palm = [&](const std::string& who, char side, double f) { return handGripPoint(ci(who), side, f); };
    g.propWorld = [&](const std::string& prop, double f) { return propWorld(pi(prop), f); };
    g.asset = [&](const std::string& prop) -> const PropAsset* { return pi(prop) < propAssets_.size() ? &propAssets_[pi(prop)] : nullptr; };
    g.armGap = [&](const std::string& who, char side, double f) { return armClearanceAt(ci(who), side, f).gap; };
    g.ikWeight = [&](const std::string& who, char side, double f) {
      const int hb = chain(who, side)[0];
      return hb < 0 ? 0.0f : scene_.animation.evaluate(who + "/ik." + characters_[ci(who)].asset.skeleton.bones[size_t(hb)].name + ".weight", f, vec3(0)).x;
    };
    if (auto errors = checkVerbConstraints(*verbs, g); !errors.empty()) return fail(errors.front().message());
  }
  if (scene_.director.is_object()) {
    std::vector<PropBox> propBoxes;
    for (size_t p = 0; p < scene_.props.size(); ++p) {
      PropBox b{vec3(-0.05f), vec3(0.05f)};  // a mesh prop without a collision proxy: 5 cm around its origin
      if (p < propAssets_.size()) {
        const PropAsset& pa = propAssets_[p];
        const float s = pa.scaleMetres;
        if (pa.mesh.kind == AssetMeshSource::Kind::Primitive) {
          if (pa.mesh.primitive == AssetMeshSource::Primitive::Cylinder)
            b = {vec3(-pa.mesh.radius, 0, -pa.mesh.radius) * s, vec3(pa.mesh.radius, pa.mesh.height, pa.mesh.radius) * s};
          else if (pa.mesh.primitive == AssetMeshSource::Primitive::Sphere) b = {vec3(-pa.mesh.radius * s), vec3(pa.mesh.radius * s)};
          else b = {-0.5f * pa.mesh.size * s, 0.5f * pa.mesh.size * s};
        } else if (pa.collision) {
          b = {pa.collision->transform.translation - vec3(0.05f), pa.collision->transform.translation + vec3(0.05f)};
        }
      }
      propBoxes.push_back(b);
    }
    planShots(*this, *gen, beats, propBoxes);
  }
  return {};
}

}  // namespace plush
