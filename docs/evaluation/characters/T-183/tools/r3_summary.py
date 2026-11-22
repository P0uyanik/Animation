"""T-183 round 3: one JSON of the summaries of the measure JSONs that r3_run.sh wrote (the per-frame rows stay out).

    python3 r3_summary.py <log dir> <out.json>          files: {props,body}_<tag>_<key>_<character>.json"""
import glob
import json
import os
import sys

out = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], "props_*.json")) + glob.glob(os.path.join(sys.argv[1], "body_*.json"))):
    d = json.load(open(f))
    if "summary" not in d:
        continue
    s = dict(d["summary"])
    s.pop("pairs" if "surfaces" in s else "", None)
    out[os.path.basename(f)[:-5]] = {"bake": os.path.relpath(d["bake"]) if os.path.isabs(d["bake"]) else d["bake"],
                                     "character": d["character"], "limit_mm": d["limit_mm"], "summary": s}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(len(out), "measures ->", sys.argv[2])
