# Mocap clips: source, licence, attribution (T-175)

Every clip in this folder comes from the **CMU Graphics Lab Motion Capture Database** (http://mocap.cs.cmu.edu),
downloaded as the official ASF/AMC files from `mocap.cs.cmu.edu/subjects/<subject>/` and converted by
`pipeline/clips/import_bvh.py`. No other mocap source is used here (no Mixamo, no non-commercial data).

**Licence (CMU):** the data is free for all uses, including commercial projects; it may be copied, modified and
redistributed; the original data must not be resold. CMU asks for this credit, which also goes into published video
credits and is stored in each clip's `attribution` field:

> The data used in this project was obtained from mocap.cs.cmu.edu.
> The database was created with funding from NSF EIA-0196217.

Details and quoted terms: `docs/references/MOCAP_LICENSES.md`.

| Clip | CMU subject / trial | CMU description | Source frames (120 fps) | Clip |
| --- | --- | --- | --- | --- |
| `cmu_walk` | 35 / 01 (`35.asf`, `35_01.amc`) | walk | cycle found automatically (see `x_mocap.loop_frames`) | 24 fps loop |
| `cmu_sit_down` | 14 / 32 (`14.asf`, `14_32.amc`) | sit on stepstool, stand up | 195–345 (origin: between the feet at frame 345, the hips' turn removed) | 24 fps one-shot |
| `cmu_stand_up` | 14 / 32 (`14.asf`, `14_32.amc`) | sit on stepstool, stand up | 195–345 played backwards | 24 fps one-shot, starts where `cmu_sit_down` ends |

The clips carry no hand (wrist) roles: the source's wrist data is noisy. `cmu_walk`'s arm rotations are low-passed
(binomial, 2 frames). Each clip's `x_mocap` block records these options.

The source files themselves are not stored in the repository. To rebuild a clip, download the two files and run the
importer with the options recorded in the clip's `x_mocap` block and `docs/evaluation/animation/T-175/README.md`.
