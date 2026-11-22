"""Procedural vocal placeholders (T-195): a small deterministic source-filter voice in numpy.

Every sound made here is a PLACEHOLDER (SOURCES.json `placeholder: true`, licence `project-own`): it stands in for
an owner-recorded or owner-approved CC0 file, which replaces it in content/sounds/library/<cue>/ with no code change.

Model (Klatt-style, simplified): a glottal pulse train (Rosenberg pulse, F0 contour with jitter and shimmer) plus
aspiration noise, through a cascade of time-varying formant resonators; unvoiced parts (breath, /h/) are the same
noise through the same tract. Every sound is a list of segments, each with its own duration, F0 contour, formant
targets (start -> end), voicing and breath amounts. The voice is a neutral child voice (F0 about 300 Hz, formants
about 1.15 x an adult female's); per-character pitch is applied later by the mixer (voices.json), so recorded and
procedural sounds go through the same path.

Deterministic: the same (cue, variant) gives the same samples on the same numpy build (seeded PCG64).
"""
from __future__ import annotations

import math
import zlib

import numpy as np

RATE = 48000

# Child vowel formants (F1, F2, F3, F4) in Hz and bandwidths; about 1.15 x adult female values.
VOWELS = {
    "a": (1000, 1550, 3300, 4300),
    "o": (600, 1000, 3000, 4200),
    "u": (420, 880, 2900, 4100),
    "w": (380, 780, 2800, 4000),
    "i": (380, 3000, 3700, 4700),
    "e": (560, 2400, 3300, 4500),
    "m": (300, 1250, 2700, 3900),  # nasal murmur: the mixer-side low-pass of a closed mouth is in `nasal`
    "h": (900, 1600, 3200, 4300),  # breath: the tract of the following vowel, roughly
}
BANDWIDTHS = (90, 110, 170, 250)


def _seed(*parts: object) -> int:
    return zlib.crc32("|".join(str(p) for p in parts).encode())


