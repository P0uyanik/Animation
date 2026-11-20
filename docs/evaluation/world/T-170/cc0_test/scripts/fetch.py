"""T-170c throwaway: download CC0 candidates at 1K into a scratch folder OUTSIDE the repo and record URL, SHA-256, size.

python3 fetch.py --out <scratch> --ph id,id --acg id,id [--hdri id,id] [--maps diff|all]
Poly Haven: api.polyhaven.com/files/<id> -> 1k JPG diff / rough / nor_gl (HDRI: 1k .hdr). ambientCG: <id>_1K-JPG.zip.
Appends to <scratch>/manifest.json: {file: {source, asset, url, sha256, bytes, license}}. Nothing is written in the repo.
"""
import argparse, hashlib, io, json, os, urllib.request, zipfile

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True)
for a in ("--ph", "--acg", "--hdri"):
    ap.add_argument(a, default="")
ap.add_argument("--maps", default="diff"); A = ap.parse_args()
MAN = os.path.join(A.out, "manifest.json"); M = json.load(open(MAN)) if os.path.exists(MAN) else {}
UA = {"User-Agent": "cc0-swatch-test/1.0"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()

def put(rel, data, **meta):
    p = os.path.join(A.out, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
    M[rel] = dict(meta, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), license="CC0 1.0")

PH = {"diff": "Diffuse", "rough": "Rough", "nor_gl": "nor_gl"}
for a in filter(None, A.ph.split(",")):
    f = json.loads(get("https://api.polyhaven.com/files/" + a))
    for short, key in PH.items():
        rel = "ph_%s/%s.jpg" % (a, short)
        if (A.maps == "diff" and short != "diff") or rel in M or key not in f:
            continue
        u = f[key]["1k"]["jpg"]["url"]; put(rel, get(u), source="polyhaven", asset=a, url=u)
for a in filter(None, A.hdri.split(",")):
    rel = "hdri_%s/%s_1k.hdr" % (a, a)
    if rel not in M:
        u = json.loads(get("https://api.polyhaven.com/files/" + a))["hdri"]["1k"]["hdr"]["url"]; put(rel, get(u), source="polyhaven", asset=a, url=u)
ACG = {"diff": "_Color.jpg", "rough": "_Roughness.jpg", "nor_gl": "_NormalGL.jpg"}
for a in filter(None, A.acg.split(",")):
    if "acg_%s/diff.jpg" % a in M and (A.maps == "diff" or "acg_%s/nor_gl.jpg" % a in M):
        continue
    u = "https://ambientcg.com/get?file=%s_1K-JPG.zip" % a
    try:
        z = get(u)
    except Exception as e:  # 2026-11-20: redirect to acg-download.struffelproductions.com is refused by the proxy
        print("SKIP", a, e); continue
    zs = hashlib.sha256(z).hexdigest()
    zf = zipfile.ZipFile(io.BytesIO(z))
    for short, suf in ACG.items():
        n = [x for x in zf.namelist() if x.endswith(suf)]
        if n and not (A.maps == "diff" and short != "diff"):
            put("acg_%s/%s.jpg" % (a, short), zf.read(n[0]), source="ambientcg", asset=a, url=u, zip_sha256=zs, zip_bytes=len(z))
json.dump(M, open(MAN, "w"), indent=1, sort_keys=True); print(len(M), "files in manifest")
