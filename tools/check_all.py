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
import integrate
from regression import tiers as regression_tiers


ROOT = Path(__file__).resolve().parents[1]
FROZEN_MANIFEST = ROOT / "tools" / "frozen_manifest.txt"
GUARDED_PATHS = ROOT / "tools" / "guarded_paths.txt"
CHARACTER_ALLOWLIST = ROOT / "tools" / "shared_character_allowlist.txt"
FIDELITY_BASELINE = ROOT / "docs" / "evaluation" / "characters" / "fidelity_baseline.json"
REGRESSION_RUNNER = ROOT / "tools" / "regression" / "run.py"
WRITE_SET_BASE = "origin/staging"
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


def check_frozen_and_assets(base: str, logs: Path) -> Result:
    """Frozen manifest and the published character-version stores (tools/check_assets.py, T-075), one summary line."""
    frozen = check_frozen()
    log = logs / "check-assets.log"
    command = [sys.executable, str(ROOT / "tools/check_assets.py"), "--json", str(logs / "check_assets.json")]
    if base:
        command += ["--base", base]
    code, seconds = run_logged(command, log)
    assets = Result("Published versions", code == 0, "" if code == 0 else f"check_assets failed; see {relative_log(log)}",
                    relative_log(log), round(seconds, 2))
    subchecks = [{"name": r.name, "ok": r.ok, "detail": r.detail, "log": r.log} for r in (frozen, assets)]
    failed = [r.detail or r.name for r in (frozen, assets) if not r.ok]
    return Result("Frozen assets", not failed, "; ".join(failed), seconds=round(frozen.seconds + assets.seconds, 2),
                  subchecks=subchecks)


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


