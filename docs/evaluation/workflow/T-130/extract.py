#!/usr/bin/env python3
"""T-130 extraction: existing data only. Usage: python extract.py (run in repo root, needs git + gh auth)."""
import json, subprocess, re, os, sys
OUT = os.path.dirname(os.path.abspath(__file__))
REPO = "p0uyanik/animation"
def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout
# 1. ledger lines on every remote ref (existing docs only)
refs = [r for r in sh("git","for-each-ref","--format=%(refname:short)","refs/remotes/origin").split() if "HEAD" not in r]
seen = {}
for ref in refs:
    for l in sh("git","grep","-n","-E",r"ledger: *build [0-9]",ref,"--","docs").splitlines():
        m = re.match(r"[^:]+:([^:]+):(\d+):(.*)", l)
        if not m or "READY ends" in l: continue
        f, ln, txt = m.groups()
        if re.search(r"build N", txt): continue
        key = (f, txt.strip())
        if key in seen: continue
        c = sh("git","log","-1","--format=%cI",ref,"--",f).strip()
        seen[key] = dict(file=f, ref=ref, line=txt.strip(), file_last_commit=c)
json.dump(list(seen.values()), open(f"{OUT}/ledger_lines.json","w"), indent=1)
# 2. workflow runs since 2026-11-18
runs = []
for p in range(1, 20):
    d = json.loads(sh("gh","api",f"repos/{REPO}/actions/runs?per_page=100&page={p}&created=>=2026-11-18"))
    rs = d.get("workflow_runs", [])
    if not rs: break
    runs += [dict(id=r["id"], name=r["name"], branch=r["head_branch"], sha=r["head_sha"][:7], event=r["event"],
                  status=r["status"], conclusion=r["conclusion"], attempt=r["run_attempt"],
                  created=r["created_at"], started=r["run_started_at"], updated=r["updated_at"]) for r in rs]
json.dump(runs, open(f"{OUT}/runs.json","w"), indent=1)
# 3. relay log + task log copies
open(f"{OUT}/RELAY_LOG.copy.md","w").write(sh("git","show","origin/relay-channel:RELAY_LOG.md"))
print(len(seen), "ledger lines;", len(runs), "runs")
