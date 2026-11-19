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

vec3 closestOnSegment(vec3 p, vec3 a, vec3 b) {
  const vec3 ab = b - a;
  const float l2 = glm::dot(ab, ab);
  if (l2 < 1e-12f) return a;
  return a + ab * std::clamp(glm::dot(p - a, ab) / l2, 0.0f, 1.0f);
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
    DynamicsCollider d;
    d.name = c.value("name", "");
    d.bone = c.value("bone", "");
    const std::string type = c.value("type", "sphere");
    if (type == "sphere") {
      d.kind = DynamicsCollider::Kind::Sphere;
      d.a = d.b = readVec3(c, "centre", vec3(0));
    } else if (type == "capsule") {
      d.kind = DynamicsCollider::Kind::Capsule;
      d.a = readVec3(c, "a", vec3(0));
      d.b = readVec3(c, "b", vec3(0));
    } else {
      return fail("dynamics: collider '" + d.name + "' has unknown type " + type);
    }
    d.radius = readFloat(c, "radius", d.radius);
    if (d.name.empty() || d.bone.empty() || !(d.radius > 0)) return fail("dynamics: a collider needs name, bone and radius > 0");
    s.colliders.push_back(d);
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
    else cj.update({{"type", "capsule"}, {"a", v3(c.a)}, {"b", v3(c.b)}});
    cols.push_back(cj);
  }
  for (const auto& c : s.chains) {
    Json cj = paramsToJson(c.params);
    cj.update({{"name", c.name}, {"group", c.group}, {"bones", c.bones}, {"tip", v3(c.tip)}, {"colliders", c.colliders}});
    if (!c.preset.empty()) cj["preset"] = c.preset;
    if (!c.anchorBone.empty()) cj["anchor"] = {{"bone", c.anchorBone}, {"weights", c.anchorWeights}};
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

void SpringChainSolver::step(State& s, double dtd, const std::vector<mat4>& g) const {
  const float dt = float(dtd);
  std::vector<vec3> xk;
  targets(g, xk);
  // Collider shapes at the end of the step.
  struct Shape {
    vec3 a, b;
    float r;
  };
  std::vector<Shape> shapes;
  for (const Collider& c : colliders_) {
    const mat4 S = g[size_t(c.bone)] * glm::translate(mat4(1), -c.head);
    shapes.push_back({vec3(S * vec4(c.a, 1)), vec3(S * vec4(c.b, 1)), c.radius});
  }
  const vec3 down(0, -1, 0);
  for (size_t c = 0; c < chains_.size(); ++c) {
    const Chain& ch = chains_[c];
    const size_t o = offset_[c], n = ch.rest.size();
    // Gravity relative to the rest shape: zero while the chain's root bone keeps its rest orientation.
    const mat3 R = mat3(g[size_t(ch.bones[0])]);
    const vec3 gEff = ch.p.gravity * 9.81f * (down - R * down);
    std::vector<vec3> p(n);
    p[0] = xk[o];
    for (size_t k = 1; k < n; ++k) {
      const size_t i = o + k;
      const float t = n > 2 ? float(k - 1) / float(n - 2) : 0.0f;
      const float stiff = ch.p.stiffnessTip >= 0 ? ch.p.stiffness + (ch.p.stiffnessTip - ch.p.stiffness) * t : ch.p.stiffness;
      const vec3 vk = (xk[i] - s.xk[i]) / dt;
      const vec3 a = stiff * (xk[i] - s.x[i]) + ch.p.damping * (vk - s.v[i]) - ch.p.drag * s.v[i] + gEff;
      const vec3 v = s.v[i] + a * dt;
      p[k] = s.x[i] + v * dt;
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
          const vec3 axis = glm::cross(dk, dir);
          if (glm::length(axis) > 1e-7f) dir = glm::angleAxis(glm::radians(ch.p.limitDeg), glm::normalize(axis)) * dk;
          else dir = dk;
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
          for (int ci : ch.colliders) {
            const Shape& sh = shapes[size_t(ci)];
            const float want = sh.r + ch.p.radius;
            const vec3 qk = closestOnSegment(xk[o + k], sh.a, sh.b);
            const float minD = std::min(want, glm::distance(xk[o + k], qk));
            const vec3 q = closestOnSegment(p[k], sh.a, sh.b);
            const vec3 off = p[k] - q;
            const float dist = glm::length(off);
            // after the first pass, a joint within the tolerance of the surface counts as outside
            if (dist >= minD - (pass > 0 ? kColliderTolerance : 0.0f)) continue;
            const vec3 nrm = dist > 1e-7f ? off / dist : glm::normalize(xk[o + k] - qk + vec3(0, 1e-6f, 0));
            p[k] = q + nrm * minD;
            pushed = true;
          }
          if (!pushed) break;
          const vec3 ds = p[k] - p[k - 1];
          const float ls = glm::length(ds);
          p[k] = p[k - 1] + (ls > 1e-9f ? ds / ls : dir) * ch.length[k - 1];
        }
      }
    }
    for (size_t k = 0; k < n; ++k) {
      const size_t i = o + k;
      s.v[i] = (p[k] - s.x[i]) / dt;
      s.x[i] = p[k];
    }
  }
  s.xk = std::move(xk);
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
                              std::vector<mat4>& globals) const {
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
  // Resume from the latest valid checkpoint at or before K.
  State s;
  long long k0 = -1;
  while (!checkpoints_.empty()) {
    auto it = checkpoints_.upper_bound(K);
    if (it == checkpoints_.begin()) break;
    --it;
    std::vector<vec3> xk;
    targets(kinematic(frameAt(it->first)), xk);
    if (xk == it->second.xk) {
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
    for (long long k = 0; k < pre; ++k) step(s, h, g0);
    k0 = 0;
    checkpoints_[0] = s;
  }
  for (long long k = k0 + 1; k <= K; ++k) {
    step(s, h, kinematic(frameAt(k)));
    if (k % 16 == 0 || k == K) checkpoints_[k] = s;
  }
  const double rem = T - double(K) * h;
  if (rem > 1e-9) step(s, rem, globals);  // partial step to the frame itself (not cached)
  write(s, globals);
}

}  // namespace plush
