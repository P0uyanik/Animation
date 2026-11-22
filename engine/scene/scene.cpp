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

Result<std::vector<SceneEvent>> reactionEventsFromJson(const Json& j) {
  std::vector<SceneEvent> out;
  if (j.is_null()) return out;
  if (!j.is_array()) return fail("events must be a list");
  static const std::pair<const char*, ReactionEvent::Kind> kinds[] = {
      {"object_appears", ReactionEvent::Kind::ObjectAppears}, {"partner_acts", ReactionEvent::Kind::PartnerActs},
      {"success", ReactionEvent::Kind::Success},              {"failure", ReactionEvent::Kind::Failure},
      {"custom", ReactionEvent::Kind::Custom}};
  for (const Json& e : j) {
    if (!e.is_object()) return fail("events: every event must be an object");
    SceneEvent se;
    ReactionEvent& r = se.event;
    auto text = [&](const char* k) -> Result<std::string> {
      auto it = e.find(k);
      if (it == e.end() || it->is_null()) return std::string();
      if (!it->is_string()) return fail(std::format("events: '{}' must be a string", k));
      return it->get<std::string>();
    };
    auto kind = text("kind"), name = text("name"), source = text("source");
    if (!kind) return std::unexpected(kind.error());
    if (!name) return std::unexpected(name.error());
    if (!source) return std::unexpected(source.error());
    r.name = *name;
    r.source = *source;
    if (!kind->empty()) {
      const auto* k = std::find_if(std::begin(kinds), std::end(kinds), [&](const auto& p) { return *kind == p.first; });
      if (k == std::end(kinds)) return fail(std::format("events: unknown kind '{}'", *kind));
      r.kind = k->second;
    }
    if (r.kind == ReactionEvent::Kind::Custom && r.name.empty()) return fail("events: a custom event needs a 'name'");
    const Json t = e.value("time", Json());
    if (!t.is_number() || !(t.get<double>() >= 0)) return fail(std::format("event '{}': 'time' must be seconds >= 0", r.name));
    r.time = t.get<double>();
    const Json sal = e.value("salience", Json(1.0));
    if (!sal.is_number() || !(sal.get<double>() >= 0 && sal.get<double>() <= 1))
      return fail(std::format("event '{}': 'salience' must be in [0, 1]", r.name));
    r.salience = sal.get<float>();
    if (auto it = e.find("characters"); it != e.end() && !it->is_null()) {
      if (!it->is_array()) return fail(std::format("event '{}': 'characters' must be a list of names", r.name));
      for (const Json& n : *it) {
        if (!n.is_string()) return fail(std::format("event '{}': 'characters' must be a list of names", r.name));
        se.characters.push_back(n.get<std::string>());
      }
    }
    out.push_back(std::move(se));
  }
  return out;
}

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
        cd.life.face = readBool(*it, "face", cd.life.face);
        if (auto gaze = it->find("gaze"); gaze != it->end() && gaze->is_object()) {
          cd.life.gaze.maxUpDeg = readFloat(*gaze, "maxUpDeg", cd.life.gaze.maxUpDeg);
          cd.life.gaze.maxDownDeg = readFloat(*gaze, "maxDownDeg", cd.life.gaze.maxDownDeg);
          cd.life.gaze.maxLeftDeg = readFloat(*gaze, "maxLeftDeg", cd.life.gaze.maxLeftDeg);
          cd.life.gaze.maxRightDeg = readFloat(*gaze, "maxRightDeg", cd.life.gaze.maxRightDeg);
          cd.life.gaze.assistYawDeg = readFloat(*gaze, "assistYawDeg", cd.life.gaze.assistYawDeg);
          cd.life.gaze.assistPitchDeg = readFloat(*gaze, "assistPitchDeg", cd.life.gaze.assistPitchDeg);
          cd.life.gaze.assistBodyYawDeg = readFloat(*gaze, "assistBodyYawDeg", cd.life.gaze.assistBodyYawDeg);
          cd.life.gaze.assistLagSec = readFloat(*gaze, "assistLagSec", cd.life.gaze.assistLagSec);
        }
      }
    }
    cd.dynamics = cj.value("dynamics", Json());
    cd.faceMotion = cj.value("faceMotion", Json());
    cd.bodyMechanics = cj.value("bodyMechanics", Json());
    cd.personality = cj.value("personality", Json());
    cd.gazeLegibility = cj.value("gazeLegibility", Json());
    if (auto r = gazeLegibilityFromJson(cd.gazeLegibility); !r)
      return fail(std::format("character '{}': {}", cd.name, r.error().message));
    cd.blinkSchedule = cj.value("blinkSchedule", Json());
    if (auto r = blinkScheduleFromJson(cd.blinkSchedule, cd.name); !r)
      return fail(std::format("character '{}': {}", cd.name, r.error().message));
    if (!cd.personality.is_null() && !cd.personality.is_string() && !cd.personality.is_boolean())
      return fail(std::format("character '{}': personality must be a profile id or false", cd.name));
    if (cd.personality.is_boolean() && cd.personality.get<bool>())
      return fail(std::format("character '{}': personality true names no profile (use its id)", cd.name));
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
  if (auto it = j.find("animPrinciples"); it != j.end()) {
    if (auto r = animPrinciplesFromJson(*it); !r) return std::unexpected(r.error());
    s.animPrinciples = *it;
  }
  if (auto it = j.find("reachMechanics"); it != j.end() && !it->is_null()) {  // T-134 (opt-in)
    if (auto r = reachMechanicsFromJson(*it); !r) return fail(std::format("{}: {}", path.string(), r.error().message));
    s.reachMechanics = *it;
  }
  if (auto it = j.find("interaction"); it != j.end() && !it->is_null()) {  // T-096 (opt-in)
    if (auto r = interactionOptionsFromJson(*it); !r) return fail(std::format("{}: {}", path.string(), r.error().message));
    s.interaction = *it;
  }
  if (auto it = j.find("gazeLegibility"); it != j.end() && !it->is_null()) {  // T-120 (opt-in)
    if (auto r = gazeLegibilityFromJson(*it); !r) return fail(std::format("{}: {}", path.string(), r.error().message));
    s.gazeLegibility = *it;
  }
  if (auto it = j.find("blinkSchedule"); it != j.end() && !it->is_null()) {  // T-136 (opt-in)
    if (auto r = blinkScheduleFromJson(*it, ""); !r) return fail(std::format("{}: {}", path.string(), r.error().message));
    s.blinkSchedule = *it;
  }
  if (auto it = j.find("timing"); it != j.end() && !it->is_null()) {  // T-104 (opt-in)
    if (!it->is_string() || it->get<std::string>().empty())
      return fail(std::format("{}: timing must name a timing profile (content/timing/<name>.timing.json)", path.string()));
    s.timing = *it;
  }
  if (auto it = j.find("events"); it != j.end() && !it->is_null()) {  // T-097D (opt-in)
    auto ev = reactionEventsFromJson(*it);
    if (!ev) return fail(std::format("{}: {}", path.string(), ev.error().message));
    for (const SceneEvent& e : *ev)
      for (const std::string& n : e.characters)
        if (std::none_of(s.characters.begin(), s.characters.end(), [&](const CharacterDesc& c) { return c.name == n; }))
          return fail(std::format("{}: event '{}': unknown character '{}'", path.string(), e.event.name, n));
    s.events = *it;
  }
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
    const bool customAssist = c.life.gaze.assistYawDeg != defaultGaze.assistYawDeg ||
                              c.life.gaze.assistPitchDeg != defaultGaze.assistPitchDeg ||
                              c.life.gaze.assistBodyYawDeg != defaultGaze.assistBodyYawDeg ||
                              c.life.gaze.assistLagSec != defaultGaze.assistLagSec;
    if (c.life.enabled || customGaze || customAssist) {
      Json life = {{"enabled", c.life.enabled},
                   {"gaze", {{"maxUpDeg", c.life.gaze.maxUpDeg}, {"maxDownDeg", c.life.gaze.maxDownDeg},
                             {"maxLeftDeg", c.life.gaze.maxLeftDeg}, {"maxRightDeg", c.life.gaze.maxRightDeg}}}};
      if (customAssist)
        life["gaze"].update({{"assistYawDeg", c.life.gaze.assistYawDeg}, {"assistPitchDeg", c.life.gaze.assistPitchDeg},
                             {"assistBodyYawDeg", c.life.gaze.assistBodyYawDeg}, {"assistLagSec", c.life.gaze.assistLagSec}});
      if (!c.life.face) life["face"] = false;
      if (c.life.enabled)
        life.update({{"breathing", c.life.breathing}, {"sway", c.life.sway}, {"headDrift", c.life.headDrift},
                     {"blinkInterval", c.life.blinkInterval}, {"headFollow", c.life.headFollow}, {"headLagSec", c.life.headLagSec}});
      cj["life"] = std::move(life);
    }
    if (!c.dynamics.is_null()) cj["dynamics"] = c.dynamics;
    if (!c.faceMotion.is_null()) cj["faceMotion"] = c.faceMotion;
    if (!c.bodyMechanics.is_null()) cj["bodyMechanics"] = c.bodyMechanics;
    if (!c.personality.is_null()) cj["personality"] = c.personality;
    if (!c.gazeLegibility.is_null()) cj["gazeLegibility"] = c.gazeLegibility;
    if (!c.blinkSchedule.is_null()) cj["blinkSchedule"] = c.blinkSchedule;
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
  if (!s.animPrinciples.is_null()) j["animPrinciples"] = s.animPrinciples;
  if (!s.reachMechanics.is_null()) j["reachMechanics"] = s.reachMechanics;
  if (!s.interaction.is_null()) j["interaction"] = s.interaction;
  if (!s.timing.is_null()) j["timing"] = s.timing;
  if (!s.gazeLegibility.is_null()) j["gazeLegibility"] = s.gazeLegibility;
  if (!s.blinkSchedule.is_null()) j["blinkSchedule"] = s.blinkSchedule;
  if (!s.events.is_null()) j["events"] = s.events;
  return j;
}

