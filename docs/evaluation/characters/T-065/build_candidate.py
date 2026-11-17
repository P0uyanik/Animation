"""T-065 candidate build: runs pipeline/charsys/build_character.py with face_generic/2 available.

    blender -b --factory-startup -P docs/evaluation/characters/T-065/build_candidate.py -- <build_character args>

face_generic/2 is implemented in pipeline/charsys/face_generic.py (GENERATOR_VERSIONS declares it) but its registry
line in pipeline/charsys/versions.py is outside this task's write-set, so this driver registers it in-process
(exactly the line the Supervisor appends: _r("face", "face_generic", 2, "face_generic")) and then builds."""
import os
import runpy
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
sys.path.insert(0, CHARSYS)
import versions as V  # noqa: E402

try:
    V.REGISTRY.entry("face", "face_generic/2")
except V.VersionError:
    V.REGISTRY.register("face", "face_generic", 2, "face_generic", note="T-065 (registered by the candidate driver)")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sys.argv = [os.path.join(CHARSYS, "build_character.py"), "--"] + argv
runpy.run_path(os.path.join(CHARSYS, "build_character.py"), run_name="__main__")
