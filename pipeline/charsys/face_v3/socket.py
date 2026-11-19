"""face_generic/3 lid socket (T-089): face_features.lid_socket (face_generic/2, T-065/T-081) with shells that end at
the eye corners. Copied, not imported, so face_generic/2 output stays byte-identical; the only change is that the
cover radius is per vertex: inside a shell's kept span it is the shell's outer radius (as in v2), past the trim it
falls smoothly to the eyeball radius (+ clearance), so the skin closes over the eyeball's sides instead of being lifted
over a shell that is no longer there. Without trims (`trim` absent in every side) the result equals lid_socket."""
import math

from face_features import _f, _edge_table, _head_coords, _smooth


def _trimmed_radius(uc, s, r_out, clear, zone):
    """Per-vertex cover radius (unit directions uc in the eye frame). s["trim"][zone] = {"outer_x", "inner_x", "back_y", "soft", "cover_margin", "eye_clearance"}: the
    shells keep |x| <= bound (frame units of the eye radius r, x signed towards the outer corner by sx). zone = "up" | "lo"."""
    import numpy as np
    R = np.full(len(uc), r_out + clear)
    t = (s.get("trim") or {}).get(zone)
    if not t:
        return R
    r_eye = s["r"] * (1.0 + float(t.get("eye_clearance", 0.0))) + clear
    xo = uc[:, 0] * s["sx"] * r_out  # x of the shell point in this direction, positive towards the outer corner
    soft = float(t.get("soft", 0.06)) * s["r"]
    margin = float(t.get("cover_margin", 0.04)) * s["r"]  # the skin stays over the cut edge before it descends
    w = np.zeros(len(uc))
    if t.get("outer_x") is not None:
        w = np.maximum(w, _smooth((xo - t["outer_x"] * s["r"] - margin) / soft))
    if t.get("inner_x") is not None:
        w = np.maximum(w, _smooth((-xo - t["inner_x"] * s["r"] - margin) / soft))
    if t.get("back_y") is not None:  # shell point behind the back cut (y > -back): no shell there
        w = np.maximum(w, _smooth((uc[:, 1] * r_out + t["back_y"] * s["r"] - margin) / soft))
    return R + (r_eye - R) * w


