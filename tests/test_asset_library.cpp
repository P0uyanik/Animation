#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <string>

#include "scene/asset_library.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;

Json validAsset() {
  return {{"format", "plush.asset"},
          {"version", 1},
          {"id", "prop.test"},
          {"licence", "CC0-1.0"},
          {"attribution", "Generated test fixture"},
          {"mesh", {{"path", "models/test.glb"}, {"object", "TestObject"}}},
          {"material_presets", {"matte"}},
          {"scale", 0.01},
          {"sockets", {{"grip", {{"translation", {1, 2, 3}},
                                    {"rotationDeg", {0, 90, 0}},
                                    {"scale", {2, 2, 2}}}}}},
          {"collision", {{"type", "sphere"}, {"radius", 0.5}}}};
}

void checkError(const Json& json, const std::string& text) {
  auto result = assetFromJson(json);
  REQUIRE_FALSE(result.has_value());
  CHECK(result.error().message.find(text) != std::string::npos);
}

Result<Scene> loadSceneJson(const Json& json, const Json* asset = nullptr) {
  const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
  const fs::path root = fs::temp_directory_path() / std::format("plush_asset_scene_{}", stamp);
  const fs::path scenePath = root / "content/scenes/test.scene.json";
  std::error_code error;
  fs::create_directories(scenePath.parent_path(), error);
  if (error) return fail(std::format("could not create test directory: {}", error.message()));
  if (asset) {
    const fs::path assetPath = root / "content/assets/test.asset.json";
    fs::create_directories(assetPath.parent_path(), error);
    if (error) return fail(std::format("could not create asset test directory: {}", error.message()));
    auto written = writeTextFile(assetPath, asset->dump());
    if (!written) return std::unexpected(written.error());
  }
  auto written = writeTextFile(scenePath, json.dump());
  if (!written) return std::unexpected(written.error());
  auto loaded = loadScene(scenePath);
  fs::remove_all(root, error);
  return loaded;
}

void checkSceneError(const Json& json, const std::string& text, const Json* asset = nullptr) {
  auto result = loadSceneJson(json, asset);
  REQUIRE_FALSE(result.has_value());
  CHECK(result.error().message.find(text) != std::string::npos);
}

Scene propEvaluationScene() {
  Scene scene;
  scene.name = "prop evaluation";
  scene.path = kRoot / "tests/data/imported/scene.json";
  scene.rate = FrameRate{30, 1};
  scene.frameStart = 0;
  scene.frameEnd = 20;
  CharacterDesc character;
  character.name = "actor_a";
  character.asset = "toy_fixture/character.json";
  scene.characters.push_back(character);
  return scene;
}

std::unique_ptr<SceneEvaluator> evaluatorFor(Scene scene) {
  auto evaluator = std::make_unique<SceneEvaluator>();
  auto loaded = evaluator->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(loaded.has_value());
  return evaluator;
}

void checkMatrix(const mat4& actual, const mat4& expected, float epsilon = 1e-5f) {
  for (int column = 0; column < 4; ++column)
    for (int row = 0; row < 4; ++row)
      CHECK(actual[column][row] == doctest::Approx(expected[column][row]).epsilon(epsilon).scale(1.0));
}

}  // namespace

TEST_CASE("plush.asset/1 parses file and primitive mesh sources") {
  auto cup = loadAsset(kRoot / "content/assets/cup.asset.json");
  REQUIRE(cup.has_value());
  CHECK(cup->id == "prop.cup");
  CHECK(cup->version == 1);
  CHECK(cup->licence == "CC0-1.0");
  CHECK(cup->mesh.kind == AssetMeshSource::Kind::Primitive);
  CHECK(cup->mesh.primitive == AssetMeshSource::Primitive::Cylinder);
  CHECK(cup->materialPresets == std::vector<std::string>{"ceramic_glaze"});
  CHECK(cup->sockets.count("grip") == 1);
  REQUIRE(cup->collision.has_value());
  CHECK(cup->collision->type == AssetCollisionProxy::Type::Capsule);

  auto sheet = loadAsset(kRoot / "content/assets/paper_sheet.asset.json");
  REQUIRE(sheet.has_value());
  CHECK(sheet->mesh.primitive == AssetMeshSource::Primitive::Box);
  CHECK(sheet->mesh.size.x == doctest::Approx(0.21));

  auto external = assetFromJson(validAsset());
  REQUIRE(external.has_value());
  CHECK(external->mesh.kind == AssetMeshSource::Kind::File);
  CHECK(external->mesh.path == fs::path("models/test.glb"));
  CHECK(external->mesh.object == "TestObject");
}