Result<InteractionOptions> interactionOptionsFromJson(const Json& j) {
  InteractionOptions o;
  if (j.is_null()) return o;
  if (!j.is_object()) return fail("interaction: expected an object");
  for (const auto& [k, v] : j.items()) {
    if (k == "headVolumes" || k == "followSharedProp" || k == "visibleGrip" || k == "graspFit") {
      if (!v.is_boolean()) return fail(std::format("interaction: {} must be true or false", k));
      (k == "headVolumes" ? o.headVolumes : k == "followSharedProp" ? o.followSharedProp : k == "graspFit" ? o.graspFit : o.visibleGrip) = v.get<bool>();
    } else if (k == "headClearance") {
      if (!v.is_number() || !(v.get<float>() >= 0 && v.get<float>() <= 0.1f))
        return fail("interaction: headClearance must be a number of metres in [0, 0.1]");
      o.headClearance = v.get<float>();
    } else {
      return fail(std::format("interaction: unknown option '{}'", k));
    }
  }
  return o;
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
  {  // the auto idle changes the pose the body-mechanics drivers are measured on
    std::lock_guard<std::mutex> lock(*bodyMutex_);
    for (auto& m : bodyCache_) m.clear();
  }
  buildLiveGaze();  // T-136 E3 (only characters with the opt-in gaze chain)
  // Secondary motion after the actions are compiled (action planning sees the kinematic pose).
  dynamics_.assign(characters_.size(), nullptr);
  dynamicsExternals_.assign(characters_.size(), {});
  {
    std::lock_guard<std::mutex> lock(*kinMemoMutex_);
    kinMemo_.clear();
    kinMemoOrder_.clear();
  }
  for (size_t c = 0; c < characters_.size(); ++c) {
    DynamicsSpec spec = characters_[c].asset.dynamics;
    // Accessory chains (T-061): the package's attach entries first (so a scene override may address them), then the
    // scene's own.
    if (auto r = resolveAccessoryChains(spec, characters_[c].asset.skeleton); !r)
      return fail(std::format("character '{}': {}", scene_.characters[c].name, r.error().message));
    if (auto r = applyDynamicsOverride(spec, scene_.characters[c].dynamics); !r)
      return fail(std::format("character '{}': {}", scene_.characters[c].name, r.error().message));
    if (auto r = resolveAccessoryChains(spec, characters_[c].asset.skeleton); !r)
      return fail(std::format("character '{}': {}", scene_.characters[c].name, r.error().message));
    // Off: nothing, unless chains rest on an anchor bone (then they are posed statically at their anchored targets).
    const bool anchored = std::any_of(spec.chains.begin(), spec.chains.end(), [](const SpringChain& ch) { return !ch.anchorBone.empty(); });
    if (spec.chains.empty() || (!spec.enabled && !anchored)) continue;
    auto solver = SpringChainSolver::create(characters_[c].asset.skeleton, spec, spec.enabled);
    if (!solver) return fail(std::format("character '{}': {}", scene_.characters[c].name, solver.error().message));
    dynamics_[c] = std::move(*solver);
    // Scene colliders (T-183 round 3): what the solver's external colliders ride on.
    for (const auto& ref : dynamics_[c]->externals()) {
      DynamicsExternal e;
      if (!ref.prop.empty()) {
        for (size_t p = 0; p < scene_.props.size(); ++p)
          if (scene_.props[p].name == ref.prop) e.prop = int(p);
        if (e.prop < 0)
          return fail(std::format("character '{}': dynamics collider on prop '{}': no such prop", scene_.characters[c].name, ref.prop));
      } else {
        for (size_t o = 0; o < scene_.characters.size(); ++o)
          if (o != c && scene_.characters[o].name == ref.character) e.character = int(o);
        if (e.character < 0)
          return fail(std::format("character '{}': dynamics collider on character '{}': no other character of that name",
                                  scene_.characters[c].name, ref.character));
        const Skeleton& sk = characters_[size_t(e.character)].asset.skeleton;
        e.bone = sk.find(ref.bone);
        if (e.bone < 0)
          return fail(std::format("character '{}': dynamics collider on character '{}': it has no bone '{}'",
                                  scene_.characters[c].name, ref.character, ref.bone));
        e.head = sk.bones[size_t(e.bone)].head;
      }
      dynamicsExternals_[c].push_back(e);
    }
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
  resetDynamics();
  return {};
}

void SceneEvaluator::updateMaterial(const Material& m) {
  auto it = materialIndex_.find(m.name);
  if (it != materialIndex_.end()) materials_[size_t(it->second)] = m;
}

std::vector<mat4> SceneEvaluator::characterGlobals(size_t c, double frame, Pose* poseOut) const {
  std::vector<mat4> g = kinematicGlobals(c, frame, poseOut);
  if (c < dynamics_.size() && dynamics_[c]) {
    if (c < dynamicsExternals_.size() && !dynamicsExternals_[c].empty())  // scene colliders (T-183 round 3, opt-in)
      dynamics_[c]->apply(frame, scene_.frameStart, scene_.rate.fps(), [&](double f) { return *kinematicGlobalsMemo(c, f); }, g,
                          [&](double f) { return dynamicsExternalFrames(c, f); });
    else
      dynamics_[c]->apply(frame, scene_.frameStart, scene_.rate.fps(), [&](double f) { return kinematicGlobals(c, f, nullptr); }, g);
  }
  return g;
}

std::shared_ptr<const std::vector<mat4>> SceneEvaluator::kinematicGlobalsMemo(size_t c, double frame) const {
  const std::pair<size_t, double> key{c, frame};
  {
    std::lock_guard<std::mutex> lock(*kinMemoMutex_);
    if (auto it = kinMemo_.find(key); it != kinMemo_.end()) return it->second;
  }
  auto g = std::make_shared<const std::vector<mat4>>(kinematicGlobals(c, frame, nullptr));  // not under the lock
  std::lock_guard<std::mutex> lock(*kinMemoMutex_);
  if (kinMemo_.emplace(key, g).second) {
    kinMemoOrder_.push_back(key);
    if (kinMemoOrder_.size() > 512) {
      kinMemo_.erase(kinMemoOrder_.front());
      kinMemoOrder_.pop_front();
    }
  }
  return g;
}

std::vector<mat4> SceneEvaluator::dynamicsExternalFrames(size_t c, double frame) const {
  const auto& refs = dynamicsExternals_[c];
  std::vector<mat4> out, props;
  out.reserve(refs.size());
  std::map<int, std::shared_ptr<const std::vector<mat4>>> kin;
  for (const DynamicsExternal& e : refs) {
    if (e.prop >= 0) {
      if (props.empty()) props = propWorldsWith(frame, true);
      out.push_back(props[size_t(e.prop)]);
      continue;
    }
    auto& g = kin[e.character];
    if (!g) g = kinematicGlobalsMemo(size_t(e.character), frame);
    out.push_back((*g)[size_t(e.bone)] * glm::translate(mat4(1), -e.head));
  }
  return out;
}

void SceneEvaluator::resetDynamics() const {
  for (const auto& d : dynamics_)
    if (d) d->reset();
  {
    std::lock_guard<std::mutex> lock(*kinMemoMutex_);
    kinMemo_.clear();
    kinMemoOrder_.clear();
  }
  std::lock_guard<std::mutex> lock(*bodyMutex_);
  for (auto& m : bodyCache_) m.clear();
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
  // Facial layer (T-046): blink, eye darts and control offsets of the living face.
  const bool face = faceActive(c);
  const FaceState fs = face ? faceEval(c, frame) : FaceState{};
  // Expression-driven bones (e.g. a jaw opening with the mouth): weight x rotation, from the package metadata.
  for (const auto& [morph, bones] : ci.asset.expressionBones) {
    float w = face ? morphControlWeight(c, morph, frame) : expressionWeight(c, morph, frame);
    if (!face)
      if (const float po = personalityFaceOffset(c, morph, frame); po != 0.0f) w = std::clamp(w + po, 0.0f, 1.0f);
    if (w == 0.0f) continue;
    for (const auto& b : bones) {
      const int bi = ci.asset.skeleton.find(b.bone);
      if (bi >= 0) pose.local[size_t(bi)] = pose.local[size_t(bi)] * glm::angleAxis(glm::radians(b.degrees * w), b.axis);
    }
  }
  LifeParams life = lifeParams(c);
  // Gaze legibility (T-120, opt-in): the eyes keep to the character's gaze range and the head turns just enough,
  // after the eyes (turnHeadForGaze), in place of the life layer's head follow and the neck / chest assist.
  GazeLegibility legible = gazeLegibility(c);
  if (legible.enabled) {
    if (legible.headYawDeg < 0) legible.headYawDeg = life.gaze.assistYawDeg;
    if (legible.headPitchDeg < 0) legible.headPitchDeg = life.gaze.assistPitchDeg;
    life.headFollow = 0;
    life.gaze.assistYawDeg = life.gaze.assistPitchDeg = life.gaze.assistBodyYawDeg = 0;
    life.gaze.maxLeftDeg = life.gaze.maxRightDeg = legible.rangeDeg.x;
    life.gaze.maxUpDeg = life.gaze.maxDownDeg = legible.rangeDeg.y;
  }
  const bool morphBlink = !blinkMorph(ci).empty();
  if (morphBlink || face) life.blinkLids = false;  // blinks are a morph for this character (see evaluate) or the face layer's
  applyLife(ci.asset.skeleton, clip, prefix, frame, scene_.rate.fps(), world, life, pose);
  if (face && !morphBlink) applyLidBlink(ci.asset.skeleton, pose, fs.blink);
  // Body mechanics (T-045): shoulders, torso, weight shift and pivot carry, before IK and look-at so they work on it.
  if (bodyMechanicsActive(c)) applyBodyMechanicsAt(c, frame, pose);
  // Gaze chain (T-136 E3, opt-in): the exact live target of an atProp / atCharacter look, torso + neck + head.
  vec3 liveOffset(0);
  double sinceLook = -1;
  const bool live = legible.enabled && legible.chain && liveGazeOffset(c, frame, liveOffset, &sinceLook);
  if (legible.enabled && legible.chain)
    turnChainForGaze(ci.asset.skeleton, clip, prefix, frame, scene_.rate.fps(), world, pose, legible, liveOffset,
                     live ? sinceLook : -1.0);
  else if (legible.enabled)
    turnHeadForGaze(ci.asset.skeleton, clip, prefix, frame, scene_.rate.fps(), world, pose, legible);
  applyConstraints(ci.asset.skeleton, clip, prefix, frame, world, pose, life.gaze, scene_.rate.fps());
  if (live)
    aimEyesAt(ci.asset.skeleton, world, pose, clip.find(prefix + "lookAt")->evaluate(frame) + liveOffset, std::clamp(clip.evaluate(prefix + "lookAt.weight", frame, vec3(1)).x, 0.0f, 1.0f));
  if (face && (fs.eyeOffsetDeg.x != 0 || fs.eyeOffsetDeg.y != 0)) {  // eye darts and gaze bias on top of the aim
    const quat dq = glm::angleAxis(glm::radians(fs.eyeOffsetDeg.x), vec3(0, 1, 0)) *
                    glm::angleAxis(glm::radians(-fs.eyeOffsetDeg.y), vec3(1, 0, 0));
    for (size_t b = 0; b < ci.asset.skeleton.bones.size(); ++b)
      if (ci.asset.skeleton.bones[b].name.rfind("eye.", 0) == 0) pose.local[b] = glm::normalize(pose.local[b] * dq);
  }
  if (legible.enabled) {  // darts and blinks too; a chained look keeps its eyes near centre (eyeShareDeg)
    vec2 range = legible.rangeDeg;
    if (legible.chain && legible.eyeShareDeg.x >= 0) range = glm::min(range, legible.eyeShareDeg + vec2(2.0f));
    clampEyesToGazeRange(ci.asset.skeleton, world, pose, range);
  }
  applyArmPoles(ci.asset.skeleton, clip, prefix, frame, world, pose);          // elbow outward (T-030)
  applyOrientConstraints(ci.asset.skeleton, clip, prefix, frame, world, pose);  // hand-prop interaction (T-022)
  if (clips) applyClipFingers(c, frame, pose);
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

std::vector<mat4> SceneEvaluator::propWorlds(double frame) const { return propWorldsWith(frame, false); }

std::vector<mat4> SceneEvaluator::propWorldsWith(double frame, bool kinematic) const {
  // kinematic (T-183 round 3, the spring chains' prop colliders): the carrier's bone before secondary motion
  const auto socketGlobal = [&](size_t character, double at, int bone) {
    return kinematic ? (*kinematicGlobalsMemo(character, at))[size_t(bone)] : characterGlobals(character, at)[size_t(bone)];
  };
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
          socketWorld = socketGlobal(character, at, bone);
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
        socketWorld = socketGlobal(character, switchFrame, bone);
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

Result<GazeLegibility> gazeLegibilityFromJson(const Json& j, GazeLegibility base) {
  auto bad = [](const std::string& m) { return std::unexpected(Error{"gazeLegibility: " + m}); };
  if (j.is_null()) return base;
  if (j.is_boolean()) {
    base.enabled = j.get<bool>();
    return base;
  }
  if (!j.is_object()) return bad("must be true, false or an object");
  base.enabled = true;
  for (auto& [key, v] : j.items()) {
    if (key == "enabled") {
      if (!v.is_boolean()) return bad("'enabled' must be true or false");
      base.enabled = v.get<bool>();
    } else if (key == "rangeDeg") {
      if (!v.is_array() || v.size() != 2 || !v[0].is_number() || !v[1].is_number() || v[0].get<float>() <= 0 ||
          v[1].get<float>() <= 0)
        return bad("'rangeDeg' must be [yaw, pitch], both above 0");
      base.rangeDeg = vec2(v[0].get<float>(), v[1].get<float>());
    } else if (key == "leadFrames" || key == "turnFrames" || key == "headYawDeg" || key == "headPitchDeg") {
      if (!v.is_number() || v.get<float>() < 0) return bad("'" + key + "' must be a number, 0 or more");
      (key == "leadFrames" ? base.leadFrames : key == "turnFrames" ? base.turnFrames
       : key == "headYawDeg" ? base.headYawDeg : base.headPitchDeg) = v.get<float>();
    } else if (key == "chain") {  // T-136 E3
      if (v.is_boolean()) {
        base.chain = v.get<bool>();
        continue;
      }
      if (!v.is_object()) return bad("'chain' must be true, false or an object");
      base.chain = true;
      for (auto& [ck, cv] : v.items()) {
        float* field = ck == "neckYawDeg" ? &base.neckYawDeg : ck == "neckPitchDeg" ? &base.neckPitchDeg
                       : ck == "torsoYawDeg" ? &base.torsoYawDeg : ck == "torsoPitchDeg" ? &base.torsoPitchDeg
                       : ck == "torsoLagFrames" ? &base.torsoLagFrames : nullptr;
        if (ck == "enabled") {
          if (!cv.is_boolean()) return bad("'chain.enabled' must be true or false");
          base.chain = cv.get<bool>();
          continue;
        }
        if (ck == "eyeShareDeg") {
          if (!cv.is_array() || cv.size() != 2 || !cv[0].is_number() || !cv[1].is_number() || cv[0].get<float>() < 0 ||
              cv[1].get<float>() < 0)
            return bad("'chain.eyeShareDeg' must be [yaw, pitch], both 0 or more");
          base.eyeShareDeg = vec2(cv[0].get<float>(), cv[1].get<float>());
          continue;
        }
        if (!field) return bad("unknown chain key '" + ck + "'");
        if (!cv.is_number() || cv.get<float>() < 0) return bad("'chain." + ck + "' must be a number, 0 or more");
        *field = cv.get<float>();
      }
    } else {
      return bad("unknown key '" + key + "'");
    }
  }
  return base;
}

Result<BlinkSchedule> blinkScheduleFromJson(const Json& j, const std::string& character, BlinkSchedule base) {
  auto bad = [](const std::string& m) { return std::unexpected(Error{"blinkSchedule: " + m}); };
  if (j.is_null()) return base;
  if (j.is_boolean()) {
    base.enabled = j.get<bool>();
    return base;
  }
  if (!j.is_object()) return bad("must be true, false or an object");
  base.enabled = true;
  for (auto& [key, v] : j.items()) {
    if (key == "enabled") {
      if (!v.is_boolean()) return bad("'enabled' must be true or false");
      base.enabled = v.get<bool>();
    } else if (key == "shortBeatFrames" || key == "preferWindowFrames") {
      if (!v.is_number() || v.get<float>() < 0) return bad("'" + key + "' must be a number, 0 or more");
      (key == "shortBeatFrames" ? base.shortBeatFrames : base.preferWindowFrames) = v.get<float>();
    } else if (key == "actionChanges") {
      if (!v.is_boolean() && !v.is_array()) return bad("'actionChanges' must be true, false or a list of frames");
      if (v.is_array())
        for (const Json& f : v) {
          if (!f.is_number()) return bad("'actionChanges' frames must be numbers");
          base.actionChanges.push_back(f.get<double>());
        }
    } else if (key == "keyBeats") {
      if (!v.is_array()) return bad("'keyBeats' must be a list");
      for (const Json& b : v) {
        if (!b.is_object() || !b.contains("start") || !b.contains("end") || !b["start"].is_number() || !b["end"].is_number() ||
            b["end"].get<double>() < b["start"].get<double>())
          return bad("a key beat needs numbers 'start' <= 'end'");
        bool mine = true;
        if (auto ch = b.find("characters"); ch != b.end()) {
          if (!ch->is_array()) return bad("a key beat's 'characters' must be a list of names");
          mine = character.empty();
          for (const Json& n : *ch) {
            if (!n.is_string()) return bad("a key beat's 'characters' must be a list of names");
            if (n.get<std::string>() == character) mine = true;
          }
        }
        for (auto& [bk, bv] : b.items())
          if (bk != "start" && bk != "end" && bk != "characters" && bk != "name") return bad("unknown key beat key '" + bk + "'");
        if (mine) base.keyBeats.push_back({b["start"].get<double>(), b["end"].get<double>()});
      }
    } else {
      return bad("unknown key '" + key + "'");
    }
  }
  return base;
}

BlinkSchedule SceneEvaluator::blinkSchedule(size_t c) const {
  BlinkSchedule b;
  if (c >= scene_.characters.size() || (scene_.blinkSchedule.is_null() && scene_.characters[c].blinkSchedule.is_null()))
    return b;
  const std::string& name = scene_.characters[c].name;
  if (auto r = blinkScheduleFromJson(scene_.blinkSchedule, name)) b = *r;
  if (auto r = blinkScheduleFromJson(scene_.characters[c].blinkSchedule, name, b)) b = *r;
  if (!b.enabled) return b;
  // Action changes: explicit frames, else (or "actionChanges": true) the character's own action starts.
  auto autoChanges = [](const Json& j) {
    const Json* a = j.is_object() ? (j.contains("actionChanges") ? &j["actionChanges"] : nullptr) : nullptr;
    return !a || (a->is_boolean() && a->get<bool>());
  };
  if (autoChanges(scene_.blinkSchedule) && autoChanges(scene_.characters[c].blinkSchedule))
    for (const Json& a : scene_.actions) {
      if (!a.is_object()) continue;
      const std::string type = a.value("type", ""), who = a.value("character", ""), to = a.value("to", "");
      if (type == "look" || type == "emotion" || (who != name && to != name)) continue;
      auto add = [&](const char* key) {
        if (auto it = a.find(key); it != a.end() && it->is_number()) b.actionChanges.push_back(it->get<double>());
      };
      if (who == name) add("start");
      if (type == "pass") {
        if (to == name) add("receiverStart");
        add("contact");
        add("release");
      }
    }
  return b;
}

GazeLegibility SceneEvaluator::gazeLegibility(size_t c) const {
  GazeLegibility g;
  if (auto r = gazeLegibilityFromJson(scene_.gazeLegibility)) g = *r;
  if (c < scene_.characters.size())
    if (auto r = gazeLegibilityFromJson(scene_.characters[c].gazeLegibility, g)) g = *r;
  return g;
}

namespace {
// Yaw (+ = the character's left) and pitch (+ = up), degrees, of a direction in the head frame; and back.
vec2 gazeAngles(vec3 d) {
  return vec2(glm::degrees(std::atan2(d.x, d.z)), glm::degrees(std::atan2(d.y, glm::length(vec2(d.x, d.z)))));
}
vec3 gazeDirection(vec2 a) {
  const float y = glm::radians(a.x), p = glm::radians(a.y), cp = std::cos(p);
  return vec3(std::sin(y) * cp, std::sin(p), std::cos(y) * cp);
}
std::vector<int> eyeBones(const Skeleton& sk) {
  std::vector<int> eyes;
  for (size_t i = 0; i < sk.bones.size(); ++i)
    if (sk.bones[i].name.rfind("eye.", 0) == 0) eyes.push_back(int(i));
  return eyes;
}
}  // namespace

void turnHeadForGaze(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, double fps,
                     const mat4& world, Pose& pose, const GazeLegibility& lg) {
  const Track* t = clip.find(prefix + "lookAt");
  const int neck = sk.find("neck"), head = sk.find("head");
  if (!t || t->keys.empty() || neck < 0 || head < 0 || (lg.headYawDeg <= 0 && lg.headPitchDeg <= 0)) return;
  if (const Track* k = clip.find(prefix + "neck.rot"); k && !k->keys.empty()) return;  // a hand-keyed neck wins
  const std::vector<int> eyes = eyeBones(sk);
  if (eyes.empty()) return;
  // Eyes lead: the head aims at where the target was leadFrames .. leadFrames + turnFrames ago (bell-weighted, so the
  // turn eases in and out). Nothing of a new target reaches the head before leadFrames.
  const double scale = std::max(1.0, fps) / 24.0, lead = lg.leadFrames * scale, turn = lg.turnFrames * scale;
  constexpr int kSamples = 8;
  vec3 target(0);
  float weight = 0, total = 0;
  for (int i = 0; i < kSamples; ++i) {
    const double u = (i + 0.5) / kSamples;
    const float k = float(0.5 - 0.5 * std::cos(2.0 * 3.14159265358979 * u));
    const double f = frame - lead - turn * u;
    target += k * t->evaluate(f);
    weight += k * clip.evaluate(prefix + "lookAt.weight", f, vec3(1)).x;
    total += k;
  }
  target /= total;
  weight = std::clamp(weight / total, 0.0f, 1.0f);
  if (weight <= 0) return;
  // The eyes follow a target exactly up to the soft limit's onset (anim: softLimit); the head takes what lies beyond.
  auto comfortable = [](float limit) { return limit - std::min(5.0f, limit * 0.25f) - 0.25f; };
  const vec2 comfort(comfortable(lg.rangeDeg.x), comfortable(lg.rangeDeg.y));
  const vec2 cap(std::max(0.0f, lg.headYawDeg), std::max(0.0f, lg.headPitchDeg));
  const quat neckBefore = pose.local[size_t(neck)];
  vec2 used(0);
  for (int pass = 0; pass < 8; ++pass) {
    const std::vector<mat4> g = boneGlobals(sk, pose, world);
    const mat3 headRot(g[size_t(head)]);
    // Per axis: how far the worse-placed (near) eye is from the edge of its comfortable range. Once the head has
    // turned on an axis it also comes back when it went too far (the two axes disturb each other at large angles).
    vec2 error(0);
    for (int axis = 0; axis < 2; ++axis) {
      float side = used[axis] != 0 ? (used[axis] > 0 ? 1.0f : -1.0f) : 0.0f, worst = 0;
      bool any = false;
      for (int e : eyes) {
        const vec3 to = target - vec3(g[size_t(e)][3]);
        if (glm::length2(to) < 1e-10f) return;
        const float a = gazeAngles(glm::normalize(glm::transpose(headRot) * glm::normalize(to)))[axis];
        if (side == 0 && std::abs(a) <= comfort[axis]) continue;
        const float s = side != 0 ? side : (a > 0 ? 1.0f : -1.0f);
        const float over = (a - s * comfort[axis]) * s;  // > 0: this eye needs more head; < 0: the head went too far
        if (!any || over > worst) worst = over;
        if (side == 0) side = s;
        any = true;
      }
      if (any) error[axis] = side * std::max(worst, -std::abs(used[axis]));  // never back past the starting pose
    }
    const vec2 step = glm::clamp(used + error, -cap, cap) - used;
    if (std::abs(step.x) < 1e-4f && std::abs(step.y) < 1e-4f) break;
    used += step;
    // World rotation about the head's up axis (yaw toward +X) and right axis (positive pitch looks up = -X rotation).
    const vec3 up = glm::normalize(headRot * vec3(0, 1, 0)), right = glm::normalize(headRot * vec3(1, 0, 0));
    const quat r = glm::angleAxis(glm::radians(step.x), up) * glm::angleAxis(glm::radians(-step.y), right);
    const int parent = sk.bones[size_t(neck)].parent;
    const quat parentRot = glm::normalize(glm::quat_cast(parent >= 0 ? mat3(g[size_t(parent)]) : mat3(world)));
    pose.local[size_t(neck)] = glm::normalize(glm::inverse(parentRot) * r * parentRot * pose.local[size_t(neck)]);
  }
  if (weight < 1) pose.local[size_t(neck)] = glm::normalize(glm::slerp(neckBefore, pose.local[size_t(neck)], weight));
}

void SceneEvaluator::buildLiveGaze() {
  // Pass 1 reads every pose with the keyed targets; pass 2 with pass 1's live targets, so two characters in eye contact
  // see each other's corrected heads.
  liveGaze_.clear();
  for (int pass = 0; pass < 2; ++pass) buildLiveGazePass();
}

void SceneEvaluator::buildLiveGazePass() {
  std::vector<std::vector<vec4>> out(characters_.size());
  for (size_t c = 0; c < characters_.size(); ++c) {
    const GazeLegibility g = gazeLegibility(c);
    if (!g.enabled || !g.chain) continue;
    for (int f = scene_.frameStart; f <= scene_.frameEnd; ++f) {
      vec3 live(0), keyed(0);
      // The offset applies the same to every sample of the lagged target (the live target's motion is the keyed one's).
      double lookStart = f;
      const bool ok = liveGazeTarget(c, f, live, keyed, &lookStart);
      if (ok) {
        // Relative to the track's own value at f (the keys are every 3 frames, linear between).
        const vec3 track = scene_.animation.find(scene_.characters[c].name + "/lookAt")->evaluate(f);
        out[c].push_back(vec4(live - track, float(f - lookStart) + 1.0f));
      } else {
        out[c].push_back(vec4(0));
      }
    }
  }
  liveGaze_ = std::move(out);
}

bool SceneEvaluator::liveGazeOffset(size_t c, double frame, vec3& offset, double* sinceStart) const {
  if (c >= liveGaze_.size() || liveGaze_[c].empty()) return false;
  const std::vector<vec4>& v = liveGaze_[c];
  const double x = frame - scene_.frameStart;
  if (x < 0 || x > double(v.size() - 1)) return false;
  const size_t i = size_t(x);
  const size_t j = std::min(i + 1, v.size() - 1);
  if (v[i].w <= 0 || v[j].w <= 0) return false;  // a look change between the two frames: the keyed target
  const float u = float(x - double(i));
  offset = glm::mix(vec3(v[i]), vec3(v[j]), u);
  if (sinceStart) *sinceStart = double(v[i].w) - 1.0 + double(u);
  return true;
}

bool SceneEvaluator::liveGazeTarget(size_t c, double frame, vec3& live, vec3& keyed, double* lookStartOut) const {
  if (c >= scene_.characters.size() || !scene_.actions.is_array()) return false;
  const std::string& name = scene_.characters[c].name;
  const Track* track = scene_.animation.find(name + "/lookAt");
  if (!track || track->keys.empty()) return false;
  const Json* look = nullptr;  // the latest authored look of c that has started
  double lookStart = -1e30;
  for (const Json& a : scene_.actions) {
    if (!a.is_object() || a.value("type", "") != "look" || a.value("character", "") != name) continue;
    const double st = a.contains("start") && a["start"].is_number() ? a["start"].get<double>() : double(scene_.frameStart);
    if (st <= frame && st >= lookStart) {
      look = &a;
      lookStart = st;
    }
  }
  if (!look || (!look->contains("atProp") && !look->contains("atCharacter"))) return false;
  if (lookStartOut) *lookStartOut = lookStart;
  if (look->contains("atProp")) {  // the prop's middle, as the look action keys it (actions.cpp), but every frame
    const std::string prop = (*look)["atProp"].is_string() ? (*look)["atProp"].get<std::string>() : "";
    bool found = false;
    for (size_t p = 0; p < scene_.props.size() && p < propAssets_.size(); ++p) {
      if (scene_.props[p].name != prop) continue;
      found = true;
      const PropAsset& pa = propAssets_[p];
      vec3 middle(0);
      if (pa.mesh.kind == AssetMeshSource::Kind::Primitive) {
        if (pa.mesh.primitive == AssetMeshSource::Primitive::Cylinder) middle = vec3(0, 0.5f * pa.mesh.height * pa.scaleMetres, 0);
      } else if (pa.collision) {
        middle = pa.collision->transform.translation;
      }
      live = keyed = vec3(propWorld(p, frame) * vec4(middle, 1));
      break;
    }
    if (!found) return false;
  } else {  // eye contact: the midpoint of the partner's eyes; the track keys a point before its face
    const std::string other = (*look)["atCharacter"].is_string() ? (*look)["atCharacter"].get<std::string>() : "";
    size_t oc = scene_.characters.size();
    for (size_t i = 0; i < scene_.characters.size(); ++i)
      if (scene_.characters[i].name == other) oc = i;
    if (oc >= characters_.size() || oc == c) return false;
    const Skeleton& sk = characters_[oc].asset.skeleton;
    const int head = sk.find("head");
    const std::vector<int> eyes = eyeBones(sk);
    if (head < 0 || eyes.empty()) return false;
    const std::vector<mat4> g = kinematicGlobals(oc, frame, nullptr);
    live = vec3(0);
    for (int e : eyes) live += vec3(g[size_t(e)][3]);
    live /= float(eyes.size());
    keyed = vec3(g[size_t(head)] * vec4(0, 0.11f, 0.09f, 1));
  }
  // A generated look (reaction events) may have taken the track over: then the keyed value is somewhere else. The track
  // was keyed while the actions compiled, so a moving prop can drift from it by some centimetres (e910: 13 cm).
  return glm::distance(track->evaluate(frame), keyed) < 0.25f;
}

void turnChainForGaze(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, double fps,
                      const mat4& world, Pose& pose, const GazeLegibility& lg, vec3 liveOffset, double sinceLookStart) {
  const Track* t = clip.find(prefix + "lookAt");
  const int head = sk.find("head");
  if (!t || t->keys.empty() || head < 0) return;
  const std::vector<int> eyes = eyeBones(sk);
  if (eyes.empty()) return;
  const bool keyedNeck = clip.find(prefix + "neck.rot") && !clip.find(prefix + "neck.rot")->keys.empty();
  const double scale = std::max(1.0, fps) / 24.0;
  // The target as it was `lag` .. `lag` + turnFrames ago (bell-weighted), moved onto the live target.
  auto lagged = [&](double lag, float& weight) {
    constexpr int kSamples = 8;
    vec3 target(0);
    float total = 0;
    weight = 0;
    for (int i = 0; i < kSamples; ++i) {
      const double u = (i + 0.5) / kSamples;
      const float k = float(0.5 - 0.5 * std::cos(2.0 * 3.14159265358979 * u));
      const double f = frame - lag * scale - lg.turnFrames * scale * u;
      target += k * t->evaluate(f);
      weight += k * clip.evaluate(prefix + "lookAt.weight", f, vec3(1)).x;
      total += k;
    }
    weight = std::clamp(weight / total, 0.0f, 1.0f);
    const vec3 laggedTarget = target / total + liveOffset;
    // Pursuit: once the look has settled (all samples inside it), ease onto the current target.
    if (sinceLookStart < 0) return laggedTarget;
    const double settled = (lag + lg.turnFrames) * scale;
    const float p = smoothstep01(float(std::clamp((sinceLookStart - settled) / std::max(1.0, lg.turnFrames * scale), 0.0, 1.0)));
    if (p <= 0) return laggedTarget;
    weight = glm::mix(weight, std::clamp(clip.evaluate(prefix + "lookAt.weight", frame, vec3(1)).x, 0.0f, 1.0f), p);
    return glm::mix(laggedTarget, t->evaluate(frame) + liveOffset, p);
  };
  auto comfortable = [](float limit) { return limit - std::min(5.0f, limit * 0.25f) - 0.25f; };
  vec2 eyeComfort(comfortable(lg.rangeDeg.x), comfortable(lg.rangeDeg.y));
  if (lg.eyeShareDeg.x >= 0) eyeComfort = glm::min(eyeComfort, lg.eyeShareDeg);
  const vec2 neckCap(std::max({0.0f, lg.headYawDeg, lg.neckYawDeg}), std::max({0.0f, lg.headPitchDeg, lg.neckPitchDeg}));
  const vec2 torsoCap(std::max(0.0f, lg.torsoYawDeg), std::max(0.0f, lg.torsoPitchDeg));
  // One stage: turn `bones` (parent first, by share) until the near eye sits at `comfort` from the target, up to cap.
  auto stage = [&](vec3 target, float weight, vec2 comfort, vec2 cap, const std::vector<std::pair<int, float>>& bones) {
    if (weight <= 0 || bones.empty()) return;
    std::vector<quat> before;
    for (const auto& b : bones) before.push_back(pose.local[size_t(b.first)]);
    vec2 used(0);
    for (int pass = 0; pass < 10; ++pass) {
      std::vector<mat4> g = boneGlobals(sk, pose, world);
      const mat3 headRot(g[size_t(head)]);
      // Per axis, the turn h that puts every eye inside its comfortable range (a - h within +-comfort): the smallest
      // such turn back towards the stage's rest, or, when the eyes straddle a near target wider than the range
      // (vergence), the middle, so both eyes share the shortfall.
      vec2 error(0);
      vec2 lo(-1e9f), hi(1e9f);
      for (int e : eyes) {
        const vec3 to = target - vec3(g[size_t(e)][3]);
        if (glm::length2(to) < 1e-10f) return;
        const vec2 a = gazeAngles(glm::normalize(glm::transpose(headRot) * glm::normalize(to)));
        lo = glm::max(lo, a - comfort);
        hi = glm::min(hi, a + comfort);
      }
      for (int axis = 0; axis < 2; ++axis)
        error[axis] = lo[axis] > hi[axis] ? 0.5f * (lo[axis] + hi[axis]) : std::clamp(-used[axis], lo[axis], hi[axis]);
      const vec2 step = glm::clamp(used + error, -cap, cap) - used;
      if (std::abs(step.x) < 1e-3f && std::abs(step.y) < 1e-3f) break;
      used += step;
      const vec3 up = glm::normalize(headRot * vec3(0, 1, 0)), right = glm::normalize(headRot * vec3(1, 0, 0));
      for (const auto& [bone, share] : bones) {
        const quat r = glm::angleAxis(glm::radians(step.x * share), up) * glm::angleAxis(glm::radians(-step.y * share), right);
        const int parent = sk.bones[size_t(bone)].parent;
        const quat parentRot = glm::normalize(glm::quat_cast(parent >= 0 ? mat3(g[size_t(parent)]) : mat3(world)));
        pose.local[size_t(bone)] = glm::normalize(glm::inverse(parentRot) * r * parentRot * pose.local[size_t(bone)]);
        g = boneGlobals(sk, pose, world);
      }
    }
    if (weight < 1)
      for (size_t i = 0; i < bones.size(); ++i)
        pose.local[size_t(bones[i].first)] = glm::normalize(glm::slerp(before[i], pose.local[size_t(bones[i].first)], weight));
  };
  auto present = [&](std::initializer_list<std::pair<const char*, float>> list) {
    std::vector<std::pair<int, float>> out;
    float total = 0;
    for (const auto& [n, s] : list)
      if (const int b = sk.find(n); b >= 0) {
        out.push_back({b, s});
        total += s;
      }
    for (auto& b : out) b.second /= std::max(1e-6f, total);
    return out;
  };
  // Torso first (it carries the head), on the target the head had torsoLagFrames earlier: it takes only what lies
  // beyond the eyes' comfortable range plus the neck's full share.
  float wTorso = 0, wNeck = 0;
  const vec3 torsoTarget = lagged(lg.leadFrames + lg.torsoLagFrames, wTorso);
  stage(torsoTarget, wTorso, eyeComfort + neckCap, torsoCap, present({{"spine", 0.4f}, {"chest", 0.6f}}));
  // Then the neck and head, as T-120's head turn but with the larger cap (a hand-keyed neck is left alone).
  if (!keyedNeck) {
    const vec3 neckTarget = lagged(lg.leadFrames, wNeck);
    stage(neckTarget, wNeck, eyeComfort, neckCap, present({{"neck", 0.5f}, {"head", 0.5f}}));
  }
}

void aimEyesAt(const Skeleton& sk, const mat4& world, Pose& pose, vec3 target, float weight) {
  if (weight <= 0) return;
  const std::vector<mat4> g = boneGlobals(sk, pose, world);
  for (int e : eyeBones(sk)) {
    const vec3 forward = glm::normalize(vec3(g[size_t(e)][2]));
    const vec3 to = target - vec3(g[size_t(e)][3]);
    if (glm::length2(to) < 1e-10f) continue;
    const vec3 wanted = glm::normalize(to);
    const vec3 axis = glm::cross(forward, wanted);
    const float s = glm::length(axis);
    if (s < 1e-7f) continue;
    const quat r = glm::angleAxis(std::atan2(s, glm::dot(forward, wanted)) * std::min(1.0f, weight), axis / s);
    const int parent = sk.bones[size_t(e)].parent;
    const quat pr = glm::normalize(glm::quat_cast(parent >= 0 ? mat3(g[size_t(parent)]) : mat3(world)));
    pose.local[size_t(e)] = glm::normalize(glm::inverse(pr) * r * pr * pose.local[size_t(e)]);
  }
}

void clampEyesToGazeRange(const Skeleton& sk, const mat4& world, Pose& pose, vec2 rangeDeg) {
  const int head = sk.find("head");
  const std::vector<int> eyes = eyeBones(sk);
  if (eyes.empty()) return;
  const std::vector<mat4> g = boneGlobals(sk, pose, world);
  for (int e : eyes) {
    const int parent = sk.bones[size_t(e)].parent;
    const mat3 parentRot = parent >= 0 ? mat3(g[size_t(parent)]) : mat3(world);
    const mat3 headRot = head >= 0 ? mat3(g[size_t(head)]) : parentRot;
    const vec3 forward = glm::normalize(vec3(g[size_t(e)][2]));
    const vec2 a = gazeAngles(glm::normalize(glm::transpose(headRot) * forward));
    const vec2 c = glm::clamp(a, -rangeDeg, rangeDeg);
    if (c == a) continue;
    // The smallest world rotation that brings the eye's direction back onto the range's edge.
    const vec3 wanted = glm::normalize(headRot * gazeDirection(c));
    const vec3 axis = glm::cross(forward, wanted);
    const float s = glm::length(axis);
    if (s < 1e-7f) continue;
    const quat r = glm::angleAxis(std::atan2(s, glm::dot(forward, wanted)), axis / s);
    const quat pr = glm::normalize(glm::quat_cast(parentRot));
    pose.local[size_t(e)] = glm::normalize(glm::inverse(pr) * r * pr * pose.local[size_t(e)]);
  }
}

// Life parameters of character c: the scene's, with the character's own blink timing where the package has one
// (an explicit scene blinkInterval wins). Characters without timing keep the defaults.
LifeParams SceneEvaluator::lifeParams(size_t c) const {
  LifeParams life = scene_.characters[c].life;
  const CharacterAsset& a = characters_[c].asset;
  if (a.blinkInterval > 0 && !life.blinkIntervalSet) life.blinkInterval = a.blinkInterval;
  if (a.blinkClose > 0) life.blinkClose = a.blinkClose;
  if (a.blinkHold >= 0 && a.blinkClose > 0) life.blinkHold = a.blinkHold;
  if (a.blinkOpen > 0) life.blinkOpen = a.blinkOpen;
  // Personality (T-053): blink rhythm and shape, idle amplitude, eyes-lead-head lag (frames at 24 fps). Explicit
  // scene values win (blinkInterval: clamped into the profile's limits, see buildPersonalities).
  if (const PersonalityProfile* P = personality(c)) {
    if (P->blinkIntervalMean && !life.blinkIntervalSet) life.blinkInterval = *P->blinkIntervalMean / 24.0f;
    if (life.blinkIntervalSet && P->limits.blinkIntervalFrames && life.blinkInterval > 0)
      life.blinkInterval = P->limits.blinkIntervalFrames->clamp(life.blinkInterval * 24.0f) / 24.0f;
    if (P->blinkDurationFrames) {
      // Whole blink = close + shut + open; the lids stay shut for the measured closed frames (at most half the
      // blink) and close faster than they open (40 : 60, VISUAL_TARGET facial micro-timing).
      const float total = P->blinkDurationFrames->mid() / 24.0f;
      const float shut = std::min(P->blinkClosedFrames ? P->blinkClosedFrames->mid() / 24.0f : 0.25f * total, 0.5f * total);
      life.blinkHold = shut;
      life.blinkClose = 0.4f * (total - shut);
      life.blinkOpen = 0.6f * (total - shut);
    }
    if (P->idleMotionAmplitudeH) {  // idle amplitude relative to the shared neutral (content/personality/shared.json)
      const float k = std::clamp(*P->idleMotionAmplitudeH / std::max(1e-6f, persona_[c].neutralIdleH), 0.25f, 2.0f);
      life.sway *= k;
      life.headDrift *= k;
      life.breathing *= std::sqrt(k);  // breathing stays visible on a still character
    }
    if (P->eyesLeadHeadFrames && life.headLagSec == LifeParams{}.headLagSec) life.headLagSec = P->eyesLeadHeadFrames->mid() / 24.0f;
  }
  return life;
}

// ------------------------------------------------------------------ personality face (T-053)
float SceneEvaluator::expressionActivity(size_t c, double frame) const {
  if (c >= persona_.size()) return 0.0f;
  float a = 0;
  for (const auto& m : persona_[c].activityMorphs) a = std::max(a, expressionWeight(c, m, frame));
  return std::clamp(a, 0.0f, 1.0f);
}

float SceneEvaluator::personalityFaceOffset(size_t c, const std::string& morph, double frame) const {
  if (c >= persona_.size() || !persona_[c].profile || persona_[c].face.empty()) return 0.0f;
  const PersonaSetup& ps = persona_[c];
  float watch = 0;
  for (auto [s, e] : ps.watchSpans) {
    const double ramp = 6.0;  // frames, as an expression action's default ramp
    const double w = frame < s ? (frame - (s - ramp)) / ramp : frame > e ? (e + ramp - frame) / ramp : 1.0;
    watch = std::max(watch, float(std::clamp(w, 0.0, 1.0)));
  }
  const float act = ps.face.bias.count(morph) ? expressionActivity(c, frame) : 0.0f;
  return plush::personalityFaceOffset(ps.face, morph, act, watch);
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
  if (const float po = personalityFaceOffset(c, morph, frame); po != 0.0f) w = std::clamp(w + po, 0.0f, 1.0f);
  const LifeParams life = lifeParams(c);
  if (faceActive(c)) {  // the facial layer: control offsets and its own blinks
    const FaceState fs = faceEval(c, frame);
    if (auto it = fs.controls.find(morph); it != fs.controls.end()) w = std::clamp(w + it->second, 0.0f, 1.0f);
    const std::string blink = blinkMorph(characters_[c]);
    if (morph == blink) w = std::max(w, fs.blink);
    else if (!blink.empty() && faces_[c].clearsWithBlink(morph))  // eye-opening controls fade while the lids close
      w *= 1.0f - std::clamp(std::max(fs.blink, expressionWeight(c, blink, frame)), 0.0f, 1.0f);
    return w;
  }
  if (life.enabled && morph == blinkMorph(characters_[c]))
    w = std::max(w, blinkAmount(frame / std::max(1.0, scene_.rate.fps()), life.blinkInterval, life.seed, life.blinkClose,
                                life.blinkHold, life.blinkOpen));
  return w;
}

bool SceneEvaluator::faceActive(size_t c) const {
  if (c >= faces_.size() || c >= scene_.characters.size() || !faces_[c].built()) return false;
  const LifeParams& life = scene_.characters[c].life;
  return life.enabled && life.face;
}

FaceState SceneEvaluator::faceState(size_t c, double frame) const {
  return faceActive(c) ? faceEval(c, frame) : FaceState{};
}

FaceState SceneEvaluator::faceEval(size_t c, double frame) const {
  FaceState fs = faces_[c].evaluate(frame);
  if (const BlinkSchedule bs = blinkSchedule(c); bs.enabled) fs.blink = faces_[c].blink(frame, bs);
  return fs;
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
    const bool face = faceActive(c);
    const FaceState fs = face ? faceEval(c, frame) : FaceState{};
    const std::string blink = life.enabled ? blinkMorph(ci) : std::string();
    const float blinkW = blink.empty() ? 0.0f
                         : face        ? fs.blink
                                       : blinkAmount(frame / std::max(1.0, scene_.rate.fps()), life.blinkInterval, life.seed,
                                                     life.blinkClose, life.blinkHold, life.blinkOpen);
    for (auto& mt : ci.rig.morphs) {
      float w = expressionWeight(c, mt.name, frame);
      if (const float po = personalityFaceOffset(c, mt.name, frame); po != 0.0f) w = std::clamp(w + po, 0.0f, 1.0f);
      if (auto it = fs.controls.find(mt.name); it != fs.controls.end()) w = std::clamp(w + it->second, 0.0f, 1.0f);
      if (mt.name == blink) w = std::max(w, blinkW);  // automatic blinks drive the character's blink morph
      else if (face && !blink.empty() && faces_[c].clearsWithBlink(mt.name))  // eye-opening controls fade while the lids close
        w *= 1.0f - std::clamp(std::max(blinkW, expressionWeight(c, blink, frame)), 0.0f, 1.0f);
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

// ------------------------------------------------------------------ body mechanics (T-045, anim/body_mechanics.h)
// ------------------------------------------------------------------ personality (T-053, anim/personality.h)
void SceneEvaluator::buildPersonalities() {
  persona_.assign(characters_.size(), PersonaSetup{});
  bool any = false;
  for (const auto& cd : scene_.characters) any |= cd.personality.is_string();
  if (!any) return;  // no profile: nothing changes (behaviour before T-053)
  // Shared data: action-unit aliases and the neutral idle amplitude (content/personality/shared.json).
  PersonalityActionUnits units = defaultPersonalityActionUnits();
  float neutralIdleH = 0.004f;
  if (auto f = findPersonalityFile(scene_.path, "shared"); !f.empty()) {
    auto j = parseJsonFile(f);
    auto u = j ? personalityActionUnitsFromJson(*j) : Result<PersonalityActionUnits>(std::unexpected(j.error()));
    if (u) {
      units = std::move(*u);
      neutralIdleH = readFloat(*j, "neutral_idle_motion_amplitude_H", neutralIdleH);
    } else warnings_.push_back(std::format("{}: {} (built-in personality defaults used)", f.string(), u.error().message));
  }
  for (size_t c = 0; c < characters_.size(); ++c) {
    const CharacterDesc& cd = scene_.characters[c];
    if (!cd.personality.is_string()) continue;
    const std::string id = cd.personality.get<std::string>();
    const auto file = findPersonalityFile(scene_.path, id);
    auto prof = file.empty() ? Result<PersonalityProfile>(fail("not found in content/personality")) : loadPersonality(file);
    if (!prof) {
      warnings_.push_back(std::format("character '{}': personality '{}': {} (no personality used)", cd.name, id, prof.error().message));
      continue;
    }
    for (auto& w : clampPersonalityToLimits(*prof)) warnings_.push_back(std::format("character '{}': {}", cd.name, w));
    PersonaSetup& ps = persona_[c];
    ps.neutralIdleH = neutralIdleH;
    // Explicit scene values outside the profile's limits are clamped (lifeParams); say so once.
    if (cd.life.blinkIntervalSet && prof->limits.blinkIntervalFrames && cd.life.blinkInterval > 0 &&
        !prof->limits.blinkIntervalFrames->contains(cd.life.blinkInterval * 24.0f))
      warnings_.push_back(std::format("character '{}': blinkInterval {:g} s outside personality '{}' limits [{:g}, {:g}] frames (clamped)",
                                      cd.name, cd.life.blinkInterval, id, prof->limits.blinkIntervalFrames->lo,
                                      prof->limits.blinkIntervalFrames->hi));
    // Face: action units -> this character's controls.
    const CharacterInstance& ci = characters_[c];
    std::vector<std::string> morphNames;
    for (auto& mt : ci.rig.morphs) morphNames.push_back(mt.name);
    auto resolve = [&](const std::string& name) { return resolveExpression(ci.asset, name, morphNames); };
    ps.face.rest = resolvePersonalityOffsets(prof->faceRestOffset, units.aliases, resolve);
    ps.face.bias = resolvePersonalityOffsets(prof->faceExpressionBias, units.aliases, resolve);
    ps.face.watching = resolvePersonalityOffsets(prof->faceWatching, units.aliases, resolve);
    const std::string blink = blinkMorph(ci);
    for (const auto& m : morphNames)
      if (m != blink && std::find(ps.activityMorphs.begin(), ps.activityMorphs.end(), m) == ps.activityMorphs.end())
        ps.activityMorphs.push_back(m);
    // Look actions: spans while the character watches (until the action's end, its next look or the shot's end).
    std::vector<std::pair<double, double>> looks;
    if (scene_.actions.is_array())
      for (const auto& a : scene_.actions)
        if (a.is_object() && a.value("type", std::string()) == "look" && a.value("character", std::string()) == cd.name &&
            a.contains("start") && a["start"].is_number())
          looks.push_back({a["start"].get<double>(), a.contains("end") && a["end"].is_number() ? a["end"].get<double>() : -1.0});
    std::sort(looks.begin(), looks.end());
    for (size_t i = 0; i < looks.size(); ++i) {
      double e = looks[i].second;
      if (e < 0) e = i + 1 < looks.size() ? looks[i + 1].first : double(scene_.frameEnd);
      ps.watchSpans.push_back({looks[i].first, e});
    }
    // Reaches (planned by the actions): their entry time against the profile's limits, reported (not changed).
    if (prof->limits.reachFrames && scene_.actions.is_array()) {
      const double per24 = 24.0 / std::max(1.0, scene_.rate.fps());
      for (const auto& a : scene_.actions) {
        if (!a.is_object() || a.value("character", std::string()) != cd.name) continue;
        const std::string type = a.value("type", std::string());
        if ((type != "reach" && type != "touch") || !a.contains("start") || !a.contains("contact") || !a["start"].is_number() ||
            !a["contact"].is_number())
          continue;
        const double frames = (a["contact"].get<double>() - a["start"].get<double>()) * per24;
        if (!prof->limits.reachFrames->contains(float(frames), 0.5f))
          warnings_.push_back(std::format("character '{}': {} at {:g} takes {:g} frames@24 to contact, outside personality '{}' "
                                          "reach limits [{:g}, {:g}]", cd.name, type, a["start"].get<double>(), frames, id,
                                          prof->limits.reachFrames->lo, prof->limits.reachFrames->hi));
      }
    }
    ps.tempo = prof->actionSpeed.value_or(1.0f);
    ps.speedLimit = prof->limits.actionSpeed;
    ps.profile = std::move(*prof);
  }
}

void SceneEvaluator::buildBodyMechanics() {
  buildPersonalities();  // T-053: profiles first (body mechanics, life and face layers read them)
  body_.assign(characters_.size(), BodyMechanicsSetup{});
  {
    std::lock_guard<std::mutex> lock(*bodyMutex_);
    bodyCache_.assign(characters_.size(), {});
  }
  // Library files (content/<kind>/<file>) are found by walking up from the scene file.
  auto findLibrary = [&](const std::string& kind, const std::string& file) -> std::filesystem::path {
    if (scene_.path.empty()) return {};
    for (auto d = std::filesystem::absolute(scene_.path).parent_path();; d = d.parent_path()) {
      auto cand = d / "content" / kind / file;
      if (std::filesystem::exists(cand)) return cand;
      if (d == d.parent_path()) return {};
    }
  };
  bool any = false;
  for (const auto& cd : scene_.characters) {
    const Json& j = cd.bodyMechanics;
    any |= (j.is_boolean() && j.get<bool>()) || (j.is_object() && readBool(j, "enabled", true));
  }
  if (!any) return;
  BodyMechanicsRigProfile profile;
  if (auto f = findLibrary("rig_profiles", "body_mechanics.json"); !f.empty()) {
    auto j = parseJsonFile(f);
    auto p = j ? bodyMechanicsRigProfileFromJson(*j) : Result<BodyMechanicsRigProfile>(std::unexpected(j.error()));
    if (p) profile = std::move(*p);
    else warnings_.push_back(std::format("{}: {} (built-in body mechanics rig defaults used)", f.string(), p.error().message));
  }
  const double fps = scene_.rate.fps();
  const double perFrame24 = fps / 24.0;  // profile frame values are at 24 fps
  for (size_t c = 0; c < characters_.size(); ++c) {
    const CharacterDesc& cd = scene_.characters[c];
    const Json& j = cd.bodyMechanics;
    BodyMechanicsSetup& b = body_[c];
    if (!((j.is_boolean() && j.get<bool>()) || j.is_object())) continue;
    b.params.enabled = true;
    b.params.seed = cd.life.seed * 0x2545F491u + 7u;
    applyBodyMechanicsLimits(b.params, profile.limits);
    // Personality: the body mechanics' own "personality" (profile id) wins; else the character's profile (T-053).
    const std::string ownId = j.is_object() ? readString(j, "personality") : std::string();
    if (!ownId.empty()) {
      const auto f = findPersonalityFile(scene_.path, ownId);
      auto pr = f.empty() ? Result<PersonalityProfile>(fail("not found")) : loadPersonality(f);
      if (pr) applyPersonalityToBodyMechanics(b.params, *pr);
      else warnings_.push_back(std::format("character '{}': body mechanics personality '{}': {} (neutral tuning used)", cd.name,
                                           ownId, pr.error().message));
    } else if (const PersonalityProfile* P = personality(c)) {
      applyPersonalityToBodyMechanics(b.params, *P);
    }
    if (j.is_object()) applyBodyMechanicsOverrides(b.params, j);
    b.rig = bindBodyMechanics(characters_[c].asset.skeleton, profile);
    b.fast = followKernel(0.0f, float(std::max(2.0, 0.5 * b.params.settleFrames * perFrame24)), b.params.overshoot);
    b.slow = followKernel(float(b.params.lagFrames * perFrame24), float(b.params.settleFrames * perFrame24), b.params.overshoot);
    b.weight = followKernel(float(b.params.lagFrames * perFrame24), float(2.0 * b.params.settleFrames * perFrame24), 0.0f);
  }
}

BodyDrivers SceneEvaluator::bodyDrivers(size_t c, long long frame) const {
  if (c >= body_.size()) return {};
  if (bodyCacheOn_) {
    std::lock_guard<std::mutex> lock(*bodyMutex_);
    if (c < bodyCache_.size())
      if (auto it = bodyCache_[c].find(frame); it != bodyCache_[c].end()) return it->second;
  }
  const CharacterDesc& cd = scene_.characters[c];
  const CharacterInstance& ci = characters_[c];
  const Skeleton& sk = ci.asset.skeleton;
  const Clip& clip = scene_.animation;
  const std::string prefix = cd.name + "/";
  const double f = double(frame);
  Pose pose = evaluatePose(sk, clip, prefix, f, &ci.asset.defaultPose);
  float yaw = clip.evaluate(cd.name + ".yaw", f, vec3(cd.yawDeg)).x;
  if (hasClipLayers(c)) {
    float clipYaw = 0;
    applyClips(c, f, pose, clipYaw);
    yaw += clipYaw;
  }
  const mat4 toChar = glm::inverse(objectMatrixLocal(clip.evaluate(cd.name + ".position", f, cd.position), yaw, 1.0f));
  std::array<vec4, 2> ik{vec4(0), vec4(0)};
  const BodyMechanicsRig& rig = body_[c].rig;
  for (int s = 0; s < 2; ++s) {
    if (rig.hand[size_t(s)] < 0) continue;
    const std::string name = prefix + "ik." + sk.bones[size_t(rig.hand[size_t(s)])].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    const float w = clip.evaluate(name + ".weight", f, vec3(1)).x;
    ik[size_t(s)] = vec4(vec3(toChar * vec4(t->evaluate(f), 1.0f)), w);
  }
  BodyDrivers d = measureBodyDrivers(sk, rig, pose, ik);
  if (c < walkSpans_.size())
    for (auto [a, e] : walkSpans_[c]) {
      const double x = f < a ? (f - (a - 4)) / 4 : f > e ? (e + 4 - f) / 4 : 1.0;
      const double cl = std::clamp(x, 0.0, 1.0);
      d.walk = std::max(d.walk, float(cl * cl * (3 - 2 * cl)));
    }
  if (bodyCacheOn_) {
    std::lock_guard<std::mutex> lock(*bodyMutex_);
    if (c < bodyCache_.size()) bodyCache_[c][frame] = d;
  }
  return d;
}

BodyDrivers SceneEvaluator::filteredDrivers(size_t c, long long frame, const std::vector<float>& kernel) const {
  BodyDrivers out;
  out.standing = 0;
  for (size_t k = 0; k < kernel.size(); ++k)
    if (kernel[k] != 0) out = out + bodyDrivers(c, frame - (long long)k) * kernel[k];
  // Standing and walking are gates, not motion: no overshoot.
  out.standing = std::clamp(out.standing, 0.0f, 1.0f);
  out.walk = std::max(std::clamp(out.walk, 0.0f, 1.0f), bodyDrivers(c, frame).walk);
  return out;
}

BodyMechanicsInput SceneEvaluator::bodyMechanicsInput(size_t c, double frame) const {
  BodyMechanicsInput in;
  if (!bodyMechanicsActive(c)) return in;
  const BodyMechanicsSetup& b = body_[c];
  const long long f0 = (long long)std::floor(frame);
  const float t = float(frame - double(f0));
  auto lerp = [&](const std::vector<float>& kernel) {
    const BodyDrivers a = filteredDrivers(c, f0, kernel);
    return t > 1e-6f ? a * (1 - t) + filteredDrivers(c, f0 + 1, kernel) * t : a;
  };
  in.fast = lerp(b.fast);
  in.slow = lerp(b.slow);
  in.weight = lerp(b.weight);
  in.idle = idleWeightShift(frame / std::max(1.0, scene_.rate.fps()), b.params);
  return in;
}

void SceneEvaluator::applyBodyMechanicsAt(size_t c, double frame, Pose& pose) const {
  const BodyMechanicsSetup& b = body_[c];
  applyBodyMechanics(characters_[c].asset.skeleton, b.rig, b.params, bodyMechanicsInput(c, frame), pose);
}

}  // namespace plush
