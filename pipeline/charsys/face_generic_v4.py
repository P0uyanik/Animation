"""Generic facial production system, round 4 (spec.generators.face = "face_generic/4"; T-216, face plan P3). Opt-in.

face_generic/4 = face_generic/3 (face_generic_v3.py, unchanged; build copied here) plus:
  face.knobs   a list of built-in Blender deform modifiers (WARP, HOOK, LATTICE) with compact falloff, anchored on
               front / profile outline points, the chin, mouth, nose or eyes (face_v4/knobs.py). At build time each
               knob is applied as a shape key and folded into Basis on the NEUTRAL skin, before eyes, lids, brows,
               mouth, ears, glasses, groom, rig and masks are built on it; keys already relative to Basis follow by
               the same offset; every helper (modifier, empty, lattice, vertex group) is removed again, so the master
               stays knob-free (face_parity.py). The lid keys are therefore generated on the fitted rest face, and
               the glasses (accessories) are seated on it as rigid objects (no Surface Deform).
  complete_inbetween_chains
               (called by build_character.py before add_inbetween_drivers) a mesh that carries the base key of an
               in-between chain ("<X>@NN" on another mesh) but none of its stop keys gets linear stop keys
               (stop f = f x the base delta), so the engine's expandInbetweens (by morph name) reproduces Blender's
               linear motion on that mesh at every partial weight (face_v4/chains.py; T-213 chain gap, option b).
Without `face.knobs` a face_generic/4 build equals face_generic/3 except the generator tag and the stop keys.
Character-independent: no character ids, names or dimensions in this module; every value is spec data."""
import math

import face_features as FF
import face as FACE
import geom as G
from face_generic import (SIDES, FaceContext, _f, _lid_edge, _lid_geometry, _rename_key, add_inbetween_drivers,  # noqa: F401
                          add_jaw_preset_drivers, add_landmarks, add_pout, bake_presets, bind_rigid, build_brows_v2,
                          build_ears, build_eyes, ear_landmark, eye_action_units, load_library, split_action_units)
from face_generic_v3 import FELT_SHADER, _apply_felt_eye
from face_v3 import lids as LIDS
from face_v3 import lower_face as LOWER
from face_v3 import socket as SOCKET
from face_v4 import chains as CHAINS
from face_v4 import knobs as KNOBS
from materials import builder as MATERIALS
from mathutils import Vector

GENERATOR_VERSIONS = ("face_generic/4",)  # versions implemented here (versions.py; released = immutable)


def complete_inbetween_chains(objs):
    """Linear stop keys on meshes that carry a chained base key without its stops (face_v4/chains.py)."""
    return CHAINS.complete(objs)


