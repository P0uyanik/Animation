"""Extract a shared viseme track from a local PCM WAV."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import wave

if __package__:
    from .validate import validate
else:
    from validate import validate


RHUBARB_VERSION = "1.13.0"
RHUBARB_SHAPES = dict(zip("ABCDEFGHX", ("MBP", "C", "E", "AI", "O", "WQ", "FV", "L", "rest")))
SPELLINGS = {
    "oo": "U", "ee": "E", "ea": "E", "ow": "O", "oh": "O", "qu": "WQ",
    "ph": "FV", "ai": "AI", "a": "AI", "i": "AI", "e": "E", "y": "E",
    "o": "O", "u": "U", "w": "WQ", "f": "FV", "v": "FV", "m": "MBP",
    "b": "MBP", "p": "MBP", "l": "L",
}


def wav_features(wav, fps):
    """RMS and zero crossings/second of the loudest channel in each frame."""
    rate, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
    scale = 1 << (width * 8 - 1)
    features = []
    total = wav.getnframes()
    for frame in range((total * fps + rate - 1) // rate):
        start = frame * rate // fps
        end = min(total, (frame + 1) * rate // fps)
        data = wav.readframes(end - start)
        if len(data) != (end - start) * channels * width:
            raise ValueError("truncated WAV samples")
        samples = [int.from_bytes(data[i:i + width], "little", signed=width > 1)
                   for i in range(0, len(data), width)]
        if width == 1:
            samples = [sample - 128 for sample in samples]
        channel = max((samples[c::channels] for c in range(channels)), key=sum_squares)
        rms = math.sqrt(sum_squares(channel) / len(channel)) / scale
        crossings = sum((a < 0) != (b < 0) for a, b in zip(channel, channel[1:]))
        features.append((rms, crossings * rate / len(channel)))
    return features


def sum_squares(samples):
    return sum(value * value for value in samples)


def fallback(features, text):
    threshold = max(.002, .045 * max(level for level, _ in features))
    active = [i for i, (level, _) in enumerate(features) if level >= threshold]
    tokens = re.findall("|".join(SPELLINGS) + "|[a-z]", text.lower())
    labels = ["rest"] * len(features)
    for index, frame in enumerate(active):
        if tokens:
            token = tokens[index * len(tokens) // len(active)]
            labels[frame] = SPELLINGS.get(token, "C")
        else:
            _, crossings = features[frame]
            if crossings > 3000:
                labels[frame] = "FV"
            elif crossings > 650:
                labels[frame] = "E"
            else:
                labels[frame] = "AI"
    return [{label: 1.0} for label in labels], "fallback-text" if tokens else "fallback-audio"


def run_rhubarb(binary, audio, text):
    binary = str(binary.resolve(strict=True))
    version = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True)
    if not re.search(r"(?<![\w.])1\.13\.0(?![\w.+-])", version.stdout + version.stderr):
        raise ValueError(f"expected Rhubarb Lip Sync {RHUBARB_VERSION}")
    with tempfile.TemporaryDirectory() as folder:
        args = [binary, "-f", "json", "--extendedShapes", "GHX", "-r", "pocketSphinx"]
        if text:
            dialog = Path(folder, "dialog.txt")
            dialog.write_text(text, encoding="utf-8")
            args.extend(["--dialogFile", str(dialog)])
        result = subprocess.run([*args, str(audio.resolve())], capture_output=True, encoding="utf-8")
        if result.returncode:
            raise ValueError(f"Rhubarb failed: {result.stderr.strip()}")
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or not isinstance(data.get("mouthCues"), list):
            raise ValueError("missing Rhubarb mouthCues array")
        return data["mouthCues"]


def sample_cues(cues, count, fps, duration):
    """Integrate cue overlap, retaining sub-frame cues and silent gaps."""
    frames = [{"rest": 1.0} for _ in range(count)]
    previous = 0
    for cue in cues:
        if not isinstance(cue, dict) or cue.get("value") not in RHUBARB_SHAPES:
            raise ValueError("invalid Rhubarb mouth cue")
        start, end = cue.get("start"), cue.get("end")
        if any(type(t) not in (float, int) or not math.isfinite(t) for t in (start, end)):
            raise ValueError("invalid Rhubarb cue times")
        if not previous <= start < end <= duration + .011:
            raise ValueError("Rhubarb cues out of order or outside WAV duration")
        previous = end
        shape = RHUBARB_SHAPES[cue["value"]]
        for i in range(math.floor(start * fps), min(count, math.ceil(end * fps))):
            left, right = i / fps, min(duration, (i + 1) / fps)
            overlap = max(0, min(right, end) - max(left, start)) / (right - left)
            weights = frames[i]
            weights["rest"] -= overlap
            weights[shape] = weights.get(shape, 0) + overlap
    return frames


def smooth(frames):
    result = []
    for i in range(len(frames)):
        weights = {}
        for offset, gain in ((-1, .25), (0, .5), (1, .25)):
            index = i + offset
            source = frames[index] if 0 <= index < len(frames) else {"rest": 1}
            for name, weight in source.items():
                weights[name] = weights.get(name, 0) + gain * weight
        result.append({name: round(weight, 8) for name, weight in weights.items() if weight > 1e-8})
    return result


def extract(audio, text, fps, rhubarb):
    with wave.open(str(audio), "rb") as wav:
        n, rate = wav.getnframes(), wav.getframerate()
        if n < 1 or rate < fps or not 1 <= wav.getsampwidth() <= 4:
            raise ValueError("expected nonempty 8/16/24/32-bit PCM WAV with sample rate >= fps")
        duration = n / rate
        if rhubarb is None:
            frames, source = fallback(wav_features(wav, fps), text)
        else:
            cues = run_rhubarb(rhubarb, audio, text)
            frames = sample_cues(cues, (n * fps + rate - 1) // rate, fps, duration)
            source = "rhubarb-" + RHUBARB_VERSION
    doc = dict(format="plush.visemes/1", duration=duration, fps=fps, source=source, frames=smooth(frames))
    validate(doc)
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--text", default="")
    parser.add_argument("--fps", choices=(24, 30), type=int, default=30)
    parser.add_argument("--rhubarb", type=Path, help="local Rhubarb Lip Sync 1.13.0 executable")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.audio.resolve() == args.out.resolve():
            raise ValueError("audio and output must use different paths")
        doc = extract(args.audio, args.text, args.fps, args.rhubarb)
        tmp = tempfile.NamedTemporaryFile(dir=args.out.parent, delete=False, mode="w",
                                          encoding="utf-8")
        try:
            with tmp:
                json.dump(doc, tmp, indent=2, allow_nan=False)
                tmp.write("\n")
            os.replace(tmp.name, args.out)
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    except (OSError, EOFError, ValueError, wave.Error, subprocess.SubprocessError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()
