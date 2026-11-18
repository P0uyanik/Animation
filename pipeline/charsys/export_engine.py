"""Exports a rigged character from a .blend into the engine's imported-character package (headless Blender).
Character-independent: everything character- or rig-specific comes from the rig profile (rig_profiles/*.json).

    blender -b --factory-startup -P pipeline/charsys/export_engine.py -- --blend <master.blend> \
        --profile pipeline/charsys/rig_profiles/humanoid_rigify.json --out <new dir> [--collection <root collection>]

Format: docs/ENGINE_CHARACTER_PACKAGE.md. Read-only on the input file (it is never saved).
Rules:
  * every deform bone is exported (role bones renamed to their engine role, all others keep their source name);
    nothing is merged;
  * a bone's parent is its nearest deform ancestor; for the profile's contiguous_chains a role bone is re-parented
    to the previous role of its chain (engine two-bone IK needs parent/grandparent = chain), and the in-between
    helpers stay children of their original parent (reported in "reparented");
  * a deform bone with no deform ancestor (Rigify: under ORG-/MCH- bones only, e.g. DEF-eye.L, DEF-shoulder.L) is
    parented to the DEF twin of its nearest ORG-/MCH- ancestor that has one (the bone Blender carries it with);
  * eye roles ("eye.*") pivot at the centre of the spherical eyeball bound only to them (reported in "eye_pivots");
  * required roles are profile-specific; a missing one fails the export;
  * coordinates: Blender (+Z up, faces -Y) -> engine (+Y up, faces +Z): (x, y, z) -> (x, z, -y); metres.
"""
import argparse
import hashlib
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
FORMAT, VERSION = "plush.imported_character", 1
# Version of this exporter's output. run_shot.py keys its package cache on it, so packages are re-exported when the
# exporter changes. 2: adds the "retarget" block (generated clip retarget data, docs/ANIMATION_CLIPS.md).
# 3 (T-021): adds the optional "dynamics" block (secondary-motion chains, docs/SECONDARY_MOTION.md); packages of
#    masters without chain metadata are unchanged apart from this number.
# 3 (T-030, developed in parallel): deform bones without a deform ancestor take the DEF twin of their Rigify ORG/MCH
#    ancestor as parent; eye roles pivot at their eyeball's centre ("eye_pivots").
# 4 (integration batch 1): both of the above together (the "dynamics" block, the DEF-parent fix and the eye pivots).
# T-043: this number is the exporter's entry "export/4" in the per-feature version registry (versions.py); 1-3 are
# retired. The literal stays here because run_shot.py reads it from this file's source for its package cache key.
# A spec pinning another exporter version fails here; the manifest records every generator pin ("versions").
# 5 (T-056): order-stable, byte-reproducible output (canonical(), docs/evaluation/characters/T-056/README.md); same
#    content as 4 within its rounding grids. export/4 output is unchanged byte for byte (released versions are immutable):
#    the pinned version selects the code path. EXPORTER_VERSION stays "4" (the legacy default every unpinned spec
#    resolves to and run_shot's cache key; a master pinning export/5 never had an export/4 package). Masters without
#    an embedded spec (test data) export as EXPORTER_DEFAULT.
# 6 (T-047): export/5 + the "collision" block (one collision body per character: torso sections and limb capsules,
#    collision_block() below; engine/scene/collision.h). Opt-in by pinning export/6; export/4 and export/5 output is
#    unchanged byte for byte.
EXPORTER_VERSION = "4"
EXPORTER_DEFAULT = "5"
EXPORTER_COLLISION = "6"
GENERATOR_VERSIONS = (f"export/{EXPORTER_VERSION}", f"export/{EXPORTER_DEFAULT}", f"export/{EXPORTER_COLLISION}")
# export/5 grids (powers of two: exact in float32, so the rounding survives the float32 write). Chosen from the noise
# measured over 7 builds of each character (docs/evaluation/characters/T-056): a value whose build-to-build noise
# crosses a rounding midpoint still differs, so each grid is coarse enough to make that unlikely (expected <= 0.02
# such values per character per pair of builds) and fine enough to be invisible.
GRID_M = 2.0 ** -15        # positions: 30.5 um (max change 15 um)
DELTA_GRID_M = 2.0 ** -14  # morph deltas: 61 um (max change 31 um; deltas below 31 um are dropped)
WEIGHT_STEPS = 2 ** 10     # skin weights: multiples of 1/1024 summing to exactly 1 (max change 4.9e-4)
# export/5 normals: the normal of the rounded positions is used where it is within this angle of Blender's normal of
# the unrounded positions (see canonical comment below).
NORMAL_SWITCH_DEG = 2.0
sys.path.insert(0, os.path.join(HERE, "..", "clips"))
import retarget as RT  # noqa: E402  (shared clip retargeting rules; pure Python)

sys.path.insert(0, HERE)
import versions as V  # noqa: E402  (per-feature generator versions; pure Python)


def version_record(root):
    """Generator pins of the master's embedded spec (versions.record); checks that it pins this exporter. Masters
    without an embedded spec (test data, older files) record only the exporter."""
    txt = bpy.data.texts.get("ps_character_spec.json")
    if txt is None:
        return {"generators": {"exporter": f"export/{EXPORTER_DEFAULT}"}, "embedded_spec": False}
    rec = V.record(json.loads(txt.as_string()))
    pinned = rec["generators"]["exporter"]
    if pinned not in GENERATOR_VERSIONS:
        raise V.VersionError(f"{root.get('ps_character_id', root.name)} pins exporter {pinned!r}; this exporter is "
                             f"{' / '.join(GENERATOR_VERSIONS)}")
    return rec


