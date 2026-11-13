#include "render/image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include <stb_image_write.h>

#ifdef PLUSH_HAS_OIDN
#include <OpenImageDenoise/oidn.hpp>
#endif

namespace plush {

bool denoiserAvailable() {
#ifdef PLUSH_HAS_OIDN
  return true;
#else
  return false;
#endif
}

bool denoise(RenderOutput& out, float blend) {
#ifdef PLUSH_HAS_OIDN
  static oidn::DeviceRef device = [] {
    oidn::DeviceRef d = oidn::newDevice(oidn::DeviceType::CPU);
    d.commit();
    return d;
  }();
  const int w = out.color.width, h = out.color.height;
  if (w == 0 || h == 0) return false;
  std::vector<vec3> result(out.color.pixels.size());
  oidn::FilterRef filter = device.newFilter("RT");
  filter.setImage("color", out.color.pixels.data(), oidn::Format::Float3, size_t(w), size_t(h));
  filter.setImage("albedo", out.albedo.pixels.data(), oidn::Format::Float3, size_t(w), size_t(h));
  filter.setImage("normal", out.normal.pixels.data(), oidn::Format::Float3, size_t(w), size_t(h));
  filter.setImage("output", result.data(), oidn::Format::Float3, size_t(w), size_t(h));
  filter.set("hdr", true);
  filter.set("quality", oidn::Quality::High);
  filter.commit();
  filter.execute();
  const char* message = nullptr;
  if (device.getError(message) != oidn::Error::None) {
    logError("denoiser: {}", message ? message : "unknown error");
    return false;
  }
  blend = std::clamp(blend, 0.0f, 1.0f);
  for (size_t i = 0; i < result.size(); ++i) result[i] = glm::mix(out.color.pixels[i], result[i], blend);
  out.color.pixels = std::move(result);
  return true;
#else
  (void)out;
  (void)blend;
  return false;
#endif
}

namespace {
// Minimal AgX (after Benjamin Wrensch), sRGB primaries.
vec3 agx(vec3 c) {
  const mat3 inset(0.842479062253094f, 0.0423282422610123f, 0.0423756549057051f, 0.0784335999999992f, 0.878468636469772f,
                   0.0784336f, 0.0792237451477643f, 0.0791661274605434f, 0.879142973793104f);
  const mat3 outset(1.19687900512017f, -0.0528968517574562f, -0.0529716355144438f, -0.0980208811401368f,
                    1.15190312990417f, -0.0980434501171241f, -0.0990297440797205f, -0.0989611768448433f,
                    1.15107367264116f);
  const float minEv = -12.47393f, maxEv = 4.026069f;
  c = inset * glm::max(c, vec3(1e-10f));
  c = glm::clamp(glm::log2(c), vec3(minEv), vec3(maxEv));
  c = (c - minEv) / (maxEv - minEv);
  vec3 x2 = c * c, x4 = x2 * x2;
  c = 15.5f * x4 * x2 - 40.14f * x4 * c + 31.96f * x4 - 6.868f * x2 * c + 0.4298f * x2 + 0.1191f * c - 0.00232f;
  return glm::clamp(outset * c, vec3(0), vec3(1));  // display-encoded
}
}  // namespace

std::vector<uint8_t> toneMapToSrgb8(const ImageRGB& img, const ToneMapSettings& tm) {
  std::vector<uint8_t> out(img.pixels.size() * 3);
  float scale = std::exp2(tm.exposureEV);
  parallelFor(img.pixels.size(), [&](size_t i) {
    vec3 c = img.pixels[i] * scale;
    float l = luminance(c);
    c = glm::max(vec3(0), vec3(l) + (c - vec3(l)) * tm.saturation);
    vec3 d = agx(c);
    for (int k = 0; k < 3; ++k) out[3 * i + size_t(k)] = uint8_t(std::clamp(d[k] * 255.0f + 0.5f, 0.0f, 255.0f));
  }, 4096);
  return out;
}

Result<void> writePng(const std::filesystem::path& path, int width, int height, const std::vector<uint8_t>& rgb) {
  std::error_code ec;
  if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
  if (!stbi_write_png(path.string().c_str(), width, height, 3, rgb.data(), width * 3))
    return fail(std::format("failed to write '{}'", path.string()));
  return {};
}

Result<void> writeHdr(const std::filesystem::path& path, const ImageRGB& img) {
  std::error_code ec;
  if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
  if (!stbi_write_hdr(path.string().c_str(), img.width, img.height, 3, &img.pixels[0].x))
    return fail(std::format("failed to write '{}'", path.string()));
  return {};
}

}  // namespace plush
