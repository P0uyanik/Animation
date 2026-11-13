#!/usr/bin/env bash
# Installs one pinned official Blender release for the Plush Studio backend (Linux x64).
#   pipeline/blender/install_blender.sh [version]      e.g. 4.5.4   (default: the version in pipeline/blender/BLENDER_VERSION)
# Downloads from download.blender.org, verifies the published SHA-256 checksum, unpacks to
# ~/.plush-studio/blender/<version>/ (outside the repository), and runs a headless version check.
# Idempotent: an existing verified installation is kept. Nothing in the repository is modified.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
version="${1:-$(grep -v '^#' "$here/BLENDER_VERSION" 2>/dev/null | head -1 | tr -d '[:space:]')}"
[ -n "$version" ] || { echo "no Blender version given or pinned" >&2; exit 2; }
series="${version%.*}"
root="${PLUSH_BLENDER_ROOT:-$HOME/.plush-studio/blender}"
dest="$root/$version"
name="blender-$version-linux-x64"
url="https://download.blender.org/release/Blender$series/$name.tar.xz"
if [ -x "$dest/$name/blender" ] && [ -f "$dest/VERIFIED" ]; then
  echo "[install] Blender $version already installed and verified at $dest/$name"
else
  mkdir -p "$dest"
  echo "[install] downloading $url"
  curl -fSL --retry 3 -o "$dest/$name.tar.xz" "$url"
  # Blender publishes one checksum file per release listing every package.
  curl -fsSL --retry 3 -o "$dest/checksums.sha256" "https://download.blender.org/release/Blender$series/$name.tar.xz.sha256" ||
    curl -fsSL --retry 3 -o "$dest/checksums.sha256" "https://download.blender.org/release/Blender$series/blender-$version.sha256"
  expected="$(grep "$name.tar.xz" "$dest/checksums.sha256" | awk '{print $1}' | head -1)"
  [ -n "$expected" ] || expected="$(awk 'NR==1{print $1}' "$dest/checksums.sha256")"
  actual="$(sha256sum "$dest/$name.tar.xz" | awk '{print $1}')"
  if [ "$expected" != "$actual" ]; then
    echo "[install] CHECKSUM MISMATCH: expected $expected, got $actual" >&2
    exit 3
  fi
  echo "[install] checksum OK ($actual)"
  tar -xJf "$dest/$name.tar.xz" -C "$dest"
  rm -f "$dest/$name.tar.xz"
  printf '%s  %s.tar.xz\n' "$actual" "$name" > "$dest/VERIFIED"
fi
"$dest/$name/blender" --background --factory-startup --version | head -3
echo "[install] blender executable: $dest/$name/blender"
