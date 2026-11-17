"""T-050 cost model (no rendering, no network). Reads timings/*.json, writes cost_model.json and prints tables.

    python3 docs/evaluation/render/T-050/cost_model.py

Every input that is not measured in this container is a named ASSUMPTION or a cited public price (README.md)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
T = {n[:-5]: json.load(open(os.path.join(HERE, "timings", n))) for n in os.listdir(os.path.join(HERE, "timings"))}
steady = {k: v["renders_s"][-1] for k, v in T.items()}

EPISODE_S = 150            # 2.5 min
RENDERS_PER_SHOT = 3       # task assumption
SET_FACTOR = (1.5, 2.0, 3.0)  # ASSUMPTION: real set/props/DOF/motion blur vs the two-character grey-backdrop probe
CPU_SCORE = (50, 75, 100)  # ASSUMPTION: Blender Open Data score of this 4-vCPU Xeon @2.1 GHz (not measurable here)
GPU_OVERHEAD_S = 1.0       # ASSUMPTION: per-frame sync / OIDN-on-GPU / PNG write on a GPU node
CLOUD_OVERHEAD = 1.3       # ASSUMPTION: +30% for boot, upload, idle and failed/interrupted frames
# Blender Open Data OptiX medians (Blender 5.x, collected 2026-09-12; RTX 5070/4070 from 4.3 / unversioned pages)
GPU_SCORE = {"RTX 5060 Ti 16GB": 4146, "RTX 4070": 5118, "RTX 5070": 6087, "RTX 4090": 11534, "RTX 5090": 16171}
# $/hour, public pages read 2026-11-17 (README: sources)
RENT = {"RTX 4090 community/interruptible (RunPod/Vast low)": ("RTX 4090", 0.34),
        "RTX 4090 on-demand secure (RunPod)": ("RTX 4090", 0.89),
        "RTX 5090 render farm card-hour (Super Renders)": ("RTX 5090", 5.17),
        "RTX 4090 render-farm machine (iRender 1x)": ("RTX 4090", 8.20)}
CPU_FARM_PER_GHZH = (0.004, 0.0141)  # Super Renders standard .. RebusFarm
CONTAINER_GHZ = 4 * 2.1

PRESETS = {  # name: (timing key, cpu s/frame measured on the probe)
    "preview 640x360 16spp+OIDN (today)": "c_0360_s16",
    "review 1080p 16spp+OIDN": "c_1080_s16",
    "review 1080p 64spp+OIDN": "q4_c64_oidn",
    "final 1080p 128spp adaptive0.01+OIDN": "q5_c128_oidn",
}


def frames_per_min(fps):
    return 60 * fps * RENDERS_PER_SHOT


def main():
    out = {"measured_steady_s_per_frame": steady, "assumptions": {
        "episode_s": EPISODE_S, "renders_per_shot": RENDERS_PER_SHOT, "set_factor": SET_FACTOR, "cpu_score": CPU_SCORE,
        "gpu_overhead_s": GPU_OVERHEAD_S, "cloud_overhead": CLOUD_OVERHEAD}, "cpu": {}, "gpu": {}, "options": {}}
    for name, key in PRESETS.items():
        s = steady[key]
        row = {}
        for fps in (24, 30):
            f = EPISODE_S * fps * RENDERS_PER_SHOT
            row[f"{fps}fps_episode_h"] = [round(f * s * k / 3600, 1) for k in SET_FACTOR]
        out["cpu"][name] = {"probe_s_per_frame": s, **row}
    final = steady["q5_c128_oidn"]
    for gpu, sc in GPU_SCORE.items():
        spf = [round(final * SET_FACTOR[1] * c / sc + GPU_OVERHEAD_S, 2) for c in CPU_SCORE]
        out["gpu"][gpu] = {"final_s_per_frame": spf,
                           "episode_h_24fps": [round(EPISODE_S * 24 * RENDERS_PER_SHOT * x / 3600, 2) for x in spf],
                           "episode_h_30fps": [round(EPISODE_S * 30 * RENDERS_PER_SHOT * x / 3600, 2) for x in spf]}
    for name, (gpu, rate) in RENT.items():
        spf = out["gpu"][gpu]["final_s_per_frame"]
        per_min = {fps: [round(frames_per_min(fps) * x / 3600 * rate * CLOUD_OVERHEAD, 2) for x in spf] for fps in (24, 30)}
        out["options"][name] = {"usd_per_hour": rate, "usd_per_finished_min_24fps": per_min[24],
                                "usd_per_finished_min_30fps": per_min[30],
                                "episode_turnaround_h_24fps": out["gpu"][gpu]["episode_h_24fps"]}
    ghzh = [frames_per_min(fps) * final * SET_FACTOR[1] * CONTAINER_GHZ / 3600 for fps in (24, 30)]
    out["options"]["CPU render farm (GHz-hour)"] = {
        "ghz_h_per_finished_min_24_30fps": [round(g) for g in ghzh],
        "usd_per_finished_min_24fps": [round(ghzh[0] * p, 2) for p in CPU_FARM_PER_GHZH],
        "usd_per_finished_min_30fps": [round(ghzh[1] * p, 2) for p in CPU_FARM_PER_GHZH]}
    json.dump(out, open(os.path.join(HERE, "cost_model.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


main()
