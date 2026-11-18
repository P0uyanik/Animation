"""T-097A evidence: plots curves.csv (written by tests/test_emotion_blend.cpp with PLUSH_T097A_EVIDENCE=<this dir>)
as curves.svg. No dependencies. Top: face morph weights, blended (solid) vs plain T-003 crossfade (dashed). Bottom:
head height (mm, minus its rest), same styles. Quarter-frame samples (the secondary-motion sampling rate).

    python3 docs/evaluation/animation/T-097A/plot_curves.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "curves.csv"))))
frames = [float(r["frame"]) for r in rows]
morphs = [k[len("blend_"):] for k in rows[0] if k.startswith("blend_") and not k.startswith("blend_head")]
colors = ["#c8781e", "#2f7fb5", "#6a4fa3"]
W, H, PAD, GAP = 900, 520, 50, 40
ph = (H - 2 * PAD - GAP) / 2
x0, x1 = frames[0], frames[-1]


def X(f):
    return PAD + (f - x0) / (x1 - x0) * (W - 2 * PAD)


def path(values, top, lo, hi):
    pts = [f"{X(f):.1f},{top + ph - (v - lo) / (hi - lo) * ph:.1f}" for f, v in zip(frames, values)]
    return "M" + " L".join(pts)


out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
       f'<rect width="{W}" height="{H}" fill="#fff"/>']
for top, title in ((PAD, "face morph weight (solid: blend, dashed: plain T-003 crossfade)"),
                   (PAD + ph + GAP, "head height, mm above rest (solid: blend, dashed: plain)")):
    out.append(f'<rect x="{PAD}" y="{top}" width="{W - 2 * PAD}" height="{ph}" fill="none" stroke="#999"/>')
    out.append(f'<text x="{PAD}" y="{top - 6}">{title}</text>')
for f in range(0, int(x1) + 1, 30):  # 1 s ticks
    for top in (PAD, PAD + ph + GAP):
        out.append(f'<line x1="{X(f):.1f}" x2="{X(f):.1f}" y1="{top}" y2="{top + ph}" stroke="#eee"/>')
    out.append(f'<text x="{X(f) - 8:.1f}" y="{H - PAD + 16}">{f}</text>')
# Action starts (frames 10, 18, 30, 110: happy, surprised, sad, afraid).
for f, n in ((10, "happy"), (18, "surprised"), (30, "sad"), (110, "afraid")):
    out.append(f'<line x1="{X(f):.1f}" x2="{X(f):.1f}" y1="{PAD}" y2="{H - PAD}" stroke="#d33" stroke-dasharray="2,3"/>')
    out.append(f'<text x="{X(f) + 2:.1f}" y="{PAD + 12 + 12 * (n == "surprised")}" fill="#d33">{n}</text>')
for i, m in enumerate(morphs):
    for v, dash in (("blend", ""), ("plain", ' stroke-dasharray="5,4"')):
        vals = [float(r[f"{v}_{m}"]) for r in rows]
        out.append(f'<path d="{path(vals, PAD, 0, 1)}" fill="none" stroke="{colors[i]}" stroke-width="1.6"{dash}/>')
    out.append(f'<text x="{W - PAD - 90}" y="{PAD + 16 + 14 * i}" fill="{colors[i]}">{m}</text>')
rest = float(rows[0]["blend_head_y_mm"])
ys = [float(r[f"{v}_head_y_mm"]) - rest for r in rows for v in ("blend", "plain")]
lo, hi = min(ys) - 1, max(ys) + 1
for v, dash in (("blend", ""), ("plain", ' stroke-dasharray="5,4"')):
    vals = [float(r[f"{v}_head_y_mm"]) - rest for r in rows]
    out.append(f'<path d="{path(vals, PAD + ph + GAP, lo, hi)}" fill="none" stroke="#333" stroke-width="1.4"{dash}/>')
out.append(f'<text x="{PAD + 4}" y="{PAD + ph + GAP + 14}">{hi:.0f} mm</text>')
out.append(f'<text x="{PAD + 4}" y="{PAD + 2 * ph + GAP - 4}">{lo:.0f} mm</text>')
out.append(f'<text x="{W / 2 - 30}" y="{H - 10}">scene frame (30 fps)</text></svg>')
open(os.path.join(HERE, "curves.svg"), "w").write("\n".join(out))
print("wrote", os.path.join(HERE, "curves.svg"))
