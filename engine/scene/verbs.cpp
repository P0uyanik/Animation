#include "scene/verbs.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <set>

#include "scene/reaction.h"

namespace plush {
namespace {

double num(const Json& a, const char* k, double fallback) {
  auto it = a.find(k);
  return it != a.end() && it->is_number() ? it->get<double>() : fallback;
}
std::string str(const Json& a, const char* k, const std::string& fallback = {}) {
  auto it = a.find(k);
  return it != a.end() && it->is_string() ? it->get<std::string>() : fallback;
}
bool flag(const Json& a, const char* k, bool fallback) {
  auto it = a.find(k);
  return it != a.end() && it->is_boolean() ? it->get<bool>() : fallback;
}
std::optional<vec3> vecOpt(const Json& a, const char* k) {
  auto it = a.find(k);
  if (it == a.end() || !it->is_array() || it->size() != 3) return std::nullopt;
  for (const Json& e : *it)
    if (!e.is_number()) return std::nullopt;
  return vec3((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
}

const std::set<std::string> kPhases = {"look", "anticipate", "approach", "contact", "manipulate", "release", "settle"};
const std::set<std::string> kCurves = {"linear", "ease_in_out", "slow_in", "slow_out", "hold"};

Result<std::vector<std::string>> strings(const Json& j, const char* key, const std::string& ctx) {
  std::vector<std::string> out;
  auto it = j.find(key);
  if (it == j.end()) return out;
  if (!it->is_array()) return fail(std::format("{}: '{}' must be an array of strings", ctx, key));
  for (const Json& e : *it) {
    if (!e.is_string()) return fail(std::format("{}: '{}' must be an array of strings", ctx, key));
    out.push_back(e.get<std::string>());
  }
  return out;
}

// "<name><=<value>mm" -> metres (e.g. palm_on_socket<=0.5mm); nullopt if the constraint is not that name.
std::optional<float> mmLimit(const std::vector<std::string>& constraints, const std::string& name) {
  for (const std::string& c : constraints) {
    if (c.rfind(name + "<=", 0) != 0) continue;
    std::string v = c.substr(name.size() + 2);
    if (v.size() > 2 && v.ends_with("mm")) v.resize(v.size() - 2);
    try {
      return std::stof(v) / 1000.0f;
    } catch (...) {
      return std::nullopt;
    }
  }
  return std::nullopt;
}
bool hasConstraint(const std::vector<std::string>& constraints, const std::string& name) {
  return std::any_of(constraints.begin(), constraints.end(), [&](const std::string& c) { return c == name || c.rfind(name + "<", 0) == 0; });
}

}  // namespace

const VerbPhase* VerbDef::phase(const std::string& name, const std::string& part) const {
  for (const VerbPhase& p : phases)
    if (p.name == name && (part.empty() || p.part == part)) return &p;
  return nullptr;
}

Result<VerbDef> verbFromJson(const Json& j) {
  if (!j.is_object() || !j.contains("format") || !j["format"].is_string() || j["format"].get<std::string>() != "plush.verb")
    return fail("not a plush.verb file");
  if (!j.contains("version") || !j["version"].is_number_integer() || j["version"] != 1) return fail("unsupported plush.verb version");
  VerbDef v;
  v.id = str(j, "id");
  if (v.id.empty()) return fail("plush.verb: 'id' is required");
  const std::string ctx = std::format("verb '{}'", v.id);
  v.lowersTo = str(j, "lowers_to");
  if (v.lowersTo != "grasp" && v.lowersTo != "hold" && v.lowersTo != "place" && v.lowersTo != "handover")
    return fail(ctx + ": 'lowers_to' must be grasp, hold, place or handover");
  if (auto r = j.find("requires"); r != j.end()) {
    if (!r->is_object()) return fail(ctx + ": 'requires' must be an object");
    v.handState = str(*r, "hand_state");
    v.propState = str(*r, "prop_state");
    if (!v.handState.empty() && v.handState != "empty" && v.handState != "holding")
      return fail(ctx + ": requires.hand_state must be \"empty\" or \"holding\"");
    if (!v.propState.empty() && v.propState != "free" && v.propState != "held")
      return fail(ctx + ": requires.prop_state must be \"free\" or \"held\"");
  }
  auto ph = j.find("phases");
  if (ph == j.end() || !ph->is_array() || ph->empty()) return fail(ctx + ": 'phases' must be a non-empty array");
  for (const Json& e : *ph) {
    if (!e.is_object()) return fail(ctx + ": every phase must be an object");
    VerbPhase p;
    p.name = str(e, "name");
    if (!kPhases.count(p.name)) return fail(std::format("{}: unknown phase '{}'", ctx, p.name));
    p.part = str(e, "part");
    p.who = str(e, "who");
    if (!p.who.empty() && p.who != "giver" && p.who != "receiver" && p.who != "both")
      return fail(std::format("{}: phase '{}': 'who' must be giver, receiver or both", ctx, p.name));
    for (const VerbPhase& q : v.phases)
      if (q.name == p.name && q.part == p.part) return fail(std::format("{}: duplicate phase '{}'", ctx, p.name));
    const std::string pc = std::format("{}: phase '{}'", ctx, p.name);
    p.beat = str(e, "beat");
    p.fallbackF = num(e, "fallback_f", 0);
    if (p.fallbackF < 0) return fail(pc + ": 'fallback_f' must not be negative");
    p.share = str(e, "share");
    p.curve = str(e, "curve");
    if (!p.curve.empty() && !kCurves.count(p.curve)) return fail(std::format("{}: unknown curve '{}'", pc, p.curve));
    p.target = str(e, "target");
    p.optional = flag(e, "optional", false);
    p.travel = flag(e, "travel", false);
    auto drives = strings(e, "drives", pc);
    auto constraints = strings(e, "constraints", pc);
    auto events = strings(e, "events", pc);
    if (!drives) return std::unexpected(drives.error());
    if (!constraints) return std::unexpected(constraints.error());
    if (!events) return std::unexpected(events.error());
    p.drives = *drives, p.constraints = *constraints, p.events = *events;
    v.phases.push_back(std::move(p));
  }
  return v;
}

Result<VerbDef> loadVerb(const std::filesystem::path& file) {
  auto j = parseJsonFile(file);
  if (!j) return std::unexpected(j.error());
  auto v = verbFromJson(*j);
  if (!v) return fail(std::format("{}: {}", file.string(), v.error().message));
  return v;
}

namespace {
// T-112c: the prop's grasp geometry is a box (a box primitive, or a box collision proxy for a mesh): its sockets sit
// on faces (interaction.cpp graspShape).
bool boxProp(const PropAsset& a) {
  if (a.mesh.kind == AssetMeshSource::Kind::Primitive) return a.mesh.primitive == AssetMeshSource::Primitive::Box;
  return a.collision && a.collision->type == AssetCollisionProxy::Type::Box;
}
}  // namespace

std::filesystem::path findVerbFile(const std::filesystem::path& from, const std::string& id) {
  for (auto d = std::filesystem::absolute(from).parent_path();; d = d.parent_path()) {
    const auto f = d / "content" / "verbs" / (id + ".verb.json");
    if (std::filesystem::exists(f)) return f;
    if (d == d.parent_path()) return {};
  }
}

bool isVerbAction(const Json& a) {
  if (!a.is_object()) return false;
  const std::string type = str(a, "type");
  return type == "pick_up" || type == "carry" || type == "pass" || (type == "place" && flag(a, "verb", false));
}

bool hasVerbAction(const Json& actions) {
  return actions.is_array() && std::any_of(actions.begin(), actions.end(), [](const Json& a) { return isVerbAction(a); });
}

std::string VerbError::message() const {
  return std::format("verb '{}': character '{}', prop '{}': {}: {}", verb, character, prop.empty() ? "-" : prop, code, reason);
}

const VerbPhaseSpan* VerbExpansion::span(size_t action, const std::string& phase, const std::string& part) const {
  for (const VerbPhaseSpan& s : phases)
    if (s.action == action && s.phase == phase && (part.empty() || s.part == part)) return &s;
  return nullptr;
}

// ------------------------------------------------------------------------------------------------------- expander
std::expected<VerbExpansion, VerbError> expandVerbs(const Json& actions, const VerbContext& ctx) {
  VerbExpansion x;
  if (!actions.is_array()) return x;
  using HandKey = std::pair<std::string, char>;

  // State at the shot start: authored prop parents (a hand socket holds, a prop socket carries) and prop origins.
  std::map<HandKey, std::string> holding;  // hand -> prop
  std::map<std::string, HandKey> holder;   // prop -> hand
  std::map<std::string, std::pair<std::string, std::string>> onProp;  // prop -> (parent prop, socket)
  std::map<std::string, std::optional<vec3>> origin;
  std::map<HandKey, std::string> heldSocket;  // T-112b: the socket a hand holds its prop by ("" = unknown)
  std::map<std::string, HandKey> followerOf;  // T-112b: prop -> the second hand of a two-hand grasp
  for (const auto& p : ctx.props) {
    origin[p.name] = std::nullopt;
    if (!p.parent) {
      origin[p.name] = p.transform.translation;
    } else if (p.parent->kind == PropParent::Kind::Character && (p.parent->socket == "hand.L" || p.parent->socket == "hand.R")) {
      holding[{p.parent->name, p.parent->socket[5]}] = p.name;
      holder[p.name] = {p.parent->name, p.parent->socket[5]};
    } else if (p.parent->kind == PropParent::Kind::Prop) {
      onProp[p.name] = {p.parent->name, p.parent->socket};
    }
  }
  auto charOf = [&](const std::string& n) -> const VerbContext::Character* {
    for (const auto& c : ctx.characters)
      if (c.name == n) return &c;
    return nullptr;
  };
  auto propOf = [&](const std::string& n) -> const VerbContext::Prop* {
    for (const auto& p : ctx.props)
      if (p.name == n) return &p;
    return nullptr;
  };
  auto sideOf = [](const Json& a, const char* k) -> char {
    const std::string s = str(a, k, "R");
    return !s.empty() && (s[0] == 'L' || s[0] == 'l') ? 'L' : 'R';
  };
  // The acting (leading) hand: the first of "hands" (two-hand verbs, T-112b), else "hand".
  auto leadOf = [&](const Json& a) -> char {
    if (auto it = a.find("hands"); it != a.end() && it->is_array() && !it->empty() && (*it)[0].is_string())
      return (*it)[0].get<std::string>() == "L" ? 'L' : 'R';
    return sideOf(a, "hand");
  };

  // Primitive interaction actions change the state at their start (ordered with the verbs by start frame).
  struct Prim {
    double start;
    size_t index;
  };
  std::vector<Prim> prims;
  std::vector<size_t> verbs;
  for (size_t i = 0; i < actions.size(); ++i) {
    const Json& a = actions[i];
    if (isVerbAction(a)) {
      verbs.push_back(i);
      continue;
    }
    const std::string t = str(a, "type");
    if (((t == "grasp" || t == "reach") && a.contains("prop") && flag(a, "grasp", true)) || t == "place" || t == "handover")
      prims.push_back({num(a, "start", num(a, "frame", 0)), i});
  }
  std::stable_sort(prims.begin(), prims.end(), [](const Prim& a, const Prim& b) { return a.start < b.start; });
  auto applyPrim = [&](const Json& a) {
    const std::string t = str(a, "type"), who = str(a, "character");
    const HandKey h{who, sideOf(a, "hand")};
    if (t == "grasp" || t == "reach") {
      const std::string p = str(a, "prop");
      heldSocket[h] = str(a, "socket", "grip");
      if (flag(a, "follower", false)) {
        holding[h] = p, followerOf[p] = h;
        return;
      }
      holding[h] = p, holder[p] = h, onProp.erase(p);
      return;
    }
    auto it = holding.find(h);
    if (it == holding.end()) return;  // the compile reports it
    const std::string p = it->second;
    holding.erase(it);
    holder.erase(p);
    heldSocket.erase(h);
    if (auto f = followerOf.find(p); f != followerOf.end()) {
      holding.erase(f->second);
      heldSocket.erase(f->second);
      followerOf.erase(f);
    }
    if (t == "handover") {
      const HandKey r{str(a, "to"), sideOf(a, "toHand")};
      holding[r] = p, holder[p] = r;
      heldSocket[r] = str(a, "toSocket", "grip_b");
    } else if (auto onto = a.find("onto"); onto != a.end() && onto->is_object()) {
      onProp[p] = {str(*onto, "prop"), str(*onto, "socket", "place")};
      origin[p] = std::nullopt;
    } else {
      origin[p] = vecOpt(a, "at");
    }
  };

  std::vector<Json> out(actions.size());
  for (size_t i = 0; i < actions.size(); ++i)
    if (!isVerbAction(actions[i])) out[i] = Json::array({actions[i]});

  // Chains: a verb without a start starts where the previous verb of the same hand ended (its settle included).
  std::map<size_t, size_t> prevOnHand;  // verb action index -> previous verb action index on the same hand
  std::map<size_t, HandKey> receiverOf;  // pass -> the receiving hand (its chain continues from the release)
  {
    std::map<HandKey, size_t> last;
    for (size_t i : verbs) {
      const Json& a = actions[i];
      const HandKey h{str(a, "character"), leadOf(a)};
      if (auto it = last.find(h); it != last.end()) prevOnHand[i] = it->second;
      last[h] = i;
      if (auto hs = a.find("hands"); hs != a.end() && hs->is_array())
        for (const Json& e : *hs)
          if (e.is_string()) last[{str(a, "character"), e.get<std::string>() == "L" ? 'L' : 'R'}] = i;
      if (str(a, "type") == "pass") {
        receiverOf[i] = {str(a, "to"), sideOf(a, "toHand")};
        last[receiverOf[i]] = i;
      }
    }
  }
  std::map<size_t, double> endOf;       // processed verb -> chain end
  std::map<size_t, double> receiverEnd;  // processed pass -> where the receiver's chain continues
  std::set<size_t> done;
  size_t nextPrim = 0;

  while (done.size() < verbs.size()) {
    // The next verb: the earliest whose start is known (explicit, or its chain predecessor is done).
    size_t pick = SIZE_MAX;
    double pickStart = 0;
    for (size_t i : verbs) {
      if (done.count(i)) continue;
      const Json& a = actions[i];
      double s;
      if (a.contains("start") && a["start"].is_number()) {
        s = a["start"].get<double>();
      } else if (auto it = prevOnHand.find(i); it != prevOnHand.end()) {
        if (!done.count(it->second)) continue;
        auto rv = receiverOf.find(it->second);
        s = rv != receiverOf.end() && rv->second == HandKey{str(a, "character"), leadOf(a)} ? receiverEnd[it->second] : endOf[it->second];
      } else {
        return std::unexpected(VerbError{str(a, "type"), str(a, "character"), str(a, "prop"), "no_start",
                                         "give 'start' (no earlier verb of this hand to follow)"});
      }
      if (pick == SIZE_MAX || s < pickStart) pick = i, pickStart = s;
    }
    if (pick == SIZE_MAX) break;  // unreachable: a chain always has a done predecessor or an explicit start
    while (nextPrim < prims.size() &&
           (prims[nextPrim].start < pickStart || (prims[nextPrim].start == pickStart && prims[nextPrim].index < pick)))
      applyPrim(actions[prims[nextPrim++].index]);

    const size_t i = pick;
    const Json& a = actions[i];
    const std::string type = str(a, "type"), who = str(a, "character");
    char side = leadOf(a);
    HandKey hand{who, side};
    std::string prop = str(a, "prop");
    auto err = [&](const std::string& code, const std::string& reason) {
      return std::unexpected(VerbError{type, who, prop, code, reason});
    };
    if (a.contains("hand") && (!a["hand"].is_string() || (str(a, "hand") != "L" && str(a, "hand") != "R")))
      return err("bad_hand", "'hand' must be \"L\" or \"R\"");
    // T-112b two hands: "hands": ["L", "R"] (or ["R", "L"]); the first leads.
    const bool twoHand = a.contains("hands");
    char other = side == 'L' ? 'R' : 'L';
    if (twoHand) {
      const Json& hs = a["hands"];
      if (!hs.is_array() || hs.size() != 2 || !hs[0].is_string() || !hs[1].is_string() ||
          !((hs[0] == "L" && hs[1] == "R") || (hs[0] == "R" && hs[1] == "L")))
        return err("bad_hand", "'hands' must be [\"L\", \"R\"] or [\"R\", \"L\"]");
      if (a.contains("hand") && str(a, "hand")[0] != side) return err("bad_hand", "'hand' must be the first of 'hands' (the leading hand)");
    }
    const VerbContext::Character* ch = charOf(who);
    if (!ch) return err("unknown_character", std::format("no character '{}' in the scene", who));
    if (!ctx.verb) return err("no_verb", "no verb library");
    auto defR = ctx.verb(type);
    if (!defR) return err("no_verb", defR.error().message);
    const VerbDef& def = *defR;
    const TimingProfile* T = ctx.timing;
    const PersonalityProfile* P = ch->personality;
    const double S = pickStart;
    const bool look = flag(a, "look", true);
    const bool react = flag(a, "react", false) && ctx.events;  // T-112b: reaction events only when the scene has events

    // Length of a phase: its beat with a profile, else its fallback; optional phases only with a profile or when the
    // action asks (true: the profile beat or the phase's fallback; a number: that many frames).
    auto length = [&](const char* name) -> double {
      const VerbPhase* p = def.phase(name);
      if (!p) return 0;
      if (p->optional) {
        auto it = a.find(name);
        if (it != a.end() && it->is_number()) return std::max(0.0, it->get<double>());
        const bool asked = it != a.end() && it->is_boolean() && it->get<bool>();
        const bool off = it != a.end() && it->is_boolean() && !it->get<bool>();
        if (off || (!T && !asked)) return 0;
        if (!T) return p->fallbackF;
      }
      return T && !p->beat.empty() ? T->frames(p->beat, p->fallbackF, P) : p->fallbackF;
    };
    auto span = [&](const char* phase, double from, double to, char hs = 0, const char* part = "") {
      if (def.phase(phase, part)) x.phases.push_back({i, type, who, prop, phase, from, to, hs, part});
    };
    auto constraintsOf = [&](const char* phase) {
      const VerbPhase* p = def.phase(phase);
      return p ? p->constraints : std::vector<std::string>{};
    };

    // Hand and prop state the verb requires.
    auto held = holding.find(hand);
    if (def.handState == "empty" && held != holding.end())
      return err("hand_full", std::format("hand.{} already holds '{}'", side, held->second));
    if (def.handState == "empty" && twoHand)
      if (auto h2 = holding.find({who, other}); h2 != holding.end())
        return err("hand_full", std::format("hand.{} already holds '{}'", other, h2->second));
    if (def.handState == "holding") {
      if (held == holding.end()) return err("hand_empty", std::format("hand.{} holds nothing", side));
      if (prop.empty()) prop = held->second;
      if (prop != held->second)
        return err("holds_other", std::format("hand.{} holds '{}', not '{}'", side, held->second, prop));
      if (auto f = followerOf.find(prop); f != followerOf.end() && f->second == hand) {  // the second hand: lower to the leader
        hand = holder[prop];
        side = hand.second;
        other = side == 'L' ? 'R' : 'L';
      }
    }
    const bool heldTwo = def.handState == "holding" && followerOf.count(prop) > 0;
    const char follow = twoHand ? other : heldTwo ? followerOf[prop].second : 0;
    const VerbContext::Prop* pr = propOf(prop);
    if (prop.empty()) return err("unknown_prop", "give 'prop'");
    if (!pr || !pr->asset) return err("unknown_prop", std::format("no prop '{}' in the scene", prop));
    if (def.propState == "free") {
      if (auto h = holder.find(prop); h != holder.end())
        return err("prop_held", std::format("'{}' is held by '{}' (hand.{})", prop, h->second.first, h->second.second));
    }
    const std::optional<PropAffordances>& aff = pr->asset->affordances;
    if (aff && !aff->error.empty()) return err("affordances_invalid", aff->error);
    if (aff && aff->deform != "rigid")
      return err("deform_unsupported", std::format("deform mode '{}' not supported yet (rigid only, T-099)", aff->deform));
    if (heldTwo && def.lowersTo == "handover") return err("two_hands", std::format("'{}' is held in two hands and cannot be passed", prop));
    if (aff && aff->hands == "two" && !twoHand && (def.lowersTo == "grasp" || def.lowersTo == "handover"))
      return err("two_hands", std::format("prop '{}' (asset '{}') needs two hands: give hands:[L,R] or a two-site set (T-112b)",
                                          prop, pr->asset->id));
    if (twoHand && def.lowersTo == "handover") return err("two_hands", "pass takes one hand ('hands' is for pick_up, carry and place)");
    if (twoHand && def.lowersTo != "grasp" && !heldTwo)
      return err("two_hands", std::format("'{}' is not held in two hands", prop));
    std::vector<Json> gen;
    // A grasp site's hand shape, approach side and finger band (T-112b) on a generated grasp.
    const bool fingers = a.contains("fingers") && a["fingers"].is_boolean() ? a["fingers"].get<bool>() : T != nullptr;
    auto styled = [&](Json g, const GraspSite* site) {
      if (a.contains("fingerClose")) g["fingerClose"] = a["fingerClose"];  // T-171 (opt-in), read by scene/interaction.cpp
      if (!site) return g;
      if (site->shape != "wrap") g["shape"] = site->shape;
      if (site->approach) g["approach"] = {site->approach->x, site->approach->y, site->approach->z};
      if (fingers && site->band) {
        g["band"] = {site->band->x, site->band->y};
        g["thumb"] = site->thumb.empty() ? "opposed" : site->thumb;
      }
      // T-112c: a site on a box asks for the per-finger search on the face its socket is on (hand.<s>.graspFace),
      // under the same gate as the band (interaction.h: wrap, pinch and palm search the face).
      if (fingers && boxProp(*pr->asset)) g["graspFace"] = true;
      return g;
    };
    // Both arms of a two-hand grasp stay outside the bodies over [from, to] (design 2.4; read only).
    auto outsideBody = [&](double from, double to) {
      for (char hs : {side, follow}) {
        VerbCheck o{VerbCheck::Kind::OutsideBody, type, who, prop, "", hs, from, to, 0.0f};
        x.checks.push_back(o);
      }
    };

    if (def.lowersTo == "grasp") {
      // Grasp site: "site", "set", an explicit "socket", or the first set (then site) this hand may use. Two hands
      // (T-112b): the named or the first two-site set, its sites matched to the leading and the second hand.
      const GraspSite* site = nullptr;
      const GraspSite* site2 = nullptr;
      const GraspSet* set2 = nullptr;
      auto handOk = [&](const GraspSite& s, char hs) { return s.hand == "any" || s.hand[0] == hs; };
      if (twoHand) {
        if (!aff) return err("unknown_set", std::format("prop '{}' (asset '{}') has no affordances: two hands need a two-site grasp set", prop,
                                                       pr->asset->id));
        if (a.contains("site")) return err("unknown_site", "two hands take a grasp set ('set'), not a site");
        if (a.contains("set")) {
          set2 = aff->set(str(a, "set"));
          if (!set2) return err("unknown_set", std::format("asset '{}' has no grasp set '{}'", pr->asset->id, str(a, "set")));
          if (set2->sites.size() != 2)
            return err("unknown_set", std::format("grasp set '{}' has {} site(s); two hands need a set of two", set2->id, set2->sites.size()));
        } else {
          for (const GraspSet& s : aff->sets)
            if (!set2 && s.sites.size() == 2) set2 = &s;
          if (!set2) return err("unknown_set", std::format("asset '{}' has no two-site grasp set", pr->asset->id));
        }
        const GraspSite* s0 = aff->site(set2->sites[0]);
        const GraspSite* s1 = aff->site(set2->sites[1]);
        if (handOk(*s0, side) && handOk(*s1, other)) site = s0, site2 = s1;
        else if (handOk(*s1, side) && handOk(*s0, other)) site = s1, site2 = s0;
        else
          return err("wrong_hand", std::format("grasp set '{}' (sites for hand.{} and hand.{}) does not fit hands [{}, {}]", set2->id, s0->hand,
                                               s1->hand, side, other));
      } else if (a.contains("site") || a.contains("set")) {
        if (!aff) return err(a.contains("site") ? "unknown_site" : "unknown_set",
                             std::format("prop '{}' (asset '{}') has no affordances", prop, pr->asset->id));
        if (a.contains("site")) {
          site = aff->site(str(a, "site"));
          if (!site) return err("unknown_site", std::format("asset '{}' has no grasp site '{}'", pr->asset->id, str(a, "site")));
        } else {
          const GraspSet* set = aff->set(str(a, "set"));
          if (!set) return err("unknown_set", std::format("asset '{}' has no grasp set '{}'", pr->asset->id, str(a, "set")));
          if (set->sites.size() != 1)
            return err("two_hands", std::format("grasp set '{}' needs two hands: give hands:[L,R] (T-112b)", set->id));
          site = aff->site(set->sites[0]);
        }
        if (!handOk(*site, side))
          return err("wrong_hand", std::format("grasp site '{}' is for hand.{}, hand.{} asked", site->id, site->hand, side));
      } else if (aff && !a.contains("socket")) {
        for (const GraspSet& s : aff->sets)
          if (!site && s.sites.size() == 1 && handOk(*aff->site(s.sites[0]), side)) site = aff->site(s.sites[0]);
        for (const GraspSite& s : aff->sites)
          if (!site && handOk(s, side)) site = &s;
        if (!site && !aff->sites.empty())
          return err("wrong_hand", std::format("no grasp site of asset '{}' is for hand.{}", pr->asset->id, side));
      }
      const std::string socket = site ? site->socket : str(a, "socket", "grip");
      if (!pr->asset->sockets.count(socket))
        return err("unknown_site", std::format("asset '{}' has no socket '{}'", pr->asset->id, socket));

      const VerbPhase* approach = def.phase("approach");
      const double L = def.phase("look") ? length("look") : 0;
      const double A = length("anticipate");
      const double R0 = S + A;
      const double reach = approach ? (T && !approach->beat.empty() ? T->frames(approach->beat, approach->fallbackF, P) : approach->fallbackF) : 14;
      const double contact = num(a, "contact", R0 + reach);
      if (contact < R0 + 6) return err("bad_frames", std::format("contact {} must be at least 6 frames after the reach starts ({})", contact, R0));
      const double pre = contact - std::min(6.0, 0.4 * (contact - R0));
      const double Z = length("settle");
      // The second hand contacts d frames after the leader (not a mirror; design 2.4): reaction_delay / 3, at least 1,
      // at most the set's simultaneous_frames.
      const double d = set2 ? std::clamp(std::round((T ? T->frames("reaction_delay", 4, P) : 4.0) / 3.0), 1.0,
                                         double(std::max(1, set2->simultaneousFrames)))
                            : 0.0;
      const double last = contact + d;
      if (T && look && L > 0) {
        gen.push_back({{"type", "look"}, {"character", who}, {"atProp", prop}, {"start", S - L}, {"end", R0}});
        span("look", S - L, S);
      } else {
        span("look", R0 - (def.phase("look") ? def.phase("look")->fallbackF : 4), R0);  // the primitive's gaze lead
      }
      span("anticipate", S, R0);
      span("approach", R0, pre);
      span("contact", pre, contact);
      if (site2) {
        span("approach", R0 + d, pre + d, other);
        span("contact", pre + d, last, other);
      }
      span("settle", last, last + Z);
      Json g = {{"type", "grasp"}, {"character", who}, {"hand", std::string(1, side)}, {"prop", prop}, {"start", R0}, {"contact", contact}};
      if (socket != "grip") g["socket"] = socket;
      if (!look) g["look"] = false;
      gen.push_back(styled(std::move(g), site));
      if (site2) {
        Json g2 = {{"type", "grasp"}, {"character", who}, {"hand", std::string(1, other)}, {"prop", prop}, {"start", R0 + d},
                   {"contact", last},  {"socket", site2->socket},           {"follower", true}, {"look", false}};
        gen.push_back(styled(std::move(g2), site2));
      }
      const auto c = constraintsOf("contact");
      const bool reachable = hasConstraint(c, "reachable") || hasConstraint(constraintsOf("approach"), "reachable");
      const auto lim = mmLimit(c, "palm_on_socket");
      if (reachable) x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, socket, side, contact, contact, 0.005f});
      // T-171 (opt-in): a natural grip may turn the grasp point about the prop's axis; the palm is checked on that point.
      const bool naturalGrip = a.contains("fingerClose") && a["fingerClose"].is_object() && a["fingerClose"].value("grip", Json()) == "natural";
      if (lim)
        x.checks.push_back({VerbCheck::Kind::PalmOnSocket, type, who, prop, naturalGrip && !site2 ? std::format("{}@{}.{}", socket, who, side) : socket,
                            side, contact, contact, *lim});
      if (site2) {
        if (reachable) x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, site2->socket, other, last, last, 0.005f});
        if (lim) x.checks.push_back({VerbCheck::Kind::PalmOnSocket, type, who, prop, site2->socket, other, last, last, *lim});
        outsideBody(last, last + Z);
        holding[{who, other}] = prop, followerOf[prop] = {who, other}, heldSocket[{who, other}] = site2->socket;
      }
      holding[hand] = prop, holder[prop] = hand, onProp.erase(prop), heldSocket[hand] = socket;
      endOf[i] = last + Z;
    } else if (def.lowersTo == "hold") {
      const auto at = vecOpt(a, "at"), by = vecOpt(a, "by");
      if (!at && !by) return err("bad_frames", "give 'at' [x,y,z] or 'by' [dx,dy,dz]");
      const VerbPhase* m = def.phase("manipulate");
      double hold = m ? m->fallbackF : 16;
      if (T && m) {
        hold = T->frames(m->beat, m->fallbackF, P);
        const std::optional<vec3> o = origin[prop];
        const std::optional<double> d = at ? (o ? std::optional<double>(glm::length(*at - *o)) : std::nullopt)
                                           : std::optional<double>(glm::length(*by));
        if (m->travel && d && ch->armLength[side == 'L' ? 0 : 1] > 0)
          hold = std::max(hold, T->travelFrames(*d, ch->armLength[side == 'L' ? 0 : 1], P));
      }
      const double end = num(a, "end", S + hold);
      if (end <= S) return err("bad_frames", "end must be after start");
      const double Z = length("settle");
      span("manipulate", S, end);
      span("settle", end, end + Z);
      Json g = {{"type", "hold"}, {"character", who}, {"hand", std::string(1, side)}, {"prop", prop}, {"start", S}, {"end", end}};
      if (at) g["at"] = a["at"];
      else g["by"] = a["by"];
      if (!look) g["look"] = false;
      gen.push_back(std::move(g));
      const auto c = constraintsOf("manipulate");
      if (hasConstraint(c, "reachable")) x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, "", side, end, end, 0.005f});
      if (heldTwo) {  // the second hand follows the prop along the path (design 4.2)
        if (hasConstraint(c, "reachable")) x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, "", follow, end, end, 0.005f});
        outsideBody(S, end + Z);
      }
      if (hasConstraint(c, "upright") && aff && aff->upright) {
        VerbCheck u{VerbCheck::Kind::Upright, type, who, prop, "", side, S, end, aff->upright->maxTiltDeg};
        u.axis = aff->upright->axis;
        x.checks.push_back(u);
      }
      if (at) origin[prop] = *at;
      else if (origin[prop]) origin[prop] = *origin[prop] + *by;
      endOf[i] = end + Z;
    } else if (def.lowersTo == "handover") {  // pass (T-112b, design 4.4)
      const std::string to = str(a, "to");
      if (a.contains("toHand") && (!a["toHand"].is_string() || (str(a, "toHand") != "L" && str(a, "toHand") != "R")))
        return err("bad_hand", "'toHand' must be \"L\" or \"R\"");
      const char toSide = sideOf(a, "toHand");
      const HandKey recv{to, toSide};
      const VerbContext::Character* rch = charOf(to);
      if (!rch) return err("unknown_character", std::format("no receiver '{}' in the scene", to));
      if (recv == hand) return err("same_hand", std::format("the receiving hand is the giving hand ('{}' hand.{})", to, toSide));
      if (auto r = holding.find(recv); r != holding.end())
        return err("hand_full", std::format("receiver '{}' hand.{} already holds '{}'", to, toSide, r->second));
      // The receiver's socket: "toSocket", "toSite" / "toSet", the asset's handover receive set, else grip_b.
      const GraspSite* rsite = nullptr;
      std::string toSocket = str(a, "toSocket");
      auto handOk = [&](const GraspSite& s) { return s.hand == "any" || s.hand[0] == toSide; };
      if (toSocket.empty() && (a.contains("toSite") || a.contains("toSet"))) {
        if (!aff) return err(a.contains("toSite") ? "unknown_site" : "unknown_set",
                             std::format("prop '{}' (asset '{}') has no affordances", prop, pr->asset->id));
        if (a.contains("toSite")) {
          rsite = aff->site(str(a, "toSite"));
          if (!rsite) return err("unknown_site", std::format("asset '{}' has no grasp site '{}'", pr->asset->id, str(a, "toSite")));
        } else {
          const GraspSet* set = aff->set(str(a, "toSet"));
          if (!set) return err("unknown_set", std::format("asset '{}' has no grasp set '{}'", pr->asset->id, str(a, "toSet")));
          if (set->sites.size() != 1) return err("two_hands", std::format("grasp set '{}' needs two hands; a pass takes one", set->id));
          rsite = aff->site(set->sites[0]);
        }
        if (!handOk(*rsite))
          return err("wrong_hand", std::format("grasp site '{}' is for hand.{}, receiver hand.{} asked", rsite->id, rsite->hand, toSide));
      } else if (toSocket.empty() && aff) {
        for (const std::string& id : aff->handoverReceive)
          if (const GraspSet* set = aff->set(id); !rsite && set && set->sites.size() == 1 && handOk(*aff->site(set->sites[0])))
            rsite = aff->site(set->sites[0]);
      }
      if (rsite) toSocket = rsite->socket;
      if (toSocket.empty()) toSocket = "grip_b";
      if (!pr->asset->sockets.count(toSocket)) return err("unknown_site", std::format("asset '{}' has no socket '{}'", pr->asset->id, toSocket));
      if (rsite && rsite->shape != "wrap")
        return err("shape_unsupported", std::format("receiver site '{}': a pass receives with a wrap grasp (hand shape '{}')", rsite->id, rsite->shape));
      // The hands must not meet: not the same socket, not overlapping finger bands.
      const std::string giveSocket = heldSocket.count(hand) ? heldSocket[hand] : std::string();
      if (giveSocket == toSocket)
        return err("hands_meet", std::format("giver and receiver would hold '{}' by the same socket '{}'", prop, toSocket));
      if (aff && !giveSocket.empty()) {
        auto bySocket = [&](const std::string& sk) -> const GraspSite* {
          for (const GraspSite& g : aff->sites)
            if (g.socket == sk) return &g;
          return nullptr;
        };
        const GraspSite* gs = bySocket(giveSocket);
        const GraspSite* rs = rsite ? rsite : bySocket(toSocket);
        // Same band: the bands overlap along the axis and the two sockets are on the same side of it (radial
        // directions about the prop's up axis less than 90 deg apart). Opposite sides at the same height do not meet
        // (the cup: grip at +x, grip_b at -x, bands overlapping by 10 mm).
        auto radial = [&](const std::string& sk) {
          const vec3 up = aff->upright ? glm::normalize(aff->upright->axis) : vec3(0, 1, 0);
          const vec3 t = pr->asset->sockets.at(sk).translation;
          return t - up * glm::dot(t, up);
        };
        const vec3 ra = radial(giveSocket), rb = radial(toSocket);
        const bool sameSide = glm::length(ra) < 1e-6f || glm::length(rb) < 1e-6f || glm::dot(ra, rb) > 0;
        if (gs && rs && gs->band && rs->band && sameSide && std::max(gs->band->x, rs->band->x) < std::min(gs->band->y, rs->band->y))
          return err("hands_meet", std::format("finger bands of sites '{}' [{:g}, {:g}] and '{}' [{:g}, {:g}] overlap on the same side: the hands "
                                               "would meet", gs->id, gs->band->x, gs->band->y, rs->id, rs->band->x, rs->band->y));
      }
      // Frames. Fallbacks are the handover defaults (design 3.3); with a profile each beat is the acting character's.
      const PersonalityProfile* PR = rch->personality;
      auto beatOf = [&](const char* name, const char* part, const PersonalityProfile* whoP, double fb) {
        const VerbPhase* ph = def.phase(name, part);
        const double f = ph ? ph->fallbackF : fb;
        return T && ph && !ph->beat.empty() ? T->frames(ph->beat, f, whoP) : f;
      };
      constexpr double kGazeLead = 4;  // the receiver's eyes lead the hand (the primitive's gaze lead)
      double noticeAt = 0;
      if (react) {  // the receiver notices the offer through the reaction system: its notice delay starts the reach
        ReactionEvent ev;
        ev.kind = ReactionEvent::Kind::PartnerActs;
        ev.name = "pass";
        ev.source = who;
        ev.time = std::max(0.0, (S - ctx.frameStart) / ctx.fps);
        ReactionContext rc;
        rc.timing = T;
        double delay = planReaction(ev, PR, rc).noticeDelay;
        if (PR && PR->reaction.delayFrames) delay = std::max(delay, double(PR->reaction.delayFrames->lo) / 24.0);
        noticeAt = ctx.frameStart + (ev.time + delay) * ctx.fps;
        x.events.push_back({{"kind", "partner_acts"}, {"name", "pass"}, {"source", who}, {"time", ev.time}, {"characters", {to}}});
      }
      // The reach starts on the first whole frame at least kGazeLead after the notice (the look keeps the reaction's
      // exact start, as planReactionActions plays it).
      const double rStart = num(a, "receiverStart", react ? std::ceil(noticeAt + kGazeLead - 1e-6) : S + beatOf("look", "", PR, 4));
      const double reachF = beatOf("approach", "", PR, 14);
      const double contact = num(a, "contact", T || react ? rStart + reachF : S + beatOf("look", "", PR, 4) + reachF);
      const double rel = num(a, "release", contact + beatOf("manipulate", "shared", P, 4));
      const double end = num(a, "end", rel + beatOf("release", "", P, 12));
      if (contact < S + 6 || contact < rStart + 6 || rel < contact + 1 || end < rel + 8)
        return err("bad_frames", "needs contact >= start + 6, contact >= receiverStart + 6, release > contact, end >= release + 8");
      if ((T || a.contains("release")) && rel - contact < 6)
        return err("shared_too_short", std::format("shared hold {:g} f (contact {:g} to release {:g}) is shorter than 6 f", rel - contact, contact, rel));
      const double Z = length("settle");
      const double still = contact - std::min(4.0, 0.3 * (contact - S));
      const double pre = contact - std::min(6.0, 0.4 * (contact - rStart));
      auto spanOf = [&](const char* phase, const char* part, const std::string& whoS, char hs, double from, double t) {
        if (def.phase(phase, part)) x.phases.push_back({i, type, whoS, prop, phase, from, t, hs, part});
      };
      spanOf("look", "", to, toSide, react ? noticeAt : rStart - kGazeLead, rStart);
      spanOf("manipulate", "offer", who, side, S, still);
      spanOf("approach", "", to, toSide, rStart, pre);
      spanOf("contact", "", to, toSide, pre, contact);
      spanOf("manipulate", "shared", who, side, contact, rel);
      spanOf("release", "", who, side, rel, end);
      spanOf("settle", "", who, side, end, end + Z);
      Json g = {{"type", "handover"}, {"character", who}, {"hand", std::string(1, side)}, {"to", to}, {"toHand", std::string(1, toSide)},
                {"prop", prop}, {"toSocket", toSocket}, {"start", S}, {"receiverStart", rStart}, {"contact", contact}, {"release", rel},
                {"end", end}};
      if (auto at = vecOpt(a, "at")) g["at"] = a["at"];
      if (a.contains("fingerClose")) g["fingerClose"] = a["fingerClose"];  // T-171 (opt-in)
      if (!look || react) g["look"] = false;
      if (fingers && aff) {  // T-112c: the receiver's site band and box face, under the same gate as the giver's grasp
        const GraspSite* rs = rsite;
        for (const GraspSite& gs : aff->sites)
          if (!rs && gs.socket == toSocket) rs = &gs;
        if (rs && rs->band) {
          g["toBand"] = {rs->band->x, rs->band->y};
          g["toThumb"] = rs->thumb.empty() ? "opposed" : rs->thumb;
        }
        if (rs && boxProp(*pr->asset)) g["toGraspFace"] = true;
      }
      gen.push_back(std::move(g));
      if (react && look) {  // one gaze source: the receiver's look is the reaction's; the giver's as look actions
        gen.push_back({{"type", "look"}, {"character", who}, {"atProp", prop}, {"start", S}, {"end", rel}});
        gen.push_back({{"type", "look"}, {"character", who}, {"atCharacter", to}, {"start", rel}, {"end", end + Z}});
        // The reaction's look (the notice) is at the giver; from the reach on the receiver's eyes are on the prop.
        gen.push_back({{"type", "look"}, {"character", to}, {"atProp", prop}, {"start", rStart}, {"end", contact + 8}});
      }
      const auto cc = constraintsOf("contact");
      if (hasConstraint(cc, "reachable")) {
        x.checks.push_back({VerbCheck::Kind::Reach, type, to, prop, toSocket, toSide, contact, contact, 0.005f});
        x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, "", side, contact, contact, 0.005f});
      }
      if (auto lim = mmLimit(cc, "palm_on_socket"))
        x.checks.push_back({VerbCheck::Kind::PalmOnSocket, type, to, prop, toSocket, toSide, contact, contact, *lim});
      if (hasConstraint(cc, "outside_body")) {  // the meeting point keeps both arms outside the bodies (design 4.4)
        x.checks.push_back({VerbCheck::Kind::OutsideBody, type, who, prop, "", side, still, rel, 0.0f});
        x.checks.push_back({VerbCheck::Kind::OutsideBody, type, to, prop, "", toSide, contact, rel, 0.0f});
      }
      holding.erase(hand);
      heldSocket.erase(hand);
      holding[recv] = prop, holder[prop] = recv, heldSocket[recv] = toSocket;
      endOf[i] = end + Z;
      receiverEnd[i] = rel;
    } else {  // place
      const std::string socket = str(a, "socket", aff && aff->place ? aff->place->socket : "place");
      if (!pr->asset->sockets.count(socket))
        return err("unknown_target", std::format("asset '{}' has no socket '{}' to place by", pr->asset->id, socket));
      std::optional<vec3> at = vecOpt(a, "at");
      std::string ontoProp, ontoSocket;
      if (auto it = a.find("onto"); it != a.end() && it->is_object()) {
        ontoProp = str(*it, "prop");
        ontoSocket = str(*it, "socket", "place");
        const VerbContext::Prop* q = propOf(ontoProp);
        if (!q || !q->asset) return err("unknown_target", std::format("no prop '{}' to place onto", ontoProp));
        if (!q->asset->sockets.count(ontoSocket))
          return err("unknown_target", std::format("prop '{}' (asset '{}') has no socket '{}'", ontoProp, q->asset->id, ontoSocket));
        for (std::string up = ontoProp; !up.empty();) {  // onto itself or onto a prop it carries
          if (up == prop) return err("onto_self", std::format("'{}' cannot be placed onto '{}' (itself or a prop it carries)", prop, ontoProp));
          auto o = onProp.find(up);
          up = o == onProp.end() ? std::string() : o->second.first;
        }
        for (const auto& [other, parent] : onProp)
          if (other != prop && parent.first == ontoProp && parent.second == ontoSocket)
            return err("target_occupied", std::format("socket '{}' of '{}' already holds '{}'", ontoSocket, ontoProp, other));
      } else if (!at) {
        return err("bad_frames", "give 'at' [x,y,z] or 'onto' {prop, socket}");
      }
      const double L = def.phase("look") ? length("look") : 0;
      const VerbPhase* m = def.phase("manipulate");
      const VerbPhase* rel = def.phase("release");
      auto beatOf = [&](const VerbPhase* p, double fallback) {
        if (!p) return fallback;
        return T && !p->beat.empty() ? T->frames(p->beat, p->fallbackF, P) : p->fallbackF;
      };
      const double contact = num(a, "contact", S + beatOf(m, 16));
      const double end = num(a, "end", contact + beatOf(rel, 14));
      if (contact < S + 6 || end < contact + 8) return err("bad_frames", "needs contact >= start + 6 and end >= contact + 8");
      const double Z = length("settle");
      if (T && look && L > 0) {
        Json l = {{"type", "look"}, {"character", who}, {"start", S - L}, {"end", S}};
        if (!ontoProp.empty()) l["atProp"] = ontoProp;
        else l["target"] = a["at"];
        gen.push_back(std::move(l));
        span("look", S - L, S);
      } else {
        span("look", S - (def.phase("look") ? def.phase("look")->fallbackF : 4), S);
      }
      span("manipulate", S, contact);
      span("contact", contact, contact);
      span("release", contact, end);
      span("settle", end, end + Z);
      Json g = {{"type", "place"}, {"character", who}, {"hand", std::string(1, side)}, {"prop", prop}, {"start", S},
                {"contact", contact}, {"end", end}};
      if (socket != "place") g["socket"] = socket;
      if (!ontoProp.empty()) g["onto"] = {{"prop", ontoProp}, {"socket", ontoSocket}};
      else g["at"] = a["at"];
      if (a.contains("fingerClose")) g["fingerClose"] = a["fingerClose"];  // T-171 (opt-in)
      if (!look) g["look"] = false;
      gen.push_back(std::move(g));
      const auto mc = constraintsOf("manipulate"), cc = constraintsOf("contact");
      if (hasConstraint(mc, "reachable") || hasConstraint(cc, "reachable")) {
        x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, socket, side, contact, contact, 0.005f});
        if (heldTwo) x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, "", follow, contact, contact, 0.005f});
      }
      if (heldTwo) outsideBody(S, contact);
      if (auto lim = mmLimit(cc, "place_on_target")) {
        VerbCheck pc{VerbCheck::Kind::PlaceOnTarget, type, who, prop, socket, side, contact, contact, *lim};
        pc.target = at.value_or(vec3(0)), pc.ontoProp = ontoProp, pc.ontoSocket = ontoSocket;
        x.checks.push_back(pc);
      }
      if (hasConstraint(mc, "upright") && aff && aff->upright) {
        VerbCheck u{VerbCheck::Kind::Upright, type, who, prop, "", side, S, contact, aff->upright->maxTiltDeg};
        u.axis = aff->upright->axis;
        x.checks.push_back(u);
      }
      holding.erase(hand);
      holder.erase(prop);
      heldSocket.erase(hand);
      if (heldTwo) {
        holding.erase(followerOf[prop]);
        heldSocket.erase(followerOf[prop]);
        followerOf.erase(prop);
      }
      if (!ontoProp.empty()) {
        onProp[prop] = {ontoProp, ontoSocket};
        origin[prop] = std::nullopt;
      } else {
        const mat4 R = assetTransformMatrix({vec3(0), pr->transform.rotationDeg, pr->transform.scale});
        origin[prop] = *at - vec3(R * vec4(pr->asset->sockets.at(socket).translation, 0));
      }
      if (react)  // T-112b: a success event at the settle (design 4.5); the cast reacts as the scene's events say
        x.events.push_back({{"kind", "success"}, {"name", "place"}, {"source", who}, {"time", std::max(0.0, (end - ctx.frameStart) / ctx.fps)}});
      endOf[i] = end + Z;
    }
    out[i] = Json(gen);
    done.insert(i);
  }
  for (const Json& list : out)
    for (const Json& g : list) x.actions.push_back(g);
  return x;
}

