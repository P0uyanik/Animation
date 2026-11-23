"""T-219 sheet composer (plain Python, Pillow).

    python3 docs/evaluation/characters/T-219/compose.py <character> <render dir> <out.jpg> [--title T] [--crops]

Columns: original reference | current (label cur) | candidate (label cand); rows front, 3/4, side, back (the
character's original turnaround views, hair_silhouette.REFS). With --crops: 100 % crops of the forehead hairline
(yaw 0) and the ear edge (yaw +90 / -90) from the head renders <dir>/{cur,cand}h_<yaw>.png, cur | cand side by side."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hair_silhouette as H  # noqa: E402

ROOT = H.ROOT


def font(n):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", n)
    except OSError:
        return ImageFont.load_default()


def label_tile(img, text, w, h):
    t = Image.new("RGB", (w, h + 22), (24, 24, 26))
    im = img.copy()
    im.thumbnail((w, h))
    t.paste(im, ((w - im.width) // 2, 22 + (h - im.height) // 2))
    ImageDraw.Draw(t).text((6, 3), text, fill=(200, 220, 255), font=font(14))
    return t


def main(a):
    cid, d, out = a[0], a[1], a[2]
    title = a[a.index("--title") + 1] if "--title" in a else cid
    cfg = H.REFS[cid]
    W = 384
    rows = []
    meta = {k: json.load(open(os.path.join(d, k + ".json"))) for k in ("cur", "cand")}
    for view, yaw in cfg["views"]:
        ref = Image.open(os.path.join(ROOT, "assets", "characters", cid, "references", "views", view + cfg["ext"]))
        tiles = [label_tile(ref.convert("RGB"), f"reference {view}", W, W)]
        for k in ("cur", "cand"):
            f = os.path.join(d, "%s_%+04d.png" % (k, yaw))
            s = meta[k]["seconds"].get("%+04d" % yaw, "?")
            tiles.append(label_tile(Image.open(f).convert("RGB"),
                                    f"{meta[k]['label_text']}  yaw {yaw}  {s} s", W, W))
        row = Image.new("RGB", (sum(t.width for t in tiles), tiles[0].height))
        x = 0
        for t in tiles:
            row.paste(t, (x, 0))
            x += t.width
        rows.append(row)
    head = Image.new("RGB", (rows[0].width, 30), (10, 10, 12))
    p = meta["cand"]
    ImageDraw.Draw(head).text((6, 6), f"{title} | profile {p['profile']} {p['spp']} spp, {p['px']} px, 70 mm, "
                                      "character_neutral/1, master A-pose", fill=(255, 255, 255), font=font(15))
    sheet = Image.new("RGB", (rows[0].width, 30 + sum(r.height for r in rows)))
    sheet.paste(head, (0, 0))
    y = 30
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(out, quality=90)
    print(out, sheet.size)


def crops(a):
    """<dir> <out.jpg> <box json: {"+000": [x0,y0,x1,y1], ...}> : 100 % crops cur | cand per yaw."""
    d, out, boxes = a[0], a[1], json.loads(a[2])
    rows = []
    for yaw, box in boxes.items():
        tiles = []
        for k, lab in (("curh", "current"), ("candh", "candidate")):
            im = Image.open(os.path.join(d, f"{k}_{yaw}.png")).convert("RGB").crop(box)
            t = Image.new("RGB", (im.width, im.height + 22), (24, 24, 26))
            t.paste(im, (0, 22))
            ImageDraw.Draw(t).text((6, 3), f"{lab} yaw {yaw} 100 % crop {box}", fill=(200, 220, 255), font=font(14))
            tiles.append(t)
        row = Image.new("RGB", (sum(t.width for t in tiles) + 8, tiles[0].height), (10, 10, 12))
        row.paste(tiles[0], (0, 0))
        row.paste(tiles[1], (tiles[0].width + 8, 0))
        rows.append(row)
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + 4 * len(rows)), (10, 10, 12))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 4
    sheet.save(out, quality=92)
    print(out, sheet.size)


if __name__ == "__main__":
    if sys.argv[1] == "--crops":
        crops(sys.argv[2:])
    else:
        main(sys.argv[1:])
