"""T-119: garments round 3 (``garment/3``, package ``garments_v3``) and the opt-in limb skin (skin_presets_r3.json).

    python3 pipeline/charsys/tests/test_garments_r3.py [--blender <exe>] [--quick]
        [--girl-current <0.12.0 master.blend>] [--girl-master <0.12.0 + T-119 master.blend>]
        [--boy-current <2.1.0 master.blend>]   [--boy-master <2.1.0 + T-119 master.blend>]
        [--girl-default <master built from the published 0.12.0 spec with this code>] [--boy-default <same, 2.1.0>]
        [--girl-components <0.12.0 + components-demo master.blend>]

Checks (each line PASS/FAIL; exit code 1 on any FAIL):
  plain     (no Blender) garment/3 is registered to garments_v3 and garment/1 and garment/2 keep their lines; the
            published specs pin garment/2, carry no garment/3 field and no skin_limbs slot (defaults unchanged); the
            T-119 overrides load on the published specs and pin garment/3; skin_presets_r3.json validates, reuses no
            id, resolves as presets/3 and leaves the older ids resolving from their own files; garments/,
            garments_v2/, their tests and the three older preset files are unchanged against the merge base.
  validate  (Blender) the candidate blocks validate; out-of-range values, unknown keys and fields on the wrong item
            type are rejected; a garment/3 block without a garment/3 field has the published block as its garment/2
            view (so it builds the garment/2 geometry by construction).
  girl      (build) the seated collar is carried by the chest and the shoulders only, stands off the layers under
            it less than the current one and stays in place in a one-arm reach; the two cuff bands do not overlap and
            the shell does not hang below them.
  boy       (build) no skin is left uncovered round the ankle at rest, toes up and toes down (the current build
            leaves some in every pose); the hands use the limb preset, the current hands do not.
  default   (build) a master built from each published spec with this code has every garment piece, hand and
            material name identical to the published master (vertex hash).
  parts     (build, scope addition) the component fixture (the girl without her vest): the Peter Pan collar lies on
            its own bodice at the configured thickness, chest-carried; each sleeve has a rib cuff band beyond its
            seam ring with the configured number of wales, skinned without head or torso-only weights.
  t126      (T-126c additions) plain: the third character's dress override pins garment/3 and holds tights, dress
            and boots; garments_v3/ and cloth_sim/ name no character. validate (Blender): her block validates, its
            garment/2 view has no tights item and no new field, bad values / unknown keys / wrong item types are
            rejected, the skirt pattern height stays in 0..1. build: on the T-070 draft body the tights are one
            masked skin-following piece, the skirt is refined, tagged for the cloth simulation and pinned at the
            waist only, every dress piece carries the ps_fibre UV map, each boot has its sole stitches.
--quick runs plain and validate only. Masters given on the command line are used instead of building them."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
CH = os.path.join(ROOT, "assets", "characters")
T119 = os.path.join(ROOT, "docs", "evaluation", "characters", "T-119")
CAST = {"girl": ("girl_auburn_bun_glasses", "0.12.0"), "boy": ("boy_yellow_hoodie", "2.1.0")}
V3_FIELDS = ("collar_seat", "cuff_gather", "ankle_close", "rib_cuff")
FIXTURE = os.path.join(T119, "components", "girl_auburn_bun_glasses.components-demo.override.json")
OLDER_PRESETS = ("presets.json", "skin_presets.json", "presets_r2.json")
GUARDED = ["pipeline/charsys/garments", "pipeline/charsys/garments_v2", "pipeline/charsys/tests/test_garments_v2.py",
           "pipeline/charsys/tests/test_garments_v2_t093b.py", "pipeline/charsys/tests/test_garment_details.py",
           "pipeline/charsys/tests/test_hoodie.py"] + [f"pipeline/charsys/materials/{f}" for f in OLDER_PRESETS]
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_garments_r3] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"),
          flush=True)


def spec_path(who):
    cid, version = CAST[who]
    return os.path.join(CH, cid, "spec", f"{cid}.{version}.spec.json")


def override_path(who):
    return os.path.join(T119, f"{CAST[who][0]}.T-119.override.json")


def run_blender(blender, script, args):
    subprocess.run([blender, "-b", "--factory-startup", "-P", script, "--"] + args, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build(blender, who, overrides):
    out = tempfile.mkdtemp(prefix="t119_")
    args = ["--spec", spec_path(who), "--out", out, "--no-glb", "--no-compare"]
    for o in overrides:
        args += ["--override", o]
    run_blender(blender, os.path.join(CHARSYS, "build_character.py"), args)
    return os.path.join(out, f"{CAST[who][0]}_master.blend")


def probe(blender, script):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "probe.py"), os.path.join(tmp, "out.json")
        open(src, "w").write("import bpy, json, sys\nsys.path.insert(0, %r)\nRESULT = {}\n%s\n"
                             "json.dump(RESULT, open(%r, 'w'))\n" % (CHARSYS, script, out))
        run_blender(blender, src, [])
        return json.load(open(out))


def test_plain():
    import spec as S
    import versions as V
    from materials import builder as M

    src = open(os.path.join(CHARSYS, "versions.py")).read()
    check("garment/3 is registered to garments_v3", '_r("garment", "garment", 3, "garments_v3")' in src
          and V.REGISTRY.check("garment", "garment/3") == "garment/3")
    check("the garment/1 and garment/2 registry lines are kept",
          '_r("garment", "garment", 1, "garments")\n' in src and '_r("garment", "garment", 2, "garments_v2")' in src)
    check("garments_v3 declares garment/3", 'GENERATOR_VERSIONS = ("garment/3",)'
          in open(os.path.join(CHARSYS, "garments_v3", "__init__.py")).read())
    for who in CAST:
        published = json.load(open(spec_path(who)))
        pins, _ = V.resolve_pins(published)
        fields = sorted(f for g in published["clothing"]["garments"] for f in V3_FIELDS if f in g)
        check(f"{who}: the published spec pins garment/2, has no garment/3 field and no skin_limbs slot",
              pins["garment"] == "garment/2" and not fields
              and "skin_limbs" not in (published["materials"].get("assignments") or {}), (pins["garment"], fields))
        spec, info = S.load(spec_path(who), [override_path(who)])
        check(f"{who}: the T-119 override loads on the published spec and pins garment/3",
              info["versions"]["generators"]["garment"] == "garment/3" and spec["clothing"]["generator"] == "garment/3")
        check(f"{who}: the override changes no garment material entry",
              {g["name"]: g.get("material") for g in published["clothing"]["garments"]}
              == {g["name"]: g.get("material") for g in spec["clothing"]["garments"]})
    boy, _ = S.load(spec_path("boy"), [override_path("boy")])
    limbs = boy["materials"]["assignments"].get("skin_limbs") or {}
    check("boy: the override adds the skin_limbs slot with an id of skin_presets_r3.json and keeps the skin slot",
          M.is_r3_preset(limbs.get("preset")) and boy["materials"]["assignments"]["skin"]
          == json.load(open(spec_path("boy")))["materials"]["assignments"]["skin"], limbs.get("preset"))
    check("boy: the candidate material assignments validate", M.validate_assignments(boy["materials"]) == [])
    bad = json.loads(json.dumps(boy["materials"]))
    bad["assignments"]["skin_limbs"]["preset"] = "skin-felt-limbs/9"
    check("an unknown skin_limbs preset id is rejected", bool(M.validate_assignments(bad)))

    r3 = M.load_r3_library()
    taken = (set(M.load_library()["presets"]) | set(M.load_skin_library()["presets"])
             | set(M.load_r2_library()["presets"]))
    check("skin_presets_r3.json validates as a presets/3 library with new ids ending in /3",
          r3["family"] == M.R2_FAMILY and all(n.endswith("/3") for n in r3["presets"]) and not set(r3["presets"]) & taken,
          sorted(r3["presets"]))
    check("its ids resolve as presets/3 from their own file",
          all(M.preset_family(n) == "presets/3" and M.library_for(n) is not None and M.resolve_preset(n)["family"]
              == M.R2_FAMILY and M.is_known_preset(n) for n in r3["presets"]))
    check("older ids are not ids of the new file and still resolve from their own files",
          not any(M.is_r3_preset(n) for n in taken) and M.preset_family("skin-felt/3") == "presets/3"
          and M.preset_family("skin-felt/2") == "presets/2" and M.preset_family("felt") == "presets/1"
          and M.library_for("skin-felt/3")["presets"].keys() == M.load_r2_library()["presets"].keys())
    old, new = M.resolve_preset("skin-felt/3"), M.resolve_preset("skin-felt-limbs/3")
    diff = sorted(f"{sec}.{k}" for sec in new if isinstance(new[sec], dict) for k in new[sec]
                  if new[sec][k] != (old.get(sec) or {}).get(k))
    check("skin-felt-limbs/3 is skin-felt/3 with a shorter subsurface scale and a lower rim weight only",
          diff == ["silhouette.weight", "surface.subsurface_scale_fraction"] and new["skin"] == old["skin"]
          and new["surface"]["subsurface_scale_fraction"] < old["surface"]["subsurface_scale_fraction"]
          and new["silhouette"]["weight"] < old["silhouette"]["weight"], diff)
    for ref in ("origin/main", "origin/integration/r4-start"):
        try:
            base = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", ref], check=True, capture_output=True,
                                  text=True).stdout.strip()
            diff = subprocess.run(["git", "-C", ROOT, "diff", "--name-only", base, "--"] + GUARDED, check=True,
                                  capture_output=True, text=True).stdout.split()
            check(f"garments/, garments_v2/, their tests and the older preset files are unchanged against {ref}",
                  not diff, diff)
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    else:
        print("[test_garments_r3] SKIP git check (no origin/main or origin/integration/r4-start here)")


VALIDATE = r'''
import copy
import garments_v3 as V3
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
out = []
blocks = {}
for who, ovr, spec in %r:
    cand = json.load(open(ovr))["override"]["clothing"]
    published = json.load(open(spec))["clothing"]
    blocks[who] = cand
    out.append([f"{who}: the candidate clothing block validates", V3.validate(copy.deepcopy(cand)) is not None])
    plain = copy.deepcopy(published)
    plain["generator"] = "garment/3"
    out.append([f"{who}: garment/3 without a new field has the published block as its garment/2 view",
                V3.v2_view(plain) == published and V3.validate(plain) is not None])
    view = V3.v2_view(cand)
    out.append([f"{who}: the garment/2 view of the candidate carries no garment/3 field",
                view["generator"] == "garment/2" and not any(f in g for g in view["garments"] for f in %r)])
def item(block, name):
    return next(g for g in block["garments"] if g["name"] == name)
def bad(who, name, field, value, label):
    c = copy.deepcopy(blocks[who])
    g = item(c, name)
    g[field] = dict(g.get(field) or {}, **value) if isinstance(value, dict) else value
    out.append([label + " rejected", raises(lambda: V3.validate(c))])
bad("girl", "blouse", "collar_seat", {"gap_m": 0.5}, "collar_seat.gap_m 0.5")
bad("girl", "blouse", "collar_seat", {"nope": 1}, "collar_seat unknown key")
bad("girl", "blouse", "collar_seat", {"over": ["cape"]}, "collar_seat.over naming no item")
bad("girl", "blouse", "collar_seat", {"shoulder_bone": "DEF-shoulder"}, "collar_seat.shoulder_bone without {side}")
bad("girl", "vest", "collar_seat", {}, "collar_seat on a vest")
bad("girl", "shorts", "cuff_gather", {"pleats": 2.5}, "cuff_gather.pleats 2.5")
bad("girl", "shorts", "cuff_gather", {"height_m": 0.0}, "cuff_gather.height_m 0")
bad("girl", "blouse", "cuff_gather", {}, "cuff_gather on a top")
bad("boy", "trousers", "ankle_close", {"ease_m": 0.5}, "ankle_close.ease_m 0.5")
bad("boy", "trousers", "ankle_close", {"sock": True}, "ankle_close unknown key")
bad("boy", "hoodie", "ankle_close", {}, "ankle_close on a hoodie")
bad("girl", "blouse", "collar_seat", {"thickness_m": 0.5}, "collar_seat.thickness_m 0.5")
bad("girl", "blouse", "rib_cuff", {"ribs": 200}, "rib_cuff.ribs 200")
bad("girl", "blouse", "rib_cuff", {"height_m": 0.0}, "rib_cuff.height_m 0")
bad("girl", "blouse", "rib_cuff", {"wales": 3}, "rib_cuff unknown key")
bad("girl", "shorts", "rib_cuff", {}, "rib_cuff on shorts")
c = copy.deepcopy(blocks["girl"])
item(c, "blouse")["rib_cuff"] = {}
item(c, "blouse")["bands"] = {"cuff": False}
out.append(["rib_cuff without sleeve cuff bands rejected", raises(lambda: V3.validate(c))])
c = copy.deepcopy(blocks["boy"])
item(c, "hoodie")["rib_cuff"] = {"ribs": 0}
out.append(["rib_cuff validates on a hoodie (plain band, ribs 0)", V3.validate(c) is not None])
fixture = json.load(open(%r))["override"]["clothing"]
out.append(["the component fixture block validates, has no vest and no collar 'over'",
            V3.validate(copy.deepcopy(fixture)) is not None
            and not any(g["name"] == "vest" for g in fixture["garments"])
            and item(fixture, "blouse")["collar_seat"]["over"] == [] and "rib_cuff" in item(fixture, "blouse")])
c = copy.deepcopy(blocks["girl"])
item(c, "blouse")["collar"] = "none"
out.append(["collar_seat without a round collar rejected", raises(lambda: V3.validate(c))])
c = copy.deepcopy(blocks["girl"])
item(c, "shorts")["bands"] = {"waist": True, "cuff": False}
item(c, "shorts")["cuff"] = False
out.append(["cuff_gather without cuff bands rejected", raises(lambda: V3.validate(c))])
c = copy.deepcopy(blocks["girl"])
c["generator"] = "garment/2"
out.append(["a garment/2 block is not a garment/3 block", raises(lambda: V3.validate(c))])
RESULT["validate"] = out
'''

HASH = r'''
import hashlib, struct
def digest(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    out = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or not (o.name.startswith("garment.") or o.name.startswith("hand.")):
            continue
        h = hashlib.sha256()
        for v in o.data.vertices:
            h.update(struct.pack("<3f", *v.co))
        h.update(repr([m.name for m in o.data.materials]).encode())
        out[o.name] = h.hexdigest()
    return out, sorted(m.name for m in bpy.data.materials)
RESULT["a"], RESULT["mats_a"] = digest(%r)
RESULT["b"], RESULT["mats_b"] = digest(%r)
'''


PARTS = r'''
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=MASTER)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
out = {"vest": [o.name for o in bpy.data.objects if o.get("ps_garment_item") == "vest"], "cuffs": {}}
collar = bpy.data.objects["garment.blouse.collar"]
h = len(collar.data.vertices) // 2
out["collar_thickness_m"] = sum((collar.data.vertices[i + h].co - collar.data.vertices[i].co).length
                                for i in range(h)) / h
for side in ("L", "R"):
    ring = bpy.data.objects[f"garment.blouse.band.cuff.{side}"]
    cuff = bpy.data.objects[f"garment.blouse.ribcuff.{side}"]
    pts = [cuff.matrix_world @ v.co for v in cuff.data.vertices]
    count = len(pts) // 18  # 2 walls x 9 sections
    row = pts[4 * count:5 * count]  # the outer wall's middle section
    mid = sum(row, Vector((0.0, 0.0, 0.0))) / count
    radii = [(p - mid).length for p in row]
    wales = sum(1 for k in range(count) if radii[k] > radii[k - 1] + 1e-6 and radii[k] >= radii[(k + 1) % count] - 1e-9)
    shoulder = rig.matrix_world @ rig.data.bones[f"DEF-upper_arm.{side}"].head_local
    def centre(o):
        return sum((o.matrix_world @ v.co for v in o.data.vertices), Vector((0.0, 0.0, 0.0))) / len(o.data.vertices)
    names = {g.index: g.name for g in cuff.vertex_groups}
    bones = sorted({names[g.group] for v in cuff.data.vertices for g in v.groups
                    if g.weight > 0.01 and not names[g.group].startswith("ps_")})
    out["cuffs"][side] = {"vertices": len(pts), "part": cuff.get("ps_garment_part"), "wales": wales, "bones": bones,
                          "generator": cuff.get("ps_garment_generator"),
                          "armature": any(m.type == "ARMATURE" for m in cuff.modifiers),
                          "beyond_ring_m": (centre(cuff) - shoulder).length - (centre(ring) - shoulder).length,
                          "mean_radius_m": sum(radii) / count}
RESULT.update(out)
'''


def test_parts(blender, current, fixture):
    r = probe(blender, "MASTER = %r\n" % fixture + PARTS)
    spec = json.load(open(FIXTURE))["override"]["clothing"]
    blouse = next(g for g in spec["garments"] if g["name"] == "blouse")
    print("[test_garments_r3] parts", json.dumps(r))
    check("fixture: no vest; the collar has the configured thickness",
          not r["vest"] and abs(r["collar_thickness_m"] - blouse["collar_seat"]["thickness_m"]) < 2e-4,
          round(r["collar_thickness_m"], 5))
    for side, c in r["cuffs"].items():
        check(f"rib cuff {side}: a garment/3 piece of part rib_cuff, skinned, beyond the sleeve's seam ring",
              c["part"] == "rib_cuff" and c["generator"] == "garment/3" and c["armature"]
              and c["beyond_ring_m"] > 0.003, round(c["beyond_ring_m"], 4))
        check(f"rib cuff {side}: {blouse['rib_cuff']['ribs']} wales round the band",
              c["wales"] == blouse["rib_cuff"]["ribs"], c["wales"])
        check(f"rib cuff {side}: carried by arm bones only", c["bones"]
              and all(b.startswith(("DEF-forearm", "DEF-hand", "DEF-upper_arm")) for b in c["bones"]), c["bones"])
    m = measure(blender, "girl", current, fixture)
    cur, new = m["current"], m["candidate"]
    check("fixture: the collar on its own bodice is chest-carried and lies closer than the current one (p95 < 1.6 cm)",
          new["collar_bones"] == ["DEF-shoulder.L", "DEF-shoulder.R", "DEF-spine.003"]
          and new["poses"]["rest"]["stand_off_m"]["p95"] < min(0.016, cur["poses"]["rest"]["stand_off_m"]["p95"]),
          (cur["poses"]["rest"]["stand_off_m"]["p95"], new["poses"]["rest"]["stand_off_m"]["p95"]))


def measure(blender, which, current, candidate):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "m.json")
        run_blender(blender, os.path.join(T119, "measure.py"), [out, which, f"current={current}", f"candidate={candidate}"])
        return json.load(open(out))["columns"]


def test_girl(blender, current, candidate):
    m = measure(blender, "girl", current, candidate)
    cur, new = m["current"], m["candidate"]
    print("[test_garments_r3] girl", json.dumps(m))
    check("the seated collar is carried by the chest and the shoulders only",
          new["collar_bones"] == ["DEF-shoulder.L", "DEF-shoulder.R", "DEF-spine.003"], new["collar_bones"])
    check("the current collar carries head or arm weight (what the seat removes)",
          any(b.startswith(("DEF-upper_arm", "DEF-spine.006")) for b in cur["collar_bones"]))
    for name in ("rest", "half_reach", "full_reach"):
        a, b = cur["poses"][name]["stand_off_m"], new["poses"][name]["stand_off_m"]
        check(f"{name}: the collar stands off the layers under it less than the current one (p95) and under 3 cm",
              b["p95"] < a["p95"] and b["p95"] < 0.03, (a["p95"], b["p95"]))
    for name in ("half_reach", "full_reach"):
        a, b = cur["poses"][name]["moved_from_rest_max_m"], new["poses"][name]["moved_from_rest_max_m"]
        check(f"{name}: the collar stays within 3 cm of its rest place (the current one is carried further)",
              b < 0.03 and b < a, (a, b))
    check("the two cuff bands do not overlap (the current ones do)",
          new["bloomers"]["band_gap_m"] >= -1e-4 and cur["bloomers"]["band_gap_m"] < -0.01,
          (cur["bloomers"]["band_gap_m"], new["bloomers"]["band_gap_m"]))
    check("the shell does not hang below the cuff bands (the current one does)",
          new["bloomers"]["shell_below_bands_m"] < 0.003 and cur["bloomers"]["shell_below_bands_m"] > 0.01,
          (cur["bloomers"]["shell_below_bands_m"], new["bloomers"]["shell_below_bands_m"]))


def test_boy(blender, current, candidate):
    m = measure(blender, "boy", current, candidate)
    cur, new = m["current"], m["candidate"]
    print("[test_garments_r3] boy", json.dumps(m))
    for name in ("rest", "toes_up", "toes_down"):
        a, b = cur["poses"][name]["uncovered_skin_cm2"], new["poses"][name]["uncovered_skin_cm2"]
        check(f"{name}: no uncovered skin round the ankle (the current build leaves some)", b < 0.5 and a > 5.0, (a, b))
    check("the candidate hands use skin-felt-limbs/3 on their own material, the current hands skin-felt/3",
          new["hand_preset"] == "skin-felt-limbs/3" and new["hand_material"] == "M_skin_limbs"
          and cur["hand_preset"] == "skin-felt/3" and cur["hand_material"] == "M_skin",
          (cur["hand_preset"], new["hand_preset"]))


def test_default(blender, who, built):
    cid, version = CAST[who]
    published = os.path.join(CH, cid, "versions", version, f"{cid}_master.blend")
    r = probe(blender, HASH % (published, built))
    diff = sorted(k for k in set(r["a"]) | set(r["b"]) if r["a"].get(k) != r["b"].get(k))
    check(f"{who}: a default build has every garment piece and hand identical to the published {version} master",
          not diff and len(r["a"]) > 20, (len(r["a"]), diff[:6]))
    check(f"{who}: a default build has the published material names (no limb material)",
          r["mats_a"] == r["mats_b"] and "M_skin_limbs" not in r["mats_b"])


T126 = os.path.join(ROOT, "docs", "evaluation", "characters", "T-126", "dress")
T126_OVERRIDE = os.path.join(T126, "girl_white_hair_blue_dress.dress.override.json")
T126_BASE = os.path.join(ROOT, "docs", "evaluation", "characters", "T-070", "candidates", "third.base.spec.json")
T126_FIELDS = ("fibre_uv", "skirt_pattern", "cloth_sim", "sole_stitch")
T126_VALIDATE = r'''
import copy
import garments_v3 as V3
from garments_v3 import pattern
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
out = []
block = json.load(open(%r))["override"]["clothing"]
out.append(["T-126: the dress override block validates", V3.validate(copy.deepcopy(block)) is not None])
view = V3.v2_view(block)
out.append(["T-126: its garment/2 view has no tights item and no garment/3 field",
            not any(g["type"] == "tights" for g in view["garments"])
            and not any(f in g for g in view["garments"] for f in %r) and len(view["garments"]) == 2])
def item(c, name):
    return next(g for g in c["garments"] if g["name"] == name)
def bad(name, field, value, label):
    c = copy.deepcopy(block)
    g = item(c, name)
    g[field] = dict(g.get(field) or {}, **value) if isinstance(value, dict) and isinstance(g.get(field), dict) else value
    out.append(["T-126: " + label + " rejected", raises(lambda: V3.validate(c))])
bad("dress", "skirt_pattern", {"panels": 0}, "skirt_pattern.panels 0")
bad("dress", "skirt_pattern", {"relief_m": 0.5}, "skirt_pattern.relief_m 0.5")
bad("dress", "skirt_pattern", {"lace": 1}, "skirt_pattern unknown key")
bad("boots", "skirt_pattern", {"panels": 8}, "skirt_pattern on boots")
bad("dress", "fibre_uv", {"swap": 1}, "fibre_uv.swap 1")
bad("dress", "fibre_uv", "yes", "fibre_uv as text")
bad("dress", "cloth_sim", {"pin_top": 2.0}, "cloth_sim.pin_top 2")
bad("boots", "cloth_sim", {"pin_top": 0.1}, "cloth_sim on boots")
bad("boots", "sole_stitch", {"pitch_m": 0.0}, "sole_stitch.pitch_m 0")
bad("dress", "sole_stitch", {"pitch_m": 0.01}, "sole_stitch on a dress")
bad("tights", "length", 0.5, "tights unknown field")
bad("tights", "ease_m", 0.5, "tights.ease_m 0.5")
bad("tights", "collar_seat", {}, "collar_seat on tights")
c = copy.deepcopy(block)
item(c, "boots").pop("sole")
out.append(["T-126: sole_stitch without a sole rejected", raises(lambda: V3.validate(c))])
c = copy.deepcopy(block)
c["garments"].append(copy.deepcopy(item(c, "tights")))
out.append(["T-126: two tights items of one name rejected", raises(lambda: V3.validate(c))])
st = dict(pattern.PATTERN)
hs = [pattern.height(u / 97.0, v / 89.0, st) for u in range(97) for v in range(90)]
out.append(["T-126: the skirt pattern height stays in 0..1 and uses the range", min(hs) >= 0.0 and 0.9 < max(hs) <= 1.0])
out.append(["T-126: a panel without leaves and cable is flat",
            max(pattern.height(u / 50.0, 0.3, dict(st, cable_share=0.0, leaf_rows=0)) for u in range(50)) == 0.0])
RESULT["validate"] = out
'''
T126_PROBE = r'''
import json
bpy.ops.wm.open_mainfile(filepath=%r)
obs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.")}
body = bpy.data.objects["body_skin"]
skirt, tights = obs["garment.dress.skirt"], obs["garment.tights.main"]
pin = [d.value for d in skirt.data.attributes["ps_cloth_pin"].data]
zs = [v.co.z for v in skirt.data.vertices]
z0, z1 = min(zs), max(zs)
RESULT["r"] = {
    "tights_parts": sorted(n for n in obs if n.startswith("garment.tights.") and not n.endswith(".fibres")),
    "tights_body_attr": "ps_body_vertex" in tights.data.attributes, "tights_verts": len(tights.data.vertices),
    "tights_z": [min(v.co.z for v in tights.data.vertices), max(v.co.z for v in tights.data.vertices)],
    "masked": list(body.get("ps_garment_mask_items", [])),
    "skirt_verts": len(skirt.data.vertices), "sim": json.loads(skirt.get("ps_cloth_sim", "null")),
    "pin_top": min(z for z, p in zip(zs, pin) if p >= 0.999) > z0 + 0.9 * (z1 - z0),
    "pin_free": sum(1 for p in pin if p == 0.0) / len(pin),
    "uv": sorted(n for n, o in obs.items() if o.type == "MESH" and o.get("ps_garment_item") == "dress"
                 and "ps_fibre" not in o.data.uv_layers),
    "stitch": {n: len(o.data.vertices) for n, o in obs.items() if ".stitch." in n and o.type == "MESH"},
    "generator": sorted({o.get("ps_garment_generator") for o in obs.values() if o.get("ps_garment_generator")}),
}
'''


def test_t126_plain():
    ovr = json.load(open(T126_OVERRIDE))["override"]
    types = [g["type"] for g in ovr["clothing"]["garments"]]
    check("T-126: the dress override pins garment/3 and holds tights, dress and boots",
          ovr["generators"] == {"garment": "garment/3"} and ovr["clothing"]["generator"] == "garment/3"
          and types == ["tights", "dress", "boots"], types)
    dress = next(g for g in ovr["clothing"]["garments"] if g["type"] == "dress")
    check("T-126: the dress reuses the T-119 components (collar_seat on a round collar, rib_cuff)",
          dress["collar"]["type"] == "round" and dress["collar_seat"]["over"] == [] and dress["rib_cuff"]["ribs"] > 0)
    named = []
    for folder in ("garments_v3", "cloth_sim"):
        for f in sorted(os.listdir(os.path.join(CHARSYS, folder))):
            if f.endswith(".py"):
                text = open(os.path.join(CHARSYS, folder, f)).read()
                named += [f"{folder}/{f}" for w in ("girl_", "boy_", "white_hair", "auburn", "hoodie_yellow") if w in text]
    check("T-126: garments_v3/ and cloth_sim/ name no character", not named, named)


def test_t126_build(blender, master):
    r = probe(blender, T126_PROBE % master)["r"]
    print("[test_garments_r3] t126", json.dumps(r))
    check("T-126: the tights are one skin-following piece from the feet to the waist, masked like other items",
          r["tights_parts"] == ["garment.tights.main"] and r["tights_body_attr"] and r["tights_verts"] > 1000
          and r["tights_z"][0] < 0.02 and r["tights_z"][1] > 0.3 and "tights" in r["masked"], r["tights_z"])
    check("T-126: the skirt is refined for the pattern and tagged for the cloth simulation, pinned at the waist only",
          r["skirt_verts"] > 20000 and isinstance(r["sim"], dict) and r["pin_top"] and r["pin_free"] > 0.8,
          (r["skirt_verts"], r["sim"], round(r["pin_free"], 3)))
    check("T-126: every dress piece carries the ps_fibre UV map", r["uv"] == [], r["uv"])
    check("T-126: each boot has its sole stitches", sorted(r["stitch"]) == ["garment.boots.stitch.L",
                                                                           "garment.boots.stitch.R"]
          and all(n >= 48 for n in r["stitch"].values()), r["stitch"])
    check("T-126: every piece is tagged garment/3", r["generator"] == ["garment/3"], r["generator"])


def build_t126(blender):
    out = tempfile.mkdtemp(prefix="t126_")
    run_blender(blender, os.path.join(CHARSYS, "build_character.py"),
                ["--spec", T126_BASE, "--out", out, "--no-glb", "--no-compare", "--override", T126_OVERRIDE])
    return os.path.join(out, "girl_white_hair_blue_dress_master.blend")


def main():
    blender = arg("--blender")
    test_plain()
    test_t126_plain()
    if blender:
        for name, ok in probe(blender, T126_VALIDATE % (T126_OVERRIDE, V3_FIELDS + T126_FIELDS))["validate"]:
            check(name, ok)
        if "--quick" not in sys.argv:
            test_t126_build(blender, arg("--t126-master") or build_t126(blender))
    if blender:
        triples = [(who, override_path(who), spec_path(who)) for who in ("girl", "boy")]
        for name, ok in probe(blender, VALIDATE % (triples, V3_FIELDS, FIXTURE))["validate"]:
            check(name, ok)
        if "--quick" not in sys.argv:
            masters = {}
            for who in ("girl", "boy"):
                masters[who] = (arg(f"--{who}-current") or build(blender, who, []),
                                arg(f"--{who}-master") or build(blender, who, [override_path(who)]))
            test_girl(blender, *masters["girl"])
            test_boy(blender, *masters["boy"])
            for who in ("girl", "boy"):
                test_default(blender, who, arg(f"--{who}-default") or masters[who][0])
            test_parts(blender, masters["girl"][0], arg("--girl-components") or build(blender, "girl", [FIXTURE]))
    else:
        print("[test_garments_r3] SKIP Blender checks (no --blender)")
    print(f"[test_garments_r3] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
