"""Render-time hair push-out (T-194): keeps hair out of the real evaluated meshes of the shot (the character's own
body, ears, hands and garments, the other characters, props and the bake's box objects) after the engine's chain
solver has moved it. Opt-in (`shot_render.py --hair-pushout`); without it nothing here runs.

Two stages, both stateless per frame (the result at frame f depends only on the evaluated meshes at f):

A. Chain joints (Python, called per frame by shot_render after every bone is keyed). Every `DYN-*` chain listed in
   the rig's `ps_dynamics` is walked from its root, in a fixed order. Segment k is tested with a RAY from joint k-1
   (already outside) to joint k: any face it crosses counts, so open garment shells, inside-out trims and deep cases
   are caught (a nearest-point + normal test pushes those to the wrong side). On a hit the joint keeps its segment
   length and slides over the hit plane with `core_radius_m + margin_m` clearance, then the segment is tested again
   (MAX_TRIES); the fallback is straight away from the surface, and only if that is blocked too the segment is
   shortened to the last free point (reported). The leading segments of a chain that already cross the character's
   own figure at rest (the root sits in the scalp) are tested only beyond that rest crossing. Changed bones are
   re-keyed; a chain whose segments cross nothing is left exactly as baked.

B. Every hair vertex (a Geometry Nodes modifier on each hair object, evaluated by Blender, no Python at render
   time). Each hair object gets a hidden anchor proxy: a local copy of its mesh whose vertices sit at a point that is
   outside at rest, deformed by the same armature: a chain vertex's anchor is its nearest point on its chain's centre
   line (weighted 1.0 to that chain bone, so it lies exactly on the deformed chain, which stage A keeps free); a
   static vertex's (no chain weight: cap, curtain, temples, masses) is `static_reach_m` outwards from the head
   centre, with the vertex's own weights. An anchor whose ray to its vertex crosses the own figure at rest is moved
   past the last such crossing (roots embedded in the scalp stay as modelled). The modifier casts a ray from the
   anchor to the vertex against all colliders and puts a vertex whose ray is blocked at `vertex_margin_m` before the
   hit. Vertices whose ray is free are not touched.

Colliders: every mesh child of a rendered character's rig with an Armature modifier except hair (`hair_*`),
`garment.collider.*`, `WGT-*` and the face parts in SKIP (the T-183 measures' list, glasses included); the props of
the shot (an open-top vessel gets a closing cap disc so hair cannot drop in through its opening) and the bake's box
objects. Hair is not a collider (hair against hair is out of scope, T-194)."""
import fnmatch
import json
import math

import numpy as np

SKIP = ["eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
DEFAULTS = {"margin_m": 0.002, "core_radius_m": 0.012, "vertex_margin_m": 0.0015, "static_reach_m": 0.03,
            "characters": "all", "stages": ["chains", "vertices"]}
MAX_TRIES = 3
EPS = 1e-5
CHAIN_MIN_WEIGHT = 0.05  # a vertex with less than this summed DYN weight is static
PREFIX = "ps_pushout"


def load_spec(arg):
    """`--hair-pushout` value: "on" (defaults), a JSON file, or inline JSON. Unknown keys are refused."""
    spec = dict(DEFAULTS)
    if arg in (None, "", "on", "1", "true"):
        return spec
    s = arg.strip()
    user = json.loads(s) if s.startswith("{") else json.load(open(s))
    bad = sorted(set(user) - set(DEFAULTS))
    if bad:
        raise ValueError(f"hair push-out: unknown keys {bad} (have {sorted(DEFAULTS)})")
    spec.update(user)
    if not set(spec["stages"]) <= {"chains", "vertices"}:
        raise ValueError(f"hair push-out: stages must be chains / vertices, got {spec['stages']}")
    return spec


# ---------------------------------------------------------------------------------------------------- geometry ----

def is_hair(o):
    return o.name.startswith("hair_")


def is_figure(o, rig):
    if o.type != "MESH" or is_hair(o) or o.name.startswith(("garment.collider", "WGT-")):
        return False
    if any(fnmatch.fnmatchcase(o.name, p) for p in SKIP):
        return False
    return any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)


