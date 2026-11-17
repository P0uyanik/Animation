#!/usr/bin/env python3
"""End-to-end test of the cleanup runner on throwaway ``cleanup-test/*`` branches (T-048 AC4).

Everything happens in a scratch directory: a local bare repository is the remote. Steps: create branches, merge
some into the scratch main, simulate T-041's backup tags and backup.yml result, dry run, refused delete without a
verified dry run, delete, verify the deletion and the pinning tag, restore from CLEANUP_LOG.md and verify the SHA.
Run: python3 tools/cleanup/tests/test_end_to_end.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scratch_repo  # noqa: E402
from scratch_repo import CLEANUP_DIR, GIT_ENV, SUCCESS_RUNS, ScratchRepo, git, verified_run_info  # noqa: E402

cli = scratch_repo.load_cli()
sel = cli.sel
CLI = str(CLEANUP_DIR / "cleanup.py")

TASK_LOG = """| ID | Task | State | Commit / branch |
| --- | --- | --- | --- |
| T-1 | open work | assigned | cleanup-test/open-task |
"""


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.repo = ScratchRepo()
        self.files = self.repo.root / "files"
        self.files.mkdir()
        self.paths = {name: str(self.files / name) for name in (
            "REQUEST.json", "TASK_LOG.md", "backup-runs.json", "DRY_RUN_LOG.jsonl", "verified.json",
            "CLEANUP_LOG.md", "summary.md", "decisions.json")}
        Path(self.paths["TASK_LOG.md"]).write_text(TASK_LOG, encoding="utf-8")
        Path(self.paths["backup-runs.json"]).write_text(json.dumps(SUCCESS_RUNS), encoding="utf-8")

    def tearDown(self):
        self.repo.close()

    def run_cli(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess:
        # cwd = tools/cleanup on purpose: select.py next to the CLI must not shadow the stdlib module.
        result = subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True, cwd=CLEANUP_DIR,
                                env={**os.environ, **GIT_ENV})
        self.assertEqual(result.returncode, expect, f"{args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def write_request(self, mode: str, branches) -> None:
        Path(self.paths["REQUEST.json"]).write_text(json.dumps(
            {"mode": mode, "branches": branches, "requested_by": "e2e test", "reason": "throwaway branches"}),
            encoding="utf-8")

    def cleanup(self, run_id: str, allow_delete: bool = True, expect: int = 0) -> dict:
        p = self.paths
        args = ["run", "--repo", str(self.repo.runner), "--request", p["REQUEST.json"], "--task-log", p["TASK_LOG.md"],
                "--backup-runs", p["backup-runs.json"], "--dry-run-log", p["DRY_RUN_LOG.jsonl"],
                "--verified-runs", p["verified.json"], "--cleanup-log", p["CLEANUP_LOG.md"],
                "--summary", p["summary.md"], "--run-id", run_id, "--decisions-json", p["decisions.json"]]
        self.run_cli(*args, *(["--allow-delete"] if allow_delete else []), expect=expect)
        data = json.loads(Path(p["decisions.json"]).read_text(encoding="utf-8"))
        return {d["branch"]: d for d in data["decisions"]}

    def test_full_cycle(self):
        repo = self.repo
        merged_a = repo.merged_backed_up("cleanup-test/merged-a")
        merged_b = repo.merged_backed_up("cleanup-test/merged-b")
        late = repo.merged_backed_up("cleanup-test/late-commit")
        unmerged = repo.branch_with_commit("cleanup-test/unmerged")
        repo.backup_tag(unmerged, "cleanup-test/unmerged")
        open_task = repo.merged_backed_up("cleanup-test/open-task")
        branches = ["cleanup-test/merged-a", "cleanup-test/merged-b", "cleanup-test/late-commit",
                    "cleanup-test/unmerged", "cleanup-test/open-task", "cleanup-test/missing"]
        before = repo.remote_refs()

        # 1. Dry run: nothing deleted, record written.
        self.write_request("dry-run", branches)
        dry = self.cleanup("101")
        self.assertEqual(repo.remote_refs(), before, "a dry run must not change any remote ref")
        self.assertEqual({b for b, d in dry.items() if d["action"] == "would-delete"},
                         {"cleanup-test/merged-a", "cleanup-test/merged-b", "cleanup-test/late-commit"})
        self.assertIn("not merged", dry["cleanup-test/unmerged"]["reason"])
        self.assertIn("open TASK_LOG row", dry["cleanup-test/open-task"]["reason"])
        self.assertIn("unknown branch", dry["cleanup-test/missing"]["reason"])
        records = sel.parse_dry_run_log(Path(self.paths["DRY_RUN_LOG.jsonl"]).read_text(encoding="utf-8"))
        self.assertEqual(len(records), 1)
        hash_ = self.run_cli("hash", "--request", self.paths["REQUEST.json"]).stdout.strip()
        self.assertEqual(records[0]["request_hash"], hash_)
        self.assertIn(hash_, Path(self.paths["summary.md"]).read_text(encoding="utf-8"))

        # 2. Delete with the same content but the dry run not (yet) confirmed by GitHub: refused.
        self.write_request("delete", branches)
        self.assertEqual(self.run_cli("hash", "--request", self.paths["REQUEST.json"]).stdout.strip(), hash_)
        self.assertEqual(self.run_cli("runs-to-verify", "--request", self.paths["REQUEST.json"],
                                      "--dry-run-log", self.paths["DRY_RUN_LOG.jsonl"]).stdout.split(), ["101"])
        refused = self.cleanup("102")
        self.assertFalse([d for d in refused.values() if d["action"] != "skip"])
        self.assertEqual(repo.remote_refs(), before)

        # 3. A different request content (other branch list) is never approved by this dry run.
        self.write_request("delete", branches[:2])
        Path(self.paths["verified.json"]).write_text(json.dumps(verified_run_info("101")), encoding="utf-8")
        other = self.cleanup("103")
        self.assertFalse([d for d in other.values() if d["action"] != "skip"])
        self.assertEqual(repo.remote_refs(), before)

        # 4. Someone pushes to late-commit after the dry run: it is no longer merged and stays.
        late_new = repo.add_commit_to("cleanup-test/late-commit")
        before = repo.remote_refs()

        # 5. mode delete without --allow-delete: nothing happens.
        self.write_request("delete", branches)
        self.cleanup("104", allow_delete=False)
        self.assertEqual(repo.remote_refs(), before)

        # 6. Real delete against the local bare remote.
        deleted = self.cleanup("105")
        self.assertEqual({b for b, d in deleted.items() if d["action"] == "deleted"},
                         {"cleanup-test/merged-a", "cleanup-test/merged-b"})
        self.assertIsNone(repo.remote_sha("cleanup-test/merged-a"))
        self.assertIsNone(repo.remote_sha("cleanup-test/merged-b"))
        self.assertEqual(repo.remote_sha("cleanup-test/late-commit"), late_new)
        self.assertEqual(repo.remote_sha("cleanup-test/unmerged"), unmerged)
        self.assertEqual(repo.remote_sha("cleanup-test/open-task"), open_task)
        self.assertNotEqual(late, late_new)
        refs = repo.remote_refs()
        pins = {ref: sha for ref, sha in refs.items() if ref.startswith("refs/tags/backup/") and
                ref.endswith("/cleanup-test/merged-a") and "20261117T000000Z" not in ref}
        self.assertEqual(list(pins.values()), [merged_a], "a fresh backup tag pins the deleted tip")
        log = Path(self.paths["CLEANUP_LOG.md"]).read_text(encoding="utf-8")
        entries = sel.parse_cleanup_log(log)
        self.assertEqual({(e["branch"], e["sha"], e["request_hash"]) for e in entries},
                         {("cleanup-test/merged-a", merged_a, hash_), ("cleanup-test/merged-b", merged_b, hash_)})
        self.assertIn("git push origin <sha>:refs/heads/<name>", log)

        # 7. Running the same delete again deletes nothing more (already gone = unknown branch).
        again = self.cleanup("106")
        self.assertFalse([d for d in again.values() if d["action"] == "deleted"])

        # 8. Restore from the log and verify the SHA; a second restore is refused.
        self.run_cli("restore", "--repo", str(repo.runner), "--cleanup-log", self.paths["CLEANUP_LOG.md"],
                     "--branch", "cleanup-test/merged-a")
        self.assertEqual(repo.remote_sha("cleanup-test/merged-a"), merged_a)
        self.run_cli("restore", "--repo", str(repo.runner), "--cleanup-log", self.paths["CLEANUP_LOG.md"],
                     "--branch", "cleanup-test/merged-a", expect=2)
        # The documented manual line works too.
        git(repo.runner, "push", "origin", f"{merged_b}:refs/heads/cleanup-test/merged-b")
        self.assertEqual(repo.remote_sha("cleanup-test/merged-b"), merged_b)

    def test_failed_backup_run_deletes_nothing(self):
        self.repo.merged_backed_up("cleanup-test/merged-a")
        before = self.repo.remote_refs()
        for runs in ([], {"workflow_runs": [dict(SUCCESS_RUNS["workflow_runs"][0], conclusion="failure")]}):
            Path(self.paths["backup-runs.json"]).write_text(json.dumps(runs), encoding="utf-8")
            self.write_request("dry-run", ["cleanup-test/merged-a"])
            dry = self.cleanup("201")
            self.assertEqual(dry["cleanup-test/merged-a"]["action"], "skip")
            self.assertEqual(self.repo.remote_refs(), before)
        os.remove(self.paths["backup-runs.json"])  # lookup failed
        self.assertEqual(self.cleanup("202")["cleanup-test/merged-a"]["action"], "skip")

    def test_branch_moved_between_check_and_delete_is_kept(self):
        sha = self.repo.merged_backed_up("cleanup-test/race")
        cli.fetch(self.repo.runner, "origin")
        new = self.repo.add_commit_to("cleanup-test/race")  # moves after the facts were gathered
        ok, why = cli.delete_branch(self.repo.runner, "origin", "cleanup-test/race", sha, "20261117T120000Z")
        self.assertFalse(ok, why)
        self.assertEqual(self.repo.remote_sha("cleanup-test/race"), new)

    def test_invalid_request_considers_nothing(self):
        self.repo.merged_backed_up("cleanup-test/merged-a")
        before = self.repo.remote_refs()
        Path(self.paths["REQUEST.json"]).write_text('{"mode": "delete", "branches": "cleanup-test/*"}')
        p = self.paths
        self.run_cli("run", "--repo", str(self.repo.runner), "--request", p["REQUEST.json"], "--task-log",
                     p["TASK_LOG.md"], "--backup-runs", p["backup-runs.json"], "--dry-run-log",
                     p["DRY_RUN_LOG.jsonl"], "--cleanup-log", p["CLEANUP_LOG.md"], "--summary", p["summary.md"],
                     "--run-id", "301", "--allow-delete", expect=2)
        self.assertEqual(self.repo.remote_refs(), before)
        self.assertIn("request rejected", Path(p["summary.md"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
