"""Render-time hair push-out (T-194): keeps hair out of the real evaluated meshes of the shot (the character's own
body, ears, hands and garments, the other characters, props and the bake's box objects) after the engine's chain
solver has moved it. Opt-in (`shot_render.py --hair-pushout`); without it nothing here runs.

Two stages, both stateless per frame (the result at frame f depends only on the evaluated meshes at f):

A. Chain joints (Python, called per frame by shot_render after every bone is keyed). Every `DYN-*` chain listed in
   the rig's `ps_dynamics` is walked from its root, in a fixed order. Segment k is tested with a RAY from joint k-1
   (already outside) to joint k: any face it crosses counts, so open garment shells, inside-out trims and deep cases
   are caught (a nearest-point + normal test pushes those to the wrong side). On a hit the joint keeps its segment
   length and slides over the hit plane with `core_radius_m + margin_m` clearance, then the segment is tested again
   (MAX_TRIES); the fallback is straight away from the surface, then the free direction nearest to the baked one among 128 fixed
   ones; segment lengths are always kept (the re-key only rotates bones), a joint with no free direction is
   reported as "blocked". A joint that is enclosed (fewer than two of 26 fixed directions get
   out of the colliders: it slipped in through an opening without crossing a face) is moved out along its shortest
   way through a wall, keeping the segment length. The leading segments of a chain that already cross the character's
   own head at rest (the root sits in the scalp; only head-dominant skin triangles count, not the ears (keep-out) and
   not cloth, so hair modelled into an ear or cloth at rest is pushed out) are tested only beyond that rest crossing. Changed bones are
   re-keyed; a chain whose segments cross nothing is left exactly as baked.

B. Every hair vertex (a Geometry Nodes modifier on each hair object, evaluated by Blender, no Python at render
   time). Each hair object gets a hidden anchor proxy: a local copy of its mesh whose vertices sit at a point that is
   outside at rest, deformed by the same armature: a chain vertex's anchor is its nearest point on its chain's centre
   line (weighted 1.0 to that chain bone, so it lies exactly on the deformed chain, which stage A keeps free); a
   static vertex's (no chain weight: cap, curtain, temples, masses) is `static_reach_m` outwards from the head
   centre, with the vertex's own weights. An anchor whose ray to its vertex crosses the own head at rest (head-dominant
   triangles) is moved past the last such crossing (roots embedded in the scalp stay as modelled). The modifier casts a ray from the
   anchor to the vertex against all colliders and puts a vertex whose ray is blocked at `vertex_margin_m` before the
   hit. A second ray from that point towards the anchor catches a vertex whose anchor got inside something at this
   frame (a neighbour's head deeper in the hair than the reach): against the CLOSED colliders only (unmasked skins,
   props, boxes; open shells give false answers), when it and the opposite ray both first meet a BACK face, the
   vertex is inside that solid and leaves through the face towards its anchor. Vertices
   embedded in the head at rest (roots, the scalp side of the cap; flag `ps_exit` = 0 on the proxy) are never moved.
   A static vertex (flag `ps_static`) whose anchor ray first meets a BACK face has its anchor inside that collider at
   this frame (spec `static_inside` "keep", the default): it is left as baked, not snapped next to its anchor; so is a
   static vertex that is not behind a surface (its own ray towards the anchor first meets a front face or nothing:
   the anchor ray only went through a thin part such as the hood rim tube).
   Vertices whose rays find nothing are not touched.

Colliders: every mesh child of a rendered character's rig with an Armature modifier except hair (`hair_*`),
`WGT-*`, the cloth-simulation proxies `garment.collider.*` other than the unmasked skin `garment.collider.body_skin`
(the rendered `body_skin` is masked away under the garments, so the torso would be hollow and a lock that slips in
at a neck opening would cross no face), and the face parts in SKIP (the T-183 measures' list, glasses included); the props of
the shot (an open-top vessel gets a closing cap disc so hair cannot drop in through its opening) and the bake's box
objects. Hair is not a collider (hair against hair is out of scope, T-194)."""
import fnmatch
import json
import math

import numpy as np

