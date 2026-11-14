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


def add_blink_lid_seam(lids, eye_r, G, cfg, eyes=()):
    """cfg flatten (0..0.6): when closed, the front of the eyeball and the closed lid/lash are compressed along the
    eye's forward axis by this fraction (Blink shape key on the eyeball too), so a protruding eye does not close into
    a dome. Default 0 keeps the F01/F02 behaviour."""
    overlap = float(cfg.get("overlap_deg", 3.0))
    flat = 1.0 - float(cfg.get("flatten", 0.0))
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
        shell = max((v.co - c).length for v in up.data.vertices) - r_in
        ts = float(cfg["closed_thickness_m"]) / shell if cfg.get("closed_thickness_m") else 1.0  # thinner when closed
        for ob in (up, lash):
            if ob.data.shape_keys is None:
                ob.shape_key_add(name="Basis")
            k = ob.shape_key_add(name="Blink")
            k.value = 0.0
            for i, v in enumerate(ob.data.vertices):
                d = R @ (v.co - c)
                if ob is up:  # pull the closed shell towards the eyeball, keeping its thickness
                    L = d.length
                    d = d * ((eye_r + closed_off + (L - r_in) * ts) / L)
                if flat < 1.0 and d.y < 0 and (ob is up or cfg.get("flatten_lash", True)):  # forward part (eye looks along -y)
                    d = Vector((d.x, d.y * flat, d.z))
                k.data[i].co = c + d
        eye = next((e for e in eyes if (e.matrix_world.translation - c).length < 1e-4), None)
        if flat < 1.0 and eye is not None:  # flatten the front of the eyeball under the closed lid
            if eye.data.shape_keys is None:
                eye.shape_key_add(name="Basis")
            ek = eye.shape_key_add(name="Blink")
            ek.value = 0.0
            for i, v in enumerate(eye.data.vertices):
                co = v.co.copy()  # eye mesh is centred on its object origin (= c)
                ek.data[i].co = Vector((co.x, co.y * flat, co.z)) if co.y < 0 else co
        report.append({"lid": up.name, "edge_upper_deg": round(e_up, 1), "edge_lower_deg": round(e_lo, 1),
                       "close_deg": round(ang, 1), "flatten": round(1 - flat, 2)})
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


