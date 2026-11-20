#include "anim/foot_lock.h"

#include <algorithm>
#include <cmath>

namespace plush {

namespace {
const quat kIdentity(1, 0, 0, 0);
bool isNumber(const Json& j) { return j.is_number(); }
quat mirrorQ(const quat& q) { return quat(q.w, q.x, -q.y, -q.z); }
std::string mirrorSide(const std::string& role) {
  if (role.size() > 2 && role[role.size() - 2] == '.') {
    std::string r = role;
    if (r.back() == 'L') r.back() = 'R';
    else if (r.back() == 'R') r.back() = 'L';
    return r;
  }
  return role;
}
// q = swing * twist, twist about +Y (the vertical of the reference space).
void swingTwistY(const quat& q, quat& swing, quat& twist) {
  const float n = std::sqrt(q.w * q.w + q.y * q.y);
  twist = n < 1e-6f ? kIdentity : quat(q.w / n, 0, q.y / n, 0);
  swing = glm::normalize(q * glm::inverse(twist));
}
double smooth01(double x) {
  x = std::clamp(x, 0.0, 1.0);
  return x * x * (3 - 2 * x);
}
}  // namespace

LocomotionStyle locomotionStyle(const Json& clip) {
  LocomotionStyle s;
  if (!clip.is_object()) return s;
  auto it = clip.find("style");
  if (it == clip.end() || !it->is_object()) return s;
  const Json& j = *it;
  s.enabled = true;
  auto num = [&](const char* k, double d) {
    auto v = j.find(k);
    return v != j.end() && isNumber(*v) ? v->get<double>() : d;
  };
  s.lean = float(std::clamp(num("lean", 1.0), 0.0, 2.0));
  s.stride = float(std::clamp(num("stride", 1.0), 0.0, 4.0));
  s.armSwing = float(std::clamp(num("arm_swing", 1.0), 0.0, 3.0));
  s.tempo = std::clamp(num("tempo", 1.0), 0.25, 4.0);
  s.footRelease = std::clamp(num("foot_release", 6.0), 0.0, 24.0);
  s.footEaseIn = std::clamp(num("foot_in", 2.0), 0.0, 24.0);
  s.footLead = std::clamp(num("foot_lead", 3.0), 0.0, 24.0);
  auto fl = j.find("foot_lock");
  s.footLock = fl != j.end() && fl->is_boolean() && fl->get<bool>();
  auto ac = j.find("arm_center");
  if (ac != j.end() && ac->is_object())
    for (auto e = ac->begin(); e != ac->end(); ++e) {
      const Json& v = e.value();
      if (!v.is_array() || v.size() != 4 || !std::all_of(v.begin(), v.end(), isNumber)) continue;
      const quat q(v[0].get<float>(), v[1].get<float>(), v[2].get<float>(), v[3].get<float>());
      if (glm::dot(q, q) > 1e-8f) s.armCenter[e.key()] = glm::normalize(q);
    }
  return s;
}

double locomotionTempo(const Json& clip) {
  if (!clip.is_object()) return 1.0;
  auto it = clip.find("style");
  if (it == clip.end() || !it->is_object()) return 1.0;
  auto v = it->find("tempo");
  return v != it->end() && v->is_number() ? std::clamp(v->get<double>(), 0.25, 4.0) : 1.0;
}

void applyLocomotionStyle(const LocomotionStyle& st, std::map<std::string, quat>& local, vec3& root, bool mirror) {
  if (!st.enabled) return;
  if (st.lean != 1.0f) {
    for (const char* role : {"hips", "spine", "chest", "neck"}) {
      auto it = local.find(role);
      if (it == local.end()) continue;
      quat swing, twist;
      swingTwistY(it->second, swing, twist);
      if (swing.w < 0) swing = -swing;
      const quat scaled = glm::normalize(glm::slerp(kIdentity, swing, st.lean) * twist);
      if (std::string(role) == "hips") {
        // The legs hang from the hips: keep their directions (R_thigh = R_hips * L_thigh stays what it was).
        const quat fix = glm::inverse(scaled) * it->second;
        for (const char* leg : {"thigh.L", "thigh.R"}) {
          auto t = local.find(leg);
          if (t != local.end()) t->second = glm::normalize(fix * t->second);
        }
      }
      it->second = scaled;
    }
  }
  if (st.armSwing != 1.0f)
    for (const auto& [role, center] : st.armCenter) {
      auto it = local.find(mirror ? mirrorSide(role) : role);
      if (it == local.end()) continue;
      quat c = mirror ? mirrorQ(center) : center;
      if (glm::dot(c, it->second) < 0) c = -c;
      // Extrapolates for arm_swing > 1 (glm::slerp is not clamped).
      it->second = glm::normalize(glm::slerp(c, it->second, st.armSwing));
    }
  root.x *= st.stride;
  root.z *= st.stride;
}

std::vector<FootPlant> footPlants(const Json& clip) {
  std::vector<FootPlant> out;
  if (!clip.is_object()) return out;
  auto it = clip.find("contacts");
  if (it == clip.end() || !it->is_array()) return out;
  for (const Json& c : *it) {
    if (!c.is_object() || c.value("type", std::string()) != "foot_plant") continue;
    auto f = c.find("frames");
    auto r = c.find("role");
    if (f == c.end() || !f->is_array() || f->size() != 2 || !isNumber((*f)[0]) || !isNumber((*f)[1])) continue;
    if (r == c.end() || !r->is_string()) continue;
    FootPlant p{r->get<std::string>(), (*f)[0].get<double>(), (*f)[1].get<double>()};
    if (p.b >= p.a && p.a >= 0) out.push_back(std::move(p));
  }
  return out;
}

PlantState plantAt(const std::vector<FootPlant>& plants, const std::string& role, double cf, int frameCount, bool loop,
                   double release, double easeIn, double lead) {
  PlantState best;
  const double N = std::max(1, frameCount);
  if (!loop) cf = std::clamp(cf, 0.0, N - 1);
  const double base = loop ? std::floor(cf / N) * N : 0.0;
  for (const FootPlant& p : plants) {
    if (p.role != role) continue;
    for (int k = 1; k >= (loop ? -1 : 0); --k) {
      if (k == 1 && !loop) continue;
      const double a = std::max(0.0, base + k * N + p.a), b = base + k * N + p.b;
      // A plant that is there from the clip's first frame holds at once; otherwise the pin eases in from `lead`
      // frames before the plant to `easeIn` frames into it.
      const double in = a <= 0.0 ? 0.0 : std::min(easeIn, b - a), pre = a <= 0.0 ? 0.0 : std::min(lead, a);
      if (b < a || cf < a - pre || cf > b + release) continue;
      float w = 1.0f;
      if (cf < a + in) w = float(smooth01((cf - (a - pre)) / std::max(1e-9, in + pre)));
      else if (cf > b) w = float(1.0 - smooth01((cf - b) / std::max(1e-9, release)));
      if (w > best.weight || !best.active) best = {true, a + in, w};
    }
  }
  return best;
}

void pinFoot(const Skeleton& sk, Pose& pose, int foot, vec3 target, float weight) {
  weight = std::clamp(weight, 0.0f, 1.0f);
  if (foot < 0 || weight <= 0) return;
  const int shin = sk.bones[size_t(foot)].parent;
  if (shin < 0 || sk.bones[size_t(shin)].parent < 0) return;
  auto globalRot = [&](int b) {
    quat q = kIdentity;
    for (; b >= 0; b = sk.bones[size_t(b)].parent) q = pose.local[size_t(b)] * q;
    return q;
  };
  const quat footGlobal = globalRot(foot);
  solveTwoBoneIK(sk, pose, mat4(1), foot, target, weight);
  const quat keep = glm::normalize(glm::inverse(globalRot(shin)) * footGlobal);
  quat& fl = pose.local[size_t(foot)];
  fl = glm::normalize(glm::slerp(fl, glm::dot(fl, keep) < 0 ? -keep : keep, weight));
}

float footReachDrop(const Skeleton& sk, const std::vector<mat4>& G, int foot, vec3 target, float stretch) {
  if (foot < 0) return 0;
  const int shin = sk.bones[size_t(foot)].parent;
  const int thigh = shin < 0 ? -1 : sk.bones[size_t(shin)].parent;
  if (thigh < 0) return 0;
  const vec3 hip(G[size_t(thigh)][3]);
  const float reach = stretch * (glm::length(vec3(G[size_t(shin)][3]) - hip) + glm::length(vec3(G[size_t(foot)][3]) - vec3(G[size_t(shin)][3])));
  const vec3 d = target - hip;
  if (glm::length(d) <= reach) return 0;
  const float h2 = d.x * d.x + d.z * d.z;
  if (h2 >= reach * reach) return 0;  // too far sideways: no drop can reach it (the leg stretches towards it)
  // hip.y - drop = target.y + sqrt(reach^2 - h2)  (the hip stays above the ankle)
  return std::max(0.0f, hip.y - (target.y + std::sqrt(reach * reach - h2)));
}

}  // namespace plush
