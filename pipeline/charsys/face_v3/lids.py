"""face_generic/3 lid shells that end at the eye corners (T-089).

face_generic/1-2 lid shells are sphere caps that wrap all the way round the eyeball; the socket skin hides them, but
at the eye's sides (3/4 view) the skin fades back to the head surface and the shell ends show as a pale rim past the
outer corner. v3 cuts each shell at a plane x = const in its eye frame (x = the frame's left-right axis):
  spec.face.eyes.lids.trim = {"outer_deg": a_o, "inner_deg": a_i (optional), "soft": 0.06, "eye_clearance": 0.0}
keeps the shell where sx * x <= r_shell * sin(a_o) (and -sx * x <= r_shell * sin(a_i)). The lids blink, widen and
squint by rotating about the frame's x axis (face.py lid seam, face_generic eye_action_units), which keeps x: a trimmed
shell therefore stays inside its bound through every lid motion (test: lid-corner bound). Only the shell (skin
material) faces are cut; lash strands joined into a lower lid keep their geometry."""
import math

import bmesh
from mathutils import Matrix, Vector

SIDES = ((1, "L"), (-1, "R"))


def _f(d, k, default):
    return float(d.get(k, default)) if d is not None else float(default)


def lid_roll(lids_cfg, sx, zone):
    """3x3 rotation of one lid about its eye's forward axis (lids.upper_roll_deg / lower_roll_deg; positive raises
    the lid's OUTER end, the eye_frame roll_deg convention), or None; with the opt-in lid_yaw, the two combined. A rolled lid stays on its sphere (concentric
    with the eyeball): the lower lid rising to the outer corner gives the D-shaped opening of felt-doll eyes."""
    deg = _f(lids_cfg, "upper_roll_deg" if zone == "up" else "lower_roll_deg", 0.0)
    yaw = _f(lids_cfg, "upper_yaw_deg" if zone == "up" else "lower_yaw_deg", 0.0)
    if abs(yaw) > 1e-9:  # T-156 (opt-in; absent = the line below, unchanged): the lid turned about the eye's vertical axis
        return lid_yaw(sx, yaw) @ Matrix.Rotation(math.radians(-sx * deg), 3, "Y")
    return Matrix.Rotation(math.radians(-sx * deg), 3, "Y") if abs(deg) > 1e-9 else None


def lid_yaw(sx, deg):
    """lids.upper_yaw_deg / lower_yaw_deg (T-156, opt-in): 3x3 rotation of one lid about its eye's vertical axis,
    positive towards the OUTER corner (the eye_frame yaw_deg convention), applied after the roll. A lid edge is close
    to a circle about the eye's forward axis, so a roll does not move its peak; the yaw does, by r_lid * sin(yaw). It
    lets the lid arch sit over the middle of an opening that the nose-side skin makes narrower on the inner side,
    while the eyeball (iris) keeps its direction. The lid stays on its sphere, concentric with the eyeball."""
    return Matrix.Rotation(math.radians(sx * deg), 3, "Z")


def roll_lid(objs, T, R3):
    """Rotates the objects' meshes (world space data) by R3 about the eye frame's origin, in the frame."""
    M = T @ R3.to_4x4() @ T.inverted()
    for ob in objs:
        ob.data.transform(M)
        ob.data.update()


def rolled_edge(fn, R3):
    """Wraps a lid-edge function (azimuth -> frame point or None) with a lid roll."""
    if R3 is None:
        return fn
    return lambda a: (lambda p: None if p is None else R3 @ p)(fn(a))


