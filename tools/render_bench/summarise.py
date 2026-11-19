"""T-124: one table of every bench run: s/frame (mean over the run's frames), phase breakdown and quality against the
high-sample reference (ref512) and against the current final (baseline), whole frame and per crop.

    python summarise.py <runs dir> <out.json> [--ref ref512] [--base baseline_a] [--frame 65]
Uses run/<image> where <image> is up_0065.png (upscaled runs) or comp_0065.png (composited runs) when present."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics  # noqa: E402


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    runs, out = sys.argv[1], sys.argv[2]
    ref, base, fr = arg("--ref", "ref512"), arg("--base", "baseline_a"), int(arg("--frame", "65"))
    crops = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crops_s010.json")))

    def image(r):
        for n in (f"up_{fr:04d}.png", f"comp_{fr:04d}.png", f"frame_{fr:04d}.png"):
            p = os.path.join(runs, r, n)
            if os.path.exists(p):
                return p
    rows = {}
    for r in sorted(os.listdir(runs)):
        bj = os.path.join(runs, r, "bench.json")
        if not os.path.exists(bj):
            continue
        d = json.load(open(bj))
        fs = [f for f in d["frames"] if f["frame"] == fr] or d["frames"]
        n = len(fs)
        row = {"description": d["description"], "frames": [f["frame"] for f in d["frames"]],
               "s_per_frame": round(sum(f["render_s"] for f in fs) / n, 1),
               "s_per_frame_all": [f["render_s"] for f in d["frames"]],
               "phases": {k: round(sum(f["phases"][k] for f in fs) / n, 2) for k in fs[0]["phases"]},
               "save_s": max(f["save_s"] for f in d["frames"]), "resolution": d["resolution"],
               "effective": d["effective"], "toggles": d["toggles"]}
        img = image(r)
        if img:
            row["image"] = os.path.relpath(img, runs)
            if r != ref:
                row["vs_ref512"] = metrics.still(img, image(ref), crops)
            if r != base:
                row["vs_baseline"] = metrics.still(img, image(base), crops)
        rows[r] = row
        print(r, row["s_per_frame"], row.get("vs_ref512", {}).get("psnr_db"), flush=True)
    json.dump({"frame": fr, "reference": ref, "baseline": base, "crops": crops, "runs": rows}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
