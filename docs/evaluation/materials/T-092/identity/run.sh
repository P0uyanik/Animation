set -e
export PATH=/home/user/bin:$PATH
eval "$(cd /home/user/Animation/pipeline/charsys && python3 -c "import determinism;[print(f\"export {k}={v}\") for k,v in determinism.ENVIRONMENT.items()]")"
S=/tmp/claude-0/-home-user-Animation/62df57c7-2a76-5d85-bea8-8636d6c8cd34/scratchpad/ident
for side in input branch; do
  if [ $side = input ]; then R=/home/user/input_4910b69; else R=/home/user/Animation; fi
  for c in boy_yellow_hoodie:boy_yellow_hoodie.2.0.0 girl_auburn_bun_glasses:girl_auburn_bun_glasses.0.11.0; do
    cid=${c%%:*}; f=${c##*:}; o=$S/$side/$cid; mkdir -p $o
    t0=$(date +%s)
    (cd $R && blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/$cid/spec/$f.spec.json --out $o --no-glb --no-compare > $o/build.log 2>&1)
    echo "$side $cid built in $(( $(date +%s)-t0 ))s"
  done
done
for side in input branch; do for cid in boy_yellow_hoodie girl_auburn_bun_glasses; do
  for b in $S/$side/$cid/*.blend; do n=$(basename $b .blend)
    blender -b --factory-startup -P /home/user/Animation/pipeline/charsys/fingerprint_v2.py -- $b $S/$side/$cid/$n.fp.json > /dev/null 2>&1
    blender -b --factory-startup -P $S/graphs.py -- $b $S/$side/$cid/$n.graphs.json > /dev/null 2>&1
  done; done; done
python3 - <<'PY'
import json,glob,os
S="/tmp/claude-0/-home-user-Animation/62df57c7-2a76-5d85-bea8-8636d6c8cd34/scratchpad/ident"
for f in sorted(glob.glob(S+"/input/*/*.json")):
    if not (f.endswith(".fp.json") or f.endswith(".graphs.json")): continue
    g=f.replace("/input/","/branch/"); a=json.load(open(f)); b=json.load(open(g)); a.pop("file",None); b.pop("file",None)
    print("IDENTICAL" if a==b else "DIFFERENT", os.path.relpath(f,S+"/input"))
PY
