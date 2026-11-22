"""Plain-Python regression tests for bounded fitting."""
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

HERE = Path(__file__).resolve()
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parents[3])]
from core import ROOT, child, fresh_output, override, read, search, start_values, write
from score import features, measure


class FitTests(unittest.TestCase):
    def test_list_override_preserves_siblings(self):
        base = {"parts": [{"x": [4, 7], "y": 3}, {"x": [1, 2]}], "other": 10}
        bounds = {"parts.0.x.1": [4, 9], "parts.0.y": [0, 5]}
        start = start_values(base, bounds)
        self.assertEqual(start, {"parts.0.x.1": 7, "parts.0.y": 3})
        self.assertEqual(override(dict.fromkeys(start, 5), base),
                         {"parts": [{"x": [4, 5], "y": 5}, {"x": [1, 2]}]})
        self.assertEqual(base["parts"][0]["x"], [4, 7])
        for key in ("parts.-1.y", "parts.2.x"):
            with self.assertRaises(ValueError):
                start_values(base, {key: [0, 1]})

    def test_bounds(self):
        spec = {"face": {"angle": 3, "fixed": 0}}
        bounds = {"face.angle": [1, 4], "face.fixed": [0, 0]}
        start = start_values(spec, bounds)
        self.assertEqual(override(start), spec)
        seen = []

        def evaluate(i, trial):
            self.assertEqual(i, len(seen))
            self.assertLessEqual(1, trial["face.angle"])
            self.assertLessEqual(trial["face.angle"], 4)
            self.assertEqual(trial["face.fixed"], 0)
            seen.append(trial)
            return trial["face.angle"]

        index, best = search(start, bounds, 11, 16, evaluate)
        self.assertEqual(len(seen), 16)
        self.assertEqual(seen[0], start)
        self.assertEqual(seen[index], best)
        self.assertEqual(best["face.angle"], max(p["face.angle"] for p in seen))
        for bad in ([4, 1], [4, 7], [0, math.inf], [0, math.nan], [1], [False, 4]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                start_values(spec, {"face.angle": bad})
        with self.assertRaises(ValueError):
            start_values(spec, {"face.other": [0, 1]})
        with self.assertRaises(ValueError):
            search(start, bounds, 0, 0, evaluate)

    def test_deterministic_proposal(self):
        def run(seed):
            path = []

            def score(i, values):
                path.append(dict(values))
                return -abs(values["x"] - 0.75)

            i, best = search({"x": 0}, {"x": [0, 1]}, seed, 12, score)
            return path, i, override(best)

        self.assertEqual(run(19), run(19))
        self.assertNotEqual(run(19)[0], run(20)[0])
        self.assertEqual(search({"x": 0}, {"x": [0, 1]}, 2, 4, lambda *_: 1), (0, {"x": 0}))

    def test_mask_and_landmark_scores(self):
        fig = np.zeros((48, 42), bool)
        fig[4:42, 10:32] = True
        eye = np.zeros_like(fig)
        eye[8:11, 20:27] = True
        anchors = {"chin": (21, 20), "neck": (21, 24), "shoulder_L": (28, 26)}
        ref = {"fig": fig, "eyes": eye, "landmarks": {**anchors, "eye_L": (23, 9)}}
        def score(candidate):
            return measure(ref, candidate, ["eye_L", "chin"])[0]
        self.assertEqual(score(ref)["score"], 100)
        damaged = fig.copy()
        damaged[23:28, 12:19] = False
        self.assertLess(score(dict(ref, fig=damaged))["figure_iou"], 1)
        self.assertEqual(score(dict(ref, eyes=~eye))["eye_iou"], 0)
        self.assertLess(score(dict(ref, landmarks=anchors))["score"], 100)
        self.assertAlmostEqual(score(dict(ref, landmarks={**anchors, "eye_L": (23, 13)}))
                               ["landmarks"]["eye_L"]["error_head"], 4/16)
        with self.assertRaises(ValueError):
            score(dict(ref, fig=np.zeros_like(fig)))

    def test_visible_features(self):
        pixels = np.zeros((8, 12, 4), np.uint8)
        pixels[2:5, 4:9] = (255, 0, 0, 255)
        face = features(pixels, {"eye_R": [0, 0]})
        self.assertEqual(face["eyes"].sum(), 15)
        self.assertEqual(face["landmarks"]["eye_inner_L"], [4.5, 3.5])
        self.assertNotIn("eye_R", face["landmarks"])

    def test_winning_outputs_use_earliest_best(self):
        import csv
        from argparse import Namespace
        from PIL import Image
        from tools.fit import run

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            out = folder / "out"
            bounds = folder / "bounds.json"
            index = folder / "reference_index.json"
            view = "front"
            write(bounds, {"angle": [0, 2]})
            write(index, {"views": [{"id": view}]})
            write(folder / "landmarks.json", {"views": {view: {"chin": [15, 19]}}})
            pixels = np.zeros((64, 32, 4), np.uint8)
            pixels[5:60, 9:24] = 255
            crops = folder / "views"
            crops.mkdir()
            Image.fromarray(pixels).save(crops / "front.png")
            Image.fromarray(pixels[:, :, 3]).save(crops / "front_mask.png")
            spec = {"identity": {"id": "test"}, "angle": 1}
            args = Namespace(spec=folder / "spec.json", override=[], bounds=bounds, reference_index=index,
                             variant="master", views=view, landmarks="chin", budget=2, seed=8, height=64,
                             out=out, blender="unused")
            write(args.spec, spec)

            def render(exe, script, flags, work, runtime):
                if script.name == "build_character.py":
                    build = Path(flags[flags.index("--out") + 1])
                    build.mkdir()
                    (build / "test_master.blend").touch()
                else:
                    Image.fromarray(pixels).save(work / "pass-000.png")
                    write(work / "pass-000.json", {"chin": [15, 19]})

            with patch.object(run.specs, "validate", side_effect=lambda value: value), \
                    patch.object(run, "blender", side_effect=render) as worker:
                run.fit(args)
            self.assertEqual(worker.call_count, 4)
            self.assertEqual(read(out / "proposal.json"), {"angle": 1})
            scores = read(out / "scores.json")
            self.assertEqual((scores["best"], len(scores["iterations"])), (0, 2))
            self.assertEqual((out / "overlay.jpg").read_bytes(), (out / "trial-000/overlay.jpg").read_bytes())
            with (out / "scores.csv").open(newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertIn(["all", "score / 100", "100.0", "100.0"], rows)
            self.assertIn(["front", "chin error (head heights)", "0.0", "0.0"], rows)
            self.assertEqual(read(args.spec), spec)

    def test_output_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            other = Path(temp) / "outside"
            other.write_text("original", encoding="utf-8")
            out = fresh_output(Path(temp) / "fit")
            for bad in ("../outside", other, out):
                with self.subTest(path=bad), self.assertRaises(ValueError):
                    child(out, bad).write_text("changed")
            self.assertEqual(other.read_text(), "original")
            with self.assertRaises(ValueError):
                fresh_output(ROOT / "assets/characters")
            child(out, "proposal.json").touch()
            with self.assertRaises(ValueError):
                fresh_output(out)


class T204FitTests(unittest.TestCase):
    """T-215 band fit: loss, finite differences, control selection, seeded CMA-ES (plain Python)."""

    def test_band_loss_and_equal_view_weights(self):
        from core import UNSCORED_LOSS, band_loss, view_cost
        self.assertEqual(band_loss(0), 0)
        self.assertAlmostEqual(band_loss(1), 0.02)
        self.assertAlmostEqual(band_loss(-3), 4 + 0.18)
        self.assertEqual(band_loss(None), UNSCORED_LOSS)
        cost, per = view_cost({"a": {"x": 3, "y": 0}, "b": {"x": 0}}, {"a": ["x", "y"], "b": ["x"]})
        self.assertAlmostEqual(per["a"], (4.18 + 0) / 2)
        self.assertAlmostEqual(cost, per["a"] / 2)  # one measure in b weighs as much as two in a
        cost2, _ = view_cost({"a": {"x": 3}, "b": {}}, {"a": ["x", "y"], "b": ["x"]})
        self.assertGreater(cost2, cost)  # measures that turn unscored are penalised, not dropped

    def test_finite_differences_and_selection(self):
        from core import fd_step, linear_z, select_controls, sensitivity
        self.assertEqual(fd_step(1.0, [0, 2], 0.5), 0.5)
        self.assertEqual(fd_step(1.8, [0, 2], 0.5), -0.5)
        with self.assertRaises(ValueError):
            fd_step(0.5, [0, 1], 2)
        z0 = {"m1": 2.0, "m2": -1.0, "m3": None}
        trials = {"a": {"m1": 1.0, "m2": -1.0, "m3": 0.5}, "b": {"m1": 1.5, "m2": -1.0, "m3": None},
                  "c": {"m1": 2.01, "m2": -1.02, "m3": None}, "d": {"m1": 2.0, "m2": 0.0, "m3": None}}
        steps = {"a": 1.0, "b": -2.0, "c": 1.0, "d": 1.0}
        cols = sensitivity(z0, trials, steps)
        self.assertEqual(cols["a"], {"m1": -1.0, "m2": 0.0})  # unscored at the start: left out
        self.assertEqual(cols["b"], {"m1": 0.5, "m2": 0.0})   # a backward step flips the sign
        kept, dropped = select_controls(cols, ["m1", "m2"], min_effect=0.25, max_cos=0.95)
        self.assertEqual(kept, ["a", "d"])
        self.assertIn("redundant with a", dropped["b"])
        self.assertIn("max |dz|", dropped["c"])
        z = linear_z(z0, cols, {"a": 0.0, "d": 0.0}, steps, {"a": 0.5, "d": 1.0})
        self.assertAlmostEqual(z["m1"], 1.5)
        self.assertAlmostEqual(z["m2"], 0.0)
        self.assertIsNone(z["m3"])

    def test_cmaes_seeded_bounded(self):
        from core import cmaes, edit_penalty
        bounds = {"a": [0, 1], "b": [-1, 0.5]}
        seen = []

        def many(batch):
            seen.extend(batch)
            return [(v["a"] - 0.3) ** 2 + (v["b"] - 0.9) ** 2 for _, v in batch]

        run = lambda seed: cmaes({"a": 0.5, "b": 0.0}, bounds, seed, 60, many, popsize=6)
        i, best, cost = run(4)
        self.assertEqual([j for j, _ in seen], list(range(60)))
        self.assertEqual(seen[0][1], {"a": 0.5, "b": 0.0})  # the mean is the first candidate
        self.assertTrue(all(0 <= v["a"] <= 1 and -1 <= v["b"] <= 0.5 for _, v in seen))
        self.assertAlmostEqual(best["a"], 0.3, places=1)
        self.assertEqual(best["b"], 0.5)  # optimum outside: pinned at the bound
        self.assertEqual(seen[i][1], best)
        first = list(seen)
        seen.clear()
        self.assertEqual(run(4), (i, best, cost))
        self.assertEqual(seen, first)
        self.assertEqual(edit_penalty({"a": 1.0}, {"a": 0.0}, {"a": 0.5}, 0.1), 0.4)


if __name__ == "__main__":
    unittest.main()
