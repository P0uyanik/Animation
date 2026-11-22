"""WAV in / out with the standard library (T-195). Integer PCM only (8/16/24/32 bit), any channel count."""
from __future__ import annotations

import hashlib
import wave
from pathlib import Path

import numpy as np


def read(path: Path, rate: int) -> np.ndarray:
    """Mono float64 samples in -1..1 at `rate` (channels averaged; linear resample when the file's rate differs)."""
    with wave.open(str(path), "rb") as w:
        sr, ch, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        data = w.readframes(n)
    if width == 1:
        x = (np.frombuffer(data, np.uint8).astype(np.float64) - 128) / 128
    elif width == 2:
        x = np.frombuffer(data, "<i2").astype(np.float64) / 32768
    elif width == 3:
        b = np.frombuffer(data, np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / (1 << 23)
    elif width == 4:
        x = np.frombuffer(data, "<i4").astype(np.float64) / (1 << 31)
    else:
        raise ValueError(f"{path}: unsupported sample width {width}")
    x = x.reshape(-1, ch).mean(axis=1)
    if sr != rate:
        x = resample(x, rate / sr)
    return x


def resample(x: np.ndarray, factor: float) -> np.ndarray:
    """Linear-interpolation resample: len(out) = len(x) * factor."""
    n = max(1, int(round(len(x) * factor)))
    return np.interp(np.arange(n) / factor, np.arange(len(x)), x)


def to_pcm16(x: np.ndarray) -> bytes:
    """Float (n,) or (n, ch) -> little-endian 16-bit, rounded, saturating (callers keep peaks under full scale)."""
    q = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    return q.tobytes()


def write(path: Path, x: np.ndarray, rate: int) -> None:
    ch = 1 if x.ndim == 1 else x.shape[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(to_pcm16(x))


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