def world_triangles(objs, deps):
    """(V (n, 3) float64, T (m, 3) int) of the evaluated objects in world space, in the given order."""
    Vs, Ts, off = [], [], 0
    for o in objs:
        e = o.evaluated_get(deps)
        me = e.to_mesh()
        try:
            n = len(me.vertices)
            me.calc_loop_triangles()
            m = len(me.loop_triangles)
            if n == 0 or m == 0:
                continue
            co = np.empty(n * 3)
            me.vertices.foreach_get("co", co)
            M = np.array(e.matrix_world)
            co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            tri = np.empty(m * 3, dtype=np.int64)
            me.loop_triangles.foreach_get("vertices", tri)
            Vs.append(co)
            Ts.append(tri.reshape(-1, 3) + off)
            off += n
        finally:
            e.to_mesh_clear()
    if not Vs:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    return np.concatenate(Vs), np.concatenate(Ts)


def bvh_of(V, T):
    from mathutils.bvhtree import BVHTree
    if len(T) == 0:
        return None
    return BVHTree.FromPolygons(V.tolist(), T.tolist(), all_triangles=True)


def ray_hit(tree, o, d, length):
    """First hit (t, point, normal facing the origin) of the ray o + t d, 0 <= t <= length, or None."""
    from mathutils import Vector
    if tree is None or length <= 0:
        return None
    co, nrm, _i, t = tree.ray_cast(Vector(o), Vector(d), float(length))
    if co is None:
        return None
    n = np.array(nrm)
    if n.dot(np.asarray(o) - np.array(co)) < 0:
        n = -n
    return float(t), np.array(co), n


def last_crossing(tree, o, d, length):
    """Distance of the last surface crossed by the ray o + t d within length (0 = none)."""
    t, last = 0.0, 0.0
    while t < length:
        h = ray_hit(tree, o + d * (t + EPS), d, length - t - EPS)
        if h is None:
            break
        t += EPS + h[0]
        last = t
    return last


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else None


def _perp(n):
    a = np.array((1.0, 0.0, 0.0)) if abs(n[0]) < 0.9 else np.array((0.0, 1.0, 0.0))
    return _unit(np.cross(n, a))


def push_chain(tree, J, allow, clearance):
    """Stage A on one chain. J: (n+1, 3) baked joints (world), allow: per segment, the rest crossing distance from
    its start that is not tested (0 for a free segment). Returns (P, info): pushed joints (P[k] is J[k] bit for bit
    where nothing upstream changed and segment k crosses nothing) and {"moved": first changed joint or None,
    "hits": n, "shortened": n, "max_move_m": x}."""
    J = np.asarray(J, dtype=np.float64)
    P = J.copy()
    info = {"moved": None, "hits": 0, "shortened": 0, "max_move_m": 0.0}
    for k in range(1, len(J)):
        o = P[k - 1]
        L = float(np.linalg.norm(J[k] - J[k - 1]))
        if L <= 1e-9:
            P[k] = o
            continue
        d = _unit(J[k] - o)
        if d is None:
            d = _unit(J[k] - J[k - 1])
        a = float(allow[k - 1]) if k - 1 < len(allow) else 0.0
        h = ray_hit(tree, o + d * a, d, L - a) if a < L else None
        if h is None:
            if info["moved"] is not None:  # upstream changed: follow the leader towards the baked joint
                P[k] = o + d * L
            continue
        info["hits"] += 1
        q = None
        for _ in range(MAX_TRIES):
            t, hp, n = h
            s_o = float((o - hp).dot(n))
            tang = d - d.dot(n) * n
            tang = _unit(tang) if _unit(tang) is not None else _perp(n)
            c = min(1.0, max(-1.0, (clearance - s_o) / L))
            u = c * n + math.sqrt(max(0.0, 1.0 - c * c)) * tang
            h2 = ray_hit(tree, o + u * a, u, L - a) if a < L else None
            if h2 is None:
                q = o + u * L
                break
            d, h = u, h2
        if q is None:  # straight away from the last surface
            n = h[2]
            h2 = ray_hit(tree, o + n * a, n, L - a) if a < L else None
            if h2 is None:
                q = o + n * L
            else:  # blocked both ways: the last free point (shorter segment)
                q = o + n * max(a, h2[0] + a - clearance)
                info["shortened"] += 1
        P[k] = q
        if info["moved"] is None:
            info["moved"] = k
    if info["moved"] is not None:
        info["max_move_m"] = float(np.linalg.norm(P - J, axis=1).max())
    return P, info


