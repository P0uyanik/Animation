#!/usr/bin/env python3
"""Implement Blender's background ``-P script -- args`` form with ``bpy``.

This is a CI adapter for the checksum-pinned bpy wheel. Local production runs
should pass the real Blender executable to ``tools/check_all.py --blender``.
"""

from __future__ import annotations

import runpy
import sys

import bpy  # type: ignore


def main() -> int:
    if "--version" in sys.argv:
        print(f"Blender {bpy.app.version_string} (bpy module)")
        return 0
    try:
        index = sys.argv.index("-P")
        script = sys.argv[index + 1]
    except (ValueError, IndexError):
        print("supported form: -b --factory-startup -P <script> -- <args>", file=sys.stderr)
        return 2
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
