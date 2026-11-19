// PNG read/write for Plush Studio (screenshots, production frame view). stb only; no renderer dependency (T-142).
#pragma once
#include <cstdint>
#include <filesystem>
#include <vector>

#include "core/core.h"

namespace plush::studio {

Result<void> writePng(const std::filesystem::path& path, int width, int height, const std::vector<uint8_t>& rgb);
Result<std::vector<uint8_t>> readImageRgb8(const std::filesystem::path& path, int& width, int& height);

}  // namespace plush::studio
