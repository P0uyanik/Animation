"""Character construction kit (iteration 3).

Builds the three reference characters from the shared body/face rig of the frozen iteration-2 girl:
  A  girl_white_hair  (content/characters/girl_white_hair.character.json)
  B  girl_brown_glasses
  C  boy_dark_hair
Run from the repository root:  python3 tools/charkit.py
Everything is data in the character files; the Studio app edits the same data.
"""
import copy, json, math, random

S = 1.06                      # head-group scale applied in iteration 2
HEAD_C = (0.0, 0.8389, 0.0)   # head ellipsoid centre / radii (iteration 4: shorter lower face)
HEAD_R = (0.1749, 0.15, 0.159)
CAP_C = (0.0, 0.8469, -0.0127)
CAP_R = (0.1823, 0.1717, 0.176)
EYE_L = (0.072, 0.794, 0.0909)   # iteration 4: larger, wider-set eyes (reference eye width ~25% of face)
EYE_R = 0.065                     # large, deep-set eyeball: wide opening (~8 cm) but only ~1.2 cm protrusion
LID_R = 0.0685                    # eyelid shell radius
RIM_Y = 0.0342                    # height of the open lid rim above the eye centre

def v_add(a, b): return [a[i] + b[i] for i in range(3)]
def v_mul(a, s): return [a[i] * s for i in range(3)]
def v_norm(a):
    l = math.sqrt(sum(x * x for x in a)) or 1.0
    return [x / l for x in a]
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

def ell_z(c, r, x, y):
    """Front (+z) surface of an axis-aligned ellipsoid, or None."""
    v = 1 - ((x - c[0]) / r[0]) ** 2 - ((y - c[1]) / r[1]) ** 2
    return c[2] + r[2] * math.sqrt(v) if v > 0 else None

def on_ellipsoid(c, r, az, el, lift=0.0):
    """Point on an ellipsoid; az 0 = back (-z), 90 = +x, 180 = front; el = degrees above the centre."""
    a, e = math.radians(az), math.radians(el)
    d = [math.sin(a) * math.cos(e), math.sin(e), -math.cos(a) * math.cos(e)]
    p = [c[i] + r[i] * d[i] for i in range(3)]
    n = v_norm([d[i] / r[i] for i in range(3)])
    return v_add(p, v_mul(n, lift)), n

# ------------------------------------------------------------------ asset helpers
def _ell_sdf(p, c, r):
    q = [(p[i] - c[i]) / r[i] for i in range(3)]
    k0 = math.sqrt(sum(x * x for x in q))
    q2 = [(p[i] - c[i]) / (r[i] * r[i]) for i in range(3)]
    k1 = math.sqrt(sum(x * x for x in q2))
    return k0 * (k0 - 1) / k1 if k1 > 1e-12 else -min(r)

def _smin(a, b, k):
    h = max(k - abs(a - b), 0) / k
    return min(a, b) - h * h * k * 0.25

def face_z(c, x, y):
    """Front surface depth of the skin (ellipsoid primitives, smooth union) at (x, y) — measured, not guessed."""
    prims = []
    for p in get_part(c, "skin")["prims"]:
        if p.get("subtract") or p["type"] != "ellipsoid":
            continue
        prims.append(p)
        if p.get("mirror"):
            m = dict(p); m["center"] = [-p["center"][0], p["center"][1], p["center"][2]]; prims.append(m)
    def f(z):
        d = None
        for p in prims:
            di = _ell_sdf([x, y, z], p["center"], p["radii"])
            d = di if d is None else _smin(d, di, p.get("blend", 0.02))
        return d
    lo, hi = 0.0, 0.3
    for _ in range(50):
        mid = (lo + hi) / 2
        if f(mid) < 0: lo = mid
        else: hi = mid
    return lo

