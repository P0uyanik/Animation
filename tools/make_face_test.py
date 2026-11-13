"""Face/expression test scene (character consistency check): one expression per frame, camera on the face.
Run from the repository root: python3 tools/make_face_test.py"""
import json
s = json.load(open("content/scenes/milestone02_classroom.scene.json"))
s["name"] = "Test - face expressions"
s["frameStart"], s["frameEnd"] = 1, 6
s["objects"] = [o for o in s["objects"] if o["name"] not in ("table", "boat")]
s["camera"].update(position=[0.0, 0.85, 0.72], target=[0.0, 0.8, 0.1], focalMm=60, fStop=0, focusDistance=-1)
step = lambda vals: [[f, v, "step"] for f, v in vals]
s["animation"] = {
    "girl/expr.smile": step([(1, 0), (2, 1), (3, 0)]),
    "girl/expr.mouthOpen": step([(1, 0), (3, 1), (4, 0)]),
    "girl/lid.L.rot": step([(1, [0, 0, 0]), (4, [86, 0, 0]), (5, [0, 0, 0])]),
    "girl/lid.R.rot": step([(1, [0, 0, 0]), (4, [86, 0, 0]), (5, [0, 0, 0])]),
    "girl/brow.L.rot": step([(1, [0, 0, 0]), (5, [-6, 0, 0]), (6, [0, 0, 0])]),
    "girl/brow.R.rot": step([(1, [0, 0, 0]), (5, [-6, 0, 0]), (6, [0, 0, 0])]),
    "girl/lookAt": step([(1, [0.0, 0.85, 0.72]), (6, [0.5, 0.75, 0.6])]),
}
json.dump(s, open("content/scenes/test_face.scene.json", "w"), indent=1)
print("wrote content/scenes/test_face.scene.json")
