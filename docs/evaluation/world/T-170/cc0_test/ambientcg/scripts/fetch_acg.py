"""T-170d throwaway: download ambientCG 1K-JPG sets into a scratch folder OUTSIDE the repo; record URL, SHA-256, size.

python3 fetch_acg.py --out <scratch> --acg Carpet016,Fabric030 [--hdri lebombo]
<scratch>/acg_<id>/{diff,rough,nor_gl}.jpg (+ zip hash); <scratch>/manifest.json. Nothing is written in the repo.
"""
import argparse, hashlib, io, json, os, urllib.request, zipfile

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--acg", default=""); ap.add_argument("--hdri", default="")
A = ap.parse_args(); MAN = os.path.join(A.out, "manifest.json"); M = json.load(open(MAN)) if os.path.exists(MAN) else {}
UA = {"User-Agent": "cc0-swatch-test/1.0"}

def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180); return r.read(), r.geturl()

def put(rel, data, **meta):
    p = os.path.join(A.out, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
    M[rel] = dict(meta, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), license="CC0 1.0")

ACG = {"diff": "_Color.jpg", "rough": "_Roughness.jpg", "nor_gl": "_NormalGL.jpg"}
for a in filter(None, A.acg.split(",")):
    if "acg_%s/diff.jpg" % a in M:
        continue
    u = "https://ambientcg.com/get?file=%s_1K-JPG.zip" % a
    try:
        z, final = get(u)
    except Exception as e:
        print("SKIP", a, e); continue
    zf = zipfile.ZipFile(io.BytesIO(z)); zs = hashlib.sha256(z).hexdigest()
    for short, suf in ACG.items():
        n = [x for x in zf.namelist() if x.endswith(suf)]
        if n:
            put("acg_%s/%s.jpg" % (a, short), zf.read(n[0]), source="ambientcg", asset=a, url=u, resolved_url=final, zip_member=n[0],
                zip_sha256=zs, zip_bytes=len(z))
    print(a, len(z), sorted(zf.namelist()))
for a in filter(None, A.hdri.split(",")):
    rel = "hdri_%s/%s_1k.hdr" % (a, a)
    if rel not in M:
        u = json.loads(get("https://api.polyhaven.com/files/" + a)[0])["hdri"]["1k"]["hdr"]["url"]; put(rel, get(u)[0], source="polyhaven", asset=a, url=u)
json.dump(M, open(MAN, "w"), indent=1, sort_keys=True); print(len(M), "files in manifest")
