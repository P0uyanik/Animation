"""T-065 criterion 0: head outline overlays on the reference views and landmark errors, before vs after.

    python3 docs/evaluation/characters/T-065/outline_sheets.py <measure dir> <out dir>

<measure dir>/<who>_before.json and <who>_after.json from outline_measure.py. On each reference view: green dots =
the outline read on the reference (head_outlines.json), blue = before (current version), red = after (candidate).
The front widths are drawn relative to the face width at the eye line (as head.outline's front_eye_width fit does:
the cranium keeps its own width, the shape below is compared). Writes <who>_outline_overlay.png and
outline_errors.json / .md."""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
A = os.path.join(ROOT, "assets", "characters")
U3 = os.path.join(A, "girl_white_hair_blue_dress", "references", "uploads")
# front view: path, eye_R, eye_L, crop; side view: path, eye front point, facing (+1 = screen right), crop
VIEWS = {
    "boy": ((os.path.join(A, "boy_yellow_hoodie/references/views/val27_front.png"), (81, 174), (151, 174), (10, 130, 230, 240)),
            (os.path.join(A, "boy_yellow_hoodie/references/views/val27_side_right.png"), (187, 172), 75.0, +1, (90, 130, 210, 240))),
    "girl": ((os.path.join(A, "girl_auburn_bun_glasses/references/views/sheet30_front.png"), (94, 140), (142.5, 140), (35, 100, 200, 200)),
             (os.path.join(A, "girl_auburn_bun_glasses/references/views/sheet30_left.png"), (20, 137), 49.7, -1, (0, 100, 100, 200))),
    "third": ((os.path.join(U3, "01_identity_front.webp"), (378, 356.5), (511, 356), (260, 280, 630, 500)),
              (os.path.join(U3, "15_canonical_identity_production_checklist.webp"), (400, 235), 62.5, -1, (340, 190, 490, 310))),
}


def interp(rows, t):
    if not rows:
        return None
    if t < rows[0][0] or t > rows[-1][0]:
        return None
    for (t0, v0), (t1, v1) in zip(rows, rows[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / max(1e-9, t1 - t0)
    return rows[-1][1]


def rel_front(meas, ref_w0):
    w0 = meas["front"][0][1]
    return [[t, w * ref_w0 / w0] for t, w in meas["front"] if t <= meas["chin_t"] + 1e-6] + [[meas["chin_t"], 0.0]]


def draw_front(img, eR, eL, rows, colour, d, dots=False):
    d_px = abs(eL[0] - eR[0])
    xm = (eL[0] + eR[0]) / 2
    pts_l = [(xm - w * d_px, eR[1] + t * d_px) for t, w in rows]
    pts_r = [(xm + w * d_px, eR[1] + t * d_px) for t, w in rows]
    if dots:
        for p in pts_l + pts_r:
            d.ellipse((p[0] - 1.5, p[1] - 1.5, p[0] + 1.5, p[1] + 1.5), fill=colour)
    else:
        d.line(pts_l, fill=colour, width=1)
        d.line(pts_r, fill=colour, width=1)


def draw_side(eye, unit, facing, rows, colour, d, dots=False):
    pts = [(eye[0] + facing * off * unit, eye[1] + t * unit) for t, off in rows]
    if dots:
        for p in pts:
            d.ellipse((p[0] - 1.5, p[1] - 1.5, p[0] + 1.5, p[1] + 1.5), fill=colour)
    elif len(pts) > 1:
        d.line(pts, fill=colour, width=1)


def errors(ref, meas):
    rf = rel_front(meas, ref["front_eye_width"])
    fe = [abs(interp(rf, t) - w) for t, w in ref["front"] if interp(rf, t) is not None]
    se = [abs(interp(meas["side"], t) - o) for t, o in ref.get("side", []) if interp(meas["side"], t) is not None]
    jaw = interp(rf, 0.5 * ref["chin_t"] + 0.25 * ref["chin_t"])  # jaw at 3/4 of the eye-to-chin depth
    jaw_ref = interp(ref["front"], 0.75 * ref["chin_t"])
    cheek = interp(rf, 0.4 * ref["chin_t"])
    cheek_ref = interp(ref["front"], 0.4 * ref["chin_t"])
    return {"chin_depth_err": round(meas["chin_t"] - ref["chin_t"], 3),
            "front_mean_abs_err": round(sum(fe) / len(fe), 3) if fe else None,
            "side_mean_abs_err": round(sum(se) / len(se), 3) if se else None,
            "cheek_width_err": round(cheek - cheek_ref, 3) if cheek is not None and cheek_ref is not None else None,
            "jaw_width_err": round(jaw - jaw_ref, 3) if jaw is not None and jaw_ref is not None else None}


def main(mdir, out):
    ref = json.load(open(os.path.join(HERE, "head_outlines.json")))
    table = {}
    for who, (fv, sv) in VIEWS.items():
        before, after = (json.load(open(os.path.join(mdir, f"{who}_{k}.json"))) for k in ("before", "after"))
        r = ref[who]
        panels = []
        img = Image.open(fv[0]).convert("RGB")
        d = ImageDraw.Draw(img)
        draw_front(img, fv[1], fv[2], rel_front(before, r["front_eye_width"]), (60, 120, 255), d)
        draw_front(img, fv[1], fv[2], rel_front(after, r["front_eye_width"]), (255, 40, 40), d)
        draw_front(img, fv[1], fv[2], r["front"] + [[r["chin_t"], 0.0]], (40, 230, 60), d, dots=True)
        panels.append(img.crop(fv[3]))
        img = Image.open(sv[0]).convert("RGB")
        d = ImageDraw.Draw(img)
        draw_side(sv[1], sv[2], sv[3], [p for p in before["side"] if p[0] <= before["chin_t"]], (60, 120, 255), d)
        draw_side(sv[1], sv[2], sv[3], [p for p in after["side"] if p[0] <= after["chin_t"]], (255, 40, 40), d)
        draw_side(sv[1], sv[2], sv[3], r.get("side", []), (40, 230, 60), d, dots=True)
        panels.append(img.crop(sv[4]))
        panels = [p.resize((int(p.width * 420 / p.height), 420), Image.LANCZOS) for p in panels]
        sheet = Image.new("RGB", (sum(p.width for p in panels), 450), (40, 40, 44))
        x = 0
        for p in panels:
            sheet.paste(p, (x, 30))
            x += p.width
        ImageDraw.Draw(sheet).text((6, 8), f"{who}: green = reference outline, blue = before (current), red = after "
                                   "(body_generic/2 head + face v2). Front widths relative to the eye-line width.",
                                   fill=(240, 240, 240))
        sheet.save(os.path.join(out, f"{who}_outline_overlay.png"), optimize=True)
        table[who] = {"before": errors(r, before), "after": errors(r, after)}
    json.dump(table, open(os.path.join(out, "outline_errors.json"), "w"), indent=1)
    lines = ["| Character | Version | chin depth err | front mean abs err | side mean abs err | cheek width err | jaw width err |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for who, e in table.items():
        for k in ("before", "after"):
            v = e[k]
            lines.append(f"| {who} | {k} | " + " | ".join("—" if v[c] is None else f"{v[c]:+.3f}" if "err" in c and c != "front_mean_abs_err" and c != "side_mean_abs_err" else f"{v[c]:.3f}"
                                                          for c in ("chin_depth_err", "front_mean_abs_err", "side_mean_abs_err", "cheek_width_err", "jaw_width_err")) + " |")
    open(os.path.join(out, "outline_errors.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
