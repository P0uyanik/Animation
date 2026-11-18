"""T-047 evidence: the export/6 collision block (pipeline/charsys/export_engine.py collision_block) computed from an
existing engine package's own arrays, so it can be compared with the engine's derivation of the same package
(measure_t047 --body) without re-exporting a master. Needs the bpy module (export_engine imports bpy / mathutils):

    <python with bpy 5.3> -I docs/evaluation/animation/T-047/collision_block_from_package.py <package dir> [out.json]
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import export_engine as EE  # noqa: E402


def arrays(pkg):
    man = json.load(open(os.path.join(pkg, "character.json")))
    blob = open(os.path.join(pkg, "geometry.bin"), "rb").read()

    def arr(a, dtype, comp):
        return np.frombuffer(blob, dtype=dtype, count=a["count"], offset=a["offset"]).reshape(-1, comp)
    meshes = []
    for m in man["meshes"]:
        meshes.append((arr(m["positions"], np.float32, 3), arr(m["joints"], np.uint16, 4), arr(m["weights"], np.float32, 4)))
    return man, meshes


def main():
    pkg = sys.argv[1]
    man, meshes = arrays(pkg)
    block = EE.collision_block(man["skeleton"], meshes)
    text = json.dumps(block, indent=1)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
