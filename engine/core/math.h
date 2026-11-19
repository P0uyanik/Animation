// Math helpers on top of glm: random numbers, sampling, frames, noise.
#pragma once
#define GLM_ENABLE_EXPERIMENTAL
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>
#include <glm/gtx/norm.hpp>
#include <glm/gtx/quaternion.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace plush {

using glm::mat3;
using glm::mat4;
using glm::quat;
using glm::vec2;
using glm::vec3;
using glm::vec4;

inline constexpr float kPi = 3.14159265358979323846f;
inline constexpr float kTwoPi = 2.0f * kPi;
inline constexpr float kInvPi = 1.0f / kPi;

inline float sqr(float x) { return x * x; }
inline float safeSqrt(float x) { return std::sqrt(std::max(0.0f, x)); }
inline float safeAsin(float x) { return std::asin(std::clamp(x, -1.0f, 1.0f)); }
inline float luminance(vec3 c) { return 0.2126f * c.r + 0.7152f * c.g + 0.0722f * c.b; }
inline float maxComponent(vec3 c) { return std::max(c.x, std::max(c.y, c.z)); }
inline float smoothstep01(float x) { x = std::clamp(x, 0.0f, 1.0f); return x * x * (3 - 2 * x); }

// SplitMix64 hash, used to derive deterministic seeds.
inline uint64_t hash64(uint64_t x) {
  x += 0x9e3779b97f4a7c15ull;
  x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
  x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
  return x ^ (x >> 31);
}
inline float hashToFloat(uint64_t h) { return float(h >> 40) * (1.0f / 16777216.0f); }

// PCG32 random number generator (deterministic, small state).
class Rng {
 public:
  explicit Rng(uint64_t seed = 1, uint64_t stream = 1) {
    state_ = 0;
    inc_ = (stream << 1u) | 1u;
    nextU32();
    state_ += hash64(seed);
    nextU32();
  }
  uint32_t nextU32() {
    uint64_t old = state_;
    state_ = old * 6364136223846793005ull + inc_;
    uint32_t xorshifted = uint32_t(((old >> 18u) ^ old) >> 27u);
    uint32_t rot = uint32_t(old >> 59u);
    return (xorshifted >> rot) | (xorshifted << ((~rot + 1u) & 31));
  }
  float next() { return std::min(float(nextU32()) * (1.0f / 4294967296.0f), 0.99999994f); }
  vec2 next2() { float a = next(); return {a, next()}; }
  float range(float lo, float hi) { return lo + (hi - lo) * next(); }

 private:
  uint64_t state_, inc_;
};

// ---------------------------------------------------------------- sampling
inline vec2 sampleConcentricDisk(vec2 u) {
  vec2 o = 2.0f * u - vec2(1.0f);
  if (o.x == 0 && o.y == 0) return vec2(0);
  float r, theta;
  if (std::abs(o.x) > std::abs(o.y)) {
    r = o.x;
    theta = (kPi / 4) * (o.y / o.x);
  } else {
    r = o.y;
    theta = kPi / 2 - (kPi / 4) * (o.x / o.y);
  }
  return r * vec2(std::cos(theta), std::sin(theta));
}
// Cosine-weighted hemisphere around +z. pdf = cos/pi.
inline vec3 sampleCosineHemisphere(vec2 u) {
  vec2 d = sampleConcentricDisk(u);
  return {d.x, d.y, safeSqrt(1 - d.x * d.x - d.y * d.y)};
}
inline vec3 sampleUniformSphere(vec2 u) {
  float z = 1 - 2 * u.x;
  float r = safeSqrt(1 - z * z);
  float phi = kTwoPi * u.y;
  return {r * std::cos(phi), r * std::sin(phi), z};
}
// Uniform cone around +z with cos(theta_max). pdf = 1 / (2 pi (1 - cosMax)).
inline vec3 sampleUniformCone(vec2 u, float cosMax) {
  float cosT = (1 - u.x) + u.x * cosMax;
  float sinT = safeSqrt(1 - cosT * cosT);
  float phi = kTwoPi * u.y;
  return {std::cos(phi) * sinT, std::sin(phi) * sinT, cosT};
}
// Point in a regular polygon (aperture blades) of unit circumradius.
inline vec2 sampleRegularPolygon(int blades, float rotation, float u0, vec2 u) {
  if (blades < 3) return sampleConcentricDisk(u);
  int k = std::min(int(u0 * blades), blades - 1);
  float a0 = rotation + kTwoPi * k / blades, a1 = rotation + kTwoPi * (k + 1) / blades;
  vec2 p0(std::cos(a0), std::sin(a0)), p1(std::cos(a1), std::sin(a1));
  float su = std::sqrt(u.x);
  return (1 - su) * vec2(0) + su * ((1 - u.y) * p0 + u.y * p1);
}

