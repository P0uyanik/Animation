# Offline lip sync

Run from the repository root with Python 3.10 or newer. The default extractor uses only the standard library. Supply a local, uncompressed integer PCM WAV (8, 16, 24 or 32 bits, mono or multichannel). Create the output directory first.

```sh
python tools/lipsync/extract.py --audio line.wav --text "Move over" --fps 24 --out line.visemes.json
python tools/lipsync/validate.py line.visemes.json
python -m unittest discover -s tools/lipsync -p "test_*.py"
```

### Recognition and timing

For English dialogue, unpack a local copy of the official Rhubarb Lip Sync **1.13.0** release for your platform. Keep its executable, resource directory, dictionaries and licence files together. On Unix the binary needs execute permission. Pass its path explicitly using `--rhubarb /path/to/rhubarb`. The tool checks the version before invoking the bundled PocketSphinx recognizer. A supplied transcript becomes a temporary UTF-8 dialog file that biases recognition. Rhubarb supplies timed mouth cues derived from phones. Its code uses the MIT licence and its distribution includes separate third-party notices for its dependencies. Retain those notices when redistributing the release. [Upstream release and source](https://github.com/DanielSWolf/rhubarb-lip-sync/releases/tag/v1.13.0)

| Rhubarb cue | X | A | B | C | D | E | F | G | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shared viseme | rest | MBP | C | E | AI | O | WQ | FV | L |

F covers tightly rounded sounds including /w/ and /u/. This backend maps both to WQ. The fallback can distinguish U from WQ using spelling. Cue overlap determines the initial frame weights. Gaps contribute rest.

Without a binary, the extractor measures RMS on the strongest channel of each frame and gates silence at the larger of 0.002 full scale and 4.5% of peak frame RMS. With English letters in the transcript, it maps spelling groups to mouth shapes and distributes them evenly across active frames. Without usable text, zero-crossing rate selects an open, spread or fricative shape. This gives approximate timing for previews. Background noise, irregular spelling and unequal syllable lengths can produce incorrect cues. The track records which backend produced it. An explicitly selected recognizer failure exits with an error.

### Track and shot contracts

A track has `format` equal to `plush.visemes/1`, audio `duration` in seconds, `fps` (24 or the default 30), `source` and dense `frames`. Frame i starts at i/fps seconds relative to the line and ends at the next frame boundary or the audio end, whichever comes first. There are ceil(duration × fps) frames. Each frame is a sparse map of viseme IDs to normalized weights, with absent IDs equal to zero. The extractor mixes the previous, current and following frame in proportions 1:2:1, taking rest beyond the track edges. This anticipates and releases shapes over one frame on each side of a transition.

A shot dialogue file uses seconds relative to the shot start. Speaker is the shot's character identifier and audio is a path relative to the dialogue file. Lines can overlap and retain author order. To locate a track frame in the shot, add the line's start to its frame time.

```json
{
  "format": "plush.dialogue/1",
  "lines": [
    {"speaker": "lead", "text": "Move over", "audio": "audio/line.wav", "start": 0.75}
  ]
}
```

Run `python tools/lipsync/validate.py shot.dialogue.json line.visemes.json` to check both files offline. The validator checks structure, track coverage and normalization. Audio path resolution and speaker lookup belong to the shot consumer. [Track schema](../tools/lipsync/plush.visemes.schema.json) · [Dialogue schema](../tools/lipsync/plush.dialogue.schema.json)

### Face controls and reference grid

The shared library gives each viseme a description, suggested unit weights for existing mouth channels, and a visual reference. For each available channel, sum its suggested values multiplied by the frame's viseme weights. Resolve `jawOpen` through the expression map (JawOpen on the boy). Resolve `mouthUp` through mouthSmile or MouthSmile. Skip missing channels independently. A jaw-only character retains aperture changes. A character with neither channel receives zero speech motion. The closed rest and MBP poses contribute zero opening. These values describe the speech contribution before a future face-layer blend. [Shared library](../content/visemes/shared_visemes.json) · [T-046 controls](evaluation/animation/T-046/README.md) · [Channel candidates](../content/emotions/face_motion.json)

Grid coordinates count only the bottom two strips of five mouth close-ups, starting at row 1, column 1. The flat closure (1,1) anchors rest and MBP. The wide opening (1,3) anchors AI and the spread E, the round opening (1,4) anchors O, and the smaller opening (2,1) anchors U and WQ. FV and C borrow the nearly closed silhouette, while L borrows the open silhouette. Teeth contact, lip protrusion and tongue placement are approximations on the current controls. These are visual targets for the third character's future rig. [Mouth-shape grid](../assets/characters/girl_white_hair_blue_dress/references/uploads/14_face_expression_mouth_shape_grid.webp)