def build(C, M, head, spec, P, H, head_bone="DEF-spine.006", eye_bone="DEF-eye.{s}"):
    """face_generic/4 build: face_generic/3's build (copied; v3 itself is unchanged) plus `face.knobs` (module
    docstring), applied right after the head shape options. Same outputs as face_generic/3's build."""
    fs = spec["face"]
    L = fs.get("layout", {})
    ecfg = fs.get("eyes", {})
    lib = load_library()
    ex, ez = P["eyes"]["x"] * H, P["eyes"]["z"] * H
    if "spacing_m" in ecfg or "offset_z_m" in ecfg:
        ex = _f(ecfg, "spacing_m", 2 * ex) / 2
        ez = ez + _f(ecfg, "offset_z_m", 0.0)
        P["eyes"]["x"], P["eyes"]["z"] = ex / H, ez / H
    r = _f(ecfg, "radius_m", 0.03)
    z_mouth = ez - _f(L, "mouth_below_eye_m", 0.05)
    ctx = FaceContext(head, z_mouth, r)
    rep = {"generator": "face_generic/4"}
    skin_rgb = tuple(spec["materials"].get("albedo_srgb", {}).get("skin") or spec["materials"]["target_colors_srgb"]["skin"])
    bl = fs.get("blush")
    z_nose = ez - _f(L, "nose_below_eye_m", 0.03)
    if fs.get("shape"):  # head proportions first (v1 options, then the v2 round-face options)
        sh = FF.shape_face_v2(head, ctx, fs["shape"], ex, ez, r, ez - _f(L, "chin_below_eye_m", 0.09))
        sh.update(FF.shape_head(head, ctx, {k: v for k, v in fs["shape"].items() if k != "cheek_roundness_m"}, ex, ez, r))
        if fs["shape"].get("lower_face"):  # T-109 (opt-in): low cheek pads, rounder jaw
            lf = LOWER.shape_lower_face(head, ctx, fs["shape"]["lower_face"], ex, ez, z_mouth,
                                        ez - _f(L, "chin_below_eye_m", 0.09))
            if lf:
                sh["lower_face"] = lf
        rep["shape"] = sh
    if fs.get("knobs"):  # v4: built-in Warp / Hook / Lattice knobs, baked into the NEUTRAL skin's Basis here,
        # before any feature, key, rig or mask is built on it (so lids, brows, mouth, ears and glasses are built on
        # the fitted rest face and every later key is relative to it)
        zc_knobs = ez - _f(L, "chin_below_eye_m", 0.09)
        rep["knobs"] = KNOBS.apply_knobs(C, head, ctx, fs["knobs"],
                                         KNOBS.anchors(ctx, ex, ez, z_mouth, zc_knobs, P["head"]["forward"] * H),
                                         z_chin=zc_knobs)
    if fs.get("skin"):
        spots = []
        if bl:
            for sx, _ in SIDES:
                bx, bz = sx * (ex + _f(bl, "out_m", 0.0)), ez - _f(bl, "below_eye_m", 0.04)
                spots.append(((bx, ctx.face_y(None, bx, bz), bz), _f(bl, "radius_m", 0.025), _f(bl, "intensity", 1.0)))
            if bl.get("nose"):
                zn = z_nose + _f(fs.get("nose", {}), "offset_z_m", 0.0)
                spots.append(((0.0, ctx.face_y(None, 0.0, zn), zn), _f(bl, "nose_radius_m", _f(bl, "radius_m", 0.025)),
                              _f(bl, "nose_intensity", _f(bl, "intensity", 1.0))))
        fc = (0.0, ctx.face_y(None, 0.0, z_nose), z_nose)
        M["face_skin"] = FF.face_skin_material("M_skin_face", skin_rgb, bl, spots, fs["skin"], fc)
        skin_assignment = MATERIALS.get_assignment(spec["materials"], "skin")
        if skin_assignment:
            MATERIALS.apply_from_assignment(M["face_skin"], skin_assignment, preserve_base_color=True)
        FF.carry_base_to_rim(M["face_skin"])
    elif bl:
        spots = []
        for sx, _ in SIDES:
            bx, bz = sx * (ex + _f(bl, "out_m", 0.0)), ez - _f(bl, "below_eye_m", 0.04)
            spots.append((bx, ctx.face_y(None, bx, bz), bz))
        if bl.get("nose"):
            spots.append((0.0, ctx.face_y(None, 0.0, z_nose), z_nose))
        M["face_skin"] = G.blush_skin_material("M_skin_face", skin_rgb, tuple(bl.get("srgb", (226, 150, 150))), spots,
                                               _f(bl, "radius_m", 0.025), subsurface=0.2)
        skin_assignment = MATERIALS.get_assignment(spec["materials"], "skin")
        if skin_assignment:
            MATERIALS.apply_from_assignment(M["face_skin"], skin_assignment, preserve_base_color=True)
    else:
        M["face_skin"] = M["skin"]
    G.assign(head, M["face_skin"])
    nc = fs.get("nose", {})
    nose_obj = None
    if nc.get("type"):
        nose_obj, nose_tip = FF.build_nose(C, M, head, ctx, nc, z_nose)
        z_nose = nose_tip.z
        rep["nose"] = {"type": nc["type"], "tip_m": [round(v, 4) for v in nose_tip]}
    elif nc:
        ny = ctx.face_y(None, 0.0, z_nose)
        G.brush(head, (0.0, ny + _f(nc, "radius_m", 0.016) * 0.3, z_nose), _f(nc, "radius_m", 0.016), (0, -_f(nc, "height_m", 0.004), 0))
        ctx.invalidate()
    lm = {"mouth": Vector((0.0, ctx.face_y(None, 0.0, z_mouth), z_mouth))}
    zc = ez - _f(L, "chin_below_eye_m", 0.09)
    lm["chin"] = Vector((0.0, ctx.face_y(None, 0.0, zc), zc))
    lm["nose"] = Vector((0.0, ctx.face_y(None, 0.0, z_nose), z_nose))
    # the felt eye replaces the eyeball material after build_eyes; build_eyes itself makes the layered/1 eye for it
    bcfg_eyes = dict(ecfg, shader="layered/1") if ecfg.get("shader") == FELT_SHADER else ecfg
    eyes, lids, frames, einfo = build_eyes(C, M, ctx, bcfg_eyes, ex, ez, _f(ecfg, "protrusion_m", 0.015),
                                           MATERIALS.get_assignment(spec["materials"], "eyes"))
    felt = None
    if ecfg.get("shader") == FELT_SHADER:  # v3: matte felt eye, one crisp highlight, matte lid line
        felt = _apply_felt_eye(eyes, lids, ecfg, r, MATERIALS.get_assignment(spec["materials"], "eyes"))
        rep["felt_eye"] = felt
    rolls = {}
    for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):  # v3: per-lid roll (lid profile: D-shaped opening)
        lc = ecfg.get("lids", {})
        rolls[side] = {"up": LIDS.lid_roll(lc, sx, "up"), "lo": LIDS.lid_roll(lc, sx, "lo")}
        if rolls[side]["up"] is not None:
            LIDS.roll_lid([up, lash], frames[side], rolls[side]["up"])
        if rolls[side]["lo"] is not None:
            LIDS.roll_lid([lo], frames[side], rolls[side]["lo"])
    lo_fit = {}
    if (ecfg.get("lids") or {}).get("lower_fit"):  # T-109 (opt-in): the lower lid follows the eyeball (no shelf)
        fit = ecfg["lids"]["lower_fit"]
        for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):
            lg = _lid_geometry(sx, ecfg, r)
            rep.setdefault("lower_fit", {})[side] = LIDS.fit_lower_lid(lo, frames[side], ecfg, r, lg["r_lo"], fit)
            lo_fit[side] = (LIDS.lower_fit_radius(frames[side], ecfg, r, fit), lg["r_lo"])
    if any(v is not None for rr in rolls.values() for v in rr.values()):
        rep["lid_roll_deg"] = {"upper": _f(ecfg.get("lids", {}), "upper_roll_deg", 0.0),
                               "lower": _f(ecfg.get("lids", {}), "lower_roll_deg", 0.0)}
    trims = {}
    for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):  # v3: lid shells end at the eye corners
        lg = _lid_geometry(sx, ecfg, r)
        tb = LIDS.trim_bounds(lg["lids_cfg"], lg["r_up_out"], lg["r_lo_out"])
        if tb:
            trims[side] = tb
            sk = M.get("face_skin")
            rm = {"up": LIDS.trim_shell(up, frames[side], sx, *tb["up"], skin_material_name=sk.name if sk else None),
                  "lo": LIDS.trim_shell(lo, frames[side], sx, *tb["lo"], skin_material_name=sk.name if sk else None)}
            rep.setdefault("lid_trim", {})[side] = {"bounds_m": {z: [None if b is None else round(b, 5) for b in tb[z]]  # outer, inner, back
                                                                for z in ("up", "lo")}, "removed_vertices": rm}
    P["eyes"]["y"] = lids[0][3].y / H
    rep["eyes"] = einfo
    for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):
        lm[f"eye_{side}"] = frames[side] @ Vector((0, -r, 0))
    # lids blended into the skin: the head wraps the lid shells (before anything else is placed on the surface)
    sock_cfg = ecfg.get("socket", {})
    socket_w = {}
    if sock_cfg.get("enabled", True):
        if int(sock_cfg.get("refine_cuts", 2)) > 0:
            rep["socket_refined_faces"] = FF.refine_eye_regions(head, [frames[s] for _, s in SIDES], r,
                                                                _f(sock_cfg, "refine_reach", 1.8), int(sock_cfg.get("refine_cuts", 2)))
            ctx.invalidate()
        sides = []
        for sx, side in SIDES:
            lg = _lid_geometry(sx, ecfg, r)
            trim = None
            if side in trims:
                tc = lg["lids_cfg"].get("trim") or {}
                trim = {z: {"outer_x": None if trims[side][z][0] is None else trims[side][z][0] / r,
                            "inner_x": None if trims[side][z][1] is None else trims[side][z][1] / r,
                            "back_y": None if trims[side][z][2] is None else trims[side][z][2] / r,
                            "soft": _f(tc, "soft", 0.06), "cover_margin": _f(tc, "cover_margin", 0.04),
                            "eye_clearance": _f(tc, "eye_clearance", 0.0)} for z in ("up", "lo")}
            sides.append({"sx": sx, "side": side, "T": frames[side], "r": r, "r_up_out": lg["r_up_out"], "r_lo_out": lg["r_lo_out"],
                          "trim": trim,
                          **({"lo_fit": lo_fit[side][0], "r_lo": lo_fit[side][1]} if side in lo_fit else {}),
                          "up_edge": FF.lid_edges(LIDS.rolled_edge(lambda a, lg=lg: _lid_edge(lg["q_up"], lg["k_up"], lg["r_up"], a, lg["lids_cfg"], True),
                                                                   rolls[side]["up"]), corner_deg=_f(sock_cfg, "corner_deg", 60.0)),
                          "lo_edge": FF.lid_edges(LIDS.rolled_edge(lambda a, lg=lg: _lid_edge(lg["q_lo"], lg["k_lo"], lg["r_lo"], a, lg["lids_cfg"], False),
                                                                   rolls[side]["lo"]), corner_deg=_f(sock_cfg, "corner_deg", 60.0))})
        rep["lid_socket"], socket_w = SOCKET.lid_socket_v3(head, ctx, sides, sock_cfg)
    ears = build_ears(C, M, ctx, fs.get("ears", {}), ez) if fs.get("ears") else []
    for (sx, side), e in zip(SIDES, ears):
        lm[f"ear_{side}"] = ear_landmark(e)
    if not ears:
        for sx, side in SIDES:
            lm[f"ear_{side}"] = Vector((ctx.side_x(sx, 0.0, ez - 0.01) or sx * 0.1, 0.0, ez - 0.01))
    au = fs.get("action_units", {})
    brows = build_brows_v2(C, ctx, fs.get("brows", {}), au, ex, ez, r) if fs.get("brows") else []
    mcfg = dict(fs["mouth"])
    M.setdefault("lip", G.material("M_lip_generic", tuple(mcfg.get("lip_srgb", skin_rgb)), roughness=0.5, subsurface=0.15))
    mouth = FACE.build_mouth_lips(C, M, head, ctx, mcfg)
    cavity = FACE.cut_mouth_and_cavity(C, M, head, ctx, mcfg, mouth)
    full = FF.lip_fullness(mouth, mcfg)
    if full:
        rep["lip_fullness"] = full
    closed = {}
    off = _f(fs.get("blink", {}), "closed_offset_m", 0.0012) / r
    for _, side in SIDES:
        env = einfo[side]["gaze_envelope"]
        closed[side] = 1.0 if env <= 1.0 else max(env * 1.005 - off, 1 + einfo[side]["lid_gap_lower"] - _f(ecfg.get("lids", {}), "lower_gap", 0.03))
    bcfg = dict(fs.get("blink", {}))
    widened = max(einfo[side]["lid_gap_lower"] - _f(ecfg.get("lids", {}), "lower_gap", 0.03) for _, side in SIDES)
    if widened > 0:
        bcfg["overlap_deg"] = _f(bcfg, "overlap_deg", 3.0) + math.degrees(widened)
        rep["blink_overlap_deg"] = round(bcfg["overlap_deg"], 2)
    rep["blink"] = eye_action_units(eyes, lids, frames, r, bcfg, au, closed)
    if socket_w:  # the socket skin follows its lid in every lid motion
        wide_up, wide_lo = _f(au, "wide_upper_deg", 10), _f(au, "wide_lower_deg", 6)
        # A closing lid (Blink, EyeSquint, the smile's lower-lid lift) slides out from under the crease, so the skin
        # stays; an opening lid (EyeWide) retracts under it, so the skin above the crease rises with it.
        FF.socket_key(head, "EyeWide", socket_w, {k: v for _, s in SIDES for k, v in (((s, "up"), -wide_up), ((s, "lo"), wide_lo))})
    if fs.get("smile_coupling"):
        rep["smile_coupling"] = FACE.add_smile_coupling(head, lids, mouth, lm, fs["smile_coupling"])
        FF.taper_key_front(head, "Smile", lm["mouth"].y + 0.03)  # no step on the cheeks at the coupling's cut-off
    for ob in [mouth, cavity, head] + [l[1] for l in lids]:
        _rename_key(ob, "Smile", "MouthSmile")
    if fs.get("cheeks"):
        cr = FF.add_cheek_raise(head, lm, fs["cheeks"], ex, ez)
        if cr:
            rep["cheek_raise"] = cr
    if socket_w:  # the lower lids ride on the cheek skin (smile, cheek lift)
        rep["lids_follow_skin"] = FF.lids_follow_skin(head, [l[1] for l in lids], ("MouthSmile", "CheekRaise"))
    if _f(au, "pout_m", 0.0) > 0:
        rep["pout"] = add_pout([mouth, cavity, head], lm["mouth"], au, _f(mcfg, "half_width_m", 0.0125))
    if mcfg.get("rest_shape", "closed_smile") != "closed_smile" or mcfg.get("rest_mix"):
        rep["mouth_rest_shape"] = {"shape": mcfg.get("rest_shape", "closed_smile"),
                                   "objects": FF.bake_rest_shape_v2([mouth, cavity, head] + [l[1] for l in lids],
                                                                    mcfg.get("rest_shape", "closed_smile"), mcfg.get("rest_mix"))}
    au_names = [a for a in lib["action_units"]]
    if rep.get("cheek_raise"):
        au_names.append("CheekRaise")
    lid_objs = [o for l in lids for o in l[:3]]
    face_objs = eyes + lid_objs + brows + [mouth, cavity, head]
    if _f(au, "pout_m", 0.0) > 0:
        au_names.append("MouthPout")
    if au.get("split"):
        rep["split_action_units"] = split_action_units(face_objs, list(au["split"]), _f(au, "split_blend_m", 0.006))
        au_names += [n for pair in rep["split_action_units"].values() for n in pair]
    present = sorted({k.name for o in face_objs if o.data.shape_keys for k in o.data.shape_keys.key_blocks[1:] if "@" not in k.name} | {"JawOpen"})
    au_built = [a for a in au_names if a in present]
    presets, jaw_w = bake_presets(face_objs, lib, fs.get("expressions", {}), set(au_built))
    if (ecfg.get("lids") or {}).get("closed_fit"):  # T-113 (opt-in): closed upper lids follow the eyeball (no dome)
        for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):
            rep.setdefault("closed_fit", {})[side] = LIDS.fit_closed_lids(
                up, lash, frames[side], ecfg, r, ecfg["lids"]["closed_fit"], f"Blink.{side}",
                fs.get("blink", {}).get("closed_thickness_m"))
    rep["action_units"] = au_built
    rep["action_units_missing"] = [a for a in au_names if a not in au_built]
    rep["presets"] = presets
    if socket_w:
        rep["lid_shell_exposed"] = FF.shell_exposure(head, [l[0] for l in lids] + [l[1] for l in lids])
        corner = _f(sock_cfg, "corner_deg", 60.0)
        shells = [l[0] for l in lids] + [l[1] for l in lids]
        sk = M.get("face_skin")
        rep["lid_shell_exposed_3q"] = {f"yaw_{int(y)}": LIDS.exposure_from(head, shells, frames, y, corner, r,
                                                                         sk.name if sk else None)
                                       for y in (-35.0, 35.0)}
    rep["lid_corner_extent_m"] = {}
    for (sx, side), (up, lo, lash, c) in zip(SIDES, lids):  # over the basis and every lid key (blink, wide, squint)
        for ob in (up, lo, lash):
            o_, i_ = LIDS.corner_extent(ob, frames[side], sx)
            rep["lid_corner_extent_m"][ob.name] = {"outer": round(o_, 5), "inner": round(i_, 5)}
    rigid = [(o, head_bone) for o in brows + ears + [mouth, cavity] + ([nose_obj] if nose_obj else [])] + [(e, eye_bone.format(s=s)) for e, (_, s) in zip(eyes, SIDES)]
    track = _f(ecfg, "lid_tracking", 0.0)
    rigid.extend(FACE.lid_bindings(lids, head_bone, eye_bone, track, tuple(side for _, side in SIDES)))
    sc = ecfg.get("scale", [1, 1, 1])
    if max(abs(float(k) - 1.0) for k in sc) > 1e-6:
        env = max(einfo[s]["gaze_envelope"] for _, s in SIDES)
        rep.setdefault("notes", []).append(
            "non-spherical eyeball (scale %s): the lids clear its rigid gaze sweep over gaze_range_deg %s (envelope %.3f)"
            % (sc, ecfg.get("gaze_range_deg", [20.0, 12.0]), env))
    engine = {k: v for k, v in lib["engine_expressions"].items() if v in set(au_built) | set(presets)}
    for name in (fs.get("expressions", {}).get("custom") or {}):
        if name in presets:
            engine.setdefault(name[0].lower() + name[1:], name)
    return {"eyes": eyes, "lids": lids, "brows": brows, "ears": ears, "nose": nose_obj, "mouth": mouth, "cavity": cavity, "landmarks": lm,
            "rigid": rigid, "frames": frames, "ctx": ctx, "controls": au_built + presets, "jaw_preset_weights": jaw_w,
            "engine_expressions": engine, "mouth_cfg": mcfg, "report": rep}
