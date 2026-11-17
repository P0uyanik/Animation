#include "scene/face_layer.h"

#include <algorithm>
#include <cmath>
#include <format>
#include <set>

namespace plush {

namespace {
// Built-in channel names (the motions the layer itself produces).
const char* const kBrowUp = "browUp";
const char* const kEyeWide = "eyeWide";
const char* const kJaw = "jawOpen";
const char* const kMouthUp = "mouthUp";
const char* const kMouthDown = "mouthDown";

// Seed salts: independent random streams of one character.
constexpr uint32_t kDoubleSalt = 0xB11F0001u, kGapSalt = 0x06A90002u, kShiftSalt = 0x051A0003u, kSacSalt = 0x5ACC0004u,
                   kHoldSalt = 0x701D0005u, kTargetSalt = 0x00C30006u, kMicroSalt = 0x3C1E0007u;

float smooth(double x) { return smoothstep01(float(x)); }

// Blink closure at u seconds after the blink starts (the life layer's blink shape, blinkAmount).
float blinkShape(double u, double close, double hold, double open) {
  if (u < 0) return 0.0f;
  if (u < close) return smooth(u / close);
  if (u < close + hold) return 1.0f;
  if (u < close + hold + open) return 1.0f - smooth((u - close - hold) / open);
  return 0.0f;
}

Result<std::optional<float>> optNumber(const Json& j, const char* k) {
  auto it = j.find(k);
  if (it == j.end() || it->is_null()) return std::optional<float>();
  if (!it->is_number()) return fail(std::format("faceMotion: '{}' must be a number", k));
  return std::optional<float>(it->get<float>());
}
}  // namespace

double FaceEnvelope::at(double f) const {
  if (f < start || f > end) return 0;
  auto ramp = [this](double x) { return linear ? std::clamp(x, 0.0, 1.0) : double(smooth(x)); };
  const double in = blendIn > 0 ? ramp((f - start) / blendIn) : 1.0;
  const double out = blendOut > 0 && end < 1e29 ? ramp((end - f) / blendOut) : 1.0;
  return weight * in * out;
}

Result<FaceMotion> faceMotionFromJson(const Json& j) {
  FaceMotion m;
  if (j.is_null()) return m;
  if (!j.is_object()) return fail("faceMotion must be an object");
  struct F {
    const char* key;
    std::optional<float> FaceMotion::*member;
  };
  for (const F& f : {F{"blinkRate", &FaceMotion::blinkRate}, F{"doubleBlink", &FaceMotion::doubleBlink},
                     F{"blinkDuration", &FaceMotion::blinkDuration}, F{"gazeShiftBlink", &FaceMotion::gazeShiftBlink},
                     F{"saccadeRate", &FaceMotion::saccadeRate}, F{"saccadeDeg", &FaceMotion::saccadeDeg},
                     F{"longHold", &FaceMotion::longHold}, F{"attention", &FaceMotion::attention},
                     F{"breath", &FaceMotion::breath}, F{"micro", &FaceMotion::micro}}) {
    auto v = optNumber(j, f.key);
    if (!v) return std::unexpected(v.error());
    m.*(f.member) = *v;
  }
  if (auto b = j.find("gazeBiasDeg"); b != j.end() && !b->is_null()) {
    if (!b->is_array() || b->size() != 2 || !(*b)[0].is_number() || !(*b)[1].is_number())
      return fail("faceMotion: 'gazeBiasDeg' must be [yaw, pitch]");
    m.gazeBiasDeg = vec2((*b)[0].get<float>(), (*b)[1].get<float>());
  }
  if (auto c = j.find("channels"); c != j.end() && !c->is_null()) {
    if (!c->is_object()) return fail("faceMotion: 'channels' must be an object of channel -> weight");
    for (auto& [k, v] : c->items()) {
      if (v.is_null()) continue;  // removed by a variant
      if (!v.is_number()) return fail(std::format("faceMotion: channel '{}' weight must be a number", k));
      m.channels[k] = v.get<float>();
    }
  }
  return m;
}

FaceLibrary defaultFaceLibrary() {
  FaceLibrary lib;
  // Engine expression names only; morph-level candidates live in content/emotions/face_motion.json.
  lib.channels[kBrowUp] = {{"browUp"}};
  lib.channels["browDown"] = {{"browDown"}};
  lib.channels[kEyeWide] = {{"eyeWide"}};
  lib.channels[kJaw] = {{"jawOpen"}};
  lib.channels[kMouthUp] = {{"mouthSmile"}};
  lib.channels[kMouthDown] = {{"mouthFrown"}};
  return lib;
}

Result<FaceLibrary> faceLibraryFromJson(const Json& j) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.face_motion") return fail("not a plush.face_motion file");
  if (j.value("version", 0) != 1) return fail(std::format("face_motion: unsupported version {}", j.value("version", 0)));
  FaceLibrary lib = defaultFaceLibrary();
  if (auto c = j.find("channels"); c != j.end()) {
    if (!c->is_object()) return fail("face_motion: 'channels' must be an object");
    for (auto& [name, cands] : c->items()) {
      if (!cands.is_array()) return fail(std::format("face_motion: channel '{}' must be a list of candidates", name));
      std::vector<std::vector<std::string>> list;
      for (auto& cand : cands) {
        std::vector<std::string> controls;
        if (cand.is_string()) controls.push_back(cand.get<std::string>());
        else if (cand.is_array())
          for (auto& x : cand) {
            if (!x.is_string()) return fail(std::format("face_motion: channel '{}': control names must be strings", name));
            controls.push_back(x.get<std::string>());
          }
        else return fail(std::format("face_motion: channel '{}': a candidate is a name or a list of names", name));
        if (!controls.empty()) list.push_back(std::move(controls));
      }
      lib.channels[name] = std::move(list);
    }
  }
  if (auto nj = j.find("neutral"); nj != j.end()) {
    if (!nj->is_object()) return fail("face_motion: 'neutral' must be an object");
    FaceNeutral& n = lib.neutral;
    struct F {
      const char* key;
      float FaceNeutral::*member;
    };
    for (const F& f : {F{"blinkRate", &FaceNeutral::blinkRate}, F{"doubleBlink", &FaceNeutral::doubleBlink},
                       F{"blinkDuration", &FaceNeutral::blinkDuration}, F{"gazeShiftBlink", &FaceNeutral::gazeShiftBlink},
                       F{"saccadeInterval", &FaceNeutral::saccadeInterval}, F{"saccadeRate", &FaceNeutral::saccadeRate},
                       F{"saccadeDeg", &FaceNeutral::saccadeDeg}, F{"longHold", &FaceNeutral::longHold},
                       F{"lookAttention", &FaceNeutral::lookAttention}, F{"breath", &FaceNeutral::breath},
                       F{"micro", &FaceNeutral::micro}, F{"breathJaw", &FaceNeutral::breathJaw},
                       F{"microBrow", &FaceNeutral::microBrow}, F{"microMouth", &FaceNeutral::microMouth},
                       F{"attentionBrow", &FaceNeutral::attentionBrow}, F{"attentionWide", &FaceNeutral::attentionWide}}) {
      auto v = optNumber(*nj, f.key);
      if (!v) return std::unexpected(v.error());
      if (*v) n.*(f.member) = **v;
    }
    if (auto b = nj->find("gazeBiasDeg"); b != nj->end() && b->is_array() && b->size() == 2)
      n.gazeBiasDeg = vec2((*b)[0].get<float>(), (*b)[1].get<float>());
    if (n.saccadeInterval <= 0) return fail("face_motion: neutral saccadeInterval must be > 0");
  }
  return lib;
}

