"""``garment/3`` ``rib_cuff`` (``top`` / ``shirt`` / ``dress`` / ``hoodie`` with sleeve cuff bands): a knitted or plain
cuff band at the end of each sleeve.

``garment/1`` ends a sleeve in one seam ring. ``rib_cuff`` adds, per arm, a short close band from that ring towards
the hand (piece ``garment.<item>.ribcuff.<side>``, part ``rib_cuff``; its material is the item's ``materials.rib_cuff``
entry, else the band material): ``height_m`` long, ``thickness_m`` thick with rounded ends, the ring's radius less
``tighten`` (a share of it), and ``ribs`` raised wales of ``depth_m`` running along the arm, as on a 1x1 rib knit.
``ribs`` 0 gives a plain turned cuff. The band starts ``overlap`` x its height under the sleeve end, so a full sleeve
reads as gathered into it. It is skinned like every garment piece (nearest skin weights) and gets the fabric's fibres.

  {"height_m": 0.02, "ribs": 14, "depth_m": 0.0015, "thickness_m": 0.003, "tighten": 0.04, "overlap": 0.15}
Lengths are multiplied by the arm scale of the body. Character-agnostic: the wrist end, direction and radius are
read from the item's own sleeve rings and the body's arm joints."""
import math

from mathutils import Vector

from garments import generator as GEN

RIB = {"height_m": 0.02, "ribs": 14, "depth_m": 0.0015, "thickness_m": 0.003, "tighten": 0.04, "overlap": 0.15}
RANGES = {"height_m": (0.004, 0.12), "depth_m": (0.0, 0.01), "thickness_m": (0.001, 0.02), "tighten": (0.0, 0.3),
          "overlap": (0.0, 0.5)}
ROWS = 8  # sections along the band
TUBE = 8  # vertices around a garment/1 limb ring's tube (sections of the seam ring)


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.rib_cuff must be true or an object")
    for key in v:
        if key not in RIB:
            raise ValueError(f"garment {name}.rib_cuff.{key}: unknown field (known: {sorted(RIB)})")
        if key == "ribs":
            if not isinstance(v[key], int) or isinstance(v[key], bool) or not 0 <= v[key] <= 64:
                raise ValueError(f"garment {name}.rib_cuff.ribs must be an integer in [0, 64]")
        else:
            GEN._number(v[key], f"garment {name}.rib_cuff.{key}", *RANGES[key])


def add(C, body, cfg, mine, J, H, G, fit):
    st = dict(RIB, **(cfg["rib_cuff"] if isinstance(cfg["rib_cuff"], dict) else {}))
    height, depth = float(st["height_m"]) * fit.arm, float(st["depth_m"]) * fit.arm
    thick, ribs = float(st["thickness_m"]) * fit.arm, int(st["ribs"])
    part = "rib_cuff" if "rib_cuff" in cfg.get("materials", {}) else "band"
    count = max(32, 4 * ribs)
    made, info = [], {"ribs": ribs, "height_m": round(height, 5), "pieces": {}}
    for side in ("L", "R"):
        ring = next((o for o in mine if o.name == f"garment.{cfg['name']}.band.cuff.{side}"), None)
        if ring is None or len(ring.data.vertices) % TUBE:
            raise ValueError(f"garment {cfg['name']}.rib_cuff: the item has no sleeve cuff band on side {side}")
        pts = [ring.matrix_world @ v.co for v in ring.data.vertices]
        mids = [sum(pts[j:j + TUBE], Vector((0.0, 0.0, 0.0))) / TUBE for j in range(0, len(pts), TUBE)]
        centre = sum(mids, Vector((0.0, 0.0, 0.0))) / len(mids)
        axis = (J[f"wrist.{side}"] - J[f"shoulder.{side}"]).normalized()  # along the arm, towards the hand
        radius = sum(((m - centre) - axis * (m - centre).dot(axis)).length for m in mids) / len(mids)
        radius *= 1.0 - float(st["tighten"])
        u = axis.cross(Vector((0.0, -1.0, 0.0)))
        u = u.normalized() if u.length > 1e-6 else Vector((1.0, 0.0, 0.0))
        w = axis.cross(u)
        s0 = -float(st["overlap"]) * height
        verts, faces = [], []
        for sheet in (1.0, -1.0):  # outer surface, then the inner wall
            for j in range(ROWS + 1):
                t = j / ROWS
                round_end = math.sin(math.pi * t) ** 0.35  # rounded ends: both walls meet the mid radius there
                for k in range(count):
                    a = 2 * math.pi * k / count
                    wale = depth * 0.5 * (1.0 + math.cos(ribs * a)) if ribs and sheet > 0 else 0.0
                    r = radius + sheet * 0.5 * thick * round_end + wale * round_end
                    verts.append(centre + axis * (s0 + t * (height - s0)) + (u * math.cos(a) + w * math.sin(a)) * r)
        per = (ROWS + 1) * count
        for j in range(ROWS):
            for k in range(count):
                a, b = j * count + k, j * count + (k + 1) % count
                faces.append((a, b, b + count, a + count))  # outer
                faces.append((per + b, per + a, per + a + count, per + b + count))  # inner (facing the arm)
        for j, flip in ((0, True), (ROWS, False)):  # close both ends between the two walls
            for k in range(count):
                a, b = j * count + k, j * count + (k + 1) % count
                faces.append((a, per + a, per + b, b) if flip else (b, per + b, per + a, a))
        ob = G.new_object(f"garment.{cfg['name']}.ribcuff.{side}", verts, faces, C)
        GEN._ensure_clearance(body, ob, 0.001 * fit.arm)
        GEN._feature(made, ob, cfg, "rib_cuff", GEN._mat_for(G, cfg, part, H), G)
        info["pieces"][ob.name] = {"vertices": len(verts), "radius_m": round(radius, 4),
                                   "centre_m": [round(c, 4) for c in centre]}
    return made, info
