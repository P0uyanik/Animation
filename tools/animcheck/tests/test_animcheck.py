#!/usr/bin/env python3
"""Unit tests for tools/animcheck (T-061) on synthetic bakes: a constant-speed straight wrist move must fail the
thresholds (ease, onset step, arc), an eased move on an arc round the shoulder must pass; segmentation, projection
and the gesture windows are checked on known inputs."""
from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import animcheck  # noqa: E402

THRESHOLDS = json.loads((HERE.parent / "thresholds.json").read_text())


def smootherstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def make_bake(tmp: Path, wrist_at, frames=range(1, 61), camera=((0, 0.5, 3), (0, 0.5, 0))):
    """A one-character bake whose bone 'hand.R' pivot follows wrist_at(frame) (rest head at the origin)."""
    pkg = tmp / "character.json"
    pkg.write_text(json.dumps({"skeleton": [{"name": "upperArm.R", "head": [0, 0, 0]}, {"name": "forearm.R", "head": [0, 0, 0]},
                                            {"name": "hand.R", "head": [0, 0, 0]}]}))
    data = []
    for f in frames:
        p = wrist_at(f)
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, p[0], p[1], p[2], 1]
        ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        data.append({"frame": f, "camera": {"position": list(camera[0]), "target": list(camera[1]), "up": [0, 1, 0]},
                     "characters": {"who": {"skin": ident + ident + m, "morphs": []}}})
    return {"format": "plush.shot_bake", "version": 1, "fps": [24, 1], "frames": [frames[0], frames[-1]],
            "characters": [{"name": "who", "package": str(pkg), "supported": True, "bones": ["upperArm.R", "forearm.R", "hand.R"]}],
            "frame_data": data}


SCENE = {"name": "synthetic", "frameRate": [24, 1], "frameStart": 1,
         "actions": [{"type": "touch", "character": "who", "hand": "R", "start": 10, "contact": 25, "end": 40}]}


class AnimcheckTest(unittest.TestCase):
    def run_case(self, wrist_at):
        with tempfile.TemporaryDirectory() as d:
            bake = make_bake(Path(d), wrist_at)
            report = animcheck.analyse(bake, SCENE, Path(d) / "scene.json")
            return report, animcheck.check(report, THRESHOLDS)

    def test_constant_speed_straight_move_fails(self):
        # 0.3 m along x in 10 frames at constant speed, then back
        def wrist(f):
            if f < 10:
                return (0.0, 0.0, 0.0)
            if f < 20:
                return (0.03 * (f - 10), 0.0, 0.0)
            if f < 30:
                return (0.3, 0.0, 0.0)
            if f < 40:
                return (0.3 - 0.03 * (f - 30), 0.0, 0.0)
            return (0.0, 0.0, 0.0)
        report, fails = self.run_case(wrist)
        g = report["gestures"][0]
        self.assertGreater(g["entry"]["ease_in"], 0.9)
        self.assertGreater(g["entry"]["onset_step"], 0.9)
        self.assertLess(g["entry"]["arc"], 1e-6)
        self.assertTrue(any("ease_in" in f for f in fails))
        self.assertTrue(any("onset_step" in f for f in fails))
        self.assertTrue(any(" arc " in f for f in fails))

    def test_eased_arc_passes(self):
        # an eased swing of 90 degrees round a pivot 0.25 m away (the shoulder), out and back
        def wrist(f):
            if f <= 25:
                u = smootherstep((f - 10) / 15)
            else:
                u = 1 - smootherstep((f - 25) / 15)
            a = math.radians(-90 + 90 * u)
            return (0.25 * math.cos(a), 0.5 + 0.25 * math.sin(a), 0.0)
        report, fails = self.run_case(wrist)
        g = report["gestures"][0]
        self.assertEqual(fails, [], fails)
        self.assertLess(g["entry"]["ease_in"], 0.2)
        self.assertLess(g["exit"]["ease_out"], 0.2)
        # sagitta of a 90 degree arc: (1 - cos 45) / (2 sin 45) = 0.207
        self.assertAlmostEqual(g["entry"]["arc"], 0.2071, places=2)
        self.assertGreater(g["entry"]["arc_screen"], 0.15)

    def test_projection_and_arc(self):
        cam = {"position": [0, 0, 3], "target": [0, 0, 0], "up": [0, 1, 0]}
        x, y = animcheck.project(cam, (0.3, 0.6, 0.0))
        self.assertAlmostEqual(x, 0.1)
        self.assertAlmostEqual(y, 0.2)
        dev, chord = animcheck.arc_deviation([(0, 0, 0), (0.5, 0.0, 0), (1, 0, 0)])
        self.assertEqual(dev, 0.0)
        self.assertAlmostEqual(chord, 1.0)

    def test_windows_do_not_overlap_the_next_gesture(self):
        scene = {"frameRate": [24, 1], "frameStart": 1, "actions": [
            {"type": "touch", "character": "a", "start": 10, "contact": 20, "end": 30},
            {"type": "touch", "character": "a", "start": 40, "contact": 50, "end": 60},
            {"type": "touch", "character": "b", "start": 12, "contact": 20, "end": 30}]}
        gs = animcheck.gestures(scene, Path("scene.json"))
        self.assertEqual(gs[0]["end"], 39)          # stops before a's next gesture
        self.assertEqual(gs[1]["from"], 31)         # starts after a's previous gesture
        self.assertEqual(gs[2]["end"], 30 + animcheck.SETTLE_MARGIN)
        self.assertEqual(gs[2]["from"], 12 - animcheck.LEAD_MARGIN)


if __name__ == "__main__":
    unittest.main()
