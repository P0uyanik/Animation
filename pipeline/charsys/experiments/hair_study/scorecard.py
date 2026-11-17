"""T-049 hair study: collect the numbers of every approach into one scorecard (JSON + markdown table).

    python3 scorecard.py <study_dir> <evidence_dir> <measure_dir> <out_dir>

study_dir/<c>_<ap>/build.json (study_build.py), evidence_dir/<c>_<ap>/fidelity.json + renders/timings_*.json +
closeup/timings.json (render_evidence.sh), measure_dir/<c>_<ap>/measure.json (measure.py). The current hair is read
from the committed fidelity runs (BASELINE) for the same views (different samples: 32 vs 16)."""
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
BASELINE = {"boy": "docs/evaluation/characters/T-032/boy/fidelity.json",
            "girl": "docs/evaluation/integration/consolidation/fidelity/girl/fidelity.json"}
VIEWS = {"boy": ["val27_front", "val27_threequarter_right", "val27_back"],
         "girl": ["sheet30_front", "sheet30_front_left", "sheet30_back"]}


def hair_metrics(fid, views):
    out = {}
    ious, ratios = [], []
    for v in views:
        pv = fid["per_view"].get(v)
        if not pv:
            continue
        h = pv["regions"].get("hair")
        if h:
            ious.append(h["iou"])
            ratios.append(h["area_ratio"])
        if v == views[0]:
            pr = pv.get("proportions", {})
            for k in ("hair_area", "hair_width_at_eyes", "hair_length"):
                if k in pr:
                    out[k + "_rel"] = round(pr[k]["relative"], 3)
            if "skin_face" in pv["regions"]:
                out["skin_face_iou_front"] = round(pv["regions"]["skin_face"]["iou"], 3)
                out["skin_face_area_ratio_front"] = round(pv["regions"]["skin_face"]["area_ratio"], 3)
    out["hair_iou_mean"] = round(sum(ious) / len(ious), 4) if ious else None
    out["hair_area_ratio_mean"] = round(sum(ratios) / len(ratios), 3) if ratios else None
    out["fidelity_score_3views"] = round(fid["overall"]["score"], 2)
    return out


def main():
    st, ev, ms, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    card = {}
    for c in ("boy", "girl"):
        card[c] = {}
        base = os.path.join(ROOT, BASELINE[c])
        if os.path.exists(base):
            card[c]["current"] = hair_metrics(json.load(open(base)), VIEWS[c])
        for ap in "ABC":
            k = f"{c}_{ap}"
            row = {}
            b = json.load(open(os.path.join(st, k, "build.json")))
            row.update({x: b[x] for x in ("label", "hair_build_s", "hair_vertices", "hair_faces", "fibre_points",
                                          "chain_bones", "peak_rss_mb", "blend_mb")})
            row["spec_bytes"] = os.path.getsize(os.path.join(os.path.dirname(__file__), "specs", f"{k}.json"))
            row.update(hair_metrics(json.load(open(os.path.join(ev, k, "fidelity.json"))), VIEWS[c]))
            rt = []
            for t in glob.glob(os.path.join(ev, k, "renders", "timings_*.json")) + \
                    [os.path.join(ev, k, "closeup", "timings.json")]:
                rt += list(json.load(open(t))["views"].values())
            row["render_s_per_still_16spp_640px"] = round(sum(rt) / len(rt), 1) if rt else None
            mp = os.path.join(ms, k, "measure.json")
            if os.path.exists(mp):
                m = json.load(open(mp))
                row["face_visible_front"] = m["rest"]["front"]["face"]
                row["eyes_visible_front"] = m["rest"]["front"]["eyes"]
                row["face_visible_34"] = m["rest"]["three_quarter"]["face"]
                row["eyes_visible_34"] = m["rest"]["three_quarter"]["eyes"]
                ext = m["turn"]["visibility_at_extremes"]
                row["eyes_visible_34_min_during_turn"] = min(v["three_quarter"]["eyes"] for v in ext.values())
                row["pen_other_rest"] = m["rest"]["penetration"]["other_inside_frac"]
                row["pen_other_turn_max"] = m["turn"]["penetration_max"]["other_inside_frac"]
                row["pen_head_rest"] = m["rest"]["penetration"]["head_inside_frac"]
                row["pen_head_turn_max"] = m["turn"]["penetration_max"]["head_inside_frac"]
                row["chains"] = m["turn"]["chains"]
                row["max_lag_deg"] = round(m["turn"]["max_lag_deg"], 1)
                row["turn_render_s_per_frame_8spp_320px"] = m["turn"]["render_s_per_frame"]
            card[c][ap] = row
    json.dump(card, open(os.path.join(out, "scorecard.json"), "w"), indent=1)
    keys = ["hair_iou_mean", "hair_area_ratio_mean", "hair_area_rel", "hair_width_at_eyes_rel", "skin_face_iou_front",
            "fidelity_score_3views", "face_visible_front", "eyes_visible_front", "face_visible_34", "eyes_visible_34",
            "eyes_visible_34_min_during_turn", "chains", "max_lag_deg", "pen_other_rest", "pen_other_turn_max",
            "hair_build_s", "render_s_per_still_16spp_640px", "turn_render_s_per_frame_8spp_320px", "hair_vertices",
            "fibre_points", "peak_rss_mb", "blend_mb", "spec_bytes"]
    L = []
    for c in ("boy", "girl"):
        cols = [x for x in ("current", "A", "B", "C") if x in card[c]]
        L += [f"### {c}", "", "| measure | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
        for k in keys:
            L.append(f"| {k} | " + " | ".join(str(card[c][x].get(k, "-")) for x in cols) + " |")
        L.append("")
    open(os.path.join(out, "scorecard_table.md"), "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
