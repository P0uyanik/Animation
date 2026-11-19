// T-112a: verb library and verb expander (scene/verbs.h; docs/architecture/INTERACTION_AFFORDANCES.md 3, 4, 6).
#include <doctest/doctest.h>

#include <filesystem>
#include <memory>

#include "anim/personality.h"
#include "scene/asset_library.h"
#include "scene/scene.h"
#include "scene/verbs.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
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
  s.name = "verb test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 110;
  s.timing = "none";  // the shared defaults (T-112a's legacy cases); since T-104d an absent key means "calibrated"
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

PropAsset cupAsset() { return loadAsset(kRoot / "content/assets/felt_cup.asset.json").value(); }

// As test_interaction.cpp: a felt cup in front of character c's right shoulder, offset in arm lengths.
PropDesc cupFor(const SceneEvaluator& probe, size_t c, const char* name, float yawCupDeg, vec3 offsetFromShoulder) {
  PropDesc cup;
  cup.name = name;
  cup.id = "prop.felt_cup";
  const vec3 shoulder = bonePos(probe, c, "upperArm.R", 1), elbow = bonePos(probe, c, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(probe, c, "hand.R", 1));
  const vec3 grip = shoulder + offsetFromShoulder * arm;
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, yawCupDeg, 0), vec3(1)});
  cup.transform.translation = grip - vec3(rot * vec4(cupAsset().sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, yawCupDeg, 0};
  return cup;
}

vec3 socketWorld(const SceneEvaluator& ev, size_t p, const std::string& socket, double f) {
  return vec3((ev.propWorld(p, f) * assetTransformMatrix(cupAsset().sockets.at(socket)))[3]);
}

// Key-for-key equality of two generated clips (names, frames, values, interpolation: exact).
void checkSameClip(const SceneEvaluator& a, const SceneEvaluator& b) {
  const auto& A = a.scene().animation.generated;
  const auto& B = b.scene().animation.generated;
  REQUIRE(A);
  REQUIRE(B);
  CHECK(A->tracks.size() == B->tracks.size());
  size_t keys = 0, diffs = 0;
  for (const auto& [name, ta] : A->tracks) {
    auto it = B->tracks.find(name);
    if (it == B->tracks.end()) {
      FAIL_CHECK("track " << name << " missing from the verb expansion");
      continue;
    }
    const Track& tb = it->second;
    if (ta.keys.size() != tb.keys.size()) {
      FAIL_CHECK("track " << name << ": " << ta.keys.size() << " vs " << tb.keys.size() << " keys");
      continue;
    }
    for (size_t k = 0; k < ta.keys.size(); ++k, ++keys)
      if (ta.keys[k].frame != tb.keys[k].frame || ta.keys[k].value != tb.keys[k].value || ta.keys[k].interp != tb.keys[k].interp) {
        if (diffs++ < 5) FAIL_CHECK("track " << name << " key " << k << " differs");
      }
  }
  MESSAGE(keys << " keys compared, " << diffs << " differ");
  CHECK(diffs == 0);
  CHECK(keys > 50);  // the arm's ik / orient / hand / gaze tracks and the prop's parent weight
}

}  // namespace

// ----------------------------------------------------------------------------------------- legacy equivalence (4)
TEST_CASE("verbs: pick_up + carry + place without a profile expand to the hand-written grasp + hold + place, key for key") {
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    CAPTURE(asset);
    Scene scene = baseScene();
    scene.frameEnd = 96;
    scene.characters.push_back(character("actor", asset, vec3(0), 0));
    auto probe = load(scene);
    scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
    const vec3 place0 = scene.props[0].transform.translation;
    const Json at = {place0.x + 0.02f, place0.y, place0.z + 0.01f};
    // The hand-written primitives of test_interaction.cpp pickUpAndPlace.
    Scene hand = scene;
    hand.actions = Json::parse(R"([
        {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
        {"type": "hold", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.06, 0.02]},
        {"type": "place", "character": "actor", "hand": "R", "start": 40, "contact": 54, "end": 68}])");
    hand.actions[2]["at"] = at;
    Scene verb = scene;
    verb.actions = Json::parse(R"([
        {"type": "pick_up", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
        {"type": "carry", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.06, 0.02]},
        {"type": "place", "verb": true, "character": "actor", "hand": "R", "start": 40, "contact": 54, "end": 68}])");
    verb.actions[2]["at"] = at;
    auto a = load(hand);
    auto b = load(verb);
    checkSameClip(*a, *b);
    CHECK(a->warnings() == b->warnings());
    REQUIRE(a->scene().props[0].parentSwitch.size() == b->scene().props[0].parentSwitch.size());
    for (size_t k = 0; k < a->scene().props[0].parentSwitch.size(); ++k)
      CHECK(a->scene().props[0].parentSwitch[k].frame == b->scene().props[0].parentSwitch[k].frame);
    for (double f : {1.0, 20.0, 36.0, 54.0, 90.0}) CHECK(a->propWorld(0, f) == b->propWorld(0, f));
  }
}

TEST_CASE("verbs: left-out frames take today's defaults (design 3.3); a chained verb starts where the last one ended") {
  Scene scene = baseScene();
  scene.frameEnd = 96;
  scene.characters.push_back(character("actor", kBoy, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  const vec3 place0 = scene.props[0].transform.translation;
  const Json at = {place0.x + 0.02f, place0.y, place0.z + 0.01f};
  Scene hand = scene, verb = scene;
  hand.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5},
      {"type": "hold", "character": "actor", "hand": "R", "start": 19, "end": 35, "by": [0, 0.06, 0.02]},
      {"type": "place", "character": "actor", "hand": "R", "start": 35}])");
  hand.actions[2]["at"] = at;
  verb.actions = Json::parse(R"([
      {"type": "pick_up", "character": "actor", "prop": "cup", "start": 5},
      {"type": "carry", "character": "actor", "by": [0, 0.06, 0.02]},
      {"type": "place", "verb": true, "character": "actor"}])");
  verb.actions[2]["at"] = at;
  auto a = load(hand);
  auto b = load(verb);
  checkSameClip(*a, *b);
}

