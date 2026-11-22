"""T-183 round 3: colliders for the hair of one character from what is around it in a shot (library of derive_shot.py).

neighbour_spheres(bake, owner, ...)   spheres that follow the surface of the OTHER characters' figures from inside
    (pipeline/charsys/groom_contact.py skin_spheres, the fit of the candidate's own body colliders), fitted on each
    neighbour's package meshes in its rest pose. Only surface that comes within `reach_m` of the owner's hair chain
    joints at some frame of the bake takes part (the bake is one of the shot WITHOUT these colliders: where the hair
    would be). Each sphere rides on the bone that carries its vertex most:
        {"name": "nb.<neighbour>.<i>", "type": "sphere", "character": "<neighbour>", "bone": "<bone>",
         "centre": [x, y, z] (the neighbour's rest space), "radius": r}
    Thin parts (REGIONS: hands and fingers by bone name; data, not code) get smaller, closer spheres.
prop_boxes(scene, scene_path)   the scene's box props as boxes in the prop's own frame, its cylinder props (a cup:
    standing on its base, axis y; an open cup counts as solid) as cylinders:
        {"name": "prop.<name>", "type": "box", "prop": "<name>", "min": [...], "max": [...], "radius": edge rounding}
        {"name": "prop.<name>", "type": "cylinder", "prop": "<name>", "a": [0, 0, 0], "b": [0, height, 0],
         "radius": r, "round": rim rounding}
Format and engine side: docs/SECONDARY_MOTION.md, "Scene colliders". Needs the bpy module (mathutils) for the spheres.

    python3 neighbours.py <bake.json> <owner> [--reach-m=0.1]     prints the counts per neighbour and bone
"""
import fnmatch
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))

