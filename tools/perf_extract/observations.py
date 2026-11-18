"""Visual coding of the hashed sources. All intervals are [first, end), in frames.

"girl" is the brown-haired girl with glasses. Labels describe visible acting.
An eye-line target is a screen-direction reading in the context of the shot.
"""

# id, start, end, expression/action. Each facial window has continuous beat coverage.
BEATS = {
    ("paperboat", "boy"): [
        (0, 12, "Dips his head over the sheet, heavy lids and slightly parted mouth"),
        (12, 32, "Holds the low-lidded look over the upright sheet"),
        (112, 125, "Returns in the wide with lowered brows and a small flat mouth"),
        (125, 132, "Upper lids dip and recover, irises stay visible"),
        (132, 151, "Holds the folded sheet with eyes lowered"),
        (259, 289, "Leans in behind the girls, eyes open wider and lips part"),
    ],
    ("paperboat", "girl"): [
        (0, 32, "Hands at the paper, small closed smile and lowered eyes"),
        (112, 125, "Holds the folded paper and looks down through her glasses"),
        (125, 132, "Raises her pupils slightly while keeping her mouth closed"),
        (132, 151, "Maintains the closed smile over the fold"),
        (255, 289, "Leans on the rim with a wide open smile as her face is revealed"),
    ],
    ("paperboat", "white_haired_girl"): [
        (0, 10, "Parted smiling lips, eyelids drop and lift"),
        (10, 32, "Open-eyed watch as her head inclines toward the paper"),
        (112, 123, "Leans toward the fold with her mouth nearly closed"),
        (123, 129, "Closes and reopens her eyes, chin still inclined"),
        (129, 151, "Holds her eyes wide with a small closed mouth"),
        (243, 250, "Clasps her hands as her eyes dip shut and reopen"),
        (250, 289, "Holds her hands under her chin, eyes wide and lips parted"),
    ],
    ("watertable", "boy"): [
        (0, 20, "Leans on the rim, brows low and mouth nearly closed"),
        (20, 27, "Blinks during the start of the reach beside him"),
        (27, 60, "Holds the same sidelong watch as the girl points"),
        (60, 81, "Blinks then lifts his head slightly with eyes open"),
        (81, 87, "Blinks again during the settle"),
        (87, 121, "Holds the raised head and small closed mouth"),
    ],
    ("watertable", "girl"): [
        (0, 15, "Hand at chin, eyes wide and mouth rounded open"),
        (15, 22, "Blinks as her hand leaves her chin"),
        (22, 39, "Leans and points down, rounded mouth narrows"),
        (39, 61, "Sustains the point, blinks and closes her mouth"),
        (61, 81, "Draws back her hand as the point resolves"),
        (81, 96, "Straightens with a blink, mouth settles to a soft smile"),
        (96, 121, "Holds upright with arms down, brief partial lid dip"),
    ],
    ("watertable", "white_haired_girl"): [
        (0, 19, "Hands on the rim, head inclined and lips parted"),
        (19, 25, "Blinks and lowers her chin toward the boat"),
        (25, 56, "Watches the boat with her mouth almost closed"),
        (56, 77, "Blinks, lifts her head and parts her lips"),
        (77, 106, "Holds her head higher as the mouth relaxes"),
        (106, 112, "Blinks as her face turns more frontward"),
        (112, 121, "Holds a small closed smile and wide eyes"),
    ],
}

GAZE = {
    ("paperboat", "boy"): [
        (0,32,"Down and screen-left over the sheet"),
        (112,151,"Low screen-left hold over the paper, including a lid dip"),
        (259,289,"Looks down toward the lit boat throughout the reveal"),
    ],
    ("paperboat", "girl"): [
        (0,32,"Down at the work surface"),
        (112,125,"Pupils sit low toward the folded paper"),
        (125,132,"Small upward eye adjustment within the paper-facing pose"),
        (132,151,"Holds the adjusted eye line"),
        (255,289,"Down toward the boat, open-eyed hold through the pullback"),
    ],
    ("paperboat", "white_haired_girl"): [
        (0,32,"Screen-right toward the paper, resumes after blink"),
        (112,151,"Screen-right and down toward the fold, resumes after blink"),
        (243,289,"Down and screen-right toward the boat"),
    ],
    ("watertable", "boy"): [
        (0,60,"Near eye aimed screen-right and down toward the table"),
        (60,81,"Reacquires the rightward look as his head lifts"),
        (81,121,"Resumes the same rightward eye line after the blink"),
    ],
    ("watertable", "girl"): [
        (0,22,"Down and screen-right from the hand-at-chin pose"),
        (22,81,"Keeps the eye line low while pointing and withdrawing"),
        (81,96,"Eyes reopen into a higher, more forward head pose"),
        (96,121,"Holds the forward and slightly downward eye line"),
    ],
    ("watertable", "white_haired_girl"): [
        (0,56,"Screen-left and down toward the middle of the table"),
        (56,77,"Resumes the screen-left look while lifting her head"),
        (77,106,"Sustains the raised eye line beside the girl"),
        (106,112,"Reorients from the leftward look across the blink"),
        (112,121,"More front-facing gaze on reopening"),
    ],
}

# First clearly lowering frame, representative minimum aperture, first recovered
# frame. The partial dips have a visible iris at their minimum.
EYELIDS = {
    ("paperboat", "boy"): [(125,128,132,"partial")],
    ("paperboat", "girl"): [],
    ("paperboat", "white_haired_girl"): [
        (4,6,10,"blink"), (122,125,129,"blink"), (245,246,250,"blink")],
    ("watertable", "boy"): [(20,22,27,"blink"), (60,62,68,"blink"), (81,83,87,"blink")],
    ("watertable", "girl"): [(15,17,20,"blink"), (54,55,59,"blink"),
                             (79,82,87,"blink"), (113,114,117,"partial")],
    ("watertable", "white_haired_girl"): [
        (19,21,24,"blink"), (56,57,62,"blink"), (106,108,112,"blink")],
}

# Inserts supply manual action references despite missing eye lines.
INSERTS = [
    ("girl",32,50,"Palms settle and smooth the page"),
    ("boy",46,63,"Yellow sleeve reaches in and helps lift the paper corner"),
    ("white_haired_girl",40,50,"Blue sleeve reaches in from the left"),
    ("girl",50,72,"Guides the corner down into the crease"),
    ("girl",72,84,"Presses the triangle flat"),
    ("ensemble",84,90,"Folded triangle changes into a boat"),
    ("girl",96,112,"Holds the formed boat"),
    ("girl",151,175,"Lowers the boat with both hands to water contact"),
    ("girl",175,191,"Opens fingers and withdraws"),
    ("scene",191,239,"Boat floats as ripples and the waterline glow grow"),
]
