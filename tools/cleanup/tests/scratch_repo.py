"""Scratch git repositories for the cleanup tests: a local bare "remote" plus a work clone.

Nothing here touches the real repository: every repository lives in a fresh temporary directory, git runs with an
isolated configuration, and the only remote is a local bare repository.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

CLEANUP_DIR = Path(__file__).resolve().parents[1]

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "cleanup-test",
    "GIT_AUTHOR_EMAIL": "cleanup-test@example.invalid",
    "GIT_COMMITTER_NAME": "cleanup-test",
    "GIT_COMMITTER_EMAIL": "cleanup-test@example.invalid",
    "GIT_TERMINAL_PROMPT": "0",
}


def isolate_git_environment() -> None:
    os.environ.update(GIT_ENV)


def load(name: str, filename: str):
    """Load a module from tools/cleanup by path (select.py must never shadow the stdlib ``select``)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, CLEANUP_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_cli():
    module = load("plush_cleanup_cli", "cleanup.py")
    return module


def load_select():
    return load_cli().sel


def git(cwd, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                            env={**os.environ, **GIT_ENV})
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {result.stderr}")
    return result.stdout.strip()


class ScratchRepo:
    """remote.git (bare, the 'origin') + work/ (a clone used to build history) + runner/ (where cleanup runs)."""

    def __init__(self):
        isolate_git_environment()
        self._temp = tempfile.TemporaryDirectory(prefix="plush-cleanup-test-")
        self.root = Path(self._temp.name)
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self.runner = self.root / "runner"
        git(self.root, "init", "--bare", "-b", "main", str(self.remote))
        git(self.root, "init", "-b", "main", str(self.work))
        git(self.work, "remote", "add", "origin", str(self.remote))
        self.commit("README.md", "scratch base\n", "base")
        git(self.work, "push", "origin", "main")
        git(self.root, "clone", "-q", str(self.remote), str(self.runner))
        self._counter = 0

    def close(self):
        self._temp.cleanup()

    # history helpers ------------------------------------------------------------------------------------------
    def commit(self, path: str, text: str, message: str) -> str:
        file = self.work / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        git(self.work, "add", path)
        git(self.work, "commit", "-q", "-m", message)
        return git(self.work, "rev-parse", "HEAD")

    def branch_with_commit(self, name: str) -> str:
        """Create ``name`` from main with one commit, push it, return its tip."""
        self._counter += 1
        git(self.work, "checkout", "-q", "main")
        git(self.work, "checkout", "-q", "-b", name)
        sha = self.commit(f"work/{self._counter}.txt", f"{name}\n", f"work on {name}")
        git(self.work, "push", "-q", "origin", f"{name}:refs/heads/{name}")
        git(self.work, "checkout", "-q", "main")
        return sha

    def merge_into_main(self, name: str) -> None:
        git(self.work, "checkout", "-q", "main")
        git(self.work, "merge", "-q", "--no-ff", "-m", f"merge {name}", name)
        git(self.work, "push", "-q", "origin", "main")

    def add_commit_to(self, name: str) -> str:
        self._counter += 1
        git(self.work, "checkout", "-q", name)
        sha = self.commit(f"work/{self._counter}.txt", "after merge\n", f"more work on {name}")
        git(self.work, "push", "-q", "origin", f"{name}:refs/heads/{name}")
        git(self.work, "checkout", "-q", "main")
        return sha

    def backup_tag(self, sha: str, label: str) -> None:
        """Simulate T-041's backup job: a backup/<UTC date-time>/<branch> tag on the remote."""
        git(self.work, "push", "-q", "origin", f"{sha}:refs/tags/backup/20261117T000000Z/{label}")

    def archive_backup_branch(self, sha: str, label: str) -> None:
        git(self.work, "push", "-q", "origin", f"{sha}:refs/heads/archive/backup-20261117-{label}")

    def merged_backed_up(self, name: str) -> str:
        sha = self.branch_with_commit(name)
        self.merge_into_main(name)
        self.backup_tag(sha, name)
        return sha

    def remote_sha(self, name: str) -> str | None:
        out = git(self.remote, "for-each-ref", "--format=%(objectname)", f"refs/heads/{name}")
        return out or None

    def remote_refs(self) -> dict[str, str]:
        out = git(self.remote, "for-each-ref", "--format=%(objectname) %(refname)")
        return {ref: sha for sha, ref in (line.split(" ", 1) for line in out.splitlines() if line)}


SUCCESS_RUNS = {"workflow_runs": [
    {"id": 2, "head_branch": "main", "status": "completed", "conclusion": "success",
     "created_at": "2026-11-17T02:17:00Z"},
    {"id": 1, "head_branch": "main", "status": "completed", "conclusion": "failure",
     "created_at": "2026-11-16T02:17:00Z"},
]}


def verified_run_info(run_id: str) -> dict:
    return {run_id: {"id": int(run_id), "path": ".github/workflows/cleanup.yml", "conclusion": "success"}}
