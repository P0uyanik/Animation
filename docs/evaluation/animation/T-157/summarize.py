"""T-157: summary of measure_t157 runs (measures/m_<variant>.json; measure_t157 output) -> markdown rows. Held: boy R f85-130, girl L f120-192.
Band out is against each variant's own band (boy) and the site band (girl); off-band fingers are excluded from it."""
import json, sys
BANDS = {"base": (45, 90), "t138": (45, 90), "a": (40, 95), "b": (45, 90), "c": (45, 95)}
OFF = {"b": {4}, "c": {4}}  # digit index in the rows (thumb, f0 index, f1, f2, f3 little)
for v in sys.argv[1:]:
    d = json.load(open(f"docs/evaluation/animation/T-157/measures/m_{v}.json"))["frames"]
    for hand, held, band, f0 in (("boy.R", (85, 130), BANDS[v], 100), ("girl.L", (120, 192), (10, 55), 150)):
        fr = [f for f in d if f["hand"] == hand and held[0] <= f["frame"] <= held[1]]
        off = OFF.get(v, set()) if hand == "boy.R" else set()
        on = lambda f: [i for i in range(len(f["tip_heights_mm"])) if i not in off]
        bo = max(max(max(band[0] - f["tip_heights_mm"][i], f["tip_heights_mm"][i] - band[1]) for i in on(f)) for f in fr)
        gap = max(max(abs(f["tip_gap_mm"][i]) for i in on(f)) for f in fr)
        fing = min(min(f["min_clearance_mm"][1:]) for f in fr)
        thumb = min(f["min_clearance_mm"][0] for f in fr)
        offc = min(min(f["min_clearance_mm"][i] for i in off) for f in fr) if off else None
        g = [f for f in fr if f["frame"] == f0][0]
        print(f"| {v} | {hand} | {band[0]}-{band[1]} | {bo:+.2f} | {gap:.2f} | {fing:+.2f} | {thumb:+.2f} | "
              f"{'-' if offc is None else f'{offc:+.2f}'} | {min(f['closest_tips_mm'] for f in fr):.1f} | "
              f"{', '.join(f'{x:.1f}' for x in g['tip_heights_mm'])} | {g['wrist'][0]:.5f} |")
