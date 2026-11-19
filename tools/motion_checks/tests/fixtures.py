"""Synthetic shots for the motion-check tests: a two-bone package (character.json + geometry.bin) with a skin plane
and a garment plane, a bake whose bone matrices the test chooses, render-pass frames, and EXR files."""
import json
import os
import struct

import numpy as np


def _dump(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f)


def mat_cm(T):
    """4x4 -> 16 column-major floats (the bake's layout)."""
    return [float(x) for x in np.asarray(T, dtype=np.float64).T.ravel()]


def translate(x, y, z):
    T = np.eye(4)
    T[:3, 3] = (x, y, z)
    return T


def rot_y(deg):
    a = np.radians(deg)
    T = np.eye(4)
    T[0, 0], T[0, 2], T[2, 0], T[2, 2] = np.cos(a), np.sin(a), -np.sin(a), np.cos(a)
    return T


def grid(n, y, z, size=0.2):
    xs = np.linspace(-size / 2, size / 2, n)
    return np.array([(x, y + yy, z) for x in xs for yy in xs], dtype=np.float32)


def write_package(d, garment_offset=0.01, n=6, garment_hips=0.0):
    """Package with bones hips (root) and chest; skin plane z=0 and garment plane z=garment_offset, both on chest;
    a hand mesh carried by hips. garment_hips: the garment's skinning weight on hips (the rest on chest), so the
    garment lags the chest. Returns the character.json path."""
    os.makedirs(d, exist_ok=True)
    blob = bytearray()
    meshes = []

    def add(part, P, N, joint, hips=0.0):
        nv = len(P)
        J = np.zeros((nv, 4), np.uint16)
        J[:, 0], J[:, 1] = joint, 0
        W = np.zeros((nv, 4), np.float32)
        W[:, 0], W[:, 1] = 1 - hips, hips
        rec = {"part": part, "material": "M_skin" if part != "garment.shirt.main" else "M_garment", "vertices": nv}
        for key, arr, dt in (("positions", P, "float32"), ("normals", N, "float32"), ("joints", J, "uint16"),
                             ("weights", W, "float32")):
            a = np.ascontiguousarray(arr).astype({"float32": np.float32, "uint16": np.uint16}[dt])
            rec[key] = {"offset": len(blob), "count": int(a.size), "dtype": dt}
            blob.extend(a.tobytes())
            while len(blob) % 4:
                blob.append(0)
        rec["indices"] = {"offset": 0, "count": 0, "dtype": "uint32"}
        meshes.append(rec)

    skin = grid(n, 1.0, 0.0)
    add("body_skin", skin, np.tile([0, 0, 1], (len(skin), 1)), 1)
    g = grid(n, 1.0, garment_offset)
    add("garment.shirt.main", g, np.tile([0, 0, 1], (len(g), 1)), 1, garment_hips)
    hand = grid(3, 0.8, 0.1, 0.05)
    add("hand.L", hand, np.tile([0, 0, 1], (len(hand), 1)), 0)
    doc = {"format": "plush.character_package", "version": 1, "name": "testchar",
           "skeleton": [{"name": "hips", "parent": None, "head": [0, 0.9, 0]},
                        {"name": "chest", "parent": "hips", "head": [0, 1.0, 0]}],
           "meshes": meshes, "morphs": [], "morph_names": [], "morph_inbetweens": {},
           "files": {"geometry.bin": {"path": "geometry.bin"}}}
    with open(os.path.join(d, "geometry.bin"), "wb") as f:
        f.write(bytes(blob))
    p = os.path.join(d, "character.json")
    _dump(doc, p)
    return p