Result<std::shared_ptr<const FaceCurves>> faceCurvesFromClipJson(const Json& clip) {
  auto f = clip.find("face");
  if (f == clip.end() || f->is_null()) return std::shared_ptr<const FaceCurves>();
  auto tr = f->find("tracks");
  if (!f->is_object() || tr == f->end() || !tr->is_object()) return fail("clip 'face' must be {\"tracks\": {channel: [[frame, value], ...]}}");
  auto out = std::make_shared<FaceCurves>();
  for (auto& [name, keys] : tr->items()) {
    if (!keys.is_array()) return fail(std::format("clip face track '{}' must be a list of [frame, value]", name));
    Track t;
    for (auto& k : keys) {
      if (!k.is_array() || k.size() < 2 || !k[0].is_number() || !k[1].is_number())
        return fail(std::format("clip face track '{}': keys are [frame, value]", name));
      t.setKey({k[0].get<double>(), vec3(k[1].get<float>()), Interp::Smooth});
    }
    if (!t.keys.empty()) out->tracks[name] = std::move(t);
  }
  return std::shared_ptr<const FaceCurves>(out);
}

void FaceLayer::build(const FaceLibrary& lib, const std::function<std::string(const std::string&)>& resolve, FaceTimeline timeline,
                      const LifeParams& life, double fps, int frameStart, int frameEnd) {
  n_ = lib.neutral;
  tl_ = std::move(timeline);
  life_ = life;
  fps_ = std::max(1.0, fps);
  // Channels: every library channel plus any other name the timeline uses (resolved directly as a control).
  std::set<std::string> names;
  for (const auto& [k, v] : lib.channels) names.insert(k);
  for (const auto& e : tl_.emotions)
    for (const auto& [k, v] : e.motion.channels) names.insert(k);
  for (const auto& c : tl_.curves)
    if (c.curves)
      for (const auto& [k, v] : c.curves->tracks) names.insert(k);
  channels_.clear();
  for (const std::string& name : names) {
    std::vector<std::string> morphs;
    auto it = lib.channels.find(name);
    if (it == lib.channels.end()) {
      if (std::string m = resolve(name); !m.empty()) morphs.push_back(m);
    } else {
      for (const auto& cand : it->second) {  // the first candidate the character has (all of it that resolves)
        for (const auto& control : cand)
          if (std::string m = resolve(control); !m.empty() && std::find(morphs.begin(), morphs.end(), m) == morphs.end())
            morphs.push_back(m);
        if (!morphs.empty()) break;
      }
    }
    channels_[name] = std::move(morphs);
  }
  // Emotion onsets with "attention" raise the brows.
  for (const auto& e : tl_.emotions)
    if (e.motion.attention && *e.motion.attention > 0) tl_.attention.push_back({e.env.start, float(*e.motion.attention * e.env.weight)});
  // Warped clocks (blinks and eye darts run faster or slower with the emotion): seconds of warped time per frame.
  frameStart_ = frameStart;
  f0_ = std::min(frameStart, 0) - 2;
  const int f1 = std::max(frameEnd, frameStart) + 2;
  blinkClock_.assign(size_t(f1 - f0_ + 1), 0.0);
  saccadeClock_.assign(blinkClock_.size(), 0.0);
  Params prev = params(f0_);
  blinkClock_[0] = f0_ / fps_ * std::max(0.05f, prev.blinkRate);
  saccadeClock_[0] = f0_ / fps_ * std::max(0.05f, prev.saccadeRate);
  for (size_t i = 1; i < blinkClock_.size(); ++i) {
    Params p = params(f0_ + int(i));
    blinkClock_[i] = blinkClock_[i - 1] + 0.5 * (std::max(0.05f, prev.blinkRate) + std::max(0.05f, p.blinkRate)) / fps_;
    saccadeClock_[i] = saccadeClock_[i - 1] + 0.5 * (std::max(0.05f, prev.saccadeRate) + std::max(0.05f, p.saccadeRate)) / fps_;
    prev = p;
  }
  built_ = true;
}

