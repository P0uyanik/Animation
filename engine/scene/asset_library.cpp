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

Result<std::string> enumField(const Json& json, const char* key, std::string fallback, std::initializer_list<const char*> allowed,
                              std::string_view context) {
  auto it = json.find(key);
  if (it == json.end()) return fallback;
  if (!it->is_string()) return fail(std::format("{}: '{}' must be a string", context, key));
  const std::string v = it->get<std::string>();
  std::string list;
  for (const char* a : allowed) {
    if (v == a) return v;
    list += std::string(list.empty() ? "" : ", ") + a;
  }
  return fail(std::format("{}: '{}' must be one of {} (got '{}')", context, key, list, v));
}

Result<std::vector<std::string>> stringList(const Json& json, const char* key, std::string_view context) {
  std::vector<std::string> out;
  auto it = json.find(key);
  if (it == json.end()) return out;
  if (!it->is_array()) return fail(std::format("{}: '{}' must be an array of strings", context, key));
  for (const Json& e : *it) {
    if (!e.is_string() || e.get<std::string>().empty())
      return fail(std::format("{}: '{}' must be an array of non-empty strings", context, key));
    out.push_back(e.get<std::string>());
  }
  return out;
}

Result<vec3> unitField(const Json& json, const char* key, vec3 fallback, std::string_view context) {
  auto v = vec3Field(json, key, fallback, context);
  if (!v) return v;
  if (glm::length(*v) < 1e-6f) return fail(std::format("{}: '{}' must not be zero", context, key));
  return glm::normalize(*v);
}

}  // namespace

const GraspSite* PropAffordances::site(const std::string& id) const {
  for (const GraspSite& s : sites)
    if (s.id == id) return &s;
  return nullptr;
}

const GraspSet* PropAffordances::set(const std::string& id) const {
  for (const GraspSet& s : sets)
    if (s.id == id) return &s;
  return nullptr;
}

