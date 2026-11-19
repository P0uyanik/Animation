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
              "phase_deg": [..] (T-126, style "wavy" only) sets the S-wave phase of every lock by design instead
              of by a random draw (list repeats over the locks; equal phases = neighbours wave together, a step
              per lock = the wave runs across the row; the mirrored side adds 180 so both sides mirror). groom/4
              then lays the wave itself on the built lock (the lock is built straight): amplitude and wavelength
              from "wave", plus "wave.depth" (0..1: front-back share, a rounder S), "wave.ramp_m" (length over
              which the wave fades in, default one wavelength), "wave.start_m" (where it starts, in metres below
              the point where the lock leaves the scalp; negative = already on the head, default 0) and "wave.tip_gain" (amplitude
              factor reached at the tip, default 1).
  accessories               one attachment rule for flowers and felt bows. Both sit on a bun (bun, around_deg,
              height_frac, out); a felt_bow can also sit on the scalp (az, el, out), and a flower item with "attach":
              {"az", "el", "out"} moves from the bun to that scalp point. "turn": {"toward": [az, el], "amount":
              0..1} (flower item or felt_bow structure) then turns the accessory about its seat from facing straight
              out towards that head direction. "seat": "hair" (T-126; flower item or felt_bow structure) seats the
              accessory on the built hair surface instead of the scalp or bun: a ray along the seat's outward
              direction finds the outermost hair surface there and "out" is then measured from that surface, so an
              accessory on thick hair is not buried and needs no hand-set offset.
Face keep-out, fibres, dynamics and binding are groom/3's."""
import copy
import math

try:
    from mathutils import Quaternion, Vector
except ImportError:  # plain Python: validation and lowering only
    Quaternion = Vector = None

import groom as G1  # groom/1 as a library (read-only use)
import groom_r4 as R4  # groom/3 as a library (read-only use)

GENERATOR_VERSIONS = ("groom/4",)
GENERATOR = "groom/4"
RING_KEYS = ("ring", "stagger", "channel", "swirl_deg")
WAVE_KEY = "_wave"  # on a lowered single lock: the designed wave that apply_waves lays on it
SEATS = ("hair",)
ACCESSORY_TYPES = ("flowers", "felt_bow", "bow", "tie", "scrunchie")
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
        if stg.get("phase_deg"):  # the lock is built straight; apply_waves lays the designed wave on it
            wv = st.get("wave") or {}
            s["wave"] = dict(wv, amplitude=0.0)
            s[WAVE_KEY] = {"amplitude": float(wv.get("amplitude", 0.0)), "wavelength": float(wv.get("wavelength", 0.1)),
                           "phase_deg": round((_cyc(stg["phase_deg"], j, 0.0) + (180.0 if sx < 0 else 0.0)) % 360.0, 4),
                           "depth": float(wv.get("depth", 0.0)), "tip_gain": float(wv.get("tip_gain", 1.0)),
                           "ramp_m": float(wv.get("ramp_m", wv.get("wavelength", 0.1))),
                           "start_m": float(wv.get("start_m", 0.0))}
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
            if not isinstance(stg, dict) or any(k not in ("z_end", "end_scale", "mirror_shift", "phase_deg")
                                                for k in stg) or not \
                    all(isinstance(stg.get(k, [0]), list) and stg.get(k, [0]) for k in ("z_end", "end_scale",
                                                                                         "phase_deg")):
                errs.append(f"{where}.stagger must be {{\"z_end\": [m, ..], \"end_scale\": [factor, ..], "
                            f"\"phase_deg\": [deg, ..], \"mirror_shift\": int}}")
            elif "phase_deg" in stg and not (s.get("style") == "wavy" and isinstance(s.get("wave"), dict)
                                             and float(s["wave"].get("wavelength", 0)) > 0
                                             and 0.0 <= float(s["wave"].get("depth", 0.0)) <= 1.0
                                             and float(s["wave"].get("tip_gain", 1.0)) >= 0.0
                                             and float(s["wave"].get("ramp_m", 1.0)) > 0.0):
                errs.append(f"{where}.stagger.phase_deg needs style \"wavy\" and wave {{amplitude, wavelength > 0, "
                            f"depth 0..1, tip_gain >= 0, ramp_m > 0}}")
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
                if it.get("seat") is not None and it["seat"] not in SEATS:
                    errs.append(f"{w}.seat must be one of {list(SEATS)}")
                at = it.get("attach") if t == "flowers" else None
                if at is not None and not (isinstance(at, dict) and "az" in at and "el" in at):
                    errs.append(f"{w}.attach must be {{\"az\", \"el\", \"out\"}}")
    if errs:
        return errs
    return R4.validate(lower(hair_spec)[0])