def upgrade_base(c):
    """Iteration 4 face and hands, applied to every character built from the shared base."""
    ex, ey, ez = EYE_L
    # Skull: shorter lower face (chin up 2 cm), fuller low cheeks, clearer nose.
    skin = get_part(c, "skin")
    for p in skin["prims"]:
        n = p["name"]
        if n == "head":
            p["center"], p["radii"] = list(HEAD_C), list(HEAD_R)
        elif n == "jaw":
            # Lower, fuller chin: the mouth sits on the front of the face, ~0.3 eye spacings above the chin (reference).
            p["center"] = [0.0, 0.752, 0.036]; p["radii"] = [0.118, 0.064, 0.11]
        elif n == "cheek.L":
            p["center"] = [0.088, 0.752, 0.078]; p["radii"] = [0.072, 0.06, 0.068]
        elif n == "nose":
            p["radii"] = [r * 0.95 for r in p["radii"]]
        elif n == "socket.L":
            p["center"] = [ex, ey - 0.003, ez]; p["radii"] = [EYE_R + 0.0015] * 3
    for b in c["skeleton"]:
        if b["name"] in ("eye.L", "lid.L"):
            b["head"] = [ex, ey, ez]
    nose = next(p for p in skin["prims"] if p["name"] == "nose")
    nose["center"] = [0.0, 0.771, face_z(c, 0.0, 0.771) - 0.007]  # mostly embedded: a small bump, as in the references
    get_part(c, "eyes")["prims"] = [{"name": "eye.L", "type": "ellipsoid", "bone": "eye.L", "center": [ex, ey, ez], "radii": [EYE_R] * 3, "mirror": True}]
    get_part(c, "lids")["prims"] = [
        {"name": "lid.L", "type": "ellipsoid", "bone": "lid.L", "center": [ex, ey, ez], "radii": [LID_R] * 3, "mirror": True},
        {"name": "lidInner.L", "type": "ellipsoid", "bone": "lid.L", "center": [ex, ey, ez], "radii": [EYE_R + 0.0012] * 3, "blend": 0.0008, "subtract": True, "mirror": True},
        {"name": "lidCut.L", "type": "roundBox", "bone": "lid.L", "center": [ex, ey + RIM_Y - 0.044, ez], "halfSize": [0.075, 0.044, 0.075], "rounding": 0.004, "blend": 0.002, "subtract": True, "mirror": True}]
    eye_tex = get_mat(c, "eye")["texture"]
    eye_tex["spots"] = [[ex, ey, ez, EYE_R], [-ex, ey, ez, EYE_R]]
    eye_tex["params"] = [11, 29, 0, 0]  # iris fills most of the opening, little white (reference)
    # Mouth and expressions placed on the measured skin surface.
    mz = lambda x, y, inset=0.0012: face_z(c, x, y) - inset
    mouth = next(p for p in skin["prims"] if p["name"] == "mouth.L")
    mouth.update(a=[0.027, 0.742, mz(0.027, 0.742)], b=[0.0, 0.736, mz(0.0, 0.736)], r=0.0046, blend=0.004)
    cheek = [0.088, 0.752, 0.078]
    c["expressions"] = [
        {"name": "smile", "part": "skin", "set": [
            {"prim": "mouth.L", "a": [0.031, 0.748, mz(0.031, 0.748)], "b": [0.0, 0.7345, mz(0.0, 0.7345)], "r": 0.0048},
            {"prim": "cheek.L", "center": [cheek[0], cheek[1] + 0.006, cheek[2]]}]},
        # Open mouth: a D-shaped opening under the smile line, revealing the mouth interior parts below.
        {"name": "mouthOpen", "part": "skin", "add": [
            {"name": "mouthCavity", "type": "ellipsoid", "center": [0.0, 0.7295, face_z(c, 0.0, 0.7295) - 0.012], "radii": [0.016, 0.0115, 0.02], "blend": 0.004, "subtract": True}]},
        # Wide open grin (character B's default): a broader opening.
        {"name": "grin", "part": "skin", "add": [
            {"name": "grinCavity", "type": "ellipsoid", "center": [0.0, 0.7285, face_z(c, 0.0, 0.7285) - 0.011], "radii": [0.026, 0.0135, 0.02], "blend": 0.004, "subtract": True}]},
        {"name": "frown", "part": "skin", "set": [
            {"prim": "mouth.L", "a": [0.028, 0.731, mz(0.028, 0.731)], "b": [0.0, 0.7375, mz(0.0, 0.7375)], "r": 0.0046},
            {"prim": "cheek.L", "center": [cheek[0], cheek[1] - 0.004, cheek[2]]}]},
    ]
    # Mouth interior, hidden inside the head until the mouth opens: dark cavity, upper teeth, tongue.
    # Each piece is placed against the face depth at its lowest point, so it stays hidden when the mouth is closed.
    mat(c, "mouth_dark", type="standard", baseColor=[0.22, 0.05, 0.05], roughness=0.6)
    mat(c, "teeth", type="standard", baseColor=[0.9, 0.87, 0.82], roughness=0.35, coat=0.3)
    mat(c, "tongue", baseColor=[0.72, 0.3, 0.3], sheen=0.3)
    part(c, "mouthInside", "mouth_dark", [{"name": "cavity", "type": "ellipsoid", "bone": "head",
         "center": [0.0, 0.729, face_z(c, 0.0, 0.717) - 0.01], "radii": [0.028, 0.012, 0.005]}], voxel=0.001)
    part(c, "teeth", "teeth", [{"name": "upper", "type": "roundBox", "bone": "head", "center": [0.0, 0.7368, face_z(c, 0.0, 0.7336) - 0.0105],
         "halfSize": [0.016, 0.0032, 0.0025], "rounding": 0.002}], voxel=0.0006)
    part(c, "tongue", "tongue", [{"name": "tongue", "type": "ellipsoid", "bone": "head", "center": [0.0, 0.7225, face_z(c, 0.0, 0.7175) - 0.0085],
         "radii": [0.015, 0.005, 0.0045]}], voxel=0.0008)
    # Iteration 4: subsurface scattering (random walk) softens the skin like the references' soft vinyl/clay.
    get_mat(c, "skin").update(subsurface=0.75, subsurfaceRadius=[0.0035, 0.0016, 0.001])
    blush = get_mat(c, "skin")["texture"]
    blush["spots"] = [[0.088, 0.748, face_z(c, 0.088, 0.748), 0.04], [-0.088, 0.748, face_z(c, 0.088, 0.748), 0.04],
                      [0.0, 0.738, face_z(c, 0.0, 0.738), 0.016]]
    brows = get_part(c, "brows")
    for p in brows["prims"]:
        p["a"] = [0.032, 0.852, face_z(c, 0.032, 0.852) + 0.003]
        p["b"] = [0.094, 0.858, face_z(c, 0.094, 0.858) + 0.003]
    # Hands: two-segment fingers and thumb with their own bones (articulated grasping).
    zs = [0.006, 0.0165, 0.027, 0.0375]
    lengths = [0.020, 0.023, 0.022, 0.018]
    names = {b["name"] for b in c["skeleton"]}
    if "f0a.L" not in names:
        c["skeleton"].append({"name": "thumbA.L", "parent": "hand.L", "head": [0.152, 0.418, 0.04], "mirror": True})
        c["skeleton"].append({"name": "thumbB.L", "parent": "thumbA.L", "head": [0.149, 0.4075, 0.0445], "mirror": True})
        for k, z in enumerate(zs):
            c["skeleton"].append({"name": f"f{k}a.L", "parent": "hand.L", "head": [0.159, 0.398, z], "mirror": True})
            c["skeleton"].append({"name": f"f{k}b.L", "parent": f"f{k}a.L", "head": [0.156, 0.398 - lengths[k] * 0.5, z + 0.002], "mirror": True})
    prims = [
        {"name": "wrist.L", "type": "capsule", "bone": "hand.L", "a": [0.152, 0.445, 0.016], "b": [0.157, 0.42, 0.019], "r": 0.016, "mirror": True},
        {"name": "palm.L", "type": "ellipsoid", "bone": "hand.L", "center": [0.159, 0.41, 0.021], "radii": [0.017, 0.022, 0.024], "blend": 0.008, "mirror": True},
        {"name": "thumbA.L", "type": "capsule", "bone": "thumbA.L", "a": [0.152, 0.418, 0.04], "b": [0.149, 0.4075, 0.0445], "r": 0.0066, "blend": 0.005, "mirror": True},
        {"name": "thumbB.L", "type": "capsule", "bone": "thumbB.L", "a": [0.149, 0.4075, 0.0445], "b": [0.146, 0.397, 0.049], "r": 0.006, "blend": 0.003, "mirror": True}]
    for k, z in enumerate(zs):
        a = [0.159, 0.398, z]; m = [0.156, 0.398 - lengths[k] * 0.5, z + 0.002]; t = [0.153, 0.398 - lengths[k], z + 0.004]
        prims.append({"name": f"f{k}a.L", "type": "capsule", "bone": f"f{k}a.L", "a": a, "b": m, "r": 0.0058, "blend": 0.003, "mirror": True})
        prims.append({"name": f"f{k}b.L", "type": "capsule", "bone": f"f{k}b.L", "a": m, "b": t, "r": 0.0052, "blend": 0.002, "mirror": True})
    get_part(c, "hands")["prims"] = prims
    return c

def load_base():
    return upgrade_base(json.load(open("content/characters/girl_white_hair_v2.character.json")))

def drop(c, parts=(), fuzz=(), locks=False):
    c["parts"] = [p for p in c["parts"] if p["name"] not in parts]
    c["fuzz"] = [f for f in c["fuzz"] if f["part"] not in parts and f["part"] not in fuzz]
    if locks:
        c["locks"] = []
    c.setdefault("lockGroups", [])

def mat(c, name, **kw):
    c["materials"] = [m for m in c["materials"] if m["name"] != name]
    m = {"name": name, "type": kw.pop("type", "plush")}
    m.update(kw)
    c["materials"].append(m)
    return name

def part(c, name, material, prims, voxel=0.003, **kw):
    c["parts"] = [p for p in c["parts"] if p["name"] != name]
    p = {"name": name, "material": material, "voxelSize": voxel, "prims": prims}
    p.update(kw)
    c["parts"].append(p)

def fuzz(c, part_name, material, density, length, radius=2.5e-5, **kw):
    f = {"part": part_name, "material": material, "density": density, "length": length, "radius": radius,
         "tilt": kw.pop("tilt", 0.55), "curl": kw.pop("curl", 0.4), "segments": kw.pop("segments", 3),
         "seed": kw.pop("seed", 40 + len(c["fuzz"]))}
    f.update(kw)
    c["fuzz"].append(f)

def lock(points, r0, r1, curl=0.0, turns=0.0, phase=0.0):
    return {"points": [list(map(float, p)) for p in points], "rootRadius": r0, "tipRadius": r1,
            "curlRadius": curl, "curlTurns": turns, "curlPhase": phase}

def group(c, name, material, core, locks, bone="head", mirror=False, **params):
    g = {"name": name, "bone": bone, "material": material, "coreMaterial": core, "locks": locks, "mirror": mirror}
    g.update(params)
    c["lockGroups"].append(g)

def prefix_materials(c, pre):
    """Character-specific material names so characters can share a scene."""
    names = {m["name"] for m in c["materials"]}
    ren = lambda n: pre + n if n in names and not n.startswith(pre) else n
    for m in c["materials"]: m["name"] = ren(m["name"])
    for p in c["parts"]: p["material"] = ren(p["material"])
    for f in c["fuzz"]: f["material"] = ren(f["material"])
    for l in c.get("locks", []):
        l["material"] = ren(l["material"]); l["coreMaterial"] = ren(l.get("coreMaterial", ""))
    for g in c["lockGroups"]:
        g["material"] = ren(g["material"]); g["coreMaterial"] = ren(g["coreMaterial"])

def get_mat(c, name): return next(m for m in c["materials"] if m["name"] == name)
def get_part(c, name): return next(p for p in c["parts"] if p["name"] == name)

# ------------------------------------------------------------------ shared face upgrades
def add_lashes(c, material, thickness=0.0016, flick=1.0):
    """Upper lash line on the eyelid rim (moves with the lid bone when blinking)."""
    lid_r, rim_y = LID_R * 0.995, RIM_Y
    rho = math.sqrt(lid_r ** 2 - rim_y ** 2) * 1.01
    ex, ey, ez = EYE_L
    line = [[ex + rho * math.sin(math.radians(t)), ey + rim_y + 0.0012 * math.cos(math.radians(t)), ez + rho * math.cos(math.radians(t))]
            for t in range(-68, 74, 12)]
    locks = [lock(line, thickness * 0.6, thickness, 0, 0)]
    for k, t in enumerate([48, 58, 68]):     # small flicks at the outer corner
        a = math.radians(t)
        root = [ex + rho * math.sin(a), ey + rim_y, ez + rho * math.cos(a)]
        out = v_norm([math.sin(a), 0.6, math.cos(a)])
        tip = v_add(root, v_mul(out, (0.006 + 0.002 * k) * flick))
        locks.append(lock([root, v_add(root, v_mul(out, 0.5 * (0.006 + 0.002 * k) * flick)), tip], thickness * 0.9, thickness * 0.25))
    group(c, "lashes.L", material, material, locks, bone="lid.L", mirror=True, samples=24, roundTip=True)

