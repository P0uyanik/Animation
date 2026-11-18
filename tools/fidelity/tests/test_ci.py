#!/usr/bin/env python3
"""Unit tests for fidelity CI selection and score-delta policy."""

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci  # noqa: E402


class ScoreDeltaTests(unittest.TestCase):
    def test_increase_is_informational(self):
        result = ci.compare_score(66.5, 64.0)
        self.assertTrue(result.ok)
        self.assertEqual(result.delta, 2.5)
        self.assertIn("+2.50", result.detail)

    def test_exactly_two_point_drop_passes(self):
        result = ci.compare_score(62.0, 64.0)
        self.assertTrue(result.ok)
        self.assertEqual(result.delta, -2.0)

    def test_exactly_two_point_drop_is_not_flagged(self):
        self.assertFalse(ci.compare_score(62.0, 64.0).needs_owner_review)

    def test_more_than_two_point_drop_flags_owner_review_instead_of_failing(self):
        # T-087 rule change (owner-approved round 2 plan A3): PASS with a warning and a summary line
        result = ci.compare_score(61.99, 64.0)
        self.assertTrue(result.ok)
        self.assertTrue(result.needs_owner_review)
        self.assertIn("-2.01", result.detail)
        self.assertIn("WARNING", result.detail)
        self.assertIn("visual regression, needs owner review", result.detail)
        line = ci.summary_line("girl", result)
        self.assertTrue(line.startswith("NEEDS OWNER REVIEW: girl fidelity"))
        self.assertEqual(ci.summary_line("boy", ci.compare_score(66.5, 64.0)), "boy fidelity score 66.50 (+2.50 vs baseline 64.00)")

    def test_large_drop_still_reported(self):
        result = ci.compare_score(40.0, 64.0)
        self.assertTrue(result.needs_owner_review)
        self.assertIn("-24.00", result.detail)


class AffectedCharacterTests(unittest.TestCase):
    characters = {"boy", "girl"}

    def test_character_spec_only_selects_that_character(self):
        changed = {"assets/characters/girl/spec/girl.spec.json"}
        self.assertEqual(ci.affected_characters(changed, self.characters), ["girl"])

    def test_reference_annotation_only_selects_that_character(self):
        changed = {"assets/characters/boy/references/annotations/front.json"}
        self.assertEqual(ci.affected_characters(changed, self.characters), ["boy"])

    def test_shared_generator_selects_every_fidelity_character(self):
        changed = {"pipeline/charsys/garments/generator.py"}
        self.assertEqual(ci.affected_characters(changed, self.characters), ["boy", "girl"])

    def test_unrelated_change_selects_none(self):
        self.assertEqual(ci.affected_characters({"docs/README.md"}, self.characters), [])


def load_tests(loader, tests, pattern):
    """CI runs this file (tools/check_all.py); it also runs the T-087 tests of tools/fidelity/run.py, tools/regression/run.py and of the review
    recipe (tools/review/tests/test_recipe.py)."""
    here = Path(__file__).resolve().parent
    for path in (here, here.parents[1] / "review" / "tests"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import test_run  # noqa: E402
    import test_recipe  # noqa: E402
    import test_regression_flag  # noqa: E402
    tests.addTests(loader.loadTestsFromModule(test_run))
    tests.addTests(loader.loadTestsFromModule(test_regression_flag))
    tests.addTests(loader.loadTestsFromModule(test_recipe))
    return tests


if __name__ == "__main__":
    unittest.main()
