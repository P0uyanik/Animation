"""Score square, view-matched head crops against T-204 targets. See README.md."""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
N = 400
TAGS = {"boy": "boy", "auburn": "girl", "white_haired": "third"}
VIEWS = ("front", "three_quarter", "side")
EM = float("nan")


def json_read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def source_image(base, trace, role):
    if role == "reference":
        with Image.open(base / "crops" / trace["source"]) as im:
            return im.convert("RGB")
    top = 128 + 1064 * trace["row"]
    with Image.open(base / "sheets" / trace["source"]) as im:
        if im.width != 2000 or top + 1000 > im.height:
            raise ValueError("Expected a T-202 sheet with two 1000 px tiles and 64 px bars.")
        return im.crop((1000, top, 2000, top + 1000)).convert("RGB")


def lab_patch(im, point):
    """Median sRGB triplet in a disk of radius 3.5/400 tile widths, D65 Lab."""
    if point is None:
        return [EM] * 3
    if im.width != im.height:
        raise ValueError("Expected a square head tile.")
    s = im.width / N
    x, y = np.asarray(point) * s
    radius = max(1, 3.5 * s)
    x0, y0 = max(0, math.floor(x-radius)), max(0, math.floor(y-radius))
    x1, y1 = min(im.width, math.ceil(x+radius)+1), min(im.height, math.ceil(y+radius)+1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rgb = np.asarray(im.crop((x0, y0, x1, y1)))[(xx-x)**2+(yy-y)**2 <= radius**2]
    if not rgb.size:
        raise ValueError(f"Sample lies outside the crop: {point}")
    v = np.median(rgb, axis=0) / 255
    lin = np.where(v <= .04045, v / 12.92, ((v + .055) / 1.055) ** 2.4)
    xyz = np.array([[.4124564,.3575761,.1804375], [.2126729,.7151522,.0721750],
                    [.0193339,.1191920,.9503041]]) @ lin / [.95047, 1, 1.08883]
    f = np.where(xyz > (6/29)**3, np.cbrt(xyz), xyz / (3*(6/29)**2) + 4/29)
    return [116*f[1]-16, 500*(f[0]-f[1]), 200*(f[1]-f[2])]


def values(a, im=None):
    """Return only finite image-plane measurements. Hidden landmarks propagate as NaN."""
    def field(key, length=2):
        return a.get(key) or [EM] * length

    def section(key, y):
        pts = a.get(key)
        if not pts or not math.isfinite(y):
            return EM
        xs, ys = np.asarray(pts).T
        if any(np.diff(ys) <= 0):
            raise ValueError(f"{key} contour must run strictly downward.")
        return np.interp(y, ys, xs, left=EM, right=EM)

    crown = field("crown")[1]
    _, chin = field("chin")
    h = chin - crown
    if not h > 0:
        raise ValueError("Set crown and chin, with chin below crown.")
    x0, et, x1, eb = field("eye", 4)
    il, ey, ir = field("iris", 3)
    ey = ey if a.get("eye_y") is None else a["eye_y"]
    eh = eb-et if a.get("eye_h") is None else a["eye_h"]
    ew, diameter = x1-x0, ir-il
    ix = (il+ir)/2
    fx, fy = field("far")
    _, ey1 = field("brow_lid") if a.get("brow_lid") else (ix, et)
    nx0, nt, nx1, nb = field("nose", 4)
    mx0, mt, mx1, mb = field("mouth", 4)
    my = (mt+mb)/2
    spacing = math.hypot(fx-ix, fy-ey)
    mid_eye = (ey+fy)/2
    left, right = a.get("left"), a.get("right")
    f = max(p[0] for p in right)-min(p[0] for p in left) if left and right else EM
    if f <= 0 or ew <= 0 or spacing == 0:
        raise ValueError("Check face contours, opening width and iris separation.")
    centre = (max(p[0] for p in right)+min(p[0] for p in left))/2 if left and right else EM
    d = dict(head_roundness=f/h, eye_width=ew/h, eye_height=eh/h,
             eye_y=(ey-crown)/h, eye_to_chin=(chin-ey)/h,
             eye_x=(ix-centre)/f, eye_spacing=spacing/f, iris_size=diameter/h,
             opening_h_w=eh/ew, iris_d_w=diameter/ew, iris_d_spacing=diameter/spacing,
             brow_gap=(ey1-field("brow")[1])/h,
             nose_width=(nx1-nx0)/f, nose_height=(nb-nt)/h, nose_y=((nt+nb)/2-crown)/h,
             mouth_width=(mx1-mx0)/f, mouth_height=(mb-mt)/h, mouth_y=(my-crown)/h,
             mouth_x=((mx0+mx1)/2-centre)/f, chin_height=(chin-my)/h)
    for metric, fraction in (("cheek_width", .5), ("jaw_width", .8), ("chin_width", .93)):
        y = ey + fraction*(chin-ey)
        d[metric] = (section("right",y)-section("left",y))/f
    cap = a.get("cap")
    if cap:
        d["hair_width"]=(cap[1][0]-cap[0][0])/f
    d["hair_height"]=(chin-field("crest")[1])/h
    skull, fringe, brow = (field(k)[1] for k in ("skull","fringe","midbrow"))
    if brow > skull and math.isfinite(fringe):
        d["forehead_covered"]=min(1,max(0,(fringe-skull)/(brow-skull)))
    d["fringe_eye"]=(mid_eye-fringe)/h
    d["crown_above_skull"]=(skull-crown)/h
    cheek_hair = a.get("hair_at_cheek")
    if a.get("no_cheek_hair"):
        d["hair_cheek_width"]=0.
    elif cheek_hair:
        d["hair_cheek_width"]=(cheek_hair[1][0]-cheek_hair[0][0])/f
    bun = a.get("bun_span")
    if a.get("no_bun"):
        d["bun_width"]=0.
    elif bun:
        d["bun_width"]=abs(bun[1][0]-bun[0][0])/f
    el, etop, er, ebot = field("ear",4)
    d.update(ear_width=(er-el)/f, ear_height=(ebot-etop)/h,
             ear_top_eye=(etop-mid_eye)/h, ear_base_mouth=(ebot-my)/h)
    if a.get("ear_turn"):
        d["ear_turn_projection"]=abs(a["ear_turn"][1][0]-a["ear_turn"][0][0])/f
    profile = a.get("profile")
    if profile and all(p is not None for p in profile):
        (u,uy),(v,vy),(w,wy)=profile
        if not uy < vy < wy:
            raise ValueError("The three profile points must run downward.")
        tangent = u + (w-u)*(vy-uy)/(wy-uy)
        d["cheek_bulge"]=a["facing"]*(v-tangent)/h
        d["cheek_advance"]=a["facing"]*(v-u)/h
    section_ends = a.get("profile_span")
    if section_ends:
        d["profile_depth"] = abs(section_ends[1][0] - section_ends[0][0]) / h
    if a.get("nose_tip") and profile and profile[0]:
        d["profile_nose"] = a["facing"] * (a["nose_tip"][0] - profile[0][0]) / h
    if a.get("exposed"):
        d["exposed_cheek"]=abs(a["exposed"][1][0]-a["exposed"][0][0])/h
    if im is not None:
        samples={k:lab_patch(im,a.get(k)) for k in ("cheek","forehead","base","bow")}
        for zone in ("cheek","forehead","bow"):
            for channel,val in zip("Lab",samples[zone]):
                d[f"{zone}_{channel}"]=val
        d["blush_da"]=samples["cheek"][1]-samples["base"][1]
    return {k:float(v) for k,v in d.items() if math.isfinite(v)}


def score(db, c, view, trace, im, source):
    measured=values(trace["points"],im)
    for key,t in db["characters"][c]["targets"][view].items():
        spec=db["metrics"][key]
        cur=measured.get(key)
        ref=t["value"]
        gap=cur-ref if cur is not None and ref is not None else None
        inferred=set(trace.get("estimated",[])).intersection(spec["depends"])
        yield dict(character=c,view=view,measure=key,unit=spec["unit"],
                   reference=ref,reference_mark=t["mark"],reference_source=t["source"],
                   tolerance=t["tolerance"],current=rounded(cur),
                   current_mark=("E" if inferred else "M") if cur is not None else "",
                   current_source=source,gap=rounded(gap),
                   result="unscored" if gap is None else
                   ("within" if abs(gap)<=t["tolerance"] else "outside"))


def rounded(x):
    return round(x,5) if x is not None else None


def write_csv(path, rows):
    with Path(path).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf",size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf",size)
        except OSError:
            return ImageFont.load_default(size=size)


