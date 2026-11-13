// Characters: a skeleton, soft SDF parts (skin, clothes, hair cap ...),
// surface fuzz layers and yarn hair locks. Built once, then posed per frame.
#pragma once
#include <filesystem>
#include <memory>

#include "anim/animation.h"
#include "fuzz/fuzz.h"
#include "geom/json_io.h"
#include "model/sdf.h"

namespace plush {

struct FuzzLayer {
  std::string part;
  std::string material;
  FuzzParams params;
};

struct LockLayer {
  std::string material;
  std::string bone = "head";
  LockParams params;
};

struct CharacterAsset {
  std::string name;
  Skeleton skeleton;
  std::vector<SdfPart> parts;  // mirrors expanded, bone indices resolved
  std::vector<FuzzLayer> fuzz;
  std::vector<LockLayer> locks;
  std::vector<Material> materials;
};

Result<CharacterAsset> characterFromJson(const Json& j);
Result<CharacterAsset> loadCharacter(const std::filesystem::path& path);
Result<SdfPrim> primFromJson(const Json& j);
Result<SdfPart> partFromJson(const Json& j);

struct SkinnedMesh {
  std::string part;
  std::string material;
  Mesh rest;
  std::vector<glm::ivec4> joints;
  std::vector<vec4> weights;
};
struct BoundFuzz {
  int mesh = 0;
  std::string material;
  SurfaceFibers fibers;
};
struct BoundLocks {
  int bone = 0;
  std::string material;
  FiberSet rest;
};
struct CharacterRig {
  std::vector<SkinnedMesh> meshes;
  std::vector<BoundFuzz> fuzz;
  std::vector<BoundLocks> locks;
};

struct BuildOptions {
  float voxelScale = 1.0f;   // >1 = coarser meshes (fast previews)
  float fuzzDensity = 1.0f;  // multiplier on all fiber counts
  bool fuzz = true;
};
CharacterRig buildCharacter(const CharacterAsset& asset, const BuildOptions& options);

// Automatic skin weights from the primitives that built the part.
void computeSkinWeights(const SdfPart& part, int boneCount, const Mesh& mesh, std::vector<glm::ivec4>& joints,
                        std::vector<vec4>& weights);

struct PosedCharacter {
  std::vector<std::shared_ptr<Mesh>> meshes;     // same order as rig.meshes
  std::vector<std::shared_ptr<FiberSet>> fuzz;   // same order as rig.fuzz
  std::vector<std::shared_ptr<FiberSet>> locks;  // same order as rig.locks
};
PosedCharacter poseCharacter(const CharacterRig& rig, const std::vector<mat4>& skin);

}  // namespace plush
