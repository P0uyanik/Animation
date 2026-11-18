#!/usr/bin/env python3
"""Unit tests for tools/animcheck (T-061) on synthetic bakes: a constant-speed straight wrist move must fail the
thresholds (ease, onset step, arc), an eased move on an arc round the shoulder must pass; segmentation, projection
and the gesture windows are checked on known inputs. T-104: the timing rule (timing.py) warns on short beats and
shots without a hold, never fails. T-053: the personality check (personality.py) on a synthetic
package (head width from geometry, blinks, double blinks, reach / hold / idle) against a profile's limits."""
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
import personality  # noqa: E402
import timing  # noqa: E402

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


def make_persona_project(tmp: Path, blink_at, wrist_at, limits: dict, frames=range(1, 121)):
    """A project with content/personality/p.json (limits only), a package with a 0.2 m wide head (skin vertices above
    the head bone) and a blink morph, and a bake whose 'Blink' weight is blink_at(frame) and hand.R follows wrist_at."""
    import array
    (tmp / "content/personality").mkdir(parents=True)
    (tmp / "content/personality/p.json").write_text(json.dumps({"format": "plush.personality", "version": 0,
        "profile_version": "1.0.0", "energy": {"idle_motion_amplitude": {"value": 0.003}},
        "limits": {k: {"value": v} for k, v in limits.items()}}))
    verts = array.array("f", [-0.1, 0.8, 0, 0.1, 0.8, 0, 0, 0.9, 0.1, 0.3, 0.1, 0])  # last vertex: below the head
    (tmp / "geometry.bin").write_bytes(verts.tobytes())
    pkg = tmp / "character.json"
    pkg.write_text(json.dumps({"skeleton": [{"name": "head", "head": [0, 0.7, 0]}, {"name": "upperArm.R", "head": [0, 0, 0]},
                                            {"name": "forearm.R", "head": [0, 0, 0]}, {"name": "hand.R", "head": [0, 0, 0]}],
                               "expressions": {"blink": "Blink"},
                               "meshes": [{"part": "head", "material": "M_skin", "positions": {"offset": 0, "count": 12}}]}))
    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    data = []
    for f in frames:
        p = wrist_at(f)
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, p[0], p[1], p[2], 1]
        data.append({"frame": f, "camera": {"position": [0, 0.5, 3], "target": [0, 0.5, 0], "up": [0, 1, 0]},
                     "characters": {"who": {"skin": ident + ident + ident + m, "morphs": [blink_at(f)]}}})
    bake = {"format": "plush.shot_bake", "version": 1, "fps": [24, 1], "frames": [frames[0], frames[-1]],
            "characters": [{"name": "who", "package": str(pkg), "supported": True, "morphs": ["Blink"],
                            "bones": ["head", "upperArm.R", "forearm.R", "hand.R"]}], "frame_data": data}
    scene = {"name": "persona", "frameRate": [24, 1], "frameStart": 1, "characters": [{"name": "who", "personality": "p"}],
             "actions": [{"type": "touch", "character": "who", "hand": "R", "start": 40, "contact": 52, "end": 90}]}
    return bake, scene, tmp / "shot.scene.json"


def blink_series(starts, length):
    return lambda f: 1.0 if any(s <= f < s + length for s in starts) else 0.0


def reach(f, a=40, n=12, hold_end=80, back=12):
    """Wrist: rest, eased 0.3 m reach over n frames, hold until hold_end, eased return over `back` frames."""
    if f < a:
        x = 0.0
    elif f < a + n:
        x = smootherstep((f - a) / n)
    elif f < hold_end:
        x = 1.0
    else:
        x = 1.0 - smootherstep((f - hold_end) / back)
    return (0.3 * x, 0.4 + 0.12 * math.sin(math.pi * x), 0.0)


class PersonalityCheck(unittest.TestCase):
    LIMITS = {"blink_interval_frames": [25, 40], "blink_duration_frames": [3, 5], "reach_frames": [8, 14],
              "hold_frames": [12, 40], "idle_motion_max_H_per_frame": 0.004}

    def run_check(self, blink_at, wrist_at=reach, limits=None):
        with tempfile.TemporaryDirectory() as d:
            bake, scene, path = make_persona_project(Path(d), blink_at, wrist_at, limits or self.LIMITS)
            return personality.analyse(bake, scene, path, THRESHOLDS)

    def test_blink_runs_and_double_blinks(self):
        self.assertEqual(personality.blinks([0, 0.2, 0.8, 0.3, 0, 0, 0.3, 0.2, 0, 0.6, 0.6]), [(1, 3), (9, 2)])
        rep = self.run_check(blink_series([10, 40, 46, 75, 105], 4))  # 46: a double blink right after 40
        b = rep["characters"][0]["blinks"]
        self.assertEqual(b["count"], 5)
        self.assertEqual(b["double_blinks"], [46])
        self.assertEqual(b["intervals"], [30.0, 35.0, 30.0])

    def test_in_character_motion_passes(self):
        rep = self.run_check(blink_series([10, 40, 75, 105], 4))
        c = rep["characters"][0]
        self.assertAlmostEqual(c["head_width_m"], 0.2, places=4)
        self.assertEqual(rep["failures"], [], rep["failures"])
        g = c["gestures"][0]
        self.assertTrue(8 <= g["reach_frames"] <= 14, g)
        self.assertTrue(12 <= g["hold_frames"] <= 40, g)
        self.assertEqual(c["idle"]["median_head_H_per_frame"], 0.0)

    def test_out_of_character_values_fail(self):
        # Long blinks, too frequent; a 4-frame snap reach, a 6-frame hold.
        rep = self.run_check(blink_series([10, 28, 46, 64, 82, 100], 8), lambda f: reach(f, n=4, hold_end=50, back=12))
        text = " ".join(rep["failures"])
        self.assertIn("lasts 8.0 f@24", text)
        self.assertIn("mean blink interval 18.0", text)
        self.assertIn("outside reach", text)
        self.assertIn("holds", text)

    def test_missing_profile_is_a_failure(self):
        with tempfile.TemporaryDirectory() as d:
            bake, scene, path = make_persona_project(Path(d), blink_series([10], 4), reach, self.LIMITS)
            scene["characters"][0]["personality"] = "nobody"
            rep = personality.analyse(bake, scene, path, THRESHOLDS)
        self.assertEqual(len(rep["failures"]), 1)


