#!/usr/bin/env python3
"""Emotional vocal sounds on a rendered clip (T-195): cue list -> mix -> mux. docs/AUDIO.md.

    python3 pipeline/audio/vocal.py cues --shots <scene dirs or shot files...> --assembly assembly.json --out cues.json
    python3 pipeline/audio/vocal.py mix  --cues cues.json --out vocal.wav [--mono]
    python3 pipeline/audio/vocal.py mux  --video in.mp4 --audio vocal.wav --out out.mp4
    python3 pipeline/audio/vocal.py demo --shots ... --assembly ... --video in.mp4 --out-dir <dir> [--name N] [--mono]

`demo` runs all three and writes <dir>/<N>.mp4 (the video stream copied bit for bit, AAC 160 kb/s 48 kHz added),
<dir>/<N>.cues.json (cue list + mixing plan + the WAV's sha256) and keeps the WAV only with --keep-wav.
The input video is never modified. Needs ffmpeg / ffprobe on PATH for mux.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

if __package__:
    from . import cues as cuemod, library, mix, wavio
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cues as cuemod
    import library
    import mix
    import wavio


def shot_files(items: list[str]) -> list[Path]:
    out = []
    for s in items:
        p = Path(s)
        out.append(p / "shot.scene.json" if p.is_dir() else p)
    return out


def video_stream_md5(video: Path) -> str:
    """md5 of the video stream's packets (ffmpeg's own stream hash), to show the mux copied the picture unchanged."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def probe(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=index,codec_type,codec_name,sample_rate,channels,width,height,nb_frames,duration",
                        "-of", "json", str(video)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def mux(video: Path, audio: Path, out: Path, bitrate: str = "160k") -> dict:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found")
    if out.resolve() == video.resolve():
        raise ValueError("mux writes a copy; --out must differ from --video")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(audio),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", bitrate, "-ar", "48000",
                    "-shortest", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact",
                    "-movflags", "+faststart", str(out)], check=True)
    src, dst = video_stream_md5(video), video_stream_md5(out)
    if src != dst:
        raise RuntimeError(f"video stream changed in the mux ({src} != {dst})")
    return {"videoStreamMd5": dst, "streams": probe(out)["streams"]}


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cues")
    c.add_argument("--shots", nargs="+", required=True)
    c.add_argument("--assembly", required=True)
    c.add_argument("--out", required=True)
    m = sub.add_parser("mix")
    m.add_argument("--cues", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--mono", action="store_true")
    x = sub.add_parser("mux")
    x.add_argument("--video", required=True)
    x.add_argument("--audio", required=True)
    x.add_argument("--out", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--shots", nargs="+", required=True)
    d.add_argument("--assembly", required=True)
    d.add_argument("--video", required=True)
    d.add_argument("--out-dir", required=True)
    d.add_argument("--name", default="vocal")
    d.add_argument("--mono", action="store_true")
    d.add_argument("--keep-wav", action="store_true")
    a = ap.parse_args(argv)

    probs = library.check()
    if probs:
        print("library problems:\n  " + "\n  ".join(probs), file=sys.stderr)
        return 1
    if a.cmd == "cues":
        doc = cuemod.derive(shot_files(a.shots), json.loads(Path(a.assembly).read_text(encoding="utf-8")))
        write_json(Path(a.out), doc)
        print(f"{len(doc['cues'])} cue(s) -> {a.out}")
    elif a.cmd == "mix":
        doc = json.loads(Path(a.cues).read_text(encoding="utf-8"))
        y, decisions, bus = mix.render(doc, stereo=not a.mono)
        wavio.write(Path(a.out), y, mix.RATE)
        print(f"{len(decisions)} cue(s), bus {bus} dB -> {a.out} sha256 {wavio.sha256(Path(a.out))}")
    elif a.cmd == "mux":
        info = mux(Path(a.video), Path(a.audio), Path(a.out))
        print(f"-> {a.out}, video stream unchanged ({info['videoStreamMd5']})")
    else:
        out_dir = Path(a.out_dir)
        doc = cuemod.derive(shot_files(a.shots), json.loads(Path(a.assembly).read_text(encoding="utf-8")))
        y, decisions, bus = mix.render(doc, stereo=not a.mono)
        wav = out_dir / f"{a.name}.wav"
        wavio.write(wav, y, mix.RATE)
        info = mux(Path(a.video), wav, out_dir / f"{a.name}.mp4")
        peak = float(abs(y).max()) if len(y) else 0.0
        report = {**doc, "cues": decisions, "mix": {
            "rate": mix.RATE, "channels": 1 if a.mono else 2, "busGainDb": bus, "busPeakLimitDbfs": mix.BUS_PEAK_DBFS,
            "peakDbfs": round(20 * __import__("math").log10(peak), 2) if peak > 0 else None,
            "wavSha256": wavio.sha256(wav), "wavSamples": len(y)},
            "video": {"input": a.video, "inputSha256": hashlib.sha256(Path(a.video).read_bytes()).hexdigest(),
                      "output": f"{a.name}.mp4", **info}}
        write_json(out_dir / f"{a.name}.cues.json", report)
        if not a.keep_wav:
            wav.unlink()
        for dcs in decisions:
            print(f"  {dcs['time']:6.2f} s  {dcs['character']:7s} {dcs['cue']:8s} {dcs['sound']}  "
                  f"{dcs['cents']:+.0f} c  {dcs['gainDb']:+.1f} dB  pan {dcs['pan']:+.2f}")
        print(f"bus {bus} dB, peak {report['mix']['peakDbfs']} dBFS -> {out_dir / (a.name + '.mp4')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
