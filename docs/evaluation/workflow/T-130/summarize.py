#!/usr/bin/env python3
"""Summarise runs.json (from extract.py) for WORKFLOW_EVAL_R4.md. T-127 cutover = 2026-11-19T15:44Z (merge into integration/t-126)."""
import json, statistics as st
from datetime import datetime as D
R=json.load(open('runs.json')); CUT='2026-11-19T15:44:00Z'
p=lambda s:D.fromisoformat(s.replace('Z','+00:00'))
G=[r for r in R if r['name']=='Quality gate']
def mins(r): return (p(r['updated'])-p(r['started'] or r['created'])).total_seconds()/60
out={}
for lab,sel in (('before',lambda r:r['created']<CUT),('after',lambda r:r['created']>=CUT)):
    g=[r for r in G if sel(r)]
    fin=[mins(r) for r in g if r['conclusion'] in('success','failure')]
    ok=[mins(r) for r in g if r['conclusion']=='success']
    out[lab]=dict(n_runs=len(g),cancelled=sum(r['conclusion']=='cancelled' for r in g),success=len(ok),failure=sum(r['conclusion']=='failure' for r in g),
      reruns_attempt_gt1=sum(r['attempt']>1 for r in g),
      median_wall_all_finished=round(st.median(fin),1) if fin else None,median_wall_success=round(st.median(ok),1) if ok else None,
      n_success_timed=len(ok), first=min((r['created'] for r in g),default=None), last=max((r['created'] for r in g),default=None))
print(json.dumps(out,indent=1))
json.dump(out,open('ci_summary.json','w'),indent=1)
