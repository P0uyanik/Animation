"""Popping: one-frame discontinuities and sudden starts / stops in the bake (joints, joint rotations, face controls,
props, skinned vertices).

Each channel is a per-frame vector x_t with velocity v_t = x_t - x_{t-1} and second difference
a_t = x_{t+1} - 2 x_t + x_{t-1} = v_{t+1} - v_t. A frame t pops when
    |a_t| >= abs_min                                   large enough to see (per kind, thresholds.json)
    |a_t| >= jerk * max(|v_{t-2}| .. |v_{t+3}|)        the velocity changes by that share of the move's peak in one frame
This is animcheck's jerk rule (tools/animcheck: "a speed change of almost half the peak within one frame is a velocity
pop", max_jerk 0.45 on the wrist) applied to every channel, with the peak taken over the six velocities around the
frame: a one-frame spike scores about 2, a move that starts or stops within one frame about 1, a cubic smoothstep
scores 0.38 over 8 frames and 0.55 over 4 (of any speed), a quintic one 0.38 over 8.
Rotations use angles: |v_t| is the rotation angle from t-1 to t, |a_t| the angle between the actual rotation at t+1
and the one constant angular velocity predicts. Mesh vertices: every `mesh_stride`-th vertex of every mesh, skinned
with the bake (morphs included); a part pops on a frame where any sampled vertex does.

Fast by design (thresholds.json "by_design"): saccades (eye bones), blinks (blink / eye-closed morphs) and the eyelid,
lash and eye meshes they move are measured with their own, larger abs_min, not the general one."""
import fnmatch

import numpy as np

KINDS = ("joint", "rotation", "morph", "prop", "prop_rotation", "mesh")
UNITS = {"joint": "mm/f^2", "rotation": "deg/f^2", "morph": "weight/f^2", "prop": "mm/f^2",
         "prop_rotation": "deg/f^2", "mesh": "mm/f^2"}


def lin_terms(x):
    """(F, C, D) -> |a| (F, C), peak |v| around each frame (F, C)."""
    v = np.zeros(x.shape[:2])
    v[1:] = np.linalg.norm(np.diff(x, axis=0), axis=-1)
    a = np.zeros(x.shape[:2])
    a[1:-1] = np.linalg.norm(x[2:] - 2 * x[1:-1] + x[:-2], axis=-1)
    return a, window_peak(v)


def window_peak(v, before=2, after=3):
    """max |v| over t-before .. t+after (velocities v_t = x_t - x_{t-1}) per frame."""
    F = v.shape[0]
    out = np.zeros_like(v)
    for t in range(F):
        out[t] = v[max(0, t - before):min(F, t + after + 1)].max(axis=0)
    return out


