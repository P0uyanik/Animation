"""T-124 short comparison clips: 2x2 grids of the same frames under four settings, full frame at 50% and a 100% crop.
    python make_clips.py <runs dir> <out dir> <first> <last>
Writes clip_full.mp4 and clip_crop.mp4 (H.264 crf 18, looped 4x for viewing) from the 16-bit clip runs."""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

RUNS = [("clip_baseline", "current final 128 spp ~436 s/fr"), ("clip_thr05", "final720 thr 0.05 ~207 s/fr"),
        ("clip_spp64", "64 spp ~218 s/fr"), ("clip_review16", "review 16 spp ~65 s/fr")]
CROP = (380, 300, 320, 240)  # girl: glasses, eyes, hair edge, fibres


def main():
    runs, out, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ("full", "crop"):
            for i, f in enumerate(range(a, b + 1)):
                tiles = []
                for r, lab in RUNS:
                    im = Image.open(os.path.join(runs, r, f"frame_{f:04d}.png")).convert("RGB")
                    if kind == "full":
                        im = im.resize((640, 360), Image.LANCZOS)
                    else:
                        x, y, w, h = CROP
                        im = im.crop((x, y, x + w, y + h))
                    d = ImageDraw.Draw(im)
                    d.rectangle([0, 0, 7 * len(lab) + 6, 14], fill=(0, 0, 0))
                    d.text((3, 1), lab, fill=(255, 255, 255))
                    tiles.append(im)
                w, h = tiles[0].size
                g = Image.new("RGB", (2 * w, 2 * h))
                for k, t in enumerate(tiles):
                    g.paste(t, ((k % 2) * w, (k // 2) * h))
                g.save(os.path.join(tmp, f"{kind}_{i:03d}.png"))
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-stream_loop", "3", "-framerate", "24", "-i",
                            os.path.join(tmp, f"{kind}_%03d.png"), "-c:v", "libx264", "-crf", "18", "-pix_fmt",
                            "yuv420p", "-movflags", "+faststart", os.path.join(out, f"clip_{kind}.mp4")], check=True)


if __name__ == "__main__":
    main()