def add_expression_keys(lids, brows, mouth, head, B, face_spec, eyes=()):
    """Dispatch: v6 keys by default; lid_seam/1 Blink and corner_lift/1 Smile when the spec asks for them."""
    blink = (face_spec or {}).get("blink", {})
    smile = (face_spec or {}).get("smile", {})
    rep = {}
    if blink.get("generator", "v6") == "lid_seam/1":
        rep["blink"] = add_blink_lid_seam(lids, B.EYE_R, B.G, blink, eyes)
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
    """Lips meeting at a seam (closed at rest).
    lips_jaw/1 rows: 0 upper outer, 1 upper seam, 2 lower seam, 3 lower outer; all in the mouth material.
    lips_jaw/2 rows: 0 upper outer, 1 upper line edge, 2 upper seam, 3 lower seam, 4 lower line edge, 5 lower outer;
      the outer strips use the lip material (cfg lip_material, default the skin), only the thin band around the seam
      (cfg seam_half_m) uses the dark mouth material, so the closed mouth reads as a line, not a dark slit.
    Shape keys: Smile (corners up, widened), JawOpen (upper lip lifts slightly; the jaw bone does the opening)."""
    import bpy
    G = B.G
    v2 = cfg.get("generator") == "lips_jaw/2"
    w, lh, fr = float(cfg.get("half_width_m", 0.0125)), float(cfg.get("lip_height_m", 0.0032)), float(cfg.get("frown_m", 0.0035))
    band = float(cfg.get("seam_half_m", 0.0008))
    edge_off, bulge = float(cfg.get("lip_edge_offset_m", 0.0002)), float(cfg.get("lip_bulge_m", 0.0012))
    dzs = (lh, band, 0.0, 0.0, -band, -lh) if v2 else (lh, 0.0, 0.0, -lh)
    n_up = len(dzs) // 2
    zm = B.Z["mouth"]
    n = 13

    def rows(frown, widen=1.0, up_lift=0.0):
        out = []
        for r, dz in enumerate(dzs):
            row = []
            for k in range(n):
                u = -1 + 2 * k / (n - 1)
                env = math.sqrt(max(1 - u * u, 0.0))
                x = u * w * widen
                z = zm - frown * u * u + dz * (0.35 + 0.65 * env) + (up_lift * env if r < n_up else 0.0)
                # v2: outer lip edges lie on the skin (no floating rim / cast shadow), the seam bulges slightly
                off = (edge_off + (bulge - edge_off) * (1 - abs(dz) / lh)) if v2 else 0.0012
                row.append((x, B.face_y(head, x, z) - off, z))
            out.append(row)
        return out
    verts = [v for row in rows(fr) for v in row]
    strips = [r for r in range(len(dzs) - 1) if r != n_up - 1]  # no faces across the seam
    faces = [(r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i) for r in strips for i in range(n - 1)]
    old = bpy.data.objects.get("mouth")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    mouth = G.new_object("mouth", verts, faces, C)
    if v2:  # mouth line: its own matte material (cfg line_srgb, line_roughness) so the seam reads as one line
        G.assign(mouth, G.material("M_mouth_line", tuple(cfg.get("line_srgb", (70, 34, 32))), roughness=float(cfg.get("line_roughness", 1.0))))
    else:
        G.assign(mouth, M["mouth"])
    if v2:  # outer strips: lip material (slot 1); seam band: line material (slot 0)
        lip = M.get(cfg.get("lip_material", "skin"), M["skin"])
        mouth.data.materials.append(lip)
        for f, (r, i) in zip(mouth.data.polygons, [(r, i) for r in strips for i in range(n - 1)]):
            f.material_index = 1 if r in (0, len(dzs) - 2) else 0
    mouth.shape_key_add(name="Basis")
    up = float(cfg.get("smile_up_m", 0.007))
    # Per-character expression shaping: intensity scales the motion, asymmetry > 0 favours the character's left (+x).
    inten, asym = float(cfg.get("smile_intensity", 1.0)), float(cfg.get("smile_asymmetry", 0.0))
    base_rows = [v for row in rows(fr) for v in row]
    shapes = (("Smile", rows(fr - fr - up, widen=float(cfg.get("smile_widen", 1.12))), True),
              ("JawOpen", rows(fr, widen=float(cfg.get("jaw_lip_round", 1.0)), up_lift=float(cfg.get("jaw_upper_lift_m", 0.0015))), False))
    for name, rr, shaped in shapes:
        k = mouth.shape_key_add(name=name)
        k.value = 0.0
        for i, v in enumerate(v for row in rr for v in row):
            b = base_rows[i]
            s = inten * (1 + asym * (1 if b[0] > 0 else -1 if b[0] < 0 else 0)) if shaped else 1.0
            k.data[i].co = tuple(b[j] + (v[j] - b[j]) * s for j in range(3))
    mouth["ps_lip_rows"] = n
    mouth["ps_seam_rows"] = [n_up - 1, n_up]          # upper seam row, lower seam row
    mouth["ps_lower_rows"] = list(range(n_up, len(dzs)))  # follow the jaw
    return mouth