def overlay(im, a):
    side=540
    tile=im.resize((side,side),Image.Resampling.LANCZOS)
    draw=ImageDraw.Draw(tile)
    def xy(p):
        return tuple(round(v*side/N) for v in p)
    def line(pts,col):
        if pts and all(p is not None for p in pts):
            draw.line([xy(p) for p in pts],fill=col,width=2)
    def dot(p,col,r=3):
        if p:
            x,y=xy(p)
            draw.ellipse((x-r,y-r,x+r,y+r),outline=col,width=2)
    gold="#ffd36a";cyan="#45e6ed";pink="#ff79ba"
    for k in ("left","right","profile","exposed","ear_turn"):
        line(a.get(k),gold)
    if a.get("profile"):
        for p in a["profile"]:
            dot(p,gold)
    for point in a.get("profile_span") or []:
        dot(point, gold)
    dot(a.get("nose_tip"), cyan)
    for k in ("crown","chin","crest","fringe"):
        dot(a.get(k),gold)
    if a.get("cap"):
        for p in a["cap"]:
            dot(p,gold)
    for k in ("eye","mouth","nose","ear"):
        box=a.get(k)
        if box:
            draw.rectangle([xy(box[:2]),xy(box[2:])],outline=cyan,width=1)
    if a.get("iris"):
        l,y,r=a["iris"]
        line([(l,y),(r,y)],cyan)
        dot(a.get("far"),cyan)
        line([((l+r)/2,y),a.get("far")],cyan)
    if a.get("brow"):
        dot(a["brow"],cyan)
    for k in ("cheek","forehead","base","bow"):
        dot(a.get(k),pink,5)
    return tile


