"""charsys body modules: an isolated copy of the v6 reference builder's part generators (head, face, ears, eyes,
brows/mouth, hoodie, hands, legs, shoes, backpack, landmarks, rig fitting, weights, expression keys).

Copied verbatim from pipeline/blender/boy_pilot/build_boy_pilot.py (sha256 6784513f7dea4c3cf887e8e4d2e4cfe23806213d8e6ee9f427aa31aa350de8da); only the
unconditional `main()` call was removed so the module can be imported. The v6 reference file is never modified.
The proportion and colour globals are set per character with `configure(spec)` (appended at the end); the v6
`main()` and `build_hair()` remain in this copy for reference but charsys uses build_character.py and hair.py.
"""
"""Automated pilot build of `boy_yellow_hoodie` in Blender (no manual modelling).

    blender -b --factory-startup -P pipeline/blender/boy_pilot/build_boy_pilot.py -- --out <dir> [--stage model|rig|all]

Every dimension below comes from the reference measurements (reference_index views #27 / #7, colour-segmented height
and width profiles, annotated face landmarks; see docs/evaluation/boy_pilot/). Total height 1.10 m (no real-world
height is given by the references; only proportions are compared). Modelling pose: A-pose (TD-36).
Blender coordinates: metres, +Z up, the character faces -Y, his left is +X.

Outputs (in --out): boy_yellow_hoodie_pilot_master.blend (A-pose, rigged), boy_yellow_hoodie_pilot_compare.blend
(arms posed down as in reference #27, fur regenerated on the posed surfaces), boy_yellow_hoodie_pilot.glb (meshes,
rig, weights, shape keys; fur curves are not carried by glTF), build_report.json."""
import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geom as G  # noqa: E402

H = 1.10  # total height (top of hair spikes to sole), metres

# ------------------------------------------------------------------------------ measured targets (fractions of H)
# Heights measured from #27 front (563 px figure) and cross-checked with #7 and #27 back (see measurements doc).
Z = {
    "hair_top": 1.10, "hair_mass_top": 1.06, "brow": 0.840, "fringe_tip": 0.812, "eye": 0.778, "nose": 0.748,
    "mouth": 0.724, "chin": 0.698, "ear": 0.756, "neck_top": 0.70, "collar": 0.684, "shoulder": 0.640,
    "hem": 0.368, "crotch": 0.340, "cuff": 0.118, "shoe_top": 0.105,
}
EYE_X, EYE_R = 0.064, 0.037  # eye centres ±7.5 cm (eye spacing / ear width 0.39-0.42 measured)
COLORS = {  # target appearances (sRGB) measured on #7/#27; albedos below are calibrated so renders land near them
    "hair": (48, 39, 35), "skin": (193, 144, 122), "hoodie": (192, 145, 80), "trousers": (40, 33, 32),
    "shoe_yellow": (185, 138, 77), "cream": (210, 197, 188),
}


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", default="all", choices=["model", "all"])
    ap.add_argument("--fur-scale", type=float, default=1.0, help="fur density multiplier (previews)")
    return ap.parse_args(argv)


# ============================================================================== materials
# Albedos (sRGB). First estimates; pipeline/blender/boy_pilot/calibrate_colors.py adjusts them so the harness renders
# match the measured reference colours, and writes albedo_calibration.json next to this script.
ALB = {"skin": (226, 172, 146), "hair": (34, 31, 30), "hair_fur": (40, 36, 34), "hoodie": (206, 142, 48),
       "hoodie_fur": (210, 146, 52), "trousers": (36, 32, 32), "trousers_fur": (40, 36, 35), "shoe": (204, 142, 50),
       "shoe_fur": (208, 146, 54), "cream": (226, 214, 200)}
_cal = os.path.join(os.path.dirname(os.path.abspath(__file__)), "albedo_calibration.json")
if os.path.exists(_cal):
    ALB.update({k: tuple(v) for k, v in json.load(open(_cal)).items()})


def make_materials():
    M = {}
    M["skin"] = G.blush_skin_material("M_skin", ALB["skin"], (232, 140, 128),
                                      [(0.092, -0.12, 0.730), (-0.092, -0.12, 0.730)], 0.05)
    M["ear"] = G.material("M_ear", (205, 128, 104), roughness=0.55, subsurface=0.25, sss_radius=(1, 0.4, 0.3), sss_scale=0.012)
    M["eye"] = G.eye_material("M_eye", (112, 74, 50), (60, 38, 26), EYE_R, 0.023, 0.0105)
    M["lash"] = G.material("M_lash", (24, 19, 17), roughness=0.6)
    M["brow"] = G.material("M_brow", (34, 26, 22), roughness=0.85)
    M["mouth"] = G.material("M_mouth", (96, 44, 40), roughness=0.6)
    M["hair"] = G.material("M_hair_felt", ALB["hair"], roughness=0.95, sheen=0.15, sheen_tint=(0.62, 0.48, 0.42))
    M["hair_fur"] = G.hair_material("M_hair_fur", ALB["hair_fur"], roughness=0.9)
    M["hoodie"] = G.material("M_hoodie_fleece", ALB["hoodie"], roughness=0.95, sheen=0.25, sheen_tint=(1.0, 0.85, 0.6))
    M["hoodie_fur"] = G.hair_material("M_hoodie_fur", ALB["hoodie_fur"], roughness=0.8)
    M["cream"] = G.material("M_cream", ALB["cream"], roughness=0.85, sheen=0.2)
    M["cord_tip"] = G.material("M_cord_tip", (150, 120, 92), roughness=0.6)
    M["trousers"] = G.material("M_trousers_fleece", ALB["trousers"], roughness=0.95, sheen=0.15, sheen_tint=(0.60, 0.48, 0.45))
    M["trousers_fur"] = G.hair_material("M_trousers_fur", ALB["trousers_fur"], roughness=0.8)
    M["shoe"] = G.material("M_shoe_felt", ALB["shoe"], roughness=0.9, sheen=0.25, sheen_tint=(1.0, 0.85, 0.6))
    M["shoe_fur"] = G.hair_material("M_shoe_fur", ALB["shoe_fur"], roughness=0.8)
    M["sole"] = G.material("M_sole", ALB["cream"], roughness=0.7)
    M["sock"] = G.material("M_sock", (232, 222, 206), roughness=0.9, sheen=0.4)
    M["pack"] = G.material("M_backpack_felt", (68, 56, 68), roughness=0.9, sheen=0.6, sheen_tint=(0.85, 0.8, 0.9))
    M["webbing"] = G.material("M_webbing", (62, 60, 68), roughness=0.75)
    M["buckle"] = G.material("M_buckle", (90, 84, 78), roughness=0.4, specular=0.5)
    return M