def trim_bounds(lids_cfg, r_up_out, r_lo_out):
    """{"up": (outer, inner), "lo": (outer, inner)} in metres (frame units), None = not trimmed."""
    t = (lids_cfg or {}).get("trim")
    if not t:
        return None
    out = {}
    for zone, rr in (("up", r_up_out), ("lo", r_lo_out)):
        o = t.get(f"{zone}_outer_deg", t.get("outer_deg"))
        i = t.get(f"{zone}_inner_deg", t.get("inner_deg"))
        b = t.get(f"{zone}_back", t.get("back"))
        out[zone] = (None if o is None else rr * math.sin(math.radians(float(o))),
                     None if i is None else rr * math.sin(math.radians(float(i))),
                     None if b is None else float(b) * rr)
    return out


def trim_shell(ob, T, sx, bound_outer, bound_inner, bound_back=None, skin_material_name=None):
    """Cuts the shell (object data in world space, object matrix identity) at x = sx*bound_outer / -sx*bound_inner in
    the eye frame T, and (bound_back) at y = -bound_back: only the front of the shell stays (its caps above and below
    the eye no longer run back past the eye's sides; the blink rotation brings the front part, not the back, over
    the eye). Only faces with the skin material (or all faces when the object has a single material) are cut.
    Returns the number of vertices removed."""
    me = ob.data
    Ti = T.inverted()
    me.transform(Ti)
    bm = bmesh.new()
    bm.from_mesh(me)
    n0 = len(bm.verts)
    skin_idx = None
    if skin_material_name and len(me.materials) > 1:
        names = [m.name if m else "" for m in me.materials]
        skin_idx = names.index(skin_material_name) if skin_material_name in names else None
    cuts = [(Vector((sgn * b, 0, 0)), Vector((-sgn, 0, 0))) for b, sgn in ((bound_outer, sx), (bound_inner, -sx))
            if b is not None]
    if bound_back is not None:
        cuts.append((Vector((0, -bound_back, 0)), Vector((0, -1, 0))))
    for co, no in cuts:
        bm.verts.index_update()
        bm.edges.index_update()
        faces = [f for f in bm.faces if skin_idx is None or f.material_index == skin_idx]
        edges = sorted({e for f in faces for e in f.edges}, key=lambda e: e.index)
        verts = sorted({v for f in faces for v in f.verts}, key=lambda v: v.index)
        # keep the side the plane normal points to (clear_inner removes the other side)
        bmesh.ops.bisect_plane(bm, geom=verts + edges + faces, plane_co=co, plane_no=no, clear_inner=True,
                               clear_outer=False)
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
    removed = n0 - len(bm.verts)
    bm.to_mesh(me)
    bm.free()
    me.transform(T)
    me.update()
    return removed


def corner_extent(ob, T, sx):
    """Largest sx * x (outer side) and -sx * x (inner side) of the object's vertices in the eye frame, over the basis
    and every shape key (blink, wide, squint, in-betweens): the measured lid-corner bound."""
    Ti = T.inverted()
    mw = ob.matrix_world
    sets = [ob.data.vertices]
    if ob.data.shape_keys:
        sets = [k.data for k in ob.data.shape_keys.key_blocks]
    outer = inner = -1e9
    for data in sets:
        for v in data:
            x = (Ti @ (mw @ v.co)).x
            outer = max(outer, sx * x)
            inner = max(inner, -sx * x)
    return outer, inner


def _shell_vertices(ob, skin_material_name=None):
    """Vertex indices of the shell itself: with several materials (lash strands joined into a lower lid), only the
    vertices of faces with the skin material; otherwise every vertex."""
    me = ob.data
    names = [m.name if m else "" for m in me.materials]
    if not skin_material_name or len(names) < 2 or skin_material_name not in names:
        return range(len(me.vertices))
    k = names.index(skin_material_name)
    return sorted({i for p in me.polygons if p.material_index == k for i in p.vertices})


