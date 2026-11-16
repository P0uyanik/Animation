#!/usr/bin/env python3
"""Run the repository's complete, cross-platform quality gate.

The console output is deliberately limited to one line per top-level check.
Full command output is written below ``--artifacts-dir`` and a machine-readable
report is written to JSON.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from fidelity import ci as fidelity_ci


ROOT = Path(__file__).resolve().parents[1]
FROZEN_MANIFEST = ROOT / "tools" / "frozen_manifest.txt"
GUARDED_PATHS = ROOT / "tools" / "guarded_paths.txt"
CHARACTER_ALLOWLIST = ROOT / "tools" / "shared_character_allowlist.txt"
FIDELITY_BASELINE = ROOT / "docs" / "evaluation" / "characters" / "fidelity_baseline.json"
CODE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".py"}
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
SHARED_PREFIXES = ("engine/", "apps/", "pipeline/charsys/", "pipeline/clips/")
CHARACTER_DATA_PREFIXES = ("pipeline/charsys/character_data/", "pipeline/charsys/data/")


@dataclasses.dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    log: str = ""
    seconds: float = 0.0
    skipped: bool = False
    subchecks: list[dict] = dataclasses.field(default_factory=list)

    def as_json(self) -> dict:
        return dataclasses.asdict(self)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check,
    )


def git_ref_exists(ref: str) -> bool:
    return git("rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0


def choose_base(explicit: str) -> str:
    if explicit:
        if not git_ref_exists(explicit):
            raise ValueError(f"base ref does not exist: {explicit}")
        return explicit
    env_base = os.environ.get("CHECK_ALL_BASE_REF", "")
    if env_base:
        if not git_ref_exists(env_base):
            raise ValueError(f"CHECK_ALL_BASE_REF does not exist: {env_base}")
        return env_base
    for candidate in ("origin/main", "main", "HEAD^"):
        if git_ref_exists(candidate):
            return candidate
    return "HEAD"


def nul_paths(data: str) -> set[str]:
    return {p.replace("\\", "/") for p in data.split("\0") if p}


def changed_paths(base: str) -> set[str]:
    compare = base
    if not git_ref_exists("MERGE_HEAD"):
        common = git("merge-base", base, "HEAD", check=False)
        if common.returncode == 0 and common.stdout.strip():
            compare = common.stdout.strip()
    diff = git("diff", "--name-only", "-z", compare, "--").stdout
    untracked = git("ls-files", "--others", "--exclude-standard", "-z").stdout
    return nul_paths(diff) | nul_paths(untracked)


def dirty_paths() -> set[str]:
    diff = git("diff", "--name-only", "-z", "HEAD", "--").stdout
    cached = git("diff", "--cached", "--name-only", "-z", "HEAD", "--").stdout
    untracked = git("ls-files", "--others", "--exclude-standard", "-z").stdout
    return nul_paths(diff) | nul_paths(cached) | nul_paths(untracked)


def tracked_and_untracked() -> set[str]:
    out = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout
    return nul_paths(out)


def short(items: list[str], limit: int = 5) -> str:
    shown = items[:limit]
    suffix = f" (+{len(items) - limit} more)" if len(items) > limit else ""
    return ", ".join(shown) + suffix


def parse_frozen_manifest() -> tuple[dict[str, str], list[str]]:
    expected: dict[str, str] = {}
    scopes: list[str] = []
    for number, raw in enumerate(FROZEN_MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# scope: "):
            scopes.append(line[len("# scope: "):].strip())
            continue
        if line.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-f]{40})\s{2}(.+)", line)
        if not match:
            raise ValueError(f"{FROZEN_MANIFEST.relative_to(ROOT)}:{number}: malformed entry")
        blob, path = match.groups()
        if path in expected:
            raise ValueError(f"duplicate frozen path: {path}")
        expected[path] = blob
    return expected, scopes


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        if not any(ch in pattern for ch in "*?["):
            return path.startswith(pattern)
        return fnmatch.fnmatchcase(path, pattern + "*")
    if not any(ch in pattern for ch in "*?["):
        return path == pattern
    return fnmatch.fnmatchcase(path, pattern)


def portable_blob_id(path: Path) -> str:
    """Return a Git blob ID with text newlines canonicalized to LF."""
    data = path.read_bytes()
    if path.suffix.casefold() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def check_frozen() -> Result:
    started = time.monotonic()
    problems: list[str] = []
    try:
        expected, scopes = parse_frozen_manifest()
        present = tracked_and_untracked()
        for path, wanted in expected.items():
            full = ROOT / Path(path)
            if not full.is_file():
                problems.append(f"missing {path}")
                continue
            actual = portable_blob_id(full)
            if actual != wanted:
                problems.append(f"changed {path}")
        extras = sorted(
            path for path in present
            if any(matches(path, scope) for scope in scopes) and path not in expected
        )
        problems.extend(f"added {path}" for path in extras)
    except (OSError, ValueError) as exc:
        problems.append(str(exc))
    return Result(
        "Frozen assets", not problems,
        "" if not problems else short(problems), seconds=round(time.monotonic() - started, 2),
    )


def guarded_patterns() -> list[str]:
    patterns = []
    for raw in GUARDED_PATHS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def approval_trailers(base: str) -> set[str]:
    proc = git("log", "--format=%B%x00", f"{base}..HEAD", check=False)
    approved = set()
    for message in proc.stdout.split("\0"):
        for match in re.finditer(r"(?im)^Supervisor-Approved:\s*(\S.*?)\s*$", message):
            approved.add(match.group(1).strip().replace("\\", "/"))
    return approved


def check_guarded(base: str, changes: set[str]) -> Result:
    started = time.monotonic()
    try:
        patterns = guarded_patterns()
        guarded = sorted(path for path in changes if any(matches(path, p) for p in patterns))
        approved = approval_trailers(base)
        merge_in_progress = git_ref_exists("MERGE_HEAD")
        dirty = dirty_paths() if not merge_in_progress else set()
        def has_approval(path: str) -> bool:
            return path in approved

        missing = [path for path in guarded if not has_approval(path) or path in dirty]
        detail = ""
        if missing:
            detail = "REQUIRES SUPERVISOR APPROVAL: " + short(missing)
        return Result("Guarded paths", not missing, detail, seconds=round(time.monotonic() - started, 2))
    except (OSError, ValueError) as exc:
        return Result("Guarded paths", False, str(exc), seconds=round(time.monotonic() - started, 2))


def character_terms() -> list[str]:
    root = ROOT / "assets" / "characters"
    terms: dict[str, str] = {}
    if not root.is_dir():
        return []
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        terms.setdefault(directory.name.casefold(), directory.name)
        for spec_path in sorted((directory / "spec").glob("*.json")) if (directory / "spec").is_dir() else []:
            try:
                identity = json.loads(spec_path.read_text(encoding="utf-8")).get("identity", {})
            except (OSError, json.JSONDecodeError):
                continue
            for value in (identity.get("id"), identity.get("display_name")):
                if isinstance(value, str) and value.strip():
                    terms.setdefault(value.strip().casefold(), value.strip())
    return [terms[key] for key in sorted(terms)]


def is_test_source(path: str) -> bool:
    """Tests may name specific characters (regression checks of concrete assets); shared code may not."""
    name = Path(path).name
    return "/tests/" in f"/{path}" or name.startswith("test_") or name.endswith("_test.py")


def shared_source_paths() -> list[str]:
    return sorted(
        path for path in tracked_and_untracked()
        if path.startswith(SHARED_PREFIXES)
        and not path.startswith(CHARACTER_DATA_PREFIXES)
        and not is_test_source(path)
        and Path(path).suffix.lower() in CODE_SUFFIXES
        and (ROOT / Path(path)).is_file()
    )


def scan_character_occurrences() -> tuple[collections.Counter, dict[tuple, list[int]]]:
    counts: collections.Counter = collections.Counter()
    locations: dict[tuple, list[int]] = collections.defaultdict(list)
    terms = character_terms()
    for path in shared_source_paths():
        try:
            lines = (ROOT / Path(path)).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            folded = line.casefold()
            digest = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()
            for term in terms:
                count = folded.count(term.casefold())
                if count:
                    key = (path, term, digest)
                    counts[key] += count
                    locations[key].extend([number] * count)
    return counts, locations


def read_character_allowlist() -> collections.Counter:
    allowed: collections.Counter = collections.Counter()
    for number, raw in enumerate(CHARACTER_ALLOWLIST.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 4 or not fields[0].isdigit() or not re.fullmatch(r"[0-9a-f]{64}", fields[3]):
            raise ValueError(f"{CHARACTER_ALLOWLIST.relative_to(ROOT)}:{number}: malformed entry")
        count, path, term, digest = fields
        allowed[(path, term, digest)] += int(count)
    return allowed


def check_shared_character_lint() -> Result:
    started = time.monotonic()
    try:
        actual, locations = scan_character_occurrences()
        allowed = read_character_allowlist()
        violations: list[str] = []
        for key, count in sorted(actual.items()):
            excess = count - allowed[key]
            if excess > 0:
                path, term, _digest = key
                lines = locations[key][-excess:]
                violations.extend(f"{path}:{line} ({term})" for line in lines)
        return Result(
            "Shared-systems lint", not violations,
            "" if not violations else "new character reference: " + short(violations),
            seconds=round(time.monotonic() - started, 2),
        )
    except (OSError, ValueError) as exc:
        return Result("Shared-systems lint", False, str(exc), seconds=round(time.monotonic() - started, 2))


def display_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command)


def run_logged(command: list[str], log_path: Path, *, append: bool = False, env: dict | None = None) -> tuple[int, float]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log_path.open("a" if append else "w", encoding="utf-8", errors="replace") as log:
        log.write(f"$ {display_command(command)}\n")
        log.flush()
        try:
            proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
            code = proc.returncode
        except OSError as exc:
            log.write(f"could not start command: {exc}\n")
            code = 127
    return code, time.monotonic() - started


def relative_log(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def cmake_configure_command(build_dir: Path, config: str) -> list[str]:
    command = [
        "cmake", "-S", str(ROOT), "-B", str(build_dir),
        "-DPLUSH_BUILD_STUDIO=ON", "-DPLUSH_BUILD_TESTS=ON",
    ]
    if not os.environ.get("CMAKE_TOOLCHAIN_FILE") and os.environ.get("VCPKG_ROOT"):
        command.append(f"-DCMAKE_TOOLCHAIN_FILE={Path(os.environ['VCPKG_ROOT']) / 'scripts/buildsystems/vcpkg.cmake'}")
    if os.environ.get("CMAKE_TOOLCHAIN_FILE"):
        command.append(f"-DCMAKE_TOOLCHAIN_FILE={os.environ['CMAKE_TOOLCHAIN_FILE']}")
    if os.environ.get("PLUSH_OIDN_ROOT"):
        command.append(f"-DPLUSH_OIDN_ROOT={os.environ['PLUSH_OIDN_ROOT']}")
    if not os.environ.get("CMAKE_GENERATOR") and shutil.which("ninja"):
        command.extend(["-G", "Ninja"])
    if config and (os.environ.get("CMAKE_GENERATOR", "").lower() == "ninja" or "-G" in command):
        command.append(f"-DCMAKE_BUILD_TYPE={config}")
    return command


def check_cpp_build(build_dir: Path, config: str, logs: Path) -> Result:
    log = logs / "cpp-build.log"
    started = time.monotonic()
    if not shutil.which("cmake"):
        return Result("C++ build", False, "cmake not found", relative_log(log))
    code, _ = run_logged(cmake_configure_command(build_dir, config), log)
    if code == 0:
        command = ["cmake", "--build", str(build_dir), "--parallel"]
        if config:
            command.extend(["--config", config])
        code, _ = run_logged(command, log, append=True)
    return Result(
        "C++ build", code == 0, "" if code == 0 else f"see {relative_log(log)}",
        relative_log(log), round(time.monotonic() - started, 2),
    )


def check_ctest(build_dir: Path, config: str, logs: Path, build_ok: bool) -> Result:
    log = logs / "ctest.log"
    if not build_ok:
        return Result("CTest", False, "not run because C++ build failed", relative_log(log))
    command = ["ctest", "--test-dir", str(build_dir), "--output-on-failure"]
    if config:
        command.extend(["-C", config])
    code, seconds = run_logged(command, log)
    return Result("CTest", code == 0, "" if code == 0 else f"see {relative_log(log)}", relative_log(log), round(seconds, 2))


def plush_test_executable(build_dir: Path, config: str) -> Path | None:
    names = ["plush_tests.exe", "plush_tests"]
    candidates = []
    for name in names:
        candidates.extend((build_dir / "tests" / config / name, build_dir / "tests" / name))
    return next((path for path in candidates if path.is_file()), None)


def check_plush_tests(build_dir: Path, config: str, logs: Path, build_ok: bool) -> Result:
    log = logs / "plush-tests.log"
    if not build_ok:
        return Result("plush_tests", False, "not run because C++ build failed", relative_log(log))
    executable = plush_test_executable(build_dir, config)
    if executable is None:
        return Result("plush_tests", False, "test executable not found", relative_log(log))
    code, seconds = run_logged([str(executable)], log)
    return Result("plush_tests", code == 0, "" if code == 0 else f"see {relative_log(log)}", relative_log(log), round(seconds, 2))


def check_python_tests(logs: Path) -> Result:
    log = logs / "python-tests.log"
    tests = [
        [sys.executable, str(ROOT / "pipeline/clips/tests/test_clip_files.py"), "--selftest"],
        [sys.executable, str(ROOT / "tools/fidelity/tests/test_ci.py")],
    ]
    failed: list[str] = []
    started = time.monotonic()
    for index, command in enumerate(tests):
        code, _ = run_logged(command, log, append=index > 0)
        if code:
            failed.append(Path(command[1]).name)
    return Result(
        "Python tests", not failed,
        "" if not failed else f"failed: {short(failed)}; see {relative_log(log)}",
        relative_log(log), round(time.monotonic() - started, 2),
    )


def check_doc_links(logs: Path) -> Result:
    log = logs / "doc-links.log"
    code, seconds = run_logged([sys.executable, str(ROOT / "tools/check_doc_links.py")], log)
    return Result("Documentation links", code == 0, "" if code == 0 else f"see {relative_log(log)}", relative_log(log), round(seconds, 2))


def blender_paths_changed(changes: set[str]) -> bool:
    prefixes = (
        "assets/characters/", "pipeline/charsys/", "pipeline/blender/",
        "engine/render/", "apps/render-cli/", "content/materials/", "tests/regression/",
    )
    keywords = ("/material", "/groom", "/garment", "/render")
    for path in changes:
        lower = "/" + path.casefold()
        if path.startswith(prefixes) or any(word in lower for word in keywords):
            return True
    return False


def add_subcheck(subchecks: list[dict], name: str, ok: bool, detail: str = "", log: Path | None = None) -> None:
    subchecks.append({
        "name": name, "ok": bool(ok), "detail": detail,
        "log": relative_log(log) if log else "",
    })


def json_pass(path: Path, key: str = "pass") -> bool:
    try:
        return bool(json.loads(path.read_text(encoding="utf-8")).get(key))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def run_fidelity_checks(
    executable: str, changes: set[str], artifacts: Path, logs: Path,
) -> tuple[list[dict], list[str]]:
    """Run fidelity for affected characters and return subchecks plus summary details."""
    subchecks: list[dict] = []
    details: list[str] = []
    try:
        baseline = json.loads(FIDELITY_BASELINE.read_text(encoding="utf-8"))
        if baseline.get("schema") != "plush-studio.fidelity-baseline/1":
            raise ValueError("unsupported fidelity baseline schema")
        characters = baseline["characters"]
        affected = fidelity_ci.affected_characters(changes, set(characters))
        maximum_drop = float(baseline["policy"]["maximum_score_drop"])
        if maximum_drop != fidelity_ci.MAX_SCORE_DROP:
            raise ValueError(f"maximum score drop must be {fidelity_ci.MAX_SCORE_DROP:.1f}")
        if baseline["policy"]["failure_reason"] != "visual regression, needs owner review":
            raise ValueError("unexpected fidelity failure reason")
        height = int(baseline["render"]["height"])
        samples = int(baseline["render"]["samples"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        add_subcheck(subchecks, "character fidelity", False, f"invalid baseline: {exc}")
        return subchecks, details

    for character_id in affected:
        entry = characters[character_id]
        log = logs / f"fidelity-{character_id}.log"
        out = artifacts / "fidelity" / character_id
        try:
            build = fidelity_ci.repo_path(ROOT, entry["build"])
            overrides = [fidelity_ci.repo_path(ROOT, value) for value in entry.get("overrides", [])]
            if not build.is_file():
                raise ValueError(f"build input not found: {entry['build']}")
            missing = [str(path) for path in overrides if not path.is_file()]
            if missing:
                raise ValueError("override not found: " + ", ".join(missing))
            command = [
                sys.executable, str(ROOT / "tools/fidelity/run.py"),
                "--character", character_id,
                "--build", str(build),
                "--blender", executable,
                "--out", str(out),
                "--height", str(height),
                "--samples", str(samples),
            ]
            for override in overrides:
                command.extend(["--override", str(override)])
            code, _ = run_logged(command, log)
            if code:
                raise ValueError(f"run.py failed; see {relative_log(log)}")
            measured = json.loads((out / "fidelity.json").read_text(encoding="utf-8"))
            comparison = fidelity_ci.compare_score(
                measured["overall"]["score"], entry["score"], maximum_drop,
            )
            details.append(f"{character_id} {comparison.detail}")
            add_subcheck(
                subchecks, f"fidelity {character_id}", comparison.ok,
                comparison.detail, log,
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            detail = str(exc)
            details.append(f"{character_id} {detail}")
            add_subcheck(subchecks, f"fidelity {character_id}", False, detail, log)
    return subchecks, details


def check_blender(blender: str, artifacts: Path, logs: Path, required: bool, changes: set[str]) -> Result:
    if not required:
        return Result("Blender tier", True, skipped=True)
    started = time.monotonic()
    subchecks: list[dict] = []
    requested = blender or os.environ.get("BLENDER", "") or "blender"
    executable = shutil.which(requested) or requested
    if not Path(executable).is_file():
        return Result("Blender tier", False, "Blender executable not found")

    out = Path(tempfile.mkdtemp(prefix="blender-", dir=artifacts))

    verify_out = out / "verify-charsys"
    verify_log = logs / "blender-verify-charsys.log"
    command = [
        sys.executable, str(ROOT / "pipeline/charsys/verify_charsys.py"),
        "--blender", executable, "--out", str(verify_out),
    ]
    code, _ = run_logged(command, verify_log)
    verify_json = verify_out / "charsys_verification.json"
    try:
        verify_data = json.loads(verify_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        verify_data = {}
    verify_ok = code == 0 and verify_data.get("verdict") == "PASS"
    add_subcheck(subchecks, "verify_charsys", verify_ok, "" if verify_ok else "verification failed", verify_log)
    fingerprint_ok = bool(verify_data.get("v6_geometry", {}).get("ok"))
    add_subcheck(subchecks, "boy fingerprint", fingerprint_ok, "" if fingerprint_ok else "v6 geometry differs", verify_log)

    export_log = logs / "blender-export-engine.log"
    export_command = [
        sys.executable, str(ROOT / "pipeline/charsys/tests/test_export_engine.py"),
        "--blender", executable,
    ]
    export_code, _ = run_logged(export_command, export_log)
    add_subcheck(subchecks, "test_export_engine", export_code == 0, "" if export_code == 0 else "export tests failed", export_log)

    master = verify_out / "build" / "boy_yellow_hoodie_master.blend"
    face_log = logs / "blender-face.log"
    if master.is_file():
        face_command = [
            executable, "-b", "--factory-startup", "-P",
            str(ROOT / "pipeline/charsys/tests/face_test.py"), "--", str(master), str(out / "face"),
        ]
        face_code, _ = run_logged(face_command, face_log)
        face_ok = face_code == 0 and (out / "face" / "face_test.json").is_file()
    else:
        face_ok = False
        face_log.parent.mkdir(parents=True, exist_ok=True)
        face_log.write_text("verify_charsys did not produce a master\n", encoding="utf-8")
    add_subcheck(subchecks, "face tests", face_ok, "" if face_ok else "face tests failed", face_log)

    hair_script = ROOT / "pipeline/charsys/tests/hair_generic_test.py"
    hair_log = logs / "blender-hair-groom.log"
    hair_json = out / "hair_generic_test.json"
    hair_command = [executable, "-b", "--factory-startup", "-P", str(hair_script), "--", str(hair_json)]
    hair_code, _ = run_logged(hair_command, hair_log)
    hair_ok = hair_code == 0 and json_pass(hair_json)
    add_subcheck(subchecks, "hair/groom test", hair_ok, "" if hair_ok else "hair/groom test failed", hair_log)

    groom_script = ROOT / "pipeline/charsys/tests/groom_generic_test.py"
    if groom_script.is_file():
        groom_log = logs / "blender-groom.log"
        groom_json = out / "groom_generic_test.json"
        groom_command = [executable, "-b", "--factory-startup", "-P", str(groom_script), "--", str(groom_json)]
        groom_code, _ = run_logged(groom_command, groom_log)
        groom_ok = groom_code == 0 and json_pass(groom_json)
        add_subcheck(subchecks, "groom_generic_test", groom_ok, "" if groom_ok else "groom test failed", groom_log)

    garment_script = ROOT / "tests/garment_generic_test.py"
    if garment_script.is_file():
        garment_log = logs / "blender-garment.log"
        garment_command = [
            sys.executable, str(garment_script), "--blender", executable,
            "--out", str(out / "garment"), "--evidence-dir", str(out / "renders"),
        ]
        garment_code, _ = run_logged(garment_command, garment_log)
        add_subcheck(subchecks, "garment_generic_test", garment_code == 0, "" if garment_code == 0 else "garment test failed", garment_log)

    material_script = ROOT / "pipeline/charsys/tests/test_material_presets.py"
    if material_script.is_file():
        material_log = logs / "material-presets.log"
        material_code, _ = run_logged([sys.executable, str(material_script)], material_log)
        add_subcheck(subchecks, "material presets", material_code == 0, "" if material_code == 0 else "material preset tests failed", material_log)

    fidelity_subchecks, fidelity_details = run_fidelity_checks(executable, changes, artifacts, logs)
    subchecks.extend(fidelity_subchecks)

    failed = [item["name"] for item in subchecks if not item["ok"]]
    detail_parts = []
    if failed:
        detail_parts.append("failed: " + short(failed))
    if fidelity_details:
        detail_parts.append("; ".join(fidelity_details))
    return Result(
        "Blender tier", not failed,
        "; ".join(detail_parts),
        seconds=round(time.monotonic() - started, 2), subchecks=subchecks,
    )


def summary_lines(results: list[Result]) -> list[str]:
    lines = []
    for result in results:
        state = "PASS" if result.ok else "FAIL"
        line = f"{state} {result.name}"
        if result.name in {"Blender tier", "Merge status"} and result.detail:
            line += f": {result.detail.replace(chr(10), ' ')}"
        elif not result.ok and result.detail:
            line += f": {result.detail.replace(chr(10), ' ')}"
        lines.append(line)
    return lines


def resolve_path(value: str, fallback: Path) -> Path:
    path = Path(value) if value else fallback
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="", help="reference to compare for guarded paths and tier selection")
    parser.add_argument("--build-dir", default="build/quality-gate", help="CMake build directory")
    parser.add_argument("--artifacts-dir", default="build/check-all", help="logs and Blender output directory")
    parser.add_argument("--json", default="", help="JSON report path (default: <artifacts>/check_all.json)")
    parser.add_argument("--summary-file", default="", help="text summary path (default: <artifacts>/summary.txt)")
    parser.add_argument("--config", default="Release", help="CMake configuration")
    parser.add_argument("--blender", default="", help="Blender executable; supplying it always enables the Blender tier")
    parser.add_argument("--merge-status", default="", help="CI trial-merge status (normally 'clean')")
    args = parser.parse_args(argv)

    artifacts = resolve_path(args.artifacts_dir, ROOT / "build/check-all")
    build_dir = resolve_path(args.build_dir, ROOT / "build/quality-gate")
    json_path = resolve_path(args.json, artifacts / "check_all.json")
    summary_path = resolve_path(args.summary_file, artifacts / "summary.txt")
    logs = artifacts / "logs"
    artifacts.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    try:
        base = choose_base(args.base)
        changes = changed_paths(base)
    except ValueError as exc:
        print(f"FAIL Gate setup: {exc}")
        return 1

    results: list[Result] = [
        check_frozen(),
        check_guarded(base, changes),
        check_shared_character_lint(),
    ]
    build_result = check_cpp_build(build_dir, args.config, logs)
    results.append(build_result)
    results.append(check_ctest(build_dir, args.config, logs, build_result.ok))
    results.append(check_plush_tests(build_dir, args.config, logs, build_result.ok))
    results.append(check_python_tests(logs))
    results.append(check_doc_links(logs))
    blender_required = bool(args.blender) or blender_paths_changed(changes)
    results.append(check_blender(args.blender, artifacts, logs, blender_required, changes))
    if args.merge_status:
        tests_ok = all(result.ok for result in results)
        if args.merge_status == "clean" and tests_ok:
            results.append(Result("Merge status", True, "clean"))
        elif args.merge_status == "clean":
            results.append(Result("Merge status", False, "clean, tests FAIL after merge"))
        else:
            results.append(Result("Merge status", False, args.merge_status))

    lines = summary_lines(results)
    if len(lines) > 10:
        raise AssertionError("quality-gate summary exceeds 10 lines")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = {
        "schema": "plush.quality-gate/1",
        "verdict": "PASS" if all(result.ok for result in results) else "FAIL",
        "platform": sys.platform,
        "base": base,
        "changed_paths": sorted(changes),
        "blender_required": blender_required,
        "checks": [result.as_json() for result in results],
        "summary": lines,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
