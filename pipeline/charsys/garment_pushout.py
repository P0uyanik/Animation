"""Render-time garment push-out (T-222, L1 part A): garment vertices that end up inside their own character's posed
body are moved back out, on the real evaluated meshes, Blender side. Opt-in (`shot_render.py --garment-pushout`);
without it nothing here runs. It reuses the T-194 hair push-out's stage B pattern (hair_pushout.py): a hidden
skinned proxy per object gives every vertex a reference that follows the body, and one Geometry Nodes modifier per
garment object does the per-vertex work. Stateless per frame (the result at frame f depends only on the evaluated
meshes at f), no Python at render time.

Per garment vertex, at REST (setup, every pose bone at rest):
  n   the body's outward direction: the normal of the own solids' face nearest to the vertex, averaged twice over the
      garment's edges (a crease of the body does not tear neighbouring vertices apart)
  c0  the rest clearance: the distance along -n from the vertex to the solids' front face, capped at
      `clearance_cap_m` (a vertex that far from the body or farther is "free"); a vertex that is inside the solids at
      rest (its rays along +n and -n both first meet a BACK face) has c0 = -(that distance): it was modelled there
Two hidden proxies per garment object carry the vertex (base) and the vertex + `reach_m` * n (tip), skinned with the
vertex's own weights; at frame f, dir = tip - base (normalised) is the rest-outward direction as the body moves.

At frame f (Geometry Nodes, after the garment's Armature modifier, before its body_collision shrinkwraps):
  s   the signed clearance along dir. Inside: the winding numbers along +dir and along -dir over the first
      `ray_hits` crossings of the own solids (back face +1, front face -1, within `max_exit_m`) are both positive (a
      ray leaking out through a wrist or neck opening disagrees with its opposite one); the exit is the first crossing
      where the count reaches its total, or the nearest surface point when that is nearer and within
      `nearest_cone_deg` of dir (a limb turned along dir: the seated thigh against the shorts' front panel; the
      crook of a bend, where an unbent sleeve belongs back towards its own axis); s = -(exit distance). A vertex
      inside more than `max_winding` parts at once (the posed body overlapping itself: thigh in belly, calf in
      thigh) is deep and covered and is left as baked. Outside: a ray along -dir up to c0 that meets a FRONT face
      gives s = its distance; else the vertex is free (not moved)
  g   the target clearance. c0 > margin: a soft clamp, g(s) = s for s >= c0 and m + k * exp((s - c0) / k) below
      (m = `margin_m`, k = c0 - m): continuous with slope 1 at c0, never below m, and monotone in c0, so a layer that
      sat over another at rest (vest over blouse) stays over it when both are pushed. c0 <= margin: hard clamp at c0
      (a vertex embedded at rest is pushed only back to its rest depth, as contact_audit's rest rule counts it).
      At rest s = c0, so the rest pose is unchanged.
  move = g - s along dir, faded out between `move_fade_m` [a, b] (a vertex that would have to jump more than b is
      left as baked: a pop is worse than a hidden overlap; such cases are reported by the audit), then optionally
      feathered: the offset field is blurred over the garment's edges `smooth_iterations` times and every vertex
      takes the longer of its own and the blurred offset. The step runs `passes` times in a row (a vertex pushed
      out of one part into an overlapping one leaves it in the next pass).

Solids (the colliders), per character, own body only (other characters are staging, T-191): the unmasked collision
proxies (`ps_collision_proxy`) plus the rendered body meshes deformed by the rig that have no MASK modifier (hands,
ears), except hair, garments, widgets and the face parts of hair_pushout.SKIP: contact_audit's "solid" role.
Garments: the rendered meshes with `ps_garment_item` deformed by the rig (spec `items` filters by item name).
No character name or dimension is in this file; per-shot values go in the spec."""
import fnmatch
import json
import math

import numpy as np

import hair_pushout as HP

PREFIX = "ps_garment_pushout"
EPS = 1e-5
DEFAULTS = {"characters": "all", "items": "all", "margin_m": 0.0015, "clearance_cap_m": 0.01, "reach_m": 0.01,
            "max_exit_m": 0.5, "move_fade_m": [0.02, 0.03], "smooth_iterations": 0, "normal_smooth": 2,
            "nearest_cone_deg": 150.0, "ray_hits": 4, "passes": 2,
            "max_winding": 1, "max_step_m": 0.003}


