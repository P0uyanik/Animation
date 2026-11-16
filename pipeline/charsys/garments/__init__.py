"""Shared spec-driven garment generator (``garment/1``)."""

from .generator import bind_to_body, build, masked_items, set_active_items, validate, visible_face_flags

__all__ = ["build", "bind_to_body", "masked_items", "set_active_items", "validate", "visible_face_flags"]
