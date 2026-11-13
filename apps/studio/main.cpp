// Plush Studio: the desktop application.
// Viewport (OpenGL preview), outliner, inspector (objects, lights, camera,
// materials, character shapes and bones), timeline with keyframes, and an
// in-app path-traced render view. The scene file is the document.
#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include <imgui.h>
#include <imgui_impl_glfw.h>
#include <imgui_impl_opengl3.h>

#include <atomic>
#include <cstdio>
#include <mutex>
#include <thread>

#include "render/bsdf.h"
#include "render/image.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

// ------------------------------------------------------------------ GL preview renderer
const char* kVs = R"(#version 330 core
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec3 aCol;
uniform mat4 uVP; out vec3 vN; out vec3 vC; out vec3 vP;
void main(){ vN=aNrm; vC=aCol; vP=aPos; gl_Position=uVP*vec4(aPos,1.0); })";
const char* kFs = R"(#version 330 core
in vec3 vN; in vec3 vC; in vec3 vP; uniform vec3 uSunDir; uniform vec3 uSunCol; uniform vec3 uEye; uniform vec3 uTint;
out vec4 o;
void main(){ vec3 n=normalize(vN); if(!gl_FrontFacing) n=-n; vec3 l=-normalize(uSunDir);
 float ndl=max(dot(n,l),0.0); float hemi=0.5+0.5*n.y;
 vec3 amb=mix(vec3(0.30,0.25,0.20),vec3(0.55,0.57,0.60),hemi);
 vec3 c=vC*uTint*(amb+uSunCol*ndl*0.8);
 vec3 v=normalize(uEye-vP); c+=pow(1.0-max(dot(n,v),0.0),3.0)*0.18;
 c=c/(1.0+c)*1.25; o=vec4(pow(clamp(c,0.0,1.0),vec3(1.0/2.2)),1.0); })";

GLuint compile(GLenum type, const char* src) {
  GLuint s = glCreateShader(type);
  glShaderSource(s, 1, &src, nullptr);
  glCompileShader(s);
  GLint ok = 0;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char log[2048];
    glGetShaderInfoLog(s, sizeof log, nullptr, log);
    logError("shader: {}", log);
  }
  return s;
}

struct GLMesh {
  GLuint vao = 0, vbo = 0, ebo = 0;
  GLsizei count = 0;
};

class PreviewRenderer {
 public:
  void init() {
    prog_ = glCreateProgram();
    glAttachShader(prog_, compile(GL_VERTEX_SHADER, kVs));
    glAttachShader(prog_, compile(GL_FRAGMENT_SHADER, kFs));
    glLinkProgram(prog_);
  }
  void resize(int w, int h) {
    if (w == w_ && h == h_) return;
    w_ = w;
    h_ = h;
    if (!fbo_) {
      glGenFramebuffers(1, &fbo_);
      glGenTextures(1, &tex_);
      glGenRenderbuffers(1, &depth_);
    }
    glBindTexture(GL_TEXTURE_2D, tex_);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glBindRenderbuffer(GL_RENDERBUFFER, depth_);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, w, h);
    glBindFramebuffer(GL_FRAMEBUFFER, fbo_);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex_, 0);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth_);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
  }
  // Vertex colours come from the procedural textures (evaluated once per mesh).
  void upload(const FrameSnapshot& snap, bool recolor) {
    if (recolor) colors_.clear();
    colors_.resize(snap.meshes.size());
    while (meshes_.size() < snap.meshes.size()) {
      GLMesh m;
      glGenVertexArrays(1, &m.vao);
      glGenBuffers(1, &m.vbo);
      glGenBuffers(1, &m.ebo);
      meshes_.push_back(m);
    }
    std::vector<float> data;
    for (size_t i = 0; i < snap.meshes.size(); ++i) {
      const Mesh& mesh = *snap.meshes[i].mesh;
      const Material& mat = snap.materials[size_t(snap.meshes[i].material)];
      auto& cols = colors_[i];
      if (cols.size() != mesh.positions.size()) {
        cols.resize(mesh.positions.size());
        parallelFor(cols.size(), [&](size_t v) { cols[v] = evalTexture(mat, mesh.pref.empty() ? mesh.positions[v] : mesh.pref[v]); }, 4096);
      }
      data.resize(mesh.positions.size() * 9);
      for (size_t v = 0; v < mesh.positions.size(); ++v) {
        std::memcpy(&data[v * 9], &mesh.positions[v], 12);
        std::memcpy(&data[v * 9 + 3], &mesh.normals[v], 12);
        std::memcpy(&data[v * 9 + 6], &cols[v], 12);
      }
      GLMesh& g = meshes_[i];
      glBindVertexArray(g.vao);
      glBindBuffer(GL_ARRAY_BUFFER, g.vbo);
      glBufferData(GL_ARRAY_BUFFER, GLsizeiptr(data.size() * 4), data.data(), GL_STREAM_DRAW);
      for (GLuint a = 0; a < 3; ++a) {
        glEnableVertexAttribArray(a);
        glVertexAttribPointer(a, 3, GL_FLOAT, GL_FALSE, 36, reinterpret_cast<void*>(uintptr_t(a * 12)));
      }
      glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, g.ebo);
      glBufferData(GL_ELEMENT_ARRAY_BUFFER, GLsizeiptr(mesh.indices.size() * 4), mesh.indices.data(), GL_STREAM_DRAW);
      g.count = GLsizei(mesh.indices.size());
    }
    drawCount_ = snap.meshes.size();
    glBindVertexArray(0);
  }
  void draw(const mat4& vp, vec3 eye, vec3 sunDir, vec3 sunCol, int highlight) {
    glBindFramebuffer(GL_FRAMEBUFFER, fbo_);
    glViewport(0, 0, w_, h_);
    glClearColor(0.16f, 0.16f, 0.18f, 1);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glUseProgram(prog_);
    glUniformMatrix4fv(glGetUniformLocation(prog_, "uVP"), 1, GL_FALSE, &vp[0][0]);
    glUniform3fv(glGetUniformLocation(prog_, "uSunDir"), 1, &sunDir.x);
    glUniform3fv(glGetUniformLocation(prog_, "uSunCol"), 1, &sunCol.x);
    glUniform3fv(glGetUniformLocation(prog_, "uEye"), 1, &eye.x);
    GLint tint = glGetUniformLocation(prog_, "uTint");
    for (size_t i = 0; i < drawCount_; ++i) {
      vec3 t = int(i) == highlight ? vec3(1.25f, 1.15f, 0.7f) : vec3(1);
      glUniform3fv(tint, 1, &t.x);
      glBindVertexArray(meshes_[i].vao);
      glDrawElements(GL_TRIANGLES, meshes_[i].count, GL_UNSIGNED_INT, nullptr);
    }
    glBindVertexArray(0);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
  }
  GLuint texture() const { return tex_; }

 private:
  GLuint prog_ = 0, fbo_ = 0, tex_ = 0, depth_ = 0;
  int w_ = 0, h_ = 0;
  std::vector<GLMesh> meshes_;
  std::vector<std::vector<vec3>> colors_;
  size_t drawCount_ = 0;
};