// ---------------------------------------------------------------------------------------------------- profile (5)
TEST_CASE("verbs: with the calibrated profile phase lengths are the beats x personality tempo (boy slower, girl quicker)") {
  Scene scene = baseScene();
  scene.timing = "calibrated";
  // Side by side, both facing +z, each with its own cup in front of the right hand.
  scene.characters.push_back(character("boy", kBoy, vec3(-0.5f, 0, 0), 0));
  scene.characters.push_back(character("girl", kGirl, vec3(0.5f, 0, 0), 0));
  scene.characters[0].personality = "boy_yellow_hoodie";
  scene.characters[1].personality = "girl_auburn_bun_glasses";
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup_b", 180, vec3(0.04f, -0.45f, 0.85f)));
  scene.props.push_back(cupFor(*probe, 1, "cup_g", 180, vec3(0.04f, -0.45f, 0.85f)));
  Json actions = Json::array();
  for (const char* who : {"boy", "girl"}) {
    const std::string cup = std::string("cup_") + who[0];
    const vec3 p = scene.props[who[0] == 'b' ? 0 : 1].transform.translation;
    actions.push_back({{"type", "pick_up"}, {"character", who}, {"prop", cup}, {"start", 10}});
    actions.push_back({{"type", "carry"}, {"character", who}, {"by", {0, 0.05, 0.01}}});
    actions.push_back({{"type", "place"}, {"verb", true}, {"character", who}, {"at", {p.x + 0.02f, p.y, p.z + 0.01f}}});
  }
  scene.actions = actions;

  // The expansion itself (pure): the context as the compile builds it.
  const TimingProfile T = loadTimingProfile(kRoot / "content/timing/calibrated.timing.json").value();
  const PersonalityProfile boyP = loadPersonality(kRoot / "content/personality/boy_yellow_hoodie.json").value();
  const PersonalityProfile girlP = loadPersonality(kRoot / "content/personality/girl_auburn_bun_glasses.json").value();
  const PropAsset asset = cupAsset();
  VerbContext vc;
  vc.timing = &T;
  for (size_t c = 0; c < 2; ++c) {
    const vec3 s = bonePos(*probe, c, "upperArm.R", 1), e = bonePos(*probe, c, "forearm.R", 1), w = bonePos(*probe, c, "hand.R", 1);
    VerbContext::Character ch{scene.characters[c].name, c == 0 ? &boyP : &girlP};
    ch.armLength[1] = glm::distance(s, e) + glm::distance(e, w);
    vc.characters.push_back(ch);
  }
  for (const PropDesc& p : scene.props) vc.props.push_back({p.name, &asset, p.transform, p.parent});
  vc.verb = [](const std::string& id) { return loadVerb(kRoot / "content/verbs" / (id + ".verb.json")); };
  auto x = expandVerbs(scene.actions, vc);
  if (!x) FAIL(x.error().message());

  auto len = [&](size_t action, const char* phase) {
    const VerbPhaseSpan* s = x->span(action, phase);
    REQUIRE(s);
    return s->to - s->from;
  };
  struct Expect {
    size_t base;
    const PersonalityProfile* P;
    const char* who;
  };
  double boyLook = 0, girlLook = 0;
  for (const Expect& e : {Expect{0, &boyP, "boy"}, Expect{3, &girlP, "girl"}}) {
    CAPTURE(e.who);
    const double look = T.frames("reaction_delay", 4, e.P), antic = T.frames("anticipation", 8, e.P);
    const double reach = T.frames("reach", 14, e.P), settle = T.frames("settle", 12, e.P);
    const double place = T.frames("place", 16, e.P), release = T.frames("release", 14, e.P);
    MESSAGE(std::string(e.who) << ": look " << look << ", anticipate " << antic << ", reach " << reach << ", settle " << settle << ", place " << place
                  << ", release " << release);
    CHECK(len(e.base, "look") == look);
    CHECK(len(e.base, "anticipate") == antic);
    CHECK(len(e.base, "approach") + len(e.base, "contact") == reach);
    CHECK(len(e.base, "contact") == doctest::Approx(std::min(6.0, 0.4 * reach)));
    CHECK(len(e.base, "settle") == settle);
    CHECK(len(e.base + 1, "manipulate") >= T.frames("hold", 16, e.P));
    CHECK(len(e.base + 1, "settle") == settle);
    CHECK(len(e.base + 2, "look") == look);
    CHECK(len(e.base + 2, "manipulate") == place);
    CHECK(len(e.base + 2, "release") == release);
    CHECK(len(e.base + 2, "settle") == settle);
    // The gaze leads the hand: the look ends at least 2 f before the approach starts.
    CHECK(x->span(e.base, "look")->to <= x->span(e.base, "approach")->from - 2);
    // Chained: the carry starts after the pick-up's settle, the place after the carry's.
    CHECK(x->span(e.base + 1, "manipulate")->from == x->span(e.base, "settle")->to);
    CHECK(x->span(e.base + 2, "manipulate")->from == x->span(e.base + 1, "settle")->to);
    (e.base == 0 ? boyLook : girlLook) = look;
  }
  // Tempo: the boy (beat_scale 1.2) is slower than the girl (0.85) on every beat-scaled phase.
  CHECK(boyLook > girlLook);
  CHECK(len(0, "anticipate") > len(3, "anticipate"));
  CHECK(len(0, "approach") + len(0, "contact") > len(3, "approach") + len(3, "contact"));
  CHECK(len(2, "manipulate") > len(5, "manipulate"));
  CHECK(len(2, "release") > len(5, "release"));

  // Compiled: the contact is exact (<= 0.5 mm, the verb's constraint) and the generated look is on the cup.
  auto ev = load(scene);
  for (const auto& w : ev->warnings()) MESSAGE(w);
  for (size_t c = 0; c < 2; ++c) {
    const double contact = x->span(c * 3, "contact")->to;
    const float d = glm::distance(ev->handGripPoint(c, 'R', contact), socketWorld(*ev, c, "grip", contact));
    MESSAGE(scene.characters[c].name << ": palm to grip at contact (frame " << contact << ") " << d * 1000 << " mm");
    CHECK(d <= 0.0005f);
    const VerbPhaseSpan* l = x->span(c * 3, "look");
    const vec3 middle = vec3(ev->propWorld(c, l->from + 3) * vec4(0, 0.05f, 0, 1));  // the cup's middle (100 mm tall)
    const std::string track = scene.characters[c].name + "/lookAt";
    CHECK(glm::distance(ev->scene().animation.evaluate(track, l->from + 3, vec3(0)), middle) < 1e-4f);
    const double placed = x->span(c * 3 + 2, "contact")->to;  // the place socket is on its target
    const vec3 p = scene.props[c].transform.translation;
    CHECK(glm::distance(socketWorld(*ev, c, "place", placed), vec3(p.x + 0.02f, p.y, p.z + 0.01f)) <= 0.0005f);
  }
}

// --------------------------------------------------------------------------------------------- failure cases (6)
namespace {

// A pure expansion over one or two characters and the given props (no geometry).
struct PureScene {
  PropAsset cup = cupAsset();
  std::vector<PropAsset> extra;
  VerbContext vc;
  explicit PureScene(int props = 1) {
    vc.characters = {{"boy", nullptr, {0.3f, 0.3f}}, {"girl", nullptr, {0.3f, 0.3f}}};
    extra.assign(3, cupAsset());
    for (int i = 0; i < props; ++i) {
      AssetTransform t;
      t.translation = vec3(0.2f * float(i), 0.5f, 0.3f);
      vc.props.push_back({i == 0 ? "cup" : "cup" + std::to_string(i + 1), i == 0 ? &cup : &extra[size_t(i - 1)], t, std::nullopt});
    }
    vc.verb = [](const std::string& id) { return loadVerb(kRoot / "content/verbs" / (id + ".verb.json")); };
  }
  VerbError fails(const char* actions) const {
    auto x = expandVerbs(Json::parse(actions), vc);
    REQUIRE_FALSE(x.has_value());
    MESSAGE(x.error().message());
    return x.error();
  }
};

void checkError(const VerbError& e, const char* verb, const char* who, const char* prop, const char* code, const char* text) {
  CHECK(e.verb == verb);
  CHECK(e.character == who);
  CHECK(e.prop == prop);
  CHECK(e.code == code);
  CHECK(e.reason.find(text) != std::string::npos);
  const std::string m = e.message();
  CHECK(m.find(std::string("'") + verb + "'") != std::string::npos);
  CHECK(m.find(std::string("'") + who + "'") != std::string::npos);
  CHECK(m.find(std::string("'") + prop + "'") != std::string::npos);
}

}  // namespace

