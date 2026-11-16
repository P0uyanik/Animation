"""Shared spec-driven garment generator (``garment/1``)."""

from .generator import build, bind_to_body, validate

__all__ = ["build", "bind_to_body", "validate"]
