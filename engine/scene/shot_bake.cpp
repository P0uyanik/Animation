#include "scene/shot_bake.h"

#include <set>

namespace plush {
namespace {
Json v3(vec3 v) { return Json::array({v.x, v.y, v.z}); }
}  // namespace

Json bakeShot(const SceneEvaluator& evaluator, int frameA, int frameB) {
  const Scene& scene = evaluator.scene();
  Json out;
  out["format"] = "plush.shot_bake";
  out["version"] = 1;
  out["scene"] = scene.name;
  out["scene_path"] = std::filesystem::absolute(scene.path).string();
  out["fps"] = Json::array({scene.rate.num, scene.rate.den});
  out["frames"] = Json::array({frameA, frameB});
  out["render"] = {{"width", scene.render.width}, {"height", scene.render.height}, {"exposureEV", scene.render.exposureEV}};
  out["coordinates"] = "engine axes: metres, +Y up, characters face +Z; matrices are column-major 4x4 world transforms of "
                       "the skinning frames (global bone transform times translate(-rest head))";
  Json lights = Json::array();
  for (const Light& l : scene.lights) {
    Json j{{"color", v3(l.color)}, {"intensity", l.intensity}};
    if (l.type == Light::Type::Sun) j.update({{"type", "sun"}, {"direction", v3(l.direction)}, {"angleDeg", l.angleDeg}});
    if (l.type == Light::Type::Rect) j.update({{"type", "rect"}, {"corner", v3(l.corner)}, {"edgeU", v3(l.edgeU)}, {"edgeV", v3(l.edgeV)}});
    if (l.type == Light::Type::Sky) j["type"] = "sky";
    lights.push_back(j);
  }
  out["lights"] = lights;
  Json objects = Json::array(), unsupported = Json::array();
  std::vector<Material> mats0;  // material colours (static in bake v1)
  if (!scene.objects.empty()) mats0 = evaluator.evaluate(frameA)->materials;
  for (const ObjectDesc& o : scene.objects) {
    if (o.kind == ObjectDesc::Kind::Box) {
      Json j{{"name", o.name}, {"kind", "box"}, {"min", v3(o.boxMin)}, {"max", v3(o.boxMax)}, {"material", o.material}};
      int mi = evaluator.materialIndex(o.material);
      if (mi >= 0 && size_t(mi) < mats0.size()) j["baseColor"] = v3(mats0[size_t(mi)].baseColor);
      objects.push_back(j);
    } else {
      unsupported.push_back(o.name);
    }
  }
  out["objects"] = objects;
  out["objects_not_baked"] = unsupported;  // SDF props, paper boats, water: not part of bake v1
  Json chars = Json::array();
  std::vector<std::vector<std::string>> morphNames(evaluator.characters().size());
  for (size_t c = 0; c < evaluator.characters().size(); ++c) {
    const auto& ci = evaluator.characters()[c];
    const auto& cd = scene.characters[c];
    Json j{{"name", cd.name}, {"package", std::filesystem::absolute(scene.path.parent_path() / cd.asset).lexically_normal().string()},
           {"supported", ci.imported}};
    if (ci.imported) {
      Json bones = Json::array();
      for (const auto& b : ci.asset.skeleton.bones) bones.push_back(b.name);
      j["bones"] = bones;
      std::set<std::string> seen;
      for (const auto& mt : ci.rig.morphs)
        if (seen.insert(mt.name).second) morphNames[c].push_back(mt.name);
      j["morphs"] = morphNames[c];
    }
    chars.push_back(j);
  }
  out["characters"] = chars;
  Json frames = Json::array();
  for (int f = frameA; f <= frameB; ++f) {
    const Camera cam = evaluator.cameraAt(f);
    Json fj{{"frame", f},
            {"camera", {{"position", v3(cam.position)}, {"target", v3(cam.target)}, {"up", v3(cam.up)}, {"focalMm", cam.focalMm},
                        {"sensorWidthMm", cam.sensorWidthMm}, {"fStop", cam.fStop}, {"focusDistance", cam.focusDistance}}}};
    Json cj = Json::object();
    for (size_t c = 0; c < evaluator.characters().size(); ++c) {
      const auto& ci = evaluator.characters()[c];
      if (!ci.imported) continue;
      auto g = evaluator.characterGlobals(c, f);
      Json mats = Json::array();
      for (size_t b = 0; b < g.size(); ++b) {
        const mat4 s = g[b] * glm::translate(mat4(1), -ci.asset.skeleton.bones[b].head);
        for (int k = 0; k < 16; ++k) mats.push_back(s[k / 4][k % 4]);
      }
      Json w = Json::array();
      for (const auto& m : morphNames[c]) w.push_back(evaluator.morphControlWeight(c, m, f));
      cj[scene.characters[c].name] = {{"skin", mats}, {"morphs", w}};
    }
    fj["characters"] = cj;
    frames.push_back(fj);
  }
  out["frame_data"] = frames;
  return out;
}

}  // namespace plush
