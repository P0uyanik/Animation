"""Shot data for the motion checks: an engine bake (plush.shot_bake/1) with its packages, skinned with numpy.

Bake matrices are column-major world transforms of the skinning frames (global bone transform times
translate(-rest head)), so a bone pivot is M @ head and a skinned vertex is sum_j w_j M_j v (linear blend skinning;
the engine's dual-quaternion option is not used by the packages here). Morph weights from the bake are applied with
the package's in-between shapes (piecewise linear in the weight)."""
import json
import os

import numpy as np


def _load(path):
    with open(path) as f:
        return json.load(f)


def mats(flat):
    """(N, 16) column-major floats -> (N, 4, 4)."""
    return np.asarray(flat, dtype=np.float64).reshape(-1, 4, 4).transpose(0, 2, 1)


class Character:
    def __init__(self, entry, frame_data):
        self.name = entry["name"]
        self.bones = entry["bones"]
        self.package_path = entry["package"]
        self.doc = _load(self.package_path)
        self._blob = None
        sk = {b["name"]: b for b in self.doc["skeleton"]}
        self.head = np.array([sk[b]["head"] if b in sk else [0, 0, 0] for b in self.bones], dtype=np.float64)
        idx = {b: i for i, b in enumerate(self.bones)}
        self.parent = np.array([idx.get((sk.get(b) or {}).get("parent"), -1) for b in self.bones])
        # (F, B, 4, 4) skinning matrices; (F, M) morph weights by the bake's own morph names
        self.M = np.stack([mats(fd["characters"][self.name]["skin"]) for fd in frame_data])
        self.morph_names = entry["morphs"]
        self.W = np.array([fd["characters"][self.name]["morphs"] for fd in frame_data], dtype=np.float64)

    # --- skeleton -------------------------------------------------------------------------------------------------
    def pivots(self):
        """(F, B, 3) world positions of the bone pivots (rest heads carried by the skinning frames)."""
        h = np.concatenate([self.head, np.ones((len(self.head), 1))], 1)
        return np.einsum("fbij,bj->fbi", self.M, h)[..., :3]

    def local_rotations(self):
        """(F, B, 3, 3) bone rotations relative to the parent bone (world rotation for roots)."""
        R = self.M[..., :3, :3]
        out = R.copy()
        has = self.parent >= 0
        out[:, has] = np.einsum("fbji,fbjk->fbik", R[:, self.parent[has]], R[:, has])
        return out

    # --- geometry -------------------------------------------------------------------------------------------------
    @property
    def blob(self):
        if self._blob is None:
            files = self.doc.get("files", {})
            name = files.get("geometry.bin", {}).get("path", "geometry.bin") if isinstance(files.get("geometry.bin"), dict) else "geometry.bin"
            with open(os.path.join(os.path.dirname(self.package_path), name), "rb") as f:
                self._blob = f.read()
        return self._blob

    def array(self, a, comp):
        dt = {"float32": np.float32, "uint32": np.uint32, "uint16": np.uint16}[a["dtype"]]
        return np.frombuffer(self.blob, dtype=dt, count=a["count"], offset=a["offset"]).reshape(-1, comp)

    def mesh_index(self, part):
        return next(i for i, m in enumerate(self.doc["meshes"]) if m["part"] == part)

    def rest(self, mi, sel=None):
        m = self.doc["meshes"][mi]
        P = self.array(m["positions"], 3).astype(np.float64)
        N = self.array(m["normals"], 3).astype(np.float64)
        J = self.array(m["joints"], 4).astype(np.int64)
        Wt = self.array(m["weights"], 4).astype(np.float64)
        if sel is not None:
            P, N, J, Wt = P[sel], N[sel], J[sel], Wt[sel]
        return P, N, J, Wt

    def _joint_map(self):
        """Package skeleton index -> bake bone index."""
        idx = {b: i for i, b in enumerate(self.bones)}
        return np.array([idx.get(b["name"], 0) for b in self.doc["skeleton"]])

    def morph_offsets(self, mi, sel):
        """(F, n, 3) morph displacement of the selected vertices of mesh mi over the shot."""
        n = len(sel)
        out = np.zeros((self.W.shape[0], n, 3))
        pos = {int(v): k for k, v in enumerate(sel)}
        shapes = {}
        for m in self.doc["morphs"]:
            if m["mesh"] != mi:
                continue
            vi = self.array(m["vertices"], 1)[:, 0]
            dp = self.array(m["dpos"], 3)
            keep = [(pos[int(v)], k) for k, v in enumerate(vi) if int(v) in pos]
            if not keep:
                continue
            d = np.zeros((n, 3))
            a, b = zip(*keep)
            d[list(a)] = dp[list(b)]
            shapes[m["name"]] = d
        inb = self.doc.get("morph_inbetweens", {})
        for k, name in enumerate(self.morph_names):
            if name not in shapes:
                continue
            w = self.W[:, k]
            keys = [(0.0, np.zeros((n, 3)))] + [(float(t), shapes.get(s, np.zeros((n, 3)))) for t, s in inb.get(name, [])]
            keys.append((1.0, shapes[name]))
            xs = np.array([t for t, _ in keys])
            for f in np.nonzero(np.abs(w) > 1e-6)[0]:
                x = float(np.clip(w[f], 0, None))
                j = int(np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2))
                t = (x - xs[j]) / (xs[j + 1] - xs[j])
                out[f] += keys[j][1] + t * (keys[j + 1][1] - keys[j][1]) if x <= 1 else x * shapes[name]
        return out

    def skin(self, mi, sel, with_morphs=True):
        """(F, n, 3) skinned positions and (F, n, 3) normals of the selected vertices of mesh mi."""
        P, N, J, Wt = self.rest(mi, sel)
        J = self._joint_map()[J]
        if with_morphs:
            Pm = P[None] + self.morph_offsets(mi, sel)
        else:
            Pm = np.broadcast_to(P, (self.M.shape[0],) + P.shape)
        A = np.einsum("nk,fnkij->fnij", Wt, self.M[:, J])  # (F, n, 4, 4)
        pos = np.einsum("fnij,fnj->fni", A[..., :3, :3], Pm) + A[..., :3, 3]
        nrm = np.einsum("fnij,nj->fni", A[..., :3, :3], N)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-12)
        return pos, nrm