def _contour(points: list[tuple[float, float]], n: int) -> np.ndarray:
    """Piecewise-linear contour over n samples from (fraction 0..1, value) points."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return np.interp(np.linspace(0, 1, n, endpoint=False), xs, ys)


def _glottal(f0: np.ndarray, rng: np.random.Generator, jitter=0.012, shimmer=0.08) -> np.ndarray:
    """Rosenberg glottal flow derivative-ish pulse train following the F0 contour."""
    n = len(f0)
    out = np.zeros(n)
    phase = 0.0
    period_jit = 1.0
    amp = 1.0
    i = 0
    # Walk pulse by pulse, so jitter / shimmer change per period.
    while i < n:
        f = max(60.0, float(f0[i])) * period_jit
        T = int(RATE / f)
        if T < 8:
            T = 8
        open_q, close_q = 0.4, 0.16
        t1, t2 = int(T * open_q), int(T * (open_q + close_q))
        k = np.arange(min(T, n - i))
        pulse = np.where(k < t1, 0.5 * (1 - np.cos(np.pi * k / max(t1, 1))),
                         np.where(k < t2, np.cos(0.5 * np.pi * (k - t1) / max(t2 - t1, 1)), 0.0))
        out[i:i + len(k)] = pulse * amp
        i += T
        period_jit = 1.0 + rng.normal(0, jitter)
        amp = max(0.2, 1.0 + rng.normal(0, shimmer))
        phase += 1
    # Flow derivative: the radiated source (spectral tilt about -6 dB/oct after the lip radiation).
    return np.diff(out, prepend=0.0) * 20.0


def _resonate(x: np.ndarray, freq: np.ndarray, bw: float) -> np.ndarray:
    """Second-order resonator with a time-varying centre frequency (unity gain at DC)."""
    r = math.exp(-math.pi * bw / RATE)
    c = -r * r
    b = 2 * r * np.cos(2 * np.pi * np.clip(freq, 50, RATE / 2 - 100) / RATE)
    a = 1 - b - c
    y = np.zeros(len(x))
    y1 = y2 = 0.0
    xs, as_, bs = x.tolist(), a.tolist(), b.tolist()
    ys = [0.0] * len(xs)
    for n in range(len(xs)):
        v = as_[n] * xs[n] + bs[n] * y1 + c * y2
        ys[n] = v
        y2, y1 = y1, v
    y[:] = ys
    return y


def _onepole_lp(x: np.ndarray, cutoff: float) -> np.ndarray:
    a = math.exp(-2 * math.pi * cutoff / RATE)
    out = [0.0] * len(x)
    y = 0.0
    for n, v in enumerate(x.tolist()):
        y = (1 - a) * v + a * y
        out[n] = y
    return np.array(out)


def segment(dur: float, f0: list, vowels: list, voice: list, breath: list, amp: list,
            rng: np.random.Generator, nasal=False, formant_scale=1.0, fade_ms=(6.0, 15.0)) -> np.ndarray:
    """One continuous sound segment (one breath group: no joins inside, so no clicks).

    f0 / voice / breath / amp are contour points [(fraction 0..1, value)]; vowels is [(fraction, vowel name)], the
    formants glide linearly between them. The segment fades in and out over fade_ms."""
    n = max(1, int(dur * RATE))
    f0c = _contour(f0, n)
    vc = _contour(voice, n)
    bc = _contour(breath, n)
    ac = _contour(amp, n)
    src = _glottal(f0c, rng) * vc
    noise = rng.normal(0, 1, n)
    noise = noise - _onepole_lp(noise, 400)  # breath has little low end
    src = src + noise * bc * 0.6
    y = src
    for k in range(4):
        fk = _contour([(fr, VOWELS[v][k]) for fr, v in vowels], n) * formant_scale
        y = _resonate(y, fk, BANDWIDTHS[k] * (1.6 if nasal else 1.0))
    if nasal:
        y = _onepole_lp(y, 900) * 2.0
    return _env_fade(y * ac, *fade_ms)


def _env_fade(x: np.ndarray, ms_in=4.0, ms_out=12.0) -> np.ndarray:
    a = min(len(x) // 2, int(RATE * ms_in / 1000))
    b = min(len(x) // 2, int(RATE * ms_out / 1000))
    x = x.copy()
    if a:
        x[:a] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if b:
        x[-b:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b))
    return x


def _silence(dur: float) -> np.ndarray:
    return np.zeros(int(dur * RATE))


# Cue recipes: variant index v (0, 1, 2...) changes timing, pitch and vowel colour a little.
def gasp_oh(v: int, rng) -> np.ndarray:
    """Surprise: a short inhaled gasp, then a bright falling "oh!"."""
    p = 1.0 + 0.06 * (v - 1)
    gasp = segment(0.20 + 0.03 * v, [(0, 300), (1, 300)], [(0, "h"), (1, "a")], [(0, 0), (1, 0)],
                   [(0, 0.0), (0.25, 1.0), (0.8, 0.8), (1, 0.0)], [(0, 1), (1, 1)], rng, formant_scale=1.05,
                   fade_ms=(10, 25))
    oh = segment(0.32 + 0.04 * v, [(0, 420 * p), (0.25, 470 * p), (1, 300 * p)],
                 [(0, "o"), (1, "u" if v == 2 else "o")],
                 [(0, 0.0), (0.08, 1.0), (0.7, 0.9), (1, 0.0)], [(0, 0.3), (0.1, 0.15), (1, 0.25)],
                 [(0, 1), (0.6, 0.8), (1, 0.0)], rng)
    return np.concatenate([gasp * 0.5, _silence(0.03), oh])


def wow(v: int, rng) -> np.ndarray:
    """Delighted "wow": one glide w -> a -> o -> u, pitch up then down."""
    p = 1.0 + 0.05 * (v - 1)
    return segment(0.55 + 0.05 * v, [(0, 280 * p), (0.2, 330 * p), (0.45, 420 * p), (0.65, 370 * p), (1, 250 * p)],
                   [(0, "w"), (0.22, "a"), (0.62, "o"), (1, "u")],
                   [(0, 0.0), (0.07, 1.0), (0.85, 0.8), (1, 0.0)], [(0, 0.1), (0.8, 0.1), (1, 0.3)],
                   [(0, 0.6), (0.2, 1.0), (0.65, 0.95), (1, 0.0)], rng)


def giggle(v: int, rng) -> np.ndarray:
    """Small giggle: 4-5 short breathy "hee" bursts, stepping down in pitch."""
    p = 1.0 + 0.05 * (v - 1)
    out = []
    for k in range(4 + (v % 2)):
        f = (520 - 30 * k) * p
        e = segment(0.11 + 0.01 * ((k + v) % 2), [(0, f), (0.3, f * 1.04), (1, f * 0.9)],
                    [(0, "h"), (0.3, "i"), (1, "e")],
                    [(0, 0.0), (0.3, 0.2), (0.45, 1.0), (1, 0.0)], [(0, 0.6), (0.3, 0.6), (0.45, 0.35), (1, 0.4)],
                    [(0, 0.5), (0.4, 1.0), (0.8, 0.8), (1, 0)], rng, formant_scale=1.03)
        out += [e * (1.0 - 0.12 * k), _silence(0.05 + 0.01 * (k % 2))]
    return np.concatenate(out)


def laugh(v: int, rng) -> np.ndarray:
    """Small laugh: "ha-ha-ha", 3-4 bursts, falling pitch."""
    p = 1.0 + 0.05 * (v - 1)
    out = []
    for k in range(3 + v % 2):
        f = (430 - 35 * k) * p
        a = segment(0.15, [(0, f), (0.27, f * 1.05), (1, f * 0.88)], [(0, "h"), (0.27, "a"), (1, "a")],
                    [(0, 0.0), (0.2, 0.3), (0.4, 1.0), (1, 0.0)], [(0, 0.7), (0.27, 0.6), (0.4, 0.3), (1, 0.35)],
                    [(0, 0.5), (0.4, 1.0), (0.8, 0.85), (1, 0)], rng)
        out += [a * (1.0 - 0.1 * k), _silence(0.06)]
    return np.concatenate(out)


def hm(v: int, rng) -> np.ndarray:
    """Curious "hm?": closed-mouth hum, rising pitch."""
    p = 1.0 + 0.05 * (v - 1)
    return segment(0.37 + 0.04 * v, [(0, 270 * p), (0.55, 290 * p), (1, 380 * p)], [(0, "m"), (1, "m")],
                   [(0, 0.0), (0.15, 1.0), (0.85, 1.0), (1, 0.0)], [(0, 0.4), (0.12, 0.05), (1, 0.05)],
                   [(0, 0.6), (0.3, 1.0), (1, 0.0)], rng, nasal=True)


def sigh(v: int, rng) -> np.ndarray:
    """Sigh: a long breathy "haah", falling."""
    p = 1.0 + 0.05 * (v - 1)
    return segment(0.65 + 0.05 * v, [(0, 300 * p), (1, 210 * p)], [(0, "a"), (1, "o")],
                   [(0, 0.0), (0.2, 0.35), (0.7, 0.25), (1, 0.0)], [(0, 0.2), (0.15, 1.0), (1, 0.0)],
                   [(0, 1), (1, 1)], rng, fade_ms=(20, 40))


RECIPES = {"gasp_oh": gasp_oh, "wow": wow, "giggle": giggle, "laugh": laugh, "hm": hm, "sigh": sigh}


def make(cue: str, variant: int, peak_dbfs: float = -6.0) -> np.ndarray:
    """Mono float samples at RATE, peak-normalised to `peak_dbfs`."""
    rng = np.random.default_rng(_seed("t195", cue, variant))
    x = RECIPES[cue](variant, rng)
    x = x - np.mean(x)
    x = _env_fade(x)
    peak = float(np.max(np.abs(x)))
    if peak > 0:
        x = x * (10 ** (peak_dbfs / 20) / peak)
    return x
