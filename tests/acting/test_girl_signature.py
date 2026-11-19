#!/usr/bin/env python3
"""Signature tests for the girl's acting (T-097-girl): girl_auburn_bun_glasses profile, gesture clips and the e908 solo
shot against the reference measurements (docs/evaluation/animation/T-106/, content/timing/reference_timing.json).

    python3 tests/acting/test_girl_signature.py [--bake <e908 bake.json>]      (or: python3 -m pytest tests/acting)

Data checks need nothing but Python. With a bake of episodes/e908_girl_acting/shots/s010 (--bake, $PLUSH_E908_BAKE, or
the shot's build/bake.json when it exists) the measured checks run too: the T-097C acting rule and the T-053
personality limits without a warning or failure, the T-061 animation metrics within tools/animcheck/thresholds.json,
the hand at her chin during the wonder beat, the index aimed at the cup during the point hold, the delighted open smile
only after the success event, and the closed rest face at the end. Without a bake those checks are reported skipped.
"""
import csv
import json
import math
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "animcheck"))
sys.path.insert(0, str(ROOT / "episodes" / "e908_girl_acting"))
import acting  # noqa: E402
import animcheck  # noqa: E402
import girl_beats  # noqa: E402

CID = "girl_auburn_bun_glasses"
PROFILE = ROOT / "content" / "personality" / f"{CID}.json"
SHOT = ROOT / "episodes" / "e908_girl_acting" / "shots" / "s010" / "shot.scene.json"
PERF = ROOT / "docs" / "evaluation" / "animation" / "T-106" / "performance.csv"
TIMING = ROOT / "content" / "timing" / "reference_timing.json"
CLIPS = ["girl_chin_think", "girl_point_down", "girl_wonder_point"]
BAKE = None  # set by --bake / $PLUSH_E908_BAKE / the shot's build folder


def val(rec):
    return rec["value"] if isinstance(rec, dict) and "value" in rec else rec


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def wt_girl_beats():
    """T-106 watertable girl acting beats: {first_frame: duration_frames}."""
    with PERF.open(encoding="utf-8") as f:
        return {int(r["first_frame"]): int(r["duration_frames"]) for r in csv.DictReader(f)
                if r["clip"] == "watertable" and r["character"] == "girl" and r["kind"] == "acting_beat"}


