#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <string>

#include "scene/asset_library.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

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

}  // namespace

TEST_CASE("plush.asset/1 parses file and primitive mesh sources") {
  const fs::path root = PLUSH_SOURCE_DIR;
  auto cup = loadAsset(root / "content/assets/cup.asset.json");
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

  auto sheet = loadAsset(root / "content/assets/paper_sheet.asset.json");
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
