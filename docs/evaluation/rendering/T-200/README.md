# T-200 · Local e912 preview

**Smart App Control blocked the unsigned native bake engine.** On 2026-11-22 at 13:53:39 UTC, after all three cast exports, Python's `CreateProcess` returned WinError 4551 launching `C:\AnimationWT\t197-codex\build\t197\engine\apps\render-cli\plush-render.exe`. Code Integrity record 1099 (event 3077) names that file and the enforced `VerifiedAndReputableDesktop` policy. Records 1100 and 1101 share its activity ID and report zero signatures (3089) and a Smart App Control block (3118). The executable's SHA-256 matches the event's flat hash.

**Bake availability.** The production bake stage calls the same executable from any Python interpreter, including Blender's. Blender consumes the resulting `bake.json`. A search of local Git refs and the project worktrees under `C:\AnimationWT`, `D:\Animation\wt` and `D:\Animation\code` found no e912 shot bake or assembled shot blend. The T-187 preview contains rendered pixels. The checked-in CI workflows identify no dedicated e912 bake artifact.

**Owner options, safest first**

1. Retrieve the original s020 and s030 bakes from the T-187 producer, or regenerate them on a trusted Linux build runner at the matching project revision. Transfer both bake JSONs and cast/version manifests, verify hashes and resolve the cast packages locally. Render with the T-197 profile on the MX350.
2. For recurring native bakes, obtain a matching project build signed by a publisher trusted by the active policy. Verify its signature and provenance. The local T-197 rebuild produced the unsigned binary identified above.
3. Approve a WSL installation for Linux-side baking if local regeneration is essential. WSL is currently absent.

**Measurements.** Zero real-shot frames rendered. The s020 hand-over, s030 walk-off (5b), 48-frame flicker strip and matched Cycles CPU stills remain unmeasured, including seconds/frame, peak VRAM and visible motion differences. [Benchmark status](bench.csv)

**Read-only verification** in PowerShell from the worktree root. The Code Integrity log and registry were readable. The optional Defender status query returned access denied in the sandbox.

```powershell
$log = 'Microsoft-Windows-CodeIntegrity/Operational'
Get-WinEvent -LogName $log -FilterXPath '*[System[(EventRecordID >= 1099 and EventRecordID <= 1101)]]' | ForEach-Object { $_.ToXml() }
$run = 'C:\AnimationWT\t197-codex\build\t197'
Get-FileHash "$run\engine\apps\render-cli\plush-render.exe" -Algorithm SHA256
Get-Content "$run\prepare.log" -Tail 12
Get-ItemPropertyValue 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' VerifiedAndReputablePolicyState
Get-MpComputerStatus | Select-Object SmartAppControlState
git grep -n 'cmd = \[a.bake_engine' -- pipeline/production/run_shot.py
```

**Windows checkout issue.** In `pipeline/clips`, `tools/cleanup` and `tools/motion_checks`, the tracked file `TESTS` collides with the directory `tests/` on this case-insensitive checkout. Git reports three pre-existing deletions.