def exposure_from(head, shells, frames, yaw_deg, corner_deg, r, skin_material_name=None):
    """3/4 socket-rim diagnostic. For a camera direction at yaw_deg (0 = front, +90 = the character's left), each shell
    on the side that turns its OUTER corner to that camera: the fraction of its vertices past the opening's corner
    (sx * x > r * sin(corner_deg) in the eye frame) that no head skin hides along the view ray. 0 = no visible rim.
    Lash strands joined into a lid (other material) are not shell and are not counted."""
    from mathutils.bvhtree import BVHTree
    mw = head.matrix_world
    me = head.data
    tree = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
    a = math.radians(yaw_deg)
    d = Vector((math.sin(a), -math.cos(a), 0.0))
    xs = r * math.sin(math.radians(corner_deg))
    out = {}
    for ob in shells:
        side = ob.name.split(".")[-1][:1]
        sx = 1 if side == "L" else -1
        if sx * yaw_deg <= 0:
            continue
        Ti = frames[side].inverted()
        tot = vis = 0
        verts = ob.data.vertices
        for vi in _shell_vertices(ob, skin_material_name):
            w = ob.matrix_world @ verts[vi].co
            if sx * (Ti @ w).x <= xs:
                continue
            tot += 1
            if tree.ray_cast(w + d * 1e-4, d, 1.0)[0] is None:
                vis += 1
        out[ob.name] = {"past_corner_vertices": tot, "visible": vis, "fraction": round(vis / max(tot, 1), 3)}
    return out


# ------------------------------------------------------------------------------------------------ T-109: lower lid fit
def _gaze_inverses(T, ecfg):
    """Inverse matrices M_g^-1 (frame units) of the eyeball's rigid gaze rotations over gaze_range_deg: in the eye
    frame the turned eyeball is M_g applied to the radius-r sphere, M_g = A^-1 R_g A (A = the frame's 3x3)."""
    import numpy as np
    A = np.array(T.to_3x3())
    Ai = np.linalg.inv(A)
    gy, gp = (float(v) for v in ecfg.get("gaze_range_deg", [20.0, 12.0]))
    out = []
    for i in range(11):
        for j in range(7):
            R = np.array(Matrix.Rotation(math.radians(-gy + 2 * gy * i / 10), 3, "Z")
                         @ Matrix.Rotation(math.radians(-gp + 2 * gp * j / 6), 3, "X"))
            out.append(np.linalg.inv(Ai @ R @ A))
    return out


def local_envelope(u, Minv):
    """Per-direction gaze envelope (unit directions u (N, 3) in the eye frame; 1 = the eyeball surface): the largest
    radius the rigidly turned eyeball reaches along each direction. face_generic/2 builds every lid at the largest
    value over ALL directions (gaze_envelope); for an oval eye that value comes from the corners, so below and above
    the eye the lids stand off the eyeball."""
    import numpy as np
    env = np.zeros(len(u))
    for Mi in Minv:
        env = np.maximum(env, 1.0 / np.maximum(np.linalg.norm(u @ Mi.T, axis=1), 1e-9))
    return env


def lower_fit_radius(T, ecfg, r, fit):
    """spec.face.eyes.lids.lower_fit = {"gap": g, "thickness_m": t (optional)}: a function (unit directions in the eye
    frame) -> the fitted outer radius r * (envelope(u) + g) (+ the lid thickness). The lower lid shell and the socket
    skin over it are pulled in to it where they stood further out (never pushed out)."""
    Minv = _gaze_inverses(T, ecfg)
    g = _f(fit, "gap", 0.02)
    return lambda u: r * (local_envelope(u, Minv) + g)


def fit_lower_lid(ob, T, ecfg, r, r_lo, fit):
    """Pulls the lower lid shell (and the lash strands joined into it) in towards the eyeball along its eye-frame
    radius: a vertex at radius rho in direction u moves to rho - max(0, r_lo - r_fit(u)), so the shell keeps its
    thickness and its edge follows the eyeball instead of standing off it (the grey shelf of an oval eye under
    glasses). Object data in world space (identity matrix). Returns a report."""
    import numpy as np
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    Tm = np.array(T)
    Ti = np.linalg.inv(Tm)
    q = co @ Ti[:3, :3].T + Ti[:3, 3]
    d = np.linalg.norm(q, axis=1)
    u = q / np.maximum(d, 1e-12)[:, None]
    shift = np.maximum(0.0, r_lo - lower_fit_radius(T, ecfg, r, fit)(u))
    q = u * (d - shift)[:, None]
    me.vertices.foreach_set("co", (q @ Tm[:3, :3].T + Tm[:3, 3]).ravel())
    me.update()
    return {"gap": _f(fit, "gap", 0.02), "shift_max_m": round(float(shift.max()), 5),
            "shift_mean_m": round(float(shift.mean()), 5)}


