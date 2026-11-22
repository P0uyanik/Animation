// T-190: is a grasp's thumb as good as its joint range allows? Shared by test_hand_shapes.cpp and
// test_grasp_contact.cpp, whose T-051 / T-138 / T-157 thumb criteria were written for a thumb that could turn anywhere.
#pragma once

#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "scene/scene.h"

namespace plush::test {

// `bad(root, knuckle, tip)` gives a thumb pose's violations of N criteria (each >= 0, 0 = met; world positions of the
// thumb chain: thumbA head, thumbB head, tip). Every thumb pose on a grid of the thumb's joint coordinates is tried
// (anim/animation.h thumbJointRotations: opposition, abduction and end flexion every 5 deg, flexion every 3 deg from
// the laid-back limit `backDeg` to full flexion; the rest of the hand and arm as evaluated at frame f).
//   reachable[j]: some pose in range has every violation i within sets[j][i] (a set of the criteria the test had
//                 before; a negative entry leaves that criterion out of the set).
//   margin:       the dominance margin of the evaluated thumb, the most any pose that is no worse on every criterion is
//                 better on one (0 = nothing in range beats it).
struct ThumbFit {
  std::vector<bool> reachable;
  float margin = 0;
};
template <size_t N, class Bad>
ThumbFit thumbFit(const SceneEvaluator& ev, size_t c, char side, double f, float backDeg, const Bad& bad,
                  const std::vector<std::array<float, N>>& sets) {
  const Skeleton& sk = ev.characters()[c].asset.skeleton;
  const std::string s = std::string(".") + side;
  const int ia = sk.find("thumbA" + s), ib = sk.find("thumbB" + s);
  REQUIRE(ia >= 0);
  REQUIRE(ib >= 0);
  Pose pose;
  const auto g = ev.characterGlobals(c, f, &pose);
  const Bone &A = sk.bones[size_t(ia)], &B = sk.bones[size_t(ib)];
  REQUIRE(A.parent >= 0);
  REQUIRE(B.parent == ia);
  auto offset = [&](int i) { return size_t(i) < pose.offset.size() ? pose.offset[size_t(i)] : vec3(0); };
  const mat4 toA = g[size_t(A.parent)] * glm::translate(mat4(1), A.head - sk.bones[size_t(A.parent)].head + offset(ia));
  const mat4 toB = glm::translate(mat4(1), B.head - A.head + offset(ib));
  const vec4 tipB(B.head - A.head, 1);
  const vec3 root(toA[3]);
  const mat4 own = toA * glm::mat4_cast(pose.local[size_t(ia)]) * toB * glm::mat4_cast(pose.local[size_t(ib)]);
  REQUIRE(glm::distance(vec3(own * tipB), vec3(g[size_t(ib)] * tipB)) <= 1e-5f);  // the chain below is the evaluator's
  const std::array<float, N> mine = bad(root, vec3(own[3]), vec3(own * tipB));
  const HandLimits lim;
  ThumbFit fit;
  fit.reachable.assign(sets.size(), false);
  for (float opp = 0; opp <= lim.thumbOpposition + 1e-3f; opp += 5)
    for (float abd = -lim.thumbAbductionIn; abd <= lim.thumbAbductionOut + 1e-3f; abd += 5)
      for (float flex = -backDeg; flex <= lim.thumbFlex + 1e-3f; flex += 3)
        for (float end = 0; end <= lim.thumbEndFlex + 1e-3f; end += 5) {
          const auto r = thumbJointRotations(sk, side, opp, abd, flex, end);
          const mat4 gb = toA * glm::mat4_cast(r.first) * toB * glm::mat4_cast(r.second);
          const std::array<float, N> v = bad(root, vec3(gb[3]), vec3(gb * tipB));
          bool noWorse = true;
          float better = 0;
          for (size_t i = 0; i < N; ++i) {
            noWorse &= v[i] <= mine[i];
            better = std::max(better, mine[i] - v[i]);
          }
          if (noWorse) fit.margin = std::max(fit.margin, better);
          for (size_t j = 0; j < sets.size(); ++j) {
            bool met = true;
            for (size_t i = 0; i < N; ++i) met &= sets[j][i] < 0 || v[i] <= sets[j][i];
            if (met) fit.reachable[j] = true;
          }
        }
  return fit;
}

}  // namespace plush::test
