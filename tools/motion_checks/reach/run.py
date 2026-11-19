"""Reach measurements over a baked shot (T-135). Report only, not a gate.

python3 tools/motion_checks/reach/run.py --bake <run>/bake.json --label e910 --out <dir> [--baseline <old>/reach.json]

Writes <out>/reach.json (format plush.reach_measures/1) and <out>/reach.md. With --baseline, every move is matched
to the baseline move of the same character and side whose start is nearest (within --match frames) and the deltas are
added (and a delta table in reach.md). Methods: measure.py; README.md."""
import argparse
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import measure as M  # noqa: E402
import shot as SH  # noqa: E402

# role -> candidate bone names ({s} = side L/R), first present wins
ROLES = {"wrist": ["hand.{s}", "wrist.{s}"], "shoulder": ["DEF-shoulder.{s}", "shoulder.{s}", "clavicle.{s}"],
         "upper_arm": ["upperArm.{s}", "upper_arm.{s}"],
         "torso": ["chest", "spine.002", "spine.001", "spine"], "hip": ["hips", "pelvis"],
         "neck": ["neck"], "head": ["head"]}
HAIR = re.compile(r"^(hair|DYN-)", re.I)  # spring chains (hair / bun / ringlets)
KEYS = [("velocity", "stall"), ("velocity", "dec2"), ("path", "max_dev_mm"), ("path", "dev_ratio"), ("path", "arc_ratio"), ("velocity", "frames"),
        ("velocity", "peak_m_s"), ("velocity", "peak_at"), ("velocity", "ease_in"), ("velocity", "ease_out"),
        ("velocity", "peak_acc"), ("velocity", "peak_dec"), ("velocity", "onset_step"), ("velocity", "stop_step")]
LEADS = ["shoulder", "shoulder_shift", "torso", "hip", "hip_shift"]
FOLLOW = ["torso", "neck", "head", "hair"]


def find(bones, role, side=None):
    for c in ROLES[role]:
        n = c.format(s=side)
        if n in bones:
            return bones.index(n)
    return None


def signals(ch, side):
    """Per-frame joint signals (deg/f, hip_shift mm/f) and the bone names used."""
    piv = ch.pivots() * 1000.0
    Rw = ch.M[..., :3, :3]
    Rl = ch.local_rotations()
    sig, used = {}, {}

    def put(key, i, s):
        if i is not None:
            sig[key], used[key] = s, ch.bones[i]
    i = find(ch.bones, "shoulder", side)
    put("shoulder", i, None if i is None else M.ang_speed(Rl[:, i]))
    i = find(ch.bones, "upper_arm", side)
    put("shoulder_shift", i, None if i is None else M.speed(piv[:, i]))
    i = find(ch.bones, "torso")
    put("torso", i, None if i is None else M.ang_speed(Rw[:, i]))
    i = find(ch.bones, "hip")
    put("hip", i, None if i is None else M.ang_speed(Rw[:, i]))
    put("hip_shift", i, None if i is None else M.speed(piv[:, i]))
    for r in ("neck", "head"):
        i = find(ch.bones, r)
        put(r, i, None if i is None else M.ang_speed(Rl[:, i]))
    hair = [k for k, b in enumerate(ch.bones) if HAIR.match(b)]
    if hair:
        sig["hair"] = np.max([M.ang_speed(Rl[:, k]) for k in hair], axis=0)
        used["hair"] = f"{len(hair)} bones ({ch.bones[hair[0]]}..)"
    return piv, sig, used