def rest_allowance(tree, J):
    """Per segment of the rest chain J: the distance from its start up to which it already crosses the own figure
    at rest. Only the leading run counts (segment 0, and segment k only while the whole segment k-1 is embedded)."""
    allow = []
    for k in range(1, len(J)):
        L = float(np.linalg.norm(J[k] - J[k - 1]))
        d = _unit(J[k] - J[k - 1])
        if d is None or (k > 1 and allow[-1] < float(np.linalg.norm(J[k - 1] - J[k - 2])) - 1e-6):
            allow.append(0.0)
            continue
        e = last_crossing(tree, J[k - 1], d, L)
        allow.append(min(L, e + 0.001) if e > 0 else 0.0)
    return allow


def nearest_on_polyline(P, J):
    """For points P (n, 3) and polyline J (m+1, 3): (closest point (n, 3), segment index (n,))."""
    best = np.full(len(P), np.inf)
    out = np.zeros_like(P)
    seg = np.zeros(len(P), dtype=np.int64)
    for k in range(len(J) - 1):
        a, b = J[k], J[k + 1]
        ab = b - a
        ll = float(ab.dot(ab))
        t = np.clip(((P - a) @ ab) / ll, 0.0, 1.0) if ll > 1e-12 else np.zeros(len(P))
        c = a + t[:, None] * ab
        dist = np.einsum("ij,ij->i", P - c, P - c)
        m = dist < best
        best[m], out[m], seg[m] = dist[m], c[m], k
    return out, seg


def rotation_between(a, b):
    """3x3 minimal rotation taking unit direction a to unit direction b."""
    v = np.cross(a, b)
    c = float(a.dot(b))
    if c < -1 + 1e-12:
        p = _perp(a)
        return 2.0 * np.outer(p, p) - np.eye(3)
    vx = np.array(((0, -v[2], v[1]), (v[2], 0, -v[0]), (-v[1], v[0], 0)))
    return np.eye(3) + vx + vx @ vx / (1.0 + c)


# ---------------------------------------------------------------------------------------------------- the shot ----

