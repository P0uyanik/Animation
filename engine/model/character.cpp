#include "model/character.h"

#include <algorithm>
#include <array>

namespace plush {

Result<SdfPrim> primFromJson(const Json& j) {
  SdfPrim p;
  p.name = readString(j, "name");
  std::string type = readString(j, "type", "ellipsoid");
  if (type == "ellipsoid") p.type = PrimType::Ellipsoid;
  else if (type == "capsule") p.type = PrimType::Capsule;
  else if (type == "roundCone") p.type = PrimType::RoundCone;
  else if (type == "roundBox") p.type = PrimType::RoundBox;
  else return fail(std::format("primitive '{}': unknown type '{}'", p.name, type));
  p.bone = readString(j, "bone");
  p.center = readVec3(j, "center", p.center);
  p.radii = readVec3(j, p.type == PrimType::RoundBox ? "halfSize" : "radii", p.radii);
  p.rotation = eulerDegreesToQuat(readVec3(j, "rotationDeg", vec3(0)));
  p.rounding = readFloat(j, "rounding", p.rounding);
  p.a = readVec3(j, "a", p.a);
  p.b = readVec3(j, "b", p.b);
  p.r1 = readFloat(j, "r1", readFloat(j, "r", p.r1));
  p.r2 = readFloat(j, "r2", p.r1);
  p.blend = readFloat(j, "blend", p.blend);
  p.subtract = readBool(j, "subtract", false);
  p.mirrorX = readBool(j, "mirror", false);
  return p;
}

Result<SdfPart> partFromJson(const Json& j) {
  SdfPart part;
  part.name = readString(j, "name");
  part.material = readString(j, "material");
  part.voxelSize = readFloat(j, "voxelSize", part.voxelSize);
  part.skinFalloff = readFloat(j, "skinFalloff", part.skinFalloff);
  part.noiseAmplitude = readFloat(j, "noiseAmplitude", part.noiseAmplitude);
  part.noiseScale = readFloat(j, "noiseScale", part.noiseScale);
  std::vector<SdfPrim> prims;
  if (auto it = j.find("prims"); it != j.end() && it->is_array()) {
    for (auto& pj : *it) {
      auto p = primFromJson(pj);
      if (!p) return fail(std::format("part '{}': {}", part.name, p.error().message));
      prims.push_back(*p);
    }
  }
  part.prims = expandMirrors(prims);
  return part;
}

Json primToJson(const SdfPrim& p) {
  const char* types[] = {"ellipsoid", "capsule", "roundCone", "roundBox"};
  Json j = {{"name", p.name}, {"type", types[int(p.type)]}, {"blend", p.blend}};
  if (!p.bone.empty()) j["bone"] = p.bone;
  if (p.subtract) j["subtract"] = true;
  vec3 euler = glm::degrees(glm::eulerAngles(p.rotation));
  switch (p.type) {
    case PrimType::Ellipsoid:
      j["center"] = toJson(p.center);
      j["radii"] = toJson(p.radii);
      j["rotationDeg"] = toJson(euler);
      break;
    case PrimType::RoundBox:
      j["center"] = toJson(p.center);
      j["halfSize"] = toJson(p.radii);
      j["rounding"] = p.rounding;
      j["rotationDeg"] = toJson(euler);
      break;
    case PrimType::Capsule:
      j["a"] = toJson(p.a);
      j["b"] = toJson(p.b);
      j["r"] = p.r1;
      break;
    case PrimType::RoundCone:
      j["a"] = toJson(p.a);
      j["b"] = toJson(p.b);
      j["r1"] = p.r1;
      j["r2"] = p.r2;
      break;
  }
  return j;
}

Json partToJson(const SdfPart& part) {
  Json prims = Json::array();
  for (auto& p : part.prims) prims.push_back(primToJson(p));
  return {{"name", part.name}, {"material", part.material}, {"voxelSize", part.voxelSize}, {"skinFalloff", part.skinFalloff},
          {"noiseAmplitude", part.noiseAmplitude}, {"noiseScale", part.noiseScale}, {"prims", prims}};
}

Json characterToJson(const CharacterAsset& c) {
  Json bones = Json::array(), mats = Json::array(), parts = Json::array(), fuzz = Json::array(), locks = Json::array();
  for (auto& b : c.skeleton.bones) {
    Json bj = {{"name", b.name}, {"head", toJson(b.head)}};
    if (b.parent >= 0) bj["parent"] = c.skeleton.bones[size_t(b.parent)].name;
    bones.push_back(bj);
  }
  for (auto& m : c.materials) mats.push_back(materialToJson(m));
  for (auto& p : c.parts) parts.push_back(partToJson(p));
  for (auto& f : c.fuzz) {
    const FuzzParams& q = f.params;
    fuzz.push_back({{"part", f.part}, {"material", f.material}, {"density", q.density}, {"length", q.length},
                    {"lengthJitter", q.lengthJitter}, {"radius", q.radius}, {"tilt", q.tilt}, {"curl", q.curl},
                    {"comb", q.comb}, {"combOrigin", toJson(q.combOrigin)}, {"segments", q.segments}, {"seed", q.seed},
                    {"strayFraction", q.strayFraction}, {"strayLength", q.strayLength}});
  }
  for (auto& l : c.locks) {
    const LockParams& q = l.params;
    locks.push_back({{"material", l.material}, {"bone", l.bone}, {"headCenter", toJson(q.headCenter)},
                     {"headRadii", toJson(q.headRadii)}, {"count", q.count}, {"azimuthMinDeg", q.azimuthMinDeg},
                     {"azimuthMaxDeg", q.azimuthMaxDeg}, {"elevationDeg", q.elevationDeg}, {"lengthMin", q.lengthMin},
                     {"lengthMax", q.lengthMax}, {"lockRadius", q.lockRadius}, {"coreRatio", q.coreRatio},
                     {"fibersPerLock", q.fibersPerLock}, {"fiberRadius", q.fiberRadius}, {"twist", q.twist},
                     {"wave", q.wave}, {"waveLength", q.waveLength}, {"headBottom", q.headBottom},
                     {"bodyClearance", q.bodyClearance}, {"sideClearance", q.sideClearance}, {"frizz", q.frizz},
                     {"segments", q.segments}, {"seed", q.seed}});
  }
  return {{"format", "plush.character"}, {"version", 1}, {"name", c.name}, {"skeleton", bones}, {"materials", mats},
          {"parts", parts}, {"fuzz", fuzz}, {"locks", locks}};
}

Result<void> resolveBones(CharacterAsset& c) {
  for (auto& part : c.parts)
    for (auto& prim : part.prims) {
      prim.boneIndex = prim.bone.empty() ? -1 : c.skeleton.find(prim.bone);
      if (!prim.bone.empty() && prim.boneIndex < 0)
        return fail(std::format("part '{}', primitive '{}': unknown bone '{}'", part.name, prim.name, prim.bone));
    }
  return {};
}

namespace {
FuzzParams fuzzFromJson(const Json& j) {
  FuzzParams f;
  f.density = readFloat(j, "density", f.density);
  f.length = readFloat(j, "length", f.length);
  f.lengthJitter = readFloat(j, "lengthJitter", f.lengthJitter);
  f.radius = readFloat(j, "radius", f.radius);
  f.tilt = readFloat(j, "tilt", f.tilt);
  f.curl = readFloat(j, "curl", f.curl);
  f.comb = readFloat(j, "comb", f.comb);
  f.combOrigin = readVec3(j, "combOrigin", f.combOrigin);
  f.segments = readInt(j, "segments", f.segments);
  f.seed = uint32_t(readInt(j, "seed", int(f.seed)));
  f.strayFraction = readFloat(j, "strayFraction", f.strayFraction);
  f.strayLength = readFloat(j, "strayLength", f.strayLength);
  return f;
}
LockParams locksFromJson(const Json& j) {
  LockParams l;
  l.headCenter = readVec3(j, "headCenter", l.headCenter);
  l.headRadii = readVec3(j, "headRadii", l.headRadii);
  l.count = readInt(j, "count", l.count);
  l.azimuthMinDeg = readFloat(j, "azimuthMinDeg", l.azimuthMinDeg);
  l.azimuthMaxDeg = readFloat(j, "azimuthMaxDeg", l.azimuthMaxDeg);
  l.elevationDeg = readFloat(j, "elevationDeg", l.elevationDeg);
  l.lengthMin = readFloat(j, "lengthMin", l.lengthMin);
  l.lengthMax = readFloat(j, "lengthMax", l.lengthMax);
  l.lockRadius = readFloat(j, "lockRadius", l.lockRadius);
  l.coreRatio = readFloat(j, "coreRatio", l.coreRatio);
  l.fibersPerLock = readInt(j, "fibersPerLock", l.fibersPerLock);
  l.fiberRadius = readFloat(j, "fiberRadius", l.fiberRadius);
  l.twist = readFloat(j, "twist", l.twist);
  l.wave = readFloat(j, "wave", l.wave);
  l.waveLength = readFloat(j, "waveLength", l.waveLength);
  l.headBottom = readFloat(j, "headBottom", l.headBottom);
  l.bodyClearance = readFloat(j, "bodyClearance", l.bodyClearance);
  l.sideClearance = readFloat(j, "sideClearance", l.sideClearance);
  l.frizz = readFloat(j, "frizz", l.frizz);
  l.segments = readInt(j, "segments", l.segments);
  l.seed = uint32_t(readInt(j, "seed", int(l.seed)));
  return l;
}
}  // namespace

Result<CharacterAsset> characterFromJson(const Json& j) {
  if (readString(j, "format") != "plush.character") return fail("not a plush.character file");
  if (readInt(j, "version", 0) != 1) return fail("unsupported plush.character version");
  CharacterAsset c;
  c.name = readString(j, "name", "character");
  // Skeleton (mirror bones are created right after their source bone).
  if (auto it = j.find("skeleton"); it != j.end() && it->is_array()) {
    for (auto& bj : *it) {
      std::string name = readString(bj, "name");
      std::string parent = readString(bj, "parent");
      vec3 head = readVec3(bj, "head", vec3(0));
      auto addBone = [&](const std::string& n, const std::string& par, vec3 h) -> Result<void> {
        Bone b{n, -1, h};
        if (!par.empty()) {
          b.parent = c.skeleton.find(par);
          if (b.parent < 0) return fail(std::format("bone '{}': parent '{}' not defined before it", n, par));
        }
        c.skeleton.bones.push_back(b);
        return {};
      };
      if (auto r = addBone(name, parent, head); !r) return std::unexpected(r.error());
      if (readBool(bj, "mirror", false))
        if (auto r = addBone(mirrorName(name), mirrorName(parent), vec3(-head.x, head.y, head.z)); !r)
          return std::unexpected(r.error());
    }
  }
  if (c.skeleton.bones.empty()) c.skeleton.bones.push_back({"root", -1, vec3(0)});
  if (auto it = j.find("materials"); it != j.end() && it->is_array())
    for (auto& mj : *it) {
      auto m = materialFromJson(mj);
      if (!m) return std::unexpected(m.error());
      c.materials.push_back(*m);
    }
  if (auto it = j.find("parts"); it != j.end() && it->is_array())
    for (auto& pj : *it) {
      auto part = partFromJson(pj);
      if (!part) return std::unexpected(part.error());
      for (auto& prim : part->prims) {
        if (prim.bone.empty()) continue;
        prim.boneIndex = c.skeleton.find(prim.bone);
        if (prim.boneIndex < 0)
          return fail(std::format("part '{}', primitive '{}': unknown bone '{}'", part->name, prim.name, prim.bone));
      }
      c.parts.push_back(std::move(*part));
    }
  if (auto it = j.find("fuzz"); it != j.end() && it->is_array())
    for (auto& fj : *it) c.fuzz.push_back({readString(fj, "part"), readString(fj, "material"), fuzzFromJson(fj)});
  if (auto it = j.find("locks"); it != j.end() && it->is_array())
    for (auto& lj : *it) c.locks.push_back({readString(lj, "material"), readString(lj, "bone", "head"), locksFromJson(lj)});
  return c;
}

Result<CharacterAsset> loadCharacter(const std::filesystem::path& path) {
  auto j = parseJsonFile(path);
  if (!j) return std::unexpected(j.error());
  auto c = characterFromJson(*j);
  if (!c) return fail(std::format("{}: {}", path.string(), c.error().message));
  return c;
}

void computeSkinWeights(const SdfPart& part, int boneCount, const Mesh& mesh, std::vector<glm::ivec4>& joints,
                        std::vector<vec4>& weights) {
  joints.assign(mesh.positions.size(), glm::ivec4(0));
  weights.assign(mesh.positions.size(), vec4(1, 0, 0, 0));
  std::vector<const SdfPrim*> driving;
  for (auto& p : part.prims)
    if (!p.subtract && p.boneIndex >= 0 && p.boneIndex < boneCount) driving.push_back(&p);
  if (driving.empty()) return;
  const float falloff = std::max(1e-4f, part.skinFalloff);
  parallelFor(mesh.positions.size(), [&](size_t v) {
    vec3 p = mesh.positions[v];
    std::array<float, 64> dist{};
    float dmin = 1e30f;
    size_t n = std::min<size_t>(driving.size(), dist.size());
    for (size_t i = 0; i < n; ++i) {
      dist[i] = sdfPrim(*driving[i], p);
      dmin = std::min(dmin, dist[i]);
    }
    // Accumulate per bone (small linear map).
    std::array<std::pair<int, float>, 16> acc{};
    int used = 0;
    for (size_t i = 0; i < n; ++i) {
      float w = std::exp(-(dist[i] - dmin) / falloff);
      if (w < 1e-4f) continue;
      int bone = driving[i]->boneIndex, k = 0;
      while (k < used && acc[size_t(k)].first != bone) ++k;
      if (k == used) {
        if (used == int(acc.size())) continue;
        acc[size_t(used++)] = {bone, 0.0f};
      }
      acc[size_t(k)].second += w;
    }
    std::sort(acc.begin(), acc.begin() + used, [](auto& a, auto& b) { return a.second > b.second; });
    glm::ivec4 jt(0);
    vec4 wt(0);
    float sum = 0;
    for (int k = 0; k < std::min(used, 4); ++k) {
      jt[k] = acc[size_t(k)].first;
      wt[k] = acc[size_t(k)].second;
      sum += wt[k];
    }
    joints[v] = jt;
    weights[v] = sum > 0 ? wt / sum : vec4(1, 0, 0, 0);
  }, 512);
}

CharacterRig buildCharacter(const CharacterAsset& asset, const BuildOptions& opt) {
  CharacterRig rig;
  Stopwatch sw;
  for (const auto& part : asset.parts) {
    SkinnedMesh sm;
    sm.part = part.name;
    sm.material = part.material;
    sm.rest = meshSdfPart(part, opt.voxelScale);
    computeSkinWeights(part, int(asset.skeleton.bones.size()), sm.rest, sm.joints, sm.weights);
    logDebug("part '{}': {} vertices, {} triangles", part.name, sm.rest.positions.size(), sm.rest.triangleCount());
    rig.meshes.push_back(std::move(sm));
  }
  if (opt.fuzz) {
    for (const auto& layer : asset.fuzz) {
      auto it = std::find_if(rig.meshes.begin(), rig.meshes.end(), [&](auto& m) { return m.part == layer.part; });
      if (it == rig.meshes.end()) {
        logWarn("fuzz layer refers to unknown part '{}'", layer.part);
        continue;
      }
      BoundFuzz bf;
      bf.mesh = int(it - rig.meshes.begin());
      bf.material = layer.material;
      bf.fibers = generateSurfaceFibers(it->rest, layer.params, opt.fuzzDensity);
      rig.fuzz.push_back(std::move(bf));
    }
    for (const auto& layer : asset.locks) {
      BoundLocks bl;
      bl.bone = std::max(0, asset.skeleton.find(layer.bone));
      bl.material = layer.material;
      bl.rest = generateLocks(layer.params, opt.fuzzDensity);
      rig.locks.push_back(std::move(bl));
    }
  }
  size_t fibers = 0;
  for (auto& f : rig.fuzz) fibers += f.fibers.fiberCount();
  for (auto& l : rig.locks) fibers += l.rest.fiberCount;
  logInfo("built character '{}' in {:.2f}s: {} parts, {} fibers", asset.name, sw.seconds(), rig.meshes.size(), fibers);
  return rig;
}

PosedCharacter poseCharacter(const CharacterRig& rig, const std::vector<mat4>& skin) {
  PosedCharacter out;
  for (const auto& sm : rig.meshes) {
    auto m = std::make_shared<Mesh>();
    m->indices = sm.rest.indices;
    m->pref = sm.rest.positions;
    size_t n = sm.rest.positions.size();
    m->positions.resize(n);
    m->normals.resize(n);
    parallelFor(n, [&](size_t v) {
      mat4 blended(0.0f);
      for (int k = 0; k < 4; ++k) {
        float w = sm.weights[v][k];
        if (w > 0) blended += w * skin[size_t(sm.joints[v][k])];
      }
      m->positions[v] = vec3(blended * vec4(sm.rest.positions[v], 1.0f));
      vec3 nn = mat3(blended) * sm.rest.normals[v];
      float len = glm::length(nn);
      m->normals[v] = len > 0 ? nn / len : sm.rest.normals[v];
    }, 2048);
    out.meshes.push_back(std::move(m));
  }
  for (const auto& bf : rig.fuzz) out.fuzz.push_back(deformSurfaceFibers(bf.fibers, *out.meshes[size_t(bf.mesh)]));
  for (const auto& bl : rig.locks) out.locks.push_back(transformFibers(bl.rest, skin[size_t(bl.bone)]));
  return out;
}

}  // namespace plush
