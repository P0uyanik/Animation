"""T-187: joins the rendered frames of the three e912 scenes into one preview clip and a contact sheet.

    python3 episodes/e912_paper_boat/assemble.py <run-id> [--out docs/evaluation/video/T-187]

Reads shots/s0N0/shot.scene.json ("x_t187": shot list and render range) and the frames of
shots/s0N0/build/runs/<run-id>/render/frame_NNNN.png, in the order s010, s020, s030. Writes
  <out>/T-187_paper_boat_h264.mp4   H.264 (crf 20, yuv420p, 24 fps): all rendered frames back to back
  <out>/contact_sheet.jpg           one tile every 12 frames (0.5 s) plus the first frame of every shot, labelled
                                    with the shot, the scene and its frame
  <out>/assembly.json               the frame list (clip frame -> scene, scene frame, shot)."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCENES = ("s010", "s020", "s030")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "evaluation", "video", "T-187"))
    ap.add_argument("--every", type=int, default=12)
    ap.add_argument("--cols", type=int, default=6)
    a = ap.parse_args()
    seq = []
    for s in SCENES:
        sc = json.load(open(os.path.join(HERE, "shots", s, "shot.scene.json")))
        x = sc["x_t187"]
        fa, fb = x["render_frames"]
        rdir = os.path.join(HERE, "shots", s, "build", "runs", a.run, "render")
        for f in range(fa, fb + 1):
            shot = next(str(sh["shot"]) for sh in x["shots"] if sh["frames"][0] <= f <= sh["frames"][1])
            p = os.path.join(rdir, f"frame_{f:04d}.png")
            if not os.path.isfile(p):
                raise SystemExit(f"missing frame {p}")
            seq.append({"scene": s, "frame": f, "shot": shot, "path": p})
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="t187_")
    try:
        for k, e in enumerate(seq):
            os.symlink(e["path"], os.path.join(tmp, f"f{k:05d}.png"))
        clip = os.path.join(a.out, "T-187_paper_boat_h264.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(tmp, "f%05d.png"),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        clip], check=True)
    finally:
        shutil.rmtree(tmp)
    firsts = {k for k, e in enumerate(seq) if k == 0 or e["shot"] != seq[k - 1]["shot"]}
    tiles = sorted(firsts | set(range(0, len(seq), a.every)))
    w, h = 320, 180
    rows = (len(tiles) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * w, rows * (h + 16)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for n, k in enumerate(tiles):
        e = seq[k]
        im = Image.open(e["path"]).convert("RGB").resize((w, h))
        x, y = (n % a.cols) * w, (n // a.cols) * (h + 16)
        sheet.paste(im, (x, y + 16))
        label = f"shot {e['shot']}  {e['scene']} f{e['frame']}  t={k / 24:.1f}s" + ("  [cut]" if k in firsts else "")
        d.text((x + 4, y + 2), label, fill=(255, 220, 120) if k in firsts else (230, 230, 230))
    sheet.save(os.path.join(a.out, "contact_sheet.jpg"), quality=88)
    json.dump({"run": a.run, "fps": 24, "frames": len(seq), "seconds": round(len(seq) / 24, 2),
               "clip": [{k: v for k, v in e.items() if k != "path"} for e in seq]},
              open(os.path.join(a.out, "assembly.json"), "w"), indent=0)
    print(f"{len(seq)} frames ({len(seq) / 24:.1f} s) -> {os.path.relpath(clip, ROOT)}, contact_sheet.jpg ({len(tiles)} tiles)")


if __name__ == "__main__":
    main()
