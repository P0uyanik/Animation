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

// ------------------------------------------------------------------------------------- arm-body clearance (T-030)
namespace {

// Smallest forearm/hand clearance over the frames where the arm's IK weight is full, and the frame of it.
std::pair<float, int> fullIkClearance(const SceneEvaluator& ev, size_t c, char side, int fa, int fb) {
  const std::string ik = ev.scene().characters[c].name + "/ik.hand." + side;
  float worst = 1e9f;
  int at = 0;
  for (int f = fa; f <= fb; ++f) {
    if (ev.scene().animation.evaluate(ik + ".weight", f, vec3(1)).x < 0.99f) continue;
    const float g = ev.armClearanceAt(c, side, f).gap;
    if (g < worst) worst = g, at = f;
  }
  return {worst, at};
}

}  // namespace

TEST_CASE("arm-body clearance: body sections and arm surface fitted from the package, rest pose is clear") {
  for (const char* pkg : {kBoy, kGirl}) {
    Scene scene = baseScene();
    scene.characters.push_back(character("a", pkg, vec3(0), 0));
    auto ev = load(scene);
    const BodyClearanceModel* M = ev->clearanceModel(0);
    REQUIRE(M);
    REQUIRE(M->valid);
    CHECK(M->source == "mesh");
    CHECK(M->body.size() == 7);  // 2 pelvis, 3 lower torso, 2 upper torso bands
    for (const BodyCapsule& C : M->body) {
      CHECK(C.r1 > 0.03f);  // a pelvis band is shallow at its round bottom end
      CHECK(C.r1 < 0.2f);
      CHECK(C.r2 > 0.03f);
      CHECK(C.r2 < 0.2f);
    }
    CHECK(M->body.front().cap0);
    CHECK(M->body.back().cap1);
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    std::vector<mat4> rest(sk.bones.size());
    for (size_t b = 0; b < sk.bones.size(); ++b) rest[b] = glm::translate(mat4(1), sk.bones[b].head);
    for (char side : {'L', 'R'}) {
      CHECK(M->arm[side == 'L' ? 0 : 1].points.size() > 100);
      const ArmClearance a = armClearance(*M, rest, side);
      MESSAGE(pkg << " " << side << ": rest gap " << a.gap * 1000 << " mm (" << a.part << " / " << a.against << ")");
      CHECK(a.gap >= kArmBodyMargin - 1e-4f);  // a point that rests against the body counts from its rest depth
    }
    // A hand pushed into the belly reads as inside, with a push pointing out of the body (forward).
    std::vector<mat4> G = rest;
    const int hand = sk.find("hand.R"), hips = sk.find("hips"), chest = sk.find("chest");
    const vec3 belly = 0.5f * (sk.bones[size_t(hips)].head + sk.bones[size_t(chest)].head) + vec3(0, 0, 0.05f);
    G[size_t(hand)] = glm::translate(mat4(1), belly);
    for (int b = 0; b < int(sk.bones.size()); ++b)  // fingers follow the hand
      for (int p = sk.bones[size_t(b)].parent; p >= 0; p = sk.bones[size_t(p)].parent)
        if (p == hand) {
          G[size_t(b)] = glm::translate(mat4(1), belly + sk.bones[size_t(b)].head - sk.bones[size_t(hand)].head);
          break;
        }
    const ArmClearance in = armClearance(*M, G, 'R');
    MESSAGE(pkg << ": hand in the belly: gap " << in.gap * 1000 << " mm, push " << in.push.x << " " << in.push.y << " " << in.push.z);
    CHECK(in.gap < -0.02f);
    CHECK(in.push.z > 0.5f);
  }
}

TEST_CASE("arm-body clearance: the elbow pole turns the elbow only (wrist and hand stay)") {
  Scene scene = baseScene();
  scene.characters.push_back(character("a", kBoy, vec3(0), 0));
  auto ev = load(scene);
  const Skeleton& sk = ev->characters()[0].asset.skeleton;
  const int hand = sk.find("hand.R"), fore = sk.find("forearm.R"), upper = sk.find("upperArm.R");
  Pose pose = restPose(sk);
  Clip ik;
  const vec3 target = vec3(boneGlobals(sk, pose, mat4(1))[size_t(upper)][3]) + vec3(0.02f, -0.1f, 0.14f);
  ik.tracks["a/ik.hand.R"].setKey({0, target, Interp::Linear});
  applyConstraints(sk, ik, "a/", 0, mat4(1), pose, GazeLimits{});
  const auto G0 = boneGlobals(sk, pose, mat4(1));
  for (const vec3 poleDir : {vec3(-1, -0.2f, 0), vec3(0, -1, 0), vec3(-0.3f, 0, -1)}) {
    Pose p = pose;
    Clip c;
    c.tracks["a/pole.hand.R"].setKey({0, poleDir, Interp::Linear});
    applyArmPoles(sk, c, "a/", 0, mat4(1), p);
    const auto G1 = boneGlobals(sk, p, mat4(1));
    CHECK(glm::distance(vec3(G1[size_t(hand)][3]), vec3(G0[size_t(hand)][3])) < 1e-5f);  // the wrist stays
    const quat h0 = glm::quat_cast(mat3(G0[size_t(hand)])), h1 = glm::quat_cast(mat3(G1[size_t(hand)]));
    CHECK(std::abs(glm::dot(glm::normalize(h0), glm::normalize(h1))) > 0.99999f);  // the hand keeps its rotation
    // the elbow now lies in the plane of the arm axis and the pole, on the pole's side
    const vec3 a(G1[size_t(upper)][3]), e(G1[size_t(fore)][3]), w(G1[size_t(hand)][3]);
    const vec3 u = glm::normalize(w - a);
    const vec3 eo = glm::normalize((e - a) - u * glm::dot(e - a, u)), po = glm::normalize(poleDir - u * glm::dot(poleDir, u));
    CHECK(glm::dot(eo, po) > 0.999f);
  }
}

