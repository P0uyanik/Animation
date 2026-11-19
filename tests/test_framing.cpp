// T-140: director framing rules (opt-in "director": {"framing": ...}): headroom that includes hair and a bun, safe
// margins and the crop choice for reach acting. Without "framing" the director plans exactly as before.
#include <doctest/doctest.h>

#include <filesystem>

#include "scene/scene.h"

using namespace plush;

namespace {

std::unique_ptr<SceneEvaluator> loadFramingScene(const Json& director) {
  Scene s;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "content/scenes/unit_test.scene.json";
  s.rate = FrameRate{30, 1};
  s.frameStart = 1;
  s.frameEnd = 90;
  // A tight master camera: the head and the reaching hand leave the frame without framing.
  s.camera.position = vec3(0.0f, 0.5f, 1.3f);
  s.camera.target = vec3(0.0f, 0.42f, 0.0f);
  s.camera.focalMm = 35.0f;  // wide 35 mm, medium 50 mm, inserts 70 mm (director defaults)
  CharacterDesc cd;
  cd.name = "kid";
  cd.asset = "../characters/boy_dark_hair.character.json";
  cd.life.enabled = false;
  s.characters.push_back(cd);
  ObjectDesc ball;
  ball.name = "ball";
  ball.kind = ObjectDesc::Kind::Box;
  ball.boxMin = vec3(-0.015f);
  ball.boxMax = vec3(0.015f);
  ball.position = vec3(-0.17f, 0.47f, 0.2f);
  s.objects.push_back(ball);
  s.actions = Json::parse(R"([{"type": "reach", "character": "kid", "hand": "R", "object": "ball",
      "start": 10, "contact": 24, "lift": 0.06, "liftEnd": 36, "place": 60, "placeAt": [-0.12, 0.45, 0.25],
      "release": 63, "end": 78, "graspRadius": 0.015}])");
  s.director = director;
  s.director["minShot"] = 24;  // keeps the medium reach shot (f1-15)
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}

// Frame extents (x: -1 left .. 1 right, y: -1 bottom .. 1 top) of what bone `root` and its children carry (every
// skinned vertex, by its most weighted joint), seen through the director's camera at frame f.
vec4 carriedExtent(const SceneEvaluator& ev, const char* root, double f) {
  const Scene& sc = ev.scene();
  const vec3 cam = sc.animation.evaluate("camera.position", f, sc.camera.position);
  const vec3 tgt = sc.animation.evaluate("camera.target", f, sc.camera.target);
  const float focal = sc.animation.evaluate("camera.lens", f, vec3(sc.camera.focalMm)).x;
  const vec3 fw = glm::normalize(tgt - cam), rt = glm::normalize(glm::cross(fw, vec3(0, 1, 0))), up = glm::cross(rt, fw);
  const float tx = sc.camera.sensorWidthMm * 0.5f / focal, ty = tx * 9.0f / 16.0f;
  const auto& ci = ev.characters()[0];
  const auto& sk = ci.asset.skeleton;
  const int r = sk.find(root);
  REQUIRE(r >= 0);
  std::vector<char> in(sk.bones.size(), 0);
  for (size_t b = 0; b < sk.bones.size(); ++b)
    in[b] = int(b) == r || (sk.bones[b].parent >= 0 && in[size_t(sk.bones[b].parent)]);
  const auto G = ev.characterGlobals(0, f);
  vec4 e(1e9f, -1e9f, 1e9f, -1e9f);
  for (const auto& m : ci.rig.meshes)
    for (size_t i = 0; i < m.rest.positions.size(); ++i) {
      int j = m.joints[i].x;
      float w = m.weights[i].x;
      for (int k = 1; k < 4; ++k)
        if (m.weights[i][k] > w) w = m.weights[i][k], j = m.joints[i][k];
      if (!in[size_t(j)]) continue;
      const vec3 p = vec3(G[size_t(j)] * vec4(m.rest.positions[i] - sk.bones[size_t(j)].head, 1));
      const vec3 d = p - cam;
      const float z = glm::dot(d, fw), x = glm::dot(d, rt) / z / tx, y = glm::dot(d, up) / z / ty;
      e = vec4(std::min(e.x, x), std::max(e.y, x), std::min(e.z, y), std::max(e.w, y));
    }
  return e;
}