# ------------------------------------------------------------------------------------------------ T-113: closed lid fit
def _smoothstep(t):
    import numpy as np
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fit_closed_lids(up, lash, T, ecfg, r, fit, close_key, closed_thickness_m=None):
    """spec.face.eyes.lids.closed_fit = {"gap": g, "fade_deg": f, "fade_above_edge_deg": a, "gaze_range_deg": [yaw, pitch]
    (optional, default the eye's), "corner_fade": [a, b] (default [0.7, 0.95]), "shell_subsurface": f (optional), "keep_thickness": bool}: the closed upper lid follows
    the eyeball surface instead of standing off it (the pale dome of Smile, Laugh, Squint and Blink).

    face_generic/2 closes the upper lid at the eye's GLOBAL gaze envelope (an oval eye: its corners' value, 1.08 r),
    and preset keys that add a squint rotation to a closing lid (Smile, Laugh, Squint) sum two rotations linearly, so
    their shell rides further out still. For every shape key of the upper lid shell and its lash (AU keys, their
    in-betweens and the baked presets) each vertex is pulled in along its eye-frame radius towards
    r (envelope(u) + g) + its own shell thickness (the per-direction gaze envelope, as lower_fit: the closed lid still
    covers the turned eyeball), by the vertex's closure c in [0, 1] (its downward rotation in that key divided by the
    full Blink rotation). Pulled in only, never pushed out. The closed lid shows where the open eye showed (the socket
    skin does not move when the lid closes): at key-position elevations up to the rest upper-lid edge the pull is
    full; it fades to none over fade_deg, ending fade_above_edge_deg above that edge, so the shell further up, under
    the socket skin, keeps its radius (no crevice under the brow). Towards the eye corners the pull fades out
    as well (corner_fade, in eye radii from the eye's vertical axis): at 3/4 a pulled-in corner opens the near eye's
    outer corner. Where a key's linear sum of rotations (blink + squint) carries the
    shell out past its rest radius, it is brought back to that radius (the bump through the brow skin). Open keys (EyeWide, brows, mouth) have c = 0 and do not change.
    shell_subsurface (optional, 0..1): the upper lid shell gets its own copy of its skin material with the Subsurface
    Weight scaled by f. The shell is ~1-2 mm thick while the skin's subsurface radius is ~1-2 cm, so a closed lid
    lets the white eyeball (and its highlight) show through: the pale part of the dome. Absent = material unchanged.
    Object data are read through matrix_world (any object matrix). Returns a report."""
    import numpy as np
    g = _f(fit, "gap", 0.01)
    fade = math.radians(_f(fit, "fade_deg", 20.0))
    over = math.radians(_f(fit, "fade_above_edge_deg", 10.0))
    cf0, cf1 = (float(v) for v in fit.get("corner_fade", [0.7, 0.95]))
    # T-156 (opt-in, absent = 0 = unchanged): sink_m moves the upper shell (not the lash) a further sink_m * c^3 in
    # towards the eye centre. Where the eyeball flattens behind the socket skin on a blink (face.blink.flatten), the
    # closed eye is the skin itself; a shell that stays proud of that skin shows as a patch of lid on it.
    sink = _f(fit, "sink_m", 0.0)
    # the closed lid clears the eyeball's gaze sweep; closed_fit.gaze_range_deg may narrow it (a closed eye moves less)
    Minv = _gaze_inverses(T, dict(ecfg, gaze_range_deg=fit["gaze_range_deg"]) if fit.get("gaze_range_deg") else ecfg)
    Tm = np.array(T)
    Ti = np.linalg.inv(Tm)

    def frame_coords(ob, data):
        n = len(ob.data.vertices)
        co = np.empty(n * 3)
        data.foreach_get("co", co)
        mw = np.array(ob.matrix_world)
        w = co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]
        return w @ Ti[:3, :3].T + Ti[:3, 3]

    def elev(q):  # elevation about the frame's x axis; the eye looks along -y
        return np.arctan2(q[:, 2], -q[:, 1])

    kb_up = up.data.shape_keys.key_blocks if up.data.shape_keys else None
    if kb_up is None or close_key not in kb_up:
        return {"skipped": f"no {close_key} key"}
    q0_up = frame_coords(up, kb_up[0].data)
    rho0_up = np.linalg.norm(q0_up, axis=1)
    r_in = float(rho0_up.min())
    shell = float(rho0_up.max()) - r_in
    a_close = float(np.median(elev(q0_up) - elev(frame_coords(up, kb_up[close_key].data))))
    if a_close <= 1e-6:
        return {"skipped": "no closing rotation"}
    # the rest edge: lowest elevation of the shell's front (the lid's free edge)
    front = q0_up[:, 1] < -0.5 * r
    e_edge = float(elev(q0_up[front]).min()) if front.any() else 0.0
    ts = (float(closed_thickness_m) / shell) if (closed_thickness_m and shell > 1e-9 and not fit.get("keep_thickness", False)) else 1.0
    rep = {"gaze_range_deg": fit.get("gaze_range_deg") or ecfg.get("gaze_range_deg", [20.0, 12.0]), "gap": g, "fade_deg": round(math.degrees(fade), 2), "fade_above_edge_deg": round(math.degrees(over), 2), "corner_fade": [cf0, cf1], "close_deg": round(math.degrees(a_close), 2),
           "rest_edge_deg": round(math.degrees(e_edge), 2), "keys": {}}
    if fit.get("shell_occlusion_tint") is not None:  # T-156 (opt-in; absent = the two lines below, unchanged)
        rep["shell_material"] = _shell_material(up, float(fit.get("shell_subsurface", 1.0)),
                                                float(fit["shell_occlusion_tint"]))
    elif fit.get("shell_subsurface") is not None:
        rep["shell_material"] = _shell_material(up, float(fit["shell_subsurface"]))
    for ob in (up, lash):
        if ob is None or ob.data.shape_keys is None:
            continue
        kb = ob.data.shape_keys.key_blocks
        q0 = frame_coords(ob, kb[0].data)
        th0 = elev(q0)
        t = np.maximum(0.0, np.linalg.norm(q0, axis=1) - r_in)  # thickness position (lash strands: beyond the shell)
        mw = np.array(ob.matrix_world)
        mwi = np.linalg.inv(mw)
        moved = 0.0
        for k in kb[1:]:
            q = frame_coords(ob, k.data)
            th = elev(q)
            c = np.clip((th0 - th) / a_close, 0.0, 1.0)
            if c.max() < 1e-4:
                continue
            rho = np.linalg.norm(q, axis=1)
            u = q / np.maximum(rho, 1e-12)[:, None]
            target = r * (local_envelope(u, Minv) + g) + t * (ts if ob is up else 1.0)  # lash: keeps its offset
            s = _smoothstep((e_edge + over - th) / max(fade, 1e-6))
            # the eye corners keep the lid's radius (at 3/4 the near eye's outer corner would open): full pull up to
            # |x| = corner_fade[0] r, none from corner_fade[1] r (x = the frame's left-right axis)
            ax = np.abs(q[:, 0]) / r
            s = s * (1.0 - _smoothstep((ax - cf0) / max(cf1 - cf0, 1e-6)))
            shift = c * s * np.maximum(0.0, rho - target)
            # a rotation keeps the radius: where a linear sum of rotations (blink + squint) carries the shell out past
            # its rest radius (it pokes through the socket skin above the eye), it goes back to that radius
            rho0 = np.linalg.norm(q0, axis=1)
            shift = np.maximum(shift, (c > 0) * np.maximum(0.0, rho - rho0))
            if sink > 0.0 and ob is up:  # T-156 (opt-in): the closed shell goes under the socket skin
                shift = shift + sink * c ** 3
            if shift.max() < 1e-7:
                continue
            q = u * (rho - shift)[:, None]
            w = q @ Tm[:3, :3].T + Tm[:3, 3]
            k.data.foreach_set("co", (w @ mwi[:3, :3].T + mwi[:3, 3]).ravel())
            moved = max(moved, float(shift.max()))
            if ob is up:
                rep["keys"][k.name] = round(float(shift.max()), 5)
        ob.data.update()
        rep.setdefault("shift_max_m", {})[ob.name] = round(moved, 5)
    fill = _skin_closed_fill(up, close_key, elev, frame_coords, a_close)  # T-156 (opt-in by socket.closed_fill)
    if fill:
        rep["skin_fill"] = fill
    if fit.get("lash_curve") and lash is not None:  # T-137 (opt-in): the closed eye shows a dark lash curve
        rep["lash_curve"] = curve_closed_lash(lash, T, r, fit["lash_curve"], a_close,
                                              _f(ecfg.get("lids"), "lower_edge_deg", -45.0))
    return rep


