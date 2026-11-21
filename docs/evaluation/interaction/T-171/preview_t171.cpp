// T-171 cheap preview (review recipe step "preview"; not part of the build, see build_measure.sh): a z-buffer picture
// of one character and the cup from the engine's own pose, one frame in well under a second. No materials, no fur:
// every digit of the chosen hand has its own colour (thumb magenta, index red, middle green, ring blue, little
// yellow), the rest of the character is grey, the cup dark red. Geometry and timing only; never evidence for the
// look (that is the Cycles sheet).
//   preview_t171 <resolved scene.json> --out <prefix> --hand <character> <L|R> --frames a,b,c
//       --view <name> <cx cy cz> <tx ty tz> <lens mm> [--view ...] [--res W H] [--prop cup <asset.json>]
//       [--radius M]   only geometry within M metres of a view's target is drawn (default 0.25; 0 = everything)
// Writes <prefix>_<view>_f<frame>.ppm (engine coordinates, +Y up, 36 mm sensor width).
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <format>
#include <fstream>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

namespace {
struct Image {
  int w, h;
  std::vector<vec3> rgb;
  std::vector<float> z;
  Image(int w_, int h_) : w(w_), h(h_), rgb(size_t(w_ * h_), vec3(0.62f, 0.62f, 0.64f)), z(size_t(w_ * h_), 1e9f) {}
};
struct View {
  std::string name;
  vec3 eye, target;
  float lens;
};
// Triangle (camera space: x right, y up, z depth > 0), flat colour with a head light and a little sky.
void tri(Image& im, const vec3 p[3], const vec3 n[3], vec3 col, float focal) {
  vec2 s[3];
  for (int i = 0; i < 3; ++i) {
    if (p[i].z < 0.01f) return;
    s[i] = vec2(0.5f * float(im.w) + focal * p[i].x / p[i].z, 0.5f * float(im.h) - focal * p[i].y / p[i].z);
  }
  const float area = (s[1].x - s[0].x) * (s[2].y - s[0].y) - (s[2].x - s[0].x) * (s[1].y - s[0].y);
  if (std::abs(area) < 1e-9f) return;
  const int x0 = std::max(0, int(std::floor(std::min({s[0].x, s[1].x, s[2].x})))), x1 = std::min(im.w - 1, int(std::ceil(std::max({s[0].x, s[1].x, s[2].x}))));
  const int y0 = std::max(0, int(std::floor(std::min({s[0].y, s[1].y, s[2].y})))), y1 = std::min(im.h - 1, int(std::ceil(std::max({s[0].y, s[1].y, s[2].y}))));
  for (int y = y0; y <= y1; ++y)
    for (int x = x0; x <= x1; ++x) {
      const vec2 q(float(x) + 0.5f, float(y) + 0.5f);
      const float a = ((s[1].x - q.x) * (s[2].y - q.y) - (s[2].x - q.x) * (s[1].y - q.y)) / area;
      const float b = ((s[2].x - q.x) * (s[0].y - q.y) - (s[0].x - q.x) * (s[2].y - q.y)) / area;
      const float c = 1 - a - b;
      if (a < 0 || b < 0 || c < 0) continue;
      const float zz = 1.0f / (a / p[0].z + b / p[1].z + c / p[2].z);
      float& zb = im.z[size_t(y * im.w + x)];
      if (zz >= zb) continue;
      zb = zz;
      vec3 nn = glm::normalize(a * n[0] + b * n[1] + c * n[2]);
      const vec3 pos = glm::normalize(a * p[0] + b * p[1] + c * p[2]);
      if (glm::dot(nn, pos) > 0) nn = -nn;
      const float head = std::max(0.0f, -glm::dot(nn, pos)), key = std::max(0.0f, glm::dot(nn, glm::normalize(vec3(-0.5f, 0.7f, -0.5f))));
      im.rgb[size_t(y * im.w + x)] = col * (0.18f + 0.5f * head + 0.45f * key);
    }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: see the header\n"), 2;
  std::string out = "preview", who, propName = "cup", assetPath = "content/assets/felt_cup.asset.json";
  char side = 'R';
  std::vector<int> frames;
  std::vector<View> views;
  int W = 480, H = 360;
  float radius = 0.25f;
  for (int i = 2; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--out" && i + 1 < argc) out = argv[++i];
    else if (a == "--hand" && i + 2 < argc) who = argv[i + 1], side = argv[i + 2][0], i += 2;
    else if (a == "--res" && i + 2 < argc) W = std::stoi(argv[i + 1]), H = std::stoi(argv[i + 2]), i += 2;
    else if (a == "--prop" && i + 2 < argc) propName = argv[i + 1], assetPath = argv[i + 2], i += 2;
    else if (a == "--radius" && i + 1 < argc) radius = std::stof(argv[++i]);
    else if (a == "--frames" && i + 1 < argc) {
      std::string s = argv[++i];
      for (size_t p = 0; p < s.size();) {
        const size_t q = std::min(s.find(',', p), s.size());
        frames.push_back(std::stoi(s.substr(p, q - p)));
        p = q + 1;
      }
    } else if (a == "--view" && i + 8 < argc) {
      views.push_back({argv[i + 1], vec3(std::stof(argv[i + 2]), std::stof(argv[i + 3]), std::stof(argv[i + 4])),
                       vec3(std::stof(argv[i + 5]), std::stof(argv[i + 6]), std::stof(argv[i + 7])), std::stof(argv[i + 8])});
      i += 8;
    }
  }
  const auto t0 = std::chrono::steady_clock::now();
  auto lap = [&](const char* w) { std::fprintf(stderr, "%s %.1f s\n", w, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count()); };
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  lap("load");
  size_t c = 0, p = 0;
  for (; c < ev.scene().characters.size(); ++c)
    if (ev.scene().characters[c].name == who) break;
  if (c == ev.characters().size()) return std::fprintf(stderr, "no character %s\n", who.c_str()), 1;
  for (; p < ev.scene().props.size(); ++p)
    if (ev.scene().props[p].name == propName) break;
  auto asset = loadAsset(assetPath);
  const bool cup = p < ev.scene().props.size() && asset;
  const auto& ci = ev.characters()[c];
  const Skeleton& sk = ci.asset.skeleton;
  // Colour per bone: the digits of the chosen hand, the hand itself, everything else.
  const std::string s = std::string(".") + side;
  std::vector<vec3> boneCol(sk.bones.size(), vec3(0.55f));
  auto paint = [&](const std::string& name, vec3 col) {
    if (int b = sk.find(name); b >= 0) boneCol[size_t(b)] = col;
  };
  paint("hand" + s, vec3(0.95f, 0.8f, 0.7f));
  paint("forearm" + s, vec3(0.9f, 0.75f, 0.3f));
  const vec3 fc[4] = {vec3(0.95f, 0.9f, 0.2f), vec3(0.25f, 0.4f, 0.95f), vec3(0.2f, 0.8f, 0.3f), vec3(0.95f, 0.2f, 0.2f)};
  for (int k = 0; k < 4; ++k) paint(std::format("f{}a{}", k, s), fc[k]), paint(std::format("f{}b{}", k, s), 0.75f * fc[k]);
  paint("thumbA" + s, vec3(0.9f, 0.2f, 0.9f)), paint("thumbB" + s, vec3(0.65f, 0.15f, 0.65f));
  for (size_t b = 0; b < sk.bones.size(); ++b)  // helper bones under the hand (thumb base etc.) take the hand colour
    if (boneCol[b] == vec3(0.55f) && sk.bones[b].parent >= 0 && sk.bones[size_t(sk.bones[b].parent)].name == "hand" + s)
      boneCol[b] = vec3(0.95f, 0.8f, 0.7f);
  for (int f : frames) {
    const auto G = ev.characterGlobals(c, f);
    lap("globals");
    std::vector<mat4> skin(G.size());
    for (size_t b = 0; b < G.size(); ++b) skin[b] = G[b] * glm::translate(mat4(1), -sk.bones[b].head);
    for (const View& v : views) {
      Image im(W, H);
      const vec3 fw = glm::normalize(v.target - v.eye), rt = glm::normalize(glm::cross(fw, vec3(0, 1, 0))), up = glm::cross(rt, fw);
      const float focal = v.lens / 36.0f * float(W);
      auto cam = [&](vec3 q) { return vec3(glm::dot(q - v.eye, rt), glm::dot(q - v.eye, up), glm::dot(q - v.eye, fw)); };
      auto camN = [&](vec3 n) { return vec3(glm::dot(n, rt), glm::dot(n, up), glm::dot(n, fw)); };
      for (const SkinnedMesh& m : ci.rig.meshes) {
        std::vector<vec3> P(m.rest.positions.size()), N(P.size());
        std::vector<vec3> col(P.size());
        std::vector<char> nearT(P.size(), 1);
        for (size_t i = 0; i < P.size(); ++i) {
          vec3 q(0), n(0);
          int top = 0;
          for (int j = 0; j < 4; ++j) {
            const float w = m.weights[i][j];
            if (w <= 0) continue;
            const mat4& S = skin[size_t(m.joints[i][j])];
            q += w * vec3(S * vec4(m.rest.positions[i], 1));
            if (i < m.rest.normals.size()) n += w * (mat3(S) * m.rest.normals[i]);
            if (w > m.weights[i][top]) top = j;
          }
          nearT[i] = radius <= 0 || glm::distance(q, v.target) < radius;
          P[i] = cam(q), N[i] = camN(glm::length(n) > 0 ? glm::normalize(n) : vec3(0, 1, 0));
          col[i] = boneCol[size_t(m.joints[i][top])];
        }
        for (size_t t = 0; t + 2 < m.rest.indices.size(); t += 3) {
          const uint32_t a = m.rest.indices[t], b = m.rest.indices[t + 1], d = m.rest.indices[t + 2];
          if (!nearT[a] && !nearT[b] && !nearT[d]) continue;
          const vec3 pp[3] = {P[a], P[b], P[d]}, nn[3] = {N[a], N[b], N[d]};
          tri(im, pp, nn, (col[a] + col[b] + col[d]) / 3.0f, focal);
        }
      }
      if (cup) {  // the cup as an open tube with a base
        const mat4 Pm = ev.propWorld(p, f);
        const float k = asset->scaleMetres > 0 ? asset->scaleMetres : 1.0f, R = asset->mesh.radius * k, Hh = asset->mesh.height * k;
        const int n = 48;
        for (int i = 0; i < n; ++i) {
          const float a0 = 6.2831853f * float(i) / n, a1 = 6.2831853f * float(i + 1) / n;
          const vec3 d0(std::cos(a0), 0, std::sin(a0)), d1(std::cos(a1), 0, std::sin(a1));
          auto wp = [&](vec3 q) { return cam(vec3(Pm * vec4(q, 1))); };
          auto wn = [&](vec3 q) { return camN(glm::normalize(mat3(Pm) * q)); };
          const vec3 q[4] = {wp(R * d0), wp(R * d1), wp(R * d1 + vec3(0, Hh, 0)), wp(R * d0 + vec3(0, Hh, 0))};
          const vec3 nq[4] = {wn(d0), wn(d1), wn(d1), wn(d0)};
          const vec3 t0[3] = {q[0], q[1], q[2]}, n0[3] = {nq[0], nq[1], nq[2]}, t1[3] = {q[0], q[2], q[3]}, n1[3] = {nq[0], nq[2], nq[3]};
          tri(im, t0, n0, vec3(0.6f, 0.2f, 0.18f), focal), tri(im, t1, n1, vec3(0.6f, 0.2f, 0.18f), focal);
          const vec3 b0[3] = {wp(vec3(0)), q[0], q[1]}, bn[3] = {wn(vec3(0, 1, 0)), wn(vec3(0, 1, 0)), wn(vec3(0, 1, 0))};
          tri(im, b0, bn, vec3(0.45f, 0.15f, 0.14f), focal);
        }
      }
      const std::string path = std::format("{}_{}_f{:04d}.ppm", out, v.name, f);
      std::ofstream o(path, std::ios::binary);
      o << "P6\n" << W << " " << H << "\n255\n";
      for (const vec3& px : im.rgb)
        for (int ch = 0; ch < 3; ++ch) o.put(char(std::clamp(int(std::pow(std::clamp(px[ch], 0.0f, 1.0f), 1 / 2.2f) * 255.0f + 0.5f), 0, 255)));
      std::printf("%s\n", path.c_str());
      lap("view");
    }
  }
  return 0;
}
