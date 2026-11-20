"""Tests of the mocap importer (T-175, pipeline/clips/import_bvh.py). Pure Python 3, no Blender:

    python3 pipeline/clips/tests/test_import_bvh.py

1. Round trip: content/clips/dense_test.clip.json is played on a synthetic adult source skeleton, written as a BVH
   (cgspeed CMU joint names), imported back; every body role's sample matches (<= 0.01 deg).
2. Limb directions: a synthetic ASF/AMC take (CMU joint names, the extra lowerback / lowerneck+upperneck joints, a
   clavicle) is imported and played on a chibi role skeleton with the engine's playback formula; every limb, spine
   and the folded hips / neck roles point exactly where the source segments point (<= 0.01 deg).
3. Contacts / ground / loop: plants are found where an ankle stands still, the planted ankle lands at the rest ankle
   height (root height), and an auto loop gives a seamless cycle with a cycle_offset.
4. Library: every content/clips/mocap/*.clip.json passes the clip validator, carries the CMU licence and
   attribution, and content/clips/mocap/ATTRIBUTION.md names every clip."""
import json
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CLIPS, "..", ".."))
sys.path.insert(0, CLIPS)
sys.path.insert(0, HERE)
import import_bvh as IB  # noqa: E402
import retarget as RT  # noqa: E402
import test_clip_files as TCF  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL", msg)


def ref_roles():
    prof = json.load(open(IB.PROFILE))
    return prof, RT.reference_pose(prof["reference_pose"])


# ------------------------------------------------------------------ synthetic skeletons (engine axes, T-pose)
ADULT = {"hips": [0, 0.95, 0], "spine": [0, 1.07, 0], "chest": [0, 1.25, 0], "neck": [0, 1.45, 0], "head": [0, 1.55, 0],
         "upperArm.L": [0.18, 1.40, 0], "forearm.L": [0.46, 1.40, 0], "hand.L": [0.72, 1.40, 0],
         "thigh.L": [0.09, 0.92, 0], "shin.L": [0.09, 0.50, 0], "foot.L": [0.09, 0.08, 0]}
CHIBI = {"hips": [0, 0.30, 0], "spine": [0, 0.36, 0], "chest": [0, 0.44, 0], "neck": [0, 0.55, 0], "head": [0, 0.58, 0],
         "upperArm.L": [0.10, 0.52, 0.01], "forearm.L": [0.19, 0.51, 0.01], "hand.L": [0.27, 0.50, 0.01],
         "thigh.L": [0.06, 0.28, 0], "shin.L": [0.065, 0.15, 0.005], "foot.L": [0.065, 0.04, 0]}


def mirrored(d):
    out = dict(d)
    for k, v in d.items():
        if k.endswith(".L"):
            out[k[:-2] + ".R"] = [-v[0], v[1], v[2]]
    return out


def bindings(heads, ref):
    data = RT.derive(heads, ref)
    order = [x for x in ref if x["name"] in data["roles"]]
    A, parent = {}, {}
    for x in order:
        c = data["roles"][x["name"]]
        A[x["name"]] = RT.qmul(RT.frame(x["ref_dir"], x["ref_twist"]), RT.qconj(RT.frame(c["dir"], c["twist"])))
        p = x["parent"]
        while p and p not in data["roles"]:
            p = next((y["parent"] for y in ref if y["name"] == p), "")
        parent[x["name"]] = p
    return data, order, A, parent


def play(L, binding):
    """Engine playback (clip.h applyClipSample at full weight, semantic hierarchy): G per role."""
    data, order, A, parent = binding
    G = {}
    for x in order:
        r = x["name"]
        p = parent[r]
        Gp = G[p] if p else [1.0, 0, 0, 0]
        Ap = A[p] if p else [1.0, 0, 0, 0]
        G[r] = RT.qnorm(RT.qmul(RT.qmul(RT.qmul(Gp, RT.qconj(Ap)), L.get(r, [1.0, 0, 0, 0])), A[r]))
    return G


def angle(a, b):
    a, b = RT.normalize(a), RT.normalize(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, RT.dot(a, b)))))


