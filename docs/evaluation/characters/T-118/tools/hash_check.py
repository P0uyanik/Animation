"""T-118 default-build check: the hair of a current spec built by its pinned generator (groom/3) and by groom/4.

    blender -b --factory-startup -P hash_check.py -- <master.blend> <spec.json> <out.json>

Builds the spec's hair twice on the head of the built master (no fibres), once with the pinned generator and once
with groom_r5 (each seeded as build_character.py seeds a build), and compares a SHA-256 over every hair object's name, vertex coordinates and faces (each
face as its sorted vertex indices: the winding that Blender's recalc_face_normals picks for felt shells is not
repeatable between two builds in one session, also for groom/3 alone). Equal hashes mean
a spec without groom/4 features builds the same geometry through groom/4 (groom/4 lowers it to itself). Also records
that the files of the released generators are byte-identical to the input commit (git diff)."""
import hashlib
import json
import os
import struct
import subprocess
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
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
mat = bpy.data.materials.new("hash_check")


def drop():
    for o in list(bpy.data.objects):
        if o.name.startswith("hair_"):
            bpy.data.objects.remove(o, do_unlink=True)


def digest(module):
    drop()
    DETERMINISM.configure_blender(DETERMINISM.DEFAULT_SEED)  # as build_character.py before every build
    objs, rep = module.build(C, head, frame, spec["hair"], lambda slot: mat, BH.face_y, None)
    h = hashlib.sha256()
    n = 0
    for o in sorted(objs, key=lambda o: o.name):
        h.update(o.name.encode())
        for v in o.data.vertices:
            h.update(struct.pack("<3f", *v.co))
        for p in o.data.polygons:
            h.update(struct.pack(f"<{len(p.vertices)}I", *sorted(p.vertices)))  # winding: see the docstring
        n += len(o.data.vertices)
    return h.hexdigest(), n, rep["generator"]


pin = spec["generators"]["groom"]
a = digest(V.load("groom", pin))
b = digest(groom_r5)
files = ["pipeline/charsys/groom.py", "pipeline/charsys/groom_hybrid.py", "pipeline/charsys/groom_r4.py",
         "pipeline/charsys/groom_felt.py", "pipeline/charsys/hair.py", "pipeline/charsys/build_character.py"]
diff = subprocess.run(["git", "-C", ROOT, "diff", "--stat", "5a90975", "--"] + files, capture_output=True, text=True)
res = {"spec": os.path.relpath(spec_path, ROOT), "pinned": pin, "pinned_sha256": a[0], "groom4_sha256": b[0],
       "vertices": a[1], "generators": [a[2], b[2]], "identical": a[0] == b[0] and a[1] == b[1],
       "released_files_unchanged_vs_5a90975": diff.returncode == 0 and not diff.stdout.strip()}
json.dump(res, open(out, "w"), indent=1)
print("HASH", json.dumps(res))
