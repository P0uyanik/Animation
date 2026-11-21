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

  Round 2 keys of the same block (all optional; without them the block builds as in round 1):
    collider {"name", "fit": "skin", "groups" | "objects" | "exclude_groups" | "exclude_objects": [patterns] (any
       combination; none = the whole figure), "spacing_m" (0.024), "radius_m" (0.045), "pad_m" (0.0025), "reach_m"
       (0.12: only surface this near to a contact chain), "min_radius_m" (0.008)}: spheres that follow the figure's
       surface from inside (skin_spheres), named <name>.<i>; each rides on the deform bone that carries its vertex
       most (no "bone"). A vertex belongs to the collider by its strongest deform group.
    "figure": {"exclude": [object-name patterns]}: meshes bound to the rig that are not part of the solid figure
       (default FIGURE_EXCLUDE: collision proxies, widgets, face features, glasses). Hair objects never are.
    "radii": {"percentile": 1..100 (100), "floor_m": 0..0.05 (0.006)}: each contact chain gets one collision radius
       per joint from the vertices it carries (chain_radii), 0 at the root, and never more than the joint's rest
       clearance to the colliders on the chain's own root bone (the head).
    "rest": true | {"friction": >= 0 (40), "max_swing": >= 0 (12)}: resting contact (docs/SECONDARY_MOTION.md);
       the chains take every collider ("solid" of a collider is then without effect).
    "sheets": [{"structure": pattern, "top_z": world z where the sheet leaves the head, "chains": 2..64 (13),
       "bones": 1..8 (4), "blend": 0.1..1 (0.5, in bones: how far below top_z the chains take over),
       "stiffness" (120), "stiffness_tip" (90), "damping" (18), "gravity" (0.5), "drag" (0.8), "limit_deg" (30)}]:
       a static hanging sheet (a curtain) gets chains: `chains` of them, spread evenly over the sheet's angle about
       the head bone's vertical axis, each down the middle of its sector from top_z to the sector's lower edge. A
       vertex below top_z follows the two chains next to it (by angle) and, along them, the bones as a lock does.
       The chains are named <structure>.<kk> (group = the structure), take binding.blend_z anchors like locks and
       the same contact block; with "radii" each joint's radius encloses its sector of the sheet. The chains are
       independent: where colliders push neighbours apart the sheet shears (T-183: the girl's back curtain, edges up
       to 3.8 x their rest length), so use it only where that cannot be seen.
