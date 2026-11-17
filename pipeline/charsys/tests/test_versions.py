"""Plain-Python tests for per-feature generator versions and spec parts (T-043). No Blender needed.

    python3 pipeline/charsys/tests/test_versions.py

Covers: the registry (unknown / retired / malformed versions fail loudly, released pins load their declared module),
pins in specs (explicit pins respected, missing pins = frozen legacy defaults, contradictions rejected, the spec and
its hash never rewritten), two characters on different versions of one generator in one session not affecting each
other, spec part composition (a split spec is the same spec with the same hash), and the exporter's version line that
run_shot.py keys its package cache on."""
import ast
import copy
import glob
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import spec as S  # noqa: E402
import versions as V  # noqa: E402

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_versions] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def raises(fn, exc=ValueError, contains=""):
    try:
        fn()
    except exc as e:
        return contains in str(e)
    return False


def spec_files():
    return sorted(p for p in glob.glob(os.path.join(ROOT, "assets", "characters", "*", "spec", "*.spec.json")))


def test_registry():
    for feature, pin in V.REGISTRY.released():
        check(f"released {feature} {pin} resolves", V.REGISTRY.check(feature, pin) == pin)
    check("unknown version fails", raises(lambda: V.REGISTRY.check("body", "body_generic/99"), V.VersionError, "unknown"))
    check("unknown generator fails", raises(lambda: V.REGISTRY.check("face", "face_nope/1"), V.VersionError, "unknown"))
    check("unknown feature fails", raises(lambda: V.REGISTRY.check("tail", "tail/1"), V.VersionError, "unknown feature"))
    check("malformed pin fails", all(raises(lambda p=p: V.parse(p), V.VersionError, "malformed")
                                     for p in ("body_generic", "body_generic/0", "body_generic/01", "/1", "a/b/1", 3)))
    for n in (1, 2, 3):
        check(f"retired export/{n} fails", raises(lambda n=n: V.REGISTRY.check("exporter", f"export/{n}"),
                                                  V.VersionError, "retired"))
    check("export/4 and export/5 (T-056) are the only released exporters",
          V.REGISTRY.released("exporter") == [("exporter", "export/4"), ("exporter", "export/5")])
    reg = V.Registry()
    reg.register("body", "probe", 1)
    check("released version cannot be re-registered", raises(lambda: reg.register("body", "probe", 1),
                                                              V.VersionError, "immutable"))
    reg.retire("body", "probe/1")
    check("retiring makes a version fail", raises(lambda: reg.check("body", "probe/1"), V.VersionError, "retired"))
    check("'none' is always accepted", V.REGISTRY.check("garment", V.NONE) == V.NONE and V.REGISTRY.load("garment", V.NONE) is None)


def test_module_declarations():
    """Every declared=True built-in names a module that declares the pin (checked from source: no bpy import)."""
    for feature, names in V.REGISTRY._entries.items():
        for versions in names.values():
            for e in versions.values():
                if not e["declared"] or e["status"] != V.RELEASED:
                    continue
                rel = e["module"].replace(".", os.sep)
                path = os.path.join(CHARSYS, rel + ".py")
                if not os.path.exists(path):
                    path = os.path.join(CHARSYS, rel, "__init__.py")
                declared = ()
                for node in ast.parse(open(path).read()).body:
                    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "GENERATOR_VERSIONS" for t in node.targets):
                        declared = ast.literal_eval(node.value)
                check(f"{e['module']} declares {e['pin']}", e["pin"] in declared, declared)


def test_exporter_line():
    src = open(os.path.join(CHARSYS, "export_engine.py")).read()
    m = re.search(r'^EXPORTER_VERSION\s*=\s*["\']([^"\']+)["\']', src, re.M)  # the regex run_shot.py uses
    check("EXPORTER_VERSION literal kept for run_shot's cache key", m is not None and m.group(1) == "4",
          m and m.group(1))
    check("legacy exporter default = the exporter's registered version",
          V.LEGACY_EXPORTER == f"export/{m.group(1)}" and V.REGISTRY.check("exporter", V.LEGACY_EXPORTER))


