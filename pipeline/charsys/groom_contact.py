"""Hair contact (T-183, opt-in keys of groom/5): the ear keep-out of the built hair and the body colliders of the
secondary-motion chains. Library of groom_r6.py; nothing here runs for a hair spec without the two keys, so released
versions build exactly as before. Character-independent: bones, objects and every value are spec data.

spec.hair.ear_keepout   {"objects": ["ear.*"] (name patterns of the keep-out meshes, default shown),
                         "margin_m": 0..0.02 (default 0.003), "smooth": 0..24 (default 6),
                         "structures": [name patterns] (default: every hair mesh)}
    Hair surface vertices inside a keep-out mesh (or closer to it than margin_m) are moved out of it before the fibres
    are grown: along the head's front/back axis, whichever way out is shorter, so hair that crossed the ear ends in
    front of or behind it instead of on top of it. The move is spread over the neighbouring vertices (`smooth`
    relaxation passes) so the surface does not crease. Vertex counts, order and faces do not change: dynamics
    records, binding and the fibre layers stay valid.

spec.hair.dynamics.contact   {"colliders": [...], "segments": bool (default true), "anchored_gravity": bool (default
                         true), "structures": [chain group patterns] (default: every lock chain, no bun)}
    Body colliders for the hair chains, fitted at bind time from the meshes bound to the rig, and the engine's chain
    "contact" block (docs/SECONDARY_MOTION.md). A collider:
      {"name", "bone": "head" | "chest" | <rig deform bone>, "fit": "blob" | "limb",
       "groups": [vertex-group patterns] | "objects": [object-name patterns],
       "bones": [<bone>, ...] (limb: the axis runs from the head of the first to the tail of the last),
       "percentile": 1..100 (default blob 85, limb 50), "pad_m": -0.02..0.05 (default 0), "solid": bool (default false)}
    blob: a capsule along the principal axis of the vertices (hands, ears); limb: a capsule along the bone axis whose
    radius is that percentile of the vertices' distance to the axis. Vertices come from every non-hair mesh bound to
    the rig, where the listed groups carry at least half the weight ("groups"), or from the named objects ("objects").
    "solid": the collider pushes to its full radius (moving parts, e.g. hands); otherwise a chain may stay as close
    as its kinematic target is (parts the hair rests on). Chains outside "structures" keep their previous colliders.
"""
import fnmatch
import json
import math

CONTACT_PROP = "ps_contact"  # the contact spec, carried on the hair objects from build to bind
KEEPOUT_DEFAULT = {"objects": ["ear.*"], "margin_m": 0.003, "smooth": 6}
COLLIDER_KEYS = {"name", "bone", "fit", "groups", "objects", "bones", "percentile", "pad_m", "solid"}
CONTACT_KEYS = {"colliders", "segments", "anchored_gravity", "structures"}
KEEPOUT_KEYS = {"objects", "margin_m", "smooth", "structures"}


def has_keys(hair_spec):
    """True when the hair spec uses a T-183 key."""
    return isinstance(hair_spec, dict) and ("ear_keepout" in hair_spec or contact_spec(hair_spec) is not None)


def contact_spec(hair_spec):
    d = hair_spec.get("dynamics") if isinstance(hair_spec, dict) else None
    return d.get("contact") if isinstance(d, dict) and d.get("contact") is not None else None


def strip(hair_spec):
    """The hair spec without the T-183 keys (what the groom/4 path below validates and builds)."""
    if not has_keys(hair_spec):
        return hair_spec
    out = {k: v for k, v in hair_spec.items() if k != "ear_keepout"}
    if isinstance(out.get("dynamics"), dict) and "contact" in out["dynamics"]:
        out["dynamics"] = {k: v for k, v in out["dynamics"].items() if k != "contact"}
    return out


# -------------------------------------------------------------------------------------------------------- validation
def _patterns(v):
    return isinstance(v, list) and bool(v) and all(isinstance(x, str) and x for x in v)


def _num(d, k, lo, hi, default):
    v = d.get(k, default)
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= float(v) <= hi


