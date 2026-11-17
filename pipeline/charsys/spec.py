"""Character spec handling (plain Python, no Blender): load, merge overrides, validate, canonical hash.

A spec is the single editable description of a character (identity, proportions, face, hair, clothing,
accessories, rig, materials, fur, animation compatibility, metadata). Builds are a pure function of
(spec, charsys code, Blender version); the spec hash is stamped into every built asset.

Spec parts (T-043): a spec file may list part files that hold some of its sections,
    "parts": {"identity": "x.identity.json", "face": "x.face.json", "outfit": "x.outfit.json", ...}
(paths relative to the spec file). A part file is {"schema": PART_SCHEMA, "part": <name>, "sections": {...}} and may
only hold the sections of its part (PART_SECTIONS); a section may be defined once (root or one part). compose() returns
the plain monolithic spec without "parts", so a split spec has exactly the hash of the same spec in one file.

Generator versions (T-043): spec.generators pins the version of every generator (versions.py); validate() rejects
unknown/retired pins, and load() reports the resolved pins in info["versions"] (missing pins = frozen legacy defaults).
The spec itself is never rewritten with the defaults, so existing specs keep their hash."""
import copy
import hashlib
import json
import os

import versions as V

SCHEMA = "plush-studio.character-spec/1"
SECTIONS = ("identity", "proportions", "body", "face", "hair", "clothing", "accessories", "rig", "materials", "fur",
            "animation", "metadata")
PART_SCHEMA = "plush-studio.character-spec-part/1"
PART_SECTIONS = {"identity": ("identity", "proportions", "metadata"), "body": ("body", "rig", "fur", "animation", "components"),
                 "face": ("face",), "hair": ("hair",), "outfit": ("clothing", "accessories"), "materials": ("materials",)}
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
    for s in SECTIONS:
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
    try:
        V.resolve_pins(spec)
    except V.VersionError as exc:
        errs.append(str(exc))
    if errs:
        raise ValueError("invalid character spec: " + "; ".join(errs))
    return spec


def canonical(spec):
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(spec):
    return hashlib.sha256(canonical(spec).encode()).hexdigest()


def compose(root, base_dir="."):
    """Monolithic spec from a root spec dict and its part files (root["parts"], paths relative to base_dir).
    A root without "parts" is returned unchanged (as a copy)."""
    parts = root.get("parts")
    spec = {k: copy.deepcopy(v) for k, v in root.items() if k != "parts"}
    if parts is None:
        return spec
    if not isinstance(parts, dict):
        raise ValueError("invalid character spec: parts must be an object of part name -> file")
    unknown = sorted(set(parts) - set(PART_SECTIONS))
    if unknown:
        raise ValueError(f"invalid character spec: unknown spec part(s) {unknown} (known: {', '.join(PART_SECTIONS)})")
    for name in PART_SECTIONS:  # fixed order: the result never depends on the order parts are listed in
        if name not in parts:
            continue
        doc = parts[name]
        if isinstance(doc, str):
            doc = json.load(open(os.path.join(base_dir, doc)))
        if doc.get("schema") != PART_SCHEMA or doc.get("part") != name:
            raise ValueError(f"invalid character spec: part {name!r} must have schema {PART_SCHEMA} and part {name!r}")
        for sec, value in doc.get("sections", {}).items():
            if sec not in PART_SECTIONS[name]:
                raise ValueError(f"invalid character spec: section {sec!r} does not belong in part {name!r} "
                                 f"(allowed: {', '.join(PART_SECTIONS[name])})")
            if sec in spec:
                raise ValueError(f"invalid character spec: section {sec!r} is defined twice (part {name!r})")
            spec[sec] = copy.deepcopy(value)
    return spec


def split(spec, parts=tuple(PART_SECTIONS)):
    """Inverse of compose(): (root without the moved sections, {part: part document}). Part documents are inlined
    (write them to files and put the file names in root["parts"] to store a split spec)."""
    root = copy.deepcopy(spec)
    docs = {}
    for name in parts:
        secs = {s: root.pop(s) for s in PART_SECTIONS[name] if s in root}
        if secs:
            docs[name] = {"schema": PART_SCHEMA, "part": name, "sections": secs}
    return root, docs


def load(path, overrides=()):
    """Loads a spec (composing its parts) and applies override files/dicts in order. Returns (spec, info).
    info["versions"] records the resolved generator pins (versions.record)."""
    spec = compose(json.load(open(path)), os.path.dirname(os.path.abspath(path)))
    applied = []
    for o in overrides:
        od = json.load(open(o)) if isinstance(o, str) else o
        spec = deep_merge(spec, od.get("override", od))
        applied.append(o if isinstance(o, str) else "<dict>")
    validate(spec)
    return spec, {"spec_path": path, "overrides": applied, "spec_sha256": sha256(spec), "versions": V.record(spec)}


def identity_changes(base, new):
    """Names of identity-level sections that differ between two specs (these need explicit owner approval)."""
    return [s for s in IDENTITY_SECTIONS if canonical(base.get(s)) != canonical(new.get(s))]
