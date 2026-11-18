// T-053 personality profile reader (anim/personality.h).
#include "anim/personality.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <format>

namespace plush {

namespace {
// The value of a record ({"value": ...}) or the plain value itself; null when absent.
const Json* recordOf(const Json& section, const char* key) {
  if (!section.is_object()) return nullptr;
  auto it = section.find(key);
  if (it == section.end() || it->is_null()) return nullptr;
  if (it->is_object() && it->contains("value")) {
    const Json& v = (*it)["value"];
    return v.is_null() ? nullptr : &v;
  }
  return &*it;
}
const Json& sectionOf(const Json& j, const char* key) {
  static const Json none;
  auto it = j.find(key);
  return it != j.end() && it->is_object() ? *it : none;
}

struct Reader {
  std::string where;
  std::string error;
  bool ok() const { return error.empty(); }
  void bad(const char* sec, const char* key, const char* what) {
    if (error.empty()) error = std::format("{}: {}.{} {}", where, sec, key, what);
  }
  void number(const Json& s, const char* sec, const char* key, std::optional<float>& out) {
    const Json* v = recordOf(s, key);
    if (!v) return;
    if (v->is_number()) out = v->get<float>();
    else if (v->is_array() && !v->empty() && v->size() <= 2 && (*v)[0].is_number() && v->back().is_number())
      out = 0.5f * ((*v)[0].get<float>() + v->back().get<float>());  // a range where a number is expected: its middle
    else if (!v->is_boolean()) bad(sec, key, "must be a number");
  }
  void range(const Json& s, const char* sec, const char* key, std::optional<PersonalityRange>& out) {
    const Json* v = recordOf(s, key);
    if (!v) return;
    if (v->is_number()) out = PersonalityRange{v->get<float>(), v->get<float>()};
    else if (v->is_array() && v->size() == 2 && (*v)[0].is_number() && (*v)[1].is_number()) {
      float a = (*v)[0].get<float>(), b = (*v)[1].get<float>();
      if (a > b) return bad(sec, key, "range must be [low, high]");
      out = PersonalityRange{a, b};
    } else if (v->is_object() && v->contains("min") && v->contains("max") && (*v)["min"].is_number() && (*v)["max"].is_number()) {
      out = PersonalityRange{(*v)["min"].get<float>(), (*v)["max"].get<float>()};
      if (out->lo > out->hi) return bad(sec, key, "min must not exceed max");
    } else bad(sec, key, "must be a number or a [low, high] range");
  }
  void boolean(const Json& s, const char* sec, const char* key, bool& out) {
    const Json* v = recordOf(s, key);
    if (!v) return;
    if (v->is_boolean()) out = v->get<bool>();
    else bad(sec, key, "must be true or false");
  }
  void text(const Json& s, const char* key, std::string& out) {
    const Json* v = recordOf(s, key);
    if (v && v->is_string()) out = v->get<std::string>();
  }
  void strings(const Json& s, const char* sec, const char* key, std::vector<std::string>& out) {
    const Json* v = recordOf(s, key);
    if (!v) return;
    if (!v->is_array()) return bad(sec, key, "must be a list");
    for (const auto& x : *v) {
      if (x.is_string()) out.push_back(x.get<std::string>());
      else if (x.is_object() && x.contains("name") && x["name"].is_string()) out.push_back(x["name"].get<std::string>());
      else return bad(sec, key, "entries must be names");
    }
  }
  void weights(const Json& s, const char* sec, const char* key, std::map<std::string, float>& out) {
    const Json* v = recordOf(s, key);
    if (!v) return;
    if (!v->is_object()) return bad(sec, key, "must be an object of action unit -> weight");
    for (const auto& [k, w] : v->items()) {
      if (!w.is_number()) return bad(sec, key, "weights must be numbers");
      const float f = w.get<float>();
      if (!std::isfinite(f) || f < -1.0f || f > 1.0f) return bad(sec, key, "weights must lie in [-1, 1]");
      out[k] = f;
    }
  }
};

std::string fmtRange(const PersonalityRange& r) { return std::format("[{:g}, {:g}]", r.lo, r.hi); }
}  // namespace

Result<PersonalityProfile> personalityFromJson(const Json& j, const std::string& id) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.personality")
    return fail("not a plush.personality file");
  if (!j.contains("version") || !j["version"].is_number_integer() || j["version"].get<int>() != 0)
    return fail(std::format("personality: unsupported version {}", j.contains("version") ? j["version"].dump() : "(none)"));
  PersonalityProfile p;
  p.id = id;
  p.character = j.value("character", std::string());
  p.profileVersion = j.contains("profile_version") && j["profile_version"].is_string() ? j["profile_version"].get<std::string>() : "";
  p.status = j.contains("status") && j["status"].is_string() ? j["status"].get<std::string>() : "";
  Reader r{id.empty() ? std::string("personality") : "personality '" + id + "'", {}};