def test_spec_pins():
    for path in spec_files():
        raw = json.load(open(path))
        spec, info = S.load(path)
        name = os.path.basename(path)
        check(f"{name}: hash unchanged by loading (pins are not written into the spec)",
              info["spec_sha256"] == S.sha256(raw) and ("generators" in spec) == ("generators" in raw))
        rec = info["versions"]
        check(f"{name}: every feature resolved", sorted(rec["generators"]) == sorted(V.FEATURES), rec["generators"])
        if "generators" not in raw:
            check(f"{name}: unpinned spec resolves to its own generator fields",
                  all(rec["generators"][f] == V.LEGACY_ALIASES.get(V._field(raw, fld), V._field(raw, fld) or V.NONE)
                      for f, fld in V.LEGACY_FIELDS.items()) and rec["generators"]["exporter"] == "export/4",
                  rec["generators"])
    base = json.load(open(spec_files()[0]))
    pinned = copy.deepcopy(base)
    pins, _ = V.resolve_pins(base)
    pinned["generators"] = dict(pins)
    p2, src = V.resolve_pins(pinned)
    check("explicit pins respected", p2 == pins and set(src.values()) == {"spec"}, src)
    for feature, bad, why in (("exporter", "export/2", "retired"), ("exporter", "export/7", "unknown"),
                              ("body", "body_generic/5", "unknown")):
        s = copy.deepcopy(base)
        s["generators"] = {feature: bad}
        check(f"spec pinning {bad} is rejected by validate()", raises(lambda s=s: S.validate(s), ValueError, why))
    s = copy.deepcopy(base)
    s["generators"] = {"wings": "wings/1"}
    check("unknown generators feature rejected", raises(lambda: S.validate(s), ValueError, "unknown generators feature"))
    s = copy.deepcopy(base)
    s["hair"] = dict(s["hair"], generator="hair_clumps/1")
    s["generators"] = {"groom": "hair_clumps/2"}
    check("pin contradicting the spec's generator field rejected", raises(lambda: V.resolve_pins(s), V.VersionError, "contradicts"))


PROBE = '''GENERATOR_VERSIONS = ("probe/{n}",)
STATE = {{"calls": 0}}
SCALE = {n}.0


def build(x):
    STATE["calls"] += 1
    return x * SCALE
'''


def test_two_versions_one_session():
    """Two characters on different versions of one generator, built interleaved in one session: each gets its own
    version's module and state; neither changes the other (a private Registry, so the built-in one is untouched)."""
    tmp = tempfile.mkdtemp(prefix="t043_versions_")
    for n in (1, 2):
        open(os.path.join(tmp, f"t043_probe_v{n}.py"), "w").write(PROBE.format(n=n))
    open(os.path.join(tmp, "t043_probe_bad.py"), "w").write("GENERATOR_VERSIONS = ()\n")
    sys.path.insert(0, tmp)
    try:
        reg = V.Registry()
        reg.register("body", "probe", 1, "t043_probe_v1")
        reg.register("body", "probe", 2, "t043_probe_v2")
        reg.register("body", "probe", 3, "t043_probe_bad")
        ch_a = {"generators": {"body": "probe/1", "face": V.NONE, "groom": V.NONE, "garment": V.NONE,
                               "accessories": V.NONE, "rig": V.NONE, "materials": V.NONE}, "materials": {}}
        ch_b = copy.deepcopy(ch_a)
        ch_b["generators"]["body"] = "probe/2"
        reg.register("exporter", "export", 4)  # the default exporter pin of these synthetic specs
        before = (S.canonical(ch_a), S.canonical(ch_b))
        pa, _ = V.resolve_pins(ch_a, reg)
        pb, _ = V.resolve_pins(ch_b, reg)
        ma, mb = reg.load("body", pa["body"]), reg.load("body", pb["body"])
        outs = [ma.build(1.0), mb.build(1.0), ma.build(2.0), mb.build(2.0)]
        check("each character gets its pinned version", (pa["body"], pb["body"]) == ("probe/1", "probe/2") and ma is not mb)
        check("interleaved builds do not affect each other", outs == [1.0, 2.0, 2.0, 4.0], outs)
        check("per-version state stays separate", ma.STATE["calls"] == 2 and mb.STATE["calls"] == 2)
        check("reloading a version returns the same module (no global swap)", reg.load("body", "probe/1") is ma)
        check("specs unchanged by resolving", before == (S.canonical(ch_a), S.canonical(ch_b)))
        check("module not declaring its version fails", raises(lambda: reg.load("body", "probe/3"), V.VersionError, "declare"))
        check("private registry left the built-in one untouched",
              raises(lambda: V.REGISTRY.check("body", "probe/1"), V.VersionError, "unknown"))
    finally:
        sys.path.remove(tmp)
        for n in ("t043_probe_v1", "t043_probe_v2", "t043_probe_bad"):
            sys.modules.pop(n, None)
    # the built-in characters, resolved interleaved in one session: same result as each alone
    files = spec_files()
    alone = [S.load(p)[1]["versions"] for p in files]
    mixed = [S.load(p)[1]["versions"] for p in files + files[::-1]]
    check("built-in characters resolve independently in one session", mixed == alone + alone[::-1])
    if len(set(json.dumps(a["generators"], sort_keys=True) for a in alone)) > 1:
        check("characters on different versions of the body generator in this repository",
              len({a["generators"]["body"] for a in alone}) > 1, [a["generators"]["body"] for a in alone])