class Shot:
    def __init__(self, bake_path):
        self.path = bake_path
        d = _load(bake_path)
        if d.get("format") != "plush.shot_bake":
            raise SystemExit(f"{bake_path}: not a plush.shot_bake")
        fd = d["frame_data"]
        self.frames = np.array([f["frame"] for f in fd])
        self.fps = d["fps"][0] / d["fps"][1] if isinstance(d["fps"], list) else float(d["fps"])
        self.characters = [Character(c, fd) for c in d["characters"] if c.get("supported", True)]
        self.props = {n: mats([f["props"][n] for f in fd]) for n in (fd[0].get("props") or {})}
        self.objects = d.get("objects", [])
        self.cameras = [f["camera"] for f in fd]
        self.render = d.get("render", {})
        self.scene_path = d.get("scene_path", "")


def project(cam, p, width, height):
    """Pixel (x, y) of world point p through the bake camera (horizontal film fit), or None behind the camera."""
    pos, tgt, up = (np.array(cam[k], dtype=np.float64) for k in ("position", "target", "up"))
    f = tgt - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    d = np.asarray(p, dtype=np.float64) - pos
    z = d @ f
    if z <= 1e-6:
        return None
    k = cam["focalMm"] / (cam["sensorWidthMm"] / 2)
    x, y = (d @ r) / z * k, (d @ u) / z * k * width / height
    return (x + 1) / 2 * width, (1 - y) / 2 * height
