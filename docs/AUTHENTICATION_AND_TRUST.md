# Authentication and trust boundaries

Plush Studio is a standalone, local production application. It does not expose an HTTP service and does not
implement user accounts, sign-in, sessions, cookies, OAuth, API keys, JWTs, access tokens or refresh tokens.
The operating-system account that launches the application is the security boundary: that account's filesystem
and process permissions determine which scenes, character packages, executables and output directories the
application can use.

## Components

| Component | Authentication responsibility |
| --- | --- |
| `apps/studio` | Local Dear ImGui/OpenGL UI. It opens project files and starts local production jobs; it has no identity layer. |
| `apps/studio/shot_workflow.*` | Converts UI actions into an argument vector for `run_shot.py`, launches it in a child process group and reads local status/log files. |
| `pipeline/production/run_shot.py` | Orchestrates the `prepare`, `bake`, `render` and `encode` stages using local files and subprocesses. |
| `apps/render-cli` and `engine/` | Parse scene and character data, evaluate animation and write bake or image outputs. |
| Blender and FFmpeg | External executables selected or discovered locally and run as subprocesses. |

## Local job flow

1. A user opens a scene or shot in Studio and chooses Prepare or Render.
2. Studio saves the source document, creates a run ID and constructs a `run_shot.py` command line.
3. The workflow starts the command as a local child process and redirects its output to the run log.
4. `run_shot.py` resolves the cast and packages, calls `plush-render --bake`, calls Blender to render the baked
   animation and optionally calls FFmpeg to encode a video.
5. Studio observes progress and results by reading `status.json`, logs and rendered frames from the run directory.

There is no client/server request authentication in this path. The workflow communicates through process
arguments and files. See [PRODUCTION_PIPELINE.md](PRODUCTION_PIPELINE.md) for the complete stage and run-folder
contract.

## Configuration, credentials and tokens

The production workflow accepts the Blender executable through `--blender`, `PLUSH_BLENDER` or the Studio
settings file selected by `PLUSH_STUDIO_SETTINGS`. These values are executable paths, not credentials, and should
not contain secrets.

Published character masters are checked against SHA-256 values in their manifests. Those hashes provide integrity
checking and cache identity; they are not authentication credentials.

The runtime does not read GitHub credentials. Credentials used to clone, fetch or push this repository are managed
outside Plush Studio by Git or the caller's GitHub integration. Build-time `FetchContent` downloads are likewise
separate from the runtime architecture.

## Security implications

Project files, executable paths and environment variables are trusted local inputs. Run Plush Studio only on
projects and character packages you trust. If the application is later exposed as a networked or multi-user
service, authentication, authorization, credential storage, tenant isolation and request validation must be added
as explicit components rather than inferred from this local trust model.