def load_spec(arg):
    """`--garment-pushout` value: "on" (defaults), a JSON file, or inline JSON. Unknown keys are refused."""
    spec = dict(DEFAULTS)
    if arg in (None, "", "on", "1", "true"):
        return spec
    s = arg.strip()
    user = json.loads(s) if s.startswith("{") else json.load(open(s))
    bad = sorted(set(user) - set(DEFAULTS))
    if bad:
        raise ValueError(f"garment push-out: unknown keys {bad} (have {sorted(DEFAULTS)})")
    spec.update(user)
    if len(spec["move_fade_m"]) != 2 or not spec["move_fade_m"][1] > spec["move_fade_m"][0]:
        raise ValueError("garment push-out: move_fade_m must be [a, b] with b > a")
    for k in ("margin_m", "clearance_cap_m", "reach_m", "max_exit_m"):
        if not float(spec[k]) > 0:
            raise ValueError(f"garment push-out: {k} must be > 0")
    if spec["clearance_cap_m"] <= spec["margin_m"]:
        raise ValueError("garment push-out: clearance_cap_m must be larger than margin_m")
    return spec


# ------------------------------------------------------------------------------------------------------ roles ----

def _deformed_by(o, rig):
    return any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)


def solids(objs, rig):
    """The own closed solids of one character (module doc)."""
    out = []
    for o in objs:
        if o.type != "MESH" or not _deformed_by(o, rig) or o.name.startswith(("WGT-", HP.PREFIX, PREFIX)):
            continue
        if o.get("ps_collision_proxy"):
            out.append(o)
            continue
        if o.hide_render or HP.is_hair(o) or "ps_garment_item" in o.keys():
            continue
        if any(fnmatch.fnmatchcase(o.name, p) for p in HP.SKIP) or any(m.type == "MASK" for m in o.modifiers):
            continue
        out.append(o)
    return sorted(out, key=lambda o: o.name)


def garments(objs, rig, items="all"):
    return sorted((o for o in objs if o.type == "MESH" and "ps_garment_item" in o.keys() and not o.hide_render
                   and _deformed_by(o, rig) and (items == "all" or o["ps_garment_item"] in items)),
                  key=lambda o: o.name)


# ------------------------------------------------------------------------------------------------- rest data ----

def smooth_normals(N, edges, iterations):
    """Averages unit vectors over mesh edges (Laplacian, `iterations` times), renormalised."""
    if iterations <= 0 or not len(edges):
        return N
    a, b = edges[:, 0], edges[:, 1]
    for _ in range(iterations):
        acc = N.copy()
        np.add.at(acc, a, N[b])
        np.add.at(acc, b, N[a])
        ln = np.linalg.norm(acc, axis=1, keepdims=True)
        N = np.where(ln > 1e-12, acc / np.maximum(ln, 1e-12), N)
    return N


def winding_exit(tree, p, d, length, hits):
    """(winding number, exit distance) along the ray p + t d over its first `hits` crossings (the node rule)."""
    T, r, rec = 0.0, 0, []
    for _ in range(hits):
        h = tree.ray_cast(p + d * (T + EPS), d, max(length - T, 0.0))
        if h[0] is None:
            break
        r += 1 if h[1].dot(d) > 0 else -1
        T = T + EPS + h[3]
        rec.append((r, T))
    exit_t = next((Tj for rj, Tj in rec if rj == r), length)
    return r, exit_t


def rest_frame(tree, P, edges, cap, max_exit, normal_smooth, cone=0.0, hits=4):
    """(n, c0) per vertex at rest (module doc). tree: BVH of the own solids (world)."""
    from mathutils import Vector
    nv = len(P)
    N = np.zeros((nv, 3))
    near = []
    for i in range(nv):
        loc, nrm, _idx, dist = tree.find_nearest(Vector(P[i]))
        N[i] = nrm if loc is not None else (0.0, 0.0, 1.0)
        near.append((np.array(loc) if loc is not None else None, dist))
    N = smooth_normals(N, edges, normal_smooth)
    c0 = np.full(nv, float(cap))
    for i in range(nv):
        p, d = Vector(P[i]), Vector(N[i])
        w, t = winding_exit(tree, p, d, max_exit, hits)
        wb, _tb = winding_exit(tree, p, -d, max_exit, hits)
        if w > 0 and wb > 0:  # inside at rest (the frame rule)
            loc, dist = near[i]
            # the frame rule: the nearest surface point when nearer and within the cone of n
            if loc is not None and dist < t and np.dot(loc - P[i], N[i]) > cone * max(float(dist), 1e-12):
                t = float(dist)
            c0[i] = -t
            continue
        h = tree.ray_cast(p, -d, cap)
        if h[0] is not None and np.dot(np.array(h[1]), N[i]) > 0:  # front face of the body behind the vertex
            c0[i] = float(h[3])
    return N, c0