class Profile(unittest.TestCase):
    def setUp(self):
        self.p = load(PROFILE)

    def test_every_record_has_a_source(self):
        def walk(node, path):
            if isinstance(node, dict) and "value" in node:
                self.assertTrue(node.get("source"), f"{path}: no source")
                self.assertIn(node.get("kind"), ("measured", "reference", "estimate", "extrapolation", "default", "owner"), path)
                return
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{path}.{k}")
        for sec in ("tempo", "energy", "posture", "attention", "gaze", "blink", "face", "smile", "reaction", "interaction", "limits"):
            walk(self.p[sec], sec)

    def test_reference_beats_are_the_t106_watertable_beats(self):
        wt = wt_girl_beats()
        rb = val(self.p["tempo"]["reference_beats"])
        for name, first in (("hand_at_chin", 0), ("leave_chin", 15), ("lean_and_point", 22), ("point_hold", 39),
                            ("draw_back", 61), ("straighten", 81), ("end_hold", 96)):
            self.assertEqual(rb[name], wt[first], name)
        # the clip beats use the same numbers (after the invented rise to the chin)
        self.assertEqual([n for _, n, _ in girl_beats.WONDER[1:]], [rb[k] for k in ("hand_at_chin", "leave_chin", "lean_and_point",
                                                                                    "point_hold", "draw_back", "straighten")])
        self.assertAlmostEqual(girl_beats.TEMPO, val(self.p["tempo"]["action_speed"]))

    def test_quick_alert_reaction_inside_the_measured_delay(self):
        lo, hi = load(TIMING)["beats"]["reaction_delay"]["frames"]
        d = val(self.p["reaction"]["delay_frames"])
        self.assertGreaterEqual(d[0], lo)  # never quicker than the measured reaction delay
        self.assertLessEqual(d[1], (lo + hi) / 2)  # alert: the quick half of the range
        self.assertGreaterEqual(val(self.p["reaction"]["gaze_shift"]), 0.8)  # she looks at what happens
        self.assertLess(val(self.p["reaction"]["gesture_min_intensity"]), 0.35)  # gestures more readily than the default

    def test_blink_rhythm_covers_the_t106_rate(self):
        lim = val(self.p["limits"]["blink_interval_frames"])
        wt_rate_interval = 24 * 60 / 35.7  # T-106 README: 35.7 blinks / visible min for the watertable girl
        self.assertLessEqual(lim[0], 25)  # the shortest measured spacing (f054 -> f079)
        self.assertGreaterEqual(lim[1], round(wt_rate_interval))
        self.assertEqual(val(self.p["blink"]["couple_to_action_change"]), True)  # WT blinks as the hand leaves the chin

    def test_gestures_name_existing_girl_clips(self):
        names = {g["name"]: g for g in val(self.p["gestures"])}
        for g, clip in (("hand_to_chin_think", "girl_chin_think"), ("point_and_explain", "girl_point_down"),
                        ("wonder_point", "girl_wonder_point")):
            self.assertEqual(names[g].get("clip"), clip)
            self.assertTrue((ROOT / "content" / "clips" / f"{clip}.clip.json").is_file(), clip)

    def test_rest_face_unchanged_delighted_is_an_acting_beat(self):
        self.assertEqual(val(self.p["face"]["rest_offset"]), {})  # the modelled closed gentle smile at rest
        self.assertEqual(self.p["face"]["mouth_rest"]["value"], "closed_gentle_smile")
        self.assertIn("open smile", val(self.p["reaction"]["delighted_style"]))

    def test_gesture_amplitude_limit(self):
        self.assertLessEqual(val(self.p["limits"]["gesture_amplitude_max"]), 1.0)
        self.assertGreaterEqual(val(self.p["limits"]["gesture_amplitude_max"]), val(self.p["energy"]["gesture_amplitude"]))


class Emotions(unittest.TestCase):
    def test_girl_emotions(self):
        for name in ("girl_wonder", "girl_delighted"):
            e = load(ROOT / "content" / "emotions" / f"{name}.emotion.json")
            self.assertEqual((e["format"], e["version"], e["name"]), ("plush.emotion", 1, name))
            self.assertTrue((ROOT / "content" / "clips" / f"{e['body']['clip']}.clip.json").is_file())
            self.assertTrue(e.get("reference"))
        d = load(ROOT / "content" / "emotions" / "girl_delighted.emotion.json")
        self.assertEqual(d["face"], {"smile": 1.0})  # the model's open Smile preset: the delighted acting-beat mouth
        self.assertFalse(any(r.startswith(("upperArm", "forearm", "hand")) for r in d["body"]["mask"]))  # arms keep the gesture
        w = load(ROOT / "content" / "emotions" / "girl_wonder.emotion.json")
        self.assertIn("WideOpen", w["face"])  # T-106 WT [0, 15): eyes wide, mouth rounded open

    def test_profile_events_use_the_girl_files(self):
        ev = val(load(PROFILE)["reaction"]["events"])
        self.assertEqual(ev["object_appears"]["emotion"], "girl_wonder")
        self.assertEqual(ev["object_appears"]["gestures"][0], "girl_wonder_point")
        self.assertEqual(ev["success"]["emotion"], "girl_delighted")
        for e in ev.values():
            self.assertTrue((ROOT / "content" / "emotions" / f"{e['emotion']}.emotion.json").is_file())
            for g in e.get("gestures", []):
                self.assertTrue((ROOT / "content" / "clips" / f"{g}.clip.json").is_file(), g)
        p = load(PROFILE)["reaction"]
        mid = sum(val(p["delay_frames"])) / 2 * val(p["tempo_scale"])
        self.assertGreaterEqual(mid, val(p["delay_frames"])[0])  # quick, never before the notice delay


