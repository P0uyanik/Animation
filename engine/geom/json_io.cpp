#include "geom/json_io.h"

#include <map>

namespace plush {

vec3 readVec3(const Json& j, const char* key, vec3 fallback) {
  auto it = j.find(key);
  if (it == j.end()) return fallback;
  if (it->is_number()) return vec3(it->get<float>());
  if (it->is_array() && it->size() == 3) return vec3((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
  return fallback;
}
vec4 readVec4(const Json& j, const char* key, vec4 fallback) {
  auto it = j.find(key);
  if (it == j.end() || !it->is_array() || it->size() != 4) return fallback;
  return vec4((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>(), (*it)[3].get<float>());
}
float readFloat(const Json& j, const char* key, float fallback) {
  auto it = j.find(key);
  return (it != j.end() && it->is_number()) ? it->get<float>() : fallback;
}
int readInt(const Json& j, const char* key, int fallback) {
  auto it = j.find(key);
  return (it != j.end() && it->is_number()) ? it->get<int>() : fallback;
}
bool readBool(const Json& j, const char* key, bool fallback) {
  auto it = j.find(key);
  return (it != j.end() && it->is_boolean()) ? it->get<bool>() : fallback;
}
std::string readString(const Json& j, const char* key, const std::string& fallback) {
  auto it = j.find(key);
  return (it != j.end() && it->is_string()) ? it->get<std::string>() : fallback;
}
Json toJson(vec3 v) { return Json::array({v.x, v.y, v.z}); }
Json toJson(vec4 v) { return Json::array({v.x, v.y, v.z, v.w}); }

namespace {
const std::map<std::string, MaterialType> kMaterialTypes = {
    {"standard", MaterialType::Standard}, {"plush", MaterialType::Plush}, {"fiber", MaterialType::Fiber}, {"glass", MaterialType::Glass}};
const std::map<std::string, TextureType> kTextureTypes = {
    {"none", TextureType::None}, {"noise", TextureType::Noise}, {"wood", TextureType::Wood}, {"wall", TextureType::Wall},
    {"iris", TextureType::Iris}, {"blush", TextureType::Blush}, {"knit", TextureType::Knit}};
template <class E>
std::string enumName(const std::map<std::string, E>& table, E value) {
  for (auto& [k, v] : table)
    if (v == value) return k;
  return "?";
}
}  // namespace

Result<Material> materialFromJson(const Json& j) {
  Material m;
  m.name = readString(j, "name");
  std::string type = readString(j, "type", "standard");
  auto t = kMaterialTypes.find(type);
  if (t == kMaterialTypes.end()) return fail(std::format("material '{}': unknown type '{}'", m.name, type));
  m.type = t->second;
  m.baseColor = readVec3(j, "baseColor", m.baseColor);
  m.roughness = readFloat(j, "roughness", m.roughness);
  m.ior = readFloat(j, "ior", m.ior);
  m.specular = readFloat(j, "specular", m.specular);
  m.coat = readFloat(j, "coat", m.coat);
  m.coatRoughness = readFloat(j, "coatRoughness", m.coatRoughness);
  m.sheen = readFloat(j, "sheen", m.sheen);
  m.sheenColor = readVec3(j, "sheenColor", m.sheenColor);
  m.sheenRoughness = readFloat(j, "sheenRoughness", m.sheenRoughness);
  m.betaM = readFloat(j, "betaM", m.betaM);
  m.betaN = readFloat(j, "betaN", m.betaN);
  m.alphaDeg = readFloat(j, "alphaDeg", m.alphaDeg);
  m.thin = readBool(j, "thin", m.thin);
  m.subsurface = std::clamp(readFloat(j, "subsurface", m.subsurface), 0.0f, 1.0f);
  m.subsurfaceRadius = glm::max(readVec3(j, "subsurfaceRadius", m.subsurfaceRadius), vec3(1e-5f));
  m.castsShadow = readBool(j, "castsShadow", m.type != MaterialType::Glass);
  if (auto it = j.find("texture"); it != j.end()) {
    const Json& tj = *it;
    std::string tt = readString(tj, "type", "none");
    auto tex = kTextureTypes.find(tt);
    if (tex == kTextureTypes.end()) return fail(std::format("material '{}': unknown texture '{}'", m.name, tt));
    m.texture.type = tex->second;
    m.texture.color2 = readVec3(tj, "color2", m.texture.color2);
    m.texture.color3 = readVec3(tj, "color3", m.texture.color3);
    m.texture.scale = readFloat(tj, "scale", m.texture.scale);
    m.texture.amount = readFloat(tj, "amount", m.texture.amount);
    m.texture.params = readVec4(tj, "params", m.texture.params);
    if (auto sp = tj.find("spots"); sp != tj.end() && sp->is_array())
      for (auto& s : *sp)
        if (s.is_array() && s.size() == 4) m.texture.spots.emplace_back(s[0].get<float>(), s[1].get<float>(), s[2].get<float>(), s[3].get<float>());
  }
  return m;
}

Json materialToJson(const Material& m) {
  Json j = {{"name", m.name}, {"type", enumName(kMaterialTypes, m.type)}, {"baseColor", toJson(m.baseColor)},
            {"roughness", m.roughness}, {"ior", m.ior}, {"specular", m.specular}, {"coat", m.coat},
            {"coatRoughness", m.coatRoughness}, {"sheen", m.sheen}, {"sheenColor", toJson(m.sheenColor)},
            {"sheenRoughness", m.sheenRoughness}, {"betaM", m.betaM}, {"betaN", m.betaN}, {"alphaDeg", m.alphaDeg}, {"thin", m.thin}, {"castsShadow", m.castsShadow}};
  if (m.subsurface > 0) {
    j["subsurface"] = m.subsurface;
    j["subsurfaceRadius"] = toJson(m.subsurfaceRadius);
  }
  if (m.texture.type != TextureType::None) {
    Json spots = Json::array();
    for (auto& s : m.texture.spots) spots.push_back(toJson(s));
    j["texture"] = {{"type", enumName(kTextureTypes, m.texture.type)}, {"color2", toJson(m.texture.color2)},
                    {"color3", toJson(m.texture.color3)}, {"scale", m.texture.scale}, {"amount", m.texture.amount},
                    {"params", toJson(m.texture.params)}, {"spots", spots}};
  }
  return j;
}

Result<Light> lightFromJson(const Json& j) {
  Light l;
  std::string type = readString(j, "type", "sun");
  if (type == "sun") l.type = Light::Type::Sun;
  else if (type == "rect") l.type = Light::Type::Rect;
  else if (type == "sky") l.type = Light::Type::Sky;
  else return fail(std::format("unknown light type '{}'", type));
  l.color = readVec3(j, "color", l.color);
  l.intensity = readFloat(j, "intensity", l.intensity);
  l.direction = glm::normalize(readVec3(j, "direction", l.direction));
  l.angleDeg = readFloat(j, "angleDeg", l.angleDeg);
  l.corner = readVec3(j, "corner", l.corner);
  l.edgeU = readVec3(j, "edgeU", l.edgeU);
  l.edgeV = readVec3(j, "edgeV", l.edgeV);
  return l;
}

Json lightToJson(const Light& l) {
  const char* names[] = {"sun", "rect", "sky"};
  return {{"type", names[int(l.type)]}, {"color", toJson(l.color)}, {"intensity", l.intensity},
          {"direction", toJson(l.direction)}, {"angleDeg", l.angleDeg}, {"corner", toJson(l.corner)},
          {"edgeU", toJson(l.edgeU)}, {"edgeV", toJson(l.edgeV)}};
}

Camera cameraFromJson(const Json& j) {
  Camera c;
  c.position = readVec3(j, "position", c.position);
  c.target = readVec3(j, "target", c.target);
  c.focalMm = readFloat(j, "focalMm", c.focalMm);
  c.sensorWidthMm = readFloat(j, "sensorWidthMm", c.sensorWidthMm);
  c.fStop = readFloat(j, "fStop", c.fStop);
  c.focusDistance = readFloat(j, "focusDistance", c.focusDistance);
  c.blades = readInt(j, "blades", c.blades);
  c.bladeRotationDeg = readFloat(j, "bladeRotationDeg", c.bladeRotationDeg);
  return c;
}

Json cameraToJson(const Camera& c) {
  return {{"position", toJson(c.position)}, {"target", toJson(c.target)}, {"focalMm", c.focalMm},
          {"sensorWidthMm", c.sensorWidthMm}, {"fStop", c.fStop}, {"focusDistance", c.focusDistance},
          {"blades", c.blades}, {"bladeRotationDeg", c.bladeRotationDeg}};
}

RenderSettings renderSettingsFromJson(const Json& j) {
  RenderSettings r;
  r.width = readInt(j, "width", r.width);
  r.height = readInt(j, "height", r.height);
  r.spp = readInt(j, "spp", r.spp);
  r.maxDepth = readInt(j, "maxDepth", r.maxDepth);
  r.exposureEV = readFloat(j, "exposureEV", r.exposureEV);
  r.denoise = readBool(j, "denoise", r.denoise);
  r.denoiseBlend = readFloat(j, "denoiseBlend", r.denoiseBlend);
  r.seed = uint32_t(readInt(j, "seed", int(r.seed)));
  r.clamp = readFloat(j, "clamp", r.clamp);
  r.adaptiveThreshold = readFloat(j, "adaptiveThreshold", r.adaptiveThreshold);
  return r;
}

Json renderSettingsToJson(const RenderSettings& r) {
  return {{"width", r.width}, {"height", r.height}, {"spp", r.spp}, {"maxDepth", r.maxDepth},
          {"exposureEV", r.exposureEV}, {"denoise", r.denoise}, {"denoiseBlend", r.denoiseBlend}, {"seed", r.seed}, {"clamp", r.clamp}, {"adaptiveThreshold", r.adaptiveThreshold}};
}

Result<Json> parseJsonFile(const std::filesystem::path& path) {
  auto text = readTextFile(path);
  if (!text) return std::unexpected(text.error());
  Json j = Json::parse(*text, nullptr, false, true);
  if (j.is_discarded()) return fail(std::format("'{}' is not valid JSON", path.string()));
  return j;
}

}  // namespace plush
