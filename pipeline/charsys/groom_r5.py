"""Hair round 5 (`groom/4`, T-118): whorl rings with staggered petals and channels, staggered lock ends, turned flowers.

T-116 review (docs/audit/current_review/REVIEW.md, section 3): groom/3 hair still reads flatter and more regular than the
references. B05/val27 show locks that radiate from a whorl in overlapping tiers with dark channels between them and
tall crown petals of different heights; G04/ref_30 show curls that end at different heights and a flower that faces
the front quarter.

groom/4 keeps groom/3 (groom_r4.py, used read-only as a library) and adds three spec features. Each one is lowered to
plain groom/3 data before the build (`lower`), so a hair spec that uses none of them builds through groom/4 exactly
as through groom/3 (`lower` returns it unchanged). Character-independent: every count, angle and size is spec data.

spec.hair (generator "groom/4"): everything of groom/3 plus
  masses rows with "ring"   the row's roots lie on a circle around its whorl pole instead of on an az/el band:
              {"count", "pole": {"az", "el"}, "ring": {"radius_deg", "around": [b0, b1]}, "len_deg", "swirl_deg",
               "stagger": {"len": [..], "lift": [..], "width": [..], "radius_deg": [..]},
               "channel": {"gap": 0..0.8}, ...per-mass keys of groom/3}
              bearing 0 points from the pole to the face, +90 to the character's left; mass k of n sits at bearing
              b0 + (b1 - b0)(k + 0.5)/n, its root radius_deg from the pole, and runs len_deg straight away from the
              pole (tip bearing + swirl_deg). No random numbers: "stagger" lists repeat over the masses in order
              (factors for len_deg, lift and width; degrees added to radius_deg), so heights and lengths differ by
              design. "channel" keeps a gap between neighbours of the row: the width is limited to (1 - gap) of the
              mass's share of the circle at the end of its held width ("hold"), and its root narrows to its share at the
              root, so an open channel runs down from the whorl between every two masses.
  locks with "stagger"      {"z_end": [offsets in m], "end_scale": [factors], "mirror_shift": int}: the locks of the
              structure end at different heights (offset k is added to z_end of lock k, lists repeat; mirror_shift
              moves the right side along the list so the two sides differ). Each lock becomes its own structure
              "<name>_<kk>" (left) / "<name>_r<kk>" (right, mirrored structures) with the dynamics settings of
              <name>.
  accessories               one attachment rule for flowers and felt bows. Both sit on a bun (bun, around_deg,
              height_frac, out); a felt_bow can also sit on the scalp (az, el, out), and a flower item with "attach":
              {"az", "el", "out"} moves from the bun to that scalp point. "turn": {"toward": [az, el], "amount":
              0..1} (flower item or felt_bow structure) then turns the accessory about its seat from facing straight
              out towards that head direction.
Face keep-out, fibres, dynamics and binding are groom/3's."""
import copy
import math

try:
    from mathutils import Vector
except ImportError:  # plain Python: validation and lowering only
    Vector = None

import groom as G1  # groom/1 as a library (read-only use)
import groom_r4 as R4  # groom/3 as a library (read-only use)

GENERATOR_VERSIONS = ("groom/4",)
GENERATOR = "groom/4"
RING_KEYS = ("ring", "stagger", "channel", "swirl_deg")
NOMINAL_HEAD_RADIUS_M = 0.15  # used when lower() is called without a head (validation, plain tests)


# ------------------------------------------------------------------------------------------------- plain 3-vectors
def direction(az, el):
    a, e = math.radians(az), math.radians(el)
    return (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))


def az_el(d):
    return math.degrees(math.atan2(d[0], -d[1])), math.degrees(math.asin(max(-1.0, min(1.0, d[2]))))


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def ring_frame(pole):
    """(p, u, v): the pole direction, the tangent towards the face (bearing 0) and towards the left (+90)."""
    p = direction(float(pole["az"]), float(pole["el"]))
    f = (0.0, -1.0, 0.0)
    k = sum(a * b for a, b in zip(f, p))
    u = tuple(a - b * k for a, b in zip(f, p))
    if sum(c * c for c in u) < 1e-8:  # pole on the face axis: use straight up as bearing 0
        u = (0.0, 0.0, 1.0)
    u = _norm(u)
    return p, u, _cross(p, u)


def ring_dir(frame, radius_deg, bearing_deg):
    p, u, v = frame
    r, b = math.radians(radius_deg), math.radians(bearing_deg)
    return _norm(tuple(math.cos(r) * p[i] + math.sin(r) * (math.cos(b) * u[i] + math.sin(b) * v[i]) for i in range(3)))


def _cyc(seq, k, default):
    return float(seq[k % len(seq)]) if seq else default


