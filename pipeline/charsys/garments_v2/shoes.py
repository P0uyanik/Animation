"""``garment/2`` sneaker side stripes (T-093): felt bands on the side walls of a ``garment/1`` sneaker upper.

``stripes`` (item field of a ``sneakers`` item; every key optional):
  count       number of parallel stripes (1..5, default 2)
  width_m     width of one stripe across its length (default 0.006)
  gap_m       gap between neighbouring stripes (default 0.005)
  slope       forward lean of the stripes: metres forward per metre up (default 0.6; 0 = vertical)
  centre      fore-aft position of the stripe set, share of the shoe half length from the plan centre
              (+ = towards the toe, default -0.05)
  z_range     [low, high] shares of the upper height above the sole where the stripes run (default [0.12, 0.8])
  side_min    the stripes stay on the side walls: share of the shoe half width from the foot axis (default 0.55)
  sides       "both" (default) or "outer" (only the side away from the body's centre line)
  thickness_m thickness of the felt band (default 0.0012)
Material part ``stripe`` (falls back to ``sole``, then ``main``). Each stripe is a flat band with rounded edges laid on
the upper's outer surface (its path is projected onto the side wall), rigid to the shoe's weight anchor; stripe points
closer to the foot axis than ``side_min`` (the instep, the heel) are left out."""
from mathutils import Vector

from garments import generator as GEN
from garments import shapes as S

DEFAULTS = {"count": 2, "width_m": 0.006, "gap_m": 0.005, "slope": 0.6, "centre": -0.05, "z_range": [0.12, 0.8],
            "side_min": 0.55, "sides": "both", "thickness_m": 0.0012}


def validate_stripes(v, name):
    if v is False:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.stripes must be an object or false")
    if "count" in v and (not isinstance(v["count"], int) or isinstance(v["count"], bool) or not 1 <= v["count"] <= 5):
        raise ValueError(f"garment {name}.stripes.count must be an integer in [1, 5]")
    for key, lo, hi in (("width_m", 0.0005, 0.05), ("gap_m", 0.0, 0.05), ("slope", -3.0, 3.0), ("centre", -1.0, 1.0),
                        ("side_min", 0.0, 1.0), ("thickness_m", 0.0002, 0.01)):
        if key in v:
            GEN._number(v[key], f"garment {name}.stripes.{key}", lo, hi)
    if "z_range" in v:
        zr = v["z_range"]
        if (not isinstance(zr, list) or len(zr) != 2 or
                any(not isinstance(z, (int, float)) or isinstance(z, bool) for z in zr) or not 0 <= zr[0] < zr[1] <= 1.2):
            raise ValueError(f"garment {name}.stripes.z_range must be [low, high] with 0 <= low < high <= 1.2")
    if v.get("sides", "both") not in ("both", "outer"):
        raise ValueError(f"garment {name}.stripes.sides must be 'both' or 'outer'")


def _mat(G, cfg, H):
    mats = cfg.get("materials", {})
    key = next((k for k in ("stripe", "sole") if k in mats), "main")
    return GEN._mat_for(G, cfg, key, H)


def add_stripes(C, cfg, mine, G, H):
    """Stripes on every upper of the item (objects ``garment.<name>.main.<side>`` carrying ``ps_shoe_frame``): flat
    felt bands (rounded edges) laid on the upper's outer surface along slanted lines on its side walls."""
    st = dict(DEFAULTS, **cfg["stripes"]) if isinstance(cfg["stripes"], dict) else dict(DEFAULTS)
    n, w, gap, slope = int(st["count"]), float(st["width_m"]), float(st["gap_m"]), float(st["slope"])
    lo, hi = (float(z) for z in st["z_range"])
    t = float(st["thickness_m"])
    made, report = [], []
    mat = None
    for upper in mine:
        frame = upper.get("ps_shoe_frame")
        if frame is None or upper.get("ps_garment_part") != "main":
            continue
        hx, cy, A, B, z0, Hz = (float(x) for x in frame)
        side = upper.name.rsplit(".", 1)[-1]
        out_sign = 1.0 if hx >= 0 else -1.0
        bvh = S.bvh_of(upper)
        zmid = z0 + 0.5 * (lo + hi) * Hz
        walls = (out_sign,) if st["sides"] == "outer" else (out_sign, -out_sign)
        for wall in walls:
            for k in range(n):
                f = float(st["centre"]) * B + (k - 0.5 * (n - 1)) * (w + gap)
                pts, nrm = [], []
                for j in range(16):
                    z = z0 + (lo + (hi - lo) * j / 15) * Hz
                    y = cy - (f + slope * (z - zmid))
                    hit, hn = S.outer_hit([bvh], Vector((hx, y, z)), Vector((wall, 0.0, 0.0)), 2.5 * A)
                    if hit is None or abs(hit.x - hx) < float(st["side_min"]) * A:
                        continue
                    pts.append(hit + hn * (0.5 * t + 0.0003))
                    nrm.append(hn)
                if len(pts) < 4:
                    continue
                tag = "o" if wall == out_sign else "i"
                ob = S.ribbon(G, C, f"garment.{cfg['name']}.stripe.{side}.{tag}{k + 1}", pts, nrm, w, t,
                              round_share=0.6)
                mat = mat or _mat(G, cfg, H)
                GEN._feature(made, ob, cfg, "stripe", mat, G)
                report.append({"object": ob.name, "points": len(pts)})
    return made, {"count": n, "width_m": w, "gap_m": gap, "slope": slope, "pieces": report}
