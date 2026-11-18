"""face_generic/3 "felt eye" shading mode (T-089), opt-in by spec data:
  spec.face.eyes.shader = "felt/1"
  spec.face.eyes.felt = {"roughness": 0.85, "sheen": 0.5, "sheen_tint_srgb": [..], "streaks": 0.0,
                         "highlight": [x, z, r(, strength)], "highlight_softness": 0.05, "highlight_strength": 1.4,
                         "lid_line": {"roughness": 0.95, "sheen": 0.3}, "round_iris": false}
A matte felt eye: the layered iris colours of face_features.eye_material_layered (same spec keys: iris, sclera_srgb,
...), but no wet clear coat, a rough felt base with sheen, no glossy streaks, and exactly ONE crisp highlight; the
upper lash tube becomes a matte felt lid line. The glossy layered/1 eye stays the default (shader absent or another
value). Character-independent: all values are data."""
import face_features as FF


def _f(d, k, default):
    return float(d.get(k, default)) if d is not None else float(default)


def felt_config(ecfg):
    felt = dict(ecfg.get("felt") or {})
    iris = dict(ecfg.get("iris") or {})
    iris["streaks"] = _f(felt, "streaks", 0.0)
    hl = felt.get("highlight") or (ecfg.get("highlights") or [[0.22, 0.12, 0.09]])[0]
    hl = [float(v) for v in hl[:3]] + [float(hl[3]) if len(hl) > 3 else 1.0]
    rough = _f(felt, "roughness", 0.85)
    return dict(ecfg, iris=iris, highlights=[hl], wet_coat={"weight": 0.0, "roughness": rough, "base_roughness": rough},
                catchlight_softness=_f(felt, "highlight_softness", 0.05),
                catchlight_strength=_f(felt, "highlight_strength", 1.4)), felt


def eye_material_felt(name, ecfg, r):
    cfg, felt = felt_config(ecfg)
    m = FF.eye_material_layered(name, cfg, r)
    if felt.get("round_iris"):  # keep the iris and highlight round on a non-uniformly scaled eyeball
        _round_iris(m, ecfg.get("scale", [1.0, 1.0, 1.0]))
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Coat Weight"].default_value = 0.0
    p.inputs["Roughness"].default_value = _f(felt, "roughness", 0.85)
    p.inputs["Specular IOR Level"].default_value = _f(felt, "specular", 0.2)
    p.inputs["Sheen Weight"].default_value = _f(felt, "sheen", 0.5)
    p.inputs["Sheen Roughness"].default_value = 0.5
    tint = felt.get("sheen_tint_srgb")
    if tint:
        p.inputs["Sheen Tint"].default_value = FF._lin(tuple(tint))
    m["ps_face_shader"] = "eye/felt/1"
    return m


def _round_iris(m, scale):
    """The layered eye paints the iris in the eyeball's unit-sphere ("Generated") space, so an eyeball scaled by
    (sx, sy, sz) shows an sx:sz oval iris. Scales the unit x coordinate by sx/sz before the iris ramp: round again."""
    sx, sz = float(scale[0]), float(scale[2])
    if abs(sx / sz - 1.0) < 1e-6:
        return
    nt = m.node_tree
    gen = next(n for n in nt.nodes if n.type == "VECT_MATH" and n.operation == "MULTIPLY_ADD")
    targets = [l.to_socket for l in nt.links if l.from_node == gen]
    mul = nt.nodes.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = (sx / sz, 1.0, 1.0)
    nt.links.new(gen.outputs[0], mul.inputs[0])
    for t in targets:
        nt.links.new(mul.outputs[0], t)
    m["ps_round_iris"] = round(sx / sz, 4)


def felt_lid_line(mat, felt):
    """The upper lash tube as a matte felt lid line (same colour, no gloss)."""
    lc = (felt or {}).get("lid_line") or {}
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Roughness"].default_value = _f(lc, "roughness", 0.95)
    p.inputs["Specular IOR Level"].default_value = _f(lc, "specular", 0.1)
    p.inputs["Sheen Weight"].default_value = _f(lc, "sheen", 0.3)
    mat["ps_face_shader"] = "lid_line/felt/1"
    return mat