TEST_CASE("verb failures: hand full") {
  PureScene s(2);
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "pick_up", "character": "boy", "prop": "cup2", "start": 30}])"),
             "pick_up", "boy", "cup2", "hand_full", "hand.R already holds 'cup'");
  // A primitive grasp fills the hand too.
  checkError(s.fails(R"([{"type": "grasp", "character": "boy", "hand": "R", "prop": "cup2", "start": 2},
                         {"type": "pick_up", "character": "boy", "prop": "cup", "start": 30}])"),
             "pick_up", "boy", "cup", "hand_full", "hand.R already holds 'cup2'");
}

TEST_CASE("verb failures: prop held by another character") {
  PureScene s;
  checkError(s.fails(R"([{"type": "pick_up", "character": "girl", "hand": "L", "prop": "cup", "start": 5},
                         {"type": "pick_up", "character": "boy", "prop": "cup", "start": 30}])"),
             "pick_up", "boy", "cup", "prop_held", "held by 'girl' (hand.L)");
  // An authored parent: the prop starts in the girl's hand.
  PureScene t;
  t.vc.props[0].parent = PropParent{PropParent::Kind::Character, "girl", "hand.R"};
  checkError(t.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5}])"), "pick_up", "boy", "cup", "prop_held",
             "held by 'girl' (hand.R)");
}

TEST_CASE("verb failures: unknown grasp site or set") {
  PureScene s;
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "rim", "start": 5}])"), "pick_up", "boy", "cup",
             "unknown_set", "no grasp set 'rim'");
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "site": "handle", "start": 5}])"), "pick_up", "boy",
             "cup", "unknown_site", "no grasp site 'handle'");
}

TEST_CASE("verb failures: wrong hand for the grasp site") {
  PureScene s;
  for (GraspSite& g : s.cup.affordances->sites) g.hand = "L";
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "hand": "R", "prop": "cup", "site": "side_a", "start": 5}])"),
             "pick_up", "boy", "cup", "wrong_hand", "grasp site 'side_a' is for hand.L, hand.R asked");
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "hand": "R", "prop": "cup", "start": 5}])"), "pick_up", "boy", "cup",
             "wrong_hand", "no grasp site of asset 'prop.felt_cup' is for hand.R");
  // The left hand may take it.
  CHECK(expandVerbs(Json::parse(R"([{"type": "pick_up", "character": "boy", "hand": "L", "prop": "cup", "start": 5}])"), s.vc).has_value());
}

TEST_CASE("verb failures: a two-hand prop with one hand") {
  PureScene s;
  s.cup.affordances->hands = "two";
  s.cup.affordances->sets.push_back({"both", {"side_a", "side_b"}, 2});
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5}])"), "pick_up", "boy", "cup", "two_hands",
             "needs two hands");
  PureScene t;
  t.cup.affordances->sets.push_back({"both", {"side_a", "side_b"}, 2});
  checkError(t.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "both", "start": 5}])"), "pick_up", "boy", "cup",
             "two_hands", "grasp set 'both' needs two hands");
}

TEST_CASE("verb failures: place target occupied, and onto itself") {
  PureScene s(3);
  s.vc.props[1].parent = PropParent{PropParent::Kind::Prop, "cup3", "contact"};  // cup2 already stands on cup3's rim socket
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "place", "verb": true, "character": "boy", "onto": {"prop": "cup3", "socket": "contact"}}])"),
             "place", "boy", "cup", "target_occupied", "socket 'contact' of 'cup3' already holds 'cup2'");
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "place", "verb": true, "character": "boy", "onto": {"prop": "cup", "socket": "contact"}}])"),
             "place", "boy", "cup", "onto_self", "itself");
  // The free socket is fine.
  CHECK(expandVerbs(Json::parse(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                                    {"type": "place", "verb": true, "character": "boy", "onto": {"prop": "cup2", "socket": "contact"}}])"),
                    s.vc)
            .has_value());
}

TEST_CASE("verb failures: non-rigid deform, invalid affordances, empty hand") {
  PureScene s;
  s.cup.affordances->deform = "squash";
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5}])"), "pick_up", "boy", "cup",
             "deform_unsupported", "deform mode 'squash' not supported yet");
  PureScene t;
  t.cup.affordances->error = "asset 'prop.felt_cup': affordances: hands \"two\" needs a grasp set of two sites";
  checkError(t.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5}])"), "pick_up", "boy", "cup",
             "affordances_invalid", "needs a grasp set of two sites");
  PureScene u;
  checkError(u.fails(R"([{"type": "carry", "character": "boy", "prop": "cup", "start": 5, "by": [0, 0.1, 0]}])"), "carry", "boy", "cup",
             "hand_empty", "hand.R holds nothing");
  checkError(u.fails(R"([{"type": "carry", "character": "boy", "prop": "cup", "by": [0, 0.1, 0]}])"), "carry", "boy", "cup", "no_start",
             "give 'start'");
}

TEST_CASE("verb failures: out of reach (checked on the compiled motion)") {
  Scene scene = baseScene();
  scene.characters.push_back(character("boy", kBoy, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 1.6f)));  // 1.66 arm lengths away
  scene.actions = Json::parse(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5}])");
  auto r = tryLoad(scene);
  REQUIRE_FALSE(r.has_value());
  MESSAGE(r.error().message);
  const std::string& m = r.error().message;
  CHECK(m.find("verb 'pick_up': character 'boy', prop 'cup': out_of_reach: hand.R cannot reach at frame 19") != std::string::npos);
  CHECK(m.find("mm short") != std::string::npos);
  // As primitives the same reach is a warning only (shots written as primitives keep warnings).
  scene.actions = Json::parse(R"([{"type": "grasp", "character": "boy", "hand": "R", "prop": "cup", "start": 5}])");
  auto ev = load(scene);
  CHECK_FALSE(ev->warnings().empty());
}

