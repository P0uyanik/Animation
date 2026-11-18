"""T-064 evidence: segmentation before/after, face windows, and the old-vs-new validation table.

    python3 make_evidence.py <old_tool_dir> <work_dir> <out_dir>

<old_tool_dir>: a checkout of tools/fidelity before T-064 (for example `git archive origin/staging tools/fidelity`).
<work_dir>: the run folders listed in README.md ("How to reproduce"): old_girl/ (old render side), seg_girl/ and
seg_boy/ (fixed render side, same beauty renders), t58/fid/, old/<case>/ and new/<case>/ fidelity runs.
"""
import importlib.util
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "fidelity"))
import analysis as A  # noqa: E402
import look as LK  # noqa: E402
import sheet as SH  # noqa: E402

GIRL = "girl_auburn_bun_glasses"
CASES = ["boy_cur", "boy_20dev", "boy_curA", "boy_A", "boy_B", "boy_C",
         "girl_cur", "girl_010_3v", "girl_09_3v", "girl_curA", "girl_A", "girl_B", "girl_C"]


def load_old(old_dir):
    spec = importlib.util.spec_from_file_location("old_analysis", os.path.join(old_dir, "analysis.py"))
    sys.path.insert(0, old_dir)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.path.pop(0)
    return mod


def labels(fig, masks, names):
    im = np.full(fig.shape + (3,), 255, np.uint8)
    im[fig] = (150, 150, 150)
    order = sorted((i for i, n in enumerate(names) if masks.get(n) is not None),
                   key=lambda i: (names[i] == "glasses", -int(masks[names[i]].sum()), i))
    for i in order:
        im[masks[names[i]]] = SH.PAL[i % len(SH.PAL)]
    return Image.fromarray(im)


def segmentation(old_dir, work, out):
    """Girl sheet30_front: reference and render regions as the old tool measured them vs the fixed tool."""
    OA = load_old(old_dir)
    v = "sheet30_front"
    ann_old = json.load(open(os.path.join(work, "girl_ann_head.json")))
    ann_new = json.load(open(os.path.join(ROOT, "assets/characters", GIRL, "references/annotations", v + ".json")))
    rdir = os.path.join(ROOT, "assets/characters", GIRL, "references/views")
    names = sorted(ann_new["regions"])
    ref_o, ref_n = OA.load_reference(rdir, ann_old), A.load_reference(rdir, ann_new)
    ren_o, ren_n = OA.load_render(os.path.join(work, "old_girl/renders"), v), A.load_render(os.path.join(work, "seg_girl/renders"), v)
    tiles = [(labels(ref_o["fig"], ref_o["regions"], names), "reference, before"),
             (labels(ren_o["fig"], ren_o["regions"], names), "render, before"),
             (labels(ref_n["fig"], ref_n["regions"], names), "reference, T-064"),
             (labels(ren_n["fig"], ren_n["regions"], names), "render, T-064")]
    H = 480
    ims = [(t.resize((int(t.width * H / t.height), H), Image.NEAREST), s) for t, s in tiles]
    W = sum(i.width for i, _ in ims) + 12 * 3
    sheet = Image.new("RGB", (W, H + 70), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    x = 0
    for im, s in ims:
        sheet.paste(im, (x, 22))
        d.text((x + 4, 4), s, fill=(0, 0, 0), font=SH.font(13))
        x += im.width + 12
    for i, n in enumerate(names):
        cx, cy = 6 + (i % 5) * (W // 5), H + 30 + 18 * (i // 5)
        d.rectangle([cx, cy + 2, cx + 10, cy + 12], fill=SH.PAL[i % len(SH.PAL)])
        d.text((cx + 14, cy), n, fill=(0, 0, 0), font=SH.font(12))
    sheet.save(os.path.join(out, "segmentation_before_after.png"), optimize=True)


def face_windows(work, out):
    cases = [(GIRL, "sheet30_front", "seg_girl/renders", "girl 0.10.0"),
             ("boy_yellow_hoodie", "val27_front", "seg_boy/renders", "boy 1.1.0"),
             ("boy_yellow_hoodie", "val27_front", "t58/fid/renders", "boy 2.0-dev")]
    tiles = []
    for cid, v, rd, label in cases:
        ann = json.load(open(os.path.join(ROOT, "assets/characters", cid, "references/annotations", v + ".json")))
        ref = A.load_reference(os.path.join(ROOT, "assets/characters", cid, "references/views"), ann)
        ren = A.load_render(os.path.join(work, rd), v)
        native = {"skin_face": ren["colour_only"]["skin_face"], "eyes": ren["regions"]["eyes"], "hair": ren["regions"]["hair"]}
        for tag, side, regs in (("reference", ref, ref["regions"]), (label, ren, native)):
            img = side["img"].astype(float)
            skin = regs["skin_face"] & ~regs["eyes"] & ~regs["hair"]
            for s in "LR":
                w = LK.eye_windows(skin.shape, side["landmarks"], s, regs["eyes"])
                if w:
                    for key, col in (("lid", (40, 60, 255)), ("cheek", (255, 30, 30))):
                        m = w[key] & skin
                        img[m] = img[m] * 0.45 + np.array(col) * 0.55
            ys, xs = np.nonzero(regs["skin_face"])
            crop = img[max(0, ys.min() - 8):ys.max() + 8, max(0, xs.min() - 8):xs.max() + 8].astype(np.uint8)
            t = Image.fromarray(crop)
            t = t.resize((260, int(260 * t.height / t.width)), Image.LANCZOS)
            tiles.append((t, tag))
    H = max(t.height for t, _ in tiles)
    sheet = Image.new("RGB", (266 * len(tiles), H + 24), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, (t, tag) in enumerate(tiles):
        sheet.paste(t, (266 * i, 24))
        d.text((266 * i + 4, 4), tag, fill=(0, 0, 0), font=SH.font(13))
    sheet.save(os.path.join(out, "face_windows.png"), optimize=True)


def table(work, out):
    rows = {}
    for c in CASES:
        r = {}
        for tag in ("old", "new"):
            p = os.path.join(work, tag, c, "fidelity.json")
            if os.path.exists(p):
                o = json.load(open(p))["overall"]
                r[tag] = {"score": o["score"], "subscores": o["subscores"]}
                if tag == "new":
                    r["new"].update({"hair_parts": o["hair"]["parts"],
                                     "skin": {k: {x: v[x] for x in ("dC_shade_median", "da_p90_median", "de00_median")}
                                              for k, v in o["skin"].items()},
                                     "face": o["face"]["difference_mean"]})
        rows[c] = r
    with open(os.path.join(out, "validation_scores.json"), "w") as f:
        f.write(json.dumps(A.M.rounded(rows), indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    old_dir, work, out = sys.argv[1:4]
    segmentation(old_dir, work, out)
    face_windows(work, out)
    table(work, out)
    print("ok")
