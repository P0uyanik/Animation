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
  PropDesc first;
  first.id = "prop.cup";
  first.transform.translation = {0.2f, 0.7f, -0.1f};
  first.transform.rotationDeg = {0, 35, 0};
  first.parentSocket = "surface.place";
  scene.props.push_back(first);
  PropDesc second;
  second.id = "prop.paper_sheet";
  second.transform.scale = {0.5f, 0.5f, 0.5f};
  scene.props.push_back(second);

  const Json original = sceneToJson(scene);
  REQUIRE(original["props"].size() == 2);
  const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
  const fs::path path = fs::temp_directory_path() / std::format("plush_asset_scene_{}.json", stamp);
  REQUIRE(writeTextFile(path, original.dump()).has_value());
  auto loaded = loadScene(path);
  std::error_code removeError;
  fs::remove(path, removeError);

  REQUIRE(loaded.has_value());
  REQUIRE(loaded->props.size() == 2);
  CHECK(loaded->props[0].id == "prop.cup");
  REQUIRE(loaded->props[0].parentSocket.has_value());
  CHECK(*loaded->props[0].parentSocket == "surface.place");
  CHECK(loaded->props[0].transform.rotationDeg.y == doctest::Approx(35));
  CHECK_FALSE(loaded->props[1].parentSocket.has_value());
  CHECK(sceneToJson(*loaded)["props"] == original["props"]);
}
