#!/usr/bin/env python3
"""Unit tests for the T-087 review recipe (validation, A-pose/variant refusals, preview gate). No Blender needed:
renders are replaced by stubs; the recipes are the T-087 evidence recipes on the real repository data."""

import copy
import functools
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import recipe as R  # noqa: E402
import strict_sheet  # noqa: E402,F401  (patched by name in PreviewGateTests)

VALIDATE = R.validate

EVIDENCE = os.path.join(R.ROOT, "docs", "evaluation", "process", "T-087")
BOY = json.load(open(os.path.join(EVIDENCE, "boy_1.1.0_vs_2.0.0.recipe.json")))
GIRL = json.load(open(os.path.join(EVIDENCE, "girl_0.10.0_vs_0.11.0.recipe.json")))


def refused(test, recipe, fragment, check_git=False):
    with test.assertRaises(R.RecipeError) as cm:
        R.validate(recipe, check_git=check_git)
    test.assertTrue(any(fragment in p for p in cm.exception.problems),
                    f"{fragment!r} not in {cm.exception.problems}")


class ValidateTests(unittest.TestCase):
    def test_boy_recipe_is_valid_and_resolves_everything(self):
        res = R.validate(copy.deepcopy(BOY), check_git=False)
        self.assertEqual([c["version"] for c in res["columns"]], ["1.1.0", "2.0.0"])
        self.assertEqual([v["name"] for v in res["cameras"]["views"]], [r for r, _, _ in R.ROWS])
        yaws = {v["name"]: v["yaw_deg"] for v in res["cameras"]["views"]}
        self.assertEqual(yaws["threequarter"], -35.0)  # taken from reference_index.json
        self.assertEqual(yaws["side"], -90.0)
        for c in res["columns"]:  # compare variant: the arms are lowered by each version's own comparison pose
            self.assertIn("upper_arm_fk_rotation_y_deg", c["comparison_pose"])

    def test_input_shas_are_checked_against_git(self):
        R.validate(copy.deepcopy(BOY), check_git=True)  # ab9fd4c is the T-087 input commit
        r = copy.deepcopy(BOY)
        r["inputs"]["main"] = "0000000"
        refused(self, r, "not found in this repository", check_git=True)
        r["inputs"]["main"] = "main"
        refused(self, r, "not a commit SHA")

    def test_apose_refused_unless_explicit(self):
        r = copy.deepcopy(GIRL)
        R.validate(r, check_git=False)
        del r["compare"]["allow_apose"]
        refused(self, r, "refused unless compare.allow_apose is true")

    def test_wrong_variant_refused(self):
        r = copy.deepcopy(BOY)  # boy references (#27) are arms-down: the A-pose master is the wrong variant
        r["compare"] = {"variant": "master", "pose": "apose", "allow_apose": True}
        refused(self, r, "differs from the variant the references match")
        r["compare"]["allow_variant_mismatch"] = True
        R.validate(r, check_git=False)

    def test_pose_must_match_variant(self):
        r = copy.deepcopy(BOY)
        r["compare"]["pose"] = "apose"
        refused(self, r, "does not match compare.variant")

    def test_compare_variant_never_falls_back_to_apose_master(self):
        r = copy.deepcopy(BOY)
        r["candidate"] = {"blend": "assets/characters/boy_yellow_hoodie/versions/2.0.0/boy_yellow_hoodie_master.blend"}
        refused(self, r, "is an A-pose master but the compare variant")
        g = copy.deepcopy(GIRL)  # no rig.comparison_pose in the girl's versions: no arms-down variant exists
        g["compare"] = {"variant": "compare", "pose": "arms_down", "allow_variant_mismatch": True}
        refused(self, g, "refusing to render its A-pose master")

    def test_baseline_must_be_published_and_current_unless_allowed(self):
        r = copy.deepcopy(BOY)
        del r["baseline"]["allow_not_current"]
        refused(self, r, "is not the current approved version")
        r["baseline"] = {"version": "9.9.9"}
        refused(self, r, "is not published")

    def test_candidate_spec_needs_sha(self):
        r = copy.deepcopy(BOY)
        r["candidate"] = {"spec": "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0.spec.json"}
        refused(self, r, "needs its commit SHA")
        r["candidate"]["sha"] = "ab9fd4c"
        R.validate(r, check_git=False)

    def test_rows_and_yaws(self):
        r = copy.deepcopy(BOY)
        del r["cameras"]["rows"]["back"]
        refused(self, r, "missing back")
        r = copy.deepcopy(BOY)
        r["cameras"]["rows"]["side"]["yaw_deg"] = 90
        refused(self, r, "differs from the reference yaw")

    def test_face_rows_can_fit_the_head(self):
        res = R.validate(copy.deepcopy(BOY), check_git=False)
        face = [v for v in res["cameras"]["views"] if v["framing"] == "face"]
        self.assertTrue(all(v["fit"] == "head" and v["target"] is None for v in face))
        job = R.render_job(res, [], "/x", res["preview"])
        self.assertEqual({v["fit"] for v in job["views"] if "fit" in v}, {"head"})
        r = copy.deepcopy(BOY)
        r["cameras"]["framing"]["body"] = {"fit": "head", "aspect": 1.6}  # body rows need a fixed camera
        refused(self, r, "cameras.framing.body")

    def test_light_and_cheap_preview(self):
        r = copy.deepcopy(BOY)
        r["light"]["calibration"] = "studio_bright/9"
        refused(self, r, "unknown light rig")
        r = copy.deepcopy(BOY)
        r["preview"]["samples"] = 64
        refused(self, r, "the preview must stay cheap")


