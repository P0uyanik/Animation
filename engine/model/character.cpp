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
  else if (type == "disc") p.type = PrimType::Disc;
  else return fail(std::format("primitive '{}': unknown type '{}'", p.name, type));
  p.bone = readString(j, "bone");
  p.center = readVec3(j, "center", p.center);
  p.radii = readVec3(j, (p.type == PrimType::RoundBox || p.type == PrimType::Disc) ? "halfSize" : "radii", p.radii);
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
  std::string pattern = readString(j, "pattern", "none");
  part.pattern = pattern == "strands" ? SurfacePattern::Strands : pattern == "knit" ? SurfacePattern::Knit
                 : pattern == "ribbed" ? SurfacePattern::Ribbed : SurfacePattern::None;
  part.patternAmplitude = readFloat(j, "patternAmplitude", part.patternAmplitude);
  part.patternScale = readFloat(j, "patternScale", part.patternScale);
  part.patternCenter = readVec3(j, "patternCenter", part.patternCenter);
  part.skinSmoothing = readInt(j, "skinSmoothing", part.skinSmoothing);
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
  const char* types[] = {"ellipsoid", "capsule", "roundCone", "roundBox", "disc"};
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
    case PrimType::Disc:
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
          {"noiseAmplitude", part.noiseAmplitude}, {"noiseScale", part.noiseScale},
          {"pattern", part.pattern == SurfacePattern::Strands ? "strands" : part.pattern == SurfacePattern::Knit ? "knit"
                      : part.pattern == SurfacePattern::Ribbed ? "ribbed" : "none"},
          {"patternAmplitude", part.patternAmplitude}, {"patternScale", part.patternScale},
          {"patternCenter", toJson(part.patternCenter)}, {"skinSmoothing", part.skinSmoothing}, {"prims", prims}};
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
    locks.push_back({{"material", l.material}, {"coreMaterial", l.coreMaterial}, {"bone", l.bone}, {"headCenter", toJson(q.headCenter)},
                     {"headRadii", toJson(q.headRadii)}, {"count", q.count}, {"azimuthMinDeg", q.azimuthMinDeg},
                     {"azimuthMaxDeg", q.azimuthMaxDeg}, {"elevationDeg", q.elevationDeg}, {"lengthMin", q.lengthMin},
                     {"lengthMax", q.lengthMax}, {"lockRadius", q.lockRadius}, {"coreRatio", q.coreRatio},
                     {"fibersPerLock", q.fibersPerLock}, {"fiberRadius", q.fiberRadius}, {"twist", q.twist},
                     {"wave", q.wave}, {"waveLength", q.waveLength}, {"headBottom", q.headBottom},
                     {"bodyClearance", q.bodyClearance}, {"sideClearance", q.sideClearance}, {"frizz", q.frizz},
                     {"segments", q.segments}, {"seed", q.seed}});
  }
  Json exprs = Json::array();
  for (auto& e : c.expressions) exprs.push_back({{"name", e.name}, {"part", e.part}, {"set", e.set}, {"add", e.add}});
  Json groups = Json::array(), pose = Json::object(), dexpr = Json::object();
  for (auto& g : c.lockGroups) groups.push_back(lockGroupToJson(g));
  for (auto& [b, v] : c.defaultPose) pose[b] = toJson(v);
  for (auto& [e, w] : c.defaultExpressions) dexpr[e] = w;
  return {{"format", "plush.character"}, {"version", 1}, {"name", c.name}, {"skeleton", bones}, {"materials", mats},
          {"skinning", c.dualQuaternion ? "dualQuaternion" : "linear"}, {"parts", parts}, {"fuzz", fuzz},
          {"locks", locks}, {"lockGroups", groups}, {"expressions", exprs}, {"defaultPose", pose},
          {"defaultExpressions", dexpr}};
}