def bake_mouth(c, smile=0.0, frown=0.0, cavity=None, scale=1.0, closed=False):
    """Iteration 4: a character's resting mouth is part of the skin surface itself (clean mesh, real pocket that
    shows the teeth and tongue). Morphing a hole open crumples the skin, so instead an open-mouthed character gets
    a 'mouthClose' expression that fills the pocket (a convex change that projects cleanly)."""
    skin = get_part(c, "skin")
    exprs = {e["name"]: e for e in c["expressions"]}
    mouth = next(p for p in skin["prims"] if p["name"] == "mouth.L")
    cheek = next(p for p in skin["prims"] if p["name"] == "cheek.L")
    lerp = lambda a, b, t: [a[i] + (b[i] - a[i]) * t for i in range(3)]
    for name, w in (("smile", smile), ("frown", frown)):
        if w <= 0:
            continue
        tm = next(x for x in exprs[name]["set"] if x["prim"] == "mouth.L")
        tc = next(x for x in exprs[name]["set"] if x["prim"] == "cheek.L")
        mouth["a"], mouth["b"] = lerp(mouth["a"], tm["a"], w), lerp(mouth["b"], tm["b"], w)
        mouth["r"] = mouth["r"] + (tm["r"] - mouth["r"]) * w
        cheek["center"] = lerp(cheek["center"], tc["center"], w)
    if cavity:
        pocket = json.loads(json.dumps(dict(exprs[cavity]["add"][0], name="mouthPocket", bone="head")))
        pocket["radii"] = [pocket["radii"][0] * scale, pocket["radii"][1] * scale, pocket["radii"][2]]
        skin["prims"].append(pocket)
        # Surprise: the pocket grows into a rounder, taller opening (growing an existing pocket morphs cleanly).
        c["expressions"].append({"name": "surprise", "part": "skin", "set": [
            {"prim": "mouthPocket", "center": [0.0, pocket["center"][1] - 0.004, pocket["center"][2] + 0.001], "radii": [0.016, 0.019, 0.02]}]})
    if cavity and closed:
        c["expressions"].append({"name": "mouthClose", "part": "skin", "set": [
            {"prim": "mouthPocket", "center": [0.0, 0.8, 0.0], "radii": [1e-4, 1e-4, 1e-4]}]})
        c["defaultExpressions"] = {"mouthClose": 1.0}
        return
    if cavity:
        # The lip line follows the opening: centre on its top edge, corners just past its sides, slightly up.
        dz = face_z(c, 0.0, pocket["center"][1]) - pocket["center"][2]
        f = math.sqrt(max(0.0, 1 - (dz / pocket["radii"][2]) ** 2))
        hw, top = pocket["radii"][0] * f, pocket["center"][1] + pocket["radii"][1] * f
        ax, ay = hw + 0.0045, top + 0.0025
        mouth["a"] = [ax, ay, face_z(c, ax, ay) - 0.0012]
        mouth["b"] = [0.0, top - 0.0008, face_z(c, 0.0, top) - 0.0012]
        mouth["r"] = 0.0038
        c["expressions"].append({"name": "mouthClose", "part": "skin", "set": [
            {"prim": "mouthPocket", "center": [0.0, 0.8, 0.0], "radii": [1e-4, 1e-4, 1e-4]}]})
    c["defaultExpressions"] = {}

def rib_bands(c, garment, names, rib_scale=320, amplitude=0.0012):
    """Iteration 4: knitted rib bands (cuffs, hems) as their own parts with vertical ribs around the band's axis.
    Mirrored prims become one part per side so each cuff gets ribs around its own arm."""
    g = get_part(c, garment)
    fz = [f for f in c["fuzz"] if f["part"] == garment]
    moved = [p for p in g["prims"] if p["name"] in names]
    g["prims"] = [p for p in g["prims"] if p["name"] not in names]
    for p in moved:
        sides = [(p, "")]
        if p.get("mirror"):
            m = json.loads(json.dumps(p))
            m["mirror"] = False
            m["center"] = [-m["center"][0], m["center"][1], m["center"][2]]
            m["bone"] = m["bone"].replace(".L", ".R")
            m["name"] = m["name"].replace(".L", ".R")
            sides = [(dict(p, mirror=False), ".L"), (m, ".R")]
        for prim, suffix in sides:
            name = f"{garment}Rib.{prim['name']}"
            part(c, name, g["material"], [dict(prim, blend=0.0)], voxel=0.0012, skinFalloff=0.02, pattern="ribbed",
                 patternAmplitude=amplitude, patternScale=rib_scale, patternCenter=[prim["center"][0], 0.0, prim["center"][2]])
            for f in fz:
                c["fuzz"].append(dict(f, part=name, seed=f.get("seed", 40) + len(c["fuzz"])))

def add_frown(c):
    """Iteration 3 helper. Since iteration 4 the frown is defined on the measured face surface in upgrade_base;
    the old version used pre-iteration-4 coordinates (it moved the cheeks) and is no longer applied."""
    assert any(e["name"] == "frown" for e in c["expressions"])

def set_eyes(c, iris, pupil_deg=15, iris_deg=48):
    t = get_mat(c, "eye")["texture"]
    t["color2"] = iris
    t["params"] = [pupil_deg, iris_deg, 0, 0]
    get_mat(c, "eye").update(coatRoughness=0.015)

def set_brows(c, color, r1=0.0058, r2=0.0038, lift=0.0, tilt=0.0):
    brows = get_part(c, "brows")
    for p in brows["prims"]:
        p["a"][1] += lift; p["b"][1] += lift + tilt
        p["r1"], p["r2"] = r1 * S, r2 * S
    get_mat(c, "brow_felt")["baseColor"] = color

def slim_cap(c, margin=0.009):
    """Hair base hugging the skull (locks provide the volume) so no hat-like brim forms."""
    cap = get_part(c, "hairCap")
    cap["prims"] = [p for p in cap["prims"] if p["name"] != "bangs"]  # iteration 4: felted fringe instead; the brim left slivers
    for p in cap["prims"]:
        if p["name"] == "cap":
            p["center"] = [HEAD_C[0], HEAD_C[1] + 0.006, HEAD_C[2] - 0.004]
            p["radii"] = [HEAD_R[0] + margin, HEAD_R[1] + margin, HEAD_R[2] + margin]
        if p["name"] == "faceCut":  # the base stops at the top of the forehead; fringe locks form the hairline
            p["center"][1] += 0.05
    cap.update(patternAmplitude=0.002, noiseAmplitude=0.0025)
    for f in c["fuzz"]:
        if f["part"] == "hairCap":
            f.update(density=120, length=0.004)

def hair_mass(c, material, fiber, density=110, length=0.006, back=(0.16, 0.105), side=(0.055, 0.045), side_x=0.12):
    """Soft felted hair volume behind and beside the head, under the locks (iteration 4).
    The locks lie half-embedded on its surface, so the hair reads as one mass instead of separate cords.
    Everything below the chin in front of the body is cut away, so it never covers the neck or chest."""
    cap = get_part(c, "hairCap")
    part(c, "hairMass", material, [
        {"name": "back", "type": "roundCone", "bone": "head", "a": [0, 0.84, -0.025], "b": [0, 0.56, -0.06], "r1": back[0], "r2": back[1]},
        {"name": "side.L", "type": "roundCone", "bone": "head", "a": [side_x, 0.79, -0.03], "b": [side_x + 0.01, 0.57, -0.065],
         "r1": side[0], "r2": side[1], "blend": 0.04, "mirror": True},
        {"name": "chestCut", "type": "roundBox", "bone": "head", "center": [0, 0.48, 0.12], "halfSize": [0.14, 0.245, 0.12],
         "rounding": 0.03, "blend": 0.03, "subtract": True},
    ], voxel=0.003, skinFalloff=0.02, noiseAmplitude=0.004, noiseScale=14, pattern="strands", patternAmplitude=0.0025,
        patternScale=34, patternCenter=list(cap.get("patternCenter", [0, CAP_C[1] + CAP_R[1], CAP_C[2]])))
    fuzz(c, "hairMass", fiber, density, length, radius=2.3e-5, tilt=0.6, curl=0.5, segments=4, comb=0.8,
         combOrigin=[0.0, CAP_C[1] + CAP_R[1], 0.0], strayFraction=0.07, strayLength=2.0)