"""
import fnmatch
import json
import math

CONTACT_PROP = "ps_contact"  # the contact spec, carried on the hair objects from build to bind
KEEPOUT_DEFAULT = {"objects": ["ear.*"], "margin_m": 0.003, "smooth": 6}
COLLIDER_KEYS = {"name", "bone", "fit", "groups", "objects", "bones", "percentile", "pad_m", "solid"}
SKIN_KEYS = {"name", "fit", "groups", "objects", "exclude_groups", "exclude_objects", "spacing_m", "radius_m", "pad_m",
             "reach_m", "min_radius_m"}
SKIN_DEFAULT = {"spacing_m": 0.024, "radius_m": 0.045, "pad_m": 0.0025, "reach_m": 0.12, "min_radius_m": 0.008}
SKIN_RANGE = {"spacing_m": (0.004, 0.1), "radius_m": (0.005, 0.2), "pad_m": (0.0, 0.02), "reach_m": (0.01, 10.0),
              "min_radius_m": (0.001, 0.05)}
FIGURE_EXCLUDE = ["garment.collider.*", "WGT-*", "eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
RADII_DEFAULT = {"percentile": 100.0, "floor_m": 0.006}
REST_DEFAULT = {"friction": 40.0, "max_swing": 12.0}
SHEET_DEFAULT = {"chains": 13, "bones": 4, "blend": 0.5, "stiffness": 120.0, "stiffness_tip": 90.0, "damping": 18.0,
                 "gravity": 0.5, "drag": 0.8, "limit_deg": 30.0}
SHEET_RANGE = {"chains": (2, 64), "bones": (1, 8), "blend": (0.1, 1.0), "stiffness": (0, 5000), "stiffness_tip": (0, 5000),
               "damping": (0, 500), "gravity": (0, 5), "drag": (0, 50), "limit_deg": (0, 180), "top_z": (-10, 10)}
DYN_BONE_PREFIX = "DYN-"  # as groom.DYN_BONE_PREFIX (chain bones)
CONTACT_KEYS = {"colliders", "segments", "anchored_gravity", "structures", "figure", "radii", "rest", "sheets"}
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
            return errs + [f"hair.dynamics.contact: keys are {sorted(CONTACT_KEYS)}"]
        errs += _validate_round2(ct)
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
            if isinstance(c, dict) and c.get("fit") == "skin":
                errs += _validate_skin(c, where, seen, existing)
                continue
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
                errs.append(f"{where}: fit must be \"blob\", \"limb\" or \"skin\"")
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


def _validate_skin(c, where, seen, existing):
    errs = []
    if set(c) - SKIN_KEYS:
        return [f"{where}: keys of a skin collider are {sorted(SKIN_KEYS)}"]
    name = c.get("name")
    if not isinstance(name, str) or not name or name in seen or name in existing:
        errs.append(f"{where}: needs a name that no other collider uses")
    seen.add(name)
    for k in ("groups", "objects", "exclude_groups", "exclude_objects"):
        if k in c and not _patterns(c[k]):
            errs.append(f"{where}: {k} must be a non-empty list of name patterns")
    for k, (lo, hi) in SKIN_RANGE.items():
        if not _num(c, k, lo, hi, SKIN_DEFAULT[k]):
            errs.append(f"{where}: {k} must be in {lo}..{hi}")
    return errs


def _validate_round2(ct):
    errs = []
    fg = ct.get("figure")
    if fg is not None and not (isinstance(fg, dict) and set(fg) <= {"exclude"} and ("exclude" not in fg or _patterns(fg["exclude"]))):
        errs.append("hair.dynamics.contact.figure must be {\"exclude\": [object-name patterns]}")
    ra = ct.get("radii")
    if ra is not None and not (isinstance(ra, dict) and set(ra) <= {"percentile", "floor_m"}
                               and _num(ra, "percentile", 1, 100, 100) and _num(ra, "floor_m", 0, 0.05, 0.006)):
        errs.append("hair.dynamics.contact.radii must be {\"percentile\": 1..100, \"floor_m\": 0..0.05}")
    rs = ct.get("rest")
    if rs is not None and not isinstance(rs, bool) and not (
            isinstance(rs, dict) and set(rs) <= {"friction", "max_swing"} and _num(rs, "friction", 0, 1000, 40)
            and _num(rs, "max_swing", 0, 1000, 12)):
        errs.append("hair.dynamics.contact.rest must be true, false or {\"friction\": 0..1000, \"max_swing\": 0..1000}")
    sh = ct.get("sheets")
    if sh is not None:
        if not isinstance(sh, list) or not sh:
            errs.append("hair.dynamics.contact.sheets must be a non-empty list")
        else:
            for i, e in enumerate(sh):
                where = f"hair.dynamics.contact.sheets[{i}]"
                if not isinstance(e, dict) or set(e) - (set(SHEET_RANGE) | {"structure"}):
                    errs.append(f"{where}: keys are {sorted(set(SHEET_RANGE) | {'structure'})}")
                    continue
                if not isinstance(e.get("structure"), str) or not e.get("structure"):
                    errs.append(f"{where}: needs a structure (name pattern)")
                if "top_z" not in e:
                    errs.append(f"{where}: needs top_z")
                for k, (lo, hi) in SHEET_RANGE.items():
                    if not _num(e, k, lo, hi, SHEET_DEFAULT.get(k, 0.0)):
                        errs.append(f"{where}: {k} must be in {lo}..{hi}")
                for k in ("chains", "bones"):
                    v = e.get(k, 1)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) != int(v):
                        errs.append(f"{where}: {k} must be a whole number")
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
    return {"colliders": [c["name"] for c in ct.get("colliders", [])],
            **({k: ct[k] for k in ("radii", "rest", "sheets") if k in ct})}


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


def fit_cover(points, axis=None, strips=0, sections=1, percentile=98.0, pad=0.0, spacing=0.5, end_inset=1.0):
    """Capsules that enclose a surface region (T-183 round 2; pure function): [(a, b, radius)].

    The region is treated as a rounded slab: capsules run along its long axis e1 (`axis` (a, b), e.g. the bone, or the
    principal axis), side by side across its width e2, and each has the local half-thickness along e3 as its radius
    (the `percentile` of the points' distance from the capsule's mid-plane, plus `pad`). `strips` capsules across the
    width (0 = as many as keep the groove between neighbours shallow: centres at most `spacing` radii apart);
    `sections` pieces along e1, each with its own radius, so a region that tapers or bulges is followed. The two outer
    ends lie `end_inset` radii inside the region's extent (1 = the round cap ends where the region ends)."""
    import numpy as np
    P = np.asarray(points, dtype=np.float64)
    if len(P) < 8:
        raise ValueError("too few vertices")
    c = P.mean(axis=0)
    Q = P - c
    if axis is not None:
        e1 = np.asarray(axis[1], dtype=np.float64) - np.asarray(axis[0], dtype=np.float64)
        if np.linalg.norm(e1) < 1e-6:
            raise ValueError("zero-length axis")
        e1 = e1 / np.linalg.norm(e1)
        flat = Q - np.outer(Q @ e1, e1)
        _, _, vt = np.linalg.svd(flat, full_matrices=False)
        e2 = vt[0]
    else:
        _, _, vt = np.linalg.svd(Q, full_matrices=False)
        e1, e2 = vt[0], vt[1]
    for e in (e1, e2):  # fixed signs: the same capsules on every build
        if e[int(np.argmax(np.abs(e)))] < 0:
            e *= -1.0
    e3 = np.cross(e1, e2)
    u, v, w = Q @ e1, Q @ e2, Q @ e3
    out = []
    ulo, uhi = float(u.min()), float(u.max())
    edges = np.linspace(ulo, uhi, int(sections) + 1)
    for si in range(int(sections)):
        a_u, b_u = float(edges[si]), float(edges[si + 1])
        grow = 0.15 * (b_u - a_u) if sections > 1 else 0.0  # neighbours overlap
        sel = (u >= a_u - grow) & (u <= b_u + grow)
        if sel.sum() < 8:
            continue
        vs, ws = v[sel], w[sel]
        w0 = 0.5 * (float(np.percentile(ws, 1)) + float(np.percentile(ws, 99)))
        half = float(np.percentile(np.abs(ws - w0), percentile))
        vlo, vhi = float(np.percentile(vs, 100 - percentile)), float(np.percentile(vs, percentile))
        width = 0.5 * (vhi - vlo)
        n = int(strips) if strips else max(1, int(math.ceil(max(0.0, width - half) * 2.0 / max(1e-6, spacing * half))) + 1)
        r_edge = min(half, width)
        centres = [0.5 * (vlo + vhi)] if n == 1 else list(np.linspace(vlo + r_edge, vhi - r_edge, n))
        for vc in centres:
            if n == 1:
                r = float(np.percentile(np.hypot(vs - vc, ws - w0), percentile))
            else:  # the local thickness of this strip, and never less than what reaches the region's edge
                band = np.abs(vs - vc) <= max(spacing * half, (vhi - vlo) / (2.0 * n))
                loc = ws[band] if band.sum() >= 8 else ws
                r = max(float(np.percentile(np.abs(loc - w0), percentile)), min(vc - vlo, vhi - vc, half))
            r = max(1e-4, r + pad)
            lo = a_u + (r * end_inset if si == 0 else 0.0)
            hi = b_u - (r * end_inset if si == sections - 1 else 0.0)
            if hi < lo:
                lo = hi = 0.5 * (a_u + b_u) if sections > 1 else 0.5 * (ulo + uhi)
            base = c + e2 * vc + e3 * w0
            out.append(((base + e1 * lo).tolist(), (base + e1 * hi).tolist(), r))
    if not out:
        raise ValueError("no capsule fitted")
    return out