SKIP = ["eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
DEFAULTS = {"margin_m": 0.002, "core_radius_m": 0.012, "vertex_margin_m": 0.0015, "static_reach_m": 0.03,
            "characters": "all", "stages": ["chains", "vertices"], "enclosure": True, "exit_test": False,
            "lock_volume": False, "static_inside": "keep"}
# exit_test / lock_volume: off by default, both make visible frame-to-frame pops (README, e912 s020 f105-111)
# static_inside "keep": a static vertex whose anchor is inside a collider at this frame (its anchor ray first meets a
# BACK face), or that is not behind a surface itself (its ray to the anchor first meets a FRONT face), is left as baked; "clamp" = the old rule (snapped next to its anchor: the boy's cap into his hood rim and
# ~30 mm pops, e912 s020, session 3)
MAX_TRIES = 3
EPS = 1e-5
CHAIN_MIN_WEIGHT = 0.05  # a vertex with less than this summed DYN weight is static
PREFIX = "ps_pushout"
EXIT_REACH = 0.03  # m: how far the second ray looks for the face a vertex is inside (a farther exit is a
# visible one-vertex spike: s020 f107, 109 mm through the neck with 0.1)


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
    if spec["static_inside"] not in ("keep", "clamp"):
        raise ValueError(f"hair push-out: static_inside must be keep / clamp, got {spec['static_inside']}")
    return spec


# ---------------------------------------------------------------------------------------------------- geometry ----

def is_hair(o):
    return o.name.startswith("hair_")


def is_figure(o, rig):
    if o.type != "MESH" or is_hair(o) or o.name.startswith("WGT-"):
        return False
    if o.name.startswith("garment.collider"):  # only the unmasked skin (the masked body_skin is hollow under cloth)
        return o.name.startswith("garment.collider.body_skin")
    if any(fnmatch.fnmatchcase(o.name, p) for p in SKIP):
        return False
    return any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)


def world_triangles(objs, deps, head_bone=None):
    """(V (n, 3) float64, T (m, 3) int) of the evaluated objects in world space, in the given order. With head_bone:
    only the triangles whose three vertices are head-dominant (weight >= 0.5 to that bone: scalp, face)."""
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
            tri = tri.reshape(-1, 3)
            if head_bone is not None:
                gi = e.vertex_groups.get(head_bone)
                keep = np.zeros(n, dtype=bool)
                if gi is not None:
                    for v in me.vertices:
                        for g in v.groups:
                            if g.group == gi.index and g.weight >= 0.5:
                                keep[v.index] = True
                tri = tri[keep[tri].all(axis=1)]
                if len(tri) == 0:
                    continue
            Vs.append(co)
            Ts.append(tri + off)
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


DIRS = [np.array(d, dtype=np.float64) / np.linalg.norm(d) for d in
        [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]]
CAP = 0.6  # m: a ray that meets nothing within this distance has left the figure
_GA = math.pi * (3.0 - math.sqrt(5.0))
FAN = [np.array((math.cos(_GA * i) * math.sqrt(1 - (1 - 2 * (i + 0.5) / 128) ** 2), 1 - 2 * (i + 0.5) / 128,
                 math.sin(_GA * i) * math.sqrt(1 - (1 - 2 * (i + 0.5) / 128) ** 2))) for i in range(128)]  # Fibonacci


def enclosed(tree, p):
    """True when fewer than two of the 26 fixed directions leave the figure from p (the T-183 measure's rule: a
    point that got in through an opening, e.g. a lock down the neck opening of a blouse over a masked skin, is inside
    although no segment crossed a face)."""
    from mathutils import Vector
    if tree is None:
        return False
    free = 0
    for d in DIRS:
        if tree.ray_cast(Vector(p + d * EPS), Vector(d), CAP)[0] is None:
            free += 1
            if free >= 2:
                return False
    return True


def shortest_wall_exit(tree, p):
    """(direction, distance) of the shortest of the 26 fixed directions out of the figure through a wall (directions
    that meet nothing are openings, not ways out)."""
    best = (None, CAP)
    for d in DIRS:
        e = last_crossing(tree, p, d, CAP)
        if 0 < e < best[1]:
            best = (d, e)
    return best


def _place(tree, o, d, L, a, clearance, h, info):
    """Segment from o (outside) of length L whose ray along d is blocked (hit h): slide over the hit plane with
    `clearance`, then straight away from the surface, then the nearest free direction of FAN (_fan)."""
    d0 = d
    for _ in range(MAX_TRIES):
        t, hp, n = h
        s_o = float((o - hp).dot(n))
        tang = d - d.dot(n) * n
        tang = _unit(tang) if _unit(tang) is not None else _perp(n)
        c = min(1.0, max(-1.0, (clearance - s_o) / L))
        u = c * n + math.sqrt(max(0.0, 1.0 - c * c)) * tang
        h2 = ray_hit(tree, o + u * a, u, L - a) if a < L else None
        if h2 is None:
            return o + u * L
        d, h = u, h2
    n = h[2]
    h2 = ray_hit(tree, o + n * a, n, L - a) if a < L else None
    if h2 is None:
        return o + n * L
    return _fan(tree, o, d0, L, a, info)


