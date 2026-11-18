// T-082 measurement (T-047's tool plus the largest planned elbow swing, torso lean and elbow height):  arm clearance on the character's collision body (engine/scene/collision.h: the same body the
// planner uses), every frame, both arms of every character, with collision planning on and off, plus the rotation
// the planning adds to the arm bones (relative to the chest) and its change per frame, and how much faster per frame
// the planned arm turns than the unplanned one ("speed_up": max over frames and bones of the planned bone's rotation
// since the previous frame minus the unplanned bone's; independent of a planned path that differs as a whole, e.g. a
// moved hand-over point). Not part of the build:
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-082/measure_t082.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -ltbb -o build/measure_t082
//   build/measure_t082 <scene.json> > out.json          (run from the repository root)
// "gap" is the smallest limb-capsule clearance (forearm wrist half and hand; negative = inside) at any frame and IK
// weight (clip arms included); "upper_gap" the upper arm / elbow surface samples (reported only, they rest against
// the side). Rotation: per arm bone (upperArm, forearm, hand), the angle between its chest-relative world rotation with
// and without planning ("added"), and the largest frame-to-frame change of that angle ("added_step").
#include <cstdio>
#include <iostream>

#include "model/imported_character.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

namespace {
quat rotOf(const mat4& M) {
  return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(M[0])), glm::normalize(vec3(M[1])), glm::normalize(vec3(M[2])))));
}
float angleDeg(quat a, quat b) {
  const float d = std::min(1.0f, std::abs(glm::dot(glm::normalize(a), glm::normalize(b))));
  return glm::degrees(2.0f * std::acos(d));
}
}  // namespace

// --compare <package dir> <block.json>: the engine's derivation of the package against a collision block (e.g. the
// export/6 block computed by collision_block_from_package.py); prints the largest differences (radius: radii and
// rest allowances).
int compareBlock(const char* pkg, const char* blockPath) {
  auto ic = loadImportedCharacter(std::string(pkg) + "/character.json");
  if (!ic) return std::fprintf(stderr, "%s\n", ic.error().message.c_str()), 1;
  auto text = readTextFile(blockPath);
  if (!text) return std::fprintf(stderr, "%s\n", text.error().message.c_str()), 1;
  auto block = collisionBodyFromJson(Json::parse(*text), ic->asset.skeleton);
  if (!block) return std::fprintf(stderr, "%s\n", block.error().message.c_str()), 1;
  const CollisionBody d = deriveCollisionBody(ic->asset.skeleton, ic->rig.meshes);
  float dp = 0, dr = 0;
  if (d.sections.size() != block->sections.size() || d.limbs.size() != block->limbs.size()) return std::printf("different part counts\n"), 1;
  for (size_t i = 0; i < d.sections.size(); ++i) {
    const auto &a = d.sections[i], &b = block->sections[i];
    dp = std::max({dp, glm::length(a.p0 - b.p0), glm::length(a.p1 - b.p1)});
    dr = std::max({dr, std::abs(a.r1 - b.r1), std::abs(a.r2 - b.r2)});
  }
  for (size_t i = 0; i < d.limbs.size(); ++i) {
    const auto &a = d.limbs[i], &b = block->limbs[i];
    dp = std::max({dp, glm::length(a.a - b.a), glm::length(a.b - b.b)});
    dr = std::max({dr, std::abs(a.r - b.r), std::abs(a.allowance - b.allowance)});
  }
  std::printf("{\"package\": \"%s\", \"max_point_diff_mm\": %.4f, \"max_radius_diff_mm\": %.4f}\n", pkg, dp * 1000, dr * 1000);
  return 0;
}

