"""Validate every repository ``content/clips/*.clip.json`` file.

Run directly with Python 3.  ``--selftest`` also makes a corrupted copy in a
temporary directory and verifies that the validator rejects it.
"""

import argparse
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLIPS_DIR = ROOT / "content" / "clips"
PROFILE_PATH = ROOT / "pipeline" / "charsys" / "rig_profiles" / "humanoid_rigify.json"
QUATERNION_NORM_TOLERANCE = 1e-3


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value):
    if not _is_number(value):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _profile_roles():
    with PROFILE_PATH.open(encoding="utf-8") as stream:
        profile = json.load(stream)

    declared = profile["reference_pose"]["roles"]
    roles = set(declared)
    left, right = profile["reference_pose"]["mirror"]["suffix"]
    for role in declared:
        if role.endswith(left):
            roles.add(role[: -len(left)] + right)
    return roles


def _check_role(role, location, valid_roles, errors):
    if not isinstance(role, str) or role not in valid_roles:
        errors.append(f"{location}: unknown role {role!r}")


def _check_quaternion(value, location, errors):
    if not isinstance(value, list) or len(value) != 4:
        errors.append(f"{location}: quaternion must contain four numbers")
        return
    if not all(_is_number(component) for component in value):
        errors.append(f"{location}: quaternion must contain four numbers")
        return
    if not all(_is_finite_number(component) for component in value):
        errors.append(f"{location}: quaternion components must be finite")
        return
    norm = math.sqrt(sum(component * component for component in value))
    if abs(norm - 1.0) > QUATERNION_NORM_TOLERANCE:
        errors.append(
            f"{location}: quaternion norm {norm:.9g} is not within "
            f"{QUATERNION_NORM_TOLERANCE:g} of 1"
        )


def _check_track(role, track, frame_count, errors):
    location = f"tracks.{role}"
    if not isinstance(track, dict):
        errors.append(f"{location}: track must be an object")
        return

    kinds = [kind for kind in ("keys", "samples") if kind in track]
    if len(kinds) != 1:
        errors.append(f"{location}: track must contain exactly one of keys or samples")
        return

    kind = kinds[0]
    values = track[kind]
    if not isinstance(values, list):
        errors.append(f"{location}.{kind}: must be an array")
        return

    if frame_count is not None:
        if kind == "samples" and len(values) != frame_count:
            errors.append(
                f"{location}.samples: has {len(values)} samples, expected frame_count {frame_count}"
            )
        if kind == "keys" and not 1 <= len(values) <= frame_count:
            errors.append(
                f"{location}.keys: has {len(values)} keys, expected between 1 and frame_count {frame_count}"
            )

    previous_frame = None
    for index, value in enumerate(values):
        item_location = f"{location}.{kind}[{index}]"
        if kind == "samples":
            _check_quaternion(value, item_location, errors)
            continue

        if not isinstance(value, list) or len(value) != 5:
            errors.append(f"{item_location}: key must be [frame, w, x, y, z]")
            continue
        frame = value[0]
        if not _is_finite_number(frame) or not float(frame).is_integer():
            errors.append(f"{item_location}: frame must be a finite integer")
        else:
            frame = int(frame)
            if frame_count is not None and not 0 <= frame < frame_count:
                errors.append(
                    f"{item_location}: frame {frame} is outside 0..{frame_count - 1}"
                )
            if previous_frame is not None and frame <= previous_frame:
                errors.append(f"{item_location}: frame keys must be strictly increasing")
            previous_frame = frame
        _check_quaternion(value[1:], item_location, errors)


