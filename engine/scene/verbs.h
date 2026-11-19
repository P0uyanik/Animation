// Verb library and verb expander (T-112a, docs/architecture/INTERACTION_AFFORDANCES.md sections 3, 4, 6).
//
// A verb (content/verbs/<id>.verb.json, plush.verb/1) is an ordered list of phases (look, anticipate, approach,
// contact, manipulate, release, settle), each with a timing beat of the T-104 profile and the current engine default
// as its fallback. The expander is a pure Json -> Json pre-pass: it turns verb actions into the existing primitive
// interaction actions (grasp, hold, place) with explicit frames, plus generated look actions, before
// planReactionActions and compileInteraction run. A scene without a verb action never enters it.
//
// Verb actions (scene "actions"):
//   pick_up {character, hand="R", prop, set? | site? | socket?, start?, contact?, anticipate?, settle?, look=true}
//   carry   {character, hand="R", prop?, start?, end?, at:[x,y,z] | by:[dx,dy,dz], settle?, look=true}
//   place   {"verb": true, character, hand="R", prop?, start?, contact?, end?, at:[x,y,z] | onto:{prop, socket},
//            socket?, settle?, look=true}
// "place" is also a primitive, so a verb place says "verb": true; pick_up and carry are verbs by type.
// A missing start chains on the previous verb of the same hand (its end, settle included).
//
// Frames (S = start, profile = the scene's "timing", each beat scaled by the character's personality tempo):
//   pick_up   look S-reaction_delay..S (fallback 4: the primitive's own gaze lead) | anticipate S..S+anticipation
//             (optional) | approach + contact: reach (fallback 14) | settle: settle (optional)
//   carry     manipulate: max(hold, travelFrames) (fallback 16) | settle (optional)
//   place     look (fallback 4) | manipulate (lower): place (fallback 16) | release: release (fallback 14) |
//             settle (optional)
// Optional phases are emitted when the scene has a timing profile or the action sets them ("anticipate": true,
// "settle": true); without a profile and without the flags they have length 0, so the expansion is exactly the
// hand-written primitives (legacy equivalence). With a profile the look is a generated look action at the prop
// (look.atProp), ending where the anticipation starts.
//
// Failures are structured (VerbError: verb, character, prop, code, reason): checked while expanding (hand state,
// prop state, affordances, sites, sets, hands, deform, place target) and after the compile by checkVerbConstraints
// (reach, palm on socket, place contact, upright). Under a verb these are errors, not warnings (T-111 decision).
#pragma once
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <vector>

#include "anim/personality.h"
#include "scene/asset_library.h"
#include "scene/scene.h"

namespace plush {

struct VerbPhase {
  std::string name;   // look | anticipate | approach | contact | manipulate | release | settle
  std::string beat;   // timing profile beat (TimingProfile::frames)
  double fallbackF = 0;  // frames without a profile (= the current engine default, design 3.3)
  std::string share;  // approach / contact: their share of the "reach" beat
  std::string curve;  // linear | ease_in_out | slow_in | slow_out | hold (the lowered primitive's curve)
  std::string target; // look: "prop" | "place_target"
  bool optional = false;
  bool travel = false;  // manipulate of carry: at least the scale-aware travel time
  std::vector<std::string> drives, constraints, events;
};

struct VerbDef {
  std::string id;
  std::string lowersTo;            // grasp | hold | place
  std::string handState;           // requires.hand_state: "empty" | "holding"
  std::string propState;           // requires.prop_state: "free" | "held" | ""
  std::vector<VerbPhase> phases;
  const VerbPhase* phase(const std::string& name) const;
};
Result<VerbDef> verbFromJson(const Json& j);
Result<VerbDef> loadVerb(const std::filesystem::path& file);
// content/verbs/<id>.verb.json found by walking up from `from` (a scene file or directory); empty if none.
std::filesystem::path findVerbFile(const std::filesystem::path& from, const std::string& id);

// An action of a verb type (pick_up, carry, or place with "verb": true).
bool isVerbAction(const Json& action);
bool hasVerbAction(const Json& actions);

struct VerbError {
  std::string verb, character, prop;
  std::string code;    // hand_full, prop_held, unknown_site, unknown_set, wrong_hand, two_hands, out_of_reach,
                       // upright_exceeded, target_occupied, deform_unsupported, affordances_invalid, hand_empty,
                       // holds_other, unknown_prop, unknown_character, unknown_target, onto_self, no_start,
                       // bad_frames, bad_hand, contact_error, no_verb
  std::string reason;
  std::string message() const;  // "verb 'pick_up': character 'boy', prop 'cup': hand_full: ..."
};

// Everything the expander reads (pure data; the caller fills it from the scene).
struct VerbContext {
  struct Character {
    std::string name;
    const PersonalityProfile* personality = nullptr;
    float armLength[2] = {0, 0};  // [L, R], metres (shoulder -> elbow -> wrist); 0 = unknown
  };
  struct Prop {
    std::string name;
    const PropAsset* asset = nullptr;
    AssetTransform transform;
    std::optional<PropParent> parent;  // authored parent at the shot start
  };
  std::vector<Character> characters;
  std::vector<Prop> props;
  const TimingProfile* timing = nullptr;  // the scene's opt-in profile (null = engine defaults)
  double frameStart = 1;
  std::function<Result<VerbDef>(const std::string& id)> verb;  // verb library lookup
};

// One phase of one expanded verb action, in scene frames.
struct VerbPhaseSpan {
  size_t action = 0;  // index of the verb action in the input array
  std::string verb, character, prop, phase;
  double from = 0, to = 0;
};

// A constraint checked after the compile (checkVerbConstraints).
struct VerbCheck {
  enum class Kind { Reach, PalmOnSocket, PlaceOnTarget, Upright };
  Kind kind = Kind::Reach;
  std::string verb, character, prop, socket;
  char side = 'R';
  double frame = 0, to = 0;  // Upright: frames [frame, to]
  float limit = 0;           // Reach: shortfall (m); PalmOnSocket / PlaceOnTarget: error (m); Upright: degrees
  vec3 target{0}, axis{0, 1, 0};
  std::string ontoProp, ontoSocket;  // PlaceOnTarget onto a prop socket (target taken from it)
};

struct VerbExpansion {
  Json actions = Json::array();  // primitive actions (verb actions replaced in place)
  std::vector<VerbPhaseSpan> phases;
  std::vector<VerbCheck> checks;
  const VerbPhaseSpan* span(size_t action, const std::string& phase) const;
};

std::expected<VerbExpansion, VerbError> expandVerbs(const Json& actions, const VerbContext& ctx);

// Read-only geometry of the compiled scene for the constraint check (the caller binds it to its SceneEvaluator).
struct VerbGeometry {
  std::function<vec3(const std::string& character, char side, double f)> shoulder;   // arm chain root
  std::function<vec3(const std::string& character, char side, double f)> wristTarget;  // ik track value
  std::function<float(const std::string& character, char side)> armLength;
  std::function<vec3(const std::string& character, char side, double f)> palm;  // handGripPoint
  std::function<mat4(const std::string& prop, double f)> propWorld;
  std::function<const PropAsset*(const std::string& prop)> asset;
};
std::vector<VerbError> checkVerbConstraints(const VerbExpansion& x, const VerbGeometry& g);

}  // namespace plush