int main(int argc, char** argv) {
  if (argc >= 4 && std::string(argv[1]) == "--compare") return compareBlock(argv[2], argv[3]);
  if (argc < 2) return std::fprintf(stderr, "usage: measure_t082 <scene.json> | --compare <package dir> <block.json>\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  Scene off = *scene;
  if (!off.actions.is_array()) off.actions = Json::array();
  for (const auto& c : scene->characters) off.actions.push_back({{"type", "collision"}, {"character", c.name}, {"enabled", false}});
  SceneEvaluator on, no;
  const EvalOptions opt{2.5f, 1.0f, false, 0};
  if (auto r = on.load(*scene, opt); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  if (auto r = no.load(off, opt); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  Json out = {{"scene", argv[1]}, {"warnings", on.warnings()}, {"characters", Json::array()}};
  for (size_t c = 0; c < on.characters().size(); ++c) {
    const auto& ci = on.characters()[c];
    const Skeleton& sk = ci.asset.skeleton;
    const BodyClearanceModel M = bodyClearanceModel(sk, ci.rig.meshes, ci.asset.collisionBlock);
    Json jc = {{"name", scene->characters[c].name}, {"collision_source", M.collision.source}, {"arms", Json::object()}};
    if (argc > 2 && std::string(argv[2]) == "--body") {  // the collision body and the limb segments at frame argv[3]
      jc["body"] = collisionBodyToJson(M.collision, sk);
      const int f = argc > 3 ? std::atoi(argv[3]) : scene->frameStart;
      const auto G = on.characterGlobals(c, f);
      for (const auto& l : M.collision.limbs) {
        vec3 a, b;
        limbSegment(l, G, a, b);
        const vec3 la = vec3(glm::inverse(G[size_t(sk.find("hips"))]) * vec4(a, 1)), lb = vec3(glm::inverse(G[size_t(sk.find("hips"))]) * vec4(b, 1));
        jc["limbs_at_frame_hips_local"][l.name] = {{"a", {la.x, la.y, la.z}}, {"b", {lb.x, lb.y, lb.z}}};
      }
    }
    const int chest = sk.find("chest");
    for (char side : {'L', 'R'}) {
      const std::string s(1, side);
      const int bones[3] = {sk.find("upperArm." + s), sk.find("forearm." + s), sk.find("hand." + s)};
      float gapOn = 1e9f, gapOff = 1e9f, upperOn = 1e9f, added = 0, step = 0;
      int atOn = 0, atOff = 0, atStep = 0;
      std::string partOn;
      float prev[3] = {0, 0, 0};
      float speedUp = 0, maxOn = 0, maxOff = 0;  // per-frame rotation of the arm bones (chest-relative)
      int atSpeed = 0;
      std::vector<quat> lastOn(3), lastOff(3);
      std::vector<float> perFrame;
      for (int f = scene->frameStart; f <= scene->frameEnd; ++f) {
        const auto G = on.characterGlobals(c, f), H = no.characterGlobals(c, f);
        const ArmClearance a = armClearance(M, G, side), b = armClearance(M, H, side);
        perFrame.push_back(a.gap);
        if (a.gap < gapOn) gapOn = a.gap, atOn = f, partOn = a.part + "/" + a.against;
        if (b.gap < gapOff) gapOff = b.gap, atOff = f;
        upperOn = std::min(upperOn, a.upperGap);
        const quat cg = rotOf(G[size_t(chest)]), ch = rotOf(H[size_t(chest)]);
        for (int k = 0; k < 3; ++k) {
          const float d = angleDeg(glm::inverse(cg) * rotOf(G[size_t(bones[k])]), glm::inverse(ch) * rotOf(H[size_t(bones[k])]));
          added = std::max(added, d);
          if (f > scene->frameStart && std::abs(d - prev[k]) > step) step = std::abs(d - prev[k]), atStep = f;
          prev[k] = d;
          const quat qOn = glm::inverse(cg) * rotOf(G[size_t(bones[k])]), qOff = glm::inverse(ch) * rotOf(H[size_t(bones[k])]);
          if (f > scene->frameStart) {
            const float sOn = angleDeg(qOn, lastOn[size_t(k)]), sOff = angleDeg(qOff, lastOff[size_t(k)]);
            maxOn = std::max(maxOn, sOn), maxOff = std::max(maxOff, sOff);
            if (sOn - sOff > speedUp) speedUp = sOn - sOff, atSpeed = f;
          }
          lastOn[size_t(k)] = qOn, lastOff[size_t(k)] = qOff;
        }
      }
      // The planner's own corrections (generated tracks): elbow swing and arm lift (degrees per frame), wrist push
      // (mm per frame).
      float swingRate = 0, liftRate = 0, pushRate = 0, swingMax = 0, elbowUpOn = -1e9f, elbowUpOff = -1e9f;
      float leanMax = 0, leanRate = 0;
      int swingAt = 0, elbowAt = 0, leanAt = 0;
      const std::string who = scene->characters[c].name, hb = "hand." + s;
      const Clip& clip = on.scene().animation;
      for (int f = scene->frameStart + 1; f <= scene->frameEnd; ++f) {
        auto d = [&](const std::string& k) { return glm::length(clip.evaluate(who + "/" + k, f, vec3(0)) - clip.evaluate(who + "/" + k, f - 1, vec3(0))); };
        swingRate = std::max(swingRate, glm::degrees(d("swing." + hb)));
        liftRate = std::max(liftRate, glm::degrees(d("abduct." + hb)));
        pushRate = std::max(pushRate, 1000 * d("collision.push." + hb));
      }
      // The largest planned elbow swing (degrees) and the elbow's height above the shoulder along the chest's up axis
      // (mm; a "wing" elbow rises towards or above the shoulder), planning on and off.
      for (int f = scene->frameStart; f <= scene->frameEnd; ++f) {
        const float lv = glm::length(clip.evaluate(who + "/collision.lean." + hb, f, vec3(0)));  // planned torso lean (deg)
        if (lv > leanMax) leanMax = lv, leanAt = f;
        if (f > scene->frameStart)
          leanRate = std::max(leanRate, glm::length(clip.evaluate(who + "/collision.lean." + hb, f, vec3(0)) -
                                                    clip.evaluate(who + "/collision.lean." + hb, f - 1, vec3(0))));
        const float sw = std::abs(glm::degrees(clip.evaluate(who + "/swing." + hb, f, vec3(0)).x));
        if (sw > swingMax) swingMax = sw, swingAt = f;
        const auto G = on.characterGlobals(c, f), H = no.characterGlobals(c, f);
        auto up = [&](const std::vector<mat4>& X) {
          const vec3 u = glm::normalize(vec3(X[size_t(chest)][1]));
          return 1000 * glm::dot(vec3(X[size_t(bones[1])][3]) - vec3(X[size_t(bones[0])][3]), u);
        };
        if (up(G) > elbowUpOn) elbowUpOn = up(G), elbowAt = f;
        elbowUpOff = std::max(elbowUpOff, up(H));
      }
      jc["arms"][s] = {{"lean_max_deg", leanMax}, {"lean_max_frame", leanAt}, {"lean_rate_deg", leanRate}, {"swing_max_deg", swingMax}, {"swing_max_frame", swingAt}, {"elbow_above_shoulder_max_mm", elbowUpOn},
                       {"elbow_above_shoulder_frame", elbowAt}, {"elbow_above_shoulder_off_max_mm", elbowUpOff}, {"swing_rate_deg", swingRate}, {"lift_rate_deg", liftRate}, {"push_rate_mm", pushRate},{"gap_mm", gapOn * 1000}, {"gap_frame", atOn}, {"gap_part", partOn}, {"gap_off_mm", gapOff * 1000},
                       {"gap_off_frame", atOff}, {"upper_gap_mm", upperOn * 1000}, {"added_deg", added},
                       {"added_step_deg", step}, {"added_step_frame", atStep}, {"speed_up_deg", speedUp},
                       {"speed_up_frame", atSpeed}, {"max_step_on_deg", maxOn}, {"max_step_off_deg", maxOff}};
      Json pf = Json::array();
      for (float g : perFrame) pf.push_back(std::round(g * 1e5f) / 100.0f);
      jc["arms"][s]["gap_per_frame_mm"] = pf;
    }
    out["characters"].push_back(jc);
  }
  std::cout << out.dump(1) << "\n";
  return 0;
}