# ----------------------------------------------------------------------------------------------------- wave phase
def apply_waves(low, head, frame, objs):
    """Lays the designed S-wave on every lowered lock that carries one (stagger.phase_deg): the built, straight lock
    is moved sideways (and by "depth" front-back) as a function of the hanging length below the point where it
    leaves the scalp. Vertex counts, order and heights do not change (dynamics records and binding stay valid)."""
    jobs = [s for s in low["structures"] if s.get(WAVE_KEY)]
    if not jobs:
        return {}
    scalp = G1.Scalp(head, frame["centre"], frame["radii"], float(low.get("scalp_offset_m", 0.008)))
    by_name = {o.name: o for o in objs}
    done = {}
    for s in jobs:
        w = s[WAVE_KEY]
        me = by_name[f"hair_{s['name']}"].data
        n = max(1, len(me.vertices))
        mid = sum((v.co for v in me.vertices), Vector()) / n - scalp.centre
        az = math.atan2(mid.x, -mid.y)
        hdir = Vector((math.sin(az), -math.cos(az), 0.0))
        tang = Vector((0, 0, 1)).cross(hdir)
        z0 = scalp.at(math.degrees(az), float(s.get("el_leave", -10)), float(s.get("lift", [0.004, 0.02])[1]))[0].z
        z0 -= w["start_m"]
        L = max(1e-6, z0 - min(v.co.z for v in me.vertices))
        ph, k = math.radians(w["phase_deg"]), 2 * math.pi / w["wavelength"]
        for v in me.vertices:
            u = max(0.0, z0 - v.co.z)
            a = w["amplitude"] * min(1.0, u / w["ramp_m"]) * (1 + (w["tip_gain"] - 1) * u / L)
            v.co += tang * (a * math.sin(ph + k * u)) + hdir * (a * w["depth"] * math.cos(ph + k * u))
        me.update()
        done[s["name"]] = w["phase_deg"]
    return done


class _Deferred:
    """Collects the fibre requests of a build so the fibres are grown after the wave is laid on the locks."""

    def __init__(self):
        self.calls = []

    def __call__(self, ob, slot, overrides):
        self.calls.append((ob, slot))
        return None


