// Plush Studio: the desktop application.
// Viewport (OpenGL preview), outliner, inspector (objects, lights, camera,
// materials, character shapes and bones), timeline with keyframes, and an
// in-app path-traced render view. The scene file is the document.
#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include <imgui.h>
#include <imgui_internal.h>  // DockBuilder (shot layout)
#include <imgui_impl_glfw.h>
#include <imgui_impl_opengl3.h>

#include <signal.h>

#include <atomic>
#include <cstdio>
#include <fstream>
#include <map>
#include <mutex>
#include <set>
#include <sstream>
#include <thread>

#include "render/bsdf.h"
#include "render/image.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"
#include "shot_workflow.h"

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
  bool loaded = false;  // a scene is loaded into the evaluators
  // ---- production workflow (T-001): Studio drives pipeline/production/run_shot.py and displays its results
  bool shotMode = false;                 // the document is a shot: saved by merging into shot.path
  workflow::ShotInfo shot;
  workflow::Config cfg;
  std::vector<workflow::ShotInfo> shots;  // shot browser
  int browserSel = -1;
  workflow::Job prodJob;
  std::string jobRunId, jobKind;
  workflow::RunSettings settings;
  workflow::RunStatus jobStatus;
  std::string jobLogTail, prodError;
  double lastPoll = 0;
  std::vector<workflow::RunInfo> runs;
  std::string selRunId;
  workflow::Job::CancelResult lastCancel;
  // result viewer texture
  GLuint viewTex = 0;
  fs::path viewImage;
  fs::file_time_type viewStamp{};
  int viewW = 0, viewH = 0;
  // responsiveness while a job runs
  int jobUiFrames = 0;
  double jobMaxFrameDt = 0;
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
  if (a.shotMode) {  // a shot's characters are engine packages built by the pipeline (a cache), never edited here
    a.status = "characters of a shot are edited at their sources (spec / asset store), not inside the shot";
    return false;
  }
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
    if (ImGui::Button("Save character")) saveCharacter(a, ci);
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
    if (ImGui::Checkbox("Life layer (breathing, sway, blinks)", &cd.life.enabled)) markEdited(a);
    if (cd.life.enabled) {
      if (ImGui::SliderFloat("Breathing", &cd.life.breathing, 0.0f, 2.0f)) markEdited(a);
      if (ImGui::SliderFloat("Sway", &cd.life.sway, 0.0f, 2.0f)) markEdited(a);
    }
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
    // A shot renders a copy of its resolved scene (engine preview); its packages are pipeline outputs, not rewritten.
    fs::path scenePath = a.shotMode ? a.shot.buildDir() / "studio_engine_preview.scene.json" : doc(a).path;
    if (auto r = saveScene(doc(a), scenePath); r) {
      if (!a.shotMode)
        for (size_t i = 0; i < a.assets.size(); ++i)
          (void)writeTextFile(doc(a).path.parent_path() / doc(a).characters[i].asset, characterToJson(a.assets[i]).dump(1));
      std::string stem = a.shotMode ? a.shot.episode + "_" + a.shot.shot + "_engine" : doc(a).path.stem().stem().string();
      std::error_code ec;
      fs::create_directories("renders", ec);
      std::string cmd = std::format("\"{}\" \"{}\" --frames {}-{} --outdir renders/{} --video renders/{}.mp4 > renders/{}.log 2>&1",
                                    PLUSH_RENDER_CLI, scenePath.string(), doc(a).frameStart, doc(a).frameEnd, stem, stem, stem);
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

// ------------------------------------------------------------------ documents and the production workflow (T-001)
// Loads a scene into the evaluators (the legacy single-scene path and a prepared shot's resolved scene).
bool loadDocument(App& a, const fs::path& scenePath) {
  a.job.stop();
  auto scene = loadScene(scenePath);
  if (!scene) {
    a.status = scene.error().message;
    logError("{}", scene.error().message);
    return false;
  }
  a.view = SceneEvaluator();
  a.full.reset();
  a.fullDirty = true;
  a.assetsEdited = false;
  a.assets.clear();
  if (auto r = a.view.load(*scene, a.viewOpt); !r) {
    a.status = r.error().message;
    logError("{}", r.error().message);
    a.loaded = false;
    return false;
  }
  for (auto& c : a.view.characters()) a.assets.push_back(c.asset);
  a.scenePath = scenePath;
  a.loaded = true;
  a.kind = App::Kind::None;
  a.sel = -1;
  a.needEval = a.recolor = true;
  a.status = "loaded " + scenePath.string();
  return true;
}

void refreshRuns(App& a) {
  a.runs = workflow::listRuns(a.shot);
  bool found = false;
  for (auto& r : a.runs) found |= r.id == a.selRunId;
  if (!found) {  // default selection: the newest successful run that rendered frames, else latest, else the newest
    a.selRunId.clear();
    for (auto& r : a.runs) {
      const auto& d = r.status.stagesDone;
      if (r.status.state == "done" && std::find(d.begin(), d.end(), "render") != d.end()) {
        a.selRunId = r.id;
        break;
      }
    }
    if (a.selRunId.empty()) a.selRunId = workflow::latestRunId(a.shot);
    if (a.selRunId.empty() && !a.runs.empty()) a.selRunId = a.runs.front().id;
  }
}

// Opens a shot: the cast is resolved by the pipeline (prepare), so the viewport shows the shot once it is prepared.
bool openShot(App& a, const fs::path& shotFile) {
  auto info = workflow::readShotInfo(shotFile);
  if (!info) {
    a.status = info.error().message;
    logError("{}", info.error().message);
    return false;
  }
  a.shotMode = true;
  a.shot = *info;
  a.settings = workflow::RunSettings{};
  a.settings.frameA = a.shot.frameStart;
  a.settings.frameB = a.shot.frameEnd;
  a.settings.width = a.shot.width;
  a.settings.height = a.shot.height;
  a.settings.samples = a.shot.samples;
  a.selRunId.clear();
  a.prodError.clear();
  refreshRuns(a);
  a.frame = a.shot.frameStart;
  bool ok = true;
  if (workflow::isPrepared(a.shot)) {
    ok = loadDocument(a, a.shot.resolvedScene());
  } else {
    a.job.stop();
    a.view = SceneEvaluator();
    a.full.reset();
    a.assets.clear();
    a.snap.reset();
    a.loaded = false;
    a.status = "shot not prepared: press Prepare (the pipeline resolves its cast)";
  }
  a.frame = a.shot.frameStart;
  logInfo("opened shot {} ({})", a.shot.path.string(), a.loaded ? "prepared" : "not prepared");
  return ok;
}

// Saves the document: a shot merges its edits into the source shot file (production block, placeholders and
// unknown data are kept); a plain scene is written as before.
bool saveDocument(App& a) {
  if (a.shotMode) {
    if (!a.loaded) return true;  // nothing loaded, nothing edited
    auto r = workflow::mergeSaveShot(a.shot.path, doc(a));
    a.status = !r ? r.error().message : *r ? "saved (merged) " + a.shot.path.string() : "no changes to save";
    return bool(r);
  }
  auto r = saveScene(doc(a), doc(a).path);
  a.status = r ? "saved " + doc(a).path.string() : r.error().message;
  return bool(r);
}

bool startProduction(App& a, const std::string& kind, workflow::RunSettings s) {
  if (a.prodJob.running()) {
    a.prodError = "a production job is already running";
    return false;
  }
  if (a.cfg.blender.empty()) {
    a.prodError = "no Blender configured (--blender, PLUSH_BLENDER or " + workflow::settingsFilePath().string() + ")";
    return false;
  }
  if (!saveDocument(a)) {  // the pipeline works on the saved shot file
    a.prodError = "save failed: " + a.status;
    return false;
  }
  if (kind == "prepare") s.stages = {"prepare"};
  a.jobRunId = workflow::newRunId();
  a.jobKind = kind;
  fs::path runDir = a.shot.runsDir() / a.jobRunId;
  auto cmd = workflow::buildCommand(a.cfg, a.shot, a.jobRunId, s);
  std::string line;
  for (auto& c : cmd) line += c + " ";
  logInfo("production job {}: {}", a.jobRunId, line);
  if (auto r = a.prodJob.start(cmd, runDir / "studio_job.log"); !r) {
    a.prodError = r.error().message;
    return false;
  }
  a.prodError.clear();
  a.jobStatus = {};
  a.jobLogTail.clear();
  a.jobUiFrames = 0;
  a.jobMaxFrameDt = 0;
  a.lastPoll = 0;
  return true;
}

void cancelProduction(App& a) {
  if (a.jobRunId.empty()) return;
  a.lastCancel = a.prodJob.cancel(8.0);
  auto st = workflow::readStatus(a.shot.runsDir() / a.jobRunId / "status.json");
  if (!st.terminal()) {  // killed before it could finalise itself: the workflow contract does it
    workflow::Job fin;
    if (fin.start(workflow::markCancelledCommand(a.cfg, a.shot, a.jobRunId), a.shot.runsDir() / a.jobRunId / "studio_job.log"))
      fin.waitFor(30);
  }
  a.jobStatus = workflow::readStatus(a.shot.runsDir() / a.jobRunId / "status.json");
  a.status = std::format("job {} cancelled ({}, {:.1f}s)", a.jobRunId, a.lastCancel.forced ? "forced" : "graceful", a.lastCancel.seconds);
  refreshRuns(a);
}

// Called every UI frame: never blocks (status.json and the log tail are read at most 4 times a second).
void pollProduction(App& a, double dt) {
  if (a.jobRunId.empty()) return;
  bool running = a.prodJob.running();
  if (running) {
    ++a.jobUiFrames;
    a.jobMaxFrameDt = std::max(a.jobMaxFrameDt, dt);
  }
  double t = glfwGetTime();
  if (running && t - a.lastPoll < 0.25) return;
  a.lastPoll = t;
  fs::path runDir = a.shot.runsDir() / a.jobRunId;
  auto st = workflow::readStatus(runDir / "status.json");
  if (st.valid) a.jobStatus = st;
  std::string stage = a.jobStatus.stage.empty() ? "render" : a.jobStatus.stage;
  std::string tail = stage == "prepare" ? "" : workflow::tailFile(runDir / "logs" / (stage + ".log"), 12);
  a.jobLogTail = tail.empty() ? workflow::tailFile(runDir / "studio_job.log", 12) : tail;
  if (running) return;
  // finished
  std::string id = a.jobRunId, kind = a.jobKind;
  if (a.jobStatus.state == "done") {
    a.status = std::format("job {} done", id);
    bool prepared = std::find(a.jobStatus.stagesDone.begin(), a.jobStatus.stagesDone.end(), "prepare") != a.jobStatus.stagesDone.end();
    if (prepared) {  // reload the resolved scene (its packages may have changed)
      double f = a.frame;
      if (loadDocument(a, a.shot.resolvedScene())) a.frame = f;
    }
    if (kind == "render") a.selRunId = id;
  } else {
    a.prodError = a.jobStatus.valid && !a.jobStatus.error.empty()
                      ? a.jobStatus.error
                      : std::format("job exited with code {}: {}", a.prodJob.exitCode(), workflow::tailFile(runDir / "studio_job.log", 6));
    a.status = std::format("job {} {}", id, a.jobStatus.valid ? a.jobStatus.state : "failed");
  }
  a.jobLogTail = workflow::tailFile(runDir / "studio_job.log", 12);
  a.jobRunId.clear();
  refreshRuns(a);
}

const workflow::RunInfo* selectedRun(App& a) {
  for (auto& r : a.runs)
    if (r.id == a.selRunId) return &r;
  return nullptr;
}

// The image of the selected run for the current timeline frame (only frames inside the run's range).
workflow::FrameView updateViewer(App& a) {
  const workflow::RunInfo* run = selectedRun(a);
  if (!run) return {false, false, {}, "no run selected"};
  workflow::FrameView v = workflow::mapFrame(*run, int(std::round(a.frame)));
  if (!v.available) return v;
  std::error_code ec;
  auto stamp = fs::last_write_time(v.image, ec);
  if (v.image != a.viewImage || stamp != a.viewStamp) {
    int w = 0, h = 0;
    auto px = readImageRgb8(v.image, w, h);
    if (!px) return {true, false, v.image, "cannot read " + v.image.string()};
    if (!a.viewTex) glGenTextures(1, &a.viewTex);
    glBindTexture(GL_TEXTURE_2D, a.viewTex);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, px->data());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    a.viewImage = v.image;
    a.viewStamp = stamp;
    a.viewW = w;
    a.viewH = h;
  }
  return v;
}

