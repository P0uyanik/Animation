#!/usr/bin/env python3
"""T-097-boy: acting signature of boy_yellow_hoodie against the reference performance data (T-106).

    python3 tests/acting/test_boy_signature.py

Checks the boy's own data only (content/personality/boy_yellow_hoodie.json, content/emotions/boy_*.emotion.json,
content/clips/boy_*.clip.json, episodes/e908_boy_acting): every tuned value carries its evidence, and the signature
"subtle, low energy, delayed interest, sideways glances, small mouth changes, reluctant gestures" holds against the
measured rows of docs/evaluation/animation/T-106/performance.csv (watertable / paperboat, boy).

With a prepared e908 shot (run_shot prepare stage: episodes/e908_boy_acting/shots/s010/build/) and an engine
(build/apps/render-cli/plush-render), the shot is baked and measured with the T-097C acting rule and the T-053
personality check; without them those tests are skipped (no Blender needed for the rest)."""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "animcheck"))
import acting  # noqa: E402
import animcheck  # noqa: E402
import personality  # noqa: E402

PROFILE = json.loads((ROOT / "content/personality/boy_yellow_hoodie.json").read_text())
PERF = list(csv.DictReader(open(ROOT / "docs/evaluation/animation/T-106/performance.csv")))
SHOT_DIR = ROOT / "episodes/e908_boy_acting/shots/s010"
SCENE = json.loads((SHOT_DIR / "shot.scene.json").read_text())
RENDER = ROOT / "build/apps/render-cli/plush-render"
RESOLVED = SHOT_DIR / "build/shot.resolved.scene.json"

R = PROFILE["reaction"]
EVENTS = R["events"]["value"]
SHARED_DEFAULT_INTENSITY = {"object_appears": 0.7, "partner_acts": 0.5, "success": 0.8, "failure": 0.6}  # reaction.h


def val(rec):
    return rec["value"] if isinstance(rec, dict) and "value" in rec else rec


def rows(clip, kind, first=None):
    return [r for r in PERF if r["clip"] == clip and r["character"] == "boy" and r["kind"] == kind
            and (first is None or int(r["first_frame"]) == first)]


def emotion(name):
    return json.loads((ROOT / f"content/emotions/{name}.emotion.json").read_text())


def clip(name):
    return json.loads((ROOT / f"content/clips/{name}.clip.json").read_text())


def qangle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def expressed(event):
    return min(1.0, EVENTS[event].get("intensity", SHARED_DEFAULT_INTENSITY[event]) * val(R["intensity_scale"]))


class Evidence(unittest.TestCase):
    def test_every_tuned_value_has_kind_and_source(self):
        for key in ("delay_frames", "intensity_scale", "gaze_shift", "gesture_min_intensity", "events"):
            with self.subTest(key=key):
                self.assertIn("kind", R[key])
                self.assertTrue(R[key]["source"])
        for name, e in EVENTS.items():
            with self.subTest(event=name):
                self.assertTrue(e.get("source"))

    def test_only_boy_prefixed_assets(self):
        for e in EVENTS.values():
            if "emotion" in e and e["emotion"] not in ("happy", "sad", "curious", "surprised"):
                self.assertTrue(e["emotion"].startswith("boy_"))
                self.assertTrue((ROOT / f"content/emotions/{e['emotion']}.emotion.json").exists())
            for g in e.get("gestures", []):
                self.assertTrue(g.startswith("boy_"))
                self.assertTrue((ROOT / f"content/clips/{g}.clip.json").exists())


