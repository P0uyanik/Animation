#include "scene/emotion.h"

#include <algorithm>
#include <cmath>
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
  if (auto fm = j.find("faceMotion"); fm != j.end() && !fm->is_null()) {
    auto m = faceMotionFromJson(*fm);
    if (!m) return fail(std::format("emotion '{}': {}", e.name, m.error().message));
    e.faceMotion = *m;
    e.hasFaceMotion = true;
  }
  if (auto b = j.find("blend"); b != j.end() && b->is_object()) {
    e.rise = seconds(*b, "rise", -1);
    e.decay = seconds(*b, "decay", -1);
  }
  if (auto a = j.find("affect"); a != j.end() && a->is_object()) {
    e.pleasantness = std::clamp(float(seconds(*a, "pleasantness", 0)), -1.f, 1.f);
    e.energy = std::clamp(float(seconds(*a, "energy", 0)), -1.f, 1.f);
  }
  if (e.onset < 0 || e.hold < 0 || e.release < 0) return fail(std::format("emotion '{}': negative timing", e.name));
  return e;
}

// ---- Blending ----

float EmotionChannel::raw(double t, float* v) const {
  // The last segment that started at or before t (segments are in time order).
  auto it = std::upper_bound(segs_.begin(), segs_.end(), t, [](double x, const Seg& s) { return x < s.t0; });
  if (it == segs_.begin()) {
    if (v) *v = 0;
    return initial_;
  }
  const Seg& s = *(it - 1);
  if (s.T <= 0 || t >= s.t0 + s.T) {
    if (v) *v = 0;
    return s.x1;
  }
  const double u = (t - s.t0) / s.T, u2 = u * u, u3 = u2 * u;
  const double h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2;
  if (v) {
    const double d00 = 6 * u2 - 6 * u, d10 = 3 * u2 - 4 * u + 1, d01 = -6 * u2 + 6 * u;
    *v = float((d00 * s.x0 + d01 * s.x1) / s.T + d10 * s.v0);
  }
  return float(h00 * s.x0 + h10 * s.T * s.v0 + h01 * s.x1);
}

float EmotionChannel::value(double t) const { return std::clamp(raw(t, nullptr), lo_, hi_); }

float EmotionChannel::velocity(double t) const {
  float v = 0;
  const float x = raw(t, &v);
  return (x < lo_ && v < 0) || (x > hi_ && v > 0) ? 0.f : v;
}

float EmotionChannel::target(double t) const {
  auto it = std::upper_bound(segs_.begin(), segs_.end(), t, [](double x, const Seg& s) { return x < s.t0; });
  return it == segs_.begin() ? initial_ : (it - 1)->x1;
}

void EmotionChannel::retarget(double t, float target, double rise, double decay) {
  target = std::clamp(target, lo_, hi_);
  float v = 0;
  float x = raw(t, &v);
  if (x < lo_ || x > hi_) {  // clamped (an overshoot): continue from the bound at rest
    x = std::clamp(x, lo_, hi_);
    v = 0;
  }
  while (!segs_.empty() && segs_.back().t0 >= t) segs_.pop_back();
  if (!segs_.empty() && segs_.back().x1 == target && v == 0 && x == target) return;  // already there
  const double T = std::max(0.0, target >= x ? rise : decay);
  // The move keeps the incoming velocity (C1): a move against the motion in progress first carries on a little, then
  // turns; values stay clamped to the channel's range.
  segs_.push_back({t, T, x, T > 0 ? v : 0.f, target});
}

void EmotionBlender::retargetEmotion(double t, const std::string& name, float weight, double rise, double decay) {
  auto [it, inserted] = weights_.try_emplace(name);
  if (inserted) order_.push_back(name);
  it->second.retarget(t, weight, rise, decay);
}

void EmotionBlender::retargetAffect(double t, float pleasantness, float energy, double rise, double decay) {
  p_.retarget(t, pleasantness, rise, decay);
  e_.retarget(t, energy, rise, decay);
}

void EmotionBlender::retarget(double t, const EmotionState& target, double rise, double decay) {
  for (const auto& n : order_) {
    const bool named = std::any_of(target.weights.begin(), target.weights.end(), [&](const auto& w) { return w.first == n; });
    if (!named) weights_.at(n).retarget(t, 0.f, rise, decay);
  }
  for (const auto& [n, w] : target.weights) retargetEmotion(t, n, w, rise, decay);
  retargetAffect(t, target.pleasantness, target.energy, rise, decay);
}

