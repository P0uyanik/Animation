"""Side-by-side review sheets for the fidelity tool (plain Python: numpy + Pillow).

Per view: reference | render (aligned to the reference frame) | silhouette difference with landmarks |
region outlines (reference polygons over the render's regions). The sheets are the primary review material: the
numbers support, but never replace, visual judgement."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PAL = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180),
       (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255)]
FOOTER = "Scores support, never replace, visual judgement: review these images."


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _up(img, k):
    return img.resize((img.width * k, img.height * k), Image.LANCZOS)


def view_sheet(view, ref, res, extra, region_names, k=2):
    h, w = ref["fig"].shape
    ref_im = Image.fromarray(ref["img"])
    bg = np.median(ref["img"][~ref["fig"]], axis=0).astype(np.uint8) if (~ref["fig"]).any() else np.array([128] * 3, np.uint8)
    ren = extra["render_img"].copy()
    ren[~extra["aligned_fig"]] = bg  # same neutral background for the side-by-side
    ren_im = Image.fromarray(ren)
    # silhouette difference + landmarks
    diff = np.full((h, w, 3), 245, np.uint8)
    a, b = ref["fig"], extra["aligned_fig"]
    diff[a & b] = (170, 170, 170)
    diff[a & ~b] = (220, 40, 40)
    diff[~a & b] = (40, 90, 230)
    diff_im = _up(Image.fromarray(diff), k)
    d = ImageDraw.Draw(diff_im)
    rl, nl = ref["landmarks"], extra["render_landmarks"]
    for name in sorted(set(rl) | set(nl)):
        if name in rl and name in nl:
            d.line([tuple(c * k for c in rl[name]), tuple(c * k for c in nl[name])], fill=(0, 0, 0), width=1)
    for name, (x, y) in sorted(rl.items()):
        d.ellipse([x * k - 3, y * k - 3, x * k + 3, y * k + 3], outline=(0, 150, 0), width=2)
    for name, (x, y) in sorted(nl.items()):
        d.rectangle([x * k - 2, y * k - 2, x * k + 2, y * k + 2], outline=(200, 0, 200), width=2)
    # regions: render regions filled, reference polygons outlined
    reg = np.asarray(ren_im).copy() // 2 + 64
    for i, name in enumerate(region_names):
        m = extra["aligned_regions"].get(name)
        if m is not None:
            reg[m] = (np.array(PAL[i % len(PAL)]) * 0.6 + reg[m] * 0.4).astype(np.uint8)
    reg_im = _up(Image.fromarray(reg), k)
    dr = ImageDraw.Draw(reg_im)
    for i, name in enumerate(region_names):
        m = ref["regions"].get(name)
        if m is None:
            continue
        edge = m & ~(np.pad(m, 1)[2:, 1:-1] & np.pad(m, 1)[:-2, 1:-1] & np.pad(m, 1)[1:-1, 2:] & np.pad(m, 1)[1:-1, :-2])
        ys, xs = np.nonzero(edge)
        for x, y in zip(xs, ys):
            dr.rectangle([x * k, y * k, x * k + k - 1, y * k + k - 1], fill=PAL[i % len(PAL)])
    panels = [_up(ref_im, k), _up(ren_im, k), diff_im, reg_im]
    titles = ["reference", "render (aligned)", "silhouette: red = missing, blue = extra; o ref / [] render",
              "regions: fill = render, outline = reference"]
    pw, ph = w * k, h * k
    head, foot, legend = 46, 26, 16 * ((len(region_names) + 3) // 4) + 6
    sheet = Image.new("RGB", (pw * 4 + 30, ph + head + foot + legend), (255, 255, 255))
    sd = ImageDraw.Draw(sheet)
    f14, f11 = font(15), font(12)
    iou = res["figure_iou"]
    nme = res["landmark_nme"]
    sd.text((8, 6), f"{view}   figure IoU {iou:.3f}   landmark error {nme:.3f} head heights" if nme is not None
            else f"{view}   figure IoU {iou:.3f}", fill=(0, 0, 0), font=f14)
    for i, (p, t) in enumerate(zip(panels, titles)):
        x = 6 + i * (pw + 6)
        sheet.paste(p, (x, head))
        sd.text((x, head - 17), t, fill=(60, 60, 60), font=f11)
    for i, name in enumerate(region_names):
        x = 8 + (i % 4) * 230
        y = head + ph + 4 + 16 * (i // 4)
        sd.rectangle([x, y + 2, x + 10, y + 12], fill=PAL[i % len(PAL)])
        r = res["regions"].get(name)
        sd.text((x + 14, y), f"{name}" + (f"  IoU {r['iou']:.2f}" if r and r["iou"] is not None else ""), fill=(0, 0, 0), font=f11)
    sd.text((8, sheet.height - foot + 6), FOOTER, fill=(150, 0, 0), font=f11)
    return sheet


def overview(sheets, path, width=1600):
    ims = [s.resize((width, int(s.height * width / s.width)), Image.LANCZOS) for s in sheets]
    out = Image.new("RGB", (width, sum(i.height for i in ims)), (255, 255, 255))
    y = 0
    for i in ims:
        out.paste(i, (0, y))
        y += i.height
    out.save(path)
