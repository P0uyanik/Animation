// Imported characters: rigged meshes produced outside the engine (the charsys Blender pipeline,
// pipeline/charsys/export_engine.py) loaded into the engine's own Skeleton / CharacterRig structures, so every
// existing behaviour (actions, life layer, constraints, skinning, morphs) runs on them unchanged.
// Package format: docs/ENGINE_CHARACTER_PACKAGE.md. The loader is profile-agnostic: it checks package
// consistency only; which roles a character must have is decided by its rig profile at export time.
#pragma once
#include <filesystem>
#include <string>
#include <vector>

#include "model/character.h"

namespace plush {

struct ImportedCharacter {
  CharacterAsset asset;  // name, skeleton (role bones carry engine role names), materials; no SDF parts
  CharacterRig rig;      // skinned meshes and morph targets
  std::string profile, kind;
  std::vector<std::string> rolesPresent, rigSpecificBones;
  Json capabilities;     // data availability per engine behaviour (as exported)
  std::string handFrameSource[2];  // L, R: "metadata", "derived" (from finger geometry) or "none" (no fingers)
};

// True if the file is an imported-character manifest ("format": "plush.imported_character").
bool isImportedCharacter(const std::filesystem::path& manifest);
Result<ImportedCharacter> loadImportedCharacter(const std::filesystem::path& manifest);

}  // namespace plush