def _skin_closed_fill(up, close_key, elev, frame_coords, a_close):
    """T-156 (opt-in: only where face_v3.socket stored "ps_socket_fill.<side>" on a mesh, spec ...socket.closed_fill;
    without that attribute nothing is read or written). The stored displacement closes the socket opening in the
    skin. It is added to the skin's key of every upper-lid key that closes the eye fully (median closing rotation
    >= 0.95 of the close key's): Blink, the sided blink and winks. The skin must not close before the lid arrives, so
    the key gets in-betweens, which face_generic.add_inbetween_drivers plays piecewise: a key the skin did not have
    gets an empty "<key>@75" (the fill then runs over the last quarter of the control); a key it had gets
    "<key>@25/50/75" as that fraction of its motion (unchanged, linear) and the fill on top of the full key. The
    attribute is removed. Returns {key: max displacement} or None."""
    import bpy
    import numpy as np
    side = close_key.rsplit(".", 1)[-1]
    name = f"ps_socket_fill.{side}"
    head = next((o for o in bpy.data.objects if o.type == "MESH" and name in o.data.attributes), None)
    if head is None:
        return None
    me = head.data
    n = len(me.vertices)
    disp = np.empty(n * 3)
    me.attributes[name].data.foreach_get("vector", disp)
    me.attributes.remove(me.attributes[name])
    if me.shape_keys is None:
        head.shape_key_add(name="Basis")
    kb = me.shape_keys.key_blocks
    base = np.empty(n * 3)
    kb[0].data.foreach_get("co", base)
    kb_up = up.data.shape_keys.key_blocks
    th0 = elev(frame_coords(up, kb_up[0].data))
    out = {}
    for k in list(kb_up[1:]):
        if "@" in k.name or float(np.median(th0 - elev(frame_coords(up, k.data)))) < 0.95 * a_close:
            continue
        if k.name not in kb:
            for nm in (f"{k.name}@75", k.name):
                head.shape_key_add(name=nm).value = 0.0
        elif not any(b.name.startswith(k.name + "@") for b in kb):
            cur = np.empty(n * 3)
            kb[k.name].data.foreach_get("co", cur)
            for f in (25, 50, 75):
                nk = head.shape_key_add(name=f"{k.name}@{f}")
                nk.value = 0.0
                nk.data.foreach_set("co", base + (cur - base) * (f / 100.0))
        cur = np.empty(n * 3)
        kb[k.name].data.foreach_get("co", cur)
        kb[k.name].data.foreach_set("co", cur + disp)
        out[k.name] = round(float(np.abs(disp).max()), 5)
    me.update()
    return out