class PushOut:
    """Built by shot_render after the characters, props and box objects exist (before any frame is keyed)."""

    def __init__(self, scene, spec, states, props, boxes):
        import bpy
        self.bpy = bpy
        self.scene = scene
        self.spec = spec
        self.states = states
        names = list(states) if spec["characters"] == "all" else [n for n in spec["characters"] if n in states]
        self.names = names
        self.report = {"spec": spec, "characters": {}, "frames": {}, "colliders": {}}
        self.figures = {n: sorted((o for o in st["ov"].all_objects if is_figure(o, st["rig"])), key=lambda o: o.name)
                        for n, st in states.items()}
        self.caps = self._caps(props)
        self.colliders = [o for n in sorted(self.figures) for o in self.figures[n]]
        self.colliders += [props[n] for n in sorted(props)] + self.caps + list(boxes)
        self.report["colliders"] = {n: [o.name for o in f] for n, f in self.figures.items()}
        self.report["colliders"]["props"] = sorted(props) + [o.name for o in self.caps] + [o.name for o in boxes]
        self.chains = {}
        self._rest()

    def _caps(self, props):
        """A closing disc for every open-top vessel (collider only, never rendered)."""
        bpy = self.bpy
        out = []
        for n in sorted(props):
            ob = props[n]
            if not any(m.type == "SOLIDIFY" for m in ob.modifiers):
                continue
            zs = [v.co.z for v in ob.data.vertices]
            top = max(zs)
            rim = [v.co for v in ob.data.vertices if abs(v.co.z - top) < 1e-6]
            if len(rim) < 3:
                continue
            r = max(math.hypot(c.x, c.y) for c in rim)
            me = bpy.data.meshes.new(f"{PREFIX}.cap.{n}")
            seg = 40
            vs = [(0.0, 0.0, top)] + [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), top)
                                       for i in range(seg)]
            me.from_pydata(vs, [], [(0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)])
            cap = bpy.data.objects.new(f"{PREFIX}.cap.{n}", me)
            self.scene.collection.objects.link(cap)
            cap.parent = ob
            cap.hide_render = True
            cap.display_type = "WIRE"
            out.append(cap)
        return out

    # -- rest: chain allowances and the anchors of stage B (own figure only, rest pose) ----------------------------
    def _rest(self):
        bpy = self.bpy
        saved = {}
        for n in self.names:
            for _i, pb in self.states[n]["bones"]:
                saved[(n, pb.name)] = (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy())
                pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        self.rest_trees = {}
        for n in self.names:
            st = self.states[n]
            rig = st["rig"]
            tree = bvh_of(*world_triangles(self.figures[n], deps))
            self.rest_trees[n] = tree
            dyn = rig.get("ps_dynamics")
            dyn = json.loads(dyn) if isinstance(dyn, str) else (dyn.to_dict() if hasattr(dyn, "to_dict") else dyn)
            W = np.array(rig.matrix_world)
            chains = []
            for ch in (dyn or {}).get("chains", []):
                bones = [b for b in ch["bones"] if b in rig.pose.bones]
                if len(bones) != len(ch["bones"]) or not bones:
                    continue
                db = rig.data.bones
                J = [db[bones[0]].head_local] + [db[b].tail_local for b in bones]
                J = np.array([W[:3, :3] @ np.array(j) + W[:3, 3] for j in J])
                chains.append({"name": ch["name"], "bones": bones, "rest": J, "allow": rest_allowance(tree, J)})
            self.chains[n] = chains
            self.report["characters"][n] = {"chains": len(chains), "allowed_root_segments":
                                            sum(1 for c in chains for a in c["allow"] if a > 0)}
        if "vertices" in self.spec["stages"]:
            for n in self.names:
                self._anchors(n)
        for n in self.names:
            for _i, pb in self.states[n]["bones"]:
                pb.location, pb.rotation_quaternion, pb.scale = saved[(n, pb.name)]
        bpy.context.view_layer.update()

    def _anchors(self, n):
        """Anchor proxies (stage B) for every hair object of character n."""
        bpy = self.bpy
        st = self.states[n]
        rig = st["rig"]
        tree = self.rest_trees[n]
        chain_of = {}
        for ci, c in enumerate(self.chains[n]):
            for k, b in enumerate(c["bones"]):
                chain_of[b] = (ci, k)
        head = st.get("head_bone")
        W = np.array(rig.matrix_world)
        hb = rig.data.bones.get(head) if head else None
        centre = (W[:3, :3] @ ((np.array(hb.head_local) + np.array(hb.tail_local)) / 2) + W[:3, 3]) if hb else None
        reach = float(self.spec["static_reach_m"])
        rep = {"objects": 0, "vertices": 0, "chain_anchors": 0, "static_anchors": 0, "anchors_moved_past_rest": 0,
               "static_without_anchor": 0}
        st["proxies"] = []
        for o in sorted((o for o in st["ov"].all_objects if o.type == "MESH" and is_hair(o)), key=lambda o: o.name):
            if not any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers):
                continue
            me = o.data
            nv = len(me.vertices)
            if nv == 0:
                continue
            Mo = np.array(o.matrix_world)
            co = np.empty(nv * 3)
            me.vertices.foreach_get("co", co)
            P = co.reshape(-1, 3) @ Mo[:3, :3].T + Mo[:3, 3]
            gname = [g.name for g in o.vertex_groups]
            wsum = np.zeros((nv, max(1, len(self.chains[n]))))
            for v in me.vertices:
                for g in v.groups:
                    nm = gname[g.group] if g.group < len(gname) else None
                    if nm in chain_of and g.weight > 0:
                        wsum[v.index, chain_of[nm][0]] += g.weight
            best = wsum.argmax(axis=1)
            is_chain = wsum.max(axis=1) >= CHAIN_MIN_WEIGHT
            A = P.copy()
            rigid = np.full(nv, -1, dtype=np.int64)  # index into the chain's bones, -1 = keep the vertex's weights
            for ci in np.unique(best[is_chain]):
                idx = np.nonzero(is_chain & (best == ci))[0]
                c = self.chains[n][ci]
                A[idx], seg = nearest_on_polyline(P[idx], c["rest"])
                rigid[idx] = seg
            stat = np.nonzero(~is_chain)[0]
            if centre is not None and len(stat):
                for i in stat:
                    r = _unit(P[i] - centre)
                    if r is None:
                        continue
                    h = ray_hit(tree, P[i] + r * EPS, r, reach)
                    hh = reach if h is None else max(0.0, h[0] - 0.001)
                    if hh <= 0.001:
                        rep["static_without_anchor"] += 1
                        continue
                    A[i] = P[i] + r * hh
            # an anchor whose ray to its vertex crosses the own figure at rest: past the last crossing
            for i in range(nv):
                d = P[i] - A[i]
                L = float(np.linalg.norm(d))
                if L < 1e-6:
                    continue
                d = d / L
                e = last_crossing(tree, A[i], d, L)
                if e > 0:
                    A[i] = A[i] + d * min(L, e + 0.0005)
                    rigid[i] = -1
                    rep["anchors_moved_past_rest"] += 1
            pm = me.copy()
            pm.name = f"{PREFIX}.anchor.{o.name}"
            Ai = np.linalg.inv(Mo)
            loc = A @ Ai[:3, :3].T + Ai[:3, 3]
            pm.vertices.foreach_set("co", loc.ravel())
            pm.update()
            px = bpy.data.objects.new(f"{PREFIX}.anchor.{o.name}", pm)
            self.scene.collection.objects.link(px)
            px.parent = o.parent
            px.parent_type = o.parent_type
            px.parent_bone = o.parent_bone
            px.matrix_parent_inverse = o.matrix_parent_inverse.copy()
            px.matrix_world = o.matrix_world.copy()
            for g in gname:
                if g not in px.vertex_groups:
                    px.vertex_groups.new(name=g)
            c_idx = np.nonzero(rigid >= 0)[0]
            if len(c_idx):
                ids = c_idx.tolist()
                for vg in px.vertex_groups:
                    vg.remove(ids)
                for ci in np.unique(best[c_idx]):
                    sel = c_idx[best[c_idx] == ci]
                    for k in np.unique(rigid[sel]):
                        bn = self.chains[n][ci]["bones"][k]
                        vg = px.vertex_groups.get(bn) or px.vertex_groups.new(name=bn)
                        vg.add(sel[rigid[sel] == k].tolist(), 1.0, "REPLACE")
            am = px.modifiers.new("Armature", "ARMATURE")
            am.object = rig
            px.hide_render = True
            px.display_type = "WIRE"
            st["proxies"].append((o, px))
            rep["objects"] += 1
            rep["vertices"] += nv
            rep["chain_anchors"] += int(len(c_idx))
            rep["static_anchors"] += int(len(stat))
        self.report["characters"][n]["vertex_stage"] = rep

    # -- stage A ---------------------------------------------------------------------------------------------------
    def frame(self, f, key_bone):
        """Stage A at frame f (the scene must be at frame f with every bone keyed). Re-keys the changed DYN bones;
        returns the set of (character, bone name) it re-keyed."""
        done = set()
        if "chains" not in self.spec["stages"]:
            return done
        bpy = self.bpy
        deps = bpy.context.evaluated_depsgraph_get()
        tree = bvh_of(*world_triangles(self.colliders, deps))
        clearance = float(self.spec["core_radius_m"]) + float(self.spec["margin_m"])
        fr = {}
        for n in self.names:
            rig = self.states[n]["rig"]
            W = np.array(rig.matrix_world)
            Wi = np.linalg.inv(W)
            out = {"chains_pushed": 0, "joints_moved": 0, "hits": 0, "shortened": 0, "max_move_mm": 0.0}
            for c in self.chains[n]:
                pbs = [rig.pose.bones[b] for b in c["bones"]]
                J = [pbs[0].head] + [pb.tail for pb in pbs]
                J = np.array([W[:3, :3] @ np.array(j) + W[:3, 3] for j in J])
                P, info = push_chain(tree, J, c["allow"], clearance)
                out["hits"] += info["hits"]
                out["shortened"] += info["shortened"]
                if info["moved"] is None:
                    continue
                out["chains_pushed"] += 1
                out["joints_moved"] += int((np.linalg.norm(P - J, axis=1) > 0).sum())
                out["max_move_mm"] = max(out["max_move_mm"], round(info["max_move_m"] * 1e3, 2))
                self._rekey(rig, pbs, J, P, info["moved"], W, Wi, f, key_bone)
                done.update((n, pb.name) for pb in pbs[info["moved"] - 1:])
            fr[n] = out
        self.report["frames"][f] = fr
        return done

    def _rekey(self, rig, pbs, J, P, first, W, Wi, f, key_bone):
        from mathutils import Matrix
        prev = None
        for b in range(first - 1, len(pbs)):
            pb = pbs[b]
            M = np.array(pb.matrix)  # armature space, evaluated
            old = _unit(Wi[:3, :3] @ (J[b + 1] - J[b]))
            new = _unit(Wi[:3, :3] @ (P[b + 1] - P[b]))
            Mn = M.copy()
            if old is not None and new is not None:
                Mn[:3, :3] = rotation_between(old, new) @ M[:3, :3]
            Mn[:3, 3] = Wi[:3, :3] @ P[b] + Wi[:3, 3]
            Pm = Matrix(Mn.tolist())
            parent = prev if prev is not None else (pb.parent.matrix if pb.parent is not None else None)
            key_bone(pb, Pm, parent, f)
            prev = Pm

    # -- stage B ---------------------------------------------------------------------------------------------------
    def install(self):
        """After every frame is keyed: the collider set object and the per-vertex modifier on every hair object."""
        if "vertices" not in self.spec["stages"]:
            return
        bpy = self.bpy
        col = bpy.data.collections.new(f"{PREFIX}.colliders")
        for o in self.colliders:
            col.objects.link(o)
        cs = bpy.data.objects.new(f"{PREFIX}.collider_set", bpy.data.meshes.new(f"{PREFIX}.collider_set"))
        self.scene.collection.objects.link(cs)
        cs.hide_render = True
        mg = cs.modifiers.new("collect", "NODES")
        mg.node_group = _collector_group(col)
        group = _clamp_group(float(self.spec["vertex_margin_m"]))
        for n in self.names:
            for o, px in self.states[n].get("proxies", []):
                m = o.modifiers.new(f"{PREFIX}", "NODES")
                m.node_group = _bind_group(group, px, cs, o.name)
        self.report["vertex_stage_installed"] = True


