"""Beat lengths of the girl's watertable signature (playback frames @24), shared by make_girl_clips.py (clip authoring)
and make_shot.py (shot beats). Reference: docs/evaluation/animation/T-106/performance.csv, watertable girl."""
TEMPO = 1.1  # tempo.action_speed of content/personality/girl_auburn_bun_glasses.json: clip frames = playback x TEMPO
LEAD = 2  # clip frames of rest before the first move
# (beat, playback frames, source)
WONDER = [
    ("rise_to_chin", 14, "invented (WT starts at the chin): a brisk rise, long enough for animcheck's rotation-step and jerk limits"),
    ("hand_at_chin", 15, "WT [0, 15)"),
    ("leave_chin", 7, "WT [15, 22)"),
    ("lean_and_point", 17, "WT [22, 39)"),
    ("point_hold", 22, "WT [39, 61)"),
    ("draw_back", 20, "WT [61, 81)"),
    ("straighten", 15, "WT [81, 96)"),
]


def wonder_clip_frames():
    """Clip frame at the END of each beat (t1..t7), authored at playback x TEMPO."""
    out, t = [], float(LEAD)
    for _, n, _ in WONDER:
        t += n * TEMPO
        out.append(t)
    return out
