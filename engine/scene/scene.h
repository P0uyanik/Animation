// Scenes (shots): objects, characters, lights, camera and animation, stored
// as JSON. The evaluator turns a scene + frame number into a FrameSnapshot.
#pragma once
#include <filesystem>
#include <map>
#include <optional>

#include "anim/animation.h"
#include "model/character.h"
#include "model/clip.h"
#include "scene/asset_library.h"

namespace plush {

struct ObjectDesc {
  enum class Kind { Box, Sdf, PaperBoat, Water };
  std::string name;
  Kind kind = Kind::Box;
  std::string material;
  vec3 boxMin{-0.5f}, boxMax{0.5f};  // Box (world space)
  SdfPart part;                       // Sdf (object space)
  vec3 position{0};
  float yawDeg = 0;
  float scale = 1;
  std::optional<FuzzLayer> fuzz;      // optional surface fuzz (rugs, cushions ...)
  // Attachment: between attachFrame and releaseFrame the object follows a character bone
  // ("<character>/<bone>"), keeping its offset at attachFrame (no jump).
  std::string attachTo;
  double attachFrame = 0, releaseFrame = 1e9;
  // Water: a rippling height-field surface (object space, y = 0 is the rest level).
  vec2 waterHalfSize{0.3f, 0.2f};
  int waterResolution = 96;
  std::vector<vec4> ripples;  // x, z, start frame, amplitude
  // Floating: from floatFrame on, the object rides the named water surface.
  std::string floatOn;
  double floatFrame = 0;
};

struct CharacterDesc {
  std::string name;
  std::string asset;  // path relative to the scene file
  vec3 position{0};
  float yawDeg = 0;
  LifeParams life;    // procedural breathing, weight shift, blinks, head follows gaze (off unless set)
};

struct PropDesc {
  std::string id;
  AssetTransform transform;
  std::optional<std::string> parentSocket;
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
  std::vector<PropDesc> props;
  std::vector<CharacterDesc> characters;
  Clip animation;
  // High-level actions ("look", "reach", "expression", "walk"), compiled into generated tracks when the scene is
  // loaded for evaluation (see actions.cpp). Saved as written.
  Json actions = Json::array();
  // Automatic camera ("director"): when set (an object, possibly empty), camera shots are planned from the actions.
  // Hand-keyed camera tracks always win. See actions.cpp.
  Json director = nullptr;
};

Result<Scene> loadScene(const std::filesystem::path& path);
Json sceneToJson(const Scene& scene);
Result<void> saveScene(const Scene& scene, const std::filesystem::path& path);

Mesh makeBoxMesh(vec3 lo, vec3 hi);
mat4 objectMatrix(vec3 pos, float yawDeg, float scale);
Mesh makePaperBoatMesh();

struct EvalOptions {
  float voxelScale = 1.0f;
  float fuzzDensity = 1.0f;
  bool fuzz = true;
  int lodWidth = 0;  // render width in pixels for fibre level of detail (0 = off)
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
    std::vector<int> meshMaterial, fuzzMaterial, lockMaterial, coreMaterial;
    bool imported = false;  // loaded from an imported-character package (not built from SDF parts)
  };
  const std::vector<CharacterInstance>& characters() const { return characters_; }
  // Non-fatal problems found while compiling actions (e.g. an expression a character does not have).
  const std::vector<std::string>& warnings() const { return warnings_; }
  int materialIndex(const std::string& name) const;
  // Replaces a character's asset (after in-app editing) and rebuilds its rig.
  Result<void> rebuildCharacter(size_t index, const CharacterAsset& asset, const EvalOptions& options);
  // Replaces material parameters by name (in-app look development).
  void updateMaterial(const Material& m);
  // Recompiles the scene's actions into generated tracks (called by load; call again after editing actions).
  Result<void> compileActions();
  // Bone frames (world space) of character c at a frame, after constraints.
  std::vector<mat4> characterGlobals(size_t c, double frame, Pose* poseOut = nullptr) const;
  mat4 objectWorld(size_t o, double frame) const;

 private:
  float waterHeight(size_t waterObject, vec2 localXZ, double frame) const;
  struct ObjectGeometry {
    std::shared_ptr<Mesh> local;
    int material = 0;
    std::optional<SurfaceFibers> fuzz;
    int fuzzMaterial = 0;
  };
  Scene scene_;
  EvalOptions options_;
  std::vector<Material> materials_;
  std::map<std::string, int> materialIndex_;
  std::vector<ObjectGeometry> objects_;
  std::vector<CharacterInstance> characters_;
  std::vector<std::string> warnings_;
  static std::string blinkMorph(const CharacterInstance& ci);
 public:
  // Camera at a frame (scene camera + camera.position/target/lens tracks).
  Camera cameraAt(double frame) const;
  // Morph control weight as rendered before in-between expansion: the animated channel, and for the character's
  // blink morph the life-layer blink (max of both). This is what a facial control is set to.
  float morphControlWeight(size_t c, const std::string& morph, double frame) const;
  // Effective life parameters of character c (scene values + the character's blink timing).
  LifeParams lifeParams(size_t c) const;
  // Animated weight of morph `morph` of character c at `frame`.
  float expressionWeight(size_t c, const std::string& morph, double frame) const;
 private:
  std::vector<ObjectDesc> authoredObjects_;  // objects as written, before actions set attachments and ripples
  // Clip actions (type "clip", model/clip.h): per character, in start order; a "base" clip replaces the default pose
  // for the whole shot. Walk spans: frames where a walk owns the legs, hips and root.
  struct ClipLayer {
    std::shared_ptr<const ClipData> clip;
    ClipBinding binding;
    double start = 0, end = 1e30, speed = 1, weight = 1, blendIn = 6, blendOut = 6;
    bool mirror = false, base = false;
    // Layer tier (application order): 0 base clip, 1 emotion posture / gesture (action "emotion"), 2 clip actions.
    int tier = 2;
    bool linear = false;  // linear instead of smoothstep blend ramps (emotion intensity curve "linear")
    double envelope(double frame) const;  // weight x blend in/out at a scene frame
    double clipFrame(double frame, double sceneFps) const;
  };
  std::vector<std::vector<ClipLayer>> clipLayers_;
  std::vector<std::vector<std::pair<double, double>>> walkSpans_;
  std::map<std::string, std::shared_ptr<const ClipData>> clipCache_;
  void applyClips(size_t c, double frame, Pose& pose, float& yawOffset) const;
  void applyClipFingers(size_t c, double frame, Pose& pose) const;
 public:
  // Clip playback data of character c for a reference pose: the package's generated block if it matches the
  // reference version, else derived from the skeleton (same rules).
  RetargetData retargetData(size_t c, const ReferencePose& ref) const;
  bool hasClipLayers(size_t c) const { return c < clipLayers_.size() && !clipLayers_[c].empty(); }
};

}  // namespace plush
