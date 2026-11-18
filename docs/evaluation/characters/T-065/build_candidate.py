"""T-065 candidate build: runs pipeline/charsys/build_character.py with face_generic/2 available.

    blender -b --factory-startup -P docs/evaluation/characters/T-065/build_candidate.py -- <build_character args>

face_generic/2 is implemented in pipeline/charsys/face_generic.py (GENERATOR_VERSIONS declares it) but its registry
line in pipeline/charsys/versions.py is outside this task's write-set, so this driver registers it in-process
(exactly the lines the Supervisor appends: _r("face", "face_generic", 2, "face_generic") and
_r("body", "body_generic", 2, "body_generic"), plus "body_generic/2": main_generic in build_character.py's build-path
table) and then builds."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
sys.path.insert(0, CHARSYS)
import versions as V  # noqa: E402

try:
    V.REGISTRY.entry("face", "face_generic/2")
except V.VersionError:
    V.REGISTRY.register("face", "face_generic", 2, "face_generic", note="T-065 (registered by the candidate driver)")
try:
    V.REGISTRY.entry("body", "body_generic/2")
except V.VersionError:
    V.REGISTRY.register("body", "body_generic", 2, "body_generic", note="T-065 head fitted to reference outlines")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sys.argv = [os.path.join(CHARSYS, "build_character.py"), "--"] + argv
# build_character.py's per-version build-path table gets body_generic/2 -> the generic path (the line the Supervisor
# adds there; build_character.py is outside this task's write-set)
src = open(os.path.join(CHARSYS, "build_character.py")).read()
old = 'paths = {"body_generic/1": main_generic,'
assert old in src
src = src.replace(old, 'paths = {"body_generic/1": main_generic, "body_generic/2": main_generic,')
code = compile(src, os.path.join(CHARSYS, "build_character.py"), "exec")
exec(code, {"__name__": "__main__", "__file__": os.path.join(CHARSYS, "build_character.py")})