FaceLayer::Params FaceLayer::params(double frame) const {
  Params p{n_.blinkRate, n_.doubleBlink, n_.blinkDuration, n_.gazeShiftBlink, n_.saccadeRate, n_.saccadeDeg, n_.longHold,
           0.0f, n_.breath, n_.micro, n_.gazeBiasDeg};
  for (const auto& e : tl_.emotions) {
    const float w = float(e.env.at(frame));
    if (w <= 0) continue;
    const FaceMotion& m = e.motion;
    auto mix = [&](float& v, const std::optional<float>& o, float neutral) {
      if (o) v += w * (*o - neutral);
    };
    mix(p.blinkRate, m.blinkRate, n_.blinkRate);
    mix(p.doubleBlink, m.doubleBlink, n_.doubleBlink);
    mix(p.blinkDuration, m.blinkDuration, n_.blinkDuration);
    mix(p.gazeShiftBlink, m.gazeShiftBlink, n_.gazeShiftBlink);
    mix(p.saccadeRate, m.saccadeRate, n_.saccadeRate);
    mix(p.saccadeDeg, m.saccadeDeg, n_.saccadeDeg);
    mix(p.longHold, m.longHold, n_.longHold);
    mix(p.breath, m.breath, n_.breath);
    mix(p.micro, m.micro, n_.micro);
    if (m.gazeBiasDeg) p.bias += w * (*m.gazeBiasDeg - n_.gazeBiasDeg);
  }
  p.blinkDuration = std::max(0.3f, p.blinkDuration);
  return p;
}

