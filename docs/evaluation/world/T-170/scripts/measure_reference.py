"""T-170 throwaway: measure material patches and frame statistics on the two reference videos.

python3 docs/evaluation/world/T-170/scripts/measure_reference.py   (needs ffmpeg, numpy, Pillow)
Writes ../measurements.json. Patch boxes are native pixels (left, top, right, bottom) of the given video frame;
every box was checked on an enlarged crop (sheet 02). Values are 8-bit display sRGB as decoded by ffmpeg.
"""
import json, os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "..", "..", "..", "references")
VID = {"pb": "video_paperboat.mp4", "wt": "video_watertable.mp4"}
TMP = tempfile.mkdtemp()

def frame(key):
    clip, idx = key
    out = os.path.join(TMP, "%s_%03d.png" % (clip, idx))
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(REF, VID[clip]), "-vf", "select=eq(n\\,%d)" % idx,
                        "-vsync", "0", "-frames:v", "1", out], check=True)
    return Image.open(out).convert("RGB")

P=[
('wood_worn_table',('pb',96),(250,360,600,440)),
('wood_oak_apron',('wt',0),(256,870,336,898)),
('wood_oak_shadow_side',('wt',0),(88,952,112,1012)),
('wood_shelf_bg',('wt',0),(555,260,600,300)),
('floor_wood',('wt',0),(430,654,495,689)),
('paper_lit',('pb',96),(370,235,415,280)),
('paper_shade',('pb',96),(438,298,498,318)),
('paper_cool_tray',('pb',168),(350,270,400,300)),
('plastic_tray_blue',('pb',168),(30,220,190,280)),
('plastic_scissor_yellow',('pb',96),(40,72,50,102)),
('plastic_scissor_blue',('pb',96),(72,108,82,132)),
('toy_paint_red',('wt',0),(124,262,136,274)),
('water_tray_pb',('pb',168),(50,360,250,450)),
('skin_hand',('pb',168),(565,215,625,280)),
('fleece_cream',('pb',96),(212,132,262,168)),
('fleece_yellow',('pb',96),(765,190,845,280)),
('fleece_blue',('pb',96),(5,215,45,300)),
('yarn_brown',('wt',0),(270,310,400,370)),
('plush_grey_toy',('wt',0),(50,450,175,525)),
('teddy_plush',('wt',0),(776,740,826,790)),
('wall_cream',('wt',0),(484,200,520,250)),
('rug_teal',('wt',0),(170,1005,235,1050)),
('rug_sage',('wt',0),(525,994,625,1034)),
('rug_rose',('wt',0),(285,1040,375,1095)),
('bin_sage',('wt',0),(35,365,95,415)),
('bin_coral',('wt',0),(125,360,175,400)),
('cup_matte',('pb',96),(10,160,85,195)),
('window_blown',('wt',0),(160,60,240,140)),
]

LUMA = np.array([.2126, .7152, .0722])
LAP = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 128)

def main():
    patches = {}
    for name, key, box in P:
        a = np.asarray(frame(key).crop(box), float); med = np.median(a.reshape(-1, 3), 0); Y = a @ LUMA
        Yi = Image.fromarray(Y.astype("uint8")); blur = np.asarray(Yi.filter(ImageFilter.GaussianBlur(4)), float)
        patches[name] = {"clip": key[0], "frame": key[1], "box": list(box), "hex": "#%02X%02X%02X" % tuple(int(x) for x in med),
                         "Y50": round(float(np.median(Y)), 1),
                         "S50": round(float(np.median((a.max(2) - a.min(2)) / np.maximum(a.max(2), 1))), 3),
                         "R_over_B": round(float(med[0] / max(med[2], 1)), 2),
                         "hf_rms": round(float(np.sqrt(np.mean((Y - blur) ** 2))), 2),
                         "Y99_over_Y50": round(float(np.percentile(Y, 99) / np.median(Y)), 2)}
    frames = {}
    for clip, step, count in (("pb", 24, 13), ("wt", 12, 11)):
        for i in range(count):
            im = frame((clip, i * step)); a = np.asarray(im, float); Y = a @ LUMA
            S = (a.max(2) - a.min(2)) / np.maximum(a.max(2), 1)
            L = np.asarray(im.convert("L").filter(LAP), float) - 128; t = 32
            E = np.array([L[y:y + t, x:x + t].var() for y in range(0, L.shape[0] - t + 1, t) for x in range(0, L.shape[1] - t + 1, t)])
            frames["%s_%03d" % (clip, i * step)] = {
                "Y05": round(float(np.percentile(Y, 5)), 1), "Y50": round(float(np.median(Y)), 1), "Y95": round(float(np.percentile(Y, 95)), 1),
                "S50_pct": round(100 * float(np.median(S)), 1), "S90_pct": round(100 * float(np.percentile(S, 90)), 1),
                "pct_px_S_gt_70": round(100 * float(np.mean(S > 0.7)), 1),
                "pct_tiles_below_0.15_E95": round(100 * float(np.mean(E < 0.15 * np.percentile(E, 95))), 0)}
    json.dump({"patches": patches, "frames": frames}, open(os.path.join(HERE, "..", "measurements.json"), "w"), indent=1)
    for k, v in patches.items():
        print("%-24s" % k, v["hex"], v["Y50"], v["S50"], v["R_over_B"], v["hf_rms"], v["Y99_over_Y50"])

if __name__ == "__main__":
    main()
