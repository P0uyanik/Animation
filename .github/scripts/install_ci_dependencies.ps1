param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('linux', 'windows')]
    [string]$Platform,
    # C++ tier: Ubuntu packages (linux; vcpkg stays the Windows path). No Embree/OIDN: the default build has
    # PLUSH_BUILD_RENDERER=OFF (T-085).
    [switch]$Cpp,
    # Renderer job only (PLUSH_BUILD_RENDERER=ON): Embree (apt renderer_packages on linux; the vcpkg "renderer"
    # feature on Windows) and the pinned OIDN 2.3.3 prebuilt, which the frozen image regressions need (without
    # OIDN: rmse 0.046 > 0.03, T-001 finding).
    [switch]$Renderer,
    # Blender tier: the checksum-pinned bpy wheel, Pillow and a `blender` shim (tools/bpy_blender.py).
    [switch]$Bpy,
    # T-127 pinned apt cache (linux): a folder kept by actions/cache, keyed on the runner image version and
    # ci-dependencies.json. Filled on a miss from the mirrors; on a hit the recorded .deb files (sha256 re-verified)
    # are installed with dpkg, no mirror contact. Any problem with the cache falls back to the mirror install.
    [string]$AptCache = ''
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

if (-not $Cpp -and -not $Renderer -and -not $Bpy) { throw 'nothing to install: pass -Cpp, -Renderer and/or -Bpy' }

function Test-AptInstalled([string[]]$Packages) {
    foreach ($package in $Packages) {
        $state = & dpkg-query -W -f='${Status}' $package 2>$null
        if ($LASTEXITCODE -ne 0 -or $state -ne 'install ok installed') { return $false }
    }
    return $true
}

function Install-AptFromCache([string[]]$Packages) {
    $manifestPath = Join-Path $AptCache 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { Write-Host 'apt cache: empty (first run on this image)'; return $false }
    try {
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        if ($manifest.packages -ne (($Packages | Sort-Object) -join ' ') -or $manifest.image -ne "$env:ImageOS/$env:ImageVersion") {
            Write-Host 'apt cache: recorded for other packages or another runner image'; return $false
        }
        $debs = @()
        foreach ($deb in @($manifest.debs | Where-Object { $_ })) {
            $path = Join-Path $AptCache "archives/$($deb.file)"
            if (-not (Test-Path -LiteralPath $path) -or (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $deb.sha256) {
                Write-Warning "apt cache: $($deb.file) missing or checksum differs"; return $false
            }
            $debs += $path
        }
        if ($debs.Count -gt 0) {
            & sudo env DEBIAN_FRONTEND=noninteractive dpkg -i @debs
            if ($LASTEXITCODE -ne 0) { Write-Warning 'apt cache: dpkg -i failed'; return $false }
        }
        if (-not (Test-AptInstalled $Packages)) { Write-Warning 'apt cache: packages not installed after dpkg'; return $false }
        Write-Host "apt cache: installed $($debs.Count) pinned .deb file(s), digest sha256:$((Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant())"
        return $true
    } catch {
        Write-Warning "apt cache: $_"; return $false
    }
}

function Install-AptPackages([string[]]$Packages) {
    if ($AptCache -and (Install-AptFromCache $Packages)) { return }
    # Fallback / first fill: the mirror install as before T-127, with retries for mirror outages (503, 2026-11-19).
    $updated = $false
    foreach ($wait in 0, 20, 60) {
        if ($wait) { Write-Warning "apt-get update failed; retrying in $wait s"; Start-Sleep -Seconds $wait }
        & sudo apt-get update -q
        if ($LASTEXITCODE -eq 0) { $updated = $true; break }
    }
    if (-not $updated) { throw 'apt-get update failed' }
    $archives = ''
    if ($AptCache) {
        $archives = Join-Path $AptCache 'archives'
        if (Test-Path -LiteralPath $AptCache) { & sudo rm -rf $AptCache }
        New-Item -ItemType Directory -Force -Path (Join-Path $archives 'partial') | Out-Null
        & sudo apt-get install -y -q --no-install-recommends --download-only -o "Dir::Cache::archives=$archives" @Packages
        if ($LASTEXITCODE -ne 0) { Write-Warning 'apt cache: download failed, installing without the cache'; $archives = '' }
        else {
            # Recorded before the install, so an apt clean-up hook cannot empty the list.
            & sudo chown -R "$(& id -u):$(& id -g)" $AptCache
            $debs = @(Get-ChildItem -LiteralPath $archives -Filter '*.deb' | Sort-Object Name | ForEach-Object {
                [ordered]@{ file = $_.Name; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant() }
            })
        }
    }
    $installed = $false
    foreach ($wait in 0, 20) {
        if ($wait) { Write-Warning "apt-get install failed; retrying in $wait s"; Start-Sleep -Seconds $wait }
        if ($archives) {
            & sudo apt-get install -y -q --no-install-recommends -o "Dir::Cache::archives=$archives" @Packages
        } else {
            & sudo apt-get install -y -q --no-install-recommends @Packages
        }
        if ($LASTEXITCODE -eq 0) { $installed = $true; break }
    }
    if (-not $installed) { throw 'apt-get install failed' }
    if ($archives) {
        & sudo chown -R "$(& id -u):$(& id -g)" $AptCache
        $manifest = [ordered]@{
            schema = 'plush.apt-cache/1'; image = "$env:ImageOS/$env:ImageVersion"
            packages = (($Packages | Sort-Object) -join ' '); debs = $debs
        }
        $manifest | ConvertTo-Json -Depth 4 | Out-File -FilePath (Join-Path $AptCache 'manifest.json') -Encoding utf8
        Write-Host "apt cache: recorded $($debs.Count) .deb file(s) for $env:ImageOS/$env:ImageVersion"
    }
}

if ($Cpp -and $Platform -eq 'linux') {
    $packages = @($pins.apt.packages)
    if ($Renderer) { $packages += @($pins.apt.renderer_packages) }
    Install-AptPackages $packages
} elseif ($Renderer -and $Platform -eq 'linux') {
    Install-AptPackages @($pins.apt.renderer_packages)
}

if ($Renderer) {
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
    }
    # No LD_LIBRARY_PATH on linux: CMake's build-tree rpath finds OIDN, and setup-python owns that variable.
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
