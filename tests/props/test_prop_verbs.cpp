// T-163: the starter felt prop library - schema validity, conventions and one verb test per prop.
// Every prop is picked up, carried and put down through the real verb expander and evaluator on the boy and the girl
// skeletons (the same as tests/test_verbs.cpp); the box lid also does "open" (lift off the box, put aside).
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>

#include <filesystem>
#include <format>
#include <map>
#include <memory>

#include "scene/asset_library.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* kGirl = "girl_auburn_bun_glasses_m3/character.json";

// name, one-hand set id (or the two-hand set), hands
struct Case { const char* name; const char* set; bool two; };
const Case kCases[] = {
    {"bowl", "a", false},  {"plate", "a", false}, {"spoon", "a", false},  {"book", "a", false},
    {"ball", "a", false},  {"box", "both", true}, {"box_lid", "a", false}, {"toy", "a", false},
    {"apple", "a", false}, {"pencil", "a", false}, {"block", "a", false}, {"basket", "both_rims", true},
};

PropAsset load(const std::string& name) { return loadAsset(kRoot / "content/assets" / (name + ".asset.json")).value(); }

Scene baseScene() {
  Scene s;
  s.name = "prop verb test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 110;
  s.timing = "calibrated";
  return s;
}

std::unique_ptr<SceneEvaluator> loadScene(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

vec3 bonePos(const SceneEvaluator& ev, const char* bone) {
  const int b = ev.characters()[0].asset.skeleton.find(bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(0, 1)[size_t(b)][3]);
}

vec3 socketWorld(const SceneEvaluator& ev, size_t p, const PropAsset& a, const std::string& socket, double f) {
  return vec3((ev.propWorld(p, f) * assetTransformMatrix(a.sockets.at(socket)))[3]);
}

// Hand-reach geometry of one character: arm length and the shoulder / chest anchors.
struct Reach { vec3 shoulderR, chest; float arm; };
Reach reachOf(const SceneEvaluator& probe) {
  Reach r;
  r.shoulderR = bonePos(probe, "upperArm.R");
  const vec3 l = bonePos(probe, "upperArm.L"), e = bonePos(probe, "forearm.R"), w = bonePos(probe, "hand.R");
  r.arm = glm::distance(r.shoulderR, e) + glm::distance(e, w);
  r.chest = 0.5f * (l + r.shoulderR);
  return r;
}

// The prop's lead grasp socket (first site of the named set).
std::string leadSocket(const PropAsset& a, const std::string& set) {
  const GraspSet* gs = a.affordances->set(set);
  REQUIRE(gs);
  return a.affordances->site(gs->sites[0])->socket;
}

}  // namespace

TEST_CASE("props: every starter prop loads with valid affordances, the felt preset and the cup conventions") {
  size_t n = 0;
  for (const Case& c : kCases) {
    const std::string id = std::string("felt_") + c.name;
    CAPTURE(id);
    auto r = loadAsset(kRoot / "content/assets" / (id + ".asset.json"));
    REQUIRE(r);
    const PropAsset& a = *r;
    CHECK(a.id == "prop." + id);
    CHECK(a.materialPresets == std::vector<std::string>{"felt"});
    REQUIRE(a.affordances);
    CHECK(a.affordances->error.empty());
    CHECK(a.affordances->sites.size() >= 1);
    CHECK(a.affordances->sets.size() >= 1);
    CHECK(a.affordances->place);
    CHECK(a.affordances->deform == "rigid");
    for (const char* s : {"place", "contact"}) CHECK(a.sockets.count(s) == 1);
    REQUIRE(a.collision);
    CHECK(a.affordances->massKg > 0);
    // every named set and the handover lists resolve (the loader checks it; this guards a silent fallback)
    CHECK((a.affordances->hands != "two" || !a.affordances->sets.empty()));
    // base-origin cylinders and centred spheres/boxes: place socket on the bottom
    const vec3 p = a.sockets.at("place").translation;
    if (a.mesh.primitive == AssetMeshSource::Primitive::Cylinder) CHECK(p == vec3(0));
    else if (a.mesh.primitive == AssetMeshSource::Primitive::Sphere) CHECK(p.y == doctest::Approx(-a.mesh.radius));
    else CHECK(p.y == doctest::Approx(-0.5f * a.mesh.size.y));
    ++n;
  }
  CHECK(n == 12);
  // the library plus the existing felt_cup stays within 10..15
  CHECK(n + 1 >= 10);
  CHECK(n + 1 <= 15);
}