def curve_closed_lash(lash, T, r, cfg, a_close, seam_deg):
    """spec.face.eyes.lids.closed_fit.lash_curve = {"out_m": o, "sag_deg": s, "corner_lift_deg": l, "blend_deg": b,
    "seam_deg": e (default: lids.lower_edge_deg), "above_seam_deg": d, "span": [inner, outer], "keys": {key name: sag factor}} (T-137, opt-in;
    absent = the lash keys are not touched).

    A closing upper lid carries its lash line past the lid seam and on under the lower lid (lid_seam overlap), where
    the lower lid shell and the socket skin cover it: a closed eye shows no lash. For every shape key of the lash, the
    key's lash-line elevation e_k is its rest elevation (a quadratic fit over x: lid roll and curve) minus the key's
    median closing rotation. With w = smoothstep((seam + above + blend - e_k) / blend) (0 while the lash is still above
    the seam, 1 at and below it), each vertex
      * turns about the frame's x axis by w times the angle that puts the line on the target curve
        seam + above - sag_deg * (1 - u^2) + corner_lift_deg * u^2 (u = 0 at the middle and 1 at the ends of span, default the rest lash line; span is the
        visible opening when the socket skin hides part of the lash line): the lash
        stops at the seam, its middle sags and its corners rise (the downward curve of a closed felt eye);
      * goes to its rest radius + out_m (w-weighted): in front of the lower lid and the skin over it.
    Lash strands keep their offsets from the line. keys maps a key name (in-betweens "Name@NN" and sided "Name.L" use
    Name's entry) to a factor on sag_deg and corner_lift_deg (0 = straight, negative = an upward arc); others use 1.
    Open keys and the basis do not change. Returns a report."""
    import numpy as np
    kb = lash.data.shape_keys.key_blocks if lash.data.shape_keys else None
    if kb is None:
        return {"skipped": "no shape keys"}
    out_m, sag, lift = _f(cfg, "out_m", 0.003), math.radians(_f(cfg, "sag_deg", 6.0)), math.radians(_f(cfg, "corner_lift_deg", 4.0))
    blend = math.radians(max(_f(cfg, "blend_deg", 10.0), 0.1))
    e_s = math.radians(_f(cfg, "seam_deg", seam_deg) + _f(cfg, "above_seam_deg", 2.0))
    factors = cfg.get("keys") or {}
    Tm = np.array(T)
    Ti = np.linalg.inv(Tm)
    mw = np.array(lash.matrix_world)
    mwi = np.linalg.inv(mw)
    n = len(lash.data.vertices)

    def frame_coords(data):
        co = np.empty(n * 3)
        data.foreach_get("co", co)
        w = co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]
        return w @ Ti[:3, :3].T + Ti[:3, 3]

    q0 = frame_coords(kb[0].data)
    th0 = np.arctan2(q0[:, 2], -q0[:, 1])
    rho0 = np.linalg.norm(q0, axis=1)
    core = rho0 <= np.percentile(rho0, 50.0) + 1e-6 * r  # the lash line itself (strands stand further out)
    line0 = np.polyval(np.polyfit(q0[core, 0], th0[core], 2), q0[:, 0])  # its rest elevation along x
    x_lo, x_hi = float(q0[core, 0].min()), float(q0[core, 0].max())  # u: 0 at the curve's middle, 1 at its ends
    if cfg.get("span"):  # the visible opening, in eye radii from the eye's axis, signed towards the outer corner
        sx = 1.0 if lash.name.split(".")[-1][:1] == "L" else -1.0
        x_lo, x_hi = sorted(sx * float(v) * r for v in cfg["span"])
    u2 = np.clip(np.abs(q0[:, 0] - 0.5 * (x_lo + x_hi)) / max(0.5 * (x_hi - x_lo), 1e-9), 0.0, 1.2) ** 2
    rep = {"out_m": out_m, "sag_deg": round(math.degrees(sag), 2), "corner_lift_deg": round(math.degrees(lift), 2),
           "seam_deg": round(math.degrees(e_s), 2), "blend_deg": round(math.degrees(blend), 2), "keys": {}}
    for k in kb[1:]:
        q = frame_coords(k.data)
        turn = float(np.median((th0 - np.arctan2(q[:, 2], -q[:, 1]))[core]))  # the key's closing rotation
        if turn <= 1e-6 or a_close <= 1e-6:
            continue
        line = line0 - turn
        w = float(_smoothstep(np.array([(e_s + blend - float(np.median(line))) / blend]))[0])
        if w < 1e-6:
            continue
        base = k.name.split("@")[0]
        f = float(factors.get(base, factors.get(base.split(".")[0], 1.0)))
        ang = w * (line - (e_s - f * sag * (1.0 - u2) + f * lift * u2))  # + = the front moves down
        ca, sa = np.cos(ang), np.sin(ang)
        q = np.stack([q[:, 0], q[:, 1] * ca - q[:, 2] * sa, q[:, 1] * sa + q[:, 2] * ca], axis=1)
        rho = np.linalg.norm(q, axis=1)
        q = q * ((rho + w * (rho0 + out_m - rho)) / np.maximum(rho, 1e-12))[:, None]
        wco = q @ Tm[:3, :3].T + Tm[:3, 3]
        k.data.foreach_set("co", (wco @ mwi[:3, :3].T + mwi[:3, 3]).ravel())
        rep["keys"][k.name] = round(w, 3)
    lash.data.update()
    return rep


