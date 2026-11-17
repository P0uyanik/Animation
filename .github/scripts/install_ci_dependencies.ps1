param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('linux', 'windows')]
    [string]$Platform
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pins = Get-Content -Raw -LiteralPath (Join-Path $root '.github/ci-dependencies.json') | ConvertFrom-Json
$download = Join-Path $env:RUNNER_TEMP 'plush-pinned-dependencies'
New-Item -ItemType Directory -Force -Path $download | Out-Null

function Get-VerifiedFile {
    param([string]$Name, [string]$Url, [string]$Sha256)
    $target = Join-Path $download $Name
    Invoke-WebRequest -Uri $Url -OutFile $target
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    if ($actual -ne $Sha256.ToLowerInvariant()) {
        throw "checksum mismatch for $Name (expected $Sha256, got $actual)"
    }
    Write-Host "verified $Name ($actual)"
    return $target
}

# OIDN is optional in the C++ build. Verify the exact source archive now so any
# later enablement uses an immutable, reviewed input rather than a moving URL.
$oidnName = "oidn-$($pins.oidn.version).src.tar.gz"
Get-VerifiedFile -Name $oidnName -Url $pins.oidn.url -Sha256 $pins.oidn.sha256 | Out-Null

$bpyPin = $pins.bpy.$Platform
$bpyName = Split-Path -Leaf $bpyPin.url
$bpyWheel = Get-VerifiedFile -Name $bpyName -Url $bpyPin.url -Sha256 $bpyPin.sha256
$blenderPython = (Get-Command python).Source
& $blenderPython -m pip install --disable-pip-version-check $bpyWheel
if ($LASTEXITCODE -ne 0) { throw 'installing the verified bpy wheel failed' }
& $blenderPython -m pip install --disable-pip-version-check 'Pillow==11.3.0'
if ($LASTEXITCODE -ne 0) { throw 'installing Pillow into the Blender Python failed' }
& $blenderPython -c "import bpy, PIL; assert bpy.app.version_string.startswith('$($pins.bpy.version)'); print(bpy.app.version_string, PIL.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'the pinned bpy module failed its import/version check' }

if ($Platform -eq 'windows') {
    $shim = Join-Path $env:RUNNER_TEMP 'plush-bpy-blender.cmd'
    Set-Content -LiteralPath $shim -Encoding ASCII -Value "@`"$blenderPython`" `"$root\tools\bpy_blender.py`" %*"
} else {
    $shim = Join-Path $env:RUNNER_TEMP 'plush-bpy-blender'
    $body = "#!/usr/bin/env bash`nexec `"$blenderPython`" `"$root/tools/bpy_blender.py`" `"`$@`"`n"
    Set-Content -LiteralPath $shim -Encoding utf8NoBOM -Value $body
    & chmod +x $shim
    if ($LASTEXITCODE -ne 0) { throw 'making the bpy shim executable failed' }
}
"BLENDER=$shim" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
