// T-096 evidence: head-to-head clearance, palm-to-socket drift while a prop is held, and how much of a held prop the
// shot camera sees. Not part of the build:
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-096/measure_t096.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/measure_t096
//   build/measure_t096 <resolved scene.json> [--interaction '<json>'] [--frames A-B] [--vis f1,f2,...] [--prop cup] [--asset <asset.json>]
// (run from the repository root; --interaction replaces the scene's T-096 "interaction" switch block, so one
// resolved scene measures before and after).
//
// head: per frame, the smallest distance between two characters' head-carried skinned vertices (every mesh: skin,
//   hair, ears, eyes, glasses; >= 50 % of the weight on the head bone or its descendants), posed exactly as the
//   engine poses them (poseCharacter, linear blend). Penetrating surfaces read as a small distance, so the head
//   volumes' signed gap (scene/collision.h, the planner's own measure) is reported next to it.
// drift: how far the palm contact point moves on the prop (in the prop's frame, from where it was at the contact),
//   every half frame of each hold (grasp contact -> hand-over release or the shot end; hand-over contact -> the shot
//   end). grip_azimuth_deg: where the palm holds the prop around its axis (prop frame, 0 = +x, 90 = -z).
// visible: the prop's camera-facing outer wall and rim (cylinder primitive of the asset), sampled; a sample is
//   visible when the ray from the camera reaches it without crossing any character triangle and it is in frame.
#include <cstdio>
#include <fstream>
#include <iostream>
#include <unordered_map>

#include "anim/animation.h"
#include "scene/asset_library.h"
#include "scene/collision.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

