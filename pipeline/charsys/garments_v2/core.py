"""``garment/2`` build: the ``garment/1`` build (by import, unchanged) plus the opt-in ``garment/2`` item fields.

Order per call of ``build``:
  1. ``validate``: the new fields are checked here; the rest of the block is checked by ``garment/1``'s own validator
     on the "garment/1 view" of the block (the same block with the new fields removed).
  2. ``garment/1`` builds every item from that view (shells, drape, rest clearance, fibres, masks).
  3. Per item, the new fields reshape its pieces or add new ones (tagged, weighted and given fibres like any
     ``garment/1`` piece).
``bind_to_body`` binds every piece with ``garment/1``'s weight transfer, then adds the pose correctives.
Character-agnostic: every size comes from the spec or from the generic body measures."""
import copy
import json

from garments import generator as GEN

from . import correctives, finish, outlines, pack, shoes

GENERATOR = "garment/2"
V1 = GEN.GENERATOR
# item type -> the garment/2 fields it accepts
ITEM_FIELDS = {
    "sneakers": ("stripes",),
    "backpack": ("flap", "tab", "pocket_flap"),
    "trousers": ("hem_break",),
    "shorts": ("hem_break", "leg_split"),
    "boots": ("cuff_roll",),
}
CORRECTIVE_TYPES = ("top", "shirt", "vest", "hoodie", "dress")
COLLAR_TYPES = ("top", "shirt", "dress")
ANY_TYPE = ("clean_fibres",)
V2_FIELDS = sorted({f for fs in ITEM_FIELDS.values() for f in fs} | {"correctives", "collar_clear"} | set(ANY_TYPE))
CORRECTIVES_PROP = "ps_garment2_correctives"


def _fields_of(raw):
    return [f for f in V2_FIELDS if f in raw]


def validate(clothing):
    """Validate a ``garment/2`` clothing block; returns it unchanged. Raises ValueError."""
    if not isinstance(clothing, dict) or clothing.get("generator") != GENERATOR:
        raise ValueError(f"clothing.generator must be {GENERATOR}")
    items = clothing.get("garments")
    if isinstance(items, list):
        for i, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            name = raw.get("name", raw.get("type"))
            for f in _fields_of(raw):
                if f in ANY_TYPE:
                    continue
                allowed = (CORRECTIVE_TYPES if f == "correctives" else COLLAR_TYPES if f == "collar_clear" else
                           [t for t, fs in ITEM_FIELDS.items() if f in fs])
                if raw.get("type") not in allowed:
                    raise ValueError(f"garment {name}.{f} ({GENERATOR}) is supported on {sorted(allowed)}")
            if "stripes" in raw:
                shoes.validate_stripes(raw["stripes"], name)
            for f in ("flap", "tab", "pocket_flap"):
                if f in raw:
                    pack.validate(raw, f, name)
            if "hem_break" in raw:
                outlines.validate_hem_break(raw["hem_break"], name)
            if "leg_split" in raw:
                outlines.validate_leg_split(raw["leg_split"], name)
            if "cuff_roll" in raw:
                outlines.validate_cuff_roll(raw["cuff_roll"], name)
            if "correctives" in raw:
                correctives.validate(raw["correctives"], name)
            if "clean_fibres" in raw:
                finish.validate_clean(raw["clean_fibres"], name)
            if "collar_clear" in raw:
                finish.validate_collar_clear(raw["collar_clear"], name)
                if raw.get("collar") in (None, "none") or (isinstance(raw.get("collar"), dict) and
                                                         raw["collar"].get("type", "none") == "none"):
                    raise ValueError(f"garment {name}.collar_clear needs a collar")
    GEN.validate(v1_view(clothing))
    return clothing


def v1_view(clothing):
    """The ``garment/1`` block ``garment/1`` builds from: the same block without the ``garment/2`` fields. A boot with
    ``cuff_roll`` drops its ``garment/1`` cuff tube (the rolled cuff replaces it)."""
    out = copy.deepcopy(clothing)
    out["generator"] = V1
    for raw in out.get("garments") or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("cuff_roll") not in (None, False):
            raw["cuff"] = False
            if isinstance(raw.get("bands"), dict):
                raw["bands"] = dict(raw["bands"], cuff=False)
            elif raw.get("bands") is True:
                raw["bands"] = {"cuff": False}
        for f in V2_FIELDS:
            raw.pop(f, None)
    return out


def _finish_new(new, cfg, lod, anchor=None, clean=(), clearance=0.0):
    """Shared finishing of pieces added by garment/2 (already tagged through GEN._feature): rest-clearance override,
    weight anchor of the item (rigid pieces) and the shared surface fibres."""
    fibres = []
    for ob in new:
        ob[GEN.CLEARANCE_PROP] = float(clearance)
        if anchor is not None:
            ob["ps_weight_anchor"] = tuple(anchor)
        f = None if clean and finish._matches(ob.get("ps_garment_part", ""), clean) else GEN.add_fibres(ob, lod)
        if f is not None:
            fibres.append(f)
    return fibres