// ----------------------------------------------------------------------------------------- constraints (read only)
std::vector<VerbError> checkVerbConstraints(const VerbExpansion& x, const VerbGeometry& g) {
  std::vector<VerbError> errors;
  auto socketWorld = [&](const std::string& prop, const std::string& socket, double f) -> std::optional<vec3> {
    const PropAsset* asset = g.asset ? g.asset(prop) : nullptr;
    if (!asset) return std::nullopt;
    // "<socket>@<character>.<hand>": the grasp point as the planner turned it for that hand (T-171 "grip": "natural"),
    // the authored socket when it did not turn it.
    const std::string name = asset->sockets.count(socket) ? socket : socket.substr(0, socket.find('@'));
    if (!asset->sockets.count(name)) return std::nullopt;
    return vec3((g.propWorld(prop, f) * assetTransformMatrix(asset->sockets.at(name)))[3]);
  };
  for (const VerbCheck& c : x.checks) {
    auto add = [&](const char* code, const std::string& reason) { errors.push_back({c.verb, c.character, c.prop, code, reason}); };
    switch (c.kind) {
      case VerbCheck::Kind::Reach: {
        const float arm = g.armLength(c.character, c.side);
        const float d = glm::distance(g.shoulder(c.character, c.side, c.frame), g.wristTarget(c.character, c.side, c.frame)) - 0.98f * arm;
        if (d > c.limit)
          add("out_of_reach", std::format("hand.{} cannot reach at frame {:g}: {:.0f} mm short (0.98 x arm length {:.0f} mm)", c.side,
                                          c.frame, d * 1000, arm * 1000));
        break;
      }
      case VerbCheck::Kind::PalmOnSocket: {
        const auto s = socketWorld(c.prop, c.socket, c.frame);
        if (!s) break;
        const float e = glm::distance(g.palm(c.character, c.side, c.frame), *s);
        if (e > c.limit)
          add("contact_error", std::format("palm {:.2f} mm from socket '{}' at contact frame {:g} (limit {:.2f} mm)", e * 1000, c.socket,
                                           c.frame, c.limit * 1000));
        break;
      }
      case VerbCheck::Kind::PlaceOnTarget: {
        const auto s = socketWorld(c.prop, c.socket, c.frame);
        const auto t = c.ontoProp.empty() ? std::optional<vec3>(c.target) : socketWorld(c.ontoProp, c.ontoSocket, c.frame);
        if (!s || !t) break;
        const float e = glm::distance(*s, *t);
        if (e > c.limit)
          add("contact_error", std::format("socket '{}' {:.2f} mm from the place target at contact frame {:g} (limit {:.2f} mm)",
                                           c.socket, e * 1000, c.frame, c.limit * 1000));
        break;
      }
      case VerbCheck::Kind::OutsideBody: {
        if (!g.armGap) break;  // not bound: the compile's own warning remains
        float worst = 1e9f;
        double at = c.frame;
        for (double f = std::ceil(c.frame); f <= c.to + 1e-9; f += 1) {
          if (g.ikWeight && g.ikWeight(c.character, c.side, f) < 0.99f) continue;
          if (const float gap = g.armGap(c.character, c.side, f); gap < worst) worst = gap, at = f;
        }
        if (worst < c.limit)
          add("arm_in_body", std::format("arm {} passes {:.1f} mm into the body at frame {:g}", c.side, (c.limit - worst) * 1000, at));
        break;
      }
      case VerbCheck::Kind::Upright: {
        float worst = 0;
        double at = c.frame;
        for (double f = c.frame; f <= c.to + 1e-9; f += 1) {
          const vec3 axis = glm::normalize(mat3(g.propWorld(c.prop, f)) * c.axis);
          const float deg = glm::degrees(std::acos(std::clamp(axis.y, -1.0f, 1.0f)));
          if (deg > worst) worst = deg, at = f;
        }
        if (worst > c.limit + 1e-3f)
          add("upright_exceeded", std::format("prop axis tilts {:.1f} deg at frame {:g} (max_tilt_deg {:g})", worst, at, c.limit));
        break;
      }
    }
  }
  return errors;
}

}  // namespace plush