  const Json& tempo = sectionOf(j, "tempo");
  r.number(tempo, "tempo", "action_speed", p.actionSpeed);
  r.range(tempo, "tempo", "reach_frames", p.reachFrames);
  r.range(tempo, "tempo", "anticipation_frames", p.anticipationFrames);
  r.range(tempo, "tempo", "settle_frames", p.settleFrames);
  r.number(tempo, "tempo", "overshoot", p.overshoot);
  r.range(tempo, "tempo", "hold_frames", p.holdFrames);
  r.number(tempo, "tempo", "careful_place_frames", p.carefulPlaceFrames);
  r.number(tempo, "tempo", "beat_scale", p.beatScale);  // T-104 (timing profiles only)
  r.number(tempo, "tempo", "hold_scale", p.holdScale);
  if (p.beatScale && *p.beatScale <= 0) r.bad("tempo", "beat_scale", "must be > 0");
  if (p.holdScale && *p.holdScale <= 0) r.bad("tempo", "hold_scale", "must be > 0");
  if (p.actionSpeed && *p.actionSpeed <= 0) r.bad("tempo", "action_speed", "must be > 0");

  const Json& energy = sectionOf(j, "energy");
  r.number(energy, "energy", "level", p.energyLevel);
  r.number(energy, "energy", "idle_motion_amplitude", p.idleMotionAmplitudeH);
  r.number(energy, "energy", "gesture_amplitude", p.gestureAmplitude);

  const Json& posture = sectionOf(j, "posture");
  r.number(posture, "posture", "slouch", p.slouch);
  r.number(posture, "posture", "head_pitch_deg", p.headPitchDeg);
  r.number(posture, "posture", "head_tilt_deg", p.headTiltDeg);
  r.number(posture, "posture", "shoulders_forward", p.shouldersForward);
  r.number(posture, "posture", "weight_shift", p.weightShift);
  r.number(posture, "posture", "lean_toward_task", p.leanTowardTask);
  r.strings(posture, "posture", "rest_hands", p.restHands);

  const Json& attention = sectionOf(j, "attention");
  r.text(attention, "primary_target", p.primaryTarget);
  r.number(attention, "attention", "span_s", p.attentionSpanS);
  r.number(attention, "attention", "glance_at_others", p.glanceAtOthersPerMin);
  r.range(attention, "attention", "glance_hold_frames", p.glanceHoldFrames);

  const Json& boredom = sectionOf(j, "boredom");
  r.boolean(boredom, "boredom", "enabled", p.boredom);
  r.number(boredom, "boredom", "onset_s", p.boredomOnsetS);
  r.range(boredom, "boredom", "fidget_interval_s", p.fidgetIntervalS);
  r.strings(boredom, "boredom", "fidget_set", p.fidgetSet);

