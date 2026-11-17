"""Garment colour medians for renders whose garments carry generated fibre curves.
groom_turnaround --ids swaps only mesh materials, and its id palette repeats after ~22 slots, so garment pixels are
taken as (that garment's slot ids OR pixels whose id is no known slot = fibre curves) inside a vertical band that only
that garment occupies in the view. Reference side: the colour_checks boxes."""
import json,sys,numpy as np, scipy.ndimage as nd
from PIL import Image
sys.path.insert(0,'pipeline/charsys/tools'); import measure_colour as M
rd=sys.argv[1]; ids=json.load(open(rd+'/ids.json'))
ref=json.load(open('assets/characters/girl_auburn_bun_glasses/references/colour_checks_outfit.json'))
band={'boots':(0.80,1.0),'vest':(0.42,0.58),'blouse':(0.35,0.60),'shorts':(0.60,0.72)}
out={}
for c in ref['checks']:
    R=np.asarray(Image.open(f"assets/characters/girl_auburn_bun_glasses/references/views/{c['view']}.png").convert('RGB'))
    b=np.median(np.concatenate([R[y0:y1,x0:x1].reshape(-1,3) for x0,y0,x1,y1 in c['ref_boxes']]),0)
    g=c['slot'].split('.')[1]; lo,hi=band[g]
    I=np.asarray(Image.open(f"{rd}/{c['view']}.png").convert('RGB')); D=np.asarray(Image.open(f"{rd}/{c['view']}_ids.png").convert('RGB')).astype(int)
    def has(col): return np.all(np.abs(D-np.array(col))<=2,axis=2)
    known=np.zeros(D.shape[:2],bool); own=np.zeros_like(known)
    for k,col in ids.items():
        h=has(col); known|=h
        if k==f'M_garment.{g}.main' and sum(v==col for v in ids.values())==1: own|=h
    bg=np.all(np.abs(D-D[2,2])<=3,axis=2)
    # an id colour shared with another slot: keep it only inside the band
    m=(own|(~known&~bg)); m=nd.binary_erosion(m)
    H=m.shape[0]; m[:int(lo*H)]=False; m[int(hi*H):]=False
    if g=='boots': m&=~has(ids['M_garment.boots.sole'])
    a=np.median(I[m],0); d=float(M.de2000(M.srgb_to_lab(a),M.srgb_to_lab(b)))
    out[c['name']]={'render':a.tolist(),'ref':b.tolist(),'dE00':round(d,2),'px':int(m.sum())}
    print(f"{c['name']:22s} render {a} ref {b} dE00 {d:.2f} px {m.sum()}")
json.dump(out,open(sys.argv[2],'w'),indent=1)
