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
    if smile.get("generator", "v6") == "corner_lift/1" and (face_spec or {}).get("mouth", {}).get("generator") != "lips_jaw/1":
        rep["smile"] = strengthen_smile(mouth, head, B, smile)
    return rep


# ============================================================================== lips_jaw/1: lips, mouth cavity, jaw bone
# spec.face.mouth = {"generator": "lips_jaw/1", "half_width_m": .., "lip_height_m": .., "frown_m": .., "smile_up_m": ..,
#                    "jaw_open_deg": .., "pivot_drop_m": .., "cavity_depth_m": .., "cheek_falloff_m": [a, b]}
# Character data come from the spec (mouth size, frown) and the built geometry (mouth line Z, face surface via
# B.face_y, ear/chin landmarks); nothing below is specific to one character.
def _smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def build_mouth_lips(C, M, head, B, cfg):
    """Upper and lower lip strips meeting at a seam (closed at rest). Rows: 0 upper outer, 1 upper inner,
    2 lower inner, 3 lower outer. Shape keys: Smile (corners up), JawOpen (upper lip lifts slightly; the jaw bone
    does the opening)."""
    import bpy
    G = B.G
    w, lh, fr = float(cfg.get("half_width_m", 0.0125)), float(cfg.get("lip_height_m", 0.0032)), float(cfg.get("frown_m", 0.0035))
    zm = B.Z["mouth"]
    n = 13

    def rows(frown, widen=1.0, up_lift=0.0):
        out = []
        for r, dz in enumerate((lh, 0.0, 0.0, -lh)):
            row = []
            for k in range(n):
                u = -1 + 2 * k / (n - 1)
                env = math.sqrt(max(1 - u * u, 0.0))
                x = u * w * widen
                z = zm - frown * u * u + dz * (0.35 + 0.65 * env) + (up_lift * env if r < 2 else 0.0)
                row.append((x, B.face_y(head, x, z) - 0.0012, z))
            out.append(row)
        return out
    verts = [v for row in rows(fr) for v in row]
    faces = [(r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i) for r in (0, 2) for i in range(n - 1)]
    old = bpy.data.objects.get("mouth")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    mouth = G.new_object("mouth", verts, faces, C)
    G.assign(mouth, M["mouth"])
    mouth.shape_key_add(name="Basis")
    up = float(cfg.get("smile_up_m", 0.007))
    for name, rr in (("Smile", rows(fr - fr - up, widen=1.12)), ("JawOpen", rows(fr, up_lift=0.0015))):
        k = mouth.shape_key_add(name=name)
        k.value = 0.0
        for i, v in enumerate(v for row in rr for v in row):
            k.data[i].co = v
    mouth["ps_lip_rows"] = n  # vertices per row; rows 2-3 belong to the lower lip (jaw)
    return mouth


def cut_mouth_and_cavity(C, M, head, B, cfg, mouth):
    """Mouth interior without cutting the head: a dark surface hanging between the inner lip edges (rows: top =
    upper-lip inner edge, middle = pushed back by cavity_depth_m, bottom = lower-lip inner edge), all just behind the
    lips. At rest the rows coincide in the front view (zero visible area); when the jaw opens, the top row stays with
    the head and the bottom row follows the jaw, so the interior fills exactly the gap between the lips and hides
    the skin behind it. (A boolean cut is not used: the head is a closed surface and a difference only dents it.)"""
    G = B.G
    n = int(mouth["ps_lip_rows"])
    co = [v.co.copy() for v in mouth.data.vertices]
    back = float(cfg.get("interior_offset_m", 0.0006))
    depth = float(cfg.get("cavity_depth_m", 0.006))
    verts = []
    for r, (row, dy) in enumerate(((1, back), (1, back + depth), (2, back))):
        for k in range(n):
            p = co[row * n + k]
            u = -1 + 2 * k / (n - 1)
            env = math.sqrt(max(1 - u * u, 0.0))
            verts.append((p.x * 0.97, p.y + (dy if r != 1 else back + depth * env), p.z))
    faces = [(r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i) for r in range(2) for i in range(n - 1)]
    cav = G.new_object("mouth_cavity", verts, faces, C)
    cav["ps_rows"] = n
    if "mouth_inner" not in M:
        M["mouth_inner"] = G.material("M_mouth_inner", tuple(cfg.get("cavity_srgb", (62, 24, 26))), roughness=0.75)
    G.assign(cav, M["mouth_inner"])
    return cav


