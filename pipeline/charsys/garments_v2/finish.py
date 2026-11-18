"""``garment/2`` edge finishing (T-093 round 2): cleanly finished edges and a collar that lies over the outer layers.

clean_fibres (any item): a list of material parts (``ps_garment_part`` values, e.g. ``["collar", "edge"]``) whose
  pieces get no surface fibres, so cut edges, rolled edges and collars read as cleanly finished instead of fringed.
  A part name ending in "*" matches every part that starts with it. The fabric's material is unchanged.
collar_clear (``top``, ``shirt``, ``dress``): {"over": [item names], "gap_m": 0.004, "reach_m": 0.03,
  "smooth": 4, "max_lift_m": 0.012} - after every item is built, the collar is lifted off the listed (outer) items wherever it lies closer
  than ``gap_m`` to them or inside them (the vest's surface and its fibres no longer show through the collar); a
  vertex that would need more than ``max_lift_m`` is taken as a hit on the far side of a thin piece and left alone. Both
  sheets of the solidified collar move together, so its thickness is kept; the lift is smoothed over the collar.
Character-agnostic: only the item and part names from the spec are used."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from garments import generator as GEN

COLLAR_CLEAR = {"over": [], "gap_m": 0.004, "reach_m": 0.03, "smooth": 4, "max_lift_m": 0.012}


def validate_clean(v, name):
    if not isinstance(v, list) or not v or any(not isinstance(p, str) or not p for p in v):
        raise ValueError(f"garment {name}.clean_fibres must be a non-empty list of part names")


def validate_collar_clear(v, name):
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.collar_clear must be an object")
    for key in v:
        if key not in COLLAR_CLEAR:
            raise ValueError(f"garment {name}.collar_clear.{key}: unknown field (known: {sorted(COLLAR_CLEAR)})")
    over = v.get("over", [])
    if not isinstance(over, list) or not over or any(not isinstance(x, str) for x in over):
        raise ValueError(f"garment {name}.collar_clear.over must be a non-empty list of item names")
    for key, lo, hi in (("gap_m", 0.0, 0.03), ("reach_m", 0.001, 0.1), ("max_lift_m", 0.001, 0.05)):
        if key in v:
            GEN._number(v[key], f"garment {name}.collar_clear.{key}", lo, hi)
    if "smooth" in v and (not isinstance(v["smooth"], int) or isinstance(v["smooth"], bool) or not 0 <= v["smooth"] <= 20):
        raise ValueError(f"garment {name}.collar_clear.smooth must be an integer in [0, 20]")


def _matches(part, patterns):
    return any(part.startswith(p[:-1]) if p.endswith("*") else part == p for p in patterns)


def clean_fibres(pieces, patterns):
    """Removes the shared surface fibres of the matching pieces. Returns the removed fibre object names."""
    removed = []
    for ob in pieces:
        if not _matches(ob.get("ps_garment_part", ""), patterns):
            continue
        for f in GEN.fibre_children(ob):
            removed.append(f.name)
            data = f.data
            bpy.data.objects.remove(f, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Curves):
                    bpy.data.hair_curves.remove(data)
                elif isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
    return sorted(removed)


def _bvh(ob):
    mw = ob.matrix_world
    return BVHTree.FromPolygons([mw @ v.co for v in ob.data.vertices], [tuple(p.vertices) for p in ob.data.polygons],
                                all_triangles=False)


def collar_clear(collar, outer, cfg, inner=()):
    """Lays the collar over the ``outer`` pieces (see the module docstring). Returns a JSON-safe report.

    The solidified collar is two sheets (vertex i and i + n/2). Each point of the first sheet is cast down its own
    normal onto the outermost of the outer pieces and the ``inner`` pieces (the blouse itself, so the collar also lies
    on the blouse where there is no vest); where it lies closer than ``gap_m`` to that surface (or under it) it is
    lifted to ``gap_m`` above it (at most ``max_lift_m``). The lift is smoothed over the sheet, then the second
    sheet is rebuilt at the collar's thickness along the new normals, so the collar stays one clean, even layer."""
    st = dict(COLLAR_CLEAR, **cfg)
    gap, reach, cap = float(st["gap_m"]), float(st["reach_m"]), float(st["max_lift_m"])
    bvhs = [_bvh(o) for o in list(outer) + list(inner) if o.type == "MESH" and len(o.data.polygons)]
    me = collar.data
    n = len(me.vertices)
    if n % 2:
        raise ValueError(f"{collar.name}: expected a solidified (two-sheet) collar")
    h = n // 2
    mw = collar.matrix_world
    inv = mw.inverted()
    pts = [mw @ v.co for v in me.vertices]
    thick = sum((pts[i + h] - pts[i]).length for i in range(h)) / h
    nrm = [(pts[i + h] - pts[i]).normalized() if (pts[i + h] - pts[i]).length > 1e-9 else
           (mw.to_3x3() @ me.vertices[i].normal).normalized() for i in range(h)]
    lift = [0.0] * h
    for i in range(h):
        p, d = pts[i], nrm[i]
        origin = p + d * (cap + reach)
        best = None
        for bvh in bvhs:
            loc, hn, _, dist = bvh.ray_cast(origin, -d, 2 * (cap + reach))
            if loc is not None and (best is None or dist < best[1]):
                best = (loc, dist)
        if best is None:
            continue
        above = (p - best[0]).dot(d)  # height of the collar point over the outermost surface along its normal
        need = gap - above
        if 0 < need <= cap:
            lift[i] = need
    nbrs = [set() for _ in range(h)]
    for e in me.edges:
        a, b = e.vertices
        if a < h and b < h:
            nbrs[a].add(b)
            nbrs[b].add(a)
    need = list(lift)
    for _ in range(int(st["smooth"])):
        lift = [max(need[i], 0.5 * lift[i] + 0.5 * sum(lift[j] for j in nbrs[i]) / len(nbrs[i])) if nbrs[i] else lift[i]
                for i in range(h)]
    moved, biggest = 0, 0.0
    for i in range(h):
        q = pts[i] + nrm[i] * lift[i]
        me.vertices[i].co = inv @ q
        me.vertices[i + h].co = inv @ (q + nrm[i] * thick)
        if lift[i] > 1e-7:
            moved += 1
            biggest = max(biggest, lift[i])
    me.update()
    return {"collar": collar.name, "over": sorted({o.get("ps_garment_item", "") for o in outer}), "gap_m": gap,
            "thickness_m": round(thick, 5), "vertices_lifted": moved, "max_lift_m": round(biggest, 5)}
