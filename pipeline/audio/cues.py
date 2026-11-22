"""Vocal cue list from shots, read-only (T-195).

Input: the shot scene files (`<scene>/shot.scene.json`, scene name = the directory name) and the clip assembly
(`assembly.json`: clip frame -> scene, scene frame, shot; written by the episode's assemble step). Nothing is
written next to the shots and no engine code runs: the cue list is derived from the `emotion` actions as authored.

Rule (content/sounds/cues.json): an `emotion` action {character, name, start, intensity=1} gives a cue when
  - its emotion (full name, then base name before '/') has a cue in the map (null / missing = silent),
  - intensity >= minIntensity, and
  - its start frame is a rendered frame of that scene (it is in the assembly) - beats whose onset is hidden in a
    pre-roll or cut away are silent - and the cue frame start + round(lead x onset x fps) is rendered too.
The onset comes from the emotion file's timing (content/emotions/<base>.emotion.json, the variant's patch applied).
A cue less than minGapSeconds after the previous cue of the same character is dropped.

Output `plush.vocalcues/1`: {fps, frames, cues: [{clipFrame, time, scene, sceneFrame, shot, character, personality,
seatX, emotion, intensity, cue, gainDb}]} sorted by clip frame then character.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUE_MAP = ROOT / "content" / "sounds" / "cues.json"
EMOTIONS = ROOT / "content" / "emotions"


def merge_patch(base, patch):
    if not isinstance(patch, dict):
        return patch
    out = dict(base) if isinstance(base, dict) else {}
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = merge_patch(out.get(k), v)
    return out


def emotion_onset(name: str, emotions: Path = EMOTIONS) -> float:
    base, _, variant = name.partition("/")
    p = emotions / f"{base}.emotion.json"
    if not p.is_file():
        return 0.0
    d = json.loads(p.read_text(encoding="utf-8"))
    if variant:
        d = merge_patch(d, d.get("variants", {}).get(variant, {}))
    return float(d.get("timing", {}).get("onset", 0.0))


def rule_for(name: str, cue_map: dict) -> dict | None:
    em = cue_map.get("emotions", {})
    entry = em.get(name, em.get(name.partition("/")[0]))
    if not entry or not entry.get("cue"):
        return None
    return {**cue_map.get("defaults", {}), **entry}


def fps_of(scene: dict) -> float:
    fr = scene.get("frameRate", 24)
    if isinstance(fr, list):
        return fr[0] / (fr[1] if len(fr) > 1 and fr[1] else 1)
    return float(fr)


def derive(shots: list[Path], assembly: dict, cue_map: dict | None = None, emotions: Path = EMOTIONS) -> dict:
    cue_map = cue_map or json.loads(CUE_MAP.read_text(encoding="utf-8"))
    fps = float(assembly["fps"])
    index = {(c["scene"], int(c["frame"])): (i, c.get("shot", "")) for i, c in enumerate(assembly["clip"])}
    raw = []
    for shot in shots:
        scene_name = shot.parent.name
        scene = json.loads(shot.read_text(encoding="utf-8"))
        if abs(fps_of(scene) - fps) > 1e-6:
            raise ValueError(f"{shot}: frame rate {fps_of(scene)} differs from the assembly's {fps}")
        chars = {c["name"]: c for c in scene.get("characters", [])}
        for a in scene.get("actions", []):
            if a.get("type") != "emotion":
                continue
            name, intensity = a.get("name", ""), float(a.get("intensity", 1.0))
            rule = rule_for(name, cue_map)
            if rule is None or intensity < rule["minIntensity"] - 1e-9:
                continue
            start = int(a["start"])
            frame = start + int(round(rule["lead"] * emotion_onset(name, emotions) * fps))
            if (scene_name, start) not in index or (scene_name, frame) not in index:
                continue
            clip_frame, shot_label = index[(scene_name, frame)]
            ch = chars.get(a["character"], {})
            span = 1.0 - rule["minIntensity"]
            t = 1.0 if span <= 0 else min(1.0, (intensity - rule["minIntensity"]) / span)
            gain = rule["levelDb"] + rule["quietDb"] * (1.0 - t)
            raw.append({
                "clipFrame": clip_frame, "time": round(clip_frame / fps, 4), "scene": scene_name,
                "sceneFrame": frame, "shot": shot_label, "character": a["character"],
                "personality": ch.get("personality", a["character"]),
                "seatX": float((ch.get("position") or [0.0])[0]), "emotion": name, "intensity": intensity,
                "cue": rule["cue"], "gainDb": round(gain, 3), "_gap": rule["minGapSeconds"],
            })
    raw.sort(key=lambda c: (c["clipFrame"], c["character"]))
    last: dict[tuple[str, str], float] = {}
    cues = []
    for c in raw:
        key = (c["personality"], c["character"])
        gap = c.pop("_gap")
        if key in last and c["time"] - last[key] < gap:
            continue
        last[key] = c["time"]
        cues.append(c)
    return {"format": "plush.vocalcues", "version": 1, "fps": fps, "frames": len(assembly["clip"]), "cues": cues}