TEST_CASE("arm-body clearance: a hold pulled across and into the body keeps the arm outside, smoothly") {
  for (const char* asset : {kBoy, kGirl}) {
    Scene scene = baseScene();
    scene.characters.push_back(character("actor", asset, vec3(0), 0));
    auto probe = load(scene);
    // The cup stands in front of the right side (clear contact); the hold then pulls it across the front towards the
    // centre line and back into the belly (an authored target the arm cannot reach while staying outside).
    scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
    scene.actions = Json::parse(R"([
        {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
        {"type": "hold", "character": "actor", "hand": "R", "start": 24, "end": 44, "by": [0.1, 0, -0.1]}])");
    auto ev = load(scene);
    for (const auto& w : ev->warnings()) MESSAGE(w);
    CHECK(ev->warnings().empty());
    const auto [gap, at] = fullIkClearance(*ev, 0, 'R', 1, 90);
    MESSAGE(asset << ": smallest forearm/hand clearance at full IK " << gap * 1000 << " mm (frame " << at << ")");
    CHECK(gap >= 0.0f);
    CHECK(glm::distance(ev->handGripPoint(0, 'R', 20), socketWorld(*ev, 0, "grip", 20)) < 0.005f);  // contact exact
    // The hold was kept outside: the cup did not arrive where the hold asked (inside the body).
    const vec3 asked = scene.props[0].transform.translation + vec3(0.1f, 0, -0.1f);
    MESSAGE(asset << ": hold end kept " << glm::distance(vec3(ev->propWorld(0, 44)[3]), asked) * 1000 << " mm from the asked point");
    CHECK(glm::distance(vec3(ev->propWorld(0, 44)[3]), asked) > 0.01f);
    // Smooth: while the push acts (the hold, with a margin of frames) no quarter-frame wrist step is a spike against
    // its neighbours (no pop) and none is faster than a hand; the prop is continuous over the whole shot.
    std::vector<float> steps;
    for (double f = 20; f < 50; f += 0.25) steps.push_back(glm::distance(bonePos(*ev, 0, "hand.R", f), bonePos(*ev, 0, "hand.R", f + 0.25)));
    float worst = 0, spike = 0;
    for (size_t i = 1; i + 1 < steps.size(); ++i) {
      worst = std::max(worst, steps[i]);
      spike = std::max(spike, steps[i] - 2.0f * std::max(steps[i - 1], steps[i + 1]));
    }
    MESSAGE(asset << ": largest quarter-frame wrist step " << worst * 1000 << " mm, largest spike " << spike * 1000 << " mm");
    CHECK(worst < 0.012f);
    CHECK(spike < 0.0005f);
    checkContinuous(*ev, 0, {20}, 1, 90);
  }
}

TEST_CASE("arm-body clearance: the hand-over meeting point keeps both arms outside their bodies") {
  for (auto [giver, receiver] : {std::pair{kBoy, kGirl}, std::pair{kGirl, kBoy}}) {
    Scene scene = baseScene();
    // Close together (0.36 m), both right hands: the default meeting point (between the shoulders) makes the arms
    // cross their own fronts; the shared search moves it until both forearms and hands are clear.
    scene.characters.push_back(character("giver", giver, vec3(-0.18f, 0, 0), 70));
    scene.characters.push_back(character("receiver", receiver, vec3(0.18f, 0, 0), -70));
    auto probe = load(scene);
    // The cup in the giver's own frame (yaw 70): 0.85 arm forward, 0.45 down, 0.06 to its right.
    const float yaw = glm::radians(70.0f);
    const vec3 fwd(std::sin(yaw), 0, std::cos(yaw)), right(-std::cos(yaw), 0, std::sin(yaw));
    scene.props.push_back(cupFor(*probe, 0, "cup", 250, 0.85f * fwd + 0.06f * right + vec3(0, -0.45f, 0)));
    scene.actions = Json::parse(R"([
        {"type": "grasp", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
        {"type": "handover", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R",
         "start": 26, "receiverStart": 28, "contact": 46, "release": 51, "end": 64}])");
    auto ev = load(scene);
    for (const auto& w : ev->warnings()) MESSAGE(w);
    CHECK(ev->warnings().empty());
    const float g = ev->armClearanceAt(0, 'R', 46).gap, r = ev->armClearanceAt(1, 'R', 46).gap;
    MESSAGE("at the hand-over: giver " << g * 1000 << " mm, receiver " << r * 1000 << " mm");
    CHECK(g >= 0.0f);
    CHECK(r >= 0.0f);
    CHECK(fullIkClearance(*ev, 0, 'R', 1, 90).first >= 0.0f);
    CHECK(fullIkClearance(*ev, 1, 'R', 1, 90).first >= 0.0f);
    CHECK(glm::distance(ev->handGripPoint(1, 'R', 46), socketWorld(*ev, 0, "grip_b", 46)) < 0.005f);
    CHECK(glm::distance(ev->handGripPoint(0, 'R', 49), socketWorld(*ev, 0, "grip", 49)) < 0.005f);  // both hold it
    checkContinuous(*ev, 0, {18, 46}, 1, 90);
  }
}