def _shell_material(ob, factor, occlusion_tint=None):
    """Replaces each material slot of the lid shell that has a Principled BSDF with subsurface by a copy named
    "<name>.lid" (shared by both lids) whose Subsurface Weight is scaled by factor (a linked weight is left linked and
    scaled through a multiply node). occlusion_tint (T-156, closed_fit.shell_occlusion_tint, 0..1; None = untouched):
    in the copy, every multiply-add Math node fed by an Ambient Occlusion node has its two constants scaled by it.
    The skin's occlusion tints darken creases; the lid dome sits inside the socket and is "occluded" all over by the
    eyeball behind it and the socket rim, so the closed lid reads as a patch of another tone than the skin around
    it. Returns {slot material: copy}."""
    import bpy
    done = {}
    for i, m in enumerate(ob.data.materials):
        if m is None or not m.use_nodes or m.name.endswith(".lid"):
            continue
        p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if p is None or "Subsurface Weight" not in p.inputs:
            continue
        name = m.name + ".lid"
        c = bpy.data.materials.get(name)
        if c is None:
            c = m.copy()
            c.name = name
            q = next(n for n in c.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            sock = q.inputs["Subsurface Weight"]
            if sock.is_linked:
                link = sock.links[0]
                mul = c.node_tree.nodes.new("ShaderNodeMath")
                mul.operation = "MULTIPLY"
                mul.inputs[1].default_value = factor
                c.node_tree.links.new(link.from_socket, mul.inputs[0])
                c.node_tree.links.new(mul.outputs[0], sock)
            else:
                sock.default_value = sock.default_value * factor
            if occlusion_tint is not None:
                for n in c.node_tree.nodes:
                    if n.type == "MATH" and n.operation == "MULTIPLY_ADD" and n.inputs[0].is_linked \
                            and n.inputs[0].links[0].from_node.type == "AMBIENT_OCCLUSION":
                        for j in (1, 2):
                            n.inputs[j].default_value = n.inputs[j].default_value * occlusion_tint
        ob.data.materials[i] = c
        done[m.name] = c.name
    return done
