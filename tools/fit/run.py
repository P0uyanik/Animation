"""Fit bounded spec parameters against annotated reference cameras with Workbench."""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
from core import (ROOT, child, cmaes, edit_penalty, fd_step, fresh_output, linear_z, override, read, search,
                  select_controls, sensitivity, start_values, view_cost, write)

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


# ---------------------------------------------------------------------------------------------- T-215 (phase P2)
# Fit existing spec scalars to the T-204 tolerance bands with the T-214 measurer as the score. Commands:
#   run.py t204-sens   --character C --spec S --controls controls.json --out DIR [--jobs 2]
#   run.py t204-search --character C --spec S --sens DIR --out DIR --budget N --seed K [--jobs 2]
# The character is a key of docs/evaluation/characters/T-214/views.json, passed in, never named in this file.
def t204_trial(args, spec, values, work, runtime):
    """Build the spec with the override, measure the reference views (plus neutral yaw 0), drop the blend."""
    import shutil
    from score import t204_measure
    tick = time.perf_counter()
    work.mkdir()
    change = child(work, "override.json")
    write(change, override(values, spec))
    build = child(work, "build")
    flags = ["--spec", args.spec.resolve(), "--out", build, "--no-glb", "--no-compare"]
    for path in [*args.override, change]:
        flags.extend(("--override", path.resolve()))
    blender(args.blender, ROOT / "pipeline/charsys/build_character.py", flags, work, runtime)
    built = time.perf_counter()
    blend = next(build.glob("*_master.blend"))
    report = t204_measure(blend, build / "spec.resolved.json", args.character, child(work, "measure"),
                          tuple(args.yaws))
    report["parameters"] = values
    report["build_s"], report["measure_s"] = built - tick, time.perf_counter() - built
    write(child(work, "measures.json"), report)
    if not args.keep_blends:
        shutil.rmtree(build)
        for f in child(work, "measure").glob("*.npz"):
            f.unlink()
    return report


