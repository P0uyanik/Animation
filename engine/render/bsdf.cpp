#include "render/bsdf.h"

#include <array>

namespace plush {

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

// ============================================================ microfacets
namespace {
float schlick(float f0, float cosT) {
  float m = std::clamp(1 - cosT, 0.0f, 1.0f);
  float m2 = m * m;
  return f0 + (1 - f0) * m2 * m2 * m;
}
float ggxD(float nh, float a) {
  float a2 = a * a;
  float d = nh * nh * (a2 - 1) + 1;
  return a2 / (kPi * d * d);
}
float ggxLambda(float cosT, float a) {
  float c2 = cosT * cosT;
  if (c2 <= 0) return 1e6f;
  float t2 = (1 - c2) / c2;
  return 0.5f * (-1 + std::sqrt(1 + a * a * t2));
}
vec3 sampleGgxVndf(vec3 v, float a, vec2 u) {
  vec3 vh = glm::normalize(vec3(a * v.x, a * v.y, v.z));
  float lensq = vh.x * vh.x + vh.y * vh.y;
  vec3 t1 = lensq > 0 ? vec3(-vh.y, vh.x, 0) / std::sqrt(lensq) : vec3(1, 0, 0);
  vec3 t2 = glm::cross(vh, t1);
  float r = std::sqrt(u.x), phi = kTwoPi * u.y;
  float p1 = r * std::cos(phi), p2 = r * std::sin(phi);
  float s = 0.5f * (1 + vh.z);
  p2 = (1 - s) * safeSqrt(1 - p1 * p1) + s * p2;
  vec3 nh = p1 * t1 + p2 * t2 + safeSqrt(1 - p1 * p1 - p2 * p2) * vh;
  return glm::normalize(vec3(a * nh.x, a * nh.y, std::max(1e-6f, nh.z)));
}
// Microfacet reflection lobe: returns f*cos and pdf for local wo, wi (z up).
vec3 ggxLobe(vec3 wo, vec3 wi, float a, float f0, float& pdf) {
  pdf = 0;
  if (wo.z <= 0 || wi.z <= 0) return vec3(0);
  vec3 h = glm::normalize(wo + wi);
  float D = ggxD(h.z, a);
  float lo = ggxLambda(wo.z, a), li = ggxLambda(wi.z, a);
  float G1 = 1 / (1 + lo), G2 = 1 / (1 + lo + li);
  float F = schlick(f0, glm::dot(wi, h));
  pdf = G1 * D / (4 * wo.z);
  return vec3(D * G2 * F / (4 * wo.z));  // * wi.z cancels the 1/cos_i
}
float charlieD(float nh, float r) {
  float inv = 1 / r;
  float sin2 = std::max(0.0f, 1 - nh * nh);
  return (2 + inv) * std::pow(sin2, 0.5f * inv) / kTwoPi;
}

struct SurfaceLobes {
  vec3 kd{0};
  float f0 = 0.04f, specW = 0, coatW = 0, sheenW = 0;
  float aSpec = 0.25f, aCoat = 0.01f, rSheen = 0.4f;
  float pDiffuse = 1, pSpec = 0, pCoat = 0;
};
SurfaceLobes setupLobes(const ShadingPoint& sp, float cosO) {
  const Material& m = *sp.material;
  SurfaceLobes l;
  l.aSpec = std::max(0.02f, m.roughness * m.roughness);
  l.aCoat = std::max(0.01f, m.coatRoughness * m.coatRoughness);
  l.rSheen = std::max(0.07f, m.sheenRoughness);
  float f0 = sqr((m.ior - 1) / (m.ior + 1));
  l.f0 = std::clamp(f0 * m.specular, 0.0f, 1.0f);
  l.coatW = m.coat;
  l.sheenW = m.sheen;
  float coatF = m.coat * schlick(0.04f, cosO);
  float specF = m.type == MaterialType::Plush ? 0.0f : schlick(l.f0, cosO);
  l.specW = m.type == MaterialType::Plush ? 0.0f : 1.0f;
  l.kd = sp.base * (1 - specF) * (1 - coatF) * (1 - 0.25f * m.sheen);
  float wd = std::max(0.05f, luminance(l.kd) + 0.3f * m.sheen);
  float ws = l.specW > 0 ? std::max(0.08f, specF * 1.5f) : 0.0f;
  float wc = m.coat > 0 ? std::max(0.08f, coatF * 1.5f) : 0.0f;
  float sum = wd + ws + wc;
  l.pDiffuse = wd / sum;
  l.pSpec = ws / sum;
  l.pCoat = wc / sum;
  return l;
}
vec3 evalSurfaceLocal(const ShadingPoint& sp, const SurfaceLobes& l, vec3 wo, vec3 wi, float& pdf) {
  pdf = 0;
  if (wo.z <= 0 || wi.z <= 0) return vec3(0);
  const Material& m = *sp.material;
  vec3 f = l.kd * (kInvPi * wi.z);
  pdf = l.pDiffuse * wi.z * kInvPi;
  if (l.sheenW > 0) {
    vec3 h = glm::normalize(wo + wi);
    float V = 1 / (4 * (wi.z + wo.z - wi.z * wo.z));
    f += m.sheenColor * (l.sheenW * charlieD(h.z, l.rSheen) * V * wi.z);
  }
  if (l.pSpec > 0) {
    float p;
    f += ggxLobe(wo, wi, l.aSpec, l.f0, p) * (l.specW * (1 - l.coatW * schlick(0.04f, wo.z)));
    pdf += l.pSpec * p;
  }
  if (l.pCoat > 0) {
    float p;
    f += ggxLobe(wo, wi, l.aCoat, 0.04f, p) * l.coatW;
    pdf += l.pCoat * p;
  }
  return f;
}

// ============================================================ fibers (Chiang et al. 2016, after pbrt-v3)
constexpr int kPMax = 3;
float I0(float x) {
  float val = 0, x2i = 1;
  double ifact = 1;
  float i4 = 1;
  for (int i = 0; i < 10; ++i) {
    if (i > 1) ifact *= i;
    val += float(x2i / (i4 * ifact * ifact));
    x2i *= x * x;
    i4 *= 4;
  }
  return val;
}
float logI0(float x) {
  if (x > 12) return x + 0.5f * (-std::log(kTwoPi) + std::log(1 / x) + 1 / (8 * x));
  return std::log(I0(x));
}
float Mp(float cosI, float cosO, float sinI, float sinO, float v) {
  float a = cosI * cosO / v, b = sinI * sinO / v;
  if (v <= 0.1f) return std::exp(logI0(a) - b - 1 / v + 0.6931f + std::log(1 / (2 * v)));
  return std::exp(-b) * I0(a) / (std::sinh(1 / v) * 2 * v);
}
float frDielectric(float cosI, float eta) {
  cosI = std::clamp(cosI, -1.0f, 1.0f);
  if (cosI < 0) { eta = 1 / eta; cosI = -cosI; }
  float sinT = safeSqrt(1 - cosI * cosI) / eta;
  if (sinT >= 1) return 1;
  float cosT = safeSqrt(1 - sinT * sinT);
  float rpar = (eta * cosI - cosT) / (eta * cosI + cosT);
  float rper = (cosI - eta * cosT) / (cosI + eta * cosT);
  return 0.5f * (rpar * rpar + rper * rper);
}
std::array<vec3, kPMax + 1> Ap(float cosO, float eta, float h, vec3 T) {
  std::array<vec3, kPMax + 1> ap;
  float cosGammaO = safeSqrt(1 - h * h);
  float f = frDielectric(cosO * cosGammaO, eta);
  ap[0] = vec3(f);
  ap[1] = sqr(1 - f) * T;
  for (int p = 2; p < kPMax; ++p) ap[size_t(p)] = ap[size_t(p - 1)] * T * f;
  ap[kPMax] = ap[kPMax - 1] * f * T / (vec3(1) - T * f);
  return ap;
}
float phiFn(int p, float gammaO, float gammaT) { return 2 * p * gammaT - 2 * gammaO + p * kPi; }
float logistic(float x, float s) { x = std::abs(x); float e = std::exp(-x / s); return e / (s * sqr(1 + e)); }
float logisticCdf(float x, float s) { return 1 / (1 + std::exp(-x / s)); }
float trimmedLogistic(float x, float s, float a, float b) { return logistic(x, s) / (logisticCdf(b, s) - logisticCdf(a, s)); }
float Np(float phi, int p, float s, float gammaO, float gammaT) {
  float d = phi - phiFn(p, gammaO, gammaT);
  while (d > kPi) d -= kTwoPi;
  while (d < -kPi) d += kTwoPi;
  return trimmedLogistic(d, s, -kPi, kPi);
}
float sampleTrimmedLogistic(float u, float s, float a, float b) {
  float k = logisticCdf(b, s) - logisticCdf(a, s);
  float x = -s * std::log(1 / (u * k + logisticCdf(a, s)) - 1);
  return std::clamp(x, a, b);
}

struct FiberModel {
  float h, gammaO, eta = 1.55f, s;
  vec3 sigmaA;
  float v[kPMax + 1];
  float sin2k[3], cos2k[3];
  FiberModel(const ShadingPoint& sp) {
    const Material& m = *sp.material;
    h = std::clamp(sp.h, -0.999f, 0.999f);
    gammaO = safeAsin(h);
    float bm = std::clamp(m.betaM, 0.02f, 1.0f), bn = std::clamp(m.betaN, 0.02f, 1.0f);
    v[0] = sqr(0.726f * bm + 0.812f * bm * bm + 3.7f * std::pow(bm, 20.0f));
    v[1] = 0.25f * v[0];
    v[2] = 4 * v[0];
    v[3] = v[2];
    s = 0.626657069f * (0.265f * bn + 1.194f * bn * bn + 5.372f * std::pow(bn, 22.0f));
    sin2k[0] = std::sin(glm::radians(m.alphaDeg));
    cos2k[0] = safeSqrt(1 - sqr(sin2k[0]));
    for (int i = 1; i < 3; ++i) {
      sin2k[i] = 2 * cos2k[i - 1] * sin2k[i - 1];
      cos2k[i] = sqr(cos2k[i - 1]) - sqr(sin2k[i - 1]);
    }
    float denom = 5.969f - 0.215f * bn + 2.532f * bn * bn - 10.73f * bn * bn * bn + 5.574f * std::pow(bn, 4.0f) + 0.245f * std::pow(bn, 5.0f);
    vec3 c = glm::clamp(sp.base, vec3(1e-4f), vec3(0.999f));
    sigmaA = vec3(sqr(std::log(c.r) / denom), sqr(std::log(c.g) / denom), sqr(std::log(c.b) / denom));
  }
  void tilt(int p, float sinO, float cosO, float& sinOp, float& cosOp) const {
    if (p == 0) { sinOp = sinO * cos2k[1] - cosO * sin2k[1]; cosOp = cosO * cos2k[1] + sinO * sin2k[1]; }
    else if (p == 1) { sinOp = sinO * cos2k[0] + cosO * sin2k[0]; cosOp = cosO * cos2k[0] - sinO * sin2k[0]; }
    else if (p == 2) { sinOp = sinO * cos2k[2] + cosO * sin2k[2]; cosOp = cosO * cos2k[2] - sinO * sin2k[2]; }
    else { sinOp = sinO; cosOp = cosO; }
    cosOp = std::abs(cosOp);
  }
  std::array<vec3, kPMax + 1> attenuation(float sinO, float cosO, float& gammaT) const {
    float sinT = sinO / eta, cosT = safeSqrt(1 - sinT * sinT);
    float etap = std::sqrt(std::max(1e-6f, eta * eta - sinO * sinO)) / std::max(1e-6f, cosO);
    float sinGT = h / etap, cosGT = safeSqrt(1 - sinGT * sinGT);
    gammaT = safeAsin(sinGT);
    vec3 T = glm::exp(-sigmaA * (2 * cosGT / std::max(1e-6f, cosT)));
    return Ap(cosO, eta, h, T);
  }
  // Local frame: x along the fiber.
  vec3 f(vec3 wo, vec3 wi, float* pdfOut) const {
    float sinO = wo.x, cosO = safeSqrt(1 - sinO * sinO), phiO = std::atan2(wo.z, wo.y);
    float sinI = wi.x, cosI = safeSqrt(1 - sinI * sinI), phiI = std::atan2(wi.z, wi.y);
    float gammaT;
    auto ap = attenuation(sinO, cosO, gammaT);
    float phi = phiI - phiO;
    vec3 fsum(0);
    for (int p = 0; p < kPMax; ++p) {
      float sOp, cOp;
      tilt(p, sinO, cosO, sOp, cOp);
      fsum += Mp(cosI, cOp, sinI, sOp, v[p]) * ap[size_t(p)] * Np(phi, p, s, gammaO, gammaT);
    }
    fsum += Mp(cosI, cosO, sinI, sinO, v[kPMax]) * ap[kPMax] / kTwoPi;
    if (pdfOut) {
      float sumY = 0;
      for (auto& a : ap) sumY += luminance(a);
      float pdf = 0;
      for (int p = 0; p < kPMax; ++p) {
        float sOp, cOp;
        tilt(p, sinO, cosO, sOp, cOp);
        pdf += Mp(cosI, cOp, sinI, sOp, v[p]) * (luminance(ap[size_t(p)]) / sumY) * Np(phi, p, s, gammaO, gammaT);
      }
      pdf += Mp(cosI, cosO, sinI, sinO, v[kPMax]) * (luminance(ap[kPMax]) / sumY) / kTwoPi;
      *pdfOut = pdf;
    }
    return fsum;
  }
  bool sample(vec3 wo, float u0, vec2 u1, vec2 u2, vec3& wi) const {
    float sinO = wo.x, cosO = safeSqrt(1 - sinO * sinO), phiO = std::atan2(wo.z, wo.y);
    float gammaT;
    auto ap = attenuation(sinO, cosO, gammaT);
    float sumY = 0;
    for (auto& a : ap) sumY += luminance(a);
    if (sumY <= 0) return false;
    int p = 0;
    float u = u0 * sumY;
    for (; p < kPMax; ++p) {
      float w = luminance(ap[size_t(p)]);
      if (u < w) break;
      u -= w;
    }
    float sOp, cOp;
    tilt(p, sinO, cosO, sOp, cOp);
    float uu = std::max(u1.x, 1e-5f);
    float cosTheta = 1 + v[p] * std::log(uu + (1 - uu) * std::exp(-2 / v[p]));
    float sinTheta = safeSqrt(1 - cosTheta * cosTheta);
    float cosPhi = std::cos(kTwoPi * u1.y);
    float sinI = -cosTheta * sOp + sinTheta * cosPhi * cOp;
    float cosI = safeSqrt(1 - sinI * sinI);
    float dphi = p < kPMax ? phiFn(p, gammaO, gammaT) + sampleTrimmedLogistic(u2.x, s, -kPi, kPi) : kTwoPi * u2.x;
    float phiI = phiO + dphi;
    wi = vec3(sinI, cosI * std::cos(phiI), cosI * std::sin(phiI));
    return true;
  }
};

Frame fiberFrame(const ShadingPoint& sp, vec3 wo) {
  vec3 x = sp.tangent;
  vec3 z = wo - x * glm::dot(wo, x);
  float lz = glm::length(z);
  z = lz > 1e-6f ? z / lz : Frame::fromNormal(x).t;
  return Frame::fromXZ(x, z);
}
Frame surfaceFrame(const ShadingPoint& sp) { return Frame::fromNormal(sp.ns); }
}  // namespace

void prepareShading(ShadingPoint& sp, vec3 wo) {
  if (sp.fiber) {
    Frame fr = fiberFrame(sp, wo);
    sp.h = std::clamp(glm::dot(sp.ng, fr.b), -1.0f, 1.0f);
    return;
  }
  // Two-sided surfaces: orient normals towards the viewer.
  if (glm::dot(sp.ng, wo) < 0) sp.ng = -sp.ng;
  if (glm::dot(sp.ns, sp.ng) < 0) sp.ns = -sp.ns;
  if (glm::dot(sp.ns, wo) <= 0.01f) sp.ns = sp.ng;
}

vec3 evalBsdf(const ShadingPoint& sp, vec3 wo, vec3 wi, float& pdf) {
  pdf = 0;
  if (sp.fiber) {
    Frame fr = fiberFrame(sp, wo);
    FiberModel fm(sp);
    return fm.f(fr.toLocal(wo), fr.toLocal(wi), &pdf);
  }
  if (glm::dot(wi, sp.ng) <= 0) return vec3(0);
  Frame fr = surfaceFrame(sp);
  vec3 lo = fr.toLocal(wo), li = fr.toLocal(wi);
  SurfaceLobes l = setupLobes(sp, lo.z);
  return evalSurfaceLocal(sp, l, lo, li, pdf);
}

bool sampleBsdf(const ShadingPoint& sp, vec3 wo, float u0, vec2 u1, vec2 u2, BsdfSample& out) {
  if (sp.fiber) {
    Frame fr = fiberFrame(sp, wo);
    FiberModel fm(sp);
    vec3 wol = fr.toLocal(wo), wil;
    if (!fm.sample(wol, u0, u1, u2, wil)) return false;
    float pdf;
    vec3 f = fm.f(wol, wil, &pdf);
    if (pdf <= 0 || !std::isfinite(pdf)) return false;
    out.wi = fr.toWorld(wil);
    out.pdf = pdf;
    out.weight = f / pdf;
    return std::isfinite(out.weight.x + out.weight.y + out.weight.z);
  }
  Frame fr = surfaceFrame(sp);
  vec3 lo = fr.toLocal(wo);
  if (lo.z <= 0) return false;
  SurfaceLobes l = setupLobes(sp, lo.z);
  vec3 li;
  if (u0 < l.pDiffuse) {
    li = sampleCosineHemisphere(u1);
  } else if (u0 < l.pDiffuse + l.pSpec) {
    vec3 hh = sampleGgxVndf(lo, l.aSpec, u1);
    li = glm::reflect(-lo, hh);
  } else {
    vec3 hh = sampleGgxVndf(lo, l.aCoat, u1);
    li = glm::reflect(-lo, hh);
  }
  if (li.z <= 0) return false;
  vec3 wi = fr.toWorld(li);
  if (glm::dot(wi, sp.ng) <= 0) return false;
  float pdf;
  vec3 f = evalSurfaceLocal(sp, l, lo, li, pdf);
  if (pdf <= 1e-8f) return false;
  out.wi = wi;
  out.pdf = pdf;
  out.weight = f / pdf;
  return true;
}

}  // namespace plush
