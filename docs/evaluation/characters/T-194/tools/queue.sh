# per item: blend then measure (step 2); candidate first; 3 at a time
cd /tmp/claude-0/s
M=/home/user/Animation/docs/evaluation/characters/T-194/tools/measure_eval.py
cat full/jobs2.txt | xargs -P 3 -L 1 bash -c 'O=/tmp/claude-0/s/full/$0_$4; [ -f $O/shot.blend ] || bash /tmp/claude-0/s/blend.sh $1 $2 $O $3 $([ $4 = on ] && echo on); [ -f $O.m.json ] || blender -b --factory-startup -P '$M' -- $O/shot.blend $O.m.json --step=2 > $O.m.log 2>&1; echo "done $0_$4 $(date +%H:%M)"'
echo ALL_DONE
