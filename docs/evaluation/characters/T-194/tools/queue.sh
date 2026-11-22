# per item: blend then measure (step 2); 3 workers, at most 2 measures at a time (3 OOM)
cd /tmp/claude-0/s
while pgrep -f "full/e912_s020c_o" >/dev/null; do sleep 30; done
cat full/jobs4.txt | xargs -P 3 -L 1 bash -c 'O=/tmp/claude-0/s/full/$0_$4; [ -f $O/shot.blend ] || bash /tmp/claude-0/s/blend.sh $1 $2 $O $3 $([ $4 = on ] && echo on); if [ ! -f $O.m.json ]; then until flock -n /tmp/claude-0/s/m1.lock -c "blender -b --factory-startup -P /home/user/Animation/docs/evaluation/characters/T-194/tools/measure_eval.py -- $O/shot.blend $O.m.json --step=2 > $O.m.log 2>&1" || [ -f $O.m.json ] || flock -n /tmp/claude-0/s/m2.lock -c "blender -b --factory-startup -P /home/user/Animation/docs/evaluation/characters/T-194/tools/measure_eval.py -- $O/shot.blend $O.m.json --step=2 > $O.m.log 2>&1" || [ -f $O.m.json ]; do sleep 30; done; fi; echo "done $0_$4 $(date +%H:%M)"'
echo ALL_DONE
