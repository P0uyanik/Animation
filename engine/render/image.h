// Image output: denoising, tone mapping (AgX-style filmic), PNG / HDR files.
#pragma once
#include <filesystem>

#include "core/core.h"
#include "render/pathtracer.h"

namespace plush {

bool denoiserAvailable();
// Denoises `out.color` in place using albedo/normal guides. Returns false if unavailable.
// blend: 1 = fully denoised, < 1 mixes back some of the noisy image (keeps fibre texture).
bool denoise(RenderOutput& out, float blend = 1.0f);

struct ToneMapSettings {
  float exposureEV = 0.0f;
  float saturation = 1.12f;  // gentle "look" on top of the neutral filmic curve
};
std::vector<uint8_t> toneMapToSrgb8(const ImageRGB& img, const ToneMapSettings& tm);
Result<void> writePng(const std::filesystem::path& path, int width, int height, const std::vector<uint8_t>& rgb);
// Reads an 8-bit RGB image (PNG/JPEG/...).
Result<std::vector<uint8_t>> readImageRgb8(const std::filesystem::path& path, int& width, int& height);
// Root-mean-square difference of two 8-bit RGB images in [0, 1]; -1 if sizes differ.
double imageRmse(const std::vector<uint8_t>& a, const std::vector<uint8_t>& b);
Result<void> writeHdr(const std::filesystem::path& path, const ImageRGB& img);

}  // namespace plush
