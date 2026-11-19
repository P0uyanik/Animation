"""Shared spec-driven garment generator ``garment/3`` (T-119): garments round 3.

``garment/3`` reuses ``garment/2`` (``pipeline/charsys/garments_v2``, which reuses ``garment/1``) by import and never
changes either: every item is built by the ``garment/2`` code from the *garment/2 view* of the clothing block (the
block without the new fields), then the opt-in ``garment/3`` fields reshape that item's pieces or add new ones. A
``garment/3`` block without any new field builds the same geometry as ``garment/2`` (only the generator tag and the
report differ). See README.md in this folder for the fields.
"""

from garments.generator import masked_items, set_active_items, visible_face_flags

from .core import GENERATOR, bind_to_body, build, v2_view, validate

GENERATOR_VERSIONS = ("garment/3",)  # versions implemented here (versions.py; released = immutable)

__all__ = ["GENERATOR", "build", "bind_to_body", "masked_items", "set_active_items", "v2_view", "validate",
           "visible_face_flags"]
