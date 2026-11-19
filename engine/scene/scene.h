// Scenes (shots): objects, characters, lights, camera and animation, stored
// as JSON. The evaluator turns a scene + frame number into a FrameSnapshot.
#pragma once
#include <filesystem>
#include <map>
#include <memory>
#include <mutex>
#include <optional>

#include "anim/animation.h"
#include "anim/body_mechanics.h"
#include "anim/personality.h"
#include "anim/principles.h"
#include "model/character.h"
#include "model/clip.h"
#include "scene/acting.h"
#include "scene/asset_library.h"
#include "scene/face_layer.h"
#include "scene/interaction.h"

namespace plush {

struct SampledLayerCurves;  // scene/emotion.h (T-097A)

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
  Json dynamics;      // secondary-motion override of the package's "dynamics" block (null = as the package says)
  // Without a base clip the shared "idle_relaxed" clip plays as the character's base layer (clip_layers.cpp, T-027).
  // Scene JSON "autoIdle": false opts out.
  bool autoIdle = true;
  // Per-character living-face tunables (T-046, same schema as an emotion's "faceMotion"): a constant layer under the
  // emotions, e.g. from a personality profile (null = the shared neutral face).
  Json faceMotion;
  // Body mechanics (T-045, anim/body_mechanics.h): null / false = off (default); true = shared neutral tuning; an
  // object = {"enabled", "personality": "<profile id>" (content/personality/<id>[.draft].json), and overrides of the
  // BodyMechanicsParams fields by name, "limits": {...}}. Saved as written.
  Json bodyMechanics;
  // Personality profile (T-053, anim/personality.h): null / false = none (default: behaviour as before T-053); a string
  // = profile id (content/personality/<id>[.draft].json, found by walking up from the scene file). It tunes the life
  // layer (blinks, idle amplitude, head lag), the face (rest offsets, expression bias, mouth while watching), clip
  // tempo and, when body mechanics is on without its own "personality", the body mechanics. Saved as written.
  Json personality;
  // Gaze legibility (T-120, opt-in): the character key "gazeLegibility" (see GazeLegibility below). Null = the scene's
  // "gazeLegibility"; false = off for this character. Saved as written.
  Json gazeLegibility;
  // Blink scheduling (T-136, opt-in): the character key "blinkSchedule" (see BlinkSchedule below). Null = the scene's;
  // false = off for this character. Saved as written.
  Json blinkSchedule;
};

// Blink scheduling (T-136 E2, opt-in; absent = off, the behaviour before T-136). Scene key "blinkSchedule" (every
// character with a face layer) and / or character key "blinkSchedule" (that character; its fields win, its key beats
// add to the scene's): true, false or
// {"enabled", "keyBeats": [{"start", "end", "characters": [names] (absent = all), "name"}], "shortBeatFrames",
//  "preferWindowFrames", "actionChanges": true | false | [frames]}.
// Key beats keep the eyes open; blinks prefer gaze shifts and action changes (by default the starts of the
// character's non-look actions, and a pass's contact and release, for giver and receiver); at most one blink per
// short beat. The planning itself is FaceLayer::blinkPlan (scene/face_layer.h). Needs the face layer (life on).
// Characters without one keep their life-layer blinks.
Result<BlinkSchedule> blinkScheduleFromJson(const Json& j, const std::string& character, BlinkSchedule base = {});

