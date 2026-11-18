#!/usr/bin/env python3
"""T-087 fidelity fixes in tools/fidelity/run.py: no silent A-pose fallback, hide filter never hides garments and
records what it really hid, garment.<item>.* measured against an annotated accessory:<item> region. No Blender."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run  # noqa: E402


class VariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.master = os.path.join(self.tmp.name, "kid_master.blend")
        open(self.master, "w").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_compare_variant_fails_clearly(self):
        with self.assertRaises(run.BuildError) as cm:
            run.variant_blend(self.master, "compare")
        msg = str(cm.exception)
        self.assertIn("kid_compare.blend does not exist", msg)
        self.assertIn("never used as a silent fallback", msg)

    def test_compare_variant_used_when_present(self):
        compare = os.path.join(self.tmp.name, "kid_compare.blend")
        open(compare, "w").close()
        self.assertEqual(run.variant_blend(self.master, "compare"), compare)
        self.assertEqual(run.variant_blend(compare, "compare"), compare)

    def test_unknown_build_name_fails_for_compare(self):
        other = os.path.join(self.tmp.name, "something.blend")
        open(other, "w").close()
        with self.assertRaises(run.BuildError):
            run.variant_blend(other, "compare")

    def test_master_variant_is_the_master(self):
        self.assertEqual(run.variant_blend(self.master, "master"), self.master)
        with self.assertRaises(run.BuildError):
            run.variant_blend(self.master, "tpose")

    def test_build_error_is_a_failing_exit(self):
        self.assertTrue(issubclass(run.BuildError, SystemExit))


class HideFilterTests(unittest.TestCase):
    def test_garments_are_never_hidden(self):
        applied, ignored = run.effective_hide(["backpack_body", "garment.backpack.main", "garment.backpack"])
        self.assertEqual(applied, ["backpack_body"])
        self.assertEqual(ignored, ["garment.backpack.main", "garment.backpack"])

    def test_garment_alias_rules_from_annotations(self):
        anns = {"front": {"regions": {"accessory:backpack": [], "hair": []}},
                "back": {"regions": {"garment:hoodie": []}}}
        self.assertEqual(run.garment_alias_rules(anns), [["garment.backpack.*", "accessory:backpack"]])
        self.assertEqual(run.garment_alias_rules({}), [])

    def test_alias_matches_garment_objects_only(self):
        import fnmatch
        glob, region = run.garment_alias_rules({"v": {"regions": {"accessory:backpack": []}}})[0]
        for name in ("garment.backpack.main", "garment.backpack.strap.L.fibres", "garment.backpack.zip.main"):
            self.assertTrue(fnmatch.fnmatchcase(name, glob), name)
        for name in ("backpack_body", "garment.hoodie.main"):
            self.assertFalse(fnmatch.fnmatchcase(name, glob), name)

    def test_prepared_objects_reads_what_was_really_hidden(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write("$ blender ...\nnoise\n")
            f.write('{"prepared": "x.blend", "hidden": ["backpack_body.001"]}\n')
            f.write('$ blender next\n')
        try:
            self.assertEqual(run.prepared_objects(f.name), ["backpack_body.001"])
        finally:
            os.unlink(f.name)
        self.assertIsNone(run.prepared_objects("/nonexistent/log"))


if __name__ == "__main__":
    unittest.main()
