"""T-119: candidate overrides on the current published specs (read-only), written next to this file.

    python3 docs/evaluation/characters/T-119/make_overrides.py

The spec merger replaces arrays, so each override carries the whole clothing list of the published spec with only
the fields below changed. Nothing is published or made current.
girl  girl_auburn_bun_glasses.T-119.override.json  0.12.0 + garment/3: blouse ``collar_seat`` (replaces the collar
      lift and ``collar_clear``), shorts ``cuff_gather`` (the T-093b crotch arch is switched off: the gather
      separates the legs).
boy   boy_yellow_hoodie.T-119.override.json        2.1.0 + garment/3: trousers ``ankle_close``; skin preset
      ``skin-felt-limbs/3`` (skin_presets_r3.json)."""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(ROOT, "assets", "characters")
GIRL = ("girl_auburn_bun_glasses", "0.12.0")
BOY = ("boy_yellow_hoodie", "2.1.0")

COLLAR_SEAT = {"over": ["vest"], "gap_m": 0.0015, "over_gap_m": 0.004, "max_droop_deg": 80, "bend_deg": 30, "smooth": 4, "step_deg": 6}
CUFF_GATHER = {"height_m": 0.09, "ease_m": 0.002, "pleats": 10, "pleat_depth_m": 0.004, "centre_m": 0.03}
ANKLE_CLOSE = {"up_m": 0.05, "down_m": 0.035, "ease_m": 0.005}
BOY_SKIN = "skin-felt-limbs/3"
BOY_LIMB_SRGB = [226, 178, 162]  # the reference hands on val27_front: slightly deeper and pinker than the face albedo (README)


def spec(cid, version):
    return json.load(open(os.path.join(CH, cid, "spec", f"{cid}.{version}.spec.json")))


def item(clothing, name):
    return next(g for g in clothing["garments"] if g["name"] == name)


def write(cid, override, note):
    override.setdefault("metadata", {})["notes"] = note
    path = os.path.join(HERE, f"{cid}.T-119.override.json")
    with open(path, "w") as f:
        json.dump({"override": override}, f, indent=1)
        f.write("\n")
    print(os.path.relpath(path, ROOT))


def girl():
    cid, version = GIRL
    clothing = copy.deepcopy(spec(cid, version)["clothing"])
    clothing["generator"] = "garment/3"
    blouse = item(clothing, "blouse")
    blouse["collar_seat"] = dict(COLLAR_SEAT)
    blouse["collar"] = dict(blouse["collar"], lift_m=0.0)  # the seat lays the collar on the vest
    shorts = item(clothing, "shorts")
    shorts["cuff_gather"] = dict(CUFF_GATHER)
    shorts["leg_split"] = dict(shorts["leg_split"], crotch_lift=0.0)
    write(cid, {"generators": {"garment": "garment/3"}, "clothing": clothing},
          f"T-119 candidate on {version}: garment/3 collar_seat (blouse) and cuff_gather (shorts).")


def boy():
    cid, version = BOY
    base = spec(cid, version)
    clothing = copy.deepcopy(base["clothing"])
    clothing["generator"] = "garment/3"
    item(clothing, "trousers")["ankle_close"] = dict(ANKLE_CLOSE)
    limbs = dict(base["materials"]["assignments"]["skin"], preset=BOY_SKIN, base_color_srgb=BOY_LIMB_SRGB)
    limbs.pop("source", None)
    write(cid, {"generators": {"garment": "garment/3"}, "clothing": clothing,
                "materials": {"assignments": {"skin_limbs": limbs}}},
          f"T-119 candidate on {version}: garment/3 ankle_close (trousers) and skin preset {BOY_SKIN}.")


if __name__ == "__main__":
    girl()
    boy()