TEST_CASE("verb failures: upright exceeded (checked on the compiled motion)") {
  Scene scene = baseScene();
  scene.characters.push_back(character("boy", kBoy, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  scene.actions = Json::parse(R"([
      {"type": "pick_up", "character": "boy", "prop": "cup", "start": 5, "contact": 20},
      {"type": "carry", "character": "boy", "start": 22, "end": 36, "by": [0, 0.06, 0.02]}])");
  CHECK(tryLoad(scene).has_value());  // upright: fine
  scene.props[0].transform.rotationDeg.x = 30;  // the cup stands tilted 30 deg (max_tilt_deg 20); the carry keeps that
  auto r = tryLoad(scene);
  REQUIRE_FALSE(r.has_value());
  MESSAGE(r.error().message);
  CHECK(r.error().message.find("verb 'carry': character 'boy', prop 'cup': upright_exceeded: prop axis tilts 30.0 deg") !=
        std::string::npos);
}

// ------------------------------------------------------------------------------------------------- verb files
TEST_CASE("verb library: content/verbs files parse; bad files are errors") {
  for (const char* id : {"pick_up", "carry", "place"}) {
    auto v = loadVerb(kRoot / "content/verbs" / (std::string(id) + ".verb.json"));
    REQUIRE(v.has_value());
    CHECK(v->id == id);
    CHECK(findVerbFile(kRoot / "episodes/e907_exchange/shots/s010/shot.scene.json", id) == kRoot / "content/verbs" / (std::string(id) + ".verb.json"));
  }
  auto pick = loadVerb(kRoot / "content/verbs/pick_up.verb.json").value();
  CHECK(pick.lowersTo == "grasp");
  CHECK(pick.phase("look")->fallbackF == 4);
  CHECK(pick.phase("approach")->fallbackF == 14);
  CHECK(pick.phase("anticipate")->optional);
  CHECK_FALSE(verbFromJson(Json::parse(R"({"format": "plush.verb", "version": 1, "id": "x", "lowers_to": "grasp",
                                           "phases": [{"name": "wiggle"}]})")));
  CHECK_FALSE(verbFromJson(Json::parse(R"({"format": "plush.verb", "version": 1, "id": "x", "lowers_to": "throw",
                                           "phases": [{"name": "look"}]})")));
  CHECK_FALSE(verbFromJson(Json::parse(R"({"format": "plush.verb", "version": 2, "id": "x"})")));
  CHECK(isVerbAction(Json::parse(R"({"type": "pick_up"})")));
  CHECK(isVerbAction(Json::parse(R"({"type": "place", "verb": true})")));
  CHECK_FALSE(isVerbAction(Json::parse(R"({"type": "place"})")));  // the primitive
  CHECK_FALSE(isVerbAction(Json::parse(R"({"type": "grasp"})")));
}

// ================================================================================================== T-112b
// pass, reactions, hand shapes, two-handed grasp sets, finger bands (docs/architecture/INTERACTION_AFFORDANCES.md 2.3,
// 2.4, 2.6, 4.4, 4.5, 5).
namespace {

// Giver and receiver face each other (as test_interaction.cpp meetingPoint); the cup in front of the giver.
Scene passScene(const char* giver, const char* receiver) {
  Scene scene = baseScene();
  scene.characters.push_back(character("giver", giver, vec3(-0.18f, 0, 0), 70));
  scene.characters.push_back(character("receiver", receiver, vec3(0.18f, 0, 0), -70));
  auto probe = load(scene);
  const float yaw = glm::radians(70.0f);
  const vec3 fwd(std::sin(yaw), 0, std::cos(yaw)), right(-std::cos(yaw), 0, std::sin(yaw));
  scene.props.push_back(cupFor(*probe, 0, "cup", 250, 0.85f * fwd + 0.06f * right + vec3(0, -0.45f, 0)));
  return scene;
}

const TimingProfile& calibrated() {
  static const TimingProfile T = loadTimingProfile(kRoot / "content/timing/calibrated.timing.json").value();
  return T;
}
const PersonalityProfile& boyProfile() {
  static const PersonalityProfile P = loadPersonality(kRoot / "content/personality/boy_yellow_hoodie.json").value();
  return P;
}
const PersonalityProfile& girlProfile() {
  static const PersonalityProfile P = loadPersonality(kRoot / "content/personality/girl_auburn_bun_glasses.json").value();
  return P;
}

PropAsset trayAsset() { return loadAsset(kRoot / "content/assets/felt_tray.asset.json").value(); }

// The felt tray (scaled to the doll-sized test characters) level in front of character c's chest: its centre
// `forward` arm lengths ahead of the shoulders' midpoint and `down` arm lengths below them.
PropDesc trayFor(const SceneEvaluator& probe, size_t c, float forward, float down, float scale) {
  PropDesc t;
  t.name = "tray";
  t.id = "prop.felt_tray";
  const vec3 l = bonePos(probe, c, "upperArm.L", 1), r = bonePos(probe, c, "upperArm.R", 1);
  const vec3 e = bonePos(probe, c, "forearm.R", 1), w = bonePos(probe, c, "hand.R", 1);
  const float arm = glm::distance(r, e) + glm::distance(e, w);
  const float yaw = glm::radians(probe.scene().characters[c].yawDeg);
  const vec3 fwd(std::sin(yaw), 0, std::cos(yaw));
  t.transform.translation = 0.5f * (l + r) + fwd * (forward * arm) - vec3(0, down * arm, 0);
  t.transform.rotationDeg = {0, probe.scene().characters[c].yawDeg + 180, 0};  // side_l (-x) at the character's left
  t.transform.scale = vec3(scale);
  return t;
}

vec3 trayFoot(const SceneEvaluator& ev, size_t p, const std::string& socket, double f) {
  return vec3((ev.propWorld(p, f) * assetTransformMatrix(trayAsset().sockets.at(socket)))[3]);
}

}  // namespace

// ------------------------------------------------------------------------------------------- pass equivalence (1)
TEST_CASE("verbs T-112b: pass without a profile expands to the hand-written handover, key for key") {
  for (auto [g, r] : {std::pair{kBoy, kGirl}, std::pair{kGirl, kBoy}}) {
    CAPTURE(g);
    const Scene scene = passScene(g, r);
    // Defaults (design 3.3: receiverStart +4, contact +18, release +4, end +12) and authored frames.
    for (const char* frames : {R"({"start": 26})", R"({"start": 26, "receiverStart": 28, "contact": 46, "release": 52, "end": 64})"}) {
      CAPTURE(frames);
      const Json f = Json::parse(frames);
      Scene hand = scene, verb = scene;
      hand.actions = Json::parse(R"([{"type": "grasp", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
          {"type": "handover", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R"}])");
      verb.actions = Json::parse(R"([{"type": "pick_up", "character": "giver", "hand": "R", "prop": "cup", "start": 4, "contact": 18},
          {"type": "pass", "character": "giver", "hand": "R", "to": "receiver", "toHand": "R"}])");
      hand.actions[1].update(f);
      verb.actions[1].update(f);
      auto a = load(hand);
      auto b = load(verb);
      checkSameClip(*a, *b);
      CHECK(a->warnings() == b->warnings());
      REQUIRE(a->scene().props[0].parentSwitch.size() == b->scene().props[0].parentSwitch.size());
      for (size_t k = 0; k < a->scene().props[0].parentSwitch.size(); ++k) {
        CHECK(a->scene().props[0].parentSwitch[k].frame == b->scene().props[0].parentSwitch[k].frame);
        CHECK(a->scene().props[0].parentSwitch[k].parent->name == b->scene().props[0].parentSwitch[k].parent->name);
      }
      for (double fr : {20.0, 46.0, 60.0, 100.0}) CHECK(a->propWorld(0, fr) == b->propWorld(0, fr));
    }
  }
}

TEST_CASE("verbs T-112b: pass phases follow the handover frames; with a profile each beat is the acting character's") {
  PropAsset cup = cupAsset();
  VerbContext vc;
  vc.characters = {{"boy", &boyProfile(), {0.27f, 0.27f}}, {"girl", &girlProfile(), {0.18f, 0.18f}}};
  vc.props = {{"cup", &cup, AssetTransform{}, std::nullopt}};
  vc.verb = [](const std::string& id) { return loadVerb(kRoot / "content/verbs" / (id + ".verb.json")); };
  const Json actions = Json::parse(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "a", "start": 4, "contact": 20},
      {"type": "pass", "character": "boy", "hand": "R", "to": "girl", "toHand": "L", "start": 40}])");
  // No profile: the handover defaults.
  auto x0 = expandVerbs(actions, vc);
  REQUIRE(x0);
  const Json& h0 = x0->actions[1];
  CHECK(h0["type"] == "handover");
  CHECK(h0["toSocket"] == "grip_b");  // the cup's handover receive set "b"
  CHECK(h0["receiverStart"] == 44);
  CHECK(h0["contact"] == 58);
  CHECK(h0["release"] == 62);
  CHECK(h0["end"] == 74);
  // Calibrated: receiver look = reaction_delay (girl), reach (girl), shared_hold and release (boy).
  const TimingProfile& T = calibrated();
  vc.timing = &T;
  auto x = expandVerbs(actions, vc);
  REQUIRE(x);
  const Json& h = x->actions[2];  // after the pick-up's generated look and grasp
  REQUIRE(h["type"] == "handover");
  const double rs = 40 + T.frames("reaction_delay", 4, &girlProfile()), c = rs + T.frames("reach", 14, &girlProfile());
  const double rel = c + T.frames("shared_hold", 4, &boyProfile()), end = rel + T.frames("release", 12, &boyProfile());
  CHECK(h["receiverStart"].get<double>() == doctest::Approx(rs));
  CHECK(h["contact"].get<double>() == doctest::Approx(c));
  CHECK(h["release"].get<double>() == doctest::Approx(rel));
  CHECK(h["end"].get<double>() == doctest::Approx(end));
  CHECK(x->span(1, "look")->character == "girl");
  CHECK(x->span(1, "look")->to == doctest::Approx(rs));
  CHECK(x->span(1, "approach")->from == doctest::Approx(rs));
  CHECK(x->span(1, "contact")->to == doctest::Approx(c));
  CHECK(x->span(1, "manipulate", "shared")->to - x->span(1, "manipulate", "shared")->from == doctest::Approx(rel - c));
  CHECK(x->span(1, "release")->to == doctest::Approx(end));
  CHECK(x->span(1, "settle")->to - x->span(1, "settle")->from == doctest::Approx(T.frames("settle", 12, &boyProfile())));
  CHECK(x->events.empty());  // no "react"
  // A verb after the pass on the receiving hand chains on the giver's release.
  const Json chained = Json::parse(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "a", "start": 4, "contact": 20},
      {"type": "pass", "character": "boy", "hand": "R", "to": "girl", "toHand": "L", "start": 40},
      {"type": "carry", "character": "girl", "hand": "L", "by": [0, 0.02, 0]}])");
  auto y = expandVerbs(chained, vc);
  REQUIRE(y);
  CHECK(y->span(2, "manipulate")->from == doctest::Approx(rel));
}