def _mid(v):
    return (float(v[0]) + float(v[1])) / 2 if isinstance(v, (list, tuple)) else float(v)


# -------------------------------------------------------------------------------------------------------- lowering
def ring_items(row, head_radius_m):
    """The explicit groom/3 masses of one ring row, and what the channel rule did: (items, info)."""
    n = int(row["count"])
    ring = row["ring"]
    b0, b1 = [float(x) for x in ring.get("around", [-180, 180])]
    frame = ring_frame(row.get("pole", {"az": 180, "el": 70}))
    stg = row.get("stagger") or {}
    gap = (row.get("channel") or {}).get("gap")
    hold = float(row.get("hold", 0.45))
    slot = math.radians(abs(b1 - b0) / n)
    keep = {k: v for k, v in row.items() if k not in RING_KEYS + ("count", "pole", "len_deg", "az", "az_list", "el",
                                                                "flow", "jitter_deg")}
    items, gaps = [], []
    for k in range(n):
        bearing = b0 + (b1 - b0) * (k + 0.5) / n
        r = float(ring["radius_deg"]) + _cyc(stg.get("radius_deg"), k, 0.0)
        L = _mid(row["len_deg"]) * _cyc(stg.get("len"), k, 1.0)
        width = _mid(row.get("width", 0.08)) * _cyc(stg.get("width"), k, 1.0)
        it = dict(keep)
        if gap is not None:
            g = float(gap)
            full = head_radius_m * math.sin(math.radians(min(90.0, r + L * hold))) * slot
            width = min(width, full * (1 - g))
            at_root = head_radius_m * math.sin(math.radians(min(90.0, max(r, 1.0)))) * slot * (1 - g)
            it["root_width"] = round(max(0.15, min(1.0, at_root / width)), 4)
            gaps.append(full - width)
        fl = _cyc(stg.get("lift"), k, 1.0)
        if "lift" in row:
            lift = [float(x) for x in row["lift"]]
            it["lift"] = [round(lift[0], 5)] + [round(x * fl, 5) for x in lift[1:]]
        a0, e0 = az_el(ring_dir(frame, r, bearing))
        a1, e1 = az_el(ring_dir(frame, r + L, bearing + float(row.get("swirl_deg", 0.0))))
        it.update(root=[round(a0, 4), round(e0, 4)], tip=[round(a1, 4), round(e1, 4)], width=round(width, 5))
        items.append(it)
    info = {"masses": n}
    if gaps:
        info["channel_min_gap_m"] = round(min(gaps), 4)
    return items, info


def _lower_masses(st, head_radius_m, info):
    rows = st.get("rows") or []
    if not any("ring" in r for r in rows):
        return st
    out = dict(st, items=list(st.get("items") or []), rows=[])
    for r in rows:
        if "ring" in r:
            items, i = ring_items(r, head_radius_m)
            out["items"] += items
            info.setdefault(st.get("name", "masses"), []).append(i)
        else:
            out["rows"].append(r)
    if not out["rows"]:
        del out["rows"]
    return out


def lock_names(st):
    """[(name, side, k)] of the single-lock structures a staggered locks structure is lowered to."""
    sides = (1, -1) if st.get("mirror") else (1,)
    base = st.get("name", "locks")
    return [(f"{base}_{'r' if sx < 0 else ''}{k:02d}", sx, k) for sx in sides for k in range(int(st["count"]))]


def _lower_locks(st):
    stg = st.get("stagger")
    if not stg:
        return [st]
    cnt = int(st["count"])
    a0, a1 = [float(x) for x in st["az"]]
    out = []
    for name, sx, k in lock_names(st):
        j = k + (int(stg.get("mirror_shift", 0)) if sx < 0 else 0)
        lo, hi = a0 + (a1 - a0) * k / cnt, a0 + (a1 - a0) * (k + 1) / cnt
        s = {x: copy.deepcopy(v) for x, v in st.items() if x not in ("stagger", "mirror")}
        dz = _cyc(stg.get("z_end"), j, 0.0)
        z = st["z_end"]
        s.update(name=name, count=1, az=[sx * lo, sx * hi],
                 z_end=[round(float(x) + dz, 5) for x in z] if isinstance(z, (list, tuple)) else round(float(z) + dz, 5))
        if stg.get("end_scale"):
            s["end_scale"] = round(float(st.get("end_scale", 0.85)) * _cyc(stg["end_scale"], j, 1.0), 5)
        if s.get("curl") and s["curl"].get("direction", "alternate") == "alternate":  # as the unlowered structure
            s["curl"]["direction"] = "ccw" if (k + (sx < 0)) % 2 == 0 else "cw"
        out.append(s)
    return out


