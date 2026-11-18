"""Fit bounded spec parameters against annotated reference cameras with Workbench."""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
from core import ROOT, child, fresh_output, override, read, search, start_values, write

sys.path[:0] = [str(ROOT), str(ROOT / "pipeline/charsys")]
import spec as specs
from PIL import Image
import numpy as np
from score import features, measure, reference, score_table, sheet


LANDMARKS = ("eye_L", "eye_R", "eye_inner_L", "eye_inner_R", "eye_outer_L", "eye_outer_R",
             "brow_inner_L", "brow_inner_R", "brow_outer_L", "brow_outer_R", "nose", "mouth", "chin")


def load_start(path, overrides):
    # Charsys composes inline part documents too. Decode every input as UTF-8
    # so a Windows console's ANSI locale cannot change a spec's canonical hash.
    document = read(path)
    for name, part in (document.get("parts") or {}).items():
        if isinstance(part, str):
            document["parts"][name] = read(path.parent / part)
    spec = specs.compose(document)
    for path in overrides:
        layer = read(path)
        spec = specs.deep_merge(spec, layer.get("override", layer))
    return specs.validate(spec)


def blender(exe, script, args, out, runtime):
    env = dict(os.environ, TEMP=str(runtime), TMP=str(runtime), TMPDIR=str(runtime),
               BLENDER_USER_RESOURCES=str(runtime), PYTHONDONTWRITEBYTECODE="1")
    cmd = [exe, "-b", "--factory-startup", "--python-exit-code", "1",
           "--python-expr", "import sys; sys.dont_write_bytecode=True", "-P", script, "--", *args]
    log = child(out, "blender.log")
    with log.open("a", encoding="utf-8") as stream:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{Path(script).name} exited {result.returncode}, see {log}")


def fit(args):
    started = time.perf_counter()
    spec = load_start(args.spec, args.override)
    cid = spec["identity"]["id"]
    index = (args.reference_index or ROOT / spec["identity"]["references"]).resolve()
    catalog = {v["id"]: v for v in read(index)["views"]}
    ids = args.views.split(",")
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[\w-]+", i) or i not in catalog for i in ids):
        raise ValueError("views must be distinct reference_index IDs")
    views = [catalog[i] for i in ids]
    fidelity_index = index.parent / "annotations/fidelity_index.json"
    declared = read(fidelity_index).get("render_variant") if fidelity_index.is_file() else None
    if declared and args.variant and args.variant != declared:
        raise ValueError(f"selected pose disagrees with reference render_variant {declared}")
    variant = declared or args.variant
    if variant not in ("master", "compare"):
        raise ValueError("supply --variant master or compare when references have no render_variant")
    bounds = read(args.bounds)
    start = start_values(spec, bounds)
    if args.budget < 1 or not 64 <= args.height <= 2048:
        raise ValueError("budget must be positive and render height must be 64..2048")
    refs = {v["id"]: reference(index, v) for v in views}
    names = args.landmarks.split(",")
    if not any(set(names) & ref["landmarks"].keys() for ref in refs.values()):
        raise ValueError("no requested landmarks annotated in selected views")
    out = fresh_output(args.out)
    runtime = child(out, "runtime")
    runtime.mkdir()
    iterations = []

    def evaluate(i, values):
        tick = time.perf_counter()
        work = child(out, f"trial-{i:03d}")
        work.mkdir()
        change = child(work, "override.json")
        write(change, override(values, spec))
        build = child(work, "build")
        flags = ["--spec", args.spec.resolve(), "--out", build, "--no-glb"]
        for path in [*args.override, change]:
            flags.extend(("--override", path.resolve()))
        if variant == "master":
            flags.append("--no-compare")
        blender(args.blender, ROOT / "pipeline/charsys/build_character.py", flags, work, runtime)
        built = time.perf_counter()
        blend = child(build, f"{cid}_{variant}.blend")
        if not blend.is_file():
            raise ValueError(f"builder produced no {variant} blend")
        job = child(work, "render-job.json")
        write(job, {"blend": str(blend.relative_to(work)), "views": views, "height": args.height})
        blender(args.blender, Path(__file__).with_name("render.py"), [job], work, runtime)
        rendered = time.perf_counter()
        details, panels = {}, {}
        for j, name in enumerate(ids):
            stem = f"pass-{j:03d}"
            with Image.open(child(work, stem + ".png")) as image:
                candidate = features(np.asarray(image.convert("RGBA")), read(child(work, stem + ".json")))
            details[name], panels[name] = measure(refs[name], candidate, names)
        score = float(np.mean([v["score"] for v in details.values()]))
        sheet(panels, child(work, "overlay.jpg"))
        record = {"trial": i, "parameters": values, "score": score, "views": details,
                  "blend": blend.relative_to(out).as_posix(), "build_s": built-tick,
                  "render_s": rendered-built, "wall_s": time.perf_counter()-tick}
        iterations.append(record)
        write(child(work, "score.json"), record)
        print(f"Trial {i}: {score:.4f} / 100 in {record['wall_s']:.1f} s", flush=True)
        return score

    best, values = search(start, bounds, args.seed, args.budget, evaluate)
    score_table(child(out, "scores.csv"), iterations[0], iterations[best])
    write(child(out, "proposal.json"), override(values, spec))
    child(out, "overlay.jpg").write_bytes(child(out, f"trial-{best:03d}/overlay.jpg").read_bytes())
    write(child(out, "scores.json"), {"spec_sha256": specs.sha256(spec), "seed": args.seed,
          "budget": args.budget, "height": args.height, "bounds": bounds, "variant": variant,
          "start": 0, "best": best, "iterations": iterations, "wall_s": time.perf_counter()-started})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--override", type=Path, action="append", default=[])
    parser.add_argument("--bounds", type=Path, required=True)
    parser.add_argument("--reference-index", type=Path)
    parser.add_argument("--variant", choices=["master", "compare"], help="pose for an unindexed reference set")
    parser.add_argument("--views", required=True, help="comma-separated IDs in the reference index")
    parser.add_argument("--landmarks", default=",".join(LANDMARKS))
    parser.add_argument("--blender", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budget", type=int, required=True, help="maximum builds, including start")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--height", type=int, default=512)
    try:
        print(fit(parser.parse_args()))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"fit: {exc}\n")


if __name__ == "__main__":
    main()
