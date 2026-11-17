"""T-064: recover the T-058 Boy 2.0-dev fidelity renders from the committed turnaround pairs.

`docs/evaluation/characters/T-058/turn_<view>.png` holds reference | render side by side (640x640, lossless PNG). The
render half is the 320x640 render at scale 1; only its top 23 px carry a label bar, which is painted back with the
background colour (it lies above the figure).

    python3 extract_t058_renders.py <out_dir>      -> <out_dir>/<view>.png
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWS = ("val27_front", "val27_threequarter_right", "val27_side_right", "val27_back", "val27_back_threequarter")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for v in VIEWS:
        im = np.asarray(Image.open(os.path.join(HERE, "..", "T-058", f"turn_{v}.png")).convert("RGB"))[:, 320:640].copy()
        bg = np.median(im[30:60, :20].reshape(-1, 3), axis=0).astype(np.uint8)
        im[:23] = bg
        Image.fromarray(im).save(os.path.join(out, v + ".png"))
    print("ok")


if __name__ == "__main__":
    main()