double FaceLayer::clock(const std::vector<double>& table, double frame) const {
  if (table.empty()) return frame / fps_;
  const double x = frame - f0_;
  if (x <= 0) return table.front() + x / fps_ * (table.size() > 1 ? (table[1] - table[0]) * fps_ : 1.0);
  const size_t last = table.size() - 1;
  if (x >= double(last)) return table[last] + (x - double(last)) / fps_ * (last > 0 ? (table[last] - table[last - 1]) * fps_ : 1.0);
  const size_t i = size_t(x);
  return table[i] + (table[i + 1] - table[i]) * (x - double(i));
}

double FaceLayer::clockInverse(const std::vector<double>& table, double tau) const {
  if (table.size() < 2) return tau * fps_;
  const size_t last = table.size() - 1;
  if (tau <= table.front()) return f0_ + (tau - table.front()) / ((table[1] - table[0]));
  if (tau >= table[last]) return f0_ + double(last) + (tau - table[last]) / (table[last] - table[last - 1]);
  const size_t i = size_t(std::upper_bound(table.begin(), table.end(), tau) - table.begin()) - 1;
  return f0_ + double(i) + (tau - table[i]) / std::max(1e-12, table[i + 1] - table[i]);
}

float FaceLayer::blink(double frame) const {
  if (!built_ || life_.blinkInterval <= 0) return 0.0f;
  const double t = frame / fps_, tau = clock(blinkClock_, frame), interval = life_.blinkInterval;
  const uint32_t seed = life_.seed;
  auto shapeAt = [&](double startFrame, float scale, double now) {
    const float d = params(startFrame).blinkDuration * scale;
    return blinkShape(now - startFrame / fps_, std::max(1e-3f, life_.blinkClose) * d, std::max(0.0f, life_.blinkHold) * d,
                      std::max(1e-3f, life_.blinkOpen) * d);
  };
  float amount = 0;
  // Rhythm blinks: the life layer's jittered schedule (blinkAmount), on the emotion-warped clock.
  double start = 0;
  for (uint32_t k = 0;; ++k) {
    start += interval * (0.55 + 0.9 * lifeHash01(seed, k));
    if (start > tau) break;
    if (start < tau - 3.0) continue;  // long over (a blink lasts well under a second)
    const double sf = clockInverse(blinkClock_, start);
    amount = std::max(amount, shapeAt(sf, 1.0f, t));
    const Params p = params(sf);
    if (lifeHash01(seed ^ kDoubleSalt, k) < p.doubleBlink) {  // a quick second blink right after the first
      const float d = p.blinkDuration;
      const double len = (std::max(1e-3f, life_.blinkClose) + std::max(0.0f, life_.blinkHold) + std::max(1e-3f, life_.blinkOpen)) * d;
      const double gap = 0.05 + 0.07 * lifeHash01(seed ^ kGapSalt, k);
      amount = std::max(amount, shapeAt(sf + (len + gap) * fps_, 0.85f, t));
    }
  }
  // Gaze-shift blinks: a new look often comes with a blink.
  for (size_t j = 0; j < tl_.lookStarts.size(); ++j) {
    const double g = tl_.lookStarts[j];
    if (g > frame || frame - g > fps_ || g <= frameStart_ + 2) continue;  // a look the shot opens with is no gaze shift
    if (lifeHash01(seed ^ kShiftSalt, uint32_t(j)) < params(g).gazeShiftBlink) amount = std::max(amount, shapeAt(g + 1, 1.0f, t));
  }
  return amount;
}