Result<PropAffordances> affordancesFromJson(const Json& json, const std::map<std::string, AssetTransform>& sockets,
                                            std::string_view ctx) {
  const std::string context(ctx);
#define PLUSH_TRY(var, expr)                         \
  auto var = (expr);                                 \
  if (!var) return std::unexpected(var.error());
  if (!json.is_object()) return fail(context + " must be an object");
  if (!json.contains("format") || !json["format"].is_string() || json["format"].get<std::string>() != "plush.affordances")
    return fail(context + ": 'format' must be \"plush.affordances\"");
  if (!json.contains("version") || !json["version"].is_number_integer() || json["version"] != 1)
    return fail(context + ": unsupported version (expected 1)");
  auto needSocket = [&](const std::string& socket, const std::string& what) -> Result<void> {
    if (!sockets.count(socket)) return fail(std::format("{}: {} names socket '{}', which the asset does not have", context, what, socket));
    return {};
  };
  PropAffordances a;
  PLUSH_TRY(size, enumField(json, "size_class", "", {"hand", "small", "medium", "large"}, context));
  PLUSH_TRY(weight, enumField(json, "weight_class", "light", {"light", "medium", "heavy"}, context));
  PLUSH_TRY(hands, enumField(json, "hands", "either", {"one", "two", "either"}, context));
  a.sizeClass = *size, a.weightClass = *weight, a.hands = *hands;
  if (json.contains("mass_kg")) {
    PLUSH_TRY(mass, numberField(json, "mass_kg", 0, context));
    if (*mass <= 0) return fail(context + ": 'mass_kg' must be positive");
    a.massKg = *mass;
  }
  if (auto it = json.find("pivot"); it != json.end()) {
    if (it->is_string()) {
      a.pivotSocket = it->get<std::string>();
      if (auto r = needSocket(a.pivotSocket, "pivot"); !r) return std::unexpected(r.error());
    } else {
      PLUSH_TRY(pivot, vec3Field(json, "pivot", vec3(0), context));
      a.pivotPoint = *pivot;
    }
  }
  if (auto it = json.find("upright"); it != json.end()) {
    if (!it->is_object()) return fail(context + ": 'upright' must be an object");
    PropAffordances::Upright u;
    PLUSH_TRY(axis, unitField(*it, "axis", u.axis, context + ".upright"));
    PLUSH_TRY(tilt, numberField(*it, "max_tilt_deg", u.maxTiltDeg, context + ".upright", true));
    if (*tilt < 0 || *tilt > 180) return fail(context + ".upright: 'max_tilt_deg' must be in [0, 180]");
    u.axis = *axis, u.maxTiltDeg = *tilt;
    a.upright = u;
  }
  std::set<std::string> siteIds;
  if (auto it = json.find("grasp_sites"); it != json.end()) {
    if (!it->is_array()) return fail(context + ": 'grasp_sites' must be an array");
    for (const Json& j : *it) {
      if (!j.is_object()) return fail(context + ": every grasp site must be an object");
      GraspSite g;
      if (!j.contains("id") || !j["id"].is_string() || j["id"].get<std::string>().empty())
        return fail(context + ": every grasp site needs a non-empty 'id'");
      g.id = j["id"].get<std::string>();
      const std::string sc = std::format("{}: grasp site '{}'", context, g.id);
      if (!siteIds.insert(g.id).second) return fail(std::format("{}: duplicate grasp site id '{}'", context, g.id));
      if (!j.contains("socket") || !j["socket"].is_string()) return fail(sc + ": 'socket' is required");
      g.socket = j["socket"].get<std::string>();
      if (auto r = needSocket(g.socket, std::format("grasp site '{}'", g.id)); !r) return std::unexpected(r.error());
      PLUSH_TRY(hand, enumField(j, "hand", "any", {"L", "R", "any"}, sc));
      PLUSH_TRY(shape, enumField(j, "shape", "wrap", {"wrap", "pinch", "palm", "hook", "cradle"}, sc));
      g.hand = *hand, g.shape = *shape;
      if (j.contains("approach")) {
        PLUSH_TRY(ap, unitField(j, "approach", vec3(0), sc));
        g.approach = *ap;
      }
      if (j.contains("aperture")) {
        PLUSH_TRY(ap, numberField(j, "aperture", 0, sc));
        if (*ap <= 0) return fail(sc + ": 'aperture' must be positive");
        g.aperture = *ap;
      }
      if (j.contains("turnable")) {
        if (!j["turnable"].is_boolean()) return fail(sc + ": 'turnable' must be a boolean");
        g.turnable = j["turnable"].get<bool>();
      }
      if (auto f = j.find("fingers"); f != j.end()) {
        if (!f->is_object()) return fail(sc + ": 'fingers' must be an object");
        PLUSH_TRY(thumb, enumField(*f, "thumb", "", {"opposed", "along", "tucked"}, sc + ".fingers"));
        g.thumb = *thumb;
        if (auto b = f->find("band"); b != f->end()) {
          if (!b->is_array() || b->size() != 2 || !(*b)[0].is_number() || !(*b)[1].is_number())
            return fail(sc + ".fingers: 'band' must be [lo, hi]");
          const vec2 band((*b)[0].get<float>(), (*b)[1].get<float>());
          if (!(band.x < band.y)) return fail(sc + ".fingers: 'band' needs lo < hi");
          g.band = band;
        }
      }
      a.sites.push_back(std::move(g));
    }
  }
  std::set<std::string> setIds;
  if (auto it = json.find("grasp_sets"); it != json.end()) {
    if (!it->is_array()) return fail(context + ": 'grasp_sets' must be an array");
    for (const Json& j : *it) {
      if (!j.is_object()) return fail(context + ": every grasp set must be an object");
      GraspSet g;
      if (!j.contains("id") || !j["id"].is_string() || j["id"].get<std::string>().empty())
        return fail(context + ": every grasp set needs a non-empty 'id'");
      g.id = j["id"].get<std::string>();
      const std::string sc = std::format("{}: grasp set '{}'", context, g.id);
      if (!setIds.insert(g.id).second) return fail(std::format("{}: duplicate grasp set id '{}'", context, g.id));
      PLUSH_TRY(sites, stringList(j, "sites", sc));
      if (sites->empty() || sites->size() > 2) return fail(sc + ": 'sites' must name one or two grasp sites");
      for (const std::string& s : *sites)
        if (!siteIds.count(s)) return fail(std::format("{}: unknown grasp site '{}'", sc, s));
      if (sites->size() == 2 && (*sites)[0] == (*sites)[1]) return fail(sc + ": the two sites must differ");
      g.sites = *sites;
      if (j.contains("simultaneous_frames")) {
        if (!j["simultaneous_frames"].is_number_integer() || j["simultaneous_frames"].get<int>() < 0)
          return fail(sc + ": 'simultaneous_frames' must be a non-negative integer");
        g.simultaneousFrames = j["simultaneous_frames"].get<int>();
      }
      a.sets.push_back(std::move(g));
    }
  }
  if (a.hands == "two" && std::none_of(a.sets.begin(), a.sets.end(), [](const GraspSet& g) { return g.sites.size() == 2; }))
    return fail(context + ": hands \"two\" needs a grasp set of two sites");
  if (a.weightClass == "heavy" && a.hands != "two") return fail(context + ": weight_class \"heavy\" needs hands \"two\"");
  if (auto it = json.find("handover"); it != json.end()) {
    if (!it->is_object()) return fail(context + ": 'handover' must be an object");
    PLUSH_TRY(give, stringList(*it, "give", context + ".handover"));
    PLUSH_TRY(receive, stringList(*it, "receive", context + ".handover"));
    for (const auto* list : {&*give, &*receive})
      for (const std::string& s : *list)
        if (!setIds.count(s)) return fail(std::format("{}.handover: unknown grasp set '{}'", context, s));
    a.handoverGive = *give, a.handoverReceive = *receive;
  }
  if (auto it = json.find("place"); it != json.end()) {
    if (!it->is_object()) return fail(context + ": 'place' must be an object");
    PropAffordances::Place pl;
    if (it->contains("socket")) {
      if (!(*it)["socket"].is_string()) return fail(context + ".place: 'socket' must be a string");
      pl.socket = (*it)["socket"].get<std::string>();
    }
    if (auto r = needSocket(pl.socket, "place"); !r) return std::unexpected(r.error());
    PLUSH_TRY(normal, unitField(*it, "surface_normal", pl.surfaceNormal, context + ".place"));
    PLUSH_TRY(settle, enumField(*it, "settle", "rigid", {"rigid", "soft"}, context + ".place"));
    pl.surfaceNormal = *normal, pl.settle = *settle;
    a.place = pl;
  }
  if (auto it = json.find("push_pull"); it != json.end()) {
    if (!it->is_object()) return fail(context + ": 'push_pull' must be an object");
    PropAffordances::PushPull pp;
    PLUSH_TRY(axis, unitField(*it, "axis", pp.axis, context + ".push_pull"));
    PLUSH_TRY(sites, stringList(*it, "sites", context + ".push_pull"));
    PLUSH_TRY(friction, enumField(*it, "friction", "slide", {"slide", "tip"}, context + ".push_pull"));
    for (const std::string& s : *sites)
      if (!siteIds.count(s)) return fail(std::format("{}.push_pull: unknown grasp site '{}'", context, s));
    pp.axis = *axis, pp.sites = *sites, pp.friction = *friction;
    a.pushPull = pp;
  }
  if (auto it = json.find("deform"); it != json.end()) {
    if (!it->is_object()) return fail(context + ": 'deform' must be an object");
    PLUSH_TRY(mode, enumField(*it, "mode", "rigid", {"rigid", "squash", "bend", "fold"}, context + ".deform"));
    PLUSH_TRY(squash, numberField(*it, "squash", 0, context + ".deform"));
    if (*squash < 0 || *squash > 1) return fail(context + ".deform: 'squash' must be in [0, 1]");
    a.deform = *mode, a.squash = *squash;
  }
#undef PLUSH_TRY
  return a;
}

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

  // T-112a: optional affordances. An invalid block never fails the asset (the primitives do not read it); it is kept
  // with its error, and a verb action on the prop fails with it.
  if (auto aff = json.find("affordances"); aff != json.end()) {
    auto parsed = affordancesFromJson(*aff, asset.sockets, std::format("asset '{}': affordances", asset.id));
    if (parsed) {
      asset.affordances = std::move(*parsed);
    } else {
      asset.affordances = PropAffordances{};
      asset.affordances->error = parsed.error().message;
    }
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
