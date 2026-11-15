"""T-003 emotion measurements AC2-AC6 from engine bakes (python3; runs plush-render --bake).

    python3 pipeline/clips/test_emotions.py --boy <pkg dir> --girl <pkg dir> --out <dir> [--engine <plush-render>]

The packages are the engine packages run_shot.py builds (e.g. episodes/e901_clip_test/shots/s010/build/packages/*).
Every scene has both characters side by side (yaw 0) on the base clip idle_relaxed, life layer off (only clip and
emotion motion is compared), and plays the shared emotion files content/emotions/*.emotion.json.
  AC2  per emotion at its peak (middle of the hold, outside the gesture): face weights of the resolved morphs equal
       the definition (1e-4), the other morphs equal the underlying value; body = the posture clip played as a plain
       clip action with the same timing (<= 0.001 deg) and boy vs girl world directions of the masked roles <= 2.0 deg.
  AC3  intensity 0.5: face weights 0.5x (1e-4); body deviation from the underlying pose (semantic-local rotation per
       masked role, roles deviating >= 1 deg at intensity 1) 0.5x within +-5 %.
  AC4  all emotions in sequence (each starts during the previous one's release): per-frame rotation change at every
       entry / transition / exit window <= 1.25 x the larger interior maximum of the neighbouring emotions (each
       played alone) or of the base idle, and <= 12 deg per frame; pose at entry and exit = the underlying pose.
  AC5  emotion + walk + look + wave (girl) / emotion + walk + look + reach (boy), against the same scenes without
       the emotion: walk keeps hips/legs; the wave's arm roles keep the wave; gaze and the reaching hand unchanged;
       a hand-keyed head wins.
  AC6  boy: exactly one warning per missing morph per emotion (also when an emotion is played twice), body as AC2,
       morphs untouched by the emotion unchanged."""
import argparse
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import measure_clips as MC  # noqa: E402
import retarget as RT  # noqa: E402

EMOTIONS = ["happy", "happy/laugh", "sad", "sad/cry", "angry", "surprised", "confused", "afraid", "sleepy", "curious"]
FPS = 30
START = 10
ROLES = MC.LIMB_ROLES + ["hand.L", "hand.R"]
PARENT = {}


def load_emotion(full):
    name, _, variant = full.partition("/")
    j = json.load(open(os.path.join(ROOT, "content", "emotions", name + ".emotion.json")))
    if variant:
        patch = j["variants"][variant]
        j = {k: v for k, v in j.items() if k != "variants"}

        def merge(a, b):
            if not isinstance(b, dict):
                return b
            a = dict(a) if isinstance(a, dict) else {}
            for k, v in b.items():
                if v is None:
                    a.pop(k, None)
                else:
                    a[k] = merge(a.get(k), v)
            return a
        j = merge(j, patch)
    return j


def timing(e, intensity_end=None):
    t = e.get("timing", {})
    on, ho, re_ = t.get("onset", 0.4) * FPS, t.get("hold", 1.5) * FPS, t.get("release", 0.6) * FPS
    end = START + on + ho + re_
    return on, ho, re_, end


def gesture_window(e):
    g = e.get("gesture")
    if not g:
        return None
    cl = json.load(open(os.path.join(ROOT, "content", "clips", g["clip"] + ".clip.json")))
    g0 = START + g.get("offset", 0) * FPS
    return g0, g0 + (cl["frame_count"] - 1) / cl["fps"] * FPS


def peak_frame(e):
    on, ho, re_, end = timing(e)
    a, b = START + on, end - re_
    gw = gesture_window(e)
    if gw:  # the largest part of the hold outside the gesture
        parts = [(a, min(b, gw[0])), (max(a, gw[1] + 1), b)]
        a, b = max(parts, key=lambda p: p[1] - p[0])
    return int(round((a + b) / 2))


def chars(pk, sd, life=False):
    return [{"name": n, "asset": os.path.relpath(pk[n], sd), "position": [x, 0, 0], "yawDeg": 0, "life": life}
            for n, x in (("boy", -0.45), ("girl", 0.45))]


def base_actions():
    return [{"type": "clip", "character": n, "clip": "idle_relaxed", "base": True} for n in ("boy", "girl")]


