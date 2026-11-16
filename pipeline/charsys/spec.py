"""Character spec handling (plain Python, no Blender): load, merge overrides, validate, canonical hash.

A spec is the single editable description of a character (identity, proportions, face, hair, clothing,
accessories, rig, materials, fur, animation compatibility, metadata). Builds are a pure function of
(spec, charsys code, Blender version); the spec hash is stamped into every built asset."""
import copy
import hashlib
import json

SCHEMA = "plush-studio.character-spec/1"
SECTIONS = ("identity", "proportions", "body", "face", "hair", "clothing", "accessories", "rig", "materials", "fur",
            "animation", "metadata")
BODY_ONLY_SECTIONS = ("face", "hair", "clothing", "accessories", "fur")
IDENTITY_SECTIONS = ("identity", "proportions", "face", "hair", "clothing", "accessories", "materials")  # changes need owner approval


def deep_merge(base, over):
    """Returns base with `over` merged in (dicts recursively; lists and scalars replaced)."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def validate(spec):
    errs = []
    if spec.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA}")
    required = [s for s in SECTIONS if not (spec.get("body", {}).get("generator") == "body_generic/1" and
                                             s in BODY_ONLY_SECTIONS)]
    for s in required:
        if s not in spec:
            errs.append(f"missing section: {s}")
    cid = spec.get("identity", {}).get("id", "")
    if not cid or not cid.replace("_", "").isalnum() or cid != cid.lower():
        errs.append("identity.id must be lower_snake_case")
    materials = spec.get("materials", {})
    if materials.get("assignments") is not None:
        try:
            from materials import builder as material_builder
            errs.extend(material_builder.validate_assignments(materials))
        except (OSError, ValueError) as exc:
            errs.append(str(exc))
    if spec.get("hair", {}).get("generator") == "groom/1":
        import groom
        errs.extend(groom.validate(spec["hair"]))
    if errs:
        raise ValueError("invalid character spec: " + "; ".join(errs))
    return spec


def canonical(spec):
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(spec):
    return hashlib.sha256(canonical(spec).encode()).hexdigest()


def load(path, overrides=()):
    """Loads a spec and applies override files/dicts in order. Returns (spec, info)."""
    spec = json.load(open(path))
    applied = []
    for o in overrides:
        od = json.load(open(o)) if isinstance(o, str) else o
        spec = deep_merge(spec, od.get("override", od))
        applied.append(o if isinstance(o, str) else "<dict>")
    validate(spec)
    return spec, {"spec_path": path, "overrides": applied, "spec_sha256": sha256(spec)}


def identity_changes(base, new):
    """Names of identity-level sections that differ between two specs (these need explicit owner approval)."""
    return [s for s in IDENTITY_SECTIONS if canonical(base.get(s)) != canonical(new.get(s))]
