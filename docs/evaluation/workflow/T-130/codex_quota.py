#!/usr/bin/env python3
"""Codex quota stops from RELAY_LOG.copy.md: stop time -> reset time (as the relay line states it, '=> ...Z')."""
import re, json
from datetime import datetime as D
rows=[]
for l in open('RELAY_LOG.copy.md'):
    if '| CODEX | QUOTA' not in l: continue
    t=D.strptime(l[:17],'%Y-%m-%dT%H:%MZ')
    m=re.search(r'=> (?:05:30 local \(CET\) = )?(\d{4}-\d\d-\d\dT\d\d:\d\d)Z',l)
    m2=re.search(r'=> (\d\d:\d\d)Z',l)
    r=None
    if m: r=D.strptime(m.group(1),'%Y-%m-%dT%H:%M')
    elif m2: r=D.strptime(f"{t:%Y-%m-%d}T{m2.group(1)}",'%Y-%m-%dT%H:%M')
    rows.append(dict(stop=t.isoformat(),reset=r.isoformat() if r else None,hours=round((r-t).total_seconds()/3600,1) if r else None))
json.dump(rows,open('codex_quota.json','w'),indent=1)
print(len(rows),'stops;',sum(1 for x in rows if x['hours'] is not None),'with reset; hours',round(sum(x['hours'] or 0 for x in rows),1))
for x in rows: print(x)