// ------------------------------------------------------------------ background path tracing
struct RenderJob {
  std::thread worker;
  std::atomic<bool> cancel{false}, running{false};
  std::mutex mutex;
  std::vector<uint8_t> rgb;
  RenderOutput last;
  int width = 0, height = 0, samples = 0, target = 0;
  bool fresh = false;
  std::string status = "idle";
  GLuint tex = 0;
  void stop() {
    cancel = true;
    if (worker.joinable()) worker.join();
    cancel = false;
  }
};

struct App {
  GLFWwindow* window = nullptr;
  fs::path scenePath;
  SceneEvaluator view;  // fast preview evaluator (no fibres, coarser meshes)
  EvalOptions viewOpt{1.4f, 0.0f, false};
  std::unique_ptr<SceneEvaluator> full;  // full quality, built on first render
  bool fullDirty = true;
  bool assetsEdited = false;  // characters changed in the app since loading
  std::vector<CharacterAsset> assets;  // editable copies
  std::shared_ptr<FrameSnapshot> snap;
  PreviewRenderer preview;
  RenderJob job;
  double frame = 1;
  bool playing = false, needEval = true, recolor = true, sceneCamera = true;
  // selection
  enum class Kind { None, Object, Character, Light, Camera, Material } kind = Kind::None;
  int sel = -1, bone = -1, part = -1, prim = -1, lockGroup = 0, lockIndex = 0;
  std::string material;
  // orbit camera
  vec3 orbitTarget{0, 0.6f, 0};
  float yaw = -0.4f, pitch = 0.25f, dist = 2.4f;
  std::string status;
  std::atomic<bool> animRendering{false};
};

Scene& doc(App& a) { return a.view.mutableScene(); }

// Preview geometry for curves: thick curves (lock cores, frames, straps) become low-poly tubes.
FrameSnapshot withTubes(const FrameSnapshot& snap) {
  FrameSnapshot out = snap;
  for (const auto& sf : snap.fibers) {
    const FiberSet& f = *sf.fibers;
    if (f.curveOffsets.size() < 2) continue;
    auto tube = std::make_shared<Mesh>();
    const int sides = 6;
    for (size_t c = 0; c + 1 < f.curveOffsets.size(); ++c) {
      uint32_t a0 = f.curveOffsets[c], a1 = f.curveOffsets[c + 1];
      if (a1 - a0 < 2 || f.points[a0].w < 5e-4f) continue;  // skip fine fibres
      uint32_t base = uint32_t(tube->positions.size());
      for (uint32_t i = a0; i < a1; ++i) {
        vec3 p(f.points[i]), q(f.points[std::min(i + 1, a1 - 1)]), o(f.points[i > a0 ? i - 1 : i]);
        vec3 t = glm::normalize(q - o + vec3(1e-7f));
        Frame fr = Frame::fromNormal(t);
        for (int k = 0; k < sides; ++k) {
          float ang = kTwoPi * float(k) / float(sides);
          vec3 n = std::cos(ang) * fr.t + std::sin(ang) * fr.b;
          tube->positions.push_back(p + n * f.points[i].w);
          tube->normals.push_back(n);
        }
      }
      for (uint32_t i = 0; i + 1 < a1 - a0; ++i)
        for (uint32_t k = 0; k < uint32_t(sides); ++k) {
          uint32_t v0 = base + i * sides + k, v1 = base + i * sides + (k + 1) % sides, v2 = v0 + sides, v3 = v1 + sides;
          tube->indices.insert(tube->indices.end(), {v0, v2, v1, v1, v2, v3});
        }
    }
    if (tube->indices.empty()) continue;
    tube->pref = tube->positions;
    out.meshes.push_back({tube, sf.material});
  }
  return out;
}

Material* findMaterial(App& a, const std::string& name) {
  for (auto& m : doc(a).materials)
    if (m.name == name) return &m;
  for (auto& c : a.assets)
    for (auto& m : c.materials)
      if (m.name == name) return &m;
  return nullptr;
}

