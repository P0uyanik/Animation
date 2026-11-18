#!/usr/bin/env python3
"""Gate step of tools/animcheck (T-061): bakes every regression shot in tools/animcheck/shots/ with the engine
(plush-render --bake, seconds) and checks the animation-principle metrics against thresholds.json.

    python3 tools/animcheck/run_gate.py --render <plush-render> [--out build/check-all/animcheck]

Exit 0 = every gesture of every shot within the thresholds and, for shots whose characters have a personality
profile (T-053), every measured blink / reach / hold / idle value within the profile's limits (tools/animcheck/
personality.py); the report is <out>/animcheck.json (one entry per shot, with all metrics and the failures) and
<out>/personality.json (the personality reports). T-104: the timing rule (tools/animcheck/timing.py) runs on every shot
and only warns (short beats against content/timing/reference_timing.json, shots without a hold): its warnings are
printed as WARN lines and written to <out>/timing.json, never counted as failures. T-097C: the acting rule
(tools/animcheck/acting.py: gesture amplitude, notice delay, still hold against each personality profile) runs on
shots with profiles and only warns as well: WARN lines, one summary line per shot, <out>/acting.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import animcheck  # noqa: E402
import personality  # noqa: E402
import timing  # noqa: E402
import acting  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", required=True, help="plush-render executable")
    ap.add_argument("--out", default=str(HERE.parents[1] / "build/check-all/animcheck"))
    ap.add_argument("--thresholds", default=str(HERE / "thresholds.json"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    thresholds = json.loads(Path(args.thresholds).read_text())
    shots = sorted((HERE / "shots").glob("*.scene.json"))
    if not shots:
        print("FAIL no regression shots in", HERE / "shots")
        return 1
    report = {"format": "plush.animcheck_gate", "version": 1, "thresholds": thresholds, "shots": []}
    persona = {"format": "plush.animcheck_personality_gate", "version": 1, "shots": []}
    timings = {"format": "plush.animcheck_timing_gate", "version": 1, "shots": []}
    actings = {"format": "plush.animcheck_acting_gate", "version": 1, "shots": []}
    failures = []
    for shot in shots:
        scene = json.loads(shot.read_text())
        bake = out / (shot.name.replace(".scene.json", "") + ".bake.json")
        cmd = [args.render, str(shot), "--bake", str(bake), "--frames", f"{scene['frameStart']}-{scene['frameEnd']}"]
        run = subprocess.run(cmd, capture_output=True, text=True)
        if run.returncode != 0 or not bake.is_file():
            failures.append(f"{shot.name}: bake failed ({run.returncode}): {run.stderr.strip()[-300:]}")
            continue
        res = animcheck.analyse(json.loads(bake.read_text()), scene, shot)
        fails = animcheck.check(res, thresholds)
        res["failures"] = fails
        report["shots"].append({"shot": shot.name, "result": res})
        failures += [f"{shot.name}: {f}" for f in fails]
        n = len(res["gestures"])
        print(f"{'PASS' if not fails else 'FAIL'} {shot.name}: {n} gestures, {len(fails)} failures")
        tim = timing.analyse(scene, json.loads(bake.read_text()), thresholds)  # T-104: warnings only
        timings["shots"].append({"shot": shot.name, "result": tim})
        for w in tim["warnings"]:
            print(f"WARN {shot.name}: timing: {w}")
        if any(isinstance(c.get("personality"), str) for c in scene.get("characters", [])):
            prep = personality.analyse(json.loads(bake.read_text()), scene, shot, thresholds)
            persona["shots"].append({"shot": shot.name, "result": prep})
            failures += [f"{shot.name}: personality: {f}" for f in prep["failures"]]
            print(f"{'PASS' if not prep['failures'] else 'FAIL'} {shot.name}: personality limits, "
                  f"{len(prep['characters'])} characters, {len(prep['failures'])} failures")
            act = acting.analyse(scene, shot, json.loads(bake.read_text()), thresholds)  # T-097C: warnings only
            actings["shots"].append({"shot": shot.name, "result": act})
            for w in act["warnings"]:
                print(f"WARN {shot.name}: acting: {w}")
            print(f"INFO {shot.name}: {acting.summary(act)}")
    report["failures"] = failures
    (out / "acting.json").write_text(json.dumps(actings, indent=1) + "\n")
    (out / "timing.json").write_text(json.dumps(timings, indent=1) + "\n")
    (out / "animcheck.json").write_text(json.dumps(report, indent=1) + "\n")
    (out / "personality.json").write_text(json.dumps(persona, indent=1) + "\n")
    for f in failures:
        print("FAIL", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
