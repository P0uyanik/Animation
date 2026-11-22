#include "anim/secondary.h"

#include <algorithm>
#include <cmath>
#include <format>

namespace plush {
namespace {

void readParams(const Json& j, SpringParams& p) {
  p.stiffness = readFloat(j, "stiffness", p.stiffness);
  p.stiffnessTip = readFloat(j, "stiffness_tip", p.stiffnessTip);
  p.damping = readFloat(j, "damping", p.damping);
  p.gravity = readFloat(j, "gravity", p.gravity);
  p.drag = readFloat(j, "drag", p.drag);
  p.limitDeg = readFloat(j, "limit_deg", p.limitDeg);
  p.radius = readFloat(j, "radius", p.radius);
}

Json paramsToJson(const SpringParams& p) {
  return {{"stiffness", p.stiffness}, {"stiffness_tip", p.stiffnessTip}, {"damping", p.damping}, {"gravity", p.gravity},
          {"drag", p.drag}, {"limit_deg", p.limitDeg}, {"radius", p.radius}};
}

Result<void> checkParams(const SpringParams& p, const std::string& where) {
  const bool ok = std::isfinite(p.stiffness) && p.stiffness >= 0 && std::isfinite(p.stiffnessTip) && std::isfinite(p.damping) &&
                  p.damping >= 0 && std::isfinite(p.gravity) && std::isfinite(p.drag) && p.drag >= 0 &&
                  std::isfinite(p.limitDeg) && p.limitDeg >= 0 && p.limitDeg <= 180 && std::isfinite(p.radius) && p.radius >= 0;
  if (!ok) return fail("dynamics: invalid parameters in " + where);
  return {};
}

Json v3(vec3 v) { return Json::array({v.x, v.y, v.z}); }

// Collider push / segment-length passes per joint and step (T-101), and how far inside a collider a joint may stay
// after the first pass (well under the collision test's 0.1 mm).
constexpr int kColliderPasses = 16;
constexpr float kColliderTolerance = 2e-5f;
constexpr float kArcPi = 3.14159265358979f;
// contact.segments (T-183): contacts closer to the segment's first joint than this share of its length are left to
// that joint's own test (the lever of joint k on such a point is too short to push it out).
constexpr float kSegmentMinParam = 0.35f;
// contact.solid: a joint or segment counts as carried past a collider within one step (and leaves on its previous
// side) only when it was outside at the previous step (within this slack) and is now deeper than half the distance.
constexpr float kFlipSlack = 1e-3f;
// contact.rest: a joint that a collider held beyond the chain's angular limit returns to the limit at this rate (1/s)
// once it is free (the excess angle decays; 12 1/s = a twelfth of a second to lose 63 % of it).
constexpr float kLimitReturn = 12.0f;

vec3 closestOnSegment(vec3 p, vec3 a, vec3 b) {
  const vec3 ab = b - a;
  const float l2 = glm::dot(ab, ab);
  if (l2 < 1e-12f) return a;
  return a + ab * std::clamp(glm::dot(p - a, ab) / l2, 0.0f, 1.0f);
}

// Closest points of segments [p1, q1] and [p2, q2]: c1 on the first (at parameter s in [0, 1]), c2 on the second.
void closestSegments(vec3 p1, vec3 q1, vec3 p2, vec3 q2, float& s, vec3& c1, vec3& c2) {
  const vec3 d1 = q1 - p1, d2 = q2 - p2, r = p1 - p2;
  const float a = glm::dot(d1, d1), e = glm::dot(d2, d2), f = glm::dot(d2, r);
  float t = 0;
  s = 0;
  if (a > 1e-12f && e > 1e-12f) {
    const float c = glm::dot(d1, r), b = glm::dot(d1, d2), den = a * e - b * b;
    s = den > 1e-12f ? std::clamp((b * f - c * e) / den, 0.0f, 1.0f) : 0.0f;
    t = (b * s + f) / e;
    if (t < 0) {
      t = 0;
      s = std::clamp(-c / a, 0.0f, 1.0f);
    } else if (t > 1) {
      t = 1;
      s = std::clamp((b - c) / a, 0.0f, 1.0f);
    }
  } else if (a > 1e-12f) {
    s = std::clamp(-glm::dot(d1, r) / a, 0.0f, 1.0f);
  } else if (e > 1e-12f) {
    t = std::clamp(f / e, 0.0f, 1.0f);
  }
  c1 = p1 + d1 * s;
  c2 = p2 + d2 * t;
}

// A collider at the end of a step. Sphere / capsule: the segment a..b with radius r. Box (T-183 round 3, world
// space): the core lo..hi with radius r (the box shrunk by its edge rounding and grown again); a = b = its centre.
// A box on a prop is oriented: lo..hi in the frame (org, rot); points are taken into that frame and back.
struct Shape {
  vec3 a, b;
  float r;
  bool box = false;
  vec3 lo{0}, hi{0};
  bool off = false;       // an external collider without its frame (no callback): not there
  bool oriented = false;  // box in the frame (org, rot) instead of world axes
  vec3 org{0};
  mat3 rot{1};
};
inline vec3 nearestOn(const Shape& sh, vec3 p) {
  if (!sh.box) return closestOnSegment(p, sh.a, sh.b);
  if (!sh.oriented) return glm::clamp(p, sh.lo, sh.hi);
  return sh.org + sh.rot * glm::clamp(glm::transpose(sh.rot) * (p - sh.org), sh.lo, sh.hi);
}
// Closest points of the segment [p1, q1] (c1, at parameter s) and the shape's core (c2). Box: the distance to a
// convex core is a convex function of s, so a ternary search over s finds it (40 fixed steps: deterministic).
inline void nearestSeg(vec3 p1, vec3 q1, const Shape& sh, float& s, vec3& c1, vec3& c2) {
  if (!sh.box) {
    closestSegments(p1, q1, sh.a, sh.b, s, c1, c2);
    return;
  }
  if (sh.oriented) {  // the same search in the box's own frame
    const mat3 inv = glm::transpose(sh.rot);
    p1 = inv * (p1 - sh.org);
    q1 = inv * (q1 - sh.org);
  }
  float s0 = 0, s1 = 1;
  const auto d2 = [&](float t) {
    const vec3 x = glm::mix(p1, q1, t);
    return glm::distance2(x, glm::clamp(x, sh.lo, sh.hi));
  };
  for (int i = 0; i < 40; ++i) {
    const float m0 = s0 + (s1 - s0) / 3.0f, m1 = s1 - (s1 - s0) / 3.0f;
    if (d2(m0) <= d2(m1)) s1 = m1;
    else s0 = m0;
  }
  s = 0.5f * (s0 + s1);
  c1 = glm::mix(p1, q1, s);
  c2 = glm::clamp(c1, sh.lo, sh.hi);
  if (sh.oriented) {
    c1 = sh.org + sh.rot * c1;
    c2 = sh.org + sh.rot * c2;
  }
}

// One "colliders" entry of a package block or of a scene override.
Result<DynamicsCollider> readCollider(const Json& c, const std::string& context) {
  DynamicsCollider d;
  if (!c.is_object()) return fail(context + ": a collider must be an object");
  d.name = c.value("name", "");
  d.bone = c.value("bone", "");
  // T-183 round 3 (scene override only): the bone belongs to another scene character, or the shape rides on a prop
  d.character = c.value("character", "");
  d.prop = c.value("prop", "");
  if (!d.character.empty() && !d.prop.empty()) return fail(context + ": collider '" + d.name + "' names a character and a prop");
  if (!d.prop.empty() && !d.bone.empty()) return fail(context + ": collider '" + d.name + "' on a prop takes no bone");
  const std::string type = c.value("type", "sphere");
  if (type == "sphere") {
    d.kind = DynamicsCollider::Kind::Sphere;
    d.a = d.b = readVec3(c, "centre", vec3(0));
  } else if (type == "capsule") {
    d.kind = DynamicsCollider::Kind::Capsule;
    d.a = readVec3(c, "a", vec3(0));
    d.b = readVec3(c, "b", vec3(0));
  } else if (type == "box") {
    // T-183 round 3: a box of the scene (table top, seat, floor) in world space; "radius" = rounding of its edges
    d.kind = DynamicsCollider::Kind::Box;
    d.a = readVec3(c, "min", vec3(0));
    d.b = readVec3(c, "max", vec3(0));
    d.radius = 0.01f;
    if (!d.character.empty()) return fail(context + ": box collider '" + d.name + "' cannot ride on a character's bone");
    if (d.name.empty() || c.value("space", d.prop.empty() ? "" : "prop") != (d.prop.empty() ? "world" : "prop") || !d.bone.empty())
      return fail(context + ": a box collider needs a name and \"space\": \"world\" (no bone), or a \"prop\"");
    if (!(d.b.x > d.a.x && d.b.y > d.a.y && d.b.z > d.a.z)) return fail(context + ": box collider '" + d.name + "' needs min < max");
  } else {
    return fail(context + ": collider '" + d.name + "' has unknown type " + type);
  }
  d.radius = readFloat(c, "radius", d.radius);
  if (d.name.empty() || (d.bone.empty() && d.prop.empty() && d.kind != DynamicsCollider::Kind::Box) || !(d.radius > 0))
    return fail(context + ": a collider needs name, bone and radius > 0");
  return d;
}

Result<void> readContact(const Json& c, SpringChain& ch, const std::string& where) {
  auto it = c.find("contact");
  if (it == c.end() || it->is_null()) return {};
  if (!it->is_object()) return fail(where + ": contact must be an object");
  for (auto& [key, _] : it->items())
    if (key != "solid" && key != "segments" && key != "anchored_gravity" && key != "radii" && key != "rest" && key != "friction" && key != "max_swing" && key != "locks" && key != "carry")
      return fail(where + ": contact has unknown key " + key);
  ch.contact.set = true;
  if (auto so = it->find("solid"); so != it->end()) {
    if (!so->is_array()) return fail(where + ": contact.solid must be a list of collider names");
    for (const Json& n : *so) {
      if (!n.is_string()) return fail(where + ": contact.solid must be a list of collider names");
      ch.contact.solid.push_back(n.get<std::string>());
    }
  }
  ch.contact.segments = readBool(*it, "segments", false);
  ch.contact.anchoredGravity = readBool(*it, "anchored_gravity", false);
  if (auto ra = it->find("radii"); ra != it->end()) {
    if (!ra->is_array() || ra->empty()) return fail(where + ": contact.radii must be a list of numbers, one per joint");
    for (const Json& r : *ra) {
      if (!r.is_number() || r.get<float>() < 0) return fail(where + ": contact.radii must be a list of numbers >= 0");
      ch.contact.radii.push_back(r.get<float>());
    }
  }
  ch.contact.rest = readBool(*it, "rest", false);
  if (auto fr = it->find("friction"); fr != it->end()) {
    if (!fr->is_number() || fr->get<float>() < 0) return fail(where + ": contact.friction must be a number >= 0");
    ch.contact.friction = fr->get<float>();
  }
  if (auto ms = it->find("max_swing"); ms != it->end()) {
    if (!ms->is_number() || ms->get<float>() < 0) return fail(where + ": contact.max_swing must be a number >= 0");
    ch.contact.maxSwing = ms->get<float>();
  }
  ch.contact.carry = readBool(*it, "carry", false);
  if (auto lk = it->find("locks"); lk != it->end()) {
    if (!lk->is_number() || lk->get<float>() < 0 || lk->get<float>() > 1) return fail(where + ": contact.locks must be a number in [0, 1]");
    ch.contact.locks = lk->get<float>();
  }
  return {};
}

// Shortest-arc rotation taking unit vector a to unit vector b. The angle is atan2(|a x b|, a . b), exact to float
// precision at every angle (T-101: acos(a . b) near 1, and the old identity cut-off at a . b > 1 - 1e-7, lost up to
// ~4.5e-4 rad, which write() turned into joint gaps of 0.01-0.04 mm on 3-8 cm chain segments).
quat arc(vec3 a, vec3 b) {
  const float d = glm::dot(a, b);
  vec3 axis = glm::cross(a, b);
  const float s = glm::length(axis);
  if (s < 1e-9f) {
    if (d > 0) return quat(1, 0, 0, 0);  // parallel
    axis = glm::cross(a, std::abs(a.x) < 0.9f ? vec3(1, 0, 0) : vec3(0, 1, 0));  // opposite: any perpendicular axis
    return glm::angleAxis(kArcPi, glm::normalize(axis));
  }
  return glm::angleAxis(std::atan2(s, d), axis / s);
}

Result<void> readPresets(const Json& j, std::map<std::string, SpringParams>& out, const std::string& where) {
  auto it = j.find("presets");
  if (it == j.end()) return {};
  if (!it->is_object()) return fail(where + ": presets must be an object");
  for (auto& [name, pj] : it->items()) {
    if (!pj.is_object()) return fail(where + ": preset " + name + " must be an object");
    SpringParams p;
    if (auto b = builtinSpringPresets().find(name); b != builtinSpringPresets().end()) p = b->second;
    if (auto o = out.find(name); o != out.end()) p = o->second;
    readParams(pj, p);
    if (auto r = checkParams(p, "preset " + name); !r) return r;
    out[name] = p;
  }
  return {};
}

const SpringParams* findPreset(const DynamicsSpec& s, const std::string& name) {
  if (auto it = s.presets.find(name); it != s.presets.end()) return &it->second;
  if (auto it = builtinSpringPresets().find(name); it != builtinSpringPresets().end()) return &it->second;
  return nullptr;
}

}  // namespace

const std::map<std::string, SpringParams>& builtinSpringPresets() {
  // stiffness 1/s^2, stiffness_tip, damping 1/s, gravity x g, drag 1/s, limit_deg, radius m
  static const std::map<std::string, SpringParams> presets = {
      {"drawstring", {25.0f, 15.0f, 3.0f, 1.0f, 0.6f, 70.0f, 0.006f}},
      {"strap", {90.0f, 70.0f, 8.0f, 0.6f, 0.4f, 35.0f, 0.01f}},
      {"bow_tail", {40.0f, 25.0f, 4.0f, 0.8f, 1.2f, 55.0f, 0.008f}},
      {"tassel", {30.0f, 20.0f, 3.5f, 1.0f, 0.8f, 60.0f, 0.008f}},
  };
  return presets;
}

Result<void> resolveAccessoryChains(DynamicsSpec& spec, const Skeleton& sk) {
  std::vector<Json> entries = std::move(spec.attach);
  spec.attach.clear();
  for (const Json& e : entries) {
    if (!e.is_object()) return fail("dynamics attach: entries must be objects");
    SpringChain ch;
    ch.name = e.value("name", e.value("prefix", ""));
    ch.preset = e.value("preset", "");
    ch.group = e.value("group", ch.preset);
    if (ch.name.empty()) return fail("dynamics attach: an entry needs a name (or a prefix)");
    for (const auto& c : spec.chains)
      if (c.name == ch.name) return fail("dynamics attach: chain name " + ch.name + " is already used");
    if (auto it = e.find("bones"); it != e.end()) {
      if (!it->is_array()) return fail("dynamics attach " + ch.name + ": bones must be a list");
      for (const Json& b : *it) ch.bones.push_back(b.get<std::string>());
    } else if (auto pre = e.find("prefix"); pre != e.end() && pre->is_string()) {
      const std::string prefix = pre->get<std::string>();
      std::vector<std::pair<long, std::string>> found;
      for (const auto& b : sk.bones) {
        if (b.name.size() <= prefix.size() || b.name.compare(0, prefix.size(), prefix) != 0) continue;
        std::string rest = b.name.substr(prefix.size());
        if (rest[0] == '.' || rest[0] == '_' || rest[0] == '-') rest = rest.substr(1);
        if (rest.empty() || !std::all_of(rest.begin(), rest.end(), [](char ch) { return ch >= '0' && ch <= '9'; })) continue;
        found.push_back({std::stol(rest), b.name});
      }
      std::sort(found.begin(), found.end());
      for (auto& [_, n] : found) ch.bones.push_back(n);
      if (ch.bones.empty()) return fail("dynamics attach " + ch.name + ": no bones named " + prefix + "<number>");
    } else {
      return fail("dynamics attach " + ch.name + ": give bones or prefix");
    }
    std::vector<int> idx;
    for (const auto& n : ch.bones) {
      const int b = sk.find(n);
      if (b < 0) return fail("dynamics attach " + ch.name + ": bone " + n + " not in the skeleton");
      idx.push_back(b);
    }
    if (e.contains("tip")) {
      ch.tip = readVec3(e, "tip", vec3(0));
    } else if (idx.size() >= 2) {
      const vec3 a = sk.bones[size_t(idx[idx.size() - 2])].head, b = sk.bones[size_t(idx.back())].head;
      ch.tip = b + (b - a);
    } else {
      const int parent = sk.bones[size_t(idx[0])].parent;
      const vec3 h = sk.bones[size_t(idx[0])].head;
      vec3 dir = parent >= 0 ? h - sk.bones[size_t(parent)].head : vec3(0, -1, 0);
      if (glm::length2(dir) < 1e-12f) dir = vec3(0, -1, 0);
      ch.tip = h + glm::normalize(dir) * 0.03f;
    }
    ch.params = SpringParams{};
    if (!ch.preset.empty()) {
      const SpringParams* p = findPreset(spec, ch.preset);
      if (!p) return fail("dynamics attach " + ch.name + ": unknown preset " + ch.preset);
      ch.params = *p;
    }
    readParams(e, ch.params);
    if (auto r = checkParams(ch.params, "attach " + ch.name); !r) return r;
    for (const Json& n : e.value("colliders", Json::array())) ch.colliders.push_back(n.get<std::string>());
    if (auto a = e.find("anchor"); a != e.end() && a->is_object()) {
      ch.anchorBone = a->value("bone", "");
      for (const Json& w : a->value("weights", Json::array())) ch.anchorWeights.push_back(w.get<float>());
      if (ch.anchorBone.empty() || ch.anchorWeights.size() != ch.bones.size() + 1)
        return fail("dynamics attach " + ch.name + ": anchor needs a bone and one weight per joint");
    }
    if (auto r = readContact(e, ch, "dynamics attach " + ch.name); !r) return r;
    spec.chains.push_back(std::move(ch));
  }
  return {};
}

Result<DynamicsSpec> dynamicsFromJson(const Json& j) {
  DynamicsSpec s;
  if (j.is_null()) return s;
  if (!j.is_object()) return fail("dynamics: block must be an object");
  s.enabled = readBool(j, "enabled", true);
  s.substepHz = readFloat(j, "substep_hz", s.substepHz);
  s.prerollSec = readFloat(j, "preroll_s", s.prerollSec);
  if (!(s.substepHz >= 24 && s.substepHz <= 10000) || !(s.prerollSec >= 0 && s.prerollSec <= 60))
    return fail("dynamics: substep_hz must be in [24, 10000] and preroll_s in [0, 60]");
  for (const Json& c : j.value("colliders", Json::array())) {
    auto d = readCollider(c, "dynamics");
    if (!d) return fail(d.error().message);
    s.colliders.push_back(*d);
  }
  SpringParams defaults;
  if (auto it = j.find("defaults"); it != j.end() && it->is_object()) readParams(*it, defaults);
  if (auto r = readPresets(j, s.presets, "dynamics"); !r) return std::unexpected(r.error());
  if (auto it = j.find("attach"); it != j.end()) {
    if (!it->is_array()) return fail("dynamics: attach must be a list");
    for (const Json& a : *it) s.attach.push_back(a);
  }
  for (const Json& c : j.value("chains", Json::array())) {
    SpringChain ch;
    ch.name = c.value("name", "");
    ch.group = c.value("group", "");
    ch.preset = c.value("preset", "");
    for (const Json& b : c.value("bones", Json::array())) ch.bones.push_back(b.get<std::string>());
    ch.tip = readVec3(c, "tip", vec3(0));
    ch.params = defaults;
    if (!ch.preset.empty()) {
      const SpringParams* p = findPreset(s, ch.preset);
      if (!p) return fail("dynamics: chain " + ch.name + ": unknown preset " + ch.preset);
      ch.params = *p;
    }
    readParams(c, ch.params);
    for (const Json& n : c.value("colliders", Json::array())) ch.colliders.push_back(n.get<std::string>());
    if (auto a = c.find("anchor"); a != c.end() && a->is_object()) {
      ch.anchorBone = a->value("bone", "");
      for (const Json& w : a->value("weights", Json::array())) ch.anchorWeights.push_back(w.get<float>());
      if (ch.anchorBone.empty() || ch.anchorWeights.size() != ch.bones.size() + 1)
        return fail("dynamics: chain " + ch.name + ": anchor needs a bone and one weight per joint");
      for (float w : ch.anchorWeights)
        if (!(w >= 0 && w <= 1)) return fail("dynamics: chain " + ch.name + ": anchor weights must be in [0, 1]");
    }
    if (ch.name.empty() || ch.bones.empty()) return fail("dynamics: a chain needs a name and at least one bone");
    if (auto r = checkParams(ch.params, "chain " + ch.name); !r) return std::unexpected(r.error());
    if (auto r = readContact(c, ch, "dynamics: chain " + ch.name); !r) return std::unexpected(r.error());
    s.chains.push_back(std::move(ch));
  }
  return s;
}

Json dynamicsToJson(const DynamicsSpec& s) {
  Json j{{"enabled", s.enabled}, {"substep_hz", s.substepHz}, {"preroll_s", s.prerollSec}};
  Json cols = Json::array(), chains = Json::array();
  for (const auto& c : s.colliders) {
    Json cj{{"name", c.name}, {"bone", c.bone}, {"radius", c.radius}};
    if (c.kind == DynamicsCollider::Kind::Sphere) cj.update({{"type", "sphere"}, {"centre", v3(c.a)}});
    else if (c.kind == DynamicsCollider::Kind::Capsule) cj.update({{"type", "capsule"}, {"a", v3(c.a)}, {"b", v3(c.b)}});
    else cj = Json{{"name", c.name}, {"type", "box"}, {"space", "world"}, {"min", v3(c.a)}, {"max", v3(c.b)}, {"radius", c.radius}};
    if (!c.character.empty()) cj["character"] = c.character;
    if (!c.prop.empty()) {
      cj["prop"] = c.prop;
      cj.erase("bone");
      if (c.kind == DynamicsCollider::Kind::Box) cj["space"] = "prop";
    }
    cols.push_back(cj);
  }
  for (const auto& c : s.chains) {
    Json cj = paramsToJson(c.params);
    cj.update({{"name", c.name}, {"group", c.group}, {"bones", c.bones}, {"tip", v3(c.tip)}, {"colliders", c.colliders}});
    if (!c.preset.empty()) cj["preset"] = c.preset;
    if (!c.anchorBone.empty()) cj["anchor"] = {{"bone", c.anchorBone}, {"weights", c.anchorWeights}};
    if (c.contact.set) {
      cj["contact"] = {{"solid", c.contact.solid}, {"segments", c.contact.segments}, {"anchored_gravity", c.contact.anchoredGravity}};
      if (!c.contact.radii.empty()) cj["contact"]["radii"] = c.contact.radii;
      if (c.contact.rest) {
        cj["contact"]["rest"] = true;
        cj["contact"]["friction"] = c.contact.friction;
        cj["contact"]["max_swing"] = c.contact.maxSwing;
      }
      if (c.contact.locks > 0) cj["contact"]["locks"] = c.contact.locks;
      if (c.contact.carry) cj["contact"]["carry"] = true;
    }
    chains.push_back(cj);
  }
  j["colliders"] = cols;
  j["chains"] = chains;
  if (!s.presets.empty()) {
    Json pj = Json::object();
    for (const auto& [name, p] : s.presets) pj[name] = paramsToJson(p);
    j["presets"] = pj;
  }
  if (!s.attach.empty()) j["attach"] = s.attach;
  return j;
}

Result<void> applyDynamicsOverride(DynamicsSpec& s, const Json& o) {
  if (o.is_null()) return {};
  if (o.is_boolean()) {
    s.enabled = s.enabled && o.get<bool>();  // true cannot switch on a character without chains
    return {};
  }
  if (!o.is_object()) return fail("scene dynamics override must be a boolean or an object");
  if (auto r = readPresets(o, s.presets, "scene dynamics override"); !r) return r;
  if (auto it = o.find("attach"); it != o.end()) {  // accessory chains: switch the layer on (unless "enabled": false)
    if (!it->is_array()) return fail("scene dynamics override: attach must be a list");
    for (const Json& a : *it) s.attach.push_back(a);
    if (!it->empty() && readBool(o, "enabled", true)) s.enabled = true;
  }
  if (o.contains("enabled")) s.enabled = s.enabled && readBool(o, "enabled", true);
  s.substepHz = readFloat(o, "substep_hz", s.substepHz);
  s.prerollSec = readFloat(o, "preroll_s", s.prerollSec);
  if (!(s.substepHz >= 24 && s.substepHz <= 10000) || !(s.prerollSec >= 0 && s.prerollSec <= 60))
    return fail("scene dynamics override: substep_hz must be in [24, 10000] and preroll_s in [0, 60]");
  if (auto it = o.find("colliders"); it != o.end()) {
    // T-183 round 3: colliders of the scene (world-space boxes: a table top, a seat) or more colliders on bones.
    // A new collider joins every chain, also chains that name their colliders.
    if (!it->is_array()) return fail("scene dynamics override: colliders must be a list");
    for (const Json& c : *it) {
      auto d = readCollider(c, "scene dynamics override");
      if (!d) return fail(d.error().message);
      for (const auto& have : s.colliders)
        if (have.name == d->name) return fail("scene dynamics override: collider '" + d->name + "' exists already");
      for (auto& ch : s.chains)
        if (!ch.colliders.empty()) ch.colliders.push_back(d->name);
      s.colliders.push_back(*d);
    }
  }
  if (auto it = o.find("chains"); it != o.end()) {
    if (!it->is_object()) return fail("scene dynamics override: chains must be an object");
    for (auto& [key, _] : it->items()) {
      bool used = key == "*";
      for (const auto& c : s.chains) used = used || c.name == key || c.group == key;
      if (!used) return fail("scene dynamics override: no chain or group named " + key);
    }
    for (auto& c : s.chains) {
      for (const std::string& key : {std::string("*"), c.group, c.name})
        if (!key.empty() && it->contains(key)) readParams((*it)[key], c.params);
      if (auto r = checkParams(c.params, "override of chain " + c.name); !r) return r;
    }
  }
  return {};
}

Result<std::shared_ptr<SpringChainSolver>> SpringChainSolver::create(const Skeleton& skeleton, const DynamicsSpec& spec,
                                                                     bool simulate) {
  auto s = std::make_shared<SpringChainSolver>();
  s->simulate_ = simulate;
  s->skeleton_ = skeleton;
  s->hz_ = spec.substepHz;
  s->preroll_ = spec.prerollSec;
  std::map<std::string, int> colliderIndex;
  for (const auto& c : spec.colliders) {
    if (!c.character.empty() || !c.prop.empty()) {
      // T-183 round 3: rides on another character's bone or on a prop; the scene resolves the names and gives the
      // frames per step. Entries with the same carrier share one frame.
      size_t e = 0;
      while (e < s->externals_.size() && !(s->externals_[e].character == c.character && s->externals_[e].bone == c.bone && s->externals_[e].prop == c.prop)) ++e;
      if (e == s->externals_.size()) s->externals_.push_back({c.character, c.bone, c.prop});
      colliderIndex[c.name] = int(s->colliders_.size());
      s->colliders_.push_back({c.kind, -1, c.a, c.b, vec3(0), c.radius, int(e)});
      continue;
    }
    if (c.kind == DynamicsCollider::Kind::Box) {  // world space: no bone; the core is the box less its edge rounding
      const vec3 half = 0.5f * (c.b - c.a);
      const float round = std::min(c.radius, std::min(half.x, std::min(half.y, half.z)));
      colliderIndex[c.name] = int(s->colliders_.size());
      s->colliders_.push_back({c.kind, -1, c.a + vec3(round), c.b - vec3(round), vec3(0), round});
      continue;
    }
    const int b = skeleton.find(c.bone);
    if (b < 0) return fail("dynamics: collider bone " + c.bone + " not in the skeleton");
    colliderIndex[c.name] = int(s->colliders_.size());
    s->colliders_.push_back({c.kind, b, c.a, c.b, skeleton.bones[size_t(b)].head, c.radius});
  }
  std::vector<bool> used(skeleton.bones.size(), false);
  for (const auto& sc : spec.chains) {
    Chain ch;
    ch.p = sc.params;
    for (size_t k = 0; k < sc.bones.size(); ++k) {
      const int b = skeleton.find(sc.bones[k]);
      if (b < 0) return fail("dynamics: chain " + sc.name + ": bone " + sc.bones[k] + " not in the skeleton");
      if (k > 0 && skeleton.bones[size_t(b)].parent != ch.bones.back())
        return fail("dynamics: chain " + sc.name + ": " + sc.bones[k] + " is not the child of the previous bone");
      if (used[size_t(b)]) return fail("dynamics: bone " + sc.bones[k] + " is in more than one chain");
      if (skeleton.bones[size_t(b)].parent < 0) return fail("dynamics: chain " + sc.name + " starts at a root bone");
      used[size_t(b)] = true;
      ch.bones.push_back(b);
      ch.rest.push_back(skeleton.bones[size_t(b)].head);
    }
    ch.rest.push_back(sc.tip);
    for (size_t k = 0; k + 1 < ch.rest.size(); ++k) {
      ch.length.push_back(glm::distance(ch.rest[k], ch.rest[k + 1]));
      if (ch.length.back() < 1e-5f) return fail("dynamics: chain " + sc.name + " has a zero-length segment");
    }
    if (!sc.anchorBone.empty()) {
      ch.anchor = skeleton.find(sc.anchorBone);
      if (ch.anchor < 0) return fail("dynamics: chain " + sc.name + ": anchor bone " + sc.anchorBone + " not in the skeleton");
      if (sc.anchorWeights.size() != ch.rest.size()) return fail("dynamics: chain " + sc.name + ": one anchor weight per joint");
      ch.anchorW = sc.anchorWeights;
    }
    if (sc.colliders.empty()) {
      for (size_t k = 0; k < s->colliders_.size(); ++k) ch.colliders.push_back(int(k));
    } else {
      for (const auto& n : sc.colliders) {
        auto it = colliderIndex.find(n);
        if (it == colliderIndex.end()) return fail("dynamics: chain " + sc.name + " names unknown collider " + n);
        ch.colliders.push_back(it->second);
      }
    }
    if (sc.contact.set) {  // T-183 contact: solid colliders join the chain's colliders
      ch.segments = sc.contact.segments;
      ch.anchoredGravity = sc.contact.anchoredGravity;
      for (const auto& n : sc.contact.solid) {
        auto it = colliderIndex.find(n);
        if (it == colliderIndex.end()) return fail("dynamics: chain " + sc.name + ": contact.solid names unknown collider " + n);
        if (std::find(ch.colliders.begin(), ch.colliders.end(), it->second) == ch.colliders.end()) ch.colliders.push_back(it->second);
      }
      if (!sc.contact.solid.empty()) {
        ch.solid.assign(ch.colliders.size(), 0);
        for (const auto& n : sc.contact.solid)
          ch.solid[size_t(std::find(ch.colliders.begin(), ch.colliders.end(), colliderIndex[n]) - ch.colliders.begin())] = 1;
      }
      if (!sc.contact.radii.empty()) {
        if (sc.contact.radii.size() != ch.rest.size()) return fail("dynamics: chain " + sc.name + ": contact.radii needs one radius per joint");
        ch.radii = sc.contact.radii;
      }
      ch.locks = sc.contact.locks;
      if (sc.contact.rest) {  // resting contact: every collider of the chain is solid
        ch.restContact = true;
        ch.friction = sc.contact.friction;
        ch.maxSwing = sc.contact.maxSwing;
        ch.carry = sc.contact.carry;
        ch.solid.assign(ch.colliders.size(), 1);
        s->keepShapes_ = true;
      }
    }
    s->offset_.push_back(s->joints_);
    s->joints_ += ch.rest.size();
    s->chains_.push_back(std::move(ch));
  }
  return s;
}

void SpringChainSolver::reset() const {
  std::lock_guard lock(mutex_);
  checkpoints_.clear();
}

// Kinematic joint positions: the root pivot, then each segment end carried by the bone it belongs to.
void SpringChainSolver::targets(const std::vector<mat4>& g, std::vector<vec3>& xk) const {
  xk.resize(joints_);
  for (size_t c = 0; c < chains_.size(); ++c) {
    const Chain& ch = chains_[c];
    const size_t o = offset_[c];
    xk[o] = vec3(g[size_t(ch.bones[0])][3]);
    for (size_t k = 1; k < ch.rest.size(); ++k) {
      const size_t b = size_t(ch.bones[k - 1]);
      xk[o + k] = vec3(g[b] * vec4(ch.rest[k] - skeleton_.bones[b].head, 1.0f));
      if (ch.anchor >= 0 && ch.anchorW[k] > 0) {
        const size_t a = size_t(ch.anchor);
        const vec3 anchored = vec3(g[a] * vec4(ch.rest[k] - skeleton_.bones[a].head, 1.0f));
        xk[o + k] = glm::mix(xk[o + k], anchored, ch.anchorW[k]);
      }
    }
  }
}

void SpringChainSolver::step(State& s, double dtd, const std::vector<mat4>& g, const std::vector<mat4>& ext) const {
  const float dt = float(dtd);
  std::vector<vec3> xk;
  targets(g, xk);
  if (keepShapes_ && s.hit.size() != joints_) s.hit.assign(joints_, 0);
  // Collider shapes at the end of the step.
  std::vector<Shape> shapes;
  for (const Collider& c : colliders_) {
    if (c.ext >= 0) {
      // external (T-183 round 3): in the frame the scene gave for this step. A prop may carry a scale: the frame is
      // split into its axes and their lengths; a box is scaled per axis, a sphere / capsule radius by the largest.
      if (size_t(c.ext) >= ext.size()) {
        shapes.push_back({vec3(0), vec3(0), 0.0f, false, vec3(0), vec3(0), true});
        continue;
      }
      const mat4& E = ext[size_t(c.ext)];
      if (c.kind != DynamicsCollider::Kind::Box) {
        const float sc = std::max(glm::length(vec3(E[0])), std::max(glm::length(vec3(E[1])), glm::length(vec3(E[2]))));
        shapes.push_back({vec3(E * vec4(c.a, 1)), vec3(E * vec4(c.b, 1)), c.radius * sc});
        continue;
      }
      const vec3 len(glm::length(vec3(E[0])), glm::length(vec3(E[1])), glm::length(vec3(E[2])));
      Shape sh{vec3(0), vec3(0), 0.0f, true};
      sh.oriented = true;
      sh.org = vec3(E[3]);
      sh.rot = mat3(vec3(E[0]) / std::max(len.x, 1e-9f), vec3(E[1]) / std::max(len.y, 1e-9f), vec3(E[2]) / std::max(len.z, 1e-9f));
      const vec3 lo = c.a * len, hi = c.b * len, half = 0.5f * (hi - lo);
      sh.r = std::min(c.radius, std::min(half.x, std::min(half.y, half.z)));
      sh.lo = lo + vec3(sh.r);
      sh.hi = hi - vec3(sh.r);
      sh.a = sh.b = sh.org + sh.rot * (0.5f * (lo + hi));
      shapes.push_back(sh);
      continue;
    }
    if (c.kind == DynamicsCollider::Kind::Box) {
      const vec3 centre = 0.5f * (c.a + c.b);
      shapes.push_back({centre, centre, c.radius, true, c.a, c.b});
      continue;
    }
    const mat4 S = g[size_t(c.bone)] * glm::translate(mat4(1), -c.head);
    shapes.push_back({vec3(S * vec4(c.a, 1)), vec3(S * vec4(c.b, 1)), c.radius});
  }
  // contact.rest: the velocity of collider ci at point q of its axis, from where the collider was at the last step
  const bool moving = keepShapes_ && s.ca.size() == shapes.size() && dt > 0;
  const auto colliderVelocity = [&](size_t ci, vec3 q) {
    if (!moving) return vec3(0);
    const Shape& sh = shapes[ci];
    const vec3 ab = sh.b - sh.a;
    const float l2 = glm::dot(ab, ab);
    const float t = l2 > 1e-12f ? std::clamp(glm::dot(q - sh.a, ab) / l2, 0.0f, 1.0f) : 0.0f;
    return (glm::mix(sh.a, sh.b, t) - glm::mix(s.ca[ci], s.cb[ci], t)) / dt;
  };
  struct Hit {
    vec3 n{0}, vc{0};
    bool on = false;
  };
  const vec3 down(0, -1, 0);
  for (size_t c = 0; c < chains_.size(); ++c) {
    const Chain& ch = chains_[c];
    const size_t o = offset_[c], n = ch.rest.size();
    // Gravity relative to the rest shape: zero while the chain's root bone keeps its rest orientation.
    const mat3 R = mat3(g[size_t(ch.bones[0])]);
    const vec3 gEff = ch.p.gravity * 9.81f * (down - R * down);
    std::vector<vec3> p(n);
    // contact chains (T-183): a collider push is inelastic. A pushed joint keeps at most the speed it had before the
    // push or the speed of its kinematic target, so the push moves it out without throwing it off the collider.
    const bool contact = ch.segments || !ch.solid.empty();
    std::vector<float> speedCap(contact ? n : 0, 0.0f);
    std::vector<char> touched(contact ? n : 0, 0);
    std::vector<Hit> hits(ch.restContact ? n : 0);
    const float segMin = kSegmentMinParam;
    p[0] = xk[o];
    for (size_t k = 1; k < n; ++k) {
      const size_t i = o + k;
      const float t = n > 2 ? float(k - 1) / float(n - 2) : 0.0f;
      const float stiff = ch.p.stiffnessTip >= 0 ? ch.p.stiffness + (ch.p.stiffnessTip - ch.p.stiffness) * t : ch.p.stiffness;
      const vec3 vk = (xk[i] - s.xk[i]) / dt;
      // contact.anchored_gravity: a joint whose target the anchor bone carries already hangs where that bone puts it
      const vec3 gk = ch.anchoredGravity && ch.anchor >= 0 ? gEff * (1.0f - ch.anchorW[k]) : gEff;
      const vec3 a = stiff * (xk[i] - s.x[i]) + ch.p.damping * (vk - s.v[i]) - ch.p.drag * s.v[i] + gk;
      const vec3 v = s.v[i] + a * dt;
      p[k] = s.x[i] + v * dt;
      if (contact) speedCap[k] = std::max(glm::length(v), glm::length(vk));
    }
    // The chain's colliders for this step. contact.rest chains may carry hundreds of small colliders that follow a
    // surface: only those near the chain are tested (a sphere around the chain, 5 cm of room for pushes).
    std::vector<size_t> active;
    active.reserve(ch.colliders.size());
    if (ch.restContact) {
      vec3 mid(0);
      for (size_t k = 0; k < n; ++k) mid += p[k];
      mid /= float(n);
      float bound = 0;
      for (size_t k = 0; k < n; ++k)
        bound = std::max(bound, std::max(glm::distance(p[k], mid), glm::distance(xk[o + k], mid)) + (ch.radii.empty() ? ch.p.radius : ch.radii[k]));
      bound += 0.05f;
      for (size_t cn = 0; cn < ch.colliders.size(); ++cn) {
        const Shape& sh = shapes[size_t(ch.colliders[cn])];
        if (!sh.off && glm::distance(mid, nearestOn(sh, mid)) - sh.r <= bound) active.push_back(cn);
      }
    } else {
      for (size_t cn = 0; cn < ch.colliders.size(); ++cn)
        if (!shapes[size_t(ch.colliders[cn])].off) active.push_back(cn);
    }
    const float cosLimit = std::cos(glm::radians(ch.p.limitDeg));
    for (int iter = 0; iter < 2; ++iter) {
      for (size_t k = 1; k < n; ++k) {
        // segment length
        vec3 d = p[k] - p[k - 1];
        const vec3 dk = glm::normalize(xk[o + k] - xk[o + k - 1]);
        float len = glm::length(d);
        vec3 dir = len > 1e-9f ? d / len : dk;
        // angular limit around the kinematic direction
        if (ch.p.limitDeg < 180.0f && glm::dot(dir, dk) < cosLimit) {
          float limit = glm::radians(ch.p.limitDeg);
          bool clamp = true;
          if (ch.restContact) {
            // contact.rest: the limit yields to contact. A collider may hold a joint beyond the limit (the push
            // comes after the clamp); clamping it back every step makes clamp and push alternate, and the joint
            // slides round the limit cone to its far side within a frame or two. So a joint that a collider pushed
            // (this step or the last) is not clamped, and once it is free its limit shrinks from the angle it had to
            // the chain's limit at kLimitReturn, so it comes back steadily instead of jumping.
            if (hits[k].on || (o + k < s.hit.size() && s.hit[o + k])) {
              clamp = false;
            } else {
              const vec3 was = s.x[o + k] - s.x[o + k - 1], kWas = s.xk[o + k] - s.xk[o + k - 1];
              if (glm::length(was) > 1e-9f && glm::length(kWas) > 1e-9f) {
                const vec3 a = glm::normalize(was), b = glm::normalize(kWas);
                const float before = std::atan2(glm::length(glm::cross(a, b)), glm::dot(a, b));
                if (before > limit) limit += (before - limit) * std::exp(-kLimitReturn * dt);
              }
              clamp = glm::dot(dir, dk) < std::cos(limit);
            }
          }
          if (clamp) {
            const vec3 axis = glm::cross(dk, dir);
            if (glm::length(axis) > 1e-7f) dir = glm::angleAxis(limit, glm::normalize(axis)) * dk;
            else dir = dk;
          }
        }
        p[k] = p[k - 1] + dir * ch.length[k - 1];
        // colliders: never closer than the radius, nor than the kinematic joint itself is (so a rest shape that
        // touches a collider is not pushed away). A push moves the joint off its segment length, and write() places
        // each bone rigidly from x[k] towards x[k+1], so a length error would open a gap at the next joint (T-101:
        // a connected bone in Blender cannot reproduce it). After a push the segment length is restored (the joint
        // swings around p[k-1]); push and length alternate until the joint is outside every collider, and the
        // length is always restored last. A joint that touches no collider takes the same path as before.
        for (int pass = 0; pass < kColliderPasses; ++pass) {
          bool pushed = false;
          if (ch.locks > 0 && pass == 0) {
            // contact.locks: the joints of the other chains with the key keep this joint off by locks x (the two
            // radii), never by more than the two kinematic joints are apart. The chains are solved in their fixed
            // order: a chain solved earlier in this step is where it is now, a later one where it was at the last
            // step. One push of half the overlap per step, so two locks yield to each other evenly.
            const float rk = ch.radii.empty() ? ch.p.radius : ch.radii[k];
            for (size_t c2 = 0; c2 < chains_.size(); ++c2) {
              const Chain& other = chains_[c2];
              if (c2 == c || other.locks <= 0) continue;
              const size_t o2 = offset_[c2];
              for (size_t j = 1; j < other.rest.size(); ++j) {
                const float minD = std::min(ch.locks * (rk + (other.radii.empty() ? other.p.radius : other.radii[j])),
                                            glm::distance(xk[o + k], xk[o2 + j]));
                const vec3 off = p[k] - s.x[o2 + j];
                const float dist = glm::length(off);
                if (dist >= minD - kColliderTolerance) continue;
                const vec3 nrm = dist > 1e-7f ? off / dist : glm::normalize(xk[o + k] - xk[o2 + j] + vec3(0, 1e-6f, 0));
                p[k] += nrm * (0.5f * (minD - dist));
                pushed = true;
              }
            }
          }
          for (const size_t cn : active) {
            const Shape& sh = shapes[size_t(ch.colliders[cn])];
            const bool solid = !ch.solid.empty() && ch.solid[cn];  // contact.solid: no kinematic-target exemption
            const float want = sh.r + (ch.radii.empty() ? ch.p.radius : ch.radii[k]);
            const vec3 qk = nearestOn(sh, xk[o + k]);
            const float minD = solid ? want : std::min(want, glm::distance(xk[o + k], qk));
            const vec3 q = nearestOn(sh, p[k]);
            const vec3 off = p[k] - q;
            const float dist = glm::length(off);
            // after the first pass, a joint within the tolerance of the surface counts as outside
            if (dist >= minD - (pass > 0 ? kColliderTolerance : 0.0f)) continue;
            vec3 nrm = dist > 1e-7f ? off / dist : glm::normalize(xk[o + k] - qk + vec3(0, 1e-6f, 0));
            if (solid) {
              // a solid collider that moved past the joint within one step must not flip it to its far side: the
              // joint leaves on the side it was on at the previous step
              const vec3 prev = s.x[o + k] - nearestOn(sh, s.x[o + k]);
              const float lp = glm::length(prev);
              if (lp >= minD - kFlipSlack && dist < 0.5f * minD && glm::dot(prev, nrm) < 0) nrm = prev / lp;
            }
            p[k] = q + nrm * minD;
            pushed = true;
            if (ch.restContact) hits[k] = {nrm, colliderVelocity(size_t(ch.colliders[cn]), q), true};
          }
          if (ch.segments) {
            // contact.segments: the segment p[k-1]..p[k] is a capsule of the chain radius. Its closest point to the
            // collider is moved out by swinging joint k about p[k-1] (the joint moves 1/s of what the point at
            // parameter s needs; a contact next to p[k-1] is that joint's own test). The exemption for a rest shape
            // that touches a collider uses the kinematic segment, as the joint test uses the kinematic joint.
            for (const size_t cn : active) {
              const Shape& sh = shapes[size_t(ch.colliders[cn])];
              const bool solid = !ch.solid.empty() && ch.solid[cn];
              float sp = 0, sk = 0;
              vec3 c1, c2, k1, k2;
              if (ch.restContact) {
                // contact.rest: the segment's middle is tested (a fixed lever of 2 on joint k). The joints at both
                // ends are tested themselves, so what is left between them is the sag of a chord, 1-2 mm.
                sp = 0.5f;
                c1 = 0.5f * (p[k - 1] + p[k]);
                c2 = nearestOn(sh, c1);
              } else {
                nearestSeg(p[k - 1], p[k], sh, sp, c1, c2);
                if (!ch.radii.empty()) {
                  // contact.radii: a tapered capsule touches the collider nearer to its thick end than its axis
                  // does: by h m / sqrt(1 - m^2) along the axis (h = distance of the axis, m = radius change per length)
                  const float m = (ch.radii[k] - ch.radii[k - 1]) / ch.length[k - 1];
                  if (m != 0.0f && std::abs(m) < 0.95f) {
                    sp = std::clamp(sp + glm::distance(c1, c2) * m / (ch.length[k - 1] * std::sqrt(1.0f - m * m)), 0.0f, 1.0f);
                    c1 = glm::mix(p[k - 1], p[k], sp);
                    c2 = nearestOn(sh, c1);
                  }
                }
              }
              if (sp < segMin) {
                // a contact next to the first joint is that joint's own test; a tapered segment whose thick end is
                // there is tested at its middle instead (the joint's test does not cover the taper)
                if (ch.restContact || ch.radii.empty() || ch.radii[k - 1] <= ch.radii[k]) continue;
                sp = 0.5f;
                c1 = 0.5f * (p[k - 1] + p[k]);
                c2 = nearestOn(sh, c1);
              }
              // contact.radii: a tapered capsule, its radius at the contact
              const float want = sh.r + (ch.radii.empty() ? ch.p.radius : glm::mix(ch.radii[k - 1], ch.radii[k], sp));
              float minD = want;
              if (!solid) {
                nearestSeg(xk[o + k - 1], xk[o + k], sh, sk, k1, k2);
                minD = std::min(want, glm::distance(k1, k2));
              }
              const vec3 off = c1 - c2;
              const float dist = glm::length(off);
              if (dist >= minD - (pass > 0 ? kColliderTolerance : 0.0f)) continue;
              vec3 nrm = dist > 1e-7f ? off / dist : glm::normalize(xk[o + k] - c2 + vec3(0, 1e-6f, 0));
              float depth = minD - dist;
              if (solid) {  // as for joints: the segment leaves on the side it was on at the previous step
                float st = 0;
                vec3 a1, a2;
                if (ch.restContact) {
                  a1 = 0.5f * (s.x[o + k - 1] + s.x[o + k]);
                  a2 = nearestOn(sh, a1);
                } else {
                  nearestSeg(s.x[o + k - 1], s.x[o + k], sh, st, a1, a2);
                }
                const float lp = glm::length(a1 - a2);
                if (lp >= minD - kFlipSlack && dist < 0.5f * minD && glm::dot(a1 - a2, nrm) < 0) {
                  nrm = (a1 - a2) / lp;
                  depth = minD + dist;
                }
              }
              p[k] += nrm * (depth / sp);
              pushed = true;
              if (ch.restContact) hits[k] = {nrm, colliderVelocity(size_t(ch.colliders[cn]), c2), true};
            }
          }
          if (!pushed) break;
          if (contact) touched[k] = 1;
          const vec3 ds = p[k] - p[k - 1];
          const float ls = glm::length(ds);
          p[k] = p[k - 1] + (ls > 1e-9f ? ds / ls : dir) * ch.length[k - 1];
        }
      }
    }
    if (ch.restContact && ch.maxSwing > 0) {
      // contact.rest: a segment turns at most max_swing (rad/s) faster than its kinematic direction does. A lock that
      // is squeezed between two colliders (a hand pressing it on the head) has no place outside both; without the
      // cap the projection jumps between far-apart places from step to step. With it the lock moves steadily.
      const float maxAngle = ch.maxSwing * dt;
      for (size_t k = 1; k < n; ++k) {
        const size_t i = o + k;
        const vec3 was = s.x[i] - s.x[i - 1], kWas = s.xk[i] - s.xk[i - 1], kNow = xk[i] - xk[i - 1], now = p[k] - p[k - 1];
        if (glm::length(was) < 1e-9f || glm::length(kWas) < 1e-9f || glm::length(kNow) < 1e-9f || glm::length(now) < 1e-9f) continue;
        const vec3 carried = glm::normalize(arc(glm::normalize(kWas), glm::normalize(kNow)) * glm::normalize(was));
        vec3 dir = glm::normalize(now);
        const float ang = std::atan2(glm::length(glm::cross(carried, dir)), glm::dot(carried, dir));
        // contact.carry: a collider that moves carries the joint it pushes: the cap yields by the collider's speed
        // relative to the joint's kinematic target (a forearm that sweeps a lock across the chest at 3 m/s takes it
        // along; held back by the cap, the lock is inside the arm or the chest for a frame). A slow or still collider
        // adds nothing, so a lock squeezed between two colliders at rest still moves steadily.
        const float cap = ch.carry && hits[k].on ? maxAngle + glm::length(hits[k].vc - (xk[i] - s.xk[i]) / dt) * dt / ch.length[k - 1] : maxAngle;
        if (ang > cap) {
          const vec3 axis = glm::cross(carried, dir);
          dir = glm::length(axis) > 1e-9f ? glm::angleAxis(cap, glm::normalize(axis)) * carried : carried;
        }
        p[k] = p[k - 1] + dir * ch.length[k - 1];
      }
    }
    for (size_t k = 0; k < n; ++k) {
      const size_t i = o + k;
      s.v[i] = (p[k] - s.x[i]) / dt;
      if (ch.restContact) {
        // resting contact: along the contact normal the joint moves with the collider (inelastic), and its sliding
        // speed on the collider decays by the friction
        if (i < s.hit.size()) s.hit[i] = hits[k].on ? 1 : 0;
        if (hits[k].on) {
          const vec3 rel = s.v[i] - hits[k].vc;
          const vec3 slide = rel - hits[k].n * glm::dot(rel, hits[k].n);
          s.v[i] = hits[k].vc + slide * std::exp(-ch.friction * dt);
        }
      } else if (contact && touched[k]) {
        const float sp = glm::length(s.v[i]);
        if (sp > speedCap[k] && sp > 1e-9f) s.v[i] *= speedCap[k] / sp;
      }
      s.x[i] = p[k];
    }
  }
  s.xk = std::move(xk);
  if (!externals_.empty()) s.ext = ext;
  if (keepShapes_) {
    s.ca.resize(shapes.size());
    s.cb.resize(shapes.size());
    for (size_t k = 0; k < shapes.size(); ++k) {
      s.ca[k] = shapes[k].a;
      s.cb[k] = shapes[k].b;
    }
  }
}

void SpringChainSolver::write(const State& s, std::vector<mat4>& globals) const {
  const std::vector<mat4> old = globals;
  std::vector<bool> moved(globals.size(), false), chainBone(globals.size(), false);
  for (size_t c = 0; c < chains_.size(); ++c) {
    const Chain& ch = chains_[c];
    const size_t o = offset_[c];
    for (size_t k = 0; k < ch.bones.size(); ++k) {
      const size_t b = size_t(ch.bones[k]);
      // the bone's own kinematic direction (an anchor may move the targets, not the bone's kinematic frame)
      const vec3 dk = mat3(old[b]) * (ch.rest[k + 1] - ch.rest[k]), ds = s.x[o + k + 1] - s.x[o + k];
      if (glm::length(dk) < 1e-9f || glm::length(ds) < 1e-9f) continue;
      const mat3 rot = mat3(arc(glm::normalize(dk), glm::normalize(ds))) * mat3(old[b]);
      mat4 m(rot);
      m[3] = vec4(s.x[o + k], 1.0f);
      globals[b] = m;
      moved[b] = chainBone[b] = true;
    }
  }
  // Non-chain descendants of moved bones follow rigidly.
  for (size_t b = 0; b < globals.size(); ++b) {
    const int p = skeleton_.bones[b].parent;
    if (chainBone[b] || p < 0 || !moved[size_t(p)]) continue;
    globals[b] = globals[size_t(p)] * glm::inverse(old[size_t(p)]) * old[b];
    moved[b] = true;
  }
}

void SpringChainSolver::apply(double frame, double frameStart, double fps, const Driver& kinematic,
                              std::vector<mat4>& globals, const External& external) const {
  if (chains_.empty()) return;
  if (!simulate_) {  // static: anchored targets, lengths kept; unanchored chains untouched
    State s;
    targets(globals, s.xk);
    s.x = s.xk;
    for (size_t c = 0; c < chains_.size(); ++c) {
      if (chains_[c].anchor < 0) continue;
      for (size_t k = 1; k < chains_[c].rest.size(); ++k) {
        const size_t i = offset_[c] + k;
        const vec3 d = s.x[i] - s.x[i - 1];
        s.x[i] = s.x[i - 1] + (glm::length(d) > 1e-9f ? glm::normalize(d) : vec3(0, -1, 0)) * chains_[c].length[k - 1];
      }
    }
    write(s, globals);
    return;
  }
  if (!(fps > 0) || frame < frameStart) return;
  std::lock_guard lock(mutex_);
  if (cacheStart_ != frameStart || cacheFps_ != fps) {
    checkpoints_.clear();
    cacheStart_ = frameStart;
    cacheFps_ = fps;
  }
  const double T = (frame - frameStart) / fps;
  const long long K = (long long)std::floor(T * hz_ + 1e-6);
  const double h = 1.0 / hz_;
  const auto frameAt = [&](long long k) { return frameStart + double(k) * h * fps; };
  // External collider frames at a scene frame (none without external colliders or without the callback).
  const bool ext = !externals_.empty() && external;
  const auto extAt = [&](double f) { return ext ? external(f) : std::vector<mat4>(); };
  // Resume from the latest valid checkpoint at or before K.
  State s;
  long long k0 = -1;
  while (!checkpoints_.empty()) {
    auto it = checkpoints_.upper_bound(K);
    if (it == checkpoints_.begin()) break;
    --it;
    std::vector<vec3> xk;
    targets(kinematic(frameAt(it->first)), xk);
    if (xk == it->second.xk && (!ext || extAt(frameAt(it->first)) == it->second.ext)) {
      s = it->second;
      k0 = it->first;
      break;
    }
    checkpoints_.clear();  // the driver changed: everything cached is stale
  }
  if (k0 < 0) {
    // Preroll: settle at the first frame's pose, then the state at step 0.
    const std::vector<mat4> g0 = kinematic(frameStart);
    targets(g0, s.xk);
    s.x = s.xk;
    s.v.assign(joints_, vec3(0));
    const long long pre = (long long)std::llround(preroll_ * hz_);
    const std::vector<mat4> e0 = extAt(frameStart);
    for (long long k = 0; k < pre; ++k) step(s, h, g0, e0);
    k0 = 0;
    checkpoints_[0] = s;
  }
  for (long long k = k0 + 1; k <= K; ++k) {
    step(s, h, kinematic(frameAt(k)), extAt(frameAt(k)));
    if (k % 16 == 0 || k == K) checkpoints_[k] = s;
  }
  const double rem = T - double(K) * h;
  if (rem > 1e-9) step(s, rem, globals, extAt(frame));  // partial step to the frame itself (not cached)
  write(s, globals);
}

}  // namespace plush