def measure_shot(sh, opts=None, windows=None):
    """windows: optional [(character, side, first frame, last frame)] measured instead of the segmented moves."""
    moves, bones_used = [], {}
    for ch in sh.characters:
        for side in ("L", "R"):
            w = find(ch.bones, "wrist", side)
            if w is None:
                continue
            piv, sig, used = signals(ch, side)
            bones_used[f"{ch.name}.{side}"] = {"wrist": ch.bones[w], **used}
            p = piv[:, w]
            fr = list(sh.frames)
            spans = [(fr.index(a), fr.index(b)) for c, sd, a, b in (windows or []) if (c, sd) == (ch.name, side)]
            for t0, t1 in (spans if windows is not None else M.segment(p, opts)):
                vel = M.velocity(p, t0, t1, sh.fps)
                tpk = t0 + 1 + int(np.argmax(M.speed(p)[t0 + 1:t1 + 1]))
                floors = {"hip_shift": {"joint_floor": 0.5}, "shoulder_shift": {"joint_floor": 0.5}}
                moves.append({
                    "character": ch.name, "side": side,
                    "start": int(sh.frames[t0]), "end": int(sh.frames[t1]), "peak_frame": int(sh.frames[tpk]),
                    "kind": "extend" if np.linalg.norm(p[t1] - piv[t1, find(ch.bones, "hip") or 0]) >
                    np.linalg.norm(p[t0] - piv[t0, find(ch.bones, "hip") or 0]) else "retract",
                    "path": M.path(p, t0, t1), "velocity": vel,
                    "anticipation": {k: M.lead(sig[k], t0, t1, tpk, {**(opts or {}), **floors.get(k, {})})
                                     for k in LEADS if k in sig},
                    "overlap": {k: M.overlap(sig[k], t0, t1, tpk, opts) for k in FOLLOW if k in sig}})
    return {"format": "plush.reach_measures", "version": 1, "bake": sh.path, "fps": sh.fps,
            "frames": [int(sh.frames[0]), int(sh.frames[-1])], "bones": bones_used,
            "options": {**M.DEFAULTS, **(opts or {})}, "moves": moves, "summary": summary(moves)}


def _get(m, sec, k):
    return (m.get(sec) or {}).get(k)


def summary(moves):
    out = {"moves": len(moves), "extend": sum(m["kind"] == "extend" for m in moves)}
    for sec, k in KEYS:
        v = [_get(m, sec, k) for m in moves]
        v = [x for x in v if x is not None]
        out[f"{sec}.{k}"] = float(np.median(v)) if v else None
    for j in LEADS:
        v = [m["anticipation"][j]["onset_lead"] for m in moves if j in m["anticipation"]]
        out[f"lead.{j}.median"] = float(np.median([x for x in v if x is not None])) if any(x is not None for x in v) else None
        out[f"lead.{j}.share_leading"] = float(np.mean([x is not None and x > 0 for x in v])) if v else None
    for j in FOLLOW:
        v = [m["overlap"][j] for m in moves if j in m["overlap"]]
        po = [x["peak_offset"] for x in v if x["peak_offset"] is not None]
        out[f"overlap.{j}.peak_offset"] = float(np.median(po)) if po else None
        out[f"overlap.{j}.settle"] = float(np.median([x["settle"] for x in v])) if v else None
    return out


def compare(rep, base, window=12):
    """Attach to each move the deltas against the nearest baseline move (same character / side)."""
    for m in rep["moves"]:
        cand = [b for b in base["moves"] if b["character"] == m["character"] and b["side"] == m["side"]
                and abs(b["start"] - m["start"]) <= window]
        if not cand:
            m["baseline"] = None
            continue
        b = min(cand, key=lambda b: abs(b["start"] - m["start"]))
        d = {f"{s}.{k}": _get(m, s, k) - _get(b, s, k) for s, k in KEYS}
        for j in LEADS:
            x, y = (m["anticipation"].get(j) or {}).get("onset_lead"), (b["anticipation"].get(j) or {}).get("onset_lead")
            d[f"lead.{j}"] = None if x is None or y is None else x - y
        for j in FOLLOW:
            x, y = m["overlap"].get(j), b["overlap"].get(j)
            d[f"settle.{j}"] = None if not x or not y else x["settle"] - y["settle"]
        m["baseline"] = {"start": b["start"], "delta": d}
    rep["baseline"] = {"bake": base["bake"], "summary": base["summary"]}
    return rep


