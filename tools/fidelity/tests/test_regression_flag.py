#!/usr/bin/env python3
"""T-087: the per-character regression job (tools/regression/run.py) flags a fidelity drop above 2 points as
"needs owner review" and exits 0, and still fails on an image regression. Blender steps are stubbed (produce)."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
# loaded under its own name: tools/fidelity/run.py already owns the module name "run" in this test process
_spec = importlib.util.spec_from_file_location("regression_run", ROOT / "tools" / "regression" / "run.py")
RR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RR)

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


@unittest.skipIf(Image is None, "Pillow missing")
class RegressionFidelityFlagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.t = t
        self.cfg = {"character": "probe", "spec_version": "1.0.0", "spec_inputs_sha256": "abc", "inputs": []}
        gdir = t / "golden" / "probe" / "1.0.0"
        (gdir / "images").mkdir(parents=True)
        Image.new("RGBA", (16, 16), (100, 100, 100, 255)).save(gdir / "images" / "v.png")
        fp = {"objects": {"head": {"coords_hash": "1"}}}
        (gdir / "fingerprint.json").write_bytes(RR.canonical(fp))
        golden = {"spec_inputs_sha256": "abc", "fingerprint_sha256": "F", "export": {"e": "1"}, "renders": {}}
        (gdir / "golden.json").write_text(json.dumps(golden), encoding="utf-8")
        self.fp = fp

    def tearDown(self):
        self.tmp.cleanup()

    def job(self, score, render_colour):
        """One per-character job (main --character probe) with a stubbed Blender produce step."""
        def produce(cfg, blender, out, env, fidelity):
            (out / "renders").mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (16, 16), render_colour).save(out / "renders" / "v.png")
            (out / "fingerprint.json").write_bytes(RR.canonical(self.fp))
            data = {"fingerprint_sha256": "F", "export": {"e": "1"}, "renders": {"v": "x"}}
            if fidelity:
                data["fidelity"] = RR.fidelity_result(score, 64.0, 2.0)
            return data
        out, gate = self.t / f"out_{score}_{render_colour[0]}", self.t / f"gate_{score}_{render_colour[0]}.json"
        with mock.patch.object(RR.tiers, "character_ids", return_value=["probe"]), \
                mock.patch.object(RR.tiers, "character_config", return_value=dict(self.cfg)), \
                mock.patch.object(RR, "produce", produce), mock.patch.object(RR, "blender_env", return_value={}), \
                mock.patch("sys.stdout"):
            code = RR.main(["--blender", "none", "--out", str(out), "--character", "probe",
                            "--baselines", str(self.t / "golden"), "--gate-report", str(gate)])
        return code, json.loads(gate.read_text(encoding="utf-8"))

    def test_fidelity_result_policy(self):
        self.assertEqual(RR.fidelity_result(62.0, 64.0, 2.0)["needs_owner_review"], False)
        f = RR.fidelity_result(61.0, 64.0, 2.0)
        self.assertTrue(f["ok"])
        self.assertTrue(f["needs_owner_review"])
        self.assertEqual(f["drop"], 3.0)

    def test_drop_above_two_points_flags_and_exits_0(self):
        code, gate = self.job(60.0, (100, 100, 100, 255))
        self.assertEqual(code, 0)
        self.assertEqual(gate["verdict"], "PASS")
        detail = gate["checks"][0]["detail"]
        self.assertIn("NEEDS OWNER REVIEW", detail)
        self.assertIn("+4.00", detail)

    def test_image_regression_still_fails(self):
        code, gate = self.job(60.0, (160, 100, 100, 255))
        self.assertEqual(code, 1)
        self.assertEqual(gate["verdict"], "FAIL")
        self.assertIn("renders", gate["checks"][0]["detail"])

    def test_no_drop_no_flag(self):
        code, gate = self.job(64.5, (100, 100, 100, 255))
        self.assertEqual(code, 0)
        self.assertNotIn("NEEDS OWNER REVIEW", gate["checks"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
