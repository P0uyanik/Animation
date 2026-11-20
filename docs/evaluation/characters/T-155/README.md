# T-155: boy 2.3.0, girl 0.14.0, third character 0.1.0

Status (2026-11-20): boy 2.3.0 and girl 0.14.0 are **current** (owner decision `docs/process/OWNER_DECISIONS.md`
2026-11-20 ~08:20Z item 1, approved directly in the implementer session; `tools/version_switch.py --approve-published`).
The third character `girl_white_hair_blue_dress` 0.1.0 is **published, no current pointer**.

The sheets were rendered before the switch, so their column labels still say "2.2.0 / 0.13.0 (current)" and
"2.3.0 / 0.14.0 candidate". Read them as previous current | new current.

## What each version is

| Character | Version | Content |
|---|---|---|
| boy_yellow_hoodie | 2.3.0 | 2.2.0 spec + T-118 hair r5 + T-119 + T-121 hands r2 (T-132 content) + T-137 F2 face incl. face override |
| girl_auburn_bun_glasses | 0.14.0 | 0.13.0 spec + the same T-118/T-119/T-121 layers + T-137 F1a eyes |
| girl_white_hair_blue_dress | 0.1.0 | T-126a spec + T-126 body/face, hands r2, hair, dress, T-126d materials + T-137 F1b eyes and fringe |

Specs are composed by `make_specs.py` (`spec.deep_merge`, lists replaced whole) into
`assets/characters/<id>/spec/candidates/T-155/`. Boy and girl also have byte-identical version specs in
`assets/characters/<id>/spec/` (their hashes match the manifests' `spec_sha256`).

**T-133 proposal not applied to the third character.** `third_measure.py` measured both builds against
`references/measurements.json` (`third_t133_decision.json`). A (F1b) had a summed fraction error of 0.0448 and
B (F1b + T-133) 0.0445. That is a tie, not a measurable improvement, so 0.1.0 = A.

## Evidence (per character folder `boy/`, `girl/`, `third/`)

- `strict_sheet.jpg`: reference | previous (boy 2.2.0, girl 0.13.0, third: unpublished T-126 first build) | new | AI target
- `preview.jpg`: the recipe preview
- `crops_100.jpg`: 100% crops (hair, hands, collar, boots and more), made with `crops.py` and `compose_crops.py`
- `eyes_100.jpg`: eye crops at 100% (T-137 `face_sheets.py eyes`)
- `expressions.jpg`: expression sheet (T-137 `face_sheets.py expr`)
- boy and girl: `sheet.json` and `recipe.resolved.json` (recipes `*_vs_*.recipe.json`)
- `fidelity/<id>/`: fidelity reports used for the rebaseline. Boy went from 67.25 to 69.54. Girl went from 64.13
  to 63.09, within the 2.0 allowed drop. The boy was scored on a deterministic rebuild with the compare variant,
  which the store does not keep.

## Checks run

- Pass: `check_assets`, `check_cast`, `test_guard_allowlist`, `test_hair_r5`, `test_hands_r2`, `test_face_r5`
  and `test_gate_tools`. The plain-Python checks of `version_switch` pass apart from `test_store`.
- `test_store` fails the same way before and after the switch: it needs a `renders/charsys/ref_1.0.0` build that
  does not exist in this container.
- Not run here: the Blender tests that `version_switch` lists (determinism, face_v*, garments_*). They are left to
  the gate.