// Gaze legibility (T-120, opt-in; absent = off, the behaviour before T-120). Scene key "gazeLegibility" (every
// character) and / or character key "gazeLegibility" (that character; its fields win over the scene's): true, false or
// {"enabled", "rangeDeg": [yaw, pitch], "leadFrames", "turnFrames", "headYawDeg", "headPitchDeg"}.
// When on, for that character:
// - the eyes are limited to rangeDeg relative to the head (the character's spec face.eyes.gaze_range_deg, the sweep its
//   lids are built for), softly while aiming and as a hard clamp after eye darts and gaze bias, so in every frame
//   (blinks included) the pupil stays inside the eye opening;
// - the eyes go to a new target at once; the head starts leadFrames later and eases over turnFrames, and turns only
//   by what the worse-placed (near) eye lacks to reach the target inside its comfortable range, up to headYawDeg /
//   headPitchDeg (default: the character's life.gaze assistYawDeg / assistPitchDeg). This replaces the life layer's
//   head follow and the neck / chest assist. A hand-keyed neck is left alone.
struct GazeLegibility {
  bool enabled = false;
  vec2 rangeDeg{20.0f, 12.0f};  // [yaw, pitch]; the character system's default gaze_range_deg
  float leadFrames = 3.0f;      // frames at 24 fps the eyes move before the head starts
  float turnFrames = 8.0f;      // frames at 24 fps the head's turn eases over
  float headYawDeg = -1.0f;     // most the head turns for a look; negative = life.gaze.assistYawDeg
  float headPitchDeg = -1.0f;   // negative = life.gaze.assistPitchDeg
  // Gaze chain (T-136 E3, opt-in key "chain": true or {"neckYawDeg", "neckPitchDeg", "torsoYawDeg", "torsoPitchDeg",
  // "torsoLagFrames"}; absent = off, the T-120 behaviour). The eyes still lead; beyond their comfortable range the
  // head and neck take over (split between the neck and head bones, up to neck*Deg, at least head*Deg) and, beyond
  // that, the torso (chest and spine, up to torso*Deg, torsoLagFrames after the head), so a look reaches its target.
  // The eyes then aim at the look's exact, live target: a prop's middle ("atProp", the cup), or the midpoint of the
  // partner's eyes ("atCharacter": held eye contact), instead of the 3-frame keyed track.
  bool chain = false;
  float neckYawDeg = 50.0f, neckPitchDeg = 40.0f;
  float torsoYawDeg = 25.0f, torsoPitchDeg = 25.0f;
  float torsoLagFrames = 3.0f;
};
// `j` on top of `base` (the scene's setting under a character's). Null keeps base; an object without "enabled" is on.
Result<GazeLegibility> gazeLegibilityFromJson(const Json& j, GazeLegibility base = {});
// The head's share of a legible look (see GazeLegibility): rotates the neck, before the eyes are aimed.
void turnHeadForGaze(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame, double fps,
                     const mat4& world, Pose& pose, const GazeLegibility& legibility);
// The gaze chain's share of a legible look (T-136, GazeLegibility::chain): torso, then neck and head, before the eyes
// are aimed. `liveOffset` moves the keyed lookAt target onto the exact live target (0 = the track as keyed). Once a
// look has settled (sinceLookStart past its lead and turn), the chain follows a moving target without the lead lag
// (pursuit), easing over turnFrames; sinceLookStart < 0 = always lagged.
void turnChainForGaze(const Skeleton& skeleton, const Clip& clip, const std::string& prefix, double frame, double fps,
                      const mat4& world, Pose& pose, const GazeLegibility& legibility, vec3 liveOffset,
                      double sinceLookStart = -1);
// Aims every "eye.*" bone exactly at `target` (blended by weight 0..1).
void aimEyesAt(const Skeleton& skeleton, const mat4& world, Pose& pose, vec3 target, float weight);
// Hard clamp of every "eye.*" bone's direction to +-rangeDeg [yaw, pitch] relative to the head.
void clampEyesToGazeRange(const Skeleton& skeleton, const mat4& world, Pose& pose, vec2 rangeDeg);

struct PropParent {
  enum class Kind { Character, Prop };
  Kind kind = Kind::Character;
  std::string name;
  std::string socket;
};

struct PropParentSwitch {
  double frame = 0;
  // null detaches the prop at its current world transform.
  std::optional<PropParent> parent;
};

