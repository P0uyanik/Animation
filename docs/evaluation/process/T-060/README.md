# T-060 Windows build evidence

**Status on 2026-11-18.** MSVC built the engine, render and export CLIs, studio job runner and complete test binary. All 104 C++ cases passed. The three frozen renders passed on an earlier build. The requested gate exited 1. The desktop studio build and a single all-green CTest run still need proof. Hosted Windows and Linux results are pending the relay push.

## Reproduction

Branch `t-060-codex-windows-ci` started at `3c9fcfb7b72e`, the local `origin/staging` tip. The comparison ref `origin/main` was `de5082d541de`. The machine used VS 2022 Build Tools, x64 MSVC 19.44.35230, SDK 10.0.26100.0, Ninja 1.12.1 and CMake 3.31.6. Python was Blender's standalone CPython 3.13.13. The owner's CPython 3.14 executable denied access.

The relay had installed the `x64-windows` manifest at vcpkg revision `528cfa41f4b1578b16ac6b2f6d2e6f98e5308d2d` and OIDN 2.3.3 at `C:\AnimationWT\ci-temp\oidn\oidn-2.3.3.x64.windows`. The OIDN bin directory was on PATH. The following configures the same full target set offline in an x64 developer shell. When the ImGui docking checkout is available, add `-DFETCHCONTENT_SOURCE_DIR_IMGUI=<checkout>` to the configure command.

```powershell
cmake -S . -B build/quality-gate -G Ninja -DCMAKE_BUILD_TYPE=Release `
  -DPLUSH_BUILD_STUDIO=ON -DPLUSH_BUILD_TESTS=ON -DVCPKG_MANIFEST_INSTALL=OFF `
  "-DVCPKG_INSTALLED_DIR=$pwd/vcpkg_installed" "-DPLUSH_OIDN_ROOT=$env:PLUSH_OIDN_ROOT" `
  -DFETCHCONTENT_FULLY_DISCONNECTED=ON
