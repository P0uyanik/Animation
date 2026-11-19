// Procedural texture colour at a rest-space point, for the studio's OpenGL viewport preview (T-142).
#pragma once
#include "geom/geometry.h"

namespace plush::studio {

vec3 evalTexture(const Material& m, vec3 pref);

}  // namespace plush::studio
