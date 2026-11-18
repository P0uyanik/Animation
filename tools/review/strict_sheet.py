"""Standard strict review sheet (T-087), layout of docs/evaluation/characters/T-081/girl_0.10.0_vs_0.11.0_strict.jpg.

Columns: original reference | previous approved | candidate [| AI target]. Rows: front, 3/4, side, back, face front,
face 3/4. Every render tile of a row is the same camera, rendered in the same run; tiles are only scaled to fit
(the same factor for every render column of a row), never cropped. The whole sheet fits in max_px (default 2048)."""
import os

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
COL_W, BODY_H, FACE_H, TITLE_H, HEAD_H = 280, 376, 260, 24, 18
BG, BAR, TXT = (92, 92, 96), (20, 20, 20), (240, 240, 240)


def tile(im, w, h, text, missing=False):
    c = Image.new("RGB", (w, h), BG)
    if im is not None:
        im = im.convert("RGB")
        s = min(w / im.width, (h - HEAD_H) / im.height)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        c.paste(im, ((w - im.width) // 2, HEAD_H + (h - HEAD_H - im.height) // 2))
    d = ImageDraw.Draw(c)
    if missing:
        d.text((8, h // 2), "not provided", fill=TXT)
    d.rectangle((0, 0, w, HEAD_H - 1), fill=BAR)
    d.text((4, 3), text[:46], fill=TXT)
    return c


def reference_image(ref):
    if not ref:
        return None
    im = Image.open(os.path.join(ROOT, ref["file"]))
    if ref.get("crop"):
        im = im.crop(tuple(ref["crop"]))
    return im


def make_sheet(resolved, render_dir, path, title_note="", max_px=2048):
    """Writes the sheet (JPEG) and returns its size."""
    cols = resolved["columns"]
    roles = {"baseline": "previous approved", "candidate": "candidate"}
    ai = resolved.get("ai_target")
    ncol = 1 + len(cols) + (1 if ai else 0)
    rows = []
    for v in resolved["cameras"]["views"]:
        h = FACE_H if v["framing"] == "face" else BODY_H
        ref = resolved["references"].get(v["name"])
        rl = (ref or {}).get("label") or os.path.basename((ref or {}).get("file", ""))
        cells = [tile(reference_image(ref), COL_W, h, f"REFERENCE {v['label']} ({rl})")]
        for c in cols:
            p = os.path.join(render_dir, c["tag"], v["name"] + ".png")
            im = Image.open(p) if os.path.exists(p) else None
            cells.append(tile(im, COL_W, h, f"{c['label']} {roles.get(c['role'], c['role'])} | {v['label']}",
                              missing=im is None))
        if ai:
            aref = ai["images"].get(v["name"])
            cells.append(tile(reference_image(aref), COL_W, h, f"AI target | {v['label']}", missing=aref is None))
        rows.append(cells)
    W = COL_W * ncol
    H = TITLE_H + sum(r[0].height for r in rows)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    r = resolved["render"] if not title_note else resolved["preview"]
    cam = resolved["cameras"]
    title = (f"{resolved['character']} | {resolved.get('task', '')} | variant {resolved['compare']['variant']} | "
             f"{cam['lens_mm']:.0f} mm, elev {cam['views'][0]['elevation_deg']:.0f} deg | "
             f"{resolved['light']['calibration']} | {r['engine']} {r['samples']} spp | "
             f"recipe {resolved['recipe_sha256'][:10]}" + (f" | {title_note}" if title_note else ""))
    d.rectangle((0, 0, W, TITLE_H - 1), fill=BAR)
    d.text((6, 6), title, fill=TXT)
    y = TITLE_H
    for row in rows:
        for i, c in enumerate(row):
            sheet.paste(c, (i * COL_W, y))
        y += row[0].height
    s = min(1.0, max_px / max(W, H))
    if s < 1.0:
        sheet = sheet.resize((round(W * s), round(H * s)), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sheet.save(path, quality=88)
    return sheet.size