  const Json& gaze = sectionOf(j, "gaze");
  r.range(gaze, "gaze", "saccade_interval_s", p.saccadeIntervalS);
  r.number(gaze, "gaze", "fixation_on_task", p.fixationOnTask);
  r.range(gaze, "gaze", "eyes_lead_head_frames", p.eyesLeadHeadFrames);
  r.number(gaze, "gaze", "look_down_bias", p.lookDownBias);

  const Json& blink = sectionOf(j, "blink");
  if (const Json* v = recordOf(blink, "interval_frames")) {
    if (v->is_object()) {
      if (v->contains("mean") && (*v)["mean"].is_number()) p.blinkIntervalMean = (*v)["mean"].get<float>();
      r.range(blink, "blink", "interval_frames", p.blinkIntervalRange);
    } else {
      r.range(blink, "blink", "interval_frames", p.blinkIntervalRange);
      if (p.blinkIntervalRange) p.blinkIntervalMean = p.blinkIntervalRange->mid();
    }
    if (p.blinkIntervalMean && *p.blinkIntervalMean <= 0) r.bad("blink", "interval_frames", "mean must be > 0");
  }
  r.range(blink, "blink", "duration_frames", p.blinkDurationFrames);
  r.range(blink, "blink", "closed_frames", p.blinkClosedFrames);
  r.boolean(blink, "blink", "couple_to_action_change", p.blinkOnActionChange);
  if (const Json* v = recordOf(blink, "long_blink_on_gaze_drop"); v && v->is_object() && v->contains("duration_frames") &&
                                                                   (*v)["duration_frames"].is_number())
    p.longBlinkFrames = (*v)["duration_frames"].get<float>();

  const Json& face = sectionOf(j, "face");
  r.weights(face, "face", "rest_offset", p.faceRestOffset);
  r.weights(face, "face", "expression_bias", p.faceExpressionBias);
  r.weights(face, "face", "watching_mouth", p.faceWatching);
  r.number(face, "face", "lid_rest", p.lidRest);
  r.number(face, "face", "asymmetry", p.faceAsymmetry);

  const Json& smile = sectionOf(j, "smile");
  r.number(smile, "smile", "frequency", p.smileFrequency);
  r.number(smile, "smile", "open_smile_share", p.openSmileShare);
  r.text(smile, "default_mouth", p.defaultMouth);

  if (auto it = j.find("gestures"); it != j.end() && it->is_object()) {
    Json wrap = {{"g", *it}};
    r.strings(wrap, "gestures", "g", p.gestures);
  }

  // T-097B reaction section (optional; text fields such as channel_order / positive_style stay documentation).
  const Json& reaction = sectionOf(j, "reaction");
  PersonalityReaction& R = p.reaction;
  r.range(reaction, "reaction", "delay_frames", R.delayFrames);
  r.number(reaction, "reaction", "intensity_scale", R.intensityScale);
  r.number(reaction, "reaction", "tempo_scale", R.tempoScale);
  r.number(reaction, "reaction", "hold_scale", R.holdScale);
  r.number(reaction, "reaction", "gaze_shift", R.gazeShift);
  r.number(reaction, "reaction", "gesture_min_intensity", R.gestureMinIntensity);
  auto within = [&](const std::optional<float>& v, const char* key, float lo, float hi, bool openLo) {
    if (v && (!std::isfinite(*v) || (openLo ? *v <= lo : *v < lo) || *v > hi))
      r.bad("reaction", key, openLo ? "out of range (0, 4]" : "must lie in [0, 1]");
  };
  if (R.delayFrames && R.delayFrames->lo < 0) r.bad("reaction", "delay_frames", "must be >= 0");
  within(R.intensityScale, "intensity_scale", 0, 4, true);
  within(R.tempoScale, "tempo_scale", 0, 4, true);
  within(R.holdScale, "hold_scale", 0, 4, true);
  within(R.gazeShift, "gaze_shift", 0, 1, false);
  within(R.gestureMinIntensity, "gesture_min_intensity", 0, 1, false);
  if (const Json* ev = recordOf(reaction, "events")) {
    if (!ev->is_object()) r.bad("reaction", "events", "must be an object of event -> reaction");
    else
      for (const auto& [name, e] : ev->items()) {
        if (!e.is_object()) {
          r.bad("reaction", "events", "entries must be objects");
          break;
        }
        PersonalityReactionEvent out;
        const std::string sec = "reaction.events." + name;
        const char* S = sec.c_str();
        r.text(e, "emotion", out.emotion);
        r.number(e, S, "intensity", out.intensity);
        r.number(e, S, "duration_s", out.durationS);
        r.number(e, S, "gaze_shift", out.gazeShift);
        r.strings(e, S, "gestures", out.gestures);
        if (out.intensity && (*out.intensity < 0 || *out.intensity > 1)) r.bad(S, "intensity", "must lie in [0, 1]");
        if (out.durationS && *out.durationS <= 0) r.bad(S, "duration_s", "must be > 0");
        if (out.gazeShift && (*out.gazeShift < 0 || *out.gazeShift > 1)) r.bad(S, "gaze_shift", "must lie in [0, 1]");
        R.events[name] = std::move(out);
      }
  }

