# Plush Studio

A personal, standalone 3D animation production application for stylized plush / felt / wool
characters (see `docs/` and the state files in this folder). No Blender, no cloud, no GPU required.

## What is in the box

| Path | What |
| --- | --- |
| `engine/` | Engine modules: `core`, `geom`, `anim`, `fuzz`, `model`, `scene`, `render` |
| `apps/studio` | **Plush Studio**, the desktop application (Dear ImGui + OpenGL 3.3 preview) |
| `apps/render-cli` | `plush-render`, headless renderer for stills, sequences and video |
| `content/` | Characters (`*.character.json`) and scenes (`*.scene.json`) |
| `tests/` | Unit and integration tests (doctest) |

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