def _f(x, nd=2):
    return "–" if x is None else (f"{x:+d}" if isinstance(x, int) and not isinstance(x, bool) else f"{x:.{nd}f}")


def markdown(rep, label):
    L = [f"# Reach measurements: {label}", "", f"bake `{rep['bake']}`, frames {rep['frames'][0]}–{rep['frames'][1]}, "
         f"{rep['fps']:g} fps, {len(rep['moves'])} wrist moves (chord ≥ {rep['options']['min_chord']:g} mm).", "",
         "| char | side | frames | kind | chord mm | dev mm (ratio) | arc | peak m/s @ | ease in/out | acc/dec mm/f² "
         "| stall / dec2 | onset/stop step | lead sh/sh-shift/torso/hip/hip-shift | overlap pk torso/neck/head/hair | settle torso/neck/head/hair |",
         "|" + " --- |" * 15]
    for m in rep["moves"]:
        p, v, a, o = m["path"], m["velocity"], m["anticipation"], m["overlap"]
        L.append("| " + " | ".join([
            m["character"], m["side"], f"{m['start']}–{m['end']}", m["kind"], f"{p['chord_mm']:.0f}",
            f"{p['max_dev_mm']:.0f} ({p['dev_ratio']:.2f})", f"{p['arc_ratio']:.2f}",
            f"{v['peak_m_s']:.2f} @ {v['peak_at']:.2f}", f"{v['ease_in']:.2f}/{v['ease_out']:.2f}",
            f"{v['peak_acc']:.1f}/{v['peak_dec']:.1f}", f"{v['stall']:.2f} / {v['dec2']:.1f}", f"{v['onset_step']:.2f}/{v['stop_step']:.2f}",
            "/".join(_f((a.get(j) or {}).get("onset_lead")) for j in LEADS),
            "/".join(_f((o.get(j) or {}).get("peak_offset")) for j in FOLLOW),
            "/".join(_f((o.get(j) or {}).get("settle")) for j in FOLLOW)]) + " |")
    L += ["", "Summary (medians): " + ", ".join(f"{k} {v if isinstance(v, int) else _f(v)}" for k, v in rep["summary"].items()), ""]
    if "baseline" in rep:
        L += [f"## Against baseline `{rep['baseline']['bake']}`", "", "| char | side | start | base start | Δ "
              + " | Δ ".join(k for k in next((m["baseline"]["delta"] for m in rep["moves"] if m["baseline"]), {})) + " |"]
        n = L[-1].count("|") - 1
        L.append("|" + " --- |" * n)
        for m in rep["moves"]:
            if m["baseline"]:
                L.append(f"| {m['character']} | {m['side']} | {m['start']} | {m['baseline']['start']} | "
                         + " | ".join(_f(x) for x in m["baseline"]["delta"].values()) + " |")
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bake", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--baseline")
    ap.add_argument("--match", type=int, default=12)
    ap.add_argument("--window", action="append", help="char.SIDE:first-last, e.g. boy.R:57-76 (repeatable); "
                    "measures these spans instead of the segmented moves")
    a = ap.parse_args(argv)
    win = None
    if a.window:
        win = []
        for w in a.window:
            cs, fr = w.split(":")
            c, sd = cs.rsplit(".", 1)
            f0, f1 = fr.split("-")
            win.append((c, sd, int(f0), int(f1)))
    rep = measure_shot(SH.Shot(a.bake), windows=win)
    if a.baseline:
        with open(a.baseline) as f:
            compare(rep, json.load(f), a.match)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "reach.json"), "w") as f:
        json.dump(rep, f, indent=1)
    with open(os.path.join(a.out, "reach.md"), "w") as f:
        f.write(markdown(rep, a.label or os.path.basename(a.bake)))
    print(f"{len(rep['moves'])} moves -> {a.out}")


if __name__ == "__main__":
    main()
