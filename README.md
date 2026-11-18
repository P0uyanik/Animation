# Plush Studio

A reusable character-production and animation platform for short plush / felt / wool episodes (target: complete
2–2.5 min episodes). How it works today (TD-37..TD-43 in [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md)):

1. **Character spec (JSON)** → the shared **Blender generators** (`pipeline/charsys/`, Blender 5.3 headless) build
   each character: geometry, rig, face, hair, clothing, materials. Approved versions are stored immutably in the
   asset store (`assets/characters/<id>/versions/`).
2. The **C++ engine** (`engine/`) owns animation: clips, emotions, face, body mechanics, interaction, life layer. It
   writes the shot bake (`plush.shot_bake/1`).
3. **Blender Cycles renders the final shots** from the bake (TD-42). Look, material and render work happens only here.
4. **Python tools** drive and check it: `pipeline/production/run_shot.py` (one command per shot), fidelity
   (`tools/fidelity/`), regression (`tools/regression/`) and the quality gate (`tools/check_all.py`,
   [docs/process/GATE.md](docs/process/GATE.md)).

**Plush Studio** (`apps/studio`) and the engine's path tracer (`plush-render`) are for previews and the existing image
tests; the engine renderer is frozen (no new features, TD-43). Details:
[docs/PRODUCTION_PIPELINE.md](docs/PRODUCTION_PIPELINE.md),
[docs/CHARACTER_REUSABILITY.md](docs/CHARACTER_REUSABILITY.md),
[docs/CHARACTER_SYSTEM_VERSIONS.md](docs/CHARACTER_SYSTEM_VERSIONS.md). Status and plans:
[CURRENT_STATUS.md](CURRENT_STATUS.md) (pointers to the task log and roadmap).

Requirements: the C++ build below (CPU only, no GPU needed) for the engine, Studio and `plush-render`. Character
builds, final renders and the full test tier need Blender 5.3 (or the `bpy` 5.3 module).

## What is in the box

| Path | What |
| --- | --- |
| `engine/` | Engine modules: `core`, `geom`, `anim`, `fuzz`, `model`, `scene`, `render` |
| `apps/studio` | **Plush Studio**, the desktop application (Dear ImGui + OpenGL 3.3 preview) |
| `apps/render-cli` | `plush-render`: engine bake (`--bake`) and the frozen preview renderer (stills, sequences, image regressions) |
| `pipeline/` | Blender backend (`charsys/`), clip tools (`clips/`), shot production (`production/run_shot.py`) |
| `assets/characters/` | Character specs, references and the versioned asset store |
| `content/` | Clips, emotions, scenes, and the engine-era SDF characters used by the image regressions |
| `episodes/` | Episodes and shots |
| `tools/` | Quality gate, regression, fidelity and process tools |
| `docs/AUTHENTICATION_AND_TRUST.md` | Local trust boundary, job flow, and credential/token handling |
| `tests/` | C++ unit and integration tests (doctest) and the frozen image regressions (CTest) |

## Build (Linux, verified)

```bash
sudo apt install cmake ninja-build g++ libembree-dev libglfw3-dev libglew-dev libglm-dev \
  nlohmann-json3-dev libstb-dev doctest-dev ffmpeg
# Optional denoiser: download oidn-2.x.x.x86_64.linux.tar.gz from github.com/RenderKit/oidn/releases
cmake -S . -B build -G Ninja -DPLUSH_OIDN_ROOT=/path/to/oidn-2.3.3.x86_64.linux
cmake --build build
./build/tests/plush_tests
```

## Build (Windows, not yet verified)

Install Visual Studio 2022 and vcpkg, then:

```bat
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake -DPLUSH_OIDN_ROOT=C:/path/to/oidn-2.3.3.x64.windows
cmake --build build --config Release
```

## Run

```bash
./build/apps/studio/plush-studio content/scenes/milestone01_classroom.scene.json
./build/apps/render-cli/plush-render content/scenes/milestone01_classroom.scene.json --frame 1 --out frame.png
./build/apps/render-cli/plush-render content/scenes/milestone01_classroom.scene.json --frames 1-48 \
    --outdir renders/m01 --video renders/m01.mp4      # resumes automatically if interrupted
```

Run both from the repository root (scene paths are relative).
