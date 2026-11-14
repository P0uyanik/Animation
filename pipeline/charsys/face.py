"""charsys face modules (selected by spec.face; the defaults keep the v6 behaviour of body_v6.add_expression_keys).

spec.face.blink = {"generator": "lid_seam/1", "overlap_deg": 3, "closed_offset_m": 0.0012}
  Replaces the v6 Blink key (a fixed 62 deg rotation that overshoots the lower lid, so the closed upper lid became a
  skin-coloured ball over the eye; measured: lid edge at about -5 deg, lower-lid edge at about -48 deg). The closing
  angle is computed from the lid meshes so the upper-lid edge meets the lower-lid edge (+ overlap); the closed lid
  is pulled in to closed_offset_m above the eyeball; the lash rotates with the lid and lands on the seam (the dark
  closed-eye line).
spec.face.smile = {"generator": "corner_lift/1", "corner_up_m": 0.007, "widen": 1.12}
  Replaces the v6 Smile key on the mouth patch with a stronger corner lift and slight widening."""
import math

from mathutils import Matrix, Vector


def _front_edge_elevation(ob, c, r, lowest):
    """Elevation (deg) of the lid's free edge at the front: the lowest (upper lid) or highest (lower lid) vertex
    among the vertices in front of the eye centre close to the middle (|x - c.x| < 0.25 r)."""
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    pts = [p for p in pts if (p.y - c.y) < -0.5 * r and abs(p.x - c.x) < 0.25 * r]
    p = min(pts, key=lambda q: q.z) if lowest else max(pts, key=lambda q: q.z)
    d = p - c
    return math.degrees(math.atan2(d.z, -d.y))


def add_blink_lid_seam(lids, eye_r, G, cfg):
    overlap = float(cfg.get("overlap_deg", 3.0))
    closed_off = float(cfg.get("closed_offset_m", 0.0012))
    report = []
    for up, lo, lash, c in lids:
        for ob in (up, lo, lash):
            if ob.modifiers:
                G.apply_mods(ob)
        e_up = _front_edge_elevation(up, c, eye_r, lowest=True)
        e_lo = _front_edge_elevation(lo, c, eye_r, lowest=False)
        ang = (e_up - e_lo) + overlap
        R = Matrix.Rotation(math.radians(ang), 3, Vector((1, 0, 0)))
        r_in = min((v.co - c).length for v in up.data.vertices)  # inner shell radius (eye_r + gap)
        for ob in (up, lash):
            if ob.data.shape_keys is None:
                ob.shape_key_add(name="Basis")
            k = ob.shape_key_add(name="Blink")
            k.value = 0.0
            for i, v in enumerate(ob.data.vertices):
                d = R @ (v.co - c)
                if ob is up:  # pull the closed shell towards the eyeball, keeping its thickness
                    L = d.length
                    d = d * ((eye_r + closed_off + (L - r_in)) / L)
                k.data[i].co = c + d
        report.append({"lid": up.name, "edge_upper_deg": round(e_up, 1), "edge_lower_deg": round(e_lo, 1),
                       "close_deg": round(ang, 1)})
    return report


def add_brow_down(brows):
    """The v6 BrowDown key (unchanged)."""
    for b in brows:
        b.shape_key_add(name="Basis")
        k = b.shape_key_add(name="BrowDown")
        k.value = 0.0
        xs = [abs(v.co.x) for v in b.data.vertices]
        x0, x1 = min(xs), max(xs)
        for i, v in enumerate(b.data.vertices):
            inner = 1 - (abs(v.co.x) - x0) / max(1e-6, x1 - x0)
            k.data[i].co = v.co + Vector((-math.copysign(0.004, v.co.x) * inner, -0.001, -0.009 * inner - 0.002))


def strengthen_smile(mouth, head, B, cfg):
    """Rebuilds the mouth's Smile key: corners up by corner_up_m (parabolic across the width), widened by `widen`,
    following the face surface."""
    up = float(cfg.get("corner_up_m", 0.007))
    widen = float(cfg.get("widen", 1.12))
    k = mouth.data.shape_keys.key_blocks["Smile"]
    base = mouth.data.shape_keys.key_blocks["Basis"]
    xs = [p.co.x for p in base.data]
    w = max(abs(x) for x in xs)
    for i, p in enumerate(base.data):
        x, z = p.co.x * widen, p.co.z
        u = p.co.x / w
        z = z + up * u * u + 0.0035 * u * u  # +0.0035 cancels the neutral frown at the corners
        k.data[i].co = Vector((x, B.face_y(head, x, z) - 0.0012, z))
    return {"corner_up_m": up, "widen": widen}


def add_expression_keys(lids, brows, mouth, head, B, face_spec):
    """Dispatch: v6 keys by default; lid_seam/1 Blink and corner_lift/1 Smile when the spec asks for them."""
    blink = (face_spec or {}).get("blink", {})
    smile = (face_spec or {}).get("smile", {})
    rep = {}
    if blink.get("generator", "v6") == "lid_seam/1":
        rep["blink"] = add_blink_lid_seam(lids, B.EYE_R, B.G, blink)
        add_brow_down(brows)
    else:
        B.add_expression_keys(lids, brows)
    if smile.get("generator", "v6") == "corner_lift/1":
        rep["smile"] = strengthen_smile(mouth, head, B, smile)
    return rep
