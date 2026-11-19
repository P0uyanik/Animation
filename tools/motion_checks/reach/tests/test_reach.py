"""Fixture tests for tools/motion_checks/reach (T-135): python3 tools/motion_checks/reach/tests/test_reach.py"""
import json
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import measure as M  # noqa: E402
import run as RUN  # noqa: E402


def ease(n, kind="cubic"):
    t = np.linspace(0, 1, n + 1)
    return 3 * t**2 - 2 * t**3 if kind == "cubic" else t


def reach(n=16, chord=300.0, arc=0.0, pre=10, post=20, kind="cubic"):
    """Wrist from (0,0,0) to (chord,0,0) over n frames, bulging up by `arc` mm at mid-path, at rest before / after."""
    s = ease(n, kind)
    p = np.zeros((pre + n + 1 + post, 3))
    p[pre:pre + n + 1, 0] = chord * s
    p[pre:pre + n + 1, 2] = arc * np.sin(np.pi * s)
    p[pre + n + 1:] = p[pre + n]
    return p


def bump(F, at, width, amp):
    """Joint speed signal (deg/f): a smooth bump peaking at frame `at`."""
    t = np.arange(F)
    return amp * np.exp(-0.5 * ((t - at) / width) ** 2)


def rotz(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


class Segment(unittest.TestCase):
    def test_one_reach_found_with_its_edges(self):
        p = reach()
        (t0, t1), = M.segment(p)
        self.assertLessEqual(abs(t0 - 10), 1)
        self.assertLessEqual(abs(t1 - 26), 1)

    def test_small_moves_and_still_ignored(self):
        self.assertEqual(M.segment(reach(chord=30)), [])
        self.assertEqual(M.segment(np.zeros((40, 3))), [])

    def test_two_reaches(self):
        p = np.concatenate([reach(post=12), reach(post=12)[::-1][1:]])
        self.assertEqual(len(M.segment(p)), 2)


class Path(unittest.TestCase):
    def test_straight_has_no_deviation(self):
        p = reach()
        r = M.path(p, *M.segment(p)[0])
        self.assertLess(r["max_dev_mm"], 1e-6)
        self.assertAlmostEqual(r["arc_ratio"], 1.0, places=6)

    def test_arc_measured(self):
        p = reach(arc=45.0)
        r = M.path(p, *M.segment(p)[0])
        self.assertAlmostEqual(r["max_dev_mm"], 45.0, delta=0.5)
        self.assertAlmostEqual(r["dev_ratio"], 0.15, delta=0.01)
        self.assertGreater(r["bulge_up"], 0.99)
        self.assertAlmostEqual(r["dev_at"], 0.5, delta=0.07)
        self.assertGreater(r["arc_ratio"], 1.03)


class Velocity(unittest.TestCase):
    def test_cubic_is_symmetric_and_eased(self):
        p = reach(n=16, chord=320)
        v = M.velocity(p, *M.segment(p)[0], fps=24)
        self.assertAlmostEqual(v["peak_mm_f"], 30.0, delta=0.3)  # 1.5 * chord / n
        self.assertAlmostEqual(v["peak_at"], 0.5, delta=0.07)
        self.assertAlmostEqual(v["ease_in"], v["ease_out"], delta=0.07)
        self.assertGreater(v["ease_in"], 0.1)  # smoothstep: half speed at t=0.15
        self.assertLess(v["onset_step"], 0.15)
        self.assertAlmostEqual(v["peak_m_s"], v["peak_mm_f"] * 24 / 1000)

    def test_linear_starts_and_stops_abruptly(self):
        p = reach(n=16, chord=320, kind="linear")
        v = M.velocity(p, *M.segment(p)[0], fps=24)
        self.assertEqual(v["ease_in"], 0.0)
        self.assertEqual(v["ease_out"], 0.0)
        self.assertAlmostEqual(v["onset_step"], 1.0)
        self.assertAlmostEqual(v["peak_acc"], 20.0, delta=1e-6)  # full speed in one frame


class Timing(unittest.TestCase):
    def test_lead_and_overlap(self):
        p = reach(n=16, pre=30)
        t0, t1 = M.segment(p)[0]
        tpk = t0 + 1 + int(np.argmax(M.speed(p)[t0 + 1:t1 + 1]))
        F = len(p)
        early = M.lead(bump(F, tpk - 4, 4, 2.0), t0, t1, tpk)
        self.assertEqual(early["peak_lead"], 4)
        self.assertGreater(early["onset_lead"], 0)
        self.assertIsNone(M.lead(np.zeros(F), t0, t1, tpk)["onset_lead"])
        busy = M.lead(np.full(F, 2.0) + bump(F, tpk, 3, 1.0), t0, t1, tpk)
        self.assertTrue(busy["busy"])
        self.assertIsNone(busy["onset_lead"])
        late = M.overlap(bump(F, tpk + 6, 4, 2.0), t0, t1, tpk)
        self.assertEqual(late["peak_offset"], 6)
        self.assertGreater(late["settle"], 0)
        still = M.overlap(bump(F, tpk, 2, 2.0), t0, t1, tpk)
        self.assertEqual(still["settle"], 0)

    def test_ang_speed(self):
        R = np.stack([rotz(3 * i) for i in range(5)])
        np.testing.assert_allclose(M.ang_speed(R)[1:], 3.0, atol=1e-6)


class FakeChar:
    """Minimal stand-in for shot.Character: bones, (F, B, 4, 4) matrices, rest heads at the origin."""
    def __init__(self, name, wrist):
        F = len(wrist)
        self.name = name
        self.bones = ["hips", "chest", "neck", "head", "hand.L", "hand.R", "DYN-bun.0.0"]
        self.parent = np.array([-1, 0, 1, 2, 1, 1, 3])
        self.M = np.tile(np.eye(4), (F, len(self.bones), 1, 1))
        self.M[:, 4, :3, 3] = wrist / 1000.0
        self.M[:, 5, :3, 3] = [0.1, 0, 0]
        self.M[:, 6, :3, :3] = np.stack([rotz(2 * np.sin(t / 3)) for t in range(F)])

    def pivots(self):
        return self.M[..., :3, 3]

    def local_rotations(self):
        R = self.M[..., :3, :3]
        out = R.copy()
        h = self.parent >= 0
        out[:, h] = np.einsum("fbji,fbjk->fbik", R[:, self.parent[h]], R[:, h])
        return out


class FakeShot:
    def __init__(self, wrist):
        self.path, self.fps = "fake/bake.json", 24.0
        self.frames = np.arange(1, len(wrist) + 1)
        self.characters = [FakeChar("kid", wrist)]


class Report(unittest.TestCase):
    def test_shot_report_and_compare(self):
        base = RUN.measure_shot(FakeShot(reach(n=12)))
        new = RUN.measure_shot(FakeShot(reach(n=16, arc=40)))
        self.assertEqual(len(base["moves"]), 1)
        m = base["moves"][0]
        self.assertEqual((m["character"], m["side"], m["kind"]), ("kid", "L", "extend"))
        self.assertIn("hair", m["overlap"])
        self.assertEqual(base["bones"]["kid.L"]["wrist"], "hand.L")
        RUN.compare(new, base)
        d = new["moves"][0]["baseline"]["delta"]
        self.assertEqual(d["velocity.frames"], 4)
        self.assertAlmostEqual(d["path.max_dev_mm"], 40, delta=1)
        md = RUN.markdown(json.loads(json.dumps(new)), "fake")
        self.assertIn("Against baseline", md)


if __name__ == "__main__":
    unittest.main()
