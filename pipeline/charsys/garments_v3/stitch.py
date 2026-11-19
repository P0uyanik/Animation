"""``garment/3`` ``sole_stitch`` (``boots``, ``shoes``; T-126): the row of yarn stitches that joins the upper to the sole.

Per side one piece ``garment.<item>.stitch.<side>`` (part ``stitch``; material ``materials.stitch``, else the band
material): short raised stitches on the upper, ``above_m`` over the top of the sole, one every ``pitch_m`` round the
foot, each ``length`` of the pitch long and ``radius_m`` thick. It is skinned like the upper under it.

  {"pitch_m": 0.007, "radius_m": 0.0011, "length": 0.55, "above_m": 0.003}
Sizes are multiplied by the leg scale of the body. Character-agnostic: the line is measured on the built upper
(its outline at that height) and the built sole."""
import math

from mathutils import Vector

from garments import generator as GEN

STITCH = {"pitch_m": 0.007, "radius_m": 0.0011, "length": 0.55, "above_m": 0.003}
RANGES = {"pitch_m": (0.002, 0.05), "radius_m": (0.0003, 0.005), "length": (0.1, 0.95), "above_m": (0.0, 0.05)}
BINS = 180


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.sole_stitch must be true or an object")
    for key in v:
        if key not in STITCH:
            raise ValueError(f"garment {name}.sole_stitch.{key}: unknown field (known: {sorted(STITCH)})")
        GEN._number(v[key], f"garment {name}.sole_stitch.{key}", *RANGES[key])


def _outline(ob, z, band):
    """Closed outline (world points) of a piece at height z: the outermost vertex per direction about its centre."""
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    near = [p for p in pts if abs(p.z - z) <= band]
    if len(near) < 12:
        raise ValueError(f"sole_stitch: {ob.name} has no outline at z = {z:.4f} m")
    c = sum(near, Vector()) / len(near)
    best = [None] * BINS
    for p in near:
        k = int((math.atan2(p.y - c.y, p.x - c.x) / (2 * math.pi) + 0.5) * BINS) % BINS
        r = math.hypot(p.x - c.x, p.y - c.y)
        if best[k] is None or r > best[k][0]:
            best[k] = (r, p)
    ring = [Vector((b[1].x, b[1].y, z)) for b in best if b is not None]
    for _ in range(2):  # light smoothing of the binned outline
        ring = [(ring[i - 1] + 2 * ring[i] + ring[(i + 1) % len(ring)]) / 4 for i in range(len(ring))]
    return ring, c


def add(C, cfg, mine, H, G, fit):
    st = dict(STITCH, **(cfg["sole_stitch"] if isinstance(cfg["sole_stitch"], dict) else {}))
    pitch, rad = float(st["pitch_m"]) * fit.leg, float(st["radius_m"]) * fit.leg
    part = "stitch" if "stitch" in cfg.get("materials", {}) else "band"
    made, info = [], {"pitch_m": round(pitch, 5), "pieces": {}}
    for side in ("L", "R"):
        upper = next((o for o in mine if o.name == f"garment.{cfg['name']}.main.{side}"), None)
        sole = next((o for o in mine if o.name == f"garment.{cfg['name']}.sole.{side}"), None)
        if upper is None or sole is None:
            raise ValueError(f"garment {cfg['name']}.sole_stitch needs the upper and the sole on side {side}")
        z = max((sole.matrix_world @ v.co).z for v in sole.data.vertices) + float(st["above_m"]) * fit.leg
        ring, centre = _outline(upper, z, 0.004 * fit.leg)
        lengths = [(ring[(i + 1) % len(ring)] - ring[i]).length for i in range(len(ring))]
        total = sum(lengths)
        count = max(8, int(total / pitch))

        def at(s):
            s %= total
            for i, seg in enumerate(lengths):
                if s <= seg:
                    return ring[i].lerp(ring[(i + 1) % len(ring)], s / max(seg, 1e-12))
                s -= seg
            return ring[0]

        verts, faces = [], []
        for k in range(count):
            s0 = total * k / count
            a, b = at(s0), at(s0 + float(st["length"]) * total / count)
            mid = (a + b) / 2
            out = Vector((mid.x - centre.x, mid.y - centre.y, 0.0)).normalized()
            a, b, mid = a + out * 0.4 * rad, b + out * 0.4 * rad, mid + out * 0.9 * rad
            base = len(verts)
            verts += [a, b, mid + out * rad, mid + Vector((0, 0, rad)), mid - out * rad, mid - Vector((0, 0, rad))]
            for j in range(4):
                p, q = base + 2 + j, base + 2 + (j + 1) % 4
                faces += [(base, q, p), (base + 1, p, q)]
        ob = G.new_object(f"garment.{cfg['name']}.stitch.{side}", verts, faces, C)
        GEN._feature(made, ob, cfg, "stitch", GEN._mat_for(G, cfg, part, H), G)
        info["pieces"][ob.name] = {"stitches": count, "z_m": round(z, 4), "outline_m": round(total, 4)}
    return made, info