class GarmentPushOut:
    """Built by shot_render after the characters exist (before any frame is keyed); install() after the keys."""

    def __init__(self, scene, spec, states):
        import bpy
        self.bpy = bpy
        self.scene = scene
        self.spec = spec
        names = list(states) if spec["characters"] == "all" else [n for n in spec["characters"] if n in states]
        self.names = names
        self.states = states
        self.report = {"spec": spec, "characters": {}}
        self.solids, self.garments, self.proxies = {}, {}, {}
        for n in names:
            st = states[n]
            objs = list(st["ov"].all_objects)
            self.solids[n] = solids(objs, st["rig"])
            self.garments[n] = garments(objs, st["rig"], spec["items"])
        self._rest()

    def _rest(self):
        bpy = self.bpy
        saved, muted, actions = {}, [], {}
        for n in self.names:
            rig = self.states[n]["rig"]
            ad = rig.animation_data
            if ad is not None and ad.action is not None:  # a keyed scene (none in shot_render: built before the keys)
                actions[n] = (ad.action, getattr(ad, "action_slot", None))
                ad.action = None
            for pb in rig.pose.bones:
                saved[(n, pb.name)] = (pb.location.copy(), pb.rotation_quaternion.copy(), pb.rotation_euler.copy(),
                                       pb.scale.copy())
                pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
                pb.rotation_euler = (0, 0, 0)
            for o in self.garments[n]:  # the input of the push-out is the skinned mesh (before the shrinkwraps)
                after = False
                for m in o.modifiers:
                    if after and m.show_viewport:
                        m.show_viewport = False
                        muted.append(m)
                    after = after or (m.type == "ARMATURE")
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        cap, mx = float(self.spec["clearance_cap_m"]), float(self.spec["max_exit_m"])
        reach = float(self.spec["reach_m"])
        for n in self.names:
            tree = HP.bvh_of(*HP.world_triangles(self.solids[n], deps))
            rep = {"solids": [o.name for o in self.solids[n]], "objects": 0, "vertices": 0, "inside_at_rest": 0,
                   "near_at_rest": 0}
            self.proxies[n] = []
            for o in self.garments[n]:
                e = o.evaluated_get(deps)
                me = e.to_mesh()
                nv = len(me.vertices)
                co = np.empty(nv * 3)
                me.vertices.foreach_get("co", co)
                e.to_mesh_clear()
                if nv == 0 or nv != len(o.data.vertices):
                    continue
                M = np.array(o.matrix_world)
                P = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
                ed = np.empty(len(o.data.edges) * 2, dtype=np.int64)
                o.data.edges.foreach_get("vertices", ed)
                Nw, c0 = rest_frame(tree, P, ed.reshape(-1, 2), cap, mx, int(self.spec["normal_smooth"]),
                                    math.cos(math.radians(float(self.spec["nearest_cone_deg"]))),
                                    int(self.spec["ray_hits"]))
                Mi = np.linalg.inv(M)
                base = P @ Mi[:3, :3].T + Mi[:3, 3]
                tip = (P + reach * Nw) @ Mi[:3, :3].T + Mi[:3, 3]
                pb_, pt_ = self._proxy(o, base, "base"), self._proxy(o, tip, "tip")
                a = pb_.data.attributes.new("ps_rest_clearance", "FLOAT", "POINT")
                a.data.foreach_set("value", c0.astype(np.float32))
                pb_.data.update()
                self.proxies[n].append((o, pb_, pt_))
                rep["objects"] += 1
                rep["vertices"] += nv
                rep["inside_at_rest"] += int((c0 < 0).sum())
                rep["near_at_rest"] += int(((c0 >= 0) & (c0 < cap)).sum())
            self.report["characters"][n] = rep
        for m in muted:
            m.show_viewport = True
        for n in self.names:
            for pb in self.states[n]["rig"].pose.bones:
                pb.location, pb.rotation_quaternion, pb.rotation_euler, pb.scale = saved[(n, pb.name)]
            if n in actions:
                ad = self.states[n]["rig"].animation_data
                ad.action = actions[n][0]
                if actions[n][1] is not None:
                    ad.action_slot = actions[n][1]
        bpy.context.view_layer.update()

    def _proxy(self, o, co_local, kind):
        """A hidden copy of garment o's mesh with its vertices at co_local, skinned like o (Armature only)."""
        bpy = self.bpy
        rig = next(m.object for m in o.modifiers if m.type == "ARMATURE")
        pm = o.data.copy()
        pm.name = f"{PREFIX}.{kind}.{o.name}"
        pm.vertices.foreach_set("co", co_local.ravel())
        pm.update()
        px = bpy.data.objects.new(pm.name, pm)
        self.scene.collection.objects.link(px)
        px.parent = o.parent
        px.parent_type = o.parent_type
        px.parent_bone = o.parent_bone
        px.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        px.matrix_world = o.matrix_world.copy()
        for g in o.vertex_groups:
            if g.name not in px.vertex_groups:
                px.vertex_groups.new(name=g.name)
        src = next(m for m in o.modifiers if m.type == "ARMATURE")
        am = px.modifiers.new("Armature", "ARMATURE")
        am.object = rig
        am.use_vertex_groups, am.use_bone_envelopes = src.use_vertex_groups, src.use_bone_envelopes
        am.use_deform_preserve_volume = src.use_deform_preserve_volume
        px.hide_render = True
        px.hide_viewport = False
        px.display_type = "WIRE"
        return px

    def install(self):
        """The per-character solid set and the modifier on every garment object (after its last Armature)."""
        bpy = self.bpy
        group = _push_group(self.spec)
        for n in self.names:
            col = bpy.data.collections.new(f"{PREFIX}.solids.{n}")
            for o in self.solids[n]:
                col.objects.link(o)
            cs = bpy.data.objects.new(f"{PREFIX}.solid_set.{n}", bpy.data.meshes.new(f"{PREFIX}.solid_set.{n}"))
            self.scene.collection.objects.link(cs)
            cs.hide_render = True
            cs.modifiers.new("collect", "NODES").node_group = HP._collector_group(col)
            for o, pb_, pt_ in self.proxies[n]:
                m = o.modifiers.new(PREFIX, "NODES")
                m.node_group = _bind_group(group, pb_, pt_, cs, o.name, int(self.spec["passes"]),
                                           float(self.spec["max_step_m"]))
                last = max(i for i, mm in enumerate(o.modifiers) if mm.type == "ARMATURE")
                o.modifiers.move(len(o.modifiers) - 1, last + 1)
                if float(self.spec["max_step_m"]) > 0:
                    m.bake_target = "PACKED"  # the rate limit's state is baked into the shot.blend (bake())
        self.report["installed"] = True

    def bake(self):
        """Bakes the rate limit (every garment modifier's simulation zone) over the scene's frame range, packed into
        the .blend: frames can then be evaluated in any order and in other processes (render, audits).
        Returns {"frames", "objects", "points" (largest state per object and frame), "seconds"}."""
        import time
        bpy = self.bpy
        if float(self.spec["max_step_m"]) <= 0:
            return None
        t = time.time()
        mods = [(o, o.modifiers[PREFIX]) for n in self.names for o, _b, _t in self.proxies[n]]
        sc = self.scene
        for o, m in mods:
            for b in m.bakes:
                b.bake_target = "PACKED"
                b.use_custom_simulation_frame_range = True
                b.frame_start, b.frame_end = sc.frame_start, sc.frame_end
        # one pass over the frames for every garment (the scene-wide bake needs the objects as the selection in
        # background mode); objects the push-out does not read are hidden meanwhile (hair, face, props: speed)
        objs = [o for o, _m in mods]
        need = set(objs) | {self.states[n]["rig"] for n in self.names}
        for n in self.names:
            need |= set(self.solids[n]) | {x for _o, b_, t_ in self.proxies[n] for x in (b_, t_)}
        need |= {o for o in sc.objects if o.name.startswith(f"{PREFIX}.solid_set.")}
        hidden = [o for o in sc.objects if o.type == "MESH" and o not in need and not o.hide_viewport]
        for o in hidden:
            o.hide_viewport = True
        try:
            with bpy.context.temp_override(selected_objects=objs, selected_editable_objects=objs, active_object=objs[0],
                                           object=objs[0], visible_objects=objs, view_layer=bpy.context.view_layer,
                                           scene=sc):
                r = bpy.ops.object.simulation_nodes_cache_bake(selected=True)
        finally:
            for o in hidden:
                o.hide_viewport = False
        if "FINISHED" not in r:
            raise RuntimeError(f"garment push-out: bake failed: {r}")
        out = {"frames": [sc.frame_start, sc.frame_end], "objects": len(mods), "seconds": round(time.time() - t, 1)}
        self.report["bake"] = out
        return out


