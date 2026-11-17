"""Gate tier selection and character bookkeeping for the full regression (delivery plan §5.1/§5.2).

Pure Python (no Blender). Used by tools/check_all.py, tools/regression/run.py and the CI planning job:

    python tools/regression/tiers.py --base origin/staging [--github-output $GITHUB_OUTPUT]

prints the tier ("fast" or "full"), the deciding paths and the character list as JSON.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PATHS_FILE = ROOT / "tools" / "regression_paths.txt"
CHARACTERS = ROOT / "assets" / "characters"
FIDELITY_BASELINE = ROOT / "docs" / "evaluation" / "characters" / "fidelity_baseline.json"
BASELINES = ROOT / "docs" / "evaluation" / "regression" / "baselines"
DEFAULT_PROFILE = "pipeline/charsys/rig_profiles/humanoid_rigify.json"
TEXT_SUFFIXES = {".json", ".md", ".txt", ".py"}

sys.path.insert(0, str(ROOT / "tools"))
import integrate  # noqa: E402  (shared glob matcher)


def load_rules(path: Path = PATHS_FILE) -> list[tuple[str, str]]:
    rules = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or parts[0] not in {"fast", "full"}:
            raise ValueError(f"{path.name}:{number}: expected '<fast|full> <glob>'")
        rules.append((parts[0], parts[1].strip()))
    return rules


def classify_path(path: str, rules: list[tuple[str, str]]) -> tuple[str, str]:
    """Return (tier, rule) for one path; unknown paths are 'full'."""
    for tier, pattern in rules:
        if integrate.path_matches(path, pattern):
            return tier, pattern
    return "full", "(unknown path)"


def classify(paths, rules: list[tuple[str, str]] | None = None) -> dict:
    rules = load_rules() if rules is None else rules
    per_path = {path: classify_path(path, rules) for path in sorted(paths)}
    full = [path for path, (tier, _rule) in per_path.items() if tier == "full"]
    unknown = [path for path, (_tier, rule) in per_path.items() if rule == "(unknown path)"]
    return {"tier": "full" if full else "fast", "full_paths": full, "unknown_paths": unknown,
            "paths": {path: {"tier": tier, "rule": rule} for path, (tier, rule) in per_path.items()}}


def portable_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if path.suffix.casefold() in TEXT_SUFFIXES else data


def character_ids() -> list[str]:
    return sorted(p.name for p in CHARACTERS.iterdir() if p.is_dir()) if CHARACTERS.is_dir() else []


def character_config(cid: str, root: Path = ROOT) -> dict:
    """Build inputs of the character's current version in the checkout `root`: the spec plus the overrides named in
    the fidelity baseline (the single list of current character versions). Raises ValueError when the character
    cannot be regressed."""
    spec = root / "assets" / "characters" / cid / "spec" / f"{cid}.spec.json"
    rel = spec.relative_to(root).as_posix()
    if not spec.is_file():
        raise ValueError(f"{cid}: no spec at {rel}")
    fidelity_baseline = root / FIDELITY_BASELINE.relative_to(ROOT)
    baseline = json.loads(fidelity_baseline.read_text(encoding="utf-8"))
    entry = baseline.get("characters", {}).get(cid)
    if entry is None:
        raise ValueError(f"{cid}: not listed in {FIDELITY_BASELINE.relative_to(ROOT).as_posix()}")
    if entry.get("build") != rel:
        raise ValueError(f"{cid}: fidelity baseline builds {entry.get('build')}, expected the character spec")
    overrides = list(entry.get("overrides", []))
    inputs = [rel, *overrides]
    for item in inputs:
        if not (root / item).is_file():
            raise ValueError(f"{cid}: build input missing: {item}")
    resolved = json.loads(spec.read_text(encoding="utf-8"))
    version = resolved.get("metadata", {}).get("spec_version", "")
    for item in overrides:
        data = json.loads((root / item).read_text(encoding="utf-8")).get("override", {})
        version = data.get("metadata", {}).get("spec_version", version)
    digest = hashlib.sha256()
    for item in inputs:
        digest.update(item.encode() + b"\0" + portable_bytes(root / item) + b"\0")
    profile = resolved.get("rig", {}).get("engine_profile", DEFAULT_PROFILE)
    return {"character": cid, "spec": inputs[0], "overrides": overrides, "inputs": inputs,
            "spec_version": version or "unversioned", "spec_inputs_sha256": digest.hexdigest(),
            "profile": profile, "fidelity": entry, "root": str(root)}


def git_changed(base: str) -> set[str]:
    common = subprocess.run(["git", "merge-base", base, "HEAD"], cwd=ROOT, text=True, capture_output=True)
    ref = common.stdout.strip() if common.returncode == 0 and common.stdout.strip() else base
    out = subprocess.run(["git", "diff", "--name-only", "-z", ref, "--"], cwd=ROOT, text=True,
                         capture_output=True, check=True).stdout
    return {p for p in out.split("\0") if p}


def changed_characters(paths, ids: list[str] | None = None) -> list[str]:
    """Characters whose spec or override inputs changed (pin-bump / look tasks). All others must stay identical."""
    ids = character_ids() if ids is None else ids
    changed = []
    for cid in ids:
        prefix = f"assets/characters/{cid}/spec/"
        try:
            inputs = set(character_config(cid)["inputs"])
        except (ValueError, OSError, json.JSONDecodeError):
            inputs = set()
        if any(p.startswith(prefix) or p in inputs for p in paths):
            changed.append(cid)
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--github-output", default="")
    a = ap.parse_args(argv)
    paths = git_changed(a.base)
    result = classify(paths)
    result.pop("paths")
    result["characters"] = character_ids()
    result["changed_characters"] = changed_characters(paths)
    print(json.dumps(result, indent=1))
    if a.github_output:
        with open(a.github_output, "a", encoding="utf-8") as out:
            out.write(f"tier={result['tier']}\n")
            out.write(f"characters={json.dumps(result['characters'])}\n")
            out.write(f"changed_characters={','.join(result['changed_characters'])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