# ------------------------------------------------------------------ 1. BVH round trip
BVH_JOINT = {"hips": "Hips", "spine": "Spine", "chest": "Spine1", "neck": "Neck", "head": "Head",
             "upperArm.L": "LeftArm", "forearm.L": "LeftForeArm", "hand.L": "LeftHand",
             "thigh.L": "LeftUpLeg", "shin.L": "LeftLeg", "foot.L": "LeftFoot"}


def euler_zxy(m):
    """m = Rz(a) Rx(b) Ry(c) (BVH 'Zrotation Xrotation Yrotation') -> degrees (a, b, c)."""
    b = math.asin(max(-1.0, min(1.0, m[2][1])))
    a = math.atan2(-m[0][1], m[1][1])
    c = math.atan2(-m[2][0], m[2][2])
    return [math.degrees(a), math.degrees(b), math.degrees(c)]


def write_bvh(path, heads, ref, samples, fps):
    """Plays clip samples (L per role) on `heads` (its own rest = T-pose, zero channels) and writes a BVH."""
    binding = bindings(heads, ref)
    data, order, A, parent = binding
    joints = {r: IB.mirror_name(BVH_JOINT[r[:-2] + ".L"]) if r.endswith(".R") else BVH_JOINT[r]
              for r in heads if (r[:-2] + ".L" if r.endswith(".R") else r) in BVH_JOINT}
    children = {}
    for x in order:
        if x["name"] in joints:
            children.setdefault(parent[x["name"]], []).append(x["name"])
    lines = ["HIERARCHY"]

    def emit(r, depth):
        ind = "  " * depth
        p = parent[r]
        off = heads[r] if not p else RT.sub(heads[r], heads[p])
        lines.append(f"{ind}{'ROOT' if not p else 'JOINT'} {joints[r]}")
        lines.append(ind + "{")
        lines.append(f"{ind}  OFFSET {off[0]:.6f} {off[1]:.6f} {off[2]:.6f}")
        ch = "Xposition Yposition Zposition Zrotation Xrotation Yrotation" if not p else "Zrotation Xrotation Yrotation"
        lines.append(f"{ind}  CHANNELS {6 if not p else 3} {ch}")
        kids = children.get(r, [])
        for k in kids:
            emit(k, depth + 1)
        if not kids:
            lines.append(f"{ind}  End Site")
            lines.append(ind + "  {")
            lines.append(f"{ind}    OFFSET 0.000000 0.050000 0.000000")
            lines.append(ind + "  }")
        lines.append(ind + "}")
    emit("hips", 0)
    seq = []

    def walk(r, out):
        out.append(r)
        for k in children.get(r, []):
            walk(k, out)
    walk("hips", seq)
    lines += ["MOTION", f"Frames: {len(samples)}", f"Frame Time: {1.0 / fps:.8f}"]
    for L in samples:
        G = play(L, binding)
        vals = []
        for r in seq:
            p = parent[r]
            Mg = IB.quat_to_matrix(G[r])
            Ml = Mg if not p else IB.mmul(IB.mT(IB.quat_to_matrix(G[p])), Mg)
            if not p:
                vals += heads[r]
            vals += euler_zxy(Ml)
        lines.append(" ".join(f"{v:.8f}" for v in vals))
    open(path, "w").write("\n".join(lines) + "\n")


