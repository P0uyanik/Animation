// T-022: shared hand-prop interaction actions (scene/interaction.h) on more than one skeleton.
#include <doctest/doctest.h>

#include <filesystem>
#include <memory>

#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
// Imported packages (read only) next to the scene path, and an engine (SDF) character with a different skeleton.
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* kGirl = "girl_auburn_bun_glasses_m3/character.json";
const char* kSdf = "../../../content/characters/girl_white_hair.character.json";

CharacterDesc character(const std::string& name, const char* asset, vec3 position, float yawDeg) {
  CharacterDesc c;
  c.name = name;
  c.asset = asset;
  c.position = position;
  c.yawDeg = yawDeg;
  c.life.enabled = true;  // breathing and sway move the shoulders: contacts must still be exact
  return c;
}

Scene baseScene() {
  Scene s;
  s.name = "interaction test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 96;
  return s;
}

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

Result<void> tryLoad(const Scene& scene) {
  SceneEvaluator ev;
  return ev.load(scene, EvalOptions{2.5f, 1.0f, false, 0});
}

vec3 bonePos(const SceneEvaluator& ev, size_t c, const char* bone, double f) {
  const int b = ev.characters()[c].asset.skeleton.find(bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(c, f)[size_t(b)][3]);
}

// A felt cup on a plinth in front of and below the character's right shoulder; the cup is turned so its "grip"
// socket (local +x) faces the hand's side. Returns the cup's local -> world yaw so callers can reason about it.
// The offset is in units of the character's arm length (shoulder -> elbow -> wrist), so every skeleton gets the same
// relative reach.
PropDesc cupFor(const SceneEvaluator& probe, size_t c, const char* name, float yawCupDeg, vec3 offsetFromShoulder) {
  PropDesc cup;
  cup.name = name;
  cup.id = "prop.felt_cup";
  const vec3 shoulder = bonePos(probe, c, "upperArm.R", 1), elbow = bonePos(probe, c, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(probe, c, "hand.R", 1));
  const vec3 grip = shoulder + offsetFromShoulder * arm;
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, yawCupDeg, 0), vec3(1)});
  const PropAsset asset = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  cup.transform.translation = grip - vec3(rot * vec4(asset.sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, yawCupDeg, 0};
  return cup;
}

vec3 socketWorld(const SceneEvaluator& ev, size_t p, const std::string& socket, double f) {
  const PropAsset asset = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  return vec3((ev.propWorld(p, f) * assetTransformMatrix(asset.sockets.at(socket)))[3]);
}

float matrixJump(const mat4& a, const mat4& b) {
  float m = glm::distance(vec3(a[3]), vec3(b[3]));
  for (int k = 0; k < 3; ++k) m = std::max(m, 0.05f * glm::distance(vec3(a[k]), vec3(b[k])));  // 5 cm lever arm
  return m;
}

// The prop never jumps: just before and after every given frame it is (nearly) the same, and between consecutive
// quarter frames it moves less than a hand can.
void checkContinuous(const SceneEvaluator& ev, size_t p, std::initializer_list<double> switches, double fa, double fb) {
  for (double f : switches) {
    const float j = matrixJump(ev.propWorld(p, f - 1e-3), ev.propWorld(p, f + 1e-3));
    MESSAGE("prop jump across frame " << f << ": " << j * 1000 << " mm");
    CHECK(j < 0.0005f);
    // and the motion through the switch frame is no faster than its neighbourhood
    CHECK(matrixJump(ev.propWorld(p, f), ev.propWorld(p, f + 1)) < 0.01f);
    CHECK(matrixJump(ev.propWorld(p, f - 1), ev.propWorld(p, f)) < 0.01f);
  }
  // Over the whole shot: no quarter-frame step is a spike against its neighbours, and none is faster than a hand.
  std::vector<float> steps;
  for (double f = fa; f < fb; f += 0.25) steps.push_back(matrixJump(ev.propWorld(p, f), ev.propWorld(p, f + 0.25)));
  float worst = 0, spike = 0;
  for (size_t i = 1; i + 1 < steps.size(); ++i) {
    worst = std::max(worst, steps[i]);
    spike = std::max(spike, steps[i] - 2.0f * std::max(steps[i - 1], steps[i + 1]));
  }
  MESSAGE("largest quarter-frame prop step: " << worst * 1000 << " mm, largest spike: " << spike * 1000 << " mm");
  CHECK(worst < 0.012f);  // 1.15 m/s at 24 fps
  CHECK(spike < 0.0005f);
}