Result<LockGroup> lockGroupFromJson(const Json& j) {
  LockGroup g;
  g.name = readString(j, "name", "locks");
  g.bone = readString(j, "bone", "head");
  g.material = readString(j, "material");
  g.coreMaterial = readString(j, "coreMaterial");
  LockGroupParams& p = g.params;
  p.samples = readInt(j, "samples", p.samples);
  p.fuzzDensity = readFloat(j, "fuzzDensity", p.fuzzDensity);
  p.fuzzLength = readFloat(j, "fuzzLength", p.fuzzLength);
  p.fuzzRadius = readFloat(j, "fuzzRadius", p.fuzzRadius);
  p.fuzzTilt = readFloat(j, "fuzzTilt", p.fuzzTilt);
  p.strayFraction = readFloat(j, "strayFraction", p.strayFraction);
  p.strayLength = readFloat(j, "strayLength", p.strayLength);
  p.roundTip = readBool(j, "roundTip", p.roundTip);
  p.seed = uint32_t(readInt(j, "seed", int(p.seed)));
  for (auto& lj : j.value("locks", Json::array())) {
    LockCurve L;
    for (auto& pt : lj.value("points", Json::array()))
      if (pt.is_array() && pt.size() == 3) L.points.emplace_back(pt[0].get<float>(), pt[1].get<float>(), pt[2].get<float>());
    if (L.points.size() < 2) return fail(std::format("lock group '{}': a lock needs at least 2 points", g.name));
    L.rootRadius = readFloat(lj, "rootRadius", L.rootRadius);
    L.tipRadius = readFloat(lj, "tipRadius", L.tipRadius);
    L.curlRadius = readFloat(lj, "curlRadius", L.curlRadius);
    L.curlTurns = readFloat(lj, "curlTurns", L.curlTurns);
    L.curlPhase = readFloat(lj, "curlPhase", L.curlPhase);
    g.locks.push_back(std::move(L));
  }
  return g;
}