def capsule_distance(points, capsules):
    """(N,) signed distance of points to the union of capsules [(a, b, radius)] (negative = inside)."""
    import numpy as np
    P = np.asarray(points, dtype=np.float64)
    best = np.full(len(P), 1e9)
    for a, b, r in capsules:
        a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
        ab = b - a
        l2 = float(ab @ ab)
        t = np.clip(((P - a) @ ab) / l2, 0.0, 1.0) if l2 > 1e-12 else np.zeros(len(P))
        best = np.minimum(best, np.linalg.norm(P - (a + t[:, None] * ab), axis=1) - r)
    return best


def cover_report(points, capsules):
    """How well capsules enclose a region's points: the share outside, the largest and 99th percentile protrusion, and
    how far the region's points lie under the capsule surface (median, 95 %): the gap hair resting on it will show."""
    import numpy as np
    d = capsule_distance(points, capsules)
    out = d[d > 0]
    return {"capsules": len(capsules), "vertices": int(len(d)), "outside": int(len(out)),
            "protrusion_max_m": round(float(d.max()), 5), "protrusion_p99_m": round(float(np.percentile(d, 99)), 5),
            "gap_p50_m": round(float(np.percentile(-d, 50)), 5), "gap_p95_m": round(float(np.percentile(-d, 95)), 5)}


