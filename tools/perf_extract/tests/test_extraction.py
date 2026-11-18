"""Verify exposure, cut boundaries, head motion and the published evidence."""

import csv
import json
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from measure import EVALUATION, eye_anchor, motion_step
from observations import BEATS
from report import event, exposure_summary, interval


class MeasurementTests(unittest.TestCase):
    def test_anchor_interpolates_only_between_visible_knots(self):
        knots = [(4, 10, 12, 8), (8, 14, 8, 12)]
        self.assertEqual(eye_anchor(knots, 6, (2, 3)), (24, 30, 20))
        for frame in (3, 9):
            self.assertIsNone(eye_anchor(knots, frame, (2, 3)))

    def test_half_open_duration(self):
        row = interval(151, 175, 24)
        self.assertEqual(row["duration_frames"], 24)
        self.assertEqual(row["duration_s"], 1)
        with self.assertRaises(ValueError):
            interval(151, 151, 24)

    def test_denominator_includes_detector_misses_and_skips_partial_blinks(self):
        rows = [dict(face_matched=int(i < 6), face_returned=int(i < 6), pose_nose_x_px="")
                for i in range(24)]
        result = exposure_summary(rows, [(2, 3, 5, "blink"), (8, 9, 11, "partial")], 24)
        self.assertEqual(result["face_matched_pct"], 25)
        self.assertEqual(result["blinks_per_visible_min"], 60)
        self.assertEqual(result["partial_dips"], 1)

    def test_optical_flow_translation_and_roll(self):
        # A symmetric feature grid makes its median displacement equal to the
        # translation at its centre, even when the patch also rotates.
        cv2.setNumThreads(1)
        before = np.zeros((180, 180), dtype=np.uint8)
        for y in range(70, 101, 10):
            for x in range(65, 116, 10):
                cv2.circle(before, (x, y), 2, 190, -1)
        anchor = (90, 90, 80)
        for angle in (0, 3):
            matrix = cv2.getRotationMatrix2D((90, 85), angle, 1)
            matrix[:, 2] += [2, -3]
            after = cv2.warpAffine(before, matrix, (180, 180))
            dx, dy, roll = motion_step(before, after, anchor)
            self.assertAlmostEqual(dx, 2, delta=.6)
            self.assertAlmostEqual(dy, -3, delta=.6)
            self.assertAlmostEqual(roll, -angle, delta=.5)
        blank = np.zeros_like(before)
        self.assertIsNone(motion_step(blank, blank, anchor))

    def test_beat_flow_excludes_incoming_step_and_propagates_missing_data(self):
        by_frame = {i: dict(face_matched="0", jawOpen="", head_dx_px=str(dx),
                            head_dy_px="0", head_droll_deg="0")
                    for i, dx in enumerate([90, 1, 2])}
        def summarize():
            return event("clip", "boy", "acting_beat", 0, 3, "Hold", 24, by_frame)
        self.assertEqual(summarize()["head_dx_px"], 3)
        by_frame[1]["head_dx_px"] = ""
        self.assertIsNone(summarize()["head_dx_px"])


class EvidenceTests(unittest.TestCase):
    def test_csvs_match_json_and_six_character_exposures(self):
        data = json.loads((EVALUATION / "performance.json").read_text())
        for section, filename in [("intervals", "performance.csv"), ("coverage", "coverage.csv")]:
            with (EVALUATION / filename).open(newline="") as stream:
                csv_rows = list(csv.DictReader(stream))
            expected = [{k: "" if v is None else str(v) for k, v in row.items()}
                        for row in data[section]]
            self.assertEqual(csv_rows, expected)
        with (EVALUATION / "frame_measurements.csv").open(newline="") as stream:
            samples = list(csv.DictReader(stream))
        self.assertEqual({(r["clip"], r["character"]) for r in data["coverage"]}, set(BEATS))
        for r in data["coverage"]:
            frames = [s for s in samples if (s["clip"], s["character"]) == (r["clip"], r["character"])]
            self.assertEqual(len(frames), r["reviewed_frames"])
            self.assertEqual(len({f["frame"] for f in frames}), len(frames))
            self.assertEqual(sum(int(f["face_matched"]) for f in frames), r["face_matched"])
            first = {}
            for f in frames:
                first.setdefault(f["shot_start"], f)
            self.assertTrue(all(f["head_dx_px"] == "" for f in first.values()))

    def test_evidence_images_are_small_decodable_jpegs(self):
        for name in ("eyelids", "paperboat", "watertable"):
            with Image.open(EVALUATION / f"{name}.jpg") as img:
                self.assertEqual(img.format, "JPEG")
                self.assertLessEqual(max(img.size), 2048)
                img.verify()


if __name__ == "__main__":
    unittest.main()