// ------------------------------------------------------------------------------------------------ reactions (2)
TEST_CASE("verbs T-112b: react appends partner_acts / success events; the notice delay is reaction_delay x tempo") {
  PropAsset cup = cupAsset();
  const TimingProfile& T = calibrated();
  auto base = [&](const PersonalityProfile* receiver, const PersonalityProfile* giver) {
    VerbContext vc;
    vc.timing = &T;
    vc.events = true;
    vc.characters = {{"giver", giver, {0.27f, 0.27f}}, {"receiver", receiver, {0.18f, 0.18f}}};
    vc.props = {{"cup", &cup, AssetTransform{}, std::nullopt}};
    vc.verb = [](const std::string& id) { return loadVerb(kRoot / "content/verbs" / (id + ".verb.json")); };
    return vc;
  };
  const Json actions = Json::parse(R"([{"type": "pick_up", "character": "giver", "prop": "cup", "start": 4, "contact": 20},
      {"type": "pass", "character": "giver", "to": "receiver", "start": 49, "react": true}])");
  struct Case {
    const char* name;
    const PersonalityProfile* receiver;
    double delay;  // expected notice delay (frames at 24 fps)
  };
  // girl: delay_frames [4, 6] middle 5 x reaction tempo_scale 0.9 = 4.5 (>= the low end 4); boy: [16, 26] middle 21
  // x tempo 1.0 (reluctant: the look phase is delayed, T-111 decision); no profile: the profile's reaction_delay 6.
  for (const Case& k : {Case{"girl", &girlProfile(), 5 * 0.9}, Case{"boy", &boyProfile(), 21.0}, Case{"none", nullptr, 6.0}}) {
    CAPTURE(k.name);
    const VerbContext vc = base(k.receiver, &boyProfile());
    auto x = expandVerbs(actions, vc);
    REQUIRE(x);
    REQUIRE(x->events.size() == 1);
    const Json& e = x->events[0];
    CHECK(e["kind"] == "partner_acts");
    CHECK(e["source"] == "giver");
    CHECK(e["characters"] == Json::array({"receiver"}));
    CHECK(e["time"].get<double>() == doctest::Approx(48.0 / 24.0));  // frame 49, frameStart 1
    const VerbPhaseSpan* look = x->span(1, "look");
    REQUIRE(look);
    MESSAGE(k.name << ": notice at " << look->from << " (delay " << look->from - 49 << " f), reach from " << look->to);
    CHECK(look->from - 49 == doctest::Approx(k.delay));
    CHECK(look->to - look->from >= 4);  // the gaze leads the hand by 4 f, to the next whole frame (gaze_leads_hand >= 2 f)
    CHECK(look->to - look->from < 5);
    CHECK(look->to == std::round(look->to));
    // One gaze source: the handover plays no gaze of its own; the giver's gaze comes as looks.
    const Json* h = nullptr;
    int looks = 0;
    const Json* rlook = nullptr;
    for (const Json& a : x->actions) {
      if (a["type"] == "handover") h = &a;
      if (a["type"] == "look" && a["character"] == "giver" && a["start"].get<double>() >= 49) ++looks;
      if (a["type"] == "look" && a["character"] == "receiver") rlook = &a;
    }
    // The receiver's only generated look starts with the reach (after the reaction's notice), on the cup.
    REQUIRE(rlook);
    CHECK((*rlook)["atProp"] == "cup");
    CHECK((*rlook)["start"].get<double>() == look->to);
    REQUIRE(h);
    CHECK((*h)["look"] == false);
    CHECK((*h)["receiverStart"].get<double>() == std::ceil(49 + k.delay + 4 - 1e-6));
    CHECK(looks == 2);
  }
  // Without scene events "react" adds nothing and the pass keeps its own receiver look.
  VerbContext quiet = base(&girlProfile(), &boyProfile());
  quiet.events = false;
  auto q = expandVerbs(actions, quiet);
  REQUIRE(q);
  CHECK(q->events.empty());
  CHECK_FALSE(q->actions.back().contains("look"));
  // place: success at the settle start.
  const Json placing = Json::parse(R"([{"type": "pick_up", "character": "giver", "prop": "cup", "start": 4, "contact": 20},
      {"type": "place", "verb": true, "character": "giver", "at": [0.1, 0.5, 0.3], "start": 40, "contact": 60, "end": 73, "react": true}])");
  auto pz = expandVerbs(placing, base(&girlProfile(), &boyProfile()));
  REQUIRE(pz);
  REQUIRE(pz->events.size() == 1);
  CHECK(pz->events[0]["kind"] == "success");
  CHECK(pz->events[0]["source"] == "giver");
  CHECK(pz->events[0]["time"].get<double>() == doctest::Approx(72.0 / 24.0));
}

