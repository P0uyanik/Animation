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