def t204_pool(args, spec, out, runtime, jobs):
    """Run [(name, values)] trials, at most args.jobs at a time (each build uses about 2 cores)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(t204_trial, args, spec, v, child(out, n), runtime) for n, v in jobs]
        return [f.result() for f in futures]


def t204_keys(report, holdout, group="face"):
    from score import t204_z
    zs = t204_z(report, group)
    return {v: sorted(k for k, z in m.items() if z is not None) for v, m in zs.items() if v != holdout}


def t204_sens(args):
    from score import t204_z
    started = time.perf_counter()
    spec = load_start(args.spec, args.override)
    controls = read(args.controls)
    bounds = {k: c["bounds"] for k, c in controls.items()}
    start = start_values(spec, bounds)
    steps = {k: fd_step(start[k], bounds[k], controls[k]["step"]) for k in sorted(controls)}
    out = fresh_output(args.out)
    runtime = child(out, "runtime")
    runtime.mkdir()
    jobs = [("start", dict(start))] + [(f"fd-{i:02d}", dict(start, **{k: start[k] + steps[k]}))
                                       for i, k in enumerate(sorted(steps))]
    reports = t204_pool(args, spec, out, runtime, jobs)
    base = reports[0]
    holdout = base["holdout"]
    flat = {}
    for r in reports:
        flat[id(r)] = {f"{v}/{k}": z for v, m in t204_z(r).items() for k, z in m.items()}
    cols = sensitivity(flat[id(base)], {k: flat[id(r)] for k, r in zip(sorted(steps), reports[1:])}, steps)
    keys = t204_keys(base, holdout)
    fitted = [f"{v}/{k}" for v, ks in keys.items() for k in ks]
    kept, dropped = select_controls(cols, fitted, args.min_effect, args.max_cos)
    write(child(out, "sensitivity.json"), {
        "character": args.character, "spec_sha256": specs.sha256(spec), "start": start, "steps": steps,
        "bounds": bounds, "fitted_measures": fitted, "holdout": holdout, "z0": flat[id(base)], "columns": cols,
        "kept": kept, "dropped": dropped, "min_effect": args.min_effect, "max_cos": args.max_cos,
        "trials": {n: {"parameters": r["parameters"], "build_s": r["build_s"], "measure_s": r["measure_s"]}
                   for (n, _), r in zip(jobs, reports)},
        "wall_s": time.perf_counter() - started})
    return out


def t204_search(args):
    started = time.perf_counter()
    spec = load_start(args.spec, args.override)
    sens = read(args.sens / "sensitivity.json")
    if sens["spec_sha256"] != specs.sha256(spec):
        raise ValueError("sensitivity run used a different spec")
    if args.controls:
        kept, dropped = args.controls.split(","), {}
    else:  # reselect from the stored columns with this run's rules (recorded in search.json)
        kept, dropped = select_controls(sens["columns"], sens["fitted_measures"], args.min_effect, args.max_cos,
                                        args.noisy.split(",") if args.noisy else (),
                                        [(m.split(","), args.coupled_cos) for m in args.coupled])
    bounds = {k: sens["bounds"][k] for k in kept}
    start = {k: sens["start"][k] for k in kept}
    scales = {k: abs(sens["steps"][k]) for k in kept}
    base = read(args.sens / "start/measures.json")
    holdout = base["holdout"]
    keys = t204_keys(base, holdout)
    cols = {k: sens["columns"][k] for k in kept}
    z0 = sens["z0"]

    def cost_of(zflat, values):
        zv = {}
        for name, z in zflat.items():
            v, m = name.split("/", 1)
            zv.setdefault(v, {})[m] = z
        c, per = view_cost(zv, keys)
        return c + edit_penalty(values, start, scales, args.edit_weight), per

    # Surrogate optimum: the same seeded CMA-ES on the linear finite-difference model (no builds).
    _, mean, _ = cmaes(start, bounds, args.seed, 3000,
                       lambda batch: [cost_of(linear_z(z0, cols, start, sens["steps"], v), v)[0] for _, v in batch],
                       sigma=0.3, popsize=12)
    out = fresh_output(args.out)
    runtime = child(out, "runtime")
    runtime.mkdir()
    trials = []

    def evaluate_many(batch):
        from score import t204_z
        reports = t204_pool(args, spec, out, runtime, [(f"trial-{i:03d}", v) for i, v in batch])
        costs = []
        for (i, v), r in zip(batch, reports):
            zflat = {f"{a}/{k}": z for a, m in t204_z(r).items() for k, z in m.items()}
            c, per = cost_of(zflat, v)
            trials.append({"trial": i, "parameters": v, "cost": c, "per_view": per,
                           "penalty": edit_penalty(v, start, scales, args.edit_weight),
                           "summary": r["summary"], "build_s": r["build_s"], "measure_s": r["measure_s"]})
            print(f"Trial {i}: cost {c:.4f}", flush=True)
            costs.append(c)
        return costs

    best, values, cost = cmaes(start, bounds, args.seed, args.budget, evaluate_many, sigma=args.sigma,
                               popsize=args.popsize, mean=mean)
    start_cost = cost_of(z0, start)
    write(child(out, "proposal.json"), override(values, spec))
    write(child(out, "search.json"), {
        "character": args.character, "spec_sha256": specs.sha256(spec), "seed": args.seed, "budget": args.budget,
        "controls": kept, "dropped": dropped,
        "selection": {"min_effect": args.min_effect, "max_cos": args.max_cos, "noisy": args.noisy,
                      "coupled": args.coupled, "coupled_cos": args.coupled_cos}, "bounds": bounds, "start": start, "start_cost": start_cost[0],
        "start_per_view": start_cost[1], "surrogate_mean": mean, "edit_weight": args.edit_weight,
        "best": best, "best_cost": cost, "best_parameters": values, "trials": trials,
        "wall_s": time.perf_counter() - started})
    return out


def t204_main(argv):
    parser = argparse.ArgumentParser(prog="run.py t204-sens|t204-search")
    parser.add_argument("command", choices=["t204-sens", "t204-search"])
    parser.add_argument("--character", required=True, help="key of the T-214 views.json")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--override", type=Path, action="append", default=[])
    parser.add_argument("--controls", help="sens: controls.json path; search: comma list (default: kept)")
    parser.add_argument("--sens", type=Path, help="search: the t204-sens output directory")
    parser.add_argument("--blender", default=os.environ.get("BLENDER", "blender"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--yaws", type=int, nargs="*", default=[0])
    parser.add_argument("--keep-blends", action="store_true")
    parser.add_argument("--min-effect", type=float, default=0.25)
    parser.add_argument("--max-cos", type=float, default=0.95)
    parser.add_argument("--noisy", default="", help="search: measures left out of control selection (comma list)")
    parser.add_argument("--coupled", action="append", default=[], help="search: trace family for the coupling test")
    parser.add_argument("--coupled-cos", type=float, default=0.85)
    parser.add_argument("--budget", type=int, default=24)
    parser.add_argument("--popsize", type=int, default=6)
    parser.add_argument("--sigma", type=float, default=0.12)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--edit-weight", type=float, default=0.005)
    a = parser.parse_args(argv)
    if a.command == "t204-sens":
        a.controls = Path(a.controls)
        return t204_sens(a)
    return t204_search(a)


def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("t204-"):
        try:
            print(t204_main(sys.argv[1:]))
        except (OSError, ValueError, RuntimeError) as exc:
            sys.exit(f"fit: {exc}")
        return
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
