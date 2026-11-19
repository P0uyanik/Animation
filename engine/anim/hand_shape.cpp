#include "anim/hand_shape.h"

#include <algorithm>
#include <cstring>
#include <format>
#include <initializer_list>
#include <set>
#include <vector>

namespace plush {

namespace {

constexpr const char* kFingerNames[4] = {"little", "ring", "middle", "index"};  // finger k = 0 .. 3

// Collects every problem of one file, so a broken shape reports all of them at once.
struct Reader {
  std::string where;
  std::vector<std::string> errors;
  void bad(const std::string& key, const std::string& why) { errors.push_back(std::format("{}: {} {}", where, key, why)); }
  void onlyKeys(const Json& j, const std::string& ctx, std::initializer_list<const char*> keys) {
    if (!j.is_object()) return;
    for (auto it = j.begin(); it != j.end(); ++it) {
      bool known = false;
      for (const char* k : keys) known |= it.key() == k;
      if (!known) bad(ctx + it.key(), "is not a hand-shape key");
    }
  }
  std::optional<float> number(const Json& j, const std::string& ctx, const char* key, float lo, float hi) {
    if (!j.contains(key)) return std::nullopt;
    const Json& v = j[key];
    if (!v.is_number()) {
      bad(ctx + key, "must be a number");
      return std::nullopt;
    }
    const float x = v.get<float>();
    if (x < lo || x > hi) {
      bad(ctx + key, std::format("must be in [{}, {}] (got {})", lo, hi, x));
      return std::nullopt;
    }
    return x;
  }
  std::string choice(const Json& j, const char* key, const std::string& fallback, std::initializer_list<const char*> allowed) {
    if (!j.contains(key)) return fallback;
    if (!j[key].is_string()) {
      bad(key, "must be a string");
      return fallback;
    }
    const std::string s = j[key].get<std::string>();
    for (const char* a : allowed)
      if (s == a) return s;
    std::string list;
    for (const char* a : allowed) list += (list.empty() ? "" : ", ") + std::string(a);
    bad(key, std::format("must be one of {} (got \"{}\")", list, s));
    return fallback;
  }
  HandShapePose pose(const Json& j, const std::string& ctx) {
    HandShapePose p;
    if (!j.is_object()) {
      bad(ctx, "must be an object");
      return p;
    }
    onlyKeys(j, ctx + ".", {"curl", "thumb", "spread", "index", "thumb_opposition", "fingers"});
    const std::string c = ctx + ".";
    if (auto v = number(j, c, "curl", 0, 1)) p.curl = *v;
    if (auto v = number(j, c, "thumb", 0, 1)) p.thumb = *v;
    if (auto v = number(j, c, "spread", -1, 1)) p.spread = *v;
    p.index = number(j, c, "index", 0, 1);
    p.thumbOpposition = number(j, c, "thumb_opposition", 0, 1);
    if (j.contains("fingers")) {
      const Json& f = j["fingers"];
      if (!f.is_object()) {
        bad(c + "fingers", "must be an object");
      } else {
        onlyKeys(f, c + "fingers.", {"little", "ring", "middle", "index"});
        for (int k = 0; k < 4; ++k) {
          if (!f.contains(kFingerNames[k])) continue;
          const Json& fk = f[kFingerNames[k]];
          const std::string fc = std::format("{}fingers.{}.", c, kFingerNames[k]);
          if (!fk.is_object()) {
            bad(fc, "must be an object");
            continue;
          }
          onlyKeys(fk, fc, {"curl", "spread"});
          vec2 v(p.curl, p.spread);
          if (auto x = number(fk, fc, "curl", 0, 1)) v.x = *x;
          if (auto x = number(fk, fc, "spread", -1, 1)) v.y = *x;
          p.fingers[size_t(k)] = v;
        }
        if (p.index && p.fingers[3]) bad(c + "index", "and fingers.index both given");
      }
    }
    return p;
  }
};

}  // namespace

HandPose HandShapePose::handPose() const {
  HandPose hp;
  hp.curl = curl;
  hp.thumb = thumb;
  hp.spread = spread;
  if (index) hp.index = *index;
  for (int k = 0; k < 4; ++k)
    if (fingers[size_t(k)]) hp.finger[size_t(k)] = vec3(*fingers[size_t(k)], 0.0f);
  if (thumbOpposition) hp.thumbPose = vec2(*thumbOpposition, thumb);
  return hp;
}

Result<HandShape> handShapeFromJson(const Json& j, const std::string& id) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.hand_shape") return fail("not a plush.hand_shape file");
  if (!j.contains("version") || !j["version"].is_number_integer() || j["version"].get<int>() != 1)
    return fail(std::format("hand shape: unsupported version {}", j.contains("version") ? j["version"].dump() : "(none)"));
  HandShape s;
  s.id = j.contains("id") && j["id"].is_string() ? j["id"].get<std::string>() : "";
  Reader r{"hand shape '" + (s.id.empty() ? id : s.id) + "'", {}};
  r.onlyKeys(j, "", {"format", "version", "id", "kind", "description", "approach", "pose", "search", "thumb",
                     "pinch_radius", "palm", "stagger"});
  if (s.id.empty()) r.bad("id", "is required (a non-empty string)");
  if (!id.empty() && !s.id.empty() && s.id != id) r.bad("id", std::format("\"{}\" does not match the file name \"{}\"", s.id, id));
  s.kind = r.choice(j, "kind", "", {"grasp", "rest", "gesture"});
  if (!j.contains("kind")) r.bad("kind", "is required");
  if (j.contains("description")) {
    if (j["description"].is_string()) s.description = j["description"].get<std::string>();
    else r.bad("description", "must be a string");
  }
  if (!j.contains("pose")) r.bad("pose", "is required");
  else s.pose = r.pose(j["pose"], "pose");
  if (j.contains("approach")) s.approach = r.pose(j["approach"], "approach");
  const bool grasp = s.kind == "grasp";
  if (grasp && !s.approach) r.bad("approach", "is required for a grasp shape");
  for (const char* k : {"search", "thumb", "pinch_radius", "palm"})
    if (!grasp && j.contains(k)) r.bad(k, "is only for grasp shapes");
  const std::string search = r.choice(j, "search", "none", {"all", "pinch", "none"});
  s.search = search == "all" ? HandShapeSearch::All : search == "pinch" ? HandShapeSearch::Pinch : HandShapeSearch::None;
  const std::string thumb = r.choice(j, "thumb", "opposed", {"opposed", "along", "tucked"});
  s.thumb = thumb == "along" ? HandPose::Thumb::Along : thumb == "tucked" ? HandPose::Thumb::Tucked : HandPose::Thumb::Opposed;
  s.pinchRadius = r.number(j, "", "pinch_radius", 1e-4f, 1.0f);
  if (s.search == HandShapeSearch::Pinch && !s.pinchRadius) r.bad("pinch_radius", "is required for search \"pinch\"");
  if (s.search != HandShapeSearch::Pinch && j.contains("pinch_radius")) r.bad("pinch_radius", "is only for search \"pinch\"");
  s.palmUp = r.choice(j, "palm", "facing", {"facing", "up"}) == "up";
  if (auto v = r.number(j, "", "stagger", 0, 6)) s.stagger = *v;
  if (!r.errors.empty()) {
    std::string msg;
    for (const auto& e : r.errors) msg += (msg.empty() ? "" : "; ") + e;
    return fail(msg);
  }
  return s;
}

