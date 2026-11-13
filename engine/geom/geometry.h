// Shared data model between scene evaluation and rendering: meshes, fibers,
// materials, lights, camera and the per-frame snapshot. No behaviour here.
#pragma once
#include <memory>
#include <string>
#include <vector>

#include "core/math.h"

namespace plush {

struct Aabb {
  vec3 lo{1e30f}, hi{-1e30f};
  void expand(vec3 p) { lo = glm::min(lo, p); hi = glm::max(hi, p); }
  void expand(const Aabb& b) { lo = glm::min(lo, b.lo); hi = glm::max(hi, b.hi); }
  bool valid() const { return lo.x <= hi.x; }
  vec3 extent() const { return hi - lo; }
  vec3 center() const { return 0.5f * (lo + hi); }
};

// Triangle mesh. `pref` is the rest-pose position used for procedural
// textures so that patterns stick to deforming surfaces.
struct Mesh {
  std::vector<vec3> positions;
  std::vector<vec3> normals;
  std::vector<vec3> pref;
  std::vector<uint32_t> indices;  // 3 per triangle
  size_t triangleCount() const { return indices.size() / 3; }
  Aabb bounds() const {
    Aabb b;
    for (auto& p : positions) b.expand(p);
    return b;
  }
};

// Fibers as round linear curves: xyz + radius per control point.
// `segmentStarts[i]` is the index of the first control point of segment i.
struct FiberSet {
  std::vector<vec4> points;
  std::vector<uint32_t> segmentStarts;
  size_t fiberCount = 0;
};

enum class MaterialType { Standard, Plush, Fiber };
enum class TextureType { None, Noise, Wood, Wall, Iris, Blush, Knit };

struct ProceduralTexture {
  TextureType type = TextureType::None;
  vec3 color2{0.5f};
  vec3 color3{0.0f};
  float scale = 1.0f;
  float amount = 0.5f;
  vec4 params{0.0f};
  std::vector<vec4> spots;  // xyz + radius (iris centres, blush spots ...)
};

struct Material {
  std::string name;
  MaterialType type = MaterialType::Standard;
  vec3 baseColor{0.8f};
  float roughness = 0.5f;
  float ior = 1.5f;
  float specular = 1.0f;     // scales the dielectric specular lobe
  float coat = 0.0f;         // clear coat weight
  float coatRoughness = 0.08f;
  float sheen = 0.0f;        // velvet / felt sheen weight
  vec3 sheenColor{1.0f};
  float sheenRoughness = 0.4f;
  // Fiber (Chiang et al. 2016) parameters.
  float betaM = 0.3f;
  float betaN = 0.3f;
  float alphaDeg = 2.0f;
  ProceduralTexture texture;
};

struct Light {
  enum class Type { Sun, Rect, Sky };
  Type type = Type::Sun;
  vec3 color{1.0f};
  float intensity = 1.0f;     // sun: irradiance; rect/sky: radiance scale
  vec3 direction{0, -1, 0};   // sun: direction light travels
  float angleDeg = 2.0f;      // sun: angular diameter
  vec3 corner{0}, edgeU{1, 0, 0}, edgeV{0, 1, 0};  // rect: emits towards cross(edgeU, edgeV)
};

struct Camera {
  vec3 position{0, 1, 3};
  vec3 target{0, 1, 0};
  vec3 up{0, 1, 0};
  float focalMm = 50.0f;
  float sensorWidthMm = 36.0f;
  float fStop = 2.8f;          // <= 0 disables depth of field
  float focusDistance = -1.0f; // <= 0: distance to target
  int blades = 6;
  float bladeRotationDeg = 15.0f;
};

struct RenderSettings {
  int width = 960;
  int height = 540;
  int spp = 64;
  int maxDepth = 10;
  float exposureEV = 0.0f;
  bool denoise = true;
  uint32_t seed = 1;
  float clamp = 12.0f;  // max luminance of an indirect sample (firefly control)
};

struct SnapshotMesh {
  std::shared_ptr<const Mesh> mesh;
  int material = 0;
};
struct SnapshotFibers {
  std::shared_ptr<const FiberSet> fibers;
  int material = 0;
};

// Everything needed to render one moment in time. Immutable once built.
struct FrameSnapshot {
  double frame = 0;
  std::vector<Material> materials;
  std::vector<SnapshotMesh> meshes;
  std::vector<SnapshotFibers> fibers;
  std::vector<Light> lights;
  Camera camera;
};

}  // namespace plush
