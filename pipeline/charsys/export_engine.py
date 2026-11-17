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
EXPORTER_VERSION = "4"
GENERATOR_VERSIONS = (f"export/{EXPORTER_VERSION}",)
sys.path.insert(0, os.path.join(HERE, "..", "clips"))
import retarget as RT  # noqa: E402  (shared clip retargeting rules; pure Python)

sys.path.insert(0, HERE)
import versions as V  # noqa: E402  (per-feature generator versions; pure Python)


def version_record(root):
    """Generator pins of the master's embedded spec (versions.record); checks that it pins this exporter. Masters
    without an embedded spec (test data, older files) record only the exporter."""
    txt = bpy.data.texts.get("ps_character_spec.json")
    if txt is None:
        return {"generators": {"exporter": GENERATOR_VERSIONS[0]}, "embedded_spec": False}
    rec = V.record(json.loads(txt.as_string()))
    pinned = rec["generators"]["exporter"]
    if pinned not in GENERATOR_VERSIONS:
        raise V.VersionError(f"{root.get('ps_character_id', root.name)} pins exporter {pinned!r}; this exporter is "
                             f"{GENERATOR_VERSIONS[0]}")
    return rec


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


def eye_pivots(rig, root, skel_by_source):
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

    pivots = eye_pivots(rig, root, {s["source_name"]: s for s in skel})

    blob = bytearray()

    def put(arr, dtype):
        nonlocal blob
        arr = np.ascontiguousarray(arr, dtype=dtype)
        off = len(blob)
        blob += arr.tobytes()
        return {"offset": off, "count": int(arr.size), "dtype": np.dtype(dtype).name}
    meshes, morphs, mats, problems = [], [], {}, []
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
                keys.append((k.name, (np.array(mw.to_3x3()) @ d.T).T))
        for mi in sorted(set(tmat.tolist())) if len(tmat) else []:
            t = tri[tmat == mi]
            used = np.unique(t)
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
            meshes.append({"part": o.name if len(set(tmat.tolist())) == 1 else f"{o.name}#{mi}", "source_object": o.name,
                           "material": mname, "vertices": int(len(used)),
                           "positions": put(to_engine(co[used]), np.float32), "normals": put(to_engine(nrm[used]), np.float32),
                           "indices": put(remap[t].reshape(-1), np.uint32), "joints": put(J[used], np.uint16),
                           "weights": put(W[used], np.float32)})
            for kname, d in keys:
                dd = to_engine(d[used])
                nz = np.nonzero(np.linalg.norm(dd, axis=1) > 1e-7)[0]
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
    man = {"format": FORMAT, "version": VERSION, "name": root.get("ps_character_id", root.name),
           "source": {"blend": os.path.basename(a.blend), "blend_sha256": src_sha, "spec_sha256": root.get("ps_spec_sha256"),
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
           "exporter_version": EXPORTER_VERSION, "versions": versions,
           "discarded": prof.get("discarded", []) + ([f"meshes without armature (not exported): {skipped}"] if skipped else []),
           "files": {"geometry.bin": {"bytes": len(blob), "sha256": hashlib.sha256(bytes(blob)).hexdigest()}}}
    json.dump(man, open(os.path.join(out, "character.json"), "w"), indent=1)
    print(f"[export_engine] {man['name']}: {len(skel)} bones ({len(present)} roles, {len(man['rig_specific_bones'])} rig-specific), "
          f"{len(meshes)} meshes, {len(morphs)} morph blocks, {len(blob) / 1e6:.1f} MB -> {out}")


main()
