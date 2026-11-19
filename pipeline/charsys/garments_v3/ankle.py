"""``garment/3`` ``ankle_close`` (trousers): no skin between the trouser hem and the shoe, in any ankle pose.

A loose trouser leg ends in a wide hem; from the side and from above the shoe the ankle skin shows inside it, and
more when the ankle flexes (the hem follows the shin, the shoe the foot). ``ankle_close`` adds, per leg, a close
inner cuff in the trouser fabric (piece ``garment.<item>.ankle.<side>``, part ``ankle``; its material is the
item's ``materials.ankle`` entry, or the main fabric): a thin shell on the leg skin from ``up_m`` above the hem to
``down_m`` below it (into the shoe), ``ease_m`` off the skin. It is skinned with the weights of the skin it lies on,
so it bends with the ankle exactly as the leg does and stays inside both the trouser hem and the shoe collar - like
the ribbed cuff of a jogger tucked into the shoe.

  {"up_m": 0.05, "down_m": 0.035, "ease_m": 0.003, "thickness_m": 0.002, "reach": 1.5}
Lengths are multiplied by the leg scale of the body (``fit.leg``). ``reach``: faces within ``reach`` leg radii of the
leg centre at the hem are covered (the leg, not the foot in front of it).
Character-agnostic: the hem height is measured on the built trousers, the leg centre and radius on the body."""
import math

from garments import generator as GEN

ANKLE = {"up_m": 0.05, "down_m": 0.035, "ease_m": 0.003, "thickness_m": 0.002, "reach": 1.5}
RANGES = {"up_m": (0.005, 0.2), "down_m": (0.0, 0.1), "ease_m": (0.0005, 0.02), "thickness_m": (0.0, 0.01),
          "reach": (1.0, 3.0)}


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.ankle_close must be true or an object")
    for key in v:
        if key not in ANKLE:
            raise ValueError(f"garment {name}.ankle_close.{key}: unknown field (known: {sorted(ANKLE)})")
        GEN._number(v[key], f"garment {name}.ankle_close.{key}", *RANGES[key])


def _leg_section(body, side, z, band):
    """(centre x, centre y, radius) of the body's cross-section on one side (+1 left, -1 right) at height z."""
    pts = [v.co for v in body.data.vertices if abs(v.co.z - z) <= band and v.co.x * side > 0]
    if not pts:
        raise ValueError("ankle_close: no body vertices at the trouser hem")
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    return 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.25 * ((x1 - x0) + (y1 - y0))


def close(C, body, cfg, mine, H, G, fit):
    st = dict(ANKLE, **(cfg["ankle_close"] if isinstance(cfg["ankle_close"], dict) else {}))
    main = next(o for o in mine if o.get("ps_garment_part") == "main")
    hem = min((main.matrix_world @ v.co).z for v in main.data.vertices)
    up, down = float(st["up_m"]) * fit.leg, float(st["down_m"]) * fit.leg
    ease, thick = float(st["ease_m"]) * fit.leg, float(st["thickness_m"])
    part = "ankle" if "ankle" in cfg.get("materials", {}) else "main"
    made, info = [], {"hem_z_m": round(hem, 4), "from_z_m": round(hem - down, 4), "to_z_m": round(hem + up, 4),
                      "ease_m": round(ease, 5), "pieces": {}}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        cx, cy, r = _leg_section(body, sx, hem + 0.5 * up, 0.004 * fit.leg)
        limit = float(st["reach"]) * r

        def selector(c, cx=cx, cy=cy, limit=limit, sx=sx):
            return hem - down <= c.z <= hem + up and c.x * sx > 0 and math.hypot(c.x - cx, c.y - cy) <= limit

        ob, _ = GEN._shell(body, f"garment.{cfg['name']}.ankle.{side}", selector, ease, thick, C, G)
        GEN._feature(made, ob, cfg, "ankle", GEN._mat_for(G, cfg, part, H), G)
        info["pieces"][ob.name] = {"vertices": len(ob.data.vertices), "leg_radius_m": round(r, 4)}
    return made, info