def _collector_group(col):
    import bpy
    ng = bpy.data.node_groups.new(f"{PREFIX}.collect", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    go = N.new("NodeGroupOutput")
    ci = N.new("GeometryNodeCollectionInfo")
    ci.transform_space = "RELATIVE"
    ci.inputs["Collection"].default_value = col
    rl = N.new("GeometryNodeRealizeInstances")
    L.new(ci.outputs[0], rl.inputs[0])
    L.new(rl.outputs[0], go.inputs[0])
    return ng


def _clamp_group(margin):
    """Shared clamp: inputs Geometry, Anchors (geometry, world), Colliders (geometry, world), Self (matrix)."""
    import bpy
    ng = bpy.data.node_groups.new(f"{PREFIX}.clamp", "GeometryNodeTree")
    I = ng.interface
    I.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Anchors", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Colliders", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Self", in_out="INPUT", socket_type="NodeSocketMatrix")
    I.new_socket("Anchor Space", in_out="INPUT", socket_type="NodeSocketMatrix")
    I.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    pos, idx = N.new("GeometryNodeInputPosition"), N.new("GeometryNodeInputIndex")
    tw = N.new("FunctionNodeTransformPoint")  # vertex, world
    L.new(pos.outputs[0], tw.inputs["Vector"])
    L.new(gi.outputs["Self"], tw.inputs["Transform"])
    si = N.new("GeometryNodeSampleIndex")
    si.data_type, si.domain = "FLOAT_VECTOR", "POINT"
    L.new(gi.outputs["Anchors"], si.inputs["Geometry"])
    L.new(pos.outputs[0], si.inputs["Value"])
    L.new(idx.outputs[0], si.inputs["Index"])
    ta = N.new("FunctionNodeTransformPoint")  # anchor, world
    L.new(si.outputs[0], ta.inputs["Vector"])
    L.new(gi.outputs["Anchor Space"], ta.inputs["Transform"])
    d = N.new("ShaderNodeVectorMath")
    d.operation = "SUBTRACT"
    L.new(tw.outputs[0], d.inputs[0])
    L.new(ta.outputs[0], d.inputs[1])
    ln = N.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    L.new(d.outputs[0], ln.inputs[0])
    nd = N.new("ShaderNodeVectorMath")
    nd.operation = "NORMALIZE"
    L.new(d.outputs[0], nd.inputs[0])
    rc = N.new("GeometryNodeRaycast")
    L.new(gi.outputs["Colliders"], rc.inputs["Target Geometry"])
    L.new(ta.outputs[0], rc.inputs["Source Position"])
    L.new(nd.outputs[0], rc.inputs["Ray Direction"])
    L.new(ln.outputs["Value"], rc.inputs["Ray Length"])
    m1 = N.new("ShaderNodeMath")
    m1.operation = "SUBTRACT"
    L.new(rc.outputs["Hit Distance"], m1.inputs[0])
    m1.inputs[1].default_value = margin
    m2 = N.new("ShaderNodeMath")
    m2.operation = "MAXIMUM"
    L.new(m1.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = 0.0
    sc = N.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    L.new(nd.outputs[0], sc.inputs[0])
    L.new(m2.outputs[0], sc.inputs["Scale"])
    ad = N.new("ShaderNodeVectorMath")
    ad.operation = "ADD"
    L.new(ta.outputs[0], ad.inputs[0])
    L.new(sc.outputs[0], ad.inputs[1])
    inv = N.new("FunctionNodeInvertMatrix")
    L.new(gi.outputs["Self"], inv.inputs[0])
    tl = N.new("FunctionNodeTransformPoint")  # back to object space
    L.new(ad.outputs[0], tl.inputs["Vector"])
    L.new(inv.outputs[0], tl.inputs["Transform"])
    sp = N.new("GeometryNodeSetPosition")
    L.new(gi.outputs["Geometry"], sp.inputs["Geometry"])
    L.new(rc.outputs["Is Hit"], sp.inputs["Selection"])
    L.new(tl.outputs[0], sp.inputs["Position"])
    L.new(sp.outputs[0], go.inputs[0])
    return ng


def _bind_group(clamp, proxy, collider_set, name):
    """Per hair object: wires its proxy, the collider set and the object transforms into the shared clamp."""
    import bpy
    ng = bpy.data.node_groups.new(f"{PREFIX}.{name}", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    me = N.new("GeometryNodeSelfObject")
    oself = N.new("GeometryNodeObjectInfo")
    oself.transform_space = "ORIGINAL"
    L.new(me.outputs[0], oself.inputs["Object"])
    op = N.new("GeometryNodeObjectInfo")
    op.transform_space = "ORIGINAL"
    op.inputs["Object"].default_value = proxy
    oc = N.new("GeometryNodeObjectInfo")
    oc.transform_space = "ORIGINAL"
    oc.inputs["Object"].default_value = collider_set
    g = N.new("GeometryNodeGroup")
    g.node_tree = clamp
    L.new(gi.outputs[0], g.inputs["Geometry"])
    L.new(op.outputs["Geometry"], g.inputs["Anchors"])
    L.new(oc.outputs["Geometry"], g.inputs["Colliders"])
    L.new(oself.outputs["Transform"], g.inputs["Self"])
    L.new(op.outputs["Transform"], g.inputs["Anchor Space"])
    L.new(g.outputs[0], go.inputs[0])
    return ng