void startRender(App& a) {
  a.job.stop();
  RenderSettings rs = doc(a).render;
  Scene sceneCopy = doc(a);
  std::vector<CharacterAsset> assets = a.assets;
  std::vector<Material> mats;
  for (auto& m : doc(a).materials) mats.push_back(m);
  for (auto& c : a.assets) mats.insert(mats.end(), c.materials.begin(), c.materials.end());
  double frame = a.frame;
  bool rebuild = a.fullDirty || !a.full;
  bool edited = a.assetsEdited;
  a.fullDirty = false;
  a.job.running = true;
  a.job.target = rs.spp;
  a.job.worker = std::thread([&a, rs, sceneCopy, assets, mats, frame, rebuild, edited] {
    auto setStatus = [&](std::string s) {
      std::lock_guard lock(a.job.mutex);
      a.job.status = std::move(s);
    };
    if (rebuild) {
      setStatus("building full-quality scene (fibres, fine meshes)...");
      a.full = std::make_unique<SceneEvaluator>();
      EvalOptions fullOpt;
      fullOpt.lodWidth = rs.width;  // coverage-preserving fibre level of detail
      if (auto r = a.full->load(sceneCopy, fullOpt); !r) {
        setStatus("error: " + r.error().message);
        a.job.running = false;
        return;
      }
      if (edited)
        for (size_t i = 0; i < assets.size(); ++i) (void)a.full->rebuildCharacter(i, assets[i], fullOpt);
    }
    a.full->mutableScene() = sceneCopy;
    for (auto& m : mats) a.full->updateMaterial(m);
    PathTracer tracer;
    tracer.setScene(a.full->evaluate(frame));
    Stopwatch sw;
    while (!a.job.cancel && tracer.accumulatedSamples() < rs.spp) {
      int n = std::max(1, std::min({4, tracer.accumulatedSamples() / 4 + 1, rs.spp - tracer.accumulatedSamples()}));
      tracer.accumulate(rs, n, [&] { return a.job.cancel.load(); });
      RenderOutput out = tracer.output();
      bool done = out.samples >= rs.spp;
      if (done && rs.denoise) denoise(out, rs.denoiseBlend);
      auto rgb = toneMapToSrgb8(out.color, ToneMapSettings{rs.exposureEV});
      std::lock_guard lock(a.job.mutex);
      a.job.rgb = std::move(rgb);
      a.job.width = out.color.width;
      a.job.height = out.color.height;
      a.job.samples = out.samples;
      a.job.fresh = true;
      if (done) a.job.last = std::move(out);
      a.job.status = std::format("{} / {} samples, {:.1f}s{}", a.job.samples, rs.spp, sw.seconds(), done ? " (denoised)" : "");
    }
    a.job.running = false;
  });
}

void markEdited(App& a, bool recolor = false) {
  a.needEval = true;
  a.recolor = a.recolor || recolor;
}

// ---------------------------------------------------------------- editor actions (UI buttons and --script share these)
void rebuildCharacter(App& a, size_t ci) {
  if (auto r = a.view.rebuildCharacter(ci, a.assets[ci], a.viewOpt); !r) a.status = r.error().message;
  a.fullDirty = true;
  a.assetsEdited = true;
  markEdited(a, true);
}
bool saveCharacter(App& a, size_t ci) {
  Scene& s = a.view.mutableScene();
  fs::path p = s.path.parent_path() / s.characters[ci].asset;
  auto r = writeTextFile(p, characterToJson(a.assets[ci]).dump(1));
  a.status = r ? "saved " + p.string() : r.error().message;
  return bool(r);
}
// New lock: a copy of the given lock shifted sideways (or a default lock hanging from the crown).
void addLock(App& a, size_t ci, size_t group, int copyOf) {
  LockGroup& g = a.assets[ci].lockGroups[group];
  LockCurve L;
  if (copyOf >= 0 && size_t(copyOf) < g.locks.size()) {
    L = g.locks[size_t(copyOf)];
    for (auto& p : L.points) p.x += 0.02f;
  } else {
    L.points = {vec3(0.0f, 0.99f, -0.06f), vec3(0.0f, 0.93f, -0.17f), vec3(0.0f, 0.80f, -0.2f), vec3(0.0f, 0.66f, -0.18f)};
    L.rootRadius = 0.018f;
    L.tipRadius = 0.005f;
  }
  g.locks.push_back(L);
  a.lockIndex = int(g.locks.size()) - 1;
}

// ------------------------------------------------------------------ panels
bool dragVec3(const char* label, vec3& v, float speed = 0.002f) { return ImGui::DragFloat3(label, &v.x, speed); }

void materialEditor(App& a, Material& m) {
  bool changed = false;
  ImGui::Text("Material: %s", m.name.c_str());
  const char* types[] = {"standard", "plush", "fiber"};
  int t = int(m.type);
  changed |= ImGui::Combo("Type", &t, types, 3);
  m.type = MaterialType(t);
  changed |= ImGui::ColorEdit3("Base colour", &m.baseColor.x, ImGuiColorEditFlags_Float);
  if (m.type == MaterialType::Fiber) {
    changed |= ImGui::SliderFloat("Longitudinal roughness", &m.betaM, 0.05f, 1.0f);
    changed |= ImGui::SliderFloat("Azimuthal roughness", &m.betaN, 0.05f, 1.0f);
  } else {
    changed |= ImGui::SliderFloat("Roughness", &m.roughness, 0.02f, 1.0f);
    changed |= ImGui::SliderFloat("Sheen", &m.sheen, 0.0f, 1.0f);
    changed |= ImGui::ColorEdit3("Sheen colour", &m.sheenColor.x, ImGuiColorEditFlags_Float);
    changed |= ImGui::SliderFloat("Clear coat", &m.coat, 0.0f, 1.0f);
    changed |= ImGui::SliderFloat("Coat roughness", &m.coatRoughness, 0.01f, 1.0f);
  }
  if (m.texture.type != TextureType::None) {
    changed |= ImGui::ColorEdit3("Pattern colour", &m.texture.color2.x, ImGuiColorEditFlags_Float);
    changed |= ImGui::SliderFloat("Pattern amount", &m.texture.amount, 0.0f, 1.0f);
  }
  if (changed) {
    a.view.updateMaterial(m);
    a.fullDirty = a.fullDirty || false;
    markEdited(a, true);
  }
}

