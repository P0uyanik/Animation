"""T-056 evidence tool: how far an export/5 package is from the export/4 package of the same master.

    python3 compare_v4_v5.py <export/4 package dir> <export/5 package dir>

export/5 writes the same meshes in another (canonical) order with rounded values, so the packages are compared
per mesh through a vertex matching: each export/5 vertex is matched to an unused export/4 vertex whose position,
rounded to the export/5 position grid (2^-15 m), is the same (coincident vertices are told apart by their triangle
neighbourhood, then normal and weights).
Reported per field, over all meshes: largest position difference (m), largest normal angle (degrees), largest
difference of any bone's skin influence (joint -> weight maps, so slot order and empty slots do not matter), largest
morph delta difference (m), morph vertices export/5 drops although their delta reaches half a grid step, and whether the
triangle sets (winding kept) are equal through the matching. Manifest keys are compared except the ones export/5
changes by design (source.blend_sha256 dropped, exporter_version, versions, files). JSON to stdout; exit 0 always."""
import json
import os
import sys

import numpy as np

GRID = 2.0 ** -15        # export/5 position grid
DELTA_GRID = 2.0 ** -14  # export/5 morph delta grid


def _arr(buf, v):
    return np.frombuffer(buf, np.dtype(v["dtype"]).newbyteorder("<"), v["count"], v["offset"])


def mesh(man, buf, i):
    m = man["meshes"][i]
    n = m["vertices"]
    out = {f: _arr(buf, m[f]).reshape(n, -1).astype(np.float64) for f in ("positions", "normals", "joints", "weights")}
    infl = {}
    for v in range(n):
        d = {}
        for j, w in zip(out["joints"][v], out["weights"][v]):
            if w > 0:
                d[int(j)] = d.get(int(j), 0.0) + float(w)
        infl[v] = d
    out["influence"] = infl
    morphs = {}
    for mo in man.get("morphs", []):
        if mo["mesh"] == i:
            d = np.zeros((n, 3))
            d[_arr(buf, mo["vertices"]).astype(np.int64)] = _arr(buf, mo["dpos"]).reshape(-1, 3)
            morphs[mo["name"]] = d
    out["morphs"] = morphs
    out["tri"] = _arr(buf, m["indices"]).astype(np.int64).reshape(-1, 3)
    return out


def canon_tris(t):
    if not len(t):
        return t
    r = np.argmin(t, axis=1)
    t = np.take_along_axis(t, (np.arange(3)[None, :] + r[:, None]) % 3, axis=1)
    return t[np.lexsort(t.T[::-1])]


def _neighbours(tri, n):
    nb = [set() for _ in range(n)]
    for x, y, z in tri.tolist():
        nb[x] |= {y, z}
        nb[y] |= {x, z}
        nb[z] |= {x, y}
    return nb


