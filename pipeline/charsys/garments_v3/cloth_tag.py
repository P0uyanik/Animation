"""``garment/3`` ``cloth_sim`` (``dress``, ``skirt``; T-126): marks a skirt piece for the opt-in cloth simulation.

The build itself does not simulate anything. ``cloth_sim`` only records, on the item's skirt piece, what the baked
simulation of ``pipeline/charsys/cloth_sim`` needs to find it: the property ``ps_cloth_sim`` (the settings as JSON) and
the float point attribute ``ps_cloth_pin`` (1 on the top ``pin_top`` share of the piece's height, where the skirt
hangs from its waist seam and keeps following the body, falling smoothly to 0 over the next ``pin_blend`` share;
0 = free cloth). A character without the field, or a shot that does not run the simulation, is unchanged: the piece
stays skinned as built.

  true | {"pin_top": 0.12, "pin_blend": 0.1}"""
import json

from garments import generator as GEN

SIM = {"pin_top": 0.12, "pin_blend": 0.1}
PROP, PIN = "ps_cloth_sim", "ps_cloth_pin"


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.cloth_sim must be true or an object")
    for key in v:
        if key not in SIM:
            raise ValueError(f"garment {name}.cloth_sim.{key}: unknown field (known: {sorted(SIM)})")
        GEN._number(v[key], f"garment {name}.cloth_sim.{key}", 0.0, 0.9)


def tag(cfg, mine):
    st = dict(SIM, **(cfg["cloth_sim"] if isinstance(cfg["cloth_sim"], dict) else {}))
    part = "skirt" if cfg["type"] == "dress" else "main"
    ob = next((o for o in mine if o.get("ps_garment_part") == part and o.type == "MESH"), None)
    if ob is None:
        raise ValueError(f"garment {cfg['name']}.cloth_sim: the item has no skirt piece")
    zs = [v.co.z for v in ob.data.vertices]
    z0, z1 = min(zs), max(zs)
    top, blend = float(st["pin_top"]), max(float(st["pin_blend"]), 1e-6)
    attr = ob.data.attributes.get(PIN) or ob.data.attributes.new(PIN, "FLOAT", "POINT")
    values = []
    for z in zs:
        d = (z1 - z) / max(z1 - z0, 1e-9)  # 0 at the waist seam, 1 at the hem
        x = max(0.0, min(1.0, 1.0 - (d - top) / blend))
        values.append(x * x * (3 - 2 * x))
    attr.data.foreach_set("value", values)
    ob[PROP] = json.dumps(st, sort_keys=True)
    return {"piece": ob.name, "pinned_vertices": sum(1 for x in values if x >= 0.999), "vertices": len(values), **st}
