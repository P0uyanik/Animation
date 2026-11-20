"""T-160 check: a hair spec without groom/5 keys builds the same geometry through groom/5 as through groom/4.

    blender -b --factory-startup -P passthrough_hash.py -- <master.blend> <spec.json> <out.json>

The hair of the spec is built twice on the head of the built master (hair only, no fibres): once with the spec's own
pin (groom/4) and once with generators.groom = groom/5. Writes the SHA-256 of every hair object's vertex coordinates
(float32 bytes) and faces for both builds and whether they are identical."""
import hashlib
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import body_helpers as BH  # noqa: E402
import versions as V  # noqa: E402

blend, spec_path, out = sys.argv[sys.argv.index("--") + 1:][:3]
spec = json.load(open(spec_path))


def build(pin):
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
    objs, rep = V.load("groom", pin).build(head.users_collection[0], head, frame, dict(spec["hair"], generator=pin),
                                           material, BH.face_y, None)
    hashes = {}
    for o in objs:
        co = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
        o.data.vertices.foreach_get("co", co)
        h = hashlib.sha256(co.tobytes())
        h.update(repr([tuple(p.vertices) for p in o.data.polygons]).encode())
        hashes[o.name] = h.hexdigest()
    return rep["generator"], hashes


g4, h4 = build(spec["generators"]["groom"])
g5, h5 = build("groom/5")
res = {"spec": os.path.basename(spec_path), "builds": [g4, g5], "objects": len(h4),
       "identical": h4 == h5, "differing": sorted(k for k in set(h4) | set(h5) if h4.get(k) != h5.get(k)),
       "sha256_of_all": hashlib.sha256(json.dumps(h4, sort_keys=True).encode()).hexdigest()}
json.dump(res, open(out, "w"), indent=1)
print("PASSTHROUGH", json.dumps(res))
