"""Fixture tests for tools/motion_checks (T-125): python3 tools/motion_checks/tests/test_motion_checks.py"""
import json
import os
import sys
import tempfile
import unittest

import numpy as np


def _load(path):
    with open(path) as f:
        return json.load(f)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import exr  # noqa: E402
import fixtures as FX  # noqa: E402
import flicker  # noqa: E402
import frames as FR  # noqa: E402
import penetration as PEN  # noqa: E402
import popping  # noqa: E402
import run as RUN  # noqa: E402
import shot as SH  # noqa: E402

THR = RUN.load_thresholds()
# flicker fixtures are synthetic: they use the generic limits (the "default" entries), not the per-region numbers
# measured on e907 / e909
FLICKER_GENERIC = {**THR["flicker"], **{k: {"default": THR["flicker"][k]["default"]}
                                        for k in ("held_noise", "flip_share", "tile_flip_share")}}
F = 40


def ease(n, total, start=10):
    """Positions of a cubic-smoothstep move of `total` over n frames starting at `start`, held before and after."""
    t = np.clip((np.arange(F) - start) / n, 0, 1)
    return total * (3 * t ** 2 - 2 * t ** 3)


class FakeShot:
    frames = np.arange(1, F + 1)


def chan_of(kind, x, names=("ch",), owner="c"):
    """A popping channel group from (F, C, D) positions (lin) or (F, C, 3, 3) rotations."""
    a, p = popping.rot_terms(x) if kind.endswith("rotation") else popping.lin_terms(x)
    return {kind: [(owner, list(names), a, p)]}


def counted(issues):
    return [i for i in issues if not i.get("by_design")]


class Popping(unittest.TestCase):
    def find(self, chan):
        return popping.find(FakeShot, THR["popping"], chan=chan)[0]

    def test_eased_fast_move_is_not_a_pop(self):
        x = np.zeros((F, 1, 3))
        x[:, 0, 0] = ease(8, 400.0)  # 400 mm in 8 frames: 75 mm/f peak, eased
        self.assertEqual(counted(self.find(chan_of("joint", x))), [])

    def test_one_frame_spike_pops(self):
        x = np.zeros((F, 1, 3))
        x[:, 0, 0] = ease(12, 200.0)
        x[20, 0, 1] += 20.0  # 20 mm sideways for one frame
        iss = counted(self.find(chan_of("joint", x)))
        self.assertEqual(len(iss), 1)
        self.assertLessEqual(iss[0]["frames"][0], 21)
        self.assertGreaterEqual(iss[0]["frames"][1], 21)
        self.assertGreater(iss[0]["jerk"], 1.0)

    def test_step_pops(self):
        x = np.zeros((F, 1, 3))
        x[25:, 0, 2] = 30.0  # a 30 mm jump between frames 25 and 26
        iss = counted(self.find(chan_of("joint", x)))
        self.assertEqual(len(iss), 1)
        self.assertIn(iss[0]["peak_frame"], (25, 26))

    def test_small_spike_below_visibility(self):
        x = np.zeros((F, 1, 3))
        x[20, 0, 0] = 2.0  # 2 mm: below abs_min
        self.assertEqual(counted(self.find(chan_of("joint", x))), [])

    def test_rotation_spike_and_smooth_turn(self):
        def R(deg):
            return FX.rot_y(deg)[:3, :3]
        smooth = np.stack([R(a) for a in ease(10, 90.0)])[:, None]
        self.assertEqual(counted(self.find(chan_of("rotation", smooth))), [])
        spiky = smooth.copy()
        spiky[30, 0] = R(90.0 + 15.0)
        iss = counted(self.find(chan_of("rotation", spiky)))
        self.assertEqual(len(iss), 1)
        self.assertIn(iss[0]["peak_frame"], (30, 31, 32))

    def test_saccade_is_by_design(self):
        x = np.zeros((F, 1, 3, 3)) + np.eye(3)
        x[20:, 0] = FX.rot_y(20.0)[:3, :3]  # a 20 degree eye jump in one frame
        iss = self.find(chan_of("rotation", x, names=("eye.L",)))
        self.assertEqual(counted(iss), [])
        iss = self.find(chan_of("rotation", x, names=("forearm.L",)))
        self.assertEqual(len(counted(iss)), 1)

    def test_channels_merge_into_one_issue(self):
        x = np.zeros((F, 3, 3))
        x[20, :, 0] = [20.0, 25.0, 30.0]
        iss = counted(self.find(chan_of("joint", x, names=("a", "b", "c"))))
        self.assertEqual(len(iss), 1)
        self.assertEqual(iss[0]["channels"], 3)
        self.assertEqual(iss[0]["channel"], "c")


