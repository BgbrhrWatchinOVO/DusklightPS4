#!/bin/sh
# Dusklight Setup Studio for Linux: opens the assistant in its own window.
here="$(cd "$(dirname "$0")" && pwd)"
maker="$here/WorkshopKit"
if [ -x "$maker/app/linux-x64/electron" ]; then
    # --no-sandbox: Chromium's sandbox helper must belong to root, which a USB stick cannot
    # provide; the window shows nothing but the assistant's own local page.
    "$maker/app/linux-x64/electron" "$maker/gui-frame" "--maker-dir=$maker" --no-sandbox && exit 0
    echo "The window app did not start; opening the assistant in the browser instead."
fi
cd "$maker" || exit 1
exec runtime/linux-x64/python/bin/python3.13 -s -E -B -m dsk_weave6bdf gui
