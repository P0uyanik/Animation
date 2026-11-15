#include "model/clip.h"

#include <algorithm>
#include <cmath>
#include <fstream>

namespace plush {

namespace {
vec3 v3(const Json& j, vec3 fallback) {
  if (!j.is_array() || j.size() < 3) return fallback;
  return vec3(j[0].get<float>(), j[1].get<float>(), j[2].get<float>());
}
Json jv(vec3 v) { return Json::array({v.x, v.y, v.z}); }
vec3 mirrorVec(vec3 v) { return vec3(-v.x, v.y, v.z); }
quat mirrorQuat(quat q) { return quat(q.w, q.x, -q.y, -q.z); }  // reflection across x = 0: M R M
// Rotation of the frame (x = dir × twist, y = dir, z = twist).
quat frameQuat(vec3 dir, vec3 twist) {
  vec3 y = glm::normalize(dir), z = glm::normalize(twist - y * glm::dot(twist, y));
  vec3 x = glm::cross(y, z);
  return glm::normalize(glm::quat_cast(mat3(x, y, z)));
}
// Twist reference perpendicular to dir (falls back to other axes if the hint is parallel).
vec3 perpendicular(vec3 dir, vec3 hint) {
  for (vec3 h : {hint, vec3(0, 1, 0), vec3(1, 0, 0), vec3(0, 0, 1)}) {
    vec3 t = h - dir * glm::dot(h, dir);
    if (glm::length(t) > 1e-3f) return glm::normalize(t);
  }
  return vec3(0, 0, 1);
}
std::string mirrorName(const std::string& n, const std::string& l, const std::string& r) {
  if (n.size() >= l.size() && n.compare(n.size() - l.size(), l.size(), l) == 0) return n.substr(0, n.size() - l.size()) + r;
  if (n.size() >= r.size() && n.compare(n.size() - r.size(), r.size(), r) == 0) return n.substr(0, n.size() - r.size()) + l;
  return n;
}
float angleDeg(vec3 a, vec3 b) {  // atan2 form: accurate for small angles (acos of a float dot is not)
  glm::dvec3 x = glm::normalize(glm::dvec3(a)), y = glm::normalize(glm::dvec3(b));
  return float(glm::degrees(std::atan2(glm::length(glm::cross(x, y)), glm::dot(x, y))));
}
}  // namespace

// ------------------------------------------------------------------ reference pose
const ReferenceRole* ReferencePose::find(const std::string& role) const {
  auto it = index.find(role);
  return it == index.end() ? nullptr : &roles[size_t(it->second)];
}

Result<ReferencePose> referencePoseFromJson(const Json& j) {
  ReferencePose p;
  if (!j.is_object() || !j.contains("roles") || !j["roles"].is_object()) return fail("reference_pose: no roles");
  p.version = j.value("version", 0);
  if (p.version != 1) return fail("reference_pose: unsupported version");
  std::string l = ".L", r = ".R";
  if (auto m = j.find("mirror"); m != j.end() && m->contains("suffix") && (*m)["suffix"].size() == 2)
    l = (*m)["suffix"][0].get<std::string>(), r = (*m)["suffix"][1].get<std::string>();
  auto parse = [&](const std::string& name, const Json& e, bool mirror) {
    ReferenceRole rr;
    auto mn = [&](const std::string& s) { return mirror ? mirrorName(s, l, r) : s; };
    auto mv = [&](vec3 v) { return mirror ? mirrorVec(v) : v; };
    rr.name = mn(name);
    rr.parent = e.contains("parent") && e["parent"].is_string() ? mn(e["parent"].get<std::string>()) : "";
    rr.end = e.contains("end") && e["end"].is_string() ? mn(e["end"].get<std::string>()) : "";
    rr.endDir = mv(v3(e.value("end_dir", Json()), vec3(0)));
    rr.continueFromParent = e.value("continue", false);
    rr.fallbackParentDir = e.value("end_fallback_dir_from_parent", false);
    if (auto tf = e.find("twist_from"); tf != e.end() && tf->is_array() && tf->size() == 2)
      rr.twistFrom[0] = mn((*tf)[0].get<std::string>()), rr.twistFrom[1] = mn((*tf)[1].get<std::string>());
    rr.twistHint = mv(v3(e.value("twist_hint", Json()), vec3(0, 0, 1)));
    rr.refDir = glm::normalize(mv(v3(e.value("ref_dir", Json()), vec3(0, 1, 0))));
    rr.refTwist = perpendicular(rr.refDir, mv(v3(e.value("ref_twist", Json()), vec3(0, 0, 1))));
    return rr;
  };
  const Json& roles = j["roles"];
  std::vector<std::pair<std::string, const Json*>> left;
  for (auto it = roles.begin(); it != roles.end(); ++it) {
    p.roles.push_back(parse(it.key(), it.value(), false));
    const std::string& k = it.key();
    if (k.size() > l.size() && k.compare(k.size() - l.size(), l.size(), l) == 0) left.push_back({k, &it.value()});
  }
  for (auto& [k, e] : left) {
    std::string rn = mirrorName(k, l, r);
    if (!roles.contains(rn)) p.roles.push_back(parse(k, *e, true));
  }
  // order: semantic parents first (a parent that is not a role counts as character space)
  std::vector<ReferenceRole> ordered;
  std::map<std::string, bool> placed, known;
  for (auto& rr : p.roles) known[rr.name] = true;
  for (size_t pass = 0; ordered.size() < p.roles.size() && pass <= p.roles.size(); ++pass)
    for (auto& rr : p.roles)
      if (!placed[rr.name] && (rr.parent.empty() || !known[rr.parent] || placed[rr.parent])) {
        ordered.push_back(rr);
        placed[rr.name] = true;
      }
  if (ordered.size() != p.roles.size()) return fail("reference_pose: cyclic parents");
  p.roles = ordered;
  for (size_t i = 0; i < p.roles.size(); ++i) p.index[p.roles[i].name] = int(i);
  return p;
}

// ------------------------------------------------------------------ retarget data
RetargetData deriveRetarget(const Skeleton& sk, const ReferencePose& ref) {
  RetargetData d;
  d.referenceVersion = ref.version;
  d.source = "derived";
  auto head = [&](const std::string& n, vec3& out) {
    int b = sk.find(n);
    if (b < 0) return false;
    out = sk.bones[size_t(b)].head;
    return true;
  };
  for (const auto& rr : ref.roles) {
    vec3 h;
    if (!head(rr.name, h)) continue;
    RetargetRole role;
    vec3 e, ph;
    bool ok = false;
    if (!rr.end.empty() && head(rr.end, e) && glm::length(e - h) > 1e-6f) {
      role.dir = glm::normalize(e - h), role.length = glm::length(e - h), ok = true;
    } else if (glm::length(rr.endDir) > 0) {
      role.dir = glm::normalize(rr.endDir), ok = true;
    } else if (rr.continueFromParent && head(rr.parent, ph) && glm::length(h - ph) > 1e-6f) {
      role.dir = glm::normalize(h - ph), role.length = glm::length(h - ph), ok = true;
    } else if (rr.fallbackParentDir && d.roles.count(rr.parent)) {
      role.dir = d.roles[rr.parent].dir, ok = true;
    }
    if (!ok) continue;
    vec3 hint = rr.twistHint, a, b;
    if (!rr.twistFrom[0].empty() && head(rr.twistFrom[0], a) && head(rr.twistFrom[1], b) && glm::length(a - b) > 1e-6f) hint = a - b;
    role.twist = perpendicular(role.dir, hint);
    d.roles[rr.name] = role;
  }
  vec3 hh;
  d.height = head("head", hh) ? hh.y : 0.0f;
  d.legLength = legLength(sk);
  return d;
}

Result<RetargetData> retargetFromJson(const Json& j) {
  RetargetData d;
  if (!j.is_object() || !j.contains("roles") || !j["roles"].is_object()) return fail("retarget: no roles");
  d.referenceVersion = j.value("reference_version", 0);
  d.height = j.value("height", 0.0f);
  d.legLength = j.value("leg_length", 0.0f);
  d.source = "package";
  for (auto it = j["roles"].begin(); it != j["roles"].end(); ++it) {
    RetargetRole r;
    r.dir = v3(it.value().value("dir", Json()), vec3(0));
    r.twist = v3(it.value().value("twist", Json()), vec3(0));
    r.length = it.value().value("length", 0.0f);
    if (glm::length(r.dir) < 0.5f || glm::length(r.twist) < 0.5f) return fail("retarget: bad vectors for role " + it.key());
    r.dir = glm::normalize(r.dir);
    r.twist = perpendicular(r.dir, r.twist);
    d.roles[it.key()] = r;
  }
  return d;
}

Json retargetToJson(const RetargetData& r) {
  Json roles = Json::object();
  for (auto& [n, x] : r.roles) roles[n] = {{"dir", jv(x.dir)}, {"twist", jv(x.twist)}, {"length", x.length}};
  return {{"version", 1}, {"reference_version", r.referenceVersion}, {"roles", roles}, {"height", r.height},
          {"leg_length", r.legLength}, {"source", r.source}};
}

float retargetMaxDifferenceDeg(const RetargetData& a, const RetargetData& b) {
  float m = 0;
  for (auto& [n, x] : a.roles) {
    auto it = b.roles.find(n);
    if (it == b.roles.end()) return 180.0f;
    m = std::max({m, angleDeg(x.dir, it->second.dir), angleDeg(x.twist, it->second.twist)});
  }
  return a.roles.size() == b.roles.size() ? m : 180.0f;
}

// ------------------------------------------------------------------ clips
std::string mirrorRole(const ClipData& c, const std::string& role) { return mirrorName(role, c.mirrorL, c.mirrorR); }

Result<ClipData> clipFromJson(const Json& j, const std::string& name) {
  ClipData c;
  if (!j.is_object() || j.value("format", "") != "plush.clip") return fail("not a plush.clip file");
  if (j.value("version", 0) != 1) return fail("unsupported plush.clip version");
  c.raw = j;
  c.name = j.value("name", name);
  c.fps = j.value("fps", 30.0);
  c.frameCount = j.value("frame_count", 1);
  c.loop = j.value("loop", false);
  if (c.fps <= 0 || c.frameCount < 1) return fail(c.name + ": bad fps or frame_count");
  if (!j.contains("license") || !j["license"].is_string() || j["license"].get<std::string>().empty())
    return fail(c.name + ": the license field is required");
  auto ref = referencePoseFromJson(j.value("reference_pose", Json()));
  if (!ref) return fail(c.name + ": " + ref.error().message);
  c.reference = *ref;
  if (auto m = j.find("mirror"); m != j.end() && m->is_object() && m->contains("suffix") && (*m)["suffix"].size() == 2)
    c.mirrorL = (*m)["suffix"][0].get<std::string>(), c.mirrorR = (*m)["suffix"][1].get<std::string>();
  auto readQuat = [](const Json& a, size_t o) {
    return glm::normalize(quat(a[o].get<float>(), a[o + 1].get<float>(), a[o + 2].get<float>(), a[o + 3].get<float>()));
  };
  const Json tracks = j.value("tracks", Json::object());
  for (auto it = tracks.begin(); it != tracks.end(); ++it) {
    ClipTrack t;
    const Json& tj = it.value();
    if (tj.contains("samples")) {  // dense: one quaternion per clip frame
      const Json& s = tj["samples"];
      for (size_t f = 0; f < s.size(); ++f) {
        if (!s[f].is_array() || s[f].size() != 4) return fail(c.name + ": bad sample in " + it.key());
        t.frames.push_back(double(f));
        t.values.push_back(readQuat(s[f], 0));
      }
    } else if (tj.contains("keys")) {  // sparse: [frame, w, x, y, z]
      for (const Json& k : tj["keys"]) {
        if (!k.is_array() || k.size() != 5) return fail(c.name + ": bad key in " + it.key());
        t.frames.push_back(k[0].get<double>());
        t.values.push_back(readQuat(k, 1));
      }
    } else {
      return fail(c.name + ": track " + it.key() + " has neither keys nor samples");
    }
    if (t.frames.empty()) continue;
    for (size_t i = 1; i < t.frames.size(); ++i)
      if (t.frames[i] <= t.frames[i - 1]) return fail(c.name + ": keys of " + it.key() + " are not increasing");
    c.tracks[it.key()] = std::move(t);
  }
  if (auto m = j.find("mask"); m != j.end() && m->is_array())
    for (auto& r : *m) c.mask.push_back(r.get<std::string>());
  if (c.mask.empty())
    for (auto& [r, _] : c.tracks) c.mask.push_back(r);
  if (auto root = j.find("root"); root != j.end() && root->is_object()) {
    c.rootScale = root->value("scale", std::string("leg_length"));
    const Json tr = root->value("translation", Json::object());
    if (tr.contains("samples"))
      for (size_t f = 0; f < tr["samples"].size(); ++f) c.rootFrames.push_back(double(f)), c.rootValues.push_back(v3(tr["samples"][f], vec3(0)));
    else
      for (const Json& k : tr.value("keys", Json::array()))
        c.rootFrames.push_back(k[0].get<double>()), c.rootValues.push_back(vec3(k[1].get<float>(), k[2].get<float>(), k[3].get<float>()));
    const Json hd = root->value("heading", Json::object());
    if (hd.contains("samples"))
      for (size_t f = 0; f < hd["samples"].size(); ++f) c.headingFrames.push_back(double(f)), c.headingValues.push_back(hd["samples"][f].get<float>());
    else
      for (const Json& k : hd.value("keys", Json::array())) c.headingFrames.push_back(k[0].get<double>()), c.headingValues.push_back(k[1].get<float>());
  }
  return c;
}

Result<ClipData> loadClip(const std::filesystem::path& path) {
  auto j = parseJsonFile(path);
  if (!j) return std::unexpected(j.error());
  std::string stem = path.filename().string();
  if (auto p = stem.find(".clip.json"); p != std::string::npos) stem = stem.substr(0, p);
  auto c = clipFromJson(*j, stem);
  if (!c) return fail(path.string() + ": " + c.error().message);
  return c;
}

namespace {
// Segment search on sorted frames; returns (i0, i1, t). For a loop of length N the segment after the last key wraps
// to the first key (+N).
struct Seg {
  size_t i0 = 0, i1 = 0;
  float t = 0;
};
Seg segment(const std::vector<double>& fr, double f, bool loop, double N) {
  Seg s;
  if (fr.size() == 1) return s;
  if (loop) {
    f = std::fmod(f, N);
    if (f < 0) f += N;
    if (f >= fr.back() || f < fr.front()) {  // wrap segment last -> first + N
      double a = fr.back(), b = fr.front() + N, x = f < fr.front() ? f + N : f;
      s.i0 = fr.size() - 1, s.i1 = 0, s.t = b > a ? float((x - a) / (b - a)) : 0.0f;
      return s;
    }
  } else {
    if (f <= fr.front()) return s;
    if (f >= fr.back()) {
      s.i0 = s.i1 = fr.size() - 1;
      return s;
    }
  }
  size_t i1 = size_t(std::upper_bound(fr.begin(), fr.end(), f) - fr.begin());
  s.i0 = i1 - 1, s.i1 = i1;
  s.t = float((f - fr[s.i0]) / (fr[s.i1] - fr[s.i0]));
  return s;
}
}  // namespace

ClipSample sampleClip(const ClipData& c, double f, bool mirror) {
  ClipSample s;
  const double N = c.frameCount;
  for (const auto& [role, t] : c.tracks) {
    Seg g = segment(t.frames, f, c.loop, N);
    quat q = glm::normalize(glm::slerp(t.values[g.i0], t.values[g.i1], g.t));
    if (mirror) s.local[mirrorRole(c, role)] = mirrorQuat(q);
    else s.local[role] = q;
  }
  if (c.hasRoot()) {
    // A loop's root wraps with its per-cycle displacement ("root.cycle_offset", default none).
    const vec3 cycle = v3(c.raw.value("root", Json::object()).value("cycle_offset", Json()), vec3(0));
    double cycles = c.loop ? std::floor(f / N) : 0.0;
    Seg g = segment(c.rootFrames, f, c.loop, N);
    vec3 a = c.rootValues[g.i0], b = c.rootValues[g.i1];
    if (c.loop && g.i1 == 0 && g.i0 == c.rootFrames.size() - 1) b += cycle;  // seam: continue, no reset
    s.root = glm::mix(a, b, g.t) + float(cycles) * cycle;
    if (mirror) s.root = mirrorVec(s.root);
  }
  if (c.hasHeading()) {
    Seg g = segment(c.headingFrames, f, c.loop, N);
    s.heading = glm::mix(c.headingValues[g.i0], c.headingValues[g.i1], g.t);
    if (mirror) s.heading = -s.heading;
  }
  return s;
}

ClipBinding bindClip(const Skeleton& sk, const ReferencePose& ref, const RetargetData& data) {
  ClipBinding b;
  b.legLength = data.legLength;
  b.retargetSource = data.source;
  for (const auto& rr : ref.roles) {
    ClipBinding::Role r;
    r.name = rr.name;
    auto it = data.roles.find(rr.name);
    r.bone = it == data.roles.end() ? -1 : sk.find(rr.name);
    if (r.bone >= 0) r.A = glm::normalize(frameQuat(rr.refDir, rr.refTwist) * glm::inverse(frameQuat(it->second.dir, it->second.twist)));
    // nearest present semantic ancestor
    for (const ReferenceRole* p = ref.find(rr.parent); p; p = ref.find(p->parent)) {
      auto pi = b.roleIndex.find(p->name);
      if (pi != b.roleIndex.end() && b.roles[size_t(pi->second)].bone >= 0) {
        r.parentRole = pi->second;
        break;
      }
    }
    b.roleIndex[r.name] = int(b.roles.size());
    b.roles.push_back(r);
  }
  return b;
}

quat globalRotation(const Skeleton& sk, const Pose& pose, int bone) {
  quat q(1, 0, 0, 0);
  for (int b = bone; b >= 0; b = sk.bones[size_t(b)].parent) q = pose.local[size_t(b)] * q;
  return q;
}

vec3 posedRoleDirection(const Skeleton& sk, const std::vector<mat4>& G, const RetargetData& d, const std::string& role) {
  int b = sk.find(role);
  auto it = d.roles.find(role);
  if (b < 0 || it == d.roles.end()) return vec3(0);
  return glm::normalize(mat3(G[size_t(b)]) * it->second.dir);
}
vec3 posedRoleTwist(const Skeleton& sk, const std::vector<mat4>& G, const RetargetData& d, const std::string& role) {
  int b = sk.find(role);
  auto it = d.roles.find(role);
  if (b < 0 || it == d.roles.end()) return vec3(0);
  return glm::normalize(mat3(G[size_t(b)]) * it->second.twist);
}

}  // namespace plush