def chain_radii(points, joints, percentile=95.0, pad=0.0, floor=0.0):
    """The collision radius of each joint of a chain from the vertices it carries (pure function): the `percentile` of
    the distance of the vertices next to that joint (within half a segment along the chain) from the chain line."""
    import numpy as np
    P = np.asarray(points, dtype=np.float64)
    J = np.asarray(joints, dtype=np.float64)
    n = len(J) - 1
    best = np.full(len(P), 1e9)
    coord = np.zeros(len(P))
    for k in range(n):
        a, ab = J[k], J[k + 1] - J[k]
        t = np.clip(((P - a) @ ab) / max(1e-12, float(ab @ ab)), 0.0, 1.0)
        d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
        closer = d < best
        best[closer], coord[closer] = d[closer], k + t[closer]
    out = []
    for k in range(n + 1):
        sel = np.abs(coord - k) <= 0.5
        r = float(np.percentile(best[sel], percentile)) if sel.sum() >= 4 else 0.0
        out.append(round(max(floor, r + pad), 5))
    return out


def skin_spheres(tree, points, normals, near, spacing=0.024, radius=0.045, pad=0.0025, reach=0.12, min_radius=0.008):
    """Spheres that follow a surface from inside (T-183 round 2): [(vertex index, centre, radius)].

    tree: a mathutils BVHTree of the whole figure (every surface the hair must stay out of); points, normals: (N, 3)
    surface vertices and their outward normals; near: (M, 3) points of the hair chains (rest pose). A vertex takes
    part when it lies within `reach` of the chains and on the outside of the figure (its normal side is open: the
    inner faces of a cloth shell are not). Samples are picked `spacing` apart (farthest point first, from the vertex
    nearest to the chains), and each carries a sphere that touches the surface there from inside: centre `r` below the
    vertex along its normal (turned to the side that is open, whatever the stored normal says), r = `radius`, or less where the figure is thinner (0.45 of its thickness there; thinner
    than `min_radius`: no sphere), plus `pad`. The union of the spheres encloses the sampled surface up to the groove
    between neighbours (about (0.58 spacing)^2 / 2r, covered by `pad`), fills creases narrower than the spheres, and
    each sphere can ride on the bone that carries its vertex, so the colliders follow the skinned surface."""
    import numpy as np
    from mathutils import Vector
    P = np.asarray(points, dtype=np.float64)
    Nn = np.asarray(normals, dtype=np.float64)
    Q = np.asarray(near, dtype=np.float64)
    d2 = np.full(len(P), np.inf)
    for q in Q:
        d2 = np.minimum(d2, ((P - q) ** 2).sum(axis=1))
    cand = np.nonzero(d2 <= reach * reach)[0]
    dirs = [Vector(d).normalized() for d in
            [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]]

    def open_side(p, n):
        """0 = nothing lies on side n of p (the ray along n meets nothing), 1 = that side is open in at least two
        other directions (a crease), 2 = enclosed."""
        q = p + n * 0.0015
        if tree.ray_cast(q, n, 0.6)[0] is None:
            return 0
        free = sum(1 for d in dirs if d.dot(n) > 0.2 and tree.ray_cast(q, d, 0.6)[0] is None)
        return 1 if free >= 2 else 2

    keep, rad, out_n = [], [], {}
    for i in cand:
        n = Vector(Nn[i])
        if n.length < 1e-9:
            continue
        n.normalize()
        p = Vector(P[i])
        # the outward side by what can be seen from it, not by the stored normal (trims may be modelled inside out)
        front, back = open_side(p, n), open_side(p, -n)
        if front == back or min(front, back) == 2:
            continue  # a sheet with nothing behind it, or a vertex enclosed on both sides
        if back < front:
            n = -n
        t, last = 0.0015, 0.0  # thickness: the last surface met going in
        while True:
            hit = tree.ray_cast(p - n * t, -n, 0.6 - t)
            if hit[0] is None:
                break
            t += hit[3] + 2e-5
            last = t
        r = min(radius, 0.45 * last)
        if r < min_radius:
            continue
        keep.append(i)
        rad.append(r)
        out_n[int(i)] = np.array(n)
    if not keep:
        return []
    keep, rad = np.array(keep), np.array(rad)
    K = P[keep]
    first = int(np.argmin(d2[keep]))
    chosen = [first]
    dist = np.linalg.norm(K - K[first], axis=1)
    while True:
        j = int(np.argmax(dist))
        if dist[j] < spacing:
            break
        chosen.append(j)
        dist = np.minimum(dist, np.linalg.norm(K - K[j], axis=1))
    out = []
    for j in chosen:
        i = int(keep[j])
        out.append((i, (P[i] - out_n[i] * rad[j]).tolist(), float(rad[j] + pad)))
    return out


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


