"""T-113: expression-sheet jobs from the emotion files (the controls each per-character emotion drives at its
expressed intensity), plus the closed-lid rows. Writes <out>/<who>_job.json for expr_sheet.py.

    python3 docs/evaluation/characters/T-113/make_jobs.py <out> <samples> <px> --boy-cols tag=blend,... --girl-cols ...
"""
import argparse
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
LIB = json.load(open(os.path.join(ROOT, "pipeline", "charsys", "face_library", "expressions.json")))
SETS = {"boy": ["boy_interested", "boy_sleepy", "boy_unimpressed", "boy_reluctant", "boy_focused"],
        "girl": ["girl_delighted", "girl_wonder", "girl_eager", "girl_shy", "girl_content"]}
# expressed intensity: boy = event 0.7 x reaction.intensity_scale 0.6; girl = her event intensities (no scale)
INTENSITY = {"boy": {}, "girl": {"girl_delighted": 0.9, "girl_wonder": 0.7}}
DEFAULT_K = {"boy": 0.42, "girl": 0.8}
FRAME = {"boy": (0.40, -0.015), "girl": (0.38, -0.02)}  # frame height, target below the eye line (m)
LIDS = {"boy": ["Blink", "Smile", "Laugh"], "girl": ["Blink", "Laugh", "Squint"]}
CHANNELS = {"browUp": ["BrowUp.L", "BrowUp.R"], "browDown": ["BrowDown"], "eyeSquint": ["EyeSquint"], "eyeWide": ["EyeWide"],
            "mouthUp": ["MouthSmile"], "mouthDown": ["MouthFrown"], "browSad": ["BrowSad"], "jawOpen": ["JawOpen"]}


def control(name):
    return "face_" + LIB["engine_expressions"].get(name, name)


def rows(who):
    out = []
    for n in SETS[who]:
        e = json.load(open(os.path.join(ROOT, "content", "emotions", n + ".emotion.json")))
        k = INTENSITY[who].get(n, DEFAULT_K[who])
        c = {}
        for name, w in e["face"].items():
            c[control(name)] = c.get(control(name), 0.0) + w * k
        fm = e.get("faceMotion") or {}
        for ch, w in (fm.get("channels") or {}).items():
            for u in CHANNELS.get(ch, []):
                c["face_" + u] = c.get("face_" + u, 0.0) + w
        out.append({"tag": n, "controls": {a: round(b, 4) for a, b in c.items()}, "gaze_deg": fm.get("gazeBiasDeg", [0.0, 0.0]),
                    "intensity": k})
    for p in LIDS[who]:
        out.append({"tag": f"{who}_{p}", "controls": {"face_" + p: 1.0}, "gaze_deg": [0.0, 0.0], "intensity": 1.0})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("samples", type=int)
    ap.add_argument("px", type=int)
    ap.add_argument("--boy-cols", default="")
    ap.add_argument("--girl-cols", default="")
    ap.add_argument("--rows", default="", help="comma list: only these row tags")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for who, cols in (("boy", a.boy_cols), ("girl", a.girl_cols)):
        if not cols:
            continue
        rr = [r for r in rows(who) if not a.rows or r["tag"] in a.rows.split(",")]
        job = {"out": os.path.join(a.out, who), "samples": a.samples, "px": a.px, "frame": "face", "frame_h": FRAME[who][0], "dz": FRAME[who][1], "yaw": -30.0, "elev": 6.0,
               "columns": [{"tag": t, "blend": b} for t, b in (x.split("=", 1) for x in cols.split(","))], "rows": rr}
        json.dump(job, open(os.path.join(a.out, f"{who}_job.json"), "w"), indent=1)
        print(who, len(rr), "rows x", len(job["columns"]), "columns")


if __name__ == "__main__":
    main()
