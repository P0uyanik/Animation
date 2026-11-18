#!/usr/bin/env python3
"""animcheck acting rule (T-097C): acting signature and consistency of a shot against each character's personality
profile (content/personality/<id>.json, plush.personality/0). Character independent: every limit is read from the
profile; nothing here names a character.

    python3 tools/animcheck/acting.py --scene shot.scene.json [--bake bake.json] [--json report.json]

It only warns (flags): the result never fails a check (exit 0 unless the inputs cannot be read). Three rules, run for
every scene character with a "personality" profile:

- **gesture amplitude** (needs a bake): for every clip gesture of the character (touch / reach go to a target the
  layout sets, so they are not gestures here), the largest swing of the arm: the angle at the shoulder (upperArm.<side>
  pivot) between the shoulder-to-wrist line of the window's first frame and of every later frame, / 180 deg (0-1: 0.5 =
  a hanging arm raised to the horizontal). Flagged above the profile's limit + AMP_TOL. Limit:
  `limits.gesture_amplitude_max` if the profile has it, else `energy.gesture_amplitude` (0-1, 1 = the strongest
  believable gesture).
- **notice delay** (scene only): the first glance (`look` action) of the character after an event must start at least
  the profile's notice delay (`reaction.delay_frames[0]`, frames@24; without it the reference `reaction_delay` of
  content/timing/reference_timing.json) after it. Events: the scene's optional `events`
  list ({"time": seconds, "name", "source"}, the fields of plush::ReactionEvent, scene/acting.h; tool-side, the
  engine ignores the key), else every other character's action start (partner acts: every action type but `look`). A
  look counts as the reaction to an event when it starts within REACTION_WINDOW frames@24 of it; a look at the
  shot's first frame is the opening gaze, not a reaction.
- **still hold** (needs a bake): the longest run of frames in which the character's wrists and head move less than
  `timing_still_mm_per_frame` (thresholds.json, T-104) must reach the reference hold (`beats.hold.frames[0]` of
  content/timing/reference_timing.json) times the profile's `tempo.hold_scale` (default 1). Quick characters
  (`tempo.beat_scale` < 1 or `tempo.action_speed` > 1) are marked: a faster tempo shortens beats, never holds.

Frame values at 24 fps (scenes at another rate are scaled)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import animcheck  # noqa: E402
import personality  # noqa: E402
import timing  # noqa: E402

AMP_TOL = 0.10  # 18 deg: measuring tolerance of the gesture amplitude (wrist pivot vs arm line, clip blends)
REACTION_WINDOW = 48  # frames@24: a look this soon after an event is the reaction to it


def num(rec, default=None):
    v = personality.value(rec)
    return default if v is None else v


def swing(bake: dict, entry: dict, window: list[int], side: str) -> float | None:
    """Largest angle (0-1 of 180 deg) at the shoulder between the first frame's shoulder-to-wrist line and a later one."""
    ch = animcheck.Character(entry)
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    lines = []
    for f in range(window[0], window[1] + 1):
        if f in frames:
            s, w = ch.position(frames[f], f"upperArm.{side}"), ch.position(frames[f], f"hand.{side}")
            if s is None or w is None:
                return None
            lines.append(animcheck.vsub(w, s))
    if not lines or animcheck.vlen(lines[0]) < 1e-6:
        return None
    v0, best = lines[0], 0.0
    for v in lines[1:]:
        n = animcheck.vlen(v0) * animcheck.vlen(v)
        if n > 1e-12:
            best = max(best, math.acos(max(-1.0, min(1.0, animcheck.vdot(v0, v) / n))))
    return best / math.pi


def events(scene: dict, fps: float) -> list[dict]:
    """Events in scene frames: the scene's `events` list (seconds, ReactionEvent fields), else partner action starts."""
    if isinstance(scene.get("events"), list):
        f0 = scene.get("frameStart", 1)
        return [{"frame": f0 + float(e.get("time", 0.0)) * fps, "name": e.get("name", ""), "source": e.get("source", "")}
                for e in scene["events"] if isinstance(e, dict)]
    return [{"frame": float(a["start"]), "name": f"{a.get('character', '')} {a.get('type')}", "source": a.get("character", "")}
            for a in scene.get("actions", []) if a.get("type") != "look" and "start" in a]


def char_still_run(bake: dict, name: str, still_mm: float) -> dict:
    """Longest run of frames in which the character's wrists and head move < still_mm per frame."""
    one = dict(bake, characters=[c for c in bake["characters"] if c["name"] == name])
    return timing.still_runs(one, still_mm)


