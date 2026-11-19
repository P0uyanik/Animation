"""Post-build felt-halo pass on a built character .blend (T-110, evaluation builds).

    blender -b --factory-startup -P pipeline/charsys/materials/apply_felt_halo.py -- --blend <in.blend> --out <out.blend>
        [--lod close|wide|off] [--report <report.json>]

Hair and garments get the shared halo inside the build (builder.add_fibres_geometry, presets/4 ids). The skin is
never routed through the surface-fibre path, so this pass adds the halo to every mesh whose material carries a
presets/4 halo and that has none yet (felt_halo.add_missing_halos). At merge the same call runs at the end of the
build; until then evaluation builds run this script on the built <id>_compare.blend. Without presets/4 materials the
file is saved unchanged (no halo objects).
"""
import argparse
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from materials import felt_halo  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lod", default="close", choices=("close", "wide", "off"))
    ap.add_argument("--report", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    made = felt_halo.add_missing_halos(list(bpy.context.scene.objects), a.lod)
    in_build = sorted(o.name for o in bpy.data.objects if o.get(felt_halo.HALO_OBJECT_PROP) and o not in made)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
    report = {"blend": os.path.basename(a.blend), "added": sorted(o.name for o in made), "halo_in_build": in_build,
              "added_sources": sorted(o[felt_halo.HALO_OBJECT_PROP] for o in made), "lod": a.lod}
    print("[apply_felt_halo]", json.dumps(report))
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1)


if __name__ == "__main__":
    main()