def validate(hair_spec):
    """Errors in the T-183 keys of a hair spec (empty without them)."""
    errs = []
    ko = hair_spec.get("ear_keepout")
    if ko is not None:
        if not isinstance(ko, dict) or set(ko) - KEEPOUT_KEYS:
            errs.append("hair.ear_keepout must be {\"objects\", \"margin_m\", \"smooth\", \"structures\"}")
        else:
            if "objects" in ko and not _patterns(ko["objects"]):
                errs.append("hair.ear_keepout.objects must be a non-empty list of name patterns")
            if "structures" in ko and not _patterns(ko["structures"]):
                errs.append("hair.ear_keepout.structures must be a non-empty list of name patterns")
            if not _num(ko, "margin_m", 0, 0.02, 0.003):
                errs.append("hair.ear_keepout.margin_m must be in 0..0.02")
            if not (_num(ko, "smooth", 0, 24, 6) and float(ko.get("smooth", 6)) == int(ko.get("smooth", 6))):
                errs.append("hair.ear_keepout.smooth must be an integer in 0..24")
    ct = contact_spec(hair_spec)
    if ct is not None:
        if not isinstance(ct, dict) or set(ct) - CONTACT_KEYS:
            return errs + ["hair.dynamics.contact must be {\"colliders\", \"segments\", \"anchored_gravity\", \"structures\"}"]
        for k in ("segments", "anchored_gravity"):
            if not isinstance(ct.get(k, True), bool):
                errs.append(f"hair.dynamics.contact.{k} must be true or false")
        if "structures" in ct and not _patterns(ct["structures"]):
            errs.append("hair.dynamics.contact.structures must be a non-empty list of name patterns")
        cols = ct.get("colliders", [])
        if not isinstance(cols, list):
            return errs + ["hair.dynamics.contact.colliders must be a list"]
        existing = {c.get("name") for c in (hair_spec.get("dynamics") or {}).get("colliders", []) if isinstance(c, dict)}
        seen = set()
        for i, c in enumerate(cols):
            where = f"hair.dynamics.contact.colliders[{i}]"
            if not isinstance(c, dict) or set(c) - COLLIDER_KEYS:
                errs.append(f"{where}: keys are {sorted(COLLIDER_KEYS)}")
                continue
            name = c.get("name")
            if not isinstance(name, str) or not name or name in seen or name in existing:
                errs.append(f"{where}: needs a name that no other collider uses")
            seen.add(name)
            if not isinstance(c.get("bone"), str) or not c.get("bone"):
                errs.append(f"{where}: needs a bone")
            fit = c.get("fit")
            if fit not in ("blob", "limb"):
                errs.append(f"{where}: fit must be \"blob\" or \"limb\"")
            if ("groups" in c) == ("objects" in c) or not _patterns(c.get("groups", c.get("objects"))):
                errs.append(f"{where}: give either groups or objects (a non-empty list of name patterns)")
            if fit == "limb" and not _patterns(c.get("bones")):
                errs.append(f"{where}: a limb needs bones")
            if fit == "blob" and "bones" in c:
                errs.append(f"{where}: bones is for a limb")
            if not _num(c, "percentile", 1, 100, 50) or not _num(c, "pad_m", -0.02, 0.05, 0):
                errs.append(f"{where}: percentile must be in 1..100 and pad_m in -0.02..0.05")
            if not isinstance(c.get("solid", False), bool):
                errs.append(f"{where}: solid must be true or false")
    return errs


def _match(name, patterns):
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


# ------------------------------------------------------------------------------------------------------ ear keep-out
def keepout_moves(points, edges, inside, exits, margin, smooth):
    """The keep-out displacement of a set of points (pure function, no Blender).

    points: [Vector]; edges: [(i, j)] between them; inside(p) -> signed distance of p to the keep-out surface (negative
    inside); exits(p) -> the point where p leaves the keep-out volume (the shorter way along the exit axis, margin
    included) or None. Returns {index: Vector displacement}. Points inside (or nearer than `margin`) move out; the
    move is relaxed over the neighbours for `smooth` passes; every moved point ends at least `margin` outside."""
    n = len(points)
    zero = points[0] * 0.0 if n else None
    pinned = {}
    for i, p in enumerate(points):
        if inside(p) < margin:
            q = exits(p)
            if q is not None:
                pinned[i] = q - p
    if not pinned:
        return {}
    nb = [[] for _ in range(n)]
    for a, b in edges:
        nb[a].append(b)
        nb[b].append(a)
    disp = dict(pinned)
    ring = set(pinned)
    for _ in range(int(smooth)):  # the free vertices that can be reached: one more ring per pass
        ring |= {j for i in ring for j in nb[i]}
    free = sorted(ring - set(pinned))
    for _ in range(int(smooth)):
        new = {}
        for i in free:
            if nb[i]:
                acc = zero
                for j in nb[i]:
                    acc = acc + disp.get(j, zero)
                new[i] = acc * (1.0 / len(nb[i]))
        disp.update(new)
    out = {}
    for i, d in disp.items():
        if i not in pinned and d.length < 1e-6:
            continue
        p = points[i] + d
        for _ in range(4):  # an oblique exit, or a relaxed neighbour, can end nearer than the margin: out again
            if inside(p) >= margin - 1e-7:
                break
            q = exits(p)
            if q is None:
                break
            p = q
        out[i] = p - points[i]
    return out