# ============================================================================== head and face
def build_head(C, M):
    # Rounded, wide head with full low cheeks (rings: z, cx, cy, half-width, front depth, back depth).
    prof = [
        (0.696, 0, -0.06, 0.020, 0.035, 0.020),
        (0.702, 0, -0.04, 0.086, 0.083, 0.043),
        (0.712, 0, -0.02, 0.123, 0.115, 0.073),
        (0.727, 0, -0.01, 0.143, 0.132, 0.097),
        (0.746, 0, 0.00, 0.153, 0.142, 0.118),
        (0.780, 0, 0.00, 0.157, 0.144, 0.135),
        (0.830, 0, 0.01, 0.160, 0.138, 0.148),
        (0.880, 0, 0.01, 0.157, 0.125, 0.152),
        (0.930, 0, 0.01, 0.146, 0.103, 0.146),
        (0.970, 0, 0.01, 0.122, 0.075, 0.124),
        (1.000, 0, 0.01, 0.078, 0.042, 0.082),
        (1.014, 0, 0.01, 0.020, 0.012, 0.022),
    ]
    head = G.profile_loft("head", prof, C, n=2.25, seg=64, steps=56)
    # Sculpt-like shaping from the landmarks: eye sockets, full low cheeks, button nose, soft chin.
    for sx in (1, -1):
        G.brush(head, (sx * EYE_X, -0.15, Z["eye"]), 0.050, (0, 0.016, 0))
        G.brush(head, (sx * 0.096, -0.11, 0.728), 0.060, (sx * 0.010, -0.012, -0.004))
    G.brush(head, (0, -0.15, Z["nose"]), 0.016, (0, -0.010, 0.0), power=1.5)
    G.brush(head, (0, -0.13, 0.702), 0.036, (0, -0.006, 0.002))
    G.add_mod(head, "SUBSURF", levels=1, render_levels=2)
    G.assign(head, M["skin"])
    neck = G.profile_loft("neck", [(0.600, 0, 0.0, 0.046, 0.044, 0.044), (0.700, 0, 0.0, 0.046, 0.044, 0.044)], C,
                          n=2.0, seg=24, steps=4)
    G.assign(neck, M["skin"])
    return head, neck


def face_y(head, x, z):
    p, _ = G.surface_point(head, (x, -1.0, z), (0, 1, 0))
    return p.y if p is not None else -0.14


def build_ears(C, M, head):
    ears = []
    for sx in (1, -1):
        e = G.uv_sphere(f"ear.{'L' if sx > 0 else 'R'}", (0, 0, 0), 1.0, C, 32, 16, (0.016, 0.030, 0.040))
        e.location = (sx * 0.160, -0.010, Z["ear"])
        e.rotation_euler = (math.radians(-10), 0, math.radians(sx * 22))
        bpy.context.view_layer.update()
        G.brush(e, (sx * 0.178, -0.022, Z["ear"] - 0.002), 0.024, (-sx * 0.008, 0.004, 0))  # inner bowl
        G.add_mod(e, "SUBSURF", levels=1, render_levels=2)
        G.assign(e, M["ear"])
        ears.append(e)
    return ears


def build_eyes(C, M, head):
    """Eyeballs set in sockets, half-closed upper lids with a thick lash line, soft lower lids."""
    eyes, lids, lms = [], [], {}
    for sx, side in ((1, "L"), (-1, "R")):
        x = sx * EYE_X
        fy = face_y(head, x, Z["eye"])
        c = Vector((x, fy + EYE_R - 0.019, Z["eye"]))
        eye = G.uv_sphere(f"eye.{side}", (0, 0, 0), EYE_R, C, 48, 24)
        eye.location = c
        G.assign(eye, M["eye"])
        eyes.append(eye)
        # Upper lid: shell above a nearly horizontal plane just above the eye centre (covers ~40-45% of the iris).
        up = G.uv_sphere(f"lid_upper.{side}", c, EYE_R + 0.0035, C, 64, 32)
        G.cut_by_plane(up, c + Vector((0, 0, 0.004)), (0, -0.18, 1.0), keep_positive=True)
        G.add_mod(up, "SOLIDIFY", thickness=0.0025, offset=1.0)
        lo = G.uv_sphere(f"lid_lower.{side}", c, EYE_R + 0.0012, C, 64, 32)
        # Lower lid: the edge dips in the middle (plane leans forward), at about the bottom of the iris.
        G.cut_by_plane(lo, c + Vector((0, 0, -0.017)), (0, 0.30, -1.0), keep_positive=True)
        G.add_mod(lo, "SOLIDIFY", thickness=0.0012, offset=1.0)
        for o in (up, lo):
            G.assign(o, M["skin"])
        # Lash line along the front of the upper-lid edge, slightly thicker towards the outer corner.
        rr = EYE_R + 0.0045
        pts, w = [], []
        dz = 0.004
        for k in range(15):
            a = math.radians(-78 + 156 * k / 14)  # around the eye's forward axis, front arc
            r_h = math.sqrt(max(rr * rr - dz * dz, 1e-8))
            px, py = math.sin(a) * r_h, -math.cos(a) * r_h
            pz = dz + 0.18 * py  # on the lid plane: z = dz + 0.18 * y (the plane leans back)
            pts.append(c + Vector((px, py - 0.0006, pz + 0.0004)))
            outer = (px * sx) > 0
            w.append(0.0022 + (0.0016 * (k / 14) if sx > 0 else 0.0016 * (1 - k / 14)))
        lash = G.tube(f"lash.{side}", pts, w, [0.0018] * len(pts), C, up_hint=(0, 0, 1), seg=10, cap_start="round", cap_end="round")
        G.assign(lash, M["lash"])
        lids.append((up, lo, lash, c))
        # Landmark = centre of the visible eye opening (between lid edge and lower lid), as annotated on the references.
        lms[f"eye_{side}"] = c + Vector((0, -EYE_R, -0.0065))
    return eyes, lids, lms


def build_brows_mouth(C, M, head):
    brows = []
    for sx, side in ((1, "L"), (-1, "R")):
        pts = []
        for k in range(5):
            t = k / 4
            x = sx * (0.045 + 0.055 * t)
            z = Z["brow"] - 0.004 + 0.008 * math.sin(math.pi * t) - 0.004 * (1 - t)  # inner end lower (sulky)
            y = face_y(head, x, z) - 0.002
            pts.append((x, y, z))
        b = G.tube(f"brow.{side}", pts, [0.0022, 0.0030, 0.0030, 0.0026, 0.0018], [0.0016] * 5, C, up_hint=(0, -1, 0), seg=10)
        G.assign(b, M["brow"])
        brows.append(b)
    # Mouth: a thin closed patch on the face following a small frown; shape keys open/curve it.
    def arcs(curve_up, half_open_top, half_open_bot, width=0.0125):
        top, bot = [], []
        for k in range(11):
            u = -1 + 2 * k / 10
            x = u * width
            zc = Z["mouth"] + curve_up * (u * u) - 0.0005
            env = math.sqrt(max(1 - u * u, 0))
            top.append((x, zc + 0.0008 + half_open_top * env))
            bot.append((x, zc - 0.0008 - half_open_bot * env))
        return top, bot

    def patch_verts(top, bot):
        vs = []
        for row in (top, [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(top, bot)], bot):
            for x, z in row:
                vs.append((x, face_y(head, x, z) - 0.0012, z))
        return vs

    top, bot = arcs(-0.0035, 0.0, 0.0)  # frown: corners down
    verts = patch_verts(top, bot)
    n = len(top)
    faces = [(r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i) for r in range(2) for i in range(n - 1)]
    mouth = G.new_object("mouth", verts, faces, C)
    G.assign(mouth, M["mouth"])
    mouth.shape_key_add(name="Basis")
    for name, args in (("Smile", (0.0045, 0.0, 0.0)), ("JawOpen", (-0.001, 0.0035, 0.0085))):
        k = mouth.shape_key_add(name=name)
        k.value = 0.0
        for i, v in enumerate(patch_verts(*arcs(*args))):
            k.data[i].co = v
    return brows, mouth