# ---- export/5: canonical, run-independent mesh data (T-056) ----
# Two builds of the same spec can store a mesh with its polygons (and, for some meshes, vertices) in a different
# order, with ulp-level noise (<= 6e-8 m) on a few coordinates, and with ulp-level noise on automatic skin weights
# (measured in docs/evaluation/characters/T-056). The builders own that order (not this exporter), so export/5 writes
# data that does not depend on it:
#   * positions rounded to GRID_M, morph deltas to DELTA_GRID_M;
#   * skin weights rounded to 1/WEIGHT_STEPS with an exact integer sum, the four influences ordered by (weight
#     descending, joint index), an empty influence slot written as joint 0;
#   * every vertex of an object gets a canonical rank: sorted by (rounded position, joints, weights, rounded morph
#     deltas in shape key order, which the spec defines); exact ties are told apart by their polygon neighbourhoods
#     (colour refinement);
#   * the build's start corners of quads and n-gons are kept: they decide how Blender splits them (export/4's
#     triangles) and they were the same in every observed build; changing them would flip quad diagonals. Triangles
#     start at their lowest-rank corner;
#   * vertex normals by Blender's own rule (as export/4), computed on temporary copies of the evaluated mesh whose
#     vertices are in canonical order and whose polygons are sorted (canonical_polygons), so the build's polygon and
#     vertex order cannot change a bit. Two copies: one with the rounded positions (noise-free, but on near-degenerate
#     garment geometry its normals turn by up to 170 deg) and one with the unrounded positions (exact, but ulp noise
#     in a position reaches its neighbours' normals). Per vertex the rounded one is written when the two are within
#     NORMAL_SWITCH_DEG, otherwise the unrounded one: the noisy regions (ears, lids) get noise-free normals,
#     near-degenerate ones keep Blender's exact normal, and no normal is more than NORMAL_SWITCH_DEG from export/4's;
#   * each exported part lists its vertices in canonical order; triangles rotated to start at their lowest index
#     (winding kept) and sorted; morph vertex lists follow the new order;
#   * the manifest leaves out the .blend's byte hash (the .blend bytes are not reproducible).


def quantise(a, grid=GRID_M):
    """Rounds to multiples of grid; -0.0 becomes +0.0 (noise around 0 must not leave a sign bit)."""
    return np.round(np.asarray(a, dtype=np.float64) / grid) * grid + 0.0


def _dense_rank(rows):
    """Dense rank of each row of a 2-D array (lexicographic, exact comparison)."""
    if not len(rows):
        return np.zeros(0, np.int64)
    order = np.lexsort(rows.T[::-1])
    srt = rows[order]
    new = np.r_[True, (srt[1:] != srt[:-1]).any(axis=1)]
    rank = np.empty(len(rows), np.int64)
    rank[order] = np.cumsum(new) - 1
    return rank


def canonical_rank(record, edges):
    """Canonical rank (0..n-1) of every vertex: vertices sorted by their record (n x k float64, compared exactly);
    ties between identical records are separated by colour refinement over the edge neighbourhood (edges: m x 2).
    Returns (rank, ties left): ties left > 0 counts vertices indistinguishable even by their neighbourhood, which
    keep their input order (reported; none in the current characters)."""
    n = len(record)
    cls = _dense_rank(record)
    if n and len(np.unique(cls)) < n and len(edges):
        nbr = [[] for _ in range(n)]
        for a, b in edges.tolist():
            nbr[a].append(b)
            nbr[b].append(a)
        for _ in range(16):
            keys = [(int(cls[i]), tuple(sorted(int(cls[j]) for j in nbr[i]))) for i in range(n)]
            sig = {k: i for i, k in enumerate(sorted(set(keys)))}
            new = np.array([sig[k] for k in keys], np.int64)
            if len(np.unique(new)) == len(np.unique(cls)):
                break
            cls = new
            if len(np.unique(cls)) == n:
                break
    order = np.lexsort((np.arange(n), cls))
    rank = np.empty(n, np.int64)
    rank[order] = np.arange(n)
    return rank, int(n - len(np.unique(cls)))


def canonical_polygons(loop_vert, loop_start, loop_total, rank):
    """Polygons as rank tuples in canonical order: sorted by the polygon rotated to its lowest rank (winding kept).
    Triangles start at their lowest rank; quads and n-gons keep their own start corner: it decides how Blender splits
    them into triangles (and so export/4's triangles), and the builds keep it (only the polygon order varies;
    docs/evaluation/characters/T-056)."""
    polys = []
    lv = rank[loop_vert].tolist()
    for s0, t in zip(loop_start.tolist(), loop_total.tolist()):
        p = lv[s0:s0 + t]
        r = p.index(min(p))
        rot = tuple(p[r:] + p[:r])
        polys.append((rot, rot if t == 3 else tuple(p)))
    polys.sort()
    return [p for _, p in polys]


def canonical_triangles(tri):
    """Triangles rotated to start at their lowest index (winding kept), sorted lexicographically."""
    if not len(tri):
        return tri
    r = np.argmin(tri, axis=1)
    t = np.take_along_axis(tri, (np.arange(3)[None, :] + r[:, None]) % 3, axis=1)
    return t[np.lexsort(t.T[::-1])]


def blender_normals(co_local, polys, rank):
    """Blender's vertex normals (object space, unit) of a mesh rebuilt in canonical order: co_local (n x 3, the
    evaluated positions as Blender stores them) placed at their ranks, polygons from canonical_polygons. Returned in
    the original vertex order."""
    n = len(co_local)
    pos = np.empty((n, 3), np.float32)
    pos[rank] = co_local
    t = bpy.data.meshes.new("ps_export_canonical_tmp")
    try:
        t.vertices.add(n)
        t.vertices.foreach_set("co", pos.ravel())
        flat = np.array([v for p in polys for v in p], np.int32)
        sizes = np.array([len(p) for p in polys], np.int32)
        t.loops.add(len(flat))
        t.loops.foreach_set("vertex_index", flat)
        t.polygons.add(len(polys))
        t.polygons.foreach_set("loop_start", (np.cumsum(sizes) - sizes).astype(np.int32))
        t.update()
        nrm = np.empty(n * 3, np.float32)
        t.vertices.foreach_get("normal", nrm)
    finally:
        bpy.data.meshes.remove(t)
    return nrm.reshape(n, 3)[rank]