class Clips(unittest.TestCase):
    def test_clip_files(self):
        for name in CLIPS:
            c = load(ROOT / "content" / "clips" / f"{name}.clip.json")
            self.assertEqual((c["format"], c["name"], c["fps"], c["loop"]), ("plush.clip", name, 24.0, False))
            self.assertEqual(c["mirror"]["suffix"], [".L", ".R"])
            self.assertIn("upperArm.R", c["mask"])
            self.assertFalse(any(r.endswith(".L") for r in c["mask"]), name)  # one arm; the other stays with the idle
            self.assertNotIn("head", c["mask"])  # gaze and head belong to look
            for role, t in c["tracks"].items():
                for k in t.get("keys", []):
                    self.assertAlmostEqual(math.sqrt(sum(x * x for x in k[1:5])), 1.0, places=3, msg=role)

    def test_wonder_clip_length_is_the_reference_sequence(self):
        c = load(ROOT / "content" / "clips" / "girl_wonder_point.clip.json")
        t7 = girl_beats.wonder_clip_frames()[-1]
        self.assertEqual(c["frame_count"], math.ceil(t7 + 4 * girl_beats.TEMPO))
        played = (t7 - girl_beats.LEAD) / girl_beats.TEMPO  # playback frames at her tempo
        self.assertAlmostEqual(played, sum(n for _, n, _ in girl_beats.WONDER), places=6)


class Shot(unittest.TestCase):
    def setUp(self):
        self.s = load(SHOT)
        self.b = self.s["x_t097_girl"]["beats"]

    def test_order_notice_reaction_gesture_hold_event(self):
        b = self.b
        order = ["E1_object_appears", "notice", "reaction", "chin", "leave_chin", "point", "E2_success", "delighted", "look_up",
                 "point_hold_end", "straight", "end"]  # the delight and the glance arrive while she still points
        self.assertEqual([b[k] for k in order], sorted(b[k] for k in order))
        self.assertGreaterEqual(b["notice"] - b["E1_object_appears"], val(load(PROFILE)["reaction"]["delay_frames"])[0])
        self.assertGreaterEqual(b["end"] - b["straight"], wt_girl_beats()[96])  # the WT end hold

    def test_events_and_cast(self):
        ev = self.s["events"]
        self.assertEqual([e["name"] for e in ev], ["object_appears", "success"])
        self.assertEqual(self.s["production"]["cast"]["girl"], {"character_id": CID, "version": "current"})
        self.assertEqual(self.s["characters"][0]["personality"], CID)

    def test_delighted_is_the_only_open_smile_and_ends_before_the_shot(self):
        emos = [a for a in self.s["actions"] if a["type"] == "emotion"]
        happy = [a for a in emos if a["name"].split("/")[0] in ("happy", "girl_delighted")]
        self.assertEqual(len(happy), 1)
        self.assertGreaterEqual(happy[0]["start"], self.b["E2_success"])
        self.assertLess(happy[0]["end"], self.s["frameEnd"])  # released: the closed rest smile returns
        self.assertFalse([a for a in self.s["actions"] if a["type"] == "expression"])

    def test_acting_rule_on_the_scene(self):
        rep = acting.analyse(self.s, SHOT)  # scene-only rules: the notice delay after each event
        self.assertEqual(rep["warnings"], [])
        glances = rep["characters"][0]["glances"]
        self.assertEqual([g["event"] for g in glances], ["object_appears", "success"])


def _bake():
    if BAKE and Path(BAKE).is_file():
        return load(BAKE)
    return None