def _fan(tree, o, d0, L, a, info):
    """Last resort: the free full-length direction (segment crosses nothing, end not enclosed) nearest to the baked
    direction d0, among FAN. The segment length is always kept: the re-key only rotates bones, so a shortened
    segment would come out at full length along the same direction, back inside. None free: the direction whose
    first hit is farthest (reported as "blocked")."""
    order = sorted(range(len(FAN)), key=lambda i: (-round(float(FAN[i].dot(d0)), 9), i))
    best, best_t = None, -1.0
    for i in order:
        u = FAN[i]
        hh = ray_hit(tree, o + u * a, u, L - a) if a < L else None
        if hh is None:
            if not enclosed(tree, o + u * L):
                return o + u * L
            continue
        if hh[0] > best_t:
            best, best_t = u, hh[0]
    info["blocked"] += 1
    return o + (best if best is not None else d0) * L


def volume_enclosed(tree, o, q, r):
    """The first enclosed sample of the lock around segment o-q (radius r: 4 points around its middle and its end),
    or None. The centre line can be outside while the lock's flesh sits in a pocket under an open shell (a vest over a
    blouse) that no ray from the centre line crosses."""
    t = _unit(q - o)
    if t is None or r <= 0:
        return None
    e1 = _perp(t)
    e2 = np.cross(t, e1)
    for frac in (0.5, 1.0):
        c = o + (q - o) * frac
        for e in (e1, -e1, e2, -e2):
            if enclosed(tree, c + e * r):
                return c + e * r
    return None


def push_chain(tree, J, allow, clearance, rest_enclosed=None, enclosure=True, radius=None, rest_volume=None):
    """Stage A on one chain. J: (n+1, 3) baked joints (world), allow: per segment, the rest crossing distance from
    its start that is not tested (0 for a free segment); rest_enclosed: per joint, True where the joint is already
    enclosed at rest (not pushed for it); radius: per segment, the lock radius at rest (volume_enclosed; rest_volume:
    per joint, True where the lock is already enclosed there at rest). Returns (P, info): pushed joints (P[k] is J[k] bit for bit where nothing
    upstream changed, segment k crosses nothing and joint k is not enclosed) and {"moved": first changed joint or
    None, "hits": n, "enclosed": n, "enclosed_left": n, "blocked": n, "max_move_m": x}."""
    J = np.asarray(J, dtype=np.float64)
    P = J.copy()
    info = {"moved": None, "hits": 0, "enclosed": 0, "enclosed_left": 0, "blocked": 0, "volume": 0, "volume_left": 0,
            "max_move_m": 0.0}
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
        changed = info["moved"] is not None
        if h is None:
            q = o + d * L if changed else J[k]  # upstream changed: follow the leader towards the baked joint
        else:
            info["hits"] += 1
            q = _place(tree, o, d, L, a, clearance, h, info)
            changed = True
        if enclosure and (rest_enclosed is None or not rest_enclosed[k]) and enclosed(tree, q):
            info["enclosed"] += 1
            for _ in range(MAX_TRIES):
                ed, e = shortest_wall_exit(tree, q)
                if ed is None:
                    break
                u = _unit(q + ed * (e + clearance) - o)
                if u is None:
                    break
                h = ray_hit(tree, o + u * a, u, L - a) if a < L else None
                q = o + u * L if h is None else _place(tree, o, u, L, a, clearance, h, info)
                changed = True
                if not enclosed(tree, q):
                    break
            else:
                info["enclosed_left"] += 1
        r = float(radius[k - 1]) if radius is not None and k - 1 < len(radius) else 0.0
        if r > 0 and not (rest_volume is not None and rest_volume[k]):
            smp = volume_enclosed(tree, o, q, r)
            if smp is not None:
                info["volume"] += 1
                for _ in range(MAX_TRIES):
                    ed, e = shortest_wall_exit(tree, smp)
                    u = _unit(q + ed * (e + clearance) - o) if ed is not None else None
                    if u is None:
                        break
                    h = ray_hit(tree, o + u * a, u, L - a) if a < L else None
                    q = o + u * L if h is None else _place(tree, o, u, L, a, clearance, h, info)
                    changed = True
                    smp = volume_enclosed(tree, o, q, r)
                    if smp is None:
                        break
                if smp is not None:
                    info["volume_left"] += 1
        P[k] = q
        if changed and info["moved"] is None:
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