void outliner(App& a) {
  ImGui::Begin("Outliner");
  Scene& s = doc(a);
  if (ImGui::TreeNodeEx("Characters", ImGuiTreeNodeFlags_DefaultOpen)) {
    for (size_t i = 0; i < s.characters.size(); ++i)
      if (ImGui::Selectable(s.characters[i].name.c_str(), a.kind == App::Kind::Character && a.sel == int(i))) {
        a.kind = App::Kind::Character;
        a.sel = int(i);
        a.bone = a.part = a.prim = -1;
      }
    ImGui::TreePop();
  }
  if (ImGui::TreeNode("Objects")) {
    for (size_t i = 0; i < s.objects.size(); ++i)
      if (ImGui::Selectable(s.objects[i].name.c_str(), a.kind == App::Kind::Object && a.sel == int(i))) {
        a.kind = App::Kind::Object;
        a.sel = int(i);
      }
    ImGui::TreePop();
  }
  if (ImGui::TreeNode("Lights")) {
    for (size_t i = 0; i < s.lights.size(); ++i) {
      const char* names[] = {"Sun", "Window / area", "Sky"};
      std::string label = std::format("{} {}", names[int(s.lights[i].type)], i);
      if (ImGui::Selectable(label.c_str(), a.kind == App::Kind::Light && a.sel == int(i))) {
        a.kind = App::Kind::Light;
        a.sel = int(i);
      }
    }
    ImGui::TreePop();
  }
  if (ImGui::Selectable("Camera", a.kind == App::Kind::Camera)) a.kind = App::Kind::Camera;
  if (ImGui::TreeNode("Materials")) {
    auto list = [&](std::vector<Material>& mats) {
      for (auto& m : mats)
        if (ImGui::Selectable(m.name.c_str(), a.kind == App::Kind::Material && a.material == m.name)) {
          a.kind = App::Kind::Material;
          a.material = m.name;
        }
    };
    list(s.materials);
    for (auto& c : a.assets) list(c.materials);
    ImGui::TreePop();
  }
  ImGui::End();
}

void characterInspector(App& a, size_t ci) {
  CharacterAsset& asset = a.assets[ci];
  Scene& s = doc(a);
  const std::string& cname = s.characters[ci].name;
  if (ImGui::CollapsingHeader("Pose & keyframes", ImGuiTreeNodeFlags_DefaultOpen)) {
    std::vector<const char*> names;
    for (auto& b : asset.skeleton.bones) names.push_back(b.name.c_str());
    ImGui::Combo("Bone", &a.bone, names.data(), int(names.size()));
    if (a.bone >= 0 && a.bone < int(names.size())) {
      std::string track = cname + "/" + asset.skeleton.bones[size_t(a.bone)].name + ".rot";
      vec3 rot = s.animation.evaluate(track, a.frame, vec3(0));
      if (ImGui::DragFloat3("Rotation (deg)", &rot.x, 0.5f, -180, 180)) {
        s.animation.tracks[track].setKey({std::round(a.frame), rot, Interp::Smooth});
        markEdited(a);
      }
      if (ImGui::Button("Delete key at frame") && s.animation.tracks.count(track)) {
        s.animation.tracks[track].removeKey(std::round(a.frame), 0.01);
        markEdited(a);
      }
      ImGui::TextDisabled("Editing a value sets a key at the current frame.");
    }
  }
  if (ImGui::CollapsingHeader("Shape (soft primitives)")) {
    std::vector<const char*> parts;
    for (auto& p : asset.parts) parts.push_back(p.name.c_str());
    ImGui::Combo("Part", &a.part, parts.data(), int(parts.size()));
    if (a.part >= 0 && a.part < int(asset.parts.size())) {
      SdfPart& part = asset.parts[size_t(a.part)];
      ImGui::SliderFloat("Surface lumpiness", &part.noiseAmplitude, 0.0f, 0.01f, "%.4f");
      std::vector<std::string> labels;
      for (auto& p : part.prims) labels.push_back(p.name.empty() ? "(unnamed)" : p.name);
      std::vector<const char*> lp;
      for (auto& l : labels) lp.push_back(l.c_str());
      ImGui::Combo("Primitive", &a.prim, lp.data(), int(lp.size()));
      if (a.prim >= 0 && a.prim < int(part.prims.size())) {
        SdfPrim& p = part.prims[size_t(a.prim)];
        if (p.type == PrimType::Ellipsoid || p.type == PrimType::RoundBox) {
          dragVec3("Centre", p.center);
          dragVec3(p.type == PrimType::Ellipsoid ? "Radii" : "Half size", p.radii, 0.001f);
        } else {
          dragVec3("End A", p.a);
          dragVec3("End B", p.b);
          ImGui::DragFloat("Radius A", &p.r1, 0.001f, 0.001f, 0.5f);
          if (p.type == PrimType::RoundCone) ImGui::DragFloat("Radius B", &p.r2, 0.001f, 0.001f, 0.5f);
        }
        ImGui::DragFloat("Blend", &p.blend, 0.001f, 0.0f, 0.2f);
        ImGui::Checkbox("Subtract", &p.subtract);
      }
    }
    if (ImGui::Button("Rebuild character")) {
      if (auto r = a.view.rebuildCharacter(ci, asset, a.viewOpt); !r) a.status = r.error().message;
      a.fullDirty = true;
      a.assetsEdited = true;
      markEdited(a, true);
    }
    ImGui::SameLine();
    if (ImGui::Button("Save character")) {
      fs::path p = s.path.parent_path() / s.characters[ci].asset;
      auto r = writeTextFile(p, characterToJson(asset).dump(1));
      a.status = r ? "saved " + p.string() : r.error().message;
    }
  }
  if (ImGui::CollapsingHeader("Hair locks & curves", ImGuiTreeNodeFlags_DefaultOpen) && !asset.lockGroups.empty()) {
    std::vector<const char*> gn;
    for (auto& g : asset.lockGroups) gn.push_back(g.name.c_str());
    a.lockGroup = std::clamp(a.lockGroup, 0, int(gn.size()) - 1);
    ImGui::Combo("Group", &a.lockGroup, gn.data(), int(gn.size()));
    LockGroup& g = asset.lockGroups[size_t(a.lockGroup)];
    ImGui::Text("%d locks  |  material %s", int(g.locks.size()), g.coreMaterial.c_str());
    ImGui::SliderFloat("Halo density /cm2", &g.params.fuzzDensity, 0.0f, 400.0f);
    ImGui::SliderFloat("Halo length", &g.params.fuzzLength, 0.0005f, 0.02f, "%.4f");
    if (!g.locks.empty()) {
      a.lockIndex = std::clamp(a.lockIndex, 0, int(g.locks.size()) - 1);
      ImGui::SliderInt("Lock", &a.lockIndex, 0, int(g.locks.size()) - 1);
      LockCurve& L = g.locks[size_t(a.lockIndex)];
      for (size_t k = 0; k < L.points.size(); ++k) {
        std::string label = k == 0 ? "Root" : std::format("Point {}", k);
        ImGui::DragFloat3(label.c_str(), &L.points[k].x, 0.001f);
      }
      if (ImGui::Button("+ point")) L.points.push_back(L.points.back() + (L.points.back() - L.points[L.points.size() - 2]) * 0.5f);
      ImGui::SameLine();
      if (ImGui::Button("- point") && L.points.size() > 2) L.points.pop_back();
      ImGui::DragFloat("Root thickness", &L.rootRadius, 0.0005f, 0.0005f, 0.06f, "%.4f");
      ImGui::DragFloat("Tip thickness", &L.tipRadius, 0.0005f, 0.0003f, 0.06f, "%.4f");
      ImGui::DragFloat("Curl radius", &L.curlRadius, 0.0005f, 0.0f, 0.05f, "%.4f");
      ImGui::DragFloat("Curl turns", &L.curlTurns, 0.05f, 0.0f, 12.0f);
    }
    if (ImGui::Button("Add lock")) addLock(a, ci, size_t(a.lockGroup), -1);
    ImGui::SameLine();
    if (ImGui::Button("Duplicate")) addLock(a, ci, size_t(a.lockGroup), a.lockIndex);
    ImGui::SameLine();
    if (ImGui::Button("Delete") && !g.locks.empty()) g.locks.erase(g.locks.begin() + a.lockIndex);
    if (ImGui::Button("Apply hair changes")) rebuildCharacter(a, ci);
    ImGui::SameLine();
    if (ImGui::Button("Save character##hair")) saveCharacter(a, ci);
  }
  if (ImGui::CollapsingHeader("Placement")) {
    CharacterDesc& cd = s.characters[ci];
    if (dragVec3("Position", cd.position)) markEdited(a);
    if (ImGui::DragFloat("Yaw", &cd.yawDeg, 0.5f)) markEdited(a);
  }
}

