"""Character fidelity measurement: renders of the current build vs. the owner's reference views (T-032).

    python3 tools/fidelity/run.py --character <id> --build <master.blend | spec.json> --blender <exe>
        [--override <override.json> ...] [--out <dir>] [--views id,...] [--height 640] [--samples 32]
        [--renders <dir>]   (reuse renders from an earlier run: analysis only, no Blender)
        [--reference-index <json>]   (experiments only: e.g. trial camera angles)

Character data (assets/characters/<id>/references/annotations/): fidelity_index.json (views, build variant, region
rules) and one <view>.json per reference view (hand-annotated landmarks and region polygons).
Steps: build from the spec when a spec is given (pipeline/charsys/build_character.py, into <out>/build); render every
view with the existing turnaround tool and the shared calibration (pipeline/charsys/tools/groom_turnaround.py,
character_neutral/1); render flat region ids and project landmarks from bones/empties/vertices
(tools/fidelity/blender_render_side.py, same cameras); measure (tools/fidelity/analysis.py); write
  <out>/sheets/<view>.png       reference | render | silhouette+landmark difference | region outlines
  <out>/sheets/overview.png
  <out>/masks/<view>.png        the measured region masks: reference | render (aligned) | disagreement (T-064)
  <out>/fidelity.json           every number, the score, the ranked differences and the (never applied) suggestions
  <out>/report.md               short report
The score and the numbers support, but never replace, visual judgement: always look at the sheets."""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A  # noqa: E402
import metrics as M  # noqa: E402
import sheet as SH  # noqa: E402
import suggest as SG  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TURNAROUND = os.path.join(ROOT, "pipeline", "charsys", "tools", "groom_turnaround.py")
BUILDER = os.path.join(ROOT, "pipeline", "charsys", "build_character.py")
RENDER_SIDE = os.path.join(HERE, "blender_render_side.py")


def rel(p):
    return os.path.relpath(os.path.abspath(p), ROOT)


def portable(p, out):
    """Repository-relative path, or <out>/... for files written by this run (never a machine-specific path)."""
    p = os.path.abspath(p)
    if p.startswith(out + os.sep):
        return "<out>/" + os.path.relpath(p, out)
    if p.startswith(ROOT + os.sep):
        return os.path.relpath(p, ROOT)
    return os.path.basename(p)


def blender(exe, script, args, log):
    cmd = [exe, "-b", "--factory-startup", "-P", script, "--"] + args
    with open(log, "a") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"Blender step failed ({os.path.basename(script)}), see {log}")


def resolve_build(a, cid, variant, out, log):
    """-> (blend path for the requested variant, provenance dict)."""
    prov = {"build_argument": a.build, "variant": variant}
    if a.build.endswith(".json"):
        bdir = os.path.join(out, "build")
        args = ["--spec", os.path.abspath(a.build), "--out", bdir, "--no-glb"]
        for o in a.override:
            args += ["--override", os.path.abspath(o)]
        blender(a.blender, BUILDER, args, log)
        prov["spec"] = rel(a.build)
        prov["overrides"] = [rel(o) for o in a.override]
        master = os.path.join(bdir, f"{cid}_master.blend")
    else:
        master = os.path.abspath(a.build)
    prov["master"] = master
    blend = master
    if variant == "compare":
        cand = master.replace("_master.blend", "_compare.blend")
        if cand != master and os.path.exists(cand):  # T-064: a build not named *_master.blend used to pass silently
            blend = cand
        else:
            prov["warning"] = "compare variant requested but not found next to the master; the master (A-pose) was used"
    prov["rendered_blend"] = blend
    return blend, prov


def render(a, cid, fidx, ref_index, views, out, log):
    variant = fidx.get("render_variant", "master")
    blend, prov = resolve_build(a, cid, variant, out, log)
    rdir = os.path.join(out, "renders")
    os.makedirs(rdir, exist_ok=True)
    region_map = os.path.join(out, "region_map.json")
    with open(region_map, "w") as f:
        json.dump({"rules": fidx.get("region_rules", [])}, f)
    by_hide = {}
    for v in ref_index["views"]:
        if v["id"] in views:
            by_hide.setdefault(tuple(v.get("hide_objects_prefix", [])), []).append(v["id"])
    for hide, ids in sorted(by_hide.items()):
        src = blend
        if hide:
            src = os.path.join(out, "prepared_" + "_".join(h.strip("_.") for h in hide)[:60] + ".blend")
            blender(a.blender, RENDER_SIDE, [blend, a.index, rdir, "--prepare-only", src, "--hide", ",".join(hide)], log)
        if a.beauty_from:  # T-064: keep earlier beauty renders, redo only the measurement passes
            for f in sorted(os.listdir(a.beauty_from)):
                if f.startswith("timings") or f in {i + ".png" for i in ids}:
                    shutil.copy2(os.path.join(a.beauty_from, f), os.path.join(rdir, f))
        else:
            blender(a.blender, TURNAROUND, [src, a.index, rdir, "--views", ",".join(ids), "--height", str(a.height),
                                             "--samples", str(a.samples)], log)
            os.replace(os.path.join(rdir, "timings.json"), os.path.join(rdir, f"timings_{ids[0]}.json"))
        blender(a.blender, RENDER_SIDE, [src, a.index, rdir, "--views", ",".join(ids), "--height", str(a.height),
                                          "--region-map", region_map], log)
        prov.setdefault("hidden_objects_prefix", {}).update({i: list(hide) for i in ids})
    return rdir, prov