class TimingRule(unittest.TestCase):
    """T-104 timing rule against content/timing/reference_timing.json."""
    REF = timing.load_reference()

    def scene(self, actions, end=66):
        return {"name": "t", "frameRate": [24, 1], "frameStart": 1, "frameEnd": end, "actions": actions}

    def test_reference_table_has_the_beats(self):
        for b in ("reach", "hold", "shared_hold", "place", "release", "anticipation", "settle"):
            lo, hi = self.REF[b]
            self.assertLessEqual(lo, hi)

    def test_t095_exchange_beats_are_flagged_and_defaults_count(self):
        acts = [{"type": "grasp", "character": "boy", "prop": "cup", "start": 4, "contact": 18},
                {"type": "hold", "character": "boy", "start": 20, "end": 28, "by": [0, 0.01, 0]},
                {"type": "handover", "character": "boy", "to": "girl", "start": 28, "receiverStart": 27, "contact": 45,
                 "release": 51, "end": 61},
                {"type": "place", "character": "girl", "start": 70}]  # defaults: contact 86, end 100
        res = timing.analyse(self.scene(acts, end=101), thresholds=THRESHOLDS, reference=self.REF)
        text = "\n".join(res["warnings"])
        self.assertIn("hold reach f20-f28 8 f", text)
        self.assertIn("shared_hold f45-f51 6 f", text)
        self.assertIn("release f51-f61 10 f", text)
        self.assertIn("place f70-f86 16 f", text)  # engine default 16 < reference 20
        self.assertIn("no hold: end hold 1 f", text)
        self.assertNotIn("grasp reach", text)  # 14 f is inside the reference

    def test_calibrated_beats_pass(self):
        acts = [{"type": "grasp", "character": "boy", "prop": "cup", "start": 11, "contact": 30},
                {"type": "hold", "character": "boy", "start": 35, "end": 45, "by": [0, 0.01, 0]},
                {"type": "handover", "character": "boy", "to": "girl", "start": 45, "receiverStart": 42, "contact": 64,
                 "release": 82, "end": 99}]
        res = timing.analyse(self.scene(acts, end=129), thresholds=THRESHOLDS, reference=self.REF)
        self.assertEqual(res["warnings"], [])

    def test_bake_still_run(self):
        # moves until f30, then still (sub-threshold breathing) to f60: a 30 f hold; moving all the time: no hold
        def settles(f):
            return (0.01 * min(f, 30), 0.0002 * math.sin(f), 0.0)

        def restless(f):
            return (0.006 * f, 0.0, 0.0)
        with tempfile.TemporaryDirectory() as d:
            ok = timing.analyse(self.scene([], end=60), make_bake(Path(d), settles), THRESHOLDS, self.REF)
            self.assertEqual(ok["holds"]["longest_still_frames"], 30)
            self.assertEqual(ok["warnings"], [])
            bad = timing.analyse(self.scene([], end=60), make_bake(Path(d), restless), THRESHOLDS, self.REF)
            self.assertEqual(bad["holds"]["longest_still_frames"], 0)
            self.assertTrue(any(w.startswith("no hold") for w in bad["warnings"]))

    def test_only_warns(self):
        with tempfile.TemporaryDirectory() as d:
            scene = Path(d) / "s.scene.json"
            scene.write_text(json.dumps(self.scene([{"type": "handover", "character": "a", "to": "b", "start": 1}], end=20)))
            self.assertEqual(timing.main(["--scene", str(scene)]), 0)

    def test_thresholds_only_added(self):
        self.assertEqual(THRESHOLDS["timing_still_mm_per_frame"], 5.0)
        for k, v in {"min_chord_mm": 100, "max_ease_ratio": 0.55, "max_jerk": 0.45, "max_first_step": 0.18, "min_arc": 0.10,
                     "min_arc_screen": 0.10, "max_step_mm": 130, "max_rot_step_deg": 45}.items():
            self.assertEqual(THRESHOLDS[k], v)


if __name__ == "__main__":
    unittest.main()