def _angle(d):
    return np.degrees(np.arccos(np.clip((np.trace(d, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))


def rot_terms(R):
    """(F, C, 3, 3) -> angular |a| (F, C) and peak angular speed (F, C), degrees."""
    F = R.shape[0]
    step = np.einsum("fcij,fckj->fcik", R[1:], R[:-1])  # R_t R_{t-1}^T
    v = np.zeros(R.shape[:2])
    v[1:] = _angle(step)
    a = np.zeros(R.shape[:2])
    if F > 2:
        pred = np.einsum("fcij,fcjk->fcik", step[:-1], R[1:-1])
        a[1:-1] = _angle(np.einsum("fcij,fckj->fcik", R[2:], pred))
    return a, window_peak(v)


def channels(shot, mesh_stride=16):
    """{kind: [(owner, channel names, |a| (F, C), peak speed (F, C))]}; mesh: the worst sampled vertex per part."""
    out = {k: [] for k in KINDS}
    for c in shot.characters:
        a, p = lin_terms(1000 * c.pivots())
        out["joint"].append((c.name, c.bones, a, p))
        out["rotation"].append((c.name, c.bones) + rot_terms(c.local_rotations()))
        out["morph"].append((c.name, c.morph_names) + lin_terms(c.W[..., None]))
        if mesh_stride:
            names, A, P = [], [], []
            for mi, m in enumerate(c.doc["meshes"]):
                sel = np.arange(0, m["vertices"], mesh_stride)
                if len(sel) == 0:
                    continue
                pos, _ = c.skin(mi, sel)
                a, p = lin_terms(1000 * pos)
                names.append(m["part"])
                A.append(a)
                P.append(p)
            out["mesh"].append((c.name, names, A, P))  # per part: (F, n) arrays (reduced in find)
    for n, M in shot.props.items():
        out["prop"].append(("props", [n]) + lin_terms(1000 * M[:, None, :3, 3]))
        R = M[:, None, :3, :3] / np.linalg.norm(M[:, None, :3, :3], axis=-2, keepdims=True)
        out["prop_rotation"].append(("props", [n]) + rot_terms(R))
    return out


def by_design(kind, name, thr):
    return any(fnmatch.fnmatch(name, pat) for pat in thr["by_design"].get(kind, {}).get("patterns", []))


def _hits(a, peak, t):
    score = a / (peak + t["floor"])
    hit = (a >= t["abs_min"]) & (score >= t["jerk"])
    hit[0] = hit[-1] = False
    return score, hit


def find(shot, thr, mesh_stride=16, chan=None):
    """Pop issues (one per channel and run of popping frames) and the measured distribution per kind."""
    chan = chan if chan is not None else channels(shot, mesh_stride)
    frames = shot.frames
    issues, stats = [], {}
    for kind, groups in chan.items():
        if not groups:
            continue
        gen, des = thr[kind], {**thr[kind], **thr["by_design"].get(kind, {}).get("override", {})}
        seen_a, seen_s, seen_a_design = [], [], []
        for owner, names, A, P in groups:
            cols = range(len(names))
            for j in cols:
                a, p = (A[j], P[j]) if kind == "mesh" else (A[:, j:j + 1], P[:, j:j + 1])
                design = by_design(kind, names[j], thr)
                t = des if design else gen
                score, hit = _hits(a, p, t)
                (seen_a_design if design else seen_a).append(a[1:-1].max(axis=1))
                if not design:
                    big = a[1:-1] >= gen["abs_min"]
                    seen_s.append(np.where(big, score[1:-1], 0).max(axis=1))
                hf = hit.any(axis=1)
                if not hf.any():
                    continue
                fs = np.nonzero(hf)[0]
                for r in np.split(fs, np.nonzero(np.diff(fs) > 2)[0] + 1):
                    sub = np.where(hit[r], a[r], -1)
                    k_r, k_c = np.unravel_index(np.argmax(sub), sub.shape)
                    k = r[k_r]
                    issues.append({"check": "popping", "kind": kind, "owner": owner, "channel": names[j],
                                   "by_design": design, "frames": [int(frames[r[0]]), int(frames[r[-1]])],
                                   "peak_frame": int(frames[k]), "value": round(float(a[k, k_c]), 3),
                                   "peak_speed": round(float(p[k, k_c]), 3), "jerk": round(float(score[k, k_c]), 2),
                                   "unit": UNITS[kind], **({"vertex_sample": int(k_c)} if kind == "mesh" else {})})
        m = np.concatenate(seen_a) if seen_a else np.zeros(1)
        s = np.concatenate(seen_s) if seen_s else np.zeros(1)
        stats[kind] = {"unit": UNITS[kind], "a_p50": q(m, 50), "a_p99": q(m, 99), "a_max": q(m, 100),
                       "jerk_max_above_abs_min": q(s, 100),
                       "by_design_a_max": q(np.concatenate(seen_a_design), 100) if seen_a_design else 0.0}
    return merge(issues), stats


def merge(raw, gap=2):
    """One issue per (kind, owner, by_design) and run of overlapping frames (within `gap`): the worst channel's
    numbers, the frame range of all, the number of channels and the five worst."""
    out = []
    key = lambda i: (i["kind"], i["owner"], i["by_design"])
    for k in sorted({key(i) for i in raw}):
        group = sorted((i for i in raw if key(i) == k), key=lambda i: i["frames"][0])
        runs, cur = [], [group[0]]
        for i in group[1:]:
            if i["frames"][0] <= max(c["frames"][1] for c in cur) + gap:
                cur.append(i)
            else:
                runs.append(cur)
                cur = [i]
        runs.append(cur)
        for r in runs:
            worst = max(r, key=lambda i: i["value"] * i["jerk"])
            top = sorted(r, key=lambda i: -i["value"] * i["jerk"])
            names = list(dict.fromkeys(i["channel"] for i in top))
            out.append({**worst, "frames": [min(i["frames"][0] for i in r), max(i["frames"][1] for i in r)],
                        "channels": len(names), "worst_channels": names[:5]})
    out.sort(key=lambda i: (i["by_design"], -i["value"] * i["jerk"]))
    return out


def q(x, p):
    return round(float(np.percentile(x, p)), 3) if len(x) else 0.0
