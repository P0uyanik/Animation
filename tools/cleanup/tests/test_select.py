#!/usr/bin/env python3
"""Selection logic of the branch cleanup (T-048 AC2/AC4) on a scratch repository built by the test.

Covers: merged, unmerged, merged-then-new-commit, each protected name and pattern, open-task branch, missing backup,
failed / never-run / unavailable backup run, delete without prior dry run, unknown branch name, invalid names.
Run: python3 tools/cleanup/tests/test_select.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scratch_repo  # noqa: E402
from scratch_repo import SUCCESS_RUNS, ScratchRepo, verified_run_info  # noqa: E402

cli = scratch_repo.load_cli()
sel = cli.sel

TASK_LOG = """# Task log

| ID | Task | State | Commit / branch | Notes |
| --- | --- | --- | --- | --- |
| T-098 | Finished task | **result accepted** 2026-11-15 | t-098-done (abc1234), merged | fine |
| T-097 | Finished and in main | **in main** 2026-11-17 | t-097-in-main (d70bc8f) | fine |
| T-099 | Still open | assigned (first batch) | t-099-open | `docs/tasks/T-099.md` |
| T-096 | Redesign | **open, redesign** | t-096-redesign (2e81e45) | not merged: split into t-096b-followup. |
| T-095 | Delivered | delivered; awaiting owner acceptance | t-095-delivered | |
| T-094 | Tricky state | not merged | t-094-not-merged | |

