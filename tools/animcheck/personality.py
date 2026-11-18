#!/usr/bin/env python3
"""Personality check (T-053): measures a baked shot against each character's personality profile limits.

For every character of the scene with a "personality" profile (content/personality/<id>.json, plush.personality/0,
its "limits" section) it measures on the engine bake (plush.shot_bake/1):

- blinks: the character's blink morph (package expression "blink"); a blink is a run of frames with weight > 0.1 that
  reaches 0.5. Duration = the run's frames (blinks cut by the shot's ends are not checked). A blink starting within DOUBLE_GAP frames@24 of the previous one's end is
  a double blink (the shared face layer's quick second blink, T-046): one rhythm event. Interval = start-to-start of
  rhythm events. Checked: every blink's duration within limits.blink_duration_frames (+-1 frame of sampling), the mean
  rhythm interval within limits.blink_interval_frames;
- reaches (touch / reach actions, measured by animcheck.analyse): the entry move's frames within limits.reach_frames
  (+-1 frame) and the hold within limits.hold_frames (+-1 frame): the longest run of frames after the entry in which
  the wrist stays within HOLD_LEAVE of the entry chord of the run's first frame (the contact / key pose), ending by
  the exit's fastest frame;
  clip gestures are reported (entry frames, dwell, peak speed), not checked against reach limits (a gesture clip is no
  reach). Moves with a chord under min_chord_mm (thresholds.json) are reported, not checked (as in animcheck);
- idle: the median head speed (head widths per frame) on frames outside every gesture window <= limits.idle_motion_max_H_per_frame;
  reported only: the idle head amplitude (half range, H) next to the profile's energy.idle_motion_amplitude, and each
  entry's peak wrist speed (H/f) next to the reference envelope (VISUAL_TARGET primary action 0.018-0.045 H/f).

All frame values are converted to 24 fps. H (head width) is measured from the package geometry: the x extent of the
skin / head-part vertices above the head bone. Exit 0 = within every limit.

    python3 tools/animcheck/personality.py --bake bake.json --scene shot.scene.json [--json report.json]
"""
from __future__ import annotations

import argparse
import array
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import animcheck  # noqa: E402

FRAME_TOL = 1.0  # frames@24: sampling tolerance of counted frame lengths
DOUBLE_GAP = 10.0  # frames@24: a blink this soon after the previous one is its double blink
HOLD_LEAVE = 0.10  # fraction of the entry chord: the wrist has left the hold pose


def find_profile(scene_path: Path, pid: str) -> Path | None:
    d = scene_path.resolve().parent
    while True:
        for sfx in (".json", ".draft.json"):
            cand = d / "content" / "personality" / f"{pid}{sfx}"
            if cand.is_file():
                return cand
        if d == d.parent:
            return None
        d = d.parent


def value(rec):
    return rec.get("value") if isinstance(rec, dict) and "value" in rec else rec