// ----------------------------------------------------------------------------------------------- hand shapes (3)
TEST_CASE("verbs T-112b: non-wrap hand shapes key their open / closed poses; no contact search; release opens them") {
  Scene scene = baseScene();
  scene.frameEnd = 80;
  scene.characters.push_back(character("actor", kBoy, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  const vec3 p0 = scene.props[0].transform.translation;
  struct Shape {
    const char* name;
    vec3 open, closed;
    float closedIndex;
  };
  for (const Shape& s : {Shape{"palm", {0.08f, 0.3f, 0}, {0.15f, 0.35f, 0}, -1}, Shape{"hook", {0.2f, 0.1f, 0}, {0.7f, 0.1f, 0}, -1},
                         Shape{"cradle", {0.1f, 0.25f, 0.2f}, {0.3f, 0.25f, 0.2f}, -1},
                         Shape{"pinch", {0.1f, 0.2f, 0.1f}, {0.6f, 0.5f, 0.1f}, 0.35f}}) {
    CAPTURE(s.name);
    Scene sc = scene;
    sc.actions = Json::parse(R"([{"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
        {"type": "place", "character": "actor", "hand": "R", "start": 30, "contact": 46, "end": 60}])");
    sc.actions[0]["shape"] = s.name;
    sc.actions[1]["at"] = {p0.x, p0.y, p0.z};
    auto ev = load(sc);
    const Clip& gen = *ev->scene().animation.generated;
    const Track* pose = gen.find("actor/hand.R");
    REQUIRE(pose);
    CHECK(pose->evaluate(14) == s.open);  // pre = 20 - 6
    CHECK(pose->evaluate(16) == s.open);  // contact - 4: still open, the fingers close in the last 4 f
    CHECK(pose->evaluate(20) == s.closed);
    CHECK(pose->evaluate(46) == s.closed);  // held closed until the place contact
    CHECK(pose->evaluate(49) == s.open);    // opened on release
    CHECK(gen.find("actor/hand.R.grasp") == nullptr);  // no contact search
    if (s.closedIndex >= 0) {
      REQUIRE(gen.find("actor/hand.R.index"));
      CHECK(gen.find("actor/hand.R.index")->evaluate(20).x == doctest::Approx(s.closedIndex));
    } else {
      CHECK(gen.find("actor/hand.R.index") == nullptr);
    }
    // The palm is still exactly on the socket.
    CHECK(glm::distance(ev->handGripPoint(0, 'R', 20), socketWorld(*ev, 0, "grip", 20)) <= 0.0005f);
  }
  // wrap is today's grasp (the golden test covers the bakes); an unknown shape is an error.
  Scene bad = scene;
  bad.actions = Json::parse(R"([{"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "shape": "claw"}])");
  auto r = tryLoad(bad);
  REQUIRE_FALSE(r);
  CHECK(r.error().message.find("unknown hand shape 'claw'") != std::string::npos);
}

