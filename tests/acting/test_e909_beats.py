#!/usr/bin/env python3
"""Beat tests for the T-114 two-character acting shot (episodes/e909_two_char_acting/shots/s010).

    python3 tests/acting/test_e909_beats.py [--bake <e909 bake.json>]      (or: python3 -m pytest tests/acting)

Data checks need nothing but Python: the committed scene is what make_shot.py writes, cast "current", the calibrated
timing default (no "timing" key), verbs + events, current-cast-safe emotions, eye limits at the specs' gaze range, and
the authored beats against the reaction delays of the personality profiles and T-106.

With a bake of the shot (--bake, $PLUSH_E909_BAKE, or the shot's build/bake.json when it exists) the measured key beats
run too (episodes/e909_two_char_acting/measure_beats.py): her notice delay, his late answer, the grasp contacts and
the hand-over frames (hand fixed on its socket in the cup's frame), the place, the delight beat, the eyes inside the
gaze range during blinks, no engine warning in the bake log, and the T-053 personality / T-061 animcheck limits.
Without a bake those checks are reported skipped."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EP = ROOT / "episodes" / "e909_two_char_acting"
SHOT = EP / "shots" / "s010" / "shot.scene.json"
sys.path.insert(0, str(ROOT / "tools" / "animcheck"))
sys.path.insert(0, str(EP))
import animcheck  # noqa: E402
import measure_beats  # noqa: E402
import personality  # noqa: E402

PROFILES = {n: ROOT / "content" / "personality" / f"{cid}.json"
            for n, cid in (("boy", "boy_yellow_hoodie"), ("girl", "girl_auburn_bun_glasses"))}
SPECS = {"boy": "boy_yellow_hoodie/versions/2.1.0", "girl": "girl_auburn_bun_glasses/versions/0.12.0"}
TIMING = ROOT / "content" / "timing" / "reference_timing.json"
BAKE = None  # set by --bake / $PLUSH_E909_BAKE / the shot's build folder

# the key beats (scene frames) read back from the bake of the committed scene (measure_beats.py), current cast
HER_CONTACT, HER_RELEASE = 58, 163  # her left hand on grip_b: pick-up contact (+1: first still frame) .. pass release
HIS_CONTACT, HIS_RELEASE = 133, 222  # his right hand on grip: pass contact .. place contact (+1)
CUP_LEAVES, CUP_BACK = 69, 221
HER_NOTICE_SIGN, HIS_ANSWER_SIGN = 21, 113  # first frame her WideOpen / his EyeWide > 0.1 after the event


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def val(rec):
    return rec["value"] if isinstance(rec, dict) and "value" in rec else rec


class Scene(unittest.TestCase):
    def setUp(self):
        self.s = load(SHOT)
        self.beats = self.s["x_t114"]["beats_authored"]

    def test_scene_is_what_make_shot_writes(self):
        before = SHOT.read_bytes()
        subprocess.run([sys.executable, str(EP / "make_shot.py")], check=True, capture_output=True)
        self.assertEqual(SHOT.read_bytes(), before, "make_shot.py output differs from the committed scene")

    def test_current_cast_calibrated_default_verbs_and_events(self):
        cast = self.s["production"]["cast"]
        self.assertEqual({n: c["version"] for n, c in cast.items()}, {"boy": "current", "girl": "current"})
        self.assertNotIn("timing", self.s)
        types = [a["type"] for a in self.s["actions"]]
        for t in ("pick_up", "carry", "pass", "place"):
            self.assertIn(t, types)
        self.assertTrue(next(a for a in self.s["actions"] if a["type"] == "pass")["react"])
        self.assertTrue(next(a for a in self.s["actions"] if a["type"] == "place")["verb"])
        kinds = {e["kind"]: e for e in self.s["events"]}
        self.assertEqual(kinds["object_appears"]["characters"], ["girl"])
        self.assertEqual(kinds["success"]["characters"], ["boy"])  # her success reaction is girl_delighted (SmileOpen)

    def test_current_cast_safe_emotions(self):
        # T-113 open point 1: the published masters have no SmileOpen / Pout
        names = {a["name"] for a in self.s["actions"] if a["type"] == "emotion"}
        self.assertFalse(names & {"girl_delighted", "boy_reluctant"}, names)
        for e in names:
            face = load(ROOT / "content" / "emotions" / f"{e}.emotion.json")["face"]
            self.assertFalse({k.lower() for k in face} & {"smileopen", "pout"}, e)
        # an emotion's lid (blink) under personality.py's 0.1 blink-run threshold, so no fake long blink
        bored = next(a for a in self.s["actions"] if a.get("name") == "boy_unimpressed")
        lid = load(ROOT / "content" / "emotions" / "boy_unimpressed.emotion.json")["face"]["blink"]
        self.assertLess(lid * bored["intensity"], 0.1)

    def test_eye_limits_are_the_spec_gaze_range(self):
        for c in self.s["characters"]:
            spec = load(ROOT / "assets" / "characters" / SPECS[c["name"]] / "spec.resolved.json")
            yaw, pitch = spec["face"]["eyes"]["gaze_range_deg"]
            g = c["life"]["gaze"]
            # 1.5 deg inside the range: the engine limit is soft
            self.assertEqual((g["maxLeftDeg"], g["maxRightDeg"], g["maxUpDeg"], g["maxDownDeg"]),
                             (yaw - 1.5, yaw - 1.5, pitch - 1.5, pitch - 1.5))

    def test_authored_beats_follow_the_profiles(self):
        b, ref = self.beats, load(TIMING)["beats"]
        # her pick-up waits for the wonder rise: T-106 WT [0, 39) wonder, the reach starts at f22
        event = round(self.s["events"][0]["time"] * 24) + 1
        self.assertGreaterEqual(b["pick_up"] - event, 22)
        # the shared hold reads (T-116), within the reference shared-hold range's upper end x 3
        shared = next(a for a in self.s["actions"] if a["type"] == "pass")["release"] - b["his_contact"]
        self.assertGreaterEqual(shared, ref["shared_hold"]["frames"][0])
        # his held look at her comes after his late success reaction (its look ends + back), and lasts a hold
        lo, hi = val(load(PROFILES["boy"])["reaction"]["delay_frames"])
        self.assertGreaterEqual(b["his_look_her"], b["success"] + hi)
        self.assertGreaterEqual(self.s["frameEnd"] - b["his_look_her"], ref["hold"]["frames"][0])
        self.assertTrue(8 * 24 <= self.s["frameEnd"] <= 12 * 24)


@unittest.skipUnless(os.environ.get("PLUSH_E909_BAKE") or BAKE or (SHOT.parent / "build" / "bake.json").is_file(),
                     "no e909 bake (--bake / $PLUSH_E909_BAKE / build/bake.json)")
class Bake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(BAKE)
        cls.bake = load(cls.path)
        cls.m = measure_beats.measure(str(cls.path))
        cls.scene = load(SHOT)

    def series(self, who, morph):
        c = next(c for c in self.bake["characters"] if c["name"] == who)
        ks = [j for j, x in enumerate(c["morphs"]) if x == morph]
        self.assertTrue(ks, f"{who} has no {morph} morph")
        return [max(f["characters"][who]["morphs"][j] for j in ks) for f in self.bake["frame_data"]]

    def test_grasp_contacts_and_handover_frames(self):
        self.assertEqual(self.m["holds"]["girl"]["runs"], [[HER_CONTACT, HER_RELEASE]])
        self.assertEqual(self.m["holds"]["boy"]["runs"], [[HIS_CONTACT, HIS_RELEASE]])
        shared = HER_RELEASE - HIS_CONTACT
        self.assertEqual(shared, self.scene["x_t114"]["shared_hold"])
        self.assertEqual(self.scene["x_t114"]["beats_authored"]["his_contact"], HIS_CONTACT)
        self.assertEqual(self.scene["x_t114"]["beats_authored"]["her_release"], HER_RELEASE)

    def test_cup_leaves_and_comes_back_to_the_table(self):
        cup = self.m["cup"]
        self.assertEqual((cup["leaves"], cup["back"]), (CUP_LEAVES, CUP_BACK))
        self.assertEqual(self.scene["x_t114"]["beats_authored"]["place_contact"], CUP_BACK)
        self.assertLess(cup["end_offset_mm"], 0.5)

    def test_notice_delays(self):
        ev = {e["kind"]: round(e["time"] * 24) + 1 for e in self.scene["events"]}
        w = self.series("girl", "WideOpen")
        self.assertLess(max(w[:ev["object_appears"]]), 0.01)
        first = next(i + 1 for i, v in enumerate(w) if v > 0.1)
        self.assertEqual(first, HER_NOTICE_SIGN)
        lo, hi = val(load(PROFILES["girl"])["reaction"]["delay_frames"])
        self.assertTrue(lo <= first - ev["object_appears"] <= hi + 6, first)  # quick: her 4-6 f + the face ramp
        pass_start = next(a for a in self.scene["actions"] if a["type"] == "pass")["start"]
        e = self.series("boy", "EyeWide")
        answer = next(i + 1 for i, v in enumerate(e) if i + 1 >= pass_start and v > 0.1)
        self.assertEqual(answer, HIS_ANSWER_SIGN)
        lo, hi = val(load(PROFILES["boy"])["reaction"]["delay_frames"])
        self.assertTrue(lo <= answer - pass_start <= hi + 6, answer)  # late: his 16-26 f + the face ramp
        self.assertLess(max(e[:pass_start]), 0.1)  # no interest before the offer reaches him

    def test_delight_beat(self):
        s = self.series("girl", "Smile")
        self.assertLess(max(s[:HIS_CONTACT - 8]), 0.01)
        self.assertGreaterEqual(max(s[HIS_CONTACT - 2:HER_RELEASE]), 0.8)
        self.assertGreaterEqual(min(s[HER_RELEASE:]), 0.8)  # held to the end

    def test_eyes_inside_the_gaze_range(self):
        # T-113 open point 3: during blinks the eyes stay inside the range the lids were fitted for
        for who, eyes in self.m["eyes"].items():
            spec = load(ROOT / "assets" / "characters" / SPECS[who] / "spec.resolved.json")
            yaw, pitch = spec["face"]["eyes"]["gaze_range_deg"]
            self.assertLessEqual(eyes["blink"]["yaw_deg"], yaw, who)
            self.assertLessEqual(eyes["blink"]["pitch_deg"], pitch, who)

    def test_no_engine_warning(self):
        log = self.path.parent / "logs" / "bake.log"
        if log.is_file():
            self.assertNotIn("warning", log.read_text(encoding="utf-8").lower())

    def test_personality_and_animcheck_limits(self):
        scene_path = self.path.parent / "shot.resolved.scene.json"
        sp = scene_path if scene_path.is_file() else SHOT
        rep = personality.analyse(self.bake, load(sp), sp)
        self.assertEqual([f for c in rep["characters"] for f in c.get("fails", [])], [])
        thr = load(ROOT / "tools" / "animcheck" / "thresholds.json")
        self.assertEqual(animcheck.check(animcheck.analyse(self.bake, load(sp), sp), thr), [])


def main():
    global BAKE
    argv = sys.argv[1:]
    if "--bake" in argv:
        i = argv.index("--bake")
        BAKE = argv[i + 1]
        del argv[i:i + 2]
    unittest.main(argv=[sys.argv[0]] + argv, verbosity=2)


BAKE = os.environ.get("PLUSH_E909_BAKE") or (str(SHOT.parent / "build" / "bake.json") if (SHOT.parent / "build" / "bake.json").is_file() else None)
if __name__ == "__main__":
    main()