# ============================================================================== hair
HAIR_C = Vector((0.0, 0.020, 0.880))
HAIR_R = Vector((0.176, 0.182, 0.168))


def on_hair(az, el, lift=0.0):
    """Point and outward normal on the hair base ellipsoid; az 0 = front (-Y), 90 = his left (+X); el above centre."""
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    p = HAIR_C + Vector((d.x * HAIR_R.x, d.y * HAIR_R.y, d.z * HAIR_R.z))
    n = Vector((d.x / HAIR_R.x, d.y / HAIR_R.y, d.z / HAIR_R.z)).normalized()
    return p + n * lift, n


def clump(name, C, root, mid, tip, width, thick, up_hint, steps=12, tip_frac=0.28):
    """Thick, soft felted clump: rounded cross-section, swelling in the middle, blunt rounded tip (#21)."""
    pts = G.bezier(root, mid, tip, steps)
    ws, ts = [], []
    for i in range(steps):
        t = i / (steps - 1)
        bulge = 1.0 + 0.35 * math.sin(math.pi * min(1.0, t * 1.3))
        taper = 1 - (1 - tip_frac) * t ** 1.5
        ws.append(0.5 * width * bulge * taper)
        ts.append(0.5 * thick * bulge * taper)
    return G.tube(name, pts, ws, ts, C, up_hint=up_hint, n=2.0, seg=16, cap_start="round", cap_end="round")


def build_hair(C, M, head, rng):
    """Big soft volume of thick felted clumps over a hair mass (#21): irregular fringe chunks to the brows, upward
    crown tufts, side clusters flaring to the measured width (±0.21 m), layered back clumps to the nape."""
    import random
    import bmesh
    R = random.Random(11)
    mass = G.uv_sphere("hair_mass", HAIR_C + Vector((0, 0.006, -0.006)), 1.0, C, 48, 24,
                       tuple(HAIR_R - Vector((0.022, 0.022, 0.022))))  # base under the clumps
    bm = bmesh.new()
    bm.from_mesh(mass.data)
    kill = [f for f in bm.faces if f.calc_center_median().y < -0.05 and f.calc_center_median().z < 0.955]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(mass.data)
    bm.free()
    G.displace_noise(mass, 0.008, 0.035, subdiv=1)
    clumps = []

    def add(name, root, mid, tip, width, thick, n, tip_frac=0.28):
        clumps.append(clump(name, C, root, mid, tip, width, thick, n, tip_frac=tip_frac))

    # Fringe: 7 irregular chunks from the hairline (~z 0.93) down to the brows; the centre one reaches between the eyes.
    xs = [-0.125, -0.085, -0.044, -0.004, 0.038, 0.080, 0.122]
    tips = [0.838, 0.826, 0.814, 0.802, 0.818, 0.828, 0.842]
    for k, (xt, zt) in enumerate(zip(xs, tips)):
        xt += R.uniform(-0.006, 0.006)
        zt += R.uniform(-0.006, 0.006)
        az = math.degrees(math.atan2(xt, 0.16)) * 1.25
        root, n = on_hair(az, 22 + R.uniform(-4, 4), 0.004)
        yt = face_y(head, xt, zt) - 0.020
        tip = Vector((xt * 1.04, yt, zt))
        mid = (root + tip) / 2 + n * 0.022 + Vector((0, -0.010, 0.0))
        add(f"hair.fringe.{k}", root, mid, tip, R.uniform(0.060, 0.072), R.uniform(0.036, 0.044), n, tip_frac=0.32)
    # Crown: big upward tufts alternating with smaller outward ones (the spiky top of #7/#21).
    for k in range(8):
        az = -160 + 320 * (k + R.uniform(0.25, 0.75)) / 8
        big = k % 2 == 0
        root, n = on_hair(az, (72 if big else 60) + R.uniform(-5, 5), -0.006)
        dirv = (n * (0.45 if big else 0.8) + Vector((0, 0, 1)) * (0.9 if big else 0.55)).normalized()
        L = R.uniform(0.045, 0.065) if big else R.uniform(0.035, 0.050)
        tip = root + dirv * L + Vector((R.uniform(-0.02, 0.02), R.uniform(-0.02, 0.02), 0))
        mid = root + dirv * L * 0.5 + n * 0.008
        add(f"hair.crown.{k}", root, mid, tip, R.uniform(0.050, 0.066), R.uniform(0.038, 0.048), n, tip_frac=0.30)
    # Centre of the crown: tufts radiating from the top so no base shows through.
    for k in range(7):
        az = -180 + 360 * (k + R.uniform(0.2, 0.8)) / 7
        root, n = on_hair(az + 180, 86, -0.004)
        tip, tn = on_hair(az + R.uniform(-15, 15), 62 + R.uniform(-6, 6), 0.035)
        mid = (root + tip) / 2 + (n + tn).normalized() * 0.035
        add(f"hair.centre.{k}", root, mid, tip, R.uniform(0.066, 0.080), R.uniform(0.046, 0.056), (n + tn).normalized(), tip_frac=0.35)
    # Top layer: short lumpy tufts all over the top, ends lifting outwards.
    for k in range(16):
        az = -180 + 360 * (k + R.uniform(0.2, 0.8)) / 16
        root, n = on_hair(az, 70 + R.uniform(-8, 8), -0.004)
        tip, tn = on_hair(az + R.uniform(-12, 12), 46 + R.uniform(-8, 6), 0.035)
        mid = (root + tip) / 2 + (n + tn).normalized() * 0.030
        add(f"hair.top.{k}", root, mid, tip, R.uniform(0.064, 0.078), R.uniform(0.044, 0.054), (n + tn).normalized(), tip_frac=0.35)
    # Sides: clusters flaring outwards to the measured width ±0.21 m.
    for sx in (1, -1):
        for row, (el0, el1, cnt, reach, lift) in enumerate(((48, 22, 5, (0.170, 0.184), 0.030), (28, 2, 5, (0.168, 0.180), 0.028),
                                                            (10, -14, 4, (0.160, 0.172), 0.022))):
            for k in range(cnt):
                az = sx * (48 + 80 * (k + R.uniform(0.2, 0.8)) / cnt)
                root, n = on_hair(az, el0 + R.uniform(-5, 5), -0.004)
                tip, tn = on_hair(az + sx * R.uniform(-4, 12), el1 + R.uniform(-6, 6), lift)
                tip.x = sx * max(abs(tip.x), R.uniform(*reach))
                mid = (root + tip) / 2 + n * 0.030
                add(f"hair.side{'L' if sx > 0 else 'R'}{row}.{k}", root, mid, tip, R.uniform(0.062, 0.076),
                    R.uniform(0.042, 0.052), n, tip_frac=0.33)
    # Back: three layers of lumpy clumps to the nape, ends lifting slightly.
    for row, (el0, el1, cnt, lift) in enumerate(((60, 30, 9, 0.032), (34, 4, 10, 0.030), (8, -30, 10, 0.024), (-12, -58, 9, 0.018))):
        for k in range(cnt):
            az = 180 + (-100 + 200 * (k + R.uniform(0.2, 0.8)) / cnt)
            root, n = on_hair(az, el0 + R.uniform(-5, 5), -0.004)
            tip, tn = on_hair(az + R.uniform(-10, 10), el1 + R.uniform(-6, 4), lift)
            mid = (root + tip) / 2 + n * 0.030
            add(f"hair.back{row}.{k}", root, mid, tip, R.uniform(0.064, 0.078), R.uniform(0.044, 0.054), n, tip_frac=0.33)
    for c in clumps:
        G.displace_noise(c, 0.005, 0.016, subdiv=1)
    hair = G.join(clumps, "hair_clumps")
    # A few thin stray strands on top (#7, #24).
    strays = []
    for k, (az, el) in enumerate(((-30, 82), (40, 78), (150, 76))):
        root, n = on_hair(az, el, 0.02)
        tip = root + (n * 0.6 + Vector((R.uniform(-0.4, 0.4), R.uniform(-0.4, 0.4), 0.6))).normalized() * 0.05
        mid = (root + tip) / 2 + Vector((R.uniform(-0.015, 0.015), 0, 0.012))
        strays.append(G.tube(f"hair_stray.{k}", G.bezier(root, mid, tip, 8), [0.0022] * 8, [0.0022] * 8, C, seg=8))
    stray = G.join(strays, "hair_strays")
    for o in (mass, hair, stray):
        G.assign(o, M["hair"])
    return [mass, hair, stray]


