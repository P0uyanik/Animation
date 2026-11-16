"""Side-by-side sheet: each reference view next to the matching render (plain Python, Pillow).

    python3 pipeline/charsys/tools/turnaround_sheet.py <reference_views_dir> <render_dir> <out.png>
        --views id[:label],id[:label],... [--height 640] [--render-prefix ""] [--tag "render"]

For every view id, <reference_views_dir>/<id>.png and <render_dir>/<render-prefix><id>.png are scaled to the same
height and placed next to each other with a small label. Character-agnostic."""
import argparse
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("refs")
    ap.add_argument("renders")
    ap.add_argument("out")
    ap.add_argument("--views", required=True)
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--render-prefix", default="")
    ap.add_argument("--tag", default="render")
    ap.add_argument("--no-reference", action="store_true", help="renders only")
    a = ap.parse_args()
    tiles = []
    for item in a.views.split(","):
        vid, _, label = item.partition(":")
        label = label or vid
        pair = [] if a.no_reference else [(os.path.join(a.refs, vid + ".png"), f"ref {label}")]
        pair.append((os.path.join(a.renders, a.render_prefix + vid + ".png"), f"{a.tag} {label}"))
        for path, text in pair:
            im = Image.open(path).convert("RGB")
            im = im.resize((round(im.width * a.height / im.height), a.height), Image.LANCZOS)
            ImageDraw.Draw(im).text((6, 6), text, fill=(255, 255, 255))
            tiles.append(im)
    sheet = Image.new("RGB", (sum(t.width for t in tiles), a.height), (96, 92, 95))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width
    sheet.save(a.out)
    print(a.out, sheet.size)


main()
