import sys, json, numpy as np
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', 'tools', 'motion_checks'))
import shot as S
out=sys.argv[1]; chains=sys.argv[2].split(','); fr=[int(x) for x in sys.argv[3].split('-')]
dyn,sta=S.Shot(out+'/bake.json'),S.Shot(out+'/bake_static.json')
cd=next(c for c in dyn.characters if c.name=='girl'); cs=next(c for c in sta.characters if c.name=='girl')
idx={b:i for i,b in enumerate(cd.bones)}
def carried(c,bone,p):
    M=c.M[:,idx[bone]]; return np.einsum('fij,j->fi',M[:,:3,:3],p)+M[:,:3,3]
hd={b['name']:np.array(b['head']) for b in cd.doc['skeleton']}
for ch in cd.doc['dynamics']['chains']:
    if ch['name'] not in chains: continue
    print(ch['name'])
    pts=[(b,hd[b]) for b in ch['bones']]+[(ch['bones'][-1],np.array(ch['tip']))]
    X=np.stack([carried(cd,b,p) for b,p in pts],1)*1000; Xs=np.stack([carried(cs,b,p) for b,p in pts],1)*1000
    for f in range(fr[0]-1,fr[1]):
        e=X[f]-Xs[f]
        print(f"  f{f+1:3d} "+" | ".join(f"{e[k,0]:6.1f},{e[k,1]:6.1f},{e[k,2]:6.1f}" for k in range(1,len(pts))))