def _check_roles(data, valid_roles, errors):
    tracks = data.get("tracks")
    if isinstance(tracks, dict):
        for role in tracks:
            _check_role(role, "tracks", valid_roles, errors)

    mask = data.get("mask", [])
    if not isinstance(mask, list):
        errors.append("mask: must be an array")
    else:
        for index, role in enumerate(mask):
            _check_role(role, f"mask[{index}]", valid_roles, errors)

    contacts = data.get("contacts", [])
    if isinstance(contacts, list):
        for index, contact in enumerate(contacts):
            if isinstance(contact, dict) and "role" in contact:
                _check_role(contact["role"], f"contacts[{index}].role", valid_roles, errors)

    reference_pose = data.get("reference_pose", {})
    reference_roles = reference_pose.get("roles", {}) if isinstance(reference_pose, dict) else {}
    if isinstance(reference_roles, dict):
        for role, definition in reference_roles.items():
            _check_role(role, "reference_pose.roles", valid_roles, errors)
            if not isinstance(definition, dict):
                continue
            for field in ("parent", "end"):
                referenced = definition.get(field)
                if referenced is not None:
                    _check_role(
                        referenced,
                        f"reference_pose.roles.{role}.{field}",
                        valid_roles,
                        errors,
                    )
            twist_from = definition.get("twist_from", [])
            if isinstance(twist_from, list):
                for index, referenced in enumerate(twist_from):
                    _check_role(
                        referenced,
                        f"reference_pose.roles.{role}.twist_from[{index}]",
                        valid_roles,
                        errors,
                    )


def _validate_data(data, valid_roles):
    errors = []
    if not isinstance(data, dict):
        return ["top level must be a JSON object"]

    version = data.get("version")
    if (
        data.get("format") != "plush.clip"
        or version != 1
        or isinstance(version, bool)
    ):
        errors.append(
            "schema must equal plush.clip/1 "
            f"(format={data.get('format')!r}, version={data.get('version')!r})"
        )

    fps = data.get("fps")
    if not _is_finite_number(fps) or fps <= 0:
        errors.append(f"fps must be a finite number greater than 0 (got {fps!r})")

    frame_count_value = data.get("frame_count")
    if (
        not isinstance(frame_count_value, int)
        or isinstance(frame_count_value, bool)
        or frame_count_value < 1
    ):
        errors.append(f"frame_count must be a positive integer (got {frame_count_value!r})")
        frame_count = None
    else:
        frame_count = frame_count_value

    tracks = data.get("tracks")
    if not isinstance(tracks, dict):
        errors.append("tracks must be an object")
    else:
        for role, track in tracks.items():
            _check_track(role, track, frame_count, errors)

    _check_roles(data, valid_roles, errors)
    return errors


def _validate_file(path, valid_roles):
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"cannot read JSON: {exc}"]
    return _validate_data(data, valid_roles)


def _display_path(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _run_selftest(source, valid_roles):
    with tempfile.TemporaryDirectory(prefix="plush_clip_validation_") as temp_dir:
        corrupted = Path(temp_dir) / source.name
        shutil.copyfile(source, corrupted)
        with corrupted.open(encoding="utf-8") as stream:
            data = json.load(stream)

        role, track = next(iter(data["tracks"].items()))
        if "samples" in track:
            quaternion = track["samples"][0]
        else:
            quaternion = track["keys"][0][1:]
        quaternion[:] = [2.0, 0.0, 0.0, 0.0]
        if "samples" in track:
            track["samples"][0] = quaternion
        else:
            track["keys"][0][1:] = quaternion

        with corrupted.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=1)
            stream.write("\n")

        errors = _validate_file(corrupted, valid_roles)
        norm_error = next((error for error in errors if "quaternion norm" in error), None)
        if norm_error:
            print(f"[EXPECTED FAIL] temporary/{corrupted.name}: {norm_error}")
            return True
        detail = "; ".join(errors) if errors else "corrupted quaternion was accepted"
        print(f"[SELFTEST FAIL] temporary/{corrupted.name}: {detail}")
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="also verify that a corrupted temporary copy is rejected",
    )
    args = parser.parse_args(argv)

    clips = sorted(CLIPS_DIR.glob("*.clip.json"))
    if not clips:
        print("[FAIL] content/clips/*.clip.json: no clip files found")
        return 1

    try:
        valid_roles = _profile_roles()
        profile_error = None
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        valid_roles = set()
        profile_error = f"cannot load rig profile: {exc}"

    passed = True
    for clip in clips:
        errors = [profile_error] if profile_error else _validate_file(clip, valid_roles)
        if errors:
            passed = False
            print(f"[FAIL] {_display_path(clip)}: {'; '.join(errors)}")
        else:
            print(f"[PASS] {_display_path(clip)}")

    if args.selftest:
        passed = _run_selftest(clips[0], valid_roles) and passed
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