  const Json& lim = sectionOf(j, "limits");
  PersonalityLimits& L = p.limits;
  r.range(lim, "limits", "blink_interval_frames", L.blinkIntervalFrames);
  r.range(lim, "limits", "blink_duration_frames", L.blinkDurationFrames);
  r.range(lim, "limits", "reach_frames", L.reachFrames);
  r.range(lim, "limits", "hold_frames", L.holdFrames);
  r.range(lim, "limits", "action_speed", L.actionSpeed);
  r.number(lim, "limits", "idle_motion_max_H_per_frame", L.idleMotionMaxHPerFrame);
  r.number(lim, "limits", "face_offset_max", L.faceOffsetMax);
  r.range(lim, "limits", "head_pitch_deg", L.headPitchDeg);
  if (L.actionSpeed && L.actionSpeed->lo <= 0) r.bad("limits", "action_speed", "must be > 0");
  if (L.faceOffsetMax && *L.faceOffsetMax < 0) r.bad("limits", "face_offset_max", "must be >= 0");

  if (!r.ok()) return fail(r.error);
  return p;
}

Result<PersonalityProfile> loadPersonality(const std::filesystem::path& file) {
  auto j = parseJsonFile(file);
  if (!j) return std::unexpected(j.error());
  std::string id = file.filename().string();
  for (const char* sfx : {".draft.json", ".json"})
    if (id.size() > std::strlen(sfx) && id.ends_with(sfx)) {
      id.resize(id.size() - std::strlen(sfx));
      break;
    }
  auto p = personalityFromJson(*j, id);
  if (p) p->path = file;
  return p;
}

// ------------------------------------------------------------------ timing profile (T-104)
double TimingProfile::frames(const std::string& beat, double fallback, const PersonalityProfile* who) const {
  auto it = beats.find(beat);
  const double f = it != beats.end() ? double(it->second) : fallback;
  const bool hold = beat == "hold" || beat == "shared_hold";
  const std::optional<float> s = who ? (hold ? who->holdScale : who->beatScale) : std::nullopt;
  return std::round(f * (s ? double(*s) : 1.0));
}

double TimingProfile::travelFrames(double distance, double armLength, const PersonalityProfile* who) const {
  double f = travelMinFrames;
  if (armLength > 1e-6 && armLengthsPerFrame > 1e-6) f = std::ceil(distance / (armLength * armLengthsPerFrame));
  f = std::round(f * (who && who->beatScale ? double(*who->beatScale) : 1.0));
  return std::clamp(f, double(travelMinFrames), double(travelMaxFrames));  // the floor and ceiling of any move
}

