"""``garment/3`` item type ``tights`` (T-126): a close knitted shell on the legs and feet.

``garment/1`` has no item for hosiery: ``trousers`` end at the ankle. ``tights`` is the skin-following shell that
``ankle_close`` builds, taken from the waist down to the toes: one piece ``garment.<item>.main`` (part ``main``),
``ease_m`` off the skin and ``thickness_m`` thick, skinned with the weights of the skin under it (each vertex keeps its
body vertex), so it bends exactly as the leg does and stays under skirts, shorts and footwear. It covers the body
faces it lies on (the body mask hides them like under any other item).

  {"type": "tights", "name": "tights", "waist_z_m": 0.40, "ease_m": 0.0025, "thickness_m": 0.0012, "material": {...}}
``waist_z_m`` defaults to the body's waist level; ``ease_m`` is multiplied by the leg scale of the body (``fit.leg``).
An item worn over the tights needs a larger ease than ``ease_m + thickness_m``.
Character-agnostic: the region is the body below the waist inside the torso section, then everything below the hip
that is not an arm or a hand."""
from garments import generator as GEN

FIELDS = {"type", "name", "waist_z_m", "ease_m", "thickness_m", "material", "materials", "mask_body", "fibre_uv",
          "clean_fibres", "seam_radius_m", "collision_clearance_m"}
RANGES = {"waist_z_m": (0.05, 2.0), "ease_m": (0.0005, 0.02), "thickness_m": (0.0, 0.01)}


def validate(raw, name):
    for key in raw:
        if key not in FIELDS:
            raise ValueError(f"garment {name}.{key}: unknown field for tights (known: {sorted(FIELDS)})")
    for key, (low, high) in RANGES.items():
        if key in raw:
            GEN._number(raw[key], f"garment {name}.{key}", low, high)
    GEN._assignment(dict(raw, name=name), "main")


def build(C, body, cfg, P, H, J, G, fit):
    """Returns (pieces, covered body faces, report)."""
    waist = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))
    if waist <= fit.hip_z:
        raise ValueError(f"garment {cfg['name']}.waist_z_m must be above the hip ({fit.hip_z:.3f} m)")
    margin = 0.015 * fit.torso
    ease, thick = float(cfg["ease_m"]) * fit.leg, float(cfg["thickness_m"])

    def selector(c):
        if c.z > waist:
            return False
        if c.z >= fit.hip_z:
            w, front, back = GEN._torso_dims(P, H, c.z)
            return abs(c.x) <= w + margin and -front - margin <= c.y <= back + margin
        return not fit.in_sleeve(c, 0.0, 2.0, 0.03 * fit.arm)  # legs and feet, never a hand below the hip

    ob, cov = GEN._shell(body, f"garment.{cfg['name']}.main", selector, ease, thick, C, G)
    made = []
    GEN._feature(made, ob, cfg, "main", GEN._mat_for(G, cfg, "main", H), G)
    return made, cov, {"waist_z_m": round(waist, 4), "ease_m": round(ease, 5), "thickness_m": thick,
                       "vertices": len(ob.data.vertices), "covered_body_faces": len(cov)}