def write_bake(path, package, hips, chest, cup=None, objects=None):
    """Bake with one character 'c' (bones hips, chest): hips / chest are lists of 4x4 skinning matrices per frame."""
    fd = []
    for i, (h, c) in enumerate(zip(hips, chest)):
        f = {"frame": i + 1, "camera": {"position": [0, 1, 3], "target": [0, 1, 0], "up": [0, 1, 0], "focalMm": 32.0,
                                       "sensorWidthMm": 36.0, "fStop": 0.0, "focusDistance": -1.0},
             "characters": {"c": {"skin": mat_cm(h) + mat_cm(c), "morphs": []}}, "props": {}}
        if cup is not None:
            f["props"]["cup"] = mat_cm(cup[i])
        fd.append(f)
    bake = {"format": "plush.shot_bake", "version": 1, "fps": [24, 1], "frames": [1, len(fd)],
            "coordinates": "test", "characters": [{"name": "c", "package": package, "bones": ["hips", "chest"],
                                                     "morphs": [], "supported": True}],
            "frame_data": fd, "objects": objects or [], "render": {"width": 64, "height": 36}}
    _dump(bake, path)
    return path


def write_frames(d, lum, index=None, depth=None, normal=None, vector=None):
    """render_passes.py-style npz frames 0001.. from (F, H, W) luminance (denoised = noisy = lum unless a tuple)."""
    os.makedirs(d, exist_ok=True)
    den, noi = lum if isinstance(lum, tuple) else (lum, lum)
    F, H, W = den.shape
    index = np.zeros((F, H, W), np.uint8) if index is None else index
    depth = np.full((F, H, W), 2.0, np.float16) if depth is None else depth
    normal = np.tile(np.array([0, 0, 1], np.float16), (F, H, W, 1)) if normal is None else normal
    for k in range(F):
        np.savez(os.path.join(d, f"{k + 1:04d}.npz"), denoised=den[k].astype(np.float16), noisy=noi[k].astype(np.float16),
                 index=index[k], depth=depth[k], normal=normal[k],
                 **({} if vector is None else {"vector": vector[k].astype(np.float16)}))


# --- EXR (uncompressed scanline), for the reader test --------------------------------------------------------------
def _attr(name, typ, data):
    return name.encode() + b"\0" + typ.encode() + b"\0" + struct.pack("<i", len(data)) + data


def _header(channels, w, h, part_name=None):
    ch = b"".join(n.encode() + b"\0" + struct.pack("<i", 2) + b"\0\0\0\0" + struct.pack("<ii", 1, 1) for n in sorted(channels))
    hd = _attr("channels", "chlist", ch + b"\0") + _attr("compression", "compression", b"\0")
    win = struct.pack("<4i", 0, 0, w - 1, h - 1)
    hd += _attr("dataWindow", "box2i", win) + _attr("displayWindow", "box2i", win)
    hd += _attr("lineOrder", "lineOrder", b"\0") + _attr("pixelAspectRatio", "float", struct.pack("<f", 1))
    hd += _attr("screenWindowCenter", "v2f", struct.pack("<ff", 0, 0)) + _attr("screenWindowWidth", "float", struct.pack("<f", 1))
    if part_name is not None:
        hd += _attr("name", "string", part_name.encode()) + _attr("type", "string", b"scanlineimage")
        hd += _attr("chunkCount", "int", struct.pack("<i", h))
    return hd + b"\0"


def write_exr(path, parts):
    """parts: [(part name or None, {channel: (H, W) float32})]; one part without a name = a single-part file."""
    multi = len(parts) > 1 or parts[0][0] is not None
    h, w = next(iter(parts[0][1].values())).shape
    out = bytearray(b"\x76\x2f\x31\x01" + struct.pack("<I", 2 | (0x1000 if multi else 0)))
    for name, chans in parts:
        out += _header(chans, w, h, name if multi else None)
    if multi:
        out += b"\0"
    table_at = len(out)
    out += b"\0" * (8 * h * len(parts))
    offsets = []
    for pi, (name, chans) in enumerate(parts):
        for y in range(h):
            offsets.append(len(out))
            row = b"".join(chans[n][y].astype("<f4").tobytes() for n in sorted(chans))
            out += (struct.pack("<i", pi) if multi else b"") + struct.pack("<ii", y, len(row)) + row
    out[table_at:table_at + 8 * len(offsets)] = struct.pack(f"<{len(offsets)}Q", *offsets)
    with open(path, "wb") as f:
        f.write(bytes(out))
