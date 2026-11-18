#include "anim/principles.h"

#include <algorithm>
#include <cmath>
#include <format>

namespace plush {

Result<AnimPrinciples> animPrinciplesFromJson(const Json& j) {
  AnimPrinciples p;
  if (j.is_null()) return p;
  if (j.is_boolean()) {
    p.enabled = j.get<bool>();
    return p;
  }
  if (!j.is_object()) return fail("animPrinciples: expected true, false or an object");
  auto number = [&](const char* key, double& out, double lo, double hi) -> Result<void> {
    auto it = j.find(key);
    if (it == j.end()) return {};
    if (!it->is_number()) return fail(std::format("animPrinciples: '{}' must be a number", key));
    const double v = it->get<double>();
    if (!(v >= lo && v <= hi)) return fail(std::format("animPrinciples: '{}' must be in [{}, {}]", key, lo, hi));
    out = v;
    return {};
  };
  if (auto it = j.find("enabled"); it != j.end()) {
    if (!it->is_boolean()) return fail("animPrinciples: 'enabled' must be true or false");
    p.enabled = it->get<bool>();
  }
  if (auto it = j.find("easePreservingRetime"); it != j.end()) {
    if (!it->is_boolean()) return fail("animPrinciples: 'easePreservingRetime' must be true or false");
    p.easePreservingRetime = it->get<bool>();
  }
  for (auto r : {number("maxBlendDegPerSec", p.maxBlendDegPerSec, 1, 1e4), number("minBlendSec", p.minBlendSec, 0, 10),
                 number("maxBlendSec", p.maxBlendSec, 0, 10), number("successionSec", p.successionSec, 0, 1), number("ikElbowLagSec", p.ikElbowLagSec, 0, 1),
                 number("retimeMaxRate", p.retimeMaxRate, 1, 10), number("retimeContrast", p.retimeContrast, 0.1, 10), number("minArc", p.minArc, 0, 1),
                 number("breakdownMaxDeg", p.breakdownMaxDeg, 0, 90), number("breakdownMinChordM", p.breakdownMinChordM, 0, 10)})
    if (!r) return std::unexpected(r.error());
  if (p.maxBlendSec < p.minBlendSec) return fail("animPrinciples: maxBlendSec must be >= minBlendSec");
  return p;
}

double easeInOut(double x) {
  x = std::clamp(x, 0.0, 1.0);
  return x * x * x * (x * (x * 6 - 15) + 10);
}

double easeInOutIntegral(double x) {
  x = std::clamp(x, 0.0, 1.0);
  const double x4 = x * x * x * x;
  return x4 * (x * x - 3 * x + 2.5);
}

double easedClock(double offset, double length, double in, double out) {
  offset = std::max(0.0, offset);
  if (in < 0 || out < 0 || in + out > length + 1e-9) return offset;  // no room for both ramps: plain clock
  double t = in > 0 && offset < in ? in * easeInOutIntegral(offset / in) : offset - 0.5 * in;
  if (out > 0 && offset > length - out) {
    const double e = std::max(0.0, length - offset);
    t = (length - out - 0.5 * in) + out * (0.5 - easeInOutIntegral(e / out));
  }
  // rescale so the clock covers the whole layer (finite layers): the ramps' lost half-lengths are made up evenly
  if (length < 1e29) t *= length / std::max(1e-9, length - 0.5 * (in + out));
  return t;
}

double minBlendFrames(double amplitudeDeg, double fps, const AnimPrinciples& p) {
  const double t = std::clamp(kEasePeakSlope * std::max(0.0, amplitudeDeg) / p.maxBlendDegPerSec, p.minBlendSec, p.maxBlendSec);
  return t * fps;
}

int successionRank(std::string_view role) {
  auto starts = [&](std::string_view p) { return role.substr(0, p.size()) == p; };
  if (starts("thumb") || (role.size() > 2 && role[0] == 'f' && role[1] >= '0' && role[1] <= '9')) return 4;
  if (starts("hand") || starts("foot") || starts("toe")) return 3;
  if (starts("forearm") || starts("shin") || role == "head") return 2;
  if (starts("upperArm") || starts("thigh") || role == "neck") return 1;
  return 0;
}

TimeWarp TimeWarp::linear(double speed, double clipFps, double sceneFps) {
  TimeWarp w;
  w.linear_ = true;
  w.rate_ = speed * clipFps / std::max(1e-9, sceneFps);
  return w;
}

TimeWarp TimeWarp::easePreserving(const std::vector<double>& motion, double speed, double clipFps, double sceneFps,
                                  const AnimPrinciples& p) {
  TimeWarp lin = linear(speed, clipFps, sceneFps);
  lin.clipLength_ = double(motion.size());
  const size_t n = motion.size();
  const double peak = n ? *std::max_element(motion.begin(), motion.end()) : 0.0;
  if (n < 2 || peak <= 1e-12 || std::abs(speed - 1.0) < 1e-9) return lin;
  // Movements: split at the local minima of the motion (lightly smoothed against noise); each frame gets its
  // movement's peak, normalised by the clip's peak.
  std::vector<double> sm(n, 0.0);
  for (size_t k = 0; k < n; ++k) {
    const double a = motion[k > 0 ? k - 1 : k], b = motion[k], c = motion[k + 1 < n ? k + 1 : k];
    sm[k] = 0.25 * std::max(0.0, a) + 0.5 * std::max(0.0, b) + 0.25 * std::max(0.0, c);
  }
  std::vector<double> w(n, 0.0);
  size_t s0 = 0;
  for (size_t k = 1; k <= n; ++k) {
    const bool boundary = k == n || (k + 1 < n && sm[k] <= sm[k - 1] && sm[k] < sm[k + 1]);
    if (!boundary) continue;
    double mpeak = 0;
    for (size_t j = s0; j < k; ++j) mpeak = std::max(mpeak, sm[j]);
    for (size_t j = s0; j < k; ++j) w[j] = mpeak;
    s0 = k;
  }
  const double wpeak = *std::max_element(w.begin(), w.end());
  if (wpeak <= 1e-12) return lin;
  for (double& x : w) x = std::pow(x / wpeak, p.retimeContrast);
  // Duration of clip frame k in clip-frame units (linear: 1 / speed). Faster: d = 1 / (1 + a w), never below
  // 1 / (speed x maxRate); slower: d = 1 + a w, never above maxRate / speed. Small movements (anticipations, settles)
  // and holds keep (close to) their authored spacing; the big movements absorb the change, each at one rate.
  const bool faster = speed > 1;
  const double dmin = 1.0 / (speed * p.retimeMaxRate), dmax = p.retimeMaxRate / speed;
  auto dur = [&](double a, size_t k) {
    return faster ? std::max(dmin, 1.0 / (1.0 + a * w[k])) : std::min(dmax, 1.0 + a * w[k]);
  };
  auto total = [&](double a) {
    double s = 0;
    for (size_t k = 0; k < n; ++k) s += dur(a, k);
    return s;
  };
  const double target = double(n) / speed;
  double lo = 0, hi = 1;
  // total(a) is monotonic in a (decreasing when faster, increasing when slower).
  auto beyond = [&](double a) { return faster ? total(a) <= target : total(a) >= target; };
  while (!beyond(hi) && hi < 1e7) hi *= 2;
  if (!beyond(hi)) return lin;  // e.g. a clip of mostly holds asked to go much faster: linear scale
  for (int it = 0; it < 80; ++it) {
    const double mid = 0.5 * (lo + hi);
    (beyond(mid) ? hi : lo) = mid;
  }
  const double a = hi;
  TimeWarp out;
  out.linear_ = false;
  out.clipLength_ = double(n);
  out.sceneAt_.resize(n + 1, 0.0);
  const double toScene = sceneFps / clipFps;
  double acc = 0;
  for (size_t k = 0; k < n; ++k) {
    acc += dur(a, k);
    out.sceneAt_[k + 1] = acc;
  }
  // exact total (the bisection leaves a tiny residual): rescale so the length equals the linear one
  const double fix = target / acc;
  for (double& s : out.sceneAt_) s *= fix * toScene;
  return out;
}

double TimeWarp::clipFrame(double offset, bool loop) const {
  offset = std::max(0.0, offset);
  if (linear_) return offset * rate_;
  const double len = sceneAt_.back();
  if (len <= 0) return 0;
  double cycles = 0;
  if (loop && offset >= len) {
    cycles = std::floor(offset / len);
    offset -= cycles * len;
  }
  if (offset >= len) return clipLength_;
  auto it = std::upper_bound(sceneAt_.begin(), sceneAt_.end(), offset);
  const size_t k1 = size_t(it - sceneAt_.begin()), k0 = k1 - 1;
  const double t = (offset - sceneAt_[k0]) / std::max(1e-12, sceneAt_[k1] - sceneAt_[k0]);
  return cycles * clipLength_ + double(k0) + t;
}

quat elbowOpening(const Skeleton& sk, const Pose& pose, int upperArm, int forearm, int hand, float degrees) {
  if (upperArm < 0 || forearm < 0 || hand < 0 || degrees == 0.0f) return quat(1, 0, 0, 0);
  const auto g = boneGlobals(sk, pose, mat4(1));
  const vec3 a(g[size_t(upperArm)][3]), b(g[size_t(forearm)][3]), c(g[size_t(hand)][3]);
  if (glm::length2(b - a) < 1e-10f || glm::length2(c - b) < 1e-10f) return quat(1, 0, 0, 0);
  const vec3 u = glm::normalize(b - a), v = glm::normalize(c - b);
  const float bend = glm::degrees(std::acos(std::clamp(glm::dot(u, v), -1.0f, 1.0f)));
  // opening: never past straight; closing (negative): never beyond 150 degrees of bend
  const float open = degrees > 0 ? std::min(degrees, bend - 2.0f) : std::max(degrees, bend - 150.0f);
  if ((degrees > 0 && open <= 0.0f) || (degrees < 0 && open >= 0.0f)) return quat(1, 0, 0, 0);
  const vec3 axis = glm::cross(v, u);
  if (glm::length2(axis) < 1e-12f || bend < 2.0f) return quat(1, 0, 0, 0);
  const quat rg = glm::angleAxis(glm::radians(open), glm::normalize(axis));  // turns v towards u (world)
  const int parent = sk.bones[size_t(forearm)].parent;
  const quat gp = parent >= 0 ? glm::normalize(glm::quat_cast(mat3(g[size_t(parent)]))) : quat(1, 0, 0, 0);
  return glm::normalize(glm::inverse(gp) * rg * gp);  // pre-multiplies the forearm's local rotation
}

float arcDeviation(const std::vector<vec3>& path, float* chordOut) {
  if (chordOut) *chordOut = 0;
  if (path.size() < 3) return 0;
  const vec3 chord = path.back() - path.front();
  const float L = glm::length(chord);
  if (chordOut) *chordOut = L;
  if (L < 1e-9f) return 0;
  const vec3 u = chord / L;
  float dev = 0;
  for (const vec3& p : path) {
    const vec3 d = p - path.front();
    dev = std::max(dev, glm::length(d - u * glm::dot(d, u)));
  }
  return dev / L;
}

}  // namespace plush
