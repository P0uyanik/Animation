"""Shared clip retargeting maths (pure Python, no Blender): the same rules as the engine (engine/model/clip.cpp).

- reference_pose(profile): the rig profile's "reference_pose" block, '.L' roles mirrored to '.R', semantic parents
  first.
- derive(heads, ref): a character's retarget data from its role pivots (engine axes): per role the rest direction,
  twist reference and segment length, plus height (head-role pivot) and leg length (thigh -> shin -> foot).
  export_engine.py writes it into every package ("retarget" block); the engine derives the same numbers for
  packages without the block.
- Quaternion helpers (w, x, y, z) and frame(dir, twist) for the clip exporter and the measurement tools.
No character names, dimensions or data live here."""
import math

RETARGET_VERSION = 1


def _v(a):
    return [float(a[0]), float(a[1]), float(a[2])]


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    n = length(a)
    return [a[0] / n, a[1] / n, a[2] / n]


def perpendicular(d, hint):
    for h in (hint, [0, 1, 0], [1, 0, 0], [0, 0, 1]):
        t = sub(h, [d[0] * dot(h, d), d[1] * dot(h, d), d[2] * dot(h, d)])
        if length(t) > 1e-3:
            return normalize(t)
    return [0.0, 0.0, 1.0]


def _mirror_name(n, l, r):
    if n.endswith(l):
        return n[: -len(l)] + r
    if n.endswith(r):
        return n[: -len(r)] + l
    return n


def reference_pose(block):
    """Expanded reference roles: list of dicts with name, parent, end, end_dir, continue, fallback, twist_from,
    twist_hint, ref_dir, ref_twist (semantic parents first)."""
    if block.get("version") != 1:
        raise ValueError("reference_pose: unsupported version")
    l, r = block.get("mirror", {}).get("suffix", [".L", ".R"])
    roles = block["roles"]
    out = []

    def parse(name, e, mirror):
        mn = (lambda s: _mirror_name(s, l, r)) if mirror else (lambda s: s)
        mv = (lambda v: [-v[0], v[1], v[2]]) if mirror else (lambda v: list(v))
        ref_dir = normalize(mv(e.get("ref_dir", [0, 1, 0])))
        return {"name": mn(name), "parent": mn(e["parent"]) if e.get("parent") else "",
                "end": mn(e["end"]) if e.get("end") else "", "end_dir": mv(e["end_dir"]) if e.get("end_dir") else None,
                "continue": bool(e.get("continue")), "fallback": bool(e.get("end_fallback_dir_from_parent")),
                "twist_from": [mn(x) for x in e["twist_from"]] if e.get("twist_from") else None,
                "twist_hint": mv(e.get("twist_hint", [0, 0, 1])), "ref_dir": ref_dir,
                "ref_twist": perpendicular(ref_dir, mv(e.get("ref_twist", [0, 0, 1])))}
    for k, e in roles.items():
        out.append(parse(k, e, False))
    for k, e in roles.items():
        if k.endswith(l) and _mirror_name(k, l, r) not in roles:
            out.append(parse(k, e, True))
    known = {x["name"] for x in out}
    ordered, placed = [], set()
    while len(ordered) < len(out):
        progress = False
        for x in out:
            if x["name"] not in placed and (not x["parent"] or x["parent"] not in known or x["parent"] in placed):
                ordered.append(x)
                placed.add(x["name"])
                progress = True
        if not progress:
            raise ValueError("reference_pose: cyclic parents")
    return ordered


def derive(heads, ref):
    """heads: {role or bone name: [x, y, z] engine axes}. Same rules as deriveRetarget in engine/model/clip.cpp."""
    roles = {}
    for rr in ref:
        if rr["name"] not in heads:
            continue
        h = _v(heads[rr["name"]])
        d = None
        ln = 0.0
        if rr["end"] and rr["end"] in heads and length(sub(_v(heads[rr["end"]]), h)) > 1e-6:
            e = sub(_v(heads[rr["end"]]), h)
            d, ln = normalize(e), length(e)
        elif rr["end_dir"] and length(rr["end_dir"]) > 0:
            d = normalize(rr["end_dir"])
        elif rr["continue"] and rr["parent"] in heads and length(sub(h, _v(heads[rr["parent"]]))) > 1e-6:
            e = sub(h, _v(heads[rr["parent"]]))
            d, ln = normalize(e), length(e)
        elif rr["fallback"] and rr["parent"] in roles:
            d = roles[rr["parent"]]["dir"]
        if d is None:
            continue
        hint = rr["twist_hint"]
        tf = rr["twist_from"]
        if tf and tf[0] in heads and tf[1] in heads and length(sub(_v(heads[tf[0]]), _v(heads[tf[1]]))) > 1e-6:
            hint = sub(_v(heads[tf[0]]), _v(heads[tf[1]]))
        roles[rr["name"]] = {"dir": [round(x, 7) for x in d], "twist": [round(x, 7) for x in perpendicular(d, hint)],
                             "length": round(ln, 7)}
    leg = 0.0
    for s in (".L", ".R"):
        t, k, f = heads.get("thigh" + s), heads.get("shin" + s), heads.get("foot" + s)
        if t and k and f:
            leg = length(sub(_v(k), _v(t))) + length(sub(_v(f), _v(k)))
            break
    return {"version": RETARGET_VERSION, "reference_version": 1, "roles": roles,
            "height": round(float(heads["head"][1]), 7) if "head" in heads else 0.0, "leg_length": round(leg, 7)}


# ------------------------------------------------------------------ quaternions (w, x, y, z)
def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return [aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw]


def qconj(q):
    return [q[0], -q[1], -q[2], -q[3]]


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


def qrot(q, v):
    p = qmul(qmul(q, [0.0] + list(v)), qconj(q))
    return p[1:]


def qangle_deg(a, b):
    d = abs(sum(x * y for x, y in zip(qnorm(a), qnorm(b))))
    return math.degrees(2 * math.acos(min(1.0, d)))


def quat_from_matrix(m):
    """m: 3x3 rows; returns a unit quaternion (w, x, y, z)."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = [0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s]
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = [(m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s]
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = [(m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s]
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = [(m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s]
    q = qnorm(q)
    return q if q[0] >= 0 else [-c for c in q]


def frame(d, t):
    """Rotation of the frame (x = d x t, y = d, z = t) as a quaternion."""
    y = normalize(d)
    z = perpendicular(y, t)
    x = cross(y, z)
    return quat_from_matrix([[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]])
