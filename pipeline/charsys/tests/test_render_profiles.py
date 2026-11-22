"""T-166 tests: final720 is the default render profile and HEVC 10-bit the default delivery encode; the previous
128 spp / 0.01 preset (legacy128) and the H.264 8-bit fallback still resolve. T-199: opt-in compositor look. T-201:
opt-in preview_eevee profile (existing profiles unchanged; with bpy a tiny EEVEE render runs). Fast without Blender.

    python3 pipeline/charsys/tests/test_render_profiles.py
"""
import ast
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" {detail}"))
    if not ok:
        FAILS.append(name)


P = json.load(open(os.path.join(CHARSYS, "render_profiles.json")))
prof = P["profiles"]


def shot_render_parse(argv):
    """The real shot_render.parse (bpy-free), pulled out of the source and run against `argv`."""
    src = open(os.path.join(CHARSYS, "shot_render.py")).read()
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "parse")
    ns = {"argparse": argparse, "json": json, "os": os, "sys": type("S", (), {"argv": ["x", "--"] + argv})}
    ns["__file__"] = os.path.join(CHARSYS, "shot_render.py")
    exec(compile(ast.Module([fn], []), "shot_render.parse", "exec"), ns)
    return ns["parse"]()


base = ["--bake", "b", "--cast", "c", "--out", "o"]

# --- profiles
check("default profile is final720", P["default_profile"] == "final720")
f = prof["final720"]
check("final720 = 1280x720, 128 spp, adaptive 0.05, persistent data",
      f["resolution"] == [1280, 720] and f["samples"] == 128 and f["cycles"] == {"adaptive_threshold": 0.05}
      and f["render"] == {"use_persistent_data": True})
check("old preset still selectable by name (legacy128: 128 spp, adaptive 0.01, no forced resolution)",
      prof["legacy128"]["samples"] == 128 and prof["legacy128"]["cycles"] == {"adaptive_threshold": 0.01}
      and "resolution" not in prof["legacy128"] and "render" not in prof["legacy128"])
check("review profile unchanged", prof["review"]["samples"] == 16 and prof["review"]["cycles"] == {"adaptive_threshold": 0.05})

# --- shot_render.parse
a = shot_render_parse(base)
check("shot_render default -> final720", a.profile == "final720" and a.resolution == [1280, 720] and a.samples == 128
      and a.profile_data["cycles"]["adaptive_threshold"] == 0.05)
a = shot_render_parse(base + ["--profile", "legacy128"])
check("shot_render --profile legacy128 -> 128 spp, 0.01, resolution from the bake",
      a.samples == 128 and a.resolution is None and a.profile_data["cycles"]["adaptive_threshold"] == 0.01)
a = shot_render_parse(base + ["--samples", "8", "--resolution", "64", "36"])
check("explicit --samples/--resolution still override the profile", a.samples == 8 and a.resolution == [64, 36])
try:
    shot_render_parse(base + ["--profile", "nope"])
    check("shot_render unknown profile refused", False)
except SystemExit:
    check("shot_render unknown profile refused", True)

# --- delivery encode
enc = P["encode"]
check("default encode is hevc10", enc["default"] == "hevc10")
h, x = enc["codecs"]["hevc10"]["args"], enc["codecs"]["h264"]["args"]
check("hevc10 = x265 10-bit", "libx265" in h and "yuv420p10le" in h and h[h.index("-crf") + 1] == "18")
check("h264 fallback = x264 8-bit", "libx264" in x and "yuv420p" in x and "yuv420p10le" not in x)
src = open(os.path.join(ROOT, "pipeline", "production", "run_shot.py")).read()
check("run_shot encode step takes its args from the codec table", "*a.encode_args" in src and '"libx264"' not in src)
check("run_shot passes the profile to shot_render", '"--profile", a.profile' in src)
r = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "production", "run_shot.py"), "--shot", "x", "--blender", "b",
                    "--codec", "nope"], capture_output=True, text=True)
check("run_shot unknown codec refused", r.returncode == 2 and "unknown --codec" in r.stderr, r.stderr[-200:])
r = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "production", "run_shot.py"), "--shot", "x", "--blender", "b",
                    "--profile", "nope"], capture_output=True, text=True)
check("run_shot unknown profile refused", r.returncode == 2 and "unknown --profile" in r.stderr, r.stderr[-200:])

# --- both encodes really run (tiny synthetic clip) when ffmpeg has the encoders
def have(name):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return name in p.stdout
for key, enc_name, pix in (("hevc10", "libx265", "yuv420p10le"), ("h264", "libx264", "yuv420p")):
    if not have(enc_name):
        print(f"SKIP encode {key}: ffmpeg has no {enc_name}")
        continue
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "o.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=128x72:rate=24:duration=0.5",
               *enc["codecs"][key]["args"], out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt",
                                "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip() if r.returncode == 0 else ""
        check(f"encode {key} runs and yields {pix}", r.returncode == 0 and probe == pix, r.stderr[-200:] + probe)

