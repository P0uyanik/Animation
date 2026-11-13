// JSON (de)serialization of the shared data model.
#pragma once
#include <nlohmann/json.hpp>

#include "core/core.h"
#include "geom/geometry.h"

namespace plush {
using Json = nlohmann::json;

vec3 readVec3(const Json& j, const char* key, vec3 fallback);
vec4 readVec4(const Json& j, const char* key, vec4 fallback);
float readFloat(const Json& j, const char* key, float fallback);
int readInt(const Json& j, const char* key, int fallback);
bool readBool(const Json& j, const char* key, bool fallback);
std::string readString(const Json& j, const char* key, const std::string& fallback = {});
Json toJson(vec3 v);
Json toJson(vec4 v);

Result<Material> materialFromJson(const Json& j);
Json materialToJson(const Material& m);
Result<Light> lightFromJson(const Json& j);
Json lightToJson(const Light& l);
Camera cameraFromJson(const Json& j);
Json cameraToJson(const Camera& c);
RenderSettings renderSettingsFromJson(const Json& j);
Json renderSettingsToJson(const RenderSettings& r);

Result<Json> parseJsonFile(const std::filesystem::path& path);

}  // namespace plush