python tools/check_all.py --base origin/main
```

Full configuration found OIDN, then stopped at the missing ImGui source pin `cf53467ab0db7a783f04b32dd9160e6aa5b720ef`. The manifest does not supply this separate FetchContent dependency. The copy bundled in Embree tutorials is 1.89.1 WIP and lacks the docking API. Nothing was downloaded or substituted in the build.

Turning off only the GUI exposed the first compiler failure in the clip tests. For the final diagnostic build, a local CMake project include under `build/` also registered the actual studio job-runner library with C++23 and its normal link dependencies. That let the existing `tests/CMakeLists.txt` include `test_shot_workflow.cpp` and its existing fixture definitions. The resulting executable contains every test source used by the studio-enabled build.

```text
-- The CXX compiler identification is MSVC 19.44.35230.0
-- Plush: Open Image Denoise found - denoising enabled
Cannot find source file: .../build/quality-gate/_deps/imgui-src/imgui.cpp
tests\test_clips.cpp(7): fatal error C1083: ... "unistd.h": No such file or directory
shot_workflow.cpp(5): fatal error C1083: ... "sys/wait.h": No such file or directory
```

## Root causes and changes

* The clip and studio tests used POSIX process IDs, environment calls, signals and shell fixtures. On Windows they now use the CRT and native Python child processes. The tests still check progress, all four members of a nested tree, graceful cancellation, forced cancellation, and the disappearance of every observed PID.
* The studio depended on `fork`, `execvp`, `waitpid`, signals, `/proc` and `ps`. The Windows implementation creates the child suspended, assigns it to a kill-on-close Job Object, and then resumes it. It forwards arguments and redirects the job's streams. Cancellation sends a console break, allows the grace period, then terminates survivors. A forced-cancel test exposed that the job's active count can reach zero before a child releases its log. Cancellation now also waits for observed process handles to signal.
* Polling status with an MSVC file stream could deny the producer permission to atomically replace `status.json`. This reproduced as a child exiting 1 with progress stuck at two of three frames. The Windows status reader opens the file with delete sharing. Windows also uses its native time conversion and normalizes CRLF in displayed log tails.
* The Windows workflow selected Ninja without initializing the x64 MSVC environment. It installed the manifest in the source root before the trial merge, and CMake used a second install location under the build directory. The source-root packages appeared as untracked task changes. The revised Windows job trial-merges first, selects VS 2022 and cl, and uses CMake's build-local manifest install tree. The gate now propagates its exit code. Previously `exit 0` could make the Windows job appear successful with a failing report.
* The relay's cold vcpkg log measured **1.8 h**, including **1.4 h** for Embree. The old timeout was 120 minutes. Windows now allows up to 360 minutes and saves binary packages immediately after install. The cache key includes the triplet, MSVC toolset version, vcpkg ports revision and manifest/configuration hash. Restore by the same toolchain prefix permits reuse of unchanged package ABIs after a manifest edit.

The compiler and runtime failures above were observed locally. The workflow findings come from its configuration and the relay's dependency log. A hosted run is still needed to establish which failure a particular GitHub runner reaches first.

## Local wall-clock evidence

| Check | Result | Seconds |
| --- | --- | ---: |
| Exact `python tools/check_all.py --base origin/main` | FAIL, full tier selected | 73.17 |
| Frozen assets / shared-systems lint in that gate | PASS / PASS | 0.58 / 0.24 |
| Full studio configure in that gate, preseeded cache | FAIL, missing ImGui | 0.20 |
| Diagnostic configure, then clean MSVC Release build (47 Ninja actions) | PASS | 0.23 / 121.67 |
| CTest after clean build | 1 of 4 passed, host blocked the renderer | 101.74 |
| Complete `plush_tests` under CTest | 104 of 104 passed | 100.00 |
| Complete `plush_tests` invoked directly | 104 of 104 passed, 33,593 assertions | 67.55 |
| Job-runner case repeated after both race fixes | 8 of 8 runs passed | 1.74–1.86 each |
| Python tests / documentation links, separately timed | PASS / PASS | 117.07 / 0.51 |
| Python tests and links inside the exact gate | PASS | 69.49 |

The Python gate reported its built-in Pillow image-comparison skip. The cleanup suite reported 25 tests, zero failures and three skips. PyYAML was absent, and two rehearsal tests also have a Windows skip condition.

| Earlier CTest render | Measured RMSE | Existing limit | Seconds |
| --- | ---: | ---: | ---: |
| Milestone 01 | 0.0164 | 0.0300 | 26.59 |
| Neutral face | 0.0054 | 0.0300 | 4.42 |
| ABC lineup | 0.0014 | 0.0300 | 20.19 |

That earlier CTest invocation failed to start its test binary. After the clean build, CTest ran the complete unit suite, but could not start the renderer. Direct retries of the same renderer confirmed Windows Application Control error 4551. Its SHA-256 was `085b8b2aac57673a1b345b599f44b5e5fb857931cbe9a3bdd5dd9b47632fdcfe`. The two runs give evidence for each test individually. Both CTest invocations returned failure.

```text
[doctest] test cases:   104 |   104 passed | 0 failed | 0 skipped
[doctest] assertions: 33593 | 33593 passed | 0 failed |
[doctest] Status: SUCCESS!
[WinError 4551] Eine Anwendungssteuerungsrichtlinie hat diese Datei blockiert
```

The local gate report is in `build/check-all/check_all.json`. Diagnostic build and final test logs are in `build/verified/`. The earlier CTest output is in `build/headless-tests.log`. A separate MSVC syntax check of the original committed studio sources reproduced the missing `pid_t` and `sys/wait.h` errors in `build/original-studio/msvc.log`.

## Files and ownership

Inside the recorded T-060 row are `.github/workflows/checks.yml` (Windows job only) and this report. The following seven files are pure portability changes authorized by the task and outside the narrower row in `docs/process/OWNERSHIP.md`.

| File | Change |
| --- | --- |
| `apps/studio/CMakeLists.txt` | Compile the native job implementation on Windows |
| `apps/studio/main.cpp` | Platform process diagnostics and orphan checks |
| `apps/studio/shot_job_windows.cpp` | Windows process tree, status reads, logging and cancellation |
| `apps/studio/shot_workflow.cpp` | POSIX implementation boundary, platform time and log handling |
| `apps/studio/shot_workflow.h` | Platform process ID, job handles, Python executable and member-query interface |
| `tests/test_clips.cpp` | Native PID for independent temporary fixtures |
| `tests/test_shot_workflow.cpp` | Portable environment/path checks and equivalent Windows process-tree fixtures |

The nine task paths classify as **fast** against staging. The 64 pre-existing differences between `origin/main` and `origin/staging` already classify as **full**, including character specs and baselines. The exact gate also saw the relay's untracked `vcpkg_installed/` and pre-existing CRLF differences under the session's Git settings. It failed the guarded-path and write-set checks. Blender was unavailable on PATH for that full-tier invocation. The frozen check passed, and none of the nine task paths occurs in the frozen manifest. All original regression thresholds remain in force.

## Hosted proof and required-check decision

The relay owns the commit and push. Before the proof run, the Supervisor needs to reconcile the seven paths with the recorded claim and approve the three guarded paths: `.github/workflows/checks.yml`, `tests/test_clips.cpp` and `tests/test_shot_workflow.cpp`. The gate reads the Supervisor's per-path approval trailers from committed history.

Trigger the Windows job with `[ci windows]` in the head commit message or by workflow dispatch. Record the Windows run URL, tested branch SHA, staging SHA and the passing `quality-windows` report. When staging is an ancestor of the branch, the trial merge tests the branch tree itself. If staging has advanced independently, retain distinct passing evidence for the branch and merged trees. The Linux job supplies Linux regression evidence.

**Proposal to the Supervisor.** Make the existing Gate verdict require Windows on scheduled Windows runs after the branch, trial merge and staging have passing hosted reports. Until then its informational setting is appropriate. This task leaves that decision with the Supervisor.
