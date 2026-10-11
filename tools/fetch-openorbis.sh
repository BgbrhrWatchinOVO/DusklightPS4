#!/usr/bin/env bash
# Fetch the PacBrew OpenOrbis PS4 SDK without pacman: download each package listed in the
# repository database, check its SHA-256 against the database, and unpack it under sdk/.
# The SDK ends up in sdk/opt/pacbrew/ps4/openorbis (export OPENORBIS to that path).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="https://pacman.mydedibox.fr/pacbrew/packages"
DL="$ROOT/downloads/pacbrew"
SDK="$ROOT/sdk"

PACKAGES=(
    clang headers musl libcxx vars create-fself create-gp4 pkgtools orbis-lib-gen readoelf
    pkg-config zlib libpng bzip2
)

mkdir -p "$DL/db" "$SDK"
curl -fsS --max-time 60 -o "$DL/pacbrew.db" "$REPO/pacbrew.db"
rm -rf "$DL/db" && mkdir -p "$DL/db"
tar -xf "$DL/pacbrew.db" -C "$DL/db"

field() { awk -v k="%$2%" '$0 == k { getline; print; exit }' "$1"; }

for name in "${PACKAGES[@]}"; do
    desc=$(ls -d "$DL"/db/ps4-openorbis-"$name"-[0-9]*/ | head -1)/desc
    file=$(field "$desc" FILENAME)
    sha=$(field "$desc" SHA256SUM)
    if [ ! -f "$DL/$file" ] || ! echo "$sha  $DL/$file" | sha256sum -c --status; then
        echo "downloading $file"
        curl -fsS --max-time 1800 -o "$DL/$file.part" "$REPO/$file"
        mv "$DL/$file.part" "$DL/$file"
    fi
    echo "$sha  $DL/$file" | sha256sum -c --quiet
    tar -xf "$DL/$file" -C "$SDK" --exclude=.PKGINFO --exclude=.BUILDINFO --exclude=.MTREE --exclude=.INSTALL
done

echo "OpenOrbis SDK ready: $SDK/opt/pacbrew/ps4/openorbis"

# PacBrew installs to /opt/pacbrew; point the SDK's scripts, CMake file and pkg-config files at
# this unpacked copy instead (text files only).
grep -rlI '/opt/pacbrew' "$SDK/opt/pacbrew" --exclude-dir=include | while read -r f; do
    sed -i "s|/opt/pacbrew|$SDK/opt/pacbrew|g" "$f"
done
