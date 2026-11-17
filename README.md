# Plush Studio

A reusable character-production and animation platform for short plush / felt / wool episodes (target: complete
2–2.5 min episodes). Three parts, each with one job (TD-37..TD-42 in [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md)):

- **Plush Studio** (`apps/studio`, C++): the product. Projects, characters, versions, episodes, shots, timeline and
  the production workflow.
- **Blender 5.3, headless** (`pipeline/charsys/`): the internal production backend. Character geometry, rig, face,
  hair, clothing, materials and the final Cycles render. Never the user-facing application.
- **C++ engine** (`engine/`): runtime animation (actions, clips, emotions, IK, interaction, life layer, playback) and
  the bake hand-off to Blender. Its path tracer is for previews and the image regressions.

Production path: character spec → Blender master (versioned asset store) → engine package → shot scene → engine bake
→ Blender render, one command per shot (`pipeline/production/run_shot.py`). Details:
[docs/PRODUCTION_PIPELINE.md](docs/PRODUCTION_PIPELINE.md),
[docs/CHARACTER_REUSABILITY.md](docs/CHARACTER_REUSABILITY.md),
[docs/CHARACTER_SYSTEM_VERSIONS.md](docs/CHARACTER_SYSTEM_VERSIONS.md). Status and plans:
[CURRENT_STATUS.md](CURRENT_STATUS.md) (pointers to the task log and roadmap).

Requirements: the C++ build below for the engine, Studio and `plush-render` (CPU only, no GPU needed). Character
builds, final renders and the full test tier need Blender 5.3 (or the `bpy` 5.3 module); the quality gate is
`tools/check_all.py` ([docs/process/GATE.md](docs/process/GATE.md)).

## What is in the box

| Path | What |
| --- | --- |
| `engine/` | Engine modules: `core`, `geom`, `anim`, `fuzz`, `model`, `scene`, `render` |
| `apps/studio` | **Plush Studio**, the desktop application (Dear ImGui + OpenGL 3.3 preview) |
| `apps/render-cli` | `plush-render`, headless engine renderer for stills, sequences and video (previews, regressions) |
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
