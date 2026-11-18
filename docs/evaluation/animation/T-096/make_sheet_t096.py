"""T-096 evidence: the strict before/after frame sheet (not part of the pipeline).

Renders the chosen frames of the two diagnostic shot.blends (run_shot --blend-only) with identical cameras, samples
and resolution through docs/evaluation/animation/T-082/render_frames.py, then composes one JPEG:
rows = frames, columns = before / after through the shot camera, then before / after from above.

    python3 docs/evaluation/animation/T-096/make_sheet_t096.py --blender <blender> --before <shot.blend> \
        --after <shot.blend> --frames 25,46,50 --out <dir> [--samples 32] [--sheet <jpg>]
"""
import argparse
import os
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
RENDER = os.path.join(ROOT, "docs", "evaluation", "animation", "T-082", "render_frames.py")
# Engine coordinates (+Y up). Top: above the pair, looking down at the gap between the heads.
TOP = ["--camera", "-0.3", "1.95", "0.55", "--target", "0", "0.72", "0", "--lens", "30"]
LABELS = {25: "f25 hold (boy)", 46: "f46 hand-over contact", 50: "f50 both hold the cup"}


def render(blender, blend, frames, out, tag, samples, extra):
    cmd = [blender, "-b", "--factory-startup", "-P", RENDER, "--", "--blend", blend, "--frames", frames, "--out", out,
           "--tag", tag, "--samples", str(samples)] + extra
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--frames", default="25,46,50")
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--sheet", default=os.path.join(HERE, "t096_e905_before_after_sheet.jpg"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for tag, blend, extra in (("before_cam", a.before, []), ("after_cam", a.after, []),
                              ("before_top", a.before, TOP), ("after_top", a.after, TOP)):
        render(a.blender, blend, a.frames, a.out, tag, a.samples, extra)
    frames = [int(f) for f in a.frames.split(",")]
    cols = ["before_cam", "after_cam", "before_top", "after_top"]
    heads = ["before: shot camera", "after: shot camera", "before: from above", "after: from above"]
    w, h, top, left = 640, 360, 44, 150
    sheet = Image.new("RGB", (left + w * len(cols), top + h * len(frames)), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), "T-096 e905 latest staging, cast current (boy 2.0.0, girl 0.11.0): before = T-082 latest as is; after = "
                   "interaction {headVolumes, headClearance 0.03, followSharedProp, visibleGrip}. Cycles %d spp, same cameras."
           % a.samples, fill="black")
    for c, t in enumerate(heads):
        d.text((left + c * w + 8, 26), t, fill="black")
    for r, f in enumerate(frames):
        d.text((8, top + r * h + h // 2), LABELS.get(f, "f%d" % f), fill="black")
        for c, tag in enumerate(cols):
            sheet.paste(Image.open(os.path.join(a.out, "%s_f%04d.png" % (tag, f))).convert("RGB"), (left + c * w, top + r * h))
    if sheet.width > 2048:
        sheet = sheet.resize((2048, int(sheet.height * 2048 / sheet.width)), Image.LANCZOS)
    sheet.save(a.sheet, quality=88)
    print(a.sheet)


if __name__ == "__main__":
    sys.exit(main())
