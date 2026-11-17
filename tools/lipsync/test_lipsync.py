import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import extract
from validate import validate


HERE = Path(__file__).resolve().parent


class LipSyncTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.audio = Path(folder.name, "tone.wav")
        self.out = Path(folder.name, "track.json")
        rate = 8000
        with wave.open(str(self.audio), "wb") as wav:
            wav.setparams((2, 2, rate, 0, "NONE", ""))
            data = bytearray()
            for i in range(rate + 1):
                value = 0
                if rate // 4 <= i < rate * 3 // 4:
                    hz = 220 if i < rate // 2 else 2400
                    value = round(16000 * math.sin(2 * math.pi * hz * i / rate))
                data.extend(struct.pack("<hh", value, -value))
            wav.writeframes(data)

    def test_audio_cli_timing_and_smoothing(self):
        for fps in (24, 30):
            subprocess.run([sys.executable, HERE / "extract.py", "--audio", self.audio,
                            "--fps", str(fps), "--out", self.out], check=True)
            subprocess.run([sys.executable, HERE / "validate.py", self.out], check=True)
            doc = json.loads(self.out.read_text())
            self.assertEqual(doc["duration"], 8001 / 8000)
            frames = doc["frames"]
            self.assertEqual(len(frames), fps + 1)
            self.assertEqual(frames[0], {"rest": 1})
            self.assertEqual(frames[-1], {"rest": 1})
            self.assertEqual(frames[fps // 3], {"AI": 1})
            self.assertEqual(frames[2 * fps // 3], {"FV": 1})
            self.assertGreater(frames[fps // 4 - 1].get("AI", 0), 0)
            for a, b in zip(frames, frames[1:]):
                for shape in a.keys() | b.keys():
                    self.assertLessEqual(abs(a.get(shape, 0) - b.get(shape, 0)), .5)

    def test_text_tracks_active_time(self):
        doc = extract.extract(self.audio, "moo", 24, None)
        self.assertEqual(doc["source"], "fallback-text")
        self.assertEqual(doc["frames"][8], {"MBP": 1})
        self.assertEqual(doc["frames"][15], {"U": 1})
        self.assertEqual(doc["frames"][1], {"rest": 1})

    def test_silent_unsigned_pcm(self):
        with wave.open(str(self.audio), "wb") as wav:
            wav.setparams((1, 1, 8000, 0, "NONE", ""))
            wav.writeframes(bytes([128]) * 10)
        doc = extract.extract(self.audio, "aaaa", 30, None)
        self.assertEqual(doc["frames"], [{"rest": 1}])

    def test_text_respects_internal_pause_across_sample_widths(self):
        for width in (1, 2, 3, 4):
            with self.subTest(width=width):
                scale = 1 << (width * 8 - 1)
                data = bytearray()
                for i in range(8000):
                    sample = round(scale * .3 * math.sin(i / 5)) if i < 2000 or i >= 6000 else 0
                    if width == 1:
                        sample += 128
                    data.extend(sample.to_bytes(width, "little", signed=width > 1))
                with wave.open(str(self.audio), "wb") as wav:
                    wav.setparams((1, width, 8000, 0, "NONE", ""))
                    wav.writeframes(data)
                frames = extract.extract(self.audio, "fee", 24, None)["frames"]
                self.assertEqual(frames[3], {"FV": 1})
                self.assertEqual(frames[12], {"rest": 1})
                self.assertEqual(frames[21], {"E": 1})

    def test_recognizer_adapter(self):
        def respond(args, **kwargs):
            if "--version" in args:
                return subprocess.CompletedProcess(args, 0, "Rhubarb Lip Sync version 1.13.0", "")
            self.assertEqual(Path(args[args.index("--dialogFile") + 1]).read_text(), "hello")
            self.assertEqual(args[-1], str(self.audio.resolve()))
            cues = [{"start": .25, "end": .50, "value": "H"}]
            return subprocess.CompletedProcess(args, 0, json.dumps({"mouthCues": cues}), "")
        with patch.object(subprocess, "run", side_effect=respond):
            doc = extract.extract(self.audio, "hello", 24, Path(sys.executable))
        self.assertEqual(doc["frames"][8], {"L": 1})
        self.assertEqual(doc["frames"][13], {"rest": 1})
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "1.13.01", "")):
            with self.assertRaisesRegex(ValueError, "expected Rhubarb"):
                extract.run_rhubarb(Path(sys.executable), self.audio, "")

    def test_partial_and_invalid_cues(self):
        cues = [{"start": .01, "end": .02, "value": "A"}]
        frame = extract.sample_cues(cues, 1, 30, .03)[0]
        self.assertAlmostEqual(frame["MBP"], 1/3)
        self.assertAlmostEqual(frame["rest"], 2/3)
        with self.assertRaises(ValueError):
            extract.sample_cues(cues * 2, 1, 30, .03)

    def test_track_validation(self):
        doc = extract.extract(self.audio, "", 24, None)
        for frame in ({"AI": .5}, {"bogus": 1}, {"E": True}, {"rest": float("nan")}):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                validate({**doc, "frames": [frame] + doc["frames"][1:]})
        for changes in ({"fps": 25}, {"frames": doc["frames"][:-1]}):
            with self.assertRaises(ValueError):
                validate({**doc, **changes})

    def test_dialogue_validation(self):
        line = dict(speaker="girl", audio="line.wav", text="hi", start=.25)
        doc = dict(format="plush.dialogue/1", lines=[line])
        validate(doc)
        for change in ({"start": -1}, {"start": True}, {"speaker": " "}, {"audio": ""}):
            with self.assertRaises(ValueError):
                validate({**doc, "lines": [{**line, **change}]})
        with self.assertRaises(ValueError):
            validate({**doc, "lines": [{}]})

    def test_inventory_matches_contract(self):
        library = HERE.parents[1] / "content/visemes/shared_visemes.json"
        ids = json.loads(library.read_text())["visemes"].keys()
        schema = json.loads((HERE / "plush.visemes.schema.json").read_text())
        self.assertEqual(set(schema["properties"]["frames"]["items"]["propertyNames"]["enum"]), ids)
        self.assertEqual(set(extract.RHUBARB_SHAPES.values()) | set(extract.SPELLINGS.values()), ids)
