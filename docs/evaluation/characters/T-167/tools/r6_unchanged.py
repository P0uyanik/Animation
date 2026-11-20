"""T-167 check: the T-160 round 6 hair builds the same geometry through groom_r6.py after the "clump" key was added.

    blender -b --factory-startup -P r6_unchanged.py -- <master.blend> <spec.json> <r6 override.json> <old groom_r6.py> <out.json>

The hair of spec + override is built twice on the head of the built master (hair only, no fibres): with the given
old groom_r6.py (git show 2dccd74:pipeline/charsys/groom_r6.py) and with the module in the tree. Writes the SHA-256 of
every hair object's vertex coordinates (float32 bytes) and faces for both builds and whether they are identical."""
import hashlib
import importlib.util
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import body_helpers as BH  # noqa: E402
import groom_r6 as NEW  # noqa: E402

blend, spec_path, ov_path, old_path, out = sys.argv[sys.argv.index("--") + 1:][:5]
spec = json.load(open(spec_path))
hair = dict(spec["hair"], **json.load(open(ov_path))["override"]["hair"])
sp = importlib.util.spec_from_file_location("groom_r6_old", old_path)
OLD = importlib.util.module_from_spec(sp)
sp.loader.exec_module(OLD)


def build(mod):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    for o in list(bpy.data.objects):
        if o.name.startswith("hair_"):
            bpy.data.objects.remove(o, do_unlink=True)
    head = bpy.data.objects["body_skin"]
    H = float(spec["body"]["height_m"])
    hp = spec["body"]["params"]["head"]
    frame = {"centre": (0, hp["forward"] * H, hp["centre_z"] * H),
             "radii": (hp["half_width"] * H, hp["half_depth"] * H, hp["half_height"] * H)}
    mats = {}

    def material(slot):
        return mats.setdefault(slot, bpy.data.materials.new("m_" + slot))
    objs, rep = mod.build(head.users_collection[0], head, frame, hair, material, BH.face_y, None)
    hashes = {}
    for o in objs:
        co = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
        o.data.vertices.foreach_get("co", co)
        h = hashlib.sha256(co.tobytes())
        h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
        hashes[o.name] = h.hexdigest()
    return hashes


h_old, h_new = build(OLD), build(NEW)
res = {"spec": os.path.basename(spec_path), "override": os.path.basename(ov_path), "objects": len(h_old),
       "identical": h_old == h_new,
       "differing": sorted(k for k in set(h_old) | set(h_new) if h_old.get(k) != h_new.get(k)),
       "sha256_of_all": hashlib.sha256(json.dumps(h_new, sort_keys=True).encode()).hexdigest()}
json.dump(res, open(out, "w"), indent=1)
print("R6UNCHANGED", json.dumps(res))
