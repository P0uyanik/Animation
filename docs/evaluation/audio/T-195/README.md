# T-195 · Emotional vocal sounds on the T-187 paper-boat clip (placeholder voices)

Owner decision 2026-11-22: short vocal sounds attached to acting cues, licence-safe for commercial YouTube use.
Branch `t-195-claude-vocal-sounds`. System and rules: [docs/AUDIO.md](../../../AUDIO.md).
**All four sounds are procedural placeholders** made by our own code (licence `project-own`). They mark timing and
placement. They are not publication quality.

## What to look at
| File | What |
| --- | --- |
| [`T-195_paper_boat_vocal.mp4`](T-195_paper_boat_vocal.mp4) | a copy of [T-187](../../video/T-187/README.md)'s clip with the vocal track: the video stream is copied bit for bit (md5 `ea72e05a...` checked in the mux and in the tests); AAC 160 kb/s 48 kHz stereo |
| [`T-195_paper_boat_vocal.cues.json`](T-195_paper_boat_vocal.cues.json) | the cue list, the mixing plan per cue (sound file, cents, dB, pan), the mix's WAV sha256, and the input video's sha256 |
| [`library_spectrogram.jpg`](library_spectrogram.jpg) | the 15 library sounds in a row (0-8 kHz): gasp_oh ×3, giggle ×3, hm ×2, laugh ×2, sigh ×2, wow ×3 |

The original `docs/evaluation/video/T-187/T-187_paper_boat_h264.mp4` and the episode files are unchanged.

## Cues (derived from the shots; nothing hand-placed)
| Clip time | Shot | Who | Beat (scene frame, intensity) | Sound | Listening note |
| --- | --- | --- | --- | --- | --- |
| 6.75 s | 3 | boy | `surprised` s020 f59, 0.9 | `gasp_oh` v2, −325 cents, −3 dB, pan right | short inhaled breath, then a falling "oh!", in a lower child voice; it lands as his eyes go to the boat |
| 6.92 s | 3 | white-hair girl | `surprised` s020 f63, 0.9 | `gasp_oh` v0, +175 cents, −4 dB, pan left | the same gasp, higher and a little thinner; it overlaps his by 0.17 s, so the two read as one shared surprise |
| 7.33 s | 3 | auburn girl | `girl_delighted` s020 f73, 0.8 | `giggle` v0, +31 cents, −8 dB, centre | 4 quick breathy "hee" bursts under the tail of the white-hair girl's "oh"; quiet, as a delighted beat should be |
| 11.50 s | 4 | boy | `happy` s020 f173, 0.8 | `wow` v0, −326 cents, −6 dB, pan right | a rising-falling "wow" as he looks at her and smiles after the hand-over |

Shot 1-2 (s010) are silent: `girl_eager`, `boy_focused` and `curious` play at 0.6, below the 0.7 threshold, and
eager / focused have no sound. Shot 5 (s030) is silent too: its emotions start in the hidden pre-roll (f20 / f30,
with the render from f45). The mix peaks at −7.9 dBFS, so the −1 dBFS bus limiter is not engaged.

**Listening caveat:** this container has no audio output, so the notes above describe the recipe, the measured
pitch and the spectrogram, not a listen. The placeholders are recognisably synthetic: buzzy, and vowel-like rather
than speech-like. Please judge them by ear.

## Open points
1. **Real voices.** CC0 *child* vocalisations are rare on all the sites checked; see [AUDIO.md section 5](../../../AUDIO.md#5-sources-investigated-2026-11-22).
   The kenney.nl site answers 403 to our client, and the itch.io creator subdomains (`cicifyre.itch.io`,
   `johncarroll.itch.io`, `kenney.itch.io`) are proxy-blocked. All the packs listed there are adult voices anyway.
   Recommended: owner-made recordings. That means 1-3 takes of each cue (gasp/"oh!", "wow", giggle, small laugh,
   "hm?", sigh) as WAVs in `content/sounds/library/<cue>/`, each with a `SOURCES.json` entry (`placeholder: false`,
   `licence: project-own`, `source.by`). They replace the placeholders with no code change.
2. **Per-character voices from one set of recordings** come from the resample pitch shift, which moves the formants
   too. Beyond about ±400 cents it starts to sound like a chipmunk. Separate takes per character would be better.
3. **Pan** follows the seat, not the camera. In the side-on shot 5b the seat order no longer matches the screen
   (no cues there in this clip).
4. A cue's sound may run past a cut. Here none ends after its shot.

## Reproduce
```sh
python3 pipeline/audio/vocal.py demo --shots episodes/e912_paper_boat/shots/s010 episodes/e912_paper_boat/shots/s020 \
    episodes/e912_paper_boat/shots/s030 --assembly docs/evaluation/video/T-187/assembly.json \
    --video docs/evaluation/video/T-187/T-187_paper_boat_h264.mp4 --out-dir docs/evaluation/audio/T-195 \
    --name T-195_paper_boat_vocal
python3 pipeline/audio/tests/test_audio.py
```
