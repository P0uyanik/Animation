// T-112a golden bake hashes (docs/architecture/INTERACTION_AFFORDANCES.md 6.3): every content scene with interaction
// actions and the test_interaction.cpp scenes compile to the same generated clip and the same engine
// plush.shot_bake/1 output as at the input SHA recorded in tests/data/golden/interaction_hashes.json. A scene with no
// verb action must never change by the verb expander, the affordance block or anything else of T-112a.
//
// Hashes: SHA-256 of (a) the generated clip, tracks sorted by name, every key as frame / value / interpolation at full
// precision (hex floats), and (b) the bake JSON (bakeShot over the scene's frame range) with the repository root
// replaced by "<root>" (the bake records absolute paths).
//
// Floating-point results are only bit-reproducible on one toolchain, so the file stores one hash set per toolchain
// (kToolchain below). On a toolchain without a recorded set the test still compiles and bakes every scene twice
// (must be deterministic and error-free) and prints the hashes to record. Regenerate (only for an intended,
// reviewed change, named in the commit): PLUSH_GOLDEN_WRITE=1 build/tests/plush_tests -tc="golden*".
#include <doctest/doctest.h>

#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "scene/asset_library.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const fs::path kGolden = kRoot / "tests/data/golden/interaction_hashes.json";

#if defined(_MSC_VER)
const std::string kToolchain = "msvc-" + std::to_string(_MSC_VER / 100);
#elif defined(__clang__)
const std::string kToolchain = "clang-" + std::to_string(__clang_major__);
#elif defined(__GNUC__)
const std::string kToolchain = "gcc-" + std::to_string(__GNUC__);
#else
const std::string kToolchain = "unknown";
#endif
#if defined(__x86_64__) || defined(_M_X64)
const std::string kArch = "x86_64";
#elif defined(__aarch64__) || defined(_M_ARM64)
const std::string kArch = "arm64";
#else
const std::string kArch = "other";
#endif
#if defined(_WIN32)
const std::string kOs = "windows";
#elif defined(__APPLE__)
const std::string kOs = "macos";
#else
const std::string kOs = "linux";
#endif
std::string toolchainId() { return kOs + "-" + kArch + "-" + kToolchain; }

// ------------------------------------------------------------------------------------------------------ SHA-256
struct Sha256 {
  std::array<uint32_t, 8> h{0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  std::array<uint8_t, 64> buf{};
  size_t used = 0;
  uint64_t bits = 0;
  static uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
  void block(const uint8_t* p) {
    static constexpr uint32_t k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
        0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8,
        0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
        0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2};
    uint32_t w[64];
    for (int i = 0; i < 16; ++i)
      w[i] = uint32_t(p[4 * i]) << 24 | uint32_t(p[4 * i + 1]) << 16 | uint32_t(p[4 * i + 2]) << 8 | uint32_t(p[4 * i + 3]);
    for (int i = 16; i < 64; ++i) {
      const uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
      const uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
    for (int i = 0; i < 64; ++i) {
      const uint32_t t1 = hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i];
      const uint32_t t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
      hh = g, g = f, f = e, e = d + t1, d = c, c = b, b = a, a = t1 + t2;
    }
    h[0] += a, h[1] += b, h[2] += c, h[3] += d, h[4] += e, h[5] += f, h[6] += g, h[7] += hh;
  }
  void update(const std::string& s) {
    for (unsigned char ch : s) {
      buf[used++] = ch;
      bits += 8;
      if (used == 64) block(buf.data()), used = 0;
    }
  }
  std::string hex() {
    const uint64_t total = bits;
    update(std::string(1, char(0x80)));
    while (used != 56) update(std::string(1, char(0)));
    for (int i = 7; i >= 0; --i) update(std::string(1, char((total >> (8 * i)) & 0xff)));
    static const char* digits = "0123456789abcdef";
    std::string out;
    for (uint32_t v : h)
      for (int i = 7; i >= 0; --i) out += digits[(v >> (4 * i)) & 0xf];
    return out;
  }
};
std::string sha256(const std::string& s) {
  Sha256 x;
  x.update(s);
  return x.hex();
}

std::string hexFloat(double v) {
  char b[64];
  std::snprintf(b, sizeof b, "%a", v);
  return b;
}

// Generated clip, tracks sorted (std::map), keys at full precision.
std::string clipHash(const SceneEvaluator& ev) {
  Sha256 x;
  const auto& gen = ev.scene().animation.generated;
  if (!gen) return x.hex();
  for (const auto& [name, track] : gen->tracks) {
    x.update(name + "\n");
    for (const Key& k : track.keys)
      x.update(hexFloat(k.frame) + " " + hexFloat(k.value.x) + " " + hexFloat(k.value.y) + " " + hexFloat(k.value.z) + " " +
               std::to_string(int(k.interp)) + "\n");
  }
  return x.hex();
}

