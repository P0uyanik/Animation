"""Reference-specific eye-line anchors marked on resized frames, in screen coordinates.

Each track is confined to one shot. Each knot gives frame, eye-line midpoint x/y
and an approximate face width. Keep full precision when scaling to source pixels.
"""

# Reference display dimensions. Source and display have the same aspect to 1 px.
DISPLAY = {"paperboat": (495, 278), "watertable": (331, 443)}
SHOTS = {
    "paperboat": [
        (0, 32, "paper at desk"), (32, 112, "hands fold paper"),
        (112, 151, "finished fold at desk"), (151, 191, "boat lowered"),
        (191, 239, "boat and light"), (239, 289, "reaction reveal"),
    ],
    "watertable": [(0, 121, "watching the water table")],
}
# The reveal begins with cropped faces. Start each series when both eyes can be read.
ANCHORS = {
    ("paperboat", 0, "white_haired_girl"): [(0,142,161,82),(16,149,168,82),(31,149,172,82)],
    ("paperboat", 0, "girl"): [(0,246,150,87),(16,247,152,87),(31,244,153,87)],
    ("paperboat", 0, "boy"): [(0,361,161,88),(16,350,170,88),(31,353,172,88)],
    ("paperboat", 112, "white_haired_girl"): [(112,130,165,87),(128,138,173,88),(150,150,174,89)],
    ("paperboat", 112, "girl"): [(112,248,153,92),(128,245,158,92),(150,241,159,92)],
    ("paperboat", 112, "boy"): [(112,359,158,89),(128,362,166,90),(150,369,167,91)],
    ("paperboat", 239, "white_haired_girl"): [(243,60,12,138),(251,67,36,136),(263,99,67,125),(271,108,88,118),(279,115,101,110),(288,121,115,102)],
    ("paperboat", 239, "girl"): [(255,327,7,145),(263,326,24,137),(271,315,54,130),(279,310,73,124),(288,307,91,118)],
    ("paperboat", 239, "boy"): [(259,212,10,98),(263,215,30,98),(271,215,58,93),(279,218,74,88),(288,216,88,85)],
    ("watertable", 0, "boy"): [(0,65,245,80),(16,65,245,80),(32,70,246,80),(48,74,249,80),(64,66,246,80),(80,53,237,79),(96,48,236,78),(120,48,236,78)],
    ("watertable", 0, "girl"): [(0,150,179,85),(16,151,181,85),(32,159,195,85),(48,157,193,85),(64,155,190,85),(80,152,185,85),(96,139,168,83),(108,139,167,83),(120,139,168,83)],
    ("watertable", 0, "white_haired_girl"): [(0,228,229,84),(16,231,229,84),(32,228,234,84),(48,227,235,84),(64,232,227,84),(80,238,216,84),(96,236,218,84),(108,239,220,84),(120,240,218,84)],
}
