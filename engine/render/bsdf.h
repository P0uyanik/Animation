// Scattering models: layered surface BSDF (diffuse, GGX specular, clear coat,
// sheen), plush felt, and the Chiang et al. 2016 fiber model for wool/hair.
#pragma once
#include "geom/geometry.h"

namespace plush {

struct ShadingPoint {
  vec3 p{0};
  vec3 ng{0, 0, 1};   // geometric normal (surfaces) or tube normal (fibers)
  vec3 ns{0, 0, 1};   // shading normal
  vec3 pref{0};
  vec3 tangent{1, 0, 0};
  bool fiber = false;
  float fiberRadius = 0;
  float h = 0;        // fiber offset in [-1, 1]
  vec3 base{0.8f};    // textured base colour
  const Material* material = nullptr;
};

struct BsdfSample {
  vec3 wi{0};
  vec3 weight{0};  // f * |cos| / pdf (fibers: f / pdf)
  float pdf = 0;
};

vec3 evalTexture(const Material& m, vec3 pref);

// Prepares the shading frame for an outgoing direction (computes fiber h).
void prepareShading(ShadingPoint& sp, vec3 wo);
// Returns f * |cos theta_i| (fibers: f, the projected-area term is built in).
vec3 evalBsdf(const ShadingPoint& sp, vec3 wo, vec3 wi, float& pdf);
bool sampleBsdf(const ShadingPoint& sp, vec3 wo, float u0, vec2 u1, vec2 u2, BsdfSample& out);

}  // namespace plush
