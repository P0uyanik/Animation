"""Minimal reader for uncompressed scanline OpenEXR files, single- or multi-part (the multilayer EXRs that
render_passes.py writes with Blender 5: codec NONE, HALF / FLOAT / UINT channels). numpy only; raises ValueError on
anything else (tiled, deep, compressed)."""
import struct

import numpy as np

_DT = {0: np.dtype("<u4"), 1: np.dtype("<f2"), 2: np.dtype("<f4")}
TILED, DEEP, MULTI = 0x200, 0x800, 0x1000


def _attrs(b, p):
    h = {}
    while b[p] != 0:
        e = b.index(b"\0", p)
        e2 = b.index(b"\0", e + 1)
        size = struct.unpack_from("<i", b, e2 + 1)[0]
        h[b[p:e].decode()] = (b[e + 1:e2].decode(), b[e2 + 5:e2 + 5 + size])
        p = e2 + 5 + size
    return h, p + 1


def _channels(raw):
    ch, q = [], 0
    while raw[q] != 0:
        e = raw.index(b"\0", q)
        ch.append((raw[q:e].decode(), _DT[struct.unpack_from("<i", raw, e + 1)[0]]))
        q = e + 17
    return ch


def read(path):
    """{channel name (part-prefixed when the part's channels are not): float32 / uint32 array (H, W)}."""
    with open(path, "rb") as f:
        b = f.read()
    if b[:4] != b"\x76\x2f\x31\x01":
        raise ValueError(f"{path}: not an OpenEXR file")
    flags = struct.unpack_from("<I", b, 4)[0]
    if flags & (TILED | DEEP):
        raise ValueError(f"{path}: tiled / deep EXR not supported")
    p, heads = 8, []
    while True:
        h, p = _attrs(b, p)
        heads.append(h)
        if not flags & MULTI or b[p] == 0:
            break
    if flags & MULTI:
        p += 1
    out = {}
    for part, h in enumerate(heads):
        if h["compression"][1][0] != 0:
            raise ValueError(f"{path}: compressed EXR (write with codec NONE)")
        if "type" in h and h["type"][1].rstrip(b"\0") != b"scanlineimage":
            raise ValueError(f"{path}: part type {h['type'][1]!r} not supported")
        x0, y0, x1, y1 = struct.unpack("<4i", h["dataWindow"][1])
        w, hh = x1 - x0 + 1, y1 - y0 + 1
        offs = np.frombuffer(b, "<u8", hh, p)
        p += 8 * hh
        prefix = ""
        if "name" in h:
            prefix = h["name"][1].decode().rstrip("\0")
        ch = _channels(h["channels"][1])
        names = [n if (not prefix or n.startswith(prefix)) else f"{prefix}.{n}" for n, _ in ch]
        planes = [np.empty((hh, w), d) for _, d in ch]
        skip = 12 if flags & MULTI else 8  # (part number,) y, data size
        for row, o in enumerate(offs):
            o = int(o) + skip
            for (_, d), pl in zip(ch, planes):
                pl[row] = np.frombuffer(b, d, w, o)
                o += w * d.itemsize
        out.update(zip(names, planes))
    return out
