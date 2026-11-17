"""T-055 evidence: girl 0.10.0 face close-ups next to the reference tiles (plain Python, Pillow).

    python3 docs/evaluation/characters/T-055/make_comparison.py <render_dir> <out_dir>

<render_dir> holds the face_expression_sheet.py outputs front2_Neutral.png (yaw 0), q34_Neutral.png (yaw 35) and
sheet_Smile.png. Reference crops (pixel boxes in the 1493x2000 uploads): ref_34 "Neutral" blendshape tile, ref_30
"Happy" tile and ref_30 "Front-Left" turnaround head. The 0.9.0 close-up is the right half of the consolidation
evidence (docs/evaluation/integration/consolidation/girl_face_front_vs_reference.png)."""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REFS = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "references", "uploads")
OLD = os.path.join(ROOT, "docs", "evaluation", "integration", "consolidation", "girl_face_front_vs_reference.png")
SIZE = 384


def ref(n, box):
    return Image.open(os.path.join(REFS, f"ref_{n}.webp")).convert("RGB").crop(box)


def fit(im):
    return im.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)


def strip(tiles, path):
    out = Image.new("RGB", (len(tiles) * (SIZE + 8) - 8, SIZE + 28), (245, 245, 245))
    d = ImageDraw.Draw(out)
    for i, (label, im) in enumerate(tiles):
        out.paste(fit(im), (i * (SIZE + 8), 28))
        d.text((i * (SIZE + 8) + 6, 8), label, fill=(20, 20, 20))
    out.save(path)


def main():
    renders, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    r = lambda name: Image.open(os.path.join(renders, name))
    old = Image.open(OLD)
    old = old.crop((old.width - 512, old.height - 512, old.width, old.height))
    strip([("reference ref_34 Neutral (target)", ref(34, (1065, 65, 1272, 292))),
           ("girl 0.10.0 neutral (T-055)", r("front2_Neutral.png")),
           ("girl 0.9.0 neutral (before)", old),
           ("reference ref_30 Happy", ref(30, (437, 890, 584, 1035))),
           ("girl 0.10.0 Smile preset (Happy)", r("sheet_Smile.png"))],
          os.path.join(out, "girl_0.10.0_face_front_vs_reference.png"))
    strip([("reference ref_30 Front-Left (mirrored)", ref(30, (370, 120, 500, 250)).transpose(Image.FLIP_LEFT_RIGHT)),
           ("girl 0.10.0 neutral, yaw 35", r("q34_Neutral.png"))],
          os.path.join(out, "girl_0.10.0_face_34_vs_reference.png"))


if __name__ == "__main__":
    main()