class PoseCheckTests(unittest.TestCase):
    def test_apose_render_refused_for_compare_variant(self):
        res = R.validate(copy.deepcopy(BOY), check_git=False)
        result = {"columns": {"baseline": {"arm_angle_from_down_deg": {"L": 5.5, "R": 5.5}},
                              "candidate": {"arm_angle_from_down_deg": {"L": 45.0, "R": 45.0}}}}
        problems = R.pose_problems(res, result)
        self.assertEqual(len(problems), 1)
        self.assertIn("candidate", problems[0])
        self.assertIn("A-pose", problems[0])

    def test_arms_down_refused_for_apose_variant(self):
        res = R.validate(copy.deepcopy(GIRL), check_git=False)
        ok = {"columns": {"baseline": {"arm_angle_from_down_deg": {"L": 32.0, "R": 32.0}}}}
        self.assertEqual(R.pose_problems(res, ok), [])
        bad = {"columns": {"baseline": {"arm_angle_from_down_deg": {"L": 12.0, "R": 12.0}}}}
        self.assertEqual(len(R.pose_problems(res, bad)), 1)


class PreviewGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = self.tmp.name
        self.recipe_path = os.path.join(self.out, "boy.recipe.json")
        json.dump(BOY, open(self.recipe_path, "w"))
        self.resolved = R.validate(copy.deepcopy(BOY), check_git=False)

    def tearDown(self):
        self.tmp.cleanup()

    def write_preview(self, **kw):
        rec = {"recipe_sha256": self.resolved["recipe_sha256"], "status": "pass", "problems": [], "at": "t"}
        rec.update(kw)
        os.makedirs(os.path.join(self.out, "preview"), exist_ok=True)
        json.dump(rec, open(os.path.join(self.out, "preview", "preview.json"), "w"))

    def test_preview_record_states(self):
        self.assertFalse(R.preview_record_ok(self.out, self.resolved)[0])
        self.write_preview(recipe_sha256="x" * 64)
        ok, why = R.preview_record_ok(self.out, self.resolved)
        self.assertFalse(ok)
        self.assertIn("different recipe", why)
        self.write_preview(status="fail", problems=["candidate: A-pose"])
        self.assertFalse(R.preview_record_ok(self.out, self.resolved)[0])
        self.write_preview()
        self.assertTrue(R.preview_record_ok(self.out, self.resolved)[0])

    def run_sheet(self, *extra):
        result = {"columns": {"baseline": {"arm_angle_from_down_deg": {"L": 5.0, "R": 5.0}},
                              "candidate": {"arm_angle_from_down_deg": {"L": 12.0, "R": 12.0}}}}
        with mock.patch.object(R, "validate", functools.partial(VALIDATE, check_git=False)), \
                mock.patch.object(R, "render", return_value=(self.out, result)) as render, \
                mock.patch("strict_sheet.make_sheet", return_value=(1120, 2048)):
            R.main(["sheet", self.recipe_path, "--blender", "none", "--out", self.out, *extra])
        return render

    def test_long_render_refuses_without_preview(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_sheet()
        self.assertIn("sheet refused", str(cm.exception.code))

    def test_override_flag_is_logged(self):
        render = self.run_sheet("--skip-preview", "test: preview checked by hand")
        self.assertEqual(render.call_count, 1)
        rec = json.load(open(os.path.join(self.out, "sheet.json")))
        self.assertEqual(rec["preview_override"]["reason"], "test: preview checked by hand")
        self.assertIn("PREVIEW OVERRIDE", open(os.path.join(self.out, "log.txt")).read())
        # the recipe is recorded next to the outputs
        self.assertEqual(json.load(open(os.path.join(self.out, "recipe.json"))), BOY)
        self.assertEqual(json.load(open(os.path.join(self.out, "recipe.resolved.json")))["recipe_sha256"],
                         self.resolved["recipe_sha256"])

    def test_sheet_runs_after_a_passing_preview(self):
        self.write_preview()
        render = self.run_sheet()
        self.assertEqual(render.call_count, 1)
        self.assertIsNone(json.load(open(os.path.join(self.out, "sheet.json")))["preview_override"])




if __name__ == "__main__":
    unittest.main()
