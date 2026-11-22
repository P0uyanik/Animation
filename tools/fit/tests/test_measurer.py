"""T-214 face measurer tests.

Pure tests (NumPy, Pillow) check the mask geometry on synthetic arrays. The validation test renders the auburn
0.14.0 master with bpy (about 15 s on 4 cores; needs tools/bpy_blender.py's bpy module or BLENDER=<exe>, the
released master and T-204's targets) and requires every disagreement with T-204's hand traces to be explained in
docs/evaluation/characters/T-214/explained.json."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import measurer as M  # noqa: E402

ROOT = HERE.parents[2]
AUBURN = ROOT / "assets/characters/girl_auburn_bun_glasses/versions/0.14.0/girl_auburn_bun_glasses_master.blend"


def has_bpy():
    import os
    return bool(os.environ.get("BLENDER")) or importlib.util.find_spec("bpy") is not None


class Geometry(unittest.TestCase):
    def test_flood_and_bbox(self):
        m = np.zeros((20, 20), bool)
        m[2:6, 3:9] = True
        m[10:12, 10:12] = True
        comp = M.flood(m, (4, 3))
        self.assertEqual(comp.sum(), 24)
        self.assertEqual(M.bbox(comp), (3, 2, 9, 6))
        self.assertFalse(M.flood(m, (0, 0)).any())

    def test_open_removes_specks(self):
        m = np.zeros((20, 20), bool)
        m[5:12, 5:12] = True
        m[1, 1] = m[18, 3] = True
        o = M.open3(m)
        self.assertFalse(o[1, 1] or o[18, 3])
        self.assertTrue(o[5:12, 5:12].all())

    def test_head_region_stops_at_occlusion_step(self):
        # face disk at 1.0 m over a neck strip 4 cm farther: the region and the downward chin edge stop at the step
        h = w = 100
        cls = np.zeros((h, w), np.uint8)
        depth = np.full((h, w), np.inf, np.float32)
        yy, xx = np.mgrid[0:h, 0:w]
        face = (xx - 50) ** 2 + (yy - 40) ** 2 < 30 ** 2
        neck = (abs(xx - 50) < 12) & (yy >= 40) & (yy < 95) & ~face
        cls[face | neck] = M.C["skin"]
        depth[face] = 1.0
        depth[neck] = 1.04
        region = M.head_region(cls, depth, (50, 40))
        self.assertTrue(region[face].all())
        self.assertFalse(region[neck].any())
        down = M.occluding_edges(region, depth, lateral=False)
        v, u = np.nonzero(down)
        self.assertEqual(v.max(), 69)  # lowest face row above the neck
        self.assertTrue((abs(u[v == v.max()] - 50) < 12).all())

    def test_camera_round_trip(self):
        m = np.eye(4)
        m[:3, 3] = [0, -1, 0.8]
        rot = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)  # columns x, y (up), z: -Z looks along +Y
        m[:3, :3] = rot
        cam = M.Camera({"camera": {"matrix_world": m.tolist(), "lens": 70.0, "sensor": 36.0}}, 512)
        p = np.array([0.03, 0.1, 0.78])
        u, v, z = cam.project(p)
        self.assertAlmostEqual(z, 1.1)
        self.assertTrue(np.allclose(cam.unproject(u, v, z), p))
        self.assertGreater(u, 256)  # +X right
        self.assertGreater(v, 256)  # below the camera height

    def test_iris_edge_from_shader(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "spec.json"
            p.write_text(json.dumps({"face": {"eyes": {"shader": "felt/1",
                                                        "iris": {"radius": 0.46, "limbal_width": 0.07}}}}))
            self.assertAlmostEqual(M.iris_radius(p)["eye_L"], 0.46 - 0.35 * 0.07)
            p.write_text(json.dumps({"face": {"eyes": {"iris": {"radius": 0.5}}}}))
            self.assertAlmostEqual(M.iris_radius(p)["eye_R"], 0.5)

    def test_t204_definitions_are_used(self):
        mod = M.t204()
        self.assertTrue(callable(mod.values))
        groups = {k for k in M.HAIR_MEASURES}
        self.assertIn("exposed_cheek", groups)


@unittest.skipUnless(has_bpy() and AUBURN.is_file(), "needs bpy (or BLENDER) and the auburn 0.14.0 master")
class Validation(unittest.TestCase):
    def test_auburn_agrees_with_t204_traces(self):
        with tempfile.TemporaryDirectory() as d:
            args = type("A", (), dict(character="auburn", out=str(Path(d) / "v"), blend=None, spec=None, px=1024))
            report = M.cmd_measure(args, validate=True)
        s = report["validation"]["summary"]
        explained = json.loads((ROOT / "docs/evaluation/characters/T-214/explained.json").read_text())["auburn"]
        self.assertEqual(s["missing"], [])
        self.assertEqual(sorted(set(s["disagree"]) - set(explained)), [])
        self.assertGreaterEqual(s["agree"], 51)
        rows = {(r["view"], r["measure"]): r for r in report["validation"]["rows"]}
        for key in ("eye_y", "eye_to_chin", "mouth_width", "mouth_y", "head_roundness", "cheek_width", "iris_size"):
            self.assertTrue(rows[("front", key)]["agree"], key)


if __name__ == "__main__":
    unittest.main()