# --- T-199 compositor look (opt-in): existing profiles untouched, look only in final720_look
sys.path.insert(0, CHARSYS)
import render_engine  # noqa: E402
check("existing profiles carry no compositor block", all("compositor" not in prof[k] for k in ("final720", "review", "legacy128")))
look = prof["final720_look"]
check("final720_look = final720 render settings + compositor block, not the default",
      {k: v for k, v in look.items() if k not in ("description", "compositor")} == {k: v for k, v in f.items() if k != "description"}
      and P["default_profile"] == "final720")
cfg = look["compositor"]
check("compositor block is explicit: look, glow, grade, vignette with exactly the known keys",
      cfg["look"] == "plush_soft" and set(cfg["glow"]) == render_engine._LOOK_KEYS["glow"]
      and set(cfg["grade"]) == render_engine._LOOK_KEYS["grade"] and set(cfg["vignette"]) == render_engine._LOOK_KEYS["vignette"])


class FakeScene:
    """Records every attribute read; apply_profile without a compositor block may only touch cycles/render."""
    def __init__(self):
        self.touched = []
        self.cycles = type("C", (), {"adaptive_threshold": 0.0})()
        self.render = type("R", (), {"use_persistent_data": False})()

    def __getattribute__(self, name):
        if name not in ("touched", "cycles", "render", "__dict__", "__class__"):
            object.__getattribute__(self, "touched").append(name)
        return object.__getattribute__(self, name)


fs = FakeScene()
res = render_engine.apply_profile(fs, f)
check("no compositor key -> apply_profile returns today's dict and touches no compositor attribute",
      res == {"cycles.adaptive_threshold": 0.05, "render.use_persistent_data": True} and not fs.touched, str(res))
try:
    render_engine.apply_profile(FakeScene(), {"compositor": {"look": "x", "bogus": {}}})
    check("unknown compositor key refused", False)
except ValueError:
    check("unknown compositor key refused", True)

# --- T-201 preview_eevee (opt-in): existing profiles byte-identical, EEVEE only when the profile is asked for
import subprocess as _sp  # noqa: E402
old = json.loads(_sp.run(["git", "show", "0f3787e:pipeline/charsys/render_profiles.json"], cwd=ROOT,
                         capture_output=True, text=True).stdout or "null")
if old is None:
    print("SKIP byte-identical check: commit 0f3787e not in this checkout")
else:
    check("T-201: every pre-T-201 profile, default_profile and encode table unchanged",
          all(prof[k] == v for k, v in old["profiles"].items()) and P["default_profile"] == old["default_profile"]
          and P["encode"] == old["encode"] and set(prof) - set(old["profiles"]) == {"preview_eevee"})
check("T-201: no Cycles profile names an engine or an eevee block",
      all("engine" not in v and "eevee" not in v for k, v in prof.items() if k != "preview_eevee"))
pe = prof["preview_eevee"]
check("T-201: preview_eevee = eevee engine, <= 1280x720, few samples, no cycles/compositor block, not the default",
      pe["engine"] == "eevee" and pe["resolution"][0] <= 1280 and pe["samples"] <= 32 and "cycles" not in pe
      and "compositor" not in pe and P["default_profile"] != "preview_eevee" and "OPT-IN" in pe["description"])
a = shot_render_parse(base + ["--profile", "preview_eevee"])
check("T-201: shot_render --profile preview_eevee takes its resolution/samples",
      a.resolution == pe["resolution"] and a.samples == pe["samples"])


class EeveeScene:
    def __init__(self, engine):
        self.render = type("R", (), {"engine": engine, "use_persistent_data": False})()
        self.eevee = type("E", (), {k: None for k in pe["eevee"]})()
        self.cycles = None  # an EEVEE profile must not touch Cycles settings


es = EeveeScene("BLENDER_EEVEE")
res = render_engine.apply_profile(es, pe)
check("T-201: apply_profile sets the eevee block on scene.eevee and records the engine",
      res["engine"] == "eevee" and all(getattr(es.eevee, k) == v and res[f"eevee.{k}"] == v for k, v in pe["eevee"].items())
      and es.render.use_persistent_data is True, str(res))
try:
    render_engine.apply_profile(EeveeScene("CYCLES"), pe)
    check("T-201: preview_eevee on a Cycles scene refused (pass --engine eevee)", False)
except ValueError as e:
    check("T-201: preview_eevee on a Cycles scene refused (pass --engine eevee)", "--engine eevee" in str(e))
try:
    render_engine.apply_profile(EeveeScene("BLENDER_EEVEE"), {"engine": "eevee", "eevee": {"bogus": 1}})
    check("T-201: unknown eevee setting refused", False)
except ValueError:
    check("T-201: unknown eevee setting refused", True)

sys.path.insert(0, os.path.join(ROOT, "tools", "pc"))
import render_package  # noqa: E402
man = {"render_entry": "code/pipeline/charsys/shot_render.py", "bake": "bake.json", "cast": "cast.json",
       "production_render": {}}
