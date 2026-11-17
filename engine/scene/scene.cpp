#include "scene/scene.h"

#include "model/imported_character.h"

#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <set>

#include <glm/gtx/matrix_decompose.hpp>

namespace plush {

namespace {
Result<ObjectDesc> objectFromJson(const Json& j) {
  ObjectDesc o;
  o.name = readString(j, "name");
  std::string kind = readString(j, "kind", "box");
  if (kind == "box") o.kind = ObjectDesc::Kind::Box;
  else if (kind == "sdf") o.kind = ObjectDesc::Kind::Sdf;
  else if (kind == "paperBoat") o.kind = ObjectDesc::Kind::PaperBoat;
  else if (kind == "water") o.kind = ObjectDesc::Kind::Water;
  else return fail(std::format("object '{}': unknown kind '{}'", o.name, kind));
  o.material = readString(j, "material");
  o.boxMin = readVec3(j, "min", o.boxMin);
  o.boxMax = readVec3(j, "max", o.boxMax);
  o.position = readVec3(j, "position", o.position);
  o.yawDeg = readFloat(j, "yawDeg", o.yawDeg);
  o.scale = readFloat(j, "scale", o.scale);
  if (auto it = j.find("part"); it != j.end()) {
    auto part = partFromJson(*it);
    if (!part) return fail(std::format("object '{}': {}", o.name, part.error().message));
    o.part = *part;
    if (o.part.material.empty()) o.part.material = o.material;
  }
  if (auto it = j.find("fuzz"); it != j.end()) {
    FuzzLayer f;
    f.material = readString(*it, "material", o.material);
    f.params.density = readFloat(*it, "density", f.params.density);
    f.params.length = readFloat(*it, "length", f.params.length);
    f.params.lengthJitter = readFloat(*it, "lengthJitter", f.params.lengthJitter);
    f.params.radius = readFloat(*it, "radius", f.params.radius);
    f.params.tilt = readFloat(*it, "tilt", f.params.tilt);
    f.params.curl = readFloat(*it, "curl", f.params.curl);
    f.params.segments = readInt(*it, "segments", f.params.segments);
    f.params.seed = uint32_t(readInt(*it, "seed", int(f.params.seed)));
    o.fuzz = f;
  }
  if (auto it = j.find("water"); it != j.end()) {
    vec3 hs = readVec3(*it, "halfSize", vec3(0.3f, 0, 0.2f));
    o.waterHalfSize = vec2(hs.x, hs.z);
    o.waterResolution = readInt(*it, "resolution", o.waterResolution);
    for (auto& r : it->value("ripples", Json::array()))
      if (r.is_array() && r.size() == 4) o.ripples.emplace_back(r[0].get<float>(), r[1].get<float>(), r[2].get<float>(), r[3].get<float>());
  }
  if (auto it = j.find("float"); it != j.end()) {
    o.floatOn = readString(*it, "on");
    o.floatFrame = readFloat(*it, "frame", 0);
  }
  if (auto it = j.find("attach"); it != j.end()) {
    o.attachTo = readString(*it, "to");
    o.attachFrame = readFloat(*it, "frame", 0);
    o.releaseFrame = readFloat(*it, "release", 1e9f);
  }
  return o;
}

mat4 objectMatrixLocal(vec3 pos, float yawDeg, float scale) {
  return glm::translate(mat4(1), pos) * glm::rotate(mat4(1), glm::radians(yawDeg), vec3(0, 1, 0)) *
         glm::scale(mat4(1), vec3(scale));
}

mat4 blendTransforms(const mat4& worldPlacement, const mat4& attachedPlacement, float weight) {
  if (weight <= 0) return worldPlacement;
  if (weight >= 1) return attachedPlacement;
  vec3 scaleA, translationA, skewA, scaleB, translationB, skewB;
  vec4 perspectiveA, perspectiveB;
  quat rotationA, rotationB;
  if (glm::decompose(worldPlacement, scaleA, rotationA, translationA, skewA, perspectiveA) &&
      glm::decompose(attachedPlacement, scaleB, rotationB, translationB, skewB, perspectiveB)) {
    rotationA = glm::normalize(rotationA);
    rotationB = glm::normalize(rotationB);
    if (glm::dot(rotationA, rotationB) < 0) rotationB = -rotationB;
    return glm::translate(mat4(1), glm::mix(translationA, translationB, weight)) *
           glm::mat4_cast(glm::normalize(glm::slerp(rotationA, rotationB, weight))) *
           glm::scale(mat4(1), glm::mix(scaleA, scaleB, weight));
  }
  return worldPlacement * (1.0f - weight) + attachedPlacement * weight;
}

std::shared_ptr<Mesh> transformMesh(const Mesh& src, const mat4& m) {
  auto out = std::make_shared<Mesh>();
  out->indices = src.indices;
  out->pref = src.pref.empty() ? src.positions : src.pref;
  out->positions.resize(src.positions.size());
  out->normals.resize(src.normals.size());
  mat3 nm = glm::transpose(glm::inverse(mat3(m)));
  for (size_t i = 0; i < src.positions.size(); ++i) out->positions[i] = vec3(m * vec4(src.positions[i], 1));
  for (size_t i = 0; i < src.normals.size(); ++i) out->normals[i] = glm::normalize(nm * src.normals[i]);
  return out;
}

Result<PropAsset> loadSceneAsset(const std::filesystem::path& scenePath, const std::string& id) {
  for (auto dir = std::filesystem::absolute(scenePath).parent_path();; dir = dir.parent_path()) {
    const auto assetDir = dir / "content" / "assets";
    std::error_code error;
    if (std::filesystem::is_directory(assetDir, error)) {
      std::vector<std::filesystem::path> files;
      for (std::filesystem::directory_iterator it(assetDir, error), end; !error && it != end; it.increment(error)) {
        if (it->is_regular_file() && it->path().filename().string().ends_with(".asset.json"))
          files.push_back(it->path());
      }
      std::sort(files.begin(), files.end());
      for (const auto& file : files) {
        auto json = parseJsonFile(file);
        if (!json || !json->is_object()) continue;
        auto assetId = json->find("id");
        if (assetId == json->end() || !assetId->is_string() || assetId->get<std::string>() != id) continue;
        auto asset = assetFromJson(*json);
        if (!asset) return fail(std::format("{}: {}", file.string(), asset.error().message));
        return asset;
      }
    }
    if (dir == dir.parent_path()) break;
  }
  return fail(std::format("asset '{}' not found in content/assets above {}", id, scenePath.string()));
}
}  // namespace

mat4 objectMatrix(vec3 pos, float yawDeg, float scale) { return objectMatrixLocal(pos, yawDeg, scale); }

Result<Scene> loadScene(const std::filesystem::path& path) {
  auto jr = parseJsonFile(path);
  if (!jr) return std::unexpected(jr.error());
  const Json& j = *jr;
  if (readString(j, "format") != "plush.scene") return fail(std::format("{}: not a plush.scene file", path.string()));
  if (readInt(j, "version", 0) != 1) return fail(std::format("{}: unsupported scene version", path.string()));
  Scene s;
  s.path = path;
  s.name = readString(j, "name", path.stem().string());
  if (auto it = j.find("frameRate"); it != j.end() && it->is_array() && it->size() == 2)
    s.rate = FrameRate{(*it)[0].get<int>(), (*it)[1].get<int>()};
  s.frameStart = readInt(j, "frameStart", s.frameStart);
  s.frameEnd = readInt(j, "frameEnd", s.frameEnd);
  if (auto it = j.find("render"); it != j.end()) s.render = renderSettingsFromJson(*it);
  if (auto it = j.find("camera"); it != j.end()) s.camera = cameraFromJson(*it);
  for (auto& mj : j.value("materials", Json::array())) {
    auto m = materialFromJson(mj);
    if (!m) return fail(std::format("{}: {}", path.string(), m.error().message));
    s.materials.push_back(*m);
  }
  for (auto& lj : j.value("lights", Json::array())) {
    auto l = lightFromJson(lj);
    if (!l) return fail(std::format("{}: {}", path.string(), l.error().message));
    s.lights.push_back(*l);
  }
  for (auto& oj : j.value("objects", Json::array())) {
    auto o = objectFromJson(oj);
    if (!o) return fail(std::format("{}: {}", path.string(), o.error().message));
    s.objects.push_back(*o);
  }
  const auto readPropParent = [&](const Json& parentJson, const std::string& propName,
                                  std::string_view field) -> Result<std::optional<PropParent>> {
    if (parentJson.is_null()) return std::optional<PropParent>{};
    if (!parentJson.is_object())
      return fail(std::format("{}: prop '{}': {} must be an object or null", path.string(), propName, field));
    PropParent parent;
    const auto requireString = [&](const char* member) -> Result<std::string> {
      auto value = parentJson.find(member);
      if (value == parentJson.end() || !value->is_string() || value->get<std::string>().empty())
        return fail(std::format("{}: prop '{}': {}.{} must be a non-empty string", path.string(), propName, field,
                                member));
      return value->get<std::string>();
    };
    auto kind = requireString("kind");
    if (!kind) return std::unexpected(kind.error());
    if (*kind == "character") parent.kind = PropParent::Kind::Character;
    else if (*kind == "prop") parent.kind = PropParent::Kind::Prop;
    else
      return fail(std::format("{}: prop '{}': {}.kind must be 'character' or 'prop'", path.string(), propName,
                              field));
    auto parentName = requireString("name");
    if (!parentName) return std::unexpected(parentName.error());
    parent.name = std::move(*parentName);
    auto socket = requireString("socket");
    if (!socket) return std::unexpected(socket.error());
    parent.socket = std::move(*socket);
    return std::optional<PropParent>{std::move(parent)};
  };
  for (const auto& pj : j.value("props", Json::array())) {
    if (!pj.is_object()) return fail(std::format("{}: prop must be an object", path.string()));
    PropDesc prop;
    if (!pj.contains("name") || !pj["name"].is_string() || pj["name"].get<std::string>().empty())
      return fail(std::format("{}: prop name is required", path.string()));
    prop.name = pj["name"].get<std::string>();
    if (!pj.contains("id") || !pj["id"].is_string() || pj["id"].get<std::string>().empty())
      return fail(std::format("{}: prop '{}': id is required", path.string(), prop.name));
    prop.id = pj["id"].get<std::string>();
    if (!pj.contains("transform"))
      return fail(std::format("{}: prop '{}': transform is required", path.string(), prop.name));
    auto transform = assetTransformFromJson(pj["transform"], std::format("prop '{}' transform", prop.name));
    if (!transform) return fail(std::format("{}: {}", path.string(), transform.error().message));
    prop.transform = *transform;
    if (auto parentJson = pj.find("parent"); parentJson != pj.end()) {
      auto parent = readPropParent(*parentJson, prop.name, "parent");
      if (!parent) return std::unexpected(parent.error());
      prop.parent = std::move(*parent);
    }
    if (auto switches = pj.find("parentSwitch"); switches != pj.end()) {
      if (!switches->is_array())
        return fail(std::format("{}: prop '{}': parentSwitch must be an array", path.string(), prop.name));
      for (size_t i = 0; i < switches->size(); ++i) {
        const Json& entry = (*switches)[i];
        if (!entry.is_object() || !entry.contains("frame") || !entry["frame"].is_number() ||
            !std::isfinite(entry["frame"].get<double>()))
          return fail(std::format("{}: prop '{}': parentSwitch[{}].frame must be a finite number", path.string(),
                                  prop.name, i));
        if (!entry.contains("parent"))
          return fail(std::format("{}: prop '{}': parentSwitch[{}].parent is required", path.string(), prop.name,
                                  i));
        auto parent = readPropParent(entry["parent"], prop.name, std::format("parentSwitch[{}].parent", i));
        if (!parent) return std::unexpected(parent.error());
        prop.parentSwitch.push_back({entry["frame"].get<double>(), std::move(*parent)});
      }
      std::stable_sort(prop.parentSwitch.begin(), prop.parentSwitch.end(),
                       [](const PropParentSwitch& a, const PropParentSwitch& b) { return a.frame < b.frame; });
      for (size_t i = 1; i < prop.parentSwitch.size(); ++i)
        if (prop.parentSwitch[i - 1].frame == prop.parentSwitch[i].frame)
          return fail(std::format("{}: prop '{}': parentSwitch has duplicate frame {}", path.string(), prop.name,
                                  prop.parentSwitch[i].frame));
    }
    s.props.push_back(std::move(prop));
  }
  for (auto& cj : j.value("characters", Json::array())) {
    CharacterDesc cd{readString(cj, "name"), readString(cj, "asset"), readVec3(cj, "position", vec3(0)),
                     readFloat(cj, "yawDeg", 0), {}};
    cd.autoIdle = readBool(cj, "autoIdle", true);
    cd.life.seed = uint32_t(std::hash<std::string>{}(cd.name) & 0xffffffffu) | 1u;
    if (auto it = cj.find("life"); it != cj.end()) {
      if (it->is_boolean()) cd.life.enabled = it->get<bool>();
      if (it->is_object()) {
        cd.life.enabled = readBool(*it, "enabled", true);
        cd.life.breathing = readFloat(*it, "breathing", cd.life.breathing);
        cd.life.sway = readFloat(*it, "sway", cd.life.sway);
        cd.life.headDrift = readFloat(*it, "headDrift", cd.life.headDrift);
        cd.life.blinkIntervalSet = it->contains("blinkInterval");
        cd.life.blinkInterval = readFloat(*it, "blinkInterval", cd.life.blinkInterval);
        cd.life.headFollow = readFloat(*it, "headFollow", cd.life.headFollow);
        cd.life.headLagSec = readFloat(*it, "headLagSec", cd.life.headLagSec);
        if (auto gaze = it->find("gaze"); gaze != it->end() && gaze->is_object()) {
          cd.life.gaze.maxUpDeg = readFloat(*gaze, "maxUpDeg", cd.life.gaze.maxUpDeg);
          cd.life.gaze.maxDownDeg = readFloat(*gaze, "maxDownDeg", cd.life.gaze.maxDownDeg);
          cd.life.gaze.maxLeftDeg = readFloat(*gaze, "maxLeftDeg", cd.life.gaze.maxLeftDeg);
          cd.life.gaze.maxRightDeg = readFloat(*gaze, "maxRightDeg", cd.life.gaze.maxRightDeg);
        }
      }
    }
    cd.dynamics = cj.value("dynamics", Json());
    s.characters.push_back(cd);
  }
  std::map<std::string, size_t> propsByName;
  for (size_t i = 0; i < s.props.size(); ++i) {
    const auto& name = s.props[i].name;
    if (!propsByName.emplace(name, i).second)
      return fail(std::format("{}: prop name '{}' is not unique", path.string(), name));
  }
  std::set<std::string> characterNames;
  for (const auto& character : s.characters) characterNames.insert(character.name);
  const auto forEachParent = [](const PropDesc& prop, const auto& fn) {
    if (prop.parent) fn(*prop.parent);
    for (const auto& sw : prop.parentSwitch)
      if (sw.parent) fn(*sw.parent);
  };
  for (const auto& prop : s.props) {
    std::optional<Error> error;
    forEachParent(prop, [&](const PropParent& parent) {
      if (error) return;
      if (parent.kind == PropParent::Kind::Character) {
        if (!characterNames.contains(parent.name))
          error = Error{std::format("{}: prop '{}': parent character '{}' does not exist", path.string(), prop.name,
                                    parent.name)};
      } else if (!propsByName.contains(parent.name)) {
        error = Error{std::format("{}: prop '{}': parent prop '{}' does not exist", path.string(), prop.name,
                                  parent.name)};
      }
    });
    if (error) return std::unexpected(*error);
  }
  const auto parentAt = [&](size_t propIndex, double frame) -> std::optional<PropParent> {
    std::optional<PropParent> parent = s.props[propIndex].parent;
    for (const auto& sw : s.props[propIndex].parentSwitch) {
      if (sw.frame > frame) break;
      parent = sw.parent;
    }
    return parent;
  };
  std::vector<double> parentGraphFrames{-std::numeric_limits<double>::infinity()};
  for (const auto& prop : s.props)
    for (const auto& sw : prop.parentSwitch) parentGraphFrames.push_back(sw.frame);
  std::sort(parentGraphFrames.begin(), parentGraphFrames.end());
  parentGraphFrames.erase(std::unique(parentGraphFrames.begin(), parentGraphFrames.end()), parentGraphFrames.end());
  for (double graphFrame : parentGraphFrames) {
    for (size_t start = 0; start < s.props.size(); ++start) {
      std::set<size_t> chain;
      size_t current = start;
      for (;;) {
        const auto parent = parentAt(current, graphFrame);
        if (!parent || parent->kind != PropParent::Kind::Prop) break;
        if (!chain.insert(current).second)
          return fail(std::format("{}: prop parent cycle includes '{}' at frame {}", path.string(),
                                  s.props[current].name, graphFrame));
        current = propsByName.at(parent->name);
      }
    }
  }
  std::map<std::string, PropAsset> assetsById;
  for (const auto& prop : s.props) {
    std::optional<Error> error;
    forEachParent(prop, [&](const PropParent& parent) {
      if (error || parent.kind != PropParent::Kind::Prop) return;
      const PropDesc& parentProp = s.props[propsByName.at(parent.name)];
      auto asset = assetsById.find(parentProp.id);
      if (asset == assetsById.end()) {
        auto loaded = loadSceneAsset(path, parentProp.id);
        if (!loaded) {
          error = Error{std::format("{}: prop '{}': {}", path.string(), prop.name, loaded.error().message)};
          return;
        }
        asset = assetsById.emplace(parentProp.id, std::move(*loaded)).first;
      }
      if (!asset->second.sockets.contains(parent.socket))
        error = Error{std::format("{}: prop '{}': parent prop '{}' asset '{}' has no socket '{}'", path.string(),
                                  prop.name, parentProp.name, parentProp.id, parent.socket)};
    });
    if (error) return std::unexpected(*error);
  }
  if (auto it = j.find("actions"); it != j.end() && it->is_array()) s.actions = *it;
  if (auto it = j.find("director"); it != j.end() && it->is_object()) s.director = *it;
  if (auto it = j.find("animation"); it != j.end() && it->is_object()) {
    for (auto& [track, keys] : it->items()) {
      Track t;
      for (auto& k : keys) {
        if (!k.is_array() || k.size() < 2) return fail(std::format("{}: bad key in track '{}'", path.string(), track));
        Key key;
        key.frame = k[0].get<double>();
        const Json& v = k[1];
        key.value = v.is_number() ? vec3(v.get<float>()) : vec3(v[0].get<float>(), v[1].get<float>(), v[2].get<float>());
        if (k.size() > 2) {
          std::string in = k[2].get<std::string>();
          key.interp = in == "linear" ? Interp::Linear : in == "step" ? Interp::Step : Interp::Smooth;
        }
        t.setKey(key);
      }
      s.animation.tracks[track] = std::move(t);
    }
  }
  return s;
}

Json sceneToJson(const Scene& s) {
  Json j = {{"format", "plush.scene"}, {"version", 1}, {"name", s.name}, {"frameRate", {s.rate.num, s.rate.den}},
            {"frameStart", s.frameStart}, {"frameEnd", s.frameEnd}, {"render", renderSettingsToJson(s.render)},
            {"camera", cameraToJson(s.camera)}};
  Json mats = Json::array(), lights = Json::array(), objs = Json::array(), props = Json::array(), chars = Json::array();
  for (auto& m : s.materials) mats.push_back(materialToJson(m));
  for (auto& l : s.lights) lights.push_back(lightToJson(l));
  for (auto& o : s.objects) {
    const char* kinds[] = {"box", "sdf", "paperBoat", "water"};
    Json oj = {{"name", o.name}, {"kind", kinds[int(o.kind)]}, {"material", o.material}};
    if (o.kind == ObjectDesc::Kind::Box) {
      oj["min"] = toJson(o.boxMin);
      oj["max"] = toJson(o.boxMax);
    } else {
      oj["position"] = toJson(o.position);
      oj["yawDeg"] = o.yawDeg;
      oj["scale"] = o.scale;
    }
    if (o.kind == ObjectDesc::Kind::Sdf) {
      Json prims = Json::array();
      for (auto& p : o.part.prims) prims.push_back(primToJson(p));
      oj["part"] = {{"name", o.part.name}, {"material", o.part.material}, {"voxelSize", o.part.voxelSize}, {"prims", prims}};
    }
    if (!o.attachTo.empty()) oj["attach"] = {{"to", o.attachTo}, {"frame", o.attachFrame}, {"release", o.releaseFrame}};
    if (!o.floatOn.empty()) oj["float"] = {{"on", o.floatOn}, {"frame", o.floatFrame}};
    if (o.kind == ObjectDesc::Kind::Water) {
      Json rip = Json::array();
      for (auto& r : o.ripples) rip.push_back(toJson(r));
      oj["water"] = {{"halfSize", toJson(vec3(o.waterHalfSize.x, 0, o.waterHalfSize.y))}, {"resolution", o.waterResolution}, {"ripples", rip}};
    }
    if (o.fuzz) {
      const FuzzParams& f = o.fuzz->params;
      oj["fuzz"] = {{"material", o.fuzz->material}, {"density", f.density}, {"length", f.length},
                    {"lengthJitter", f.lengthJitter}, {"radius", f.radius}, {"tilt", f.tilt}, {"curl", f.curl},
                    {"segments", f.segments}, {"seed", f.seed}};
    }
    objs.push_back(oj);
  }
  for (const auto& prop : s.props) {
    Json pj = {{"name", prop.name}, {"id", prop.id}, {"transform", assetTransformToJson(prop.transform)}};
    const auto parentJson = [](const PropParent& parent) {
      const char* kind = parent.kind == PropParent::Kind::Character ? "character" : "prop";
      return Json{{"kind", kind}, {"name", parent.name}, {"socket", parent.socket}};
    };
    if (prop.parent) {
      pj["parent"] = parentJson(*prop.parent);
    }
    if (!prop.parentSwitch.empty()) {
      Json switches = Json::array();
      for (const auto& sw : prop.parentSwitch)
        switches.push_back({{"frame", sw.frame}, {"parent", sw.parent ? parentJson(*sw.parent) : Json(nullptr)}});
      pj["parentSwitch"] = std::move(switches);
    }
    props.push_back(std::move(pj));
  }
  for (auto& c : s.characters) {
    Json cj = {{"name", c.name}, {"asset", c.asset}, {"position", toJson(c.position)}, {"yawDeg", c.yawDeg}};
    if (!c.autoIdle) cj["autoIdle"] = false;
    const GazeLimits defaultGaze;
    const bool customGaze = c.life.gaze.maxUpDeg != defaultGaze.maxUpDeg ||
                            c.life.gaze.maxDownDeg != defaultGaze.maxDownDeg ||
                            c.life.gaze.maxLeftDeg != defaultGaze.maxLeftDeg ||
                            c.life.gaze.maxRightDeg != defaultGaze.maxRightDeg;
    if (c.life.enabled || customGaze) {
      Json life = {{"enabled", c.life.enabled},
                   {"gaze", {{"maxUpDeg", c.life.gaze.maxUpDeg}, {"maxDownDeg", c.life.gaze.maxDownDeg},
                             {"maxLeftDeg", c.life.gaze.maxLeftDeg}, {"maxRightDeg", c.life.gaze.maxRightDeg}}}};
      if (c.life.enabled)
        life.update({{"breathing", c.life.breathing}, {"sway", c.life.sway}, {"headDrift", c.life.headDrift},
                     {"blinkInterval", c.life.blinkInterval}, {"headFollow", c.life.headFollow}, {"headLagSec", c.life.headLagSec}});
      cj["life"] = std::move(life);
    }
    if (!c.dynamics.is_null()) cj["dynamics"] = c.dynamics;
    chars.push_back(cj);
  }
  Json anim = Json::object();
  for (auto& [name, track] : s.animation.tracks) {
    Json keys = Json::array();
    for (auto& k : track.keys) {
      const char* in = k.interp == Interp::Linear ? "linear" : k.interp == Interp::Step ? "step" : "smooth";
      keys.push_back({k.frame, toJson(k.value), in});
    }
    anim[name] = keys;
  }
  j["materials"] = mats;
  j["lights"] = lights;
  j["objects"] = objs;
  if (!props.empty()) j["props"] = props;
  j["characters"] = chars;
  j["animation"] = anim;
  if (!s.actions.empty()) j["actions"] = s.actions;
  if (s.director.is_object()) j["director"] = s.director;
  return j;
}

Result<void> saveScene(const Scene& scene, const std::filesystem::path& path) {
  return writeTextFile(path, sceneToJson(scene).dump(2));
}

Mesh makeBoxMesh(vec3 lo, vec3 hi) {
  Mesh m;
  const vec3 n[6] = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
  for (int f = 0; f < 6; ++f) {
    vec3 nn = n[f];
    vec3 u = std::abs(nn.y) > 0.5f ? vec3(1, 0, 0) : vec3(0, 1, 0);
    vec3 v = glm::cross(nn, u);
    vec3 c = 0.5f * (lo + hi), e = 0.5f * (hi - lo);
    uint32_t base = uint32_t(m.positions.size());
    for (int k = 0; k < 4; ++k) {
      float su = (k == 0 || k == 3) ? -1.f : 1.f, sv = (k < 2) ? -1.f : 1.f;
      m.positions.push_back(c + e * (nn + u * su + v * sv));
      m.normals.push_back(nn);
    }
    m.indices.insert(m.indices.end(), {base, base + 1, base + 2, base, base + 2, base + 3});
  }
  m.pref = m.positions;
  return m;
}

Mesh makePaperBoatMesh() {
  // Classic folded paper boat, ~16 cm long, built from flat triangles.
  Mesh m;
  auto tri = [&](vec3 a, vec3 b, vec3 c) {
    vec3 nn = glm::normalize(glm::cross(b - a, c - a));
    uint32_t base = uint32_t(m.positions.size());
    m.positions.insert(m.positions.end(), {a, b, c});
    m.normals.insert(m.normals.end(), {nn, nn, nn});
    m.indices.insert(m.indices.end(), {base, base + 1, base + 2});
  };
  const float L = 0.08f, l = 0.045f, H = 0.032f, W = 0.03f, S = 0.095f;
  for (float side : {1.0f, -1.0f}) {
    vec3 k0(-l, 0.004f, 0), k1(l, 0.004f, 0), t0(-L, H, side * W), t1(L, H, side * W);
    tri(k0, k1, t1);
    tri(k0, t1, t0);
  }
  for (float end : {1.0f, -1.0f}) tri(vec3(end * L, H, W), vec3(end * L, H, -W), vec3(end * l, 0.004f, 0));
  // Sail: two slightly separated layers (folded paper).
  for (float z : {0.0025f, -0.0025f}) {
    tri(vec3(-0.042f, H - 0.004f, z), vec3(0.042f, H - 0.004f, z), vec3(0, S, z * 0.3f));
    tri(vec3(-0.026f, H - 0.004f, z * 3.0f), vec3(0.026f, H - 0.004f, z * 3.0f), vec3(0, S * 0.82f, z * 1.2f));
  }
  m.pref = m.positions;
  return m;
}

int SceneEvaluator::materialIndex(const std::string& name) const {
  auto it = materialIndex_.find(name);
  return it == materialIndex_.end() ? 0 : it->second;
}

Result<void> SceneEvaluator::load(const Scene& scene, const EvalOptions& opt) {
  scene_ = scene;
  for (auto& prop : scene_.props) {
    for (const auto& sw : prop.parentSwitch)
      if (!std::isfinite(sw.frame))
        return fail(std::format("prop '{}': parentSwitch frame must be finite", prop.name));
    std::stable_sort(prop.parentSwitch.begin(), prop.parentSwitch.end(),
                     [](const PropParentSwitch& a, const PropParentSwitch& b) { return a.frame < b.frame; });
    for (size_t i = 1; i < prop.parentSwitch.size(); ++i)
      if (prop.parentSwitch[i - 1].frame == prop.parentSwitch[i].frame)
        return fail(std::format("prop '{}': parentSwitch has duplicate frame {}", prop.name,
                                prop.parentSwitch[i].frame));
  }
  options_ = opt;
  materials_.clear();
  materialIndex_.clear();
  objects_.clear();
  characters_.clear();
  propAssets_.clear();
  auto addMaterial = [&](const Material& m) {
    if (materialIndex_.count(m.name)) return;
    materialIndex_[m.name] = int(materials_.size());
    materials_.push_back(m);
  };
  Material fallback;
  fallback.name = "__default";
  addMaterial(fallback);
  for (auto& m : scene_.materials) addMaterial(m);

  for (auto& cd : scene_.characters) {
    std::filesystem::path p = scene_.path.parent_path() / cd.asset;
    CharacterInstance ci;
    if (isImportedCharacter(p)) {  // rigged meshes from outside the engine (docs/ENGINE_CHARACTER_PACKAGE.md)
      auto ic = loadImportedCharacter(p);
      if (!ic) return std::unexpected(ic.error());
      ci.asset = std::move(ic->asset);
      ci.rig = std::move(ic->rig);
      ci.imported = true;
      for (auto& m : ci.asset.materials) addMaterial(m);
    } else {
      auto asset = loadCharacter(p);
      if (!asset) return std::unexpected(asset.error());
      ci.asset = std::move(*asset);
      for (auto& m : ci.asset.materials) addMaterial(m);
      ci.rig = buildCharacter(ci.asset, BuildOptions{opt.voxelScale, opt.fuzzDensity, opt.fuzz});
    }
    for (auto& sm : ci.rig.meshes) ci.meshMaterial.push_back(materialIndex(sm.material));
    for (auto& f : ci.rig.fuzz) ci.fuzzMaterial.push_back(materialIndex(f.material));
    for (auto& l : ci.rig.locks) {
    ci.lockMaterial.push_back(materialIndex(l.material));
    ci.coreMaterial.push_back(materialIndex(l.coreMaterial.empty() ? l.material : l.coreMaterial));
  }
    characters_.push_back(std::move(ci));
  }
  for (const auto& prop : scene_.props) {
    auto asset = loadSceneAsset(scene_.path, prop.id);
    if (!asset) return fail(std::format("prop '{}': {}", prop.name, asset.error().message));
    propAssets_.push_back(std::move(*asset));
  }
  for (auto& o : scene_.objects) {
    ObjectGeometry g;
    g.material = materialIndex(o.material);
    switch (o.kind) {
      case ObjectDesc::Kind::Box: g.local = std::make_shared<Mesh>(makeBoxMesh(o.boxMin, o.boxMax)); break;
      case ObjectDesc::Kind::PaperBoat: g.local = std::make_shared<Mesh>(makePaperBoatMesh()); break;
      case ObjectDesc::Kind::Water: g.local = std::make_shared<Mesh>(); break;  // rebuilt per frame
      case ObjectDesc::Kind::Sdf: g.local = std::make_shared<Mesh>(meshSdfPart(o.part, opt.voxelScale)); break;
    }
    if (o.fuzz && opt.fuzz) {
      g.fuzz = generateSurfaceFibers(*g.local, o.fuzz->params, opt.fuzzDensity);
      g.fuzzMaterial = materialIndex(o.fuzz->material);
    }
    objects_.push_back(std::move(g));
  }
  authoredObjects_ = scene_.objects;
  authoredProps_ = scene_.props;
  auto compiled = compileActions();
  if (!compiled) return compiled;
  prepareAutoIdle();
  // Secondary motion after the actions are compiled (action planning sees the kinematic pose).
  dynamics_.assign(characters_.size(), nullptr);
  for (size_t c = 0; c < characters_.size(); ++c) {
    DynamicsSpec spec = characters_[c].asset.dynamics;
    if (auto r = applyDynamicsOverride(spec, scene_.characters[c].dynamics); !r)
      return fail(std::format("character '{}': {}", scene_.characters[c].name, r.error().message));
    // Off: nothing, unless chains rest on an anchor bone (then they are posed statically at their anchored targets).
    const bool anchored = std::any_of(spec.chains.begin(), spec.chains.end(), [](const SpringChain& ch) { return !ch.anchorBone.empty(); });
    if (spec.chains.empty() || (!spec.enabled && !anchored)) continue;
    auto solver = SpringChainSolver::create(characters_[c].asset.skeleton, spec, spec.enabled);
    if (!solver) return fail(std::format("character '{}': {}", scene_.characters[c].name, solver.error().message));
    dynamics_[c] = std::move(*solver);
  }

  std::map<std::string, size_t> charactersByName, propsByName;
  for (size_t c = 0; c < scene_.characters.size(); ++c) charactersByName[scene_.characters[c].name] = c;
  for (size_t p = 0; p < scene_.props.size(); ++p)
    if (!propsByName.emplace(scene_.props[p].name, p).second)
      return fail(std::format("prop name '{}' is not unique", scene_.props[p].name));
  const auto validateParent = [&](const PropDesc& prop, const PropParent& parent) -> Result<void> {
    if (parent.kind == PropParent::Kind::Character) {
      auto character = charactersByName.find(parent.name);
      if (character == charactersByName.end())
        return fail(std::format("prop '{}': parent character '{}' does not exist", prop.name, parent.name));
      if (characterSocketBone(character->second, parent.socket) < 0)
        return fail(std::format("prop '{}': parent character '{}' has no bone or role socket '{}'", prop.name,
                                parent.name, parent.socket));
      return {};
    }
    auto parentProp = propsByName.find(parent.name);
    if (parentProp == propsByName.end())
      return fail(std::format("prop '{}': parent prop '{}' does not exist", prop.name, parent.name));
    const PropAsset& asset = propAssets_[parentProp->second];
    if (!asset.sockets.contains(parent.socket))
      return fail(std::format("prop '{}': parent prop '{}' asset '{}' has no socket '{}'", prop.name, parent.name,
                              asset.id, parent.socket));
    return {};
  };
  for (const auto& prop : scene_.props) {
    if (prop.parent) {
      auto valid = validateParent(prop, *prop.parent);
      if (!valid) return valid;
    }
    for (const auto& sw : prop.parentSwitch)
      if (sw.parent) {
        auto valid = validateParent(prop, *sw.parent);
        if (!valid) return valid;
      }
  }
  const auto parentAt = [&](size_t prop, double frame) -> std::optional<PropParent> {
    std::optional<PropParent> parent = scene_.props[prop].parent;
    for (const auto& sw : scene_.props[prop].parentSwitch)
      if (sw.frame <= frame) parent = sw.parent;
    return parent;
  };
  std::vector<double> graphFrames{-std::numeric_limits<double>::infinity()};
  for (const auto& prop : scene_.props)
    for (const auto& sw : prop.parentSwitch) graphFrames.push_back(sw.frame);
  std::sort(graphFrames.begin(), graphFrames.end());
  graphFrames.erase(std::unique(graphFrames.begin(), graphFrames.end()), graphFrames.end());
  for (double graphFrame : graphFrames)
    for (size_t start = 0; start < scene_.props.size(); ++start) {
      std::set<size_t> chain;
      size_t current = start;
      for (;;) {
        const auto parent = parentAt(current, graphFrame);
        if (!parent || parent->kind != PropParent::Kind::Prop) break;
        if (!chain.insert(current).second)
          return fail(std::format("prop parent cycle includes '{}' at frame {}", scene_.props[current].name,
                                  graphFrame));
        current = propsByName.at(parent->name);
      }
    }
  return {};
}

Result<void> SceneEvaluator::rebuildCharacter(size_t index, const CharacterAsset& asset, const EvalOptions& opt) {
  if (index < characters_.size() && characters_[index].imported) return fail("imported characters are edited in their source pipeline");
  if (index >= characters_.size()) return fail("character index out of range");
  CharacterInstance ci;
  ci.asset = asset;
  if (auto r = resolveBones(ci.asset); !r) return r;
  for (auto& m : ci.asset.materials)
    if (!materialIndex_.count(m.name)) {
      materialIndex_[m.name] = int(materials_.size());
      materials_.push_back(m);
    }
  ci.rig = buildCharacter(ci.asset, BuildOptions{opt.voxelScale, opt.fuzzDensity, opt.fuzz});
  for (auto& sm : ci.rig.meshes) ci.meshMaterial.push_back(materialIndex(sm.material));
  for (auto& f : ci.rig.fuzz) ci.fuzzMaterial.push_back(materialIndex(f.material));
  for (auto& l : ci.rig.locks) {
    ci.lockMaterial.push_back(materialIndex(l.material));
    ci.coreMaterial.push_back(materialIndex(l.coreMaterial.empty() ? l.material : l.coreMaterial));
  }
  characters_[index] = std::move(ci);
  if (index < clearance_.size())  // the arm-body model follows the edited body (T-040 post-pass)
    clearance_[index] = bodyClearanceModel(characters_[index].asset.skeleton, characters_[index].rig.meshes);
  resetDynamics();
  return {};
}

void SceneEvaluator::updateMaterial(const Material& m) {
  auto it = materialIndex_.find(m.name);
  if (it != materialIndex_.end()) materials_[size_t(it->second)] = m;
}

std::vector<mat4> SceneEvaluator::characterGlobals(size_t c, double frame, Pose* poseOut) const {
  std::vector<mat4> g = kinematicGlobals(c, frame, poseOut);
  if (c < dynamics_.size() && dynamics_[c])
    dynamics_[c]->apply(frame, scene_.frameStart, scene_.rate.fps(), [&](double f) { return kinematicGlobals(c, f, nullptr); }, g);
  return g;
}

void SceneEvaluator::resetDynamics() const {
  for (const auto& d : dynamics_)
    if (d) d->reset();
}

std::vector<mat4> SceneEvaluator::kinematicGlobals(size_t c, double frame, Pose* poseOut) const {
  const CharacterDesc& cd = scene_.characters[c];
  const CharacterInstance& ci = characters_[c];
  const Clip& clip = scene_.animation;
  std::string prefix = cd.name + "/";
  vec3 pos = clip.evaluate(cd.name + ".position", frame, cd.position);
  float yaw = clip.evaluate(cd.name + ".yaw", frame, vec3(cd.yawDeg)).x;
  Pose pose = evaluatePose(ci.asset.skeleton, clip, prefix, frame, &ci.asset.defaultPose);
  const bool clips = hasClipLayers(c);  // clip actions (clip_layers.cpp); without them nothing below changes
  if (clips) {
    float clipYaw = 0;
    applyClips(c, frame, pose, clipYaw);
    yaw += clipYaw;
  }
  mat4 world = objectMatrixLocal(pos, yaw, 1.0f);
  // Expression-driven bones (e.g. a jaw opening with the mouth): weight x rotation, from the package metadata.
  for (const auto& [morph, bones] : ci.asset.expressionBones) {
    const float w = expressionWeight(c, morph, frame);
    if (w == 0.0f) continue;
    for (const auto& b : bones) {
      const int bi = ci.asset.skeleton.find(b.bone);
      if (bi >= 0) pose.local[size_t(bi)] = pose.local[size_t(bi)] * glm::angleAxis(glm::radians(b.degrees * w), b.axis);
    }
  }
  LifeParams life = lifeParams(c);
  if (!blinkMorph(ci).empty()) life.blinkLids = false;  // blinks are a morph for this character (see evaluate)
  applyLife(ci.asset.skeleton, clip, prefix, frame, scene_.rate.fps(), world, life, pose);
  applyConstraints(ci.asset.skeleton, clip, prefix, frame, world, pose, life.gaze);
  applyArmPoles(ci.asset.skeleton, clip, prefix, frame, world, pose);          // elbow outward (T-030)
  applyOrientConstraints(ci.asset.skeleton, clip, prefix, frame, world, pose);  // hand-prop interaction (T-022)
  if (clips) applyClipFingers(c, frame, pose);
  // Arms out of the body, whatever moved them (T-040): the last pose step, on the full pose.
  if (armClearance_ && c < clearance_.size() && clearance_[c].valid)
    for (char side : {'L', 'R'}) {
      const std::string hand = ci.asset.skeleton.bones[size_t(clearance_[c].arm[side == 'L' ? 0 : 1].hand)].name;
      auto weightOf = [&](const std::string& track) {
        const Track* t = clip.find(track);
        if (!t || t->keys.empty()) return 0.0f;
        return std::clamp(clip.evaluate(track + ".weight", frame, vec3(1)).x, 0.0f, 1.0f);
      };
      const float pin = weightOf(prefix + "ik." + hand), keep = weightOf(prefix + "orient." + hand);
      applyArmBodyClearance(ci.asset.skeleton, clearance_[c], world, side, pin, keep, pose);
    }
  if (poseOut) *poseOut = pose;
  return boneGlobals(ci.asset.skeleton, pose, world);
}

mat4 SceneEvaluator::objectWorld(size_t i, double frame) const {
  const ObjectDesc& o = scene_.objects[i];
  const Clip& clip = scene_.animation;
  auto base = [&](double f) {
    vec3 pos = clip.evaluate(o.name + ".position", f, o.position);
    float yaw = clip.evaluate(o.name + ".yaw", f, vec3(o.yawDeg)).x;
    return objectMatrixLocal(pos, yaw, o.scale);
  };
  if (o.attachTo.empty() || frame < o.attachFrame) return base(frame);
  auto slash = o.attachTo.find('/');
  std::string charName = o.attachTo.substr(0, slash), boneName = slash == std::string::npos ? "" : o.attachTo.substr(slash + 1);
  for (size_t c = 0; c < characters_.size(); ++c) {
    if (scene_.characters[c].name != charName) continue;
    int bone = characters_[c].asset.skeleton.find(boneName);
    if (bone < 0) break;
    double f = std::min(frame, o.releaseFrame);
    mat4 g0 = characterGlobals(c, o.attachFrame)[size_t(bone)];
    mat4 g1 = characterGlobals(c, f)[size_t(bone)];
    return g1 * glm::inverse(g0) * base(o.attachFrame);
  }
  return base(frame);
}

int SceneEvaluator::characterSocketBone(size_t character, const std::string& socket) const {
  const int direct = characters_[character].asset.skeleton.find(socket);
  if (direct >= 0) return direct;  // imported role bones carry their shared role name
  // The bindings are the same role-to-bone mapping used by clip layer evaluation. Checking all layers makes the
  // resolution independent of which layer happens to be active at the requested frame.
  if (character < clipLayers_.size())
    for (const auto& layer : clipLayers_[character]) {
      const auto role = layer.binding.roleIndex.find(socket);
      if (role == layer.binding.roleIndex.end()) continue;
      const int bone = layer.binding.roles[size_t(role->second)].bone;
      if (bone >= 0) return bone;
    }
  return -1;
}

std::vector<mat4> SceneEvaluator::propWorlds(double frame) const {
  struct PropState {
    std::optional<PropParent> parent;
    mat4 worldPlacement{1};
    mat4 offset{1};
  };
  struct PropPose {
    mat4 world{1};
    mat4 attached{1};
  };
  struct SwitchEvent {
    double frame = 0;
    size_t prop = 0;
    std::optional<PropParent> parent;
  };

  std::map<std::string, size_t> charactersByName, propsByName;
  for (size_t c = 0; c < scene_.characters.size(); ++c) charactersByName[scene_.characters[c].name] = c;
  for (size_t p = 0; p < scene_.props.size(); ++p) propsByName[scene_.props[p].name] = p;
  std::vector<PropState> state(scene_.props.size());
  std::vector<SwitchEvent> events;
  for (size_t p = 0; p < scene_.props.size(); ++p) {
    const mat4 authored = assetTransformMatrix(scene_.props[p].transform);
    state[p] = {scene_.props[p].parent, authored, authored};
    for (const auto& sw : scene_.props[p].parentSwitch) events.push_back({sw.frame, p, sw.parent});
  }
  std::stable_sort(events.begin(), events.end(), [](const SwitchEvent& a, const SwitchEvent& b) {
    if (a.frame != b.frame) return a.frame < b.frame;
    return a.prop < b.prop;
  });

  const auto evaluateState = [&](double at, const std::vector<PropState>& current,
                                 const std::map<size_t, mat4>* overrides = nullptr) {
    std::vector<PropPose> poses(scene_.props.size());
    std::vector<unsigned char> mark(scene_.props.size(), 0);
    std::function<void(size_t)> resolve = [&](size_t prop) {
      if (mark[prop] == 2) return;
      // Parent cycles are rejected by load(); retaining a guard here prevents runaway recursion on a mutated scene.
      if (mark[prop] == 1) {
        poses[prop].world = current[prop].worldPlacement;
        poses[prop].attached = current[prop].worldPlacement;
        mark[prop] = 2;
        return;
      }
      mark[prop] = 1;
      if (overrides) {
        auto overrideWorld = overrides->find(prop);
        if (overrideWorld != overrides->end()) {
          poses[prop] = {overrideWorld->second, overrideWorld->second};
          mark[prop] = 2;
          return;
        }
      }
      const PropState& configured = current[prop];
      poses[prop].attached = configured.worldPlacement;
      if (configured.parent) {
        mat4 socketWorld(1);
        if (configured.parent->kind == PropParent::Kind::Character) {
          const size_t character = charactersByName.at(configured.parent->name);
          const int bone = characterSocketBone(character, configured.parent->socket);
          socketWorld = characterGlobals(character, at)[size_t(bone)];
        } else {
          const size_t parentProp = propsByName.at(configured.parent->name);
          resolve(parentProp);
          socketWorld = poses[parentProp].world *
                        assetTransformMatrix(propAssets_[parentProp].sockets.at(configured.parent->socket));
        }
        poses[prop].attached = socketWorld * configured.offset;
        const float weight = std::clamp(
            scene_.animation.evaluate(scene_.props[prop].name + ".parent.weight", at, vec3(1)).x, 0.0f, 1.0f);
        poses[prop].world = blendTransforms(configured.worldPlacement, poses[prop].attached, weight);
      } else {
        poses[prop].world = configured.worldPlacement;
      }
      mark[prop] = 2;
    };
    for (size_t prop = 0; prop < scene_.props.size(); ++prop) resolve(prop);
    return poses;
  };

  for (size_t first = 0; first < events.size() && events[first].frame <= frame;) {
    size_t last = first + 1;
    while (last < events.size() && events[last].frame == events[first].frame) ++last;
    const double switchFrame = events[first].frame;
    const std::vector<PropPose> before = evaluateState(switchFrame, state);
    std::map<size_t, mat4> continuousWorld;
    std::map<size_t, mat4> continuousAttached;
    for (size_t e = first; e < last; ++e) {
      const size_t prop = events[e].prop;
      continuousWorld[prop] = before[prop].world;
      continuousAttached[prop] = state[prop].parent ? before[prop].attached : before[prop].world;
      state[prop].parent = events[e].parent;
      if (!state[prop].parent) {
        state[prop].worldPlacement = before[prop].world;
        state[prop].offset = before[prop].world;
      }
    }
    // A switched parent is known to keep its old world matrix at the event. These overrides also make simultaneous
    // parent/child switches independent of their authored order.
    for (size_t e = first; e < last; ++e) {
      const size_t prop = events[e].prop;
      if (!state[prop].parent) continue;
      const PropParent& parent = *state[prop].parent;
      mat4 socketWorld(1);
      if (parent.kind == PropParent::Kind::Character) {
        const size_t character = charactersByName.at(parent.name);
        const int bone = characterSocketBone(character, parent.socket);
        socketWorld = characterGlobals(character, switchFrame)[size_t(bone)];
      } else {
        const size_t parentProp = propsByName.at(parent.name);
        auto overridden = continuousWorld.find(parentProp);
        const mat4 parentWorld = overridden != continuousWorld.end()
                                     ? overridden->second
                                     : evaluateState(switchFrame, state, &continuousWorld)[parentProp].world;
        socketWorld = parentWorld * assetTransformMatrix(propAssets_[parentProp].sockets.at(parent.socket));
      }
      state[prop].offset = glm::inverse(socketWorld) * continuousAttached.at(prop);
    }
    first = last;
  }

  const std::vector<PropPose> poses = evaluateState(frame, state);
  std::vector<mat4> worlds;
  worlds.reserve(poses.size());
  for (const auto& pose : poses) worlds.push_back(pose.world);
  return worlds;
}

mat4 SceneEvaluator::propWorld(size_t prop, double frame) const { return propWorlds(frame).at(prop); }

float SceneEvaluator::waterHeight(size_t wi, vec2 p, double frame) const {
  const ObjectDesc& w = scene_.objects[wi];
  float fps = float(scene_.rate.fps());
  float h = 0.0006f * std::sin(p.x * 70.0f + float(frame) * 0.21f) * std::sin(p.y * 55.0f - float(frame) * 0.17f);  // calm ripples
  const float k = kTwoPi / 0.035f, speed = 0.22f;  // 3.5 cm wavelength, 22 cm/s
  for (const vec4& r : w.ripples) {
    float t = (float(frame) - r.z) / fps;
    if (t <= 0) continue;
    float d = glm::length(p - vec2(r.x, r.y));
    float front = speed * t;
    float window = smoothstep01((front - d) / 0.02f + 1.0f) * smoothstep01(1.0f - (front - d) / 0.12f);
    h += r.w * std::exp(-1.2f * t) * std::sin(k * (d - front)) * window / std::sqrt(1.0f + d / 0.02f);
  }
  return h;
}

namespace {
// Flat layout of the paper boat's vertices (the sheet before folding).
vec3 unfoldedPaper(vec3 v) {
  if (std::abs(v.z) < 0.009f && v.y > 0.02f) return vec3(v.x * 1.25f, 0.0012f, v.z * 0.2f);  // sail lies on the sheet
  float s = v.z >= 0 ? 1.0f : -1.0f;
  return vec3(v.x * 1.25f, 0.0006f, s * (std::abs(v.z) + v.y * 1.5f));
}
}  // namespace

// Life parameters of character c: the scene's, with the character's own blink timing where the package has one
// (an explicit scene blinkInterval wins). Characters without timing keep the defaults.
LifeParams SceneEvaluator::lifeParams(size_t c) const {
  LifeParams life = scene_.characters[c].life;
  const CharacterAsset& a = characters_[c].asset;
  if (a.blinkInterval > 0 && !life.blinkIntervalSet) life.blinkInterval = a.blinkInterval;
  if (a.blinkClose > 0) life.blinkClose = a.blinkClose;
  if (a.blinkHold >= 0 && a.blinkClose > 0) life.blinkHold = a.blinkHold;
  if (a.blinkOpen > 0) life.blinkOpen = a.blinkOpen;
  return life;
}

Camera SceneEvaluator::cameraAt(double frame) const {
  const Clip& clip = scene_.animation;
  Camera cam = scene_.camera;
  cam.position = clip.evaluate("camera.position", frame, cam.position);
  cam.target = clip.evaluate("camera.target", frame, cam.target);
  if (const Track* t = clip.find("camera.lens"); t && !t->keys.empty()) {
    vec3 lens = t->evaluate(frame);  // focalMm, fStop, focusDistance
    cam.focalMm = lens.x;
    cam.fStop = lens.y;
    cam.focusDistance = lens.z;
  }
  return cam;
}

float SceneEvaluator::morphControlWeight(size_t c, const std::string& morph, double frame) const {
  float w = expressionWeight(c, morph, frame);
  const LifeParams life = lifeParams(c);
  if (life.enabled && morph == blinkMorph(characters_[c]))
    w = std::max(w, blinkAmount(frame / std::max(1.0, scene_.rate.fps()), life.blinkInterval, life.seed, life.blinkClose,
                                life.blinkHold, life.blinkOpen));
  return w;
}

// Animated weight of a morph channel (track "<name>/expr.<morph>", else the character's default expression).
float SceneEvaluator::expressionWeight(size_t c, const std::string& morph, double frame) const {
  const CharacterInstance& ci = characters_[c];
  auto d = ci.asset.defaultExpressions.find(morph);
  const float def = d == ci.asset.defaultExpressions.end() ? 0.0f : d->second;
  return scene_.animation.evaluate(scene_.characters[c].name + "/expr." + morph, frame, vec3(def)).x;
}

// The character's blink morph ("blink" in its expression map naming an existing morph), or "".
std::string SceneEvaluator::blinkMorph(const CharacterInstance& ci) {
  auto it = ci.asset.expressionMap.find("blink");
  if (it == ci.asset.expressionMap.end()) return {};
  for (auto& mt : ci.rig.morphs)
    if (mt.name == it->second) return mt.name;
  return {};
}

std::shared_ptr<FrameSnapshot> SceneEvaluator::evaluate(double frame) const {
  auto snap = std::make_shared<FrameSnapshot>();
  snap->frame = frame;
  snap->materials = materials_;
  snap->lights = scene_.lights;
  const Clip& clip = scene_.animation;
  for (size_t c = 0; c < characters_.size(); ++c) {
    const CharacterInstance& ci = characters_[c];
    std::string prefix = scene_.characters[c].name + "/";
    auto skin = characterGlobals(c, frame);
    for (size_t b = 0; b < skin.size(); ++b) skin[b] = skin[b] * glm::translate(mat4(1), -ci.asset.skeleton.bones[b].head);
    std::vector<float> weights;
    std::vector<std::string> names;
    const LifeParams life = lifeParams(c);
    const std::string blink = life.enabled ? blinkMorph(ci) : std::string();
    const float blinkW = blink.empty() ? 0.0f
                                       : blinkAmount(frame / std::max(1.0, scene_.rate.fps()), life.blinkInterval, life.seed,
                                                     life.blinkClose, life.blinkHold, life.blinkOpen);
    for (auto& mt : ci.rig.morphs) {
      float w = expressionWeight(c, mt.name, frame);
      if (mt.name == blink) w = std::max(w, blinkW);  // automatic blinks drive the character's blink morph
      weights.push_back(w);
      names.push_back(mt.name);
    }
    weights = expandInbetweens(ci.asset, names, std::move(weights));  // rotation-like morphs follow their arc
    PosedCharacter posed = poseCharacter(ci.rig, skin, weights, ci.asset.dualQuaternion);
    for (size_t k = 0; k < posed.meshes.size(); ++k) snap->meshes.push_back({posed.meshes[k], ci.meshMaterial[k]});
    for (size_t k = 0; k < posed.fuzz.size(); ++k) snap->fibers.push_back({posed.fuzz[k], ci.fuzzMaterial[k]});
    for (size_t k = 0; k < posed.locks.size(); ++k) snap->fibers.push_back({posed.locks[k], ci.lockMaterial[k]});
    for (size_t k = 0; k < posed.lockCores.size(); ++k)
      if (!posed.lockCores[k]->points.empty()) snap->fibers.push_back({posed.lockCores[k], ci.coreMaterial[k]});
  }
  // Objects after characters (objects may be attached to bones). Kept in scene order after the characters.
  std::vector<SnapshotMesh> objectMeshes;
  for (size_t i = 0; i < objects_.size(); ++i) {
    const ObjectDesc& o = scene_.objects[i];
    const ObjectGeometry& g = objects_[i];
    if (o.kind == ObjectDesc::Kind::Box) {
      objectMeshes.push_back({g.local, g.material});
      if (g.fuzz) snap->fibers.push_back({deformSurfaceFibers(*g.fuzz, *g.local), g.fuzzMaterial});
      continue;
    }
    if (o.kind == ObjectDesc::Kind::Water) {
      // Height-field grid rebuilt every frame.
      Mesh grid;
      int n = std::max(8, o.waterResolution);
      for (int zi = 0; zi <= n; ++zi)
        for (int xi = 0; xi <= n; ++xi) {
          vec2 p(glm::mix(-o.waterHalfSize.x, o.waterHalfSize.x, float(xi) / float(n)),
                 glm::mix(-o.waterHalfSize.y, o.waterHalfSize.y, float(zi) / float(n)));
          float e = 0.002f;
          float h = waterHeight(i, p, frame);
          float hx = waterHeight(i, p + vec2(e, 0), frame) - waterHeight(i, p - vec2(e, 0), frame);
          float hz = waterHeight(i, p + vec2(0, e), frame) - waterHeight(i, p - vec2(0, e), frame);
          grid.positions.push_back(vec3(p.x, h, p.y));
          grid.normals.push_back(glm::normalize(vec3(-hx / (2 * e), 1.0f, -hz / (2 * e))));
        }
      for (int zi = 0; zi < n; ++zi)
        for (int xi = 0; xi < n; ++xi) {
          uint32_t a = uint32_t(zi * (n + 1) + xi), b = a + 1, c = a + uint32_t(n + 1), d = c + 1;
          grid.indices.insert(grid.indices.end(), {a, c, b, b, c, d});
        }
      grid.pref = grid.positions;
      objectMeshes.push_back({transformMesh(grid, objectWorld(i, frame)), g.material});
      continue;
    }
    mat4 world = objectWorld(i, frame);
    const bool held = !o.attachTo.empty() && frame >= o.attachFrame && frame < o.releaseFrame;
    if (!o.floatOn.empty() && frame >= o.floatFrame && !held) {
      for (size_t wi = 0; wi < scene_.objects.size(); ++wi) {
        if (scene_.objects[wi].name != o.floatOn) continue;
        mat4 wm = objectWorld(wi, frame), inv = glm::inverse(wm);
        vec3 pos(world[3]);
        vec3 local = vec3(inv * vec4(pos, 1));
        vec2 xz(local.x, local.z);
        float e = 0.01f, h = waterHeight(wi, xz, frame);
        float tx = (waterHeight(wi, xz + vec2(e, 0), frame) - waterHeight(wi, xz - vec2(e, 0), frame)) / (2 * e);
        float tz = (waterHeight(wi, xz + vec2(0, e), frame) - waterHeight(wi, xz - vec2(0, e), frame)) / (2 * e);
        vec3 surf = vec3(wm * vec4(local.x, h - 0.004f, local.z, 1));
        mat4 tilt = glm::rotate(mat4(1), std::atan(tz), vec3(1, 0, 0)) * glm::rotate(mat4(1), -std::atan(tx), vec3(0, 0, 1));
        // A floating object keeps only its heading (yaw); pitch and roll come from the water.
        vec3 fwd = vec3(world * vec4(1, 0, 0, 0));
        float yaw = std::atan2(-fwd.z, fwd.x);
        world = glm::translate(mat4(1), surf) * tilt * glm::rotate(mat4(1), yaw, vec3(0, 1, 0));
        break;
      }
    }
    std::shared_ptr<Mesh> m;
    if (o.kind == ObjectDesc::Kind::PaperBoat && clip.find(o.name + ".fold")) {
      float f = smoothstep01(std::clamp(clip.evaluate(o.name + ".fold", frame, vec3(1)).x, 0.0f, 1.0f));
      Mesh folded = *g.local;
      for (auto& p : folded.positions) p = glm::mix(unfoldedPaper(p), p, f);
      for (size_t t = 0; t + 2 < folded.indices.size(); t += 3) {
        vec3 a = folded.positions[folded.indices[t]], b = folded.positions[folded.indices[t + 1]], c = folded.positions[folded.indices[t + 2]];
        vec3 nn = glm::cross(b - a, c - a);
        nn = glm::length2(nn) > 1e-14f ? glm::normalize(nn) : vec3(0, 1, 0);
        for (int k = 0; k < 3; ++k) folded.normals[folded.indices[t + size_t(k)]] = nn;
      }
      m = transformMesh(folded, world);
    } else {
      m = transformMesh(*g.local, world);
    }
    if (g.fuzz) snap->fibers.push_back({deformSurfaceFibers(*g.fuzz, *m), g.fuzzMaterial});
    objectMeshes.push_back({m, g.material});
  }
  snap->meshes.insert(snap->meshes.begin(), objectMeshes.begin(), objectMeshes.end());
  Camera cam = cameraAt(frame);
  snap->camera = cam;
  if (options_.lodWidth > 0) {
    float perMetre = (cam.sensorWidthMm / cam.focalMm) / float(options_.lodWidth);
    for (auto& f : snap->fibers) {
      const FiberSet& fs = *f.fibers;
      if (fs.points.empty()) continue;
      // Use the median root radius and the distance to the set's centre.
      Aabb box;
      float radius = 0;
      size_t step = std::max<size_t>(1, fs.points.size() / 256), n = 0;
      for (size_t i = 0; i < fs.points.size(); i += step, ++n) {
        box.expand(vec3(fs.points[i]));
        radius += fs.points[i].w;
      }
      radius /= float(std::max<size_t>(1, n));
      float dist = std::max(0.05f, glm::distance(box.center(), cam.position) - 0.5f * glm::length(box.extent()) * 0.5f);
      float k = fiberLodFactor(radius, dist, perMetre);
      if (k > 1.01f) f.fibers = thinFibers(fs, k);
    }
  }
  return snap;
}

}  // namespace plush
