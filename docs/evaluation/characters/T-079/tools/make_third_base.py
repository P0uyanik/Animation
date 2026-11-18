"""T-044: a head + hair TEST base for the third character (her full character is V6; she has no spec yet).

Derived from an existing generic-body spec (body, face rig and garments reused as a stand-in), with her reference
colours (skin, blue iris, light brows, powder-blue dress, off-white tights, camel boots) and no glasses. Only the head
and hair are evidence; body proportions, face shape and outfit are NOT hers. Writes candidates/third.base.spec.json.

    python3 docs/evaluation/characters/T-079/tools/make_third_base.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
CAND = os.path.join(HERE, "..", "candidates")
CH = json.load(open(os.path.join(CAND, "characters.json")))
c = CH["third"]
spec = json.load(open(os.path.join(ROOT, c["stand_in_spec"])))
col = {k: v["srgb"] for k, v in json.load(open(os.path.join(ROOT, c["colours"]))).items() if isinstance(v, dict) and "srgb" in v}
spec["identity"] = {"id": c["id"], "display_name": c["id"] + " (T-044 head + hair test base)",
                    "note": "stand-in body/face/outfit geometry; only head colours and hair are evaluated"}
spec["accessories"]["items"] = []
eyes = spec["face"]["eyes"]
eyes["iris"].update(srgb=col["iris"], inner_srgb=[104, 140, 172], dark_srgb=[30, 46, 66], limbal_srgb=[18, 24, 34],
                    glow_srgb=[150, 186, 214], shade_srgb=[34, 52, 74])
spec["face"]["brows"]["srgb"] = [170, 150, 130]
spec["face"]["mouth"]["rest_shape"] = c.get("rest_mouth", spec["face"]["mouth"]["rest_shape"])
mats = spec["materials"]
mats["target_colors_srgb"]["skin"] = col["skin"]
mats["assignments"]["skin"]["base_color_srgb"] = col["skin"]
for slot in ("glasses", "glasses_lens"):
    mats["assignments"].pop(slot, None)
garment_cols = [col["dress"], col["dress"], col["tights"], col["boots"]]
for g, rgb in zip(spec["clothing"]["garments"], garment_cols):
    g["material"]["base_color_srgb"] = rgb
    for m in (g.get("materials") or {}).values():
        m["base_color_srgb"] = rgb
    if "embroidery" in g:
        g["embroidery"]["material"]["base_color_srgb"] = rgb
        g["embroidery"]["accent_material"]["base_color_srgb"] = rgb
out = os.path.join(CAND, "third.base.spec.json")
json.dump(spec, open(out, "w"), indent=1)
print("wrote", out)
