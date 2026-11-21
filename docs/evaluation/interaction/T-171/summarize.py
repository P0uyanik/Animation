"""T-171: one table row per variant from measure_t171 output (measures/m_<variant>.json, boy R, f58-f100).
python3 summarize.py <measures dir> base t157a r2 r2a r2s r2site"""
import json, sys

D, names = sys.argv[1], sys.argv[2:]
DIG = ["thumb", "index", "middle", "ring", "little"]
print("| variant | lands at frame (thumb, index..little) | largest curl step, deg/frame (thumb / fingers) | held fingertips apart, mm (i-m, m-r, r-l) | held tip gap, mm | min skin clearance in the close f69-100, mm | approach graze f58-68, mm | tip heights held, mm |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for n in names:
    F = {f["frame"]: f for f in json.load(open(f"{D}/m_{n}.json"))["frames"]}
    fr = sorted(F)
    land = []
    for i in range(5):
        hit = [f for f in fr if f >= 69 and F[f]["tip_gap_mm"][i] <= 0.5]
        land.append(str(hit[0]) if hit else "-")
    step = [max(abs(F[f]["curl_deg"][i][j] - F[f - 1]["curl_deg"][i][j]) for f in fr[1:] if f >= 69 for j in (0, 1)) for i in range(5)]
    h = F[100]
    close = min(min(F[f]["clear_mm"]) for f in fr if f >= 69)
    graze = min(min(F[f]["clear_mm"]) for f in fr if f <= 68)
    gap = max(abs(g) for g in h["tip_gap_mm"])
    print(f"| {n} | {', '.join(land)} | {step[0]:.0f} / {max(step[1:]):.0f} | {', '.join(f'{x:.1f}' for x in h['tips_apart_mm'])} | {gap:.2f} | {close:.2f} | {graze:.2f} | {', '.join(f'{x:.0f}' for x in h['tip_h_mm'])} |")
