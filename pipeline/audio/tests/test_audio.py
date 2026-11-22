"""T-195 vocal sounds: cue derivation, library / SOURCES.json, synth, mix and mux."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import cues as cuemod  # noqa: E402
import library  # noqa: E402
import mix  # noqa: E402
import synth  # noqa: E402
import vocal  # noqa: E402
import wavio  # noqa: E402

ROOT = library.ROOT
E912 = ROOT / "episodes" / "e912_paper_boat" / "shots"
T187 = ROOT / "docs" / "evaluation" / "video" / "T-187"
EVIDENCE = ROOT / "docs" / "evaluation" / "audio" / "T-195"
SHOTS = [E912 / s / "shot.scene.json" for s in ("s010", "s020", "s030")]
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def e912_cues() -> dict:
    return cuemod.derive(SHOTS, json.loads((T187 / "assembly.json").read_text(encoding="utf-8")))


def tiny_scene(tmp: Path, actions: list[dict], name="s1") -> tuple[Path, dict]:
    d = tmp / name
    d.mkdir(parents=True)
    scene = {"frameRate": [24, 1], "characters": [
        {"name": "a", "personality": "girl_auburn_bun_glasses", "position": [0.0, 0, 0]},
        {"name": "b", "personality": "boy_yellow_hoodie", "position": [0.4, 0, 0]}], "actions": actions}
    (d / "shot.scene.json").write_text(json.dumps(scene), encoding="utf-8")
    assembly = {"fps": 24, "clip": [{"scene": name, "frame": f, "shot": "1"} for f in range(10, 110)]}
    return d / "shot.scene.json", assembly


def emotion(ch, name, start, intensity=1.0):
    return {"type": "emotion", "character": ch, "name": name, "start": start, "intensity": intensity}


class CueTests(unittest.TestCase):
    def test_e912_cue_list(self):
        got = [(c["scene"], c["sceneFrame"], c["clipFrame"], c["character"], c["cue"]) for c in e912_cues()["cues"]]
        # s010 (all 0.6) and s030 (onsets in the pre-roll) are silent; s020 has the surprise, the giggle, the wow.
        self.assertEqual(got, [("s020", 59, 162, "boy", "gasp_oh"), ("s020", 63, 166, "white", "gasp_oh"),
                               ("s020", 73, 176, "auburn", "giggle"), ("s020", 173, 276, "boy", "wow")])

    def test_rules(self):
        with tempfile.TemporaryDirectory() as t:
            shot, asm = tiny_scene(Path(t), [
                emotion("a", "surprised", 5),            # start before the rendered range: silent
                emotion("a", "happy", 20, 0.69),          # below minIntensity: silent
                emotion("a", "girl_eager", 30),           # mapped to null: silent
                emotion("a", "no_such_emotion", 35),      # unknown: silent
                emotion("b", "happy/laugh", 40),          # variant name -> laugh
                emotion("b", "surprised", 50),            # same character 10 frames later: min gap drops it
                emotion("a", "surprised/some_variant", 60, 0.7),  # base-name fallback, quietest level
                emotion("b", "happy", 108),               # cue frame after the last rendered frame: silent
            ])
            got = cuemod.derive([shot], asm)["cues"]
        self.assertEqual([(c["character"], c["emotion"], c["cue"]) for c in got],
                         [("b", "happy/laugh", "laugh"), ("a", "surprised/some_variant", "gasp_oh")])
        self.assertAlmostEqual(got[1]["gainDb"], -9.0)
        self.assertAlmostEqual(got[0]["gainDb"], 0.0)
        self.assertEqual(got[0]["sceneFrame"], 40 + round(0.25 * cuemod.emotion_onset("happy/laugh") * 24))

    def test_read_only(self):
        before = {p: p.read_bytes() for p in SHOTS}
        e912_cues()
        self.assertEqual(before, {p: p.read_bytes() for p in SHOTS})


class LibraryTests(unittest.TestCase):
    def test_repository_library(self):
        self.assertEqual(library.check(), [])
        doc = library.load_sources()
        self.assertEqual(set(doc["allowedLicences"]), set(library.ALLOWED_LICENCES))
        cues_used = {e["cue"] for e in json.loads(cuemod.CUE_MAP.read_text())["emotions"].values() if e.get("cue")}
        for cue in cues_used:
            self.assertTrue(library.candidates(cue), cue)

    def test_check_rejects(self):
        with tempfile.TemporaryDirectory() as t:
            sounds = Path(t)
            x = synth.make("hm", 0)
            wavio.write(sounds / "library/hm/a.wav", x, synth.RATE)
            entry = {"path": "library/hm/a.wav", "sha256": wavio.sha256(sounds / "library/hm/a.wav"), "cue": "hm",
                     "placeholder": False, "licence": "CC0-1.0", "evidence": "https://example.invalid/licence",
                     "source": {"kind": "download", "url": "https://example.invalid/a"}}
            doc = {"format": "plush.soundsources", "version": 1, "sounds": [entry]}
            library.save_sources(doc, sounds)
            self.assertEqual(library.check(sounds), [])
            for licence in ("CC-BY-4.0", "CC-BY-NC-4.0", "CC-BY-SA-4.0", "royalty-free", None):
                bad = copy.deepcopy(doc)
                bad["sounds"][0]["licence"] = licence
                library.save_sources(bad, sounds)
                self.assertTrue(any("licence" in p for p in library.check(sounds)), licence)
            bad = copy.deepcopy(doc)
            bad["sounds"][0]["sha256"] = "0" * 64
            library.save_sources(bad, sounds)
            self.assertTrue(any("sha256" in p for p in library.check(sounds)))
            bad = copy.deepcopy(doc)
            del bad["sounds"][0]["evidence"]
            library.save_sources(bad, sounds)
            self.assertTrue(any("evidence" in p for p in library.check(sounds)))
            library.save_sources(doc, sounds)
            (sounds / "library/hm/stray.wav").write_bytes((sounds / "library/hm/a.wav").read_bytes())
            self.assertTrue(any("without a SOURCES.json entry" in p for p in library.check(sounds)))

    def test_real_sound_replaces_placeholders(self):
        with tempfile.TemporaryDirectory() as t:
            sounds = Path(t)
            entries = []
            for name, placeholder in (("proc_0.wav", True), ("proc_1.wav", True), ("owner_take1.wav", False)):
                wavio.write(sounds / f"library/wow/{name}", synth.make("wow", 0), synth.RATE)
                entries.append({"path": f"library/wow/{name}", "cue": "wow", "placeholder": placeholder,
                                "sha256": wavio.sha256(sounds / f"library/wow/{name}"), "licence": "project-own",
                                "evidence": "x", "source": {"kind": "recorded", "by": "owner"}})
            library.save_sources({"sounds": entries}, sounds)
            self.assertEqual([e["path"] for e in library.candidates("wow", sounds)], ["library/wow/owner_take1.wav"])


class SynthTests(unittest.TestCase):
    def test_deterministic_and_bounded(self):
        for cue, n in library.PLACEHOLDERS.items():
            for v in range(n):
                a, b = synth.make(cue, v), synth.make(cue, v)
                self.assertTrue(np.array_equal(a, b), (cue, v))
                self.assertTrue(np.isfinite(a).all())
                self.assertAlmostEqual(20 * np.log10(np.max(np.abs(a))), -6.0, places=3)
                self.assertLess(len(a) / synth.RATE, 1.5)
                # starts and ends silent (no click at the edges)
                self.assertLess(abs(a[0]), 1e-3)
                self.assertLess(abs(a[-1]), 1e-3)


class MixTests(unittest.TestCase):
    def test_e912_mix(self):
        doc = e912_cues()
        y1, plan, bus = mix.render(doc)
        y2, _, _ = mix.render(doc)
        self.assertEqual(wavio.to_pcm16(y1), wavio.to_pcm16(y2))
        self.assertEqual(y1.shape, (round(434 / 24 * mix.RATE), 2))
        self.assertLessEqual(np.max(np.abs(y1)), 10 ** (-1 / 20) + 1e-9)
        boy = [p for p in plan if p["character"] == "boy"][0]
        white = [p for p in plan if p["character"] == "white"][0]
        self.assertLess(boy["cents"], -250)
        self.assertGreater(white["cents"], 100)
        self.assertGreater(boy["pan"], 0)
        self.assertLess(white["pan"], 0)
        # the boy's gasp is louder on the right
        s = round(boy["clipFrame"] / 24 * mix.RATE)
        seg = y1[s:s + mix.RATE // 4]
        self.assertGreater(np.abs(seg[:, 1]).sum(), np.abs(seg[:, 0]).sum())
        # silence where there are no cues (shot 1)
        self.assertEqual(np.max(np.abs(y1[: 5 * mix.RATE])), 0.0)

    def test_bus_limit_and_mono(self):
        loud = {"fps": 24, "frames": 48, "cues": [
            {"clipFrame": 2, "scene": "x", "sceneFrame": k, "character": f"c{k}", "personality": "",
             "seatX": 0, "cue": "gasp_oh", "gainDb": 6.0} for k in range(12)]}
        y, _, bus = mix.render(loud, stereo=False)
        self.assertEqual(y.ndim, 1)
        self.assertLess(bus, 0)
        self.assertAlmostEqual(np.max(np.abs(y)), 10 ** (-1 / 20), places=9)
        self.assertLessEqual(np.max(np.abs(np.round(y * 32767))), 32767)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg / ffprobe not on PATH")
class MuxTests(unittest.TestCase):
    def test_mux_copies_video(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            video = t / "v.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=24:duration=1",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
            before = video.read_bytes()
            doc = {"fps": 24, "frames": 24, "cues": [{"clipFrame": 3, "scene": "x", "sceneFrame": 3, "character": "a",
                                                      "personality": "", "seatX": 0, "cue": "wow", "gainDb": 0}]}
            y, _, _ = mix.render(doc)
            wavio.write(t / "a.wav", y, mix.RATE)
            info = vocal.mux(video, t / "a.wav", t / "out.mp4")
            self.assertEqual(video.read_bytes(), before)
            kinds = {s["codec_type"]: s["codec_name"] for s in info["streams"]}
            self.assertEqual(kinds, {"video": "h264", "audio": "aac"})
            self.assertEqual(vocal.video_stream_md5(video), vocal.video_stream_md5(t / "out.mp4"))
            with self.assertRaises(ValueError):
                vocal.mux(video, t / "a.wav", video)


class EvidenceTests(unittest.TestCase):
    """The committed demo matches what the code derives now (re-run `vocal.py demo` after changing a rule)."""

    def test_demo_matches(self):
        report = json.loads((EVIDENCE / "T-195_paper_boat_vocal.cues.json").read_text(encoding="utf-8"))
        doc = e912_cues()
        y, plan, _ = mix.render(doc)
        keys = ("clipFrame", "character", "cue", "sound", "cents", "gainDb", "pan")
        self.assertEqual([{k: p[k] for k in keys} for p in plan], [{k: p[k] for k in keys} for p in report["cues"]])
        import hashlib
        with tempfile.TemporaryDirectory() as t:
            wavio.write(Path(t) / "m.wav", y, mix.RATE)
            self.assertEqual(wavio.sha256(Path(t) / "m.wav"), report["mix"]["wavSha256"])
        self.assertEqual(report["video"]["inputSha256"],
                         hashlib.sha256((T187 / "T-187_paper_boat_h264.mp4").read_bytes()).hexdigest())
        if HAVE_FFMPEG:
            self.assertEqual(vocal.video_stream_md5(EVIDENCE / "T-195_paper_boat_vocal.mp4"),
                             vocal.video_stream_md5(T187 / "T-187_paper_boat_h264.mp4"))


if __name__ == "__main__":
    unittest.main()