Result<TimingProfile> timingProfileFromJson(const Json& j, const std::string& name) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.timing_profile") return fail("not a plush.timing_profile file");
  if (!j.contains("version") || !j["version"].is_number_integer() || j["version"].get<int>() != 1)
    return fail(std::format("timing profile: unsupported version {}", j.contains("version") ? j["version"].dump() : "(none)"));
  TimingProfile t;
  t.name = name.empty() ? j.value("name", std::string()) : name;
  t.status = j.contains("status") && j["status"].is_string() ? j["status"].get<std::string>() : "";
  const std::string where = std::format("timing profile '{}'", t.name);
  if (auto it = j.find("beats"); it != j.end()) {
    if (!it->is_object()) return fail(where + ": beats must be an object of beat -> frames");
    for (const auto& [k, v] : it->items()) {
      const Json* x = v.is_object() && v.contains("value") ? &v["value"] : &v;
      if (!x->is_number() || !std::isfinite(x->get<double>()) || x->get<double>() < 1)
        return fail(std::format("{}: beats.{} must be a number of frames >= 1", where, k));
      t.beats[k] = x->get<float>();
    }
  }
  if (auto it = j.find("travel"); it != j.end()) {
    if (!it->is_object()) return fail(where + ": travel must be an object");
    auto get = [&](const char* k, float& out) -> bool {
      if (!it->contains(k)) return true;
      const Json& v = (*it)[k];
      const Json* x = v.is_object() && v.contains("value") ? &v["value"] : &v;
      if (!x->is_number() || x->get<double>() <= 0) return false;
      out = x->get<float>();
      return true;
    };
    if (!get("arm_lengths_per_frame", t.armLengthsPerFrame) || !get("min_frames", t.travelMinFrames) ||
        !get("max_frames", t.travelMaxFrames) || t.travelMinFrames > t.travelMaxFrames)
      return fail(where + ": travel needs arm_lengths_per_frame > 0 and 0 < min_frames <= max_frames");
  }
  return t;
}

Result<TimingProfile> loadTimingProfile(const std::filesystem::path& file) {
  auto j = parseJsonFile(file);
  if (!j) return std::unexpected(j.error());
  std::string name = file.filename().string();
  if (name.ends_with(".timing.json")) name.resize(name.size() - std::strlen(".timing.json"));
  auto t = timingProfileFromJson(*j, name);
  if (t) t->path = file;
  return t;
}

std::filesystem::path findTimingProfileFile(const std::filesystem::path& from, const std::string& name) {
  if (from.empty() || name.empty() || name.find('/') != std::string::npos || name.find('\\') != std::string::npos) return {};
  std::error_code ec;
  auto d = std::filesystem::absolute(from, ec);
  if (ec) return {};
  if (!std::filesystem::is_directory(d, ec)) d = d.parent_path();
  for (;; d = d.parent_path()) {
    auto cand = d / "content" / "timing" / (name + ".timing.json");
    if (std::filesystem::exists(cand, ec)) return cand;
    if (d == d.parent_path()) return {};
  }
}

std::filesystem::path findPersonalityFile(const std::filesystem::path& from, const std::string& id) {
  if (from.empty() || id.empty() || id.find('/') != std::string::npos || id.find('\\') != std::string::npos) return {};
  std::error_code ec;
  auto d = std::filesystem::absolute(from, ec);
  if (ec) return {};
  if (!std::filesystem::is_directory(d, ec)) d = d.parent_path();
  for (;; d = d.parent_path()) {
    for (const char* sfx : {".json", ".draft.json"}) {
      auto cand = d / "content" / "personality" / (id + sfx);
      if (std::filesystem::exists(cand, ec)) return cand;
    }
    if (d == d.parent_path()) return {};
  }
}

