# Emotional vocal sounds (T-195)

**Status:** the system is implemented and tested. Every sound in the library is a procedural **placeholder**
(our own code, `placeholder: true`). The owner can replace these with recorded or approved CC0 files with no code
change (section 4). Nothing is approved.

Short non-verbal vocal sounds are attached to the acting beats of a rendered clip: a surprised gasp / "oh!", a
delighted "wow", a giggle, a small laugh, a curious "hm?" and a sigh. The cue list is derived read-only from the shot
files and the clip assembly. It is mixed to a stereo track and muxed onto a **copy** of the clip, with the video
stream copied bit for bit. There is no re-render, and no scene, episode or engine edit.

```
shots/<scene>/shot.scene.json --+
assembly.json (clip frame map) -+-> cues.py --> plush.vocalcues/1 --> mix.py --> 48 kHz WAV --> vocal.py mux --> copy.mp4
content/sounds/cues.json -------+               voices.json, library --^                      (-c:v copy, AAC 160k)
```

## 1. Commands
```sh
python3 pipeline/audio/library.py check          # SOURCES.json vs files: hashes, licences, evidence
python3 pipeline/audio/library.py build          # (re)generate the procedural placeholders and their entries
python3 pipeline/audio/vocal.py demo \
    --shots episodes/e912_paper_boat/shots/s010 episodes/e912_paper_boat/shots/s020 episodes/e912_paper_boat/shots/s030 \
    --assembly docs/evaluation/video/T-187/assembly.json \
    --video docs/evaluation/video/T-187/T-187_paper_boat_h264.mp4 \
    --out-dir docs/evaluation/audio/T-195 --name T-195_paper_boat_vocal      # [--mono] [--keep-wav]
python3 pipeline/audio/vocal.py cues|mix|mux ...  # the three steps one at a time (--help)
python3 pipeline/audio/tests/test_audio.py
```
You need Python 3.10+ with numpy for the audio steps, and ffmpeg / ffprobe for the mux step only. Blender is not
used.

## 2. Cues: from acting beats to a cue list (`pipeline/audio/cues.py`)
The source is the shot's `emotion` actions `{character, name, start, end?, intensity}` (docs/EMOTIONS.md) as authored.
The cue map is `content/sounds/cues.json`. It is looked up by the full emotion name (`happy/laugh`) first, then by the
base name (`happy`).

| Emotion | Cue | Notes |
| --- | --- | --- |
| `surprised`, `afraid` | `gasp_oh` | lead 0: the gasp starts with the face |
| `happy` | `wow` | |
| `happy/laugh` | `laugh` | |
| `girl_delighted` | `giggle` | -2 dB |
| `girl_wonder` | `wow` | -2 dB |
| `curious`, `confused` | `hm` | -3 dB |
| `sad`, `sleepy` | `sigh` | -3 / -4 dB |
| `angry`, `boy_focused`, `girl_eager`, `girl_content`, anything unlisted | none | |

An emotion action gives a cue when all of these hold:
- it has a cue in the map;
- `intensity` is at least `minIntensity` (0.7);
- its `start` is a rendered frame of that scene (listed in the assembly);
- the cue frame `start + round(lead × onset × fps)` is rendered too. `lead` defaults to 0.25, and the onset comes
  from the emotion file's `timing`, with the variant patch applied.

So a beat whose onset lies in a hidden pre-roll or is cut away is silent. A cue less than `minGapSeconds` (1 s)
after the previous cue of the same character is dropped.

The level is `gainDb = levelDb + quietDb × (1 − t)`, where `t = (intensity − 0.7) / 0.3` and `quietDb` is −9.

The output `plush.vocalcues/1` holds `{fps, frames, cues: [{clipFrame, time, scene, sceneFrame, shot, character,
personality, seatX, emotion, intensity, cue, gainDb}]}`.