def lower(hair_spec, head_radius_m=NOMINAL_HEAD_RADIUS_M):
    """The groom/3 form of a groom/4 hair spec and a report of what was lowered: (spec, info). A spec without
    groom/4 features is returned as it is (the same object), so its build is groom/3's."""
    sts = hair_spec.get("structures")
    if not isinstance(sts, list):
        return hair_spec, {}
    info, out, renamed = {}, [], {}
    for s in sts:
        if s.get("type") == "masses":
            out.append(_lower_masses(s, head_radius_m, info))
        elif s.get("type") == "locks" and s.get("stagger"):
            subs = _lower_locks(s)
            renamed[s.get("name", "locks")] = [x["name"] for x in subs]
            out += subs
        else:
            out.append(s)
    if all(a is b for a, b in zip(out, sts)) and len(out) == len(sts):
        return hair_spec, {}
    low = dict(hair_spec, structures=out)
    dyn = hair_spec.get("dynamics")
    if renamed:
        info["staggered_locks"] = {k: len(v) for k, v in renamed.items()}
        if isinstance(dyn, dict) and isinstance(dyn.get("structures"), dict):
            ds = {}
            for name, cfg in dyn["structures"].items():
                for n in renamed.get(name, [name]):
                    ds[n] = cfg
            low["dynamics"] = dict(dyn, structures=ds)
    return low, info


# ------------------------------------------------------------------------------------------------------ validation
def validate(hair_spec):
    """Errors in a groom/4 hair spec: the groom/4 keys, then the groom/3 rules on the lowered spec."""
    sts = hair_spec.get("structures")
    if not isinstance(sts, list) or not sts:
        return ["hair.structures must be a non-empty list"]
    errs = []
    for i, s in enumerate(sts):
        t = s.get("type")
        where = f"hair.structures[{i}]"
        if t == "masses":
            for j, row in enumerate(s.get("rows") or []):
                w = f"{where}.rows[{j}]"
                if "ring" not in row:
                    if any(k in row for k in ("stagger", "channel", "swirl_deg")):
                        errs.append(f"{w}: stagger, channel and swirl_deg need 'ring'")
                    continue
                ring = row["ring"]
                if not isinstance(ring, dict) or "radius_deg" not in ring:
                    errs.append(f"{w}.ring must be {{\"radius_deg\", \"around\": [b0, b1]}}")
                    continue
                if not 0.0 <= float(ring["radius_deg"]) <= 120.0:
                    errs.append(f"{w}.ring.radius_deg must be within 0..120")
                ar = ring.get("around", [-180, 180])
                if not (isinstance(ar, list) and len(ar) == 2 and 0 < abs(float(ar[1]) - float(ar[0])) <= 360):
                    errs.append(f"{w}.ring.around must be [b0, b1] spanning at most 360 degrees")
                for k in ("count", "len_deg"):
                    if k not in row:
                        errs.append(f"{w} (ring) needs '{k}'")
                if int(row.get("count", 1)) < 1:
                    errs.append(f"{w} (ring) count must be at least 1")
                stg = row.get("stagger", {})
                if not isinstance(stg, dict) or any(k not in ("len", "lift", "width", "radius_deg") or not
                                                    (isinstance(v, list) and v) for k, v in stg.items()):
                    errs.append(f"{w}.stagger must hold non-empty lists under len, lift, width, radius_deg")
                elif any(float(x) <= 0 for k in ("len", "lift", "width") for x in stg.get(k, [])):
                    errs.append(f"{w}.stagger factors must be positive")
                ch = row.get("channel")
                if ch is not None and not (isinstance(ch, dict) and 0.0 <= float(ch.get("gap", -1)) <= 0.8):
                    errs.append(f"{w}.channel must be {{\"gap\": 0..0.8}}")
        elif t == "locks" and s.get("stagger") is not None:
            stg = s["stagger"]
            if not isinstance(stg, dict) or any(k not in ("z_end", "end_scale", "mirror_shift") for k in stg) or not \
                    all(isinstance(stg.get(k, [0]), list) and stg.get(k, [0]) for k in ("z_end", "end_scale")):
                errs.append(f"{where}.stagger must be {{\"z_end\": [m, ..], \"end_scale\": [factor, ..], "
                            f"\"mirror_shift\": int}}")
            elif any(float(x) <= 0 for x in stg.get("end_scale", [])):
                errs.append(f"{where}.stagger.end_scale factors must be positive")
            elif not all(k in s for k in ("count", "az", "z_end")):
                errs.append(f"{where} (staggered locks) needs count, az and z_end")
        elif t in ("flowers", "felt_bow"):
            for j, it in enumerate((s.get("items") or []) if t == "flowers" else [s]):
                w = f"{where}.items[{j}]" if t == "flowers" else where
                tn = it.get("turn")
                if tn is not None and not (isinstance(tn, dict) and isinstance(tn.get("toward"), list)
                                           and len(tn["toward"]) == 2 and 0.0 <= float(tn.get("amount", 1.0)) <= 1.0):
                    errs.append(f"{w}.turn must be {{\"toward\": [az, el], \"amount\": 0..1}}")
                at = it.get("attach") if t == "flowers" else None
                if at is not None and not (isinstance(at, dict) and "az" in at and "el" in at):
                    errs.append(f"{w}.attach must be {{\"az\", \"el\", \"out\"}}")
    if errs:
        return errs
    return R4.validate(lower(hair_spec)[0])