def to_engine(v):
    v = np.asarray(v, dtype=np.float64)
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], axis=-1)


def expand_profile(p):
    """Mirror-expands '.L' role entries (engine suffix -> source suffix) to the right side."""
    (el, er), (sl, sr) = p["mirror"]["engine"], p["mirror"]["source"]
    roles = {}
    for role, src in p["roles"].items():
        roles[role] = src
        if role.endswith(el):
            roles[role[: -len(el)] + er] = src[: -len(sl)] + sr if src.endswith(sl) else src.replace(sl, sr)
    chains = []
    for ch in p.get("contiguous_chains", []):
        chains.append(ch)
        if all(r.endswith(el) for r in ch):
            chains.append([r[: -len(el)] + er for r in ch])
    return roles, chains


def capabilities(roles_present, has_morphs, behaviours, expressions=()):
    out = {}
    for name, b in behaviours.items():
        missing = [r for r in b.get("roles", []) if r not in roles_present]
        alt = b.get("or_expression") in expressions
        if b.get("roles_any") and not any(r in roles_present for r in b["roles_any"]) and not alt:
            missing += ["any of " + "/".join(b["roles_any"]) + (f" or expression '{b['or_expression']}'" if b.get("or_expression") else "")]
        if b.get("morphs") and not has_morphs:
            missing.append("morph targets")
        out[name] = {"data": "available" if not missing else "missing", "missing": missing,
                     "tested": "see docs/ENGINE_CHARACTER_PACKAGE.md (behaviour support table)"}
    return out


def export_dynamics(rig, engine_name, deform_names):
    """Package "dynamics" block (engine axes, engine bone names) from the rig's "ps_dynamics" metadata (written by a
    shared generator such as groom/1); None when the rig has none. A chain or collider naming a bone that is not
    exported fails the export (the engine would reject the package)."""
    raw = rig.get("ps_dynamics")
    if not raw:
        return None
    d = json.loads(raw)
    # metadata is in Blender world coordinates (rest pose), as the exported bone heads (M @ head_local)
    P = lambda p: [round(float(x), 6) for x in to_engine(np.array(p))]  # noqa: E731
    for ch in d["chains"]:
        for b in ch["bones"]:
            if b not in deform_names:
                raise SystemExit(f"dynamics chain {ch['name']}: bone {b} is not a deform bone")
    out = {k: d[k] for k in ("enabled", "substep_hz", "preroll_s") if k in d}
    out["colliders"] = []
    for c in d.get("colliders", []):
        if c["bone"] not in deform_names:
            raise SystemExit(f"dynamics collider {c['name']}: bone {c['bone']} is not a deform bone")
        e = {"name": c["name"], "type": c["type"], "bone": engine_name[c["bone"]], "radius": float(c["radius"])}
        if c["type"] == "sphere":
            e["centre"] = P(c["centre"])
        else:
            e["a"], e["b"] = P(c["a"]), P(c["b"])
        out["colliders"].append(e)
    out["chains"] = []
    for ch in d["chains"]:
        c = dict({k: v for k, v in ch.items() if k not in ("bones", "tip", "anchor")}, bones=[engine_name[b] for b in ch["bones"]],
                 tip=P(ch["tip"]))
        if "anchor" in ch:
            if ch["anchor"]["bone"] not in deform_names:
                raise SystemExit(f"dynamics chain {ch['name']}: anchor bone {ch['anchor']['bone']} is not a deform bone")
            c["anchor"] = {"bone": engine_name[ch["anchor"]["bone"]], "weights": ch["anchor"]["weights"]}
        out["chains"].append(c)
    return out


def sphere_fit(P):
    """Least-squares sphere through points (N x 3): (centre, radius, rms residual)."""
    A = np.c_[2.0 * P, np.ones(len(P))]
    x = np.linalg.lstsq(A, (P * P).sum(axis=1), rcond=None)[0]
    c = x[:3]
    r = float(np.sqrt(max(x[3] + c @ c, 0.0)))
    return c, r, float(np.sqrt(np.mean((np.linalg.norm(P - c, axis=1) - r) ** 2)))


def eye_pivots(rig, root, skel_by_source, canonical=False):
    """Eye roles ("eye.*", the bones the engine aims) turn about the centre of the eyeball they carry (T-030).
    The eyeball is the most spherical mesh bound only to that bone and without shape keys (rms residual below 2 %
    of its radius; a lid shell fits worse than the ball). When the rig's bone head is elsewhere (a Rigify eye bone on the front of the ball),
    rotating about it swings the ball out of its socket while the eyes look around, so the exported head (the engine
    pivot) is moved to the ball's centre. Skinning stays exact: the engine's skin matrices are world transforms of
    the geometry, independent of the pivot. Returns the report; edits skel_by_source in place."""
    rep = {}
    M = rig.matrix_world
    for src, entry in skel_by_source.items():
        if not entry["name"].startswith("eye."):
            continue
        best = None
        for o in root.all_objects:
            if o.type != "MESH" or o.data.shape_keys is not None or len(o.data.vertices) < 16:
                continue
            if not any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers):
                continue
            used = {o.vertex_groups[g.group].name for v in o.data.vertices for g in v.groups if g.weight > 0}
            if used != {src}:
                continue
            mw = o.matrix_world
            P = np.array([tuple(mw @ v.co) for v in o.data.vertices])
            if canonical:  # export/5: the fit must not depend on the vertex order
                P = P[np.lexsort(P.T[::-1])]
            c, r, res = sphere_fit(P)
            if r > 0 and res < 0.02 * r and (best is None or res / r < best[0]):
                best = (res / r, c, r, o.name)
        if best is None:
            continue
        old = np.array(entry["head"])
        new = to_engine(best[1])
        moved = float(np.linalg.norm(new - old))
        if moved > 1e-5:
            entry["head"] = [round(float(x), 6) for x in new]
            rep[entry["name"]] = {"object": best[3], "radius_m": round(best[2], 5), "moved_mm": round(moved * 1000, 3),
                                  "rig_head": [round(float(x), 6) for x in old]}
    return rep


