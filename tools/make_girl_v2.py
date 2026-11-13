"""Builds girl_white_hair.character.json (iteration 2) from the frozen milestone-01 asset.

Run from the repository root:  python3 tools/make_girl_v2.py
Every change is listed here so the look iteration is reproducible and reviewable.
"""
import copy, json, math

SRC = "content/characters/girl_white_hair_m01.character.json"
DST = "content/characters/girl_white_hair.character.json"
c = json.load(open(SRC))
c["notes"] = "Iteration 2: lids/blink, brows, mouth expressions, strand hair relief, bang tufts, finer locks, knit geometry, collar, soles, larger head."
c["skinning"] = "dualQuaternion"

def part(name):
    return next(p for p in c["parts"] if p["name"] == name)

def head_z(x, y, lift=0.0):
    """Front surface of the head ellipsoid (pre-scale coordinates) + lift."""
    v = 1 - (x / 0.165) ** 2 - ((y - 0.82) / 0.152) ** 2
    return 0.15 * math.sqrt(max(v, 0.0)) + lift

# --- skeleton: brows (pivot at head centre so a rotation slides them over the forehead) and upper lids
c["skeleton"] += [
    {"name": "brow.L", "parent": "head", "head": [0.0, 0.82, 0.0], "mirror": True},
    {"name": "lid.L", "parent": "head", "head": [0.058, 0.79, 0.112], "mirror": True},
]

# --- face
skin = part("skin")
skin["skinSmoothing"] = 2
for p in skin["prims"]:
    if p["name"] == "socket.L":
        p["center"] = [0.058, 0.786, 0.112]
    if p["name"] == "mouth.L":
        p.update(a=[0.025, 0.740, 0.1368], b=[0.0, 0.732, 0.1358], r=0.0046, blend=0.004)  # surface z measured ~0.138-0.139
c["parts"].append({"name": "lids", "material": "skin", "voxelSize": 0.0011, "prims": [
    {"name": "lid.L", "type": "ellipsoid", "bone": "lid.L", "center": [0.058, 0.79, 0.112], "radii": [0.0392, 0.0392, 0.0392], "mirror": True},
    {"name": "lidInner.L", "type": "ellipsoid", "bone": "lid.L", "center": [0.058, 0.79, 0.112], "radii": [0.0369, 0.0369, 0.0369], "blend": 0.0008, "subtract": True, "mirror": True},
    {"name": "lidCut.L", "type": "roundBox", "bone": "lid.L", "center": [0.058, 0.79 + 0.019 - 0.03, 0.112], "halfSize": [0.05, 0.03, 0.05], "rounding": 0.004, "blend": 0.002, "subtract": True, "mirror": True},
]})
c["parts"].append({"name": "brows", "material": "brow_felt", "voxelSize": 0.0012, "prims": [
    {"name": "brow.L", "type": "roundCone", "bone": "brow.L",
     "a": [0.024, 0.823, head_z(0.024, 0.823, 0.003)], "b": [0.076, 0.828, head_z(0.076, 0.828, 0.003)],
     "r1": 0.0058, "r2": 0.0038, "mirror": True},
]})
c["materials"].append({"name": "brow_felt", "type": "plush", "baseColor": [0.40, 0.33, 0.27], "sheen": 0.5})
blush = next(m for m in c["materials"] if m["name"] == "skin")["texture"]
blush["spots"].append([0.0, 0.734, 0.13, 0.016])  # lips
c["expressions"] = [
    {"name": "smile", "part": "skin", "set": [
        {"prim": "mouth.L", "a": [0.029, 0.745, 0.1372], "b": [0.0, 0.7315, 0.1356], "r": 0.0047},
        {"prim": "cheek.L", "center": [0.074, 0.772, 0.075]}]},
    {"name": "mouthOpen", "part": "skin", "add": [
        {"name": "mouthCavity", "type": "ellipsoid", "center": [0.0, 0.729, 0.125], "radii": [0.019, 0.016, 0.016], "blend": 0.006, "subtract": True}]},
]

