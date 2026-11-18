"""Shared spec-driven garment generator ``garment/2`` (T-093): garment outlines and accessories.

``garment/2`` reuses ``garment/1`` (``pipeline/charsys/garments``) by import and never changes it: every item is built
by the ``garment/1`` code, then the new, opt-in fields of ``garment/2`` add or reshape pieces of that item. A
``garment/2`` clothing block without any new field builds the same geometry as ``garment/1`` (only the generator tag
and the report differ). See README.md in this folder for the fields.
"""

from garments.generator import masked_items, set_active_items, visible_face_flags

from .core import GENERATOR, bind_to_body, build, v1_view, validate

GENERATOR_VERSIONS = ("garment/2",)  # versions implemented here (versions.py; released = immutable)

__all__ = ["GENERATOR", "build", "bind_to_body", "masked_items", "set_active_items", "v1_view", "validate",
           "visible_face_flags"]
