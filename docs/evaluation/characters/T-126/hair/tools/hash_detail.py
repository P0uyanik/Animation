"""T-126b: per-object detail behind the T-118 default-build hash check (read-only on every input).

    blender -b --factory-startup -P hash_detail.py -- <master.blend> <spec.json> <out.json>

Builds the spec's hair three times on the head of the built master (no fibres, each build seeded as
build_character.py seeds it): A with the pinned generator, B with groom_r5, C with the pinned generator again.
For every hair object it compares vertex coordinates (largest difference in metres) and faces (as sorted vertex
indices) of A-B and of A-C. A-C is the pinned generator against itself: what differs there is not caused by groom/4."""
import hashlib
import json
import os
import struct
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import body_helpers as BH  # noqa: E402
import determinism as DETERMINISM  # noqa: E402
import groom_r5  # noqa: E402
import versions as V  # noqa: E402

blend, spec_path, out = sys.argv[sys.argv.index("--") + 1:][:3]
spec = json.load(open(spec_path))
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
head = bpy.data.objects["body_skin"]
C = head.users_collection[0]
H = float(spec["body"]["height_m"])
hp = spec["body"]["params"]["head"]
frame = {"centre": (0, hp["forward"] * H, hp["centre_z"] * H),
         "radii": (hp["half_width"] * H, hp["half_depth"] * H, hp["half_height"] * H)}
mat = bpy.data.materials.new("hash_detail")


def snapshot(module):
    for o in list(bpy.data.objects):
        if o.name.startswith("hair_"):
            bpy.data.objects.remove(o, do_unlink=True)
    DETERMINISM.configure_blender(DETERMINISM.DEFAULT_SEED)
    objs, _ = module.build(C, head, frame, spec["hair"], lambda slot: mat, BH.face_y, None)
    snap = {}
    for o in objs:
        co = [tuple(v.co) for v in o.data.vertices]
        h = hashlib.sha256()
        for p in o.data.polygons:
            h.update(struct.pack(f"<{len(p.vertices)}I", *sorted(p.vertices)))
        snap[o.name] = (co, h.hexdigest())
    return snap


def compare(a, b):
    rows = {}
    for name in sorted(set(a) | set(b)):
        if name not in a or name not in b or len(a[name][0]) != len(b[name][0]):
            rows[name] = {"vertices": "count differs"}
            continue
        d = max((abs(x - y) for p, q in zip(a[name][0], b[name][0]) for x, y in zip(p, q)), default=0.0)
        if d > 0 or a[name][1] != b[name][1]:
            rows[name] = {"max_coordinate_difference_m": d, "faces_equal": a[name][1] == b[name][1]}
    return rows


pin = spec["generators"]["groom"]
A = snapshot(V.load("groom", pin))
B = snapshot(groom_r5)
Cc = snapshot(V.load("groom", pin))
res = {"spec": os.path.relpath(spec_path, ROOT), "pinned": pin, "objects": len(A),
       "environment": {k: os.environ.get(k) for k in DETERMINISM.ENVIRONMENT},
       "pinned_vs_groom4_differing_objects": compare(A, B),
       "pinned_vs_pinned_again_differing_objects": compare(A, Cc)}
json.dump(res, open(out, "w"), indent=1)
print("DETAIL", json.dumps(res))