Json lockGroupToJson(const LockGroup& g) {
  Json locks = Json::array();
  for (auto& L : g.locks) {
    Json pts = Json::array();
    for (auto& p : L.points) pts.push_back(toJson(p));
    locks.push_back({{"points", pts}, {"rootRadius", L.rootRadius}, {"tipRadius", L.tipRadius},
                     {"curlRadius", L.curlRadius}, {"curlTurns", L.curlTurns}, {"curlPhase", L.curlPhase}});
  }
  const LockGroupParams& p = g.params;
  return {{"name", g.name}, {"bone", g.bone}, {"material", g.material}, {"coreMaterial", g.coreMaterial},
          {"samples", p.samples}, {"fuzzDensity", p.fuzzDensity}, {"fuzzLength", p.fuzzLength}, {"fuzzRadius", p.fuzzRadius},
          {"fuzzTilt", p.fuzzTilt}, {"strayFraction", p.strayFraction}, {"strayLength", p.strayLength},
          {"roundTip", p.roundTip}, {"seed", p.seed}, {"locks", locks}};
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
    for (auto& lj : *it)
      c.locks.push_back({readString(lj, "material"), readString(lj, "coreMaterial"), readString(lj, "bone", "head"), locksFromJson(lj)});
  c.dualQuaternion = readString(j, "skinning", "linear") == "dualQuaternion";
  if (auto it = j.find("lockGroups"); it != j.end() && it->is_array())
    for (auto& gj : *it) {
      auto g = lockGroupFromJson(gj);
      if (!g) return std::unexpected(g.error());
      if (c.skeleton.find(g->bone) < 0) return fail(std::format("lock group '{}': unknown bone '{}'", g->name, g->bone));
      bool mirror = readBool(gj, "mirror", false);
      c.lockGroups.push_back(*g);
      if (mirror) {
        LockGroup m = *g;
        m.name = mirrorName(g->name) == g->name ? g->name + ".mirror" : mirrorName(g->name);
        m.bone = mirrorName(g->bone);
        m.params.seed += 7919;
        for (auto& L : m.locks)
          for (auto& p : L.points) p.x = -p.x;
        c.lockGroups.push_back(m);
      }
    }
  if (auto it = j.find("defaultPose"); it != j.end() && it->is_object())
    for (auto& [bone, v] : it->items()) c.defaultPose[bone] = vec3(v[0].get<float>(), v[1].get<float>(), v[2].get<float>());
  if (auto it = j.find("defaultExpressions"); it != j.end() && it->is_object())
    for (auto& [name, v] : it->items()) c.defaultExpressions[name] = v.get<float>();
  if (auto it = j.find("expressions"); it != j.end() && it->is_array())
    for (auto& ej : *it) {
      Expression e{readString(ej, "name"), readString(ej, "part"), {}, {}};
      for (auto& s : ej.value("set", Json::array())) e.set.push_back(s);
      for (auto& a : ej.value("add", Json::array())) e.add.push_back(a);
      c.expressions.push_back(std::move(e));
    }
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
    if (part.skinSmoothing > 0)
      smoothSkinWeights(sm.rest, int(asset.skeleton.bones.size()), part.skinSmoothing, sm.joints, sm.weights);
    logDebug("part '{}': {} vertices, {} triangles", part.name, sm.rest.positions.size(), sm.rest.triangleCount());
    rig.meshes.push_back(std::move(sm));
  }
  for (const auto& e : asset.expressions) {
    auto it = std::find_if(asset.parts.begin(), asset.parts.end(), [&](auto& p) { return p.name == e.part; });
    if (it == asset.parts.end()) {
      logWarn("expression '{}' refers to unknown part '{}'", e.name, e.part);
      continue;
    }
    size_t mi = size_t(it - asset.parts.begin());
    auto modified = applyExpression(*it, e);
    if (!modified) {
      logWarn("expression '{}': {}", e.name, modified.error().message);
      continue;
    }
    const Mesh& rest = rig.meshes[mi].rest;
    MorphTarget mt;
    mt.name = e.name;
    mt.mesh = int(mi);
    std::vector<vec3> dp(rest.positions.size(), vec3(0)), dn(rest.positions.size(), vec3(0));
    std::vector<uint8_t> moved(rest.positions.size(), 0);
    const float eps = std::max(1e-5f, 0.1f * it->voxelSize * opt.voxelScale);
    parallelFor(rest.positions.size(), [&](size_t v) {
      vec3 p0 = rest.positions[v];
      if (std::abs(sdfPart(*modified, p0) - sdfPart(*it, p0)) < 1e-6f) return;  // surface unchanged here
      vec3 p = p0;
      for (int k = 0; k < 8; ++k) {
        vec3 g = sdfGradient(*modified, p, eps);
        float g2 = glm::dot(g, g);
        if (g2 < 1e-12f) break;
        p -= g * (sdfPart(*modified, p) / g2);
      }
      vec3 d = p - p0;
      float len = glm::length(d);
      if (len > 0.03f) d *= 0.03f / len;
      dp[v] = d;
      moved[v] = 1;
    }, 1024);
    // Projection alone bunches vertices up where the surface folds inwards (an opening mouth): neighbouring
    // vertices land on nearly the same point and the surface crumples. Relax the moved vertices towards their
    // neighbours' average and project back onto the edited surface, a few times (tangential smoothing).
    {
      std::vector<std::vector<uint32_t>> nbr(rest.positions.size());
      for (size_t t = 0; t < rest.triangleCount(); ++t)
        for (int k = 0; k < 3; ++k) {
          uint32_t a = rest.indices[3 * t + size_t(k)], b = rest.indices[3 * t + size_t((k + 1) % 3)];
          if (moved[a] || moved[b]) {
            nbr[a].push_back(b);
            nbr[b].push_back(a);
          }
        }
      std::vector<vec3> cur(rest.positions.size());
      for (size_t v = 0; v < cur.size(); ++v) cur[v] = rest.positions[v] + dp[v];
      for (int iter = 0; iter < 12; ++iter) {
        std::vector<vec3> next = cur;
        parallelFor(cur.size(), [&](size_t v) {
          if (!moved[v] || nbr[v].empty()) return;
          vec3 avg(0);
          for (uint32_t u : nbr[v]) avg += cur[u];
          vec3 p = glm::mix(cur[v], avg / float(nbr[v].size()), 0.5f);
          for (int k = 0; k < 3; ++k) {
            vec3 g = sdfGradient(*modified, p, eps);
            float g2 = glm::dot(g, g);
            if (g2 < 1e-12f) break;
            p -= g * (sdfPart(*modified, p) / g2);
          }
          next[v] = p;
        }, 1024);
        cur.swap(next);
      }
      parallelFor(cur.size(), [&](size_t v) {
        if (!moved[v]) return;
        vec3 d = cur[v] - rest.positions[v];
        float len = glm::length(d);
        if (len > 0.03f) d *= 0.03f / len;
        dp[v] = d;
        vec3 g = sdfGradient(*modified, rest.positions[v] + d, eps);
        float lg = glm::length(g);
        dn[v] = (lg > 0 ? g / lg : rest.normals[v]) - rest.normals[v];
      }, 1024);
    }
    for (size_t v = 0; v < moved.size(); ++v)
      if (moved[v]) {
        mt.vertices.push_back(uint32_t(v));
        mt.dpos.push_back(dp[v]);
        mt.dnrm.push_back(dn[v]);
      }
    logDebug("expression '{}': {} vertices", e.name, mt.vertices.size());
    rig.morphs.push_back(std::move(mt));
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
      FiberSet all = generateLocks(layer.params, opt.fuzzDensity);
      bl.coreMaterial = layer.coreMaterial;
      if (layer.coreMaterial.empty()) {
        bl.rest = std::move(all);
      } else {  // split pinned cores from the fibres
        for (size_t c = 0; c + 1 < all.curveOffsets.size(); ++c) {
          FiberSet& dst = all.pinned[c] ? bl.cores : bl.rest;
          if (dst.curveOffsets.empty()) dst.curveOffsets.push_back(0);
          uint32_t base = uint32_t(dst.points.size());
          for (uint32_t i = all.curveOffsets[c]; i < all.curveOffsets[c + 1]; ++i) dst.points.push_back(all.points[i]);
          for (uint32_t i = 0; i + 1 < all.curveOffsets[c + 1] - all.curveOffsets[c]; ++i) dst.segmentStarts.push_back(base + i);
          dst.curveOffsets.push_back(uint32_t(dst.points.size()));
          dst.pinned.push_back(all.pinned[c]);
          dst.fiberCount++;
        }
      }
      rig.locks.push_back(std::move(bl));
    }
  }
  for (const auto& g : asset.lockGroups) {
    BoundLocks bl;
    bl.bone = std::max(0, asset.skeleton.find(g.bone));
    bl.material = g.material;
    bl.coreMaterial = g.coreMaterial.empty() ? g.material : g.coreMaterial;
    LockGroupParams prm = g.params;
    if (!opt.fuzz) prm.fuzzDensity = 0;
    generateLockGroup(prm, g.locks, opt.fuzzDensity, bl.cores, bl.rest);
    rig.locks.push_back(std::move(bl));
  }
  size_t fibers = 0;
  for (auto& f : rig.fuzz) fibers += f.fibers.fiberCount();
  for (auto& l : rig.locks) fibers += l.rest.fiberCount;
  logInfo("built character '{}' in {:.2f}s: {} parts, {} fibers", asset.name, sw.seconds(), rig.meshes.size(), fibers);
  return rig;
}