// ------------------------------------------------------------------------------------------------- finger band (5)
TEST_CASE("verbs T-112b: hand.<s>.band keys from a site's fingers block (Step at the reach start), gated like the optional phases") {
  Scene scene = baseScene();
  scene.frameEnd = 60;
  scene.characters.push_back(character("actor", kBoy, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(cupFor(*probe, 0, "cup", 180, vec3(0.04f, -0.45f, 0.85f)));
  auto bandOf = [&](const char* action, const Json& timing) -> const Track* {
    Scene s = scene;
    s.timing = timing;
    s.actions = Json::array({Json::parse(action)});
    static std::unique_ptr<SceneEvaluator> keep;
    keep = load(s);
    return keep->scene().animation.generated->find("actor/hand.R.band");
  };
  // side_a: grip at 66 mm on the cup's axis, band [0.045, 0.09], thumb opposed -> (-0.021, 0.024, 0).
  const Track* t = bandOf(R"({"type": "pick_up", "character": "actor", "prop": "cup", "set": "a", "start": 5, "fingers": true})", "none");
  REQUIRE(t);
  REQUIRE(t->keys.size() == 1);
  CHECK(t->keys[0].frame == 5);
  CHECK(t->keys[0].interp == Interp::Step);
  CHECK(t->keys[0].value.x == doctest::Approx(0.045 - 0.066).epsilon(1e-4));
  CHECK(t->keys[0].value.y == doctest::Approx(0.09 - 0.066).epsilon(1e-4));
  CHECK(t->keys[0].value.z == 0);
  // With a profile the band is written; with "none" (legacy expansion) and with "fingers": false it is not.
  const Track* p = bandOf(R"({"type": "pick_up", "character": "actor", "prop": "cup", "set": "a", "start": 5})", "calibrated");
  REQUIRE(p);
  CHECK(p->keys[0].frame == 5 + calibrated().frames("anticipation", 8, nullptr));  // the reach start, after the anticipation
  CHECK(bandOf(R"({"type": "pick_up", "character": "actor", "prop": "cup", "set": "a", "start": 5})", "none") == nullptr);
  // T-104d: an absent timing key is the calibrated profile, so the band is written.
  CHECK(bandOf(R"({"type": "pick_up", "character": "actor", "prop": "cup", "set": "a", "start": 5})", Json()) != nullptr);
  CHECK(bandOf(R"({"type": "pick_up", "character": "actor", "prop": "cup", "set": "a", "start": 5, "fingers": false})", "calibrated") ==
        nullptr);
}

// -------------------------------------------------------------------------------------------- two-handed tray (4)
TEST_CASE("verbs T-112b: two-handed tray - pick up, carry, place on boy and girl skeletons") {
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    Scene scene = baseScene();
    scene.frameEnd = 120;
    scene.timing = "calibrated";
    scene.characters.push_back(character("actor", asset, vec3(0), 0));
    auto probe = load(scene);
    scene.props.push_back(trayFor(*probe, 0, 0.75f, 0.55f, 0.6f));
    const vec3 t0 = scene.props[0].transform.translation;
    scene.actions = Json::parse(R"([
        {"type": "pick_up", "character": "actor", "hands": ["L", "R"], "prop": "tray", "start": 8},
        {"type": "carry", "character": "actor", "hands": ["L", "R"], "by": [0, 0.03, 0.01]},
        {"type": "place", "verb": true, "character": "actor", "hands": ["L", "R"]}])");
    const float foot = 0.015f * 0.6f;  // the place socket is the tray's bottom centre
    scene.actions[2]["at"] = {t0.x, t0.y - foot, t0.z};
    auto ev = load(scene);
    for (const auto& w : ev->warnings()) MESSAGE(w);

    // The expansion (to read the frames).
    VerbContext vc;
    const TimingProfile& T = calibrated();
    vc.timing = &T;
    VerbContext::Character ch{"actor", nullptr, {0.2f, 0.2f}};
    vc.characters = {ch};
    const PropAsset tray = trayAsset();
    vc.props = {{"tray", &tray, scene.props[0].transform, std::nullopt}};
    vc.verb = [](const std::string& id) { return loadVerb(kRoot / "content/verbs" / (id + ".verb.json")); };
    auto x = expandVerbs(scene.actions, vc);
    REQUIRE(x);
    const Json* lead = nullptr;
    const Json* follow = nullptr;
    for (const Json& a : x->actions)
      if (a["type"] == "grasp") (a.contains("follower") ? follow : lead) = &a;
    REQUIRE(lead);
    REQUIRE(follow);
    CHECK((*lead)["hand"] == "L");
    CHECK((*lead)["socket"] == "side_l");
    CHECK((*lead)["shape"] == "palm");
    CHECK((*follow)["hand"] == "R");
    CHECK((*follow)["socket"] == "side_r");
    const double c1 = (*lead)["contact"].get<double>(), c2 = (*follow)["contact"].get<double>();
    CHECK(c2 - c1 >= 1);
    CHECK(c2 - c1 <= 2);  // simultaneous_frames
    const double placed = x->span(2, "contact")->to, lifted = x->span(1, "manipulate")->from;

    // One parent: the tray switches to the leading hand at its contact and to the world at the place contact.
    const auto& sw = ev->scene().props[0].parentSwitch;
    REQUIRE(sw.size() == 2);
    CHECK(sw[0].frame == c1);
    REQUIRE(sw[0].parent);
    CHECK(sw[0].parent->socket == "hand.L");
    CHECK(sw[1].frame == placed);
    CHECK_FALSE(sw[1].parent);
    // Both palms on their sockets from the follower's contact to the place contact; both arms outside the body; the
    // tray level within 8 deg.
    float worstPalm = 0, worstGap = 1e9f, worstTilt = 0;
    for (double f = c2; f <= placed; f += 1) {
      worstPalm = std::max(worstPalm, glm::distance(ev->handGripPoint(0, 'L', f), trayFoot(*ev, 0, "side_l", f)));
      worstPalm = std::max(worstPalm, glm::distance(ev->handGripPoint(0, 'R', f), trayFoot(*ev, 0, "side_r", f)));
      worstGap = std::min({worstGap, ev->armClearanceAt(0, 'L', f).gap, ev->armClearanceAt(0, 'R', f).gap});
      const vec3 up = glm::normalize(mat3(ev->propWorld(0, f)) * vec3(0, 1, 0));
      worstTilt = std::max(worstTilt, glm::degrees(std::acos(std::clamp(up.y, -1.0f, 1.0f))));
    }
    MESSAGE("contacts " << c1 << " / " << c2 << ", lift " << lifted << ", placed " << placed << ": palm error " << worstPalm * 1000
                        << " mm, arm gap " << worstGap * 1000 << " mm, tilt " << worstTilt << " deg");
    CHECK(worstPalm <= 0.0005f);
    CHECK(worstGap >= 0);
    CHECK(worstTilt <= 8.0f);
    // The carry moved it (by 3 cm up, 1 cm forward) and the place put it back down on the target.
    CHECK(trayFoot(*ev, 0, "place", placed - 26)[1] > t0.y - foot + 0.02f);
    CHECK(glm::distance(trayFoot(*ev, 0, "place", placed), vec3(t0.x, t0.y - foot, t0.z)) <= 0.0005f);
    CHECK(glm::distance(trayFoot(*ev, 0, "place", 120), vec3(t0.x, t0.y - foot, t0.z)) <= 0.0005f);
    // Both hands let go: palm shapes open, IK released by the end of the release.
    const Clip& gen = *ev->scene().animation.generated;
    for (const char* hs : {"L", "R"}) {
      CHECK(gen.find(std::string("actor/hand.") + hs + ".grasp") == nullptr);
      CHECK(ev->scene().animation.evaluate(std::string("actor/ik.hand.") + hs + ".weight", x->span(2, "release")->to, vec3(1)).x ==
            doctest::Approx(0));
    }
  }
}

// ------------------------------------------------------------------------------------------- failure cases (6)
TEST_CASE("verb failures T-112b: pass - receiver hand full, receiver is the giving hand") {
  PureScene s(2);
  checkError(s.fails(R"([{"type": "pick_up", "character": "girl", "hand": "L", "prop": "cup2", "start": 2},
                         {"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "pass", "character": "boy", "to": "girl", "toHand": "L", "start": 30}])"),
             "pass", "boy", "cup", "hand_full", "receiver 'girl' hand.L already holds 'cup2'");
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "pass", "character": "boy", "to": "boy", "toHand": "R", "start": 30}])"),
             "pass", "boy", "cup", "same_hand", "the receiving hand is the giving hand");
  // The other hand of the same character may take it.
  CHECK(expandVerbs(Json::parse(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                                    {"type": "pass", "character": "boy", "to": "boy", "toHand": "L", "start": 30}])"), s.vc).has_value());
}

TEST_CASE("verb failures T-112b: pass - giver and receiver on the same socket or the same band") {
  PureScene s;
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "a", "start": 5},
                         {"type": "pass", "character": "boy", "to": "girl", "toSocket": "grip", "start": 30}])"),
             "pass", "boy", "cup", "hands_meet", "same socket 'grip'");
  PureScene t;  // grip_b moved to the grip's side: the bands [0.045, 0.09] and [0.01, 0.055] overlap there
  t.cup.sockets["grip_b"].translation.x = 0.04f;
  checkError(t.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "a", "start": 5},
                         {"type": "pass", "character": "boy", "to": "girl", "start": 30}])"),
             "pass", "boy", "cup", "hands_meet", "overlap on the same side");
  // As authored (grip_b on the far side) the same bands are fine.
  CHECK(expandVerbs(Json::parse(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "set": "a", "start": 5},
                                    {"type": "pass", "character": "boy", "to": "girl", "start": 30}])"), s.vc).has_value());
}

TEST_CASE("verb failures T-112b: pass - shared hold shorter than 6 f, a prop held in two hands") {
  PureScene s;
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "pass", "character": "boy", "to": "girl", "start": 30, "contact": 50, "release": 53}])"),
             "pass", "boy", "cup", "shared_too_short", "shared hold 3 f");
  PureScene t;
  PropAsset tray = trayAsset();
  t.vc.props[0].asset = &tray;
  checkError(t.fails(R"([{"type": "pick_up", "character": "boy", "hands": ["L", "R"], "prop": "cup", "start": 5},
                         {"type": "pass", "character": "boy", "hand": "L", "to": "girl", "start": 40}])"),
             "pass", "boy", "cup", "two_hands", "held in two hands");
}

