"""Policy helpers for the optional T-023 character-fidelity CI check.

This module deliberately contains no fidelity metric calculations.  It only
selects affected characters and compares a measured score with guarded data.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path


MAX_SCORE_DROP = 2.0


OWNER_REVIEW_FLAG = "needs owner review"


@dataclasses.dataclass(frozen=True)
class ScoreDelta:
    score: float
    baseline: float
    delta: float
    ok: bool
    detail: str
    needs_owner_review: bool = False


def compare_score(score: float, baseline: float, max_drop: float = MAX_SCORE_DROP) -> ScoreDelta:
    """Compare scores. T-087 rule change (owner-approved round 2 plan A3): the score is a regression signal, not a
    blocker. A drop of more than ``max_drop`` points no longer fails; it passes with a warning and the flag
    ``needs_owner_review`` (the owner judges the strict visual sheet). Exactly ``max_drop`` down is not flagged."""
    score = float(score)
    baseline = float(baseline)
    delta = score - baseline
    flagged = delta < -float(max_drop)
    detail = f"score {score:.2f} ({delta:+.2f} vs baseline {baseline:.2f})"
    if flagged:
        detail += (f"; WARNING: drop above {float(max_drop):.2f} points, visual regression, "
                   f"{OWNER_REVIEW_FLAG} (PASS, flagged)")
    return ScoreDelta(score, baseline, delta, True, detail, flagged)


def summary_line(character_id: str, result: ScoreDelta) -> str:
    """One gate summary line per character; flagged drops start with the owner-review marker."""
    prefix = f"NEEDS OWNER REVIEW: {character_id} fidelity" if result.needs_owner_review else f"{character_id} fidelity"
    return f"{prefix} {result.detail}"


def _shared_generator_change(path: str) -> bool:
    path = path.replace("\\", "/")
    prefixes = (
        "pipeline/charsys/garments/",
        "pipeline/charsys/materials/",
    )
    files = {
        "pipeline/charsys/body_generic.py",
        "pipeline/charsys/body_v6.py",
        "pipeline/charsys/build_character.py",
        "pipeline/charsys/face.py",
        "pipeline/charsys/face_generic.py",
        "pipeline/charsys/geom.py",
        "pipeline/charsys/groom.py",
        "pipeline/charsys/hair.py",
        "pipeline/charsys/render_calibration.json",
        "pipeline/charsys/render_calibration.py",
    }
    return path in files or path.startswith(prefixes)


def affected_characters(changes: set[str], character_ids: set[str]) -> list[str]:
    """Return fidelity-enabled characters affected by specs, references, or generators."""
    normalized = {path.replace("\\", "/") for path in changes}
    if any(_shared_generator_change(path) for path in normalized):
        return sorted(character_ids)

    affected = set()
    for character_id in character_ids:
        root = f"assets/characters/{character_id}/"
        for path in normalized:
            if path.startswith(root + "references/") or path.startswith(root + "spec/"):
                affected.add(character_id)
                break
    return sorted(affected)


def repo_path(root: Path, value: str) -> Path:
    """Resolve and constrain a baseline input to the repository."""
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"baseline path escapes repository: {value}") from exc
    return candidate
