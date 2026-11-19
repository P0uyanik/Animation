// Procedural texture colours for the studio's OpenGL viewport (moved verbatim from the removed engine/render/bsdf.cpp,
// T-142; the Blender pipeline owns final look and materials).
#include "preview_texture.h"

#include <array>

namespace plush::studio {

// ============================================================ textures
namespace {
float hashf(int a, int b) { return hashToFloat(hash64(uint64_t(uint32_t(a)) * 1315423911ull ^ uint64_t(uint32_t(b)) * 2654435761ull)); }
float fract(float x) { return x - std::floor(x); }
}  // namespace

vec3 evalTexture(const Material& m, vec3 pref) {
  const ProceduralTexture& t = m.texture;
  vec3 c = m.baseColor;
  switch (t.type) {
    case TextureType::None: return c;
    case TextureType::Noise: {
      float n = 0.5f + 0.5f * fbm(pref * t.scale, 4);
      float fine = 0.5f + 0.5f * gradientNoise(pref * t.scale * 9.0f);
      return glm::mix(c, t.color2, std::clamp(n * t.amount + (fine - 0.5f) * 0.25f * t.amount, 0.0f, 1.0f));
    }
    case TextureType::Knit: {
      // Stockinette "V" stitches: columns along x, rows along y.
      float u = pref.x * t.scale, v = pref.y * t.scale * 1.25f;
      float col = fract(u);
      float row = fract(v + std::abs(col - 0.5f) * 0.9f);
      float groove = smoothstep01(std::min(row, 1 - row) / 0.18f) * smoothstep01(std::min(col, 1 - col) / 0.12f);
      float n = 0.5f + 0.5f * fbm(pref * 60.0f, 2);
      vec3 base = glm::mix(c, t.color2, 0.3f * n);
      return base * glm::mix(1.0f - t.amount, 1.0f, groove);
    }
    case TextureType::Wood: {
      float plankW = t.params.x > 0 ? t.params.x : 0.14f, plankL = t.params.y > 0 ? t.params.y : 1.1f;
      float pz = pref.z / plankW;
      int row = int(std::floor(pz));
      float px = (pref.x + hashf(row, 7) * plankL) / plankL;
      int seg = int(std::floor(px));
      float tone = 0.8f + 0.35f * hashf(row, seg);
      float grain = fbm(vec3(pref.x * 2.5f, pref.y * 3.0f, pref.z * 55.0f) + vec3(hashf(row, seg) * 40.0f), 4);
      float ring = 0.5f + 0.5f * std::sin(grain * 9.0f + pref.z * 30.0f);
      vec3 col = glm::mix(c, t.color2, std::clamp(0.5f + 0.6f * grain * t.amount + 0.2f * ring * t.amount, 0.0f, 1.0f)) * tone;
      float fz = fract(pz), fx = fract(px);
      float gapZ = std::min(fz, 1 - fz) * plankW, gapX = std::min(fx, 1 - fx) * plankL;
      float gap = smoothstep01(std::min(gapZ, gapX) / 0.0025f);
      return col * glm::mix(0.35f, 1.0f, gap);
    }
    case TextureType::Wall: {
      float wainscot = t.params.x > 0 ? t.params.x : 0.6f, board = t.params.y > 0 ? t.params.y : 0.12f;
      float n = fbm(pref * 8.0f, 3);
      if (pref.y < wainscot) {
        float along = std::abs(pref.x) > std::abs(pref.z) ? pref.x : pref.z;
        float f = fract(along / board);
        float groove = smoothstep01(std::min(f, 1 - f) * board / 0.004f);
        float rail = smoothstep01((wainscot - pref.y) / 0.02f);
        return t.color2 * (0.95f + 0.08f * n) * glm::mix(0.7f, 1.0f, groove) * glm::mix(0.85f, 1.0f, rail);
      }
      return c * (0.96f + 0.06f * n);
    }
    case TextureType::Iris: {
      // spots: eye centres (xyz) + unused; eyes look along +z in rest pose.
      vec3 centre = t.spots.empty() ? vec3(0) : vec3(t.spots[0]);
      for (auto& s : t.spots)
        if (glm::distance2(vec3(s), pref) < glm::distance2(centre, pref)) centre = vec3(s);
      vec3 d = glm::normalize(pref - centre + vec3(1e-9f));
      float theta = std::acos(std::clamp(d.z, -1.0f, 1.0f));
      float pupil = glm::radians(t.params.x > 0 ? t.params.x : 13.0f);
      float iris = glm::radians(t.params.y > 0 ? t.params.y : 38.0f);
      if (theta < pupil) return t.color3;
      if (theta < iris) {
        float r = (theta - pupil) / (iris - pupil);
        float phi = std::atan2(d.y, d.x);
        float streak = fbm(vec3(std::cos(phi) * 6.0f, std::sin(phi) * 6.0f, r * 3.0f), 3);
        vec3 col = glm::mix(t.color2 * 1.5f, t.color2 * 0.55f, std::pow(r, 1.3f)) * (0.85f + 0.35f * streak);
        col = glm::mix(col, t.color3, smoothstep01((r - 0.82f) / 0.18f) * 0.75f);  // limbal ring
        float highlightRing = smoothstep01(1 - std::abs(r - 0.35f) / 0.12f) * 0.25f;
        return glm::clamp(col + highlightRing * t.color2, vec3(0), vec3(1));
      }
      return c;
    }
    case TextureType::Blush: {
      vec3 col = c * (0.97f + 0.05f * fbm(pref * 25.0f, 2));
      for (auto& s : t.spots) {
        float d2 = glm::distance2(vec3(s), pref) / std::max(1e-8f, s.w * s.w);
        col = glm::mix(col, t.color2, t.amount * std::exp(-d2));
      }
      return col;
    }
  }
  return c;
}

}  // namespace plush::studio