namespace {
struct DualQuat {
  quat r{1, 0, 0, 0}, d{0, 0, 0, 0};
};
DualQuat toDualQuat(const mat4& m) {
  DualQuat q;
  q.r = glm::normalize(glm::quat_cast(mat3(m)));
  vec3 t(m[3]);
  q.d = 0.5f * (quat(0, t.x, t.y, t.z) * q.r);
  return q;
}
}  // namespace

PosedCharacter poseCharacter(const CharacterRig& rig, const std::vector<mat4>& skin, const std::vector<float>& morphWeights,
                             bool dualQuaternion) {
  PosedCharacter out;
  std::vector<DualQuat> dqs;
  if (dualQuaternion)
    for (auto& m : skin) dqs.push_back(toDualQuat(m));
  for (size_t mi = 0; mi < rig.meshes.size(); ++mi) {
    const SkinnedMesh& sm = rig.meshes[mi];
    // Rest shape plus active morph targets.
    std::vector<vec3> pos = sm.rest.positions, nrm = sm.rest.normals;
    for (size_t t = 0; t < rig.morphs.size() && t < morphWeights.size(); ++t) {
      const MorphTarget& mt = rig.morphs[t];
      float w = morphWeights[t];
      if (mt.mesh != int(mi) || std::abs(w) < 1e-4f) continue;
      for (size_t k = 0; k < mt.vertices.size(); ++k) {
        pos[mt.vertices[k]] += w * mt.dpos[k];
        nrm[mt.vertices[k]] += w * mt.dnrm[k];
      }
    }
    auto m = std::make_shared<Mesh>();
    m->indices = sm.rest.indices;
    m->pref = sm.rest.positions;
    size_t n = pos.size();
    m->positions.resize(n);
    m->normals.resize(n);
    parallelFor(n, [&](size_t v) {
      vec3 nn;
      if (dualQuaternion) {
        DualQuat b0 = dqs[size_t(sm.joints[v][0])], acc;
        acc.r = quat(0, 0, 0, 0);
        for (int k = 0; k < 4; ++k) {
          float w = sm.weights[v][k];
          if (w <= 0) continue;
          DualQuat q = dqs[size_t(sm.joints[v][k])];
          if (glm::dot(q.r, b0.r) < 0) w = -w;
          acc.r = acc.r + w * q.r;
          acc.d = acc.d + w * q.d;
        }
        float len = glm::length(acc.r);
        quat r = acc.r / len, d = acc.d / len;
        quat t = 2.0f * (d * glm::conjugate(r));
        m->positions[v] = r * pos[v] + vec3(t.x, t.y, t.z);
        nn = r * nrm[v];
      } else {
        mat4 blended(0.0f);
        for (int k = 0; k < 4; ++k) {
          float w = sm.weights[v][k];
          if (w > 0) blended += w * skin[size_t(sm.joints[v][k])];
        }
        m->positions[v] = vec3(blended * vec4(pos[v], 1.0f));
        nn = mat3(blended) * nrm[v];
      }
      float len = glm::length(nn);
      m->normals[v] = len > 0 ? nn / len : sm.rest.normals[v];
    }, 2048);
    out.meshes.push_back(std::move(m));
  }
  for (const auto& bf : rig.fuzz) out.fuzz.push_back(deformSurfaceFibers(bf.fibers, *out.meshes[size_t(bf.mesh)]));
  for (const auto& bl : rig.locks) {
    out.locks.push_back(transformFibers(bl.rest, skin[size_t(bl.bone)]));
    out.lockCores.push_back(transformFibers(bl.cores, skin[size_t(bl.bone)]));
  }
  return out;
}