def _figure(rig, skip, exclude):
    """The solid figure in the rest pose: every evaluated mesh bound to the rig that is not hair (`skip`) and not
    excluded by name. Returns world positions, outward normals as stored, polygons, and per vertex the object name
    and the name of the deform bone that carries it most ("" when none)."""
    import bpy
    import numpy as np
    deps = bpy.context.evaluated_depsgraph_get()
    deform = {b.name for b in rig.data.bones if b.use_deform}
    P, N, polys, obn, bone = [], [], [], [], []
    base = 0
    for ob in sorted(rig.children, key=lambda o: o.name):
        if ob.type != "MESH" or ob in skip or _match(ob.name, exclude):
            continue
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        mw = ev.matrix_world
        rot = mw.to_3x3().inverted().transposed()
        gname = [g.name if g.name in deform else "" for g in ob.vertex_groups]
        for v in me.vertices:
            P.append(tuple(mw @ v.co))
            N.append(tuple(rot @ v.normal))
            best, bw = "", 0.0
            for g in v.groups:
                if g.group < len(gname) and gname[g.group] and g.weight > bw:
                    best, bw = gname[g.group], g.weight
            bone.append(best)
        obn += [ob.name] * len(me.vertices)
        polys += [tuple(base + i for i in pl.vertices) for pl in me.polygons]
        base += len(me.vertices)
        ev.to_mesh_clear()
    return np.array(P, dtype=np.float64).reshape(-1, 3), np.array(N, dtype=np.float64).reshape(-1, 3), polys, obn, bone


def _collider_distance(p, c):
    """Distance of point p from the surface of a stored collider (sphere or capsule; negative inside)."""
    a = c.get("a", c.get("centre"))
    b = c.get("b", c.get("centre"))
    ab = [b[i] - a[i] for i in range(3)]
    l2 = sum(x * x for x in ab)
    t = min(1.0, max(0.0, sum((p[i] - a[i]) * ab[i] for i in range(3)) / l2)) if l2 > 1e-12 else 0.0
    return math.dist(p, [a[i] + t * ab[i] for i in range(3)]) - float(c["radius"])


def capped_radii(radii, joints, root_colliders):
    """Chain radii that do not collide in the rest pose with the colliders of the chain's own root bone (pure): 0 at
    the root, otherwise at most the joint's clearance to those colliders (never negative)."""
    out = [0.0]
    for r, j in zip(radii[1:], joints[1:]):
        clear = min((_collider_distance(j, c) for c in root_colliders), default=r)
        out.append(round(max(0.0, min(r, clear)), 5))
    return out


def _bone_weights(u, n):
    """As groom._chain_weights: weights of the n chain bones at chain coordinate u (linear between bone centres)."""
    b = min(max(u - 0.5, 0.0), n - 1.0)
    lo = int(math.floor(b))
    f = b - lo
    w = {lo: 1.0 - f}
    if f > 0 and lo + 1 < n:
        w[lo + 1] = f
    return w


