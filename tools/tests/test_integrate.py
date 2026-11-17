#!/usr/bin/env python3
"""Local-only integration tests for tools/integrate.py."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
INTEGRATE = SOURCE_ROOT / "tools" / "integrate.py"
TEST_PARENT = SOURCE_ROOT / "build"


class IntegrationRepository:
    def __init__(self) -> None:
        TEST_PARENT.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="integrate-test-", dir=TEST_PARENT)
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin.git"
        self.seed = self.root / "seed"
        self.worker = self.root / "worker"
        self.env = os.environ.copy()
        self.env.update({
            "GIT_AUTHOR_NAME": "Integration Test",
            "GIT_AUTHOR_EMAIL": "integration@example.invalid",
            "GIT_COMMITTER_NAME": "Integration Test",
            "GIT_COMMITTER_EMAIL": "integration@example.invalid",
            "GIT_TERMINAL_PROMPT": "0",
        })
        self.run(self.root, "git", "init", "--bare", str(self.origin))
        self.run(self.root, "git", "init", "--initial-branch=main", str(self.seed))
        (self.seed / "tools").mkdir()
        (self.seed / "docs" / "process").mkdir(parents=True)
        shutil.copy2(INTEGRATE, self.seed / "tools" / "integrate.py")
        (self.seed / "tools" / "check_all.py").write_text(textwrap.dedent("""\
            import argparse
            from pathlib import Path
            parser = argparse.ArgumentParser()
            parser.add_argument('--base')
            parser.add_argument('--blender')
            parser.add_argument('--build-dir')
            parser.add_argument('--fast', action='store_true')
            parser.parse_args()
            raise SystemExit(1 if Path('gate-fail').exists() else 0)
            """), encoding="utf-8")
        (self.seed / "tools" / "guarded_paths.txt").write_text("", encoding="utf-8")
        (self.seed / "docs" / "process" / "TASK_LOG.md").write_text(
            "# Task log\n\n| ID | Task | State | Commit / branch | Notes |\n"
            "| --- | --- | --- | --- | --- |\n", encoding="utf-8")
        (self.seed / "shared.txt").write_text("base\n", encoding="utf-8")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "initial")
        self.git(self.seed, "remote", "add", "origin", str(self.origin))
        self.git(self.seed, "push", "origin", "main", "main:staging")
        self.run(self.root, "git", "clone", str(self.origin), str(self.worker))
        self.git(self.worker, "config", "user.name", "Integration Test")
        self.git(self.worker, "config", "user.email", "integration@example.invalid")

    def close(self) -> None:
        self.temp.cleanup()

    def run(self, cwd: Path, *command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            list(command), cwd=cwd, env=self.env, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if check and proc.returncode:
            self.fail_command(command, proc)
        return proc

    @staticmethod
    def fail_command(command: tuple[str, ...], proc: subprocess.CompletedProcess[str]) -> None:
        raise AssertionError(f"command failed: {command}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    def git(self, cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run(cwd, "git", *args, check=check)

    def output(self, cwd: Path, *args: str) -> str:
        return self.git(cwd, *args).stdout.strip()

    def branch(self, name: str, filename: str, content: str) -> str:
        self.git(self.worker, "checkout", "--detach", "origin/staging")
        self.git(self.worker, "checkout", "-b", name)
        (self.worker / filename).write_text(content, encoding="utf-8")
        self.git(self.worker, "add", filename)
        self.git(self.worker, "commit", "-m", f"add {filename}")
        self.git(self.worker, "push", "-u", "origin", name)
        return self.output(self.worker, "rev-parse", "HEAD")

    def integrate(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run(self.worker, sys.executable, "tools/integrate.py", *args, check=check)


class IntegrateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = IntegrationRepository()

    def tearDown(self) -> None:
        self.repo.close()

    def test_clean_stage_and_revert(self) -> None:
        self.repo.branch("t-101-clean", "feature.txt", "clean\n")
        self.repo.integrate("stage", "t-101-clean", "--fast")
        staging = self.repo.output(self.repo.worker, "ls-remote", "origin", "refs/heads/staging").split()[0]
        self.repo.git(self.repo.worker, "fetch", "origin")
        message = self.repo.output(self.repo.worker, "show", "-s", "--format=%B", staging)
        self.assertIn("Gate-Result: PASS", message)
        log = self.repo.output(self.repo.worker, "show", "origin/staging:docs/process/TASK_LOG.md")
        self.assertIn("t-101-clean", log)
        merge = self.repo.output(self.repo.worker, "rev-parse", f"{staging}^")
        self.assertEqual(2, len(self.repo.output(self.repo.worker, "show", "-s", "--format=%P", merge).split()))

        self.repo.integrate("revert", merge)
        self.repo.git(self.repo.worker, "fetch", "origin")
        files = self.repo.output(self.repo.worker, "ls-tree", "-r", "--name-only", "origin/staging").splitlines()
        self.assertNotIn("feature.txt", files)
        self.assertTrue(self.repo.output(self.repo.worker, "show", "-s", "--format=%s", "origin/staging").startswith("Revert"))

    def test_conflict_aborts_without_changing_staging(self) -> None:
        old_staging = self.repo.output(self.repo.worker, "rev-parse", "origin/staging")
        self.repo.branch("t-102-conflict", "shared.txt", "task\n")
        self.repo.git(self.repo.worker, "checkout", "--detach", old_staging)
        (self.repo.worker / "shared.txt").write_text("staging\n", encoding="utf-8")
        self.repo.git(self.repo.worker, "add", "shared.txt")
        self.repo.git(self.repo.worker, "commit", "-m", "staging change")
        self.repo.git(self.repo.worker, "push", "origin", "HEAD:staging")
        before = self.repo.output(self.repo.worker, "ls-remote", "origin", "refs/heads/staging").split()[0]

        result = self.repo.integrate("stage", "t-102-conflict", "--fast", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("shared.txt", result.stderr)
        after = self.repo.output(self.repo.worker, "ls-remote", "origin", "refs/heads/staging").split()[0]
        self.assertEqual(before, after)

    def test_promote_fast_forward_and_prune_safety(self) -> None:
        self.repo.git(self.repo.worker, "checkout", "--detach", "origin/staging")
        (self.repo.worker / "promoted.txt").write_text("yes\n", encoding="utf-8")
        self.repo.git(self.repo.worker, "add", "promoted.txt")
        self.repo.git(self.repo.worker, "commit", "-m", "green staging", "-m", "Gate-Result: PASS")
        self.repo.git(self.repo.worker, "push", "origin", "HEAD:staging", "HEAD:refs/heads/topic-merged")

        self.repo.git(self.repo.worker, "checkout", "--detach", "origin/main")
        (self.repo.worker / "unmerged.txt").write_text("keep\n", encoding="utf-8")
        self.repo.git(self.repo.worker, "add", "unmerged.txt")
        self.repo.git(self.repo.worker, "commit", "-m", "unmerged work")
        unmerged = self.repo.output(self.repo.worker, "rev-parse", "HEAD")
        self.repo.git(self.repo.worker, "push", "origin", "HEAD:refs/heads/topic-unmerged")

        backup = self.repo.root / "backups"
        self.repo.integrate("promote", "--backup-dir", str(backup), "--prune", "topic-*", "--fast")
        main = self.repo.output(self.repo.worker, "ls-remote", "origin", "refs/heads/main").split()[0]
        staging = self.repo.output(self.repo.worker, "ls-remote", "origin", "refs/heads/staging").split()[0]
        self.assertEqual(staging, main)
        refs = self.repo.output(self.repo.worker, "ls-remote", "--heads", "origin")
        self.assertNotIn("refs/heads/topic-merged", refs)
        self.assertIn(f"{unmerged}\trefs/heads/topic-unmerged", refs)
        bundles = list(backup.glob("*.bundle"))
        self.assertEqual(1, len(bundles))
        self.repo.git(self.repo.worker, "bundle", "verify", str(bundles[0]))


if __name__ == "__main__":
    unittest.main()