def report_md(cid, doc, out):
    o = doc["overall"]
    L = [f"# Fidelity report: {cid}", "",
         "**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets "
         "(`sheets/`) before acting on any number.", "",
         f"- Build: `{doc['build'].get('spec') or doc['build'].get('master')}` -> `{doc['build'].get('rendered_blend')}`"
         + (f" + {', '.join('`' + x + '`' for x in doc['build'].get('overrides', []))}" if doc['build'].get('overrides') else "")
         + f" (variant: {doc['build']['variant']})",
         *([f"- **Warning:** {doc['build']['warning']}"] if doc["build"].get("warning") else []),
         f"- Views: {', '.join(doc['views'])}",
         f"- Render: groom_turnaround.py, {doc['render']['lighting']}, {doc['render']['height']} px, {doc['render']['samples']} samples",
         "", f"## Fidelity score: {o['score']:.1f} / 100", "",
         "| part | sub-score | measure |", "|---|---|---|"]
    meas = {"silhouette": f"figure IoU {o['figure_iou_mean']:.3f}",
            "regions": f"mean region IoU {o['subscores']['regions']:.3f}" if o['subscores']['regions'] is not None else "-",
            "landmarks": f"mean error {o['landmark_nme_mean']:.3f} head heights" if o['landmark_nme_mean'] is not None else "-",
            "proportions": f"mean relative error {o['proportion_rel_error_mean'] * 100:.1f}%" if o['proportion_rel_error_mean'] is not None else "-",
            "colour": f"mean dE00 {o['colour_de00_mean']:.1f}" if o['colour_de00_mean'] is not None else "-",
            "texture": f"mean abs log2 ratio {o['texture_log2_ratio_mean']:.2f}" if o['texture_log2_ratio_mean'] is not None else "-",
            "hair": ", ".join(f"{k} {v * 100:.0f}" for k, v in o["hair"]["parts"].items() if v is not None),
            "skin": "; ".join(f"{k} dE00 {v['de00_median']:.1f}, shade chroma {v['dC_shade_median']:+.1f}, "
                              f"blush a* P90 {v['da_p90_median']:+.1f}" for k, v in o["skin"].items()) or "-",
            "face": (", ".join(f"{k} {v:+.1f}" for k, v in o["face"]["difference_mean"].items() if v is not None)
                     + f" ({o['face']['views']} views)") if o["face"]["views"] else "-"}
    for k, w in o["weights"].items():
        s = o["subscores"].get(k)
        L.append(f"| {k} (weight {w:.2f}) | {s * 100:.0f} | {meas[k]} |" if s is not None else f"| {k} | - | - |")
    L += ["", "## Per view", "", "| view | figure IoU | landmark error (head heights) | sheet |", "|---|---|---|---|"]
    for v in doc["views"]:
        r = doc["per_view"][v]
        n = f"{r['landmark_nme']:.3f}" if r["landmark_nme"] is not None else "-"
        L.append(f"| {v} | {r['figure_iou']:.3f} | {n} | [sheet](sheets/{v}.png) |")
    L += ["", "## Largest differences (ranked)", ""]
    for d in o["differences"][:15]:
        L.append(f"{d['rank']}. {d['text']}  _(severity {d['severity']:.1f}, {d['kind']})_")
    L += ["", "## Suggested spec corrections (suggestions only, never applied)", ""]
    if doc["suggestions"]:
        for s in doc["suggestions"]:
            L.append(f"- `{s['path']}`: {s['current']} -> **{s['suggested']}** ({s['reason']})")
    else:
        L.append("- none")
    L += ["", "Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.", ""]
    with open(os.path.join(out, "report.md"), "w") as f:
        f.write("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--character", required=True)
    ap.add_argument("--build", required=True, help="a built <id>_master.blend or a spec .json (built first)")
    ap.add_argument("--blender", default="blender")
    ap.add_argument("--override", action="append", default=[])
    ap.add_argument("--out", default="")
    ap.add_argument("--views", default="")
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--beauty-from", default="", help="re-run only the measurement passes (region ids, landmarks) "
                    "and reuse the beauty renders of this earlier renders/ folder (same build required)")
    ap.add_argument("--renders", default="", help="reuse an earlier run's renders/ folder (analysis only)")
    ap.add_argument("--reference-index", default="", help="experiments only: another reference_index.json (e.g. a "
                    "trial camera yaw); default: the one named in fidelity_index.json")
    a = ap.parse_args()
    a.beauty_from = os.path.abspath(a.beauty_from) if a.beauty_from else ""
    cid = a.character
    adir = os.path.join(ROOT, "assets", "characters", cid, "references", "annotations")
    fidx = json.load(open(os.path.join(adir, "fidelity_index.json")))
    a.index = os.path.abspath(a.reference_index) if a.reference_index else os.path.join(ROOT, fidx["reference_index"])
    ref_index = json.load(open(a.index))
    views = [v for v in (a.views.split(",") if a.views else fidx["views"]) if v]
    out = os.path.abspath(a.out or os.path.join("fidelity_out", cid))
    os.makedirs(out, exist_ok=True)
    log = os.path.join(out, "blender.log")
    if a.renders:
        rdir = os.path.abspath(a.renders)
        prev = os.path.join(os.path.dirname(rdir), "fidelity.json")
        prov = json.load(open(prev))["build"] if os.path.exists(prev) else {"build_argument": a.build, "variant": fidx.get("render_variant", "master")}
    else:
        open(log, "w").close()
        rdir, prov = render(a, cid, fidx, ref_index, views, out, log)
    ref_dir = os.path.join(ROOT, "assets", "characters", cid, "references", "views")
    anns = {v: json.load(open(os.path.join(adir, v + ".json"))) for v in views}
    refs = {v: A.load_reference(ref_dir, anns[v]) for v in views}
    # head height fraction of the reference (for views without a visible chin)
    fr = []
    for v in views:
        if "chin" in refs[v]["landmarks"]:
            f = A.frame(refs[v])
            fr.append((refs[v]["landmarks"]["chin"][1] - f["top"]) / f["height"])
    head_fraction = sorted(fr)[len(fr) // 2] if fr else 0.25
    per_view, extras = {}, {}
    for v in views:
        ren = A.load_render(rdir, v)
        per_view[v], extras[v] = A.analyse_view(refs[v], ren, head_fraction)
    overall = A.summarise(per_view)
    spec_path = a.build if a.build.endswith(".json") else None
    suggestions = SG.suggest(overall, spec_path, a.override)
    regions_json = json.load(open(os.path.join(rdir, "regions.json")))
    calib = "character_neutral/1"
    try:
        t = json.load(open(next(os.path.join(rdir, f) for f in sorted(os.listdir(rdir)) if f.startswith("timings"))))
        calib = t.get("lighting", calib)
    except StopIteration:
        pass
    doc = {"schema": "plush-studio.fidelity/1", "character": cid, "views": views,
           "build": {k: (portable(v, out) if isinstance(v, str) and os.path.isabs(v) else v) for k, v in prov.items()},
           "render": {"tool": "pipeline/charsys/tools/groom_turnaround.py", "lighting": calib, "height": a.height,
                      "samples": a.samples, "region_objects": regions_json["objects"]},
           "annotations": {v: rel(os.path.join(adir, v + ".json")) for v in views},
           "reference_index": rel(a.index),
           "reference_head_fraction": head_fraction,
           "note": "Scores support, but never replace, visual judgement: the side-by-side sheets are the review material.",
           "overall": overall, "per_view": per_view, "suggestions": suggestions}
    with open(os.path.join(out, "fidelity.json"), "w") as f:
        f.write(M.dumps(doc))
    sdir = os.path.join(out, "sheets")
    os.makedirs(sdir, exist_ok=True)
    region_names = sorted(set().union(*[set(r["regions"]) for r in per_view.values()]))
    sheets = []
    mdir = os.path.join(out, "masks")
    os.makedirs(mdir, exist_ok=True)
    for v in views:
        s = SH.view_sheet(v, refs[v], per_view[v], extras[v], region_names)
        s.save(os.path.join(sdir, v + ".png"))
        sheets.append(s)
        SH.mask_sheet(v, refs[v], extras[v], region_names).save(os.path.join(mdir, v + ".png"))
    SH.overview(sheets, os.path.join(sdir, "overview.png"))
    report_md(cid, doc, out)
    print(json.dumps({"score": round(overall["score"], 2), "out": out,
                      "top_differences": [d["text"] for d in overall["differences"][:8]]}, indent=1))


if __name__ == "__main__":
    main()
