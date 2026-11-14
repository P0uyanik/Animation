#pragma once
// Shot bake: the engine's evaluated animation of a shot in a renderer-neutral interchange format
// ("plush.shot_bake", version 1), so a production renderer (Blender) can render exactly what the engine animated.
// Per frame: camera; per imported character: deform-bone world matrices (engine axes) and morph control weights.
// Static: lights and box objects. Character placement is inside the bone matrices. Characters that are not
// imported packages (engine SDF characters) are listed with "supported": false and no data.
#include <filesystem>

#include "scene/scene.h"

namespace plush {

Json bakeShot(const SceneEvaluator& evaluator, int frameA, int frameB);

}  // namespace plush