void inspector(App& a) {
  ImGui::Begin("Inspector");
  Scene& s = doc(a);
  switch (a.kind) {
    case App::Kind::None: ImGui::TextDisabled("Select something in the Outliner."); break;
    case App::Kind::Character: characterInspector(a, size_t(a.sel)); break;
    case App::Kind::Object: {
      ObjectDesc& o = s.objects[size_t(a.sel)];
      ImGui::Text("%s", o.name.c_str());
      if (o.kind == ObjectDesc::Kind::Box) {
        ImGui::TextDisabled("Static box (room geometry)");
      } else {
        vec3 pos = s.animation.evaluate(o.name + ".position", a.frame, o.position);
        if (dragVec3("Position", pos)) {
          if (s.animation.find(o.name + ".position")) s.animation.tracks[o.name + ".position"].setKey({std::round(a.frame), pos});
          else o.position = pos;
          markEdited(a);
        }
        if (ImGui::Button("Key position")) {
          s.animation.tracks[o.name + ".position"].setKey({std::round(a.frame), pos});
          markEdited(a);
        }
        if (ImGui::DragFloat("Yaw", &o.yawDeg, 0.5f)) markEdited(a);
      }
      if (Material* m = findMaterial(a, o.material)) materialEditor(a, *m);
      break;
    }
    case App::Kind::Light: {
      Light& l = s.lights[size_t(a.sel)];
      bool c = ImGui::ColorEdit3("Colour", &l.color.x, ImGuiColorEditFlags_Float);
      c |= ImGui::DragFloat("Intensity", &l.intensity, 0.02f, 0.0f, 100.0f);
      if (l.type == Light::Type::Sun) {
        c |= dragVec3("Direction", l.direction, 0.005f);
        c |= ImGui::SliderFloat("Size (deg)", &l.angleDeg, 0.1f, 20.0f);
        l.direction = glm::normalize(l.direction);
      }
      if (c) markEdited(a);
      break;
    }
    case App::Kind::Camera: {
      Camera& cam = s.camera;
      vec3 pos = s.animation.evaluate("camera.position", a.frame, cam.position);
      vec3 tgt = s.animation.evaluate("camera.target", a.frame, cam.target);
      bool c = dragVec3("Position", pos, 0.005f);
      c |= dragVec3("Target", tgt, 0.005f);
      if (c) {
        if (s.animation.find("camera.position")) s.animation.tracks["camera.position"].setKey({std::round(a.frame), pos});
        else cam.position = pos;
        if (s.animation.find("camera.target")) s.animation.tracks["camera.target"].setKey({std::round(a.frame), tgt});
        else cam.target = tgt;
      }
      c |= ImGui::SliderFloat("Focal length (mm)", &cam.focalMm, 12, 200);
      c |= ImGui::SliderFloat("f-stop (0 = no blur)", &cam.fStop, 0, 22);
      if (ImGui::Button("Key camera")) {
        s.animation.tracks["camera.position"].setKey({std::round(a.frame), pos});
        s.animation.tracks["camera.target"].setKey({std::round(a.frame), tgt});
        c = true;
      }
      ImGui::SameLine();
      if (ImGui::Button("Camera from view")) {
        vec3 eye = a.orbitTarget + a.dist * vec3(std::cos(a.pitch) * std::sin(a.yaw), std::sin(a.pitch), std::cos(a.pitch) * std::cos(a.yaw));
        cam.position = eye;
        cam.target = a.orbitTarget;
        s.animation.tracks.erase("camera.position");
        s.animation.tracks.erase("camera.target");
        a.sceneCamera = true;
        c = true;
      }
      if (c) markEdited(a);
      break;
    }
    case App::Kind::Material:
      if (Material* m = findMaterial(a, a.material)) materialEditor(a, *m);
      break;
  }
  ImGui::End();
}

