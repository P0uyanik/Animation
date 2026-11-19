"""``garment/3`` build: the ``garment/2`` build (by import, unchanged) plus the opt-in ``garment/3`` item fields.

Order per call of ``build``:
  1. ``validate``: the new fields are checked here; the rest of the block is checked by ``garment/2``'s validator on
     the "garment/2 view" of the block (the same block with the new fields removed and the generator renamed).
  2. ``garment/2`` builds every item from that view.
  3. Per item, the new fields: ``cuff_gather`` (shorts), ``ankle_close`` (trousers), then ``collar_seat`` (needs
     every item built: the collar is laid on the layers under it).
``bind_to_body`` binds with ``garment/2`` (weights, collision, its correctives), then carries each seated collar by
the chest and adds its reach keys. Character-agnostic: every size comes from the spec, the rig or the body."""
import copy
import json

from garments import generator as GEN
from garments_v2 import core as V2

from . import ankle, collar, cuffs

GENERATOR = "garment/3"
PREVIOUS = V2.GENERATOR
# item type -> the garment/3 fields it accepts
ITEM_FIELDS = {"shorts": ("cuff_gather",), "trousers": ("ankle_close",), "top": ("collar_seat",),
               "shirt": ("collar_seat",), "dress": ("collar_seat",)}
V3_FIELDS = sorted({f for fs in ITEM_FIELDS.values() for f in fs})
SEAT_PROP = "ps_garment3_collar_seat"


def validate(clothing):
    """Validate a ``garment/3`` clothing block; returns it unchanged. Raises ValueError."""
    if not isinstance(clothing, dict) or clothing.get("generator") != GENERATOR:
        raise ValueError(f"clothing.generator must be {GENERATOR}")
    items = clothing.get("garments")
    names = [g.get("name", g.get("type")) for g in items if isinstance(g, dict)] if isinstance(items, list) else []
    for raw in items if isinstance(items, list) else []:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name", raw.get("type"))
        for f in V3_FIELDS:
            if f in raw and f not in ITEM_FIELDS.get(raw.get("type"), ()):
                allowed = sorted(t for t, fs in ITEM_FIELDS.items() if f in fs)
                raise ValueError(f"garment {name}.{f} ({GENERATOR}) is supported on {allowed}")
        if "cuff_gather" in raw:
            cuffs.validate(raw["cuff_gather"], name)
            bands = raw.get("bands")
            if not (raw.get("cuff") or bands is True or (isinstance(bands, dict) and bands.get("cuff"))):
                raise ValueError(f"garment {name}.cuff_gather needs the cuff bands (cuff / bands.cuff)")
        if "ankle_close" in raw:
            ankle.validate(raw["ankle_close"], name)
        if "collar_seat" in raw:
            collar.validate(raw["collar_seat"], name, names)
            c = raw.get("collar")
            if (c.get("type") if isinstance(c, dict) else c) != "round":
                raise ValueError(f"garment {name}.collar_seat needs a round collar")
    V2.validate(v2_view(clothing))
    return clothing


def v2_view(clothing):
    """The ``garment/2`` block ``garment/2`` builds from: the same block without the ``garment/3`` fields. A collar
    with ``collar_seat`` drops ``collar_clear`` (the seat replaces it: it lays the whole collar on the outer layers)."""
    out = copy.deepcopy(clothing)
    out["generator"] = PREVIOUS
    for raw in out.get("garments") or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("collar_seat") not in (None, False):
            raw.pop("collar_clear", None)
        for f in V3_FIELDS:
            raw.pop(f, None)
    return out


def build(C, body, clothing, P, H, J, G):
    """Build garments before rigging. Returns ``(objects, JSON-safe report)`` like ``garment/2``."""
    validate(clothing)
    objects, report = V2.build(C, body, v2_view(clothing), P, H, J, G)
    fit = GEN.BodyFit(P, H, J)
    lod = clothing.get("fibres_lod", "close")
    by_item = {}
    for ob in objects:
        by_item.setdefault(ob["ps_garment_item"], []).append(ob)
    ordered, v3_report, seats = [], {}, {}
    for raw in clothing["garments"]:
        cfg = GEN._merge(clothing.get("defaults"), raw)
        mine = by_item.get(cfg["name"], [])
        new, info = [], {}
        if cfg.get("cuff_gather") not in (None, False):
            info["cuff_gather"] = cuffs.gather(cfg, mine, body, fit)
        if cfg.get("ankle_close") not in (None, False):
            made, info["ankle_close"] = ankle.close(C, body, cfg, mine, H, G, fit)
            new += made
        if cfg.get("collar_seat") not in (None, False):
            seats[cfg["name"]] = cfg["collar_seat"]
        if new:
            fibres = V2._finish_new(new, cfg, lod, None, cfg.get("clean_fibres") or [])
            for entry in report["items"]:
                if entry["name"] == cfg["name"]:
                    entry["objects"] += [o.name for o in new]
                    entry["fibres"] += [{"object": f.name, "source": f[GEN.FIBRES_PROP],
                                         "preset": f["ps_material_preset"], "lod": f["ps_fibres_lod"]} for f in fibres]
        if info:
            v3_report[cfg["name"]] = info
        ordered += mine + new
    for raw in clothing["garments"]:  # collars last: they lie on every layer under them
        cfg = GEN._merge(clothing.get("defaults"), raw)
        if cfg["name"] in seats:
            v3_report.setdefault(cfg["name"], {})["collar_seat"] = collar.seat(cfg, ordered, body, P, H, fit)
    for ob in ordered:
        ob["ps_garment_generator"] = GENERATOR
    body[SEAT_PROP] = json.dumps(seats, sort_keys=True)
    report["generator"] = GENERATOR
    report["reuses"] = PREVIOUS
    report["objects"] = len(ordered)
    report["garment_3"] = v3_report
    return ordered, report


def bind_to_body(rig, body, garments, neighbours=1, max_influences=4, worn=None):
    """``garment/2`` binding for every piece, then each seated collar: carried by the chest (not by the head or the
    arm) and kept over the layers under it when an arm reaches."""
    out = V2.bind_to_body(rig, body, garments, neighbours=neighbours, max_influences=max_influences, worn=worn)
    seats = json.loads(body.get(SEAT_PROP, "{}") or "{}")
    if seats:
        out["collar_seat"] = {name: collar.bind(rig, garments, name, cfg, max_influences)
                              for name, cfg in sorted(seats.items())}
    return out
