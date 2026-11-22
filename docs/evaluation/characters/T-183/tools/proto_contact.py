"""Prototype harness: modify the girl's package dynamics block (colliders, chain contact), bake, measure, noise.
usage: proto.py <name> [key=value ...]"""
import sys, os, json, shutil, subprocess, glob
import numpy as np
SP=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(SP,'..','..','..','..','..'))
sys.path.insert(0, ROOT+'/pipeline/charsys'); sys.path.insert(0, ROOT+'/tools/motion_checks')
import groom_contact as C
import shot as S
name=sys.argv[1]; kv=dict(a.split('=',1) for a in sys.argv[2:])
G=lambda k,d: type(d)(kv.get(k,d)) if not isinstance(d,bool) else kv.get(k,str(int(d)))=='1'
B=ROOT+'/episodes/e909_two_char_acting/shots/s010_t183/build'
src=kv.get('src', glob.glob(B+'/packages/girl_*')[0])
out=f'{B}/exp/{name}'; os.makedirs(out+'/packages/girl',exist_ok=True)
scene=json.load(open(B+'/shot.resolved.scene.json'))
for c in scene['characters']:
    if c['name']=='girl': c['asset']=out+'/packages/girl/character.json'
    else: c['asset']=B+'/'+c['asset']
doc=json.load(open(src+'/character.json'))
if not os.path.exists(out+'/packages/girl/geometry.bin'): os.symlink(src+'/geometry.bin', out+'/packages/girl/geometry.bin')
# --- package data
class Pk:
    def __init__(s,doc,folder):
        s.doc=doc; s.blob=open(folder+'/geometry.bin','rb').read()
    def arr(s,a,comp):
        dt={"float32":np.float32,"uint32":np.uint32,"uint16":np.uint16}[a["dtype"]]
        return np.frombuffer(s.blob,dtype=dt,count=a["count"],offset=a["offset"]).reshape(-1,comp)
pk=Pk(doc,src)
names=[b['name'] for b in doc['skeleton']]; head={b['name']:np.array(b['head']) for b in doc['skeleton']}
def region(groups, parts=None, notparts=('hair_',), minw=0.5):
    import fnmatch
    out=[]
    gi=[i for i,n in enumerate(names) if any(fnmatch.fnmatchcase(n,g) for g in groups)]
    for m in doc['meshes']:
        p=m['part']
        if any(p.startswith(x) for x in notparts) or p.startswith(('eye','lash','lid','brow','mouth','glasses')): continue
        if parts and not any(fnmatch.fnmatchcase(p,x) for x in parts): continue
        P=pk.arr(m['positions'],3).astype(float); J=pk.arr(m['joints'],4).astype(int); W=pk.arr(m['weights'],4).astype(float)
        w=(W*np.isin(J,gi)).sum(1)
        out.append(P[w>=minw])
    return np.concatenate(out)
dyn=doc['dynamics']
import bpy
from mathutils.bvhtree import BVHTree
keepn=('head','torso','shoulder_l','shoulder_r')
keep=[c for c in dyn['colliders'] if c['name'] in keepn]
pct=G('pct',98.0); pad=G('pad',0.0025)
# figure: all non-hair meshes
FP=[];FN=[];FB=[];FT=[];FE=[];base=0
for m in doc['meshes']:
    p=m['part']
    if p.startswith(('hair_','eye','lash','lid','brow','mouth','glasses')): continue
    P=pk.arr(m['positions'],3).astype(float); N=pk.arr(m['normals'],3).astype(float); J=pk.arr(m['joints'],4).astype(int); W=pk.arr(m['weights'],4).astype(float)
    FP.append(P);FN.append(N);FE.append(np.full(len(P),p.startswith('ear.')));FB.append(J[np.arange(len(J)),W.argmax(1)]);FT.append(pk.arr(m['indices'],3).astype(np.int64)+base);base+=len(P)
FE=np.concatenate(FE);FP=np.concatenate(FP);FN=np.concatenate(FN);FB=np.concatenate(FB);FT=np.concatenate(FT)
tree=BVHTree.FromPolygons(FP.tolist(),FT.tolist())
near=[]
for ch in dyn['chains']:
    if ch['group']=='bun': continue
    J=[head[b] for b in ch['bones']]+[np.array(ch['tip'])]
    for x,y in zip(J[:-1],J[1:]): near+= [x,(x+y)/2,y]
import fnmatch
excl=[i for i,n in enumerate(names) if n in('head','DEF-jaw') or n.startswith(('eye','hand','f0','f1','f2','f3','thumb','DEF-f_','DEF-palm','DEF-thumb','thigh','shin','DEF-thigh','DEF-shin','DEF-toe','foot'))]
armb=[i for i,n in enumerate(names) if n.startswith(('upperArm','DEF-upper_arm','forearm','DEF-forearm'))]
handb=[i for i,n in enumerate(names) if n.startswith(('hand','f0','f1','f2','f3','thumb','DEF-f_','DEF-palm','DEF-thumb'))]
headb=[i for i,n in enumerate(names) if n in('head','DEF-jaw')]
sets=[('head',np.nonzero(np.isin(FB,headb)&~FE)[0],dict(spacing=G('spacing',0.024),radius=G('R',0.045),reach=G('head_reach',0.10))),
      ('ears',np.nonzero(FE)[0],dict(spacing=G('ear_spacing',0.010),radius=0.02,reach=9.0,min_radius=0.003)),
      ('torso',np.nonzero(~np.isin(FB,excl+armb))[0],dict(spacing=G('spacing',0.024),radius=G('R',0.045),reach=G('reach',0.12))),
      ('arms',np.nonzero(np.isin(FB,armb))[0],dict(spacing=G('arm_spacing',0.022),radius=G('R',0.045),reach=9.0)),
      ('hands',np.nonzero(np.isin(FB,handb))[0],dict(spacing=G('hand_spacing',0.012),radius=0.02,reach=9.0,min_radius=0.004))]