def current_branch() -> str:
    for name in ("CHECK_ALL_BRANCH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
        if os.environ.get(name):
            return os.environ[name]
    return git("branch", "--show-current", check=False).stdout.strip()


def check_write_set(task: str, base: str) -> Result:
    """Task branches may only change files inside their claim (docs/process/OWNERSHIP.md, plan section 3)."""
    started = time.monotonic()
    try:
        branch = current_branch()
        if task:
            claim = integrate.find_claim(task)
            label = task
        else:
            if not integrate.task_from_branch(branch):
                return Result("Write-set", True, f"not a task branch ({branch or 'detached'})",
                              seconds=round(time.monotonic() - started, 2))
            claim = integrate.claim_for_branch(branch)
            label = branch
        if claim is None or not claim.write_set:
            return Result("Write-set", False, f"no claim for {label} in docs/process/OWNERSHIP.md or docs/tasks",
                          seconds=round(time.monotonic() - started, 2))
        compare = WRITE_SET_BASE if git_ref_exists(WRITE_SET_BASE) else base
        if git_ref_exists("MERGE_HEAD"):
            # Trial merge with staging in progress: the merge result minus staging is exactly the task's change.
            common = compare
        else:
            common = git("merge-base", compare, "HEAD", check=False).stdout.strip() or compare
        paths = nul_paths(git("diff", "--name-only", "-z", common, "--").stdout)
        paths |= nul_paths(git("ls-files", "--others", "--exclude-standard", "-z").stdout)
        outside = integrate.write_set_violations(paths, claim)
        detail = f"{claim.task}: {len(paths)} changed path(s) vs {compare}, all inside the claim"
        if outside:
            detail = f"{claim.task} changes files outside its claim: " + short(outside)
        return Result("Write-set", not outside, detail, seconds=round(time.monotonic() - started, 2))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return Result("Write-set", False, str(exc), seconds=round(time.monotonic() - started, 2))


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


# T-127: one entry per command run_logged ran (gate report "durations" + durations.txt, slowest first).
DURATIONS: list[dict] = []


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
    seconds = time.monotonic() - started
    script = next((Path(part).name for part in command[1:] if part.endswith(".py")), Path(command[0]).name)
    DURATIONS.append({"log": relative_log(log_path), "script": script, "exit": code, "seconds": round(seconds, 2)})
    return code, seconds


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


def plush_render_executable(build_dir: Path, config: str) -> Path | None:
    names = ["plush-render.exe", "plush-render"]
    return next((p for n in names for p in (build_dir / "apps/render-cli" / config / n, build_dir / "apps/render-cli" / n)
                 if p.is_file()), None)


def check_animcheck(build_dir: Path, config: str, logs: Path, build_ok: bool) -> Result:
    """T-061: animation-principle metrics on the engine regression shots (tools/animcheck, thresholds.json)."""
    log = logs / "animcheck.log"
    if not build_ok:
        return Result("animcheck", False, "not run because C++ build failed", relative_log(log))
    render = plush_render_executable(build_dir, config)
    if render is None:
        return Result("animcheck", False, "plush-render not found", relative_log(log))
    command = [sys.executable, str(ROOT / "tools/animcheck/run_gate.py"), "--render", str(render),
               "--out", str(logs.parent / "animcheck")]
    code, seconds = run_logged(command, log)
    return Result("animcheck", code == 0, "" if code == 0 else f"see {relative_log(log)}", relative_log(log), round(seconds, 2))


def check_cpp_tests(build_dir: Path, config: str, logs: Path, build_ok: bool) -> Result:
    """CTest (incl. the frozen image regressions), the doctest binary and animcheck (T-061), reported on one line."""
    ctest = check_ctest(build_dir, config, logs, build_ok)
    doctest = check_plush_tests(build_dir, config, logs, build_ok)
    anim = check_animcheck(build_dir, config, logs, build_ok)
    subchecks = []
    for item in (ctest, doctest, anim):
        subchecks.append({"name": item.name, "ok": item.ok, "detail": item.detail, "log": item.log})
    failed = [f"{item.name} ({item.detail})" if item.detail else item.name for item in (ctest, doctest, anim) if not item.ok]
    return Result("C++ tests", not failed, "" if not failed else "failed: " + "; ".join(failed),
                  seconds=round(ctest.seconds + doctest.seconds + anim.seconds, 2), subchecks=subchecks)


def check_python_tests(logs: Path) -> Result:
    log = logs / "python-tests.log"
    tests = [
        [sys.executable, str(ROOT / "pipeline/clips/tests/test_clip_files.py"), "--selftest"],
        [sys.executable, str(ROOT / "tools/fidelity/tests/test_ci.py")],
        [sys.executable, str(ROOT / "tools/regression/tests/test_gate_tools.py")],
        [sys.executable, str(ROOT / "pipeline/production/tests/test_run_shot_current.py")],  # T-062 cast check
        [sys.executable, str(ROOT / "tools/animcheck/tests/test_animcheck.py")],  # T-061 animation metrics
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_versions.py")],  # T-043 version registry (T-077)
        [sys.executable, str(ROOT / "tools/fidelity/tests/test_metrics.py")],  # fidelity metric functions (T-077)
        [sys.executable, str(ROOT / "tools/fidelity/tests/test_metrics_v2.py")],  # T-153 opt-in score v2
        [sys.executable, str(ROOT / "tools/lipsync/test_lipsync.py")],  # T-054a lip sync (T-077)
        [sys.executable, str(ROOT / "tools/tests/test_version_switch.py")],  # T-088 version switch
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_materials_r2.py")],  # T-092 presets/3
        [sys.executable, str(ROOT / "pipeline/production/tests/test_sets.py")],  # T-098L set data
        [sys.executable, str(ROOT / "tools/fit/tests/test_fit.py")],  # T-090 fit optimiser
        [sys.executable, str(ROOT / "tests/props/test_props.py")],  # T-163 starter prop library
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_face_v3.py")],  # T-089 face/3 (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_face_v3b.py")],  # T-089b face polish (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_face_v4.py")],  # T-109 face round 4 (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_hair_r4.py")],  # T-091 groom/3 (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_hair_r5.py")],  # T-118 groom/4 (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_hands_r2.py")],  # T-121 hands_r2 (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_garments_r3.py")],  # T-119 garment/3 (plain checks)
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_expressions_r3.py")],  # T-113 expression sets (plain checks)
        [sys.executable, str(ROOT / "tests/acting/test_girl_signature.py")],  # T-097-girl acting signature
        [sys.executable, str(ROOT / "tests/acting/test_e909_beats.py")],  # T-114 e909 beats
        [sys.executable, str(ROOT / "tests/acting/test_boy_signature.py")],  # T-097-boy acting signature
        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_boy2_face.py")],  # T-058 spec checks, no Blender (T-077)
        [sys.executable, str(ROOT / "tools/ci/tests/test_t127_shards.py")],  # T-127 shard plan, verdict, inventory
        [sys.executable, str(ROOT / "tools/tests/test_task_kit.py")],  # T-165 opt-in task kit
    ]
    cleanup_tests = ROOT / "tools/cleanup/run_tests.py"  # T-048 branch-cleanup tests, once merged
    if cleanup_tests.is_file():
        tests.append([sys.executable, str(cleanup_tests)])
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


def check_python_and_links(logs: Path) -> Result:
    """Python tests and the Markdown link check, reported on one line (the summary has at most 10 lines)."""
    tests, links = check_python_tests(logs), check_doc_links(logs)
    subchecks = [{"name": r.name, "ok": r.ok, "detail": r.detail, "log": r.log} for r in (tests, links)]
    failed = [f"{r.name} ({r.detail})" if r.detail else r.name for r in (tests, links) if not r.ok]
    return Result("Python tests and links", not failed, "" if not failed else "failed: " + "; ".join(failed),
                  seconds=round(tests.seconds + links.seconds, 2), subchecks=subchecks)


def select_tier(changes: set[str]) -> dict:
    """fast or full (tools/regression_paths.txt; unknown paths are full)."""
    try:
        return regression_tiers.classify(changes)
    except (OSError, ValueError) as exc:
        return {"tier": "full", "full_paths": [], "unknown_paths": [], "paths": {}, "error": str(exc)}


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