vec2 FaceLayer::saccade(double frame) const {
  const double tau = clock(saccadeClock_, frame);
  const uint32_t seed = life_.seed;
  vec2 prev(0), cur(0);
  double curFrame = -1e30, s = 0;
  for (uint32_t j = 0; j < 100000; ++j) {
    const double hold = n_.saccadeInterval * (0.4 + 1.2 * lifeHash01(seed ^ kSacSalt, j));
    const double sf0 = clockInverse(saccadeClock_, s);  // the previous dart's frame (for this hold's parameters)
    s += hold * (lifeHash01(seed ^ kHoldSalt, j) < params(sf0).longHold ? 2.5 : 1.0);
    if (s > tau) break;
    const double sf = clockInverse(saccadeClock_, s);
    const float a = std::max(0.0f, params(sf).saccadeDeg);
    vec2 target;
    const float h = lifeHash01(seed ^ kTargetSalt, 3 * j), hx = lifeHash01(seed ^ kTargetSalt, 3 * j + 1),
                hy = lifeHash01(seed ^ kTargetSalt, 3 * j + 2);
    if (h < 0.35f) target = vec2(0.2f * a * (2 * hx - 1), 0.2f * a * (2 * hy - 1));  // back near the fixation point
    else target = vec2(a * (2 * hx - 1), 0.55f * a * (2 * hy - 1));
    prev = cur;
    cur = target;
    curFrame = sf;
  }
  if (curFrame < -1e29) return vec2(0);
  // A dart takes ~45 ms plus 2.5 ms per degree (main sequence), then the eyes hold.
  const double move = 0.045 + 0.0025 * glm::length(cur - prev);
  return glm::mix(prev, cur, smooth((frame - curFrame) / fps_ / move));
}

void FaceLayer::addChannel(std::map<std::string, float>& out, const std::string& channel, float w) const {
  if (w == 0) return;
  auto it = channels_.find(channel);
  if (it == channels_.end()) return;
  for (const auto& m : it->second) out[m] += w;
}

FaceState FaceLayer::evaluate(double frame) const {
  FaceState s;
  if (!built_) return s;
  const double t = frame / fps_;
  const Params p = params(frame);
  s.blink = blink(frame);
  s.eyeOffsetDeg = saccade(frame) + p.bias;
  std::map<std::string, float> ch;
  for (const auto& e : tl_.emotions) {
    const float w = float(e.env.at(frame));
    if (w > 0)
      for (const auto& [k, v] : e.motion.channels) ch[k] += w * v;
  }
  // Attention: brows lift and eyes open a little (rise 0.25 s, hold 0.35 s, settle 0.9 s).
  float att = 0;
  for (const auto& a : tl_.attention) {
    const double u = t - a.frame / fps_;
    if (u < 0 || u > 1.5) continue;
    const float shape = u < 0.25 ? smooth(u / 0.25) : u < 0.6 ? 1.0f : 1.0f - smooth((u - 0.6) / 0.9);
    att = std::max(att, a.amount * shape);
  }
  ch[kBrowUp] += n_.attentionBrow * att;
  ch[kEyeWide] += n_.attentionWide * att;
  // Breathing: the jaw drops a hair at the top of each inhale.
  ch[kJaw] += n_.breathJaw * p.breath * 0.5f * (1.0f + breathSignal(t, life_.seed));
  // Micro motion: slow, incommensurate drifts of the mouth corners and brows (never frozen, never twitchy).
  const uint32_t seed = life_.seed;
  auto wave = [&](uint32_t k, double period) {
    return float(std::sin(kTwoPi * t / period + 6.283 * lifeHash01(seed ^ kMicroSalt, k)));
  };
  const float mouth = 0.6f * wave(0, 3.7) + 0.4f * wave(1, 6.1), brow = 0.55f * wave(2, 4.3) + 0.45f * wave(3, 7.9);
  if (mouth > 0) ch[kMouthUp] += n_.microMouth * p.micro * mouth;
  else ch[kMouthDown] -= n_.microMouth * p.micro * mouth;
  ch[kBrowUp] += n_.microBrow * p.micro * 0.5f * (1.0f + brow);
  // Clip face curves (a yawn's jaw, a shrug's brows ...), weighted by the clip layer's envelope.
  for (const auto& c : tl_.curves) {
    const float w = float(c.env.at(frame));
    if (w <= 0 || !c.curves) continue;
    const double cf = std::max(0.0, frame - c.start) * c.speed * c.clipFps / fps_;
    for (const auto& [k, tr] : c.curves->tracks) ch[k] += w * tr.evaluate(cf).x;
  }
  for (const auto& [k, v] : ch) addChannel(s.controls, k, v);
  return s;
}

}  // namespace plush
