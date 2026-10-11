#!/usr/bin/env bash
# Upload the packages to the PS4's /data/pkg (for GoldHEN's Package Installer) and, if given, the
# game's disc image to /data/dusklight-ps4/game.iso, over GoldHEN's FTP server.
#   upload.sh <ps4 ip> [disc image]
set -euo pipefail
source "$(dirname "$0")/env.sh"
HOST="${1:?usage: upload.sh <ps4 ip> [disc image]}"
DISC="${2:-}"
FTP="ftp://$HOST:${PS4_FTP_PORT:-2121}"

put() {  # put <local file> <remote path>
    echo "uploading $(basename "$1") -> $2 ($(du -h "$1" | cut -f1))"
    curl --fail --show-error --ftp-pasv --ftp-create-dirs --progress-bar -T "$1" "$FTP$2"
}

for pkg in "$PS4_PORT_ROOT"/out/*.pkg; do
    put "$pkg" "/data/pkg/$(basename "$pkg")"
done
if [ -n "$DISC" ]; then
    put "$DISC" /data/dusklight-ps4/game.iso
fi
echo "done: install the packages with GoldHEN's Package Installer"
