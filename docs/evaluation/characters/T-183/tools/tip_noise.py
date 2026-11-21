"""Tip noise: frame-to-frame zigzag of each chain tip relative to the dynamics-off pose.
zigzag at frame f = min(|d1|,|d2|) when d1.d2<0, d1 = e[f]-e[f-1], d2 = e[f+1]-e[f], e = tip - static tip (mm)."""
import sys, json, numpy as np
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', 'tools', 'motion_checks'))
import shot as S
dyn,sta=S.Shot(sys.argv[1]),S.Shot(sys.argv[2])
cd=next(c for c in dyn.characters if c.name=='girl'); cs=next(c for c in sta.characters if c.name=='girl')
idx={b:i for i,b in enumerate(cd.bones)}
def carried(c,bone,p):
    M=c.M[:,idx[bone]]; return np.einsum('fij,j->fi',M[:,:3,:3],p)+M[:,:3,3]
hp=carried(cs,'head',np.array([b['head'] for b in cd.doc['skeleton'] if b['name']=='head'][0])+np.array([0,0.15,-0.1]))*1000
ha=np.linalg.norm(hp[2:]-2*hp[1:-1]+hp[:-2],axis=1)   # head acceleration per frame^2 (mm) at frames 1..F-2
calm=np.convolve(ha<0.6,np.ones(3),'same')>=3        # three calm frames in a row
rows=[]
for ch in cd.doc['dynamics']['chains']:
    tip=np.array(ch['tip']); last=ch['bones'][-1]
    e=(carried(cd,last,tip)-carried(cs,last,tip))*1000
    d=np.diff(e,axis=0); dot=(d[:-1]*d[1:]).sum(1); mn=np.minimum(np.linalg.norm(d[:-1],axis=1),np.linalg.norm(d[1:],axis=1))
    z=np.where(dot<0,mn,0)
    zc=z*calm
    rows.append((ch['name'],z.max(),int((z>1).sum()),int(dyn.frames[1+z.argmax()]),np.linalg.norm(e,axis=1).max(),np.linalg.norm(d,axis=1).max(),zc.max(),int((zc>0.5).sum()),int(dyn.frames[1+zc.argmax()])))
rows.sort(key=lambda r:-r[1])
print('tip zigzag (mm): worst chains:', [(r[0],round(float(r[1]),2),r[2],r[3]) for r in rows[:4]])
rc=sorted(rows,key=lambda r:-r[6]); print('  calm frames (%d of %d): worst'%(int(calm.sum()),len(calm)), [(r[0],round(float(r[6]),2),r[7],r[8]) for r in rc[:4]], 'total frames>0.5mm', sum(r[7] for r in rows))
print('  all chains: max zigzag %.2f mm, frames>1mm total %d; max tip offset from static %.0f mm; max tip step/frame %.1f mm'%(max(r[1] for r in rows),sum(r[2] for r in rows),max(r[4] for r in rows),max(r[5] for r in rows)))
