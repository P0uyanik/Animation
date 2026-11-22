"""T-189 throwaway: download Poly Haven MODELS (1k glTF + its include files) into a scratch folder OUTSIDE the repo.

python3 -I fetch_ph_models.py --out <scratch> --ids a,b,c [--res 1k]
Uses api.polyhaven.com/files/<id> -> gltf/<res>. Appends {file: {asset,url,sha256,bytes,license}} to <out>/manifest.json.
"""
import argparse, hashlib, json, os, urllib.request

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--ids", required=True)
ap.add_argument("--res", default="1k"); A = ap.parse_args()
MAN = os.path.join(A.out, "manifest.json"); M = json.load(open(MAN)) if os.path.exists(MAN) else {}
UA = {"User-Agent": "cc0-model-test/1.0"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()

def put(rel, url):
    p = os.path.join(A.out, rel)
    if rel in M and os.path.exists(p):
        return
    data = get(url); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
    M[rel] = dict(url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), license="CC0 1.0", source="polyhaven")

for a in A.ids.split(","):
    f = json.loads(get("https://api.polyhaven.com/files/" + a))
    g = f["gltf"][A.res]["gltf"]
    put("%s/%s" % (a, os.path.basename(g["url"])), g["url"])
    for rel, inc in g.get("include", {}).items():
        put("%s/%s" % (a, rel), inc["url"])
    print(a, "ok", sum(v["bytes"] for k, v in M.items() if k.startswith(a + "/")), "bytes")
json.dump(M, open(MAN, "w"), indent=1, sort_keys=True); print(len(M), "files in manifest")