def felt_clumps(c, name, material, fiber, clumps, blend=0.01, voxel=0.0016, density=130, length=0.005,
                noise=0.0012, strands=0.0012, bone="head"):
    """Felted hair clumps as one blended SDF volume (iteration 4).
    Each clump is (points[3], root radius, tip radius): two round cones root->mid->tip, smoothly blended with
    its neighbours, so the result is a single felted mass with pointed tips and soft grooves between clumps
    (the references' fringes and tousled clumps) instead of separate cords."""
    prims = []
    for i, (pts, r0, r1) in enumerate(clumps):
        rm = r0 * 0.66 + r1 * 0.34
        prims.append({"name": f"{name}{i}a", "type": "roundCone", "bone": bone, "a": pts[0], "b": pts[1], "r1": r0, "r2": rm, "blend": blend})
        prims.append({"name": f"{name}{i}b", "type": "roundCone", "bone": bone, "a": pts[1], "b": pts[2], "r1": rm, "r2": r1, "blend": blend * 0.5})
    part(c, name, material, prims, voxel=voxel, skinFalloff=0.02, noiseAmplitude=noise, noiseScale=45,
         pattern="strands", patternAmplitude=strands, patternScale=90, patternCenter=[0, CAP_C[1] + CAP_R[1], CAP_C[2]])
    fuzz(c, name, fiber, density, length, radius=2.3e-5, tilt=0.6, curl=0.5, segments=4, comb=0.7,
         combOrigin=[0.0, CAP_C[1] + CAP_R[1], 0.0], strayFraction=0.06, strayLength=2.0)

def crown_clumps(rng, count, part_x=0.0, length_deg=(10, 22), lift=0.004, r0=0.022, front_gap=40):
    """Broad felted clumps over the top of the head, from the crown/parting outwards."""
    out = []
    for k in range(count):
        az = -180 + 360 * (k + rng.uniform(0.2, 0.8)) / count
        if front_gap > 0 and abs(abs(az) - 180) < front_gap * 0.5:
            continue
        el0 = rng.uniform(70, 80)
        el1 = el0 - rng.uniform(*length_deg) * 2
        pts = []
        for t in (0.0, 0.5, 1.0):
            p, n = on_ellipsoid(CAP_C, CAP_R, az, el0 + (el1 - el0) * t, lift * (0.4 + 0.8 * t))
            if t == 0.0:
                p[0] += part_x * (1 if math.sin(math.radians(az)) >= 0 else -1)
            pts.append(p)
        out.append((pts, r0 * rng.uniform(0.85, 1.15), r0 * 0.35))
    return out

# ------------------------------------------------------------------ hair builders
def drape(az, el, length, out, amp, wave_len, phase, n=9, body=0.115):
    """A lock that follows the hair volume outward and then falls, gently waving."""
    a = math.radians(az)
    radial = [math.sin(a), 0.0, -math.cos(a)]
    tangential = [math.cos(a), 0.0, math.sin(a)]
    rxz = math.hypot(CAP_R[0] * radial[0], CAP_R[2] * radial[2])
    root_y = CAP_C[1] + CAP_R[1] * math.sin(math.radians(el))
    root_r = rxz * math.cos(math.radians(el)) * 0.96
    widest, pts = root_r, []
    for i in range(n):
        s = i / (n - 1)
        y = root_y - s * length
        dy = (y - CAP_C[1]) / CAP_R[1]
        head_r = rxz * math.sqrt(max(0.0, 1 - dy * dy)) + out
        widest = max(widest, head_r)
        r = max(head_r, root_r) if y > CAP_C[1] else widest
        r = max(r * (1 - 0.1 * max(0.0, s - 0.6) / 0.4), body + 0.045 * abs(math.sin(a)))
        w = amp * math.sin(phase + 2 * math.pi * s * length / wave_len) * min(1.0, s * 3)
        p = [CAP_C[0] + radial[0] * (r + 0.3 * w) + tangential[0] * w, y, CAP_C[2] + radial[2] * (r + 0.3 * w) + tangential[2] * w]
        pts.append(p)
    return pts