void productionPanel(App& a) {
  ImGui::Begin("Production");
  if (ImGui::CollapsingHeader("Shots", a.shotMode ? 0 : ImGuiTreeNodeFlags_DefaultOpen)) {
    if (ImGui::Button("Rescan")) a.shots = workflow::discoverShots(a.cfg.root);
    for (size_t i = 0; i < a.shots.size(); ++i) {
      const auto& sh = a.shots[i];
      std::string label = std::format("{}/{}  {}##shot{}", sh.episode, sh.shot, sh.name, i);
      if (ImGui::Selectable(label.c_str(), a.shotMode && a.shot.path == sh.path, ImGuiSelectableFlags_AllowDoubleClick) &&
          !a.prodJob.running())
        openShot(a, sh.path);
    }
  }
  if (!a.shotMode) {
    ImGui::TextDisabled("Open a shot (above or --shot <file>) to prepare and render it.");
    ImGui::End();
    return;
  }
  ImGui::Text("Shot: %s/%s  (%s)", a.shot.episode.c_str(), a.shot.shot.c_str(), a.loaded ? "prepared" : "not prepared");
  ImGui::TextDisabled("Blender: %s  [%s]", a.cfg.blender.empty() ? "(not configured)" : a.cfg.blender.c_str(), a.cfg.blenderSource.c_str());
  if (ImGui::CollapsingHeader("Cast", ImGuiTreeNodeFlags_DefaultOpen)) {
    Json prep = workflow::readPrepareReport(a.shot);
    if (ImGui::BeginTable("cast", 3, ImGuiTableFlags_Borders | ImGuiTableFlags_SizingStretchProp)) {
      ImGui::TableSetupColumn("Character");
      ImGui::TableSetupColumn("Source");
      ImGui::TableSetupColumn("Package");
      ImGui::TableHeadersRow();
      for (const auto& c : a.shot.cast) {
        ImGui::TableNextRow();
        ImGui::TableNextColumn();
        ImGui::TextUnformatted(c.name.c_str());
        ImGui::TableNextColumn();
        const Json pc = prep.is_object() ? prep.value("cast", Json::object()).value(c.name, Json::object()) : Json::object();
        std::string src = pc.contains("source") ? pc["source"].get<std::string>() : (c.sourceKind == "published" ? "published: " : "spec (unpublished build): ") + c.source;
        ImGui::TextWrapped("%s", src.c_str());
        ImGui::TableNextColumn();
        if (pc.contains("package_state"))
          ImGui::TextWrapped("%s (master %s)", pc["package_state"].get<std::string>().c_str(), pc["master_state"].get<std::string>().c_str());
        else
          ImGui::TextDisabled("not prepared");
      }
      ImGui::EndTable();
    }
  }
  bool busy = a.prodJob.running();
  if (ImGui::CollapsingHeader("Render settings", ImGuiTreeNodeFlags_DefaultOpen)) {
    ImGui::DragIntRange2("Frames", &a.settings.frameA, &a.settings.frameB, 1, a.shot.frameStart, a.shot.frameEnd);
    ImGui::SetNextItemWidth(100);
    ImGui::DragInt("W", &a.settings.width, 8, 64, 7680);
    ImGui::SameLine();
    ImGui::SetNextItemWidth(100);
    ImGui::DragInt("H", &a.settings.height, 8, 64, 4320);
    ImGui::SameLine();
    ImGui::SetNextItemWidth(100);
    ImGui::DragInt("Samples##prod", &a.settings.samples, 1, 1, 4096);
    ImGui::TextDisabled("Defaults from the shot's production.render; light_scale %.2f", a.shot.lightScale);
  }
  ImGui::BeginDisabled(busy);
  if (ImGui::Button("Prepare")) startProduction(a, "prepare", a.settings);
  ImGui::SameLine();
  if (ImGui::Button("Render (bake + Blender)")) startProduction(a, "render", a.settings);
  ImGui::EndDisabled();
  ImGui::SameLine();
  ImGui::BeginDisabled(!busy);
  if (ImGui::Button("Cancel")) cancelProduction(a);
  ImGui::EndDisabled();
  if (!a.jobRunId.empty() || a.jobStatus.valid) {
    const auto& st = a.jobStatus;
    ImGui::Text("Job %s: %s  stage %s", st.runId.empty() ? a.jobRunId.c_str() : st.runId.c_str(), st.state.c_str(), st.stage.c_str());
    float frac = st.framesTotal > 0 ? float(st.framesDone) / float(st.framesTotal) : 0.0f;
    std::string over = std::format("{} / {} frames", st.framesDone, st.framesTotal);
    ImGui::ProgressBar(frac, ImVec2(-1, 0), over.c_str());
    ImGui::BeginChild("log", ImVec2(0, 70), ImGuiChildFlags_Borders);
    ImGui::TextUnformatted(a.jobLogTail.c_str());
    ImGui::EndChild();
  }
  if (!a.prodError.empty()) ImGui::TextColored(ImVec4(1, 0.4f, 0.35f, 1), "Error: %s", a.prodError.c_str());
  if (ImGui::CollapsingHeader("Result viewer", ImGuiTreeNodeFlags_DefaultOpen)) {
    workflow::FrameView v = updateViewer(a);
    if (const workflow::RunInfo* run = selectedRun(a)) {
      const auto& st = run->status;
      ImGui::Text("Run %s: %s, frames %d-%d, %dx%d, %d samples, light_scale %.2f, exposure %.2f", run->id.c_str(), st.state.c_str(),
                  st.frameA, st.frameB, st.width, st.height, st.samples, st.lightScale, st.exposureEV);
    }
    ImGui::Text("Timeline frame %d", int(std::round(a.frame)));
    if (v.available && a.viewTex && a.viewW > 0) {
      float avail = ImGui::GetContentRegionAvail().x;
      ImGui::Image(ImTextureID(uintptr_t(a.viewTex)), ImVec2(avail, avail * float(a.viewH) / float(a.viewW)));
      ImGui::TextDisabled("%s", v.image.filename().string().c_str());
    } else {
      ImGui::TextColored(ImVec4(1, 0.8f, 0.4f, 1), "%s", v.message.c_str());
    }
  }
  if (ImGui::CollapsingHeader("Runs", ImGuiTreeNodeFlags_DefaultOpen)) {
    if (ImGui::Button("Refresh runs")) refreshRuns(a);
    ImGui::BeginChild("runs", ImVec2(0, 110), ImGuiChildFlags_Borders);
    for (const auto& r : a.runs) {
      std::string label = std::format("{}{}  {}  frames {}-{}  {}x{}  {} spp##{}", r.id, r.latest ? " (latest)" : "", r.status.state,
                                      r.status.frameA, r.status.frameB, r.status.width, r.status.height, r.status.samples, r.id);
      if (ImGui::Selectable(label.c_str(), r.id == a.selRunId)) a.selRunId = r.id;
    }
    ImGui::EndChild();
  }
  if (a.loaded && ImGui::CollapsingHeader("Shot actions")) {
    Json& acts = doc(a).actions;
    bool changed = false;
    for (size_t i = 0; i < acts.size(); ++i) {
      Json& act = acts[i];
      if (!act.is_object() || !act.contains("start") || !act.contains("end")) continue;
      int se[2] = {act["start"].get<int>(), act["end"].get<int>()};
      std::string label = std::format("{} {} {}##act{}", act.value("type", "?"), act.value("character", ""), act.value("name", ""), i);
      if (ImGui::DragInt2(label.c_str(), se, 1, doc(a).frameStart, doc(a).frameEnd)) {
        act["start"] = se[0];
        act["end"] = std::max(se[0], se[1]);
        changed = true;
      }
    }
    if (changed) {
      if (auto r = a.view.compileActions(); !r) a.status = r.error().message;
      markEdited(a);
    }
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

// ------------------------------------------------------------------ scripted production tests (Xvfb + Mesa)
// --script-production DIR: prepare -> playback check against the bake -> render -> viewer mapping -> screenshots.
// --script-cancel DIR: render, cancel during the Blender render, check processes and earlier runs.
// --script-fail DIR: a render with a missing Blender executable shows its error.
// They drive the same functions as the Production panel buttons; results are written as JSON into DIR.
struct ProdScript {
  std::string mode;  // production / cancel / fail
  fs::path dir;
  int frameA = 5, frameB = 7, width = 320, height = 180, samples = 16;
  int step = 0, wait = 0;
  double t0 = 0;
  Json out = Json::object();
  std::string pendingShot;  // screenshot requested (written after the frame is drawn)
  bool shotWritten = false;
  std::string lastProgress;
  Json progress = Json::array();
  std::set<int> visited;
  std::vector<std::pair<std::string, Json>> earlierRuns;
};

Json v3j(vec3 v) { return Json::array({v.x, v.y, v.z}); }

// Snapshot of a run folder for "earlier runs untouched": every file with size and modification time.
Json folderState(const fs::path& d) {
  Json j = Json::object();
  std::error_code ec;
  for (auto it = fs::recursive_directory_iterator(d, ec); it != fs::recursive_directory_iterator(); ++it) {
    if (!it->is_regular_file()) continue;
    auto t = fs::last_write_time(it->path(), ec).time_since_epoch().count();
    j[fs::relative(it->path(), d).string()] = std::format("{} {}", fs::file_size(it->path(), ec), t);
  }
  return j;
}

std::string psList() {
  std::string out;
  if (FILE* p = ::popen("ps -eo pid,pgid,ppid,stat,args --sort=pid", "r")) {
    char buf[4096];
    while (fgets(buf, sizeof buf, p)) out += buf;
    ::pclose(p);
  }
  return out;
}

bool pngComplete(const fs::path& p) {
  std::ifstream f(p, std::ios::binary);
  char sig[8] = {};
  f.read(sig, 8);
  if (std::memcmp(sig, "\x89PNG\r\n\x1a\n", 8) != 0) return false;
  f.seekg(-8, std::ios::end);
  char tail[4] = {};
  f.read(tail, 4);
  return std::memcmp(tail, "IEND", 4) == 0;
}

// R2: the evaluator the viewport draws from, at given frames, against a bake written by the pipeline.
Json playbackCheck(App& a, const Json& bake) {
  Json res = Json::object();
  std::map<int, const Json*> byFrame;
  for (const auto& fd : bake["frame_data"]) byFrame[fd["frame"].get<int>()] = &fd;
  const Scene& s = doc(a);
  std::vector<int> frames;
  for (int k = 0; k <= 8; ++k) frames.push_back(s.frameStart + (s.frameEnd - s.frameStart) * k / 8);
  frames.insert(frames.end(), {5, 6, 7});
  std::sort(frames.begin(), frames.end());
  frames.erase(std::unique(frames.begin(), frames.end()), frames.end());
  double maxCam = 0, maxSkin = 0, maxMorph = 0;
  Json perFrame = Json::array();
  std::map<std::string, std::vector<vec3>> roots;
  std::map<std::string, std::vector<std::vector<float>>> morphs;
  std::map<std::string, std::vector<std::vector<float>>> skins;
  std::vector<vec3> meshCentroid, camPos, camTgt;
  for (int f : frames) {
    if (!byFrame.count(f)) continue;
    a.frame = f;  // the timeline frame
    auto snap = a.view.evaluate(f);  // what the viewport draws
    vec3 c(0);
    size_t n = 0;
    for (const auto& m : snap->meshes)
      for (const auto& p : m.mesh->positions) c += p, ++n;
    meshCentroid.push_back(n ? c / float(n) : c);
    Json mine = bakeShot(a.view, f, f)["frame_data"][0];
    const Json& ref = *byFrame[f];
    auto diff = [](const Json& x, const Json& y) {
      double d = 0;
      for (size_t i = 0; i < x.size(); ++i) d = std::max(d, std::abs(x[i].get<double>() - y[i].get<double>()));
      return x.size() == y.size() ? d : 1e9;
    };
    double dc = 0;
    for (const char* k : {"position", "target", "up"}) dc = std::max(dc, diff(mine["camera"][k], ref["camera"][k]));
    for (const char* k : {"focalMm", "sensorWidthMm", "fStop", "focusDistance"})
      dc = std::max(dc, std::abs(mine["camera"][k].get<double>() - ref["camera"][k].get<double>()));
    auto vj = [](const Json& v) { return vec3(v[0].get<float>(), v[1].get<float>(), v[2].get<float>()); };
    camPos.push_back(vj(ref["camera"]["position"]));
    camTgt.push_back(vj(ref["camera"]["target"]));
    Json fr = {{"frame", f}, {"camera_max_abs_diff", dc}, {"characters", Json::object()}};
    maxCam = std::max(maxCam, dc);
    for (auto it = ref["characters"].begin(); it != ref["characters"].end(); ++it) {
      double ds = diff(mine["characters"][it.key()]["skin"], it.value()["skin"]);
      double dm = diff(mine["characters"][it.key()]["morphs"], it.value()["morphs"]);
      maxSkin = std::max(maxSkin, ds);
      maxMorph = std::max(maxMorph, dm);
      const Json& sk = it.value()["skin"];
      roots[it.key()].push_back(vec3(sk[12].get<float>(), sk[13].get<float>(), sk[14].get<float>()));
      morphs[it.key()].push_back(it.value()["morphs"].get<std::vector<float>>());
      skins[it.key()].push_back(sk.get<std::vector<float>>());
      fr["characters"][it.key()] = {{"skin_max_abs_diff", ds}, {"morph_max_abs_diff", dm}};
    }
    perFrame.push_back(fr);
  }
  res["frames"] = frames;
  res["per_frame"] = perFrame;
  res["max_abs_diff"] = {{"camera", maxCam}, {"skin_matrices", maxSkin}, {"morph_weights", maxMorph}};
  res["equal_within_1e-6"] = maxCam <= 1e-6 && maxSkin <= 1e-6 && maxMorph <= 1e-6;
  // the animation changes over time as the actions require
  Json change = Json::object();
  for (auto& [name, rs] : roots) {
    float travel = 0;
    for (auto& r : rs) travel = std::max(travel, glm::length(r - rs.front()));
    // largest change of any bone's skinning matrix (gaze / head / limbs), and per-morph weight ranges
    double boneChange = 0;
    for (auto& sk : skins[name])
      for (size_t i = 0; i < sk.size(); ++i) boneChange = std::max(boneChange, double(std::abs(sk[i] - skins[name].front()[i])));
    Json mr = Json::object();
    const Json* ch = nullptr;
    for (const auto& c : bake["characters"])
      if (c["name"] == name) ch = &c;
    for (size_t m = 0; ch && m < (*ch)["morphs"].size(); ++m) {
      float lo = 1e9f, hi = -1e9f;
      for (auto& w : morphs[name]) lo = std::min(lo, w[m]), hi = std::max(hi, w[m]);
      if (hi - lo > 1e-4f) mr[(*ch)["morphs"][m].get<std::string>()] = {lo, hi};
    }
    change[name] = {{"bone0_max_travel_m", travel}, {"max_skin_matrix_change", boneChange}, {"morph_weight_ranges", mr},
                    {"bone0_translation_per_frame", Json::array()}};
    for (auto& r : rs) change[name]["bone0_translation_per_frame"].push_back(v3j(r));
  }
  float meshMove = 0, camMove = 0, tgtMove = 0;
  for (auto& c : meshCentroid) meshMove = std::max(meshMove, glm::length(c - meshCentroid.front()));
  for (auto& c : camPos) camMove = std::max(camMove, glm::length(c - camPos.front()));
  for (auto& c : camTgt) tgtMove = std::max(tgtMove, glm::length(c - camTgt.front()));
  change["camera_target_max_move_m"] = tgtMove;
  change["viewport_mesh_centroid_max_move_m"] = meshMove;
  change["camera_max_move_m"] = camMove;
  res["changes_over_time"] = change;
  return res;
}

void finishScript(App& a, ProdScript& ps) {
  std::error_code ec;
  fs::create_directories(ps.dir, ec);
  std::ofstream(ps.dir / std::format("studio_{}.json", ps.mode)) << ps.out.dump(1);
  logInfo("script {} finished -> {}", ps.mode, (ps.dir / std::format("studio_{}.json", ps.mode)).string());
  glfwSetWindowShouldClose(a.window, 1);
}

void tickScript(App& a, ProdScript& ps) {
  if (!ps.pendingShot.empty()) return;  // wait for the screenshot
  if (ps.wait > 0) {
    --ps.wait;
    return;
  }
  auto jobDone = [&] { return a.jobRunId.empty(); };
  auto runDir = [&](const std::string& id) { return a.shot.runsDir() / id; };
  workflow::RunSettings rs = a.settings;
  rs.frameA = ps.frameA;
  rs.frameB = ps.frameB;
  rs.width = ps.width;
  rs.height = ps.height;
  rs.samples = ps.samples;
  if (ps.step == 0) a.settings = rs;  // the script types its settings into the panel's fields
  std::string id;
  switch (ps.step) {
    case 0: {  // open (done at start-up) -> Prepare
      std::error_code ec;
      fs::create_directories(ps.dir, ec);
      ps.t0 = glfwGetTime();
      ps.out["shot"] = a.shot.path.string();
      ps.out["shots_discovered"] = Json::array();
      for (auto& s : a.shots) ps.out["shots_discovered"].push_back(s.path.string());
      ps.out["prepared_at_open"] = a.loaded;
      ps.out["blender"] = a.cfg.blender;
      ps.out["gl_renderer"] = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
      ps.out["gl_version"] = reinterpret_cast<const char*>(glGetString(GL_VERSION));
      if (ps.mode == "fail") {
        a.cfg.blender = "/nonexistent/blender";
        ps.step = 20;
        return;
      }
      startProduction(a, "prepare", rs);
      ps.out["prepare_run"] = a.jobRunId;
      ps.step = 1;
      return;
    }
    case 1:
      if (!jobDone()) return;
      ps.out["prepare_status"] = a.jobStatus.state;
      ps.out["prepare_report"] = Json::parse(std::ifstream(runDir(ps.out["prepare_run"]) / "prepare.json"), nullptr, false);
      ps.out["loaded_after_prepare"] = a.loaded;
      ps.out["characters_imported"] = Json::array();
      for (auto& c : a.view.characters()) ps.out["characters_imported"].push_back(c.imported);
      if (!a.loaded || a.jobStatus.state != "done") return finishScript(a, ps);
      ps.step = ps.mode == "cancel" ? 10 : 2;
      return;
    case 2: {  // a bake of the full shot range for the playback check (the pipeline's engine bake)
      workflow::RunSettings b = rs;
      b.stages = {"bake"};
      b.frameA = a.shot.frameStart;
      b.frameB = a.shot.frameEnd;
      startProduction(a, "bake", b);
      ps.out["playback_bake_run"] = a.jobRunId;
      ps.step = 3;
      return;
    }
    case 3: {
      if (!jobDone()) return;
      Json bake = Json::parse(std::ifstream(runDir(ps.out["playback_bake_run"]) / "bake.json"), nullptr, false);
      if (bake.is_discarded()) {
        ps.out["error"] = "no bake";
        return finishScript(a, ps);
      }
      ps.out["playback_check"] = playbackCheck(a, bake);
      a.frame = a.shot.frameStart;
      a.playing = true;
      ps.visited.clear();
      ps.wait = 0;
      ps.t0 = glfwGetTime();
      ps.step = 4;
      return;
    }
    case 4:  // timeline playback through the main loop (the same path as the Play button)
      ps.visited.insert(int(std::floor(a.frame)));
      if (glfwGetTime() - ps.t0 < 3.0) return;
      a.playing = false;
      ps.out["playback"] = {{"seconds", glfwGetTime() - ps.t0}, {"distinct_frames_shown", ps.visited.size()},
                            {"first", *ps.visited.begin()}, {"last", *ps.visited.rbegin()}};
      ps.step = 5;
      return;
    case 5:
      startProduction(a, "render", rs);
      ps.out["render_run"] = a.jobRunId;
      ps.out["render_command"] = Json::array();
      for (auto& c : workflow::buildCommand(a.cfg, a.shot, a.jobRunId, rs)) ps.out["render_command"].push_back(c);
      ps.t0 = glfwGetTime();
      ps.step = 6;
      return;
    case 6: {
      std::string p = std::format("{} {} {}", a.jobStatus.state, a.jobStatus.stage, a.jobStatus.framesDone);
      if (p != ps.lastProgress && a.jobStatus.valid) {
        ps.lastProgress = p;
        ps.progress.push_back({{"t", glfwGetTime() - ps.t0}, {"state", a.jobStatus.state}, {"stage", a.jobStatus.stage},
                               {"frames_done", a.jobStatus.framesDone}, {"frames_total", a.jobStatus.framesTotal}});
      }
      if (!jobDone()) return;
      ps.out["render_progress"] = ps.progress;
      ps.out["render_status"] = a.jobStatus.state;
      ps.out["render_error"] = a.prodError;
      ps.out["responsiveness"] = {{"ui_frames_during_job", a.jobUiFrames}, {"max_ui_frame_s", a.jobMaxFrameDt},
                                  {"job_s", glfwGetTime() - ps.t0}};
      ps.step = 7;
      return;
    }
    case 7: {  // viewer mapping
      a.selRunId = ps.out["render_run"];
      refreshRuns(a);
      const workflow::RunInfo* run = selectedRun(a);
      if (!run) return finishScript(a, ps);
      ps.out["viewer_run_settings"] = {{"frames", {run->status.frameA, run->status.frameB}},
                                       {"resolution", {run->status.width, run->status.height}},
                                       {"samples", run->status.samples}, {"light_scale", run->status.lightScale},
                                       {"exposure_ev", run->status.exposureEV}};
      Json m = Json::array();
      for (int f : {a.shot.frameStart, ps.frameA - 1, ps.frameA, ps.frameA + 1, ps.frameB, ps.frameB + 1, a.shot.frameEnd}) {
        auto v = workflow::mapFrame(*run, f);
        m.push_back({{"frame", f}, {"in_range", v.inRange}, {"available", v.available}, {"image", v.image.filename().string()},
                     {"message", v.message}});
      }
      ps.out["viewer_mapping"] = m;
      a.frame = ps.frameA + 1;
      a.needEval = true;
      ps.wait = 5;
      ps.step = 8;
      return;
    }
    case 8:
      ps.out["screenshot_rendered_frame"] = int(a.frame);
      ps.pendingShot = (ps.dir / "viewer_rendered_frame.png").string();
      ps.step = 9;
      return;
    case 9:
      a.frame = std::min(a.shot.frameEnd, ps.frameB + 13);
      a.needEval = true;
      ps.wait = 5;
      ps.step = 100;
      return;
    case 100:
      ps.out["screenshot_not_rendered_frame"] = int(a.frame);
      ps.pendingShot = (ps.dir / "viewer_not_rendered_frame.png").string();
      ps.step = 101;
      return;
    case 101:
      return finishScript(a, ps);
    // ---- cancel test
    case 10: {
      refreshRuns(a);
      ps.out["latest_before"] = workflow::latestRunId(a.shot);
      for (auto& r : a.runs) ps.earlierRuns.push_back({r.id, folderState(r.dir)});
      ps.out["earlier_runs"] = Json::array();
      for (auto& [rid, st] : ps.earlierRuns) ps.out["earlier_runs"].push_back(rid);
      workflow::RunSettings c = rs;
      c.frameA = a.shot.frameStart;  // long enough to cancel inside the Blender render
      c.frameB = a.shot.frameEnd;
      startProduction(a, "render", c);
      ps.out["cancel_run"] = a.jobRunId;
      ps.t0 = glfwGetTime();
      ps.step = 11;
      return;
    }
    case 11: {
      if (jobDone()) {
        ps.out["error"] = "job finished before it could be cancelled";
        return finishScript(a, ps);
      }
      if (!(a.jobStatus.stage == "render" && a.jobStatus.framesDone >= 1)) return;
      id = a.jobRunId;
      pid_t pg = a.prodJob.pgid();
      Json before = Json::array();
      for (auto& p : workflow::processGroupMembers(pg)) before.push_back({{"pid", p.pid}, {"cmd", p.cmd}});
      std::ofstream(ps.dir / "processes_before_cancel.txt") << psList();
      ps.out["process_group"] = pg;
      ps.out["group_before_cancel"] = before;
      ps.out["frames_done_at_cancel"] = a.jobStatus.framesDone;
      cancelProduction(a);
      std::string after = psList();
      std::ofstream(ps.dir / "processes_after_cancel.txt") << after;
      Json groupAfter = Json::array();
      for (auto& p : workflow::processGroupMembers(pg)) groupAfter.push_back({{"pid", p.pid}, {"cmd", p.cmd}});
      // survivors: any process whose command line names this run (run_shot.py --run-dir <id>, Blender --bake
      // .../runs/<id>/bake.json, ffmpeg ...), and every process of the job's group from before the cancel
      Json survivors = Json::array();
      std::istringstream lines(after);
      for (std::string l; std::getline(lines, l);)
        if (l.find(id) != std::string::npos && l.find(" ps -eo") == std::string::npos) survivors.push_back(l);
      for (auto& b : before) {
        bool alive = ::kill(b["pid"].get<pid_t>(), 0) == 0;
        if (alive) survivors.push_back(std::format("pid {} still exists", b["pid"].get<int>()));
      }
      ps.out["group_after_cancel"] = groupAfter;
      ps.out["surviving_processes"] = survivors;
      ps.out["cancel_result"] = {{"graceful", a.lastCancel.graceful}, {"forced", a.lastCancel.forced},
                                 {"group_gone", a.lastCancel.groupGone}, {"seconds", a.lastCancel.seconds}};
      auto st = workflow::readStatus(runDir(id) / "status.json");
      ps.out["status_after_cancel"] = Json::parse(std::ifstream(runDir(id) / "status.json"), nullptr, false);
      Json frames = Json::array();
      bool allComplete = true;
      std::error_code ec;
      for (auto& e : fs::directory_iterator(runDir(id) / "render", ec))
        if (e.path().extension() == ".png") {
          bool ok = pngComplete(e.path());
          allComplete &= ok;
          frames.push_back({{"file", e.path().filename().string()}, {"complete", ok}});
        }
      ps.out["frames_on_disk"] = frames;
      ps.out["all_frames_on_disk_complete"] = allComplete;
      ps.out["state_cancelled"] = st.state == "cancelled";
      bool same = true;
      for (auto& [rid, state] : ps.earlierRuns) same &= folderState(runDir(rid)) == state;
      ps.out["earlier_runs_unchanged"] = same;
      ps.out["latest_after"] = workflow::latestRunId(a.shot);
      ps.out["latest_unchanged"] = ps.out["latest_after"] == ps.out["latest_before"];
      ps.out["no_orphans"] = groupAfter.empty() && survivors.empty();
      ps.wait = 5;
      ps.step = 12;
      return;
    }
    case 12:
      ps.pendingShot = (ps.dir / std::format("studio_after_{}.png", ps.mode)).string();
      ps.step = 101;
      return;
    // ---- failure test
    case 20:
      startProduction(a, "render", rs);
      ps.out["fail_run"] = a.jobRunId;
      ps.step = 21;
      return;
    case 21:
      if (!jobDone()) return;
      ps.out["status"] = a.jobStatus.state;
      ps.out["error_shown"] = a.prodError;
      ps.wait = 5;
      ps.step = 12;
      ps.mode = "fail";
      return;
  }
}

}  // namespace

int main(int argc, char** argv) {
  fs::path scenePath = "content/scenes/milestone01_classroom.scene.json";
  std::string screenshot;
  bool scriptHairEdit = false, scriptVerify = false;
  int screenshotAfter = 30;
  bool autoRender = false;
  int renderW = 0, renderH = 0, renderSpp = 0;
  fs::path shotArg;
  std::string blenderArg;
  ProdScript script;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--screenshot" && i + 1 < argc) screenshot = argv[++i];
    else if (arg == "--screenshot-after" && i + 1 < argc) screenshotAfter = std::stoi(argv[++i]);
    else if (arg == "--auto-render") autoRender = true;
    else if (arg == "--render-size" && i + 2 < argc) { renderW = std::stoi(argv[++i]); renderH = std::stoi(argv[++i]); }
    else if (arg == "--render-spp" && i + 1 < argc) renderSpp = std::stoi(argv[++i]);
    else if (arg == "--script-hair-edit") scriptHairEdit = true;  // automated editor test (same actions as the buttons)
    else if (arg == "--script-verify") scriptVerify = true;
    // production workflow (T-001)
    else if (arg == "--shot" && i + 1 < argc) shotArg = argv[++i];
    else if (arg == "--blender" && i + 1 < argc) blenderArg = argv[++i];
    else if ((arg == "--script-production" || arg == "--script-cancel" || arg == "--script-fail") && i + 1 < argc) {
      script.mode = arg.substr(9);
      script.dir = argv[++i];
    }
    else if (arg == "--script-frames" && i + 1 < argc) {
      std::string r = argv[++i];
      size_t dash = r.find('-');
      script.frameA = std::stoi(r.substr(0, dash));
      script.frameB = dash == std::string::npos ? script.frameA : std::stoi(r.substr(dash + 1));
    }
    else if (arg == "--script-size" && i + 2 < argc) { script.width = std::stoi(argv[++i]); script.height = std::stoi(argv[++i]); }
    else if (arg == "--script-samples" && i + 1 < argc) script.samples = std::stoi(argv[++i]);
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
  logInfo("OpenGL: {} / {}", reinterpret_cast<const char*>(glGetString(GL_RENDERER)), reinterpret_cast<const char*>(glGetString(GL_VERSION)));

  // production workflow: the pipeline of this source tree, Blender from --blender / PLUSH_BLENDER / settings file
  workflow::becomeSubreaper();  // a cancelled job's descendants are reaped here (no zombies, no orphans)
  app.cfg = workflow::makeConfig(PLUSH_SOURCE_DIR, PLUSH_RENDER_CLI, blenderArg);
  app.shots = workflow::discoverShots(app.cfg.root);
  if (!shotArg.empty()) {
    if (!openShot(app, fs::absolute(shotArg))) return 1;
  } else {
    if (!loadDocument(app, scenePath)) return 1;
    app.frame = doc(app).frameStart;
  }
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
  if (!script.mode.empty() && !app.shotMode) {
    logError("--script-{} needs --shot", script.mode);
    return 1;
  }

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
    double dt = now - last;
    last = now;
    pollProduction(app, dt);
    if (!script.mode.empty()) tickScript(app, script);
    if (app.needEval && app.loaded) {
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
        if (ImGui::MenuItem("Save scene", "Ctrl+S")) saveDocument(app);
        if (ImGui::MenuItem("Quit")) glfwSetWindowShouldClose(app.window, 1);
        ImGui::EndMenu();
      }
      ImGui::TextDisabled("  %s  |  %s", app.shotMode ? app.shot.name.c_str() : doc(app).name.c_str(), app.status.c_str());
      ImGui::EndMainMenuBar();
    }
    if (io.KeyCtrl && ImGui::IsKeyPressed(ImGuiKey_S)) saveDocument(app);
    ImGui::SetNextWindowPos(ImVec2(0, 20), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(260, 640), ImGuiCond_FirstUseEver);
    outliner(app);
    ImGui::SetNextWindowPos(ImVec2(260, 20), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(900, 640), ImGuiCond_FirstUseEver);
    viewport(app);
    // Layout of the new Production panel: in a plain scene it is a tab behind Render (the existing layout stays as
    // it was); in a shot the right column holds Production, Inspector and Render as tabs, Production in front.
    static int layout = 0;  // 0 none, 1 scene, 2 shot
    static int focusRender = 0, focusProduction = 0;
    auto dockColumn = [](const char* id, ImVec2 pos, ImVec2 size, std::initializer_list<const char*> windows) {
      ImGuiID node = ImGui::GetID(id);
      if (ImGui::DockBuilderGetNode(node)) return;
      ImGui::DockBuilderAddNode(node, ImGuiDockNodeFlags_None);
      ImGui::DockBuilderSetNodePos(node, pos);
      ImGui::DockBuilderSetNodeSize(node, size);
      for (const char* w : windows) ImGui::DockBuilderDockWindow(w, node);
      ImGui::DockBuilderFinish(node);
    };
    if (!app.shotMode && layout == 0) {
      layout = 1;
      focusRender = 3;  // the docked tab is selected once the dock node exists
      dockColumn("SceneRenderColumn", ImVec2(1160, 360), ImVec2(440, 540), {"Render", "Production"});
    }
    if (app.shotMode && layout != 2) {
      layout = 2;
      focusProduction = 3;
      dockColumn("ShotRightColumn", ImVec2(1160, 20), ImVec2(440, 880), {"Inspector", "Render", "Production"});
    }
    ImGui::SetNextWindowPos(ImVec2(1160, 20), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(440, 340), ImGuiCond_FirstUseEver);
    inspector(app);
    ImGui::SetNextWindowPos(ImVec2(1160, 360), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(440, 540), ImGuiCond_FirstUseEver);
    if (focusRender > 0 && focusRender-- == 1) ImGui::SetNextWindowFocus();
    renderPanel(app);
    ImGui::SetNextWindowPos(ImVec2(1160, 360), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(440, 540), ImGuiCond_FirstUseEver);
    if (focusProduction > 0 && focusProduction-- == 1) ImGui::SetNextWindowFocus();
    productionPanel(app);
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
    auto capture = [&](const std::string& path) {
      std::vector<uint8_t> px(size_t(fbw) * size_t(fbh) * 3), flipped(px.size());
      glPixelStorei(GL_PACK_ALIGNMENT, 1);
      glReadPixels(0, 0, fbw, fbh, GL_RGB, GL_UNSIGNED_BYTE, px.data());
      for (int y = 0; y < fbh; ++y) std::memcpy(&flipped[size_t(y) * size_t(fbw) * 3], &px[size_t(fbh - 1 - y) * size_t(fbw) * 3], size_t(fbw) * 3);
      (void)writePng(path, fbw, fbh, flipped);
      logInfo("screenshot written to {}", path);
    };
    if (!script.pendingShot.empty()) {
      std::error_code ec;
      fs::create_directories(fs::path(script.pendingShot).parent_path(), ec);
      capture(script.pendingShot);
      script.pendingShot.clear();
    }
    if (!screenshot.empty() && script.mode.empty() && ++frameCounter >= screenshotAfter &&
        (!autoRender || (!app.job.running && app.job.samples > 0))) {
      capture(screenshot);
      glfwSetWindowShouldClose(app.window, 1);
    }
    glfwSwapBuffers(app.window);
  }
  if (app.prodJob.running()) app.prodJob.cancel(8.0);
  app.job.stop();
  ImGui_ImplOpenGL3_Shutdown();
  ImGui_ImplGlfw_Shutdown();
  ImGui::DestroyContext();
  glfwDestroyWindow(app.window);
  glfwTerminate();
  return 0;
}