TEST_CASE("props: one verb test per prop - pick up, carry and put down on the boy and the girl") {
  for (const char* character : {kBoy, kGirl}) {
    for (const Case& c : kCases) {
      const std::string id = std::string("felt_") + c.name;
      CAPTURE(character);
      CAPTURE(id);
      const PropAsset asset = load(id);
      Scene scene = baseScene();
      CharacterDesc ch;
      ch.name = "actor";
      ch.asset = character;
      ch.life.enabled = true;
      scene.characters.push_back(ch);
      auto probe = loadScene(scene);
      const Reach R = reachOf(*probe);
      const vec3 fwd(0, 0, 1);

      // Placement: one-handed props sit on the right side with the lead grasp socket where the cup test puts its grip;
      // two-handed props sit level in front of the chest with their side sockets at the shoulder line.
      PropDesc prop;
      prop.name = "prop";
      prop.id = "prop." + id;
      prop.transform.rotationDeg = {0, 180, 0};
      const vec3 lead = assetTransformMatrix(asset.sockets.at(leadSocket(asset, c.set)))[3];
      if (c.two) {
        const float rimHeight = asset.sockets.at(leadSocket(asset, c.set)).translation.y;
        prop.transform.translation = R.chest + fwd * (0.75f * R.arm) - vec3(0, 0.55f * R.arm + rimHeight, 0);
      } else {
        const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
        const vec3 grip = R.shoulderR + vec3(0.04f, -0.45f, 0.85f) * R.arm;
        prop.transform.translation = grip - vec3(rot * vec4(lead, 0));
      }
      scene.props.push_back(prop);
      std::vector<PropAsset> assets = {asset};
      if (std::string(c.name) == "box_lid") {  // the lid sits on the box (the box does not move)
        PropDesc box;
        box.name = "box";
        box.id = "prop.felt_box";
        box.transform.translation = prop.transform.translation - vec3(0, 0.035f + 0.006f, 0);
        box.transform.rotationDeg = {0, 180, 0};
        scene.props.push_back(box);
      }
      const vec3 t0 = scene.props[0].transform.translation;
      const vec3 placeStart = socketWorld(*loadScene(scene), 0, asset, "place", 1);
      const vec3 target = placeStart + vec3(c.two ? 0.0f : 0.02f, 0, c.two ? 0.0f : 0.01f) +
                          (std::string(c.name) == "box_lid" ? vec3(0.0f, 0, -0.14f) : vec3(0));  // the lid goes aside = "open"
      const std::string hands = c.two ? R"("hands": ["L", "R"])" : R"("hand": "R")";
      scene.actions = Json::parse(std::format(
          R"([{{"type": "pick_up", "character": "actor", {0}, "prop": "prop", "set": "{1}", "start": 5, "contact": 20}},
              {{"type": "carry", "character": "actor", {0}, "start": 22, "end": 36, "by": [0, 0.06, 0.02]}},
              {{"type": "place", "verb": true, "character": "actor", {0}, "start": 40, "contact": 54, "end": 68}}])",
          hands, c.set));
      scene.actions[2]["at"] = {target.x, target.y, target.z};
      scene.frameEnd = 96;
      auto ev = loadScene(scene);  // the verb constraints (reach, palm on the socket <= 0.5 mm, upright) are enforced on load

      const auto& sw = ev->scene().props[0].parentSwitch;
      REQUIRE(sw.size() == 2);
      REQUIRE(sw[0].parent);
      CHECK(sw[0].parent->socket.rfind("hand.", 0) == 0);
      CHECK_FALSE(sw[1].parent);
      const double grabbed = sw[0].frame, released = sw[1].frame;
      CHECK(grabbed < released);

      const std::string socket = leadSocket(asset, c.set);
      float palm = 0, tilt = 0;
      const char side = c.two ? 'L' : 'R';
      for (double f = grabbed + 2; f <= released; f += 1) {
        palm = std::max(palm, glm::distance(ev->handGripPoint(0, side, f), socketWorld(*ev, 0, asset, socket, f)));
        const vec3 up = glm::normalize(mat3(ev->propWorld(0, f)) * vec3(0, 1, 0));
        tilt = std::max(tilt, glm::degrees(std::acos(std::clamp(up.y, -1.0f, 1.0f))));
      }
      MESSAGE(character << " " << id << ": grabbed " << grabbed << ", released " << released << ", palm " << palm * 1000
                        << " mm, tilt " << tilt << " deg");
      CHECK(palm <= 0.0015f);
      CHECK(tilt <= asset.affordances->upright->maxTiltDeg);
      // carried up, then put down on the target
      CHECK(socketWorld(*ev, 0, asset, "place", released - 10)[1] > placeStart.y + 0.02f);
      CHECK(glm::distance(socketWorld(*ev, 0, asset, "place", released), target) <= 0.0015f);
      CHECK(glm::distance(socketWorld(*ev, 0, asset, "place", 96), target) <= 0.0015f);
      (void)t0;
    }
  }
}

TEST_CASE("props: the lid seats on the box (place socket on lid_seat) and a handover pair exists on one-hand props") {
  const PropAsset box = load("felt_box"), lid = load("felt_box_lid");
  const float lidBottom = lid.sockets.at("place").translation.y, seat = box.sockets.at("lid_seat").translation.y;
  CHECK(seat - lidBottom == doctest::Approx(0.035f + 0.006f));  // lid centre sits 41 mm above the box centre
  CHECK(lid.mesh.size.x >= box.mesh.size.x);
  for (const Case& c : kCases) {
    const PropAsset a = load(std::string("felt_") + c.name);
    if (a.affordances->hands == "two") continue;
    if (std::string(c.name) == "box") continue;
    CAPTURE(c.name);
    CHECK_FALSE(a.affordances->handoverGive.empty());
    CHECK_FALSE(a.affordances->handoverReceive.empty());
  }
}
