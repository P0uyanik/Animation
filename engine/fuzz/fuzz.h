// Fibers: procedural surface fuzz (felt, fleece, suede, wool) and yarn locks
// (twisted fiber bundles around a solid core) for stylized wool hair.
#pragma once
#include <memory>

#include "geom/geometry.h"

namespace plush {

struct FuzzParams {
  float density = 50.0f;      // fibers per cm^2
  float length = 0.003f;      // metres
  float lengthJitter = 0.4f;  // 0..1
  float radius = 3e-5f;       // metres at the root
  float tilt = 0.5f;          // 0 = straight out of the surface, 1 = lying flat
  float curl = 0.3f;          // bending / waviness
  float comb = 0.0f;          // 0..1 how much fibers lean away from combOrigin
  vec3 combOrigin{0};
  int segments = 3;
  uint32_t seed = 1;
  float strayFraction = 0.0f;  // share of long flyaway fibres (soft halo)
  float strayLength = 3.0f;    // their length multiplier
};

// Fibers bound to a mesh surface; deform with the mesh.
struct SurfaceFibers {
  int pointsPerFiber = 0;
  std::vector<uint32_t> triangle;
  std::vector<vec2> bary;
  std::vector<vec4> local;  // per point: offset in the root frame (T, B, N) + radius
  size_t fiberCount() const { return triangle.size(); }
};

SurfaceFibers generateSurfaceFibers(const Mesh& rest, const FuzzParams& params, float densityScale = 1.0f);
std::shared_ptr<FiberSet> deformSurfaceFibers(const SurfaceFibers& fibers, const Mesh& deformed);

// Wavy yarn locks hanging from a head (rest space).
struct LockParams {
  vec3 headCenter{0, 0.82f, 0};
  vec3 headRadii{0.17f, 0.16f, 0.165f};
  int count = 28;
  float azimuthMinDeg = -115.0f;  // 0 = straight back (-z), positive = towards +x
  float azimuthMaxDeg = 115.0f;
  float elevationDeg = 12.0f;     // root height above the head centre (degrees on the scalp)
  float lengthMin = 0.20f, lengthMax = 0.30f;
  float lockRadius = 0.014f;
  float coreRatio = 0.7f;         // solid core tube radius / lock radius
  int fibersPerLock = 300;
  float fiberRadius = 7e-5f;
  float twist = 10.0f;            // turns per metre
  float wave = 0.012f;            // metres
  float waveLength = 0.09f;
  float headBottom = 0.68f;       // below this y the locks clear the body
  float bodyClearance = 0.115f;
  float sideClearance = 0.045f;
  float frizz = 0.0015f;
  int segments = 24;
  uint32_t seed = 7;
};
FiberSet generateLocks(const LockParams& params, float densityScale = 1.0f);

std::shared_ptr<FiberSet> transformFibers(const FiberSet& fibers, const mat4& m);

// ---------------------------------------------------------------- explicit locks / curves
// A hand-placed lock (or any tube: lash, glasses frame, drawstring): a smooth curve through
// control points with a tapered radius, optional curl (helix around the path), a solid core
// and an optional fibre halo grown from the core surface.
struct LockCurve {
  std::vector<vec3> points;  // rest space, root first
  float rootRadius = 0.012f;
  float tipRadius = 0.003f;
  float curlRadius = 0.0f;   // helix radius around the path (curls)
  float curlTurns = 0.0f;
  float curlPhase = 0.0f;
};
struct LockGroupParams {
  int samples = 32;            // curve samples per lock (more for tight curls)
  float fuzzDensity = 0.0f;    // halo fibres per cm^2 of core surface (0 = none)
  float fuzzLength = 0.004f;
  float fuzzRadius = 3e-5f;
  float fuzzTilt = 0.6f;       // 0 = straight out, 1 = lying along the lock towards the tip
  float strayFraction = 0.05f;
  float strayLength = 2.5f;
  bool roundTip = true;
  uint32_t seed = 1;
};
std::vector<vec3> sampleCatmullRom(const std::vector<vec3>& points, int samples);
// Appends the cores (pinned curves) and the halo fibres of every lock.
void generateLockGroup(const LockGroupParams& params, const std::vector<LockCurve>& locks, float densityScale,
                       FiberSet& cores, FiberSet& fibers);

// Coverage-preserving level of detail: keeps ~1/k of the curves (deterministic subset,
// pinned curves always kept) and multiplies their radius by k.
std::shared_ptr<FiberSet> thinFibers(const FiberSet& fibers, float k);
// LOD factor for fibres of root radius `radius` seen at `distance` with `metresPerPixelAt1m` footprint.
float fiberLodFactor(float radius, float distance, float metresPerPixelAt1m, float maxFactor = 6.0f);

}  // namespace plush