class Signature(unittest.TestCase):
    def test_subtle_reactions(self):
        # Smaller than the shared emotion system's intensity (T-106: jaw 0.033, a 5 deg roll).
        self.assertLess(val(R["intensity_scale"]), 1.0)
        self.assertLessEqual(val(PROFILE["energy"]["gesture_amplitude"]), 0.3)

    def test_reluctant_gestures(self):
        # A plain partner act (shared intensity) earns no gesture; his tuned partner_acts just does.
        thr = val(R["gesture_min_intensity"])
        self.assertGreater(thr, 0.35)  # above the shared 0.35
        self.assertLess(SHARED_DEFAULT_INTENSITY["partner_acts"] * val(R["intensity_scale"]), thr)
        self.assertGreaterEqual(expressed("partner_acts"), thr)
        self.assertLess(expressed("partner_acts") - thr, 0.1)  # only just

    def test_sideways_glances_keep_the_task(self):
        # T-106 WT gaze rows: his eye line stays on the table through the girl's point.
        wt_gaze = rows("watertable", "gaze")
        self.assertTrue(all("right" in r["observation"].lower() for r in wt_gaze))
        self.assertLessEqual(val(R["gaze_shift"]), 0.4)
        self.assertLessEqual(EVENTS["partner_acts"]["gaze_shift"], val(R["gaze_shift"]))
        self.assertEqual(val(PROFILE["attention"]["glance_at_others"]), 0)

    def test_no_smile_small_mouth(self):
        e = emotion(EVENTS["partner_acts"]["emotion"])
        self.assertFalse({"MouthSmile", "Smile", "smile", "happy", "laugh"} & set(e["face"]))
        k = expressed("partner_acts")
        # T-106 PB [259, 289): lips part, median jawOpen 0.033
        pb = rows("paperboat", "acting_beat", 259)[0]
        self.assertAlmostEqual(e["face"]["JawOpen"] * k, float(pb["jaw_open_median"]), delta=0.01)
        self.assertLessEqual(e["face"]["MouthO"] * k, 0.15)
        self.assertGreater(e["face"]["EyeWide"] * k, 0.25)  # 'eyes open wider'
        self.assertGreater(e["face"].get("BrowDown", 0), 0)  # brows down in concentration (positive_style)

    def test_reaction_timing_matches_watertable(self):
        e = emotion(EVENTS["partner_acts"]["emotion"])
        lift = rows("watertable", "acting_beat", 60)[0]
        hold = rows("watertable", "acting_beat", 87)[0]
        self.assertAlmostEqual(e["blend"]["rise"], float(lift["duration_s"]), places=3)
        self.assertAlmostEqual(e["timing"]["onset"], float(lift["duration_s"]), places=3)
        self.assertAlmostEqual(e["timing"]["hold"], float(hold["duration_s"]), delta=0.01)
        # the raised head is held at least as long as WT shows (it holds to the clip's end: open-ended)
        self.assertGreaterEqual(EVENTS["partner_acts"]["duration_s"], float(lift["duration_s"]) + float(hold["duration_s"]))

    def test_head_lift_roll(self):
        # T-106 WT [60, 81): about 5 deg roll at his expressed intensity.
        c, idle = clip("boy_head_lift"), clip("idle_relaxed")
        roll = qangle(c["tracks"]["head"]["keys"][0][1:], idle["tracks"]["head"]["keys"][0][1:])
        self.assertAlmostEqual(roll * expressed("partner_acts"), 5.0 + 2.0, delta=2.5)  # roll + the small lift
        self.assertEqual(sorted(c["mask"]), ["head", "neck"])

    def test_shrug_is_small_slow_and_rises_slower_than_it_falls(self):
        c, idle = clip("boy_reluctant_shrug"), clip("idle_relaxed")
        self.assertNotIn("head", c["mask"])  # keeps the reaction's head lift
        self.assertNotIn("neck", c["mask"])
        self.assertEqual(c["fps"], 24.0)
        for role in ("upperArm.R", "forearm.R"):
            rest = idle["tracks"][role]["keys"][0][1:]
            ang = [qangle(k[1:], rest) for k in c["tracks"][role]["keys"]]
            top = max(ang)
            self.assertLess(top, 0.3 * 180)  # energy.gesture_amplitude
            up = [i for i, a in enumerate(ang) if a >= 0.9 * top]
            moving = [i for i, a in enumerate(ang) if a >= 0.1 * top]
            rise, fall = up[0] - moving[0], moving[-1] - up[-1]  # 10 % -> 90 % and back
            with self.subTest(role=role, rise=rise, fall=fall):
                self.assertGreaterEqual(rise - fall, 2)  # guide: the rise is 2-3 f slower than the fall
        self.assertNotIn("browUp", c.get("face", {}).get("tracks", {}))  # no surprise brows

    def test_blink_and_hold_ranges_contain_the_measurements(self):
        lo, hi = val(PROFILE["limits"]["hold_frames"])
        for first in (27, 87):
            d = int(rows("watertable", "acting_beat", first)[0]["duration_frames"])
            self.assertTrue(lo <= d <= hi, d)
        peaks = sorted(int(r["peak_frame"]) for r in rows("watertable", "blink"))
        gaps = [b - a for a, b in zip(peaks, peaks[1:])]
        blo, bhi = val(PROFILE["limits"]["blink_interval_frames"])
        self.assertTrue(all(blo <= g <= bhi for g in gaps), gaps)
        self.assertAlmostEqual(val(PROFILE["blink"]["interval_frames"])["mean"], sum(gaps) / len(gaps), delta=1.0)