def test_round_trip():
    prof, ref = ref_roles()
    clip = json.load(open(os.path.join(ROOT, "content", "clips", "dense_test.clip.json")))
    body = [r for r in clip["tracks"] if r in mirrored(ADULT)]
    samples = [{r: clip["tracks"][r]["samples"][k] for r in body} for k in range(clip["frame_count"])]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "rt.bvh")
        write_bvh(p, mirrored(ADULT), ref, samples, clip["fps"])
        src = IB.load_bvh(p)
        out = IB.convert(src, "rt", face="none", fps_out=clip["fps"])
    check(out["frame_count"] == clip["frame_count"], f"round trip frame count {out['frame_count']}")
    worst = 0.0
    for r in body:
        for k in range(clip["frame_count"]):
            worst = max(worst, RT.qangle_deg(samples[k][r], out["tracks"][r]["samples"][k]))
    check(worst <= 0.01, f"round trip worst {worst:.5f} deg")
    print(f"round trip: {len(body)} roles x {clip['frame_count']} frames, worst {worst:.6f} deg")
    # 24 fps resampling of a 60 fps take keeps the length and matches the slerped source
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "rt.bvh")
        write_bvh(p, mirrored(ADULT), ref, samples, clip["fps"])
        out24 = IB.convert(IB.load_bvh(p), "rt24", face="none")
    check(out24["fps"] == 24.0 and out24["frame_count"] == int((clip["frame_count"] - 1) / clip["fps"] * 24) + 1,
          f"24 fps resample: {out24['fps']} {out24['frame_count']}")
    k24 = 10  # t = 10/24 s = source frame 25 (60 fps)
    w24 = max(RT.qangle_deg(samples[25][r], out24["tracks"][r]["samples"][k24]) for r in body)
    check(w24 <= 0.01, f"24 fps sample worst {w24:.5f} deg")


# ------------------------------------------------------------------ 2. ASF/AMC limb directions, folding
ASF = """:version 1.10
:name TEST
:units
  mass 1.0
  length 1.0
  angle deg
:root
   order TX TY TZ RX RY RZ
   axis XYZ
   position 0 0 0
   orientation 0 0 0
:bonedata
{bones}:hierarchy
  begin
    root lhipjoint rhipjoint lowerback
    lhipjoint lfemur
    lfemur ltibia
    ltibia lfoot
    lfoot ltoes
    rhipjoint rfemur
    rfemur rtibia
    rtibia rfoot
    rfoot rtoes
    lowerback upperback
    upperback thorax
    thorax lowerneck lclavicle rclavicle
    lowerneck upperneck
    upperneck head
    lclavicle lhumerus
    lhumerus lradius
    lradius lwrist
    lwrist lhand
    rclavicle rhumerus
    rhumerus rradius
    rradius rwrist
    rwrist rhand
  end
"""
BONES = [("lhipjoint", [1, -1, 0], 1.3, [0, 0, 0], ""), ("lfemur", [0, -1, 0], 7.0, [0, 0, 20], "rx ry rz"),
         ("ltibia", [0, -1, 0], 7.4, [0, 0, 20], "rx"), ("lfoot", [0, -0.2, 1], 2.0, [-90, 0, 20], "rx rz"),
         ("ltoes", [0, 0, 1], 1.0, [-90, 0, 20], "rx"),
         ("lowerback", [0, 1, 0.05], 2.0, [0, 0, 0], "rx ry rz"), ("upperback", [0, 1, 0], 2.0, [0, 0, 0], "rx ry rz"),
         ("thorax", [0, 1, 0], 2.0, [0, 0, 0], "rx ry rz"), ("lowerneck", [0, 1, 0.1], 1.5, [0, 0, 0], "rx ry rz"),
         ("upperneck", [0, 1, -0.1], 1.5, [0, 0, 0], "rx ry rz"), ("head", [0, 1, 0], 1.5, [0, 0, 0], "rx ry rz"),
         ("lclavicle", [1, 0.2, 0], 3.0, [0, 0, 0], "ry rz"), ("lhumerus", [1, 0, 0], 5.0, [0, 0, 90], "rx ry rz"),
         ("lradius", [1, 0, 0], 3.5, [0, 0, 90], "rx"), ("lwrist", [1, 0, 0], 1.0, [0, 0, 90], "ry"),
         ("lhand", [1, 0, 0], 1.0, [0, 0, 90], "rx rz")]