def _grow_fibres(low, calls, fibres, rep):
    """The fibre step of groom_r4.build, on the final geometry (same layers, order and post steps)."""
    fb = low["fibres"]
    layers = fb.get("layers", [{}])
    dr = fb.get("directional") or {}
    comb = float(dr.get("strength", 0.8)) if dr.get("enabled") else 0.0
    made = []
    for (ob, slot), layer in zip(calls, [l for _ in range(len(calls) // max(1, len(layers))) for l in layers]):
        fo = fibres(ob, slot, layer.get("overrides") or {})
        if fo is not None:
            if layer.get("shaft_radius_mm"):
                R4.H.fixed_shaft(fo, float(layer["shaft_radius_mm"]) / 1000.0, float(layer.get("tip_ratio", 0.35)))
            if comb and R4.COMB_ATTR in ob.data.attributes:
                R4.comb_fibres(fo, ob, comb)
            fo.parent = ob
            fo.matrix_parent_inverse = ob.matrix_world.inverted()
            fo["ps_groom_fibres"] = layer.get("name", "fibres")
            made.append(fo.name)
    rep["fibres"] = dict(rep.get("fibres") or {}, objects=len(made))


# ----------------------------------------------------------------------------------------------------- accessories
def hair_surface(sts, objs):
    """BVH trees of the built hair without the accessories (world coordinates)."""
    from mathutils.bvhtree import BVHTree
    skip = set()
    for s in sts:
        if s.get("type") in ACCESSORY_TYPES:
            base = f"hair_{s.get('name', s['type'])}"
            skip |= {base, base + "_petals", base + "_centres"}
    trees = []
    for o in objs:
        if o.name in skip or o.type != "MESH" or not o.data.polygons:
            continue
        mw = o.matrix_world
        trees.append(BVHTree.FromPolygons([mw @ v.co for v in o.data.vertices],
                                          [tuple(p.vertices) for p in o.data.polygons]))
    return trees


def surface_hit(trees, c, n, reach=0.3):
    """The outermost point of the hair surface on the line through seat c along its outward direction n."""
    best = None
    start = c + n * reach
    for t in trees:
        hit, _, _, dist = t.ray_cast(start, -n, 2 * reach)
        if hit is not None and (best is None or dist < best[1]):
            best = (hit, dist)
    return best[0] if best else None


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
    todo = [s for s in sts if (s.get("type") == "flowers" and any(it.get("turn") or it.get("attach") or it.get("seat")
                                                                   for it in s["items"]))
            or (s.get("type") == "felt_bow" and (s.get("turn") or s.get("seat")))]
    if not todo:
        return {}
    scalp = G1.Scalp(head, frame["centre"], frame["radii"], float(hair_spec.get("scalp_offset_m", 0.008)))
    ctx = {"scalp": scalp, "buns": []}
    for s in sts:
        if s["type"] == "bun":
            ctx["buns"] += G1.bun_frames(s, ctx)
    by_name = {o.name: o for o in objs}
    done = {}
    surface = None  # the built hair (no accessories), made on first use
    for s in todo:
        name = s.get("name", s["type"])
        flowers = s["type"] == "flowers"
        items = s["items"] if flowers else [s]
        for j, it in enumerate(items):
            tn, at = it.get("turn"), it.get("attach") if flowers else None
            if not (tn or at or it.get("seat")):
                continue
            c, n = _seat(ctx, s, it)
            moves = []  # (rotation about `about`, then the seat moves to `to`)
            if at:
                c1, n1 = scalp.at(float(at["az"]), float(at["el"]), float(at.get("out", 0.006)))
                moves.append((n.rotation_difference(n1), c, c1))
                c, n = c1, n1
            if it.get("seat"):
                if surface is None:
                    surface = hair_surface(sts, objs)
                out = float(it.get("out", (at or {}).get("out", 0.006 if at or not flowers else 0.0)))
                hit = surface_hit(surface, c, n)
                if hit is not None:
                    c1 = hit + n * out
                    moves.append((Quaternion(), c, c1))
                    done.setdefault("seated_lift_m", {})[f"{name}.{j}" if flowers else name] = round((c1 - c).dot(n), 4)
                    c = c1
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
    waved = any(s.get(WAVE_KEY) for s in low["structures"])
    later = _Deferred() if waved and fibres is not None else None  # fibres grow on the final (waved) geometry
    objs, rep = R4.build(C, head, frame, low, material, face_y, later or fibres)
    if waved:
        info["wave_phase_deg"] = apply_waves(low, head, frame, objs)
        if later and later.calls:
            _grow_fibres(low, later.calls, fibres, rep)
    placed = place_accessories(hair_spec, head, frame, objs)
    if placed:
        info["accessories"] = placed
    rep["generator"] = GENERATOR
    rep["lowered"] = info
    return objs, rep


def bind(rig, objs, head_bone, chest_bone, binding):
    """As groom.bind."""
    G1.bind(rig, objs, head_bone, chest_bone, binding)