# ---- export/6: the character's collision body (T-047) ----
# The same fit as engine/scene/collision.cpp deriveCollisionBody (the engine derives it for packages without this
# block; the block freezes it with the character version). Engine axes and names; points relative to the carrying
# bone's rest head. Inputs: the exported skeleton (engine names, parents, heads) and per mesh the exported rest
# positions (engine axes, float32 as written), joints and weights.
COLLISION_MARGIN = 0.005
LIMB_RADIUS_QUANTILE = 0.5


def _quantile(v, q, fallback, min_count=20):
    v = np.asarray(v, dtype=np.float32)
    if len(v) < min_count:
        return np.float32(fallback)
    k = min(len(v) - 1, int(np.float32(q) * np.float32(len(v) - 1)))
    return np.partition(v, k)[k]


def collision_block(skel, mesh_arrays):
    names = [b["name"] for b in skel]
    idx = {n: i for i, n in enumerate(names)}
    par = [idx[b["parent"]] if b["parent"] is not None else -1 for b in skel]
    head = np.array([b["head"] for b in skel], dtype=np.float32)

    def finger(n):
        return len(n) >= 4 and ((n[0] == "f" and n[1].isdigit()) or n.startswith("thumb"))

    def region(b):  # 0 other, 1 torso, 2 arm L, 3 arm R, 4 leg, 5 head
        while b >= 0:
            n = names[b]
            if n.startswith(("upperArm.", "forearm.", "hand.")) or (finger(n) and "." in n):
                return 2 if n.endswith("L") else 3
            if n.startswith(("thigh.", "shin.", "foot.", "toe")):
                return 4
            if n in ("neck", "head") or n.startswith("eye."):
                return 5
            if n in ("hips", "spine", "chest"):
                return 1
            b = par[b]
        return 0

    def part(b):  # 0 none, 1 upper, 2 fore, 3 hand
        while b >= 0:
            n = names[b]
            if n.startswith("hand.") or finger(n):
                return 3
            if n.startswith("forearm."):
                return 2
            if n.startswith("upperArm."):
                return 1
            b = par[b]
        return 0
    for r in ("hips", "chest", "hand.L", "hand.R"):
        if r not in idx:
            return None
    hips, chest = idx["hips"], idx["chest"]
    spine, neck = idx.get("spine", -1), idx.get("neck", -1)
    hand = [idx["hand.L"], idx["hand.R"]]
    fore = [par[h] for h in hand]
    upper = [par[f] if f >= 0 else -1 for f in fore]
    if min(upper) < 0:
        return None
    reg = np.array([region(b) for b in range(len(names))])
    prt = np.array([part(b) for b in range(len(names))])
    torso, fores, hands = [], [[], []], [[], []]
    for P, J, W in mesh_arrays:
        J = J.astype(np.int64)
        valid = (J >= 0) & (J < len(names)) & (W > 0)
        Jc = np.clip(J, 0, len(names) - 1)
        w = np.zeros((len(P), 6), dtype=np.float32)
        wp = np.zeros((len(P), 2, 4), dtype=np.float32)
        for k in range(J.shape[1]):
            wk = np.where(valid[:, k], W[:, k], 0).astype(np.float32)
            r = reg[Jc[:, k]]
            np.add.at(w, (np.arange(len(P)), r), wk)
            for s, rr in ((0, 2), (1, 3)):
                m = r == rr
                np.add.at(wp, (np.arange(len(P))[m], s, prt[Jc[m, k]]), wk[m])
        torso.append(P[w[:, 1] >= 0.9])
        ok = (w[:, 5] + w[:, 4]) < 0.1
        for s in range(2):
            fores[s].append(P[ok & (wp[:, s, 2] >= 0.5)])
            hands[s].append(P[ok & (wp[:, s, 3] >= 0.5)])
    torso = np.concatenate(torso) if torso else np.zeros((0, 3), np.float32)
    shoulder_half = np.float32(0.5) * np.float32(np.linalg.norm(head[upper[0]] - head[upper[1]]))
    r_default = np.float32(0.95) * shoulder_half
    sections = []

    def norm(v):
        return v / np.float32(np.linalg.norm(v))

    def band(name, bone, a, b):
        u = norm(b - a)
        e1 = norm(np.array([1, 0, 0], np.float32) - u * u[0])
        e2 = norm(np.cross(e1, u))
        ab = b - a
        t = (torso - a) @ ab / np.float32(ab @ ab)
        sel = (t >= 0) & (t <= 1)
        d = torso[sel] - (a + t[sel, None] * ab)
        front = d @ e2
        keep = front >= 0
        side = np.abs(d[keep] @ e1)
        r1 = float(np.clip(_quantile(side, 0.99, r_default), 0.02, 0.5))
        r2 = float(np.clip(_quantile(front[keep], 0.99, r_default), 0.02, 0.5))
        sections.append({"name": name, "bone": names[bone], "p0": (a - head[bone]).tolist(), "p1": (b - head[bone]).tolist(),
                         "e1": e1.tolist(), "e2": e2.tolist(), "r1": r1, "r2": r2, "cap0": False, "cap1": False})
    top = head[neck] if neck >= 0 else head[chest] + np.array([0, 0.6 * shoulder_half, 0], np.float32)
    bottom = head[hips] + np.float32(0.4) * (head[hips] - head[chest])

    def bands(name, bone, a, b, n):
        for i in range(n):
            band(f"{name}_{i + 1}", bone, a + (b - a) * np.float32(i / n), a + (b - a) * np.float32((i + 1) / n))
    bands("pelvis", hips, bottom, head[hips], 2)
    bands("torso_lower", spine if spine >= 0 else hips, head[hips], head[chest], 3)
    bands("torso_upper", chest, head[chest], top, 2)
    sections[0]["cap0"] = True
    sections[-1]["cap1"] = True
    limbs = []
    # (the rest-pose clearance fix of the engine fit is applied by the engine when it loads the block's limbs only if
    # they come from its own derivation; here the same loop runs on the same numbers)
    sec_np = [(idx[s["bone"]], np.array(s["p0"], np.float32), np.array(s["p1"], np.float32), np.array(s["e1"], np.float32),
               np.array(s["e2"], np.float32), np.float32(s["r1"]), np.float32(s["r2"]), s["cap0"], s["cap1"]) for s in sections]

    def section_gap(sec, p):  # rest frames: the bone's global is a translation to its head
        bone, p0, p1, e1, e2, r1, r2, c0, c1 = sec
        u = p1 - p0
        L = np.float32(np.linalg.norm(u))
        u = u / L if L > 1e-6 else norm(np.cross(e1, e2))
        r = min(r1, r2)
        s1, s2 = r / r1, r / r2
        q0 = (p - head[bone]) - p0
        qx, qy, qz = np.float32(q0 @ u), np.float32(q0 @ e1) * s1, np.float32(q0 @ e2) * s2
        radial = np.float32(np.hypot(qy, qz))
        ax = -qx if qx < 0 else (qx - L if qx > L else np.float32(0))
        rnd = (qx < 0 and c0) or (qx > L and c1)
        if ax <= 0 or rnd:
            return float(np.linalg.norm([qx - np.clip(qx, 0, L), qy, qz]) - r)
        ro = max(radial - r, 0.0)
        return float(np.sqrt(ro * ro + ax * ax))

    def seg_gap(a, b, r):
        return min(section_gap(sec, a + (b - a) * np.float32(i / 8)) - r for i in range(9) for sec in sec_np)
    for s, side in enumerate("LR"):
        e, wr = head[fore[s]], head[hand[s]]
        fore_len = np.float32(np.linalg.norm(wr - e))
        fr = [head[idx[f"f{k}a.{side}"]] for k in range(4) if f"f{k}a.{side}" in idx]
        d = (np.mean(fr, axis=0).astype(np.float32) - wr) if fr else (wr - e)
        d = norm(d) if np.linalg.norm(d) > 1e-6 else norm(wr - e)
        uf = norm(wr - e)
        F = np.concatenate(fores[s]) if fores[s] else np.zeros((0, 3), np.float32)
        H = np.concatenate(hands[s]) if hands[s] else np.zeros((0, 3), np.float32)

        def radial(P, o, u, t0, t1):
            t = (P - o) @ u
            sel = (t >= t0) & (t <= t1)
            return np.linalg.norm((P[sel] - o) - u * t[sel, None], axis=1), t[sel]
        t0 = np.float32(0.5)
        rf, _ = radial(F, e, uf, t0 * fore_len, fore_len)
        f_r = float(np.clip(_quantile(rf, LIMB_RADIUS_QUANTILE, np.float32(0.18) * fore_len, 10), 0.008, 0.08))
        hand_len = max(np.float32(0.02), np.float32(0.75) * fore_len)
        rh, along = radial(H, wr, d, -0.01, 2.0 * hand_len)
        h_r = float(np.clip(_quantile(rh, LIMB_RADIUS_QUANTILE, np.float32(0.3) * hand_len, 10), 0.008, 0.06))
        tip = max(h_r + 0.005, float(_quantile(along, 0.98, hand_len, 10)))
        hb = d * np.float32(max(0.005, tip - h_r))
        while seg_gap(e + uf * (t0 * fore_len), wr, f_r) < COLLISION_MARGIN and t0 < 0.85:
            t0 = np.float32(t0 + 0.05)
        r0 = f_r
        while seg_gap(e + uf * (t0 * fore_len), wr, f_r) < COLLISION_MARGIN and f_r > 0.6 * r0:
            f_r -= 0.001
        r0 = h_r
        while seg_gap(wr, wr + hb, h_r) < COLLISION_MARGIN and h_r > 0.6 * r0:
            h_r -= 0.001
        f_allow = min(0.0, seg_gap(e + uf * (t0 * fore_len), wr, f_r) - COLLISION_MARGIN)
        h_allow = min(0.0, seg_gap(wr, wr + hb, h_r) - COLLISION_MARGIN)
        limbs.append({"name": f"forearm.{side}", "bone": names[fore[s]], "side": side, "a": (uf * (t0 * fore_len)).tolist(),
                      "b": (uf * fore_len).tolist(), "r": float(np.float32(f_r)), "allowance": f_allow})
        limbs.append({"name": f"hand.{side}", "bone": names[hand[s]], "side": side, "a": [0.0, 0.0, 0.0],
                      "b": hb.tolist(), "r": float(np.float32(h_r)), "allowance": h_allow})
    rnd = lambda v: [round(float(x), 6) for x in v]  # noqa: E731
    for sct in sections:
        for k in ("p0", "p1", "e1", "e2"):
            sct[k] = rnd(sct[k])
        sct["r1"], sct["r2"] = round(sct["r1"], 6), round(sct["r2"], 6)
    for lb in limbs:
        lb["a"], lb["b"], lb["r"], lb["allowance"] = rnd(lb["a"]), rnd(lb["b"]), round(lb["r"], 6), round(lb["allowance"], 6)
    return {"format": "plush.collision_body", "version": 1, "margin": COLLISION_MARGIN, "sections": sections, "limbs": limbs}


