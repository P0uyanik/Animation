import sys, glob, os, json
import numpy as np, mediapipe as mp
from PIL import Image, ImageDraw
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
S=sys.argv[1]
lm=vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=S+'/dl/mp/face_landmarker.task'),
    num_faces=1, min_face_detection_confidence=0.2, min_face_presence_confidence=0.2, output_face_blendshapes=True))
det=vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
    base_options=mpt.BaseOptions(model_asset_path=S+'/dl/mp/blaze_face_short_range.tflite'), min_detection_confidence=0.2))
out={}
os.makedirs(S+'/probes/mp_out',exist_ok=True)
for f in sorted(glob.glob(S+'/t202/crops/*.png')+glob.glob(S+'/t202/renders/*.png')):
    im=Image.open(f).convert('RGB')
    res={}
    for size in (256,512):
        a=np.asarray(im.resize((size,size)))
        mi=mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(a))
        d=det.detect(mi); r=lm.detect(mi)
        res[size]={'det':[round(x.categories[0].score,2) for x in d.detections],'landmarks':len(r.face_landmarks[0]) if r.face_landmarks else 0}
        if size==512 and r.face_landmarks:
            dr=ImageDraw.Draw(im2:=Image.fromarray(a))
            for p in r.face_landmarks[0]:
                x,y=p.x*size,p.y*size; dr.ellipse((x-1,y-1,x+1,y+1),fill=(0,255,0))
            im2.save(S+'/probes/mp_out/'+os.path.basename(f))
    out[os.path.basename(f)]=res
    print(os.path.basename(f),res)
json.dump(out,open(S+'/probes/mp_result.json','w'),indent=1)
