// Soft-body modeling with signed distance fields.
// Characters and props are built from rounded primitives that blend smoothly,
// which suits plush / felt shapes and gives automatic skin weights for free.
#pragma once
#include <string>
#include <vector>

#include "geom/geometry.h"

namespace plush {

enum class PrimType { Ellipsoid, Capsule, RoundCone, RoundBox, Disc };  // Disc: radii.x radius, radii.z half thickness
// Geometric surface relief added to a part (real displacement, not just colour).
enum class SurfacePattern { None, Strands, Knit, Ribbed };

struct SdfPrim {
  std::string name;
  PrimType type = PrimType::Ellipsoid;
  std::string bone;  // bone that drives this primitive (empty = none)
  int boneIndex = -1;
  // Ellipsoid / RoundBox
  vec3 center{0};
  vec3 radii{0.1f};      // ellipsoid radii, or box half size (including rounding)
  quat rotation{1, 0, 0, 0};
  float rounding = 0.01f;
  // Capsule / RoundCone
  vec3 a{0}, b{0, 0.1f, 0};
  float r1 = 0.05f, r2 = 0.05f;
  // Combination
  float blend = 0.02f;   // smooth blend radius with what came before
  bool subtract = false;
  bool mirrorX = false;  // also create a copy mirrored across x = 0
};

struct SdfPart {
  std::string name;
  std::string material;
  float voxelSize = 0.003f;    // metres
  float skinFalloff = 0.012f;  // metres; softness of automatic skin weights
  float noiseAmplitude = 0.0f; // metres; lumpy surface (felted wool, knitted volume)
  float noiseScale = 20.0f;    // 1/metres
  SurfacePattern pattern = SurfacePattern::None;
  float patternAmplitude = 0.0f;  // metres (outward relief)
  float patternScale = 40.0f;     // strands: ridges around the crown; knit/ribbed: columns per metre at 0.1 m radius
  vec3 patternCenter{0};          // strands: crown point; knit/ribbed: point on the vertical axis
  int skinSmoothing = 0;          // Laplacian smoothing passes over the automatic skin weights
  std::vector<SdfPrim> prims;
};

float sdfPrim(const SdfPrim& prim, vec3 p);
float sdfPart(const SdfPart& part, vec3 p);
float patternHeight(const SdfPart& part, vec3 p);  // in [0, 1]
vec3 sdfGradient(const SdfPart& part, vec3 p, float eps);
Aabb partBounds(const SdfPart& part);

// Replaces each mirrorX primitive by itself plus its mirror (".L" <-> ".R" bones).
std::vector<SdfPrim> expandMirrors(const std::vector<SdfPrim>& prims);
std::string mirrorName(const std::string& name);

// Polygonises the zero level set (surface nets, projected onto the surface).
// voxelScale > 1 gives a coarser, faster mesh (previews).
// cullPrims: near the surface, each 8^3 brick only evaluates primitives within reach (much faster for parts
// with many primitives; deviation from exhaustive evaluation is bounded by a unit test).
Mesh meshSdfPart(const SdfPart& part, float voxelScale = 1.0f, bool cullPrims = true);

}  // namespace plush