# ============================================================================== body, clothes, accessories
SHOULDER = 0.118


def arm_points(sx, angle_deg=45.0):
    d = Vector((sx * math.sin(math.radians(angle_deg)), 0.0, -math.cos(math.radians(angle_deg))))
    S = Vector((sx * SHOULDER, 0.0, 0.618))
    E = S + d * 0.120 + Vector((0, 0.008, 0))
    W = E + d * 0.112
    return S, E, W, d


def build_hoodie(C, M):
    parts = {}
    prof = [
        (0.372, 0, 0.004, 0.126, 0.104, 0.088),
        (0.400, 0, 0.004, 0.130, 0.108, 0.090),
        (0.470, 0, 0.003, 0.131, 0.110, 0.090),
        (0.540, 0, 0.000, 0.128, 0.104, 0.090),
        (0.600, 0, 0.000, 0.121, 0.097, 0.090),
        (0.635, 0, 0.000, 0.110, 0.090, 0.088),
        (0.656, 0, 0.002, 0.090, 0.077, 0.080),
        (0.672, 0, 0.004, 0.058, 0.055, 0.060),
    ]
    torso = G.profile_loft("hoodie_torso", prof, C, n=2.3, seg=64, steps=36)
    parts["torso"] = torso
    # Ribbed hem band.
    rings = []
    for z in (0.352, 0.360, 0.384, 0.392):
        grow = 0.006 if 0.355 < z < 0.39 else 0.0
        ring = G.superellipse_ring(0, 0.004, z, 0.126 + grow, 0.104 + grow, 0.088 + grow, 2.3, 96)
        ring = [(x * (1 + 0.012 * (i % 2)), y * (1 + 0.012 * (i % 2)), zz) for i, (x, y, zz) in enumerate(ring)]
        rings.append(ring)
    parts["hem"] = G.loft("hoodie_hem", rings, C)
    # Sleeves (A-pose) with ribbed cuffs.
    for sx, side in ((1, "L"), (-1, "R")):
        S, E, W, d = arm_points(sx)
        pts = G.bezier(S - d * 0.035 + Vector((0, 0, 0.012)), E, W, 14)
        r = [0.056, 0.057, 0.056, 0.054, 0.053, 0.052, 0.051, 0.050, 0.050, 0.049, 0.049, 0.048, 0.047, 0.046]
        parts[f"sleeve.{side}"] = G.tube(f"hoodie_sleeve.{side}", pts, r, [x * 0.95 for x in r], C, up_hint=(0, -1, 0), seg=32,
                                        cap_start="round", cap_end="flat")
        cpts = [W - d * 0.006, W + d * 0.012, W + d * 0.022]
        cuff = G.tube(f"hoodie_cuff.{side}", cpts, [0.047, 0.045, 0.043], [0.046, 0.044, 0.042], C, up_hint=(0, -1, 0), seg=64,
                      cap_start=None, cap_end=None)
        for i, v in enumerate(cuff.data.vertices):  # ribs
            cen = Vector(cpts[min(i // 64, 2)])
            v.co = cen + (v.co - cen) * (1.0 + 0.03 * ((i % 64) % 2))
        parts[f"cuff.{side}"] = cuff
    # Hood: collar roll forming a V at the front, and the hood lying on the upper back.
    path = [(0.024, -0.090, 0.626), (0.050, -0.072, 0.650), (0.075, -0.035, 0.668), (0.082, 0.020, 0.680),
            (0.064, 0.068, 0.690), (0.030, 0.092, 0.695), (0.0, 0.098, 0.696)]
    full = path + [(-x, y, z) for x, y, z in reversed(path[:-1])]
    rw = [0.020, 0.026, 0.030, 0.032, 0.033, 0.034, 0.034] + [0.034, 0.033, 0.032, 0.030, 0.026, 0.020][::-1][::-1]
    rw = rw[:len(full)]
    parts["hood_roll"] = G.tube("hood_roll", full, rw, [w * 0.85 for w in rw], C, up_hint=(0, 0, 1), seg=24)
    back = G.uv_sphere("hood_back", (0, 0.098, 0.630), 1.0, C, 32, 16, (0.098, 0.040, 0.075))
    G.brush(back, (0, 0.06, 0.70), 0.06, (0, 0.012, 0.012))
    parts["hood_back"] = back
    # Kangaroo pocket on the belly (shrinkwrapped panel with thickness).
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=12, size=1.0)
    pk = bpy.context.object
    pk.name = "hoodie_pocket"
    for v in pk.data.vertices:  # rounded trapezoid in XZ, wider at the bottom
        u, w = v.co.x, v.co.y
        z = 0.465 + w * 0.085
        half = 0.088 - 0.012 * (w + 0.5)
        v.co = Vector((u * 2 * half, -0.3, z))
    for c in list(bpy.context.view_layer.objects.active.users_collection):
        c.objects.unlink(pk)
    C.objects.link(pk)
    sw = pk.modifiers.new("shrink", "SHRINKWRAP")
    sw.target = torso
    sw.wrap_method = "PROJECT"
    sw.use_project_y = True
    sw.use_negative_direction = True
    sw.use_positive_direction = True
    sw.offset = 0.004
    G.add_mod(pk, "SOLIDIFY", thickness=0.007, offset=-1.0)
    G.add_mod(pk, "SUBSURF", levels=1, render_levels=1)
    parts["pocket"] = pk
    for p in parts.values():
        G.assign(p, M["hoodie"])
    # Cream undershirt collar in the V, drawstrings with darker tips.
    tee = G.uv_sphere("undershirt", (0, -0.072, 0.648), 1.0, C, 24, 12, (0.030, 0.012, 0.020))
    G.assign(tee, M["cream"])
    cords = []
    for sx in (1, -1):
        pts = [(sx * 0.020, -0.094, 0.640), (sx * 0.023, -0.108, 0.600), (sx * 0.025, -0.113, 0.555)]
        cd = G.tube(f"drawstring.{'L' if sx > 0 else 'R'}", G.bezier(*pts, 8), [0.0042] * 8, [0.0042] * 8, C, seg=12)
        G.assign(cd, M["cream"])
        tip = G.tube(f"drawstring_tip.{'L' if sx > 0 else 'R'}", [(sx * 0.025, -0.113, 0.556), (sx * 0.025, -0.114, 0.538)],
                     [0.0046, 0.0044], [0.0046, 0.0044], C, seg=12)
        G.assign(tip, M["cord_tip"])
        cords += [cd, tip]
    return parts, [tee] + cords


def build_hands(C, M):
    hands = {}
    for sx, side in ((1, "L"), (-1, "R")):
        S, E, W, d = arm_points(sx)
        palm_n = Vector((-sx * 0.707, 0.0, -0.707)).normalized()  # palm faces down/in, towards the body
        side_v = d.cross(palm_n).normalized()  # across the knuckles
        base = W + d * 0.018
        pieces = [G.uv_sphere(f"palm.{side}", base + d * 0.022, 1.0, C, 24, 12, (0.036, 0.036, 0.036))]
        pieces[0].scale = (1, 1, 1)
        # Scale the palm sphere into a soft box along the hand frame.
        R = Matrix((side_v, palm_n, d)).transposed()
        for v in pieces[0].data.vertices:
            loc = v.co - (base + d * 0.022)
            loc = R.inverted() @ loc
            loc = Vector((loc.x * 0.85, loc.y * 0.55, loc.z * 1.0))
            v.co = (base + d * 0.022) + R @ loc
        fingers = []
        for k, off in enumerate((-0.019, -0.0065, 0.0065, 0.019)):
            root = base + d * 0.044 + side_v * off * sx
            L = (0.018, 0.021, 0.020, 0.016)[k]  # short, chubby fingers (#7, #24, #27)
            tip = root + d * L + palm_n * 0.004
            fingers.append(G.tube(f"finger{k}.{side}", [root, (root + tip) / 2, tip], [0.0098, 0.0096, 0.0090],
                                  [0.0094, 0.0092, 0.0086], C, up_hint=tuple(palm_n), seg=12))
        troot = base + d * 0.016 + side_v * (-0.026 * sx) + palm_n * 0.008
        ttip = troot + d * 0.020 + side_v * (-0.010 * sx) + palm_n * 0.010
        fingers.append(G.tube(f"thumb.{side}", [troot, (troot + ttip) / 2, ttip], [0.0105, 0.0100, 0.0092],
                              [0.0100, 0.0096, 0.0088], C, up_hint=tuple(palm_n), seg=12))
        hand = G.join(pieces + fingers, f"hand.{side}")
        G.voxel_remesh(hand, 0.0022, smooth_iter=4)
        G.assign(hand, M["skin"])
        hands[side] = hand
    return hands


def build_legs(C, M):
    parts = []
    waist = G.profile_loft("trousers_waist", [(0.320, 0, 0.004, 0.118, 0.090, 0.082), (0.420, 0, 0.004, 0.120, 0.095, 0.085)], C,
                           n=2.3, seg=48, steps=6)
    parts.append(waist)
    for sx, side in ((1, "L"), (-1, "R")):
        x = sx * 0.060
        pts = [(x, 0.0, 0.372), (x, 0.0, 0.300), (sx * 0.0605, -0.004, 0.230), (sx * 0.061, -0.002, 0.170), (sx * 0.061, 0.0, 0.140),
               (sx * 0.061, 0.0, 0.124), (sx * 0.061, 0.0, 0.112)]
        w = [0.062, 0.063, 0.061, 0.060, 0.061, 0.052, 0.046]
        leg = G.tube(f"trouser_leg.{side}", pts, w, [v * 0.98 for v in w], C, up_hint=(0, -1, 0), seg=40, cap_start="flat", cap_end="flat")
        parts.append(leg)
    for p in parts:
        G.assign(p, M["trousers"])
    socks = []
    for sx, side in ((1, "L"), (-1, "R")):
        s = G.tube(f"sock.{side}", [(sx * 0.064, 0.012, 0.070), (sx * 0.064, 0.010, 0.128)], [0.040, 0.041], [0.040, 0.041], C,
                   seg=24, cap_start="flat", cap_end="flat")
        G.assign(s, M["sock"])
        socks.append(s)
    return parts, socks


def build_shoes(C, M):
    shoes, extras = [], []
    prof = [(-0.140, 0.040, 0.030), (-0.125, 0.056, 0.050), (-0.095, 0.064, 0.066), (-0.050, 0.066, 0.080),
            (0.000, 0.064, 0.086), (0.040, 0.060, 0.084), (0.062, 0.050, 0.074), (0.072, 0.034, 0.058)]
    for sx, side in ((1, "L"), (-1, "R")):
        cx = sx * 0.072
        rings = []
        for k in range(29):
            y = prof[0][0] + (prof[-1][0] - prof[0][0]) * k / 28
            w, h = G.interp_profile(prof, y)
            ring = []
            for i in range(40):
                t = 2 * math.pi * i / 40
                c, s = math.cos(t), math.sin(t)
                xx = cx + w * math.copysign(abs(c) ** (2 / 3.0), c)
                zz = 0.022 + h / 2 + (h / 2) * math.copysign(abs(s) ** (2 / 2.4), s)
                ring.append((xx, y, max(zz, 0.020)))
            rings.append(ring)
        body = G.loft(f"shoe.{side}", rings, C)
        G.assign(body, M["shoe"])
        body.data.materials.append(M["sole"])  # toe cap in cream
        for poly in body.data.polygons:
            if poly.center.y < -0.085 and poly.center.z < 0.075:
                poly.material_index = 1
        G.add_mod(body, "SUBSURF", levels=1, render_levels=2)
        shoes.append(body)
        sole_rings = []
        for k in range(29):
            y = prof[0][0] - 0.004 + (prof[-1][0] - prof[0][0] + 0.008) * k / 28
            w, _ = G.interp_profile(prof, y)
            sole_rings.append(G.superellipse_ring(cx, y, 0.0, w + 0.004, 1e-4, 1e-4, 3.0, 32))
        # Build the sole as a flat slab from outline rings.
        outline = [G.superellipse_ring(cx, 0, 0, 1, 1, 1, 2, 4)]
        sole = G.profile_loft(f"sole.{side}", [(0.0, cx, -0.034, 0.070, 0.112, 0.112), (0.026, cx, -0.034, 0.070, 0.112, 0.112)], C,
                              n=3.2, seg=48, steps=3)
        for v in sole.data.vertices:
            v.co.y = max(min(v.co.y, 0.078), -0.147)
        G.add_mod(sole, "SUBSURF", levels=1, render_levels=1)
        G.assign(sole, M["sole"])
        extras.append(sole)
        for j, yy in enumerate((-0.050, -0.020)):
            pts = []
            for k in range(9):
                xx = cx + sx * (-0.060 + 0.120 * k / 8) * 1.0
                top, _ = G.surface_point(body, (xx, yy, 0.3), (0, 0, -1))
                pts.append((xx, yy, (top.z if top is not None else 0.1) + 0.0025))
            st = G.tube(f"shoe_strap{j}.{side}", pts, [0.0075] * 9, [0.0028] * 9, C, up_hint=(0, 0, 1), seg=12)
            G.assign(st, M["sole"])
            extras.append(st)
    return shoes, extras


def build_backpack(C, M, torso):
    prof = [(0.420, 0, 0.140, 0.080, 0.035, 0.030), (0.440, 0, 0.140, 0.102, 0.045, 0.040), (0.600, 0, 0.140, 0.104, 0.046, 0.042),
            (0.630, 0, 0.138, 0.090, 0.042, 0.038), (0.648, 0, 0.136, 0.050, 0.028, 0.026)]
    body = G.profile_loft("backpack_body", prof, C, n=4.0, seg=48, steps=24)
    pocket = G.profile_loft("backpack_pocket", [(0.445, 0, 0.183, 0.066, 0.012, 0.024), (0.540, 0, 0.183, 0.072, 0.012, 0.026),
                                                (0.552, 0, 0.181, 0.060, 0.010, 0.020)], C, n=4.0, seg=40, steps=10)
    handle = G.tube("backpack_handle", G.bezier((-0.025, 0.140, 0.640), (0.0, 0.140, 0.680), (0.025, 0.140, 0.640), 10),
                    [0.006] * 10, [0.004] * 10, C, seg=10)
    for o in (body, pocket):
        G.add_mod(o, "SUBSURF", levels=1, render_levels=2)
        G.assign(o, M["pack"])
    G.assign(handle, M["webbing"])
    straps = []
    for sx, side in ((1, "L"), (-1, "R")):
        # Over the shoulder, then straight down the chest sides just inside the arms (#7, #24, #27), to the side seam.
        path = [(sx * 0.066, 0.110, 0.620), (sx * 0.080, 0.050, 0.664), (sx * 0.088, -0.020, 0.666), (sx * 0.096, -0.070, 0.640),
                (sx * 0.100, -0.090, 0.600), (sx * 0.103, -0.095, 0.550), (sx * 0.106, -0.095, 0.500), (sx * 0.114, -0.080, 0.462),
                (sx * 0.124, -0.020, 0.452), (sx * 0.112, 0.060, 0.448), (sx * 0.080, 0.110, 0.450)]
        pts = []
        for p in path:  # follow the hoodie surface: front points projected along +Y, back points along -Y
            p = Vector(p)
            if p.z < 0.645 and abs(p.y) > 0.04:
                sgn = -1.0 if p.y < 0 else 1.0
                hit, _ = G.surface_point(torso, (p.x, sgn * 1.0, p.z), (0, -sgn, 0), 2.0)
                pts.append(hit + Vector((0, sgn * 0.006, 0)) if hit is not None else p)
            else:
                pts.append(p)
        st = G.tube(f"backpack_strap.{side}", pts, [0.011] * len(pts), [0.0028] * len(pts), C, up_hint=(0, 0, 1), seg=12)
        G.assign(st, M["webbing"])
        bk = G.uv_sphere(f"buckle.{side}", (sx * 0.099, -0.111, 0.545), 1.0, C, 12, 8, (0.012, 0.004, 0.008))
        G.assign(bk, M["buckle"])
        straps += [st, bk]
    return [body, pocket, handle], straps


# ============================================================================== landmarks
def add_landmarks(C, lms, head, ears):
    out = dict(lms)
    front = [head.matrix_world @ v.co for v in head.data.vertices]
    low = min((p for p in front if abs(p.x) < 0.02 and p.y < -0.04), key=lambda p: p.z)
    out["chin"] = Vector((0, low.y, low.z))  # lowest visible point of the face
    out["mouth"] = Vector((0, face_y(head, 0, Z["mouth"]), Z["mouth"]))
    out["nose"] = Vector((0, face_y(head, 0, Z["nose"]), Z["nose"]))
    for e, side in zip(ears, ("L", "R")):
        xs = [(e.matrix_world @ v.co).x for v in e.data.vertices]
        x = max(xs) if side == "L" else min(xs)
        out[f"ear_{side}"] = Vector((x, -0.004, Z["ear"]))
    empties = {}
    for k, p in out.items():
        em = bpy.data.objects.new(f"LM_{k}", None)
        em.location = p
        em.empty_display_size = 0.01
        C.objects.link(em)
        empties[k] = em
    return empties


# ============================================================================== rig
def fit_metarig(meta):
    """Places the Rigify human metarig bones on the pilot's measured joints (A-pose); face bones removed."""
    bpy.context.view_layer.objects.active = meta
    bpy.ops.object.mode_set(mode="EDIT")
    eb = meta.data.edit_bones
    face_root = eb.get("face")
    if face_root:
        for b in [face_root] + list(face_root.children_recursive):
            eb.remove(b)
    for n in ("breast.L", "breast.R"):
        if eb.get(n):
            eb.remove(eb[n])
    def put(name, h, t, roll=None):
        b = eb[name]
        b.head, b.tail = Vector(h), Vector(t)
        if roll is not None:
            b.roll = roll
    put("spine", (0, 0.004, 0.360), (0, 0.004, 0.440))
    put("spine.001", (0, 0.004, 0.440), (0, 0.003, 0.520))
    put("spine.002", (0, 0.003, 0.520), (0, 0.002, 0.590))
    put("spine.003", (0, 0.002, 0.590), (0, 0.003, 0.650))
    put("spine.004", (0, 0.003, 0.650), (0, 0.002, 0.678))
    put("spine.005", (0, 0.002, 0.678), (0, 0.0, 0.700))
    put("spine.006", (0, 0.0, 0.700), (0, 0.0, 0.990))
    for sx, s in ((1, "L"), (-1, "R")):
        S, E, W, d = arm_points(sx)
        put(f"shoulder.{s}", (sx * 0.018, -0.006, 0.636), (sx * 0.100, 0.004, 0.630))
        put(f"upper_arm.{s}", S, E)
        put(f"forearm.{s}", E, W)
        put(f"hand.{s}", W, W + d * 0.040)
        palm_n = Vector((-sx * 0.707, 0.0, -0.707)).normalized()
        side_v = d.cross(palm_n).normalized()
        base = W + d * 0.018
        names = (("palm.04", "f_pinky"), ("palm.03", "f_ring"), ("palm.02", "f_middle"), ("palm.01", "f_index"))
        for k, ((palm, fing), off) in enumerate(zip(names, (0.019, 0.0065, -0.0065, -0.019))):
            pr = base + d * 0.006 + side_v * off * sx
            root = base + d * 0.044 + side_v * off * sx
            L = (0.019, 0.024, 0.025, 0.022)[k]
            put(f"{palm}.{s}", pr, root)
            tip = root + d * L + palm_n * 0.004
            put(f"{fing}.01.{s}", root, root + (tip - root) * 0.40)
            put(f"{fing}.02.{s}", root + (tip - root) * 0.40, root + (tip - root) * 0.72)
            put(f"{fing}.03.{s}", root + (tip - root) * 0.72, tip)
        troot = base + d * 0.016 + side_v * (-0.026 * sx) + palm_n * 0.008
        ttip = troot + d * 0.020 + side_v * (-0.010 * sx) + palm_n * 0.010
        put(f"thumb.01.{s}", base + d * 0.004 + side_v * (-0.014 * sx), troot)
        put(f"thumb.02.{s}", troot, troot + (ttip - troot) * 0.5)
        put(f"thumb.03.{s}", troot + (ttip - troot) * 0.5, ttip)
        put(f"pelvis.{s}", (0, 0.004, 0.360), (sx * 0.075, -0.040, 0.420))
        put(f"thigh.{s}", (sx * 0.060, 0.0, 0.350), (sx * 0.061, -0.008, 0.230))
        put(f"shin.{s}", (sx * 0.061, -0.008, 0.230), (sx * 0.064, 0.008, 0.090))
        put(f"foot.{s}", (sx * 0.064, 0.008, 0.090), (sx * 0.066, -0.070, 0.035))
        put(f"toe.{s}", (sx * 0.066, -0.070, 0.035), (sx * 0.066, -0.125, 0.035))
        put(f"heel.02.{s}", (sx * 0.030, 0.050, 0.0), (sx * 0.100, 0.050, 0.0))
        # Eye bone (gaze control): deforms the eyeball.
        e = eb.new(f"eye.{s}")
        e.head = Vector((sx * EYE_X, -0.11, Z["eye"]))
        e.tail = e.head + Vector((0, -0.03, 0))
        e.parent = eb["spine.006"]
    bpy.ops.object.mode_set(mode="OBJECT")
    for s in ("L", "R"):
        pb = meta.pose.bones[f"eye.{s}"]
        pb.rigify_type = "basic.super_copy"
        try:
            pb.rigify_parameters.make_deform = True
        except AttributeError:
            pass


def rig_character(C, objs, rigid):
    import addon_utils
    addon_utils.enable("rigify", default_set=True)
    bpy.ops.object.armature_human_metarig_add()
    meta = bpy.context.object
    meta.name = "metarig"
    fit_metarig(meta)
    t = time.time()
    bpy.ops.pose.rigify_generate()
    rig = bpy.context.object
    rig.name = "rig_boy_yellow_hoodie"
    for coll in list(rig.users_collection):  # keep the rig in the character collection (export, harness)
        coll.objects.unlink(rig)
    C.objects.link(rig)
    report = {"rigify_bones": len(rig.data.bones), "deform_bones": sum(1 for b in rig.data.bones if b.use_deform),
              "generate_s": round(time.time() - t, 1)}
    bpy.data.objects.remove(meta, do_unlink=True)
    # Rigid parts: fixed weights to one deform bone, or a uniform split between bones (used by shared eyelid
    # tracking). No heat weighting is needed.
    t = time.time()
    for ob, bone in rigid:
        ob.parent = rig
        ob.matrix_parent_inverse = rig.matrix_world.inverted()
        for name, weight in (bone.items() if isinstance(bone, dict) else ((bone, 1.0),)):
            vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
            vg.add(list(range(len(ob.data.vertices))), weight, "REPLACE")
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = rig
    # Deforming parts: automatic (heat) weights, then fill unweighted vertices from their nearest weighted neighbour,
    # normalise, limit to 4 influences.
    unweighted_before = unweighted_after = total = 0
    for ob in objs:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        allowed = allowed_bones(ob.name)
        if allowed:  # heat weighting picks up nearby bones of other limbs (e.g. hands next to the hips)
            for vg in list(ob.vertex_groups):
                if not allowed(vg.name):
                    ob.vertex_groups.remove(vg)
        ub, ua = cleanup_weights(ob)
        if ua:  # heat weighting failed silently for this object (e.g. thin open tubes): nearest allowed bone
            ua = bind_to_nearest_bone(ob, rig, allowed)
            report.setdefault("nearest_bone_fallback", []).append(ob.name)
        unweighted_before += ub
        unweighted_after += ua
        total += len(ob.data.vertices)
    report.update({"nearest_bone_fallback": report.get("nearest_bone_fallback", []), "weighted_objects": len(objs), "rigid_objects": len(rigid), "vertices": total,
                   "unweighted_after_heat": unweighted_before, "unweighted_after_cleanup": unweighted_after,
                   "weights_s": round(time.time() - t, 1)})
    return rig, report


def allowed_bones(name):
    """Which deform bones an object may follow (a test on the bone name), or None = any. Heat weighting otherwise
    picks up nearby bones of other limbs (measured: trouser legs followed fingers, straps followed the upper arms)."""
    side = name.rsplit(".", 1)[-1] if name.endswith((".L", ".R")) else None
    spine = lambda b: b.startswith("DEF-spine")
    if name.startswith(("trouser", "sock")):
        return lambda b: spine(b) or b.startswith(("DEF-pelvis", "DEF-thigh", "DEF-shin", "DEF-foot"))
    if name.startswith(("hood_", "neck")):
        return lambda b: spine(b) or b.startswith("DEF-shoulder")
    if name.startswith(("hoodie_torso", "hoodie_hem", "hoodie_pocket")):
        return lambda b: spine(b) or b.startswith(("DEF-shoulder", "DEF-upper_arm", "DEF-pelvis"))
    if name.startswith(("hoodie_sleeve", "hoodie_cuff")) and side:
        return lambda b: b == "DEF-spine.003" or (b.endswith(side) and b.startswith(("DEF-shoulder", "DEF-upper_arm", "DEF-forearm", "DEF-hand")))
    if name.startswith("hand.") and side:
        return lambda b: b.endswith(side) and b.startswith(("DEF-forearm", "DEF-hand", "DEF-f_", "DEF-thumb", "DEF-palm"))
    return None


def bind_to_nearest_bone(ob, rig, allowed):
    """Weights each unweighted vertex 1.0 to the nearest deform bone segment the object may follow."""
    bones = [b for b in rig.data.bones if b.use_deform and (allowed is None or allowed(b.name))]
    segs = [(b.name, rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in bones]
    groups = {g.name: g for g in ob.vertex_groups}
    left = 0
    for v in ob.data.vertices:
        if sum(g.weight for g in v.groups) >= 1e-4:
            continue
        p = ob.matrix_world @ v.co
        best, bd = None, 1e9
        for name, h, t in segs:
            d = t - h
            u = max(0.0, min(1.0, (p - h).dot(d) / max(d.length_squared, 1e-12)))
            dist = (p - (h + d * u)).length
            if dist < bd:
                best, bd = name, dist
        if best is None:
            left += 1
            continue
        g = groups.get(best) or ob.vertex_groups.new(name=best)
        groups[best] = g
        g.add([v.index], 1.0, "REPLACE")
    return left


def cleanup_weights(ob):
    import numpy as np
    me = ob.data
    n = len(me.vertices)
    co = np.array([v.co[:] for v in me.vertices])
    tot = np.array([sum(g.weight for g in v.groups) for v in me.vertices])
    bad = np.nonzero(tot < 1e-4)[0]
    good = np.nonzero(tot >= 1e-4)[0]
    before = len(bad)
    if before and len(good):
        groups = {g.index: g for g in ob.vertex_groups}
        for i in bad:
            j = good[np.argmin(np.sum((co[good] - co[i]) ** 2, axis=1))]
            for g in me.vertices[j].groups:
                groups[g.group].add([int(i)], g.weight, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    after = sum(1 for v in me.vertices if sum(g.weight for g in v.groups) < 1e-4)
    return before, after


def add_expression_keys(lids, brows):
    """Blink on the upper lids (with lashes), BrowDown on the brows. Smile and JawOpen are on the mouth."""
    for up, lo, lash, c in lids:
        for ob in (up, lash):
            G.apply_mods(ob)
            ob.shape_key_add(name="Basis")
            k = ob.shape_key_add(name="Blink")
            k.value = 0.0
            R = Matrix.Rotation(math.radians(62), 3, Vector((1, 0, 0)))  # front edge down over the eye
            for i, v in enumerate(ob.data.vertices):
                k.data[i].co = c + R @ (v.co - c)
    for b in brows:
        b.shape_key_add(name="Basis")
        k = b.shape_key_add(name="BrowDown")
        k.value = 0.0
        xs = [abs(v.co.x) for v in b.data.vertices]
        x0, x1 = min(xs), max(xs)
        for i, v in enumerate(b.data.vertices):
            inner = 1 - (abs(v.co.x) - x0) / max(1e-6, x1 - x0)
            k.data[i].co = v.co + Vector((-math.copysign(0.004, v.co.x) * inner, -0.001, -0.009 * inner - 0.002))


# ============================================================================== main
def main():
    a = parse()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    C = bpy.data.collections.new("boy_yellow_hoodie")
    scene.collection.children.link(C)
    M = make_materials()
    head, neck = build_head(C, M)
    ears = build_ears(C, M, head)
    eyes, lids, lms = build_eyes(C, M, head)
    brows, mouth = build_brows_mouth(C, M, head)
    hair = build_hair(C, M, head, None)
    hoodie, hoodie_bits = build_hoodie(C, M)
    hands = build_hands(C, M)
    trousers, socks = build_legs(C, M)
    shoes, shoe_bits = build_shoes(C, M)
    pack, straps = build_backpack(C, M, hoodie["torso"])
    empties = add_landmarks(C, lms, head, ears)
    report = {"blender": bpy.app.version_string, "stage": a.stage, "height_m": H, "targets_z": Z,
              "model_s": round(time.time() - t0, 1)}
    add_expression_keys(lids, brows)

    # Bake modifiers (except armature) so the master holds final geometry; keep shape-keyed objects as they are.
    for ob in list(C.objects):
        if ob.type == "MESH" and not ob.data.shape_keys and ob.modifiers:
            G.apply_mods(ob)

    head_bone, chest = "DEF-spine.006", "DEF-spine.003"
    rigid = [(o, head_bone) for o in [head] + ears + brows + [mouth] + hair + [l for tup in lids for l in tup[:3]]]
    rigid += [(e, f"DEF-eye.{s}") for e, s in zip(eyes, ("L", "R"))]
    rigid += [(s, f"DEF-foot.{side}") for s, side in zip(shoes, ("L", "R"))]
    rigid += [(o, f"DEF-foot.{'L' if o.name.endswith('.L') else 'R'}") for o in shoe_bits]
    rigid += [(o, chest) for o in pack]
    chest_rigid = [o for o in hoodie_bits + straps]  # undershirt, drawstrings, backpack straps and buckles
    rigid += [(o, chest) for o in chest_rigid]
    deforming = [neck] + list(hoodie.values()) + list(hands.values()) + trousers + socks
    if a.stage == "all":
        rig, rr = rig_character(C, deforming, rigid)
        report["rig"] = rr
        for em in empties.values():  # landmarks follow the head
            em.parent = rig
            em.parent_type = "BONE"
            em.parent_bone = head_bone
            em.matrix_world = Matrix.Translation(em.location)
    fur_specs = [("fur_hair", hair, M["hair_fur"], 420000, (0.004, 0.009), 0.00030, 0.8, 0.15),
                 ("fur_hoodie", list(hoodie.values()), M["hoodie_fur"], 380000, (0.0018, 0.0035), 0.00022, 0.9, 0.0),
                 ("fur_trousers", trousers, M["trousers_fur"], 300000, (0.0015, 0.003), 0.0002, 0.9, 0.0),
                 ("fur_shoes", shoes, M["shoe_fur"], 300000, (0.0012, 0.0024), 0.0002, 0.9, 0.0)]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), "boy_yellow_hoodie_pilot_master.blend"))
    report["master_s"] = round(time.time() - t0, 1)
    if a.stage == "all":  # interchange export of the A-pose master: meshes, deform skeleton, weights, shape keys
        glb = os.path.join(os.path.abspath(a.out), "boy_yellow_hoodie_pilot.glb")
        t = time.time()
        bpy.ops.object.select_all(action="DESELECT")
        for o in C.objects:
            if o.type in ("MESH", "ARMATURE"):
                o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_skins=True, export_morph=True,
                                  export_def_bones=True, export_animations=False, use_selection=True)
        report["gltf"] = {"mb": round(os.path.getsize(glb) / 1e6, 1), "s": round(time.time() - t, 1)}
    if a.stage == "all":
        # Comparison pose: arms down as in reference #27 (FK controls), then fur on the posed surfaces.
        bpy.context.view_layer.objects.active = rig
        for pb in rig.pose.bones:  # Rigify limbs: use FK so the FK controls drive the arms
            if "IK_FK" in pb.keys():
                pb["IK_FK"] = 1.0
        bpy.ops.object.mode_set(mode="POSE")
        for s, sx in (("L", 1), ("R", -1)):
            pb = rig.pose.bones.get(f"upper_arm_fk.{s}")
            if pb is None:
                continue
            head_w = rig.matrix_world @ pb.head
            Rm = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(sx * 41), 4, "Y") @ Matrix.Translation(-head_w)
            pb.matrix = rig.matrix_world.inverted() @ Rm @ rig.matrix_world @ pb.matrix
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
    for name, objs, mat, dens, L, rad, spread, grav in fur_specs:
        G.add_fur(name, objs, C, mat, dens * a.fur_scale, L, rad, spread=spread, gravity=grav, seed=sum(map(ord, name)))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), "boy_yellow_hoodie_pilot_compare.blend"))
    report["landmarks_rest"] = {k: [round(c, 4) for c in v.location] for k, v in empties.items()}
    report["objects"] = sorted(o.name for o in C.objects)
    report["total_s"] = round(time.time() - t0, 1)
    json.dump(report, open(os.path.join(a.out, "build_report.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("objects", "targets_z", "landmarks_rest")}, indent=1))


# ============================================================================== charsys: per-character configuration
def configure(spec):
    """Sets this module's proportion and colour globals from a character spec (identity/proportions/materials).
    The part generators read these globals when called, so configure() must run before building."""
    global H, Z, EYE_X, EYE_R, HAIR_C, HAIR_R, SHOULDER, ALB, COLORS
    p = spec["proportions"]
    H = float(p["height_m"])
    Z = {k: float(v) for k, v in p["z_targets_m"].items()}
    EYE_X, EYE_R = float(p["eye_x_m"]), float(p["eye_radius_m"])
    HAIR_C, HAIR_R = Vector(p["hair_ellipsoid_centre_m"]), Vector(p["hair_ellipsoid_radii_m"])
    SHOULDER = float(p["shoulder_half_width_m"])
    m = spec["materials"]
    ALB = {k: tuple(v) for k, v in m["albedo_srgb"].items()}
    COLORS = {k: tuple(v) for k, v in m["target_colors_srgb"].items()}