def cut_mouth_and_cavity(C, M, head, B, cfg, mouth):
    """Mouth interior without cutting the head: a surface hanging between the inner lip edges, just behind the lips.
    All rows coincide at rest (zero visible area). Each row follows the jaw by its fraction t (top 0 = head, bottom
    1 = jaw), so it fills exactly the gap between the lips. (A boolean cut is not used: the head is a closed
    surface and a difference only dents it.)
    lips_jaw/1: 3 rows, one dark material. lips_jaw/2: cfg interior_rows rows with vertex-colour shading for depth:
    reddish inner edges (cfg inner_srgb), dark throat in the middle (cfg throat_srgb), tongue tint low in the
    centre (cfg tongue_srgb; set it to the throat colour for no tongue). No extra geometry."""
    import bpy
    G = B.G
    v2 = cfg.get("generator") == "lips_jaw/2"
    n = int(mouth["ps_lip_rows"])
    s_up, s_lo = (list(mouth["ps_seam_rows"]) if "ps_seam_rows" in mouth else [1, 2])
    co = [v.co.copy() for v in mouth.data.vertices]
    back = float(cfg.get("interior_offset_m", 0.0006))
    depth = float(cfg.get("cavity_depth_m", 0.0))
    ts = [0.0, 0.5, 1.0] if not v2 else [i / (int(cfg.get("interior_rows", 7)) - 1) for i in range(int(cfg.get("interior_rows", 7)))]
    verts = []
    for t in ts:
        for k in range(n):
            p = co[s_up * n + k] if t < 0.5 else co[s_lo * n + k]
            u = -1 + 2 * k / (n - 1)
            env = math.sqrt(max(1 - u * u, 0.0))
            mid = 1 - abs(2 * t - 1)
            verts.append((p.x * 0.97, p.y + back + depth * env * mid, p.z))
    R = len(ts)
    faces = [(r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i) for r in range(R - 1) for i in range(n - 1)]
    cav = G.new_object("mouth_cavity", verts, faces, C)
    cav["ps_rows"] = n
    cav["ps_row_weights"] = ts
    if v2:
        lin = lambda c: tuple(float(x) for x in G.srgb_to_linear(tuple(c)))  # noqa: E731
        inner, throat, tongue = (lin(cfg.get(k, d)) for k, d in (("inner_srgb", (128, 52, 52)), ("throat_srgb", (34, 12, 14)),
                                                                  ("tongue_srgb", (150, 72, 74))))
        attr = cav.data.color_attributes.new("ps_mouth_shade", "FLOAT_COLOR", "POINT")
        for r, t in enumerate(ts):
            for k in range(n):
                u = -1 + 2 * k / (n - 1)
                edge = max(abs(2 * t - 1), abs(u)) ** 3  # 1 at the lips, 0 deep inside
                col = [throat[i] + (inner[i] - throat[i]) * edge for i in range(3)]
                tw = max(0.0, (t - 0.55) / 0.45) * max(0.0, 1 - abs(u) * 1.3) * (1 - edge)  # tongue: low, central
                col = [col[i] + (tongue[i] - col[i]) * tw for i in range(3)]
                attr.data[r * n + k].color = (*col, 1.0)
        mat = M.get("mouth_inner_v2")
        if mat is None:
            mat = bpy.data.materials.new("M_mouth_inner_shaded")
            mat.use_nodes = True
            nt = mat.node_tree
            p = nt.nodes.get("Principled BSDF")
            a = nt.nodes.new("ShaderNodeAttribute")
            a.attribute_name = "ps_mouth_shade"
            nt.links.new(a.outputs["Color"], p.inputs["Base Color"])
            p.inputs["Roughness"].default_value = 0.6
            M["mouth_inner_v2"] = mat
        G.assign(cav, mat)
    else:
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
        # sharp at the lip seam (hidden by the interior), widening towards and past the corners (visible skin)
        band = 0.003 + 0.6 * max(0.0, ax - float(cfg.get("jaw_band_start", 0.85)) * w)
        # Outside the lip corners the skin is continuous: centre the ramp on the mouth line there (the corner moves
        # about half as much as the lower lip) instead of starting it at the line (cfg jaw_corner_center 0..1).
        top = zm + 0.5 * band * float(cfg.get("jaw_corner_center", 0.0)) * _smooth(0.85 * w, 1.15 * w, ax)
        s1 = _smooth(top, top - band, p.z) if p.z < top else 0.0
        s2 = 1 - _smooth(c0, c1, ax)
        s3 = _smooth(piv.y + 0.01, piv.y - 0.03, p.y)
        return s1 * s2 * s3
    stats = {}
    n = int(cav["ps_rows"])
    cj = cav.vertex_groups.get("DEF-jaw") or cav.vertex_groups.new(name="DEF-jaw")
    for r, wr in enumerate(list(cav.get("ps_row_weights", [0.0, 0.5, 1.0]))):  # interior: top with the head, bottom with the jaw
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
    for r in list(mouth.get("ps_lower_rows", [2, 3])):  # lower lip follows the jaw; its corners blend so they do not tear
        for k in range(n):
            u = -1 + 2 * k / (n - 1)
            wj = 1 - 0.6 * u ** 4
            jg.add([r * n + k], wj, "REPLACE")
            mouth.vertex_groups[head_bone].add([r * n + k], 1 - wj, "REPLACE")
    stats["pivot"] = [round(c, 4) for c in piv]
    return stats