# not part of a neighbour's solid figure (measure_body.py SKIP + its hair)
SKIP_PARTS = ["hair_*", "eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
# fit values per region; a vertex belongs to the first region whose bone patterns match the bone that carries it most
REGIONS = [
    {"name": "hands", "bones": ["*hand*", "*f_index*", "*f_middle*", "*f_ring*", "*f_pinky*", "*thumb*", "*palm*", "*finger*"],
     "spacing_m": 0.012, "radius_m": 0.02, "min_radius_m": 0.004},
    {"name": "body", "bones": ["*"], "spacing_m": 0.024, "radius_m": 0.045, "min_radius_m": 0.008},
]
PAD = 0.0025


def _solid(ch):
    parts = [m["part"] for m in ch.doc["meshes"]]
    return [i for i, p in enumerate(parts) if not any(fnmatch.fnmatchcase(p, s) for s in SKIP_PARTS)]


def chain_joints(ch):
    """(F, J, 3) world positions of the pivots of the owner's chain bones over the bake."""
    bones = sorted({b for c in (ch.doc.get("dynamics") or {}).get("chains", []) for b in c["bones"]})
    idx = [ch.bones.index(b) for b in bones if b in ch.bones]
    return ch.pivots()[:, idx]


def neighbour_spheres(bake, owner, reach=0.1, step=2, regions=REGIONS, pad=PAD, only=None):
    """[collider, ...], {neighbour: {"spheres": n, "surface_vertices": n, "bones": {bone: n}}} for the hair of
    `owner` (a character name of the bake)."""
    import bpy  # noqa: F401 (makes mathutils importable)
    from mathutils.bvhtree import BVHTree
    import shot as S
    import groom_contact as GC
    shot = S.Shot(bake)
    own = next(c for c in shot.characters if c.name == owner)
    J = chain_joints(own)[::step]  # (F', J, 3)
    out, report = [], {}
    for ch in shot.characters:
        if ch.name == owner or (only and ch.name not in only):
            continue
        solid = _solid(ch)
        P, N, tris, top, base = [], [], [], [], 0
        jm = ch._joint_map()
        skel = [b["name"] for b in ch.doc["skeleton"]]
        for mi in solid:
            p, n, j, w = ch.rest(mi)
            P.append(p)
            N.append(n)
            top += [skel[j[k, int(np.argmax(w[k]))]] for k in range(len(p))]
            tris.append(ch.array(ch.doc["meshes"][mi]["indices"], 3).astype(np.int64) + base)
            base += len(p)
        P, N, tris = np.concatenate(P), np.concatenate(N), np.concatenate(tris)
        # surface within reach of the owner's chain joints at some frame
        near = np.zeros(len(P), dtype=bool)
        base = 0
        for mi in solid:
            p, _, j, w = ch.rest(mi)
            jj = jm[j]
            for f in range(0, ch.M.shape[0], step):
                Jf = J[f // step]
                lo, hi = Jf.min(0) - reach, Jf.max(0) + reach
                A = np.einsum("nk,nkij->nij", w, ch.M[f][jj])
                W = np.einsum("nij,nj->ni", A[:, :3, :3], p) + A[:, :3, 3]
                cand = np.nonzero(np.all((W >= lo) & (W <= hi), axis=1) & ~near[base:base + len(p)])[0]
                if len(cand):
                    d2 = ((W[cand, None, :] - Jf[None, :, :]) ** 2).sum(-1).min(1)
                    near[base + cand[d2 <= reach * reach]] = True
            base += len(p)
        report[ch.name] = {"surface_vertices": int(near.sum()), "spheres": 0, "bones": {}}
        if not near.any():
            continue
        tree = BVHTree.FromPolygons(P.tolist(), tris.tolist())
        taken = np.zeros(len(P), dtype=bool)
        k = 0
        for reg in regions:
            sel = np.array([i for i in np.nonzero(near & ~taken)[0] if any(fnmatch.fnmatchcase(top[i], b) for b in reg["bones"])], dtype=np.int64)
            taken[sel] = True
            if not len(sel):
                continue
            for vi, centre, r in GC.skin_spheres(tree, P[sel], N[sel], [P[sel[0]]], spacing=reg["spacing_m"], radius=reg["radius_m"],
                                                 pad=pad, reach=1e9, min_radius=reg["min_radius_m"]):
                bone = top[int(sel[vi])]
                out.append({"name": f"nb.{ch.name}.{k}", "type": "sphere", "character": ch.name, "bone": bone,
                            "centre": [round(float(x), 4) for x in centre], "radius": round(float(r), 4)})
                report[ch.name]["bones"][bone] = report[ch.name]["bones"].get(bone, 0) + 1
                k += 1
        report[ch.name]["spheres"] = k
    return out, report


def prop_assets(scene_path):
    """{prop id: asset json} from content/assets of the repository and of the scene's episode."""
    dirs = [os.path.join(ROOT, "content", "assets")]
    d = os.path.dirname(os.path.abspath(scene_path))
    while len(d) > len(ROOT):
        dirs.append(os.path.join(d, "content", "assets"))
        d = os.path.dirname(d)
    out = {}
    for a in dirs:
        for f in sorted(glob.glob(os.path.join(a, "**", "*.asset.json"), recursive=True)):
            try:
                j = json.load(open(f))
            except ValueError:
                continue
            if isinstance(j, dict) and "id" in j:
                out[j["id"]] = j
    return out


def prop_boxes(scene, scene_path, skip=(), radius=0.003):
    """The scene's props whose asset is a box primitive, as box colliders in the prop's own frame (centred, scaled
    by the asset's scale as the engine draws it). The edge rounding is `radius`, at most the smallest half extent.
    A cylinder primitive (standing on its base, axis y, as measure_props.prop_shape reads it) becomes a cylinder
    collider with the same rounding at its rims."""
    assets = prop_assets(scene_path)
    out = []
    for p in scene.get("props", []):
        a = assets.get(p.get("id"))
        m = (a or {}).get("mesh", {})
        if m.get("primitive") not in ("box", "cylinder") or any(fnmatch.fnmatchcase(p["name"], s) for s in skip):
            continue
        if m["primitive"] == "cylinder":
            sc = float(a.get("scale", 1.0))
            r, h = round(sc * float(m["radius"]), 5), round(sc * float(m["height"]), 5)
            out.append({"name": f"prop.{p['name']}", "type": "cylinder", "prop": p["name"], "a": [0.0, 0.0, 0.0], "b": [0.0, h, 0.0],
                        "radius": r, "round": round(min(radius, r, 0.5 * h), 5)})
            continue
        h = [round(0.5 * float(a.get("scale", 1.0)) * float(x), 5) for x in m["size"]]
        out.append({"name": f"prop.{p['name']}", "type": "box", "prop": p["name"], "min": [-x for x in h], "max": h,
                    "radius": round(min(radius, min(h)), 5)})
    return out


if __name__ == "__main__":
    reach = float(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--reach-m=")), "0.1"))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cols, rep = neighbour_spheres(args[0], args[1], reach=reach)
    print(json.dumps(rep, indent=1))
    print(len(cols), "spheres")