# ----------------------------------------------------------------------------------------------------- accessories
def _seat(ctx, st, it):
    """The attachment point of an accessory as its builder placed it: (point, outward direction). On a bun
    (bun, around_deg, height_frac, out) or, for a felt_bow without "bun", on the scalp (az, el, out)."""
    if st["type"] == "felt_bow" and "bun" not in st:
        return ctx["scalp"].at(float(st["az"]), float(st["el"]), float(st.get("out", 0.008)))
    hf, out = (0.15, 0.006) if st["type"] == "felt_bow" else (0.2, 0.0)
    c, radial, _ = G1._bun_point(ctx, st, float(it.get("around_deg", 0)), float(it.get("height_frac", hf)),
                                 float(it.get("out", out)))
    return c, radial


def place_accessories(hair_spec, head, frame, objs):
    """The shared attachment rule of flowers and felt bows: a flower item with "attach" moves rigidly from its bun
    seat to the scalp point; "turn" then rotates the accessory about its seat. Returns what was done."""
    sts = hair_spec["structures"]
    todo = [s for s in sts if (s.get("type") == "flowers" and any(it.get("turn") or it.get("attach") for it in
                                                                   s["items"])) or (s.get("type") == "felt_bow" and s.get("turn"))]
    if not todo:
        return {}
    scalp = G1.Scalp(head, frame["centre"], frame["radii"], float(hair_spec.get("scalp_offset_m", 0.008)))
    ctx = {"scalp": scalp, "buns": []}
    for s in sts:
        if s["type"] == "bun":
            ctx["buns"] += G1.bun_frames(s, ctx)
    by_name = {o.name: o for o in objs}
    done = {}
    for s in todo:
        name = s.get("name", s["type"])
        flowers = s["type"] == "flowers"
        items = s["items"] if flowers else [s]
        for j, it in enumerate(items):
            tn, at = it.get("turn"), it.get("attach") if flowers else None
            if not (tn or at):
                continue
            c, n = _seat(ctx, s, it)
            moves = []  # (rotation about `about`, then the seat moves to `to`)
            if at:
                c1, n1 = scalp.at(float(at["az"]), float(at["el"]), float(at.get("out", 0.006)))
                moves.append((n.rotation_difference(n1), c, c1))
                c, n = c1, n1
            if tn:
                target = G1.Scalp.direction(float(tn["toward"][0]), float(tn["toward"][1]))
                q = n.rotation_difference(G1.slerp(n, target, float(tn.get("amount", 1.0))))
                moves.append((q, c, c))
                done.setdefault("turned_deg", {})[f"{name}.{j}" if flowers else name] = round(math.degrees(q.angle), 2)
            if at:
                done.setdefault("attached", []).append(f"{name}.{j}")
            for part in (("petals", "centres") if flowers else (None,)):
                me = by_name[f"hair_{name}_{part}" if part else f"hair_{name}"].data
                per = len(me.vertices) // len(items)
                for v in me.vertices[j * per:(j + 1) * per]:
                    for q, about, to in moves:
                        v.co = to + q @ (v.co - about)
                me.update()
    return done


# ------------------------------------------------------------------------------------------------------------ build
def build(C, head, frame, hair_spec, material, face_y, fibres=None):
    """As groom_r4.build (same arguments and return value), for groom/4 specs."""
    errs = validate(hair_spec)
    if errs:
        raise SystemExit("groom/4: " + "; ".join(errs))
    low, info = lower(hair_spec, sum(float(x) for x in frame["radii"]) / 3)
    objs, rep = R4.build(C, head, frame, low, material, face_y, fibres)
    placed = place_accessories(hair_spec, head, frame, objs)
    if placed:
        info["accessories"] = placed
    rep["generator"] = GENERATOR
    rep["lowered"] = info
    return objs, rep


def bind(rig, objs, head_bone, chest_bone, binding):
    """As groom.bind."""
    G1.bind(rig, objs, head_bone, chest_bone, binding)
