"""T-046: face control curves of the evidence shot from its engine bake (any Python with matplotlib).

    python plot_bake.py <bake.json> <out image>

Per character: the baked facial control weights that move (one line each) and the eye offset from the head (yaw,
pitch) derived from the baked eye and head matrices."""
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

bake = json.load(open(sys.argv[1]))
fig, axes = plt.subplots(2, 2, figsize=(14, 7), sharex=True)
for row, ch in enumerate(bake["characters"]):
    name, morphs, bones = ch["name"], ch["morphs"], ch["bones"]
    frames = [fd["frame"] for fd in bake["frame_data"]]
    W = [fd["characters"][name]["morphs"] for fd in bake["frame_data"]]
    ax = axes[row][0]
    for i, m in enumerate(morphs):
        v = [w[i] for w in W]
        if "@" in m or max(v) - min(v) < 0.02:
            continue
        ax.plot(frames, v, label=m, lw=1.4 if m == "Blink" else 1.0)
    ax.set_title(f"{name}: facial controls (baked)")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=7, ncol=3, loc="upper left")
    ie, ih = bones.index("eye.L"), bones.index("head")
    yaw, pitch = [], []
    for fd in bake["frame_data"]:
        sk = fd["characters"][name]["skin"]
        col = lambda i, k: [sk[16 * i + 4 * k + r] for r in range(3)]
        ef, hx, hu, hf = col(ie, 2), col(ih, 0), col(ih, 1), col(ih, 2)
        dot = lambda a, b: sum(x * y for x, y in zip(a, b))
        yaw.append(math.degrees(math.atan2(dot(ef, hx), dot(ef, hf))))
        pitch.append(math.degrees(math.asin(max(-1.0, min(1.0, dot(ef, hu))))))
    ax = axes[row][1]
    ax.plot(frames, yaw, label="eye yaw vs head (deg)")
    ax.plot(frames, pitch, label="eye pitch vs head (deg)")
    ax.set_title(f"{name}: gaze (look targets + darts + emotion bias)")
    ax.legend(fontsize=8)
for ax in axes[1]:
    ax.set_xlabel("frame (30 fps): idle 1-19, happy 20-, surprised 66-, sad 102-")
plt.tight_layout()
plt.savefig(sys.argv[2], dpi=90)
