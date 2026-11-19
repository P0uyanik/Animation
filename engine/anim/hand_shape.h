// Hand-shape table (T-051, docs/architecture/INTERACTION_AFFORDANCES.md sections 2.3 and 5): named hand poses in
// content/hand_shapes/*.json (plush.hand_shape/1) - the grasp shapes a grasp site names (wrap, pinch, palm, hook,
// cradle), the relaxed idle hand and gesture hands (point, count_1..3, chin_touch). A shape is data on top of the
// engine's HandPose: the approach (open) pose, the held pose, which digits the contact search closes and the thumb
// mode. Shapes are shared: no character names or dimensions; a character's bias (e.g. a curlier rest hand) comes
// only from its personality profile, applied with biased().
//
// File (one shape per file, `<id>.hand_shape.json`):
//   {"format": "plush.hand_shape", "version": 1, "id": "pinch", "kind": "grasp" | "rest" | "gesture",
//    "description": "...",
//    "approach": {pose},                 // required for kind "grasp": the open hand before contact
//    "pose": {pose},                     // the held / gesture pose (grasp: the pose the search starts from)
//    "search": "all" | "pinch" | "none", // grasp only: every digit, index + thumb, or no contact search
//    "thumb": "opposed" | "along" | "tucked",  // grasp only (default opposed)
//    "pinch_radius": 0.01,               // search "pinch": the sphere the index and thumb close on (m)
//    "palm": "facing" | "up",            // grasp only: palm towards the object (default) or under it (cradle)
//    "stagger": 1}                       // optional: frames between fingers closing (index -> little) / opening
//   pose = {"curl": 0..1, "thumb": 0..1, "spread": -1..1, "index": 0..1?, "thumb_opposition": 0..1?,
//           "fingers": {"index" | "middle" | "ring" | "little": {"curl": 0..1, "spread": -1..1}}?}
// Unknown keys are load errors (a per-character field cannot slip in).
#pragma once
#include <array>
#include <filesystem>
#include <map>
#include <optional>
#include <string>

#include "anim/animation.h"
#include "geom/json_io.h"

namespace plush {

struct HandShapePose {
  float curl = 0.25f, thumb = 0.15f, spread = 0.0f;
  std::optional<float> index;                 // index curl (as HandPose::index)
  std::array<std::optional<vec2>, 4> fingers{};  // (curl, spread) per finger k = 0 little .. 3 index
  std::optional<float> thumbOpposition;
  // The engine hand pose (no grasp): curl / thumb / spread / index, per-finger and thumb overrides.
  HandPose handPose() const;
};

enum class HandShapeSearch { All, Pinch, None };

struct HandShape {
  std::string id, kind, description;  // kind: "grasp" | "rest" | "gesture"
  std::optional<HandShapePose> approach;
  HandShapePose pose;
  HandShapeSearch search = HandShapeSearch::None;
  HandPose::Thumb thumb = HandPose::Thumb::Opposed;
  std::optional<float> pinchRadius;
  bool palmUp = false;
  float stagger = 0;  // frames; 0 = none
  std::filesystem::path path;
};

Result<HandShape> handShapeFromJson(const Json& j, const std::string& id = {});
Result<HandShape> loadHandShape(const std::filesystem::path& file);

struct HandShapeTable {
  std::map<std::string, HandShape> shapes;
  const HandShape* find(const std::string& id) const;
};
// Every *.hand_shape.json in `dir`; ids must be unique and match the file name.
Result<HandShapeTable> loadHandShapeTable(const std::filesystem::path& dir);
// content/hand_shapes of the first ancestor of `from` that has one (empty if none).
std::filesystem::path findHandShapeDir(const std::filesystem::path& from);

// A shape with the personality's rest-curl bias added to its pose (and approach) curls, clamped to 0..1.
HandShape biased(const HandShape& shape, float restCurlBias);

// Keys a shape onto one hand's tracks at `frame`: `hand` is the hand track ("<prefix>hand.L"); writes hand.<s>
// (curl, thumb, spread), .index, .f<k> (curl, spread, free) and .thumb (opposition, curl) where the shape sets them,
// and .stagger when it asks for one. approach = the shape's approach pose instead of its held pose. A pinch keys its
// non-index fingers free (out of the contact search). Grasp geometry (.grasp, .graspRadius, ...) is the caller's.
void keyHandShape(Clip& clip, const std::string& hand, double frame, const HandShape& shape, bool approach = false,
                  Interp interp = Interp::Smooth);

}  // namespace plush
