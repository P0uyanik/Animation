"""T-113 reference crops for the expression sheets (read-only on the references).

    python3 docs/evaluation/characters/T-113/ref_frames.py <out dir>

Video frames: the T-106 face crop (tools/perf_extract/sheets.py face_crop, its eye-line anchors) of the frame named
in REFS; still references: a tile box given as fractions of the image (x0, y0, x1, y1). Writes <out>/<key>.png."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "perf_extract"))
import types  # noqa: E402

from PIL import Image  # noqa: E402

# measure.py imports mediapipe at module level; the crops need only its geometry helpers
_mp = types.ModuleType("mediapipe")
_mp.tasks = types.SimpleNamespace(vision=types.SimpleNamespace(), BaseOptions=None)
sys.modules.setdefault("mediapipe", _mp)
import sheets  # noqa: E402

B28 = "docs/references/boy_pipeline/28_boy_facial_expression_library.webp"
G34 = "assets/characters/girl_auburn_bun_glasses/references/uploads/ref_34.webp"
# key: (label, source)  source = ("video", clip, who, frame) | ("still", path, (x0, y0, x1, y1) fractions)
REFS = {
    "boy_interested": ("PB f288 eyes open wider, lips part", ("video", "paperboat", "boy", 288)),
    "boy_sleepy": ("PB f025 low-lidded hold", ("video", "paperboat", "boy", 25)),
    "boy_unimpressed": ("WT f010 brows low, mouth nearly closed", ("video", "watertable", "boy", 10)),
    "boy_reluctant": ("#28 r3c3 sulky pout", ("still", B28, (770 / 1493, 1075 / 2000, 1088 / 1493, 1445 / 2000))),
    "boy_focused": ("PB f140 eyes lowered, lips parted", ("video", "paperboat", "boy", 140)),
    "boy_Blink": ("WT f083 closed lids", ("video", "watertable", "boy", 83)),
    "boy_Smile": ("#28 r1c2 Happy (closed arcs)", ("still", B28, (424 / 1493, 175 / 2000, 742 / 1493, 545 / 2000))),
    "girl_delighted": ("PB f265 open smile", ("video", "paperboat", "girl", 265)),
    "girl_wonder": ("WT f000 eyes wide, rounded mouth", ("video", "watertable", "girl", 0)),
    "girl_eager": ("WT f033 leans and points", ("video", "watertable", "girl", 33)),
    "girl_shy": ("PB f012 small closed smile, eyes down", ("video", "paperboat", "girl", 12)),
    "girl_content": ("WT f120 settled smile", ("video", "watertable", "girl", 120)),
    "girl_Blink": ("WT f017 eyes close", ("video", "watertable", "girl", 17)),
    "girl_Laugh": ("#34 Laugh tile", ("still", G34, (1065 / 1493, 1760 / 2000, 1272 / 1493, 1958 / 2000))),
}
CAST = {"boy": "boy", "girl": "girl"}


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    vids = {}
    for key, (_, src) in REFS.items():
        if src[0] == "video":
            vids.setdefault(src[1], set()).add(src[3])
    frames = {clip: sheets.read_frames(__import__("pathlib").Path(ROOT) / "docs" / "references", clip, sorted(idx))
              for clip, idx in vids.items()}
    for key, (label, src) in REFS.items():
        if src[0] == "video":
            im = sheets.face_crop(frames[src[1]][src[3]], src[1], CAST[src[2]], src[3])
        else:
            img = Image.open(os.path.join(ROOT, src[1])).convert("RGB")
            x0, y0, x1, y1 = src[2]
            im = img.crop((int(x0 * img.width), int(y0 * img.height), int(x1 * img.width), int(y1 * img.height)))
        im.save(os.path.join(out, key + ".png"))
        print(key, label, im.size)


if __name__ == "__main__":
    main()