TEST_CASE("plush.asset/1 reports validation errors") {
  Json missingLicence = validAsset();
  missingLicence.erase("licence");
  checkError(missingLicence, "licence field is required");

  Json wrongMeshType = validAsset();
  wrongMeshType["mesh"]["path"] = "models/test.fbx";
  checkError(wrongMeshType, ".blend or .glb");

  Json badSocket = validAsset();
  badSocket["sockets"]["grip"]["scale"] = {1, 0, 1};
  checkError(badSocket, "scale' components must be nonzero");

  Json badCollision = validAsset();
  badCollision["collision"] = {{"type", "capsule"}, {"radius", 0.4}, {"height", 0.5}};
  checkError(badCollision, "at least twice the radius");
}

TEST_CASE("asset socket transforms compose translation rotation and scale") {
  auto asset = assetFromJson(validAsset());
  REQUIRE(asset.has_value());
  const mat4 transform = assetTransformMatrix(asset->sockets.at("grip"));
  const vec3 point = vec3(transform * vec4(0, 0, 1, 1));
  CHECK(point.x == doctest::Approx(3.0));
  CHECK(point.y == doctest::Approx(2.0));
  CHECK(point.z == doctest::Approx(3.0));
}

TEST_CASE("scene prop placements round-trip through JSON") {
  Scene scene;
  scene.name = "prop round trip";
  CharacterDesc character;
  character.name = "actor_a";
  scene.characters.push_back(character);
  PropDesc first;
  first.name = "cup_near";
  first.id = "prop.cup";
  first.transform.translation = {0.2f, 0.7f, -0.1f};
  first.transform.rotationDeg = {0, 35, 0};
  first.parent = PropParent{PropParent::Kind::Character, "actor_a", "hand.R"};
  first.parentSwitch.push_back({12, std::nullopt});
  scene.props.push_back(first);
  PropDesc second;
  second.name = "cup_far";
  second.id = "prop.cup";
  second.transform.scale = {0.5f, 0.5f, 0.5f};
  scene.props.push_back(second);

  const Json original = sceneToJson(scene);
  REQUIRE(original["props"].size() == 2);
  auto loaded = loadSceneJson(original);

  REQUIRE(loaded.has_value());
  REQUIRE(loaded->props.size() == 2);
  CHECK(loaded->props[0].name == "cup_near");
  CHECK(loaded->props[0].id == "prop.cup");
  REQUIRE(loaded->props[0].parent.has_value());
  CHECK(loaded->props[0].parent->kind == PropParent::Kind::Character);
  CHECK(loaded->props[0].parent->name == "actor_a");
  CHECK(loaded->props[0].parent->socket == "hand.R");
  REQUIRE(loaded->props[0].parentSwitch.size() == 1);
  CHECK(loaded->props[0].parentSwitch[0].frame == doctest::Approx(12));
  CHECK_FALSE(loaded->props[0].parentSwitch[0].parent.has_value());
  CHECK(loaded->props[0].transform.rotationDeg.y == doctest::Approx(35));
  CHECK(loaded->props[1].name == "cup_far");
  CHECK(loaded->props[1].id == "prop.cup");
  CHECK_FALSE(loaded->props[1].parent.has_value());
  CHECK(sceneToJson(*loaded)["props"] == original["props"]);
}

TEST_CASE("scene prop instance names are unique") {
  Scene scene;
  PropDesc first;
  first.name = "cup";
  first.id = "prop.cup";
  scene.props.push_back(first);
  scene.props.push_back(first);

  checkSceneError(sceneToJson(scene), "prop name 'cup' is not unique");
}

TEST_CASE("scene prop parents must name an existing instance and valid socket kind") {
  Scene scene;
  PropDesc prop;
  prop.name = "cup";
  prop.id = "prop.cup";
  prop.parent = PropParent{PropParent::Kind::Character, "missing", "hand.R"};
  scene.props.push_back(prop);
  Json json = sceneToJson(scene);

  checkSceneError(json, "parent character 'missing' does not exist");
  json["props"][0]["parent"] = {{"kind", "prop"}, {"name", "missing"}, {"socket", "grip"}};
  checkSceneError(json, "parent prop 'missing' does not exist");
  json["props"][0]["parent"]["kind"] = "object";
  checkSceneError(json, "parent.kind must be 'character' or 'prop'");
  json["props"][0]["parent"] = {{"kind", "character"}, {"name", "missing"}, {"socket", ""}};
  checkSceneError(json, "parent.socket must be a non-empty string");
}

TEST_CASE("scene rejects prop parent cycles") {
  Scene scene;
  PropDesc first;
  first.name = "cup_a";
  first.id = "prop.cup";
  first.parent = PropParent{PropParent::Kind::Prop, "cup_b", "grip"};
  scene.props.push_back(first);
  PropDesc second;
  second.name = "cup_b";
  second.id = "prop.cup";
  second.parent = PropParent{PropParent::Kind::Prop, "cup_a", "grip"};
  scene.props.push_back(second);

  checkSceneError(sceneToJson(scene), "prop parent cycle");
}

