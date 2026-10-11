#!/bin/bash
# Dusklight Setup Studio for macOS: opens the assistant in its own window.
here="$(cd "$(dirname "$0")" && pwd)"
maker="$here/WorkshopKit"
case "$(uname -m)" in arm64) arch=arm64 ;; *) arch=x64 ;; esac
runtime="$maker/runtime/macos-$arch"
# A downloaded copy carries the quarantine flag on every file; this script was opened on purpose.
xattr -dr com.apple.quarantine "$runtime" 2>/dev/null
# The window app needs symbolic links, which USB sticks (exFAT) cannot hold: it is unpacked once
# into Application Support.
target="$HOME/Library/Application Support/Dusklight Setup Studio/electron-44.4.5-$arch"
if [ ! -d "$target/Electron.app" ] && [ -f "$maker/app/macos-$arch.zip" ]; then
    echo "Preparing the window app (first start only) ..."
    mkdir -p "$target" && ditto -x -k "$maker/app/macos-$arch.zip" "$target" || rm -rf "$target"
fi
if [ -x "$target/Electron.app/Contents/MacOS/Electron" ]; then
    xattr -dr com.apple.quarantine "$target" 2>/dev/null
    open -n -a "$target/Electron.app" --args "$maker/gui-frame" "--maker-dir=$maker" && exit 0
    echo "The window app did not start; opening the assistant in the browser instead."
fi
cd "$maker" || exit 1
"$runtime/python/bin/python3.13" -s -E -B -m dsk_weave6bdf gui
status=$?
if [ $status -ne 0 ]; then read -r -p "Press Enter to close ..."; fi
exit $status
