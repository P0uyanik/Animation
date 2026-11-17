#!/usr/bin/env python3
"""Writes the T-061 evidence shots: the T-045 evidence shot with body mechanics on (idle -> touch -> wave clip at
speed 1.5 with a 4-frame blend in), with the CURRENT approved character versions (run_shot cast "current", from
docs/evaluation/characters/fidelity_baseline.json; owner decision 2026-11-17), rendered twice:

shot_before/shot.scene.json: "animPrinciples": false (the engine's behaviour before T-061, bit for bit).
shot_after/shot.scene.json:  the shared defaults (animPrinciples on).
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
T045 = HERE.parent / "T-045" / "shot_after" / "shot.scene.json"


def main():
    base = json.loads(T045.read_text())
    for variant, on in (("shot_before", False), ("shot_after", True)):
        s = copy.deepcopy(base)
        s["name"] = "T-061 animation principles: T-045 shot (body mechanics on), " + ("principles on" if on else "principles off")
        if not on:
            s["animPrinciples"] = False
        s["production"]["cast"] = {"boy": {"character_id": "boy_yellow_hoodie", "version": "current"},
                                   "girl": {"character_id": "girl_auburn_bun_glasses", "version": "current"}}
        out = HERE / variant / "shot.scene.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", out.relative_to(HERE.parents[3]))


if __name__ == "__main__":
    main()