def as_range(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return [float(v), float(v)]
    return [float(v[0]), float(v[1])]


def package_doc(package: str) -> tuple[dict, Path]:
    p = Path(package)
    f = p if p.is_file() else p / "character.json"
    return json.loads(f.read_text()), f.parent


def head_width(package: str) -> float | None:
    """x extent (m) of the skin / head vertices above the head bone (+2 cm: the neck is excluded)."""
    doc, base = package_doc(package)
    heads = {b["name"]: b["head"] for b in doc.get("skeleton", [])}
    if "head" not in heads:
        return None
    hy = heads["head"][1] + 0.02
    geo = base / doc.get("files", {}).get("geometry", "geometry.bin") if isinstance(doc.get("files"), dict) else base / "geometry.bin"
    if not geo.is_file():
        geo = base / "geometry.bin"
    raw = geo.read_bytes()
    lo, hi = math.inf, -math.inf
    for m in doc.get("meshes", []):
        part, mat = str(m.get("part", "")), str(m.get("material", ""))
        if not (part.startswith("head") or "skin" in mat.lower()):
            continue
        pos = m["positions"]
        a = array.array("f")
        a.frombytes(raw[pos["offset"]:pos["offset"] + pos["count"] * 4])
        for i in range(0, len(a) - 2, 3):
            if a[i + 1] > hy:
                lo, hi = min(lo, a[i]), max(hi, a[i])
    return hi - lo if hi > lo else None


def blinks(series: list[float]) -> list[tuple[int, int]]:
    """(start index, length) of every blink: a run above 0.1 that reaches 0.5."""
    out, i, n = [], 0, len(series)
    while i < n:
        if series[i] > 0.1:
            j = i
            while j < n and series[j] > 0.1:
                j += 1
            if max(series[i:j]) >= 0.5:
                out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def within(x: float, r, tol: float = 0.0) -> bool:
    return r[0] - tol <= x <= r[1] + tol


def analyse(bake: dict, scene: dict, scene_path: Path, thresholds: dict | None = None) -> dict:
    fps = bake["fps"][0] / bake["fps"][1]
    to24 = 24.0 / fps
    min_chord = float((thresholds or {}).get("min_chord_mm", 100))
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    order = sorted(frames)
    gest = animcheck.analyse(bake, scene, scene_path)["gestures"]
    windows = animcheck.gestures(scene, scene_path)
    entries = {c["name"]: c for c in bake["characters"] if c.get("supported")}
    report = {"format": "plush.animcheck_personality", "version": 1, "scene": scene.get("name", ""), "fps": fps,
              "characters": [], "failures": []}
    for cd in scene.get("characters", []):
        pid = cd.get("personality")
        if not isinstance(pid, str) or cd["name"] not in entries:
            continue
        name = cd["name"]
        res = {"character": name, "personality": pid}
        fails = []
        prof_file = find_profile(scene_path, pid)
        if not prof_file:
            report["failures"].append(f"{name}: personality '{pid}' not found")
            continue
        prof = json.loads(prof_file.read_text())
        lim = {k: value(v) for k, v in prof.get("limits", {}).items()}
        res["profile"] = str(prof_file.relative_to(HERE.parents[1])) if HERE.parents[1] in prof_file.parents else str(prof_file)
        res["profile_version"] = prof.get("profile_version", "")
        res["limits"] = lim
        entry = entries[name]
        H = head_width(entry["package"])
        res["head_width_m"] = round(H, 4) if H else None
        # Blinks.
        doc, _ = package_doc(entry["package"])
        blink = doc.get("expressions", {}).get("blink")
        morphs = entry.get("morphs", [])
        if blink in morphs:
            k = morphs.index(blink)
            series = [frames[f]["characters"][name]["morphs"][k] for f in order]
            bl = blinks(series)
            durs = [round(n * to24, 2) for _, n in bl]
            events, doubles = [], []
            for i, (s0, n) in enumerate(bl):
                if events and (s0 - (bl[i - 1][0] + bl[i - 1][1])) * to24 < DOUBLE_GAP:
                    doubles.append(order[s0])
                    continue
                events.append(s0)
            ivs = [round((events[i + 1] - events[i]) * to24, 2) for i in range(len(events) - 1)]
            res["blinks"] = {"morph": blink, "count": len(bl), "frames": [order[s] for s, _ in bl], "durations": durs,
                             "double_blinks": doubles, "intervals": ivs,
                             "mean_interval": round(statistics.mean(ivs), 2) if ivs else None}
            if "blink_duration_frames" in lim:
                r = as_range(lim["blink_duration_frames"])
                for (s0, n), f, d in zip(bl, res["blinks"]["frames"], durs):
                    if s0 == 0 or s0 + n >= len(series):
                        continue  # cut by the shot's first / last frame: length unknown
                    if not within(d, r, FRAME_TOL):
                        fails.append(f"{name}: blink at f{f} lasts {d} f@24, outside {r}")
            if "blink_interval_frames" in lim and ivs:
                r = as_range(lim["blink_interval_frames"])
                if not within(res["blinks"]["mean_interval"], r):
                    fails.append(f"{name}: mean blink interval {res['blinks']['mean_interval']} f@24 outside {r}")
            elif "blink_interval_frames" in lim:
                res["blinks"]["note"] = "fewer than two blinks: interval not measured"
        else:
            res["blinks"] = {"note": "no blink morph"}
        # Gestures.
        res["gestures"] = []
        for g in gest:
            if g.get("character") != name or "entry" not in g:
                continue
            e = g["entry"]
            m = {"label": g["label"], "reach_frames": round((e["frames"][1] - e["frames"][0]) * to24, 2),
                 "chord_mm": e["chord_mm"], "checked": e["chord_mm"] >= min_chord}
            if H:
                m["peak_H_per_frame"] = round(e["peak_mm_per_frame"] / 1000.0 / H / to24, 4)
            # Hold: the longest run of frames after the entry that stays within HOLD_LEAVE of the entry chord of
            # its first frame (the contact / key pose, wherever the wrist settles).
            w0 = g["window"][0]
            pts = g["wrist"]
            k0 = e["frames"][1] - w0
            # The run ends by the exit's fastest frame at the latest (the move back is under way).
            sp = g["speed_mm_per_frame"]
            if "exit" in g:
                xa, xb = g["exit"]["frames"][0] - w0, g["exit"]["frames"][1] - w0
                k1 = max(range(xa, min(xb, len(sp))), key=lambda i: sp[i]) if xb > xa else xa
            else:
                k1 = len(pts) - 1
            r = HOLD_LEAVE * e["chord_mm"] / 1000.0
            best = 0
            for a in range(max(0, k0), min(len(pts), k1)):
                b = a
                while b + 1 <= k1 and animcheck.vlen(animcheck.vsub(pts[b + 1], pts[a])) <= r:
                    b += 1
                best = max(best, b - a)
            m["hold_frames"] = round(best * to24, 2) if best >= 2 else None
            m["kind"] = g.get("kind")
            if m["checked"] and m["kind"] in ("touch", "reach"):
                if "reach_frames" in lim and not within(m["reach_frames"], as_range(lim["reach_frames"]), FRAME_TOL):
                    fails.append(f"{name}: {g['label']} entry takes {m['reach_frames']} f@24, outside reach {as_range(lim['reach_frames'])}")
                if "hold_frames" in lim and m.get("hold_frames") is not None and not within(m["hold_frames"], as_range(lim["hold_frames"]), FRAME_TOL):
                    fails.append(f"{name}: {g['label']} holds {m['hold_frames']} f@24, outside {as_range(lim['hold_frames'])}")
            res["gestures"].append(m)
        # Idle head motion outside every gesture window of this character.
        busy = [(w["from"], w["end"]) for w in windows if w["character"] == name]
        ch = animcheck.Character(entry)
        idle = []
        prev = None
        for f in order:
            p = ch.position(frames[f], "head")
            free = not any(lo <= f <= hi for lo, hi in busy)
            if prev is not None and free and prev[0] == f - 1 and p is not None:
                idle.append(animcheck.vlen(animcheck.vsub(p, prev[1])))
            prev = (f, p) if p is not None else None
        if idle and H:
            med = statistics.median(idle) / H / to24
            pts = [ch.position(frames[f], "head") for f in order if not any(lo <= f <= hi for lo, hi in busy)]
            pts = [p for p in pts if p is not None]
            amp = max((max(p[k] for p in pts) - min(p[k] for p in pts)) / 2 for k in range(3)) / H if pts else None
            res["idle"] = {"frames": len(idle), "median_head_H_per_frame": round(med, 5),
                           "p95_head_H_per_frame": round(sorted(idle)[int(0.95 * (len(idle) - 1))] / H / to24, 5),
                           "head_amplitude_H": round(amp, 5) if amp is not None else None,
                           "profile_idle_motion_amplitude_H": value(prof.get("energy", {}).get("idle_motion_amplitude"))}
            if "idle_motion_max_H_per_frame" in lim and med > float(lim["idle_motion_max_H_per_frame"]):
                fails.append(f"{name}: idle head motion {round(med, 5)} H/f > {lim['idle_motion_max_H_per_frame']}")
        res["failures"] = fails
        report["characters"].append(res)
        report["failures"] += fails
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--thresholds", default=str(HERE / "thresholds.json"))
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    scene_path = Path(args.scene)
    rep = analyse(json.loads(Path(args.bake).read_text()), json.loads(scene_path.read_text()), scene_path,
                  json.loads(Path(args.thresholds).read_text()))
    for c in rep["characters"]:
        b = c.get("blinks", {})
        print(f"{c['character']} ({c['personality']} {c.get('profile_version', '')}): H {c.get('head_width_m')} m | "
              f"blinks {b.get('count')} dur {b.get('durations')} mean interval {b.get('mean_interval')} | "
              f"idle {c.get('idle', {}).get('median_head_H_per_frame')} H/f, amplitude {c.get('idle', {}).get('head_amplitude_H')} H "
              f"(profile {c.get('idle', {}).get('profile_idle_motion_amplitude_H')})")
        for g in c["gestures"]:
            note = "" if g["checked"] and g["kind"] in ("touch", "reach") else " (reported only)"
            print(f"  {g['label']}: entry {g['reach_frames']} f, hold {g.get('hold_frames')} f, peak {g.get('peak_H_per_frame')} H/f{note}")
    for f in rep["failures"]:
        print("FAIL", f)
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1) + "\n")
    return 1 if rep["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