class Shot(unittest.TestCase):
    def test_e908_beats_follow_watertable(self):
        b = SCENE["x_t097boy_staging"]["beats"]
        point_arrives = int(rows("watertable", "acting_beat", 27)[0]["first_frame"]) + 12  # girl's reach [22, 39)
        self.assertEqual(point_arrives, 39)
        self.assertEqual(b["delay_frames"], 60 - point_arrives)  # his blink + head lift at WT f60
        lo, hi = val(R["delay_frames"])
        self.assertTrue(lo <= b["delay_frames"] <= hi)
        self.assertEqual((lo + hi) / 2, b["delay_frames"])  # the planner's notice delay at salience 1
        self.assertEqual(b["end_hold"][1] - b["end_hold"][0], int(rows("watertable", "acting_beat", 87)[0]["duration_frames"]))
        ev = SCENE["events"][0]
        self.assertEqual(ev["kind"], "partner_acts")
        self.assertEqual(ev["source"], "")  # off screen: no look target, the glance is authored
        self.assertAlmostEqual(SCENE["frameStart"] + ev["time"] * 24, b["event"], places=3)
        ch = SCENE["characters"][0]
        self.assertEqual(ch["personality"], "boy_yellow_hoodie")
        self.assertEqual(SCENE["production"]["cast"]["boy"]["version"], "current")
        # The reaction is generated from `events` (T-097D): nothing authored duplicates it.
        types = {a["type"] for a in SCENE["actions"]}
        self.assertNotIn("emotion", types)
        self.assertEqual([a for a in SCENE["actions"] if a["type"] == "clip" and not a.get("base")], [])
        # The planned notice frame (delay_frames middle, salience 1) is the WT beat, and the shrug's rest lead puts the
        # arm's first move at the authored gesture beat.
        self.assertEqual(notice_frame(SCENE), b["notice"])
        self.assertEqual(b["gesture"] - b["notice"], 21 + 10)  # head lift rises 21 f (WT [60, 81)), settles 10 f
        self.assertGreaterEqual(b["notice"] + lead_frames(), b["gesture"])  # the arm is still at rest at that beat

    def test_acting_check_scene_only(self):
        rep = acting.analyse(SCENE, SHOT_DIR / "shot.scene.json")
        self.assertEqual(rep["warnings"], [])
        g = rep["characters"][0]["glances"][0]
        self.assertEqual(g["delay_frames"], 21.0)


@unittest.skipUnless(RESOLVED.exists() and RENDER.exists(), "needs a prepared e908 shot and plush-render")
def notice_frame(scene):
    """Mirror of the T-097B planner's notice delay at salience 1 (reaction.h): middle of delay_frames x (2 - s)."""
    ev = scene["events"][0]
    lo, hi = val(R["delay_frames"])
    s = ev.get("salience", 1.0)
    return round(scene["frameStart"] + ev["time"] * 24 + (lo + hi) / 2 * (2 - s))


