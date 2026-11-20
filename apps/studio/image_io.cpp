#include "image_io.h"

#include <format>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include <stb_image_write.h>
#define STB_IMAGE_IMPLEMENTATION
#include <stb_image.h>

namespace plush::studio {

Result<void> writePng(const std::filesystem::path& path, int width, int height, const std::vector<uint8_t>& rgb) {
  std::error_code ec;
  if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
  if (!stbi_write_png(path.string().c_str(), width, height, 3, rgb.data(), width * 3))
    return fail(std::format("failed to write '{}'", path.string()));
  return {};
}

Result<std::vector<uint8_t>> readImageRgb8(const std::filesystem::path& path, int& width, int& height) {
  int comp = 0;
  unsigned char* data = stbi_load(path.string().c_str(), &width, &height, &comp, 3);
  if (!data) return fail(std::format("cannot read image '{}'", path.string()));
  std::vector<uint8_t> out(data, data + size_t(width) * size_t(height) * 3);
  stbi_image_free(data);
  return out;
}

}  // namespace plush::studio
