// Scenes (shots): objects, characters, lights, camera and animation, stored
// as JSON. The evaluator turns a scene + frame number into a FrameSnapshot.
#pragma once
#include <filesystem>
#include <map>
#include <optional>

#include "anim/animation.h"
#include "model/character.h"

namespace plush {

struct ObjectDesc {
  enum class Kind { Box, Sdf, PaperBoat };
  std::string name;
  Kind kind = Kind::Box;
  std::string material;
  vec3 boxMin{-0.5f}, boxMax{0.5f};  // Box (world space)
  SdfPart part;                       // Sdf (object space)
  vec3 position{0};
  float yawDeg = 0;
  float scale = 1;
  std::optional<FuzzLayer> fuzz;      // optional surface fuzz (rugs, cushions ...)
};

struct CharacterDesc {
  std::string name;
  std::string asset;  // path relative to the scene file
  vec3 position{0};
  float yawDeg = 0;
};

struct Scene {
  std::string name;
  std::filesystem::path path;  // where it was loaded from / saved to
  FrameRate rate;
  int frameStart = 1, frameEnd = 48;
  RenderSettings render;
  Camera camera;
  std::vector<Material> materials;
  std::vector<Light> lights;
  std::vector<ObjectDesc> objects;
  std::vector<CharacterDesc> characters;
  Clip animation;
};

Result<Scene> loadScene(const std::filesystem::path& path);
Json sceneToJson(const Scene& scene);
Result<void> saveScene(const Scene& scene, const std::filesystem::path& path);

Mesh makeBoxMesh(vec3 lo, vec3 hi);
Mesh makePaperBoatMesh();

struct EvalOptions {
  float voxelScale = 1.0f;
  float fuzzDensity = 1.0f;
  bool fuzz = true;
};

class SceneEvaluator {
 public:
  Result<void> load(const Scene& scene, const EvalOptions& options);
  std::shared_ptr<FrameSnapshot> evaluate(double frame) const;
  const Scene& scene() const { return scene_; }
  Scene& mutableScene() { return scene_; }
  // Character data (for editors).
  struct CharacterInstance {
    CharacterAsset asset;
    CharacterRig rig;
    std::vector<int> meshMaterial, fuzzMaterial, lockMaterial;
  };
  const std::vector<CharacterInstance>& characters() const { return characters_; }
  int materialIndex(const std::string& name) const;
  // Replaces a character's asset (after in-app editing) and rebuilds its rig.
  Result<void> rebuildCharacter(size_t index, const CharacterAsset& asset, const EvalOptions& options);
  // Replaces material parameters by name (in-app look development).
  void updateMaterial(const Material& m);

 private:
  struct ObjectGeometry {
    std::shared_ptr<Mesh> local;
    int material = 0;
    std::optional<SurfaceFibers> fuzz;
    int fuzzMaterial = 0;
  };
  Scene scene_;
  std::vector<Material> materials_;
  std::map<std::string, int> materialIndex_;
  std::vector<ObjectGeometry> objects_;
  std::vector<CharacterInstance> characters_;
};

}  // namespace plush