def asf_text():
    out = []
    i = 1
    for n, d, ln, ax, dof in BONES + [(IB.mirror_name(n), [-d[0], d[1], d[2]], ln, [a for a in ax], dof)
                                       for n, d, ln, ax, dof in BONES if n.startswith("l") and n != "lowerback" and n != "lowerneck"]:
        out.append(f"  begin\n     id {i}\n     name {n}\n     direction {d[0]} {d[1]} {d[2]}\n     length {ln}\n"
                   f"     axis {ax[0]} {ax[1]} {ax[2]} XYZ\n" + (f"    dof {dof}\n" if dof else "") + "  end\n")
        i += 1
    return ASF.format(bones="".join(out))


def amc_text(n, fps=120.0):
    """A walking-ish take: legs alternate, trunk sways, arms swing, root travels +Z then turns."""
    lines = [":FULLY-SPECIFIED", ":DEGREES"]
    dof = {b[0]: b[4].split() for b in BONES}
    for b in BONES:
        if b[0].startswith("l") and b[0] not in ("lowerback", "lowerneck"):
            dof[IB.mirror_name(b[0])] = b[4].split()
    for k in range(n):
        t = k / fps
        ph = 2 * math.pi * t / 1.1
        lines.append(str(k + 1))
        lines.append(f"root {0.3 * math.sin(ph):.5f} {16.5 + 0.3 * math.cos(2 * ph):.5f} {14.0 * t:.5f} "
                     f"{4 * math.sin(ph):.5f} {20 * t + 5 * math.sin(ph):.5f} {3 * math.cos(ph):.5f}")
        for bn, ds in dof.items():
            if not ds:
                continue
            side = 1 if bn.startswith("l") else -1
            vals = [(13 + 7 * i) * math.sin(ph * (1 + 0.1 * i) + side + 0.4 * i) for i in range(len(ds))]
            lines.append(bn + " " + " ".join(f"{v:.5f}" for v in vals))
    return "\n".join(lines) + "\n"


def test_limb_directions():
    prof, ref = ref_roles()
    with tempfile.TemporaryDirectory() as d:
        pa, pm = os.path.join(d, "t.asf"), os.path.join(d, "t.amc")
        open(pa, "w").write(asf_text())
        open(pm, "w").write(amc_text(240))
        src = IB.load_asf_amc(pa, pm)
        clip = IB.convert(src, "t", face="none")
    roles = IB.full_roles(IB.CMU_ASF_ROLES)
    piv = IB.full_side(IB.CMU_ASF_PIVOT)
    binding = bindings(mirrored(CHIBI), ref)
    data, order, A, parent = binding
    ends = {x["name"]: x["end"] for x in order}
    worst, per = 0.0, {}
    n = clip["frame_count"]
    for k in range(n):
        L = {r: clip["tracks"][r]["samples"][k] for r in clip["tracks"]}
        G = play(L, binding)
        pose = src.frames[int(round(k * src.fps / 24.0))]
        for r, e in ends.items():
            if not e or e not in roles or r not in G:
                continue
            sd = RT.sub(pose[piv.get(e, roles[e][0])][0], pose[piv.get(r, roles[r][0])][0])
            td = RT.qrot(G[r], data["roles"][r]["dir"])
            a = angle(sd, td)
            per[r] = max(per.get(r, 0.0), a)
            worst = max(worst, a)
    check(worst <= 0.01, f"limb direction worst {worst:.5f} deg {per}")
    check("hips" in per and "neck" in per, "folded roles measured")
    print(f"limb directions on the chibi skeleton: {len(per)} roles x {n} frames, worst {worst:.6f} deg "
          f"(hips {per.get('hips', -1):.6f}, neck {per.get('neck', -1):.6f})")
    check(sorted(clip["x_mocap"]["folded"]) == ["hips", "neck"], f"folded {clip['x_mocap']['folded']}")


# ------------------------------------------------------------------ 3. contacts, ground, loop
def plant_heads():
    return mirrored(ADULT)


