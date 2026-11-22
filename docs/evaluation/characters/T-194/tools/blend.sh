# blend.sh <shotdir> <run> <out> <frames> [pushout-arg]
cd /home/user/Animation
SD=$1; R=$SD/build/runs/$2
args=(--bake $R/bake.json --cast $SD/build/cast.json --out $3 --frames $4 --blend-only --resolution 640 360 --samples 16)
[ -n "$5" ] && args+=(--hair-pushout "$5")
blender -b --factory-startup -P pipeline/charsys/shot_render.py -- "${args[@]}" > $3.log 2>&1; echo "exit $? $3"