void timeline(App& a) {
  ImGui::Begin("Timeline");
  Scene& s = doc(a);
  if (ImGui::Button(a.playing ? "Pause" : "Play")) a.playing = !a.playing;
  ImGui::SameLine();
  if (ImGui::Button("|<")) { a.frame = s.frameStart; markEdited(a); }
  ImGui::SameLine();
  float f = float(a.frame);
  ImGui::SetNextItemWidth(-200);
  if (ImGui::SliderFloat("##frame", &f, float(s.frameStart), float(s.frameEnd), "frame %.0f")) {
    a.frame = std::round(f);
    markEdited(a);
  }
  ImGui::SameLine();
  ImGui::SetNextItemWidth(80);
  ImGui::DragInt("start", &s.frameStart, 1, 0, s.frameEnd);
  ImGui::SameLine();
  ImGui::SetNextItemWidth(80);
  ImGui::DragInt("end", &s.frameEnd, 1, s.frameStart, 100000);
  // Key markers for the selected bone (or all tracks).
  ImDrawList* dl = ImGui::GetWindowDrawList();
  ImVec2 p0 = ImGui::GetCursorScreenPos();
  float w = ImGui::GetContentRegionAvail().x;
  dl->AddRectFilled(p0, ImVec2(p0.x + w, p0.y + 18), IM_COL32(40, 40, 46, 255));
  auto xOf = [&](double fr) { return p0.x + float((fr - s.frameStart) / std::max(1, s.frameEnd - s.frameStart)) * w; };
  for (auto& [name, track] : s.animation.tracks)
    for (auto& k : track.keys) dl->AddRectFilled(ImVec2(xOf(k.frame) - 1.5f, p0.y + 3), ImVec2(xOf(k.frame) + 1.5f, p0.y + 15), IM_COL32(230, 190, 80, 200));
  dl->AddLine(ImVec2(xOf(a.frame), p0.y), ImVec2(xOf(a.frame), p0.y + 18), IM_COL32(255, 90, 90, 255), 2);
  ImGui::Dummy(ImVec2(w, 20));
  ImGui::End();
}

void renderPanel(App& a) {
  ImGui::Begin("Render");
  RenderSettings& rs = doc(a).render;
  ImGui::SetNextItemWidth(120);
  ImGui::DragInt("Width", &rs.width, 8, 64, 7680);
  ImGui::SameLine();
  ImGui::SetNextItemWidth(120);
  ImGui::DragInt("Height", &rs.height, 8, 64, 4320);
  ImGui::SetNextItemWidth(120);
  ImGui::DragInt("Samples", &rs.spp, 1, 1, 4096);
  ImGui::SameLine();
  ImGui::SetNextItemWidth(120);
  ImGui::SliderFloat("Exposure", &rs.exposureEV, -4, 4);
  ImGui::Checkbox("Denoise", &rs.denoise);
  if (ImGui::Button(a.job.running ? "Restart path trace" : "Path trace this frame")) startRender(a);
  ImGui::SameLine();
  if (ImGui::Button("Stop")) a.job.stop();
  ImGui::SameLine();
  if (ImGui::Button("Save image")) {
    std::lock_guard lock(a.job.mutex);
    fs::path out = fs::path("renders") / std::format("{}_f{:04d}.png", doc(a).path.stem().stem().string(), int(a.frame));
    auto r = a.job.rgb.empty() ? fail("nothing rendered yet") : writePng(out, a.job.width, a.job.height, a.job.rgb);
    a.status = r ? "saved " + out.string() : r.error().message;
  }
  if (ImGui::Button(a.animRendering ? "Rendering animation..." : "Render animation to video") && !a.animRendering) {
    if (auto r = saveScene(doc(a), doc(a).path); r) {
      for (size_t i = 0; i < a.assets.size(); ++i)
        (void)writeTextFile(doc(a).path.parent_path() / doc(a).characters[i].asset, characterToJson(a.assets[i]).dump(1));
      std::string stem = doc(a).path.stem().stem().string();
      std::string cmd = std::format("\"{}\" \"{}\" --frames {}-{} --outdir renders/{} --video renders/{}.mp4 > renders/{}.log 2>&1",
                                    PLUSH_RENDER_CLI, doc(a).path.string(), doc(a).frameStart, doc(a).frameEnd, stem, stem, stem);
      a.animRendering = true;
      std::thread([&a, cmd] {
        int rc = std::system(cmd.c_str());
        a.status = rc == 0 ? "animation finished (see renders/)" : "animation render failed, see renders/*.log";
        a.animRendering = false;
      }).detach();
    }
  }
  {
    std::lock_guard lock(a.job.mutex);
    ImGui::TextUnformatted(a.job.status.c_str());
    if (a.job.fresh && !a.job.rgb.empty()) {
      if (!a.job.tex) glGenTextures(1, &a.job.tex);
      glBindTexture(GL_TEXTURE_2D, a.job.tex);
      glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
      glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, a.job.width, a.job.height, 0, GL_RGB, GL_UNSIGNED_BYTE, a.job.rgb.data());
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
      a.job.fresh = false;
    }
  }
  if (a.job.tex && a.job.width > 0) {
    float avail = ImGui::GetContentRegionAvail().x;
    ImGui::Image(ImTextureID(uintptr_t(a.job.tex)), ImVec2(avail, avail * float(a.job.height) / float(a.job.width)));
  }
  ImGui::End();
}

