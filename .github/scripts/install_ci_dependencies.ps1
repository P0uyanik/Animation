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
& python -m pip install --disable-pip-version-check $bpyWheel
if ($LASTEXITCODE -ne 0) { throw 'installing the verified bpy wheel failed' }
& python -c "import bpy; assert bpy.app.version_string.startswith('$($pins.bpy.version)'); print(bpy.app.version_string)"
if ($LASTEXITCODE -ne 0) { throw 'the pinned bpy module failed its import/version check' }

if ($Platform -eq 'windows') {
    $shim = Join-Path $env:RUNNER_TEMP 'plush-bpy-blender.cmd'
    $python = (Get-Command python).Source
    Set-Content -LiteralPath $shim -Encoding ASCII -Value "@`"$python`" `"$root\tools\bpy_blender.py`" %*"
} else {
    $shim = Join-Path $env:RUNNER_TEMP 'plush-bpy-blender'
    $python = (Get-Command python).Source
    $body = "#!/usr/bin/env bash`nexec `"$python`" `"$root/tools/bpy_blender.py`" `"`$@`"`n"
    Set-Content -LiteralPath $shim -Encoding utf8NoBOM -Value $body
    & chmod +x $shim
    if ($LASTEXITCODE -ne 0) { throw 'making the bpy shim executable failed' }
}
"BLENDER=$shim" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
