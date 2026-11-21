"""T-171 round 3: one table row per variant from measure_t171 output (measures/r3_<variant>.json, boy R, f47-f150).
Every number is taken on the character's own mesh against the cup as a capped solid.
python3 summarize_r3.py <measures dir> base r2site r3site r3"""
import json, sys

D, names = sys.argv[1], sys.argv[2:]
print("| variant | thumb side at hold | deepest in the cup on the way in f50-75, mm (palm / thumb / fingers) | deepest in the cup held f84, mm (palm / thumb / fingers) | thumb turned from rest, deg | least joint bend, deg (negative = backwards) | index joints held, deg | fingers off the cup held, mm (largest) | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold f84, deg | wrist bend in the carry f100-135, deg (largest) |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for n in names:
    F = {f["frame"]: f for f in json.load(open(f"{D}/r3_{n}.json"))["frames"] if "mesh_in_mm" in f}
    fr = sorted(F)
    way = [max(F[f]["mesh_in_mm"][i] for f in fr if 50 <= f <= 75) for i in range(3)]
    h = F[84]
    flex = [x for d in h["flex_deg"] for x in d]
    land = []
    for i in range(5):
        hit = [f for f in fr if f >= 69 and F[f]["mesh_gap_mm"][i] <= 0.5]
        land.append(str(hit[0]) if hit else "-")
    step = max(abs(a - b) for f in fr[1:] if 69 <= f <= 100 for da, db in zip(F[f]["flex_deg"], F[f - 1]["flex_deg"]) for a, b in zip(da, db))
    bend = lambda f: min(F[f]["wrist_deg"][0], 360 - F[f]["wrist_deg"][0])
    carry = max(bend(f) for f in fr if 100 <= f <= 135)
    print(f"| {n} | {'up' if h['thumb_up'] > 0.7 else 'down' if h['thumb_up'] < -0.7 else 'side'} | {way[0]:.1f} / {way[1]:.1f} / {way[2]:.1f} | "
          f"{h['mesh_in_mm'][0]:.1f} / {h['mesh_in_mm'][1]:.1f} / {h['mesh_in_mm'][2]:.1f} | {h['turn_deg'][0]:.0f} | {min(flex):.0f} | "
          f"{', '.join(f'{x:.0f}' for x in h['flex_deg'][1])} | {max(h['mesh_gap_mm'][1:]):.1f} | {', '.join(land)} | {step:.0f} | "
          f"{bend(84):.0f} / {h['wrist_deg'][1]:.0f} | {carry:.0f} |")