class Bake(unittest.TestCase):
    """Skinning from a synthetic package and bake: pivots, mesh-level pops and the body-garment check."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def bake(self, chest_z, garment_offset=0.01):
        pkg = FX.write_package(os.path.join(self.d, "pkg"), garment_offset)
        hips = [np.eye(4)] * F
        chest = [FX.translate(0, 0, z) for z in chest_z]
        return SH.Shot(FX.write_bake(os.path.join(self.d, "bake.json"), pkg, hips, chest))

    def test_pivots_follow_skinning_matrices(self):
        s = self.bake(np.linspace(0, 0.1, F))
        P = s.characters[0].pivots()
        np.testing.assert_allclose(P[-1, 1], [0, 1.0, 0.1], atol=1e-9)
        np.testing.assert_allclose(P[:, 0], np.tile([0, 0.9, 0], (F, 1)), atol=1e-9)

    def test_mesh_pop_from_bake(self):
        z = ease(10, 0.2)
        z[30] += 0.02  # the chest (and the skin and garment it carries) jumps 20 mm for one frame
        s = self.bake(z)
        iss = counted(popping.find(s, THR["popping"], mesh_stride=1)[0])
        kinds = {i["kind"] for i in iss}
        self.assertIn("mesh", kinds)
        self.assertIn("joint", kinds)
        mesh = [i for i in iss if i["kind"] == "mesh"][0]
        self.assertIn(mesh["peak_frame"], (30, 31, 32))
        self.assertIn("body_skin", mesh["worst_channels"])

    def test_garment_clear_when_it_moves_with_the_body(self):
        s = self.bake(ease(10, 0.2))
        self.assertEqual(PEN.garment(s, THR["interpenetration"])[0], [])

    def test_garment_sinking_under_the_skin(self):
        pkg = FX.write_package(os.path.join(self.d, "pkg"), 0.01, garment_hips=0.4)
        z = np.zeros(F)
        z[20:26] = 0.05  # the chest moves 50 mm forward for six frames; the garment follows only 60 %: 10 mm under
        s = SH.Shot(FX.write_bake(os.path.join(self.d, "bake.json"), pkg, [np.eye(4)] * F,
                                  [FX.translate(0, 0, v) for v in z]))
        thr = dict(THR["interpenetration"], garment_stride=1, skin_stride=1)
        d, d_rest = PEN.garment_depths(s.characters[0], thr)["garment.shirt.main"]
        np.testing.assert_allclose(d_rest, 0.01, atol=1e-6)
        np.testing.assert_allclose(d[22], -0.01, atol=1e-6)
        iss, st = PEN.garment(s, thr)
        self.assertEqual(len(iss), 1)
        self.assertEqual(iss[0]["frames"], [21, 26])
        self.assertAlmostEqual(iss[0]["value_mm"], -20.0, places=3)

    def test_prop_through_table(self):
        pkg = FX.write_package(os.path.join(self.d, "pkg"))
        y = np.full(F, 0.47)
        y[15:20] = 0.44  # the cup sinks 30 mm into the table top for five frames
        cup = [FX.translate(0, v, 0) for v in y]
        table = {"kind": "box", "name": "table_top", "min": [-0.2, 0.44, -0.2], "max": [0.2, 0.47, 0.2]}
        s = SH.Shot(FX.write_bake(os.path.join(self.d, "b.json"), pkg, [np.eye(4)] * F, [np.eye(4)] * F, cup, [table]))
        asset = {"collision": {"type": "capsule", "radius": 0.04, "height": 0.1}}
        iss, st = PEN.prop_room(s, {"cup": asset}, THR["interpenetration"])
        self.assertEqual(len(iss), 1)
        self.assertEqual(iss[0]["frames"], [16, 20])
        self.assertAlmostEqual(iss[0]["value_mm"], -30.0, places=3)
        self.assertAlmostEqual(st["cup/table_top"]["min_mm"], -30.0, places=3)


class Trace(unittest.TestCase):
    def trace(self):
        fr = list(range(1, 11))
        gap = [0.004] * 10
        gap[4:7] = [-0.002, -0.006, -0.004]  # 6 mm into the body at frame 6
        head = [0.02] * 10
        head[8] = -0.001
        return {"frames": fr,
                "characters": [{"name": "a", "arm": {"L": {"gap": gap, "part": ["hand"] * 10, "against": ["chest"] * 10},
                                                     "R": {"gap": [0.01] * 10, "part": [""] * 10, "against": [""] * 10}}}],
                "pairs": [{"a": "a", "b": "b", "head_gap": head, "limb": {"a.hand.L": [0.1] * 10}}],
                "props": [{"name": "cup", "hand": {"a.hand.R": [-0.012] * 9 + [-0.02]}, "body": {"a": [0.05] * 10}}]}

    def test_runs_and_kinds(self):
        iss, st = PEN.from_trace(self.trace(), THR["interpenetration"])
        by = {i["kind"]: i for i in iss}
        self.assertEqual(by["arm"]["frames"], [6, 7])  # below -3 mm on frames 6 and 7
        self.assertEqual(by["arm"]["peak_frame"], 6)
        self.assertEqual(by["arm"]["part"], "hand")
        self.assertEqual(by["head"]["frames"], [9, 9])
        self.assertEqual(by["hand_prop"]["frames"], [10, 10])  # a grip (-12 mm) is not deeper than the grip limit
        self.assertNotIn("limb", by)
        self.assertAlmostEqual(st["arm"]["min_mm"], -6.0)


class Flicker(unittest.TestCase):
    H, W = 64, 96

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rng = np.random.default_rng(1)

    def tearDown(self):
        self.tmp.cleanup()

    def run_frames(self, lum, thr=FLICKER_GENERIC, **kw):
        d = os.path.join(self.tmp.name, "f")
        FX.write_frames(d, lum, **kw)
        fr, data = FR.load_dir(d)
        return flicker.find(fr, data, thr)

    def test_region_limits(self):
        # the same hair noise passes the measured hair limit and fails the generic one
        lum = np.full((12, self.H, self.W), 0.4) + self.rng.normal(0, 0.001, (12, self.H, self.W))
        lum[:, 8:40, 24:56] += self.rng.normal(0, 0.018, (12, 32, 32))  # held noise ~0.045 relative
        index = np.zeros((12, self.H, self.W), np.uint8)
        index[:, 8:40, 24:56] = 1
        iss, st = self.run_frames(lum, index=index)
        self.assertIn(("held_noise", "hair"), {(i["kind"], i["region"]) for i in iss})
        self.assertLess(st["hair"]["denoised_noise_median"], THR["flicker"]["held_noise"]["hair"])
        iss, _ = self.run_frames(lum, thr=THR["flicker"], index=index)
        self.assertNotIn(("held_noise", "hair"), {(i["kind"], i["region"]) for i in iss})

    def test_clean_static_frames(self):
        lum = np.full((12, self.H, self.W), 0.5) + self.rng.normal(0, 0.002, (12, self.H, self.W))
        iss, st = self.run_frames(lum)
        self.assertEqual(iss, [])
        self.assertLess(st["background"]["denoised_noise_max"], 0.01)

    def test_noisy_frames_and_denoiser_gain(self):
        noisy = np.full((12, self.H, self.W), 0.5) + self.rng.normal(0, 0.05, (12, self.H, self.W))
        den = np.full((12, self.H, self.W), 0.5) + self.rng.normal(0, 0.002, (12, self.H, self.W))
        iss, st = self.run_frames((den, noisy))
        self.assertEqual(iss, [])  # the denoised image is clean
        self.assertGreater(st["background"]["noisy_noise_median"], 0.05)
        iss, st = self.run_frames((noisy, noisy))
        kinds = {i["kind"] for i in iss}
        self.assertIn("held_noise", kinds)
        self.assertIn("flip_share", kinds)

    def test_smooth_motion_is_not_flicker(self):
        x = np.arange(self.W)[None, None, :]
        t = np.arange(12)[:, None, None]
        lum = 0.3 + 0.2 * np.sin((x + 0.7 * t) / 9.0) + np.zeros((12, self.H, 1))  # a pattern drifting 0.7 px/frame
        depth = np.full((12, self.H, self.W), 2.0, np.float16)
        depth[:] += (t * 0.02).astype(np.float16)  # the surface moves: not held
        iss, _ = self.run_frames(lum, depth=depth)
        self.assertEqual(iss, [])

    def test_fast_motion_is_compensated(self):
        # a textured surface sweeping 6 px per frame across a skin region: without vectors its flips count (no held
        # pixels to stand on), with the Vector pass the neighbours are warped onto t and nothing turns back
        x = np.arange(self.W)[None, None, :]
        t = np.arange(12)[:, None, None]
        tex = lambda u: 0.4 + 0.15 * np.sign(np.sin(u / 2.0))  # hard stripes, 4 px wide
        lum = tex(x - 6.0 * t) + np.zeros((12, self.H, 1))
        index = np.full((12, self.H, self.W), 4, np.uint8)
        vec = np.zeros((12, self.H, self.W, 4))
        vec[..., 0] = -6.0  # previous: x + X = x - 6
        vec[..., 2] = -6.0  # next: x - Z = x + 6
        normal = np.tile(np.array([0, 0, 1], np.float16), (12, self.H, self.W, 1))
        normal[1::2] = np.array([0, 1, 0], np.float16)  # the surface turns: not held, not nearly held
        iss, st = self.run_frames(lum, index=index, vector=vec, normal=normal)
        self.assertEqual(iss, [])
        self.assertTrue(st["cloth"]["motion_compensated"])
        self.assertLess(st["cloth"]["denoised_flip_share_max"], 0.02)

    def test_local_shimmer_tile(self):
        lum = np.full((12, self.H, self.W), 0.4) + self.rng.normal(0, 0.001, (12, self.H, self.W))
        sign = np.where(np.arange(12) % 2, 1.0, -1.0)[:, None, None]
        pat = np.where(self.rng.random((self.H, self.W)) < 0.8, 1.0, 0.0)[None]
        lum[:, 16:32, 32:48] += 0.1 * sign * pat[:, 16:32, 32:48]  # one tile flickers +-25 % every frame
        index = np.zeros((12, self.H, self.W), np.uint8)
        index[:, 8:40, 24:56] = 1  # hair region around it
        depth = np.full((12, self.H, self.W), 2.0, np.float16)
        depth[:, 8:40, 24:56] += (np.arange(12) * 0.02).astype(np.float16)[:, None, None]  # moving hair: not held
        iss, _ = self.run_frames(lum, index=index, depth=depth)
        tile = [i for i in iss if i["kind"] == "tile_flip_share"]
        self.assertEqual(len(tile), 1)
        self.assertEqual(tile[0]["region"], "hair")
        self.assertEqual(tile[0]["worst_tile_px"], [32, 16])

    def test_blink_is_not_shimmer(self):
        lum = np.full((12, self.H, self.W), 0.4) + self.rng.normal(0, 0.001, (12, self.H, self.W))
        lum[6, 16:32, 32:48] = 0.1  # dark for one frame, as a blink
        index = np.full((12, self.H, self.W), 3, np.uint8)
        iss, _ = self.run_frames(lum, index=index)
        self.assertEqual([i for i in iss if i["kind"] == "tile_flip_share"], [])


class Exr(unittest.TestCase):
    def test_single_and_multi_part(self):
        with tempfile.TemporaryDirectory() as d:
            a = np.arange(12, dtype=np.float32).reshape(3, 4)
            p = os.path.join(d, "s.exr")
            FX.write_exr(p, [(None, {"R": a, "G": a * 2})])
            r = exr.read(p)
            np.testing.assert_array_equal(r["G"], a * 2)
            p = os.path.join(d, "m.exr")
            FX.write_exr(p, [("ViewLayer.Combined", {"R": a, "G": a, "B": a}), ("ViewLayer.Object Index", {"X": a + 1})])
            r = exr.read(p)
            np.testing.assert_array_equal(r["ViewLayer.Object Index.X"], a + 1)
            np.testing.assert_array_equal(r["ViewLayer.Combined.B"], a)


class EndToEnd(unittest.TestCase):
    def test_run_writes_report_and_strips(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = FX.write_package(os.path.join(d, "pkg"))
            z = ease(10, 0.2)
            z[30] += 0.03
            bake = FX.write_bake(os.path.join(d, "bake.json"), pkg, [np.eye(4)] * F, [FX.translate(0, 0, v) for v in z])
            lum = np.full((F, 36, 64), 0.5, np.float32)
            FX.write_frames(os.path.join(d, "frames"), lum)
            rc = RUN.main(["--bake", bake, "--frames", os.path.join(d, "frames"), "--out", os.path.join(d, "out"),
                           "--root", d, "--check"])
            self.assertEqual(rc, 1)
            rep = _load(os.path.join(d, "out", "motion_checks.json"))
            self.assertGreater(rep["counts"]["popping"], 0)
            self.assertEqual(rep["counts"]["flicker"], 0)
            strips = [i["strip"] for i in rep["issues"] if "strip" in i]
            self.assertTrue(strips)
            self.assertTrue(all(os.path.getsize(os.path.join(d, "out", s)) < 60000 for s in strips))


if __name__ == "__main__":
    unittest.main()
