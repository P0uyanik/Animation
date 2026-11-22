# From the worktree root, with the three relay ZIPs under build/t208-data.
# Use a fresh build/t208-run. The saved Vulkan scene is reused for the OpenGL retry.
$ErrorActionPreference = 'Stop'
$p = 'C:/AnimationWT/t106-codex/build/perf-venv/Scripts/python.exe'
$b = 'D:/Animation/tools/blender-5.3/blender.exe'
$d = 'docs/evaluation/rendering/T-208'
$w = 'build/t208-run'
New-Item -ItemType Directory -Path $w | Out-Null
foreach ($zip in Get-ChildItem build/t208-data/*/*.bake.zip) {
    Copy-Item -LiteralPath $zip.FullName -Destination $w
    & $p -B tools/pc/render_package.py "$w/$($zip.Name)" --verify-only
    if ($LASTEXITCODE) { throw "Package verification failed" }
}
& $p -Bu "$d/run.py" s020 eevee 125-172
# This run produced shot.blend before the Vulkan device loss.
Rename-Item -LiteralPath "$w/s020-eevee-125-172" -NewName 'vulkan-s020-125-172'
& $p -Bu "$d/retry.py" s020 vulkan-s020-125-172 opengl 125-172
if ($LASTEXITCODE) { throw "OpenGL retry failed" }
& $p -Bu "$d/queue.py"
if ($LASTEXITCODE) { throw "Frame queue failed" }
& $p -B "$d/measure.py"
& $p -B "$d/crop.py" s010 41 table.jpg 196 0 1100 680
& $p -B "$d/crop.py" s020 147 hand-over.jpg 280 120 1070 540
& $p -B "$d/crop.py" s030 140 walk-off.jpg 0 0 920 640
& $b -b --factory-startup --python-exit-code 3 -P "$d/encode.py" -- "$w/s020-eevee-125-172" "$d/s020-hand-over.mp4"
if ($LASTEXITCODE) { throw "Hand-over encoding failed" }
& $b -b --factory-startup --python-exit-code 3 -P "$d/encode.py" -- "$w/s030-eevee-93-140" "$d/s030-walk-off.mp4"
if ($LASTEXITCODE) { throw "Walk-off encoding failed" }