TEST_CASE("scene validates sockets on prop parents") {
  Scene scene;
  PropDesc parent;
  parent.name = "stand";
  parent.id = "prop.test";
  scene.props.push_back(parent);
  PropDesc child;
  child.name = "cup";
  child.id = "prop.cup";
  child.parent = PropParent{PropParent::Kind::Prop, "stand", "grip"};
  scene.props.push_back(child);
  Json asset = validAsset();

  auto loaded = loadSceneJson(sceneToJson(scene), &asset);
  REQUIRE(loaded.has_value());
  Json invalid = sceneToJson(scene);
  invalid["props"][1]["parent"]["socket"] = "missing";
  checkSceneError(invalid, "asset 'prop.test' has no socket 'missing'", &asset);
}

TEST_CASE("scenes without props retain the old JSON output") {
  Scene scene;
  scene.name = "legacy scene";
  const Json oldOutput = sceneToJson(scene);
  REQUIRE_FALSE(oldOutput.contains("props"));

  auto loaded = loadSceneJson(oldOutput);
  REQUIRE(loaded.has_value());
  CHECK(sceneToJson(*loaded) == oldOutput);
}

TEST_CASE("scene evaluator prop follows a moving character bone socket") {
  Scene scene = propEvaluationScene();
  PropDesc prop;
  prop.name = "item";
  prop.id = "prop.cup";
  prop.transform.translation = {0, 0, 0.1f};
  prop.parent = PropParent{PropParent::Kind::Character, "actor_a", "hand.R"};
  scene.props.push_back(prop);
  scene.animation.tracks["actor_a/hand.R.rot"].setKey({0, vec3(0), Interp::Linear});
  scene.animation.tracks["actor_a/hand.R.rot"].setKey({10, vec3(0, 90, 0), Interp::Linear});

  auto evaluator = evaluatorFor(std::move(scene));
  const int hand = evaluator->characters()[0].asset.skeleton.find("hand.R");
  REQUIRE(hand >= 0);
  checkMatrix(evaluator->propWorld(0, 10),
              evaluator->characterGlobals(0, 10)[size_t(hand)] * assetTransformMatrix(prop.transform));
  CHECK(glm::distance(vec3(evaluator->propWorld(0, 0)[3]), vec3(evaluator->propWorld(0, 10)[3])) > 0.05f);
}

TEST_CASE("scene evaluator accepts a shared character role as a prop socket") {
  Scene scene = propEvaluationScene();
  PropDesc prop;
  prop.name = "role_item";
  prop.id = "prop.paper_sheet";
  prop.transform.translation = {0.02f, 0, 0};
  prop.parent = PropParent{PropParent::Kind::Character, "actor_a", "upperArm.R"};
  scene.props.push_back(prop);

  auto evaluator = evaluatorFor(std::move(scene));
  const int roleBone = evaluator->characters()[0].asset.skeleton.find("upperArm.R");
  REQUIRE(roleBone >= 0);
  checkMatrix(evaluator->propWorld(0, 4),
              evaluator->characterGlobals(0, 4)[size_t(roleBone)] * assetTransformMatrix(prop.transform));
}

TEST_CASE("scene evaluator resolves a prop-on-prop socket chain in dependency order") {
  Scene scene = propEvaluationScene();
  scene.characters.clear();
  PropDesc base;
  base.name = "base";
  base.id = "prop.cup";
  base.transform.translation = {0.3f, 0.4f, -0.2f};
  base.transform.rotationDeg = {0, 30, 0};
  scene.props.push_back(base);
  PropDesc child;
  child.name = "child";
  child.id = "prop.paper_sheet";
  child.transform.translation = {0, 0.06f, 0};
  child.parent = PropParent{PropParent::Kind::Prop, "base", "grip"};
  scene.props.push_back(child);

  auto evaluator = evaluatorFor(std::move(scene));
  const PropAsset cup = loadAsset(kRoot / "content/assets/cup.asset.json").value();
  const mat4 expected = assetTransformMatrix(base.transform) * assetTransformMatrix(cup.sockets.at("grip")) *
                        assetTransformMatrix(child.transform);
  checkMatrix(evaluator->propWorld(1, 3), expected);
}