def sheet_layout(points, axis_xy, top_z, chains, bones):
    """Chains for a hanging sheet (pure): {"mid": angle of the sheet's middle, "a0", "step": the chains' angles are
    a0 + k step (relative to mid), "bottom": [z of each chain's lower end], "joints": [[(x, y, z)] * (bones + 1)]}.

    points: (N, 3) vertices of the sheet. Angles are taken about the vertical axis through axis_xy, relative to the
    middle direction of the vertices below top_z (so a sheet may lie anywhere round the head, but not all round).
    Chain k runs down the middle of its sector (an equal share of the angle): joint j lies at top_z + (bottom -
    top_z) j / bones, at the mean place of the sector's vertices of that height (both faces of a shell: mid-sheet);
    bottom is the 2nd percentile of the sector's heights."""
    import numpy as np
    P = np.asarray(points, dtype=np.float64)
    P = P[P[:, 2] < top_z]
    if len(P) < 4 * chains:
        raise ValueError("too few vertices below top_z")
    d = P[:, :2] - np.asarray(axis_xy, dtype=np.float64)
    mid = math.atan2(float(d[:, 1].mean()), float(d[:, 0].mean()))
    ang = (np.arctan2(d[:, 1], d[:, 0]) - mid + math.pi) % (2 * math.pi) - math.pi
    lo, hi = float(ang.min()), float(ang.max())
    step = (hi - lo) / chains
    a0 = lo + 0.5 * step
    bottom, joints = [], []
    for k in range(chains):
        sel = P[np.abs(ang - (a0 + k * step)) <= 0.5 * step + 1e-9]
        if len(sel) < 4:
            raise ValueError(f"no vertices in sector {k}")
        zb = float(np.percentile(sel[:, 2], 2))
        seg = (top_z - zb) / bones
        if seg < 1e-4:
            raise ValueError(f"sector {k} does not reach below top_z")
        J = []
        for j in range(bones + 1):
            z = top_z - seg * j
            near = np.abs(sel[:, 2] - z)
            band = sel[near <= max(0.5 * seg, float(np.sort(near)[3]))]
            J.append((float(band[:, 0].mean()), float(band[:, 1].mean()), z))
        bottom.append(zb)
        joints.append(J)
    return {"mid": mid, "a0": a0, "step": step, "bottom": bottom, "joints": joints}


def sheet_weights(p, layout, axis_xy, top_z, blend=0.5):
    """Chain weights of a sheet vertex p (pure): ({(chain, bone): weight}, chain coordinate u). Empty at or above
    top_z. Below it the vertex follows the two chains next to its angle (linear between them, the edge chain alone
    beyond it) and along them the bones by its height (u = 0 at top_z, `bones` at the chains' lower end, which is
    interpolated between the two); over the first `blend` bones the weights rise from 0 (the static binding keeps
    the rest: no step at top_z)."""
    K = len(layout["joints"])
    n = len(layout["joints"][0]) - 1
    if p[2] >= top_z:
        return {}, 0.0
    a = (math.atan2(p[1] - axis_xy[1], p[0] - axis_xy[0]) - layout["mid"] + math.pi) % (2 * math.pi) - math.pi
    t = min(K - 1.0, max(0.0, (a - layout["a0"]) / layout["step"]))
    k0 = min(K - 2, int(math.floor(t))) if K > 1 else 0
    f = t - k0 if K > 1 else 0.0
    zb = layout["bottom"][k0] * (1 - f) + (layout["bottom"][k0 + 1] * f if f > 0 else 0.0)
    u = min(float(n), n * (top_z - p[2]) / max(1e-6, top_z - zb))
    rise = min(1.0, u / blend)
    out = {}
    for k, wk in ((k0, 1.0 - f), (k0 + 1, f)):
        if wk > 1e-6:
            for i, wi in _bone_weights(u, n).items():
                out[(k, i)] = wk * wi * rise
    return out, u