struct PropDesc {
  std::string name;
  std::string id;
  AssetTransform transform;
  std::optional<PropParent> parent;
  std::vector<PropParentSwitch> parentSwitch;
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
  // Animation principles (T-061, anim/principles.h): null / true = on with the shared defaults, false = off (the
  // behaviour before T-061), an object = field overrides. Saved as written.
  Json animPrinciples = nullptr;
  // Interaction options (T-096, opt-in): the scene key "interaction" (absent = all off, the behaviour before T-096).
  // Parsed and checked by interactionOptionsFromJson; saved as written.
  Json interaction = nullptr;
  // Timing profile (T-104; the default since T-104d): the scene key "timing" names content/timing/<name>.timing.json
  // (anim/personality.h TimingProfile). Absent / null = kDefaultTimingProfile ("calibrated"); "none" = the shared
  // interaction timing defaults (the behaviour before T-104). It only sets the defaults of action frames a scene leaves
  // out; frames written in an action always win. Saved as written (an absent key stays absent).
  Json timing = nullptr;
  static constexpr const char* kDefaultTimingProfile = "calibrated";
  // The profile name the scene resolves to: the key's value, kDefaultTimingProfile when absent, empty for "none".
  std::string timingProfile() const {
    if (!timing.is_string()) return kDefaultTimingProfile;
    const std::string name = timing.get<std::string>();
    return name == "none" ? std::string() : name;
  }
  // Reaction events (T-097D, opt-in): the scene key "events" (absent = no reactions, the behaviour before T-097D). Each
  // event is planned per reacting character (scene/reaction.h) and played as generated look, blended emotion and
  // gesture actions (actions.cpp; docs/PRODUCTION_PIPELINE.md "Scene events"). Checked by reactionEventsFromJson;
  // saved as written.
  Json events = nullptr;
  // Gaze legibility (T-120, opt-in): the scene key "gazeLegibility" (absent = off). See GazeLegibility; saved as written.
  Json gazeLegibility = nullptr;
  // Blink scheduling (T-136, opt-in): the scene key "blinkSchedule" (absent = off). See BlinkSchedule; saved as written.
  Json blinkSchedule = nullptr;
};

// One entry of a scene's "events" list (T-097D): the event and the characters that react to it (empty = every scene
// character). Fields: "time" (seconds from frameStart), "kind" ("object_appears", "partner_acts", "success", "failure",
// "custom"; default "custom"), "name", "source" (a character or object name, "" = the scene), "salience" (0..1,
// default 1), "characters" (optional list of names).
struct SceneEvent {
  ReactionEvent event;
  std::vector<std::string> characters;
};
Result<std::vector<SceneEvent>> reactionEventsFromJson(const Json& j);