def regression_subchecks(report: dict, log: Path | None) -> tuple[list[dict], list[str]]:
    subchecks: list[dict] = []
    details: list[str] = []
    results = report.get("results", [])
    expected = regression_tiers.character_ids()
    seen = {item.get("character") for item in results}
    for missing in sorted(set(expected) - seen):
        add_subcheck(subchecks, f"regression {missing}", False, "no regression result (character not covered)", log)
    for item in results:
        failed = [c for c in item.get("checks", []) if not c.get("ok")]
        kind = ("references only, not buildable yet" if item.get("not_buildable") else
                "unchanged" if item.get("unchanged") else "spec changed")
        fidelity = item.get("measured", {}).get("fidelity")
        note = f"fidelity {fidelity['score']:.2f}" if fidelity else ""
        detail = "; ".join(f"{c['name']}: {c['detail']}" for c in failed) or (
            kind if item.get("not_buildable") else f"{kind}, identical{', ' + note if note else ''}")
        if item.get("unchanged") is False and not failed:
            detail = f"spec changed, needs owner visual review{', ' + note if note else ''}"
        add_subcheck(subchecks, f"regression {item.get('character')}", item.get("ok", False) and not failed, detail, log)
        details.append(f"{item.get('character')} {'PASS' if item.get('ok') and not failed else 'FAIL'}"
                       + (f" ({note})" if note else ""))
    return subchecks, details


