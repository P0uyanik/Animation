"""Mix a vocal cue list into one track (T-195).

Per cue: pick the sound (library.candidates; the variant by hash), shift its pitch for the character
(voices.json pitchCents + a hashed spread, linear resample), apply the cue gain and the voice level, pan it
(constant power; the seat: scene x position x seatPanScale, clamped to -1..1, unless the voice gives `pan`) and add it
at the cue's clip time. The bus is float; if its peak would pass BUS_PEAK_DBFS (-1 dBFS) the whole track is scaled
down (never clipped). Output: 48 kHz 16-bit PCM WAV, stereo (or mono), exactly frames / fps long.

Deterministic: hash = sha256("<scene>:<sceneFrame>:<character>:<cue>"); variant = hash mod n, spread from the next
bits. The same cue list, library and voices give byte-identical output.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

if __package__:
    from . import library, wavio
else:
    import library
    import wavio

RATE = 48000
BUS_PEAK_DBFS = -1.0
VOICES = library.ROOT / "content" / "sounds" / "voices.json"


def cue_hash(c: dict) -> int:
    return int.from_bytes(hashlib.sha256(f"{c['scene']}:{c['sceneFrame']}:{c['character']}:{c['cue']}".encode())
                          .digest()[:8], "big")


def voice_for(c: dict, voices: dict) -> dict:
    v = dict(voices.get("default", {}))
    v.update(voices.get("characters", {}).get(c.get("personality", ""), {}))
    return v


def plan(cuelist: dict, voices: dict | None = None, sounds: Path = library.SOUNDS) -> list[dict]:
    """The per-cue mixing decisions (sound file, cents, gain, pan), in cue order."""
    voices = voices or json.loads(VOICES.read_text(encoding="utf-8"))
    out = []
    for c in cuelist["cues"]:
        cands = library.candidates(c["cue"], sounds)
        if not cands:
            raise ValueError(f"no sound in the library for cue {c['cue']!r}")
        h = cue_hash(c)
        entry = cands[h % len(cands)]
        v = voice_for(c, voices)
        spread = float(v.get("spreadCents", 0))
        frac = ((h >> 20) % 2001 - 1000) / 1000.0
        cents = float(v.get("pitchCents", 0)) + spread * frac
        pan = v["pan"] if "pan" in v else max(-1.0, min(1.0, c.get("seatX", 0.0) * voices.get("seatPanScale", 1.0)))
        out.append({**c, "sound": entry["path"], "placeholder": bool(entry.get("placeholder")),
                    "cents": round(cents, 2), "gainDb": round(c["gainDb"] + float(v.get("levelDb", 0)), 3),
                    "pan": round(float(pan), 3)})
    return out


def render(cuelist: dict, voices: dict | None = None, sounds: Path = library.SOUNDS, stereo: bool = True):
    """(samples (n,) or (n, 2) float, plan, bus gain in dB)."""
    decisions = plan(cuelist, voices, sounds)
    n = int(round(cuelist["frames"] / cuelist["fps"] * RATE))
    bus = np.zeros((n, 2 if stereo else 1))
    cache: dict[str, np.ndarray] = {}
    for d in decisions:
        if d["sound"] not in cache:
            cache[d["sound"]] = wavio.read(sounds / d["sound"], RATE)
        x = cache[d["sound"]]
        ratio = 2 ** (d["cents"] / 1200)
        x = wavio.resample(x, 1 / ratio) * 10 ** (d["gainDb"] / 20)
        start = int(round(d["clipFrame"] / cuelist["fps"] * RATE))
        if start >= n:
            continue
        x = x[: n - start]
        if stereo:
            th = (d["pan"] + 1) * math.pi / 4
            bus[start:start + len(x), 0] += x * math.cos(th)
            bus[start:start + len(x), 1] += x * math.sin(th)
        else:
            bus[start:start + len(x), 0] += x
    peak = float(np.max(np.abs(bus))) if n else 0.0
    limit = 10 ** (BUS_PEAK_DBFS / 20)
    bus_db = 0.0
    if peak > limit:
        bus *= limit / peak
        bus_db = 20 * math.log10(limit / peak)
    return (bus if stereo else bus[:, 0]), decisions, round(bus_db, 3)
