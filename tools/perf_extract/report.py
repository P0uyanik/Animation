"""Combine frame measurements and reviewed annotations into calibration tables."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from measure import EVALUATION, write_csv, write_json
from observations import BEATS, EYELIDS, GAZE, INSERTS


def interval(start, end, fps):
    if start < 0 or end <= start or fps <= 0:
        raise ValueError("Expected non-empty, half-open frame range and positive fps")
    return dict(first_frame=start, end_frame_exclusive=end, duration_frames=end-start,
                start_s=round(start/fps, 5), end_s=round(end/fps, 5),
                duration_s=round((end-start)/fps, 5))


def exposure_summary(rows, eyelids, fps):
    exposed = len(rows)
    detected = sum(int(row["face_matched"]) for row in rows)
    count = sum(kind == "blink" for _, _, _, kind in eyelids)
    return dict(reviewed_frames=exposed, reviewed_s=round(exposed/fps, 5),
                face_returned=sum(int(row["face_returned"]) for row in rows),
                face_matched=detected, face_matched_pct=round(100*detected/exposed, 2),
                pose_matched=sum(row["pose_nose_x_px"] != "" for row in rows),
                blinks=count, partial_dips=len(eyelids)-count,
                blinks_per_visible_min=round(count*60*fps/exposed, 2))


def event(clip, cast, kind, start, end, label, fps, by_frame, peak=None):
    row = dict(clip=clip, character=cast, kind=kind, **interval(start, end, fps),
               observation=label, peak_frame=peak, flow_steps=None, head_dx_px=None,
               head_dy_px=None, head_droll_deg=None, face_matched_frames=None, jaw_open_median=None,
               peak_eyeBlinkLeft=None, peak_eyeBlinkRight=None)
    if kind == "insert":
        return row
    frames = [by_frame[i] for i in range(start, end)]
    row["face_matched_frames"] = sum(int(f["face_matched"]) for f in frames)
    if kind == "acting_beat":
        # A sample at frame i measures displacement from i-1. Do not include
        # an incoming step from outside this beat, or bridge failed flow.
        steps = [f for f in frames[1:] if f["head_dx_px"] != "" and f["head_dy_px"] != ""]
        row["flow_steps"] = len(steps)
        if len(steps) == end-start-1 and steps:
            for field in ("head_dx_px", "head_dy_px"):
                row[field] = round(sum(float(f[field]) for f in steps), 2)
            if all(f["head_droll_deg"] != "" for f in steps):
                row["head_droll_deg"] = round(sum(float(f["head_droll_deg"]) for f in steps), 2)
        jaws = [float(f["jawOpen"]) for f in frames if f["jawOpen"] != ""]
        if jaws:
            row["jaw_open_median"] = round(median(jaws), 4)
    if peak is not None:
        for field in ("eyeBlinkLeft", "eyeBlinkRight"):
            value = by_frame[peak][field]
            row["peak_" + field] = float(value) if value != "" else None
    return row


def assemble(directory):
    sources = json.loads((directory / "sources.json").read_text())
    by_cast = defaultdict(dict)
    with (directory / "frame_measurements.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            frames = by_cast[row["clip"], row["character"]]
            i = int(row["frame"])
            if i in frames:
                raise ValueError(f"Duplicate sample {i}: {row['clip']} {row['character']}")
            frames[i] = row

    events, coverage = [], []
    for (clip, cast), beats in BEATS.items():
        key = clip, cast
        fps = sources["videos"][clip]["fps"]
        frames = by_cast[key]
        lids = EYELIDS[key]
        coverage.append(dict(clip=clip, character=cast,
                             **exposure_summary(frames.values(), lids, fps)))
        for kind, spans in (("acting_beat", beats), ("gaze", GAZE[key])):
            covered = [i for start, end, _ in spans for i in range(start, end)]
            if covered != sorted(frames):
                raise ValueError(f"{key} {kind}: annotations must cover the exact reviewed frames")
            for start, end, label in spans:
                events.append(event(clip, cast, kind, start, end, label, fps, frames))
        for start, peak, end, kind in lids:
            label = ("Visible lid closes and reopens" if kind == "blink"
                     else "Lid dips and recovers with iris still visible")
            events.append(event(clip, cast, kind, start, end, label, fps, frames, peak))
    for cast, start, end, label in INSERTS:
        events.append(event("paperboat", cast, "insert", start, end, label,
                            sources["videos"]["paperboat"]["fps"], {}))
    write_json(directory / "performance.json", dict(coverage=coverage, intervals=events))
    write_csv(directory / "performance.csv", events)
    write_csv(directory / "coverage.csv", coverage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=EVALUATION)
    assemble(parser.parse_args().out)
