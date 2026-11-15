#include "scene/emotion.h"

#include <format>

namespace plush {

namespace {
Result<std::vector<std::pair<std::string, float>>> faceMix(const Json& j, const char* what) {
  std::vector<std::pair<std::string, float>> out;
  if (j.is_null()) return out;
  if (!j.is_object()) return fail(std::format("emotion: '{}' must be an object of expression name -> weight", what));
  for (auto& [k, v] : j.items()) {
    if (v.is_null()) continue;  // removed by a variant
    if (!v.is_number()) return fail(std::format("emotion: {} weight of '{}' must be a number", what, k));
    out.push_back({k, v.get<float>()});
  }
  return out;
}
double seconds(const Json& j, const char* k, double fallback) {
  auto it = j.find(k);
  return it != j.end() && it->is_number() ? it->get<double>() : fallback;
}
}  // namespace

Result<EmotionDef> emotionFromJson(const Json& file, const std::string& variant) {
  if (!file.is_object() || file.value("format", std::string()) != "plush.emotion") return fail("not a plush.emotion file");
  EmotionDef e;
  e.raw = file;
  e.version = file.value("version", 0);
  if (e.version != 1) return fail(std::format("emotion: unsupported version {}", e.version));
  Json j = file;
  if (!variant.empty()) {
    auto v = file.find("variants");
    if (v == file.end() || !v->is_object() || !v->contains(variant))
      return fail(std::format("emotion '{}': no variant '{}'", file.value("name", std::string()), variant));
    j.erase("variants");
    j.merge_patch((*v)[variant]);
  }
  e.name = j.value("name", std::string());
  e.variant = variant;
  auto face = faceMix(j.value("face", Json()), "face");
  if (!face) return std::unexpected(face.error());
  e.face = *face;
  if (auto b = j.find("body"); b != j.end() && b->is_object()) {
    e.bodyClip = b->value("clip", std::string());
    for (auto& m : b->value("mask", Json::array())) e.bodyMask.push_back(m.get<std::string>());
    if (b->contains("loop") && (*b)["loop"].is_boolean()) e.bodyLoop = (*b)["loop"].get<bool>() ? 1 : 0;
  }
  if (auto g = j.find("gesture"); g != j.end() && g->is_object() && !g->value("clip", std::string()).empty()) {
    e.hasGesture = true;
    e.gesture.clip = (*g)["clip"].get<std::string>();
    e.gesture.offset = seconds(*g, "offset", 0);
    e.gesture.blendIn = seconds(*g, "blendIn", 0.2);
    e.gesture.blendOut = seconds(*g, "blendOut", 0.2);
    e.gesture.mirror = g->value("mirror", false);
    auto gf = faceMix(g->value("face", Json()), "gesture face");
    if (!gf) return std::unexpected(gf.error());
    e.gesture.face = *gf;
  }
  if (auto t = j.find("timing"); t != j.end() && t->is_object()) {
    e.onset = seconds(*t, "onset", e.onset);
    e.hold = seconds(*t, "hold", e.hold);
    e.release = seconds(*t, "release", e.release);
    const std::string curve = t->value("curve", std::string("smooth"));
    if (curve != "smooth" && curve != "linear") return fail(std::format("emotion '{}': unknown curve '{}'", e.name, curve));
    e.linear = curve == "linear";
  }
  if (e.onset < 0 || e.hold < 0 || e.release < 0) return fail(std::format("emotion '{}': negative timing", e.name));
  return e;
}

}  // namespace plush
