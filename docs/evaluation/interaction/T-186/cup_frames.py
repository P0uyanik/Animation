import json, sys, math
d = json.load(open(sys.argv[1])); a, b = int(sys.argv[2]), int(sys.argv[3]); prop = sys.argv[4] if len(sys.argv) > 4 else "cup"
fd = d["frame_data"]; f0 = d["frames"][0] if isinstance(d["frames"], list) else 1
def M(i): return fd[i]["props"][prop]
m1 = M(0)
for i, fr in enumerate(fd):
    f = fr["frame"]
    if not (a <= f <= b): continue
    m = M(i)
    dt = [(m[12 + k] - m1[12 + k]) * 1e3 for k in range(3)]
    rot = max(abs(m[j] - m1[j]) for j in (0,1,2,4,5,6,8,9,10))
    # rotation of m relative to m1 (column-major 4x4): R = m * m1^T, angle from its skew part
    A=[[m[c*4+r] for c in range(3)] for r in range(3)]; B=[[m1[c*4+r] for c in range(3)] for r in range(3)]
    R=[[sum(A[i][k]*B[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    w=((R[2][1]-R[1][2])/2,(R[0][2]-R[2][0])/2,(R[1][0]-R[0][1])/2)
    ang = math.degrees(math.asin(min(1, math.sqrt(sum(x*x for x in w)))))
    print(f"f{f:3d} dx {dt[0]:7.2f} dy {dt[1]:7.2f} dz {dt[2]:7.2f} mm  rot {ang:6.2f} deg")