def _bind_sheets(rig, objs, sheets, head_bone, chest_bone, blend_z):
    """Adds the sheet chains: bones (deform, parented to the head bone), vertex weights, chain records."""
    import bpy
    from mathutils import Vector
    mw = rig.matrix_world
    inv = mw.inverted()
    axis = tuple((mw @ rig.data.bones[head_bone].head_local))[:2]
    jobs = []
    for sh in sheets:
        cfg = dict(SHEET_DEFAULT, **sh)
        for ob in objs:
            name = ob.name[5:] if ob.name.startswith("hair_") else ob.name
            if not _match(name, [sh["structure"]]):
                continue
            pts = [tuple(ob.matrix_world @ v.co) for v in ob.data.vertices]
            try:
                lay = sheet_layout(pts, axis, float(cfg["top_z"]), int(cfg["chains"]), int(cfg["bones"]))
            except ValueError as e:
                raise SystemExit(f"hair.dynamics.contact.sheets: {ob.name}: {e}")
            jobs.append((ob, name, cfg, pts, lay))
    if not jobs:
        raise SystemExit("hair.dynamics.contact.sheets: no hair object matches a sheet's structure")
    bpy.ops.object.select_all(action="DESELECT")
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    bone_names = {}
    for ob, name, cfg, pts, lay in jobs:
        for k, J in enumerate(lay["joints"]):
            prev, names = eb[head_bone], []
            for j in range(len(J) - 1):
                b = eb.new(f"{DYN_BONE_PREFIX}{name}.{k:02d}.{j}")
                b.head, b.tail = inv @ Vector(J[j]), inv @ Vector(J[j + 1])
                b.parent = prev
                b.use_connect = j > 0
                b.use_deform = True
                prev = b
                names.append(b.name)
            bone_names[(name, k)] = names
    bpy.ops.object.mode_set(mode="OBJECT")
    out, rep = [], {}
    for ob, name, cfg, pts, lay in jobs:
        groups = {}
        moved = 0
        for v, p in zip(ob.data.vertices, pts):
            w, _ = sheet_weights(p, lay, axis, float(cfg["top_z"]), float(cfg["blend"]))
            if not w:
                continue
            keep = 1.0 - sum(w.values())
            for g in list(v.groups):
                vg = ob.vertex_groups[g.group]
                if keep <= 1e-6:
                    vg.remove([v.index])
                else:
                    vg.add([v.index], g.weight * keep, "REPLACE")
            for (k, i), x in w.items():
                if x > 1e-6:
                    gname = bone_names[(name, k)][i]
                    vg = groups.get(gname) or ob.vertex_groups.new(name=gname)
                    groups[gname] = vg
                    vg.add([v.index], x, "REPLACE")
            moved += 1
        for k, J in enumerate(lay["joints"]):
            ch = {"name": f"{name}.{k:02d}", "group": name, "bones": bone_names[(name, k)], "tip": list(J[-1]),
                  **{key: float(cfg[key]) for key in ("stiffness", "stiffness_tip", "damping", "gravity", "drag", "limit_deg")},
                  "radius": 0.0}
            if blend_z and chest_bone != head_bone:
                lo, hi = float(blend_z[0]), float(blend_z[1])
                w = [round(1.0 - min(1.0, max(0.0, (j[2] - lo) / (hi - lo))), 4) for j in J]
                if any(w[1:]):
                    ch["anchor"] = {"bone": chest_bone, "weights": [0.0] + w[1:]}
            out.append(ch)
        rep[ob.name] = {"chains": len(lay["joints"]), "bones": int(cfg["bones"]), "vertices": moved,
                        "sector_deg": round(math.degrees(lay["step"]), 1),
                        "bottom_z": [round(min(lay["bottom"]), 3), round(max(lay["bottom"]), 3)]}
    return out, rep


