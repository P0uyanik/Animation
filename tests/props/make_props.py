#!/usr/bin/env python3
"""T-163: generates the starter felt prop assets (content/assets/felt_*.asset.json).

Conventions follow felt_cup (T-111/T-112): cylinders stand on their base at the origin with the axis +Y, spheres and
boxes are centred; wrap/pinch sites on round props point the socket +Y along the outward normal (cup: grip on +X has
rotationDeg z -90); box props use rotation 0 and an explicit 'approach' (felt_tray). Every prop has the sockets grip*/
place/contact. Material presets: 'felt' only. Run: python3 tests/props/make_props.py [--check]
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "content/assets"
ONE = [1.0, 1.0, 1.0]
# outward-normal rotations for round props (socket +Y = normal)
RX, LX, RZ, LZ = [0, 0, -90], [0, 0, 90], [90, 0, 0], [-90, 0, 0]


def sock(t, rot=(0, 0, 0)):
    return {"translation": [round(v, 5) for v in t], "rotationDeg": list(rot), "scale": ONE}


def asset(name, attribution, mesh, sockets, collision, aff):
    return {"format": "plush.asset", "version": 1, "id": f"prop.felt_{name}", "licence": "CC0-1.0",
            "attribution": f"Plush Studio project; {attribution}", "mesh": mesh, "material_presets": ["felt"],
            "scale": 1.0, "sockets": sockets, "collision": collision, "affordances": aff}


def aff(size, weight, hands, mass, pivot, tilt, sites, sets, place, handover=None, push=None):
    a = {"format": "plush.affordances", "version": 1, "size_class": size, "weight_class": weight, "mass_kg": mass,
         "hands": hands, "pivot": pivot, "upright": {"axis": [0, 1, 0], "max_tilt_deg": tilt},
         "grasp_sites": sites, "grasp_sets": sets}
    if handover:
        a["handover"] = handover
    a["place"] = place
    if push:
        a["push_pull"] = push
    a["deform"] = {"mode": "rigid"}
    return a


def site(i, socket, shape="wrap", hand="any", **kw):
    d = {"id": i, "socket": socket, "hand": hand, "shape": shape}
    d.update(kw)
    return d


def opp(lo, hi):
    return {"thumb": "opposed", "band": [lo, hi]}


def sets(*ids):
    return [{"id": i, "sites": s} for i, s in ids]


def place(sock_="place", settle="rigid"):
    return {"socket": sock_, "surface_normal": [0, 1, 0], "settle": settle}


def cap(r, h, y):  # capsule proxy over a base-origin cylinder
    return {"type": "capsule", "radius": r, "height": h, "transform": sock([0, y, 0])}


def boxc(size, y=0.0):
    return {"type": "box", "size": size, "transform": sock([0, y, 0])}


P = {}

# --- round props with side grips (cup pattern: a = upper side for the giver, b = lower opposite side for the receiver)
def side_pair(r, ya, yb):
    return {"grip": sock([r, ya, 0], RX), "grip_b": sock([-r, yb, 0], LX)}

P["bowl"] = asset("bowl", "generated from a cylinder primitive (stands on its base at the origin, axis +Y)",
    {"primitive": "cylinder", "radius": 0.06, "height": 0.05, "open_top": True, "wall": 0.005},
    {**side_pair(0.06, 0.035, 0.015), "place": sock([0, 0, 0]), "contact": sock([0, 0.05, 0])},
    boxc([0.12, 0.05, 0.12], 0.025),
    aff("small", "light", "one", 0.12, "place", 25,
        [site("side_a", "grip", "wrap", turnable=True, fingers=opp(0.02, 0.05)),
         site("side_b", "grip_b", "wrap", turnable=True, fingers=opp(0.0, 0.03))],
        sets(("a", ["side_a"]), ("b", ["side_b"])), place(settle="soft"), {"give": ["a"], "receive": ["b"]}))

P["toy"] = asset("toy", "a stubby standing felt doll generated from a cylinder primitive (base at the origin, axis +Y)",
    {"primitive": "cylinder", "radius": 0.03, "height": 0.10},
    {**side_pair(0.03, 0.065, 0.035), "place": sock([0, 0, 0]), "contact": sock([0, 0.10, 0])},
    cap(0.03, 0.10, 0.05),
    aff("small", "light", "one", 0.06, "place", 180,
        [site("torso_a", "grip", "wrap", turnable=True, fingers=opp(0.045, 0.085)),
         site("torso_b", "grip_b", "wrap", turnable=True, fingers=opp(0.015, 0.055))],
        sets(("a", ["torso_a"]), ("b", ["torso_b"])), place(settle="soft"), {"give": ["a"], "receive": ["b"]}))

P["basket"] = asset("basket", "generated from a cylinder primitive (base at the origin, axis +Y); two-handed rim carry",
    {"primitive": "cylinder", "radius": 0.09, "height": 0.07, "open_top": True, "wall": 0.006},
    {"rim_l": sock([-0.09, 0.06, 0], LX), "rim_r": sock([0.09, 0.06, 0], RX),
     "place": sock([0, 0, 0]), "contact": sock([0, 0.07, 0])},
    boxc([0.18, 0.07, 0.18], 0.035),
    aff("large", "medium", "two", 0.35, "place", 12,
        [site("rim_l", "rim_l", "hook", "L", approach=[-1, 0, 0]), site("rim_r", "rim_r", "hook", "R", approach=[1, 0, 0])],
        [{"id": "both_rims", "sites": ["rim_l", "rim_r"], "simultaneous_frames": 2}], place()))

P["plate"] = asset("plate", "generated from a cylinder primitive (base at the origin, axis +Y)",
    {"primitive": "cylinder", "radius": 0.09, "height": 0.012},
    {"grip": sock([0.09, 0.006, 0], RX), "grip_b": sock([-0.09, 0.006, 0], LX),
     "place": sock([0, 0, 0]), "contact": sock([0, 0.012, 0])},
    boxc([0.18, 0.012, 0.18], 0.006),
    aff("medium", "light", "either", 0.1, "place", 10,
        [site("rim_a", "grip", "pinch", aperture=0.012), site("rim_b", "grip_b", "pinch", aperture=0.012)],
        sets(("a", ["rim_a"]), ("b", ["rim_b"])), place(), {"give": ["a"], "receive": ["b"]}))

P["pencil"] = asset("pencil", "generated from a cylinder primitive (stands on its base at the origin, axis +Y)",
    {"primitive": "cylinder", "radius": 0.006, "height": 0.17},
    {"grip": sock([0.006, 0.09, 0], RX), "grip_b": sock([-0.006, 0.05, 0], LX),
     "place": sock([0, 0, 0]), "contact": sock([0, 0.17, 0])},
    cap(0.006, 0.17, 0.085),
    aff("hand", "light", "one", 0.01, "place", 90,
        [site("pinch_a", "grip", "pinch", aperture=0.012), site("pinch_b", "grip_b", "pinch", aperture=0.012)],
        sets(("a", ["pinch_a"]), ("b", ["pinch_b"])), place(), {"give": ["a"], "receive": ["b"]}))

# --- spheres (centred)
def sphere(name, r, mass, stem):
    s = {"grip": sock([r, 0, 0], RX), "grip_b": sock([-r, 0, 0], LX),
         "place": sock([0, -r, 0]), "contact": sock([0, r, 0])}
    sites = [site("side_a", "grip", "wrap", turnable=True, fingers=opp(-0.5 * r, 0.5 * r)),
             site("side_b", "grip_b", "wrap", turnable=True, fingers=opp(-0.5 * r, 0.5 * r))]
    st = sets(("a", ["side_a"]), ("b", ["side_b"]))
    if stem:
        s["stem"] = sock([0, r, 0])
        sites.append(site("stem", "stem", "pinch", aperture=0.01, approach=[0, 1, 0]))
        st.append({"id": "stem", "sites": ["stem"]})
    return asset(name, "generated from a sphere primitive (centred)", {"primitive": "sphere", "radius": r}, s,
                 {"type": "sphere", "radius": r},
                 aff("small", "light", "one", mass, [0, 0, 0], 180, sites, st, place(settle="soft"),
                     {"give": ["a"], "receive": ["b"]}))

P["ball"] = sphere("ball", 0.045, 0.03, False)
P["apple"] = sphere("apple", 0.035, 0.04, True)

# --- boxes (centred, rotation-0 sockets, explicit approach)
def face(x, y, z): return sock([x, y, z])

P["block"] = asset("block", "generated from a box primitive (centred cube)",
    {"primitive": "box", "size": [0.05, 0.05, 0.05]},
    {"grip": face(0.025, 0, 0), "grip_b": face(-0.025, 0, 0), "place": face(0, -0.025, 0), "top": face(0, 0.025, 0),
     "contact": face(0, 0.025, 0)},
    {"type": "box", "size": [0.05, 0.05, 0.05]},
    aff("hand", "light", "one", 0.06, [0, 0, 0], 45,
        [site("face_a", "grip", "pinch", aperture=0.05, approach=[1, 0, 0]),
         site("face_b", "grip_b", "pinch", aperture=0.05, approach=[-1, 0, 0])],
        sets(("a", ["face_a"]), ("b", ["face_b"])), place(), {"give": ["a"], "receive": ["b"]}))

P["book"] = asset("book", "generated from a box primitive (centred; closed cover)",
    {"primitive": "box", "size": [0.15, 0.025, 0.21]},
    {"grip": face(-0.075, 0, 0), "grip_b": face(0.075, 0, 0), "place": face(0, -0.0125, 0), "top": face(0, 0.0125, 0),
     "contact": face(0, 0.0125, 0)},
    {"type": "box", "size": [0.15, 0.025, 0.21]},
    aff("medium", "light", "one", 0.3, [0, 0, 0], 30,
        [site("spine", "grip", "pinch", aperture=0.025, approach=[-1, 0, 0]),
         site("fore_edge", "grip_b", "pinch", aperture=0.025, approach=[1, 0, 0])],
        sets(("a", ["spine"]), ("b", ["fore_edge"])), place(), {"give": ["a"], "receive": ["b"]}))

P["spoon"] = asset("spoon", "generated from a box primitive (centred flat bar)",
    {"primitive": "box", "size": [0.15, 0.008, 0.022]},
    {"grip": face(-0.045, 0, 0), "grip_b": face(0.0, 0, 0), "place": face(0, -0.004, 0), "top": face(0, 0.004, 0),
     "contact": face(0.075, 0.004, 0)},
    {"type": "box", "size": [0.15, 0.008, 0.022]},
    aff("hand", "light", "one", 0.02, [0, 0, 0], 60,
        [site("handle_end", "grip", "pinch", aperture=0.008, approach=[0, 1, 0]),
         site("handle_mid", "grip_b", "pinch", aperture=0.008, approach=[0, 1, 0])],
        sets(("a", ["handle_end"]), ("b", ["handle_mid"])), place(), {"give": ["a"], "receive": ["b"]}))

BOX = [0.12, 0.07, 0.09]
P["box"] = asset("box", "generated from a box primitive (centred; the lid is prop.felt_box_lid, seated at socket lid_seat)",
    {"primitive": "box", "size": BOX},
    {"side_l": face(-0.06, 0, 0), "side_r": face(0.06, 0, 0), "lid_seat": face(0, 0.035, 0),
     "place": face(0, -0.035, 0), "top": face(0, 0.035, 0), "contact": face(0, 0.035, 0)},
    {"type": "box", "size": BOX},
    aff("small", "light", "either", 0.15, [0, 0, 0], 12,
        [site("side_l", "side_l", "palm", "L", approach=[-1, 0, 0]), site("side_r", "side_r", "palm", "R", approach=[1, 0, 0])],
        [{"id": "l", "sites": ["side_l"]}, {"id": "r", "sites": ["side_r"]},
         {"id": "both", "sites": ["side_l", "side_r"], "simultaneous_frames": 2}], place(),
        None, {"axis": [0, 0, 1], "sites": ["side_l", "side_r"], "friction": "slide"}))

LID = [0.125, 0.012, 0.095]
P["box_lid"] = asset("box_lid", "generated from a box primitive (centred; seats on prop.felt_box socket lid_seat)",
    {"primitive": "box", "size": LID},
    {"grip": face(0, 0.006, 0.0475), "grip_b": face(0, 0.006, -0.0475), "place": face(0, -0.006, 0),
     "top": face(0, 0.006, 0), "contact": face(0, 0.006, 0)},
    {"type": "box", "size": LID},
    aff("hand", "light", "one", 0.03, [0, 0, 0], 20,
        [site("front_edge", "grip", "pinch", aperture=0.012, approach=[0, 0, 1]),
         site("back_edge", "grip_b", "pinch", aperture=0.012, approach=[0, 0, -1])],
        sets(("a", ["front_edge"]), ("b", ["back_edge"])), place(), {"give": ["a"], "receive": ["b"]}))


def main():
    bad = 0
    for name, a in P.items():
        text = json.dumps(a, indent=2) + "\n"
        f = OUT / f"felt_{name}.asset.json"
        if "--check" in sys.argv:
            if not f.exists() or f.read_text() != text:
                print("differs:", f.name); bad += 1
        else:
            f.write_text(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
