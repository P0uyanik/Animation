param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('linux', 'windows')]
    [string]$Platform,
    # C++ tier: Ubuntu packages (linux; vcpkg stays the Windows path) and the pinned OIDN 2.3.3 prebuilt, which
    # the frozen image regressions need (without OIDN: rmse 0.046 > 0.03, T-001 finding).
    [switch]$Cpp,
    # Blender tier: the checksum-pinned bpy wheel, Pillow and a `blender` shim (tools/bpy_blender.py).
    [switch]$Bpy
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pins = Get-Content -Raw -LiteralPath (Join-Path $root '.github/ci-dependencies.json') | ConvertFrom-Json
# Cached by actions/cache (key: hash of ci-dependencies.json); every file is re-verified before use.
$download = Join-Path $env:RUNNER_TEMP 'plush-pinned-dependencies'
New-Item -ItemType Directory -Force -Path $download | Out-Null

function Get-VerifiedFile {
    param([string]$Name, [string]$Url, [string]$Sha256)
    $target = Join-Path $download $Name
    if (Test-Path -LiteralPath $target) {
        $cached = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
        if ($cached -eq $Sha256.ToLowerInvariant()) {
            Write-Host "verified $Name ($cached, cached)"
            return $target
        }
        Remove-Item -LiteralPath $target -Force
    }
    Invoke-WebRequest -Uri $Url -OutFile $target
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    if ($actual -ne $Sha256.ToLowerInvariant()) {
        throw "checksum mismatch for $Name (expected $Sha256, got $actual)"
    }
    Write-Host "verified $Name ($actual)"
    return $target
}

function Add-Env([string]$Name, [string]$Value) {
    "$Name=$Value" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
}

if (-not $Cpp -and -not $Bpy) { throw 'nothing to install: pass -Cpp and/or -Bpy' }

if ($Cpp) {
    # OIDN source archive stays pinned (reviewed input); the prebuilt binary is what the build links.
    $oidnName = "oidn-$($pins.oidn.version).src.tar.gz"
    Get-VerifiedFile -Name $oidnName -Url $pins.oidn.url -Sha256 $pins.oidn.sha256 | Out-Null
    $pre = $pins.oidn.prebuilt.$Platform
    $archive = Get-VerifiedFile -Name (Split-Path -Leaf $pre.url) -Url $pre.url -Sha256 $pre.sha256
    $oidnDir = Join-Path $env:RUNNER_TEMP 'oidn'
    New-Item -ItemType Directory -Force -Path $oidnDir | Out-Null
    if ($Platform -eq 'windows') {
        Expand-Archive -LiteralPath $archive -DestinationPath $oidnDir -Force
    } else {
        & tar -xzf $archive -C $oidnDir
        if ($LASTEXITCODE -ne 0) { throw 'extracting OIDN failed' }
    }
    $oidnRoot = Join-Path $oidnDir $pre.folder
    if (-not (Test-Path -LiteralPath (Join-Path $oidnRoot 'include'))) { throw "OIDN layout unexpected: $oidnRoot" }
    Add-Env 'PLUSH_OIDN_ROOT' $oidnRoot
    if ($Platform -eq 'windows') {
        "$oidnRoot\bin" | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
    } else {
        $packages = @($pins.apt.packages)
        & sudo apt-get update -q
        if ($LASTEXITCODE -ne 0) { throw 'apt-get update failed' }
        & sudo apt-get install -y -q --no-install-recommends @packages
        if ($LASTEXITCODE -ne 0) { throw 'apt-get install failed' }
        Add-Env 'LD_LIBRARY_PATH' "$oidnRoot/lib"
    }
}

if ($Bpy) {
    $bpyPin = $pins.bpy.$Platform
    $bpyName = Split-Path -Leaf $bpyPin.url
    $bpyWheel = Get-VerifiedFile -Name $bpyName -Url $bpyPin.url -Sha256 $bpyPin.sha256
    & python -m pip install --disable-pip-version-check $bpyWheel
    if ($LASTEXITCODE -ne 0) { throw 'installing the verified bpy wheel failed' }
    & python -m pip install --disable-pip-version-check 'Pillow==11.3.0'
    if ($LASTEXITCODE -ne 0) { throw 'installing the pinned Pillow dependency failed' }
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
    Add-Env 'BLENDER' $shim
}