std::string bakeHash(const SceneEvaluator& ev) {
  std::string s = bakeShot(ev, ev.scene().frameStart, ev.scene().frameEnd).dump();
  const std::string root = fs::absolute(kRoot).lexically_normal().string();
  for (size_t at; !root.empty() && (at = s.find(root)) != std::string::npos;) s.replace(at, root.size(), "<root>");
  return sha256(s);
}

// ------------------------------------------------------------------------------------------------------- scenes
// Imported test packages (read only) next to the test scene path, and an engine (SDF) character.
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* kGirl = "girl_auburn_bun_glasses_m3/character.json";
const char* kSdf = "../../../content/characters/girl_white_hair.character.json";

CharacterDesc character(const std::string& name, const char* asset, vec3 position, float yawDeg) {
  CharacterDesc c;
  c.name = name;
  c.asset = asset;
  c.position = position;
  c.yawDeg = yawDeg;
  c.life.enabled = true;
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

const EvalOptions kOptions{2.5f, 1.0f, false, 0};

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, kOptions);
  if (!r) FAIL(r.error().message);
  return ev;
}

vec3 bonePos(const SceneEvaluator& ev, size_t c, const char* bone, double f) {
  const int b = ev.characters()[c].asset.skeleton.find(bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(c, f)[size_t(b)][3]);
}

// As test_interaction.cpp cupFor (the same scene construction, so the same scenes are hashed).
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

struct GoldenScene {
  std::string name;
  std::function<Scene()> make;
};

Scene pickUpAndPlace(const char* asset) {
  Scene scene = baseScene();
  scene.characters.push_back(character("actor", asset, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  const vec3 place0 = scene.props[0].transform.translation;
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
      {"type": "hold", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.06, 0.02]},
      {"type": "place", "character": "actor", "hand": "R", "start": 40, "contact": 54, "end": 68,
       "at": [0, 0, 0]}])");
  scene.actions[2]["at"] = {place0.x + 0.02f, place0.y, place0.z + 0.01f};
  return scene;
}

Scene handover(const char* giver, const char* receiver) {
  Scene scene = baseScene();
  scene.characters.push_back(character("giver", giver, vec3(-0.18f, 0, 0), 90));
  scene.characters.push_back(character("receiver", receiver, vec3(0.18f, 0, 0), -90));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", -90, vec3(0.85f, -0.45f, 0.04f)));
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
      {"type": "hold", "character": "giver", "hand": "R", "start": 20, "end": 30, "by": [0.03, 0.08, 0]},
      {"type": "handover", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R",
       "start": 30, "receiverStart": 32, "contact": 50, "release": 55, "end": 68},
      {"type": "hold", "character": "receiver", "hand": "R", "start": 62, "end": 78, "by": [0, 0.04, -0.02]}])");
  return scene;
}

Scene holdIntoBody(const char* asset) {
  Scene scene = baseScene();
  scene.characters.push_back(character("actor", asset, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
      {"type": "hold", "character": "actor", "hand": "R", "start": 24, "end": 44, "by": [0.1, 0, -0.1]}])");
  return scene;
}

Scene meetingPoint(const char* giver, const char* receiver) {
  Scene scene = baseScene();
  scene.characters.push_back(character("giver", giver, vec3(-0.18f, 0, 0), 70));
  scene.characters.push_back(character("receiver", receiver, vec3(0.18f, 0, 0), -70));
  auto probe = load(scene);
  const float yaw = glm::radians(70.0f);
  const vec3 fwd(std::sin(yaw), 0, std::cos(yaw)), right(-std::cos(yaw), 0, std::sin(yaw));
  scene.props.push_back(cupFor(*probe, 0, "cup", 250, 0.85f * fwd + 0.06f * right + vec3(0, -0.45f, 0)));
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
      {"type": "handover", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R",
       "start": 26, "receiverStart": 28, "contact": 46, "release": 51, "end": 64}])");
  return scene;
}

Scene sharedFollow(bool follow) {
  Scene scene = baseScene();
  scene.characters.push_back(character("giver", kBoy, vec3(-0.18f, 0, 0), 90));
  scene.characters.push_back(character("receiver", kGirl, vec3(0.18f, 0, 0), -90));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", -90, vec3(0.85f, -0.45f, 0.04f)));
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
      {"type": "handover", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R",
       "start": 30, "receiverStart": 32, "contact": 50, "release": 56, "end": 68},
      {"type": "hold", "character": "receiver", "hand": "R", "start": 51, "end": 56, "by": [0.0, 0.006, 0.006]}])");
  if (follow) scene.interaction = Json{{"followSharedProp", true}};
  return scene;
}

Scene visibleGrip(const char* asset) {
  Scene scene = baseScene();
  scene.frameEnd = 40;
  scene.characters.push_back(character("actor", asset, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  const vec3 cupAt = scene.props[0].transform.translation;
  scene.camera.position = cupAt + vec3(-1.5f, 0.3f, 0.2f);
  scene.camera.target = cupAt;
  scene.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
      {"type": "hold", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.04, 0]}])");
  scene.interaction = Json{{"visibleGrip", true}};
  return scene;
}

