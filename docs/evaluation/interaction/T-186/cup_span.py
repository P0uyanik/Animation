# Largest cup motion (translation mm, rotation deg) against frame `ref` over frames a..b; and the lowest y (mm, table = ref).
import json, math, sys
def mats(p):
    d = json.load(open(p)); return {f["frame"]: f["props"]["cup"] for f in d["frame_data"]}
def rot(m, m1):
    A = [[m[c*4+r] for c in range(3)] for r in range(3)]; B = [[m1[c*4+r] for c in range(3)] for r in range(3)]
    R = [[sum(A[i][k]*B[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    tr = (R[0][0] + R[1][1] + R[2][2] - 1) / 2
    w = ((R[2][1]-R[1][2])/2, (R[0][2]-R[2][0])/2, (R[1][0]-R[0][1])/2)
    return math.degrees(math.atan2(math.sqrt(sum(x*x for x in w)), tr))
def span(p, a, b, ref):
    M = mats(p); r = M[ref]
    t = max(math.dist(M[f][12:15], r[12:15]) for f in range(a, b + 1)) * 1e3
    lo = min(M[f][13] - r[13] for f in range(a, b + 1)) * 1e3
    slide = max(math.hypot(M[f][12] - r[12], M[f][14] - r[14]) for f in range(a, b + 1)) * 1e3
    ang = max(rot(M[f], r) for f in range(a, b + 1))
    return t, lo, slide, ang
if __name__ == "__main__":
    for p in sys.argv[4:]:
        t, lo, s, ang = span(p, int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
        print(f"{p}: f{sys.argv[1]}-{sys.argv[2]} largest move {t:.3f} mm, lowest {lo:.3f} mm, slide {s:.3f} mm, rotation {ang:.4f} deg")