def static_anchor(tree, htree, v, centre, reach):
    """Rest anchor of a static hair vertex v (no chain weight) and its kind:
    "static_outside": v is in front of its nearest rest surface: reach outwards from that surface (shortened before
        the next surface on the way);
    "static_in_cloth": v is behind a surface that is not the head and enclosed (hair modelled into cloth or the neck
        at rest): the anchor is outside that surface, so the clamp takes v out of it;
    "static_in_head": v is embedded in the head (scalp side of the cap, roots): anchor = v, never moved;
    "static_free": nothing within reach: radially out from the head centre."""
    from mathutils import Vector
    hit = tree.find_nearest(Vector(v), 0.1) if tree is not None else (None,) * 4
    if hit[0] is None:
        r = _unit(v - centre) if centre is not None else None
        if r is None:
            return v, "static_free"
        h = ray_hit(tree, v + r * EPS, r, reach)
        return v + r * (reach if h is None else max(0.0, h[0] - 0.001)), "static_free"
    co, n, dist = np.array(hit[0]), np.array(hit[1]), hit[3]
    if (v - co).dot(n) >= 0 or not enclosed(tree, v):  # in front of it, or behind an open / inside-out face only
        u = _unit(v - co) if dist > 1e-6 else n
        h = ray_hit(tree, v + u * EPS, u, reach)
        return v + u * (reach if h is None else max(0.0, h[0] - 0.001)), "static_outside"
    if htree is not None:
        hh = htree.find_nearest(Vector(v), dist + 1e-4)
        if hh[0] is not None and (v - np.array(hh[0])).dot(np.array(hh[1])) < 0:
            return v, "static_in_head"
    u = n
    h = ray_hit(tree, co + u * 0.0005, u, reach)
    return co + u * (reach if h is None else max(0.0005, h[0] - 0.001)), "static_in_cloth"


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
        # closed solids only (the unmasked skins, props with their caps, boxes): the inside test of stage B's second
        # ray must not see open shells (masked skin borders, inside-out trims), where a ray through a hole meets a
        # back face from outside
        self.closed = [o for n in sorted(self.figures) for o in self.figures[n]
                       if o.name.startswith("garment.collider.body_skin")]
        self.closed += [props[n] for n in sorted(props)] + self.caps + list(boxes)
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
            # rest crossings are allowed only through the head (roots in the scalp, temples behind the ears): hair
            # modelled into cloth at rest is pushed out like any other
            skin = [o for o in self.figures[n] if not o.name.startswith(("ear.", "garment."))]  # ears: keep-out
            htree = bvh_of(*world_triangles(skin, deps, st.get("head_bone"))) if st.get("head_bone") else None
            self.rest_trees[n] = (tree, htree)
            dyn = rig.get("ps_dynamics")
            dyn = json.loads(dyn) if isinstance(dyn, str) else (dyn.to_dict() if hasattr(dyn, "to_dict") else dyn)
            W = np.array(rig.matrix_world)
            chains = []
            htree = self.rest_trees[n][1]
            for ch in (dyn or {}).get("chains", []):
                bones = [b for b in ch["bones"] if b in rig.pose.bones]
                if len(bones) != len(ch["bones"]) or not bones:
                    continue
                db = rig.data.bones
                J = [db[bones[0]].head_local] + [db[b].tail_local for b in bones]
                J = np.array([W[:3, :3] @ np.array(j) + W[:3, 3] for j in J])
                chains.append({"name": ch["name"], "bones": bones, "rest": J, "allow": rest_allowance(htree, J),
                               "rest_enclosed": [bool(enclosed(htree, j)) for j in J]})
            self.chains[n] = chains
            self.report["characters"][n] = {"chains": len(chains), "allowed_root_segments":
                                            sum(1 for c in chains for a in c["allow"] if a > 0)}
        if "vertices" in self.spec["stages"]:
            for n in self.names:
                self._anchors(n)
                tree = self.rest_trees[n][0]
                for c in self.chains[n]:  # lock radius per segment (90th percentile of its vertices' distance to the
                    acc = c.pop("_dist", {})  # centre line) and where the lock is already enclosed at rest
                    c["radius"] = [float(np.percentile(np.concatenate(acc[k]), 90)) if k in acc else 0.0
                                   for k in range(len(c["bones"]))]
                    c["rest_volume"] = [False] + [volume_enclosed(tree, c["rest"][k - 1], c["rest"][k],
                                                                  c["radius"][k - 1]) is not None
                                                  for k in range(1, len(c["rest"]))]
                self.report["characters"][n]["lock_radius_mm"] = round(1e3 * float(np.median(
                    [r for c in self.chains[n] for r in c["radius"] if r > 0] or [0.0])), 1)
                self.report["characters"][n]["lock_enclosed_at_rest"] = sum(
                    sum(c["rest_volume"]) for c in self.chains[n])
        for n in self.names:
            for _i, pb in self.states[n]["bones"]:
                pb.location, pb.rotation_quaternion, pb.scale = saved[(n, pb.name)]
        bpy.context.view_layer.update()

    def _anchors(self, n):
        """Anchor proxies (stage B) for every hair object of character n."""
        bpy = self.bpy
        st = self.states[n]
        rig = st["rig"]
        tree, htree = self.rest_trees[n]
        chain_of = {}
        for ci, c in enumerate(self.chains[n]):
            for k, b in enumerate(c["bones"]):
                chain_of[b] = (ci, k)
        head = st.get("head_bone")
        W = np.array(rig.matrix_world)
        hb = rig.data.bones.get(head) if head else None
        centre = (W[:3, :3] @ ((np.array(hb.head_local) + np.array(hb.tail_local)) / 2) + W[:3, 3]) if hb else None
        reach = float(self.spec["static_reach_m"])
        rep = {"objects": 0, "vertices": 0, "chain_anchors": 0, "static_anchors": 0, "anchors_moved_past_rest": 0}
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
                dd = np.linalg.norm(P[idx] - A[idx], axis=1)
                acc = c.setdefault("_dist", {})
                for k in np.unique(seg):
                    acc.setdefault(int(k), []).append(dd[seg == k])
            stat = np.nonzero(~is_chain)[0]
            embedded = np.zeros(nv, dtype=bool)  # in the head at rest: never moved (roots, scalp side of the cap)
            for i in stat:
                A[i], kind = static_anchor(tree, htree, P[i], centre, reach)
                rep[kind] = rep.get(kind, 0) + 1
                embedded[i] = kind == "static_in_head"
            if htree is not None:
                from mathutils import Vector
                for i in np.nonzero(~embedded)[0]:
                    hh = htree.find_nearest(Vector(P[i]), 0.05)
                    if hh[0] is not None and (P[i] - np.array(hh[0])).dot(np.array(hh[1])) < 0:
                        embedded[i] = True
            # an anchor whose ray to its vertex crosses the own figure at rest: past the last crossing
            for i in range(nv):
                d = P[i] - A[i]
                L = float(np.linalg.norm(d))
                if L < 1e-6:
                    continue
                d = d / L
                e = last_crossing(htree, A[i], d, L) if htree is not None else 0.0
                if e > 0:
                    A[i] = A[i] + d * min(L, e + 0.0005)
                    rigid[i] = -1
                    embedded[i] = True
                    rep["anchors_moved_past_rest"] += 1
            pm = me.copy()
            pm.name = f"{PREFIX}.anchor.{o.name}"
            Ai = np.linalg.inv(Mo)
            loc = A @ Ai[:3, :3].T + Ai[:3, 3]
            pm.vertices.foreach_set("co", loc.ravel())
            ex = pm.attributes.get("ps_exit") or pm.attributes.new("ps_exit", "FLOAT", "POINT")
            ex.data.foreach_set("value", (~embedded).astype(np.float32))
            sa = pm.attributes.get("ps_static") or pm.attributes.new("ps_static", "FLOAT", "POINT")
            sa.data.foreach_set("value", (rigid < 0).astype(np.float32))  # anchor follows the vertex's own weights
            pm.update()
            rep["embedded_at_rest"] = rep.get("embedded_at_rest", 0) + int(embedded.sum())
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
            out = {"chains_pushed": 0, "joints_moved": 0, "hits": 0, "enclosed": 0, "enclosed_left": 0, "blocked": 0,
                   "volume": 0, "volume_left": 0, "max_move_mm": 0.0}
            for c in self.chains[n]:
                pbs = [rig.pose.bones[b] for b in c["bones"]]
                J = [pbs[0].head] + [pb.tail for pb in pbs]
                J = np.array([W[:3, :3] @ np.array(j) + W[:3, 3] for j in J])
                vol = bool(self.spec["lock_volume"])
                P, info = push_chain(tree, J, c["allow"], clearance, c["rest_enclosed"], bool(self.spec["enclosure"]),
                                     c.get("radius") if vol else None, c.get("rest_volume"))
                for key in ("hits", "enclosed", "enclosed_left", "blocked", "volume", "volume_left"):
                    out[key] += info[key]
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
        ccol = bpy.data.collections.new(f"{PREFIX}.closed")
        for o in self.closed:
            ccol.objects.link(o)
        sets = []
        for name, c in (("collider_set", col), ("closed_set", ccol)):
            cs = bpy.data.objects.new(f"{PREFIX}.{name}", bpy.data.meshes.new(f"{PREFIX}.{name}"))
            self.scene.collection.objects.link(cs)
            cs.hide_render = True
            mg = cs.modifiers.new("collect", "NODES")
            mg.node_group = _collector_group(c)
            sets.append(cs)
        group = _clamp_group(float(self.spec["vertex_margin_m"]), bool(self.spec["exit_test"]),
                             self.spec["static_inside"] == "keep")
        for n in self.names:
            oc = bpy.data.collections.new(f"{PREFIX}.others.{n}")
            for m_ in sorted(self.figures):
                if m_ != n:
                    for o in self.figures[m_]:
                        if o.name.startswith("garment.collider.body_skin"):
                            oc.objects.link(o)
            os_ = bpy.data.objects.new(f"{PREFIX}.others_set.{n}", bpy.data.meshes.new(f"{PREFIX}.others_set.{n}"))
            self.scene.collection.objects.link(os_)
            os_.hide_render = True
            os_.modifiers.new("collect", "NODES").node_group = _collector_group(oc)
            for o, px in self.states[n].get("proxies", []):
                m = o.modifiers.new(f"{PREFIX}", "NODES")
                m.node_group = _bind_group(group, px, sets[0], sets[1], o.name, os_)
        self.report["vertex_stage_installed"] = True


