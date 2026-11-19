"""Draw T-094 movie frames alongside enlarged T-123 mask overlays."""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=Path)
    parser.add_argument("masks", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    with (args.report / "readability.csv").open(newline="", encoding="utf-8") as stream:
        rows = {int(row["frame"]): row for row in csv.DictReader(stream)}

    movie = cv2.VideoCapture(str(args.movie))
    sheet = Image.new("RGB", (1232, 816), "#182127")
    draw = ImageDraw.Draw(sheet)
    heading = ImageFont.load_default(size=24)
    body = ImageFont.load_default(size=17)
    text = "#e6ecef"
    cyan, orange = (65, 235, 244), (255, 163, 65)
    draw.text((16, 9), "e907   /   Cup and pupil visibility", font=heading, fill=text)
    for x, caption in [(16, "T-094 shot camera"), (465, "Pupil IDs in cyan   /   anatomical L, R"),
                       (1030, "Cup ID in orange")]:
        draw.text((x, 47), caption, font=body, fill=text)
    for i, (f, beat) in enumerate(((18, "Pickup"), (48, "Shared hold"), (58, "After release"))):
        movie.set(cv2.CAP_PROP_POS_FRAMES, f - 1)
        ok, frame = movie.read()
        if not ok:
            raise ValueError(f"missing movie frame {f}")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        filename = f"frame_{f:04d}.png"
        with Image.open(args.masks / "visible" / filename) as source:
            ids = np.array(source)
        with Image.open(args.masks / "cup_only" / filename) as source:
            full = np.array(source) == 255
        overlay = (rgb * 0.67).astype("uint8")
        overlay[full] = (142, 115, 161)
        overlay[ids == 255] = orange
        overlay[(ids != 0) & (ids != 255)] = cyan
        y = 77 + i * 245
        sheet.paste(Image.fromarray(rgb).resize((392, 221), Image.Resampling.LANCZOS), (16, y))
        masked = Image.fromarray(overlay)
        for box, size, xy in [((144, 116, 512, 233), (552, 176), (465, y + 21)),
                              ((250, 186, 364, 300), (184, 184), (1030, y + 16))]:
            sheet.paste(masked.crop(box).resize(size, Image.Resampling.NEAREST), xy)
        row = rows[f]
        draw.text((16, y + 222), f"f{f}   {beat}", fill=text, font=body)
        eyes = "     ".join(f"{who}  {row[who+'.L_pupil_px']}, {row[who+'.R_pupil_px']} px"
                            for who in ("girl", "boy"))
        draw.text((465, y + 202), eyes, fill=cyan, font=body)
        draw.text((1030, y + 202), f"{row['cup_patch_px']} px   {float(row['cup_patch_pct']):.1f}%",
                  fill=orange, font=body)
    movie.release()
    sheet.save(args.report / "evidence.jpg", quality=90, subsampling=0)


if __name__ == "__main__":
    main()
