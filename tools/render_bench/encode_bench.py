"""T-124 encoding comparison at 1280x720/24 from a lossless 16-bit PNG master sequence.

    python3 encode_bench.py <master dir> <first frame> <out dir>
Encodes H.264 8-bit (libx264, yuv420p), HEVC 10-bit (libx265, yuv420p10le) and AV1 10-bit (libsvtav1, yuv420p10le)
over a CRF sweep, then measures each against the master with ffmpeg's SSIM and PSNR filters (computed in
yuv444p16 from the RGB master, i.e. chroma subsampling counts against the codec), plus the same on the background
gradient crop (soft gradient: banding). Writes encode.json and per-encode files (mp4/mkv) in <out dir>."""
import json
import os
import re
import subprocess
import sys
import time

CODECS = {
    "h264_8bit": (["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p"], "mp4", [12, 16, 20, 24]),
    "hevc_10bit": (["-c:v", "libx265", "-preset", "slow", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
                    "-x265-params", "log-level=error"], "mp4", [14, 18, 22, 26]),
    "av1_10bit": (["-c:v", "libsvtav1", "-preset", "6", "-pix_fmt", "yuv420p10le"], "mp4", [18, 26, 34, 42]),
}
GRAD = (40, 380, 240, 240)  # background_gradient crop (crops_s010.json)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def measure(enc, master, first, crop=None):
    vf = "[0:v]format=yuv444p16{c}[a];[1:v]format=yuv444p16{c}[b];[a][b]ssim;[0:v]format=yuv444p16{c}[c];" \
         "[1:v]format=yuv444p16{c}[d];[c][d]psnr"
    c = f",crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}" if crop else ""
    p = run(["ffmpeg", "-hide_banner", "-i", enc, "-framerate", "24", "-start_number", str(first), "-i",
             os.path.join(master, "frame_%04d.png"), "-filter_complex", vf.replace("{c}", c), "-f", "null", "-"])
    ssim = re.search(r"SSIM .*All:([\d.]+)", p.stderr)
    psnr = re.search(r"PSNR .*average:([\d.inf]+)", p.stderr)
    return float(ssim.group(1)), float(psnr.group(1))


def main():
    master, first, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    n = len([f for f in os.listdir(master) if f.startswith("frame_") and f.endswith(".png")])
    raw = sum(os.path.getsize(os.path.join(master, f)) for f in os.listdir(master) if f.endswith(".png"))
    res = {"master": {"frames": n, "seconds": n / 24, "png16_bytes": raw}, "encodes": []}
    for name, (args, ext, crfs) in CODECS.items():
        for crf in crfs:
            path = os.path.join(out, f"{name}_crf{crf}.{ext}")
            t = time.time()
            p = run(["ffmpeg", "-hide_banner", "-y", "-framerate", "24", "-start_number", str(first), "-i",
                     os.path.join(master, "frame_%04d.png"), "-vf", "scale=out_color_matrix=bt709:out_range=tv",
                     *args, "-crf", str(crf), "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace",
                     "bt709", "-r", "24", path])
            if p.returncode:
                print(p.stderr[-800:])
                continue
            enc_s = time.time() - t
            size = os.path.getsize(path)
            ssim, psnr = measure(path, master, first)
            gssim, gpsnr = measure(path, master, first, GRAD)
            row = {"codec": name, "crf": crf, "bytes": size, "kbit_s": round(size * 8 / (n / 24) / 1000, 1),
                   "encode_s": round(enc_s, 1), "ssim": ssim, "psnr_db": psnr, "gradient_ssim": gssim,
                   "gradient_psnr_db": gpsnr}
            res["encodes"].append(row)
            print(json.dumps(row), flush=True)
    json.dump(res, open(os.path.join(out, "encode.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