def run_regression(executable: str, base: str, artifacts: Path, logs: Path, results_dir: str,
                   external: str = "") -> tuple[list[dict], list[str]]:
    """All-character regression + unchanged-character guard (tools/regression/run.py), or its CI results."""
    log = logs / "regression.log"
    if external:
        # CI: one job per character runs tools/regression/run.py in parallel; the "Gate verdict" job requires a
        # passing report from each of them. Recorded here so the report says where the regression ran.
        subchecks: list[dict] = []
        add_subcheck(subchecks, "character regression", True,
                     f"runs in {external} ({', '.join(regression_tiers.character_ids())}); required by the verdict")
        return subchecks, [f"in {external}"]
    if results_dir:
        reports = sorted(Path(results_dir).rglob("regression.json"))
        merged: dict = {"results": []}
        for path in reports:
            try:
                merged["results"].extend(json.loads(path.read_text(encoding="utf-8")).get("results", []))
            except (OSError, json.JSONDecodeError) as exc:
                merged["results"].append({"character": path.parent.name, "ok": False,
                                          "checks": [{"name": "report", "ok": False, "detail": str(exc)}]})
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("results from " + ", ".join(p.as_posix() for p in reports) + "\n", encoding="utf-8")
        return regression_subchecks(merged, log)
    out = artifacts / "regression"
    command = [sys.executable, str(REGRESSION_RUNNER), "--blender", executable, "--out", str(out), "--base", base]
    if git_ref_exists("origin/main"):
        command += ["--against", "origin/main"]  # unchanged characters: identical to main built on this machine
    run_logged(command, log)
    try:
        report = json.loads((out / "regression.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        subchecks: list[dict] = []
        add_subcheck(subchecks, "regression", False, f"runner produced no report; see {relative_log(log)}", log)
        return subchecks, []
    return regression_subchecks(report, log)


def current_published_masters() -> dict[str, Path | str]:
    """Per character of the fidelity baseline: the published master of its current approved version (run_shot's
    "current" resolution), or the reason there is none."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_shot_for_gate", ROOT / "pipeline/production/run_shot.py")
    run_shot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_shot)
    baseline = json.loads((ROOT / "docs/evaluation/characters/fidelity_baseline.json").read_text(encoding="utf-8"))
    masters: dict[str, Path | str] = {}
    for cid in sorted(baseline.get("characters", {})):
        try:
            source = run_shot.current_source(cid, str(ROOT))
        except SystemExit as exc:
            masters[cid] = f"no current version: {exc.code}"
            continue
        vdir = source.get("version_dir")
        found = sorted((ROOT / vdir).glob("*_master.blend")) if vdir else []
        masters[cid] = found[0] if found else f"current version {source['resolved']['version']} has no published master"
    return masters


# --- Blender tier (T-127: split into named units so CI can run them in parallel shards) -----------------------------
# Every unit runs exactly the commands it ran before T-127, in the same order inside the unit. Units with an internal
# dependency stay one unit (verify_charsys -> face tests on its master; the boy 2.0.0-dev build -> its two tests), so
# no built character is shared between units (owner decision T-127: item 6 not approved). Without --blender-shard the
# units run in this order on one runner, which is the pre-T-127 behaviour (local runs and the CI fallback path).
BLENDER_SHARDS_FILE = ROOT / "tools" / "ci" / "blender_shards.json"


@dataclasses.dataclass
class BlenderContext:
    executable: str
    out: Path
    logs: Path
    artifacts: Path
    changes: set[str]
    tier: dict
    base: str
    regression_results: str
    regression_external: str
    engine: Path | None
    subchecks: list[dict]
    details: dict = dataclasses.field(default_factory=dict)


def unit_charsys(c: BlenderContext) -> None:
    executable, out, logs, subchecks = c.executable, c.out, c.logs, c.subchecks
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


def unit_face(c: BlenderContext) -> None:
    # Reads the master verify_charsys built in this run (as before T-127): always in the same shard as "charsys".
    executable, out, logs, subchecks = c.executable, c.out, c.logs, c.subchecks
    master = out / "verify-charsys" / "build" / "boy_yellow_hoodie_master.blend"
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


def unit_determinism(c: BlenderContext) -> None:
    # Build the boy twice and compare format-2 fingerprints (pipeline/charsys/fingerprint_v2.py) at 0.01 mm and 0.1 mm.
    determinism_log = c.logs / "blender-determinism.log"
    determinism_out = c.out / "determinism"
    determinism_command = [
        sys.executable, str(ROOT / "pipeline/charsys/tests/test_determinism.py"),
        "--blender", c.executable, "--out", str(determinism_out),
    ]
    determinism_code, _ = run_logged(determinism_command, determinism_log)
    determinism_ok = determinism_code == 0 and json_pass(determinism_out / "determinism.json")
    add_subcheck(c.subchecks, "build determinism", determinism_ok, "" if determinism_ok else "two builds differ",
                 determinism_log)


def unit_build_determinism_girl(c: BlenderContext) -> None:
    # T-158: build the current girl (0.13.0) twice; before T-158 her ears / upper lids changed between runs by ~1e-8 m
    # (below the 0.01 mm fingerprint grid, hence --strict: 1e-7 m mesh hashes with shape keys).
    log = c.logs / "blender-build-determinism-girl.log"
    out = c.out / "build-determinism-girl"
    code, _ = run_logged([sys.executable, str(ROOT / "pipeline/charsys/tests/test_determinism.py"), "--blender",
                          c.executable, "--out", str(out), "--character", "girl_auburn_bun_glasses", "--runs", "2",
                          "--jobs", "2", "--strict"], log)
    ok = code == 0 and json_pass(out / "determinism.json")
    add_subcheck(c.subchecks, "build determinism girl", ok, "" if ok else "two girl builds differ", log)


def unit_export_engine(c: BlenderContext) -> None:
    export_log = c.logs / "blender-export-engine.log"
    export_command = [
        sys.executable, str(ROOT / "pipeline/charsys/tests/test_export_engine.py"),
        "--blender", c.executable,
    ]
    export_code, _ = run_logged(export_command, export_log)
    add_subcheck(c.subchecks, "test_export_engine", export_code == 0, "" if export_code == 0 else "export tests failed",
                 export_log)


def unit_hair(c: BlenderContext) -> None:
    hair_script = ROOT / "pipeline/charsys/tests/hair_generic_test.py"
    hair_log = c.logs / "blender-hair-groom.log"
    hair_json = c.out / "hair_generic_test.json"
    hair_command = [c.executable, "-b", "--factory-startup", "-P", str(hair_script), "--", str(hair_json)]
    hair_code, _ = run_logged(hair_command, hair_log)
    hair_ok = hair_code == 0 and json_pass(hair_json)
    add_subcheck(c.subchecks, "hair/groom test", hair_ok, "" if hair_ok else "hair/groom test failed", hair_log)


def unit_hair_curves(c: BlenderContext) -> None:
    # T-141 opt-in native hair curves: the test launches Blender itself (--blender), so it runs in the Blender tier.
    log = c.logs / "blender-hair-curves.log"
    code, _ = run_logged([sys.executable, str(ROOT / "pipeline/charsys/tests/test_hair_curves.py"), "--blender",
                          c.executable], log)
    add_subcheck(c.subchecks, "hair curves (T-141)", code == 0, "" if code == 0 else "hair curves test failed", log)


def unit_groom(c: BlenderContext) -> None:
    groom_script = ROOT / "pipeline/charsys/tests/groom_generic_test.py"
    if groom_script.is_file():
        groom_log = c.logs / "blender-groom.log"
        groom_json = c.out / "groom_generic_test.json"
        groom_command = [c.executable, "-b", "--factory-startup", "-P", str(groom_script), "--", str(groom_json)]
        groom_code, _ = run_logged(groom_command, groom_log)
        groom_ok = groom_code == 0 and json_pass(groom_json)
        add_subcheck(c.subchecks, "groom_generic_test", groom_ok, "" if groom_ok else "groom test failed", groom_log)


def unit_garment(c: BlenderContext) -> None:
    garment_script = ROOT / "tests/garment_generic_test.py"
    if garment_script.is_file():
        garment_log = c.logs / "blender-garment.log"
        garment_command = [
            sys.executable, str(garment_script), "--blender", c.executable,
            "--out", str(c.out / "garment"), "--evidence-dir", str(c.out / "renders"),
        ]
        garment_code, _ = run_logged(garment_command, garment_log)
        add_subcheck(c.subchecks, "garment_generic_test", garment_code == 0,
                     "" if garment_code == 0 else "garment test failed", garment_log)


def unit_material_presets(c: BlenderContext) -> None:
    material_script = ROOT / "pipeline/charsys/tests/test_material_presets.py"
    if material_script.is_file():
        material_log = c.logs / "material-presets.log"
        material_code, _ = run_logged([sys.executable, str(material_script)], material_log)
        add_subcheck(c.subchecks, "material presets", material_code == 0,
                     "" if material_code == 0 else "material preset tests failed", material_log)


def t077_unit(name: str, command_for, json_for=None):
    """T-077 (from T-071): self-contained Blender tests that ran nowhere before (each a few seconds). Slow shot-level
    tests stay nightly/local (docs/evaluation/process/T-077)."""
    def run(c: BlenderContext) -> None:
        json_out = json_for(c) if json_for else None
        log = c.logs / f"blender-{name.replace(' ', '-')}.log"
        code, _ = run_logged(command_for(c), log)
        ok = code == 0 and (json_out is None or json_pass(json_out))
        add_subcheck(c.subchecks, name, ok, "" if ok else f"{name} failed", log)
    return run


def unit_boy2(c: BlenderContext) -> None:
    # The shared boy 2.0.0-dev build (about a minute) and the two tests that read it: one unit, never shared further.
    executable = c.executable
    boy2_log = c.logs / "blender-boy2.log"
    boy2_out = c.out / "boy2"
    boy2_code, _ = run_logged([
        executable, "-b", "--factory-startup", "-P", str(ROOT / "pipeline/charsys/build_character.py"), "--",
        "--spec", str(ROOT / "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json"),
        "--out", str(boy2_out), "--no-glb", "--no-compare",
    ], boy2_log)
    boy2_master = boy2_out / "boy_yellow_hoodie_master.blend"
    for script in ("test_boy2_face.py", "test_hoodie.py"):
        if boy2_code == 0 and boy2_master.is_file():
            code, _ = run_logged([sys.executable, str(ROOT / "pipeline/charsys/tests" / script), "--blender", executable,
                                  "--master", str(boy2_master)], boy2_log, append=True)
        else:
            code = 1
        add_subcheck(c.subchecks, script[:-3], code == 0, "" if code == 0 else f"{script} failed", boy2_log)


def unit_deform(c: BlenderContext) -> None:
    """T-101: deform_test on each current published master (a measurement without limits: it fails when a pose
    control is missing or a mesh cannot be measured; docs/evaluation/process/T-077 §4)."""
    for cid, master in current_published_masters().items():
        name = f"deform_test {cid}"
        log = c.logs / f"blender-deform-{cid}.log"
        if not isinstance(master, Path):
            log.write_text(f"{master}\n", encoding="utf-8")
            add_subcheck(c.subchecks, name, False, master, log)
            continue
        code, _ = run_logged([c.executable, "-b", "--factory-startup", "-P",
                              str(ROOT / "pipeline/charsys/tests/deform_test.py"),
                              "--", str(master), str(c.out / f"deform-{cid}")], log)
        ok = code == 0 and (c.out / f"deform-{cid}" / "deform_test.json").is_file()
        add_subcheck(c.subchecks, name, ok, "" if ok else "deform_test failed", log)


def unit_shot_eyes(c: BlenderContext) -> None:
    """T-101: test_shot_eyes runs its shot with cast "current" (needs plush-render for the bake)."""
    if c.engine is None:
        add_subcheck(c.subchecks, "test_shot_eyes", False, "plush-render not found (needed for the bake)")
        return
    log = c.logs / "blender-shot-eyes.log"
    code, _ = run_logged([sys.executable, str(ROOT / "pipeline/charsys/tests/test_shot_eyes.py"), "--blender",
                          c.executable, "--cast", "current", "--bake-engine", str(c.engine)], log)
    add_subcheck(c.subchecks, "test_shot_eyes", code == 0, "" if code == 0 else "test_shot_eyes failed", log)


def unit_emotions(c: BlenderContext) -> None:
    """T-101: test_emotions runs its shot with cast "current" (needs plush-render for the bake)."""
    if c.engine is None:
        add_subcheck(c.subchecks, "test_emotions", False, "plush-render not found (needed for the bake)")
        return
    # The emotion scenes and bakes must sit inside the repository (the engine finds content/ above a scene) and are
    # large, so they go to build/test_tmp; only the measurements are copied next to the other artifacts.
    tmp_root = ROOT / "build" / "test_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    emo_out = Path(tempfile.mkdtemp(prefix="check_all_emotions_", dir=tmp_root))
    log = c.logs / "blender-emotions.log"
    code, _ = run_logged([sys.executable, str(ROOT / "pipeline/clips/test_emotions.py"), "--blender", c.executable,
                          "--engine", str(c.engine), "--out", str(emo_out)], log)
    measurements = emo_out / "emotion_measurements.json"
    if measurements.is_file():
        shutil.copy2(measurements, c.out / "emotion_measurements.json")
    shutil.rmtree(emo_out, ignore_errors=True)
    add_subcheck(c.subchecks, "test_emotions", code == 0, "" if code == 0 else "test_emotions failed", log)


def unit_fidelity_regression(c: BlenderContext) -> None:
    if c.tier.get("tier") == "full":
        # The full regression measures fidelity for every character, so the affected-character run is not repeated.
        regression, c.details["regression"] = run_regression(c.executable, c.base, c.artifacts, c.logs,
                                                             c.regression_results, c.regression_external)
        c.subchecks.extend(regression)
    else:
        fidelity_subchecks, c.details["fidelity"] = run_fidelity_checks(c.executable, c.changes, c.artifacts, c.logs)
        c.subchecks.extend(fidelity_subchecks)


# (unit id, function, needs plush-render). Order = the pre-T-127 order of check_blender (t101 split into its three
# tests, which ran in this order). Add new Blender tests here; tools/ci/blender_shards.json assigns them to a shard
# (an unassigned unit runs in shard 1, never nowhere).
BLENDER_UNITS: list[tuple[str, object, bool]] = [
    ("charsys", unit_charsys, False),
    ("determinism", unit_determinism, False),
    ("build-determinism-girl", unit_build_determinism_girl, False),  # T-158
    ("export-engine", unit_export_engine, False),
    ("face", unit_face, False),
    ("hair", unit_hair, False),
    ("hair-curves", unit_hair_curves, False),  # T-141
    ("face-front-fade", t077_unit("face front fade (T-159)", lambda c: [sys.executable, str(ROOT / "pipeline/charsys/tests/test_face_front_fade.py"), "--blender", c.executable]), False),
    ("ears-shape", t077_unit("ears shape (T-159)", lambda c: [sys.executable, str(ROOT / "pipeline/charsys/tests/test_ears_shape.py"), "--blender", c.executable]), False),
    ("glasses-rest", t077_unit("glasses rest on ear (T-159)", lambda c: [sys.executable, str(ROOT / "pipeline/charsys/tests/test_glasses_rest.py"), "--blender", c.executable]), False),
    ("groom", unit_groom, False),
    ("garment", unit_garment, False),
    ("material-presets", unit_material_presets, False),
    ("render-engine-selector", t077_unit("render engine selector", lambda c: [
        c.executable, "-b", "--factory-startup", "-P", str(ROOT / "pipeline/charsys/tests/test_render_engine.py")]), False),
    ("materials-r2-graphs", t077_unit("materials r2 graphs", lambda c: [  # T-092
        c.executable, "-b", "--factory-startup", "-P",
        str(ROOT / "pipeline/charsys/tests/test_materials_r2_graphs.py")]), False),
    ("garments-v2-quick", t077_unit("garments v2 quick", lambda c: [  # T-093 pin + validate (full run: local)
        sys.executable, str(ROOT / "pipeline/charsys/tests/test_garments_v2.py"), "--blender", c.executable,
        "--quick"]), False),
    ("groom-dynamics", t077_unit("groom dynamics", lambda c: [
        c.executable, "-b", "--factory-startup", "-P", str(ROOT / "pipeline/charsys/tests/groom_dynamics_test.py"),
        "--", str(c.out / "groom_dynamics_test.json")], lambda c: c.out / "groom_dynamics_test.json"), False),
    ("export-determinism", t077_unit("export determinism", lambda c: [
        sys.executable, str(ROOT / "pipeline/charsys/tests/test_export_determinism.py"), "--blender", c.executable,
        "--out", str(c.out / "export-determinism")]), False),
    ("boy2", unit_boy2, False),
    ("deform", unit_deform, False),
    ("shot-eyes", unit_shot_eyes, True),
    ("emotions", unit_emotions, True),
    ("fidelity-regression", unit_fidelity_regression, False),
]
BLENDER_UNIT_IDS = [unit_id for unit_id, _, _ in BLENDER_UNITS]
BLENDER_UNIT_DEPENDS = {"face": "charsys"}  # unit -> the unit whose output it reads (same shard, same run)


def blender_shard_plan(path: Path = BLENDER_SHARDS_FILE) -> dict:
    """{"count": N, "shards": {"1": [unit ids], ...}} with every unit in exactly one shard. Unassigned units go to
    shard 1; an unknown or duplicated unit id in the file is an error (stale plan), never silently dropped."""
    data = json.loads(path.read_text(encoding="utf-8"))
    count = int(data["count"])
    if not 1 <= count <= 8:
        raise ValueError(f"{path.name}: count {count} outside 1..8")
    shards = {str(k): list(data["shards"].get(str(k), [])) for k in range(1, count + 1)}
    extra = set(data["shards"]) - set(shards)
    if extra:
        raise ValueError(f"{path.name}: shards {sorted(extra)} beyond count {count}")
    seen: list[str] = [unit for units in shards.values() for unit in units]
    unknown = sorted(set(seen) - set(BLENDER_UNIT_IDS))
    duplicates = sorted({unit for unit in seen if seen.count(unit) > 1})
    if unknown or duplicates:
        raise ValueError(f"{path.name}: unknown units {unknown}, duplicated units {duplicates}")
    shards["1"].extend(unit for unit in BLENDER_UNIT_IDS if unit not in seen)
    for unit, needed in BLENDER_UNIT_DEPENDS.items():
        if not any(unit in units and needed in units for units in shards.values()):
            raise ValueError(f"{path.name}: unit {unit} must be in the same shard as {needed}")
    return {"count": count, "shards": shards}


def parse_shard(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)/(\d+)", value or "")
    if not match or not 1 <= int(match.group(1)) <= int(match.group(2)):
        raise ValueError(f"--blender-shard must be K/N with 1 <= K <= N, got {value!r}")
    return int(match.group(1)), int(match.group(2))


def check_blender(blender: str, artifacts: Path, logs: Path, required: bool, changes: set[str],
                  tier: dict | None = None, base: str = "", regression_results: str = "",
                  regression_external: str = "", other_runner: str = "", engine: Path | None = None,
                  units: list[str] | None = None, shards_external: str = "") -> Result:
    """units: run only these Blender units (one CI shard); None runs every unit in order on this runner.
    shards_external: CI only, the units run in these separate shard jobs; the verdict requires every shard."""
    tier = tier or {"tier": "fast"}
    if other_runner:
        return Result("Blender tier", True, f"{tier.get('tier', 'fast')} tier; runs on the {other_runner} (not on "
                      f"{sys.platform})", skipped=True)
    if not required:
        return Result("Blender tier", True, f"not required: fast tier ({len(changes)} changed path(s), none full)",
                      skipped=True)
    if shards_external:
        subchecks: list[dict] = []
        add_subcheck(subchecks, "blender shards", True,
                     f"{len(BLENDER_UNIT_IDS)} units run in {shards_external}; the verdict requires every shard")
        return Result("Blender tier", True, f"{tier.get('tier', 'fast')} tier; runs in {shards_external}",
                      subchecks=subchecks)
    full = tier.get("tier") == "full"
    started = time.monotonic()
    subchecks = []
    requested = blender or os.environ.get("BLENDER", "") or "blender"
    executable = shutil.which(requested) or requested
    if not Path(executable).is_file():
        why = "full regression required by " + short(tier.get("full_paths", []), 3) if full else "--blender given"
        return Result("Blender tier", False, f"Blender executable not found ({why}); this tier is never skipped")

    out = Path(tempfile.mkdtemp(prefix="blender-", dir=artifacts))
    context = BlenderContext(executable, out, logs, artifacts, changes, tier, base, regression_results,
                             regression_external, engine, subchecks)
    selected = BLENDER_UNIT_IDS if units is None else units
    for unit_id, function, _needs_engine in BLENDER_UNITS:
        if unit_id in selected:
            function(context)

    regression_details = context.details.get("regression", [])
    fidelity_details = context.details.get("fidelity", [])
    failed = [item["name"] for item in subchecks if not item["ok"]]
    detail_parts = [f"{tier.get('tier', 'fast')} tier"]
    if failed:
        detail_parts.append("failed: " + short(failed))
    if regression_details:
        detail_parts.append("regression " + ", ".join(regression_details))
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
        if result.name in {"Blender tier", "Merge status", "Write-set"} and result.detail:
            line += f": {result.detail.replace(chr(10), ' ')}"
        elif not result.ok and result.detail:
            line += f": {result.detail.replace(chr(10), ' ')}"
        else:
            skipped = [f"{item['name']} {item['detail']}" for item in result.subchecks if item.get("skipped")]
            if skipped:
                line += ": " + "; ".join(skipped)
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
    parser.add_argument("--task", default=os.environ.get("CHECK_ALL_TASK", ""),
                        help="task ID for the Write-set check (default: from the branch name / OWNERSHIP.md branch)")
    parser.add_argument("--full", action="store_true", help="force the full tier (all-character regression)")
    parser.add_argument("--regression-results", default="",
                        help="folder with regression.json files from tools/regression/run.py (CI per-character jobs)")
    parser.add_argument("--regression-external", default="",
                        help="CI only: the character regression runs in these separate jobs (verdict requires them)")
    parser.add_argument("--blender-on-other-runner", default="",
                        help="CI only: the Blender tier runs on this other runner (reported, never silent)")
    parser.add_argument("--blender-shard", default="",
                        help="CI only (T-127): K/N, run only the Blender units of shard K of tools/ci/blender_shards.json")
    parser.add_argument("--blender-shards-external", default="",
                        help="CI only (T-127): the Blender units run in these shard jobs (verdict requires all of them)")
    parser.add_argument("--list-blender-units", action="store_true",
                        help="print the Blender units and the shard plan as JSON and exit")
    args = parser.parse_args(argv)
    if args.list_blender_units:
        print(json.dumps({"units": BLENDER_UNIT_IDS, "plan": blender_shard_plan(),
                          "engine_units": [unit for unit, _, needs in BLENDER_UNITS if needs]}))
        return 0

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

    if args.blender_shard:
        return blender_shard_main(args, base, changes, artifacts, build_dir, json_path, summary_path, logs)

    results: list[Result] = [
        check_frozen_and_assets(base, logs),
        check_guarded(base, changes),
        check_write_set(args.task, base),
        check_shared_character_lint(),
    ]
    build_result = check_cpp_build(build_dir, args.config, logs)
    results.append(build_result)
    results.append(check_cpp_tests(build_dir, args.config, logs, build_result.ok))
    results.append(check_python_and_links(logs))
    tier = select_tier(changes)
    if args.full:
        tier["tier"] = "full"
    blender_required = bool(args.blender) or tier["tier"] == "full"
    results.append(check_blender(args.blender, artifacts, logs, blender_required, changes, tier, base,
                                 args.regression_results, args.regression_external, args.blender_on_other_runner,
                                 plush_render_executable(build_dir, args.config) if build_result.ok else None,
                                 shards_external=args.blender_shards_external if blender_required else ""))
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
        "blender_units": BLENDER_UNIT_IDS if blender_required and args.blender_shards_external else [],
        "tier": tier["tier"],
        "tier_full_paths": tier.get("full_paths", []),
        "tier_unknown_paths": tier.get("unknown_paths", []),
        "checks": [result.as_json() for result in results],
        "summary": lines,
    }
    return write_report(report, json_path, lines)


def write_report(report: dict, json_path: Path, lines: list[str]) -> int:
    report["durations"] = sorted(DURATIONS, key=lambda item: -item["seconds"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    durations = [f"{item['seconds']:8.1f} s  {'ok  ' if item['exit'] == 0 else 'FAIL'}  {item['script']}  ({item['log']})"
                 for item in report["durations"]]
    (json_path.parent / "durations.txt").write_text("\n".join(durations) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if report["verdict"] == "PASS" else 1


def build_render_engine(build_dir: Path, config: str, logs: Path) -> tuple[Path | None, dict]:
    """Shard mode: the plush-render target only (the bake engine of test_shot_eyes/test_emotions), same configure."""
    log = logs / "blender-plush-render-build.log"
    code, _ = run_logged(cmake_configure_command(build_dir, config), log)
    if code == 0:
        command = ["cmake", "--build", str(build_dir), "--parallel", "--target", "plush-render"]
        if config:
            command.extend(["--config", config])
        code, _ = run_logged(command, log, append=True)
    engine = plush_render_executable(build_dir, config) if code == 0 else None
    item = {"name": "plush-render build", "ok": engine is not None,
            "detail": "" if engine else "plush-render build failed (needed for the bake)", "log": relative_log(log)}
    return engine, item


def blender_shard_main(args, base: str, changes: set[str], artifacts: Path, build_dir: Path, json_path: Path,
                       summary_path: Path, logs: Path) -> int:
    """T-127: one CI shard of the Blender tier. The other checks run in the linux gate job; this report carries only
    "Blender tier" plus the shard identity and unit list, which the verdict compares with the full unit list."""
    try:
        index, count = parse_shard(args.blender_shard)
        plan = blender_shard_plan()
        if plan["count"] != count:
            raise ValueError(f"shard count {count} differs from tools/ci/blender_shards.json ({plan['count']})")
        units = plan["shards"][str(index)]
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        index, count, units = 0, 0, []
        result = Result("Blender tier", False, f"shard setup: {exc}")
    else:
        tier = select_tier(changes)
        if args.full:
            tier["tier"] = "full"
        engine, engine_item = None, None
        if any(needs for unit_id, _, needs in BLENDER_UNITS if unit_id in units):
            engine, engine_item = build_render_engine(build_dir, args.config, logs)
        result = check_blender(args.blender, artifacts, logs, True, changes, tier, base, args.regression_results,
                               args.regression_external, "", engine, units=units)
        if engine_item and not engine_item["ok"]:
            result.subchecks.insert(0, engine_item)
            result.ok = False
        result.detail = f"shard {index}/{count} ({', '.join(units)}): {result.detail}"
    lines = summary_lines([result])
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = {
        "schema": "plush.quality-gate/1",
        "verdict": "PASS" if result.ok else "FAIL",
        "platform": f"linux-blender-{index}",
        "base": base,
        "blender_shard": {"index": index, "count": count, "units": units},
        "checks": [result.as_json()],
        "summary": lines,
    }
    return write_report(report, json_path, lines)


if __name__ == "__main__":
    raise SystemExit(main())