def apply_ear_keepout(hair_spec, objs):
    """Moves the hair surface out of the keep-out meshes (in place). Returns the report."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    cfg = dict(KEEPOUT_DEFAULT, **hair_spec["ear_keepout"])
    margin, smooth = float(cfg["margin_m"]), int(cfg["smooth"])
    deps = bpy.context.evaluated_depsgraph_get()
    volumes = []
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH" or not _match(ob.name, cfg["objects"]) or ob in objs:
            continue
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        mw = ob.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        if not polys:
            continue
        lo = Vector([min(v[k] for v in verts) for k in range(3)])
        hi = Vector([max(v[k] for v in verts) for k in range(3)])
        volumes.append((ob.name, BVHTree.FromPolygons(verts, polys), lo, hi))
    rep = {"margin_m": margin, "smooth": smooth, "volumes": [v[0] for v in volumes], "objects": {}}
    if not volumes:
        return rep
    axis = Vector((0.0, 1.0, 0.0))  # the head's front/back axis (the face looks along -Y)
    reach = margin + 0.03
    for ob in objs:
        if ob.type != "MESH" or ("structures" in cfg and not _match(ob.name[len("hair_"):] if ob.name.startswith("hair_")
                                                                   else ob.name, cfg["structures"])):
            continue
        me, mw = ob.data, ob.matrix_world
        inv = mw.inverted()
        world = [mw @ v.co for v in me.vertices]
        for vname, tree, lo, hi in volumes:
            cand = [i for i, p in enumerate(world) if all(lo[k] - reach <= p[k] <= hi[k] + reach for k in range(3))]
            if not cand:
                continue
            local = {i: k for k, i in enumerate(cand)}
            edges = [(local[e.vertices[0]], local[e.vertices[1]]) for e in me.edges
                     if e.vertices[0] in local and e.vertices[1] in local]

            def inside(p, tree=tree):
                loc, nrm, _, dist = tree.find_nearest(p)
                if loc is None:
                    return 1.0
                return dist if (p - loc).dot(nrm) >= 0 else -dist

            def exits(p, tree=tree):
                d = inside(p)
                if d >= 0:  # outside, within the margin: away from the surface
                    loc, nrm, _, _ = tree.find_nearest(p)
                    return loc + nrm * margin
                best = None
                for sgn in (1.0, -1.0):
                    hit, _, _, t = tree.ray_cast(p, axis * sgn)
                    if hit is not None and (best is None or t < best[0]):
                        best = (t, hit + axis * (sgn * margin))
                return best[1] if best else None

            moves = keepout_moves([world[i] for i in cand], edges, inside, exits, margin, smooth)
            if not moves:
                continue
            far = 0.0
            for k, d in moves.items():
                i = cand[k]
                world[i] = world[i] + d
                me.vertices[i].co = inv @ world[i]
                far = max(far, d.length)
            left = sum(1 for i in cand if inside(world[i]) < 0)
            rep["objects"].setdefault(ob.name, {})[vname] = {"moved": len(moves), "max_m": round(far, 5), "inside_after": left}
        me.update()
    return rep


# ------------------------------------------------------------------------------------------------- contact colliders
def store(hair_spec, objs):
    """Build step: the contact spec travels to bind() on the hair objects (bind has no hair spec)."""
    ct = contact_spec(hair_spec)
    if ct is None:
        return None
    buns = [s.get("name", s["type"]) for s in hair_spec.get("structures", []) if s.get("type") == "bun"]
    data = json.dumps({"contact": ct, "bun_groups": buns}, sort_keys=True)
    for ob in objs:
        ob[CONTACT_PROP] = data
    return {"colliders": [c["name"] for c in ct.get("colliders", [])]}


def fit_capsule(points, fit, axis=None, percentile=None, pad=0.0):
    """A capsule (a, b, radius) around points ([(x, y, z)]). blob: along the principal axis, the radius is the
    percentile (default 85) of the distance to it and the ends lie one radius inside the 2nd/98th percentile of the
    extent. limb: along `axis` ((a, b), bone head to tail), the radius is the percentile (default 50) of the distance
    of the points of the middle 70 % of the axis, and the ends lie one radius (at most 45 % of the length) inside."""
    import numpy as np
    P = np.asarray(points, dtype=np.float64)
    if len(P) < 4:
        raise ValueError("too few vertices")
    if fit == "limb":
        a, b = np.asarray(axis[0], dtype=np.float64), np.asarray(axis[1], dtype=np.float64)
        L = float(np.linalg.norm(b - a))
        if L < 1e-6:
            raise ValueError("zero-length axis")
        ax = (b - a) / L
        t = (P - a) @ ax
        mid = P[(t > 0.15 * L) & (t < 0.85 * L)]
        if len(mid) < 4:
            raise ValueError("too few vertices along the axis")
        rad = np.linalg.norm((mid - a) - np.outer((mid - a) @ ax, ax), axis=1)
        r = max(1e-4, float(np.percentile(rad, 50 if percentile is None else percentile)) + pad)
        ins = min(r, 0.45 * L)
        return (a + ax * ins).tolist(), (b - ax * ins).tolist(), r
    c = P.mean(axis=0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    ax = vt[0]
    if ax[int(np.argmax(np.abs(ax)))] < 0:  # a fixed sign: the same capsule on every build
        ax = -ax
    t = (P - c) @ ax
    rad = np.linalg.norm((P - c) - np.outer(t, ax), axis=1)
    r = max(1e-4, float(np.percentile(rad, 85 if percentile is None else percentile)) + pad)
    lo, hi = float(np.percentile(t, 2)) + r, float(np.percentile(t, 98)) - r
    if hi < lo:
        lo = hi = 0.5 * (lo + hi)
    return (c + ax * lo).tolist(), (c + ax * hi).tolist(), r


def _carried(rig, skip, patterns):
    """World positions of the vertices of the meshes bound to the rig (not `skip`) that the vertex groups matching
    `patterns` carry with at least half of the weight."""
    out = []
    for ob in sorted(rig.children, key=lambda o: o.name):
        if ob.type != "MESH" or ob in skip:
            continue
        idx = {g.index for g in ob.vertex_groups if _match(g.name, patterns)}
        if not idx:
            continue
        mw = ob.matrix_world
        for v in ob.data.vertices:
            w = sum(g.weight for g in v.groups if g.group in idx)
            if w >= 0.5:
                out.append(tuple(mw @ v.co))
    return out


def bind_contact(rig, objs, head_bone, chest_bone):
    """Bind step: fits the contact colliders and writes them, with the chains' "contact" blocks, into the rig's
    "ps_dynamics" (the engine exporter passes chain keys through). No-op without a stored contact spec or chains."""
    import bpy
    raw = next((ob[CONTACT_PROP] for ob in objs if CONTACT_PROP in ob), None)
    if raw is None or not rig.get("ps_dynamics"):
        return None
    stored = json.loads(raw)
    ct, buns = stored["contact"], set(stored["bun_groups"])
    dyn = json.loads(rig["ps_dynamics"])
    before = [c["name"] for c in dyn["colliders"]]
    resolve = {"head": head_bone, "chest": chest_bone}
    mw = rig.matrix_world
    skip = set(objs)
    rep, solid = {}, []
    for c in ct.get("colliders", []):
        bone = resolve.get(c["bone"], c["bone"])
        if bone not in rig.data.bones:
            raise SystemExit(f"hair.dynamics.contact: collider {c['name']}: no bone {bone} in the rig")
        if "groups" in c:
            pts = _carried(rig, skip, c["groups"])
        else:
            pts = [tuple(o.matrix_world @ v.co) for o in sorted(bpy.data.objects, key=lambda o: o.name)
                   if o.type == "MESH" and o not in skip and _match(o.name, c["objects"]) for v in o.data.vertices]
        axis = None
        if c["fit"] == "limb":
            for b in c["bones"]:
                if b not in rig.data.bones:
                    raise SystemExit(f"hair.dynamics.contact: collider {c['name']}: no bone {b} in the rig")
            axis = (tuple(mw @ rig.data.bones[c["bones"][0]].head_local), tuple(mw @ rig.data.bones[c["bones"][-1]].tail_local))
        try:
            a, b, r = fit_capsule(pts, c["fit"], axis, c.get("percentile"), float(c.get("pad_m", 0.0)))
        except ValueError as e:
            raise SystemExit(f"hair.dynamics.contact: collider {c['name']}: {e} ({len(pts)} vertices)")
        dyn["colliders"].append({"name": c["name"], "type": "capsule", "bone": bone, "radius": round(r, 5),
                                 "a": [round(x, 6) for x in a], "b": [round(x, 6) for x in b]})
        if c.get("solid", False):
            solid.append(c["name"])
        rep[c["name"]] = {"bone": bone, "radius_m": round(r, 5), "length_m": round(math.dist(a, b), 5),
                          "vertices": len(pts), "solid": bool(c.get("solid", False))}
    chains = 0
    for ch in dyn["chains"]:
        on = ch.get("group") not in buns and ("structures" not in ct or _match(ch.get("group", ""), ct["structures"]))
        if on:
            ch["contact"] = {"solid": solid, "segments": bool(ct.get("segments", True)),
                             "anchored_gravity": bool(ct.get("anchored_gravity", True))}
            chains += 1
        elif not ch.get("colliders"):
            ch["colliders"] = before  # as before: none of the contact colliders
    rig["ps_dynamics"] = json.dumps(dyn)
    return {"colliders": rep, "chains": chains}