def add_jaw(rig, head, cav, mouth, landmarks, head_bone, cfg):
    """Adds DEF-jaw (deforming, child of the head bone) at a pivot derived from the ear landmarks, drives its
    rotation from the rig's face_JawOpen control, and moves smooth jaw weights onto head, cavity and lower lip."""
    import bpy
    ears = [landmarks[k] for k in ("ear_L", "ear_R") if k in landmarks]
    ez = sum(e.z for e in ears) / len(ears)
    ey = sum(e.y for e in ears) / len(ears)
    piv = Vector((0.0, ey, ez - float(cfg.get("pivot_drop_m", 0.012))))
    chin = landmarks["chin"]
    zm = landmarks["mouth"].z
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones.new("DEF-jaw")
    eb.head, eb.tail = piv, Vector((0.0, chin.y, chin.z))
    eb.parent = rig.data.edit_bones[head_bone]
    eb.use_deform = True
    bpy.ops.object.mode_set(mode="POSE")
    pb = rig.pose.bones["DEF-jaw"]
    pb.rotation_mode = "XYZ"
    fc = pb.driver_add("rotation_euler", 0)
    d = fc.driver
    d.type = "SCRIPTED"
    v = d.variables.new()
    v.name, v.type = "j", "SINGLE_PROP"
    v.targets[0].id = rig
    v.targets[0].data_path = '["face_JawOpen"]'
    d.expression = f"j * {math.radians(float(cfg.get('jaw_open_deg', 7.0))):.5f}"  # simple expression: no Python needed
    bpy.ops.object.mode_set(mode="OBJECT")
    c0, c1 = cfg.get("cheek_falloff_m", [0.030, 0.065])
    w = float(cfg.get("half_width_m", 0.0125))

    def jaw_w(p):
        ax = abs(p.x)
        band = 0.003 + 0.6 * max(0.0, ax - 0.85 * w)  # sharp at the lip seam (hole), wide past the corners (skin)
        s1 = _smooth(zm, zm - band, p.z) if p.z < zm else 0.0
        s2 = 1 - _smooth(c0, c1, ax)
        s3 = _smooth(piv.y + 0.01, piv.y - 0.03, p.y)
        return s1 * s2 * s3
    stats = {}
    n = int(cav["ps_rows"])
    cj = cav.vertex_groups.get("DEF-jaw") or cav.vertex_groups.new(name="DEF-jaw")
    for r, wr in ((0, 0.0), (1, 0.5), (2, 1.0)):  # interior: top with the head, bottom with the jaw
        for k in range(n):
            u = -1 + 2 * k / (n - 1)
            wj = wr * (1 - 0.6 * u ** 4)
            cj.add([r * n + k], wj, "REPLACE")
            cav.vertex_groups[head_bone].add([r * n + k], 1 - wj, "REPLACE")
    for ob in (head,):
        hg = ob.vertex_groups[head_bone]
        jg = ob.vertex_groups.get("DEF-jaw") or ob.vertex_groups.new(name="DEF-jaw")
        moved = 0
        for vtx in ob.data.vertices:
            wj = jaw_w(ob.matrix_world @ vtx.co)
            if wj > 1e-4:
                jg.add([vtx.index], wj, "REPLACE")
                hg.add([vtx.index], 1 - wj, "REPLACE")
                moved += 1
        stats[ob.name] = moved
    n = int(mouth.get("ps_lip_rows", 13))
    jg = mouth.vertex_groups.get("DEF-jaw") or mouth.vertex_groups.new(name="DEF-jaw")
    for r in (2, 3):  # lower lip follows the jaw; its corners blend with the head so they do not tear
        for k in range(n):
            u = -1 + 2 * k / (n - 1)
            wj = 1 - 0.6 * u ** 4
            jg.add([r * n + k], wj, "REPLACE")
            mouth.vertex_groups[head_bone].add([r * n + k], 1 - wj, "REPLACE")
    stats["pivot"] = [round(c, 4) for c in piv]
    return stats
