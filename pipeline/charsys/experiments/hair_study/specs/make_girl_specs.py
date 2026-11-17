"""Writes girl_A/B/C.json from the girl's current spec (T-049 study; experiment data only).
    python3 pipeline/charsys/experiments/hair_study/specs/make_girl_specs.py"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SPEC = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"
src = json.load(open(os.path.join(ROOT, SPEC)))["hair"]
S = {s.get("name", s["type"]): s for s in src["structures"]}
H = 0.97
FRAME = {"centre": [0.0, -0.00412 * H, 0.85052 * H], "radii": [0.14639 * H, 0.13918 * H, 0.14948 * H]}
CURL = S["back_curls"]["curl"]
FELT = S["back_curls"]["felt"]


def head(approach, label):
    return {"schema": "plush-studio.hair-study/1", "approach": approach, "label": label, "character_spec": SPEC,
            "head_object": "body_skin", "frame": FRAME}


def hair(structures, dyn_structs):
    h = {k: copy.deepcopy(v) for k, v in src.items() if k not in ("structures", "dynamics", "components", "provenance")}
    h["seed"] = 49
    h["structures"] = structures
    d = copy.deepcopy(src["dynamics"])
    d["structures"] = dyn_structs
    h["dynamics"] = d if dyn_structs else {"enabled": False}
    return h


def raised(st, d_el):
    st = copy.deepcopy(st)
    st["tip_el"] = [e + d_el for e in st["tip_el"]]
    return st


def temple(name, az):
    st = copy.deepcopy(S["temple_l"])
    st.update(name=name, az=az, radii=[0.05, 0.045, 0.075])
    return st


# sculpted ringlet curtain from behind the ears around the back (B and C)
CURTAIN = {"type": "study_curtain", "name": "curtain", "az": [92, 268],
           "root_el": [[92, 14], [125, 24], [180, 30]], "leave_el": -6,
           "z_end": [[92, 0.6], [130, 0.5], [180, 0.44]], "rest_radii": [0.175, 0.15], "rest_z": 0.62,
           "columns": 14, "thick": 0.036, "column_depth": 0.6, "lobe": {"pitch": 0.046, "depth": 0.45, "twist": 0.7},
           "scallop": 0.045, "resolution": [200, 110], "inset": 0.004}
SHELL = [S["cap"], S["bun"], S["crown"], raised(S["fringe"], 3), raised(S["fringe_part"], 3),
         temple("temple_l", 82), temple("temple_r", -82)]
ACC = [S["band"], S["flowers"]]

# --- C: hybrid = shells + curtain + a limited number of ringlets at the edges
side = {"type": "locks", "name": "edge_side", "style": "curly", "mirror": True, "count": 2, "az": [88, 104],
        "el_root": [12, 22], "el_leave": -10, "lift": [0.006, 0.02], "hang_radii": [0.2, 0.175], "z_end": [0.55, 0.62],
        "flare": 0.05, "width": [0.038, 0.044], "thick": [0.03, 0.035], "tip_frac": 0.6, "curl": CURL, "felt": FELT,
        "finish": "felt"}
back = {"type": "locks", "name": "edge_back", "style": "curly", "count": 7, "az": [130, 230], "el_root": [-14, -6],
        "el_leave": -30, "lift": [0.01, 0.03], "hang_radii": [0.2, 0.18], "z_end": [0.42, 0.5], "flare": 0.06,
        "width": [0.038, 0.046], "thick": [0.03, 0.036], "tip_frac": 0.6, "hang_jitter": 0.05,
        "rest_radii": [0.2, 0.17], "rest_z": 0.62, "curl": CURL, "felt": FELT, "finish": "felt"}
dyn_c = {"edge_side": {"bones": [3, 4], "bone_length": 0.06}, "edge_back": {"bones": [3, 5], "bone_length": 0.07},
         "bun": S and src["dynamics"]["structures"]["bun"]}
C = head("C", "hybrid: felted crown/fringe/bun/temple shells + sculpted ringlet curtain + 11 felt ringlets at the edges")
C["hair"] = hair(SHELL + [CURTAIN, side, back] + ACC, dyn_c)

# --- B: sculpted = the same shells + a deeper-carved curtain, fused into one volume (no locks, no chains)
cb = copy.deepcopy(CURTAIN)
cb.update(thick=0.046, column_depth=0.45, lobe={"pitch": 0.056, "depth": 0.35, "twist": 0.5})
B = head("B", "sculpted: crown/fringe/bun/temple shells + carved ringlet curtain fused by voxel remesh into one sculpt")
B["hair"] = hair(SHELL + [cb] + ACC, {})
B["fuse"] = {"voxel": 0.0022, "smooth": 3, "exclude": ["cap", "band", "flowers_petals", "flowers_centres"]}

# --- A: strand/lock groom = yarn locks swept to the bun, yarn fringe locks, many felt ringlet locks (face kept clear)
bun_y = copy.deepcopy(S["bun"])
bun_y["finish"] = "yarn"
sw = {"width": [0.02, 0.026], "thick": [0.012, 0.016], "lift": [0.004, 0.01], "target": {"bun": 0}, "finish": "yarn"}
A_st = [S["cap"], bun_y,
        dict(sw, type="sweep", name="sweep_front", count=30, az=[-75, 75], el_root=[36, 44]),
        dict(sw, type="sweep", name="sweep_side_l", count=12, az=[75, 130], el_root=[4, 14]),
        dict(sw, type="sweep", name="sweep_side_r", count=12, az=[-130, -75], el_root=[4, 14]),
        dict(sw, type="sweep", name="sweep_back", count=26, az=[130, 230], el_root=[12, 18]),
        {"type": "fringe", "name": "fringe", "finish": "yarn", "root_az": [-20, -20, -21, -22, -23, -24, -26],
         "root_el": [56, 70], "tip_x": [0.0, 0.03, 0.06, 0.09, 0.115, -0.05, -0.095],
         "tip_z": [0.885, 0.88, 0.87, 0.85, 0.82, 0.88, 0.85], "tip_gap": 0.014, "bulge": 0.03,
         "width": [0.026, 0.032], "thick": [0.016, 0.02], "tip_frac": 0.5}]
locks = []
for nm, cnt, az, mirror in (("side_curls", 4, [90, 114], True), ("back_curls", 24, [124, 236], False),
                            ("nape_curls", 10, [140, 220], False)):
    st = copy.deepcopy(S[nm])
    st.update(count=cnt, az=az, mirror=mirror, width=[0.028, 0.034], thick=[0.022, 0.027], finish="felt")
    if nm == "side_curls":
        st["el_root"] = [18, 30]
    locks.append(st)
dyn_a = {"side_curls": {"bones": [3, 4], "bone_length": 0.06}, "back_curls": {"bones": [3, 5], "bone_length": 0.07},
         "nape_curls": {"bones": [3, 5], "bone_length": 0.07}, "bun": src["dynamics"]["structures"]["bun"]}
A = head("A", "strand/lock groom: yarn locks swept to a yarn bun, yarn fringe locks, 42 felt ringlet locks")
A["hair"] = hair(A_st + locks + ACC, dyn_a)

for name, d in (("A", A), ("B", B), ("C", C)):
    json.dump(d, open(os.path.join(HERE, f"girl_{name}.json"), "w"), indent=1)
print("wrote girl_A/B/C.json")