std::vector<std::string> clampPersonalityToLimits(PersonalityProfile& p) {
  std::vector<std::string> w;
  const PersonalityLimits& L = p.limits;
  auto clampValue = [&](std::optional<float>& v, const std::optional<PersonalityRange>& r, const char* what) {
    if (!v || !r || r->contains(*v)) return;
    const float c = r->clamp(*v);
    w.push_back(std::format("personality '{}': {} {:g} outside its limits {} (clamped to {:g})", p.id, what, *v, fmtRange(*r), c));
    v = c;
  };
  auto clampRange = [&](std::optional<PersonalityRange>& v, const std::optional<PersonalityRange>& r, const char* what) {
    if (!v || !r || (r->contains(v->lo) && r->contains(v->hi))) return;
    PersonalityRange c{r->clamp(v->lo), r->clamp(v->hi)};
    w.push_back(std::format("personality '{}': {} {} outside its limits {} (clamped to {})", p.id, what, fmtRange(*v), fmtRange(*r),
                            fmtRange(c)));
    v = c;
  };
  clampValue(p.blinkIntervalMean, L.blinkIntervalFrames, "blink interval");
  clampRange(p.blinkIntervalRange, L.blinkIntervalFrames, "blink interval range");
  clampRange(p.blinkDurationFrames, L.blinkDurationFrames, "blink duration");
  clampRange(p.reachFrames, L.reachFrames, "reach frames");
  clampRange(p.holdFrames, L.holdFrames, "hold frames");
  clampValue(p.actionSpeed, L.actionSpeed, "action speed");
  clampValue(p.headPitchDeg, L.headPitchDeg, "head pitch");
  if (L.faceOffsetMax) {
    const float m = *L.faceOffsetMax;
    for (auto* map : {&p.faceRestOffset, &p.faceExpressionBias, &p.faceWatching})
      for (auto& [k, v] : *map)
        if (std::abs(v) > m) {
          w.push_back(std::format("personality '{}': face offset {} {:g} beyond its limit {:g} (clamped)", p.id, k, v, m));
          v = std::clamp(v, -m, m);
        }
  }
  return w;
}

PersonalityActionUnits defaultPersonalityActionUnits() {
  PersonalityActionUnits u;
  // Shared action units (pipeline/charsys/face_library/expressions.json) -> controls of older packages.
  u.aliases = {
      {"Blink.L", {"Blink.L", "blinkLeft", "Blink"}},  {"Blink.R", {"Blink.R", "blinkRight", "Blink"}},
      {"BrowUp.L", {"BrowUp.L", "browUp"}},            {"BrowUp.R", {"BrowUp.R", "browUp"}},
      {"BrowDown", {"BrowDown", "browDown"}},          {"BrowSad", {"BrowSad", "browSad", "Worried"}},
      {"EyeWide", {"EyeWide", "eyeWide"}},             {"EyeSquint", {"EyeSquint", "squint"}},
      {"MouthSmile", {"MouthSmile", "mouthSmile", "smile"}},   {"MouthFrown", {"MouthFrown", "mouthFrown", "frown"}},
      {"MouthWide", {"MouthWide", "mouthWide"}},       {"MouthO", {"MouthO", "mouthO"}},
      {"JawOpen", {"JawOpen", "jawOpen"}},
  };
  return u;
}

Result<PersonalityActionUnits> personalityActionUnitsFromJson(const Json& j) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.personality_action_units")
    return fail("not a plush.personality_action_units file");
  if (j.value("version", 0) != 1) return fail(std::format("personality action units: unsupported version {}", j.value("version", 0)));
  auto it = j.find("aliases");
  if (it == j.end() || !it->is_object()) return fail("personality action units: 'aliases' must be an object");
  PersonalityActionUnits u;
  for (const auto& [au, list] : it->items()) {
    if (!list.is_array()) return fail(std::format("personality action units: '{}' must be a list of control names", au));
    auto& out = u.aliases[au];
    for (const auto& n : list) {
      if (!n.is_string()) return fail(std::format("personality action units: '{}' entries must be strings", au));
      out.push_back(n.get<std::string>());
    }
  }
  return u;
}

}  // namespace plush
