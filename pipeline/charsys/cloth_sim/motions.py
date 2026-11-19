"""Test motions for the cloth simulation prototype: FK poses per frame on the shared rig (24 fps).

A motion is {"frames", "pose": frame -> [(bone pattern, world axis, degrees, sides)], "evidence": {name: frame},
"props": [...]}. Angles turn a bone about a world axis through its head, in order (thigh, then shin). On this rig a
negative X turn swings a leg forward. They are probes for the skirt, not animation: no root motion, no foot contact.
The arms stay in the A-pose: lowered arms press into the skirt sides (the body is the collider, sleeves and hands
are not) and their swing drags a stiff skirt upwards by centimetres, which is an arm/sleeve contact problem this
prototype does not solve."""
import math

SETTLE = 12  # frames at rest before a motion starts (the cloth settles under gravity)


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def walk(cycles=2, period=24, swing=26.0, knee=38.0, arm=18.0):
    frames = SETTLE + cycles * period

    def pose(f):
        if f <= SETTLE:
            return []
        ph = 2 * math.pi * (f - SETTLE) / period
        gain = _ease((f - SETTLE) / 6.0)
        out = []
        for side, sg in (("L", 1.0), ("R", -1.0)):
            s = math.sin(ph) * sg
            out.append(("thigh_fk.{s}", "X", -swing * s * gain, side))
            out.append(("shin_fk.{s}", "X", knee * max(0.0, math.cos(ph) * sg) * gain, side))
            out.append(("upper_arm_fk.{s}", "X", arm * s * gain, side))
        return out

    q = period // 4
    return {"name": "walk", "frames": frames, "pose": pose, "props": [],
            "evidence": {"walk_stride_L": SETTLE + period + q, "walk_passing": SETTLE + period + 2 * q,
                         "walk_stride_R": SETTLE + period + 3 * q}}


def sit(into=20, hold=22, thigh=82.0, shin=80.0):
    frames = SETTLE + into + hold

    def pose(f):
        g = _ease((f - SETTLE) / into)
        return [("thigh_fk.{s}", "X", -thigh * g, "LR"), ("shin_fk.{s}", "X", shin * g, "LR")]

    return {"name": "sit", "frames": frames, "pose": pose, "props": ["seat"],
            "evidence": {"sit_half": SETTLE + into // 2, "sit": frames}}


def kneel(into=20, hold=22, thigh=12.0, shin=105.0):
    frames = SETTLE + into + hold

    def pose(f):
        g = _ease((f - SETTLE) / into)
        return [("thigh_fk.{s}", "X", -thigh * g, "LR"), ("shin_fk.{s}", "X", shin * g, "LR")]

    return {"name": "kneel", "frames": frames, "pose": pose, "props": [], "evidence": {"kneel": frames}}


MOTIONS = {"walk": walk, "sit": sit, "kneel": kneel}