def analyse(scene: dict, scene_path: Path, bake: dict | None = None, thresholds: dict | None = None,
            reference: dict | None = None) -> dict:
    thr = thresholds or json.loads((HERE / "thresholds.json").read_text())
    ref = reference or timing.load_reference()
    fr = scene.get("frameRate", [24, 1])
    fps = fr[0] / fr[1]
    k = 24.0 / fps
    f0 = scene.get("frameStart", 1)
    evs = events(scene, fps)
    gest = animcheck.analyse(bake, scene, scene_path)["gestures"] if bake is not None else []
    entries = {c["name"]: c for c in (bake or {}).get("characters", []) if c.get("supported")}
    report = {"format": "plush.animcheck_acting", "version": 1, "scene": scene.get("name", ""), "characters": [],
              "warnings": []}
    for cd in scene.get("characters", []):
        pid = cd.get("personality")
        if not isinstance(pid, str):
            continue
        name = cd["name"]
        res = {"character": name, "personality": pid, "warnings": []}
        warn = res["warnings"]
        pf = personality.find_profile(scene_path, pid)
        if not pf:
            warn.append(f"{name}: personality '{pid}' not found")
            report["characters"].append(res)
            report["warnings"] += warn
            continue
        prof = json.loads(pf.read_text())
        tempo, lim = prof.get("tempo", {}), prof.get("limits", {})
        beat_scale, speed = float(num(tempo.get("beat_scale"), 1.0)), float(num(tempo.get("action_speed"), 1.0))
        res["quick"] = beat_scale < 1.0 or speed > 1.0
        # Notice delay: first look after each event (not the character's own action).
        delay = personality.as_range(num(prof.get("reaction", {}).get("delay_frames"), ref.get("reaction_delay")))
        looks = sorted(float(a["start"]) for a in scene.get("actions", [])
                       if a.get("type") == "look" and a.get("character") == name and "start" in a and float(a["start"]) > f0)
        res["glances"] = []
        if delay:
            for e in evs:
                if e["source"] == name:
                    continue
                after = [s for s in looks if 0 <= (s - e["frame"]) * k <= REACTION_WINDOW]
                if not after:
                    continue
                d = (after[0] - e["frame"]) * k
                res["glances"].append({"event": e["name"], "event_frame": e["frame"], "look_frame": after[0],
                                       "delay_frames": round(d, 2), "notice_delay_frames": delay[0]})
                if d < delay[0]:
                    warn.append(f"{name}: glance at f{after[0]:g} {d:g} f after '{e['name']}' (f{e['frame']:g}) "
                                f"< notice delay {delay[0]:g} f")
        if bake is not None and name in entries:
            entry = entries[name]
            # Gesture amplitude.
            amp_lim = num(lim.get("gesture_amplitude_max"), num(prof.get("energy", {}).get("gesture_amplitude")))
            res["gestures"] = []
            for g in gest:
                if g.get("character") != name or g.get("kind") != "clip" or "wrist" not in g:
                    continue
                amp = swing(bake, entry, g["window"], g["side"])
                if amp is None:
                    continue
                res["gestures"].append({"label": g["label"], "amplitude": round(amp, 3), "swing_deg": round(180 * amp, 1),
                                        "limit": amp_lim})
                if amp_lim is not None and amp > float(amp_lim) + AMP_TOL:
                    warn.append(f"{name}: {g['label']} amplitude {amp:.2f} ({180 * amp:.0f} deg) > profile {float(amp_lim):g} "
                                f"(+{AMP_TOL:g})")
            # Still hold (quick characters too).
            need = ref["hold"][0] * float(num(tempo.get("hold_scale"), 1.0))
            run = char_still_run(bake, name, thr["timing_still_mm_per_frame"])
            res["hold"] = dict(run, longest_still_frames_24=round(run["longest_still_frames"] * k, 2), required=need)
            if run["longest_still_frames"] * k < need:
                warn.append(f"{name}: {'quick character ' if res['quick'] else ''}never holds: longest still run "
                            f"{run['longest_still_frames'] * k:g} f < hold {need:g} f")
        report["characters"].append(res)
        report["warnings"] += warn
    return report


def summary(rep: dict) -> str:
    return f"acting: {len(rep['characters'])} characters, {len(rep['warnings'])} warnings (warnings only)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--bake", default="")
    ap.add_argument("--thresholds", default=str(HERE / "thresholds.json"))
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    scene_path = Path(a.scene)
    rep = analyse(json.loads(scene_path.read_text()), scene_path,
                  json.loads(Path(a.bake).read_text()) if a.bake else None, json.loads(Path(a.thresholds).read_text()))
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    for w in rep["warnings"]:
        print("WARN", w)
    print(summary(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