// The scene's "interaction" block (T-096). Every field is optional and off by default:
//   "headVolumes": bool      head and hair volumes in each character's collision body (scene/collision.h); the
//                            characters' heads keep at least headClearance apart (a small, rate-limited neck tilt
//                            away from the other head, interaction.cpp)
//   "headClearance": metres  clearance kept between two characters' head volumes (default 0.03: wool and hair fibres stand off the mesh, in [0, 0.1])
//   "followSharedProp": bool hand-over: while both hands hold the prop (receiver's contact -> giver's release) the
//                            giver's palm follows its own socket, wherever the receiver's hand carries the prop
//   "visibleGrip": bool      grasps keep the held prop visible from the shot camera: the palm meets the prop on its
//                            socket's far side from the camera when the prop has a mirrored socket ("<socket>_far"
//                            is not needed: see interaction.cpp)
struct InteractionOptions {
  bool headVolumes = false;
  float headClearance = 0.03f;
  bool followSharedProp = false;
  bool visibleGrip = false;
};
Result<InteractionOptions> interactionOptionsFromJson(const Json& j);

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
  Scene& mutableScene() {
    resetDynamics();  // edits may change what drives the spring chains
    return scene_;
  }
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
  // Actions generated from the scene's "events" by the last compile (T-097D; empty without events), in the scene's
  // action format: a scene with these appended to its "actions" is what animcheck's acting rule reads.
  const Json& reactionActions() const { return reactionActions_; }
  int materialIndex(const std::string& name) const;
  // Replaces a character's asset (after in-app editing) and rebuilds its rig.
  Result<void> rebuildCharacter(size_t index, const CharacterAsset& asset, const EvalOptions& options);
  // Replaces material parameters by name (in-app look development).
  void updateMaterial(const Material& m);
  // Recompiles the scene's actions into generated tracks (called by load; call again after editing actions).
  // Also rebuilds the facial layers (T-046) from the compiled emotions, looks and clips.
  Result<void> compileActions();
  // Facial layer (scene/face_layer.h, T-046): active for character c while its life layer is on (and life "face" is
  // not false). faceState is empty when it is not active.
  bool faceActive(size_t c) const;
  FaceState faceState(size_t c, double frame) const;
  const FaceLayer* faceLayer(size_t c) const { return c < faces_.size() ? &faces_[c] : nullptr; }
  // Bone frames (world space) of character c at a frame, after constraints.
  // Includes secondary motion (spring chains, anim/secondary.h) when the character has it; poseOut stays kinematic.
  std::vector<mat4> characterGlobals(size_t c, double frame, Pose* poseOut = nullptr) const;
  // Drops cached spring-chain states and body-mechanics drivers (done automatically on load and on mutableScene()).
  void resetDynamics() const;
  // Body mechanics (T-045): whether the layer is on for character c, its resolved tuning and rig binding, the raw
  // drivers at a frame (pose before the layer) and the filtered input the layer uses at a (fractional) frame.
  bool bodyMechanicsActive(size_t c) const { return c < body_.size() && body_[c].params.enabled; }
  const BodyMechanicsParams* bodyMechanicsParams(size_t c) const { return c < body_.size() ? &body_[c].params : nullptr; }
  const BodyMechanicsRig* bodyMechanicsRig(size_t c) const { return c < body_.size() ? &body_[c].rig : nullptr; }
  // Personality (T-053): the resolved profile of character c (null = none) and the clip tempo its gestures play at.
  const PersonalityProfile* personality(size_t c) const {
    return c < persona_.size() && persona_[c].profile ? &*persona_[c].profile : nullptr;
  }
  double clipTempo(size_t c) const { return c < persona_.size() ? persona_[c].tempo : 1.0; }
  // Face offset of the personality on morph `morph` of character c at a frame (0 without a profile).
  float personalityFaceOffset(size_t c, const std::string& morph, double frame) const;
  BodyDrivers bodyDrivers(size_t c, long long frame) const;
  BodyMechanicsInput bodyMechanicsInput(size_t c, double frame) const;
  mat4 objectWorld(size_t o, double frame) const;
  // Prop instance frames (world space). Prop parents are resolved in dependency order; parent switches are
  // rebased at their switch frame so random-access evaluation remains continuous.
  std::vector<mat4> propWorlds(double frame) const;
  mat4 propWorld(size_t prop, double frame) const;
  // World position of a hand's palm contact point (interaction.h): the point that meets a prop's grasp socket.
  vec3 handGripPoint(size_t c, char side, double frame) const;

 private:
  float waterHeight(size_t waterObject, vec2 localXZ, double frame) const;
  // A socket may name an exported bone directly or a semantic role from a compiled clip binding.
  int characterSocketBone(size_t character, const std::string& socket) const;
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
  std::vector<PropAsset> propAssets_;
  std::vector<std::string> warnings_;
  // Reaction events (T-097D): the actions generated from scene_.events by the last compile (look, emotion, clip).
  Json reactionActions_ = Json::array();
  Result<Json> planReactionActions();
  static std::string blinkMorph(const CharacterInstance& ci);
  // Facial layer (T-046): events gathered while actions compile, then one layer per character.
  Result<void> compileActionsBody();
  void buildFaceLayers();
  FaceLibrary faceLibrary_;
  std::vector<FaceTimeline> faceTimelines_;
  std::vector<FaceLayer> faces_;
 public:
  // Camera at a frame (scene camera + camera.position/target/lens tracks).
  Camera cameraAt(double frame) const;
  // Morph control weight as rendered before in-between expansion: the animated channel, and for the character's
  // blink morph the life-layer blink (max of both). This is what a facial control is set to.
  float morphControlWeight(size_t c, const std::string& morph, double frame) const;
  // Effective life parameters of character c (scene values + the character's blink timing).
  LifeParams lifeParams(size_t c) const;
  GazeLegibility gazeLegibility(size_t c) const;
  // The exact live target of character c's current look (T-136 E3) and the keyed track's value it replaces; false when
  // the current look is not an "atProp" / "atCharacter" look or a generated look has taken over the track.
  bool liveGazeTarget(size_t c, double frame, vec3& live, vec3& keyed, double* lookStart = nullptr) const;
  // Live-target offsets (live - keyed) per frame from frameStart, w = frames since the look started + 1 (0 = none); built once at load, before the
  // secondary motion exists (a held prop's pose is read through its holder), and read with liveGazeOffset.
  void buildLiveGaze();
  void buildLiveGazePass();
  bool liveGazeOffset(size_t c, double frame, vec3& offset, double* sinceStart = nullptr) const;
  std::vector<std::vector<vec4>> liveGaze_;
  BlinkSchedule blinkSchedule(size_t c) const;  // the scene's setting with the character's on top (T-136)
  FaceState faceEval(size_t c, double frame) const;  // faces_[c].evaluate with the blink schedule applied  // the scene's setting with the character's on top (T-120)
  // Animated weight of morph `morph` of character c at `frame`.
  float expressionWeight(size_t c, const std::string& morph, double frame) const;
 private:
  std::vector<ObjectDesc> authoredObjects_;  // objects as written, before actions set attachments and ripples
  std::vector<PropDesc> authoredProps_;      // props as written, before interaction actions add parent switches
  // Interaction actions (interaction.cpp): returns false for an action that is not a prop interaction.
  Result<bool> compileInteraction(const Json& action, Clip& gen, InteractionContext& ctx);
  Result<void> finishInteractions(Clip& gen, InteractionContext& ctx);
  // Arm-body clearance (T-030, interaction.cpp): elbow poles and wrist-target pushes for every IK-driven arm.
  void armClearancePass(Clip& gen, const InteractionContext& ctx);
  void buildClearanceModels();
  void writeArmPole(Clip& gen, size_t c, char side);
  std::vector<BodyClearanceModel> clearance_;  // per character (built by compileActions)
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
    // Animation principles (T-061, clip actions only): quintic ease ramps; each succession rank (successionRank)
    // blends `succession` frames after the previous one, in and out; an optional ease-preserving time warp; elbow
    // breakdowns (degrees the elbow opens mid blend, per side L / R) where the wrist path would be near-linear.
    bool principles = false;
    // Eased clock: ramps (scene frames) over which the clip's clock accelerates from / decelerates to a stop, at the
    // ends where the clip itself is moving (a clip cut mid-motion); 0 = the plain clock at that end. The layer keeps
    // its length (anim/principles.h easedClock).
    double clockIn = 0, clockOut = 0;
    double succession = 0;
    std::shared_ptr<const TimeWarp> warp;
    float breakIn[2] = {0, 0}, breakOut[2] = {0, 0};
    // Blended emotion posture (T-097A, scene/emotion.h): per-frame weight (x the envelope) and clip clock; null = none.
    std::shared_ptr<const SampledLayerCurves> sampled;
    double envelope(double frame) const;  // weight x blend in/out at a scene frame (any rank still blending)
    double envelopeRank(double frame, int rank) const;  // the same for one succession rank
    double clipFrame(double frame, double sceneFps) const;
  };
  std::vector<std::vector<ClipLayer>> clipLayers_;
  AnimPrinciples principles_;  // the scene's animPrinciples (parsed when actions compile)
  void applyBreakdowns(size_t c, const ClipLayer& L, double frame, Pose& pose) const;
  // Automatic base idle (T-027): per character, the shared idle clip bound to it (prepared once by load); it plays
  // only while the character has no base clip action, so recompiled actions decide (autoIdleLayer).
  std::vector<std::optional<ClipLayer>> autoIdle_;
  void prepareAutoIdle();
  const ClipLayer* autoIdleLayer(size_t c) const;
  std::vector<const ClipLayer*> activeClipLayers(size_t c) const;  // auto idle (if it applies) + the clip layers
  std::vector<std::vector<std::pair<double, double>>> walkSpans_;
  std::map<std::string, std::shared_ptr<const ClipData>> clipCache_;
  void applyClips(size_t c, double frame, Pose& pose, float& yawOffset) const;
  // Clips, life, constraints: the pose before secondary motion.
  std::vector<mat4> kinematicGlobals(size_t c, double frame, Pose* poseOut) const;
  std::vector<std::shared_ptr<SpringChainSolver>> dynamics_;  // per character; null = no secondary motion
  // Body mechanics (T-045): per character tuning, rig binding and follow-through kernels (scene frames); raw drivers
  // are cached per integer frame (not while actions compile: the generated tracks are still changing).
  struct BodyMechanicsSetup {
    BodyMechanicsParams params;
    BodyMechanicsRig rig;
    std::vector<float> fast, slow, weight;
  };
  std::vector<BodyMechanicsSetup> body_;
  void buildBodyMechanics();
  // Personality (T-053): resolved per character when actions compile (before body mechanics and the face layers).
  struct PersonaSetup {
    std::optional<PersonalityProfile> profile;
    PersonalityFace face;                               // resolved to this character's morphs
    std::vector<std::string> activityMorphs;            // morphs whose animated weight is "expression activity"
    std::vector<std::pair<double, double>> watchSpans;  // look actions (mouth while watching)
    double tempo = 1.0;                                 // clip clock multiplier of gestures (1 = none)
    std::optional<PersonalityRange> speedLimit;         // effective gesture clip speed (limits.action_speed)
    float neutralIdleH = 0.004f;                        // shared neutral idle amplitude (head widths)
  };
  std::vector<PersonaSetup> persona_;
  void buildPersonalities();
  float expressionActivity(size_t c, double frame) const;
  double layerClipFrame(size_t c, const ClipLayer& L, double frame) const;  // clip_layers.cpp: clipFrame x tempo
  void applyBodyMechanicsAt(size_t c, double frame, Pose& pose) const;
  BodyDrivers filteredDrivers(size_t c, long long frame, const std::vector<float>& kernel) const;
  std::shared_ptr<std::mutex> bodyMutex_ = std::make_shared<std::mutex>();
  mutable std::vector<std::map<long long, BodyDrivers>> bodyCache_;
  bool bodyCacheOn_ = true;
  void applyClipFingers(size_t c, double frame, Pose& pose) const;
 public:
  // Clip playback data of character c for a reference pose: the package's generated block if it matches the
  // reference version, else derived from the skeleton (same rules).
  RetargetData retargetData(size_t c, const ReferencePose& ref) const;
  // Planned clip actions of character c (T-061, read only: tests and tools): timing, blends and breakdowns.
  struct ClipLayerPlan {
    std::string clip;
    double start = 0, end = 0, blendIn = 0, blendOut = 0, succession = 0, clockIn = 0, clockOut = 0;
    bool principles = false, warped = false;
    float breakIn[2] = {0, 0}, breakOut[2] = {0, 0};
  };
  std::vector<ClipLayerPlan> clipLayerPlans(size_t c) const;
  bool hasClipLayers(size_t c) const { return (c < clipLayers_.size() && !clipLayers_[c].empty()) || autoIdleLayer(c); }
  // Arm-body clearance of character c's arm `side` at a frame (gap < 0: the arm is inside a body capsule), and the
  // body model it is measured against (T-030, scene/interaction.h).
  ArmClearance armClearanceAt(size_t c, char side, double frame) const;
  const BodyClearanceModel* clearanceModel(size_t c) const { return c < clearance_.size() ? &clearance_[c] : nullptr; }
};

}  // namespace plush