void pickUpAndPlace(const char* asset) {
  Scene scene = baseScene();
  scene.characters.push_back(character("actor", asset, vec3(0), 0));
  auto probe = load(scene);
  // Grip faces the right hand (the character's right is -x): cup yaw 180 puts local +x at world -x.
  // T-030: the cup stands in front of the body (0.85 arm lengths forward, 0.45 down; 0.96 arm from the shoulder).
  // T-022 had it 0.5 forward / 0.65 down, at the belly surface, so the forearm had to enter the body at contact; the
  // arm-body clearance reports that now.
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  // The hold lifts the cup and moves it a little away from the body (T-022 moved it 3 cm towards the body, which ends
  // inside the boy's: his sleeve is skinned between shoulder and hand).
  const vec3 place0 = scene.props[0].transform.translation;
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
      {"type": "hold", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.06, 0.02]},
      {"type": "place", "character": "actor", "hand": "R", "start": 40, "contact": 54, "end": 68,
       "at": [0, 0, 0]}])");
  scene.actions[2]["at"] = {place0.x + 0.02f, place0.y, place0.z + 0.01f};
  auto ev = load(scene);
  for (const auto& w : ev->warnings()) MESSAGE(w);
  CHECK(ev->warnings().empty());
  // Contact: the palm point is on the grip socket within 5 mm.
  const float d = glm::distance(ev->handGripPoint(0, 'R', 20), socketWorld(*ev, 0, "grip", 20));
  MESSAGE(std::string(asset) << ": palm to grip socket at contact " << d * 1000 << " mm");
  CHECK(d < 0.005f);
  // The cup waits on the table until contact, then rides with the hand, upright.
  CHECK(glm::distance(vec3(ev->propWorld(0, 19)[3]), place0) < 1e-5f);
  const mat4 lifted = ev->propWorld(0, 36);
  CHECK(glm::distance(vec3(lifted[3]), place0 + vec3(0, 0.06f, 0.02f)) < 0.005f);
  CHECK(glm::dot(glm::normalize(vec3(lifted[1])), vec3(0, 1, 0)) > 0.999f);
  // Put down: the place socket lands on the target at contact and stays there after the hand has gone.
  const vec3 target(place0.x + 0.02f, place0.y, place0.z + 0.01f);
  CHECK(glm::distance(socketWorld(*ev, 0, "place", 54), target) < 0.005f);
  CHECK(glm::distance(socketWorld(*ev, 0, "place", 90), target) < 0.005f);
  CHECK(glm::distance(ev->handGripPoint(0, 'R', 90), socketWorld(*ev, 0, "grip", 90)) > 0.03f);  // let go
  // Size-adaptive grasp: the fingers close on the cup (the hand pose track opens, the grasp closes it).
  CHECK(ev->scene().animation.evaluate("actor/hand.R.graspRadius", 20, vec3(0)).x ==
        doctest::Approx(loadAsset(kRoot / "content/assets/felt_cup.asset.json").value().mesh.radius));
  CHECK(ev->scene().animation.evaluate("actor/hand.R.grasp.weight", 20, vec3(0)).x == doctest::Approx(1.0f));
  // Gaze is on the cup while it is handled.
  CHECK(glm::distance(ev->scene().animation.evaluate("actor/lookAt", 30, vec3(0)), vec3(ev->propWorld(0, 30)[3])) < 0.08f);
  checkContinuous(*ev, 0, {20, 54}, 1, 90);
}

}  // namespace

TEST_CASE("interaction: reach/grasp lands the palm on the prop socket within 5 mm (boy skeleton)") { pickUpAndPlace(kBoy); }
TEST_CASE("interaction: reach/grasp lands the palm on the prop socket within 5 mm (girl skeleton)") { pickUpAndPlace(kGirl); }
TEST_CASE("interaction: reach/grasp lands the palm on the prop socket within 5 mm (engine skeleton)") { pickUpAndPlace(kSdf); }

TEST_CASE("interaction: hand-over between two characters keeps the prop continuous") {
  for (auto [giver, receiver] : {std::pair{kBoy, kGirl}, std::pair{kGirl, kBoy}}) {
    Scene scene = baseScene();
    // Facing each other: the giver at -x looking +x (its right is +z), the receiver at +x looking -x (right is -z).
    scene.characters.push_back(character("giver", giver, vec3(-0.18f, 0, 0), 90));
    scene.characters.push_back(character("receiver", receiver, vec3(0.18f, 0, 0), -90));
    auto probe = load(scene);
    // Cup yaw -90: grip (local +x) faces +z (giver's right hand side), grip_b faces -z (receiver's right hand).
    // T-030: the receiver's last hold lifts the cup and moves it to her right side (-z); T-022 moved it 2 cm across
    // her front (+x towards her body), which the arm-body clearance now resists.
    scene.props.push_back(cupFor(*probe, 0, "cup", -90, vec3(0.85f, -0.45f, 0.04f)));  // in front of the body (T-030)
    scene.actions = Json::parse(R"([
        {"type": "grasp", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
        {"type": "hold", "character": "giver", "hand": "R", "start": 20, "end": 30, "by": [0.03, 0.08, 0]},
        {"type": "handover", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R",
         "start": 30, "receiverStart": 32, "contact": 50, "release": 55, "end": 68},
        {"type": "hold", "character": "receiver", "hand": "R", "start": 62, "end": 78, "by": [0, 0.04, -0.02]}])");
    auto ev = load(scene);
    for (const auto& w : ev->warnings()) MESSAGE(w);
    CHECK(ev->warnings().empty());
    const float dg = glm::distance(ev->handGripPoint(0, 'R', 18), socketWorld(*ev, 0, "grip", 18));
    const float dr = glm::distance(ev->handGripPoint(1, 'R', 50), socketWorld(*ev, 0, "grip_b", 50));
    MESSAGE("giver palm to grip " << dg * 1000 << " mm, receiver palm to grip_b " << dr * 1000 << " mm");
    CHECK(dg < 0.005f);
    CHECK(dr < 0.005f);
    // Between contact and release both hands are on the cup (the giver still touches its socket).
    CHECK(glm::distance(ev->handGripPoint(0, 'R', 53), socketWorld(*ev, 0, "grip", 53)) < 0.005f);
    // After the hand-over the cup follows the receiver, not the giver.
    CHECK(glm::distance(vec3(ev->propWorld(0, 78)[3]) - vec3(ev->propWorld(0, 62)[3]), vec3(0, 0.04f, -0.02f)) < 0.005f);
    CHECK(glm::distance(ev->handGripPoint(1, 'R', 78), socketWorld(*ev, 0, "grip_b", 78)) < 0.005f);
    CHECK(glm::distance(ev->handGripPoint(0, 'R', 80), socketWorld(*ev, 0, "grip", 80)) > 0.03f);
    CHECK(glm::dot(glm::normalize(vec3(ev->propWorld(0, 78)[1])), vec3(0, 1, 0)) > 0.999f);  // still upright
    checkContinuous(*ev, 0, {18, 50}, 1, 90);
  }
}