def coil(center, radius, turns, tube, phase=0.0, n=40, squash=0.9):
    """A lock wound around a ball (styled bun)."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        h = (-0.75 + 1.5 * t) * radius * squash
        ring = math.sqrt(max(radius ** 2 - (h / squash) ** 2, 0)) + tube * 0.6
        a = phase + 2 * math.pi * turns * t
        pts.append([center[0] + ring * math.cos(a), center[1] + h, center[2] + ring * math.sin(a)])
    return pts

def crown_locks(rng, count, part_x=0.0, length_deg=(8, 20), lift=0.007, r0=0.016, front_gap=40):
    """Locks lying over the top of the hair volume from the crown/parting outwards, so the top reads as hair."""
    locks = []
    for k in range(count):
        az = -180 + 360 * (k + rng.uniform(0.2, 0.8)) / count
        if front_gap > 0 and abs(abs(az) - 180) < front_gap * 0.5:
            continue
        el0, el1 = rng.uniform(78, 86), rng.uniform(*length_deg)
        pts = []
        for i in range(6):
            t = i / 5
            p, n = on_ellipsoid(CAP_C, CAP_R, az, el0 + (el1 - el0) * t, lift * (0.6 + 0.8 * t))
            if i == 0:
                p[0] += part_x * (1 if math.sin(math.radians(az)) >= 0 else -1)
            pts.append(p)
        locks.append(lock(pts, r0 * rng.uniform(0.85, 1.1), r0 * 0.45, curl=0.003, turns=0.6, phase=rng.uniform(0, 6.28)))
    return locks

def spike(root, normal, length, droop, rng):
    """Short tapered clump pointing out of the scalp and bending down (tousled hair)."""
    d = v_norm(v_add(v_mul(normal, 1.0), [rng.uniform(-0.35, 0.35), -droop, rng.uniform(-0.35, 0.35)]))
    mid = v_add(root, v_mul(d, length * 0.5))
    tip = v_add(mid, v_mul(v_norm(v_add(d, [0, -droop * 0.8, 0])), length * 0.55))
    return [root, mid, tip]

# ------------------------------------------------------------------ characters
def character_a():
    c = load_base()
    c["name"] = "girl_white_hair"
    c["notes"] = "Iteration 3: explicit layered wool locks, coiled buns, ribbon bow, lashes, frown expression."
    drop(c, parts=("bangs", "bow"), locks=True)
    slim_cap(c)
    buns = get_part(c, "buns")
    for p in buns["prims"]:
        p["radii"] = [r * 1.22 for r in p["radii"]]  # iteration 4: reference buns are large round puffs (~40% of head width)
        p["center"] = [p["center"][0] * 1.12, p["center"][1] + 0.012, p["center"][2]]
    mat(c, "lash", type="standard", baseColor=[0.05, 0.035, 0.03], roughness=0.5)
    add_lashes(c, "lash")
    add_frown(c)
    bake_mouth(c, smile=0.6, cavity="mouthOpen")  # reference: small open happy mouth
    set_eyes(c, get_mat(c, "eye")["texture"]["color2"], pupil_deg=12, iris_deg=34)
    set_brows(c, [0.72, 0.64, 0.56], r1=0.0042, r2=0.0028, lift=0.012, tilt=0.002)  # iteration 4: hidden under the fringe
    wool, core = "wool_fiber", "wool_lock_core"
    get_mat(c, core).update(baseColor=[0.83, 0.81, 0.77])
    hair_mass(c, "wool_cap", wool, density=120, length=0.007)
    halo = dict(fuzzDensity=150, fuzzLength=0.009, fuzzRadius=2.4e-5, fuzzTilt=0.6, strayFraction=0.08, strayLength=2.0, samples=40)
    rng = random.Random(3)
    back, outer = [], []
    for k in range(46):  # inner layer, full circle except the face (iteration 4: denser, thicker, clear of the eyes)
        az = -132 + 264 * (k + rng.uniform(0.2, 0.8)) / 46
        back.append(lock(drape(az, rng.uniform(4, 16), rng.uniform(0.32, 0.42), 0.006, rng.uniform(0.012, 0.018), rng.uniform(0.07, 0.1), rng.uniform(0, 6.28)),
                         rng.uniform(0.021, 0.026), 0.008, curl=0.006, turns=1.5, phase=rng.uniform(0, 6.28)))
    for k in range(24):  # outer layer: shorter, higher, gives the layered silhouette
        az = -126 + 252 * (k + rng.uniform(0.2, 0.8)) / 24
        outer.append(lock(drape(az, rng.uniform(26, 38), rng.uniform(0.26, 0.34), 0.018, rng.uniform(0.012, 0.02), rng.uniform(0.07, 0.1), rng.uniform(0, 6.28)),
                          rng.uniform(0.019, 0.024), 0.007, curl=0.006, turns=1.2, phase=rng.uniform(0, 6.28)))
    group(c, "hair.back", wool, core, back, seed=51, **halo)
    group(c, "hair.outer", wool, core, outer, seed=52, **halo)
    # Iteration 4: the fringe and the crown are felted volumes with pointed clumps (reference), not cords.
    frng = random.Random(53)
    fringe = []
    for k in range(11):
        x = -0.13 + 0.026 * k + frng.uniform(-0.004, 0.004)
        tip_y = 0.845 + 0.008 * math.sin(k * 2.1) + frng.uniform(-0.006, 0.006)
        tx = x * 1.06 + frng.uniform(-0.008, 0.008)
        root = [x * 0.55, 0.985, 0.07]
        mid_z = ell_z(CAP_C, CAP_R, x * 0.92, 0.915) or 0.12
        tip_z = (ell_z(HEAD_C, HEAD_R, tx, tip_y) or 0.13) + 0.011
        fringe.append(([root, [x * 0.92, 0.915, mid_z + 0.004], [tx, tip_y, tip_z]], frng.uniform(0.024, 0.029), 0.0055))
    felt_clumps(c, "fringe", "wool_cap", wool, fringe, density=150, length=0.006)
    felt_clumps(c, "crown", "wool_cap", wool, crown_clumps(random.Random(31), 26, r0=0.026), voxel=0.002, density=130, length=0.006)
    for side, sx in (("L", 1), ("R", -1)):
        bc = [sx * 0.106 * 1.12, 1.0133 + 0.012, -0.0265]
        coils = [lock(coil(bc, 0.068, 2.2, 0.021, phase=ph), 0.022, 0.016) for ph in (0.0, 2.1)]
        group(c, f"bun.{side}", wool, core, coils, seed=54 if sx > 0 else 55, **halo)
    # Ribbon bow on the character's right (-x): two puffy loops, a knot and two tails.
    p0, n = on_ellipsoid(CAP_C, CAP_R, -128, 40, 0.02)
    u = v_norm(cross([0, 1, 0], n)); v = v_norm(cross(n, u))
    K = 1.6  # iteration 4: the reference bow is about a quarter of the head width
    P = lambda a, b, d=0.0: v_add(p0, v_add(v_mul(u, a * K), v_add(v_mul(v, b * K), v_mul(n, d * K))))
    bow = [lock([P(0, 0), P(0.02, 0.016, 0.004), P(0.042, 0.012, 0.003), P(0.04, -0.006), P(0.012, -0.004, 0.002), P(0, 0)], 0.0085 * K, 0.006 * K),
           lock([P(0, 0), P(-0.02, 0.016, 0.004), P(-0.042, 0.012, 0.003), P(-0.04, -0.006), P(-0.012, -0.004, 0.002), P(0, 0)], 0.0085 * K, 0.006 * K),
           lock([P(0.004, -0.002), P(0.016, -0.022), P(0.024, -0.036)], 0.006 * K, 0.004 * K),
           lock([P(-0.004, -0.002), P(-0.014, -0.022), P(-0.02, -0.038)], 0.006 * K, 0.004 * K),
           lock([P(-0.006, 0, 0.002), P(0.006, 0, 0.002)], 0.0095 * K, 0.009 * K)]
    mat(c, "bow_felt", baseColor=[0.17, 0.30, 0.62], sheen=0.8, sheenColor=[0.7, 0.8, 1.0])
    group(c, "bow", "bow_fiber", "bow_felt", bow, fuzzDensity=120, fuzzLength=0.0025, fuzzRadius=2e-5, samples=36, seed=56)
    dress = get_part(c, "dress")
    keep = [p for p in dress["prims"] if p["name"].startswith(("sleeve", "cuff"))]
    dress["prims"] = [
        {"name": "bodice", "type": "roundCone", "bone": "chest", "a": [0, 0.665, 0], "b": [0, 0.555, 0], "r1": 0.068, "r2": 0.074},
        {"name": "waist", "type": "ellipsoid", "bone": "spine", "center": [0, 0.548, 0.006], "radii": [0.08, 0.03, 0.074], "blend": 0.03},
        {"name": "skirt", "type": "roundCone", "bone": "hips", "a": [0, 0.545, 0], "b": [0, 0.32, 0], "r1": 0.082, "r2": 0.17, "blend": 0.03},
        {"name": "bell", "type": "ellipsoid", "bone": "hips", "center": [0, 0.335, 0], "radii": [0.185, 0.075, 0.17], "blend": 0.05},
        {"name": "hemCut", "type": "roundBox", "center": [0, 0.17, 0], "halfSize": [0.3, 0.1, 0.3], "rounding": 0.01, "blend": 0.02, "subtract": True},
    ] + keep
    part(c, "hemBand", get_part(c, "dress")["material"], [
        {"name": "band", "type": "ellipsoid", "bone": "hips", "center": [0, 0.283, 0], "radii": [0.197, 0.016, 0.182]},
        {"name": "inner", "type": "ellipsoid", "bone": "hips", "center": [0, 0.283, 0], "radii": [0.17, 0.05, 0.155], "blend": 0.004, "subtract": True},
    ], voxel=0.0014, skinFalloff=0.02, pattern="ribbed", patternAmplitude=0.0016, patternScale=260, patternCenter=[0, 0, 0])
    c["defaultPose"] = {"upperArm.L": [0, 0, 9], "upperArm.R": [0, 0, -9]}
    rib_bands(c, "dress", ("cuff.L",))
    prefix_materials(c, "A_")
    return c

def character_b():
    c = load_base()
    c["name"] = "girl_brown_glasses"
    c["notes"] = "Iteration 3: brown curly yarn hair with a coiled top bun and clips, round glasses, blouse, rose knit vest, sage shorts."
    drop(c, parts=("bangs", "bow", "buns", "dress", "collar", "tights"), locks=True)
    set_eyes(c, [0.30, 0.15, 0.06], pupil_deg=12, iris_deg=33)
    set_brows(c, [0.22, 0.12, 0.06], r1=0.0062, r2=0.0042, lift=0.004, tilt=0.002)
    mat(c, "lash", type="standard", baseColor=[0.06, 0.035, 0.025], roughness=0.5)
    add_lashes(c, "lash", thickness=0.0017)
    add_frown(c)
    bake_mouth(c, smile=1.0, cavity="grin")  # reference: wide open smile
    skin = get_mat(c, "skin")
    skin["texture"]["amount"] = 0.8
    slim_cap(c)
    hair_core = mat(c, "hair_core", baseColor=[0.15, 0.075, 0.038], sheen=0.5, sheenColor=[0.8, 0.65, 0.5],
                    texture={"type": "noise", "color2": [0.22, 0.11, 0.05], "scale": 80, "amount": 0.4})
    hair_fiber = mat(c, "hair_fiber", type="fiber", baseColor=[0.12, 0.06, 0.03], betaM=0.45, betaN=0.85)
    mat(c, "wool_cap", baseColor=[0.18, 0.09, 0.045], sheen=0.5,
        texture={"type": "noise", "color2": [0.2, 0.1, 0.05], "scale": 30, "amount": 0.3})
    for f in c["fuzz"]:
        if f["part"] == "hairCap": f["material"] = hair_fiber
    halo = dict(fuzzDensity=110, fuzzLength=0.006, fuzzRadius=2.4e-5, fuzzTilt=0.6, strayFraction=0.08)
    rng = random.Random(7)
    curls = []
    for k in range(30):
        az = -125 + 250 * (k + rng.uniform(0.2, 0.8)) / 30
        pts = drape(az, rng.uniform(4, 22), rng.uniform(0.26, 0.38), 0.012, 0.004, 0.1, 0.0, n=8)
        curls.append(lock(pts, rng.uniform(0.017, 0.022), 0.009, curl=rng.uniform(0.016, 0.022),
                          turns=rng.uniform(2.2, 3.2), phase=rng.uniform(0, 6.28)))
    group(c, "hair.curls", hair_fiber, hair_core, curls, samples=96, seed=61, **halo)
    hair_mass(c, "wool_cap", hair_fiber, density=100, length=0.006, back=(0.155, 0.1), side=(0.05, 0.04))
    sweep = []  # centre-parted side-swept fringe framing the face, felted (iteration 4)
    for sx in (1, -1):
        for k in range(5):
            x = 0.04 + 0.024 * k
            root = [sx * 0.012, 0.99, 0.05]
            mid = [sx * (x * 0.95 + 0.01), 0.935, (ell_z(CAP_C, CAP_R, x * 0.95 + 0.01, 0.935) or 0.11) + 0.006]
            tip_y = 0.875 - 0.022 * k
            tx = min(x * 1.15 + 0.035, 0.165)
            tip = [sx * tx, tip_y, (ell_z(HEAD_C, HEAD_R, tx, tip_y) or 0.09) + 0.011]
            sweep.append(([root, mid, tip], 0.022, 0.004))
    felt_clumps(c, "fringe", "hair_core", hair_fiber, sweep, density=110, length=0.005)
    bun_c = [0.0, 1.045, -0.03]
    bun = [lock(coil(bun_c, 0.05, 2.4, 0.019, phase=ph), 0.02, 0.014) for ph in (0.0, 2.3)]
    bun.append(lock(coil([0.0, 1.085, -0.032], 0.028, 1.6, 0.014, phase=1.0, n=28), 0.015, 0.01))
    group(c, "hair.bun", hair_fiber, hair_core, bun, samples=60, seed=63, **halo)
    felt_clumps(c, "crown", "hair_core", hair_fiber, crown_clumps(random.Random(37), 26, part_x=0.012, front_gap=70, r0=0.024),
                voxel=0.002, density=110, length=0.005)
    # Pastel clips (pompoms and a felt flower) around the bun base.
    pink = mat(c, "clip_pink", baseColor=[0.85, 0.45, 0.5], sheen=0.8)
    part(c, "clips", pink, [
        {"name": "pom1", "type": "ellipsoid", "bone": "head", "center": [-0.045, 1.0, 0.02], "radii": [0.012, 0.012, 0.012]},
        {"name": "pom2", "type": "ellipsoid", "bone": "head", "center": [-0.022, 1.004, 0.035], "radii": [0.011, 0.011, 0.011], "blend": 0.002},
        {"name": "petal1", "type": "ellipsoid", "bone": "head", "center": [0.035, 1.012, 0.03], "radii": [0.012, 0.009, 0.007], "rotationDeg": [0, 0, 30], "blend": 0.004},
        {"name": "petal2", "type": "ellipsoid", "bone": "head", "center": [0.052, 1.0, 0.026], "radii": [0.012, 0.009, 0.007], "rotationDeg": [0, 0, -40], "blend": 0.004},
        {"name": "petal3", "type": "ellipsoid", "bone": "head", "center": [0.043, 0.99, 0.034], "radii": [0.011, 0.009, 0.007], "rotationDeg": [0, 0, 90], "blend": 0.004},
    ], voxel=0.0015)
    fuzz(c, "clips", hair_fiber, 0, 0.002)
    c["fuzz"] = [f for f in c["fuzz"] if f["part"] != "clips"]
    fuzz(c, "clips", mat(c, "clip_fiber", type="fiber", baseColor=[0.9, 0.6, 0.65], betaM=0.4, betaN=0.8), 260, 0.003)
    # Round glasses: thin frames (curves) and thin glass lenses.
    frame = mat(c, "glasses_frame", type="standard", baseColor=[0.35, 0.18, 0.1], roughness=0.25, coat=0.8, coatRoughness=0.05)
    gz = 0.176  # in front of the larger eyes
    rings = []
    for sx in (1, -1):
        cx = sx * EYE_L[0]
        rings.append(lock([[cx + 0.046 * math.cos(2 * math.pi * t / 32), EYE_L[1] + 0.046 * math.sin(2 * math.pi * t / 32),
                            gz - 0.004 * (1 - math.cos(2 * math.pi * t / 32)) * sx * 0] for t in range(33)], 0.0016, 0.0016))
        rings.append(lock([[sx * 0.118, 0.8, gz - 0.006], [sx * 0.168, 0.81, 0.09], [sx * 0.174, 0.805, 0.0]], 0.0015, 0.0013))
    rings.append(lock([[-0.026, 0.8, gz + 0.002], [0.0, 0.806, gz + 0.006], [0.026, 0.8, gz + 0.002]], 0.0016, 0.0016))
    group(c, "glasses", frame, frame, rings, samples=64, roundTip=False, seed=64)
    lens = mat(c, "glasses_lens", type="glass", baseColor=[0.98, 0.98, 0.98], ior=1.5, thin=True, castsShadow=False)
    part(c, "lenses", lens, [{"name": "lens.L", "type": "disc", "bone": "head", "center": [EYE_L[0], EYE_L[1], gz - 0.001],
                              "halfSize": [0.045, 0.045, 0.0012], "rounding": 0.001, "mirror": True}], voxel=0.0008)
    # Clothes: blouse, open knit vest with pockets and buttons, puffy shorts, bare legs.
    blouse = mat(c, "blouse_cotton", baseColor=[0.86, 0.84, 0.79], sheen=0.4, sheenColor=[1, 1, 1],
                 texture={"type": "noise", "color2": [0.8, 0.78, 0.73], "scale": 60, "amount": 0.3})
    part(c, "blouse", blouse, [
        {"name": "torso", "type": "roundCone", "bone": "chest", "a": [0, 0.662, 0], "b": [0, 0.47, 0], "r1": 0.066, "r2": 0.083},
        {"name": "belly", "type": "ellipsoid", "bone": "spine", "center": [0, 0.5, 0.008], "radii": [0.09, 0.055, 0.082], "blend": 0.04},
        {"name": "sleeveUpper.L", "type": "roundCone", "bone": "upperArm.L", "a": [0.075, 0.625, 0], "b": [0.122, 0.515, 0], "r1": 0.036, "r2": 0.034, "blend": 0.025, "mirror": True},
        {"name": "sleeveLower.L", "type": "roundCone", "bone": "forearm.L", "a": [0.122, 0.515, 0], "b": [0.15, 0.448, 0.012], "r1": 0.034, "r2": 0.03, "blend": 0.015, "mirror": True},
        {"name": "cuff.L", "type": "ellipsoid", "bone": "forearm.L", "center": [0.152, 0.446, 0.013], "radii": [0.03, 0.011, 0.03], "blend": 0.006, "mirror": True},
    ], voxel=0.002, skinFalloff=0.015, skinSmoothing=3)
    fuzz(c, "blouse", mat(c, "blouse_fiber", type="fiber", baseColor=[0.9, 0.88, 0.84], betaM=0.4, betaN=0.8), 30, 0.0018)
    part(c, "blouseCollar", blouse, [
        {"name": "collarFlap.L", "type": "ellipsoid", "bone": "chest", "center": [0.03, 0.652, 0.058], "radii": [0.038, 0.008, 0.026], "rotationDeg": [10, -30, -18], "mirror": True},
        {"name": "neckHole", "type": "capsule", "bone": "chest", "a": [0, 0.62, 0], "b": [0, 0.7, 0], "r": 0.04, "blend": 0.004, "subtract": True},
    ], voxel=0.0012, skinFalloff=0.02)
    btn = mat(c, "button_cream", type="standard", baseColor=[0.85, 0.8, 0.7], roughness=0.35, coat=0.5)
    part(c, "blouseButtons", btn, [{"name": f"b{k}", "type": "ellipsoid", "bone": "chest", "center": [0, 0.62 - 0.035 * k, 0.074 + 0.004 * k],
                                    "radii": [0.0045, 0.0045, 0.0022]} for k in range(4)], voxel=0.0008)
    vest = mat(c, "vest_knit", baseColor=[0.36, 0.22, 0.21], sheen=0.55, sheenColor=[0.85, 0.65, 0.62],
               texture={"type": "knit", "color2": [0.3, 0.18, 0.17], "scale": 170, "amount": 0.15})
    part(c, "vest", vest, [
        {"name": "shell", "type": "roundCone", "bone": "chest", "a": [0, 0.655, -0.004], "b": [0, 0.455, 0], "r1": 0.075, "r2": 0.103},
        {"name": "hem", "type": "ellipsoid", "bone": "spine", "center": [0, 0.47, 0.0], "radii": [0.098, 0.03, 0.09], "blend": 0.03},
        {"name": "frontOpen", "type": "roundBox", "bone": "chest", "center": [0, 0.56, 0.11], "halfSize": [0.019, 0.14, 0.06], "rounding": 0.01, "blend": 0.01, "subtract": True},
        {"name": "vNeck", "type": "ellipsoid", "bone": "chest", "center": [0, 0.665, 0.1], "radii": [0.042, 0.1, 0.06], "blend": 0.01, "subtract": True},
        {"name": "neckOpen", "type": "ellipsoid", "bone": "chest", "center": [0, 0.672, 0.02], "radii": [0.062, 0.05, 0.075], "blend": 0.01, "subtract": True},
        {"name": "armHole.L", "type": "ellipsoid", "bone": "chest", "center": [0.085, 0.6, 0], "radii": [0.035, 0.05, 0.05], "blend": 0.008, "subtract": True, "mirror": True},
        {"name": "inner", "type": "roundCone", "bone": "chest", "a": [0, 0.68, -0.004], "b": [0, 0.40, 0], "r1": 0.068, "r2": 0.094, "blend": 0.003, "subtract": True},
    ], voxel=0.0014, skinFalloff=0.015, skinSmoothing=3, pattern="knit", patternAmplitude=0.0012, patternScale=150, patternCenter=[0, 0, 0])
    fuzz(c, "vest", mat(c, "vest_fiber", type="fiber", baseColor=[0.5, 0.3, 0.3], betaM=0.4, betaN=0.8), 90, 0.003)
    part(c, "vestPockets", vest, [{"name": "pocket.L", "type": "roundBox", "bone": "spine", "center": [0.05, 0.49, 0.085],
                                   "halfSize": [0.022, 0.02, 0.004], "rounding": 0.003, "rotationDeg": [0, 28, 0], "mirror": True}], voxel=0.0012)
    # Embroidered motifs on each front panel (small felt flowers: cream centre, dark petals).
    def vest_z(x, y):
        t = (0.655 - y) / 0.2
        r = 0.075 + (0.103 - 0.075) * t
        return math.sqrt(max(r * r - x * x, 0.0)) - 0.003
    cream = mat(c, "motif_cream", baseColor=[0.86, 0.8, 0.7], sheen=0.6)
    dark = mat(c, "motif_dark", baseColor=[0.12, 0.09, 0.09], sheen=0.5)
    petals, centres = [], []
    for sx in (1, -1):
        for (mx, my, s) in ((0.047, 0.585, 1.0), (0.058, 0.548, 0.75)):
            x0 = sx * mx
            centres.append({"name": f"mc{len(centres)}", "type": "ellipsoid", "bone": "chest", "center": [x0, my, vest_z(mx, my) + 0.002],
                            "radii": [0.0045 * s, 0.0045 * s, 0.0025]})
            for k in range(5):
                a = 2 * math.pi * k / 5 + 0.3
                px, py = mx + 0.008 * s * math.cos(a), my + 0.008 * s * math.sin(a)
                petals.append({"name": f"mp{len(petals)}", "type": "ellipsoid", "bone": "chest",
                               "center": [sx * px, py, vest_z(px, py) + 0.0015], "radii": [0.005 * s, 0.003 * s, 0.002],
                               "rotationDeg": [0, 0, math.degrees(a) * sx], "blend": 0.001})
    part(c, "vestMotifs", dark, petals, voxel=0.0007)
    part(c, "vestMotifCentres", cream, centres, voxel=0.0007)
    brass = mat(c, "button_brass", type="standard", baseColor=[0.75, 0.55, 0.3], roughness=0.3, coat=0.8, specular=1.0)
    part(c, "vestButtons", brass, [{"name": f"vb{k}.L", "type": "ellipsoid", "bone": "chest", "center": [0.034, 0.59 - 0.04 * k, 0.084 + 0.004 * k],
                                    "radii": [0.004, 0.004, 0.0025], "mirror": True} for k in range(3)], voxel=0.0008)
    shorts = mat(c, "shorts_felt", baseColor=[0.27, 0.34, 0.27], sheen=0.7,
                 texture={"type": "noise", "color2": [0.22, 0.28, 0.22], "scale": 50, "amount": 0.3})
    part(c, "shorts", shorts, [
        {"name": "waist", "type": "roundCone", "bone": "hips", "a": [0, 0.47, 0], "b": [0, 0.40, 0], "r1": 0.088, "r2": 0.095},
        {"name": "leg.L", "type": "roundCone", "bone": "thigh.L", "a": [0.048, 0.42, 0], "b": [0.06, 0.32, 0.004], "r1": 0.062, "r2": 0.06, "blend": 0.03, "mirror": True},
        {"name": "cuff.L", "type": "ellipsoid", "bone": "thigh.L", "center": [0.06, 0.305, 0.004], "radii": [0.06, 0.016, 0.058], "blend": 0.012, "mirror": True},
    ], voxel=0.002, skinFalloff=0.02, skinSmoothing=3)
    fuzz(c, "shorts", mat(c, "shorts_fiber", type="fiber", baseColor=[0.33, 0.4, 0.32], betaM=0.4, betaN=0.8), 70, 0.0028)
    part(c, "legs", "skin", [
        {"name": "thigh.L", "type": "capsule", "bone": "thigh.L", "a": [0.05, 0.40, 0], "b": [0.054, 0.22, 0], "r": 0.036, "mirror": True},
        {"name": "shin.L", "type": "capsule", "bone": "shin.L", "a": [0.054, 0.22, 0], "b": [0.056, 0.07, 0], "r": 0.032, "blend": 0.02, "mirror": True},
    ], voxel=0.0025, skinSmoothing=2)
    prefix_materials(c, "B_")
    return c

def character_c():
    c = load_base()
    c["name"] = "boy_dark_hair"
    c["notes"] = "Iteration 3: tousled black wool clumps, half-lidded sleepy eyes, low brows, mustard fleece hoodie, black joggers, sneakers, backpack straps."
    drop(c, parts=("bangs", "bow", "buns", "dress", "collar", "tights", "boots", "soles"), locks=True)
    set_eyes(c, [0.2, 0.12, 0.07], pupil_deg=12, iris_deg=31)
    set_brows(c, [0.05, 0.04, 0.035], r1=0.0048, r2=0.0038, lift=-0.002, tilt=-0.003)
    mat(c, "lash", type="standard", baseColor=[0.04, 0.03, 0.03], roughness=0.5)
    add_lashes(c, "lash", thickness=0.0014, flick=0.4)
    add_frown(c)
    c["defaultPose"] = {"lid.L": [34, 0, 0], "lid.R": [34, 0, 0], "brow.L": [3, 0, 0], "brow.R": [3, 0, 0]}
    bake_mouth(c, frown=0.35, cavity="mouthOpen", scale=0.5, closed=True)  # reference: small flat, slightly sulky mouth
    skin = get_mat(c, "skin")
    skin["texture"]["amount"] = 0.45
    cap = get_part(c, "hairCap")
    cap.update(patternAmplitude=0.004, noiseAmplitude=0.005)
    cap["prims"] = [p for p in cap["prims"] if p["name"] != "bangs"]  # iteration 4: the fringe clumps cover the forehead, no brim
    for p in cap["prims"]:
        if p["name"] == "faceCut":
            p["center"][1] += 0.012
    black_core = mat(c, "hair_core", baseColor=[0.03, 0.028, 0.027], sheen=0.45, sheenColor=[0.35, 0.35, 0.38],
                     texture={"type": "noise", "color2": [0.02, 0.02, 0.02], "scale": 80, "amount": 0.5})
    black_fiber = mat(c, "hair_fiber", type="fiber", baseColor=[0.035, 0.032, 0.03], betaM=0.4, betaN=0.8)
    mat(c, "wool_cap", baseColor=[0.03, 0.028, 0.027], sheen=0.45, sheenColor=[0.35, 0.35, 0.38])
    for f in c["fuzz"]:
        if f["part"] == "hairCap": f["material"] = black_fiber
    rng = random.Random(11)
    spikes = []
    for k in range(96):  # iteration 4: longer, thicker clumps that flare out of a larger volume
        az = rng.uniform(-180, 180)
        el = rng.uniform(0, 88)
        if 115 < abs(az) and el < 38:  # the face: the fringe covers the forehead
            continue
        root, n = on_ellipsoid(CAP_C, CAP_R, az, el, -0.006)
        top = el > 58
        length = rng.uniform(0.075, 0.115) * (1.1 if top else 1.0)
        droop = rng.uniform(0.05, 0.45) if top else rng.uniform(0.4, 0.9)
        spikes.append((spike(root, n, length, droop, rng), rng.uniform(0.026, 0.034), 0.003))
    for k in range(8):  # heavy pointed fringe clumps down to the brows
        x = -0.105 + 0.03 * k + rng.uniform(-0.006, 0.006)
        root = [x * 0.6, 0.985, 0.085]
        tip_y = 0.848 + rng.uniform(-0.01, 0.006)
        tx = x * 1.1 + rng.uniform(-0.018, 0.018)
        tip = [tx, tip_y, (ell_z(HEAD_C, HEAD_R, tx, tip_y) or 0.13) + 0.016]
        mid = [x * 0.95, 0.925, (ell_z(CAP_C, CAP_R, x * 0.95, 0.925) or 0.12) + 0.014]
        spikes.append(([root, mid, tip], rng.uniform(0.026, 0.031), 0.003))
    felt_clumps(c, "hairClumps", "hair_core", black_fiber, spikes, blend=0.008, voxel=0.0018, density=120, length=0.0045,
                noise=0.0015, strands=0.0014)
    hoodie = mat(c, "hoodie_fleece", baseColor=[0.62, 0.42, 0.07], sheen=0.9, sheenColor=[1.0, 0.85, 0.5],
                 texture={"type": "noise", "color2": [0.52, 0.34, 0.05], "scale": 45, "amount": 0.35})
    part(c, "hoodie", hoodie, [
        {"name": "torso", "type": "roundCone", "bone": "chest", "a": [0, 0.658, 0], "b": [0, 0.43, 0], "r1": 0.082, "r2": 0.104},
        {"name": "belly", "type": "ellipsoid", "bone": "spine", "center": [0, 0.47, 0.012], "radii": [0.11, 0.065, 0.1], "blend": 0.04},
        {"name": "sleeveUpper.L", "type": "roundCone", "bone": "upperArm.L", "a": [0.078, 0.622, 0], "b": [0.124, 0.515, 0], "r1": 0.046, "r2": 0.043, "blend": 0.025, "mirror": True},
        {"name": "sleeveLower.L", "type": "roundCone", "bone": "forearm.L", "a": [0.124, 0.515, 0], "b": [0.15, 0.452, 0.012], "r1": 0.043, "r2": 0.04, "blend": 0.015, "mirror": True},
        {"name": "cuff.L", "type": "ellipsoid", "bone": "forearm.L", "center": [0.153, 0.447, 0.013], "radii": [0.035, 0.013, 0.035], "blend": 0.008, "mirror": True},
        {"name": "hem", "type": "ellipsoid", "bone": "hips", "center": [0, 0.432, 0.004], "radii": [0.117, 0.021, 0.109], "blend": 0.02},
    ], voxel=0.002, skinFalloff=0.015, skinSmoothing=3)
    part(c, "hood", hoodie, [
        {"name": "hoodShell", "type": "ellipsoid", "bone": "chest", "center": [0, 0.668, -0.04], "radii": [0.102, 0.038, 0.08]},
        {"name": "neckHole", "type": "capsule", "bone": "chest", "a": [0, 0.6, 0.0], "b": [0, 0.72, 0.0], "r": 0.04, "blend": 0.006, "subtract": True},
    ], voxel=0.002, skinFalloff=0.02)
    part(c, "pocket", hoodie, [{"name": "pocket", "type": "roundBox", "bone": "spine", "center": [0, 0.482, 0.113],
                                "halfSize": [0.06, 0.03, 0.006], "rounding": 0.005, "rotationDeg": [-8, 0, 0]}], voxel=0.0015)
    hfib = mat(c, "hoodie_fiber", type="fiber", baseColor=[0.7, 0.5, 0.12], betaM=0.4, betaN=0.85)
    for pn in ("hoodie", "hood", "pocket"):
        fuzz(c, pn, hfib, 160, 0.0035)
    rib_bands(c, "hoodie", ("cuff.L", "hem"), rib_scale=300)
    cord = mat(c, "cord", baseColor=[0.82, 0.76, 0.62], sheen=0.4)
    group(c, "drawstrings", cord, cord, [lock([[sx * 0.022, 0.648, 0.078], [sx * 0.024, 0.61, 0.093], [sx * 0.022, 0.575, 0.1]], 0.0028, 0.0028)
                                         for sx in (1, -1)], bone="chest", samples=16, roundTip=True)
    strap = mat(c, "strap", type="standard", baseColor=[0.08, 0.09, 0.13], roughness=0.6)
    group(c, "straps.L", strap, strap, [lock([[0.062, 0.48, -0.086], [0.077, 0.62, -0.07], [0.082, 0.672, 0.0], [0.077, 0.63, 0.079], [0.072, 0.53, 0.1]], 0.0085, 0.0085)],
          bone="chest", mirror=True, samples=40, roundTip=False)
    jog = mat(c, "jogger_fleece", baseColor=[0.025, 0.025, 0.028], sheen=0.5, sheenColor=[0.35, 0.35, 0.4])
    part(c, "joggers", jog, [
        {"name": "waist", "type": "roundCone", "bone": "hips", "a": [0, 0.45, 0], "b": [0, 0.39, 0], "r1": 0.095, "r2": 0.098},
        {"name": "thigh.L", "type": "roundCone", "bone": "thigh.L", "a": [0.054, 0.40, 0], "b": [0.06, 0.22, 0], "r1": 0.057, "r2": 0.051, "blend": 0.03, "mirror": True},
        {"name": "shin.L", "type": "roundCone", "bone": "shin.L", "a": [0.06, 0.22, 0], "b": [0.06, 0.085, 0], "r1": 0.051, "r2": 0.049, "blend": 0.02, "mirror": True},
        {"name": "ankle.L", "type": "ellipsoid", "bone": "shin.L", "center": [0.059, 0.084, 0.002], "radii": [0.046, 0.016, 0.046], "blend": 0.012, "mirror": True},
    ], voxel=0.002, skinFalloff=0.02, skinSmoothing=3)
    fuzz(c, "joggers", mat(c, "jogger_fiber", type="fiber", baseColor=[0.035, 0.035, 0.04], betaM=0.4, betaN=0.85), 140, 0.003)
    yellow = mat(c, "sneaker_canvas", baseColor=[0.78, 0.6, 0.12], sheen=0.5)
    part(c, "sneakers", yellow, [{"name": "upper.L", "type": "roundBox", "bone": "foot.L", "center": [0.058, 0.04, 0.026],
                                  "halfSize": [0.042, 0.032, 0.07], "rounding": 0.026, "mirror": True}], voxel=0.0018)
    fuzz(c, "sneakers", mat(c, "sneaker_fiber", type="fiber", baseColor=[0.8, 0.62, 0.15], betaM=0.4, betaN=0.8), 60, 0.0018)
    white = mat(c, "sole_white", type="standard", baseColor=[0.86, 0.85, 0.82], roughness=0.6)
    part(c, "sneakerSoles", white, [
        {"name": "sole.L", "type": "roundBox", "bone": "foot.L", "center": [0.058, 0.011, 0.028], "halfSize": [0.045, 0.012, 0.074], "rounding": 0.009, "mirror": True},
        {"name": "toe.L", "type": "ellipsoid", "bone": "foot.L", "center": [0.058, 0.03, 0.084], "radii": [0.036, 0.022, 0.024], "blend": 0.01, "mirror": True},
    ], voxel=0.0015)
    prefix_materials(c, "C_")
    return c

if __name__ == "__main__":
    for fn, path in ((character_a, "girl_white_hair"), (character_b, "girl_brown_glasses"), (character_c, "boy_dark_hair")):
        c = fn()
        json.dump(c, open(f"content/characters/{path}.character.json", "w"), indent=1)
        print("wrote", path, "-", len(c["parts"]), "parts,", len(c["lockGroups"]), "lock groups")
