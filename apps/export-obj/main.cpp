// plush-export-obj: writes one evaluated frame of a scene as Wavefront OBJ + MTL.
// Meshes are written as they are posed; curves thicker than --min-radius (lock cores: straps, drawstrings,
// thick yarn) become low-poly tubes; thin fibres (fuzz, halo) are skipped. Positions are in metres, Y up.
// Used by the Blender comparison harness (pipeline/blender); it does not change the engine.
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>

#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
void usage() {
  std::puts("usage: plush-export-obj <scene.json> --out <file.obj> [--frame N] [--min-radius metres] [--tube-sides N]");
}
std::string safeName(std::string s) {
  for (char& c : s)
    if (!(std::isalnum(static_cast<unsigned char>(c)) || c == '_' || c == '.' || c == '-')) c = '_';
  return s;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    usage();
    return 1;
  }
  fs::path scenePath = argv[1], out;
  double frame = 1;
  float minRadius = 5e-4f;
  int sides = 8;
  for (int i = 2; i < argc; ++i) {
    std::string a = argv[i];
    auto next = [&]() -> std::string {
      if (i + 1 >= argc) {
        logError("missing value for {}", a);
        std::exit(1);
      }
      return argv[++i];
    };
    if (a == "--out") out = next();
    else if (a == "--frame") frame = std::stod(next());
    else if (a == "--min-radius") minRadius = std::stof(next());
    else if (a == "--tube-sides") sides = std::max(3, std::stoi(next()));
    else {
      usage();
      return 1;
    }
  }
  if (out.empty()) {
    usage();
    return 1;
  }
  auto scene = loadScene(scenePath);
  if (!scene) {
    logError("{}", scene.error().message);
    return 1;
  }
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{1.0f, 1.0f, false, 0}); !r) {
    logError("{}", r.error().message);
    return 1;
  }
  auto snap = ev.evaluate(frame);
  fs::path mtlPath = out;
  mtlPath.replace_extension(".mtl");
  std::ofstream obj(out), mtl(mtlPath);
  if (!obj || !mtl) {
    logError("cannot write {}", out.string());
    return 1;
  }
  obj << "# plush-export-obj: " << scenePath.filename().string() << " frame " << frame << " (Y up, metres)\n";
  obj << "mtllib " << mtlPath.filename().string() << "\n";
  for (const Material& m : snap->materials)
    mtl << "newmtl " << safeName(m.name) << "\nKd " << m.baseColor.x << ' ' << m.baseColor.y << ' ' << m.baseColor.z
        << "\nNs 10\nd 1\n\n";
  size_t vbase = 1, tris = 0, tubes = 0;
  int part = 0;
  for (const SnapshotMesh& sm : snap->meshes) {
    const Mesh& m = *sm.mesh;
    if (m.indices.empty()) continue;
    const std::string mat = safeName(snap->materials[size_t(sm.material)].name);
    obj << "o mesh" << part++ << "_" << mat << "\nusemtl " << mat << "\n";
    for (const vec3& p : m.positions) obj << "v " << p.x << ' ' << p.y << ' ' << p.z << '\n';
    for (const vec3& n : m.normals) obj << "vn " << n.x << ' ' << n.y << ' ' << n.z << '\n';
    for (size_t t = 0; t < m.indices.size(); t += 3) {
      size_t a = vbase + m.indices[t], b = vbase + m.indices[t + 1], c = vbase + m.indices[t + 2];
      obj << "f " << a << "//" << a << ' ' << b << "//" << b << ' ' << c << "//" << c << '\n';
    }
    vbase += m.positions.size();
    tris += m.triangleCount();
  }
  for (const SnapshotFibers& sf : snap->fibers) {
    const FiberSet& fs = *sf.fibers;
    if (fs.curveOffsets.size() < 2) continue;
    const std::string mat = safeName(snap->materials[size_t(sf.material)].name);
    bool header = false;
    for (size_t c = 0; c + 1 < fs.curveOffsets.size(); ++c) {
      uint32_t a = fs.curveOffsets[c], b = fs.curveOffsets[c + 1];
      if (b - a < 2) continue;
      float rmax = 0;
      for (uint32_t i = a; i < b; ++i) rmax = std::max(rmax, fs.points[i].w);
      if (rmax < minRadius) continue;  // fuzz and halo fibres
      if (!header) {
        obj << "o curves" << part++ << "_" << mat << "\nusemtl " << mat << "\n";
        header = true;
      }
      // Rings around the curve with a parallel-transported frame.
      vec3 t0 = glm::normalize(vec3(fs.points[a + 1]) - vec3(fs.points[a]));
      vec3 n = glm::normalize(glm::cross(t0, std::abs(t0.y) < 0.9f ? vec3(0, 1, 0) : vec3(1, 0, 0)));
      const uint32_t rings = b - a;
      for (uint32_t i = a; i < b; ++i) {
        vec3 p(fs.points[i]);
        vec3 t = glm::normalize(vec3(fs.points[std::min(i + 1, b - 1)]) - vec3(fs.points[i == a ? a : i - 1]));
        n = glm::normalize(n - t * glm::dot(n, t));
        vec3 bn = glm::cross(t, n);
        for (int k = 0; k < sides; ++k) {
          float ang = 6.2831853f * float(k) / float(sides);
          vec3 q = p + fs.points[i].w * (std::cos(ang) * n + std::sin(ang) * bn);
          obj << "v " << q.x << ' ' << q.y << ' ' << q.z << '\n';
        }
      }
      for (uint32_t r = 0; r + 1 < rings; ++r)
        for (int k = 0; k < sides; ++k) {
          size_t i0 = vbase + r * size_t(sides) + size_t(k), i1 = vbase + r * size_t(sides) + size_t((k + 1) % sides);
          obj << "f " << i0 << ' ' << i1 << ' ' << i1 + size_t(sides) << ' ' << i0 + size_t(sides) << '\n';
        }
      vbase += size_t(rings) * size_t(sides);
      ++tubes;
    }
  }
  logInfo("wrote {} ({} triangles, {} tubes) and {}", out.string(), tris, tubes, mtlPath.filename().string());
  return 0;
}