def lead_frames():
    """Rest frames before the shrug's arm leaves its rest pose (> 0.5 deg on upperArm.R)."""
    c, idle = clip("boy_reluctant_shrug"), clip("idle_relaxed")
    rest = idle["tracks"]["upperArm.R"]["keys"][0][1:]
    return next(k[0] for k in c["tracks"]["upperArm.R"]["keys"] if qangle(k[1:], rest) > 0.5)


def with_reaction(scene):
    """The scene as the acting rule reads it (T-097D): the generated reaction actions appended, mirrored from the
    profile (emotion and gesture at the notice frame; no look: the event has no source). The bake tests check that the
    bake shows them at those frames."""
    out = json.loads(json.dumps(scene))
    f, e = notice_frame(scene), EVENTS["partner_acts"]
    out["actions"] += [{"type": "emotion", "character": "boy", "name": e["emotion"], "start": f, "blend": True,
                        "intensity": e["intensity"], "modulation": {"intensityScale": val(R["intensity_scale"]),
                                                                    "gazeShift": e["gaze_shift"]}},
                       {"type": "clip", "character": "boy", "clip": e["gestures"][0], "start": f}]
    return out


class Baked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / "bake.json"
        subprocess.run([str(RENDER), str(RESOLVED), "--bake", str(out)], check=True, capture_output=True)
        cls.bake = json.loads(out.read_text())
        cls.scene = json.loads(RESOLVED.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_acting_rule_no_warnings(self):
        rep = acting.analyse(with_reaction(self.scene), RESOLVED, self.bake)
        self.assertEqual(rep["warnings"], [])
        c = rep["characters"][0]
        self.assertTrue(c["gestures"])
        for g in c["gestures"]:
            self.assertLessEqual(g["amplitude"], g["limit"])
        self.assertGreaterEqual(c["hold"]["longest_still_frames_24"], c["hold"]["required"])

    def test_personality_limits(self):
        rep = personality.analyse(self.bake, with_reaction(self.scene), RESOLVED) if hasattr(personality, "analyse") else None
        if rep is None:
            self.skipTest("personality.analyse not available")
        self.assertEqual(rep["failures"], [])


    def test_generated_reaction_plays_at_the_planned_frames(self):
        """The bake shows the generated reaction: the face starts at the notice frame, the arm at the gesture beat."""
        ch = self.bake["characters"][0]
        f0, n = self.bake["frames"][0], notice_frame(self.scene)
        wide = ch["morphs"].index("EyeWide")
        w = [fd["characters"]["boy"]["morphs"][wide] for fd in self.bake["frame_data"]]
        self.assertLess(max(w[: n - f0]), 0.02)        # nothing before he notices
        self.assertGreater(w[n - f0 + 21], 0.25)       # lids up after the 21 f rise
        pkg = json.loads(Path(ch["package"]).read_text())
        head = next(b["head"] for b in pkg["skeleton"] if b["name"] == "hand.R")
        i = ch["bones"].index("hand.R")
        P = [animcheck.pivot(fd["characters"]["boy"]["skin"][16 * i:16 * i + 16], head) for fd in self.bake["frame_data"]]
        speed = [1000 * math.dist(a, b) for a, b in zip(P, P[1:])]  # speed[k]: frame f0 + k -> f0 + k + 1
        g = self.scene["x_t097boy_staging"]["beats"]["gesture"]
        shrug = max(speed[g - f0: g - f0 + 60])
        self.assertGreater(shrug, 5.0)  # the shrug (mm/f)
        # before it only the layer's small blend-in settle (the arm goes to the clip's rest pose), well under the shrug
        self.assertLess(max(speed[n - f0: g - f0]), 0.3 * shrug)


if __name__ == "__main__":
    unittest.main(verbosity=2)