def evidence(base,db,c,out):
    plate=Image.new("RGB",(1080,1816),"#1f252c")
    draw=ImageDraw.Draw(plate)
    ch=db["characters"][c]
    draw.text((14,10),f"{c.replace('_',' ').title()}   /   release {ch['release']}",font=font(29),fill="white")
    draw.text((14,49),"Gold   contour / hair      Cyan   features      Pink   colour samples",font=font(18),fill="#d8e2ed")
    for i,v in enumerate(VIEWS):
        y=83+i*576
        for j,role in enumerate(("reference","current")):
            t=ch["views"][v][role]
            label=t["source"].removesuffix(".png") if j==0 else f"current   /   yaw {ch['yaw'][i]} deg"
            draw.text((j*540+12,y+3),v.replace("_"," ")+"   |   "+label,font=font(17),fill="white")
            plate.paste(overlay(source_image(base,t,role),t["points"]),(j*540,y+32))
    plate.save(out/f"{c}.jpg",quality=90,optimize=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs",type=Path,help="T-202 directory with crops/ and sheets/")
    p.add_argument("--output",type=Path,required=True,help="CSV or template JSON destination")
    p.add_argument("--evidence",type=Path,help="existing directory for three baseline JPEGs")
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--trace",type=Path,help="score edited landmark JSON against fixed targets")
    mode.add_argument("--template",nargs=2,metavar=("CHARACTER","VIEW"))
    p.add_argument("--image",type=Path,help="square new render for template mode")
    p.add_argument("--grid",type=Path,help="coordinate guide JPEG for template mode")
    args=p.parse_args()
    db=json_read(HERE/"targets.json")
    if args.template:
        c,v=args.template
        if c not in TAGS or v not in VIEWS or not args.image:
            p.error("template needs a valid character, view and --image")
        with Image.open(args.image) as src:
            im=ImageOps.exif_transpose(src).convert("RGB")
        if im.width!=im.height:
            p.error("use a square crop preserving the face aspect ratio")
        t=db["characters"][c]["views"][v]["current"]
        obj=dict(character=c,view=v,image=str(args.image.resolve()),estimated=[],
                 points={k:None for k in t["points"]},example_points=t["points"])
        # Reference-only landmarks may become visible in a new release.
        obj["points"].update({k:None for k in db["characters"][c]["views"][v]["reference"]["points"]})
        json_write(args.output,obj)
        if args.grid:
            tile=im.resize((800,800),Image.Resampling.LANCZOS)
            d=ImageDraw.Draw(tile)
            for i in range(0,400,10):
                for j in range(0,400,10):
                    d.point((2*i,2*j),fill="#35cdda")
                if i%20==0:
                    d.text((2*i+2,1),str(i),font=font(12),fill="white",stroke_width=1,stroke_fill="black")
                    d.text((2,2*i+2),str(i),font=font(12),fill="white",stroke_width=1,stroke_fill="black")
            tile.save(args.grid)
        return
    if args.trace:
        t=json_read(args.trace); c=t["character"];v=t["view"]
        path=args.trace.parent / t["image"]
        with Image.open(path) as src:
            im=ImageOps.exif_transpose(src).convert("RGB")
        if im.width!=im.height:
            p.error("trace image must be square")
        rows=list(score(db,c,v,t,im,str(path)))
    else:
        base=args.inputs or ROOT/"build/in/docs/evaluation/characters/T-202"
        if args.inputs is None and not base.exists():
            base=HERE.parent/"T-202"
        rows=[]
        for c,ch in db["characters"].items():
            for v in VIEWS:
                t=ch["views"][v]["current"]
                im=source_image(base,t,"current")
                rows.extend(score(db,c,v,t,im,f"T-202/sheets/{t['source']} right row {t['row']+1}"))
            if args.evidence:
                evidence(base,db,c,args.evidence)
    write_csv(args.output,rows)


if __name__=="__main__":
    main()