def _collector_group(col):
    import bpy
    ng = bpy.data.node_groups.new(f"{PREFIX}.collect.{col.name}", "GeometryNodeTree")
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


def _clamp_group(margin, exit_test=True, static_keep=True):
    """Shared clamp: inputs Geometry, Anchors (geometry, world), Colliders (geometry, world), Self (matrix)."""
    import bpy
    ng = bpy.data.node_groups.new(f"{PREFIX}.clamp", "GeometryNodeTree")
    I = ng.interface
    I.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Anchors", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Colliders", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Closed", in_out="INPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Others", in_out="INPUT", socket_type="NodeSocketGeometry")
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
    L.new(inv.outputs[0], tl.inputs["Transform"])
    # second ray: from the (clamped) vertex towards its anchor; a first hit on a BACK face means the vertex is inside
    # that solid (its anchor got inside something at this frame): it leaves through that face, `margin` beyond
    # anchor inside another character (the first hit of its ray on the other characters' unmasked skins is a back
    # face: a neighbour's head over the hair's anchor): squeezed, not clamped (clamping would only move the vertex next
    # to its anchor, still inside)
    rc4 = N.new("GeometryNodeRaycast")
    L.new(gi.outputs["Others"], rc4.inputs["Target Geometry"])
    L.new(ta.outputs[0], rc4.inputs["Source Position"])
    L.new(nd.outputs[0], rc4.inputs["Ray Direction"])
    L.new(ln.outputs["Value"], rc4.inputs["Ray Length"])
    dot4 = N.new("ShaderNodeVectorMath")
    dot4.operation = "DOT_PRODUCT"
    L.new(rc4.outputs["Hit Normal"], dot4.inputs[0])
    L.new(nd.outputs[0], dot4.inputs[1])
    back4 = N.new("FunctionNodeCompare")
    back4.data_type, back4.operation = "FLOAT", "GREATER_THAN"
    L.new(dot4.outputs["Value"], back4.inputs[0])
    back4.inputs[1].default_value = 0.0
    sq = N.new("FunctionNodeBooleanMath")
    sq.operation = "AND"
    L.new(rc4.outputs["Is Hit"], sq.inputs[0])
    L.new(back4.outputs[0], sq.inputs[1])
    if static_keep:
        # a static vertex (anchor on the vertex's own weights, not on a chain centre line that stage A keeps free)
        # whose anchor ray first meets a BACK face: the anchor is inside that collider at this frame (the boy's cap
        # anchors inside his hood rim when the head turns); clamping would snap the vertex next to its anchor, into
        # the collider: left as baked
        dot0 = N.new("ShaderNodeVectorMath")
        dot0.operation = "DOT_PRODUCT"
        L.new(rc.outputs["Hit Normal"], dot0.inputs[0])
        L.new(nd.outputs[0], dot0.inputs[1])
        back0 = N.new("FunctionNodeCompare")
        back0.data_type, back0.operation = "FLOAT", "GREATER_THAN"
        L.new(dot0.outputs["Value"], back0.inputs[0])
        back0.inputs[1].default_value = 0.0
        nst = N.new("GeometryNodeInputNamedAttribute")
        nst.data_type = "FLOAT"
        nst.inputs["Name"].default_value = "ps_static"
        sst = N.new("GeometryNodeSampleIndex")
        sst.data_type, sst.domain = "FLOAT", "POINT"
        L.new(gi.outputs["Anchors"], sst.inputs["Geometry"])
        L.new(nst.outputs["Attribute"], sst.inputs["Value"])
        L.new(idx.outputs[0], sst.inputs["Index"])
        ist = N.new("FunctionNodeCompare")
        ist.data_type, ist.operation = "FLOAT", "GREATER_THAN"
        L.new(sst.outputs[0], ist.inputs[0])
        ist.inputs[1].default_value = 0.5
        sin = N.new("FunctionNodeBooleanMath")
        sin.operation = "AND"
        L.new(back0.outputs[0], sin.inputs[0])
        L.new(ist.outputs[0], sin.inputs[1])
        # ... and a static vertex that is not behind a surface (its own ray towards the anchor first meets a FRONT
        # face, or nothing): it is outside, the anchor ray only went through a thin part (hood rim tube, s020 f53
        # auburn curtain): left as baked
        neg = N.new("ShaderNodeVectorMath")
        neg.operation = "SCALE"
        L.new(nd.outputs[0], neg.inputs[0])
        neg.inputs["Scale"].default_value = -1.0
        st5 = N.new("ShaderNodeVectorMath")
        st5.operation = "MULTIPLY_ADD"
        L.new(neg.outputs[0], st5.inputs[0])
        st5.inputs[1].default_value = (1e-4, 1e-4, 1e-4)
        L.new(tw.outputs[0], st5.inputs[2])
        rc5 = N.new("GeometryNodeRaycast")
        L.new(gi.outputs["Colliders"], rc5.inputs["Target Geometry"])
        L.new(st5.outputs[0], rc5.inputs["Source Position"])
        L.new(neg.outputs[0], rc5.inputs["Ray Direction"])
        L.new(ln.outputs["Value"], rc5.inputs["Ray Length"])
        dot5 = N.new("ShaderNodeVectorMath")
        dot5.operation = "DOT_PRODUCT"
        L.new(rc5.outputs["Hit Normal"], dot5.inputs[0])
        L.new(neg.outputs[0], dot5.inputs[1])
        back5 = N.new("FunctionNodeCompare")
        back5.data_type, back5.operation = "FLOAT", "GREATER_THAN"
        L.new(dot5.outputs["Value"], back5.inputs[0])
        back5.inputs[1].default_value = 0.0
        behind = N.new("FunctionNodeBooleanMath")
        behind.operation = "AND"
        L.new(rc5.outputs["Is Hit"], behind.inputs[0])
        L.new(back5.outputs[0], behind.inputs[1])
        outside = N.new("FunctionNodeBooleanMath")
        outside.operation = "NIMPLY"  # static and not behind
        L.new(ist.outputs[0], outside.inputs[0])
        L.new(behind.outputs[0], outside.inputs[1])
        sin2 = N.new("FunctionNodeBooleanMath")
        sin2.operation = "OR"
        L.new(sin.outputs[0], sin2.inputs[0])
        L.new(outside.outputs[0], sin2.inputs[1])
        sq2 = N.new("FunctionNodeBooleanMath")
        sq2.operation = "OR"
        L.new(sq.outputs[0], sq2.inputs[0])
        L.new(sin2.outputs[0], sq2.inputs[1])
        sq = sq2
    clamp = N.new("FunctionNodeBooleanMath")
    clamp.operation = "NIMPLY"  # hit and not squeezed
    L.new(rc.outputs["Is Hit"], clamp.inputs[0])
    L.new(sq.outputs[0], clamp.inputs[1])
    sw1 = N.new("GeometryNodeSwitch")
    sw1.input_type = "VECTOR"
    L.new(clamp.outputs[0], sw1.inputs["Switch"])
    L.new(tw.outputs[0], sw1.inputs["False"])
    L.new(ad.outputs[0], sw1.inputs["True"])
    out = N.new("ShaderNodeVectorMath")
    out.operation = "SCALE"
    L.new(nd.outputs[0], out.inputs[0])
    out.inputs["Scale"].default_value = -1.0
    st = N.new("ShaderNodeVectorMath")
    st.operation = "MULTIPLY_ADD"
    L.new(out.outputs[0], st.inputs[0])
    st.inputs[1].default_value = (1e-4, 1e-4, 1e-4)
    L.new(sw1.outputs[0], st.inputs[2])
    rc2 = N.new("GeometryNodeRaycast")
    L.new(gi.outputs["Closed"], rc2.inputs["Target Geometry"])
    L.new(st.outputs[0], rc2.inputs["Source Position"])
    L.new(out.outputs[0], rc2.inputs["Ray Direction"])
    rc2.inputs["Ray Length"].default_value = EXIT_REACH
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L.new(rc2.outputs["Hit Normal"], dot.inputs[0])
    L.new(out.outputs[0], dot.inputs[1])
    back = N.new("FunctionNodeCompare")
    back.data_type, back.operation = "FLOAT", "GREATER_THAN"
    L.new(dot.outputs["Value"], back.inputs[0])
    back.inputs[1].default_value = 0.0
    # ... and the opposite way too (two rays meeting back faces: inside a closed solid)
    st3 = N.new("ShaderNodeVectorMath")
    st3.operation = "MULTIPLY_ADD"
    L.new(nd.outputs[0], st3.inputs[0])
    st3.inputs[1].default_value = (1e-4, 1e-4, 1e-4)
    L.new(sw1.outputs[0], st3.inputs[2])
    rc3 = N.new("GeometryNodeRaycast")
    L.new(gi.outputs["Closed"], rc3.inputs["Target Geometry"])
    L.new(st3.outputs[0], rc3.inputs["Source Position"])
    L.new(nd.outputs[0], rc3.inputs["Ray Direction"])
    rc3.inputs["Ray Length"].default_value = CAP
    dot3 = N.new("ShaderNodeVectorMath")
    dot3.operation = "DOT_PRODUCT"
    L.new(rc3.outputs["Hit Normal"], dot3.inputs[0])
    L.new(nd.outputs[0], dot3.inputs[1])
    back3 = N.new("FunctionNodeCompare")
    back3.data_type, back3.operation = "FLOAT", "GREATER_THAN"
    L.new(dot3.outputs["Value"], back3.inputs[0])
    back3.inputs[1].default_value = 0.0
    b3 = N.new("FunctionNodeBooleanMath")
    b3.operation = "AND"
    L.new(rc3.outputs["Is Hit"], b3.inputs[0])
    L.new(back3.outputs[0], b3.inputs[1])
    na = N.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT"
    na.inputs["Name"].default_value = "ps_exit"
    se = N.new("GeometryNodeSampleIndex")
    se.data_type, se.domain = "FLOAT", "POINT"
    L.new(gi.outputs["Anchors"], se.inputs["Geometry"])
    L.new(na.outputs["Attribute"], se.inputs["Value"])
    L.new(idx.outputs[0], se.inputs["Index"])
    ok = N.new("FunctionNodeCompare")
    ok.data_type, ok.operation = "FLOAT", "GREATER_THAN"
    L.new(se.outputs[0], ok.inputs[0])
    ok.inputs[1].default_value = 0.5
    a1 = N.new("FunctionNodeBooleanMath")
    a1.operation = "AND"
    L.new(rc2.outputs["Is Hit"], a1.inputs[0])
    L.new(back.outputs[0], a1.inputs[1])
    a1b = N.new("FunctionNodeBooleanMath")
    a1b.operation = "AND"
    L.new(a1.outputs[0], a1b.inputs[0])
    L.new(b3.outputs[0], a1b.inputs[1])
    a2 = N.new("FunctionNodeBooleanMath")
    a2.operation = "AND"
    L.new(a1b.outputs[0], a2.inputs[0])
    L.new(ok.outputs[0], a2.inputs[1])
    ex = N.new("ShaderNodeVectorMath")
    ex.operation = "MULTIPLY_ADD"
    L.new(out.outputs[0], ex.inputs[0])
    ex.inputs[1].default_value = (margin, margin, margin)
    L.new(rc2.outputs["Hit Position"], ex.inputs[2])
    sw2 = N.new("GeometryNodeSwitch")
    sw2.input_type = "VECTOR"
    L.new(a2.outputs[0], sw2.inputs["Switch"])
    L.new(sw1.outputs[0], sw2.inputs["False"])
    L.new(ex.outputs[0], sw2.inputs["True"])
    any_ = N.new("FunctionNodeBooleanMath")
    any_.operation = "OR"
    L.new(clamp.outputs[0], any_.inputs[0])
    if exit_test:
        L.new(sw2.outputs[0], tl.inputs["Vector"])
        L.new(a2.outputs[0], any_.inputs[1])
    else:  # spec "exit_test": false: the anchor ray only
        L.new(sw1.outputs[0], tl.inputs["Vector"])
    sp = N.new("GeometryNodeSetPosition")
    L.new(gi.outputs["Geometry"], sp.inputs["Geometry"])
    L.new(any_.outputs[0], sp.inputs["Selection"])
    L.new(tl.outputs[0], sp.inputs["Position"])
    L.new(sp.outputs[0], go.inputs[0])
    return ng


def _bind_group(clamp, proxy, collider_set, closed_set, name, others_set):
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
    ocl = N.new("GeometryNodeObjectInfo")
    ocl.transform_space = "ORIGINAL"
    ocl.inputs["Object"].default_value = closed_set
    L.new(ocl.outputs["Geometry"], g.inputs["Closed"])
    oo = N.new("GeometryNodeObjectInfo")
    oo.transform_space = "ORIGINAL"
    oo.inputs["Object"].default_value = others_set
    L.new(oo.outputs["Geometry"], g.inputs["Others"])
    L.new(oself.outputs["Transform"], g.inputs["Self"])
    L.new(op.outputs["Transform"], g.inputs["Anchor Space"])
    L.new(g.outputs[0], go.inputs[0])
    return ng
