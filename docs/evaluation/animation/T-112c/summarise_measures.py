"""T-112c evidence: summarises two measure_t051 runs (docs/evaluation/animation/T-051/measure_t051.cpp) of e907
s010_verbs per held hand: all hold frames, and closed (from contact + 4 f). "single" = the second run (fingers false).

    python3 docs/evaluation/animation/T-112c/summarise_measures.py measure_s010_verbs.json measure_s010_verbs_fingers_false.json
"""
import json,math,sys
a=json.load(open(sys.argv[1]))['frames']; b=json.load(open(sys.argv[2]))['frames']
for hand in ('boy.R','girl.L'):
  A=[x for x in a if x['hand']==hand]; B={x['frame']:x for x in b if x['hand']==hand}
  for lab,sel in (('all',A),('closed',[x for x in A if x['frame']>=A[0]['frame']+4])):
    w=max(x['tip_gap_mm'] for x in sel); d=min(x['deepest_mm'] for x in sel); bo=max(x['band_out_mm'] for x in sel); th=max(x['thumb_side_mm'] for x in sel)
    dw=max(math.dist(x['wrist'],B[x['frame']]['wrist']) for x in sel)*1e3; dp=max(math.dist(x['palm'],B[x['frame']]['palm']) for x in sel)*1e3
    wb=max(B[x['frame']]['tip_gap_mm'] for x in sel); db=min(B[x['frame']]['deepest_mm'] for x in sel); bb=max(B[x['frame']]['band_out_mm'] for x in sel); tb=max(B[x['frame']]['thumb_side_mm'] for x in sel)
    print(hand,lab,f"f{sel[0]['frame']}-{sel[-1]['frame']} gap {w:.2f} deepest {d:.2f} bandout {bo:.2f} thumb {th:.1f} | single gap {wb:.2f} deepest {db:.2f} bandout {bb:.2f} thumb {tb:.1f} | dwrist {dw:.6f} dpalm {dp:.6f} skin {sel[0]['skin_radius_mm']}")
