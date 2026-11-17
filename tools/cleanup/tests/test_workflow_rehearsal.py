#!/usr/bin/env python3
"""Rehearsal of .github/workflows/cleanup.yml: its real shell steps, run against a scratch remote.

The `cleanup` job's run steps are taken verbatim from the workflow file and executed with bash in a scratch
directory laid out like the runner (main/ = tools from this checkout, request/ = clone of the scratch remote on
branch cleanup-request). `gh` is replaced by a fake that returns a successful backup.yml history and confirms
dry-run runs. Covers: guard, gathering, dry run + log commit to cleanup-request, delete + CLEANUP_LOG commit,
main untouched, guard refusal when the request branch carries a different workflow. Linux/macOS only (the workflow
runs on ubuntu).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scratch_repo import CLEANUP_DIR, GIT_ENV, SUCCESS_RUNS, ScratchRepo, git  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO_ROOT = CLEANUP_DIR.parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/cleanup.yml"
STEPS = ["Guard - request branch must run the workflow from main",
         "Gather backup.yml results, open tasks and dry-run confirmations",
         "Decide and (in mode delete) delete",
         "Commit logs to cleanup-request (never to main)"]

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
if args[:1] != ["api"]:
    sys.exit(2)
url = args[1]
if "/actions/workflows/backup.yml/runs" in url:
    print(open(os.environ["FAKE_BACKUP_RUNS"]).read())
    sys.exit(0)
m = re.search(r"/actions/runs/(\d+)$", url)
if m:
    print(json.dumps({"id": int(m.group(1)), "path": ".github/workflows/cleanup.yml", "conclusion": "success",
                      "status": "completed", "head_branch": "cleanup-request"}))
    sys.exit(0)
sys.exit(1)
'''


@unittest.skipIf(yaml is None or os.name == "nt" or shutil.which("bash") is None, "needs PyYAML and bash")
class WorkflowRehearsal(unittest.TestCase):
    def setUp(self):
        self.repo = ScratchRepo()
        root = self.repo.root
        self.steps = {}
        for job in yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"].values():
            for step in job["steps"]:
                if "run" in step:
                    self.steps[step.get("name")] = step["run"]
        # main of the scratch remote carries the same workflow file (the guard compares against it).
        workflow_copy = self.repo.work / ".github/workflows/cleanup.yml"
        workflow_copy.parent.mkdir(parents=True)
        shutil.copy(WORKFLOW, workflow_copy)
        git(self.repo.work, "add", ".github")
        git(self.repo.work, "commit", "-q", "-m", "add cleanup workflow")
        git(self.repo.work, "push", "-q", "origin", "main")
        # Runner layout.
        self.runner_dir = root / "runner-ws"
        (self.runner_dir / "main/tools").mkdir(parents=True)
        shutil.copytree(CLEANUP_DIR, self.runner_dir / "main/tools/cleanup",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (self.runner_dir / "main/docs/process").mkdir(parents=True)
        (self.runner_dir / "main/docs/process/TASK_LOG.md").write_text(
            "| ID | Task | State | Branch |\n| --- | --- | --- | --- |\n| T-1 | x | assigned | cleanup-test/open |\n",
            encoding="utf-8")
        bin_dir = root / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH, encoding="utf-8")
        (bin_dir / "gh").chmod(0o755)
        (root / "backup-runs.json").write_text(json.dumps(SUCCESS_RUNS), encoding="utf-8")
        self.summary = root / "summary.md"
        self.env = {**os.environ, **GIT_ENV, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_BACKUP_RUNS": str(root / "backup-runs.json"), "GITHUB_REPOSITORY": "scratch/repo",
                    "GITHUB_STEP_SUMMARY": str(self.summary), "WORK": str(root / "work-tmp"), "GH_TOKEN": "x"}

    def tearDown(self):
        self.repo.close()

    def push_request(self, mode: str, branches) -> None:
        work = self.repo.work
        exists = git(self.repo.remote, "for-each-ref", "refs/heads/cleanup-request")
        if exists:
            git(work, "fetch", "-q", "origin", "cleanup-request")
            git(work, "checkout", "-q", "-B", "cleanup-request", "FETCH_HEAD")
        else:
            git(work, "checkout", "-q", "-B", "cleanup-request", "main")
        request = work / "cleanup/REQUEST.json"
        request.parent.mkdir(exist_ok=True)
        request.write_text(json.dumps({"mode": mode, "branches": branches, "requested_by": "rehearsal",
                                       "reason": "throwaway"}), encoding="utf-8")
        git(work, "add", "cleanup/REQUEST.json")
        git(work, "commit", "-q", "-m", f"cleanup request {mode}")
        git(work, "push", "-q", "origin", "cleanup-request")
        git(work, "checkout", "-q", "main")

    def run_job(self, run_id: str) -> list[int]:
        request = self.runner_dir / "request"
        if request.exists():
            shutil.rmtree(request)
        git(self.runner_dir, "clone", "-q", "-b", "cleanup-request", str(self.repo.remote), "request")
        codes = []
        for name in STEPS:
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.steps[name]], cwd=self.runner_dir,
                                    env={**self.env, "GITHUB_RUN_ID": run_id}, capture_output=True, text=True)
            codes.append(result.returncode)
            if result.returncode != 0:
                self.last_output = result.stdout + result.stderr
                break
        return codes

    def remote_file(self, path: str) -> str:
        return git(self.repo.remote, "show", f"cleanup-request:{path}")

    def test_dry_run_then_delete(self):
        repo = self.repo
        sha_a = repo.merged_backed_up("cleanup-test/a")
        repo.merged_backed_up("cleanup-test/open")
        unmerged = repo.branch_with_commit("cleanup-test/unmerged")
        main_before = repo.remote_sha("main")
        branches = ["cleanup-test/a", "cleanup-test/open", "cleanup-test/unmerged"]

        self.push_request("dry-run", branches)
        self.assertEqual(self.run_job("501"), [0, 0, 0, 0])
        self.assertIsNotNone(repo.remote_sha("cleanup-test/a"))
        record = json.loads(self.remote_file("cleanup/DRY_RUN_LOG.jsonl").splitlines()[-1])
        self.assertEqual(record["run_id"], "501")
        self.assertEqual(record["would_delete"], {"cleanup-test/a": sha_a})
        self.assertIn("would-delete", self.summary.read_text(encoding="utf-8"))

        self.push_request("delete", branches)
        self.assertEqual(self.run_job("502"), [0, 0, 0, 0])
        self.assertIsNone(repo.remote_sha("cleanup-test/a"))
        self.assertIsNotNone(repo.remote_sha("cleanup-test/open"))
        self.assertEqual(repo.remote_sha("cleanup-test/unmerged"), unmerged)
        log = self.remote_file("docs/process/CLEANUP_LOG.md")
        self.assertIn(f"| cleanup-test/a | {sha_a} |", log)
        self.assertEqual(repo.remote_sha("main"), main_before, "the workflow never writes to main")
        self.assertNotIn("CLEANUP_LOG", git(repo.remote, "ls-tree", "-r", "--name-only", "main"))
        # restore with the documented line
        git(repo.work, "push", "-q", "origin", f"{sha_a}:refs/heads/cleanup-test/a")
        self.assertEqual(repo.remote_sha("cleanup-test/a"), sha_a)

    def test_guard_refuses_modified_workflow_on_request_branch(self):
        sha_a = self.repo.merged_backed_up("cleanup-test/a")
        self.push_request("dry-run", ["cleanup-test/a"])
        work = self.repo.work
        git(work, "fetch", "-q", "origin", "cleanup-request")
        git(work, "checkout", "-q", "-B", "cleanup-request", "FETCH_HEAD")
        with open(work / ".github/workflows/cleanup.yml", "a", encoding="utf-8") as handle:
            handle.write("# tampered\n")
        git(work, "commit", "-q", "-am", "tamper")
        git(work, "push", "-q", "origin", "cleanup-request")
        git(work, "checkout", "-q", "main")
        self.assertEqual(self.run_job("601"), [1])
        self.assertIn("differs from main", self.last_output)
        self.assertEqual(self.repo.remote_sha("cleanup-test/a"), sha_a)


if __name__ == "__main__":
    unittest.main(verbosity=1)
