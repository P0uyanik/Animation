"""Measure shot-camera visibility from lossless, co-registered ID passes.

For each requested frame supply visible/frame_####.png (the shot with occluders)
and cup_only/frame_####.png (just the cup, in the same pose, camera and sampling).
Use grayscale bytes or palette indices. Zero is background. Use one unique ID
for the cup and for each pupil region. See docs/evaluation/tools/T-123.
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image


def read_ids(path):
    with Image.open(path) as image:
        if image.format != "PNG" or image.mode not in ("L", "P"):
            raise ValueError(f"{path}: expected an 8-bit grayscale or indexed PNG")
        return np.array(image)


def largest_patch(mask):
    """Count the largest 8-connected component. Pad the stride to avoid row wrap."""
    y, x = np.nonzero(mask)
    stride = mask.shape[1] + 2
    remaining = set((y * stride + x).tolist())
    offsets = (-stride - 1, -stride, -stride + 1, -1, 1, stride - 1, stride, stride + 1)
    largest = 0
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            pixel = stack.pop()
            size += 1
            for offset in offsets:
                neighbor = pixel + offset
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        largest = max(largest, size)
    return largest


def measure(visible, isolated, cup_id, eyes):
    if visible.shape != isolated.shape:
        raise ValueError("pass dimensions differ")
    cup = visible == cup_id
    silhouette = isolated == cup_id
    if np.any((isolated != 0) & ~silhouette):
        raise ValueError("unexpected ID in cup-only pass")
    if np.any(cup & ~silhouette):
        raise ValueError("visible cup extends outside the cup-only silhouette")
    full = int(silhouette.sum())
    patch = largest_patch(cup)
    return {
        "cup_patch_px": patch,
        "cup_only_px": full,
        "cup_patch_pct": 100 * patch / full if full else None,
        **{f"{name}_pupil_px": int((visible == label).sum()) for name, label in eyes.items()},
    }


def frame_ranges(frames):
    spans = []
    for f in frames:
        if spans and spans[-1][1] + 1 == f:
            spans[-1][1] = f
        else:
            spans.append([f, f])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans) or "none"


def summary(rows, eyes, cup_threshold, pupil_threshold):
    lines = [f"Frames {rows[0]['frame']}-{rows[-1]['frame']} ({len(rows)} frames)"]

    def metric(key, title, threshold=None):
        valid = [row for row in rows if row[key] is not None]
        if valid:
            minimum = min(row[key] for row in valid)
            at_min = frame_ranges(r["frame"] for r in valid if r[key] == minimum)
            lines.append(f"{title} minimum {minimum:.6g} at {at_min}")
        else:
            lines.append(f"{title} minimum undefined")
        if threshold is not None:
            low = [r["frame"] for r in valid if r[key] < threshold]
            unit = "frame" if len(low) == 1 else "frames"
            lines.append(f"  Below {threshold:g} ({len(low)} {unit}): {frame_ranges(low)}")

    metric("cup_patch_px", "Cup largest patch (px)")
    metric("cup_patch_pct", "Cup largest patch (% of isolated silhouette)", cup_threshold)
    absent = [r["frame"] for r in rows if r["cup_only_px"] == 0]
    lines.append(f"No in-frame cup silhouette (percentage undefined): {frame_ranges(absent)}")
    for name in eyes:
        metric(f"{name}_pupil_px", f"{name} visible pupil (px)", pupil_threshold)
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("masks", type=Path, help="directory containing visible/ and cup_only/")
    parser.add_argument("--frames", type=int, nargs=2, required=True, metavar=("FIRST", "LAST"))
    parser.add_argument("--cup-id", type=int, default=255)
    parser.add_argument("--eye", action="append", required=True, metavar="CHARACTER.SIDE=ID")
    parser.add_argument("--cup-threshold", type=float, required=True, metavar="PERCENT")
    parser.add_argument("--pupil-threshold", type=int, required=True, metavar="PX")
    parser.add_argument("--out", type=Path, required=True, help="directory for readability.csv and summary.txt")
    args = parser.parse_args(argv)
    first, last = args.frames
    if last < first:
        parser.error("FIRST must be <= LAST")
    if not 0 <= args.cup_threshold <= 100 or args.pupil_threshold < 0:
        parser.error("expected a cup threshold in [0, 100] and a nonnegative pupil threshold")
    eyes = {}
    try:
        for item in args.eye:
            name, value = item.rsplit("=", 1)
            character, _, side = name.rpartition(".")
            if not character or not side or name in eyes:
                raise ValueError(f"expected a unique CHARACTER.SIDE in {item!r}")
            eyes[name] = int(value)
    except ValueError as error:
        parser.error(str(error))
    ids = [args.cup_id, *eyes.values()]
    if len(set(ids)) != len(ids) or any(not 1 <= label <= 255 for label in ids):
        parser.error("cup and eye IDs must be distinct integers from 1 to 255")

    rows = []
    shape = None
    for frame in range(first, last + 1):
        filename = f"frame_{frame:04d}.png"
        try:
            visible = read_ids(args.masks / "visible" / filename)
            if shape is not None and visible.shape != shape:
                raise ValueError("shot resolution changed")
            shape = visible.shape
            isolated = read_ids(args.masks / "cup_only" / filename)
            rows.append({"frame": frame, **measure(visible, isolated, args.cup_id, eyes)})
        except (OSError, ValueError) as error:
            parser.error(f"frame {frame}: {error}")

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "readability.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    report = summary(rows, eyes, args.cup_threshold, args.pupil_threshold)
    (args.out / "summary.txt").write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