# --- hands: separate finer part with palm, four fingers and a thumb (were mitten blobs)
skin["prims"] = [p for p in skin["prims"] if p["name"] not in ("wrist.L", "hand.L", "thumb.L")]
fingers = []
for k, z in enumerate([0.006, 0.0165, 0.027, 0.0375]):
    length = [0.020, 0.023, 0.022, 0.018][k]
    fingers.append({"name": f"finger{k}.L", "type": "capsule", "bone": "hand.L", "a": [0.159, 0.398, z],
                    "b": [0.153, 0.398 - length, z + 0.004], "r": 0.0056, "blend": 0.003, "mirror": True})
c["parts"].append({"name": "hands", "material": "skin", "voxelSize": 0.0011, "skinFalloff": 0.006, "skinSmoothing": 1, "prims": [
    {"name": "wrist.L", "type": "capsule", "bone": "hand.L", "a": [0.152, 0.445, 0.016], "b": [0.157, 0.42, 0.019], "r": 0.016, "mirror": True},
    {"name": "palm.L", "type": "ellipsoid", "bone": "hand.L", "center": [0.159, 0.41, 0.021], "radii": [0.017, 0.022, 0.024], "blend": 0.008, "mirror": True},
    {"name": "thumb.L", "type": "capsule", "bone": "hand.L", "a": [0.152, 0.418, 0.04], "b": [0.146, 0.397, 0.049], "r": 0.0065, "blend": 0.005, "mirror": True},
] + fingers})

# --- hair: strands relief + separate bang tufts that are not cut by the face cut
cap = part("hairCap")
cap.update(pattern="strands", patternAmplitude=0.0042, patternScale=34, patternCenter=[0, 0.99, -0.01], noiseAmplitude=0.0055, noiseScale=11)
for p in cap["prims"]:
    if p["name"] == "faceCut":
        p["center"] = [0, 0.75, 0.12]
        p["radii"] = [0.175, 0.13, 0.12]
tufts = []
for i, x in enumerate([-0.115 + 0.023 * k for k in range(11)]):
    tip_y = 0.853 + 0.006 * math.sin(i * 2.3) - 0.008 * (abs(x) / 0.115) ** 2
    tip_x = x * 1.08
    tufts.append({"name": f"tuft{i}", "type": "roundCone", "bone": "head",
                  "a": [x * 0.85, 0.955, head_z(x * 0.85, 0.955, 0.006) - 0.012], "b": [tip_x, tip_y, head_z(tip_x, tip_y, 0.008)],
                  "r1": 0.03, "r2": 0.009, "blend": 0.026})
c["parts"].append({"name": "bangs", "material": "wool_cap", "voxelSize": 0.0022, "noiseAmplitude": 0.0012, "noiseScale": 40,
                   "pattern": "strands", "patternAmplitude": 0.002, "patternScale": 60, "patternCenter": [0, 0.99, -0.01],
                   "prims": tufts})
for f in c["fuzz"]:
    if f["part"] == "hairCap":
        f.update(density=300, radius=2.2e-5, length=0.0075, strayFraction=0.07)
c["fuzz"].append({"part": "bangs", "material": "wool_fiber", "density": 260, "length": 0.006, "radius": 2.2e-5, "tilt": 0.5,
                  "curl": 0.5, "comb": 0.9, "combOrigin": [0, 0.99, 0], "segments": 4, "seed": 17, "strayFraction": 0.06, "strayLength": 2.5})
c["fuzz"].append({"part": "brows", "material": "boots_fiber", "density": 120, "length": 0.0015, "radius": 1.5e-5, "tilt": 0.7,
                  "curl": 0.3, "segments": 2, "seed": 18})
lock = c["locks"][0]
lock.update(count=56, fibersPerLock=520, fiberRadius=3.5e-5, frizz=0.0012, lockRadius=0.0165, twist=6, coreRatio=0.78)
lock["coreMaterial"] = "wool_lock_core"
c["materials"].append({"name": "wool_lock_core", "type": "plush", "baseColor": [0.80, 0.78, 0.74], "sheen": 0.7, "sheenRoughness": 0.5,
                       "texture": {"type": "noise", "color2": [0.68, 0.66, 0.62], "scale": 90, "amount": 0.35}})

