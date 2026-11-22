"""T-198 continuity.py: the per-frame speed limit on a bake, and the intended jumps by data (cut / fast)."""
import os
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import continuity as C  # noqa: E402
import fixtures as FX  # noqa: E402


class Continuity(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.pkg = FX.write_package(os.path.join(self.d, "pkg"))

    def bake(self, step_m=0.0, turn_deg=0.0, at=10, n=20):
        hips = []
        for f in range(1, n + 1):
            x = step_m if f >= at else 0.0
            yaw = turn_deg if f >= at else 0.0
            hips.append(FX.translate(x, 0, 0) @ FX.rot_y(yaw))
        return FX.write_bake(os.path.join(self.d, "bake.json"), self.pkg, hips, hips)

    def test_under_the_limit(self):
        self.assertEqual(C.report(self.bake(step_m=0.05)), [])  # 50 mm in a frame at 24 fps: under 100 mm
        self.assertEqual(C.report(self.bake(turn_deg=30)), [])  # 30 deg: under 45

    def test_snap(self):
        rows = C.report(self.bake(step_m=0.3))
        self.assertEqual({r["bone"] for r in rows}, {"hips", "chest"})
        self.assertTrue(all(r["frame"] == 10 and r["class"] == "snap" and abs(r["mm"] - 300) < 1 for r in rows))
        rows = C.report(self.bake(turn_deg=60))
        self.assertTrue(rows and all(r["frame"] == 10 and abs(r["deg"] - 60) < 0.5 for r in rows))

    def test_cut_and_fast_by_data(self):
        b = self.bake(step_m=0.3)
        cut = {"animation": {"c.position": [[1, [0, 0, 0], "step"], [10, [0.3, 0, 0], "step"]]}}
        self.assertTrue(all(r["class"] == "cut" for r in C.report(b, cut)))
        cam = {"animation": {"camera.position": [[1, [0, 1, 3], "step"], [10, [1, 1, 3], "step"]]}}
        self.assertTrue(all(r["class"] == "cut" for r in C.report(b, cam)))
        fast = {"actions": [{"type": "look", "character": "c", "start": 8, "end": 9, "fast": True}]}
        self.assertTrue(all(r["class"] == "fast" for r in C.report(b, fast)))  # start .. end + 1
        other = {"actions": [{"type": "look", "character": "x", "start": 8, "end": 9, "fast": True}]}
        self.assertTrue(all(r["class"] == "snap" for r in C.report(b, other)))
        linear = {"animation": {"c.position": [[1, [0, 0, 0]], [10, [0.3, 0, 0]]]}}
        self.assertTrue(all(r["class"] == "snap" for r in C.report(b, linear)))

    def test_bone_classes(self):
        self.assertEqual(C.bone_class("hand.R"), "body")
        self.assertEqual(C.bone_class("f1a.L"), "finger")
        self.assertFalse(C.bone_class("eye.L"))
        self.assertFalse(C.bone_class("DEF-spine.005"))


if __name__ == "__main__":
    unittest.main()