cols=list(keep); nsk=0
for nm,sel,kw in sets:
    sph=C.skin_spheres(tree,FP[sel],FN[sel],near,pad=pad,**kw)
    for (i,c,r) in sph:
        cols.append({'name':f'skin.{nsk}','type':'sphere','bone':names[FB[sel[i]]],'radius':round(r,5),'centre':[round(x,6) for x in c]}); nsk+=1
    d=C.capsule_distance(FP[sel],[(c,c,r) for _,c,r in sph])
    if kw['reach']<1:
        reachd=np.min(np.linalg.norm(FP[sel][:,None,:]-np.array(near)[None,::3,:],axis=2),axis=1); d=d[reachd<kw['reach']*0.8]
    print(f"skin {nm}: {len(sph)} spheres, radius min/median {min(r for _,_,r in sph)*1000:.1f}/{np.median([r for _,_,r in sph])*1000:.1f} mm; surface outside the spheres: {int((d>0).sum())}/{len(d)} max {d.max()*1000:.1f} mm p99 {np.percentile(d,99)*1000:.1f} mm")
dyn['colliders']=cols
colnames=[c['name'] for c in dyn['colliders']]
headcols=[c for c in dyn['colliders'] if c['bone']=='head']
def col_dist(p,c):
    a=np.array(c.get('a',c.get('centre'))); b=np.array(c.get('b',c.get('centre'))); ab=b-a; l2=ab@ab
    t=np.clip(((p-a)@ab)/l2,0,1) if l2>1e-12 else 0
    return np.linalg.norm(p-(a+t*ab))-c['radius']
rp=G('radius_pct',95.0); floor=G('radius_floor',0.006)
for ch in dyn['chains']:
    if ch['group']=='bun':
        ch['colliders']=[n for n in ('head','torso','shoulder_l','shoulder_r') if n in colnames]
        continue
    J=[head[b] for b in ch['bones']]+[np.array(ch['tip'])]
    m=next(m for m in doc['meshes'] if m['part']=='hair_'+ch['group'])
    P=pk.arr(m['positions'],3).astype(float); Jn=pk.arr(m['joints'],4).astype(int); W=pk.arr(m['weights'],4).astype(float)
    bi=[names.index(b) for b in ch['bones']]
    w=(W*np.isin(Jn,bi)).sum(1)
    radii=C.chain_radii(P[w>=0.5],J,percentile=rp,floor=floor)
    # no joint collides with the colliders of the chain's own root bone in the rest pose
    capped=[]
    for k,r in enumerate(radii):
        clear=min(col_dist(J[k],c) for c in headcols)
        capped.append(round(max(0.0,min(r,clear)) if k>0 else 0.0,5))
    ch.pop('colliders',None)
    ch['contact']={'solid':[], 'segments':True,'anchored_gravity':True,'radii':capped if G('radii',True) else [ch['radius']]*len(J)}
    if G('rest',True):
        ch['contact']['rest']=True; ch['contact']['friction']=G('friction',40.0); ch['contact']['max_swing']=G('max_swing',12.0)
    else:
        ch['contact']['solid']=[n for n in colnames if n not in('head',)]
    for k in ('limit_deg','stiffness','stiffness_tip','damping','gravity','drag'):
        if k in kv: ch[k]=float(kv[k])
    if ch['name'] in ('ringlets_side_r00.00','ringlets_back_05.00'): print(ch['name'],'radii fitted',radii,'used',capped)
json.dump(doc,open(out+'/packages/girl/character.json','w'))
json.dump(scene,open(out+'/scene.json','w'))
r=subprocess.run([ROOT+'/build/apps/render-cli/plush-render',out+'/scene.json','--bake',out+'/bake.json'],capture_output=True,text=True)
if r.returncode: print(r.stdout[-2000:],r.stderr[-2000:]); sys.exit(1)
# static reference (dynamics off) once
for c in scene['characters']:
    if c['name']=='girl': c['dynamics']=False
json.dump(scene,open(out+'/scene_static.json','w'))
subprocess.run([ROOT+'/build/apps/render-cli/plush-render',out+'/scene_static.json','--bake',out+'/bake_static.json'],capture_output=True)
subprocess.run(['python3',SP+'/tip_noise.py',out+'/bake.json',out+'/bake_static.json'])
if not G('nomeasure',False):
    r=subprocess.run(['python3',ROOT+'/docs/evaluation/characters/T-183/tools/measure_body.py',out+'/bake.json','--out='+out+'/measure.json']+(['--step='+kv['step']] if 'step' in kv else []),capture_output=True,text=True)
    txt=r.stdout; open(out+'/measure.txt','w').write(txt+r.stderr)
    i=txt.find('summary:'); print(txt[i:i+2600])