class Bake(unittest.TestCase):
    def setUp(self):
        self.bake = _bake()
        if self.bake is None:
            self.skipTest("no e908 bake (run_shot --stages prepare,bake, or --bake)")
        self.s = load(SHOT)
        self.b = self.s["x_t097_girl"]["beats"]
        self.ch = animcheck.Character(next(c for c in self.bake["characters"] if c["name"] == "girl"))
        self.frames = {fd["frame"]: fd for fd in self.bake["frame_data"]}

    def test_acting_and_personality_checks_clean(self):
        import subprocess
        for tool in ("acting.py", "personality.py"):
            out = subprocess.run([sys.executable, str(ROOT / "tools" / "animcheck" / tool), "--scene", str(SHOT), "--bake", str(BAKE)],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertNotIn("WARN", out.stdout)
            self.assertNotIn("FAIL", out.stdout)
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "animcheck" / "animcheck.py"), "--bake", str(BAKE), "--scene", str(SHOT),
                              "--thresholds", str(ROOT / "tools" / "animcheck" / "thresholds.json"), "--check"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("FAIL", out.stdout)

    def test_library_clips_pass_animcheck(self):
        """girl_chin_think and girl_point_down on her package (the bake's), with her profile and life: T-061 metrics."""
        import subprocess
        render = ROOT / "build" / "apps" / "render-cli" / "plush-render"
        if not render.is_file():
            self.skipTest("no engine build (build/apps/render-cli/plush-render)")
        scene = json.loads(json.dumps(self.s))
        scene["characters"][0]["asset"] = next(c for c in self.bake["characters"] if c["name"] == "girl")["package"]
        scene["actions"] = [{"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
                            {"type": "look", "character": "girl", "start": 1, "end": 200, "target": [0.0, 0.45, 0.42]},
                            {"type": "clip", "character": "girl", "clip": "girl_chin_think", "start": 10},
                            {"type": "clip", "character": "girl", "clip": "girl_point_down", "start": 80}]
        scene["frameEnd"] = 170
        scene.pop("events", None)
        scene.pop("production", None)
        out = SHOT.parent / "build" / "test_library_clips"
        out.mkdir(parents=True, exist_ok=True)
        sp, bp = out / "lib.scene.json", out / "lib.bake.json"
        sp.write_text(json.dumps(scene))
        r = subprocess.run([str(render), str(sp), "--bake", str(bp)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("warning", (r.stdout + r.stderr).lower())
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "animcheck" / "animcheck.py"), "--bake", str(bp), "--scene", str(sp),
                            "--thresholds", str(ROOT / "tools" / "animcheck" / "thresholds.json"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_hand_at_chin(self):
        import measure_girl
        rows = {r["frame"]: r for r in measure_girl.measure(self.bake)}
        hold = [rows[f]["chin_mm"] for f in rows if self.b["chin"] + 2 <= f <= self.b["leave_chin"]]
        rest = [rows[f]["chin_mm"] for f in rows if f <= self.b["reaction"]]
        self.assertTrue(hold)
        self.assertLess(max(hold), 40.0)  # knuckles at the chin (fingers curled against it)
        self.assertGreater(min(rest), 200.0)  # arm down before the reaction

    def test_index_aims_at_the_cup(self):
        cup = next(p for p in self.s["props"] if p["name"] == "cup")["transform"]["translation"]
        errs = []
        for f, fd in self.frames.items():
            if self.b["point"] + 3 <= f <= self.b["point_hold_end"] - 1:
                a, t = self.ch.position(fd, "f3a.R"), self.ch.position(fd, "f3b.R")
                d, w = animcheck.vsub(t, a), animcheck.vsub(cup, a)
                errs.append(math.degrees(math.acos(max(-1.0, min(1.0, animcheck.vdot(d, w) / (animcheck.vlen(d) * animcheck.vlen(w)))))))
        self.assertTrue(errs)
        self.assertLess(sum(errs) / len(errs), 10.0)

    def test_open_smile_only_in_the_delighted_beat(self):
        names = next(c for c in self.bake["characters"] if c["name"] == "girl")["morphs"]
        i = names.index("Smile")
        smile = {f: fd["characters"]["girl"]["morphs"][i] for f, fd in self.frames.items()}
        self.assertLess(max(v for f, v in smile.items() if f < self.b["E2_success"]), 0.05)
        self.assertGreater(max(v for f, v in smile.items() if self.b["delighted"] <= f <= self.b["straight"]), 0.7)
        self.assertLess(smile[self.s["frameEnd"]], 0.05)  # back to the modelled closed smile at the end


def main():
    global BAKE
    argv = sys.argv[1:]
    if "--bake" in argv:
        i = argv.index("--bake")
        BAKE = argv[i + 1]
        del argv[i:i + 2]
    unittest.main(argv=[sys.argv[0]] + argv, verbosity=2)


BAKE = os.environ.get("PLUSH_E908_BAKE") or (str(SHOT.parent / "build" / "bake.json") if (SHOT.parent / "build" / "bake.json").is_file() else None)

if __name__ == "__main__":
    main()