def main():
    argv =sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--collection", default="")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit("--out must be new or empty")
    os.makedirs(out, exist_ok=True)
    prof = json.load(open(a.profile))
    behaviours = json.load(open(os.path.join(HERE, "rig_profiles", "engine_behaviours.json")))["behaviours"]
    roles, chains = expand_profile(prof)
    src_sha = hashlib.sha256(open(a.blend, "rb").read()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    root = bpy.data.collections.get(a.collection) if a.collection else next(
        (c for c in bpy.data.collections if c.get("ps_character_id")), None)
    if root is None:
        raise SystemExit("character root collection not found (give --collection)")
    versions = version_record(root)  # fails before any work when the spec pins another exporter version
    out_version = versions["generators"]["exporter"].split("/")[1]
    canonical = out_version != "4"  # export/5 (T-056); export/4 keeps its released code path
    rigs = [o for o in root.all_objects if o.type == "ARMATURE"]
    if len(rigs) != 1:
        raise SystemExit(f"expected one armature in {root.name}, found {len(rigs)}")
    rig = rigs[0]
    rig.data.pose_position = "REST"  # rest geometry; the file is never saved
    bpy.context.view_layer.update()
    M = rig.matrix_world
    deform = [b for b in rig.data.bones if b.use_deform]
    dnames = {b.name for b in deform}
    src_to_role = {}
    for role, src in roles.items():
        if src in dnames:
            src_to_role[src] = role
    missing_req = [r for r in prof["required_roles"] if r not in roles or roles[r] not in dnames]
    if missing_req:
        raise SystemExit(f"required roles missing for profile {prof['profile']}: {missing_req}")

    def deform_parent(b):
        p = b.parent
        while p is not None and not p.use_deform:
            p = p.parent
        if p is not None:
            return p.name
        # No deform ancestor (T-030). Rigify hangs some deform bones under mechanism/original bones only
        # (DEF-eye.L -> ORG-eye.L -> ORG-spine.006 -> ..., DEF-shoulder.L -> ORG-shoulder.L -> ORG-spine.003 -> ...).
        # Blender carries them with the deform twin of such an ancestor (ORG-x/MCH-x follow DEF-x), so that twin is
        # the engine parent. Without it these bones were engine roots: eyes stayed in character space while the head
        # moved (up to 60 mm off the sockets in e905) and the shoulder girdle did not follow the chest.
        p = b.parent
        while p is not None:
            if "-" in p.name:
                twin = rig.data.bones.get("DEF-" + p.name.split("-", 1)[1])
                if twin is not None and twin.use_deform and twin != b and b.name not in {x.name for x in twin.parent_recursive}:
                    return twin.name
            p = p.parent
        return None
    parent = {b.name: deform_parent(b) for b in deform}
    reparented = []
    role_to_src = {v: k for k, v in src_to_role.items()}
    for ch in chains:
        for prev, cur in zip(ch, ch[1:]):
            if prev in role_to_src and cur in role_to_src:
                s_cur, s_prev = role_to_src[cur], role_to_src[prev]
                if parent[s_cur] != s_prev:
                    reparented.append({"bone": cur, "from": parent[s_cur], "to": prev,
                                       "reason": "contiguous chain for engine two-bone IK"})
                    parent[s_cur] = s_prev
    # order: parents before children
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        if parent[n] is not None:
            visit(parent[n])
        seen.add(n)
        order.append(n)
    for b in deform:
        visit(b.name)
    rig_specific = set(prof.get("rig_specific_bones", []))
    engine_name = {n: src_to_role.get(n, n) for n in order}
    index = {n: i for i, n in enumerate(order)}
    skel = []
    for n in order:
        b = rig.data.bones[n]
        kind = "role" if n in src_to_role else ("rig_specific" if n in rig_specific else "helper")
        skel.append({"name": engine_name[n], "source_name": n, "kind": kind,
                     "parent": engine_name[parent[n]] if parent[n] else None,
                     "head": [round(float(x), 6) for x in to_engine(M @ b.head_local)]})

    pivots = eye_pivots(rig, root, {s["source_name"]: s for s in skel}, canonical)

    blob = bytearray()

    def put(arr, dtype):
        nonlocal blob
        arr = np.ascontiguousarray(arr, dtype=dtype)
        off = len(blob)
        blob += arr.tobytes()
        return {"offset": off, "count": int(arr.size), "dtype": np.dtype(dtype).name}
    meshes, morphs, mats, problems = [], [], {}, []
    collision_meshes = [] if out_version == EXPORTER_COLLISION else None  # export/6 only
    canon_report = {"ties_left": {}, "unrounded_normals": {}}
    deps = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in root.all_objects if o.type == "MESH" and not o.name.startswith(("WGT-", "LM_"))
            and any(m.type == "ARMATURE" for m in o.modifiers) and not o.get("ps_collision_proxy")]
    skipped = sorted(o.name for o in root.all_objects if o.type == "MESH" and o not in objs and not o.name.startswith("WGT-"))
    for o in sorted(objs, key=lambda o: o.name):
        # A garment body mask (garment/1) hides covered faces; export keeps all vertices and drops those faces.
        masks = [m for m in o.modifiers if m.type == "MASK" and m.mode == "VERTEX_GROUP" and m.show_viewport
                 and m.vertex_group in o.vertex_groups]
        hidden_verts = None
        if masks:
            hidden_verts = set()
            for m in masks:
                gidx = o.vertex_groups[m.vertex_group].index
                member = {v.index for v in o.data.vertices if any(g.group == gidx and g.weight > 0 for g in v.groups)}
                hidden_verts |= member if m.invert_vertex_group else {v.index for v in o.data.vertices} - member
                m.show_viewport = False
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        n = len(me.vertices)
        if n != len(o.data.vertices):
            problems.append(f"{o.name}: evaluated vertex count differs from base mesh; skipped")
            ev.to_mesh_clear()
            for m in masks:
                m.show_viewport = True
            continue
        mw = o.matrix_world
        co = np.array([mw @ v.co for v in me.vertices])
        nm3 = mw.to_3x3().inverted().transposed()
        if canonical:
            co = quantise(co)
            co_local = np.empty(n * 3, np.float32)
            me.vertices.foreach_get("co", co_local)
            lv = np.empty(len(me.loops), np.int64)
            me.loops.foreach_get("vertex_index", lv)
            ls = np.empty(len(me.polygons), np.int64)
            lt = np.empty(len(me.polygons), np.int64)
            me.polygons.foreach_get("loop_start", ls)
            me.polygons.foreach_get("loop_total", lt)
            nxt = np.arange(len(lv)) + 1
            nxt[ls + lt - 1] = ls
            edges = np.stack([lv, lv[nxt]], axis=1)
            co_local = co_local.reshape(n, 3)
        else:
            nrm = np.array([(nm3 @ v.normal).normalized() for v in me.vertices])
        me.calc_loop_triangles()
        tri = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64).reshape(-1, 3)
        tmat = np.array([t.material_index for t in me.loop_triangles], dtype=np.int64)
        ev.to_mesh_clear()
        if masks:
            if hidden_verts:
                keep = ~np.isin(tri, np.array(sorted(hidden_verts), dtype=np.int64)).any(axis=1)
                tri, tmat = tri[keep], tmat[keep]
            for m in masks:
                m.show_viewport = True
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
        # skin weights: deform-bone groups only, top 4, normalised
        gi = {g.index: g.name for g in o.vertex_groups if g.name in index}
        J = np.zeros((n, 4), np.uint16)
        W = np.zeros((n, 4), np.float32)
        zero = 0
        for v in o.data.vertices:
            ws = sorted(((g.weight, index[gi[g.group]]) for g in v.groups if g.group in gi and g.weight > 0), reverse=True)[:4]
            s = sum(w for w, _ in ws)
            if s <= 0:
                zero += 1
                continue
            if canonical:
                q = [int(np.round(w / s * WEIGHT_STEPS)) for w, _ in ws]
                q[0] += WEIGHT_STEPS - sum(q)  # exact sum; the largest influence absorbs the rounding
                ws = sorted(((qi, j) for qi, (_, j) in zip(q, ws) if qi > 0), key=lambda x: (-x[0], x[1]))
                ws, s = [(qi / WEIGHT_STEPS, j) for qi, j in ws], 1.0
            for k, (w, j) in enumerate(ws):
                J[v.index, k], W[v.index, k] = j, w / s
        if zero:
            problems.append(f"{o.name}: {zero} vertices without deform weights")
        keys = []
        if o.data.shape_keys:
            kb = o.data.shape_keys.key_blocks
            basis = np.array([v.co for v in kb[0].data])
            for k in kb[1:]:
                d = np.array([v.co for v in k.data]) - basis
                d = (np.array(mw.to_3x3()) @ d.T).T
                keys.append((k.name, quantise(d, DELTA_GRID_M) if canonical else d))
        if canonical:
            # canonical vertex rank: rounded position, joints, weights, rounded morph deltas (shape key order)
            rec = np.hstack([co, J.astype(np.float64), W.astype(np.float64)] + [d for _, d in keys])
            rank, ties = canonical_rank(rec, edges)
            if ties:
                canon_report["ties_left"][o.name] = ties
            polys = canonical_polygons(lv, ls, lt, rank)
            n_raw = blender_normals(co_local, polys, rank).astype(np.float64)
            n_q = blender_normals(quantise(co_local).astype(np.float32), polys, rank).astype(np.float64)
            use_q = (n_raw * n_q).sum(axis=1) >= np.cos(np.radians(NORMAL_SWITCH_DEG))
            canon_report["unrounded_normals"][o.name] = int((~use_q).sum())
            nl = np.where(use_q[:, None], n_q, n_raw)
            nrm = (np.array(nm3, dtype=np.float64) @ nl.T).T
            ln = np.linalg.norm(nrm, axis=1, keepdims=True)
            nrm = np.divide(nrm, ln, out=np.zeros_like(nrm), where=ln > 0)
        for mi in sorted(set(tmat.tolist())) if len(tmat) else []:
            t = tri[tmat == mi]
            used = np.unique(t)
            if canonical:
                used = used[np.argsort(rank[used], kind="stable")]
            remap = -np.ones(n, np.int64)
            remap[used] = np.arange(len(used))
            slot = o.material_slots[mi].material if mi < len(o.material_slots) else None
            mname = slot.name if slot else "__default"
            if slot and mname not in mats:
                p = slot.node_tree.nodes.get("Principled BSDF") if slot.node_tree else None
                bc = list(p.inputs["Base Color"].default_value)[:3] if p else list(slot.diffuse_color)[:3]
                mats[mname] = {"name": mname, "baseColor": [round(float(c), 5) for c in bc],
                               "roughness": round(float(p.inputs["Roughness"].default_value), 4) if p else 0.5,
                               "sheen": round(float(p.inputs["Sheen Weight"].default_value), 4) if p and "Sheen Weight" in p.inputs else 0.0}
            mi_index = len(meshes)
            if collision_meshes is not None:
                collision_meshes.append((to_engine(co[used]).astype(np.float32), J[used], W[used].astype(np.float32)))
            meshes.append({"part": o.name if len(set(tmat.tolist())) == 1 else f"{o.name}#{mi}", "source_object": o.name,
                           "material": mname, "vertices": int(len(used)),
                           "positions": put(to_engine(co[used]), np.float32), "normals": put(to_engine(nrm[used]), np.float32),
                           "indices": put((canonical_triangles(remap[t]) if canonical else remap[t]).reshape(-1), np.uint32),
                           "joints": put(J[used], np.uint16),
                           "weights": put(W[used], np.float32)})
            for kname, d in keys:
                dd = to_engine(d[used])
                nz = (np.nonzero(np.abs(dd).max(axis=1) > 0)[0] if canonical
                      else np.nonzero(np.linalg.norm(dd, axis=1) > 1e-7)[0])
                if len(nz):
                    morphs.append({"name": kname, "mesh": mi_index, "vertices": put(nz, np.uint32),
                                   "dpos": put(dd[nz], np.float32)})
    if problems:
        raise SystemExit("export problems: " + "; ".join(problems))
    open(os.path.join(out, "geometry.bin"), "wb").write(bytes(blob))
    present = set(src_to_role.values())
    # engine expression -> morph: the rig profile's map, extended per character by the face system
    # (collection property ps_engine_expressions, JSON; written by face_generic). No engine change is involved.
    expr_map = {**prof.get("expressions", {}), **json.loads(root.get("ps_engine_expressions", "{}") or "{}")}
    # Facial metadata written by the face system (optional; the engine validates it):
    #  morph_inbetweens: "<base>@<pct>" morphs form a piecewise chain towards <base> (rotation-like shapes, e.g. blink)
    #  expression_bones: bone rotations driven by an expression weight (axis converted to engine axes)
    #  blink: the character's blink timing
    names = {m["name"] for m in morphs}
    inbetweens = {}
    for n in sorted(names):
        base, _, pct = n.rpartition("@")
        if base and pct.isdigit() and base in names:
            inbetweens.setdefault(base, []).append([int(pct) / 100.0, n])
    inbetweens = {k: sorted(v) for k, v in inbetweens.items()}
    expr_bones, expr_bones_missing = {}, []
    for morph, lst in json.loads(root.get("ps_expression_bones", "{}") or "{}").items():
        if morph not in names:
            continue
        for e in lst:
            b = rig.data.bones.get(e["bone"])
            if b is None or not b.use_deform:
                expr_bones_missing.append(f"{morph}: {e['bone']}")
                continue
            ax = (rig.matrix_world.to_3x3() @ b.matrix_local.to_3x3() @ Vector(e["axis_local"])).normalized()
            expr_bones.setdefault(morph, []).append({"bone": engine_name.get(e["bone"], e["bone"]),
                                                     "axis": [round(float(v), 6) for v in to_engine(np.array([ax]))[0]],
                                                     "degrees": float(e["degrees"])})
    blink_timing = json.loads(root.get("ps_blink_timing", "{}") or "{}")
    # Clip retarget data, generated from the role pivots with the profile's reference-pose rules (the engine derives
    # the same numbers from the skeleton for packages without this block).
    retarget = None
    if "reference_pose" in prof:
        retarget = RT.derive({s["name"]: s["head"] for s in skel}, RT.reference_pose(prof["reference_pose"]))
        retarget["profile"] = prof["profile"]
    dynamics = export_dynamics(rig, engine_name, dnames)
    collision = collision_block(skel, collision_meshes) if collision_meshes is not None else None
    if collision_meshes is not None and collision is None:
        raise SystemExit("export/6: the skeleton lacks the roles of a collision body (hips, chest, both arm chains)")
    man = {"format": FORMAT, "version": VERSION, "name": root.get("ps_character_id", root.name),
           "source": {"blend": os.path.basename(a.blend), **({} if canonical else {"blend_sha256": src_sha}),
                      "spec_sha256": root.get("ps_spec_sha256"),
                      "spec_version": root.get("ps_spec_version"), "blender": bpy.app.version_string},
           "profile": {"name": prof["profile"], "kind": prof["kind"], "required_roles": prof["required_roles"]},
           "coordinates": "metres; +Y up; character faces +Z; converted from Blender (x, y, z) -> (x, z, -y)",
           "skeleton": skel, "reparented": reparented, **({"eye_pivots": pivots} if pivots else {}), "roles_present": sorted(present),
           "rig_specific_bones": [s["name"] for s in skel if s["kind"] == "rig_specific"],
           "materials": list(mats.values()), "meshes": meshes, "morphs": morphs,
           "morph_names": sorted({m["name"] for m in morphs}),
           **({"morph_inbetweens": inbetweens} if inbetweens else {}),
           **({"expression_bones": expr_bones} if expr_bones else {}),
           **({"expression_bones_missing": expr_bones_missing} if expr_bones_missing else {}),
           **({"blink": {k: blink_timing[k] for k in ("close_s", "hold_s", "open_s", "mean_interval_s") if k in blink_timing}} if blink_timing else {}),
           "expressions": {k: v for k, v in expr_map.items() if v in {m["name"] for m in morphs}},
           "expressions_missing": sorted(k for k, v in expr_map.items() if v not in {m["name"] for m in morphs}),
           "capabilities": capabilities(present, bool(morphs), behaviours,
                                        {k for k, v in expr_map.items() if v in {m["name"] for m in morphs}}),
           **({"walk": prof["walk"]} if "walk" in prof else {}), **({"hands": prof["hands"]} if "hands" in prof else {}),
           **({"retarget": retarget} if retarget else {}), **({"dynamics": dynamics} if dynamics else {}),
           **({"collision": collision} if collision else {}),
           "exporter_version": out_version, "versions": versions,
           "discarded": prof.get("discarded", []) + ([f"meshes without armature (not exported): {skipped}"] if skipped else []),
           "files": {"geometry.bin": {"bytes": len(blob), "sha256": hashlib.sha256(bytes(blob)).hexdigest()}}}
    json.dump(man, open(os.path.join(out, "character.json"), "w"), indent=1)
    print(f"[export_engine] {man['name']}: {len(skel)} bones ({len(present)} roles, {len(man['rig_specific_bones'])} rig-specific), "
          f"{len(meshes)} meshes, {len(morphs)} morph blocks, {len(blob) / 1e6:.1f} MB -> {out}")
    if canonical:
        print(f"[export_engine] export/{out_version} canonical: {json.dumps(canon_report, sort_keys=True)}")


if __name__ == "__main__":  # Blender -P runs this file as __main__; importing it (tests) only defines the functions
    main()
