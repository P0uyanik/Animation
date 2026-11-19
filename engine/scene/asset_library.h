// Reusable prop assets. plush.asset/1 describes source geometry, material presets,
// interaction sockets and an optional coarse collision proxy.
#pragma once

#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "geom/json_io.h"

namespace plush {

struct AssetTransform {
  vec3 translation{0};
  vec3 rotationDeg{0};  // XYZ Euler angles; X is applied first.
  vec3 scale{1};
};

mat4 assetTransformMatrix(const AssetTransform& transform);
Result<AssetTransform> assetTransformFromJson(const Json& json, std::string_view context = "transform");
Json assetTransformToJson(const AssetTransform& transform);

struct AssetMeshSource {
  enum class Kind { File, Primitive };
  enum class Primitive { Box, Sphere, Cylinder };

  Kind kind = Kind::File;
  std::filesystem::path path;
  std::string object;

  Primitive primitive = Primitive::Box;
  vec3 size{1};  // box dimensions in source units
  float radius = 0.5f;
  float height = 1.0f;  // cylinder height in source units
};

struct AssetCollisionProxy {
  enum class Type { Box, Sphere, Capsule };

  Type type = Type::Box;
  AssetTransform transform;
  vec3 size{1};
  float radius = 0.5f;
  float height = 1.0f;  // capsule tip-to-tip height
};

// Object affordances (T-112a, docs/architecture/INTERACTION_AFFORDANCES.md 2.2): how a prop is held, carried and put
// down. Optional; read only by the verb expander (scene/verbs.h), never by the primitive interaction actions.
struct GraspSite {
  std::string id;
  std::string socket;          // an existing socket of the asset (palm contact point and frame)
  std::string hand = "any";    // "L" | "R" | "any"
  std::string shape = "wrap";  // "wrap" | "pinch" | "palm" | "hook" | "cradle"
  std::optional<vec3> approach;  // prop-frame direction the palm comes from (unit)
  std::optional<float> aperture;  // open hand width before contact (m)
  bool turnable = false;
  std::string thumb;              // fingers.thumb: "" | "opposed" | "along" | "tucked" (read by T-051 only)
  std::optional<vec2> band;       // fingers.band: contact band along the grasp axis (m, prop frame)
};
struct GraspSet {
  std::string id;
  std::vector<std::string> sites;  // grasp site ids, one per hand
  int simultaneousFrames = 2;      // contacts of a two-site set at most this far apart
};
struct PropAffordances {
  std::string sizeClass;               // "hand" | "small" | "medium" | "large"; "" = derived when needed
  std::string weightClass = "light";   // "light" | "medium" | "heavy"
  std::optional<float> massKg;
  std::string hands = "either";        // "one" | "two" | "either"
  std::string pivotSocket;             // pivot: a socket name, or
  std::optional<vec3> pivotPoint;      // a prop-frame point
  struct Upright {
    vec3 axis{0, 1, 0};  // prop frame, unit
    float maxTiltDeg = 15;
  };
  std::optional<Upright> upright;
  std::vector<GraspSite> sites;
  std::vector<GraspSet> sets;
  std::vector<std::string> handoverGive, handoverReceive;  // grasp set ids
  struct Place {
    std::string socket = "place";
    vec3 surfaceNormal{0, 1, 0};
    std::string settle = "rigid";  // "rigid" | "soft"
  };
  std::optional<Place> place;
  struct PushPull {
    vec3 axis{0, 0, 1};
    std::vector<std::string> sites;
    std::string friction = "slide";  // "slide" | "tip"
  };
  std::optional<PushPull> pushPull;
  std::string deform = "rigid";  // "rigid" | "squash" | "bend" | "fold" (only rigid is supported by the verbs)
  float squash = 0;
  // Non-empty: the block is present but invalid. The asset still loads (nothing but a verb action reads the block);
  // a verb action on this prop fails with this message.
  std::string error;

  const GraspSite* site(const std::string& id) const;
  const GraspSet* set(const std::string& id) const;
};
// Parses and validates an "affordances" block against the asset's sockets (design 2.2 rules).
Result<PropAffordances> affordancesFromJson(const Json& json, const std::map<std::string, AssetTransform>& sockets,
                                            std::string_view context = "affordances");

struct PropAsset {
  std::string id;
  int version = 1;
  std::string licence;
  std::string attribution;
  AssetMeshSource mesh;
  std::vector<std::string> materialPresets;
  float scaleMetres = 1.0f;  // metres per source unit
  std::map<std::string, AssetTransform> sockets;
  std::optional<AssetCollisionProxy> collision;
  std::optional<PropAffordances> affordances;  // T-112a (a present but invalid block: affordances->error is set)
};

Result<PropAsset> assetFromJson(const Json& json);
Result<PropAsset> loadAsset(const std::filesystem::path& path);

}  // namespace plush
