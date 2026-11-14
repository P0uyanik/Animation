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
  std::string coreMaterial;  // material of the solid core tubes (empty = same as fibres)
  std::string bone = "head";
  LockParams params;
};

// A facial (or any) shape target defined by changing primitives of one part.
// Built into a morph target with the same topology by projecting the rest mesh
// onto the modified surface. Weight track: "<character>/expr.<name>".
struct Expression {
  std::string name;
  std::string part;
  std::vector<Json> set;  // {"prim": name, ...fields to override}; .L overrides also update .R
  std::vector<Json> add;  // extra primitives (same format as part primitives)
};

// A group of explicit locks / tubes attached to one bone (hair locks, lashes, frames, strings).
struct LockGroup {
  std::string name;
  std::string bone = "head";
  std::string material;      // halo fibres
  std::string coreMaterial;  // core tubes (empty = material)
  LockGroupParams params;
  std::vector<LockCurve> locks;
};

// Default walk step per metre of leg (thigh -> shin -> foot): 0.11 m for the 0.3451 m legs of the original chibi
// characters, so their walks are unchanged; other proportions scale.
constexpr float kDefaultWalkStepScale = 0.11f / 0.3451f;
// Walk step length for a character (explicit length, else scale x leg length, else 0.11 m without legs).
float walkStep(const struct CharacterAsset& c);
// Morph name for an engine expression name ("" if the character has none).
std::string resolveExpression(const struct CharacterAsset& c, const std::string& name, const std::vector<std::string>& morphNames);

struct CharacterAsset {
  std::string name;
  std::vector<LockGroup> lockGroups;          // mirrors expanded
  std::map<std::string, vec3> defaultPose;    // bone -> euler degrees when no track (personality)
  std::map<std::string, float> defaultExpressions;
  // Engine expression name (e.g. "blink", "smile") -> this character's morph name. Empty = morph names are used as
  // given. A "blink" entry naming a morph makes the life layer blink with that morph instead of rotating lid bones.
  std::map<std::string, std::string> expressionMap;
  float walkStepLength = 0.0f;  // > 0: walk step in metres
  float walkStepScale = 0.0f;   // > 0: walk step = scale * leg length (default: kDefaultWalkStepScale)
  bool dualQuaternion = false;  // skinning method (false = linear blend)
  std::vector<Expression> expressions;
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
Json primToJson(const SdfPrim& p);
Json partToJson(const SdfPart& part);
// Saves the expanded asset (mirror copies are written out explicitly).
Json characterToJson(const CharacterAsset& c);
Result<LockGroup> lockGroupFromJson(const Json& j);
Json lockGroupToJson(const LockGroup& g);
// Re-resolves primitive bone indices after editing.
Result<void> resolveBones(CharacterAsset& c);

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
  FiberSet rest;  // fibres around the cores, or everything if no core material
  std::string coreMaterial;
  FiberSet cores;
};
struct MorphTarget {
  std::string name;
  int mesh = 0;
  std::vector<uint32_t> vertices;
  std::vector<vec3> dpos, dnrm;
};
struct CharacterRig {
  std::vector<MorphTarget> morphs;
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
  std::vector<std::shared_ptr<FiberSet>> lockCores;  // same order as rig.locks (may be empty sets)
};
// morphWeights: one per rig.morphs entry (may be empty).
PosedCharacter poseCharacter(const CharacterRig& rig, const std::vector<mat4>& skin,
                             const std::vector<float>& morphWeights = {}, bool dualQuaternion = false);
void smoothSkinWeights(const Mesh& mesh, int boneCount, int iterations, std::vector<glm::ivec4>& joints,
                       std::vector<vec4>& weights);
// Applies an expression's overrides/additions to a copy of the part.
Result<SdfPart> applyExpression(const SdfPart& part, const Expression& e);

}  // namespace plush