void smoothSkinWeights(const Mesh& mesh, int boneCount, int iterations, std::vector<glm::ivec4>& joints,
                       std::vector<vec4>& weights) {
  size_t n = mesh.positions.size(), nb = size_t(std::max(1, boneCount));
  std::vector<std::vector<uint32_t>> adj(n);
  for (size_t t = 0; t < mesh.triangleCount(); ++t)
    for (int k = 0; k < 3; ++k) {
      uint32_t a = mesh.indices[3 * t + size_t(k)], b = mesh.indices[3 * t + size_t((k + 1) % 3)];
      adj[a].push_back(b);
      adj[b].push_back(a);
    }
  std::vector<float> dense(n * nb, 0.0f), next(n * nb);
  for (size_t v = 0; v < n; ++v)
    for (int k = 0; k < 4; ++k) dense[v * nb + size_t(joints[v][k])] += weights[v][k];
  for (int it = 0; it < iterations; ++it) {
    parallelFor(n, [&](size_t v) {
      for (size_t b = 0; b < nb; ++b) {
        float sum = 0;
        for (uint32_t u : adj[v]) sum += dense[size_t(u) * nb + b];
        float avg = adj[v].empty() ? dense[v * nb + b] : sum / float(adj[v].size());
        next[v * nb + b] = 0.5f * dense[v * nb + b] + 0.5f * avg;
      }
    }, 2048);
    dense.swap(next);
  }
  parallelFor(n, [&](size_t v) {
    std::array<std::pair<float, int>, 4> best{};
    for (size_t b = 0; b < nb; ++b) {
      float w = dense[v * nb + b];
      if (w > best[3].first) {
        best[3] = {w, int(b)};
        std::sort(best.begin(), best.end(), [](auto& x, auto& y) { return x.first > y.first; });
      }
    }
    float sum = best[0].first + best[1].first + best[2].first + best[3].first;
    for (int k = 0; k < 4; ++k) {
      joints[v][k] = best[size_t(k)].second;
      weights[v][k] = sum > 0 ? best[size_t(k)].first / sum : (k == 0 ? 1.0f : 0.0f);
    }
  }, 2048);
}