def bind_contact(rig, objs, head_bone, chest_bone, binding=None):
    """Bind step: fits the contact colliders and writes them, with the chains' "contact" blocks, into the rig's
    "ps_dynamics" (the engine exporter passes chain keys through). No-op without a stored contact spec or chains."""
    import bpy
    raw = next((ob[CONTACT_PROP] for ob in objs if CONTACT_PROP in ob), None)
    if raw is None or not rig.get("ps_dynamics"):
        return None
    stored = json.loads(raw)
    ct, buns = stored["contact"], set(stored["bun_groups"])
    out = {}
    dyn = json.loads(rig["ps_dynamics"])
    before = [c["name"] for c in dyn["colliders"]]
    if ct.get("sheets"):
        more, out["sheets"] = _bind_sheets(rig, objs, ct["sheets"], head_bone, chest_bone, (binding or {}).get("blend_z"))
        dyn["chains"] += more
    resolve = {"head": head_bone, "chest": chest_bone}
    mw = rig.matrix_world
    skip = set(objs)
    rep, solid = {}, []

    def on(ch):
        return ch.get("group") not in buns and ("structures" not in ct or _match(ch.get("group", ""), ct["structures"]))

    def joints(ch):
        return [tuple(mw @ rig.data.bones[b].head_local) for b in ch["bones"]] + [tuple(ch["tip"])]

    figure = None
    for c in ct.get("colliders", []):
        if c["fit"] == "skin":
            import numpy as np
            from mathutils.bvhtree import BVHTree
            if figure is None:
                figure = _figure(rig, skip, (ct.get("figure") or {}).get("exclude", FIGURE_EXCLUDE))
                tree = BVHTree.FromPolygons(figure[0].tolist(), figure[2])
                near = []
                for ch in dyn["chains"]:
                    if on(ch):
                        J = joints(ch)
                        for a, b in zip(J[:-1], J[1:]):
                            near += [a, tuple((a[i] + b[i]) / 2 for i in range(3)), b]
            FP, FN, _, obn, vbone = figure
            sel = [i for i in range(len(FP)) if vbone[i]
                   and ("groups" not in c or _match(vbone[i], c["groups"]))
                   and ("objects" not in c or _match(obn[i], c["objects"]))
                   and not ("exclude_groups" in c and _match(vbone[i], c["exclude_groups"]))
                   and not ("exclude_objects" in c and _match(obn[i], c["exclude_objects"]))]
            kw = {k[:-2]: float(c.get(k, d)) for k, d in SKIN_DEFAULT.items()}
            sph = skin_spheres(tree, FP[sel], FN[sel], near, **kw) if sel and near else []
            if not sph:
                raise SystemExit(f"hair.dynamics.contact: collider {c['name']}: no surface for a sphere ({len(sel)} vertices)")
            for k, (i, centre, r) in enumerate(sph):
                dyn["colliders"].append({"name": f"{c['name']}.{k}", "type": "sphere", "bone": vbone[sel[i]],
                                         "radius": round(r, 5), "centre": [round(x, 6) for x in centre]})
            d = capsule_distance(FP[sel], [(s[1], s[1], s[2]) for s in sph])
            if kw["reach"] < 1.0:  # the cover counts where the chains can come (well inside the reach)
                Q = np.asarray(near)[::3]
                d = d[np.min(np.linalg.norm(FP[sel][:, None, :] - Q[None, :, :], axis=2), axis=1) < 0.8 * kw["reach"]]
            rr = [s[2] for s in sph]
            rep[c["name"]] = {"fit": "skin", "spheres": len(sph), "vertices": len(sel),
                              "radius_mm": [round(min(rr) * 1000, 1), round(float(np.median(rr)) * 1000, 1)],
                              "bones": len({vbone[sel[s[0]]] for s in sph}),
                              "outside_max_mm": round(float(d.max()) * 1000, 1) if len(d) else 0.0,
                              "outside_p99_mm": round(float(np.percentile(d, 99)) * 1000, 1) if len(d) else 0.0}
            continue
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
    rest = ct.get("rest", False)
    rest_kw = dict(REST_DEFAULT, **(rest if isinstance(rest, dict) else {})) if rest else None
    radii_kw = dict(RADII_DEFAULT, **ct["radii"]) if ct.get("radii") is not None else None
    chains, radii_rep = 0, {}
    for ch in dyn["chains"]:
        if on(ch):
            block = {"solid": [] if rest_kw else solid, "segments": bool(ct.get("segments", True)),
                     "anchored_gravity": bool(ct.get("anchored_gravity", True))}
            if radii_kw:
                J = joints(ch)
                pts = []
                for ob in objs:
                    idx = {g.index for g in ob.vertex_groups if g.name in ch["bones"]}
                    if idx:
                        m = ob.matrix_world
                        pts += [tuple(m @ v.co) for v in ob.data.vertices
                                if sum(g.weight for g in v.groups if g.group in idx) >= 0.5]
                fitted = chain_radii(pts, J, percentile=float(radii_kw["percentile"]), floor=float(radii_kw["floor_m"])) \
                    if len(pts) >= 4 else [float(ch.get("radius", 0.0))] * len(J)
                root = rig.data.bones[ch["bones"][0]].parent
                block["radii"] = capped_radii(fitted, J, [c for c in dyn["colliders"] if root and c["bone"] == root.name])
                radii_rep[ch["name"]] = [round(max(block["radii"]) * 1000, 1), round(max(fitted) * 1000, 1)]
            if rest_kw:
                block.update(rest=True, friction=float(rest_kw["friction"]), max_swing=float(rest_kw["max_swing"]))
                ch.pop("colliders", None)  # every collider
            ch["contact"] = block
            chains += 1
        elif not ch.get("colliders"):
            ch["colliders"] = before  # as before: none of the contact colliders
    rig["ps_dynamics"] = json.dumps(dyn)
    out.update(colliders=rep, chains=chains)
    if radii_rep:
        out["radii_mm"] = {"largest used / fitted": radii_rep}
    print("groom contact: " + json.dumps(out, sort_keys=True))
    return out