## Open visual issues
| ID | Issue | Status |
| --- | --- | --- |
| T-093a | Visual issue on branch t-093-visual | open |
"""

PROTECTED_FIXED = ["main", "staging", "relay-channel", "supervisor-state", "decisions-tools", "cleanup-request"]
PROTECTED_PATTERN = ["archive/old-work", "backup/some-copy", "codex/t-004-codex-clip-check"]


def request(mode: str, branches, reason: str = "test") -> "sel.Request":
    return sel.parse_request(json.dumps({"mode": mode, "branches": list(branches), "requested_by": "test",
                                         "reason": reason}))


class PureRules(unittest.TestCase):
    def test_request_validation(self):
        good = {"mode": "dry-run", "branches": ["a"], "requested_by": "s", "reason": "r"}
        sel.parse_request(json.dumps(good))
        bad = [
            "not json", "[]", {**good, "mode": "nuke"}, {**good, "branches": []}, {**good, "branches": "a"},
            {**good, "branches": ["a", "a"]}, {**good, "branches": [1]}, {**good, "requested_by": ""},
            {**good, "reason": " "}, {**good, "extra": 1}, {k: v for k, v in good.items() if k != "reason"},
        ]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(sel.RequestError):
                sel.parse_request(item if isinstance(item, str) else json.dumps(item))

    def test_hash_ignores_mode_only(self):
        dry, delete = request("dry-run", ["a", "b"]), request("delete", ["a", "b"])
        self.assertEqual(sel.request_hash(dry), sel.request_hash(delete))
        self.assertNotEqual(sel.request_hash(dry), sel.request_hash(request("dry-run", ["a"])))
        self.assertNotEqual(sel.request_hash(dry), sel.request_hash(request("dry-run", ["b", "a"])))
        self.assertNotEqual(sel.request_hash(dry), sel.request_hash(request("dry-run", ["a", "b"], "other")))

    def test_invalid_names_and_wildcards(self):
        for name in ["*", "t-*", "a?", "[ab]", "refs/heads/x", "origin/x", "a..b", "a b", "-x", "x/", "x.lock",
                     ".hidden", "a//b", "HEAD", "@", "x~1", "x^", "a:b", "a\\b", ""]:
            with self.subTest(name=name):
                self.assertIsNotNone(sel.invalid_name_reason(name))
        for name in ["t-041-claude-gate-claims", "integration/v3", "cleanup-test/a", "x.y"]:
            self.assertIsNone(sel.invalid_name_reason(name))

    def test_protected(self):
        for name in PROTECTED_FIXED + PROTECTED_PATTERN:
            with self.subTest(name=name):
                self.assertIsNotNone(sel.protected_reason(name, frozenset()))
        self.assertIsNone(sel.protected_reason("archived/x", frozenset()))
        self.assertIsNone(sel.protected_reason("codexx", frozenset()))
        self.assertIsNotNone(sel.protected_reason("t-1", frozenset({"t-1"})))

    def test_task_log_open_rows(self):
        names = ["t-098-done", "t-097-in-main", "t-099-open", "t-096-redesign", "t-096b-followup",
                 "t-095-delivered", "t-094-not-merged", "t-093-visual", "t-099", "t-098"]
        open_ = sel.open_task_branches(TASK_LOG, names)
        self.assertEqual(open_, frozenset({"t-099-open", "t-096-redesign", "t-096b-followup", "t-095-delivered",
                                           "t-094-not-merged", "t-093-visual"}))

    def test_task_log_without_state_column_is_open(self):
        log = "| A | B |\n| --- | --- |\n| x | t-1-branch merged |\n"
        self.assertEqual(sel.open_task_branches(log, ["t-1-branch"]), frozenset({"t-1-branch"}))

    def test_backup_run_status(self):
        ok = lambda runs: sel.backup_run_status(runs)[0]  # noqa: E731
        self.assertTrue(ok(SUCCESS_RUNS["workflow_runs"]))
        self.assertFalse(ok(None), "lookup failed")
        self.assertFalse(ok([]), "never ran")
        failed = [dict(SUCCESS_RUNS["workflow_runs"][0], conclusion="failure")]
        self.assertFalse(ok(failed))
        self.assertFalse(ok([dict(SUCCESS_RUNS["workflow_runs"][0], head_branch="staging")]))
        running = [{"id": 3, "head_branch": "main", "status": "in_progress", "conclusion": None,
                    "created_at": "2026-11-18T00:00:00Z"}]
        self.assertFalse(ok(running))
        self.assertTrue(ok(running + SUCCESS_RUNS["workflow_runs"]), "latest COMPLETED run decides")
        newer_failure = [{"id": 4, "head_branch": "main", "status": "completed", "conclusion": "cancelled",
                          "created_at": "2026-11-18T00:00:00Z"}]
        self.assertFalse(ok(newer_failure + SUCCESS_RUNS["workflow_runs"]))

    def test_dry_run_approval(self):
        req = request("delete", ["a"])
        hash_ = sel.request_hash(req)
        record = sel.dry_run_record(request("dry-run", ["a"]), "77", "d",
                                    [sel.Decision("a", "1" * 40, sel.ACTION_WOULD_DELETE, "")])
        self.assertFalse(sel.dry_run_approval(hash_, [], {}).ok)
        self.assertFalse(sel.dry_run_approval(hash_, [record], {}).ok, "unverified run")
        wrong_path = {"77": {"path": ".github/workflows/other.yml", "conclusion": "success"}}
        self.assertFalse(sel.dry_run_approval(hash_, [record], wrong_path).ok)
        failed = {"77": {"path": ".github/workflows/cleanup.yml", "conclusion": "failure"}}
        self.assertFalse(sel.dry_run_approval(hash_, [record], failed).ok)
        approval = sel.dry_run_approval(hash_, [record], verified_run_info("77"))
        self.assertTrue(approval.ok)
        self.assertEqual(approval.approved, {"a": "1" * 40})
        other = sel.request_hash(request("delete", ["a"], "different reason"))
        self.assertFalse(sel.dry_run_approval(other, [record], verified_run_info("77")).ok)
        self.assertEqual(sel.parse_dry_run_log("garbage\n" + json.dumps(record) + "\n"), [record])

    def test_cleanup_log_roundtrip(self):
        line = sel.cleanup_log_line("2026-11-17T00:00:00Z", "t-1", "a" * 40, "f" * 64)
        entries = sel.parse_cleanup_log(sel.CLEANUP_LOG_HEADER + line + "\n")
        self.assertEqual(entries, [{"date": "2026-11-17T00:00:00Z", "branch": "t-1", "sha": "a" * 40,
                                    "request_hash": "f" * 64}])
        self.assertEqual(sel.restore_command(entries[0]), ["git", "push", "origin", f"{'a' * 40}:refs/heads/t-1"])


class ScratchSelection(unittest.TestCase):
    """Real git facts from a scratch repository, then the pure decision."""

    @classmethod
    def setUpClass(cls):
        repo = cls.repo = ScratchRepo()
        cls.sha = {}
        cls.sha["merged"] = repo.merged_backed_up("t-100-merged")
        cls.sha["unmerged"] = repo.branch_with_commit("t-101-unmerged")
        repo.backup_tag(cls.sha["unmerged"], "t-101-unmerged")
        merged_then = repo.merged_backed_up("t-102-merged-then-new")
        cls.sha["merged_then_new"] = repo.add_commit_to("t-102-merged-then-new")
        repo.backup_tag(cls.sha["merged_then_new"], "t-102-merged-then-new-2")
        assert merged_then != cls.sha["merged_then_new"]
        cls.sha["archive_backup"] = repo.branch_with_commit("t-104-archive-backup")
        repo.merge_into_main("t-104-archive-backup")
        repo.archive_backup_branch(cls.sha["archive_backup"], "t-104")
        cls.sha["open"] = repo.merged_backed_up("t-099-open")
        cls.sha["closed"] = repo.merged_backed_up("t-098-done")
        for name in ["staging", "relay-channel", "supervisor-state", "decisions-tools", "cleanup-request",
                     *PROTECTED_PATTERN]:
            repo.merged_backed_up(name)
        repo.backup_tag(cls.repo.remote_sha("main"), "main")
        # Created last: no backup ref made afterwards may contain its tip (a later main backup tag would, since
        # reachability from any backup ref is the rule).
        cls.sha["no_backup"] = repo.branch_with_commit("t-103-no-backup")
        cls.sha["archive_only"] = repo.branch_with_commit("t-105-archive-only")  # does not contain t-103
        repo.merge_into_main("t-103-no-backup")
        repo.merge_into_main("t-105-archive-only")
        repo.archive_backup_branch(cls.sha["archive_only"], "t-105")
        cli.fetch(repo.runner, "origin")
        cls.all_names = ["t-100-merged", "t-101-unmerged", "t-102-merged-then-new", "t-103-no-backup",
                         "t-104-archive-backup", "t-105-archive-only", "t-099-open", "t-098-done", "no-such-branch", "t-*",
                         *PROTECTED_FIXED, *PROTECTED_PATTERN]
        cls.facts = cli.gather_facts(repo.runner, "origin", cls.all_names, "refs/remotes/origin/main")

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def decide(self, mode="dry-run", runs=SUCCESS_RUNS["workflow_runs"], approval=None, names=None):
        names = names or self.all_names
        return {d.branch: d for d in sel.decide(request(mode, names), self.facts, TASK_LOG, runs, approval)}

    def test_facts(self):
        f = self.facts
        self.assertTrue(f["t-100-merged"].merged)
        self.assertEqual(f["t-100-merged"].sha, self.sha["merged"])
        self.assertFalse(f["t-101-unmerged"].merged)
        self.assertFalse(f["t-102-merged-then-new"].merged)
        self.assertEqual(f["t-103-no-backup"].backup_refs, ())
        self.assertIn("branch archive/backup-20261117-t-104", f["t-104-archive-backup"].backup_refs)
        self.assertEqual(f["t-105-archive-only"].backup_refs, ("branch archive/backup-20261117-t-105",))
        self.assertIn("backup/20261117T000000Z/main", f["t-100-merged"].backup_refs, "reachable via main backup")
        self.assertFalse(f["no-such-branch"].exists)
        self.assertFalse(f["t-*"].exists)

    def test_only_correct_branches_selected(self):
        decisions = self.decide()
        selected = {name for name, d in decisions.items() if d.action == sel.ACTION_WOULD_DELETE}
        self.assertEqual(selected, {"t-100-merged", "t-104-archive-backup", "t-105-archive-only", "t-098-done"})
        expect = {
            "t-101-unmerged": "not merged", "t-102-merged-then-new": "not merged", "t-103-no-backup": "no backup",
            "t-099-open": "open TASK_LOG row", "no-such-branch": "unknown branch", "t-*": "wildcards",
        }
        for name, fragment in expect.items():
            with self.subTest(name=name):
                self.assertEqual(decisions[name].action, sel.ACTION_SKIP)
                self.assertIn(fragment, decisions[name].reason)
        for name in PROTECTED_FIXED + PROTECTED_PATTERN:
            with self.subTest(name=name):
                self.assertEqual(decisions[name].action, sel.ACTION_SKIP)
                self.assertIn("protected", decisions[name].reason)

    def test_failed_never_run_or_unknown_backup_blocks_everything(self):
        failed = [dict(SUCCESS_RUNS["workflow_runs"][0], conclusion="failure")]
        for label, runs in [("failed", failed), ("never ran", []), ("lookup failed", None)]:
            with self.subTest(label=label):
                decisions = self.decide(runs=runs)
                self.assertFalse([d for d in decisions.values() if d.action != sel.ACTION_SKIP])
                self.assertIn("backup", decisions["t-100-merged"].reason)

    def test_delete_without_prior_dry_run(self):
        names = ["t-100-merged", "t-098-done"]
        hash_ = sel.request_hash(request("delete", names))
        no_dry_run = sel.dry_run_approval(hash_, [], {})
        decisions = self.decide("delete", approval=no_dry_run, names=names)
        self.assertTrue(all(d.action == sel.ACTION_SKIP for d in decisions.values()))
        self.assertIn("dry run", decisions["t-100-merged"].reason)
        decisions = self.decide("delete", approval=None, names=names)
        self.assertTrue(all(d.action == sel.ACTION_SKIP for d in decisions.values()))

    def test_delete_after_dry_run_only_approved_and_unchanged(self):
        names = ["t-100-merged", "t-098-done", "t-104-archive-backup"]
        dry = list(self.decide("dry-run", names=names).values())
        record = sel.dry_run_record(request("dry-run", names), "55", "d", dry)
        record["would_delete"].pop("t-104-archive-backup")              # not approved by the dry run
        record["would_delete"]["t-098-done"] = "0" * 40                  # tip changed since the dry run
        approval = sel.dry_run_approval(sel.request_hash(request("delete", names)), [record], verified_run_info("55"))
        decisions = self.decide("delete", approval=approval, names=names)
        self.assertEqual(decisions["t-100-merged"].action, sel.ACTION_DELETE)
        self.assertEqual(decisions["t-104-archive-backup"].action, sel.ACTION_SKIP)
        self.assertIn("not approved", decisions["t-104-archive-backup"].reason)
        self.assertEqual(decisions["t-098-done"].action, sel.ACTION_SKIP)
        self.assertIn("tip changed", decisions["t-098-done"].reason)

    def test_summary_table(self):
        names = ["t-100-merged", "t-101-unmerged"]
        req = request("dry-run", names)
        text = sel.summary_markdown(req, sel.request_hash(req), list(self.decide(names=names).values()), ["note"])
        self.assertIn("| `t-100-merged` |", text)
        self.assertIn("would-delete", text)
        self.assertIn("git push origin <sha>:refs/heads/<name>", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
