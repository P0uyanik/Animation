# full real-shot runs: blends (off/on) then measures, 3 at a time
cd /tmp/claude-0/s; mkdir -p full
A=docs/evaluation/characters/T-194/shots; W=/home/user/t183wt/episodes
jobs=()
for x in "e912_s010 $A/e912/s010 rel2" "e912_s020 $A/e912/s020 rel2" "e912_s030 $A/e912/s030 rel2" "e909_s010 $A/e909/s010 rel2" \
         "e912_s010c $W/e912_paper_boat/shots/s010_t183 cand1" "e912_s020c $W/e912_paper_boat/shots/s020_t183 cand1" \
         "e912_s030c $W/e912_paper_boat/shots/s030_t183 cand1" "e909_s010c $W/e909_two_char_acting/shots/s010_t183 cand1"; do
  set -- $x; fr=$(python3 -c "import json,sys;d=json.load(open('/home/user/Animation/$2/shot.scene.json' if not '$2'.startswith('/') else '$2/shot.scene.json'));print(f\"{d['frameStart']}-{d['frameEnd']}\")")
  echo "$1 $2 $3 $fr off" >> full/jobs.txt; echo "$1 $2 $3 $fr on" >> full/jobs.txt
done
cat full/jobs.txt | xargs -P 3 -L 1 bash -c 'O=/tmp/claude-0/s/full/$0_$4; [ -f $O/shot.blend ] || bash /tmp/claude-0/s/blend.sh $1 $2 $O $3 $([ $4 = on ] && echo on)'
echo BLENDS_DONE
M=/home/user/Animation/docs/evaluation/characters/T-194/tools/measure_eval.py
ls -d full/*_o* | grep -v log | xargs -P 3 -I{} bash -c '[ -f {}.m.json ] || blender -b --factory-startup -P '$M' -- {}/shot.blend {}.m.json --step=2 > {}.m.log 2>&1; echo measured {}'
echo MEASURES_DONE