# --------------------------------------------------------------------------------------------- node groups ----

def _push_group(spec):
    """Shared per-vertex push: inputs Geometry, Base, Tip (proxies, own space), Solids (world), Self, Proxy Space."""
    import bpy
    margin, cap = float(spec["margin_m"]), float(spec["clearance_cap_m"])
    mx, (fa, fb) = float(spec["max_exit_m"]), [float(x) for x in spec["move_fade_m"]]
    ng = bpy.data.node_groups.new(f"{PREFIX}.push", "GeometryNodeTree")
    I = ng.interface
    I.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Base", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Tip", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Solids", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Self", in_out="INPUT", socket_type="NodeSocketMatrix")
    I.new_socket("Proxy Space", in_out="INPUT", socket_type="NodeSocketMatrix")
    I.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")

    def vm(op, a, b=None, scale=None):
        n_ = N.new("ShaderNodeVectorMath")
        n_.operation = op
        for k, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (tuple, list)):
                n_.inputs[k].default_value = x
            else:
                L.new(x, n_.inputs[k])
        if scale is not None:
            if isinstance(scale, (int, float)):
                n_.inputs["Scale"].default_value = scale
            else:
                L.new(scale, n_.inputs["Scale"])
        return n_

    def fm(op, a, b=None, clamp=False):
        n_ = N.new("ShaderNodeMath")
        n_.operation = op
        n_.use_clamp = clamp
        for k, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n_.inputs[k].default_value = x
            else:
                L.new(x, n_.inputs[k])
        return n_.outputs[0]

    def cmp(op, a, b):
        n_ = N.new("FunctionNodeCompare")
        n_.data_type, n_.operation = "FLOAT", op
        L.new(a, n_.inputs[0])
        if isinstance(b, (int, float)):
            n_.inputs[1].default_value = b
        else:
            L.new(b, n_.inputs[1])
        return n_.outputs[0]

    def boolean(op, a, b=None):
        n_ = N.new("FunctionNodeBooleanMath")
        n_.operation = op
        L.new(a, n_.inputs[0])
        if b is not None:
            L.new(b, n_.inputs[1])
        return n_.outputs[0]

    def switch(kind, cond, f, t):
        n_ = N.new("GeometryNodeSwitch")
        n_.input_type = kind
        L.new(cond, n_.inputs["Switch"])
        for k, x in (("False", f), ("True", t)):
            if isinstance(x, (int, float)):
                n_.inputs[k].default_value = x
            else:
                L.new(x, n_.inputs[k])
        return n_.outputs[0]

    def sample(geo, value, dtype):
        n_ = N.new("GeometryNodeSampleIndex")
        n_.data_type, n_.domain = dtype, "POINT"
        L.new(geo, n_.inputs["Geometry"])
        L.new(value, n_.inputs["Value"])
        L.new(idx.outputs[0], n_.inputs["Index"])
        return n_.outputs[0]

    def to_world(v, mat):
        n_ = N.new("FunctionNodeTransformPoint")
        L.new(v, n_.inputs["Vector"])
        L.new(mat, n_.inputs["Transform"])
        return n_.outputs[0]

    def ray(src, d, length):
        n_ = N.new("GeometryNodeRaycast")
        L.new(gi.outputs["Solids"], n_.inputs["Target Geometry"])
        L.new(src, n_.inputs["Source Position"])
        L.new(d, n_.inputs["Ray Direction"])
        if isinstance(length, (int, float)):
            n_.inputs["Ray Length"].default_value = length
        else:
            L.new(length, n_.inputs["Ray Length"])
        back = cmp("GREATER_THAN", vm("DOT_PRODUCT", n_.outputs["Hit Normal"], d).outputs["Value"], 0.0)
        return n_.outputs["Is Hit"], back, n_.outputs["Hit Distance"]

    pos, idx = N.new("GeometryNodeInputPosition"), N.new("GeometryNodeInputIndex")
    pw = to_world(pos.outputs[0], gi.outputs["Self"])
    bw = to_world(sample(gi.outputs["Base"], pos.outputs[0], "FLOAT_VECTOR"), gi.outputs["Proxy Space"])
    tw = to_world(sample(gi.outputs["Tip"], pos.outputs[0], "FLOAT_VECTOR"), gi.outputs["Proxy Space"])
    d = vm("NORMALIZE", vm("SUBTRACT", tw, bw).outputs[0]).outputs[0]
    nd = vm("SCALE", d, scale=-1.0).outputs[0]
    ca = N.new("GeometryNodeInputNamedAttribute")
    ca.data_type = "FLOAT"
    ca.inputs["Name"].default_value = "ps_rest_clearance"
    c0 = sample(gi.outputs["Base"], ca.outputs["Attribute"], "FLOAT")
    # inside: the winding number along +dir over the first `ray_hits` crossings (back face +1, front face -1) is
    # positive; one first hit alone is fooled where the body mesh passes into itself (seated thighs into the belly,
    # e912 s010 f70: inside the thigh AND the belly). The exit along dir is the first crossing where the count reaches
    # its total (from there on the ray is outside every part).
    def walk(dv):
        """(winding number, [(hit, running count, distance)]) along dv over the first `ray_hits` crossings."""
        T, r, rec = 0.0, 0.0, []
        for _j in range(int(spec["ray_hits"])):
            src = vm("ADD", pw, vm("SCALE", dv, scale=fm("ADD", T, EPS) if not isinstance(T, float) else T + EPS)
                     .outputs[0]).outputs[0]
            hit, back, dist = ray(src, dv, fm("MAXIMUM", fm("SUBTRACT", mx, T), 0.0) if not isinstance(T, float)
                                  else mx)
            step = switch("FLOAT", hit, 0.0, switch("FLOAT", back, -1.0, 1.0))
            r = fm("ADD", r, step) if not isinstance(r, float) else step
            T = switch("FLOAT", hit, T, fm("ADD", fm("ADD", T, EPS), dist) if not isinstance(T, float) else
                       fm("ADD", T + EPS, dist))
            rec.append((hit, r, T))
        return r, rec
    W, rec = walk(d)
    Wb, _recb = walk(nd)
    # inside along both +dir and -dir (a ray that leaks out through an opening of the body, a wrist or the neck,
    # disagrees with its opposite one: isolated spikes of 50-70 mm, e912 s010 f3-4)
    inside = boolean("AND", cmp("GREATER_THAN", W, 0.5), cmp("GREATER_THAN", Wb, 0.5))
    # inside more than `max_winding` parts at once (an overlap of the posed body with itself: seated thigh in the
    # belly, calf in the thigh): deep and covered on every side; a move out of one part ends inside the other
    deep = cmp("GREATER_THAN", fm("MAXIMUM", W, Wb), float(spec["max_winding"]) + 0.5)
    t1 = mx
    for hit, rj, Tj in reversed(rec):
        at = boolean("AND", hit, cmp("LESS_THAN", fm("ABSOLUTE", fm("SUBTRACT", rj, W)), 0.5))
        t1 = switch("FLOAT", at, t1, Tj)
    # an inside vertex leaves by the nearest surface point when that is on its outer side (within 90 degrees of
    # dir) and nearer than the exit along dir (a limb turned along dir: seated thigh vs the shorts' front panel)
    px = N.new("GeometryNodeProximity")
    px.target_element = "FACES"
    L.new(gi.outputs["Solids"], px.inputs["Target"] if "Target" in px.inputs else px.inputs[0])
    L.new(pw, px.inputs["Source Position"])
    tn = px.outputs["Distance"]
    un = vm("NORMALIZE", vm("SUBTRACT", px.outputs["Position"], pw).outputs[0]).outputs[0]
    cone = math.cos(math.radians(float(spec["nearest_cone_deg"])))
    use_n = boolean("AND", inside, boolean("AND", cmp("GREATER_THAN", vm("DOT_PRODUCT", un, d).outputs["Value"], cone),
                                                 cmp("LESS_THAN", tn, t1)))
    t_in = switch("FLOAT", use_n, t1, tn)
    hit2, back2, t2 = ray(pw, nd, cap)
    behind = boolean("NIMPLY", hit2, back2)  # hit and not a back face: the body's front face behind the vertex
    near = boolean("AND", boolean("NOT", inside), behind)
    s = switch("FLOAT", inside, t2, fm("MULTIPLY", t_in, -1.0))
    active = boolean("AND", boolean("OR", inside, near), boolean("NOT", deep))
    # g(s): soft clamp for c0 > margin, hard clamp at c0 otherwise
    k = fm("SUBTRACT", c0, margin)
    soft = cmp("GREATER_THAN", k, 1e-5)
    ks = fm("MAXIMUM", k, 1e-5)
    e = fm("EXPONENT", fm("DIVIDE", fm("MINIMUM", fm("SUBTRACT", s, c0), 0.0), ks))
    g_soft = fm("ADD", margin, fm("MULTIPLY", ks, e))
    g_soft = fm("MAXIMUM", g_soft, s)
    g_hard = fm("MAXIMUM", s, c0)
    g = switch("FLOAT", soft, g_hard, g_soft)
    move = fm("MAXIMUM", fm("SUBTRACT", g, s), 0.0)
    w = N.new("ShaderNodeMapRange")
    w.clamp = True
    L.new(move, w.inputs["Value"])
    w.inputs["From Min"].default_value, w.inputs["From Max"].default_value = fa, fb
    w.inputs["To Min"].default_value, w.inputs["To Max"].default_value = 1.0, 0.0
    move = fm("MULTIPLY", move, w.outputs["Result"])
    move = switch("FLOAT", active, 0.0, move)
    u = N.new("GeometryNodeSwitch")
    u.input_type = "VECTOR"
    L.new(use_n, u.inputs["Switch"])
    L.new(d, u.inputs["False"])
    L.new(un, u.inputs["True"])
    tgt = vm("ADD", pw, vm("SCALE", u.outputs[0], scale=move).outputs[0]).outputs[0]
    inv = N.new("FunctionNodeInvertMatrix")
    L.new(gi.outputs["Self"], inv.inputs[0])
    tl = to_world(tgt, inv.outputs[0])
    off = vm("SUBTRACT", tl, pos.outputs[0]).outputs[0]
    # store the offset (one evaluation of the rays), optionally feather it, then move
    st = N.new("GeometryNodeStoreNamedAttribute")
    st.data_type, st.domain = "FLOAT_VECTOR", "POINT"
    st.inputs["Name"].default_value = f"{PREFIX}.offset"
    L.new(gi.outputs["Geometry"], st.inputs["Geometry"])
    L.new(off, st.inputs["Value"])
    na = N.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT_VECTOR"
    na.inputs["Name"].default_value = f"{PREFIX}.offset"
    final = na.outputs["Attribute"]
    it = int(spec["smooth_iterations"])
    if it > 0:
        bl = N.new("GeometryNodeBlurAttribute")
        bl.data_type = "FLOAT_VECTOR"
        L.new(na.outputs["Attribute"], bl.inputs["Value"])
        bl.inputs["Iterations"].default_value = it
        longer = cmp("GREATER_THAN", vm("LENGTH", bl.outputs["Value"]).outputs["Value"],
                     vm("LENGTH", na.outputs["Attribute"]).outputs["Value"])
        sw = N.new("GeometryNodeSwitch")
        sw.input_type = "VECTOR"
        L.new(longer, sw.inputs["Switch"])
        L.new(na.outputs["Attribute"], sw.inputs["False"])
        L.new(bl.outputs["Value"], sw.inputs["True"])
        final = sw.outputs[0]
    sp = N.new("GeometryNodeSetPosition")
    L.new(st.outputs[0], sp.inputs["Geometry"])
    L.new(final, sp.inputs["Offset"])
    rm = N.new("GeometryNodeRemoveAttribute")
    L.new(sp.outputs[0], rm.inputs["Geometry"])
    rm.inputs["Name"].default_value = f"{PREFIX}.offset"
    L.new(rm.outputs[0], go.inputs[0])
    return ng


