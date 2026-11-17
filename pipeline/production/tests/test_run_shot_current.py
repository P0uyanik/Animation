"""T-062 tests: run_shot's "current" cast reference and the cast check (tools/check_cast.py). Fast: no Blender.

    python3 pipeline/production/tests/test_run_shot_current.py

1. "current" resolves, for every character in the fidelity baseline, to the same build inputs and version as the
   gate's all-character regression (tools/regression/tiers.py character_config).
2. Resolution rules on a temporary repository: unpublished version -> spec + overrides; published version -> the
   published version_dir; unknown character / missing input / mismatched spec -> refused; explicit sources unchanged;
   unsupported explicit versions refused.
3. prepare() with "current" (fake Blender and exporter): run_shot.json's cast and prepare.json record the resolved
   version and inputs, cast.json carries the version; an explicit cast keeps its exact pre-T-062 keys.
4. Cast check rules (fixtures): "current" passes; a pinned old version fails unless "legacy_reason"; an explicit
   source of the current version passes in new docs/evaluation shots but fails in evaluation shots.
5. The repository itself passes the cast check (content/scenes/eval + new docs/evaluation shots). This is the
   gate's fast-tier cast check (tools/check_all.py runs this file)."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAILS = []


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_shot = load("run_shot", "pipeline/production/run_shot.py")
check_cast = load("check_cast", "tools/check_cast.py")
sys.path.insert(0, str(ROOT / "tools" / "regression"))
tiers = load("tiers", "tools/regression/tiers.py")


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def raises(fn):
    try:
        fn()
    except SystemExit as exc:
        return str(exc.code)
    return ""


def write(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1))
    return path


def fixture(root):
    """A minimal repository: character c_one (spec 2.0.0 + override 2.1.0, unpublished; 2.0.0 published) and
    c_two (spec 0.5.0, published 0.5.0)."""
    write(root, "docs/evaluation/characters/fidelity_baseline.json", {"characters": {
        "c_one": {"build": "assets/characters/c_one/spec/c_one.spec.json",
                  "overrides": ["assets/characters/c_one/spec/c_one.2.1.0.override.json"]},
        "c_two": {"build": "assets/characters/c_two/spec/c_two.spec.json", "overrides": []}}})
    for cid, ver in (("c_one", "2.0.0"), ("c_two", "0.5.0")):
        write(root, f"assets/characters/{cid}/spec/{cid}.spec.json",
              {"identity": {"id": cid}, "metadata": {"spec_version": ver}})
        master = write(root, f"assets/characters/{cid}/versions/{ver}/{cid}_master.blend", b"master " + cid.encode())
        write(root, f"assets/characters/{cid}/versions/{ver}/manifest.json",
              {"character_id": cid, "version": ver,
               "files": {f"{cid}_master.blend": {"sha256": run_shot.sha256(str(master))}}})
    write(root, "assets/characters/c_one/spec/c_one.2.1.0.override.json",
          {"override": {"metadata": {"spec_version": "2.1.0"}}})


FAKE_BLENDER = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[sys.argv.index("--") + 1:]
out = args[args.index("--out") + 1]
os.makedirs(out, exist_ok=True)
if "build_character.py" in sys.argv[sys.argv.index("-P") + 1]:
    cid = json.load(open(args[args.index("--spec") + 1]))["identity"]["id"]
    open(os.path.join(out, cid + "_master.blend"), "wb").write(b"built " + " ".join(args).encode())
else:
    json.dump({"format": "plush.imported_character", "blend": args[args.index("--blend") + 1]},
              open(os.path.join(out, "character.json"), "w"))
'''


def test_matches_regression(failures_before):
    baseline = json.loads((ROOT / run_shot.FIDELITY_BASELINE).read_text())
    for cid in sorted(baseline["characters"]):
        src = run_shot.current_source(cid)
        cfg = tiers.character_config(cid)
        res = src["resolved"]
        check(f"current {cid} = regression config (spec, overrides, version {res['version']})",
              (res["spec"], res["overrides"], res["version"]) == (cfg["spec"], cfg["overrides"], cfg["spec_version"]),
              f"{res} vs {cfg['spec']} {cfg['overrides']} {cfg['spec_version']}")
        published = (ROOT / "assets/characters" / cid / "versions" / res["version"] / "manifest.json").is_file()
        check(f"current {cid}: published master iff the version is published",
              ("version_dir" in src) == published and ("spec" in src) != published, src)


def test_rules(tmp):
    fixture(tmp)
    one = run_shot.current_source("c_one", tmp)
    check("unpublished current (2.1.0) builds from spec + overrides",
          one.get("spec") == "assets/characters/c_one/spec/c_one.spec.json"
          and one.get("overrides") == ["assets/characters/c_one/spec/c_one.2.1.0.override.json"]
          and "version_dir" not in one and one["resolved"]["version"] == "2.1.0", one)
    two = run_shot.current_source("c_two", tmp)
    check("published current (0.5.0) uses the published version_dir",
          two.get("version_dir", "").replace(os.sep, "/") == "assets/characters/c_two/versions/0.5.0"
          and "spec" not in two and two["resolved"]["version"] == "0.5.0", two)
    check("unknown character refused", "not listed" in raises(lambda: run_shot.current_source("c_none", tmp)))
    check("missing character_id refused", "needs a character_id" in raises(lambda: run_shot.current_source(None, tmp)))
    os.remove(Path(tmp) / "assets/characters/c_one/spec/c_one.2.1.0.override.json")
    check("missing build input refused", "missing" in raises(lambda: run_shot.current_source("c_one", tmp)))
    write(tmp, "assets/characters/c_one/spec/c_one.2.1.0.override.json",
          {"override": {"metadata": {"spec_version": "2.1.0"}}})
    write(tmp, "assets/characters/c_two/spec/c_two.spec.json", {"identity": {"id": "c_one"}, "metadata": {}})
    check("baseline spec of another character refused", "not this character" in raises(lambda: run_shot.current_source("c_two", tmp)))
    write(tmp, "assets/characters/c_two/spec/c_two.spec.json", {"identity": {"id": "c_two"}, "metadata": {"spec_version": "0.5.0"}})
    explicit = {"spec": "x.spec.json", "overrides": []}
    check("explicit cast sources are unchanged", run_shot.cast_source("a", explicit) is explicit
          and run_shot.cast_source("a", {"version_dir": "v"}) == {"version_dir": "v"})
    check("unsupported explicit version refused",
          "not supported" in raises(lambda: run_shot.cast_source("a", {"character_id": "c_one", "version": "2.0.0"})))


def test_prepare(tmp):
    fixture(tmp)
    blender = Path(tmp) / "fake_blender.py"
    blender.write_text(FAKE_BLENDER)
    blender.chmod(0o755)
    old_root, old_env = run_shot.ROOT, os.environ.get("PLUSH_EXPORT_ENGINE")
    run_shot.ROOT = tmp
    os.environ["PLUSH_EXPORT_ENGINE"] = str(blender)  # any file path works as the "exporter" for the fake Blender
    try:
        shot = {"characters": [{"name": "a"}, {"name": "b"}, {"name": "c"}],
                "production": {"cast": {"a": {"character_id": "c_one", "version": "current"},
                                        "b": {"character_id": "c_two", "version": "current"},
                                        "c": {"version_dir": "assets/characters/c_one/versions/2.0.0"}}}}
        out, logs = Path(tmp) / "shot/build", Path(tmp) / "shot/build/logs"
        logs.mkdir(parents=True)
        rep = {"steps": {}, "cast": {}}
        _, prep = run_shot.prepare(shot, str(Path(tmp) / "shot/shot.scene.json"), str(out), str(logs),
                                   str(blender), rep)
        cast_json = json.loads((out / "cast.json").read_text())
    finally:
        run_shot.ROOT = old_root
        if old_env is None:
            os.environ.pop("PLUSH_EXPORT_ENGINE", None)
        else:
            os.environ["PLUSH_EXPORT_ENGINE"] = old_env
    a, b, c = rep["cast"]["a"], rep["cast"]["b"], rep["cast"]["c"]
    check("run_shot.json records the resolved current version (unpublished: built)",
          a["version"] == "2.1.0" and a["resolved"]["from"] == "current" and a["status"].startswith("current 2.1.0 (unpublished")
          and a["resolved"]["overrides"] == ["assets/characters/c_one/spec/c_one.2.1.0.override.json"], a)
    check("run_shot.json records the resolved current version (published)",
          b["version"] == "0.5.0" and b["status"] == "current 0.5.0 (published 0.5.0)"
          and b["resolved"]["version_dir"] == "assets/characters/c_two/versions/0.5.0", b)
    check("explicit cast keeps its pre-T-062 run_shot.json keys",
          sorted(c) == ["character_id", "master_sha256", "package", "status"] and c["status"] == "published 2.0.0", c)
    check("prepare.json and cast.json carry the version of current casts only",
          prep["cast"]["a"]["version"] == "2.1.0" and prep["cast"]["b"]["version"] == "0.5.0"
          and "version" not in prep["cast"]["c"] and cast_json["a"]["version"] == "2.1.0"
          and "version" not in cast_json["c"], (prep["cast"], cast_json))
    check("resolved scene points every character at its package",
          all(ch["asset"].endswith("character.json") for ch in shot["characters"]))


def test_cast_check(tmp):
    fixture(tmp)
    cur = {"character_id": "c_one", "version": "current"}
    old = {"version_dir": "assets/characters/c_one/versions/2.0.0"}
    same = {"spec": "assets/characters/c_one/spec/c_one.spec.json",
            "overrides": ["assets/characters/c_one/spec/c_one.2.1.0.override.json"]}
    cases = [("eval current", "content/scenes/eval/x/shot.scene.json", True, cur, True),
             ("eval pinned old version", "content/scenes/eval/x/shot.scene.json", True, old, False),
             ("eval pinned old version with legacy_reason", "content/scenes/eval/x/shot.scene.json", True,
              dict(old, legacy_reason="frozen comparison"), True),
             ("eval explicit source of the current version", "content/scenes/eval/x/shot.scene.json", True, same, False),
             ("new evidence shot: explicit current version", "docs/evaluation/a/T-1/shot/shot.scene.json", False, same, True),
             ("new evidence shot: pinned old version", "docs/evaluation/a/T-1/shot/shot.scene.json", False, old, False),
             ("new evidence shot: empty legacy_reason", "docs/evaluation/a/T-1/shot/shot.scene.json", False,
              dict(old, legacy_reason=" "), False),
             ("unknown character", "content/scenes/eval/x/shot.scene.json", True,
              {"character_id": "c_none", "version": "current"}, False)]
    for name, rel, require, src, expect in cases:
        write(tmp, rel, {"characters": [{"name": "a"}], "production": {"cast": {"a": src}}})
        result = check_cast.check_shot(rel, require, run_shot, Path(tmp))
        check(f"cast check: {name} -> {'pass' if expect else 'fail'}", (not result["problems"]) == expect, result)
    check("new-shot pattern matches nested and direct evidence shots",
          check_cast.matches("docs/evaluation/animation/T-9/shot_after/shot.scene.json", check_cast.NEW_SHOT_GLOB)
          and check_cast.matches("docs/evaluation/T-9/shot.scene.json", check_cast.NEW_SHOT_GLOB)
          and not check_cast.matches("docs/evaluation/T-9/scene.json", check_cast.NEW_SHOT_GLOB))


def test_repository():
    report = check_cast.run(check_cast.choose_base(""))
    check(f"repository cast check ({len(report['checked'])} shots, base {report['base'] or 'none'})",
          report["pass"], "; ".join(report["problems"]))
    eval_shots = check_cast.evaluation_shots()
    names = {Path(p).parent.name for p in eval_shots}
    check("evaluation shots: idle, walk, reach + touch, wave, hand-over, emotion sequence",
          {"idle", "walk", "reach_touch_wave", "wave", "handover", "emotions"} <= names, sorted(names))
    baseline = json.loads((ROOT / run_shot.FIDELITY_BASELINE).read_text())
    for p in eval_shots:
        cast = json.loads((ROOT / p).read_text())["production"]["cast"]
        check(f"{p}: every cast entry is 'current' of a baseline character",
              all(s.get("version") == "current" and s.get("character_id") in baseline["characters"] for s in cast.values()), cast)
    check("every built character appears in the evaluation shots",
          not report["current_characters_not_in_evaluation_shots"], report["current_characters_not_in_evaluation_shots"])


def main():
    test_matches_regression(len(FAILS))
    for test in (test_rules, test_prepare, test_cast_check):
        tmp = tempfile.mkdtemp(prefix="t062_")
        try:
            test(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    test_repository()
    print(f"{'FAIL' if FAILS else 'PASS'}: test_run_shot_current ({len(FAILS)} failed)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
