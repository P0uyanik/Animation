#!/usr/bin/env python3
"""Static safety checks of .github/workflows/cleanup.yml (T-048 AC1/AC3): triggers, permissions, gating."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/cleanup.yml"

try:
    import yaml  # optional: structural checks when PyYAML is installed
except ImportError:  # pragma: no cover
    yaml = None


class WorkflowStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_no_schedule_no_wildcard(self):
        self.assertNotRegex(self.text, r"(?m)^\s*schedule\s*:")
        self.assertNotIn("--mirror", self.text)
        self.assertNotRegex(self.text, r"git push[^\n]*(--delete|\s-d\s|--force\b|--prune)")

    def test_trigger_and_tools_from_main(self):
        self.assertIn("branches: [cleanup-request]", self.text)
        self.assertIn("paths: [cleanup/REQUEST.json]", self.text)
        self.assertIn("workflow_dispatch:", self.text)
        commands = re.findall(r"python3 (\S+)", self.text)
        self.assertTrue(commands)
        for command in commands:
            if command != "-":
                self.assertTrue(command.startswith("main/") or command == "tools/cleanup/run_tests.py", command)
        self.assertIn("differs from main", self.text)

    def test_logs_go_to_cleanup_request_only(self):
        pushes = re.findall(r"git push ([^\n]+)", self.text)
        self.assertEqual(pushes, ["origin HEAD:refs/heads/cleanup-request; then exit 0; fi"])

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_structure(self):
        data = yaml.safe_load(self.text)
        on = data.get("on", data.get(True))
        self.assertEqual(set(on), {"push", "workflow_dispatch"})
        self.assertEqual(on["push"]["branches"], ["cleanup-request"])
        self.assertEqual(data["permissions"], {"contents": "write", "actions": "read"})
        self.assertFalse(data["concurrency"]["cancel-in-progress"])
        jobs = data["jobs"]
        self.assertEqual(jobs["cleanup"]["needs"], "self-test")
        names = [step.get("name", "") for step in jobs["cleanup"]["steps"]]
        self.assertLess(names.index("Guard - request branch must run the workflow from main"),
                        names.index("Decide and (in mode delete) delete"))
        main_checkout = jobs["cleanup"]["steps"][0]["with"]
        self.assertEqual(main_checkout["ref"], "main")
        self.assertFalse(main_checkout["persist-credentials"])
        self.assertEqual(jobs["self-test"]["steps"][0]["with"]["ref"], "main")


if __name__ == "__main__":
    unittest.main(verbosity=1)