def lid_socket_v3(head, ctx, sides, cfg):
    """Blends the lids into the skin (face_generic/2). In each eye's frame (azimuth a around the forward axis,
    elevation e), with the lid edges e_up(a) and e_lo(a): above the upper edge the skin stays behind the lid shell for
    band_deg (the visible lid band), rises over ramp_deg to just outside the shell (clearance_m; where it crosses the
    shell is the crease) and blends back to the original face over reach_deg; the same below the lower edge
    (lower_band_deg). Skin far off the shell (radial_reach x radius) and the opening itself stay as they are. Upper
    and lower profiles blend smoothly at the eye corners. The lid shells therefore show only as a narrow band at
    their edge; the rest lies under the face skin.
    sides: [{"side", "T" (eye frame), "r", "up_edge", "lo_edge" (unit directions), "r_up_out", "r_lo_out"}].
    Returns (report, per-side weights {"up", "lo", "T"} for the lid-following shape keys)."""
    import numpy as np
    band_up = math.radians(_f(cfg, "band_deg", 7.0))
    band_lo = math.radians(_f(cfg, "lower_band_deg", _f(cfg, "band_deg", 7.0)))
    ramp = math.radians(_f(cfg, "ramp_deg", 6.0))
    reach = math.radians(_f(cfg, "reach_deg", 24.0))
    clear = _f(cfg, "clearance_m", 0.0006)
    inner = _f(cfg, "inner_scale", 0.95)
    corner = math.radians(_f(cfg, "corner_deg", 60.0))
    # T-081 (opt-in; defaults = the T-065 constants, so existing builds are unchanged): azimuth width over which the
    # skin at an eye corner changes from the lid band (behind the shell) to covering the shell, and over which the
    # lid edges close in beyond the corner. A wider blend turns the step at the corner into a gentle slope.
    cblend = math.radians(_f(cfg, "corner_blend_deg", 10.0))
    cclose = math.radians(_f(cfg, "corner_close_deg", 12.0))
    follow_reach = math.radians(_f(cfg, "follow_reach_deg", _f(cfg, "reach_deg", 24.0) * 0.6))
    fa = math.radians(_f(cfg, "follow_azimuth_deg", 40.0))
    world, write = _head_coords(head)
    p = world.copy()
    weights, rep = {}, {}
    smooth_sel = []
    wall_sel = []  # T-081: the socket wall (lid band and ramp outside the opening), for the opt-in wall smoothing
    corner_sel = []  # T-089b: skin at the eye corners (opening included), for the opt-in corner relax
    crel = math.radians(_f(cfg, "corner_relax_deg", 14.0))
    soft = _f(cfg, "cover_softness", 0.12)

    ramp_lo = math.radians(_f(cfg, "lower_ramp_deg", _f(cfg, "ramp_deg", 6.0)))  # steeper lower wall (less lit slope)

    def profile(delta, dc, band, R_s, behind, radial, ramp=ramp):
        """Skin radius along one lid: behind the eye under the lid band, then over the shell (a smooth maximum of the
        face and the shell's outer radius, so the face is only raised where the shell would show). Continuous in
        delta, starting from the opening's own value (behind) at the edge."""
        k = soft * radial / 0.4
        cover = 0.5 * (dc + R_s + np.sqrt((dc - R_s) ** 2 + k * k))
        start = max(band - ramp, 0.0)
        rise = _smooth((delta - start) / max(band - start, math.radians(1.0)))
        back = _smooth((delta - band) / reach) * _smooth((dc - R_s) / (0.5 * radial))  # blend back where the face is in front
        back = np.maximum(back, _smooth((dc - R_s - 0.5 * radial) / radial))  # surfaces far in front (temples, cheeks) stay
        cover = cover * (1 - back) + dc * back
        return behind + (cover - behind) * rise, back
    for s in sides:
        T = np.array(s["T"])
        Ti = np.linalg.inv(T)
        q = p @ Ti[:3, :3].T + Ti[:3, 3]
        d = np.linalg.norm(q, axis=1)
        u = q / np.maximum(d, 1e-9)[:, None]
        cand = (u[:, 1] < -0.05) & (d < s["r"] * 2.2)
        uc, dc = u[cand], d[cand]
        a = np.arctan2(uc[:, 0], -uc[:, 1])
        e = np.arcsin(np.clip(uc[:, 2], -1, 1))
        ac = np.clip(a, -corner, corner)
        tu, tl = _edge_table(s["up_edge"]), _edge_table(s["lo_edge"])
        e_up = np.interp(ac, tu[0], tu[1])
        e_lo = np.interp(ac, tl[0], tl[1])
        # beyond the corner the edges close in towards their mean (the opening ends)
        over = np.abs(a) - corner
        mid = (e_up + e_lo) / 2
        k = _smooth(over / cclose)
        e_up = e_up + (mid - e_up) * k
        e_lo = e_lo + (mid - e_lo) * k
        du, dl = e - e_up, e_lo - e
        inside = (du < 0) & (dl < 0)
        radial = _f(cfg, "radial_reach", 0.4) * s["r"]
        t_in = s["r"] * inner
        cr = _f(cfg, "carve_reach", 0.15) * s["r"]  # only skin close in front of the eye is carved (not the corners' skin)
        fo = (1.0 - _smooth((np.abs(a) - (corner - cblend)) / cblend)) * (1.0 - _smooth((dc - s["r"] - cr) / cr))
        behind = np.where(dc > t_in, dc + (t_in - dc) * fo, dc)  # the opening: skin in front of the eyeball moves behind it
        R_up = _trimmed_radius(uc, s, s["r_up_out"], clear, "up")  # v3: past a shell's trim the skin covers the eyeball
        R_lo = _trimmed_radius(uc, s, s["r_lo_out"], clear, "lo")
        if s.get("lo_fit") is not None:  # T-109 (opt-in): the lower lid follows the eyeball; the skin over it too
            R_lo = np.minimum(R_lo, s["lo_fit"](uc) + s["r_lo_out"] - s["r_lo"] + clear)
        nu, bu = profile(du, dc, band_up, R_up, behind, radial)
        nl, bl = profile(dl, dc, band_lo, R_lo, behind, radial, ramp_lo)
        # beyond the eye corners there is no opening and no lid band: the skin only covers the shells
        cf = 1.0 - _smooth((np.abs(a) - corner) / cblend + 0.5)
        kk = soft * radial / 0.4
        for nn, R_s in ((nu, R_up), (nl, R_lo)):
            cov = 0.5 * (dc + R_s + np.sqrt((dc - R_s) ** 2 + kk * kk))
            cov = cov + (dc - cov) * _smooth((dc - R_s - 0.5 * radial) / radial)
            nn[:] = cov + (nn - cov) * cf
        zu = _smooth((du - dl) / math.radians(8.0) + 0.5)  # 1 = nearer the upper lid (further above it than below the lower)
        newd = np.where(inside, behind, zu * nu + (1 - zu) * nl)
        fw = _smooth((-uc[:, 1] - 0.05) / 0.35)  # the socket fades out towards the eye's sides
        dd = newd - dc
        if cfg.get("cover_sides"):  # keep the cover over the shells at the eye's sides (only the carving fades)
            newd = dc + np.where(dd > 0, dd * _smooth((-uc[:, 1] - 0.05) / 0.12), dd * fw)  # short fade at the region edge
        else:
            newd = dc + dd * fw
        q[cand] = uc * newd[:, None]
        far = np.where(zu > 0.5, du - band_up, dl - band_lo) > math.radians(3.0)
        wsm = (zu * (1 - bu) + (1 - zu) * (1 - bl)) * fw * cf + (1 - cf) * fw  # where the skin covers the shells
        keep = far & ~inside & (wsm > 0.02)
        smooth_sel.append((np.where(cand)[0][keep], wsm[keep]))
        wall_sel.append(np.where(cand)[0][~far & ~inside & (fw * np.maximum(cf, 0.0) + (1 - cf) * fw > 0.02)])
        cw_ = _smooth((np.abs(a) - (corner - crel)) / max(crel, 1e-6)) * (1.0 - _smooth((dc - 1.6 * s["r"]) / (0.2 * s["r"]))) * fw
        corner_sel.append((np.where(cand)[0][cw_ > 0.02], cw_[cw_ > 0.02]))
        # lid-following weights (EyeWide): the skin from just inside the edge to the crease, over the eye's width
        azw = 1.0 - _smooth((np.abs(a) - fa) / math.radians(35.0))
        azw = azw * (1.0 - _smooth((dc - R_up) / (0.35 * s["r"])))  # skin away from the eye moves less
        wu_ = _smooth((du + band_up) / band_up) * (1.0 - _smooth((du - band_up) / follow_reach)) * azw * (1 - bu * _smooth((du - band_up) / math.radians(2.0)))
        wl_ = _smooth((dl + band_lo) / band_lo) * (1.0 - _smooth((dl - band_lo) / (0.4 * follow_reach))) * azw * (1 - bl * _smooth((dl - band_lo) / math.radians(2.0)))
        wu, wl = np.zeros(len(p)), np.zeros(len(p))
        idx = np.where(cand)[0]
        wu[idx], wl[idx] = wu_ * zu, wl_ * (1 - zu)
        weights[s["side"]] = {"up": wu, "lo": wl, "T": s["T"]}
        p = q @ T[:3, :3].T + T[:3, 3]
        rep[s["side"]] = {"vertices": int(cand.sum()), "opening": int(inside.sum()),
                          "moved_max_m": round(float(np.abs(newd - dc).max()) if len(dc) else 0.0, 4)}
    # gentle Laplacian smoothing of the covered / blended skin (never the lid band or the opening): removes the small
    # ripples a coarse cheek surface gets when it is pulled onto the shell
    it = int(_f(cfg, "smooth_iterations", 4))
    if it > 0 and smooth_sel:
        sel = np.zeros(len(p), bool)
        wsel = np.zeros(len(p))
        for idx_s, w_s in smooth_sel:
            sel[idx_s] = True
            wsel[idx_s] = np.maximum(wsel[idx_s], w_s)
        me = head.data
        ed = np.empty(len(me.edges) * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", ed)
        ed = ed.reshape(-1, 2)
        ed = ed[sel[ed[:, 0]] | sel[ed[:, 1]]]
        deg = np.bincount(ed.ravel(), minlength=len(p)).astype(float)
        for _ in range(it):
            acc = np.zeros_like(p)
            np.add.at(acc, ed[:, 0], p[ed[:, 1]])
            np.add.at(acc, ed[:, 1], p[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            p[sel] += (0.5 * wsel[sel])[:, None] * (avg[sel] - p[sel])  # fades out with the cover: no groove at its edge
        rep["smoothed_vertices"] = int(sel.sum())
    # T-081 (opt-in, default 0 = unchanged): relax the socket wall itself. Pulling a refined, irregular cheek surface
    # radially onto the lid profile leaves narrow pleats in the wall at the eye corners (sharp folds that shade as
    # dark specks); a few Laplacian passes over the wall and the covered skin, with the opening's own vertices fixed,
    # remove them while keeping the wall's depth profile.
    wit = int(_f(cfg, "wall_smooth_iterations", 0))
    if wit > 0 and wall_sel:
        sel = np.zeros(len(p), bool)
        for idx_s in wall_sel:
            sel[idx_s] = True
        for idx_s, w_s in smooth_sel:
            sel[idx_s[w_s > 0.2]] = True
        me = head.data
        ed = np.empty(len(me.edges) * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", ed)
        ed = ed.reshape(-1, 2)
        ed = ed[sel[ed[:, 0]] | sel[ed[:, 1]]]
        deg = np.bincount(ed.ravel(), minlength=len(p)).astype(float)
        f = _f(cfg, "wall_smooth_factor", 0.5)
        for _ in range(wit):
            acc = np.zeros_like(p)
            np.add.at(acc, ed[:, 0], p[ed[:, 1]])
            np.add.at(acc, ed[:, 1], p[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            p[sel] += f * (avg[sel] - p[sel])
        rep["wall_smoothed_vertices"] = int(sel.sum())
    # T-089b (opt-in, default 0 = unchanged): relax the skin at the eye corners, the opening's own vertices included.
    # A wider (less narrowed) eyeball makes the opening's corner meet the socket wall at a sharp fold that the wall
    # smoothing cannot reach (it keeps the opening fixed); a few weighted passes in a narrow azimuth band at each
    # corner (corner_relax_deg inside the corner and beyond it, fading out with distance) turn it into a slope.
    cit = int(_f(cfg, "corner_relax_iterations", 0))
    if cit > 0 and corner_sel:
        wsel = np.zeros(len(p))
        for idx_s, w_s in corner_sel:
            wsel[idx_s] = np.maximum(wsel[idx_s], w_s)
        sel = wsel > 0
        me = head.data
        ed = np.empty(len(me.edges) * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", ed)
        ed = ed.reshape(-1, 2)
        ed = ed[sel[ed[:, 0]] | sel[ed[:, 1]]]
        deg = np.bincount(ed.ravel(), minlength=len(p)).astype(float)
        f = _f(cfg, "corner_relax_factor", 0.5)
        for _ in range(cit):
            acc = np.zeros_like(p)
            np.add.at(acc, ed[:, 0], p[ed[:, 1]])
            np.add.at(acc, ed[:, 1], p[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            p[sel] += (f * wsel[sel])[:, None] * (avg[sel] - p[sel])
        rep["corner_relaxed_vertices"] = int(sel.sum())
    write(p)
    ctx.invalidate()
    return rep, weights