void viewport(App& a) {
  ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0, 0));
  ImGui::Begin("Viewport");
  ImVec2 size = ImGui::GetContentRegionAvail();
  int w = std::max(16, int(size.x)), h = std::max(16, int(size.y));
  a.preview.resize(w, h);
  float aspect = float(w) / float(h);
  vec3 eye, target;
  mat4 proj;
  if (a.sceneCamera && a.snap) {
    const Camera& c = a.snap->camera;
    eye = c.position;
    target = c.target;
    float sensorH = c.sensorWidthMm / aspect;
    proj = glm::perspective(2.0f * std::atan(0.5f * sensorH / c.focalMm), aspect, 0.01f, 50.0f);
  } else {
    eye = a.orbitTarget + a.dist * vec3(std::cos(a.pitch) * std::sin(a.yaw), std::sin(a.pitch), std::cos(a.pitch) * std::cos(a.yaw));
    target = a.orbitTarget;
    proj = glm::perspective(glm::radians(40.0f), aspect, 0.01f, 50.0f);
  }
  vec3 sunDir(0.3f, -1, 0.2f), sunCol(1);
  if (a.snap)
    for (auto& l : a.snap->lights)
      if (l.type == Light::Type::Sun) { sunDir = l.direction; sunCol = glm::min(vec3(1.2f), l.color * (l.intensity / 6.0f)); }
  int highlight = -1;
  if (a.kind == App::Kind::Object) highlight = a.sel;
  a.preview.draw(proj * glm::lookAt(eye, target, vec3(0, 1, 0)), eye, sunDir, sunCol, highlight);
  ImVec2 origin = ImGui::GetCursorScreenPos();
  ImGui::Image(ImTextureID(uintptr_t(a.preview.texture())), ImVec2(float(w), float(h)), ImVec2(0, 1), ImVec2(1, 0));
  if (ImGui::IsItemHovered()) {
    ImGuiIO& io = ImGui::GetIO();
    if (ImGui::IsMouseDragging(ImGuiMouseButton_Left) || ImGui::IsMouseDragging(ImGuiMouseButton_Right)) {
      if (a.sceneCamera && a.snap) {  // start orbiting from the scene camera
        a.orbitTarget = a.snap->camera.target;
        vec3 d = a.snap->camera.position - a.orbitTarget;
        a.dist = glm::length(d);
        a.yaw = std::atan2(d.x, d.z);
        a.pitch = std::asin(d.y / a.dist);
        a.sceneCamera = false;
      }
      a.yaw -= io.MouseDelta.x * 0.006f;
      a.pitch = std::clamp(a.pitch + io.MouseDelta.y * 0.006f, -1.4f, 1.4f);
    }
    if (io.MouseWheel != 0) {
      a.dist = std::clamp(a.dist * std::pow(0.9f, io.MouseWheel), 0.1f, 20.0f);
      a.sceneCamera = false;
    }
  }
  ImGui::SetCursorScreenPos(ImVec2(origin.x + 8, origin.y + 8));
  ImGui::Checkbox("Look through scene camera", &a.sceneCamera);
  ImGui::End();
  ImGui::PopStyleVar();
}

}  // namespace

