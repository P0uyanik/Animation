"""Reach measurements on per-frame arrays (T-135). Pure numpy; no file access.

Units: positions in mm (the bake is in metres; callers scale), frames for time, speeds in mm/f, rotations in deg/f.

A *move* is one wrist (hand-bone pivot) excursion: a run of frames whose speed exceeds `v_on`, runs closer than
`gap` frames merged, kept when its chord (start to end) is at least `min_chord`. Its start / end are where the speed
falls below `edge` x the move's peak on either side of the peak. Everything else is measured inside that window
(plus `pre` frames before for anticipation and `post` frames after for settle)."""
import numpy as np

DEFAULTS = {"v_on": 1.5, "gap": 3, "min_chord": 60.0, "edge": 0.1, "pre": 24, "post": 36,
            "joint_floor": 0.25, "settle_frac": 0.1}


def speed(x):
    """(F, D) -> (F,) |x_t - x_{t-1}|, 0 at t=0."""
    v = np.zeros(len(x))
    v[1:] = np.linalg.norm(np.diff(x, axis=0), axis=-1)
    return v


def ang_speed(R):
    """(F, 3, 3) -> (F,) rotation angle t-1 -> t in degrees, 0 at t=0."""
    v = np.zeros(len(R))
    if len(R) > 1:
        d = np.einsum("fij,fkj->fik", R[1:], R[:-1])
        v[1:] = np.degrees(np.arccos(np.clip((np.trace(d, axis1=1, axis2=2) - 1) / 2, -1, 1)))
    return v


def segment(p, o=None):
    """Wrist positions (F, 3) mm -> list of (t0, t1) position-frame indices of moves."""
    o = {**DEFAULTS, **(o or {})}
    s = speed(p)
    act = np.nonzero(s > o["v_on"])[0]
    runs = []
    for t in act:
        if runs and t - runs[-1][1] <= o["gap"]:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    out = []
    for a, b in runs:
        k = a + int(np.argmax(s[a:b + 1]))
        thr = o["edge"] * s[k]
        i = k
        while i > 1 and s[i - 1] >= thr:
            i -= 1
        j = k
        while j < len(s) - 1 and s[j + 1] >= thr:
            j += 1
        t0, t1 = i - 1, j  # position frames bracketing the moving velocities s[i..j]
        if np.linalg.norm(p[t1] - p[t0]) >= o["min_chord"] and (not out or t0 >= out[-1][1]):
            out.append((t0, t1))
    return out


def path(p, t0, t1):
    """Deviation of the wrist path from its chord p[t0] -> p[t1]."""
    seg = p[t0:t1 + 1]
    c = p[t1] - p[t0]
    L = float(np.linalg.norm(c))
    u = c / max(L, 1e-9)
    rel = seg - p[t0]
    perp = rel - np.outer(rel @ u, u)
    d = np.linalg.norm(perp, axis=1)
    k = int(np.argmax(d))
    length = float(np.linalg.norm(np.diff(seg, axis=0), axis=1).sum())
    bulge = perp[k] / max(d[k], 1e-9)
    return {"chord_mm": L, "max_dev_mm": float(d[k]), "dev_ratio": float(d[k] / max(L, 1e-9)),
            "dev_at": float(k / max(len(seg) - 1, 1)), "arc_ratio": float(length / max(L, 1e-9)),
            "bulge_up": float(bulge[2])}


def velocity(p, t0, t1, fps):
    """Speed profile of the move: peak, its timing, ease-in / ease-out shares, acceleration and edge steps."""
    s = speed(p)[t0 + 1:t1 + 1]  # velocities inside the move
    n = len(s)
    k = int(np.argmax(s))
    pk = float(s[k])
    half = np.nonzero(s >= 0.5 * pk)[0]
    acc = np.diff(np.concatenate([[0.0], s, [0.0]]))  # tangential acceleration incl. start from / stop to rest
    # stall: deepest dip between two speed humps, as a share of the peak (0 = one hump)
    stall, stall_at = 0.0, None
    for i in range(1, n - 1):
        if s[i] <= s[i - 1] and s[i] <= s[i + 1]:
            d = min(s[:i].max(), s[i + 1:].max()) - s[i]
            if d / pk > stall:
                stall, stall_at = float(d / pk), i
    after = s[k:]
    dec2 = float(max((after[j] - after[j + 2] for j in range(len(after) - 2)), default=0.0))
    return {"stall": stall, "stall_at": None if stall_at is None else float((stall_at + 0.5) / n),
            "dec2": dec2, "frames": int(t1 - t0), "peak_mm_f": pk, "peak_m_s": pk * fps / 1000.0,
            "peak_at": float((k + 0.5) / n), "ease_in": float(half[0] / n), "ease_out": float((n - 1 - half[-1]) / n),
            "peak_acc": float(acc.max()), "peak_dec": float(-acc.min()),
            "onset_step": float(s[0] / pk), "stop_step": float(s[-1] / pk)}


def _onset(sig, a, b, floor, frac):
    """First frame in [a, b] where sig exceeds frac x its peak there (and floor); peak frame. None if quiet."""
    w = sig[a:b + 1]
    if not len(w) or w.max() < floor:
        return None, None
    k = int(np.argmax(w))
    thr = max(frac * w[k], floor * 0.5)
    i = k
    while i > 0 and w[i - 1] >= thr:
        i -= 1
    return a + i, a + k


def lead(sig, t0, t1, tpk, o=None):
    """Anticipation of a joint signal relative to the wrist: onset lead and peak lead in frames (+ = joint first)."""
    o = {**DEFAULTS, **(o or {})}
    a, b = max(0, t0 - o["pre"]), min(len(sig) - 1, t1)
    on, pk = _onset(sig, a, b, o["joint_floor"], o["edge"])
    if on is None:
        return {"onset_lead": None, "peak_lead": None, "busy": False, "peak": float(sig[a:b + 1].max(initial=0))}
    # already moving when the window opens: the joint is busy with something else, its onset is not measured
    busy = bool(on == a and a > 0)
    return {"onset_lead": None if busy else int(t0 - on), "peak_lead": int(tpk - pk), "busy": busy,
            "peak": float(sig[pk])}


def overlap(sig, t0, t1, tpk, o=None):
    """Follow-through of a joint signal: peak offset after the wrist peak, and settle after the wrist stops."""
    o = {**DEFAULTS, **(o or {})}
    b = min(len(sig) - 1, t1 + o["post"])
    w = sig[t0:b + 1]
    if not len(w) or w.max() < o["joint_floor"]:
        return {"peak_offset": None, "settle": 0, "after_ratio": 0.0, "peak": float(w.max(initial=0))}
    k = t0 + int(np.argmax(w))
    thr = max(o["settle_frac"] * w.max(), o["joint_floor"])
    tail = sig[t1 + 1:b + 1]
    above = np.nonzero(tail > thr)[0]
    settle = int(above[-1] + 1) if len(above) else 0
    during = sig[t0:t1 + 1].max()
    return {"peak_offset": int(k - tpk), "settle": settle, "settle_capped": bool(len(above) and above[-1] == len(tail) - 1),
            "after_ratio": float(tail.max(initial=0) / max(during, 1e-9)), "peak": float(w.max())}
