"""``garment/3`` ``fibre_uv`` (any item; T-126): a knit that runs down the body and along the sleeve.

Directional material patterns (``fibre.kind`` ``knit``, ``weave``, ``denim``) are laid in object space unless the
material asks for ``fibre.coordinates: "uv"``, which reads the mesh's ``ps_fibre`` UV map (as groom ropes do).
``fibre_uv`` writes that map on every mesh piece of the item, in metres: U round the limb or the body, V along it.
Each face takes the axis of the body part it clothes: an arm (shoulder to wrist) inside the sleeve, a leg below the
hip on leg wear, else the vertical axis of the piece. U is the angle about that axis times the mean radius of the
piece's faces on that axis, so stitches keep one width down a piece; the angle seam is at the back of the body and
under the limb. The map only takes effect in materials that ask for it.

  true | {"swap": false}      # swap: exchange U and V (for a pattern whose rows should run along the piece)
Character-agnostic: axes come from the rig joints and the body measures."""
import math

from mathutils import Vector

from garments import generator as GEN

UV = "ps_fibre"
SLEEVED = ("top", "shirt", "dress", "hoodie")
LEGGED = ("tights", "trousers", "shorts")
Z = Vector((0.0, 0.0, 1.0))


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict) or any(k != "swap" for k in v) or not isinstance(v.get("swap", False), bool):
        raise ValueError(f"garment {name}.fibre_uv must be true or {{\"swap\": bool}}")


def _frame(a, b, seam):
    """(origin, unit axis, e1, e2): the angle is 0 opposite ``seam`` (a direction the seam side faces)."""
    w = (b - a).normalized()
    e1 = -(seam - w * seam.dot(w))
    e1 = e1.normalized() if e1.length > 1e-6 else w.orthogonal().normalized()
    return a, w, e1, w.cross(e1)


def add(cfg, mine, P, H, J, fit):
    swap = bool(cfg["fibre_uv"].get("swap", False)) if isinstance(cfg["fibre_uv"], dict) else False
    arms = [(J[f"shoulder.{s}"], J[f"wrist.{s}"]) for s in ("L", "R")] if cfg["type"] in SLEEVED else []
    puff = float(cfg.get("sleeve_puff_m", 0.0)) + 0.015 * fit.arm
    legs = cfg["type"] in LEGGED
    info = {}
    for ob in mine:
        if ob.type != "MESH":
            continue
        me, mw = ob.data, ob.matrix_world
        pts = [mw @ v.co for v in me.vertices]
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        one_side = min(p.x for p in pts) * max(p.x for p in pts) > 0  # a piece on one side (boot, cuff) has its own axis
        frames, per_face = {}, []
        for poly in me.polygons:
            c = sum((pts[i] for i in poly.vertices), Vector()) / len(poly.vertices)
            key = "body"
            for k, (a, b) in enumerate(arms):
                d = b - a
                t = (c - a).dot(d) / d.length_squared
                if -0.05 <= t <= 1.6 and (c - (a + d * t)).length <= GEN._arm_radius(P, H, max(0.0, min(1.0, t))) + puff:
                    key = f"arm{k}"
            if key == "body" and legs and c.z < fit.hip_z:
                key = "leg0" if c.x > 0 else "leg1"
            if key not in frames:
                if key.startswith("arm"):
                    a, b = arms[int(key[3])]
                    frames[key] = _frame(a, b, -Z)  # seam under the arm
                elif key.startswith("leg"):
                    hip = J["hip.L" if key == "leg0" else "hip.R"]
                    frames[key] = _frame(Vector((hip.x, hip.y, 0.0)), Vector((hip.x, hip.y, 1.0)), Vector((0, 1, 0)))
                else:
                    o = Vector((cx if one_side else 0.0, cy, 0.0))
                    frames[key] = _frame(o, o + Z, Vector((0, 1, 0)))  # seam at the back
            per_face.append((key, c))
        radius = {}
        for key, c in per_face:
            o, w, _, _ = frames[key]
            q = c - o
            s = radius.setdefault(key, [0.0, 0])
            s[0] += (q - w * q.dot(w)).length
            s[1] += 1
        radius = {k: s[0] / s[1] for k, s in radius.items()}
        layer = me.uv_layers.get(UV) or me.uv_layers.new(name=UV, do_init=False)
        for poly, (key, c) in zip(me.polygons, per_face):
            o, w, e1, e2 = frames[key]
            q = c - o
            ac = math.atan2(q.dot(e2), q.dot(e1))
            for li in poly.loop_indices:
                q = pts[me.loops[li].vertex_index] - o
                da = math.atan2(q.dot(e2), q.dot(e1)) - ac
                da = (da + math.pi) % (2.0 * math.pi) - math.pi  # corners stay on their face's side of the seam
                uv = ((ac + da) * radius[key], q.dot(w))
                layer.data[li].uv = (uv[1], uv[0]) if swap else uv
        info[ob.name] = {k: round(r, 4) for k, r in sorted(radius.items())}
    return {"uv_map": UV, "swap": swap, "mean_radius_m": info}