TEST_CASE("verb failures T-112b: pass - receiver out of reach (checked on the compiled motion)") {
  Scene scene = passScene(kBoy, kGirl);
  scene.characters[1].position.x = 0.9f;  // far away: no meeting point both can reach
  scene.actions = Json::parse(R"([{"type": "pick_up", "character": "giver", "prop": "cup", "start": 4, "contact": 18},
      {"type": "pass", "character": "giver", "to": "receiver", "start": 26}])");
  auto r = tryLoad(scene);
  REQUIRE_FALSE(r);
  MESSAGE(r.error().message);
  CHECK(r.error().message.find("verb 'pass'") != std::string::npos);
  CHECK(r.error().message.find("out_of_reach") != std::string::npos);
}

TEST_CASE("verb failures T-112b: two hands - no two-site set, set does not fit the hands, bad hands, second hand full") {
  PureScene s;
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "hands": ["L", "R"], "prop": "cup", "start": 5}])"), "pick_up", "boy",
             "cup", "unknown_set", "no two-site grasp set");
  checkError(s.fails(R"([{"type": "pick_up", "character": "boy", "hands": ["L", "L"], "prop": "cup", "start": 5}])"), "pick_up", "boy",
             "cup", "bad_hand", "'hands' must be");
  PureScene t(2);
  PropAsset tray = trayAsset();
  t.vc.props[0].asset = &tray;
  checkError(t.fails(R"([{"type": "pick_up", "character": "boy", "hand": "L", "prop": "cup2", "start": 2},
                         {"type": "pick_up", "character": "boy", "hands": ["R", "L"], "prop": "cup", "start": 5}])"),
             "pick_up", "boy", "cup", "hand_full", "hand.L already holds 'cup2'");
  PureScene u;
  PropAsset wrong = trayAsset();
  for (GraspSite& g : wrong.affordances->sites) g.hand = "R";
  u.vc.props[0].asset = &wrong;
  checkError(u.fails(R"([{"type": "pick_up", "character": "boy", "hands": ["L", "R"], "prop": "cup", "start": 5}])"), "pick_up", "boy",
             "cup", "wrong_hand", "does not fit hands [L, R]");
  // carry with two hands of a prop held in one
  PureScene v;
  checkError(v.fails(R"([{"type": "pick_up", "character": "boy", "prop": "cup", "start": 5},
                         {"type": "carry", "character": "boy", "hands": ["R", "L"], "by": [0, 0.1, 0]}])"),
             "carry", "boy", "cup", "two_hands", "not held in two hands");
  // the tray with one hand (design 2.6)
  PureScene w;
  w.vc.props[0].asset = &tray;
  checkError(w.fails(R"([{"type": "pick_up", "character": "boy", "hand": "R", "prop": "cup", "start": 5}])"), "pick_up", "boy", "cup",
             "two_hands", "needs two hands: give hands:[L,R]");
}

TEST_CASE("verb failures T-112b: two hands - the second hand cannot follow the carry (checked on the compiled motion)") {
  Scene scene = baseScene();
  scene.frameEnd = 120;
  scene.timing = "calibrated";
  scene.characters.push_back(character("actor", kBoy, vec3(0), 0));
  auto probe = load(scene);
  scene.props.push_back(trayFor(*probe, 0, 0.75f, 0.55f, 0.6f));
  scene.actions = Json::parse(R"([
      {"type": "pick_up", "character": "actor", "hands": ["L", "R"], "prop": "tray", "start": 8},
      {"type": "carry", "character": "actor", "hands": ["L", "R"], "by": [0.16, 0, 0]}])");
  auto r = tryLoad(scene);
  REQUIRE_FALSE(r);
  MESSAGE(r.error().message);
  CHECK(r.error().message.find("verb 'carry': character 'actor', prop 'tray': out_of_reach: hand.R") != std::string::npos);
}

TEST_CASE("verb library T-112b: pass.verb.json parses; phase parts tell the two manipulate phases apart") {
  auto v = loadVerb(kRoot / "content/verbs/pass.verb.json");
  REQUIRE(v);
  CHECK(v->lowersTo == "handover");
  REQUIRE(v->phase("manipulate", "offer"));
  REQUIRE(v->phase("manipulate", "shared"));
  CHECK(v->phase("manipulate", "shared")->beat == "shared_hold");
  CHECK(v->phase("look")->who == "receiver");
  CHECK(isVerbAction(Json::parse(R"({"type": "pass"})")));
  CHECK_FALSE(isVerbAction(Json::parse(R"({"type": "handover"})")));
  CHECK_FALSE(verbFromJson(Json::parse(R"({"format": "plush.verb", "version": 1, "id": "x", "lowers_to": "handover",
      "phases": [{"name": "manipulate", "part": "a"}, {"name": "manipulate", "part": "a"}]})")));
  CHECK(verbFromJson(Json::parse(R"({"format": "plush.verb", "version": 1, "id": "x", "lowers_to": "handover",
      "phases": [{"name": "manipulate", "part": "a"}, {"name": "manipulate", "part": "b"}]})")));
}

TEST_CASE("verbs T-112b: a reacting pass compiles through the reaction system (scene events; one gaze source)") {
  for (auto [g, r] : {std::pair{kBoy, kGirl}, std::pair{kGirl, kBoy}}) {
    CAPTURE(g);
    Scene scene = passScene(g, r);
    scene.timing = "calibrated";
    scene.characters[0].personality = g == kBoy ? "boy_yellow_hoodie" : "girl_auburn_bun_glasses";
    scene.characters[1].personality = r == kBoy ? "boy_yellow_hoodie" : "girl_auburn_bun_glasses";
    scene.events = Json::array();
    scene.actions = Json::parse(R"([{"type": "pick_up", "character": "giver", "prop": "cup", "start": 4, "contact": 22, "settle": 4},
        {"type": "pass", "character": "giver", "to": "receiver", "react": true}])");
    auto ev = load(scene);
    for (const auto& w : ev->warnings()) MESSAGE(w);
    // The expected notice: pass start 26 (pick_up contact 22 + settle 4) + the receiver's delay.
    const PersonalityProfile& R = r == kBoy ? boyProfile() : girlProfile();
    const double delay = std::max(double(R.reaction.delayFrames->mid() * R.reaction.tempoScale.value_or(1.f)), double(R.reaction.delayFrames->lo));
    const double notice = 26 + delay, reach = std::ceil(notice + 4 - 1e-6);
    const Track* look = ev->scene().animation.generated->find("receiver/lookAt");
    REQUIRE(look);
    // A key at the notice (the reaction's look starts there) ...
    bool keyed = false;
    for (const Key& k : look->keys) keyed |= std::abs(k.frame - notice) < 1e-3;
    CHECK(keyed);
    // ... at the giver's face; from the reach on the cup.
    const vec3 head = bonePos(*ev, 0, "head", notice + 3);
    const vec3 cupMid = vec3(ev->propWorld(0, reach + 8) * vec4(0, 0.05f, 0, 1));
    CHECK(glm::distance(look->evaluate(notice + 3), head) < glm::distance(look->evaluate(notice + 3), vec3(ev->propWorld(0, notice + 3)[3])));
    CHECK(glm::distance(look->evaluate(reach + 8), cupMid) < 0.01f);  // the look keys a moving cup every few frames (cup radius 40 mm)
    // The palm is on the receiver's socket at contact (the verb's constraint passed: no load error).
    CHECK(ev->scene().props[0].parentSwitch.back().parent->name == "receiver");
  }
}