// A content scene (run_shot sets the cast): the imported test packages stand in for the cast, so the hash covers the
// engine code path without a Blender export. Engine regression only, not visual evidence.
Scene contentScene(const char* rel) {
  auto s = loadScene(kRoot / rel);
  if (!s) FAIL(s.error().message);
  Scene scene = *s;
  for (CharacterDesc& c : scene.characters) {
    if (c.name == "boy") c.asset = (kRoot / "tests/data/imported" / kBoy).string();
    if (c.name == "girl") c.asset = (kRoot / "tests/data/imported" / kGirl).string();
  }
  return scene;
}

std::vector<GoldenScene> goldenScenes() {
  std::vector<GoldenScene> out;
  for (const char* rel : {"content/scenes/eval/exchange/shot.scene.json", "content/scenes/eval/handover/shot.scene.json",
                          "episodes/e901_clip_test/shots/s010/shot.scene.json", "episodes/e905_props_test/shots/s010/shot.scene.json",
                          "episodes/e907_exchange/shots/s010/shot.scene.json",
                          "episodes/e907_exchange/shots/s010_calibrated/shot.scene.json"})
    out.push_back({rel, [rel] { return contentScene(rel); }});
  for (auto [n, a] : {std::pair{"boy", kBoy}, std::pair{"girl", kGirl}, std::pair{"engine", kSdf}}) {
    const char* asset = a;
    out.push_back({std::string("test_interaction/pickUpAndPlace/") + n, [asset] { return pickUpAndPlace(asset); }});
    out.push_back({std::string("test_interaction/visibleGrip/") + n, [asset] { return visibleGrip(asset); }});
  }
  out.push_back({"test_interaction/handover/boy_to_girl", [] { return handover(kBoy, kGirl); }});
  out.push_back({"test_interaction/handover/girl_to_boy", [] { return handover(kGirl, kBoy); }});
  out.push_back({"test_interaction/holdIntoBody/boy", [] { return holdIntoBody(kBoy); }});
  out.push_back({"test_interaction/holdIntoBody/girl", [] { return holdIntoBody(kGirl); }});
  out.push_back({"test_interaction/meetingPoint/boy_to_girl", [] { return meetingPoint(kBoy, kGirl); }});
  out.push_back({"test_interaction/meetingPoint/girl_to_boy", [] { return meetingPoint(kGirl, kBoy); }});
  out.push_back({"test_interaction/sharedFollow/off", [] { return sharedFollow(false); }});
  out.push_back({"test_interaction/sharedFollow/on", [] { return sharedFollow(true); }});
  return out;
}

}  // namespace

TEST_CASE("golden: interaction scenes bake byte-identically to the recorded input SHA (T-112a)") {
  // The hash itself (FIPS 180-2 test vectors).
  REQUIRE(sha256("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  REQUIRE(sha256(std::string(1000, 'a')) == "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3");
  const bool write = std::getenv("PLUSH_GOLDEN_WRITE") != nullptr;
  Json golden = Json::object();
  if (fs::exists(kGolden)) {
    auto j = parseJsonFile(kGolden);
    REQUIRE(j.has_value());
    golden = *j;
  }
  REQUIRE_FALSE(golden.empty());
  const std::string id = toolchainId();
  const bool recorded = golden.contains("toolchains") && golden["toolchains"].contains(id);
  if (!recorded && !write)
    MESSAGE("golden: no hashes recorded for toolchain '" << id << "' (recorded: " << golden["toolchains"].dump()
                                                        << " keys); checking determinism only");
  Json scenes = Json::object();
  for (const GoldenScene& g : goldenScenes()) {
    CAPTURE(g.name);
    const Scene scene = g.make();
    auto ev = load(scene);
    const std::string clip = clipHash(*ev), bake = bakeHash(*ev);
    scenes[g.name] = {{"clip", clip}, {"bake", bake}};
    if (recorded && !write) {
      const Json& want = golden["toolchains"][id]["scenes"];
      REQUIRE(want.contains(g.name));
      CHECK(want[g.name]["clip"].get<std::string>() == clip);
      CHECK(want[g.name]["bake"].get<std::string>() == bake);
    } else {
      auto again = load(scene);  // unrecorded toolchain: at least deterministic
      CHECK(clipHash(*again) == clip);
      CHECK(bakeHash(*again) == bake);
      MESSAGE(g.name << ": clip " << clip << " bake " << bake);
    }
  }
  if (recorded && !write) CHECK(golden["toolchains"][id]["scenes"].size() == scenes.size());
  if (write) {
    golden["toolchains"][id]["scenes"] = scenes;
    std::ofstream(kGolden) << golden.dump(1) << "\n";
    MESSAGE("golden: wrote " << scenes.size() << " scene hashes for '" << id << "' to " << kGolden.string());
  }
}
