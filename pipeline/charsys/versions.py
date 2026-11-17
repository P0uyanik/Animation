"""Per-feature generator versions (T-043): the registry every character build resolves its pins against.

Plain Python (no Blender), so spec validation, tools and tests can use it without bpy.

A character spec pins the version of every generator, preset library and the exporter it uses:

    "generators": {"body": "body_generic/1", "face": "face_generic/1", "groom": "groom/1", "garment": "garment/1",
                   "accessories": "accessories/1", "rig": "rigify_human/1", "materials": "presets/1",
                   "exporter": "export/4"}

A pin is "<name>/<number>"; "none" means the character does not use that feature. Rules
(docs/CHARACTER_SYSTEM_VERSIONS.md):
  * a released version is immutable: its output may never change. New behaviour = a new number, registered here and
    implemented in its own module (or behind its own code path), so characters pinned to the old number are untouched;
  * building with an unknown or retired version fails loudly (VersionError), never falls back;
  * a spec without a pin for a feature builds with the legacy defaults (LEGACY_FIELDS): the versions every spec written before T-043
    builds with, derived only from the spec's own generator fields. That table is frozen: adding a new version never
    changes it, so an unpinned spec keeps building exactly as it did.

Generator modules declare the versions they implement (GENERATOR_VERSIONS = ("body_generic/1",)); load() checks the
declaration after import. Modules that are frozen or owned elsewhere (body_v6, hair, accessories, materials) are
registered with declared=False.
"""
import importlib

FEATURES = ("body", "face", "groom", "garment", "accessories", "rig", "materials", "exporter")
NONE = "none"
RELEASED, RETIRED = "released", "retired"


class VersionError(ValueError):
    """Unknown, retired, malformed or conflicting generator version."""


def parse(pin):
    """'body_generic/1' -> ('body_generic', 1). Raises VersionError on anything else."""
    if not isinstance(pin, str) or pin.count("/") != 1:
        raise VersionError(f"malformed version pin {pin!r} (expected '<name>/<number>')")
    name, num = pin.split("/")
    if not name or not num.isdigit() or str(int(num)) != num or int(num) < 1:
        raise VersionError(f"malformed version pin {pin!r} (expected '<name>/<number>', number >= 1)")
    return name, int(num)


class Registry:
    """feature -> name -> number -> entry. The module-level REGISTRY holds the built-in versions; tests may make their
    own Registry so they never change the global one."""

    def __init__(self):
        self._entries = {}

    def register(self, feature, name, number, module=None, status=RELEASED, declared=True, note=""):
        if feature not in FEATURES:
            raise VersionError(f"unknown feature {feature!r} (known: {', '.join(FEATURES)})")
        pin = f"{name}/{number}"
        parse(pin)
        if status not in (RELEASED, RETIRED):
            raise VersionError(f"{feature} {pin}: status must be {RELEASED!r} or {RETIRED!r}")
        versions = self._entries.setdefault(feature, {}).setdefault(name, {})
        if number in versions:
            raise VersionError(f"{feature} {pin} is already registered (released versions are immutable)")
        versions[number] = {"feature": feature, "pin": pin, "module": module, "status": status,
                            "declared": declared, "note": note}
        return versions[number]

    def retire(self, feature, pin):
        self.entry(feature, pin, allow_retired=True)["status"] = RETIRED

    def entry(self, feature, pin, allow_retired=False):
        """The registered entry of a pin. Unknown or (unless allowed) retired versions raise VersionError."""
        if feature not in FEATURES:
            raise VersionError(f"unknown feature {feature!r} (known: {', '.join(FEATURES)})")
        name, number = parse(pin)
        versions = self._entries.get(feature, {}).get(name)
        if versions is None:
            known = sorted(f"{n}/{v}" for n, vs in self._entries.get(feature, {}).items() for v in vs)
            raise VersionError(f"unknown {feature} generator {name!r} in pin {pin!r} (registered: {', '.join(known)})")
        e = versions.get(number)
        if e is None:
            raise VersionError(f"unknown {feature} version {pin!r} (registered {name} versions: "
                               f"{', '.join(str(n) for n in sorted(versions))})")
        if e["status"] == RETIRED and not allow_retired:
            raise VersionError(f"{feature} version {pin!r} is retired and can no longer be built; pin a released "
                               f"version (path B pin bump, owner approval)")
        return e

    def check(self, feature, pin):
        """Raises VersionError unless pin is 'none' or a released version of the feature."""
        if pin != NONE:
            self.entry(feature, pin)
        return pin

    def load(self, feature, pin):
        """Imports the module implementing a pinned version (None for 'none'). Each version has its own module or
        code path, so loading one version never changes another one that is already loaded."""
        if pin == NONE:
            return None
        e = self.entry(feature, pin)
        if not e["module"]:
            raise VersionError(f"{feature} {pin} has no loadable module")
        mod = importlib.import_module(e["module"])
        if e["declared"] and pin not in getattr(mod, "GENERATOR_VERSIONS", ()):
            raise VersionError(f"module {e['module']} does not declare {pin} in GENERATOR_VERSIONS")
        return mod

    def released(self, feature=None):
        return sorted((e["feature"], e["pin"]) for f, names in self._entries.items() if feature in (None, f)
                      for vs in names.values() for e in vs.values() if e["status"] == RELEASED)