TEST_CASE("interaction: hand grip geometry and orientation constraint are skeleton independent") {
  for (const char* pkg : {"boy_yellow_hoodie_1.0.0/character.json", "toy_fixture/character.json"}) {
    Scene scene = baseScene();
    scene.characters.push_back(character("a", pkg, vec3(0), 0));
    auto ev = load(scene);
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    for (char side : {'L', 'R'}) {
      const int hand = sk.find(std::string("hand.") + side);
      REQUIRE(hand >= 0);
      const HandGrip g = handGrip(sk, hand, side);
      CHECK(glm::length(g.fingerDir) == doctest::Approx(1.0f));
      CHECK(std::abs(glm::dot(g.fingerDir, g.palmNormal)) < 1e-4f);
      CHECK(g.palmLength > 0.015f);
      CHECK(glm::length(g.palm) < 0.1f);
      // An orient track turns the hand's world rotation to the keyed one, whatever the arm does.
      Clip clip;
      const quat want = glm::angleAxis(0.7f, glm::normalize(vec3(0.3f, 1, -0.2f)));
      clip.tracks[std::string("a/orient.hand.") + side].setKey({0, rotationVector(want), Interp::Linear});
      Pose pose = restPose(sk);
      pose.local[size_t(sk.bones[size_t(hand)].parent)] = glm::angleAxis(0.5f, vec3(1, 0, 0));
      applyOrientConstraints(sk, clip, "a/", 0, mat4(1), pose);
      const quat got = glm::normalize(glm::quat_cast(mat3(boneGlobals(sk, pose, mat4(1))[size_t(hand)])));
      CHECK(std::abs(glm::dot(got, want)) > 0.99999f);
    }
  }
  CHECK(glm::length(rotationVector(fromRotationVector(vec3(0.1f, -2.0f, 0.4f))) - vec3(0.1f, -2.0f, 0.4f)) < 1e-4f);
}

TEST_CASE("interaction: bad action timelines are load errors") {
  Scene scene = baseScene();
  scene.characters.push_back(character("actor", kBoy, vec3(0), 0));
  auto probe = load(scene);
  // T-030: the cup stands in front of the body (0.85 arm lengths forward, 0.45 down; 0.96 arm from the shoulder).
  // T-022 had it 0.5 forward / 0.65 down, at the belly surface, so the forearm had to enter the body at contact; the
  // arm-body clearance reports that now.
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  auto expectError = [&](const char* actions, const char* text) {
    Scene s = scene;
    s.actions = Json::parse(actions);
    auto r = tryLoad(s);
    REQUIRE_FALSE(r.has_value());
    MESSAGE(r.error().message);
    CHECK(r.error().message.find(text) != std::string::npos);
  };
  expectError(R"([{"type": "place", "character": "actor", "start": 5, "at": [0, 0, 0]}])", "holds nothing");
  expectError(R"([{"type": "grasp", "character": "actor", "prop": "nope", "start": 5}])", "unknown prop");
  expectError(R"([{"type": "grasp", "character": "actor", "prop": "cup", "socket": "lid", "start": 5}])", "no socket 'lid'");
  expectError(R"([{"type": "grasp", "character": "actor", "prop": "cup", "start": 5, "contact": 20},
                  {"type": "grasp", "character": "actor", "prop": "cup", "start": 25, "contact": 40}])", "already holds");
  expectError(R"([{"type": "grasp", "character": "actor", "prop": "cup", "start": 5, "contact": 20},
                  {"type": "handover", "character": "actor", "to": "ghost", "start": 25}])", "unknown receiver");
}