TEST_CASE("prop parent weight blends continuously between world and attached placement") {
  Scene scene = propEvaluationScene();
  PropDesc prop;
  prop.name = "blend_item";
  prop.id = "prop.cup";
  prop.transform.translation = {0.8f, 0.1f, 0.2f};
  prop.parent = PropParent{PropParent::Kind::Character, "actor_a", "hand.L"};
  scene.props.push_back(prop);
  Track& weight = scene.animation.tracks["blend_item.parent.weight"];
  weight.setKey({0, vec3(0), Interp::Linear});
  weight.setKey({10, vec3(1), Interp::Linear});

  auto evaluator = evaluatorFor(std::move(scene));
  const vec3 worldPosition(assetTransformMatrix(prop.transform)[3]);
  const int hand = evaluator->characters()[0].asset.skeleton.find("hand.L");
  REQUIRE(hand >= 0);
  const vec3 attachedPosition(
      (evaluator->characterGlobals(0, 10)[size_t(hand)] * assetTransformMatrix(prop.transform))[3]);
  CHECK(glm::distance(vec3(evaluator->propWorld(0, 0)[3]), worldPosition) < 1e-6f);
  CHECK(glm::distance(vec3(evaluator->propWorld(0, 10)[3]), attachedPosition) < 1e-5f);
  CHECK(glm::distance(vec3(evaluator->propWorld(0, 5)[3]), glm::mix(worldPosition, attachedPosition, 0.5f)) < 1e-5f);
  CHECK(glm::distance(vec3(evaluator->propWorld(0, 5.001)[3]), vec3(evaluator->propWorld(0, 4.999)[3])) < 0.001f);
}

TEST_CASE("prop parent switch preserves its world transform at the switch frame") {
  Scene scene = propEvaluationScene();
  PropDesc prop;
  prop.name = "switch_item";
  prop.id = "prop.cup";
  prop.transform.translation = {0, 0, 0.1f};
  prop.parent = PropParent{PropParent::Kind::Character, "actor_a", "hand.L"};
  prop.parentSwitch.push_back({10, PropParent{PropParent::Kind::Character, "actor_a", "hand.R"}});
  scene.props.push_back(prop);
  scene.animation.tracks["switch_item.parent.weight"].setKey({0, vec3(0.35f), Interp::Linear});
  scene.animation.tracks["actor_a/hand.R.rot"].setKey({10, vec3(0), Interp::Linear});
  scene.animation.tracks["actor_a/hand.R.rot"].setKey({20, vec3(0, 90, 0), Interp::Linear});

  auto evaluator = evaluatorFor(std::move(scene));
  const mat4 before = evaluator->propWorld(0, 10.0 - 1e-6);
  const mat4 switched = evaluator->propWorld(0, 10);
  checkMatrix(switched, before, 1e-4f);
  CHECK(glm::distance(vec3(switched[3]), vec3(evaluator->propWorld(0, 20)[3])) > 0.05f);
}

TEST_CASE("shot bake carries prop matrices and otherwise matches a scene without props") {
  Scene withProp = propEvaluationScene();
  PropDesc prop;
  prop.name = "baked_item";
  prop.id = "prop.cup";
  prop.transform.translation = {0.25f, 0.5f, -0.1f};
  withProp.props.push_back(prop);
  Scene withoutProp = withProp;
  withoutProp.props.clear();

  auto propEvaluator = evaluatorFor(std::move(withProp));
  auto legacyEvaluator = evaluatorFor(std::move(withoutProp));
  Json propBake = bakeShot(*propEvaluator, 1, 2);
  const Json legacyBake = bakeShot(*legacyEvaluator, 1, 2);
  REQUIRE(propBake["frame_data"].size() == 2);
  for (Json& frame : propBake["frame_data"]) {
    REQUIRE(frame.contains("props"));
    REQUIRE(frame["props"].contains("baked_item"));
    REQUIRE(frame["props"]["baked_item"].size() == 16);
    CHECK(frame["props"]["baked_item"][12].get<float>() == doctest::Approx(0.25f));
    CHECK(frame["props"]["baked_item"][13].get<float>() == doctest::Approx(0.5f));
    CHECK(frame["props"]["baked_item"][14].get<float>() == doctest::Approx(-0.1f));
    frame.erase("props");
  }
  CHECK(propBake == legacyBake);
  for (const Json& frame : legacyBake["frame_data"]) CHECK_FALSE(frame.contains("props"));
}

TEST_CASE("scene evaluator reports a missing character prop socket") {
  Scene scene = propEvaluationScene();
  PropDesc prop;
  prop.name = "item";
  prop.id = "prop.cup";
  prop.parent = PropParent{PropParent::Kind::Character, "actor_a", "missing_socket"};
  scene.props.push_back(prop);

  SceneEvaluator evaluator;
  auto loaded = evaluator.load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE_FALSE(loaded.has_value());
  CHECK(loaded.error().message.find("has no bone or role socket 'missing_socket'") != std::string::npos);
}
