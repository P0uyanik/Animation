#include "model/imported_character.h"

#include <array>
#include <cstring>
#include <fstream>

namespace plush {
namespace {

struct Blob {
  std::vector<char> bytes;
  // An array of `count` scalars of `dtype`, read as count / components elements of T (T = components scalars).
  template <class T>
  Result<std::vector<T>> array(const Json& a, const char* dtype, size_t components) const {
    if (!a.is_object() || a.value("dtype", std::string()) != dtype) return fail(std::string("package: expected dtype ") + dtype);
    const size_t off = a.value("offset", size_t(0)), count = a.value("count", size_t(0));
    const size_t elems = count / components;
    if (count % components != 0 || off + elems * sizeof(T) > bytes.size()) return fail("package: array out of range");
    std::vector<T> out(elems);
    if (elems) std::memcpy(static_cast<void*>(out.data()), bytes.data() + off, elems * sizeof(T));
    return out;
  }
};

}  // namespace

bool isImportedCharacter(const std::filesystem::path& manifest) {
  auto text = readTextFile(manifest);
  if (!text) return false;
  Json j = Json::parse(*text, nullptr, false);
  return j.is_object() && j.value("format", std::string()) == "plush.imported_character";
}

Result<ImportedCharacter> loadImportedCharacter(const std::filesystem::path& manifest) {
  auto text = readTextFile(manifest);
  if (!text) return std::unexpected(text.error());
  Json j = Json::parse(*text, nullptr, false);
  if (!j.is_object() || j.value("format", std::string()) != "plush.imported_character")
    return fail("not an imported character package: " + manifest.string());
  if (j.value("version", 0) != 1) return fail("unsupported imported character version");
  Blob blob;
  {
    std::ifstream f(manifest.parent_path() / "geometry.bin", std::ios::binary);
    if (!f) return fail("package: geometry.bin missing");
    blob.bytes.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    if (blob.bytes.size() != j["files"]["geometry.bin"].value("bytes", size_t(0))) return fail("package: geometry.bin size mismatch");
  }
  ImportedCharacter ic;
  ic.asset.name = j.value("name", std::string("imported"));
  ic.profile = j["profile"].value("name", std::string());
  ic.kind = j["profile"].value("kind", std::string());
  ic.rolesPresent = j.value("roles_present", std::vector<std::string>{});
  ic.rigSpecificBones = j.value("rig_specific_bones", std::vector<std::string>{});
  ic.capabilities = j.value("capabilities", Json::object());
  // Skeleton: parents precede children (checked).
  for (const Json& b : j.at("skeleton")) {
    Bone bone;
    bone.name = b.at("name").get<std::string>();
    if (ic.asset.skeleton.find(bone.name) >= 0) return fail("package: duplicate bone " + bone.name);
    if (!b["parent"].is_null()) {
      bone.parent = ic.asset.skeleton.find(b["parent"].get<std::string>());
      if (bone.parent < 0) return fail("package: parent after child for bone " + bone.name);
    }
    auto h = b.at("head");
    bone.head = vec3(h[0].get<float>(), h[1].get<float>(), h[2].get<float>());
    ic.asset.skeleton.bones.push_back(bone);
  }
  const int boneCount = int(ic.asset.skeleton.bones.size());
  for (const Json& m : j.value("materials", Json::array())) {
    auto mat = materialFromJson(m);
    if (!mat) return std::unexpected(mat.error());
    ic.asset.materials.push_back(*mat);
  }
  for (const Json& m : j.at("meshes")) {
    SkinnedMesh sm;
    sm.part = m.value("part", std::string());
    sm.material = m.value("material", std::string());
    auto pos = blob.array<vec3>(m["positions"], "float32", 3);
    auto nrm = blob.array<vec3>(m["normals"], "float32", 3);
    auto idx = blob.array<uint32_t>(m["indices"], "uint32", 1);
    auto jnt = blob.array<std::array<uint16_t, 4>>(m["joints"], "uint16", 4);
    auto wgt = blob.array<vec4>(m["weights"], "float32", 4);
    if (!pos || !nrm || !idx || !jnt || !wgt) return fail("package: bad mesh arrays in " + sm.part);
    const size_t n = pos->size();
    if (nrm->size() != n || jnt->size() != n || wgt->size() != n || idx->size() % 3) return fail("package: inconsistent mesh " + sm.part);
    for (uint32_t i : *idx)
      if (i >= n) return fail("package: index out of range in " + sm.part);
    sm.rest.positions = std::move(*pos);
    sm.rest.normals = std::move(*nrm);
    sm.rest.indices = std::move(*idx);
    sm.joints.resize(n);
    sm.weights = std::move(*wgt);
    for (size_t i = 0; i < n; ++i) {
      for (int k = 0; k < 4; ++k) {
        int b = (*jnt)[i][size_t(k)];
        if (b >= boneCount) return fail("package: joint index out of range in " + sm.part);
        sm.joints[i][k] = b;
      }
    }
    ic.rig.meshes.push_back(std::move(sm));
  }
  for (const Json& m : j.value("morphs", Json::array())) {
    MorphTarget mt;
    mt.name = m.at("name").get<std::string>();
    mt.mesh = m.at("mesh").get<int>();
    if (mt.mesh < 0 || mt.mesh >= int(ic.rig.meshes.size())) return fail("package: morph mesh out of range");
    auto v = blob.array<uint32_t>(m["vertices"], "uint32", 1);
    auto d = blob.array<vec3>(m["dpos"], "float32", 3);
    if (!v || !d || v->size() != d->size()) return fail("package: bad morph " + mt.name);
    for (uint32_t i : *v)
      if (i >= ic.rig.meshes[size_t(mt.mesh)].rest.positions.size()) return fail("package: morph vertex out of range");
    mt.vertices = std::move(*v);
    mt.dpos = std::move(*d);
    mt.dnrm.assign(mt.dpos.size(), vec3(0));
    ic.rig.morphs.push_back(std::move(mt));
  }
  return ic;
}

}  // namespace plush