int main(int argc, char** argv) {
  fs::path scenePath = "content/scenes/milestone01_classroom.scene.json";
  std::string screenshot;
  bool scriptHairEdit = false, scriptVerify = false;
  int screenshotAfter = 30;
  bool autoRender = false;
  int renderW = 0, renderH = 0, renderSpp = 0;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--screenshot" && i + 1 < argc) screenshot = argv[++i];
    else if (arg == "--screenshot-after" && i + 1 < argc) screenshotAfter = std::stoi(argv[++i]);
    else if (arg == "--auto-render") autoRender = true;
    else if (arg == "--render-size" && i + 2 < argc) { renderW = std::stoi(argv[++i]); renderH = std::stoi(argv[++i]); }
    else if (arg == "--render-spp" && i + 1 < argc) renderSpp = std::stoi(argv[++i]);
    else if (arg == "--script-hair-edit") scriptHairEdit = true;  // automated editor test (same actions as the buttons)
    else if (arg == "--script-verify") scriptVerify = true;
    else scenePath = arg;
  }
  if (!glfwInit()) {
    logError("could not initialise GLFW (no display?)");
    return 1;
  }
  glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
  glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
  glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
  glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
  App app;
  app.window = glfwCreateWindow(1600, 900, "Plush Studio", nullptr, nullptr);
  if (!app.window) {
    logError("could not create an OpenGL 3.3 window");
    return 1;
  }
  glfwMakeContextCurrent(app.window);
  glfwSwapInterval(1);
  glewExperimental = GL_TRUE;
  if (glewInit() != GLEW_OK) {
    logError("GLEW initialisation failed");
    return 1;
  }
  IMGUI_CHECKVERSION();
  ImGui::CreateContext();
  ImGuiIO& io = ImGui::GetIO();
  io.ConfigFlags |= ImGuiConfigFlags_DockingEnable;
  ImGui::StyleColorsDark();
  ImGui_ImplGlfw_InitForOpenGL(app.window, true);
  ImGui_ImplOpenGL3_Init("#version 330");
  app.preview.init();

  auto scene = loadScene(scenePath);
  if (!scene) {
    logError("{}", scene.error().message);
    return 1;
  }
  app.frame = scene->frameStart;
  if (auto r = app.view.load(*scene, app.viewOpt); !r) {
    logError("{}", r.error().message);
    return 1;
  }
  for (auto& c : app.view.characters()) app.assets.push_back(c.asset);
  app.status = "loaded " + scenePath.string();
  if (renderW > 0) { doc(app).render.width = renderW; doc(app).render.height = renderH; }
  if (renderSpp > 0) doc(app).render.spp = renderSpp;
  if (scriptHairEdit && !app.assets.empty() && !app.assets[0].lockGroups.empty()) {
    // Select the first character's first hair group, duplicate lock 0, thicken it, apply, save scene + character.
    app.kind = App::Kind::Character;
    app.sel = 0;
    size_t gi = 0;
    for (size_t k = 0; k < app.assets[0].lockGroups.size(); ++k)
      if (app.assets[0].lockGroups[k].name.rfind("hair.", 0) == 0) { gi = k; break; }
    app.lockGroup = int(gi);
    size_t before = app.assets[0].lockGroups[gi].locks.size();
    addLock(app, 0, gi, 0);
    app.assets[0].lockGroups[gi].locks.back().rootRadius *= 1.5f;
    rebuildCharacter(app, 0);
    doc(app).animation.tracks["camera.position"].setKey({2, doc(app).camera.position + vec3(0.1f, 0, 0)});
    bool ok = saveCharacter(app, 0) && bool(saveScene(doc(app), doc(app).path));
    logInfo("script: group '{}' locks {} -> {}, saved: {}", app.assets[0].lockGroups[gi].name, before,
            app.assets[0].lockGroups[gi].locks.size(), ok ? "yes" : "no");
  }
  if (scriptVerify && !app.assets.empty())
    for (auto& g : app.assets[0].lockGroups) logInfo("verify: group '{}' has {} locks", g.name, g.locks.size());
  if (autoRender) startRender(app);

  int frameCounter = 0;
  double last = glfwGetTime();
  while (!glfwWindowShouldClose(app.window)) {
    glfwPollEvents();
    double now = glfwGetTime();
    if (app.playing) {
      app.frame += (now - last) * doc(app).rate.fps();
      if (app.frame > doc(app).frameEnd) app.frame = doc(app).frameStart;
      app.needEval = true;
    }
    last = now;
    if (app.needEval) {
      app.snap = app.view.evaluate(app.playing ? std::floor(app.frame) : app.frame);
      app.preview.upload(withTubes(*app.snap), app.recolor);
      app.needEval = app.recolor = false;
    }
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplGlfw_NewFrame();
    ImGui::NewFrame();
    ImGui::DockSpaceOverViewport(0, ImGui::GetMainViewport());
    if (ImGui::BeginMainMenuBar()) {
      if (ImGui::BeginMenu("File")) {
        if (ImGui::MenuItem("Save scene", "Ctrl+S")) {
          auto r = saveScene(doc(app), doc(app).path);
          app.status = r ? "saved " + doc(app).path.string() : r.error().message;
        }
        if (ImGui::MenuItem("Quit")) glfwSetWindowShouldClose(app.window, 1);
        ImGui::EndMenu();
      }
      ImGui::TextDisabled("  %s  |  %s", doc(app).name.c_str(), app.status.c_str());
      ImGui::EndMainMenuBar();
    }
    if (io.KeyCtrl && ImGui::IsKeyPressed(ImGuiKey_S)) (void)saveScene(doc(app), doc(app).path);
    ImGui::SetNextWindowPos(ImVec2(0, 20), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(260, 640), ImGuiCond_FirstUseEver);
    outliner(app);
    ImGui::SetNextWindowPos(ImVec2(260, 20), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(900, 640), ImGuiCond_FirstUseEver);
    viewport(app);
    ImGui::SetNextWindowPos(ImVec2(1160, 20), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(440, 340), ImGuiCond_FirstUseEver);
    inspector(app);
    ImGui::SetNextWindowPos(ImVec2(1160, 360), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(440, 540), ImGuiCond_FirstUseEver);
    renderPanel(app);
    ImGui::SetNextWindowPos(ImVec2(0, 660), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(1160, 240), ImGuiCond_FirstUseEver);
    timeline(app);
    ImGui::Render();
    int fbw, fbh;
    glfwGetFramebufferSize(app.window, &fbw, &fbh);
    glViewport(0, 0, fbw, fbh);
    glClearColor(0.1f, 0.1f, 0.11f, 1);
    glClear(GL_COLOR_BUFFER_BIT);
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    if (!screenshot.empty() && ++frameCounter >= screenshotAfter && (!autoRender || (!app.job.running && app.job.samples > 0))) {
      std::vector<uint8_t> px(size_t(fbw) * size_t(fbh) * 3), flipped(px.size());
      glPixelStorei(GL_PACK_ALIGNMENT, 1);
      glReadPixels(0, 0, fbw, fbh, GL_RGB, GL_UNSIGNED_BYTE, px.data());
      for (int y = 0; y < fbh; ++y) std::memcpy(&flipped[size_t(y) * size_t(fbw) * 3], &px[size_t(fbh - 1 - y) * size_t(fbw) * 3], size_t(fbw) * 3);
      (void)writePng(screenshot, fbw, fbh, flipped);
      logInfo("screenshot written to {}", screenshot);
      glfwSetWindowShouldClose(app.window, 1);
    }
    glfwSwapBuffers(app.window);
  }
  app.job.stop();
  ImGui_ImplOpenGL3_Shutdown();
  ImGui_ImplGlfw_Shutdown();
  ImGui::DestroyContext();
  glfwDestroyWindow(app.window);
  glfwTerminate();
  return 0;
}
