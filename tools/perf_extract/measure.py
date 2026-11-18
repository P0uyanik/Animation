"""Offline, frame-addressable measurements for the two T-106 references."""

import argparse
import csv
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from reference import ANCHORS, DISPLAY, SHOTS

ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "docs/evaluation/animation/T-106"
VIDEO_HASHES = {
    "paperboat": "31fa6189014db231131f2dce4912a6c8814affa69bfd5df797f61142cfb260f5",
    "watertable": "b8101437d65fced27e461858214ea64712307f6d81a70b75305d75320e2dca5b",
}
SCORES = ("eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight")
VISION = mp.tasks.vision


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def eye_anchor(knots, frame, scale):
    """Return x, y, face width in source pixels, only within the marked window."""
    if not knots[0][0] <= frame <= knots[-1][0]:
        return None
    frames, xs, ys, widths = zip(*knots)
    return tuple(float(np.interp(frame, frames, values) * factor)
                 for values, factor in zip((xs, ys, widths), (*scale, scale[0])))


def bounds(anchor, shape, x_radius, above, below):
    x, y, width = anchor
    h, w = shape[:2]
    return (max(0, round(x - width * x_radius)), max(0, round(y - width * above)),
            min(w, round(x + width * x_radius)), min(h, round(y + width * below)))


def motion_step(before, after, anchor):
    """Estimate screen translation and in-plane roll on the upper face."""
    left, top, right, bottom = bounds(anchor, before.shape, .44, .35, .25)
    patch = before[top:bottom, left:right]
    corners = cv2.goodFeaturesToTrack(patch, 64, .015, 4)
    if corners is None:
        return None
    points = corners + np.float32([left, top])
    moved, valid, _ = cv2.calcOpticalFlowPyrLK(before, after, points, None)
    back, returned, _ = cv2.calcOpticalFlowPyrLK(after, before, moved, None)
    good = (valid.ravel() & returned.ravel()).astype(bool)
    good &= np.linalg.norm((back - points)[:, 0], axis=1) < 1
    if good.sum() < 5:
        return None
    source, target = points[good, 0], moved[good, 0]
    dx, dy = np.median(target - source, axis=0)
    matrix, inliers = cv2.estimateAffinePartial2D(source, target, ransacReprojThreshold=1.5)
    roll = None
    if matrix is not None and inliers.sum() >= 5:
        roll = float(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))
    return float(dx), float(dy), roll


def mp_image(bgr):
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def face_measure(detector, frame, anchor):
    left, top, right, bottom = bounds(anchor, frame.shape, .78, .81, .73)
    result = detector.detect(mp_image(frame[top:bottom, left:right]))
    row = dict(face_returned=0, face_matched=0, **dict.fromkeys(SCORES))
    if result.face_landmarks:
        row["face_returned"] = 1
        mesh = result.face_landmarks[0]
        x = left + (mesh[33].x + mesh[263].x) * .5 * (right - left)
        y = top + (mesh[33].y + mesh[263].y) * .5 * (bottom - top)
        if np.hypot(x - anchor[0], y - anchor[1]) <= .35 * anchor[2]:
            row["face_matched"] = 1
            row.update({item.category_name: round(item.score, 4)
                        for item in result.face_blendshapes[0] if item.category_name in SCORES})
    return row


def pose_matches(detector, frame, anchors):
    """Assign each high-visibility nose to at most one nearby eye-line anchor."""
    result = detector.detect(mp_image(frame))
    matches = {}
    for pose in result.pose_landmarks:
        nose = pose[0]
        if min(nose.visibility, nose.presence) < .5:
            continue
        x, y = nose.x * frame.shape[1], nose.y * frame.shape[0]
        distance, cast = min((np.hypot(x - ax, y - ay) / width, cast)
                             for cast, (ax, ay, width) in anchors.items())
        if distance <= .5 and (cast not in matches or distance < matches[cast][0]):
            matches[cast] = distance, round(x, 2), round(y, 2)
    return matches


def analyze_clip(name, path, face, pose):
    if digest(path) != VIDEO_HASHES[name]:
        raise ValueError(f"{path}: video differs from the annotated reference")
    video = cv2.VideoCapture(str(path))
    rows = []
    try:
        fps = video.get(cv2.CAP_PROP_FPS)
        width, height = (int(video.get(prop)) for prop in (3, 4))
        scale = (width / DISPLAY[name][0], height / DISPLAY[name][1])
        previous_gray = None
        previous_anchors = {}
        for start, end, _ in SHOTS[name]:
            previous_anchors.clear()
            tracks = {cast: knots for (clip, first, cast), knots in ANCHORS.items()
                      if clip == name and first == start}
            for i in range(start, end):
                ok, frame = video.read()
                if not ok:
                    raise ValueError(f"{path}: missing frame {i}")
                anchors = {cast: a for cast, knots in tracks.items()
                           if (a := eye_anchor(knots, i, scale)) is not None}
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                noses = pose_matches(pose, frame, anchors) if anchors else {}
                for cast, anchor in anchors.items():
                    delta = None
                    if cast in previous_anchors:
                        delta = motion_step(previous_gray, gray, previous_anchors[cast])
                    _, nose_x, nose_y = noses.get(cast, (None, None, None))
                    rows.append(dict(clip=name, shot_start=start, character=cast, frame=i,
                                     time_s=round(i / fps, 5), **face_measure(face, frame, anchor),
                                     pose_nose_x_px=nose_x, pose_nose_y_px=nose_y,
                                     head_dx_px=round(float(delta[0]), 3) if delta is not None else None,
                                     head_dy_px=round(delta[1], 3) if delta is not None else None,
                                     head_droll_deg=round(delta[2], 4)
                                     if delta is not None and delta[2] is not None else None))
                previous_gray, previous_anchors = gray, anchors
        if video.read()[0]:
            raise ValueError(f"{path}: unannotated trailing frames")
    finally:
        video.release()
    return rows, dict(file=path.name, sha256=VIDEO_HASHES[name], fps=fps, width=width,
                      height=height, frames=end)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def measure(args):
    def options(filename):
        return mp.tasks.BaseOptions(model_asset_path=str(args.models / filename),
                                    delegate=mp.tasks.BaseOptions.Delegate.CPU)

    models = ["face_landmarker.task", "pose_landmarker_full.task"]
    metadata = dict(models={model: digest(args.models / model) for model in models}, videos={})
    rows = []
    with ExitStack() as stack:
        face = stack.enter_context(VISION.FaceLandmarker.create_from_options(
            VISION.FaceLandmarkerOptions(base_options=options(models[0]), output_face_blendshapes=True)))
        pose = stack.enter_context(VISION.PoseLandmarker.create_from_options(
            VISION.PoseLandmarkerOptions(base_options=options(models[1]), num_poses=3)))
        for name in SHOTS:
            measurements, metadata["videos"][name] = analyze_clip(
                name, args.references / f"video_{name}.mp4", face, pose)
            rows.extend(measurements)
    args.out.mkdir(exist_ok=True, parents=True)
    write_csv(args.out / "frame_measurements.csv", rows)
    write_json(args.out / "sources.json", metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=ROOT / "build/perf-models")
    parser.add_argument("--references", type=Path, default=ROOT / "docs/references")
    parser.add_argument("--out", type=Path, default=EVALUATION)
    measure(parser.parse_args())
