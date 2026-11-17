"""T-043 evidence tool: compares two engine character packages (character.json + geometry.bin) block by block.

    python3 compare_exports.py <package A dir> <package B dir> [--ignore-keys versions]

Prints, per manifest key, whether it is equal (source.blend_sha256 and files.geometry.bin.sha256 are reported, since
they follow geometry.bin and the .blend bytes), and per typed geometry block (meshes and morphs) the number of
differing elements and the largest absolute difference. Exit 0 always; the JSON summary goes to stdout.

Canonical comparison: two builds of the same commit can export the same mesh with its vertices and triangles in a
different ORDER (measured on origin/staging: two identical boy builds differ in 126800 bytes, all of it ordering).
So each mesh is also compared order-independently: every vertex becomes a record (position, normal, joints,
weights, and its delta in every morph of that mesh), records are sorted, triangles are rewritten with the sorted
record ranks (rotated to start at the lowest rank, winding kept) and sorted; the mesh is equal when both sorted
arrays are bit-identical. "canonical_equal" is true when every mesh is.

Matched comparison ("matched_equal"): each vertex of A is matched to an unused vertex of B at the same position
(grid lookup, within 1 micrometre; coincident seam vertices are told apart by their other attributes); then normals (<= 1e-3), weights (<= 1e-5), joints (equal), morph deltas
(<= 1e-6 m) and the triangle set (through the matching, winding kept) must agree. These tolerances absorb the float
noise of evaluated normals measured between two identical origin/staging builds (normals 4e-5, positions 6e-8 m)
and are far below anything visible; any real geometry, topology, skinning or morph change fails it."""
import json
import os
import sys

import numpy as np


def blocks(man):
    for i, m in enumerate(man.get("meshes", [])):
        for f, v in m.items():
            if isinstance(v, dict) and "offset" in v:
                yield f"mesh[{m.get('part', i)}].{f}", v
    for i, m in enumerate(man.get("morphs", [])):
        for f, v in m.items():
            if isinstance(v, dict) and "offset" in v:
                yield f"morph[{m.get('mesh', '')}:{m.get('name', i)}].{f}", v


def _arr(buf, v):
    return np.frombuffer(buf, np.dtype(v["dtype"]).newbyteorder("<"), v["count"], v["offset"])


def canonical_mesh(man, buf, i):
    m = man["meshes"][i]
    n = m["vertices"]
    cols = [_arr(buf, m[f]).reshape(n, 3).astype(np.float64) for f in ("positions", "normals")]
    for f in ("joints", "weights"):
        if f in m:
            cols.append(_arr(buf, m[f]).reshape(n, -1).astype(np.float64))
    for mo in sorted((mo for mo in man.get("morphs", []) if mo["mesh"] == i), key=lambda mo: mo["name"]):
        d = np.zeros((n, 3))
        d[_arr(buf, mo["vertices"]).astype(np.int64)] = _arr(buf, mo["dpos"]).reshape(-1, 3)
        cols.append(d)
    rec = np.hstack(cols)
    order = np.lexsort(rec.T[::-1])
    rank = np.empty(n, np.int64)
    rank[order] = np.arange(n)
    tri = rank[_arr(buf, m["indices"]).astype(np.int64).reshape(-1, 3)]
    roll = np.argmin(tri, axis=1)
    tri = np.stack([np.roll(t, -r) for t, r in zip(tri, roll)]) if len(tri) else tri
    tri = tri[np.lexsort(tri.T[::-1])] if len(tri) else tri
    return rec[order].tobytes() + tri.astype("<i8").tobytes()


def canonical_diff(ma, mb, ba, bb):
    if [m.get("vertices") for m in ma["meshes"]] != [m.get("vertices") for m in mb["meshes"]]:
        return ["<mesh list differs>"]
    return [m.get("part", str(i)) for i, m in enumerate(ma["meshes"])
            if canonical_mesh(ma, ba, i) != canonical_mesh(mb, bb, i)]


TOL = {"positions": 1e-6, "normals": 1e-3, "weights": 1e-5, "joints": 0.0, "dpos": 1e-6}


def mesh_attrs(man, buf, i):
    m = man["meshes"][i]
    n = m["vertices"]
    at = {f: _arr(buf, m[f]).reshape(n, -1).astype(np.float64) for f in ("positions", "normals", "joints", "weights") if f in m}
    for mo in (mo for mo in man.get("morphs", []) if mo["mesh"] == i):
        d = np.zeros((n, 3))
        d[_arr(buf, mo["vertices"]).astype(np.int64)] = _arr(buf, mo["dpos"]).reshape(-1, 3)
        at["dpos:" + mo["name"]] = d
    return at, _arr(buf, m["indices"]).astype(np.int64).reshape(-1, 3)


