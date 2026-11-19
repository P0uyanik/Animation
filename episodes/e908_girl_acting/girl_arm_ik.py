"""Pose solver for the girl's gesture clips (T-097-girl; pure Python, no Blender).

Clip rotations are joint rotations in each role's REFERENCE (T-pose) frame relative to its semantic parent
(docs/ANIMATION_CLIPS.md): the world direction of a role is the product of its parents' clip rotations and its own,
applied to the role's reference direction (+x for the left arm chain). The engine retargets the same rotations to
every rig, so a pose whose hand should land on the girl's own chin has to be solved on HER proportions (short arms,
big head: girl 0.11.0 upper arm 0.094 m, forearm 0.086 m, hand 0.039 m; the authoring mannequin's arm is longer).

solve_arm() finds left-side definitions (upperArm, forearm, hand; mirrored for the right side by the clip helpers) that
put the knuckle point (hand head + hand length along the hand) on a target in the character's rest frame, with a
preferred hand direction and the elbow kept low and close to the body. Deterministic (Nelder-Mead from a fixed start).
"""
import math

ID = [1.0, 0.0, 0.0, 0.0]


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return [aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw]


def qrot(q, v):
    p = qmul(qmul(q, [0.0] + list(v)), [q[0], -q[1], -q[2], -q[3]])
    return p[1:]


def rot(axis, deg):
    a = math.radians(deg) / 2
    n = math.sqrt(sum(c * c for c in axis))
    return [math.cos(a)] + [c / n * math.sin(a) for c in axis]


def rx(d):
    return rot([1, 0, 0], d)


def ry(d):
    return rot([0, 1, 0], d)


def rz(d):
    return rot([0, 0, 1], d)


def seq(*qs):
    out = ID
    for q in qs:
        out = qmul(q, out)
    return out


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def scale(a, s):
    return [x * s for x in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    n = math.sqrt(dot(a, a))
    return [x / n for x in a]


# girl_auburn_bun_glasses 0.11.0 engine package (left side; measured from the exported skeleton, T-097-girl)
GIRL = {"chest": [0.0, 0.536, 0.0], "shoulder": [0.098, 0.614, 0.0], "upper": 0.0943, "fore": 0.0860, "hand": 0.0390}


def arm_points(p, chest_q=ID, rig=GIRL):
    """Shoulder, elbow, wrist and knuckle positions (rest frame) of the left arm for parameters p (degrees):
    upper = seq(rx(p0), rz(p1), ry(p2)), fore = seq(ry(p3), rz(p4)), hand = seq(rz(p5), ry(p6)); chest_q rotates
    the chest (and so the shoulder) about the chest head."""
    up = seq(rx(p[0]), rz(p[1]), ry(p[2]))
    fo = seq(ry(p[3]), rz(p[4]))
    ha = seq(rz(p[5]), ry(p[6]))
    sh = add(rig["chest"], qrot(chest_q, sub(rig["shoulder"], rig["chest"])))
    Ru = qmul(chest_q, up)
    el = add(sh, scale(qrot(Ru, [1, 0, 0]), rig["upper"]))
    Rf = qmul(Ru, fo)
    wr = add(el, scale(qrot(Rf, [1, 0, 0]), rig["fore"]))
    Rh = qmul(Rf, ha)
    hd = qrot(Rh, [1, 0, 0])
    kn = add(wr, scale(hd, rig["hand"]))
    return sh, el, wr, kn, hd, (up, fo, ha)


def nelder_mead(f, x0, step=10.0, iters=4000, tol=1e-10):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step if j == i else 0.0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        xr = [c[j] + (c[j] - pts[-1][j]) for j in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [c[j] + 2 * (c[j] - pts[-1][j]) for j in range(n)]
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [c[j] + 0.5 * (pts[-1][j] - c[j]) for j in range(n)]
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [[pts[0][j] + 0.5 * (p[j] - pts[0][j]) for j in range(n)] for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    i = min(range(n + 1), key=lambda k: vals[k])
    return pts[i], vals[i]


BODY_FRONT = 0.085  # girl 0.11.0: front of the vest / chest at |x| < 0.09 m (mesh profile), rest frame z


def solve_arm(target, hand_dir, x0, chest_q=ID, rig=GIRL, elbow_drop=0.03, elbow_in=None, w_dir=0.02,
              point_dir=None, front=BODY_FRONT):
    """Left-arm parameters (degrees, see arm_points) whose knuckle lands on `target` (rest frame, metres) with the
    hand pointing along `hand_dir`; the elbow stays elbow_drop below the shoulder and (if elbow_in) no further out
    than elbow_in in x. The elbow never swings across the shoulder line (the upper arm would cut through the chest; the
    engine's pose clearance then pushes the arm out) and elbow and wrist stay in front of the body (z >= front)
    where they are in front of it (|x| < shoulder x). point_dir (optional): the wrist-to-knuckle line should also continue the forearm (a straight
    pointing arm along point_dir). Returns (params, knuckle error in metres)."""
    hd_pref = norm(hand_dir)

    def cost(p):
        sh, el, wr, kn, hd, _ = arm_points(p, chest_q, rig)
        c = 1e4 * dot(sub(kn, target), sub(kn, target))
        c += w_dir * (1 - dot(hd, hd_pref))
        c += 50 * max(0.0, el[1] - (sh[1] - elbow_drop)) ** 2 * 1e2
        c += 1e3 * max(0.0, sh[0] - el[0]) ** 2  # no adduction across the chest
        for q in (el, wr):
            if abs(q[0]) < sh[0] + 0.01:
                c += 1e3 * max(0.0, front - q[2]) ** 2
        if elbow_in is not None:
            c += 1e3 * max(0.0, el[0] - elbow_in) ** 2
        if point_dir is not None:
            pd = norm(point_dir)
            c += 0.05 * (1 - dot(norm(sub(wr, el)), pd)) + 0.05 * (1 - dot(norm(sub(el, sh)), pd))
        c += 1e-6 * sum(x * x for x in p)  # the smallest rotations that do it
        return c

    best, val = nelder_mead(cost, x0)
    for _ in range(3):  # restarts from the best point (Nelder-Mead stalls on long valleys)
        best, val = nelder_mead(cost, best, step=5.0)
    kn = arm_points(best, chest_q, rig)[3]
    return best, math.sqrt(dot(sub(kn, target), sub(kn, target)))
