# T-205 · Bake in the cloud, render on the PC

**The PC no longer needs the engine.** A GitHub Actions run builds `plush-render` on Linux, runs the shot's prepare and bake stages, and publishes a *bake package*. The package is a zip holding everything Blender's render stage reads, with a SHA-256 for every file and the source commit. On the PC, one command checks the zip and renders it with Blender. Nothing runs `plush-render.exe` and no system setting changes, so Smart App Control has nothing to block (T-200, WinError 4551).

## Owner steps (Windows PC)

1. **Start the bake.** On GitHub, open *Actions → Bake package → Run workflow*. The shot field defaults to `episodes/e912_paper_boat/shots/s010/shot.scene.json`. Leave *frames* empty for the whole shot, then press *Run workflow* and wait for the green tick.
2. **Download it.** Open the finished run and download the **bake-package** artifact from the bottom of the page. GitHub delivers it inside an outer zip, so right-click it and choose *Extract All*. The folder holds `<name>.bake.zip` and `<name>.bake.zip.sha256`.
3. **Render.** Open *Command Prompt* in your Animation checkout and run:
   `tools\pc\render_package.cmd "%USERPROFILE%\Downloads\bake-package\<name>.bake.zip"`
   The command unpacks and verifies the zip. It finds Blender under *C:\Program Files\Blender Foundation* (or takes `--blender "<path>\blender.exe"`) and renders. Frames, `shot.blend` and `render.log` land next to the zip in `<name>_render_final720\`. Each new run gets a new folder.
4. **Pick the quality.** The command uses the shot's own render settings, exactly as `run_shot.py` does. For e912 s010 that means 640×360 at 16 samples on the `final720` profile. For full 720p, add `--resolution 1280 720 --samples 128`. Add `--frames 1-24` for part of the shot, or `--video` if ffmpeg is installed.
5. **Fast EEVEE preview.** Add `--profile preview_eevee` once T-201 adds that profile, using a package baked after it lands. Until then the command stops with *"render profile 'preview_eevee' is not in this package"* and renders nothing.

If the command reports **package verification failed**, the download was damaged or a file was edited. Delete the unpacked `<name>` folder and download the artifact again. Do not repair files by hand. To check the download itself, run `certutil -hashfile <name>.bake.zip SHA256` and compare the result with the `.sha256` file and the run's summary.

## Proof (this session, Linux, Blender 5.3.0 bpy, 4 vCPU)

| Check | Result |
|---|---|
| Package for e912 s010, frames 1–24 at commit `0cb0053a53` | `e912_paper_boat_s010_0cb0053a53_f1-24.bake.zip`, 121.9 MB, 27 files, sha256 `acc50669…935411b` |
| Determinism | Packing the same bake twice gave byte-identical `MANIFEST.json` and zip. A second engine bake of the resolved scene was identical apart from its host path. |
| Render from the package alone | The zip was copied alone into an empty temp folder with the engine binary renamed away and `PATH` reduced to system folders. Frames 1–3 rendered at 320×180, 4 spp, Cycles, with all three characters and nothing in `not_rendered`. Setup took 67.1 s, then 15.7 s/frame. |
| Same pixels as the repository render | Rendering the same bake from the repository paths matched the package render pixel for pixel on frames 1–3 (MAE 0, max 0). Only the PNG metadata differs. |
| Masters | All three masters link no library and no unpacked file. `bake_package.py` checks this with Blender on every pack. |

The packed girl, auburn and boy masters total about 120 MB of the zip. The full 184-frame bake adds about 25 MB of JSON. The engine-only `geometry.bin` files are not shipped; their hashes are recorded in `MANIFEST.json` under `engine_packages`.

One finding predates this task. The prop asset's material preset `paper_white` exists in no preset library, so the sheet renders with a default material. Cloud and PC renders show the same result.

## Package contents (`plush.bake_package/1`)

All paths are relative to the package folder, which is also Blender's working folder:

- `bake.json`, with `scene_path` rewritten to point inside the package
- `cast.json`
- `scene/shot.resolved.scene.json`
- `characters/<name>/` holding the master `.blend`, its published `manifest.json` and `package/character.json`
- `content/assets/<prop>.asset.json`, for the prop assets the scene names
- `code/pipeline/charsys/`: `shot_render.py` and every file it imports or reads, including `geom.py`, the render profiles and the material library. A module list check fails the pack if shot_render's imports outgrow the list.

`MANIFEST.json` lists every other file with its sha256 and size. Missing, changed or unlisted files all fail verification.

## Cloud side

- **Make a package locally or in a cloud session.** Run `python3 pipeline/production/bake_package.py --shot <shot.scene.json> --blender <blender> [--frames A-B] [--smoke 1-2]`. Output goes to `build/bake_packages/`, and `--smoke` renders a few tiny frames from the unpacked zip as a self-check. To pack an existing bake, use `--from-bake <run>/bake.json`. To verify a package, use `--verify <zip|folder>`.
- **Workflow.** `.github/workflows/bake_package.yml` is manual only, runs on `ubuntu-24.04` with a read-only token and no secrets, and keeps the artifact for 14 days. It installs the quality gate's pinned dependencies, builds `plush-render`, packs, smoke-renders frames 1–2 and uploads the zip with its sha256. The sha256 also goes to the run summary.
- **Fallback if artifacts are awkward.** Commit the *unpacked* package folder to a branch, never the zip: GitHub refuses files over 100 MB, and the e912 s010 zip is 122 MB while its largest file is a 42 MB master. Put the folder under `bake_packages/` beside a `bake_packages/.gitattributes` containing `* -text`. Without that file, Windows line-ending conversion would change the JSON hashes. Keep the `.gitattributes` outside the package folder, because an unlisted file fails verification. On the PC, run `git fetch origin bake/<name>` and `git checkout bake/<name> -- bake_packages/<name> bake_packages/.gitattributes`, then `tools\pc\render_package.cmd bake_packages\<name>`. The command accepts a folder as well as a zip.

## Tests

`python3 pipeline/production/tests/test_bake_package.py` runs fast, with no Blender and no engine. It checks:

- **Determinism:** same input gives the same MANIFEST and zip, and one changed input changes only its own hashes.
- **Completeness:** a lone zip renders in a clean folder with the source tree deleted and no engine on PATH. A fake Blender checks every path shot_render reads.
- **Verification failures:** a changed, missing or unlisted file, or a zip entry outside the package, stops the run before Blender starts.
- **Missing profile:** an absent profile, including `preview_eevee`, fails with a clear message.
- **Render code list:** the packaged list covers shot_render's imports.
