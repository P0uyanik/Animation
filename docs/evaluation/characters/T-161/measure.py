"""Score a manual image trace against the T-161 projected reference bands."""
import argparse
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ["character", "measure", "reference_source", "reference_trace", "reference_mark",
          "reference", "tolerance", "current_source", "current_trace", "current_mark",
          "current", "result"]


def decode(trace, kind):
    if not trace or trace == "?":
        return None
    if kind == "category":
        return trace
    if "/" in trace:
        top, bottom = map(float, trace.split("/"))
        if bottom <= 0:
            raise ValueError("the denominator must be positive")
        value = top / bottom
    else:
        value = float(trace)
    if not math.isfinite(value):
        raise ValueError("expected a finite trace")
    return round(value, 4)


def score(rows, spec):
    seen = set()
    for row in rows:
        key = row["measure"]
        character = row["character"]
        if (character, key) in seen:
            raise ValueError(f"duplicate {character}/{key}")
        seen.add((character, key))
        target = spec["characters"][character][key]
        kind = spec["definitions"][key]["kind"]
        ref = target["value"]
        tol = target["tolerance"]
        cur = decode(row["current_trace"], kind)
        if cur is not None and (row["current_mark"] not in ("M", "E") or not row["current_source"]):
            raise ValueError(f"{character}/{key} needs an image source and M/E mark")
        row.update(reference_source=target["source"], reference_trace=target["trace"],
                   reference_mark=target["mark"], reference=ref, tolerance=tol, current=cur)
        if cur is None:
            row["result"] = "unobserved"
        elif kind == "category":
            row["result"] = "within" if cur == ref else "outside"
        else:
            row["result"] = "within" if abs(cur - ref) <= tol + 1e-8 else "outside"
        yield row


def pick(image_path):
    """Display a still, collect two segments and print the lengths in source px."""
    import cv2
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise ValueError(f"cannot read {image_path}")
    h, w = frame.shape[:2]
    scale = min(1000 / w, 760 / h, 4)
    base = cv2.resize(frame, (round(w * scale), round(h * scale)))
    points = []
    title = "Click numerator endpoints, then denominator endpoints. Esc cancels."

    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))

    cv2.namedWindow(title)
    cv2.setMouseCallback(title, click)
    try:
        while len(points) < 4:
            view = base.copy()
            for i, point in enumerate(points):
                cv2.circle(view, point, 2, (0, 220, 255), -1)
                if i % 2:
                    cv2.line(view, points[i-1], point, (0, 220, 255), 1)
            cv2.imshow(title, view)
            if cv2.waitKey(25) == 27 or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                return
        lengths = [math.dist(points[i], points[i+1]) / scale for i in (0, 2)]
        print("/".join(f"{v:.2f}" for v in lengths))
    finally:
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "measures.csv")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--character", choices=["boy", "auburn", "white_haired"])
    parser.add_argument("--template", action="store_true", help="clear current observations")
    parser.add_argument("--pick", type=Path, help="optional OpenCV four-click ratio picker")
    args = parser.parse_args()
    if args.pick:
        pick(args.pick)
        return
    if not args.output:
        parser.error("--output is required")
    spec = json.loads((HERE / "targets.json").read_text(encoding="utf-8"))
    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        rows = [r for r in csv.DictReader(stream)
                if not args.character or r["character"] == args.character]
    if args.template:
        for row in rows:
            row.update(current_source="", current_trace="?", current_mark="E")
    rows = list(score(rows, spec))
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} observations, {sum(r['result']=='outside' for r in rows)} outside band")


if __name__ == "__main__":
    main()