def build(C, body, clothing, P, H, J, G):
    """Build garments before rigging. Returns ``(objects, JSON-safe report)`` like ``garment/1``."""
    validate(clothing)
    objects, report = GEN.build(C, body, v1_view(clothing), P, H, J, G)
    fit = GEN.BodyFit(P, H, J)
    lod = clothing.get("fibres_lod", "close")
    by_item = {}
    for ob in objects:
        by_item.setdefault(ob["ps_garment_item"], []).append(ob)
    ordered, v2_report, corr = [], {}, {}
    for raw in clothing["garments"]:
        cfg = GEN._merge(clothing.get("defaults"), raw)
        mine = by_item.get(cfg["name"], [])
        new, info = [], {}
        if cfg.get("stripes") not in (None, False):
            made, info["stripes"] = shoes.add_stripes(C, cfg, mine, G, H)
            new += made
        if any(cfg.get(f) not in (None, False) for f in ("flap", "tab", "pocket_flap")):
            made, info["flap_pack"] = pack.add_flaps(C, cfg, mine, G, H, fit)
            new += made
        if cfg.get("hem_break") not in (None, False):
            info["hem_break"] = outlines.hem_break(cfg, mine, P, H, J, fit)
        if cfg.get("leg_split") not in (None, False):
            info["leg_split"] = outlines.leg_split(cfg, mine, P, H, J, fit, body)
        if cfg.get("cuff_roll") not in (None, False):
            made, info["cuff_roll"] = outlines.cuff_roll(C, body, cfg, mine, P, H, J, G, fit)
            new += made
        if cfg.get("correctives") not in (None, False):
            corr[cfg["name"]] = cfg["correctives"]
            info["correctives"] = sorted(cfg["correctives"])
        removed = []
        if cfg.get("clean_fibres"):
            removed = finish.clean_fibres(mine, cfg["clean_fibres"])
            info["clean_fibres"] = {"parts": list(cfg["clean_fibres"]), "fibres_removed": len(removed)}
        fibres = []
        if new:
            anchor = next((ob["ps_weight_anchor"] for ob in mine if "ps_weight_anchor" in ob), None)
            rigid = cfg["type"] in ("backpack", "sneakers")
            fibres = _finish_new(new, cfg, lod, anchor if rigid else None, cfg.get("clean_fibres") or [])
        for entry in report["items"]:
            if entry["name"] == cfg["name"]:
                entry["objects"] += [o.name for o in new]
                entry["fibres"] = [f for f in entry["fibres"] if f["object"] not in removed]
                entry["fibres"] += [{"object": f.name, "source": f[GEN.FIBRES_PROP], "preset": f["ps_material_preset"],
                                     "lod": f["ps_fibres_lod"]} for f in fibres]
                entry["material_presets"] = sorted(set(entry["material_presets"]) |
                                                   {o.get("ps_material_preset", "") for o in new})
        if info:
            v2_report[cfg["name"]] = info
        ordered += mine + new
    # final pass: collars over the outer layers (needs every item built)
    for raw in clothing["garments"]:
        cfg = GEN._merge(clothing.get("defaults"), raw)
        if not cfg.get("collar_clear"):
            continue
        collar = next((o for o in ordered if o.get("ps_garment_item") == cfg["name"]
                       and o.get("ps_garment_part") == "collar"), None)
        over = set(cfg["collar_clear"]["over"])
        outer = [o for o in ordered if o.get("ps_garment_item") in over and o.type == "MESH"]
        if collar is None or not outer:
            raise ValueError(f"garment {cfg['name']}.collar_clear: no collar or no piece of {sorted(over)}")
        inner = [o for o in ordered if o.get("ps_garment_item") == cfg["name"] and o.type == "MESH"
                 and o.get("ps_garment_part") == "main"]
        v2_report.setdefault(cfg["name"], {})["collar_clear"] = finish.collar_clear(collar, outer, cfg["collar_clear"],
                                                                                   inner)
    for ob in ordered:
        ob["ps_garment_generator"] = GENERATOR
    body[CORRECTIVES_PROP] = json.dumps(corr, sort_keys=True)
    report["generator"] = GENERATOR
    report["reuses"] = V1
    report["objects"] = len(ordered)
    report["garment_2"] = v2_report
    return ordered, report


def bind_to_body(rig, body, garments, neighbours=1, max_influences=4, worn=None):
    """``garment/1`` weight transfer and collision for every piece, then the pose correctives of the items that ask
    for them (shape keys driven by the arm pose)."""
    out = GEN.bind_to_body(rig, body, garments, neighbours=neighbours, max_influences=max_influences, worn=worn)
    corr = json.loads(body.get(CORRECTIVES_PROP, "{}") or "{}")
    if corr:
        out["correctives"] = {name: correctives.add(rig, [o for o in garments if o.get("ps_garment_item") == name], cfg,
                                                    max_influences, [o for o in garments
                                                                     if o.get("ps_garment_item") != name])
                              for name, cfg in sorted(corr.items())}
    return out
