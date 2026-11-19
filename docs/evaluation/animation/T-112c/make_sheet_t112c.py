"""T-112c evidence: the strict hands close-up sheet of e907 s010_verbs at its shared hold (not part of the pipeline).

The T-051 sheet (docs/evaluation/animation/T-051/make_sheet_t051.py) on s010_verbs: f66 (mid shared hold, f58-f76) of
two shot.blends built by run_shot --blend-only (cast current, fidelity_baseline.json), one baked by the input SHA's
engine (T-112b verbs: the boy's band only) and one by T-112c (both bands from the verbs), through the same three
close-up cameras on the cup with identical cameras, samples and resolution (T-051 render_close.py). Columns:
reference hand crops | input | T-112c.

    python3 docs/evaluation/animation/T-112c/make_sheet_t112c.py --blender <blender> --single <input shot.blend> \
        --band <T-112c shot.blend> --out <dir> [--samples 32] [--res 480 360] [--sheet <jpg>]
"""
import argparse
import os
import subprocess

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
RENDER = os.path.join(HERE, "..", "T-051", "render_close.py")
KEY = os.path.join(ROOT, "docs", "evaluation", "characters", "T-053a", "key")
CUP = ["-0.042", "0.583", "0.007"]  # the cup's middle at f66 (engine coordinates, +Y up)
VIEWS = [("front", ["-0.042", "0.66", "0.30"] + CUP + ["50"], "front: the boy's right hand (giver, band 45-90 mm)"),
         ("back", ["-0.042", "0.66", "-0.29"] + CUP + ["50"], "back: the girl's left hand (receiver, band 10-55 mm)"),
         ("top", ["-0.03", "0.86", "0.03"] + CUP + ["45"], "top: both hands round the rim")]
REFS = [("pb_hands098.jpg", "PB f098: girl, fingertips on both sides of the boat"),
        ("pb_hands062.jpg", "PB f062: boy (yellow) and girl, curled hands"),
        ("pb_hands163.jpg", "PB f163: girl, both hands lowering the boat")]
FRAME = 66


def render(blender, blend, out, tag, samples, res):
    cmd = [blender, "-b", "--factory-startup", "-P", RENDER, "--", "--blend", blend, "--frames", str(FRAME), "--out", out,
           "--tag", tag, "--samples", str(samples), "--res", str(res[0]), str(res[1])]
    for name, v, _ in VIEWS:
        cmd += ["--view", name] + v
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--single", required=True)
    ap.add_argument("--band", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--res", type=int, nargs=2, default=(480, 360))
    ap.add_argument("--sheet", default=os.path.join(HERE, "t112c_s010_verbs_hands_strict_sheet.jpg"))
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    render(a.blender, a.single, a.out, "single", a.samples, a.res)
    render(a.blender, a.band, a.out, "band", a.samples, a.res)
    w, h = a.res
    top, left = 52, 0
    cols = ["reference", "single", "band"]
    heads = ["reference (Paper Boat key frames, T-053a)", "input ae9be36: verbs, boy band only (girl single search)",
             "T-112c: verbs key both bands (pass receiver too)"]
    sheet = Image.new("RGB", (left + w * len(cols), top + (h + 18) * len(VIEWS)), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), a.title or ("T-112c e907 s010_verbs f%d shared hold, cast current (boy 2.0.0, girl 0.12.0). Cycles %d spp, "
                               "%dx%d, identical cameras / lights / samples per row." % (FRAME, a.samples, w, h)), fill="black")
    for c, t in enumerate(heads):
        d.text((left + c * w + 8, 30), t, fill="black")
    for r, (name, _, label) in enumerate(VIEWS):
        y = top + r * (h + 18)
        ref, rlabel = REFS[r]
        im = Image.open(os.path.join(KEY, ref)).convert("RGB")
        im = im.resize((w, int(im.height * w / im.width)))
        sheet.paste(im.crop((0, 0, w, min(h, im.height))), (left, y))
        d.text((left + 6, y + h + 3), rlabel, fill="black")
        for c, tag in enumerate(cols[1:], start=1):
            sheet.paste(Image.open(os.path.join(a.out, "%s_%s_f%04d.png" % (tag, name, FRAME))).convert("RGB"), (left + c * w, y))
            d.text((left + c * w + 6, y + h + 3), label, fill="black")
    if sheet.width > 2048:
        sheet = sheet.resize((2048, int(sheet.height * 2048 / sheet.width)))
    sheet.save(a.sheet, quality=90)
    print(a.sheet)


if __name__ == "__main__":
    main()
