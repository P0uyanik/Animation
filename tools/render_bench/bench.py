"""T-124 render benchmark: renders chosen frames of a prepared shot.blend under one settings variant and records a
per-frame time breakdown from Blender's own render-stats stream.

    <blender> -b -P tools/render_bench/bench.py -- --blend shot.blend --frames 1,65,129 --out <dir>
        [--variant name]  (from tools/render_bench/variants.json)   [--set path=value ...]   [--tag label] [--repeat N]

The shot.blend comes from `shot_render.py --blend-only --resolution 1280 720 --samples 128` (the unchanged production
path), so the baseline is exactly the production final settings. Every frame is rendered by a fresh render call;
`render.use_persistent_data` (a lever) keeps scene data between those calls exactly as an animation render would.

Phases (seconds, from the render_stats messages, each message's time charged to the phase it names):
  sync        scene/object synchronisation into Cycles (includes depsgraph evaluation for render: armature,
              geometry nodes, fibre generation)
  bvh         BVH build
  kernels     kernel/shader loading and other "Updating ..." steps
  path_trace  path tracing samples
  denoise     OIDN denoising
  other       anything else between the render call and its end
  save        writing the PNG (timed separately)
Writes <out>/bench.json and <out>/frame_####.png."""
import argparse
import json
import os
import re
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--frames", default="65")
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", default="baseline")
    ap.add_argument("--set", action="append", default=[], help="dotted.path=json_value on the scene")
    ap.add_argument("--tag", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--no-save", action="store_true")
    return ap.parse_args(argv)


def frames_of(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def set_path(root, path, value):
    *head, last = path.split(".")
    obj = root
    for h in head:
        obj = getattr(obj, h)
    setattr(obj, last, value)


def is_fibre(o):
    return o.type == "CURVES" and any(m.name.startswith("PS Surface Fibres") for m in o.modifiers)


def apply_toggles(scene, toggles):
    """Element toggles for the cost-driver breakdown (measurement only; nothing is saved)."""
    done = {}
    for t in toggles:
        n = 0
        if t in ("no_hair_fibres", "no_garment_fibres", "no_fibres"):
            for o in scene.objects:
                if is_fibre(o):
                    hair = o.name.startswith("hair_")
                    if t == "no_fibres" or (t == "no_hair_fibres") == hair:
                        o.hide_render = True
                        n += 1
        elif t == "no_hair":  # hair meshes and their fibres
            for o in scene.objects:
                if o.name.startswith("hair_"):
                    o.hide_render = True
                    n += 1
        elif t == "no_sss":
            for m in bpy.data.materials:
                for nd in (m.node_tree.nodes if m.node_tree else []):
                    if nd.type == "BSDF_PRINCIPLED" and nd.inputs["Subsurface Weight"].default_value > 0:
                        nd.inputs["Subsurface Weight"].default_value = 0.0
                        n += 1
        elif t == "no_glasses":
            for o in scene.objects:
                if o.name.startswith("glasses"):
                    o.hide_render = True
                    n += 1
        elif t in ("no_sun", "no_rect"):
            want = "sun" if t == "no_sun" else "rect"
            for o in scene.objects:
                if o.type == "LIGHT" and o.name.startswith(want):
                    o.hide_render = True
                    n += 1
        else:
            raise SystemExit(f"unknown toggle {t}")
        done[t] = n
    return done


def fibre_density(scene, keep):
    """Render-time fibre LOD lever: keeps a random fraction of every fibre object's curves (a modifier added to the
    shot copy only; the shared fibre node group and the masters are untouched)."""
    ng = bpy.data.node_groups.new("T124 fibre keep", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    rnd = N.new("FunctionNodeRandomValue")
    rnd.data_type = "BOOLEAN"
    rnd.inputs["Probability"].default_value = 1.0 - keep
    rnd.inputs["Seed"].default_value = 124
    dl = N.new("GeometryNodeDeleteGeometry")
    dl.domain = "CURVE"
    ng.links.new(gi.outputs[0], dl.inputs["Geometry"])
    ng.links.new(next(x for x in rnd.outputs if x.type == "BOOLEAN"), dl.inputs["Selection"])
    ng.links.new(dl.outputs[0], go.inputs[0])
    n = 0
    for o in scene.objects:
        if is_fibre(o):
            m = o.modifiers.new("T124 fibre keep", "NODES")
            m.node_group = ng
            n += 1
    return n


def shadow_catcher_fg(scene):
    """Still-camera lever, foreground pass: scene props become shadow catchers on a transparent film, so the
    characters (and their shadows on the props) are path traced; the background plate is rendered once."""
    scene.render.film_transparent = True
    n = 0
    for o in scene.objects:
        if o.name.startswith("prop."):
            o.is_shadow_catcher = True
            n += 1
    return n


def background_only(scene):
    """Still-camera lever, background plate: everything but the props hidden (rendered once per shot)."""
    n = 0
    for o in scene.objects:
        if o.type in ("MESH", "CURVES") and not o.name.startswith("prop."):
            o.hide_render = True
            n += 1
    return n


PHASES = [("path_trace", re.compile(r"Sample \d+/\d+|Path Tracing|Rendered \d+/\d+")),
          ("denoise", re.compile(r"Denois")),
          ("bvh", re.compile(r"BVH")),
          ("sync", re.compile(r"Synchroniz|Preparing|Scene|Object|Geometry|Mesh|Curves|Hair|Updating Images")),
          ("kernels", re.compile(r"Loading|Updating|Kernel|Shaders|Compil"))]


def classify(msg):
    for name, rx in PHASES:
        if rx.search(msg):
            return name
    return "other"


class Stats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.events, self.peak = [], ""

    def __call__(self, stats, *_):
        self.events.append((time.perf_counter(), str(stats)))
        m = re.search(r"Peak[: ]*([\d.]+ ?[KMG])", str(stats))
        if m:
            self.peak = m.group(1)

    def breakdown(self, t0, t1):
        """Phase seconds plus a compact timeline of phase changes ([t offset, phase, first message])."""
        ph = {k: 0.0 for k in ("sync", "bvh", "kernels", "path_trace", "denoise", "other")}
        prev_t, prev_p, traced, tl = t0, "sync", False, []
        last_sample, finished = None, None
        for t, s in self.events:
            msg = s.split("|")[-1].strip()
            p = classify(msg)
            if p == "path_trace":
                last_sample = t
            if msg.startswith("Finished") and finished is None:
                finished = t
            if p == "other" and not traced:
                p = "sync"  # object names / attribute copies reported while synchronising
            traced = traced or p == "path_trace"
            ph[prev_p] += t - prev_t
            if p != prev_p:
                tl.append([round(t - t0, 2), p, re.sub(r"\d+", "#", msg)[:60]])
            prev_t, prev_p = t, p
        ph[prev_p] += t1 - prev_t
        # OIDN runs after the last sample message without a message of its own: charge that gap to denoise.
        if last_sample is not None and finished is not None and finished > last_sample:
            ph["denoise"] += finished - last_sample
            ph["path_trace"] -= finished - last_sample
        return {k: round(v, 2) for k, v in ph.items()}, tl


def main():
    a = parse()
    os.makedirs(a.out, exist_ok=True)
    variants = json.load(open(os.path.join(HERE, "variants.json")))["variants"]
    var = variants[a.variant]
    t = time.perf_counter()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    load_s = time.perf_counter() - t
    scene = bpy.context.scene
    settings = dict(var.get("set", {}))
    for kv in a.set:
        k, _, v = kv.partition("=")
        settings[k] = json.loads(v)
    for k, v in settings.items():
        set_path(scene, k, v)
    toggles = apply_toggles(scene, var.get("toggles", []))
    if var.get("fibre_keep") is not None:
        toggles["fibre_keep"] = fibre_density(scene, float(var["fibre_keep"]))
    if var.get("shadow_catcher_fg"):
        toggles["shadow_catcher_fg"] = shadow_catcher_fg(scene)
    if var.get("background_only"):
        toggles["background_only"] = background_only(scene)
    if var.get("render_scale"):
        scene.render.resolution_percentage = int(var["render_scale"])
    scene.render.filepath = os.path.join(os.path.abspath(a.out), "frame_")
    st = Stats()
    bpy.app.handlers.render_stats.append(st)
    rows = []
    for rep in range(a.repeat):
        for f in frames_of(a.frames):
            scene.frame_current = f
            st.reset()
            t0 = time.perf_counter()
            bpy.ops.render.render(write_still=False)
            t1 = time.perf_counter()
            save = 0.0
            if not a.no_save and rep == 0:
                ts = time.perf_counter()
                bpy.data.images["Render Result"].save_render(os.path.join(a.out, f"frame_{f:04d}.png"))
                save = time.perf_counter() - ts
            phases, timeline = st.breakdown(t0, t1)
            row = {"frame": f, "repeat": rep, "render_s": round(t1 - t0, 2), "save_s": round(save, 2),
                   "phases": phases, "peak_mem": st.peak, "timeline": timeline}
            rows.append(row)
            print("[bench]", a.variant, json.dumps({k: row[k] for k in ("frame", "repeat", "render_s", "phases", "peak_mem")}),
                  flush=True)
    c = scene.cycles
    rep = {"variant": a.variant, "tag": a.tag, "description": var.get("description", ""), "settings": settings,
           "toggles": toggles, "blend": os.path.abspath(a.blend), "load_s": round(load_s, 2),
           "blender": bpy.app.version_string, "threads": scene.render.threads,
           "resolution": [scene.render.resolution_x * scene.render.resolution_percentage // 100,
                          scene.render.resolution_y * scene.render.resolution_percentage // 100],
           "effective": {"samples": c.samples, "adaptive": c.use_adaptive_sampling, "threshold": c.adaptive_threshold,
                         "max_bounces": c.max_bounces, "denoiser": c.denoiser if c.use_denoising else None,
                         "denoise_passes": c.denoising_input_passes, "prefilter": c.denoising_prefilter,
                         "persistent": scene.render.use_persistent_data},
           "frames": rows}
    json.dump(rep, open(os.path.join(a.out, "bench.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