namespace {
void applyPrimFields(SdfPrim& p, const Json& o) {
  p.center = readVec3(o, "center", p.center);
  p.radii = readVec3(o, (p.type == PrimType::RoundBox || p.type == PrimType::Disc) ? "halfSize" : "radii", p.radii);
  if (o.contains("rotationDeg")) p.rotation = eulerDegreesToQuat(readVec3(o, "rotationDeg", vec3(0)));
  p.a = readVec3(o, "a", p.a);
  p.b = readVec3(o, "b", p.b);
  p.r1 = readFloat(o, "r1", readFloat(o, "r", p.r1));
  p.r2 = readFloat(o, "r2", p.type == PrimType::Capsule ? p.r1 : p.r2);
  p.blend = readFloat(o, "blend", p.blend);
  p.rounding = readFloat(o, "rounding", p.rounding);
  p.subtract = readBool(o, "subtract", p.subtract);
}
}  // namespace

Result<SdfPart> applyExpression(const SdfPart& part, const Expression& e) {
  SdfPart out = part;
  for (const Json& o : e.set) {
    std::string name = readString(o, "prim");
    auto it = std::find_if(out.prims.begin(), out.prims.end(), [&](auto& p) { return p.name == name; });
    if (it == out.prims.end()) return fail(std::format("unknown primitive '{}'", name));
    applyPrimFields(*it, o);
    std::string mirror = mirrorName(name);
    if (mirror != name) {
      auto mit = std::find_if(out.prims.begin(), out.prims.end(), [&](auto& p) { return p.name == mirror; });
      if (mit != out.prims.end()) {
        SdfPrim src = *it;
        src.mirrorX = true;
        auto pair = expandMirrors({src});
        SdfPrim m = pair.back();
        m.name = mit->name;
        m.bone = mit->bone;
        m.boneIndex = mit->boneIndex;
        *mit = m;
      }
    }
  }
  for (const Json& a : e.add) {
    auto p = primFromJson(a);
    if (!p) return std::unexpected(p.error());
    for (auto& q : expandMirrors({*p})) out.prims.push_back(q);
  }
  return out;
}

}  // namespace plush