def test_parts():
    for path in spec_files():
        name = os.path.basename(path)
        mono, info = S.load(path)
        tmp = tempfile.mkdtemp(prefix="t043_parts_")
        root, docs = S.split(json.load(open(path)))
        root["parts"] = {}
        for part, doc in reversed(list(docs.items())):  # listed in reverse: composition order must not matter
            fn = f"{part}.part.json"
            json.dump(doc, open(os.path.join(tmp, fn), "w"), indent=1)
            root["parts"][part] = fn
        rp = os.path.join(tmp, "root.spec.json")
        json.dump(root, open(rp, "w"), indent=1)
        split_spec, split_info = S.load(rp)
        check(f"{name}: split into {len(docs)} parts composes to the same spec and hash",
              split_info["spec_sha256"] == info["spec_sha256"] and split_spec == mono, sorted(docs))
        check(f"{name}: parts moved every part section out of the root",
              not any(s in root for secs in S.PART_SECTIONS.values() for s in secs))
        over = {"override": {"metadata": {"spec_version": "9.9.9-test"}}}
        o_spec, _ = S.load(rp, [over])
        check(f"{name}: overrides apply after composition", o_spec["metadata"]["spec_version"] == "9.9.9-test")
    base = json.load(open(spec_files()[0]))
    root, docs = S.split(base, parts=("face",))
    dup = dict(root, face=base["face"], parts={"face": docs["face"]})
    check("section defined twice rejected", raises(lambda: S.compose(dup), ValueError, "defined twice"))
    wrong = dict(root, parts={"hair": {"schema": S.PART_SCHEMA, "part": "hair", "sections": {"face": base["face"]}}})
    check("section in the wrong part rejected", raises(lambda: S.compose(wrong), ValueError, "does not belong"))
    check("unknown part rejected", raises(lambda: S.compose(dict(root, parts={"tail": {}})), ValueError, "unknown spec part"))
    bad = dict(root, parts={"face": dict(docs["face"], schema="x")})
    check("part with a wrong schema rejected", raises(lambda: S.compose(bad), ValueError, "must have schema"))
    check("inline parts compose like files", S.compose(dict(root, parts={"face": docs["face"]})) == base)
    check("spec without parts unchanged", S.compose(base) == base)


def main():
    test_registry()
    test_module_declarations()
    test_exporter_line()
    test_spec_pins()
    test_two_versions_one_session()
    test_parts()
    ok = all(RESULTS)
    print(f"[test_versions] {'ALL PASS' if ok else 'FAILURES'} ({sum(RESULTS)}/{len(RESULTS)})")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
