"""Spec-value suggestions from measured fidelity ratios (T-032 step 5). SUGGESTIONS ONLY: nothing is ever written
to a spec; a person decides, edits a new spec version and re-runs the tool.

Proportions: value x (reference / render) of the matching measured ratio (first-order, one parameter at a time).
Colours: the current base sRGB moved in Lab by (reference median - render median) of that region (first-order; the
render pipeline is not linear, so iterate and re-measure). Spec paths are looked up in the known spec schemas
(face_generic / garment/1 / material assignments, and the legacy body_v6 fields); missing paths give no suggestion."""
import copy
import json

import numpy as np

import metrics as M

PROPORTION_PATHS = {
    "eye_width_to_head": ["face.eyes.radius_m", "proportions.eye_radius_m"],
    "eye_spacing_to_head": ["body.params.eyes.x", "proportions.eye_x_m"],
    "arm_length": ["body.params.arm.upper_len", "body.params.arm.fore_len"],
    "shoulder_width": ["body.params.shoulder.joint_x", "proportions.shoulder_half_width_m"],
}
MIN_REL = {"eye_width_to_head": 0.08, "eye_spacing_to_head": 0.06, "arm_length": 0.06, "shoulder_width": 0.06}


def deep_merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        else:
            a[k] = v
    return a


def get(spec, path):
    cur = spec
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def colour_paths(spec, region):
    """[(path, current sRGB)] for a region name such as garment:vest, hair, skin_face."""
    out = []
    item = region.split(":", 1)[1] if ":" in region else region
    if region.startswith("skin"):
        item = "skin"
    for i, g in enumerate(get(spec, "clothing.garments") or []):
        if isinstance(g, dict) and g.get("name") == item and isinstance(g.get("material"), dict):
            out.append((f"clothing.garments[{i}].material.base_color_srgb", g["material"].get("base_color_srgb")))
    for p in (f"materials.assignments.{item}.base_color_srgb", f"materials.albedo_srgb.{item}"):
        v = get(spec, p)
        if v is not None:
            out.append((p, v))
    return [(p, v) for p, v in out if isinstance(v, list) and len(v) == 3]


def suggest(overall, spec_path, overrides=()):
    if not spec_path:
        return []
    spec = json.load(open(spec_path))
    for o in overrides:
        spec = deep_merge(copy.deepcopy(spec), json.load(open(o)).get("override", {}))
    out = []
    for key, paths in PROPORTION_PATHS.items():
        p = overall["proportions"].get(key)
        if not p or p["relative_median"] is None or abs(p["relative_median"]) < MIN_REL[key]:
            continue
        ratio = p["reference_median"] / p["render_median"]
        for path in paths:
            v = get(spec, path)
            if isinstance(v, (int, float)):
                out.append({"path": path, "current": v, "suggested": round(v * ratio, 5),
                            "reason": f"{key} render/reference {1 + p['relative_median']:.2f} (median over views)",
                            "kind": "proportion"})
    for region, c in sorted(overall["colour"].items()):
        if c["de00_median"] is None or c["de00_median"] < 3:
            continue
        delta = np.array(c["reference_lab_median"]) - np.array(c["render_lab_median"])
        for path, cur in colour_paths(spec, region):
            new = M.lab_to_srgb(M.srgb_to_lab(np.array(cur, float)) + delta).tolist()
            out.append({"path": path, "current": cur, "suggested": new,
                        "reason": f"{region} dE00 {c['de00_median']:.1f}; Lab shift {np.round(delta, 1).tolist()} "
                                  "(first-order; re-measure after changing)", "kind": "colour"})
    return out
