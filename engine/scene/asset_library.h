// Reusable prop assets. plush.asset/1 describes source geometry, material presets,
// interaction sockets and an optional coarse collision proxy.
#pragma once

#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "geom/json_io.h"

namespace plush {

struct AssetTransform {
  vec3 translation{0};
  vec3 rotationDeg{0};  // XYZ Euler angles; X is applied first.
  vec3 scale{1};
};

mat4 assetTransformMatrix(const AssetTransform& transform);
Result<AssetTransform> assetTransformFromJson(const Json& json, std::string_view context = "transform");
Json assetTransformToJson(const AssetTransform& transform);

struct AssetMeshSource {
  enum class Kind { File, Primitive };
  enum class Primitive { Box, Sphere, Cylinder };

  Kind kind = Kind::File;
  std::filesystem::path path;
  std::string object;

  Primitive primitive = Primitive::Box;
  vec3 size{1};  // box dimensions in source units
  float radius = 0.5f;
  float height = 1.0f;  // cylinder height in source units
};

struct AssetCollisionProxy {
  enum class Type { Box, Sphere, Capsule };

  Type type = Type::Box;
  AssetTransform transform;
  vec3 size{1};
  float radius = 0.5f;
  float height = 1.0f;  // capsule tip-to-tip height
};

struct PropAsset {
  std::string id;
  int version = 1;
  std::string licence;
  std::string attribution;
  AssetMeshSource mesh;
  std::vector<std::string> materialPresets;
  float scaleMetres = 1.0f;  // metres per source unit
  std::map<std::string, AssetTransform> sockets;
  std::optional<AssetCollisionProxy> collision;
};

Result<PropAsset> assetFromJson(const Json& json);
Result<PropAsset> loadAsset(const std::filesystem::path& path);

}  // namespace plush