EmotionState EmotionBlender::evaluate(double t) const {
  EmotionState s;
  for (const auto& n : order_) s.weights.push_back({n, weights_.at(n).value(t)});
  s.pleasantness = p_.value(t);
  s.energy = e_.value(t);
  return s;
}

float EmotionBlender::weight(const std::string& name, double t) const {
  auto it = weights_.find(name);
  return it == weights_.end() ? 0.f : it->second.value(t);
}

const EmotionChannel* EmotionBlender::channel(const std::string& name) const {
  auto it = weights_.find(name);
  return it == weights_.end() ? nullptr : &it->second;
}

std::pair<float, float> impliedAffect(const std::vector<std::pair<std::string, float>>& weights,
                                      const std::map<std::string, std::pair<float, float>>& affect) {
  double sum = 0, p = 0, e = 0;
  for (const auto& [n, w] : weights) {
    auto it = affect.find(n);
    sum += w;
    if (it == affect.end()) continue;
    p += w * it->second.first;
    e += w * it->second.second;
  }
  const double k = 1.0 / std::max(1.0, sum);
  return {std::clamp(float(p * k), -1.f, 1.f), std::clamp(float(e * k), -1.f, 1.f)};
}

Result<PersonalityModulation> modulationFromJson(const Json& j) {
  PersonalityModulation m;
  if (j.is_null()) return m;
  if (!j.is_object()) return fail("modulation must be an object");
  m.intensityScale = float(seconds(j, "intensityScale", 1));
  m.tempoScale = float(seconds(j, "tempoScale", 1));
  m.holdScale = float(seconds(j, "holdScale", 1));
  m.gazeShift = std::clamp(float(seconds(j, "gazeShift", 0)), 0.f, 1.f);
  for (const auto& g : j.value("preferredGestures", Json::array()))
    if (g.is_string()) m.preferredGestures.push_back(g.get<std::string>());
  if (!(m.intensityScale >= 0) || !(m.tempoScale > 0) || !(m.holdScale >= 0))
    return fail("modulation: intensityScale >= 0, tempoScale > 0 and holdScale >= 0");
  return m;
}

EmotionTiming modulatedTiming(double rise, double hold, double decay, float intensity, const PersonalityModulation& m) {
  EmotionTiming t;
  t.rise = rise * m.tempoScale;
  t.decay = decay * m.tempoScale;
  t.hold = hold * m.tempoScale * m.holdScale;
  t.intensity = std::clamp(intensity * m.intensityScale, 0.f, 1.f);
  return t;
}

double emotionTempo(float energy, const PersonalityModulation& m, float energyTempo) {
  return std::max(0.05, (1.0 + double(energyTempo) * std::clamp(energy, -1.f, 1.f)) / std::max(1e-3f, m.tempoScale));
}

double SampledLayerCurves::clockAt(double f) const {
  if (clock.empty()) return 0;
  const double x = std::clamp(f - start, 0.0, double(clock.size() - 1));
  const size_t k = std::min(size_t(x), clock.size() - 1);
  if (k + 1 >= clock.size()) return clock[k];
  const double u = x - double(k), p0 = clock[k > 0 ? k - 1 : k], p1 = clock[k], p2 = clock[k + 1],
               p3 = clock[k + 2 < clock.size() ? k + 2 : k + 1];  // Catmull-Rom (C1), as sampledCurve
  return 0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u * u * u);
}

std::vector<float> overrideWeights(const std::vector<float>& w) {
  double S = 0;
  for (float x : w) S += std::max(0.f, x);
  const double k = S > 1 ? 1.0 / S : 1.0;
  S = std::min(S, 1.0);
  std::vector<float> out(w.size(), 0.f);
  double acc = 1.0 - S;  // the base's share
  for (size_t i = 0; i < w.size(); ++i) {
    const double wi = std::max(0.f, w[i]) * k;
    acc += wi;
    out[i] = acc > 1e-9 ? float(wi / acc) : 0.f;
  }
  return out;
}

}  // namespace plush