std::vector<Key> keys(const SceneEvaluator& ev, const char* track) {
  const auto& g = ev.scene().animation.generated;
  REQUIRE(g);
  auto it = g->tracks.find(track);
  REQUIRE(it != g->tracks.end());
  return it->second.keys;
}

}  // namespace

TEST_CASE("director framing is opt-in: without it (or false) the planned camera is unchanged") {
  auto base = loadFramingScene(Json::object());
  auto off = loadFramingScene(Json::parse(R"({"framing": false})"));
  for (const char* t : {"camera.position", "camera.target", "camera.lens"}) {
    const auto a = keys(*base, t), b = keys(*off, t);
    REQUIRE(a.size() == b.size());
    for (size_t i = 0; i < a.size(); ++i) {
      CHECK(a[i].frame == b[i].frame);
      CHECK(a[i].value == b[i].value);
    }
  }
}

TEST_CASE("director framing keeps the head (hair included) under the headroom line and the hands in the safe area") {
  auto base = loadFramingScene(Json::object());
  auto framed = loadFramingScene(Json::parse(R"({"framing": {"headroom": 0.05, "safeMargin": 0.04}})"));
  float topBase = -9, topFramed = -9, handBase = 0, handFramed = 0;
  auto insert = [](const SceneEvaluator& ev, double f) {
    return ev.scene().animation.evaluate("camera.lens", f, vec3(0)).x > 60.0f;  // inserts keep only their subject
  };
  for (double f = 1; f <= 90; f += 1) {
    if (!insert(*base, f)) {
      const vec4 head = carriedExtent(*base, "head", f), hand = carriedExtent(*base, "hand.R", f);
      topBase = std::max(topBase, head.w);
      handBase = std::max({handBase, -hand.z, hand.w, -hand.x, hand.y});
    }
    if (!insert(*framed, f)) {  // wide and medium reach shots keep the head and the reaching hand
      const vec4 head = carriedExtent(*framed, "head", f), hand = carriedExtent(*framed, "hand.R", f);
      topFramed = std::max(topFramed, head.w);
      handFramed = std::max({handFramed, -hand.z, hand.w, -hand.x, hand.y});
    }
  }
  MESSAGE("head top: " << topBase << " -> " << topFramed << ", reaching hand furthest: " << handBase << " -> " << handFramed);
  CHECK(topBase > 1.0f);              // the tight master crops the hair without framing
  CHECK(topFramed <= 0.9f + 0.01f);   // headroom 0.05 of the frame height (top line at 0.9)
  CHECK(handFramed <= 0.92f + 0.01f); // safe margin 0.04 of the frame
}

TEST_CASE("director cuts false keeps one master camera, refitted by framing") {
  auto framed = loadFramingScene(Json::parse(R"({"framing": true, "cuts": false})"));
  const auto pos = keys(*framed, "camera.position");
  REQUIRE(pos.size() == 1);
  CHECK(pos[0].frame == 1);
  const vec3 master = framed->scene().camera.position, target = framed->scene().camera.target;
  // Same direction, backed off.
  const vec3 newTarget = keys(*framed, "camera.target")[0].value;
  CHECK(glm::dot(glm::normalize(pos[0].value - newTarget), glm::normalize(master - target)) > 0.9999f);
  CHECK(glm::distance(pos[0].value, newTarget) > glm::distance(master, target));
  // "face" keeps the head but lets the hands leave: it backs off less than "hands".
  auto face = loadFramingScene(Json::parse(R"({"framing": {"reachCrop": "face"}, "cuts": false})"));
  const float dFace = glm::distance(keys(*face, "camera.position")[0].value, keys(*face, "camera.target")[0].value);
  CHECK(dFace <= glm::distance(pos[0].value, newTarget) + 1e-5f);
}