def run(engine, sd, name, sc):
    p = os.path.join(sd, name + ".scene.json")
    json.dump(sc, open(p, "w"), indent=1)
    out = os.path.join(sd, name + ".bake.json")
    r = subprocess.run([engine, p, "--bake", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"bake failed for {p}:\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    warnings = re.findall(r"warning: (.*)", r.stdout + r.stderr)
    return json.load(open(out)), warnings


class Bake:
    def __init__(self, bake, pk):
        self.raw = bake
        self.B = MC.Baked(bake, pk)
        self.morphs = {}
        for i, ch in enumerate(bake["characters"]):
            self.morphs[ch["name"]] = {fd["frame"]: dict(zip(ch["morphs"], fd["characters"][ch["name"]]["morphs"]))
                                       for fd in bake["frame_data"]}
        self.names = {ch["name"]: ch["morphs"] for ch in bake["characters"]}
        self.bones = {ch["name"]: ch["bones"] for ch in bake["characters"]}

    def q(self, who, f, role):
        return self.B.data[who][f][role][0]

    def local(self, who, f, role):  # semantic-local rotation (relative to the semantic parent role)
        par = PARENT.get(role)
        q = self.q(who, f, role)
        return RT.qmul(RT.qconj(self.q(who, f, par)), q) if par else q

    def skin(self, who, f, bone):
        fd = next(x for x in self.raw["frame_data"] if x["frame"] == f)
        s = fd["characters"][who]["skin"]
        b = self.bones[who].index(bone)
        return [[s[16 * b + c * 4 + r] for c in range(3)] for r in range(3)], [s[16 * b + 12 + r] for r in range(3)]


def resolve(pkg, name):
    m = pkg.get("expressions", {})
    morphs = [n for n in pkg["morph_names"] if "@" not in n]
    if name in m and m[name] in morphs:
        return m[name]
    return name if name in morphs else None


def expected_face(e, pkg, k=1.0):
    out = {}
    for n, w in e.get("face", {}).items():
        mo = resolve(pkg, n)
        if mo:
            out[mo] = out.get(mo, 0.0) + w * k
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boy", required=True)
    ap.add_argument("--girl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    sd = os.path.join(out, "scenes")
    os.makedirs(sd, exist_ok=True)
    pk = {k: os.path.join(os.path.abspath(getattr(a, k)), "character.json") for k in ("boy", "girl")}
    pkg = {k: json.load(open(v)) for k, v in pk.items()}
    prof = json.load(open(os.path.join(ROOT, "pipeline", "charsys", "rig_profiles", "humanoid_rigify.json")))
    for r, v in prof["reference_pose"]["roles"].items():
        PARENT[r] = v["parent"]
        if r.endswith(".L"):
            p = v["parent"] or ""
            PARENT[r[:-2] + ".R"] = p[:-2] + ".R" if p.endswith(".L") else v["parent"]
    E = {n: load_emotion(n) for n in EMOTIONS}
    ok = {}
    res = {"limits": {"face_tol": 1e-4, "clip_match_deg": 1e-3, "boy_vs_girl_dir_deg": 2.0, "intensity_ratio": [0.475, 0.525],
                      "boundary_factor": 1.25, "max_deg_per_frame": 12.0}, "AC2": {}, "AC3": {}, "AC4": {}, "AC5": {}, "AC6": {}}
    longest = max(timing(e)[3] for e in E.values()) + 12
    base, _ = run(a.engine, sd, "base", MC.scene(chars(pk, sd), base_actions(), int(longest)))
    Bb = Bake(base, pk)
    interior = {}
    # ---------------------------------------------------------------- AC2 / AC3 / AC6 per emotion
    all_warn_ok = True
    for n, e in E.items():
        tag = n.replace("/", "_")
        on, ho, re_, end = timing(e)
        fe = int(end) + 12
        acts = base_actions() + [{"type": "emotion", "character": c, "name": n, "start": START} for c in ("boy", "girl")]
        b1, w1 = run(a.engine, sd, f"emo_{tag}", MC.scene(chars(pk, sd), acts, fe))
        acts5 = base_actions() + [{"type": "emotion", "character": c, "name": n, "start": START, "intensity": 0.5} for c in ("boy", "girl")]
        b5, _ = run(a.engine, sd, f"emo_{tag}_i05", MC.scene(chars(pk, sd), acts5, fe))
        clipacts = base_actions()
        for c in ("boy", "girl"):
            clipacts.append({"type": "clip", "character": c, "clip": e["body"]["clip"], "start": START, "end": end,
                             "blendIn": on, "blendOut": re_})
            if e.get("gesture"):
                g = e["gesture"]
                cl = json.load(open(os.path.join(ROOT, "content", "clips", g["clip"] + ".clip.json")))
                clipacts.append({"type": "clip", "character": c, "clip": g["clip"], "start": START + g.get("offset", 0) * FPS,
                                 "blendIn": g.get("blendIn", 0.2) * FPS, "blendOut": g.get("blendOut", 0.2) * FPS})
        bc, _ = run(a.engine, sd, f"clip_{tag}", MC.scene(chars(pk, sd), clipacts, fe))
        twice = base_actions() + [{"type": "emotion", "character": "boy", "name": n, "start": START},
                                  {"type": "emotion", "character": "boy", "name": n, "start": int(end) + 2}]
        _, w2 = run(a.engine, sd, f"emo_{tag}_twice", MC.scene(chars(pk, sd), twice, int(end + end - START) + 14))
        B1, B5, BC = Bake(b1, pk), Bake(b5, pk), Bake(bc, pk)
        f = peak_frame(e)
        clip = json.load(open(os.path.join(ROOT, "content", "clips", e["body"]["clip"] + ".clip.json")))
        masked = [r for r in ROLES if r in clip["mask"]]
        r2 = {"peak_frame": f, "masked_roles": masked}
        r3 = {"peak_frame": f}
        for who in ("boy", "girl"):
            exp = expected_face(e, pkg[who])
            fw1, fw5, fwb = B1.morphs[who][f], B5.morphs[who][f], Bb.morphs[who][f]
            d_face = max([abs(fw1[m] - exp.get(m, fwb[m])) for m in fw1] + [0.0])
            d_face5 = max([abs((fw5[m] - fwb[m]) - 0.5 * (fw1[m] - fwb[m])) for m in fw1] + [0.0])
            d_clip = max(RT.qangle_deg(B1.q(who, f, r), BC.q(who, f, r)) for r in masked)
            ratios = []
            for r in masked:
                d1 = RT.qangle_deg(B1.local(who, f, r), Bb.local(who, f, r))
                if d1 >= 1.0:
                    ratios.append((r, round(d1, 3), RT.qangle_deg(B5.local(who, f, r), Bb.local(who, f, r)) / d1))
            worst = max(ratios, key=lambda x: abs(x[2] - 0.5)) if ratios else None
            r2[who] = {"face_expected": exp, "face_max_err": d_face, "body_vs_clip_max_deg": d_clip,
                       "pass": d_face <= 1e-4 and d_clip <= 1e-3}
            r3[who] = {"face_max_err": d_face5, "body_ratio_worst": worst, "ratios": ratios,
                       "pass": d_face5 <= 1e-4 and all(0.475 <= x[2] <= 0.525 for x in ratios)}
        dirs = max(MC.ang(B1.B.data["boy"][f][r][1], B1.B.data["girl"][f][r][1]) for r in masked)
        r2["boy_vs_girl_max_dir_deg"] = dirs
        r2["pass"] = r2["boy"]["pass"] and r2["girl"]["pass"] and dirs <= 2.0
        r3["pass"] = r3["boy"]["pass"] and r3["girl"]["pass"]
        res["AC2"][n], res["AC3"][n] = r2, r3
        # AC6: warnings (boy missing morphs; the girl has none missing)
        names = list(e.get("face", {})) + list((e.get("gesture") or {}).get("face", {}))
        exp_w = sorted(m for m in names if resolve(pkg["boy"], m) is None)
        got = sorted(re.search(r"expression '([^']+)'", w).group(1) for w in w1 if "emotion" in w and "'boy'" in w)
        got2 = sorted(re.search(r"expression '([^']+)'", w).group(1) for w in w2 if "emotion" in w and "'boy'" in w)
        girl_w = [w for w in w1 if "'girl'" in w]
        other = [m for m in Bb.names["boy"] if m not in expected_face(e, pkg["boy"]) and m not in
                 ((lambda g: [resolve(pkg["boy"], x) for x in g])((e.get("gesture") or {}).get("face", {})))]
        unchanged = max([abs(B1.morphs["boy"][fr][m] - Bb.morphs["boy"][fr][m]) for fr in B1.morphs["boy"] if fr in Bb.morphs["boy"] for m in other] + [0.0])
        res["AC6"][n] = {"expected_missing": exp_w, "warnings": got, "warnings_when_played_twice": got2, "girl_warnings": girl_w,
                         "other_morphs_max_change": unchanged, "body_pass_AC2": r2["boy"]["body_vs_clip_max_deg"] <= 1e-3,
                         "pass": got == exp_w and got2 == exp_w and not girl_w and unchanged == 0.0 and r2["boy"]["body_vs_clip_max_deg"] <= 1e-3}
        all_warn_ok &= res["AC6"][n]["pass"]
        # interior maxima for AC4 (each emotion alone, its whole span)
        for who in ("boy", "girl"):
            per = B1.B.data[who]
            chg, _ = MC.per_frame_change(per, ROLES, [x for x in B1.B.frames if START <= x <= end])
            interior.setdefault(who, {})[n] = {r: max(v.values(), default=0.0) for r, v in chg.items()}
            fch = {m: max(abs(B1.morphs[who][x][m] - B1.morphs[who][x - 1][m]) for x in range(START + 1, int(end) + 1)) for m in B1.names[who]}
            interior[who][n]["__face"] = fch
    for who in ("boy", "girl"):
        chg, _ = MC.per_frame_change(Bb.B.data[who], ROLES, Bb.B.frames)
        interior[who]["base"] = {r: max(v.values(), default=0.0) for r, v in chg.items()}
    # ---------------------------------------------------------------- AC4 sequence
    acts, spans, t = base_actions(), [], START
    for n in EMOTIONS:
        on, ho, re_, end = timing(E[n])
        length = end - START
        for c in ("boy", "girl"):
            acts.append({"type": "emotion", "character": c, "name": n, "start": t})
        spans.append((n, t, t + length, re_))
        t = t + length - re_  # the next starts at the beginning of this one's release
    fe = int(spans[-1][2]) + 12
    bs, _ = run(a.engine, sd, "sequence", MC.scene(chars(pk, sd), acts, fe))
    bsb, _ = run(a.engine, sd, "sequence_base", MC.scene(chars(pk, sd), base_actions(), fe))
    BS, BSB = Bake(bs, pk), Bake(bsb, pk)
    res["AC4"] = {"windows": [], "entry_exit": [], "sequence": [{"emotion": n, "start": s, "end": e_} for n, s, e_, _ in spans]}
    windows = [("entry " + spans[0][0], spans[0][1] - 3, spans[0][1] + 6, [spans[0][0]])]
    for (n0, s0, e0, r0), (n1, s1, e1, r1) in zip(spans, spans[1:]):
        windows.append((f"{n0} -> {n1}", s1 - 3, e0 + 3, [n0, n1]))
    windows.append(("exit " + spans[-1][0], spans[-1][2] - 6, spans[-1][2] + 3, [spans[-1][0]]))
    for who in ("boy", "girl"):
        chg, _ = MC.per_frame_change(BS.B.data[who], ROLES, BS.B.frames)
        for wname, a0, a1, ns in windows:
            worst = None
            okw = True
            for r in ROLES:
                lim = 1.25 * max([interior[who][x][r] for x in ns] + [interior[who]["base"][r]])
                v = max([chg[r][fr] for fr in range(int(a0), int(a1) + 1) if fr in chg[r]] + [0.0])
                if v > lim + 1e-6 or v > 12.0:
                    okw = False
                if worst is None or v / max(lim, 1e-9) > worst[2]:
                    worst = (r, round(v, 4), v / max(lim, 1e-9))
            # face: per-frame change in the window <= 1.25 x the neighbours' largest per-frame change
            fworst, ffail = 0.0, []
            for m in BS.names[who]:
                lim = 1.25 * max([interior[who][x]["__face"][m] for x in ns] + [0.0])
                v = max(abs(BS.morphs[who][fr][m] - BS.morphs[who][fr - 1][m]) for fr in range(int(a0) + 1, int(a1) + 1))
                if v > lim + 1e-6:
                    okw = False
                    ffail.append((m, round(v, 5), round(lim, 5)))
                fworst = max(fworst, v)
            res["AC4"]["windows"].append({"character": who, "window": wname, "frames": [a0, a1], "worst_role": worst[0],
                                          "worst_deg_per_frame": worst[1], "worst_ratio_to_limit": round(worst[2], 3),
                                          "face_max_change_per_frame": round(fworst, 5), "face_fail": ffail, "pass": okw})
        for label, fr in (("entry", int(spans[0][1])), ("exit", int(math.ceil(spans[-1][2])))):
            d = max(RT.qangle_deg(BS.q(who, fr, r), BSB.q(who, fr, r)) for r in ROLES)
            df = max(abs(BS.morphs[who][fr][m] - BSB.morphs[who][fr][m]) for m in BS.names[who])
            res["AC4"]["entry_exit"].append({"character": who, "event": label, "frame": fr, "max_diff_vs_underlying_deg": d,
                                             "max_face_diff": df, "pass": d <= 1e-3 and df <= 1e-4})
    imax = max(v for who in interior for n in EMOTIONS for r, v in interior[who][n].items() if r != "__face")
    res["AC4"]["single_emotion_max_deg_per_frame"] = imax
    res["AC4"]["pass"] = (all(w["pass"] for w in res["AC4"]["windows"]) and all(x["pass"] for x in res["AC4"]["entry_exit"])
                          and imax <= 12.0)
    # ---------------------------------------------------------------- AC5 layering
    objs = [{"name": "pedestal", "kind": "box", "min": [0.05, 0.0, 0.25], "max": [0.13, 0.4, 0.33], "material": "m"},
            {"name": "cup", "kind": "box", "min": [0.08, 0.4, 0.28], "max": [0.105, 0.43, 0.305], "material": "m",
             "position": [0.0925, 0.415, 0.2925]}]

    def layering(with_emotion, with_wave=True):
        acts = base_actions() + [
            {"type": "walk", "character": "girl", "start": 30, "end": 100, "to": [0.75, 0.0], "face": 0},
            {"type": "walk", "character": "boy", "start": 30, "end": 100, "to": [-0.15, 0.0], "face": 0},
            {"type": "look", "character": "girl", "start": 20, "end": 200, "camera": True},
            {"type": "look", "character": "boy", "start": 20, "end": 110, "camera": True},
            {"type": "reach", "character": "boy", "hand": "R", "object": "cup", "start": 120, "contact": 140, "liftEnd": 150,
             "place": 165, "release": 170, "end": 190, "lift": 0.0}]
        if with_wave:
            acts.append({"type": "clip", "character": "girl", "clip": "wave", "start": 50, "blendIn": 8, "blendOut": 8})
        if with_emotion:
            acts += [{"type": "emotion", "character": "girl", "name": "sad", "start": 10, "end": 200},
                     {"type": "emotion", "character": "boy", "name": "angry", "start": 10, "end": 200}]
        sc = MC.scene(chars(pk, sd), acts, 210, objs)
        sc["animation"] = {"girl/head.rot": [[170, [0, 25, 0], "smooth"], [200, [0, 25, 0], "smooth"]]}
        return sc
    bl, _ = run(a.engine, sd, "layering", layering(True))
    bl0, _ = run(a.engine, sd, "layering_noemotion", layering(False))
    L, L0 = Bake(bl, pk), Bake(bl0, pk)
    walk_roles = ["hips", "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"]
    r5 = {}
    for who in ("girl", "boy"):
        d = max(RT.qangle_deg(L.q(who, f, r), L0.q(who, f, r)) for f in range(40, 91) for r in walk_roles)
        dp = max(math.dist(L.B.data[who][f]["hips"][3], L0.B.data[who][f]["hips"][3]) for f in range(40, 91))
        r5[f"{who}_walk_keeps_hips_legs_root"] = {"max_deg": d, "max_hips_m": dp, "pass": d <= 1e-3 and dp <= 1e-5}
        emo = max(RT.qangle_deg(L.local(who, 60, r), L0.local(who, 60, r)) for r in ("spine", "chest", "neck"))
        r5[f"{who}_emotion_visible_on_torso_during_walk_deg"] = emo
    wave = ["upperArm.R", "forearm.R", "hand.R"]
    d = max(RT.qangle_deg(L.local("girl", f, r), L0.local("girl", f, r)) for f in range(84, 122) for r in wave)
    r5["girl_wave_keeps_its_roles_during_walk_and_emotion"] = {"frames": [84, 121], "max_semantic_local_deg": d, "pass": d <= 1e-2}

    def eye_err(B, who, f):
        cam = [0, 0.8, 3.5]
        worst = 0.0
        for eye in ("eye.L", "eye.R"):
            m, t = B.skin(who, f, eye)
            head = next(b["head"] for b in pkg[who]["skeleton"] if b["name"] == eye)
            pos = [sum(m[r][c] * head[c] for c in range(3)) + t[r] for r in range(3)]
            fwd = [m[r][2] for r in range(3)]
            worst = max(worst, MC.ang(fwd, RT.sub(cam, pos)))
        return worst
    eg = max(abs(eye_err(L, w, f) - eye_err(L0, w, f)) for w, fs in (("girl", range(40, 200, 10)), ("boy", range(40, 110, 10))) for f in fs)
    r5["look_keeps_gaze"] = {"max_aim_error_change_deg": eg, "pass": eg <= 0.5}
    hd = max(math.dist(L.B.data["boy"][f]["hand.R"][3], L0.B.data["boy"][f]["hand.R"][3]) for f in range(140, 166))
    r5["boy_reach_keeps_hand"] = {"frames": [140, 165], "max_hand_pos_m": hd, "pass": hd <= 1e-3}

    def engine_local(B, who, f, bone):
        par = next(b.get("parent") for b in pkg[who]["skeleton"] if b["name"] == bone)
        q = RT.quat_from_matrix(B.skin(who, f, bone)[0])
        return RT.qmul(RT.qconj(RT.quat_from_matrix(B.skin(who, f, par)[0])), q) if par else q
    hk = max(RT.qangle_deg(engine_local(L, "girl", f, "head"), engine_local(L0, "girl", f, "head")) for f in (175, 185, 195))
    r5["hand_keyed_head_wins"] = {"max_engine_local_deg": hk, "pass": hk <= 1e-2}
    r5["pass"] = all(v["pass"] for v in r5.values() if isinstance(v, dict))
    res["AC5"] = r5
    for k in ("AC2", "AC3", "AC6"):
        ok[k] = all(v["pass"] for v in res[k].values())
    ok["AC4"], ok["AC5"] = res["AC4"]["pass"], res["AC5"]["pass"]
    res["summary"] = ok
    json.dump(res, open(os.path.join(out, "emotion_measurements.json"), "w"), indent=1)
    for n in EMOTIONS:
        r2, r3, r6 = res["AC2"][n], res["AC3"][n], res["AC6"][n]
        print(f"{n:12s} AC2 face {max(r2['boy']['face_max_err'], r2['girl']['face_max_err']):.1e} clip "
              f"{max(r2['boy']['body_vs_clip_max_deg'], r2['girl']['body_vs_clip_max_deg']):.1e} deg boy-girl {r2['boy_vs_girl_max_dir_deg']:.3f} deg "
              f"{'PASS' if r2['pass'] else 'FAIL'} | AC3 worst {r3['girl']['body_ratio_worst']} {r3['boy']['body_ratio_worst']} "
              f"{'PASS' if r3['pass'] else 'FAIL'} | AC6 {r6['warnings']} {'PASS' if r6['pass'] else 'FAIL'}")
    for w in res["AC4"]["windows"]:
        if not w["pass"] or w["worst_ratio_to_limit"] > 0.8:
            print("AC4", w)
    print("AC4 worst ratio", max(w["worst_ratio_to_limit"] for w in res["AC4"]["windows"]),
          "max deg/frame", max(w["worst_deg_per_frame"] for w in res["AC4"]["windows"]),
          "entry/exit", max(x["max_diff_vs_underlying_deg"] for x in res["AC4"]["entry_exit"]),
          "single-emotion max deg/frame", res["AC4"]["single_emotion_max_deg_per_frame"])
    print("AC5", json.dumps(res["AC5"]))
    print("SUMMARY", ok)
    sys.exit(0 if all(ok.values()) else 1)


if __name__ == "__main__":
    main()