## 3. Voice and mix (`pipeline/audio/mix.py`, `content/sounds/voices.json`)
- **Per character** (keyed by the scene character's `personality`): `pitchCents` sets the character's pitch:
  boy −320, auburn girl +60, white-hair girl +180. `spreadCents` (±30) adds a per-cue variation taken from the
  cue's hash, and `levelDb` trims the voice. The pitch shift is a linear resample, so the formants move with it;
  keep it within about ±400 cents.
- **Deterministic choice:** the hash is `h = sha256("<scene>:<sceneFrame>:<character>:<cue>")`. The variant is
  `h mod n` over the cue's candidates, and the spread comes from other bits of `h`. The same cue list, library and
  voices give a byte-identical WAV.
- **Pan:** stereo by default, constant power. The position is the seat: the scene `position.x` × `seatPanScale`,
  clamped to −1..1 (white −0.43, auburn 0, boy +0.40 in e912). A voice entry can fix `pan` instead. `--mono` writes
  one channel.
- **Bus:** the mix is summed in float. If its peak would exceed **−1 dBFS**, the whole track is scaled down, so
  nothing is ever clipped. The output is 48 kHz 16-bit PCM, exactly `frames / fps` long.
- **Mux** (`vocal.py mux`): ffmpeg runs with `-c:v copy -c:a aac -b:a 160k -ar 48000`, bitexact flags and
  `+faststart`. The step refuses to write over its input. It checks that the video stream's md5 is unchanged.

## 4. Library and licences (`content/sounds/`)
```
content/sounds/library/<cue>/<file>.wav   48 kHz mono 16-bit PCM, <= 1.5 s, peak -6 dBFS (plain git, no LFS)
content/sounds/SOURCES.json               one entry per file
content/sounds/cues.json, voices.json     the rules above
```
A `SOURCES.json` entry has these fields:
- `path`, `sha256`, `cue`;
- `placeholder` (true / false);
- `licence`, which must be **`CC0-1.0` or `project-own`**: anything with BY / SA / NC / "royalty-free" fails the
  check;
- `source`: `{kind: procedural, generator, recipe, variant, seed}`, `{kind: recorded, by}` or
  `{kind: download, url, author}`;
- `evidence`: a licence URL, or the owner's statement;
- `added`, `seconds`, `rate`, `channels`.

`library.py check` and the tests fail on any of the following:
- a missing or extra file;
- a hash mismatch;
- a licence outside the whitelist;
- a non-procedural file with no evidence or no `source.url` / `source.by`.

**Replacing a placeholder (no code change):**
1. Put the WAV in `content/sounds/library/<cue>/`. Any integer PCM WAV works; it is resampled to 48 kHz mono.
2. Add its entry to `SOURCES.json` with `placeholder: false`.

For a cue, files with `placeholder: false` win over the placeholders as soon as one exists. Owner recordings are
`project-own` with `source.by`; downloads must be per-file CC0 with the licence URL as evidence. Re-run `demo`, and
update `EvidenceTests` if the evidence directory changes.

**Placeholders** (`pipeline/audio/synth.py`) come from a small deterministic source-filter voice in numpy:
- a Rosenberg glottal pulse train with jitter and shimmer, plus aspiration noise;
- 4 time-varying formant resonators, using child vowel formants (about 1.15 × adult female) and a neutral F0
  around 300-450 Hz;
- each breath group is one continuous segment with raised-cosine edge fades, so there are no clicks.

Recipes: `gasp_oh` (inhaled breath, then a falling "oh!"), `wow` (w→a→o→u glide, pitch up then down), `giggle` (4-5
breathy "hee" bursts stepping down), `laugh` ("ha-ha-ha", falling), `hm` (nasal hum, rising), `sigh` (breathy
falling "haah"). There are 15 files (936 KB). They are recognisably synthetic: use them for timing and placement,
not for publication.

## 5. Sources investigated (2026-11-22)
- **Not reachable or not usable from the cloud environment:**
  - `freesound.org` / `cdn.freesound.org`: proxy-blocked; downloads need an API key.
  - `kenney.nl`: allowed, but the site itself answers 403 to our client. No browser user-agent was faked. Its CC0
    audio has no child vocalisations; the voice pack is adult announcer words.
  - Creator subdomains on itch.io (`cicifyre.itch.io`, `johncarroll.itch.io`, `kenney.itch.io`): proxy-blocked.
    The CC0-tagged voice packs listed on `itch.io` are adult voices, and pitching an adult voice up to a child's
    reads as a "chipmunk" voice.
- **Rejected on licence:** pixabay, mixkit, BBC SFX (NC), soundbible (mostly BY), Sonniss GDC (no redistribution),
  research datasets (BY-SA / research-only).
- **CC0 candidates found but not used** (adult voices, not checked by ear):
  - opengameart.org "Group giggling" (AuraVoice, CC0 + "use however you like, no credit required"; a layered adult
    giggle, F0 median ~280 Hz);
  - Wikimedia Commons `File:Laughter(s).ogg` (CC0, sagetyrtle via Freesound; the download was rate-limited, 429).
- **Child vocalisations under CC0 are rare on every site checked.** The recommended real source is short
  owner-made recordings (section 4).