def _canon_tris(t):
    if not len(t):
        return t
    t = np.stack([np.roll(x, -r) for x, r in zip(t, np.argmin(t, axis=1))])
    return t[np.lexsort(t.T[::-1])]


def matched_mesh(ma, ba, mb, bb, i):
    """None if equal within TOL after matching vertices by position, else a short reason."""
    A, ta = mesh_attrs(ma, ba, i)
    B, tb = mesh_attrs(mb, bb, i)
    if set(A) != set(B):
        return "attribute/morph set differs"
    cell = TOL["positions"]
    grid = {}
    for j, p in enumerate(B["positions"]):
        grid.setdefault(tuple(np.floor(p / cell).astype(np.int64)), []).append(j)
    perm = np.full(len(A["positions"]), -1, np.int64)
    used = set()
    for j, p in enumerate(A["positions"]):
        c = np.floor(p / cell).astype(np.int64)
        best, bd = -1, (cell, np.inf)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for k in grid.get((c[0] + dx, c[1] + dy, c[2] + dz), ()):
                        d = (float(np.abs(B["positions"][k] - p).max()),
                             sum(float(np.abs(B[f][k] - A[f][j]).sum()) for f in A if f != "positions"))
                        if d[0] <= cell and k not in used and (d[1], d[0]) < (bd[1], bd[0]):
                            best, bd = k, d
        if best < 0:
            return f"vertex {j} has no match within {cell} m"
        perm[j] = best
        used.add(best)
    for f, x in A.items():
        tol = TOL["dpos" if f.startswith("dpos:") else f]
        d = float(np.abs(x - B[f][perm]).max(initial=0))
        if d > tol:
            return f"{f} differs by {d:.3g} (> {tol})"
    if not np.array_equal(_canon_tris(perm[ta]), _canon_tris(tb)):
        return "triangles differ"
    return None


def matched_diff(ma, mb, ba, bb):
    if [m.get("vertices") for m in ma["meshes"]] != [m.get("vertices") for m in mb["meshes"]]:
        return {"<mesh list>": "differs"}
    out = {}
    for i, m in enumerate(ma["meshes"]):
        r = matched_mesh(ma, ba, mb, bb, i)
        if r:
            out[m.get("part", str(i))] = r
    return out


def main():
    a_dir, b_dir = sys.argv[1], sys.argv[2]
    ignore = set(sys.argv[sys.argv.index("--ignore-keys") + 1].split(",")) if "--ignore-keys" in sys.argv else set()
    ma, mb = (json.load(open(os.path.join(d, "character.json"))) for d in (a_dir, b_dir))
    ba, bb = (open(os.path.join(d, "geometry.bin"), "rb").read() for d in (a_dir, b_dir))
    keys = {}
    for k in sorted(set(ma) | set(mb)):
        if k in ignore:
            keys[k] = "ignored"
        elif k == "source":
            sa = {x: y for x, y in ma[k].items() if x != "blend_sha256"}
            sb = {x: y for x, y in mb[k].items() if x != "blend_sha256"}
            keys[k] = "equal" if sa == sb else "DIFFERS"
            keys["source.blend_sha256"] = "equal" if ma[k].get("blend_sha256") == mb[k].get("blend_sha256") else "differs"
        elif k == "files":
            keys[k] = "equal" if ma[k] == mb[k] else "differs (geometry.bin bytes)"
        else:
            keys[k] = "equal" if ma.get(k) == mb.get(k) else "DIFFERS"
    diff = {}
    worst = {}
    if len(ba) == len(bb):
        for name, v in blocks(ma):
            dt = np.dtype(v["dtype"]).newbyteorder("<")
            n = v["count"]
            x = np.frombuffer(ba, dt, n, v["offset"]).astype(np.float64)
            y = np.frombuffer(bb, dt, n, v["offset"]).astype(np.float64)
            d = np.abs(x - y)
            if d.max(initial=0) > 0:
                kind = name.rsplit(".", 1)[1]
                diff[name] = {"elements": int((d > 0).sum()), "max_abs": float(d.max())}
                worst[kind] = max(worst.get(kind, 0.0), float(d.max()))
    canon = canonical_diff(ma, mb, ba, bb)
    matched = matched_diff(ma, mb, ba, bb)
    out = {"a": a_dir, "canonical_equal": not canon, "canonical_differing_meshes": canon,
           "matched_equal": not matched, "matched_differences": matched, "b": b_dir, "geometry_bytes_equal": ba == bb, "geometry_size": [len(ba), len(bb)],
           "manifest_keys": keys, "differing_blocks": len(diff), "worst_by_field": worst, "blocks": diff}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