REGISTRY = Registry()
_r = REGISTRY.register
# ---- built-in versions (released versions are immutable; append new numbers, never edit an existing line) ----
_r("body", "body_v6", 1, "body_v6", declared=False, note="legacy v6 builder (frozen file)")
_r("body", "body_generic", 1, "body_generic")
_r("face", "body_v6", 1, "body_v6", declared=False, note="legacy v6 face with face.py expression keys")
_r("face", "face_generic", 1, "face_generic")
_r("groom", "hair_clumps", 1, "hair", declared=False, note="legacy clump hair (hair.py)")
_r("groom", "hair_clumps", 2, "hair", declared=False, note="legacy lock-family hair (hair.py; experiments)")
_r("groom", "groom", 1, "groom")
_r("garment", "body_v6", 1, "body_v6", declared=False, note="legacy v6 clothing")
_r("garment", "garment", 1, "garments")
_r("accessories", "body_v6", 1, "body_v6", declared=False, note="legacy v6 backpack")
_r("accessories", "accessories", 1, "accessories", declared=False)
_r("rig", "rigify_human", 1, None, declared=False, note="Rigify human (body_v6.rig_character / body_generic.rig_generic)")
_r("materials", "body_v6", 1, "body_v6", declared=False, note="legacy v6 albedo materials (body_v6.make_materials)")
_r("materials", "albedo", 1, "geom", declared=False, note="generic path without preset assignments (geom.material)")
_r("materials", "presets", 1, "materials.builder", declared=False,
   note="material preset library plush-studio.material-presets/1")
_r("exporter", "export", 1, None, RETIRED, note="no retarget block")
_r("exporter", "export", 2, None, RETIRED, note="retarget block")
_r("exporter", "export", 3, None, RETIRED, note="dynamics block or DEF-parent fix (two parallel 3s)")
_r("exporter", "export", 4, "export_engine", declared=False, note="dynamics + DEF-parent fix + eye pivots; the script")
_r("exporter", "export", 5, "export_engine", declared=False, note="export/4 + order-stable, byte-reproducible output (T-056)")
del _r
# ---- retirements (status changes only; the registration lines above stay as released) ----
# hair_clumps/2: CP-2 lock-family hair, used only by the boy's H20-H35 experiments (archived in T-072; F09/H28 rejected
# by the owner 2026-11-17). No character spec or override pins it (owner decision 2026-11-17, item 4).
REGISTRY.retire("groom", "hair_clumps/2")

# ---- legacy defaults: frozen. The spec field each feature's default comes from; its value maps to the pin of the same
# name (a pre-T-043 field already names the exact version it builds with), "none" to none, and the legacy builder's
# bare name "body_v6" to body_v6/1. Adding a new version never changes what an unpinned spec resolves to. ----
LEGACY_FIELDS = {"body": "body.generator", "face": "face.generator", "groom": "hair.generator",
                 "garment": "clothing.generator", "accessories": "accessories.generator", "rig": "rig.generator"}
LEGACY_ALIASES = {"body_v6": "body_v6/1", NONE: NONE}
LEGACY_EXPORTER = "export/4"


def _field(spec, dotted):
    sec, key = dotted.split(".")
    return (spec.get(sec) or {}).get(key)


def legacy_default(spec, feature):
    """The version an unpinned spec builds this feature with (frozen rules; see LEGACY_FIELDS)."""
    if feature == "exporter":
        return LEGACY_EXPORTER
    if feature == "materials":
        if (spec.get("materials") or {}).get("assignments"):
            return "presets/1"
        return "body_v6/1" if _field(spec, "body.generator") == "body_v6" else "albedo/1"
    value = _field(spec, LEGACY_FIELDS[feature])
    if value is None:
        return NONE
    value = LEGACY_ALIASES.get(value, value)
    try:
        parse(value) if value != NONE else None
    except VersionError:
        raise VersionError(f"{LEGACY_FIELDS[feature]} = {value!r} has no default version; pin generators.{feature}")
    return value


def resolve_pins(spec, registry=None):
    """Returns (pins, sources): the pin of every feature and where it came from ("spec" or "default"). Every pin must
    be 'none' or a released version; an explicit pin may not contradict the spec's own generator field (same generator
    family with another number). The spec itself is never changed (its hash stays the same)."""
    reg = registry or REGISTRY
    given = spec.get("generators") or {}
    if not isinstance(given, dict):
        raise VersionError("generators must be an object of feature -> '<name>/<number>'")
    unknown = sorted(set(given) - set(FEATURES))
    if unknown:
        raise VersionError(f"unknown generators feature(s) {unknown} (known: {', '.join(FEATURES)})")
    pins, sources = {}, {}
    for f in FEATURES:
        if f in given:
            pin, sources[f] = given[f], "spec"
            if f in LEGACY_FIELDS and pin != NONE:
                value = _field(spec, LEGACY_FIELDS[f])
                if isinstance(value, str) and "/" in value and value.split("/")[0] == parse(pin)[0] and value != pin:
                    raise VersionError(f"generators.{f} = {pin!r} contradicts {LEGACY_FIELDS[f]} = {value!r}")
        else:
            pin, sources[f] = legacy_default(spec, f), "default"
        pins[f] = reg.check(f, pin)
    return pins, sources


def record(spec, registry=None):
    """The block written into build reports and engine package manifests."""
    pins, sources = resolve_pins(spec, registry)
    return {"generators": pins, "pinned_in_spec": sorted(f for f, s in sources.items() if s == "spec"),
            "defaulted": sorted(f for f, s in sources.items() if s == "default")}


def load(feature, pin):
    return REGISTRY.load(feature, pin)
