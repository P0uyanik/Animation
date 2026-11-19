"""Lossless ID-pass fixtures. Run with unittest, NumPy and Pillow."""

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import readability


class ReadabilityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / "report"
        for group in ("visible", "cup_only"):
            (self.root / group).mkdir()
        self.command = [str(self.root), "--frames", "7", "9", "--cup-id", "1",
                        "--eye", "a.L=2", "--eye", "a.R=3", "--eye", "b.L=4", "--eye", "b.R=5",
                        "--cup-threshold", "50", "--pupil-threshold", "2", "--out", str(self.out)]
        # The first two cup pixels touch diagonally. The third is a separate patch.
        self.visible = np.array([[1, 2, 0, 3, 1], [0, 1, 4, 0, 0], [2, 0, 0, 0, 5]], dtype="uint8")
        self.isolated = np.array([[1, 1, 0, 0, 1], [0, 1, 0, 0, 0], [0, 0, 0, 0, 0]], dtype="uint8")
        blank = np.zeros_like(self.visible)
        for f, vis, iso in ((7, self.visible, self.isolated), (8, blank, self.isolated), (9, blank, blank)):
            self.save("visible", f, vis)
            self.save("cup_only", f, iso)

    def save(self, group, frame, data):
        Image.fromarray(data).save(self.root / group / f"frame_{frame:04d}.png")

    def run_tool(self):
        with redirect_stdout(io.StringIO()):
            readability.main(self.command)

    def refused(self, message):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            self.run_tool()
        self.assertIn(message, stderr.getvalue())
        self.assertFalse(self.out.exists())

    def test_per_frame_csv_minima_and_strict_thresholds(self):
        self.run_tool()
        with (self.out / "readability.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(tuple(rows[0].values()), ("7", "2", "4", "50.0", "2", "1", "1", "1"))
        self.assertEqual([r["cup_patch_pct"] for r in rows], ["50.0", "0.0", ""])
        self.assertEqual([r["frame"] for r in rows], ["7", "8", "9"])
        report = (self.out / "summary.txt").read_text(encoding="utf-8")
        self.assertIn("Cup largest patch (px) minimum 0 at 8-9", report)
        self.assertIn("Below 50 (1 frame): 8\n", report)
        self.assertIn("percentage undefined): 9", report)
        self.assertIn("a.L visible pupil (px) minimum 0 at 8-9\n  Below 2 (2 frames): 8-9", report)
        self.assertIn("b.R visible pupil (px) minimum 0 at 8-9\n  Below 2 (3 frames): 7-9", report)

    def test_opposite_edges_do_not_wrap(self):
        self.assertEqual(readability.largest_patch(np.array([[0, 0, 0, 1], [1, 0, 0, 0]])), 1)

    def test_indexed_png_uses_indices(self):
        path = self.root / "visible/frame_0007.png"
        image = Image.fromarray(self.visible)
        image.putpalette([255, 255, 255] * 256)
        image.save(path)
        np.testing.assert_array_equal(readability.read_ids(path), self.visible)

    def test_missing_frame_reports_frame(self):
        (self.root / "cup_only/frame_0008.png").unlink()
        self.refused("frame_0008.png")

    def test_mismatched_dimensions(self):
        self.save("visible", 7, self.visible[:, :-1])
        self.refused("pass dimensions differ")

    def test_misaligned_passes(self):
        self.isolated[1, 1] = 0
        self.save("cup_only", 7, self.isolated)
        self.refused("outside the cup-only silhouette")

    def test_wrong_reference_id(self):
        self.isolated[1, 3] = 3
        self.save("cup_only", 7, self.isolated)
        self.refused("unexpected ID in cup-only pass")

    def test_ambiguous_labels(self):
        self.command.extend(["--eye", "b.center=2"])
        self.refused("distinct integers")


if __name__ == "__main__":
    unittest.main()