# --- clothing: knit geometry, collar part, soles, finer tights
dress = part("dress")
dress.update(voxelSize=0.0014, skinSmoothing=3, pattern="knit", patternAmplitude=0.0011, patternScale=170, patternCenter=[0, 0, 0])
dress["prims"] = [p for p in dress["prims"] if p["name"] != "collar"]
next(m for m in c["materials"] if m["name"] == "dress_knit")["texture"]["amount"] = 0.12
c["parts"].append({"name": "collar", "material": "dress_knit", "voxelSize": 0.0012, "skinFalloff": 0.02, "prims": [
    {"name": "collarRing", "type": "ellipsoid", "bone": "chest", "center": [0, 0.651, 0.008], "radii": [0.074, 0.011, 0.066]},
    {"name": "collarFlap.L", "type": "ellipsoid", "bone": "chest", "center": [0.036, 0.647, 0.062], "radii": [0.042, 0.009, 0.03], "rotationDeg": [8, -25, -6], "blend": 0.008, "mirror": True},
    {"name": "neckHole", "type": "capsule", "bone": "chest", "a": [0, 0.62, 0.0], "b": [0, 0.70, 0.0], "r": 0.04, "blend": 0.004, "subtract": True},
]})
part("tights").update(skinSmoothing=2, pattern="knit", patternAmplitude=0.0005, patternScale=260, voxelSize=0.0018)
c["parts"].append({"name": "soles", "material": "sole", "voxelSize": 0.0025, "prims": [
    {"name": "sole.L", "type": "roundBox", "bone": "foot.L", "center": [0.058, 0.007, 0.024], "halfSize": [0.043, 0.008, 0.069], "rounding": 0.006, "mirror": True}]})
c["materials"].append({"name": "sole", "type": "standard", "baseColor": [0.12, 0.07, 0.04], "roughness": 0.7})
for f in c["fuzz"]:
    if f["part"] == "boots":
        f.update(density=220, length=0.006)

# --- proportions: head group 6% larger around the neck pivot
HEAD_BONES = {"head", "eye.L", "eye.R", "brow.L", "brow.R", "lid.L", "lid.R"}
PIVOT, S = [0.0, 0.69, 0.0], 1.06
def sp(v):
    return [PIVOT[i] + (v[i] - PIVOT[i]) * S for i in range(3)]
for b in c["skeleton"]:
    if b["name"] in HEAD_BONES:
        b["head"] = sp(b["head"])
head_parts = {"hairCap", "buns", "bow", "eyes", "lids", "brows", "bangs"}
for p in c["parts"]:
    for q in p["prims"]:
        if p["name"] in head_parts or q.get("bone") in HEAD_BONES:
            for k in ("center", "a", "b"):
                if k in q: q[k] = sp(q[k])
            for k in ("radii", "halfSize"):
                if k in q: q[k] = [v * S for v in q[k]]
            for k in ("r", "r1", "r2", "rounding"):
                if k in q: q[k] *= S
    if "patternCenter" in p and p["name"] in head_parts:
        p["patternCenter"] = sp(p["patternCenter"])
for e in c["expressions"]:
    for q in e.get("set", []) + e.get("add", []):
        for k in ("center", "a", "b"):
            if k in q: q[k] = sp(q[k])
        for k in ("radii",):
            if k in q: q[k] = [v * S for v in q[k]]
        for k in ("r",):
            if k in q: q[k] *= S
for m in c["materials"]:
    for s in m.get("texture", {}).get("spots", []):
        s[:3] = sp(s[:3]); s[3] *= S
for f in c["fuzz"]:
    if "combOrigin" in f: f["combOrigin"] = sp(f["combOrigin"])
lock["headCenter"] = sp(lock["headCenter"]); lock["headRadii"] = [v * S for v in lock["headRadii"]]
lock["lengthMin"] *= S; lock["lengthMax"] *= S
json.dump(c, open(DST, "w"), indent=1)
print("wrote", DST)
