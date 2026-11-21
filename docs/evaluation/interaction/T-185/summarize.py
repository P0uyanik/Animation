"""T-185: T-171's round 3 table (summarize_r3.py) with the shot's own frames instead of e910's fixed ones.
Contact C = the frame the index lands in the first variant (mesh gap <= 0.5 mm, from frame --from); way in = C-26..C-1,
held = C+8, carry = --carry A B (e910: 100-135). Same columns and definitions as summarize_r3.py.
    python3 summarize.py <measures dir> --prefix r3_ --from 69 --carry 100 135 <variant ...>"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("dir"); ap.add_argument("names", nargs="+")
ap.add_argument("--prefix", default="r3_"); ap.add_argument("--from", dest="frm", type=int, default=69)
ap.add_argument("--carry", type=int, nargs=2, default=(100, 135)); ap.add_argument("--contact", type=int)
a = ap.parse_args()
load = lambda n: {f["frame"]: f for f in json.load(open(f"{a.dir}/{a.prefix}{n}.json"))["frames"] if "mesh_in_mm" in f}
F0 = load(a.names[0])
C = a.contact or min(f for f in sorted(F0) if f >= a.frm and F0[f]["mesh_gap_mm"][1] <= 0.5)
H, W0, W1, K0, K1 = C + 8, C - 26, C - 1, a.carry[0], a.carry[1]
print(f"contact f{C} (index lands, {a.names[0]}); way in f{W0}-{W1}; held f{H}; carry f{K0}-{K1}\n")
print(f"| variant | thumb side at hold | deepest in the cup on the way in f{W0}-{W1}, mm (palm / thumb / fingers) | deepest in the cup held f{H}, mm (palm / thumb / fingers) | thumb turned from rest, deg | least joint bend, deg (negative = backwards) | index joints held, deg | fingers off the cup held, mm (largest) | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold f{H}, deg | wrist bend in the carry f{K0}-{K1}, deg (largest) |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for n in a.names:
    F = load(n); fr = sorted(F); h = F[H]
    way = [max(F[f]["mesh_in_mm"][i] for f in fr if W0 <= f <= W1) for i in range(3)]
    flex = [x for d in h["flex_deg"] for x in d]
    land = []
    for i in range(5):
        hit = [f for f in fr if f >= a.frm and F[f]["mesh_gap_mm"][i] <= 0.5]
        land.append(str(hit[0]) if hit else "-")
    step = max(abs(x - y) for f in fr[1:] if a.frm <= f <= C + 24 and f - 1 in F
               for da, db in zip(F[f]["flex_deg"], F[f - 1]["flex_deg"]) for x, y in zip(da, db))
    bend = lambda f: min(F[f]["wrist_deg"][0], 360 - F[f]["wrist_deg"][0])
    carry = max(bend(f) for f in fr if K0 <= f <= K1)
    print(f"| {n} | {'up' if h['thumb_up'] > 0.7 else 'down' if h['thumb_up'] < -0.7 else 'side'} | {way[0]:.1f} / {way[1]:.1f} / {way[2]:.1f} | "
          f"{h['mesh_in_mm'][0]:.1f} / {h['mesh_in_mm'][1]:.1f} / {h['mesh_in_mm'][2]:.1f} | {h['turn_deg'][0]:.0f} | {min(flex):.0f} | "
          f"{', '.join(f'{x:.0f}' for x in h['flex_deg'][1])} | {max(h['mesh_gap_mm'][1:]):.1f} | {', '.join(land)} | {step:.0f} | "
          f"{bend(H):.0f} / {h['wrist_deg'][1]:.0f} | {carry:.0f} |")
