#include "scene/verbs.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <set>

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

const VerbPhase* VerbDef::phase(const std::string& name) const {
  for (const VerbPhase& p : phases)
    if (p.name == name) return &p;
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
  if (v.lowersTo != "grasp" && v.lowersTo != "hold" && v.lowersTo != "place")
    return fail(ctx + ": 'lowers_to' must be grasp, hold or place");
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
    if (v.phase(p.name)) return fail(std::format("{}: duplicate phase '{}'", ctx, p.name));
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
  return type == "pick_up" || type == "carry" || (type == "place" && flag(a, "verb", false));
}

bool hasVerbAction(const Json& actions) {
  return actions.is_array() && std::any_of(actions.begin(), actions.end(), [](const Json& a) { return isVerbAction(a); });
}

std::string VerbError::message() const {
  return std::format("verb '{}': character '{}', prop '{}': {}: {}", verb, character, prop.empty() ? "-" : prop, code, reason);
}

const VerbPhaseSpan* VerbExpansion::span(size_t action, const std::string& phase) const {
  for (const VerbPhaseSpan& s : phases)
    if (s.action == action && s.phase == phase) return &s;
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
      holding[h] = p, holder[p] = h, onProp.erase(p);
      return;
    }
    auto it = holding.find(h);
    if (it == holding.end()) return;  // the compile reports it
    const std::string p = it->second;
    holding.erase(it);
    holder.erase(p);
    if (t == "handover") {
      const HandKey r{str(a, "to"), sideOf(a, "toHand")};
      holding[r] = p, holder[p] = r;
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
  {
    std::map<HandKey, size_t> last;
    for (size_t i : verbs) {
      const HandKey h{str(actions[i], "character"), sideOf(actions[i], "hand")};
      if (auto it = last.find(h); it != last.end()) prevOnHand[i] = it->second;
      last[h] = i;
    }
  }
  std::map<size_t, double> endOf;  // processed verb -> chain end
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
        s = endOf[it->second];
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
    const char side = sideOf(a, "hand");
    const HandKey hand{who, side};
    std::string prop = str(a, "prop");
    auto err = [&](const std::string& code, const std::string& reason) {
      return std::unexpected(VerbError{type, who, prop, code, reason});
    };
    if (a.contains("hand") && (!a["hand"].is_string() || (str(a, "hand") != "L" && str(a, "hand") != "R")))
      return err("bad_hand", "'hand' must be \"L\" or \"R\"");
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
    auto span = [&](const char* phase, double from, double to) {
      if (def.phase(phase)) x.phases.push_back({i, type, who, prop, phase, from, to});
    };
    auto constraintsOf = [&](const char* phase) {
      const VerbPhase* p = def.phase(phase);
      return p ? p->constraints : std::vector<std::string>{};
    };

    // Hand and prop state the verb requires.
    auto held = holding.find(hand);
    if (def.handState == "empty" && held != holding.end())
      return err("hand_full", std::format("hand.{} already holds '{}'", side, held->second));
    if (def.handState == "holding") {
      if (held == holding.end()) return err("hand_empty", std::format("hand.{} holds nothing", side));
      if (prop.empty()) prop = held->second;
      if (prop != held->second)
        return err("holds_other", std::format("hand.{} holds '{}', not '{}'", side, held->second, prop));
    }
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
    if (aff && aff->hands == "two")
      return err("two_hands", std::format("prop '{}' (asset '{}') needs two hands: give hands:[L,R] or a two-site set (T-112b)",
                                          prop, pr->asset->id));
    std::vector<Json> gen;

    if (def.lowersTo == "grasp") {
      // Grasp site: "site", "set", an explicit "socket", or the first set (then site) this hand may use.
      const GraspSite* site = nullptr;
      auto handOk = [&](const GraspSite& s) { return s.hand == "any" || s.hand[0] == side; };
      if (a.contains("site") || a.contains("set")) {
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
        if (!handOk(*site))
          return err("wrong_hand", std::format("grasp site '{}' is for hand.{}, hand.{} asked", site->id, site->hand, side));
      } else if (aff && !a.contains("socket")) {
        for (const GraspSet& s : aff->sets)
          if (!site && s.sites.size() == 1 && handOk(*aff->site(s.sites[0]))) site = aff->site(s.sites[0]);
        for (const GraspSite& s : aff->sites)
          if (!site && handOk(s)) site = &s;
        if (!site && !aff->sites.empty())
          return err("wrong_hand", std::format("no grasp site of asset '{}' is for hand.{}", pr->asset->id, side));
      }
      if (site && site->shape != "wrap")
        return err("shape_unsupported", std::format("grasp site '{}': hand shape '{}' comes with T-112b (wrap only)", site->id, site->shape));
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
      if (T && look && L > 0) {
        gen.push_back({{"type", "look"}, {"character", who}, {"atProp", prop}, {"start", S - L}, {"end", R0}});
        span("look", S - L, S);
      } else {
        span("look", R0 - (def.phase("look") ? def.phase("look")->fallbackF : 4), R0);  // the primitive's gaze lead
      }
      span("anticipate", S, R0);
      span("approach", R0, pre);
      span("contact", pre, contact);
      span("settle", contact, contact + Z);
      Json g = {{"type", "grasp"}, {"character", who}, {"hand", std::string(1, side)}, {"prop", prop}, {"start", R0}, {"contact", contact}};
      if (socket != "grip") g["socket"] = socket;
      if (!look) g["look"] = false;
      gen.push_back(std::move(g));
      const auto c = constraintsOf("contact");
      if (hasConstraint(c, "reachable") || hasConstraint(constraintsOf("approach"), "reachable"))
        x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, socket, side, contact, contact, 0.005f});
      if (auto lim = mmLimit(c, "palm_on_socket"))
        x.checks.push_back({VerbCheck::Kind::PalmOnSocket, type, who, prop, socket, side, contact, contact, *lim});
      holding[hand] = prop, holder[prop] = hand, onProp.erase(prop);
      endOf[i] = contact + Z;
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
      if (hasConstraint(c, "upright") && aff && aff->upright) {
        VerbCheck u{VerbCheck::Kind::Upright, type, who, prop, "", side, S, end, aff->upright->maxTiltDeg};
        u.axis = aff->upright->axis;
        x.checks.push_back(u);
      }
      if (at) origin[prop] = *at;
      else if (origin[prop]) origin[prop] = *origin[prop] + *by;
      endOf[i] = end + Z;
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
      if (!look) g["look"] = false;
      gen.push_back(std::move(g));
      const auto mc = constraintsOf("manipulate"), cc = constraintsOf("contact");
      if (hasConstraint(mc, "reachable") || hasConstraint(cc, "reachable"))
        x.checks.push_back({VerbCheck::Kind::Reach, type, who, prop, socket, side, contact, contact, 0.005f});
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
      if (!ontoProp.empty()) {
        onProp[prop] = {ontoProp, ontoSocket};
        origin[prop] = std::nullopt;
      } else {
        const mat4 R = assetTransformMatrix({vec3(0), pr->transform.rotationDeg, pr->transform.scale});
        origin[prop] = *at - vec3(R * vec4(pr->asset->sockets.at(socket).translation, 0));
      }
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
    if (!asset || !asset->sockets.count(socket)) return std::nullopt;
    return vec3((g.propWorld(prop, f) * assetTransformMatrix(asset->sockets.at(socket)))[3]);
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
