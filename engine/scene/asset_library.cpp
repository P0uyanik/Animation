#include "scene/asset_library.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <set>

namespace plush {
namespace {

bool finite(vec3 value) { return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z); }

Result<vec3> vec3Field(const Json& json, const char* key, vec3 fallback, std::string_view context) {
  auto it = json.find(key);
  if (it == json.end()) return fallback;
  if (!it->is_array() || it->size() != 3 || !(*it)[0].is_number() || !(*it)[1].is_number() ||
      !(*it)[2].is_number())
    return fail(std::format("{}: '{}' must be an array of three numbers", context, key));
  vec3 value((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
  if (!finite(value)) return fail(std::format("{}: '{}' must contain finite numbers", context, key));
  return value;
}

Result<float> numberField(const Json& json, const char* key, float fallback, std::string_view context,
                          bool required = false) {
  auto it = json.find(key);
  if (it == json.end()) {
    if (required) return fail(std::format("{}: '{}' is required", context, key));
    return fallback;
  }
  if (!it->is_number()) return fail(std::format("{}: '{}' must be a number", context, key));
  const float value = it->get<float>();
  if (!std::isfinite(value)) return fail(std::format("{}: '{}' must be finite", context, key));
  return value;
}

bool allPositive(vec3 value) { return value.x > 0 && value.y > 0 && value.z > 0; }
bool allNonzero(vec3 value) { return value.x != 0 && value.y != 0 && value.z != 0; }

Result<AssetMeshSource> meshFromJson(const Json& json, const std::string& id) {
  const std::string context = std::format("asset '{}': mesh", id);
  if (!json.is_object()) return fail(context + " must be an object");
  const bool hasPath = json.contains("path");
  const bool hasPrimitive = json.contains("primitive");
  if (hasPath == hasPrimitive) return fail(context + " must contain exactly one of 'path' or 'primitive'");

  AssetMeshSource source;
  if (hasPath) {
    if (!json["path"].is_string() || json["path"].get<std::string>().empty())
      return fail(context + ": 'path' must be a non-empty string");
    if (!json.contains("object") || !json["object"].is_string() || json["object"].get<std::string>().empty())
      return fail(context + ": 'object' is required for a file source");
    source.kind = AssetMeshSource::Kind::File;
    source.path = json["path"].get<std::string>();
    source.object = json["object"].get<std::string>();
    std::string extension = source.path.extension().string();
    std::transform(extension.begin(), extension.end(), extension.begin(),
                   [](unsigned char c) { return char(std::tolower(c)); });
    if (extension != ".blend" && extension != ".glb")
      return fail(context + ": file source must use a .blend or .glb path");
    return source;
  }

  if (!json["primitive"].is_string() || json["primitive"].get<std::string>().empty())
    return fail(context + ": 'primitive' must be a non-empty string");
  source.kind = AssetMeshSource::Kind::Primitive;
  const std::string primitive = json["primitive"].get<std::string>();
  if (primitive == "box") {
    source.primitive = AssetMeshSource::Primitive::Box;
    auto size = vec3Field(json, "size", source.size, context);
    if (!size) return std::unexpected(size.error());
    if (!json.contains("size") || !allPositive(*size)) return fail(context + ": box 'size' must be positive");
    source.size = *size;
  } else if (primitive == "sphere") {
    source.primitive = AssetMeshSource::Primitive::Sphere;
    auto radius = numberField(json, "radius", source.radius, context, true);
    if (!radius) return std::unexpected(radius.error());
    if (*radius <= 0) return fail(context + ": sphere 'radius' must be positive");
    source.radius = *radius;
  } else if (primitive == "cylinder") {
    source.primitive = AssetMeshSource::Primitive::Cylinder;
    auto radius = numberField(json, "radius", source.radius, context, true);
    auto height = numberField(json, "height", source.height, context, true);
    if (!radius) return std::unexpected(radius.error());
    if (!height) return std::unexpected(height.error());
    if (*radius <= 0 || *height <= 0) return fail(context + ": cylinder 'radius' and 'height' must be positive");
    source.radius = *radius;
    source.height = *height;
  } else {
    return fail(std::format("{}: unknown primitive '{}'", context, primitive));
  }
  return source;
}

Result<AssetCollisionProxy> collisionFromJson(const Json& json, const std::string& id) {
  const std::string context = std::format("asset '{}': collision", id);
  if (!json.is_object()) return fail(context + " must be an object");
  if (!json.contains("type") || !json["type"].is_string()) return fail(context + ": 'type' is required");

  AssetCollisionProxy proxy;
  if (auto it = json.find("transform"); it != json.end()) {
    auto transform = assetTransformFromJson(*it, context + ".transform");
    if (!transform) return std::unexpected(transform.error());
    proxy.transform = *transform;
  }
  const std::string type = json["type"].get<std::string>();
  if (type == "box") {
    proxy.type = AssetCollisionProxy::Type::Box;
    auto size = vec3Field(json, "size", proxy.size, context);
    if (!size) return std::unexpected(size.error());
    if (!json.contains("size") || !allPositive(*size)) return fail(context + ": box 'size' must be positive");
    proxy.size = *size;
  } else if (type == "sphere") {
    proxy.type = AssetCollisionProxy::Type::Sphere;
    auto radius = numberField(json, "radius", proxy.radius, context, true);
    if (!radius) return std::unexpected(radius.error());
    if (*radius <= 0) return fail(context + ": sphere 'radius' must be positive");
    proxy.radius = *radius;
  } else if (type == "capsule") {
    proxy.type = AssetCollisionProxy::Type::Capsule;
    auto radius = numberField(json, "radius", proxy.radius, context, true);
    auto height = numberField(json, "height", proxy.height, context, true);
    if (!radius) return std::unexpected(radius.error());
    if (!height) return std::unexpected(height.error());
    if (*radius <= 0 || *height < 2 * *radius)
      return fail(context + ": capsule 'radius' must be positive and 'height' must be at least twice the radius");
    proxy.radius = *radius;
    proxy.height = *height;
  } else {
    return fail(std::format("{}: unknown type '{}'", context, type));
  }
  return proxy;
}

}  // namespace

mat4 assetTransformMatrix(const AssetTransform& transform) {
  const vec3 radians = glm::radians(transform.rotationDeg);
  const mat4 rotation = glm::rotate(mat4(1), radians.z, vec3(0, 0, 1)) *
                        glm::rotate(mat4(1), radians.y, vec3(0, 1, 0)) *
                        glm::rotate(mat4(1), radians.x, vec3(1, 0, 0));
  return glm::translate(mat4(1), transform.translation) * rotation * glm::scale(mat4(1), transform.scale);
}

Result<AssetTransform> assetTransformFromJson(const Json& json, std::string_view context) {
  if (!json.is_object()) return fail(std::string(context) + " must be an object");
  AssetTransform transform;
  auto translation = vec3Field(json, "translation", transform.translation, context);
  auto rotation = vec3Field(json, "rotationDeg", transform.rotationDeg, context);
  auto scale = vec3Field(json, "scale", transform.scale, context);
  if (!translation) return std::unexpected(translation.error());
  if (!rotation) return std::unexpected(rotation.error());
  if (!scale) return std::unexpected(scale.error());
  if (!allNonzero(*scale)) return fail(std::format("{}: 'scale' components must be nonzero", context));
  transform.translation = *translation;
  transform.rotationDeg = *rotation;
  transform.scale = *scale;
  return transform;
}

Json assetTransformToJson(const AssetTransform& transform) {
  return {{"translation", toJson(transform.translation)},
          {"rotationDeg", toJson(transform.rotationDeg)},
          {"scale", toJson(transform.scale)}};
}

Result<PropAsset> assetFromJson(const Json& json) {
  if (!json.is_object()) return fail("not a plush.asset file");
  auto format = json.find("format");
  if (format == json.end() || !format->is_string() || format->get<std::string>() != "plush.asset")
    return fail("not a plush.asset file");
  auto version = json.find("version");
  if (version == json.end() || !version->is_number_integer() || *version != 1)
    return fail("unsupported plush.asset version");

  PropAsset asset;
  asset.version = 1;
  if (!json.contains("id") || !json["id"].is_string() || json["id"].get<std::string>().empty())
    return fail("plush.asset: the id field is required");
  asset.id = json["id"].get<std::string>();
  if (!json.contains("licence") || !json["licence"].is_string() || json["licence"].get<std::string>().empty())
    return fail(std::format("asset '{}': the licence field is required", asset.id));
  if (!json.contains("attribution") || !json["attribution"].is_string() ||
      json["attribution"].get<std::string>().empty())
    return fail(std::format("asset '{}': the attribution field is required", asset.id));
  asset.licence = json["licence"].get<std::string>();
  asset.attribution = json["attribution"].get<std::string>();

  if (!json.contains("mesh")) return fail(std::format("asset '{}': the mesh field is required", asset.id));
  auto mesh = meshFromJson(json["mesh"], asset.id);
  if (!mesh) return std::unexpected(mesh.error());
  asset.mesh = *mesh;

  auto scale = numberField(json, "scale", asset.scaleMetres, std::format("asset '{}'", asset.id), true);
  if (!scale) return std::unexpected(scale.error());
  if (*scale <= 0) return fail(std::format("asset '{}': scale must be positive", asset.id));
  asset.scaleMetres = *scale;

  auto materials = json.find("material_presets");
  if (materials == json.end() || !materials->is_array() || materials->empty())
    return fail(std::format("asset '{}': material_presets must be a non-empty array", asset.id));
  std::set<std::string> materialNames;
  for (const Json& material : *materials) {
    if (!material.is_string() || material.get<std::string>().empty())
      return fail(std::format("asset '{}': material preset names must be non-empty strings", asset.id));
    const std::string name = material.get<std::string>();
    if (!materialNames.insert(name).second)
      return fail(std::format("asset '{}': duplicate material preset '{}'", asset.id, name));
    asset.materialPresets.push_back(name);
  }

  if (auto sockets = json.find("sockets"); sockets != json.end()) {
    if (!sockets->is_object()) return fail(std::format("asset '{}': sockets must be an object", asset.id));
    for (auto it = sockets->begin(); it != sockets->end(); ++it) {
      if (it.key().empty()) return fail(std::format("asset '{}': socket names must be non-empty", asset.id));
      auto transform = assetTransformFromJson(it.value(), std::format("asset '{}': socket '{}'", asset.id, it.key()));
      if (!transform) return std::unexpected(transform.error());
      asset.sockets[it.key()] = *transform;
    }
  }

  if (auto collision = json.find("collision"); collision != json.end()) {
    auto proxy = collisionFromJson(*collision, asset.id);
    if (!proxy) return std::unexpected(proxy.error());
    asset.collision = *proxy;
  }
  return asset;
}

Result<PropAsset> loadAsset(const std::filesystem::path& path) {
  auto json = parseJsonFile(path);
  if (!json) return std::unexpected(json.error());
  auto asset = assetFromJson(*json);
  if (!asset) return fail(std::format("{}: {}", path.string(), asset.error().message));
  return asset;
}

}  // namespace plush
