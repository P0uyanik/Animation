import bpy, sys, os, hashlib, math, struct, wave, time, json
out = sys.argv[sys.argv.index("--")+1]
os.makedirs(out, exist_ok=True)
res = {"blender": bpy.app.version_string}
# 1. two tone WAVs
def tone(p, f, secs=2.0, sr=48000):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(8000*math.sin(2*math.pi*f*i/sr))) for i in range(int(secs*sr))))
tone(f"{out}/a.wav", 440); tone(f"{out}/b.wav", 660)
sc = bpy.context.scene
sc.render.fps = 24; sc.frame_start = 1; sc.frame_end = 96
se = sc.sequence_editor_create()
strips = se.strips
s1 = strips.new_sound("dlg", f"{out}/a.wav", channel=1, frame_start=1)
s2 = strips.new_sound("sfx", f"{out}/b.wav", channel=2, frame_start=49)
s2.volume = 0.5
col = strips.new_effect("bg", "COLOR", channel=3, frame_start=1, length=96) if True else None
res["vse_api"] = "strips" if hasattr(se, "strips") else "sequences"
hs = []
for k in range(2):
    p = f"{out}/mix{k}.wav"
    t = time.time()
    bpy.ops.sound.mixdown(filepath=p, container="WAV", codec="PCM", format="S16")
    hs.append(hashlib.sha256(open(p, "rb").read()).hexdigest()[:16])
res["mixdown_sha_two_runs"] = hs
# 2. compositor availability
res["compositing_node_group_attr"] = hasattr(sc, "compositing_node_group")
# 3. modifiers / features present
ob = bpy.data.objects.new("m", bpy.data.meshes.new("m")); sc.collection.objects.link(ob)
for t in ("CORRECTIVE_SMOOTH", "SHRINKWRAP", "SURFACE_DEFORM", "CLOTH", "NODES", "MESH_CACHE"):
    try: ob.modifiers.new(t.lower(), t); res[t] = True
    except Exception as e: res[t] = str(e)
res["grease_pencil_v3"] = hasattr(bpy.data, "grease_pencils_v3") or hasattr(bpy.data, "grease_pencils")
res["ffmpeg_codecs"] = [i.identifier for i in bpy.types.FFmpegSettings.bl_rna.properties["codec"].enum_items]
json.dump(res, open(f"{out}/probe.json", "w"), indent=1); print(json.dumps(res))