def _bind_group(push, base, tip, solid_set, name, passes=1, max_step=0.0):
    """Per garment object: wires its two proxies, the solid set and the transforms into the shared push group."""
    import bpy
    ng = bpy.data.node_groups.new(f"{PREFIX}.{name}", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")

    def info(obj):
        n_ = N.new("GeometryNodeObjectInfo")
        n_.transform_space = "ORIGINAL"
        if obj is None:
            L.new(N.new("GeometryNodeSelfObject").outputs[0], n_.inputs["Object"])
        else:
            n_.inputs["Object"].default_value = obj
        return n_
    me, ob, ot, os_ = info(None), info(base), info(tip), info(solid_set)
    prev = gi.outputs[0]
    for _p in range(max(1, passes)):  # a vertex pushed out of one part into an overlapping one leaves it next pass
        g = N.new("GeometryNodeGroup")
        g.node_tree = push
        L.new(prev, g.inputs["Geometry"])
        L.new(ob.outputs["Geometry"], g.inputs["Base"])
        L.new(ot.outputs["Geometry"], g.inputs["Tip"])
        L.new(os_.outputs["Geometry"], g.inputs["Solids"])
        L.new(me.outputs["Transform"], g.inputs["Self"])
        L.new(ob.outputs["Transform"], g.inputs["Proxy Space"])
        prev = g.outputs[0]
    L.new(_rate_limit(ng, gi.outputs[0], prev, max_step) if max_step > 0 else prev, go.inputs[0])
    return ng


def _rate_limit(ng, g0, g1, step):
    """Per-vertex rate limit on the push (spec `max_step_m`): offset(f) = offset(f-1) + (raw(f) - offset(f-1))
    clamped to `step` in length, raw = g1 - g0 (same topology). The state is a simulation zone holding only the
    vertices with a non-zero offset, as points at (vertex index, 0, 0) with the attribute `off`, so the baked cache
    stays small. A frame-to-frame change of the push is never larger than `step`: no pop from a push that switches
    on or off, or turns, between two frames."""
    N, L = ng.nodes, ng.links
    pos, idx = N.new("GeometryNodeInputPosition"), N.new("GeometryNodeInputIndex")

    def node(kind, **props):
        n_ = N.new(kind)
        for k, v in props.items():
            setattr(n_, k, v)
        return n_

    def vm(op, a, b=None):
        n_ = node("ShaderNodeVectorMath", operation=op)
        L.new(a, n_.inputs[0])
        if b is not None:
            L.new(b, n_.inputs[1])
        return n_.outputs["Vector"] if op not in ("LENGTH", "DOT_PRODUCT") else n_.outputs["Value"]

    def sample(geo, value, index, dtype):
        n_ = node("GeometryNodeSampleIndex", data_type=dtype, domain="POINT")
        L.new(geo, n_.inputs["Geometry"])
        L.new(value, n_.inputs["Value"])
        L.new(index, n_.inputs["Index"])
        return n_.outputs[0]

    key = node("ShaderNodeCombineXYZ")
    L.new(idx.outputs[0], key.inputs["X"])
    off_attr = node("GeometryNodeInputNamedAttribute", data_type="FLOAT_VECTOR")
    off_attr.inputs["Name"].default_value = "off"

    def lookup(cloud):
        """The `off` of this vertex in a state cloud (zero when it has no point)."""
        ni = node("GeometryNodeSampleNearest")
        L.new(cloud, ni.inputs["Geometry"])
        L.new(key.outputs[0], ni.inputs["Sample Position"])
        sp = node("ShaderNodeSeparateXYZ")
        L.new(sample(cloud, pos.outputs[0], ni.outputs[0], "FLOAT_VECTOR"), sp.inputs[0])
        dx = node("ShaderNodeMath", operation="SUBTRACT")
        L.new(sp.outputs["X"], dx.inputs[0])
        L.new(idx.outputs[0], dx.inputs[1])
        ab = node("ShaderNodeMath", operation="ABSOLUTE")
        L.new(dx.outputs[0], ab.inputs[0])
        ok = node("FunctionNodeCompare", data_type="FLOAT", operation="LESS_THAN")
        L.new(ab.outputs[0], ok.inputs[0])
        ok.inputs[1].default_value = 0.5
        sw = node("GeometryNodeSwitch", input_type="VECTOR")
        L.new(ok.outputs[0], sw.inputs["Switch"])
        L.new(sample(cloud, off_attr.outputs["Attribute"], ni.outputs[0], "FLOAT_VECTOR"), sw.inputs["True"])
        return sw.outputs[0]

    raw = vm("SUBTRACT", sample(g1, pos.outputs[0], idx.outputs[0], "FLOAT_VECTOR"), pos.outputs[0])
    si, so = N.new("GeometryNodeSimulationInput"), N.new("GeometryNodeSimulationOutput")
    si.pair_with_output(so)
    prev = lookup(si.outputs["Geometry"])
    diff = vm("SUBTRACT", raw, prev)
    ln = vm("LENGTH", diff)
    mx_ = node("ShaderNodeMath", operation="MAXIMUM")
    L.new(ln, mx_.inputs[0])
    mx_.inputs[1].default_value = 1e-9
    q = node("ShaderNodeMath", operation="DIVIDE")
    q.inputs[0].default_value = step
    L.new(mx_.outputs[0], q.inputs[1])
    mn = node("ShaderNodeMath", operation="MINIMUM")
    L.new(q.outputs[0], mn.inputs[0])
    mn.inputs[1].default_value = 1.0
    sc = node("ShaderNodeVectorMath", operation="SCALE")
    L.new(diff, sc.inputs[0])
    L.new(mn.outputs[0], sc.inputs["Scale"])
    new = vm("ADD", prev, sc.outputs[0])
    st = node("GeometryNodeStoreNamedAttribute", data_type="FLOAT_VECTOR", domain="POINT")
    st.inputs["Name"].default_value = "off"
    L.new(g0, st.inputs["Geometry"])
    L.new(new, st.inputs["Value"])
    nz = node("FunctionNodeCompare", data_type="FLOAT", operation="GREATER_THAN")
    L.new(vm("LENGTH", off_attr.outputs["Attribute"]), nz.inputs[0])
    nz.inputs[1].default_value = 1e-7
    mp = N.new("GeometryNodeMeshToPoints")
    L.new(st.outputs[0], mp.inputs["Mesh"])
    L.new(nz.outputs[0], mp.inputs["Selection"])
    L.new(key.outputs[0], mp.inputs["Position"])
    L.new(mp.outputs[0], so.inputs["Geometry"])
    spos = N.new("GeometryNodeSetPosition")
    L.new(g0, spos.inputs["Geometry"])
    L.new(lookup(so.outputs["Geometry"]), spos.inputs["Offset"])
    return spos.outputs[0]