def compare_mesh(A, B):
    key = lambda p: tuple(np.round(p / GRID).astype(np.int64))  # noqa: E731
    ga, gb = {}, {}
    for j, p in enumerate(A["positions"]):
        ga.setdefault(key(p), []).append(j)
    for j, p in enumerate(B["positions"]):
        gb.setdefault(key(p), []).append(j)
    perm = np.full(len(B["positions"]), -1, np.int64)
    groups = []
    for k, bs in gb.items():
        a = ga.get(k, [])
        if len(a) != len(bs):
            return {"error": f"grid point {k}: {len(a)} export/4 vs {len(bs)} export/5 vertices"}
        if len(bs) == 1:
            perm[bs[0]] = a[0]
        else:
            groups.append((a, bs))
    # coincident vertices: matched by their triangle neighbourhood (through the unique matches), then attributes
    if groups:
        na, nb = _neighbours(A["tri"], len(A["positions"])), _neighbours(B["tri"], len(B["positions"]))
        for _ in range(3):
            for a, bs in groups:
                inv = {int(perm[j]): j for j in range(len(perm)) if perm[j] >= 0}
                pairs = []
                for i in a:
                    mapped = {inv.get(x, -1 - x) for x in na[i]}
                    for j in bs:
                        attr = float(np.abs(A["normals"][i] - B["normals"][j]).sum()) + sum(
                            abs(A["influence"][i].get(t, 0.0) - B["influence"][j].get(t, 0.0))
                            for t in set(A["influence"][i]) | set(B["influence"][j]))
                        pairs.append((len(mapped ^ nb[j]), attr, i, j))
                used_a, used_b = set(), set()
                for _, _, i, j in sorted(pairs):
                    if i not in used_a and j not in used_b:
                        perm[j] = i
                        used_a.add(i)
                        used_b.add(j)
    pa = A["positions"][perm]
    dot = np.clip((A["normals"][perm] * B["normals"]).sum(axis=1), -1, 1)
    infl = 0.0
    for j in range(len(perm)):
        a, b = A["influence"][int(perm[j])], B["influence"][j]
        for jt in set(a) | set(b):
            infl = max(infl, abs(a.get(jt, 0.0) - b.get(jt, 0.0)))
    morph, only_one = 0.0, 0
    if set(A["morphs"]) != set(B["morphs"]):
        return {"error": "morph sets differ"}
    for name, db in B["morphs"].items():
        da = A["morphs"][name][perm]
        morph = max(morph, float(np.abs(da - db).max(initial=0)))
        # export/4 lists a vertex when |delta| > 1e-7 m, export/5 when its rounded delta is not 0 (|delta| >= 2^-15)
        only_one += int(((np.linalg.norm(da, axis=1) > 1e-7) & ~(np.abs(db).max(axis=1) > 0)
                         & (np.abs(da).max(axis=1) > DELTA_GRID / 2)).sum())
    inv = np.empty(len(perm), np.int64)
    inv[perm] = np.arange(len(perm))
    tri_equal = np.array_equal(canon_tris(inv[A["tri"]]), canon_tris(B["tri"]))
    deg = np.degrees(np.arccos(dot))
    return {"position_m": float(np.abs(pa - B["positions"]).max(initial=0)),
            "normal_deg": float(deg.max(initial=0.0)),
            "normals_over_deg": {t: int((deg > t).sum()) for t in (0.1, 0.5, 1.0, 2.0, 5.0)},
            "influence": infl, "morph_m": morph, "morph_vertices_only_one_side": only_one, "triangles_equal": tri_equal}


def mesh_b_positions(man, i):
    return range(man["meshes"][i]["vertices"])


def main():
    a_dir, b_dir = sys.argv[1], sys.argv[2]
    ma, mb = (json.load(open(os.path.join(d, "character.json"))) for d in (a_dir, b_dir))
    ba, bb = (open(os.path.join(d, "geometry.bin"), "rb").read() for d in (a_dir, b_dir))
    by_design = {"exporter_version", "versions", "files", "meshes", "morphs"}
    keys = {}
    for k in sorted(set(ma) | set(mb)):
        if k in by_design:
            continue
        if k == "source":
            sa = {x: y for x, y in ma[k].items() if x != "blend_sha256"}
            keys[k] = "equal" if sa == mb[k] else "DIFFERS"
        else:
            keys[k] = "equal" if ma.get(k) == mb.get(k) else "DIFFERS"
    strip = lambda m: [{k: v for k, v in x.items() if not isinstance(v, dict)} for x in m]  # noqa: E731
    keys["meshes (layout: part, material, vertex count)"] = "equal" if strip(ma["meshes"]) == strip(mb["meshes"]) else "DIFFERS"
    keys["morphs (mesh, name)"] = "equal" if sorted((m["mesh"], m["name"]) for m in ma["morphs"]) == \
        sorted((m["mesh"], m["name"]) for m in mb["morphs"]) else "DIFFERS"
    per, worst = {}, {"position_m": 0.0, "normal_deg": 0.0, "influence": 0.0, "morph_m": 0.0,
                      "morph_vertices_only_one_side": 0, "triangles_equal": True,
                      "normals_over_deg": {}, "vertices": 0}
    errors = {}
    for i, m in enumerate(mb["meshes"]):
        r = compare_mesh(mesh(ma, ba, i), mesh(mb, bb, i))
        if "error" in r:
            errors[m["part"]] = r["error"]
            continue
        per[m["part"]] = r
        for f, v in r.items():
            if f == "triangles_equal":
                worst[f] = v and worst[f]
            elif f == "normals_over_deg":
                for t, c in v.items():
                    worst[f][t] = worst[f].get(t, 0) + c
            elif f == "morph_vertices_only_one_side":
                worst[f] += v
            else:
                worst[f] = max(worst[f], v)
        worst["vertices"] += len(mesh_b_positions(mb, i))
    print(json.dumps({"export4": a_dir, "export5": b_dir, "manifest_keys": keys, "errors": errors, "worst": worst,
                      "meshes": per}, indent=1))


if __name__ == "__main__":
    main()