Result<HandShape> loadHandShape(const std::filesystem::path& file) {
  auto j = parseJsonFile(file);
  if (!j) return std::unexpected(j.error());
  std::string name = file.filename().string();
  if (name.ends_with(".hand_shape.json")) name.resize(name.size() - std::strlen(".hand_shape.json"));
  auto s = handShapeFromJson(*j, name);
  if (!s) return fail(std::format("{}: {}", file.string(), s.error().message));
  s->path = file;
  return s;
}

const HandShape* HandShapeTable::find(const std::string& id) const {
  auto it = shapes.find(id);
  return it == shapes.end() ? nullptr : &it->second;
}

Result<HandShapeTable> loadHandShapeTable(const std::filesystem::path& dir) {
  std::error_code ec;
  if (!std::filesystem::is_directory(dir, ec)) return fail(std::format("hand shapes: no directory {}", dir.string()));
  std::vector<std::filesystem::path> files;
  for (const auto& e : std::filesystem::directory_iterator(dir, ec))
    if (e.is_regular_file() && e.path().filename().string().ends_with(".hand_shape.json")) files.push_back(e.path());
  std::sort(files.begin(), files.end());
  HandShapeTable t;
  for (const auto& f : files) {
    auto s = loadHandShape(f);
    if (!s) return std::unexpected(s.error());
    if (t.shapes.count(s->id)) return fail(std::format("hand shapes: duplicate id \"{}\" ({})", s->id, f.string()));
    t.shapes.emplace(s->id, std::move(*s));
  }
  if (t.shapes.empty()) return fail(std::format("hand shapes: no *.hand_shape.json in {}", dir.string()));
  return t;
}

std::filesystem::path findHandShapeDir(const std::filesystem::path& from) {
  if (from.empty()) return {};
  std::error_code ec;
  auto d = std::filesystem::absolute(from, ec);
  if (ec) return {};
  if (!std::filesystem::is_directory(d, ec)) d = d.parent_path();
  for (;; d = d.parent_path()) {
    auto cand = d / "content" / "hand_shapes";
    if (std::filesystem::is_directory(cand, ec)) return cand;
    if (d == d.parent_path()) return {};
  }
}

HandShape biased(const HandShape& shape, float restCurlBias) {
  HandShape s = shape;
  auto bias = [&](HandShapePose& p) {
    p.curl = std::clamp(p.curl + restCurlBias, 0.0f, 1.0f);
    for (auto& f : p.fingers)
      if (f) f->x = std::clamp(f->x + restCurlBias, 0.0f, 1.0f);
  };
  bias(s.pose);
  if (s.approach) bias(*s.approach);
  return s;
}

void keyHandShape(Clip& clip, const std::string& hand, double frame, const HandShape& shape, bool approach, Interp interp) {
  const HandShapePose& p = approach && shape.approach ? *shape.approach : shape.pose;
  auto key = [&](const std::string& name, vec3 v) { clip.tracks[name].setKey(Key{frame, v, interp}); };
  key(hand, vec3(p.curl, p.thumb, p.spread));
  if (p.index) key(hand + ".index", vec3(*p.index));
  const bool pinch = shape.search == HandShapeSearch::Pinch;
  for (int k = 0; k < 4; ++k) {
    const bool freeFinger = pinch && k != 3;
    if (p.fingers[size_t(k)]) key(std::format("{}.f{}", hand, k), vec3(*p.fingers[size_t(k)], freeFinger ? 1.0f : 0.0f));
    else if (freeFinger) key(std::format("{}.f{}", hand, k), vec3(p.curl, p.spread, 1.0f));
  }
  if (p.thumbOpposition) key(hand + ".thumb", vec3(*p.thumbOpposition, p.thumb, 0));
  if (shape.stagger > 0) key(hand + ".stagger", vec3(shape.stagger));
}

}  // namespace plush
