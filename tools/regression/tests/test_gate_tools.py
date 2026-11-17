#!/usr/bin/env python3
"""Unit tests for tools/integrate.py (claims, write-set) and tools/regression (tiers, comparisons). Plain Python.

    python tools/regression/tests/test_gate_tools.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "regression"))
import integrate as I  # noqa: E402
import run as R  # noqa: E402
import tiers as T  # noqa: E402

FAILURES: list[str] = []


def expect(condition, label):
    if not condition:
        FAILURES.append(label)
        print(f"FAIL {label}")


def test_glob_overlap():
    cases = [
        ("tools/**", "tools/check_all.py", True),
        ("engine/scene/emotion.{h,cpp}", "engine/scene/*.cpp", True),
        ("engine/scene/emotion.{h,cpp}", "engine/scene/interaction.*", False),
        ("engine/model/**", "engine/scene/**", False),
        ("**/tests/", "tools/fidelity/tests/x.py", True),
        ("**/tests/", "tests/x.cpp", True),
        ("tools/a*", "tools/b*", False),
        ("tools/*.py", "tools/sub/x.py", False),
        ("tools/**/x.py", "tools/x.py", True),
        ("assets/characters/*/spec/*.json", "assets/characters/girl/spec/a.json", True),
        ("docs/", "docs/process/OWNERSHIP.md", True),
        ("tests/test_emotions*.cpp", "tests/test_[ef]*.cpp", True),
        ("tests/test_emotions*.cpp", "tests/test_interaction.cpp", False),
        ("a?c", "a/c", False),
    ]
    for a, b, want in cases:
        expect(I.globs_overlap(a, b) is want, f"overlap({a}, {b}) == {want}")
        expect(I.globs_overlap(b, a) is want, f"overlap({b}, {a}) == {want} (symmetric)")
    expect(I.path_matches("tools/regression/run.py", "tools/regression/**"), "path in folder glob")
    expect(not I.path_matches("tools/integrate.py", "tools/regression/**"), "path outside folder glob")
    expect(I.task_from_branch("t-041-claude-gate-claims") == "T-041", "task from branch")
    expect(I.task_from_branch("staging") == "", "staging is not a task branch")


TABLE = """
| Task | Lane | Branch | Write-set | Depends on | Versions bumped |
| --- | --- | --- | --- | --- | --- |
| T-900 | A | `t-900-x` | `tools/a.py`, `docs/x/**` | `pipeline/b.py` (stable) | `face_generic` |
| T-901 | B | `t-901-y` | `pipeline/b.py`, `engine/{m,n}.cpp` | — | — |
| T-902 | C | `t-902-z` | `engine/*.cpp` | — | `face_generic` |
| T-903 | C | `t-903-w` | `content/**` | `tools/a.py` | — |
"""


def test_claims():
    claims = I.parse_ownership(TABLE)
    expect([c.task for c in claims] == ["T-900", "T-901", "T-902", "T-903"], "claims parsed")
    by = {c.task: c for c in claims}
    expect(by["T-901"].write_set == ["pipeline/b.py", "engine/{m,n}.cpp"], "write-set cell parsed")
    expect(by["T-900"].stable_depends == ["pipeline/b.py"] and not by["T-900"].depends_on, "stable dependency")
    conflicts, warnings = I.check_claims(by["T-900"], claims)
    expect(any("T-902" in c and "face_generic" in c for c in conflicts), "same version bump = conflict")
    expect(any("T-903 depends on tools/a.py" in c for c in conflicts), "other task depends on my file = conflict")
    expect(any("T-901" in w for w in warnings) and not any("T-901" in c for c in conflicts), "stable dep = warning")
    conflicts, _ = I.check_claims(by["T-901"], claims)
    expect(any("T-902" in c and "engine/" in c for c in conflicts), "glob-aware write-set overlap")
    expect(I.write_set_violations({"tools/a.py", "docs/x/y/z.md", "tools/b.py"}, by["T-900"]) == ["tools/b.py"],
           "write-set violations")
    task = I.parse_task_file("# T-904\nbranch `t-904-q`\n## Write-set\n`a/b.py`, `c/**`.\nNot: `d.py`.\n"
                             "## Depends on\nReads `e/f.py` (stable).\n", "T-904")
    expect(task.write_set == ["a/b.py", "c/**"] and task.stable_depends == ["e/f.py"] and task.branch == "t-904-q",
           "task file parsed (Not: excluded)")
    real = I.load_claims()
    expect(any(c.task == "T-041" for c in real), "OWNERSHIP.md parses")


def test_tiers():
    rules = [("full", "pipeline/**"), ("fast", "docs/**"), ("fast", "tools/**")]
    expect(T.classify({"docs/a.md"}, rules)["tier"] == "fast", "docs only = fast")
    unknown = T.classify({"docs/a.md", "newdir/thing.bin"}, rules)
    expect(unknown["tier"] == "full" and unknown["unknown_paths"] == ["newdir/thing.bin"], "unknown path = full")
    expect(T.classify({"pipeline/charsys/x.py"}, rules)["tier"] == "full", "shared system = full")
    real = T.load_rules()
    expect(T.classify({"pipeline/charsys/face_generic.py"}, real)["tier"] == "full", "real rules: generator = full")
    expect(T.classify({"docs/process/GATE.md"}, real)["tier"] == "fast", "real rules: docs = fast")
    expect(T.classify({"tools/regression_paths.txt"}, real)["tier"] == "full", "real rules: classification = full")
    expect(T.classify({"something/new.txt"}, real)["tier"] == "full", "real rules: unknown = full")
    ids = T.character_ids()
    expect(len(ids) >= 2, "characters found")
    for cid in ids:
        cfg = T.character_config(cid)
        expect(cfg["spec_inputs_sha256"] and cfg["spec_version"], f"config {cid}")
    if ids:
        changed = T.changed_characters({f"assets/characters/{ids[0]}/spec/{ids[0]}.spec.json", "docs/x.md"})
        expect(changed == [ids[0]], "changed character from its spec path")


def test_compare():
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        print("SKIP image comparison (Pillow missing)")
        return
    noise = {"max_rmse": 0.01, "max_changed_fraction": 0.01}
    with tempfile.TemporaryDirectory() as temp:
        t = Path(temp)
        cfg = {"character": "probe", "spec_version": "1.0.0", "spec_inputs_sha256": "abc", "inputs": []}
        golden_root = t / "golden"
        gdir = golden_root / "probe" / "1.0.0"
        (gdir / "renders").mkdir(parents=True)
        out = t / "out"
        (out / "renders").mkdir(parents=True)
        Image.new("RGBA", (16, 16), (100, 100, 100, 255)).save(gdir / "renders" / "v.png")
        Image.new("RGBA", (16, 16), (100, 100, 100, 255)).save(out / "renders" / "v.png")
        fp = {"objects": {"head": {"coords_hash": "1"}}}
        (gdir / "fingerprint.json").write_bytes(R.canonical(fp))
        (out / "fingerprint.json").write_bytes(R.canonical(fp))
        golden = {"spec_inputs_sha256": "abc", "fingerprint_sha256": "F", "export": {"e": "1"}, "renders": {}}
        (gdir / "golden.json").write_text(json.dumps(golden), encoding="utf-8")
        data = {"fingerprint_sha256": "F", "export": {"e": "1"}, "renders": {"v": "x"}}
        checks = R.compare(cfg, dict(data), out, golden_root, True, noise)
        expect(all(c["ok"] for c in checks), "identical character passes")
        changed_fp = dict(data, fingerprint_sha256="G")
        (out / "fingerprint.json").write_bytes(R.canonical({"objects": {"head": {"coords_hash": "2"}}}))
        checks = R.compare(cfg, changed_fp, out, golden_root, True, noise)
        bad = [c for c in checks if not c["ok"]]
        expect(bad and bad[0]["name"] == "fingerprint" and "head" in bad[0]["detail"],
               "unchanged character with changed fingerprint = FAIL")
        checks = R.compare(cfg, changed_fp, out, golden_root, False, noise)
        expect(all(c["ok"] for c in checks), "changed-spec character: differences reported, not failed")
        Image.new("RGBA", (16, 16), (160, 100, 100, 255)).save(out / "renders" / "v.png")
        checks = R.compare(cfg, dict(data), out, golden_root, True, noise)
        expect(any(c["name"] == "renders" and not c["ok"] for c in checks), "render outside noise = FAIL")
        checks = R.compare(dict(cfg, spec_inputs_sha256="other"), dict(data), out, golden_root, True, noise)
        expect(any(c["name"] == "baseline" and not c["ok"] for c in checks), "stale baseline = FAIL")
        checks = R.compare(dict(cfg, spec_version="2.0.0"), dict(data), out, golden_root, True, noise)
        expect(any(c["name"] == "baseline" and not c["ok"] for c in checks), "missing baseline for unchanged = FAIL")


def main() -> int:
    for test in (test_glob_overlap, test_claims, test_tiers, test_compare):
        test()
    print(f"{'FAIL' if FAILURES else 'PASS'} gate tools: {len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