namespace {
std::vector<vec3> headPoints(const SceneEvaluator& ev, size_t c, double f, std::vector<std::vector<int>>& sel) {
  const auto& ci = ev.characters()[c];
  const Skeleton& sk = ci.asset.skeleton;
  Pose pose;
  const std::vector<mat4> G = ev.characterGlobals(c, f, &pose);
  std::vector<mat4> skin(G.size());
  for (size_t b = 0; b < G.size(); ++b) skin[b] = G[b] * glm::translate(mat4(1), -sk.bones[b].head);
  if (sel.empty()) {
    const int head = sk.find("head");
    std::vector<char> underHead(sk.bones.size(), 0);
    for (size_t b = 0; b < sk.bones.size(); ++b)
      for (int k = int(b); k >= 0; k = sk.bones[size_t(k)].parent)
        if (k == head) underHead[b] = 1;
    sel.resize(ci.rig.meshes.size());
    for (size_t m = 0; m < ci.rig.meshes.size(); ++m) {
      const SkinnedMesh& M = ci.rig.meshes[m];
      for (size_t v = 0; v < M.rest.positions.size() && v < M.weights.size(); ++v) {
        float w = 0;
        for (int k = 0; k < 4; ++k)
          if (M.joints[v][k] >= 0 && size_t(M.joints[v][k]) < underHead.size() && underHead[size_t(M.joints[v][k])]) w += M.weights[v][k];
        if (w >= 0.5f) sel[m].push_back(int(v));
      }
    }
  }
  std::vector<vec3> out;
  for (size_t m = 0; m < sel.size(); ++m) {
    const SkinnedMesh& M = ci.rig.meshes[m];
    for (int v : sel[m]) {
      vec3 p(0);
      for (int k = 0; k < 4; ++k)
        if (M.weights[size_t(v)][k] > 0) p += M.weights[size_t(v)][k] * vec3(skin[size_t(M.joints[size_t(v)][k])] * vec4(M.rest.positions[size_t(v)], 1));
      out.push_back(p);
    }
  }
  return out;
}

float cloudDistance(const std::vector<vec3>& A, const std::vector<vec3>& B, float cell = 0.06f) {
  auto key = [&](vec3 p) {
    const glm::ivec3 i = glm::ivec3(glm::floor(p / cell));
    return (long long)(i.x + 4096) * 100000000LL + (long long)(i.y + 4096) * 10000LL + (long long)(i.z + 4096);
  };
  std::unordered_map<long long, std::vector<int>> grid;
  for (size_t i = 0; i < B.size(); ++i) grid[key(B[i])].push_back(int(i));
  float best = cell;
  for (const vec3& p : A) {
    const glm::ivec3 i = glm::ivec3(glm::floor(p / cell));
    for (int dx = -1; dx <= 1; ++dx)
      for (int dy = -1; dy <= 1; ++dy)
        for (int dz = -1; dz <= 1; ++dz) {
          const vec3 q = (vec3(i + glm::ivec3(dx, dy, dz)) + 0.5f) * cell;
          auto it = grid.find(key(q));
          if (it == grid.end()) continue;
          for (int j : it->second) best = std::min(best, glm::distance(p, B[size_t(j)]));
        }
  }
  return best;  // == cell: at least `cell` apart
}

bool rayHits(vec3 o, vec3 d, float tmax, vec3 a, vec3 b, vec3 c) {
  const vec3 e1 = b - a, e2 = c - a, p = glm::cross(d, e2);
  const float det = glm::dot(e1, p);
  if (std::abs(det) < 1e-12f) return false;
  const float inv = 1.0f / det;
  const vec3 s = o - a;
  const float u = glm::dot(s, p) * inv;
  if (u < 0 || u > 1) return false;
  const vec3 q = glm::cross(s, e1);
  const float v = glm::dot(d, q) * inv;
  if (v < 0 || u + v > 1) return false;
  const float t = glm::dot(e2, q) * inv;
  return t > 1e-5f && t < tmax;
}

struct Vis {
  float fraction = 0;
  int visible = 0, facing = 0;
  std::map<std::string, int> hiddenBy;
};
Vis cupVisibility(const SceneEvaluator& ev, size_t prop, double f, float radius, float height) {
  const Camera cam = ev.cameraAt(f);
  const mat4 P = ev.propWorld(prop, f);
  const RenderSettings& rs = ev.scene().render;
  const vec3 fwd = glm::normalize(cam.target - cam.position), right = glm::normalize(glm::cross(fwd, cam.up)),
             up = glm::cross(right, fwd);
  const float halfW = 0.5f * cam.sensorWidthMm / cam.focalMm, halfH = halfW * float(rs.height) / float(rs.width);
  std::vector<std::pair<vec3, vec3>> samples;  // point, outward normal
  for (int i = 0; i < 48; ++i) {
    const float a = 6.2831853f * (float(i) + 0.5f) / 48.0f;
    const vec3 n(std::cos(a), 0, std::sin(a));
    for (int k = 0; k < 16; ++k) samples.push_back({n * radius + vec3(0, height * (float(k) + 0.5f) / 16.0f, 0), n});
    for (int k = 0; k < 2; ++k) samples.push_back({n * (radius * (0.93f + 0.05f * float(k))) + vec3(0, height, 0), vec3(0, 1, 0)});
  }
  // Occluders: every character's posed triangles near the camera -> prop line.
  struct Tri { vec3 a, b, c; std::string who; };
  std::vector<Tri> tris;
  Aabb box;
  box.expand(cam.position);
  for (const auto& s : samples) box.expand(vec3(P * vec4(s.first, 1)));
  for (size_t c = 0; c < ev.characters().size(); ++c) {
    const auto& ci = ev.characters()[c];
    Pose pose;
    const std::vector<mat4> G = ev.characterGlobals(c, f, &pose);
    std::vector<mat4> skin(G.size());
    for (size_t b = 0; b < G.size(); ++b) skin[b] = G[b] * glm::translate(mat4(1), -ci.asset.skeleton.bones[b].head);
    const PosedCharacter pc = poseCharacter(ci.rig, skin);
    for (size_t mi = 0; mi < pc.meshes.size(); ++mi)
      for (size_t t = 0, m0 = 0; t + 2 < pc.meshes[mi]->indices.size(); t += 3, (void)m0) {
        const auto& m = pc.meshes[mi];
        const vec3 a = m->positions[m->indices[t]], b = m->positions[m->indices[t + 1]], cc = m->positions[m->indices[t + 2]];
        const vec3 lo = glm::min(a, glm::min(b, cc)), hi = glm::max(a, glm::max(b, cc));
        if (glm::any(glm::lessThan(hi, box.lo)) || glm::any(glm::greaterThan(lo, box.hi))) continue;
        tris.push_back({a, b, cc, ev.scene().characters[c].name + ":" + ci.rig.meshes[mi].part});
      }
  }
  Vis out;
  for (const auto& s : samples) {
    const vec3 p = vec3(P * vec4(s.first, 1)), n = glm::normalize(mat3(P) * s.second);
    if (glm::dot(n, cam.position - p) <= 0) continue;  // faces away (the cup hides it from itself)
    const vec3 d = p - cam.position;
    const float z = glm::dot(d, fwd);
    if (z <= 0 || std::abs(glm::dot(d, right) / z) > halfW || std::abs(glm::dot(d, up) / z) > halfH) continue;
    ++out.facing;
    const float L = glm::length(d);
    const vec3 u = d / L;
    std::string by;
    for (const Tri& t : tris)
      if (rayHits(cam.position, u, L - 1e-4f, t.a, t.b, t.c)) {
        by = t.who;
        break;
      }
    if (by.empty()) ++out.visible;
    else ++out.hiddenBy[by];
  }
  out.fraction = out.facing ? float(out.visible) / float(out.facing) : 0;
  return out;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: measure_t096 <scene.json> [--interaction json] [--frames A-B] [--vis f,..] [--prop name]\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  std::string propName = "cup", visList, assetPath = "content/assets/felt_cup.asset.json";
  int f0 = scene->frameStart, f1 = scene->frameEnd;
  Json interaction;
  bool setInteraction = false;
  for (int i = 2; i + 1 < argc; i += 2) {
    const std::string k = argv[i];
    if (k == "--interaction") interaction = Json::parse(argv[i + 1]), setInteraction = true;
    else if (k == "--frames") std::sscanf(argv[i + 1], "%d-%d", &f0, &f1);
    else if (k == "--vis") visList = argv[i + 1];
    else if (k == "--prop") propName = argv[i + 1];
    else if (k == "--asset") assetPath = argv[i + 1];
  }
  Json sj = sceneToJson(*scene);
  if (setInteraction) {
    if (interaction.is_null()) sj.erase("interaction");
    else sj["interaction"] = interaction;
  }
  const std::filesystem::path tmp = std::filesystem::path(argv[1]).replace_extension(".t096tmp.json");
  { std::ofstream(tmp) << sj.dump(1); }
  auto s2 = loadScene(tmp);
  std::filesystem::remove(tmp);
  if (!s2) return std::fprintf(stderr, "%s\n", s2.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*s2, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  Json out = {{"scene", argv[1]}, {"interaction", sj.value("interaction", Json())}, {"warnings", ev.warnings()}};

  // Heads (first two characters).
  if (ev.characters().size() >= 2) {
    std::vector<std::vector<int>> selA, selB;
    std::vector<CollisionBody> bodies;
    for (size_t c = 0; c < 2; ++c) {
      CollisionBody b = deriveCollisionBody(ev.characters()[c].asset.skeleton, ev.characters()[c].rig.meshes);
      addHeadVolumes(b, ev.characters()[c].asset.skeleton, ev.characters()[c].rig.meshes);
      bodies.push_back(b);
    }
    Json per = Json::array();
    float minD = 1e9f, minV = 1e9f;
    int atD = 0, atV = 0;
    for (int f = f0; f <= f1; ++f) {
      const std::vector<vec3> A = headPoints(ev, 0, f, selA), B = headPoints(ev, 1, f, selB);
      const float d = cloudDistance(A, B);
      const float v = headGap(bodies[0], ev.characterGlobals(0, f), bodies[1], ev.characterGlobals(1, f)).gap;
      if (d < minD) minD = d, atD = f;
      if (v < minV) minV = v, atV = f;
      per.push_back({f, std::round(d * 1e4f) / 10.0f, std::round(v * 1e4f) / 10.0f});
    }
    out["heads"] = {{"min_mesh_distance_mm", minD * 1000}, {"min_mesh_frame", atD}, {"min_volume_gap_mm", minV * 1000},
                    {"min_volume_frame", atV}, {"head_points", {selA.empty() ? 0 : 1, selB.empty() ? 0 : 1}},
                    {"per_frame_[f,mesh_mm(60=at_least),volume_gap_mm]", per}};
    // The planned head tilt (degrees; generated "<who>/collision.headTilt.<other>") and its largest change per frame.
    Json tj = Json::array();
    for (size_t c = 0; c < 2; ++c) {
      const std::string t = ev.scene().characters[c].name + "/collision.headTilt." + ev.scene().characters[1 - c].name;
      float mx = 0, rate = 0;
      int at = 0, first = 0, last = 0;
      for (int f = ev.scene().frameStart; f <= ev.scene().frameEnd; ++f) {
        const float v = ev.scene().animation.evaluate(t, f, vec3(0)).x;
        if (v > mx) mx = v, at = f;
        if (v > 0.05f) last = f, first = first ? first : f;
        if (f > ev.scene().frameStart) rate = std::max(rate, std::abs(v - ev.scene().animation.evaluate(t, f - 1, vec3(0)).x));
      }
      tj.push_back({{"character", ev.scene().characters[c].name}, {"max_tilt_deg", mx}, {"at_frame", at}, {"max_rate_deg_per_frame", rate}, {"tilted_frames", {first, last}}});
    }
    out["head_tilt"] = tj;
    Json hv = Json::array();
    for (size_t c = 0; c < 2; ++c) hv.push_back({{"character", ev.scene().characters[c].name}, {"head_volumes", bodies[c].heads.size()}});
    out["head_volumes"] = hv;
  }

  // Drift while held.
  int prop = -1;
  for (size_t p = 0; p < ev.scene().props.size(); ++p)
    if (ev.scene().props[p].name == propName) prop = int(p);
  if (prop >= 0) {
    auto asset = loadAsset(assetPath);
    if (!asset) return std::fprintf(stderr, "%s\n", asset.error().message.c_str()), 1;
    const PropAsset& A = *asset;
    auto sock = [&](const std::string& k, double f) { return vec3((ev.propWorld(size_t(prop), f) * assetTransformMatrix(A.sockets.at(k)))[3]); };
    auto ci = [&](const std::string& n) {
      for (size_t c = 0; c < ev.scene().characters.size(); ++c)
        if (ev.scene().characters[c].name == n) return int(c);
      return -1;
    };
    struct Hold { int c; char side; std::string socket; double from, to; };
    std::vector<Hold> holds;
    for (const Json& a : ev.scene().actions) {
      const std::string t = a.value("type", "");
      if (t == "grasp" || (t == "reach" && a.value("grasp", true)))
        holds.push_back({ci(a.value("character", "")), a.value("hand", "R")[0], a.value("socket", "grip"), a.value("contact", a.value("start", 0.0) + 14), double(ev.scene().frameEnd)});
    }
    for (const Json& a : ev.scene().actions)
      if (a.value("type", "") == "handover") {
        const double contact = a.value("contact", a.value("start", 0.0) + 18), rel = a.value("release", contact + 4);
        for (Hold& h : holds)
          if (h.c == ci(a.value("character", "")) && h.side == a.value("hand", "R")[0]) h.to = rel;
        holds.push_back({ci(a.value("to", "")), a.value("toHand", "R")[0], a.value("toSocket", "grip_b"), contact, double(ev.scene().frameEnd)});
      }
    Json dj = Json::array();
    for (const Hold& h : holds) {
      // The palm point in the prop's frame, relative to where it was at the contact (exact there: <= 0.0003 mm): the
      // socket the engine used (authored or turned by visibleGrip) does not matter.
      auto local = [&](double f) { return vec3(glm::inverse(ev.propWorld(size_t(prop), f)) * vec4(ev.handGripPoint(size_t(h.c), h.side, f), 1)); };
      const vec3 at0 = local(h.from);
      float worst = 0;
      double at = h.from;
      for (double f = h.from; f <= h.to + 1e-9; f += 0.5) {
        const float e = glm::distance(local(f), at0);
        if (e > worst) worst = e, at = f;
      }
      const float contactErr = glm::distance(ev.handGripPoint(size_t(h.c), h.side, h.from), sock(h.socket, h.from));
      dj.push_back({{"character", ev.scene().characters[size_t(h.c)].name}, {"hand", std::string(1, h.side)}, {"authored_socket", h.socket},
                    {"from", h.from}, {"to", h.to}, {"max_drift_mm", worst * 1000}, {"at_frame", at},
                    {"grip_azimuth_deg", glm::degrees(std::atan2(-at0.z, at0.x))}, {"palm_to_authored_socket_at_contact_mm", contactErr * 1000}});
    }
    out["drift"] = dj;
    // Visibility.
    float radius = 0.04f, height = 0.1f;
    if (A.collision) radius = A.collision->radius, height = A.collision->height;
    Json vj = Json::array();
    for (size_t p0 = 0; p0 < visList.size();) {
      size_t p1 = visList.find(',', p0);
      if (p1 == std::string::npos) p1 = visList.size();
      const double f = std::atof(visList.substr(p0, p1 - p0).c_str());
      const Vis v = cupVisibility(ev, size_t(prop), f, radius, height);
      vj.push_back({{"frame", f}, {"visible_fraction", v.fraction}, {"visible", v.visible}, {"facing_in_frame", v.facing}, {"hidden_by", v.hiddenBy}});
      p0 = p1 + 1;
    }
    out["visibility"] = vj;
  }
  std::cout << out.dump(1) << "\n";
  return 0;
}
