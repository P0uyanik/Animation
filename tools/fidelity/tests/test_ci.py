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

    def test_more_than_two_point_drop_fails_with_required_reason(self):
        result = ci.compare_score(61.99, 64.0)
        self.assertFalse(result.ok)
        self.assertIn("-2.01", result.detail)
        self.assertIn("visual regression, needs owner review", result.detail)


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


if __name__ == "__main__":
    unittest.main()