# ============================================================================== smile coupling (any face)
# spec.face.smile_coupling = {"cheek_raise_m", "cheek_forward_m", "cheek_radius_scale", "corner_follow",
#                             "corner_radius_scale", "eye_squint_deg"}
# Adds "Smile" shape keys to the head (cheeks rise and round forward; the skin around the mouth corners follows the
# lips' own Smile motion so the corners do not stretch) and to the lower lids (they rise: the eyes narrow). The
# existing face_Smile control drives every key named Smile, so no new control is needed. Placement comes only from
# landmarks (eyes, mouth) and the lips' geometry; sizes are fractions of the eye-to-mouth-corner distance.
def add_smile_coupling(head, lids, mouth, landmarks, cfg):
    inten, asym = float(cfg.get("intensity", 1.0)), float(cfg.get("asymmetry", 0.0))
    side_s = lambda x: inten * (1 + asym * (1 if x > 0 else -1))  # noqa: E731  (+x = character's left)
    raise_m = float(cfg.get("cheek_raise_m", 0.003))
    fwd_m = float(cfg.get("cheek_forward_m", 0.0015))
    rscale = float(cfg.get("cheek_radius_scale", 0.55))
    follow = float(cfg.get("corner_follow", 0.8))
    crs = float(cfg.get("corner_radius_scale", 0.9))
    squint = float(cfg.get("eye_squint_deg", 8.0))
    n = int(mouth["ps_lip_rows"])
    seam = list(mouth.get("ps_seam_rows", [1, 2]))[0]
    kb = mouth.data.shape_keys.key_blocks
    mw = mouth.matrix_world
    corners = []
    for k in (0, n - 1):  # lip corners and their Smile motion (world)
        i = seam * n + k
        p0, p1 = mw @ kb["Basis"].data[i].co, mw @ kb["Smile"].data[i].co
        corners.append((p0, p1 - p0))
    half_w = abs(corners[0][0].x - corners[1][0].x) / 2
    eyes = [landmarks[k] for k in ("eye_L", "eye_R") if k in landmarks]
    hmw, hinv = head.matrix_world, head.matrix_world.inverted()
    if head.data.shape_keys is None:
        head.shape_key_add(name="Basis")
    key = head.shape_key_add(name="Smile")
    key.value = 0.0
    face_front = landmarks["mouth"].y + 0.03  # only the front of the face moves
    cheeks = []
    for (c0, dc) in corners:
        eye = min(eyes, key=lambda e: (e - c0).length)  # the eye on the same side
        dist = (eye - c0).length
        lateral = Vector((math.copysign(0.35 * abs(eye.x - c0.x), c0.x), 0, 0))
        cheeks.append((c0 + (eye - c0) * 0.5 + lateral, rscale * dist, side_s(c0.x)))
    moved = 0
    for i, v in enumerate(head.data.vertices):
        p = hmw @ v.co
        if p.y > face_front:
            continue
        d = Vector((0, 0, 0))
        for centre, R, ss in cheeks:
            g = math.exp(-((p - centre).length / R) ** 2)
            d += Vector((0, -fwd_m, raise_m)) * (g * ss)
        for c0, dc in corners:  # dc already carries the lips' own intensity/asymmetry
            g = math.exp(-((p - c0).length / (crs * half_w)) ** 2)
            d += dc * (follow * g)
        if d.length > 1e-6:
            key.data[i].co = hinv @ (p + d)
            moved += 1
    # lower lids rise (rotation about the eye centre, opposite to the blink direction)
    for up, lo, lash, c in lids:
        R = Matrix.Rotation(math.radians(-squint * side_s(c.x)), 3, Vector((1, 0, 0)))
        if lo.data.shape_keys is None:
            lo.shape_key_add(name="Basis")
        k = lo.shape_key_add(name="Smile")
        k.value = 0.0
        for i, v in enumerate(lo.data.vertices):
            k.data[i].co = c + R @ (v.co - c)
    return {"head_vertices": moved, "cheek_radius_m": [round(c[1], 4) for c in cheeks], "eye_squint_deg": squint,
            "intensity": inten, "asymmetry": asym}