for prof_name, engine_arg, want in (("preview_eevee", None, "eevee"), ("review", None, "cycles"),
                                    ("final720", None, "cycles"), ("review", "eevee", "eevee")):
    ns = argparse.Namespace(profile=prof_name, resolution=None, samples=None, engine=engine_arg, frames="")
    cmd, eff = render_package.render_command("pkg", man, P, ns, "blender", "out")
    check(f"T-201: render_package {prof_name} (--engine {engine_arg}) -> {want}",
          eff["engine"] == want and (("--engine" in cmd) == (want == "eevee")), " ".join(cmd))

try:
    import bpy  # noqa: E402
except ImportError:
    bpy = None
    print("SKIP compositor render tests: no bpy")
if bpy is not None:
    import hashlib
    from array import array
    import types
    import warnings
    warnings.simplefilter("ignore", DeprecationWarning)

    def render_sha(profile, via_apply=True):
        """Tiny fixed-seed Cycles render of a lit sphere; returns (pixel sha256, applied dict, tree-is-None)."""
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        bpy.ops.mesh.primitive_uv_sphere_add()
        bpy.ops.object.light_add(type="SUN", location=(2, -2, 3))
        bpy.context.object.data.energy = 6
        cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
        sc.collection.objects.link(cam)
        cam.location, cam.rotation_euler, sc.camera = (0, -5, 0), (1.5708, 0, 0), cam
        render_engine.configure(sc, "cycles", 4)
        applied = render_engine.apply_profile(sc, profile) if via_apply else {}
        if not via_apply:  # what the pre-T-199 apply_profile did, by hand
            sc.cycles.adaptive_threshold = profile["cycles"]["adaptive_threshold"]
            sc.render.use_persistent_data = profile["render"]["use_persistent_data"]
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 96, 54, 100
        sc.cycles.seed = 7
        sc.cycles.device = "CPU"
        sc.cycles.use_denoising = False  # OIDN output was not run-to-run stable here (also without T-199)
        with tempfile.TemporaryDirectory() as t:
            sc.render.filepath = os.path.join(t, "o.png")
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(sc.render.filepath)  # pixels, not file bytes: PNG bytes differ run to run
            sha = hashlib.sha256(array("f", im.pixels[:]).tobytes()).hexdigest()
            bpy.data.images.remove(im)
        return sha, applied, sc.compositing_node_group is None

    base_sha, _, no_tree = render_sha(f, via_apply=False)
    sha1, applied1, no_tree1 = render_sha(f)
    check("no compositor key: render is bit-identical to the pre-T-199 path and no node tree is created",
          sha1 == base_sha and no_tree and no_tree1 and "compositor" not in applied1, f"{sha1} {base_sha}")
    lsha1, la, tree_none = render_sha(look)
    lsha2, _, _ = render_sha(look)
    check("look changes the image", lsha1 != sha1 and not tree_none)
    check("look is deterministic (two renders, same pixel SHA-256)", lsha1 == lsha2)
    comp = la["compositor"]
    check("look is recorded: name, params, Blender version, node chain",
          comp["look"] == "plush_soft" and comp["params"]["glow"] == cfg["glow"] and comp["blender"] == bpy.app.version_string
          and comp["node_chain"][0].endswith("CompositorNodeRLayers") and comp["node_chain"][-1].endswith("NodeGroupOutput")
          and any("CompositorNodeGlare" in n for n in comp["node_chain"]), str(comp))
    if os.environ.get("PLUSH_TEST_EEVEE") == "1":  # T-201: ~30-60 s on a GPU-less box (Mesa software OpenGL)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        bpy.ops.mesh.primitive_uv_sphere_add()
        bpy.ops.object.light_add(type="SUN", location=(2, -2, 3))
        cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
        sc.collection.objects.link(cam)
        cam.location, cam.rotation_euler, sc.camera = (0, -5, 0), (1.5708, 0, 0), cam
        render_engine.configure(sc, "eevee", pe["samples"])
        ea = render_engine.apply_profile(sc, pe)
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 96, 54, 100
        with tempfile.TemporaryDirectory() as t:
            sc.render.filepath = os.path.join(t, "e.png")
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(sc.render.filepath)
            px = im.pixels[:]
            bpy.data.images.remove(im)
        check("T-201: preview_eevee renders headless with EEVEE (non-blank image)",
              ea["engine"] == "eevee" and max(px) - min(px) > 0.1)
    else:
        print("SKIP T-201 EEVEE render: set PLUSH_TEST_EEVEE=1 (needs an OpenGL/EGL context; software Mesa is enough)")
    fake = types.ModuleType("bpy")
    fake.app = types.SimpleNamespace(version=(6, 0, 0), version_string="6.0.0")
    real = sys.modules["bpy"]
    sys.modules["bpy"] = fake
    try:
        render_engine.apply_compositor_look(FakeScene(), cfg)
        check("unsupported Blender version (6.0) refused loudly", False)
    except ValueError as e:
        check("unsupported Blender version (6.0) refused loudly", "5.x only" in str(e))
    finally:
        sys.modules["bpy"] = real

print("[test_render_profiles] " + ("FAILED: " + ", ".join(FAILS) if FAILS else "ALL PASS"))
sys.exit(1 if FAILS else 0)