// Orthonormal basis (Duff et al. 2017).
struct Frame {
  vec3 t, b, n;
  static Frame fromNormal(vec3 n) {
    float sign = std::copysign(1.0f, n.z);
    float a = -1.0f / (sign + n.z);
    float bb = n.x * n.y * a;
    return {vec3(1 + sign * n.x * n.x * a, sign * bb, -sign * n.x), vec3(bb, sign + n.y * n.y * a, -n.y), n};
  }
  static Frame fromXZ(vec3 x, vec3 z) { return {x, glm::cross(z, x), z}; }
  vec3 toLocal(vec3 v) const { return {glm::dot(v, t), glm::dot(v, b), glm::dot(v, n)}; }
  vec3 toWorld(vec3 v) const { return v.x * t + v.y * b + v.z * n; }
};

// ---------------------------------------------------------------- noise
// Gradient noise in [-1, 1] (hash based, no tables, deterministic everywhere).
inline vec3 noiseGradient(int x, int y, int z) {
  uint64_t h = hash64(uint64_t(uint32_t(x)) * 73856093ull ^ uint64_t(uint32_t(y)) * 19349663ull ^
                      uint64_t(uint32_t(z)) * 83492791ull);
  float a = hashToFloat(h) * kTwoPi;
  float zc = hashToFloat(hash64(h)) * 2 - 1;
  float r = safeSqrt(1 - zc * zc);
  return {r * std::cos(a), r * std::sin(a), zc};
}
inline float gradientNoise(vec3 p) {
  vec3 fl = glm::floor(p);
  int ix = int(fl.x), iy = int(fl.y), iz = int(fl.z);
  vec3 f = p - fl;
  vec3 w = f * f * f * (f * (f * 6.0f - 15.0f) + 10.0f);
  float acc[2][2][2];
  for (int dz = 0; dz < 2; ++dz)
    for (int dy = 0; dy < 2; ++dy)
      for (int dx = 0; dx < 2; ++dx)
        acc[dz][dy][dx] = glm::dot(noiseGradient(ix + dx, iy + dy, iz + dz), f - vec3(dx, dy, dz));
  auto lerp = [](float a, float b, float t) { return a + (b - a) * t; };
  float x00 = lerp(acc[0][0][0], acc[0][0][1], w.x), x10 = lerp(acc[0][1][0], acc[0][1][1], w.x);
  float x01 = lerp(acc[1][0][0], acc[1][0][1], w.x), x11 = lerp(acc[1][1][0], acc[1][1][1], w.x);
  return std::clamp(1.6f * lerp(lerp(x00, x10, w.y), lerp(x01, x11, w.y), w.z), -1.0f, 1.0f);
}
inline float fbm(vec3 p, int octaves = 4, float lacunarity = 2.0f, float gain = 0.5f) {
  float sum = 0, amp = 0.5f, norm = 0;
  for (int i = 0; i < octaves; ++i) {
    sum += amp * gradientNoise(p);
    norm += amp;
    p = p * lacunarity + vec3(17.3f, -9.1f, 4.7f);
    amp *= gain;
  }
  return sum / norm;
}

}  // namespace plush