def test_contacts_ground_loop():
    prof, ref = ref_roles()
    # A synthetic gait on the adult BVH skeleton: thighs swing, the stance foot stays down; hips height constant.
    heads = plant_heads()
    leg = RT.derive(heads, ref)["leg_length"]
    fps, period = 120.0, 1.0
    speed = 0.35 * 2 * math.pi / period * leg  # the stance foot stands still at mid-stance
    samples = []
    for k in range(int(3 * fps)):
        ph = 2 * math.pi * k / (fps * period)
        L = {}
        for s, off in ((".L", 0.0), (".R", math.pi)):
            a = 0.35 * math.sin(ph + off)
            L["thigh" + s] = RT.qnorm([math.cos(a / 2), math.sin(a / 2), 0, 0])
            kn = max(0.0, 0.9 * math.sin(ph + off - 2.2))
            L["shin" + s] = RT.qnorm([math.cos(kn / 2), math.sin(kn / 2), 0, 0])
        samples.append(L)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "g.bvh")
        write_bvh(p, heads, ref, samples, fps)
        src = IB.load_bvh(p)
        # move the root forward (a treadmill-free walk) by editing the source frames' root channel
        for k, fr in enumerate(src.frames):
            dz = speed * k / fps
            for j, (pos, rot) in list(fr.items()):
                fr[j] = ([pos[0], pos[1] + 0.25, pos[2] + dz], rot)  # lifted 25 cm: the importer grounds it
        clip = IB.convert(src, "g", loop="auto", style="walk", face="travel")
    check(clip["loop"] and abs(clip["frame_count"] - 24) <= 1, f"loop period {clip['frame_count']} frames")
    cyc = clip["root"].get("cycle_offset")
    check(cyc is not None and abs(cyc[2] - speed * period / leg) < 0.02 and abs(cyc[1]) < 1e-9, f"cycle_offset {cyc}")
    plants = [c for c in clip["contacts"] if c["type"] == "foot_plant"]
    check({c["role"] for c in plants} == {"foot.L", "foot.R"}, f"plants {plants}")
    ys = [r[1] for r in clip["root"]["translation"]["samples"]]
    check(max(ys) < 0.02 and min(ys) > -0.2, f"ground: root height {min(ys):.4f}..{max(ys):.4f} leg lengths")
    for r in ("thigh.L", "shin.L", "hips"):
        a, b = clip["tracks"][r]["samples"][0], clip["tracks"][r]["samples"][-1]
        check(RT.qangle_deg(a, b) < 20, f"loop seam {r}")
    st = clip.get("style", {})
    check(st.get("foot_lock") is True and "arm_center" in st, f"style block {st}")
    print(f"contacts/ground/loop: period {clip['frame_count']} f, cycle {cyc}, plants {plants}")


# ------------------------------------------------------------------ 4. the library
def test_library():
    d = os.path.join(ROOT, "content", "clips", "mocap")
    files = sorted(f for f in os.listdir(d) if f.endswith(".clip.json")) if os.path.isdir(d) else []
    check(len(files) >= 2, f"mocap library has {len(files)} clips")
    valid = TCF._profile_roles()
    att = open(os.path.join(d, "ATTRIBUTION.md")).read() if os.path.exists(os.path.join(d, "ATTRIBUTION.md")) else ""
    check("mocap.cs.cmu.edu" in att and "NSF EIA-0196217" in att, "ATTRIBUTION.md carries the CMU credit")
    for f in files:
        data = json.load(open(os.path.join(d, f)))
        errs = TCF._validate_data(data, valid)
        check(not errs, f"{f}: {errs[:3]}")
        check(data.get("license") == IB.CMU_LICENSE and "mocap.cs.cmu.edu" in data.get("attribution", ""), f"{f}: licence")
        check(data.get("source") == "mocap", f"{f}: source")
        check(data["name"] in att, f"{f}: not in ATTRIBUTION.md")
        for c in data.get("contacts", []):
            a, b = c["frames"]
            lim = 2 * data["frame_count"] if data.get("loop") else data["frame_count"]
            check(0 <= a <= b < lim, f"{f}: contact frames {c}")
    print(f"library: {len(files)} clips")


if __name__ == "__main__":
    test_round_trip()
    test_limb_directions()
    test_contacts_ground_loop()
    test_library()
    if FAILS:
        print(f"{len(FAILS)} failure(s)")
        sys.exit(1)
    print("test_import_bvh: all passed")
