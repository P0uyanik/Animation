"""face_generic/3 lower-face fullness (T-109, opt-in): spec.face.shape.lower_face.

Felt-doll faces in the references are often widest low down: round cheek pads beside the mouth and
a U-shaped jaw that runs into a soft, barely marked chin. face_generic/2's shape options round the outline and fill
the cheekbones; these two add volume lower down. Both are applied to the head mesh right after face.shape (before
any feature is placed), and all default to 0 (absent = unchanged):
  cheek_pad_m           outward size of the low cheek pads; centre at cheek_pad_x * eye x and cheek_pad_below_eye_m
                        (default: the mouth line), radius cheek_pad_radius_m, vertically stretched by cheek_pad_height;
                        direction between outward (radial from the head axis, horizontal) and forward
                        (cheek_pad_forward 0..1); nothing moves above cheek_pad_top_below_eye_m (default 0.03, the
                        eye region keeps its skin)
  jaw_round_m           the jaw line fills out sideways and down between the chin and the jaw corner: a band around
                        jaw_below_eye_m (default: chin_below_eye_m - 0.01), height jaw_band_m, peak at jaw_x of the
                        face half width there; jaw_down (0..1) is the downward share of the motion
Only skin in front of the head's centre (y) and within the falloffs moves; the neck and back of the head stay.
Character-independent: every value is spec data."""
import math

from face_features import _f, _head_coords


def shape_lower_face(head, ctx, cfg, ex, ez, z_mouth, z_chin):
    """Applies spec.face.shape.lower_face to the head mesh. Returns a report (empty when nothing is set)."""
    import numpy as np
    cp, jr = _f(cfg, "cheek_pad_m", 0.0), _f(cfg, "jaw_round_m", 0.0)
    if not (cp or jr):
        return {}
    rep = {}
    world, write = _head_coords(head)
    p = world.copy()
    head_m = (p[:, 2] > z_chin - 0.04) & (p[:, 2] < ez + 0.06)
    yc = float(np.median(p[head_m, 1]))  # head axis (front/back centre) at face height
    front = np.clip((yc - p[:, 1]) / 0.02, 0.0, 1.0)  # 1 in front of the head's centre, fading over 2 cm
    rad_dir = np.stack([p[:, 0], p[:, 1] - yc, np.zeros(len(p))], axis=1)
    rad_dir /= np.maximum(np.linalg.norm(rad_dir, axis=1, keepdims=True), 1e-9)
    if cp:
        rad = _f(cfg, "cheek_pad_radius_m", 0.04)
        hz = _f(cfg, "cheek_pad_height", 1.2)
        fwd = _f(cfg, "cheek_pad_forward", 0.3)
        zc = ez - _f(cfg, "cheek_pad_below_eye_m", ez - z_mouth)
        # nothing moves above cheek_pad_top_below_eye_m (the eyes, lids and socket keep their skin)
        zt = ez - _f(cfg, "cheek_pad_top_below_eye_m", 0.03)
        u = np.clip((zt - p[:, 2]) / 0.015, 0.0, 1.0)
        top = u * u * (3 - 2 * u)
        dirv = rad_dir * (1 - fwd) + np.array([0.0, -1.0, 0.0]) * fwd
        dirv /= np.maximum(np.linalg.norm(dirv, axis=1, keepdims=True), 1e-9)
        for sx in (1, -1):
            x = sx * ex * _f(cfg, "cheek_pad_x", 1.0)
            c = np.array([x, ctx.face_y(None, x, zc), zc])
            dv = p - c
            dv[:, 2] /= hz
            t = np.linalg.norm(dv, axis=1) / rad
            f = np.clip(1 - t * t, 0, None) ** 2 * front * top
            p += dirv * (cp * f)[:, None]
        rep["cheek_pad_m"] = cp
    if jr:
        zj = ez - _f(cfg, "jaw_below_eye_m", ez - z_chin - 0.01)
        band = _f(cfg, "jaw_band_m", 0.025)
        jx = _f(cfg, "jaw_x", 0.6)
        down = _f(cfg, "jaw_down", 0.3)
        sel = np.abs(p[:, 2] - zj) < 0.003
        hw = float(np.abs(p[sel & (p[:, 1] < yc), 0]).max()) if (sel & (p[:, 1] < yc)).any() else ex * 2
        wz = np.exp(-((p[:, 2] - zj) / band) ** 2)
        wx = np.exp(-((np.abs(p[:, 0]) - jx * hw) / (0.45 * hw)) ** 2)
        dirv = rad_dir * math.sqrt(max(1 - down * down, 0.0)) + np.array([0.0, 0.0, -1.0]) * down
        p += dirv * (jr * wz * wx * front)[:, None]
        rep["jaw_round_m"] = jr
        rep["jaw_z_m"] = round(zj, 4)
        rep["jaw_half_width_m"] = round(hw, 4)
    write(p)
    ctx.invalidate()
    return rep
