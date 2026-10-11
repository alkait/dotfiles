#!/bin/sh
# Jump to an app in its home workspace: launch it there (fullscreen) if it isn't
# running yet, or move it back there if it has strayed elsewhere.
#
# Usage: app-workspace.sh <bundle-id> <workspace>
#
# The bundle id is matched exactly, so Brave web apps
# (com.brave.Browser.origin.app.*) are kept apart from Brave itself.
# Herdr has no bundle id of its own; see herdr-workspace.sh for that one.
# The dev browser shares Brave's bundle id, so its windows (matched by pid) are
# skipped here; see dev-browser-workspace.sh for that one.

bundle=$1
workspace=$2
[ -n "$bundle" ] && [ -n "$workspace" ] || exit 1

dev_pid=$(pgrep -f "MacOS/Brave Origin --user-data-dir=$HOME/.cache/chrome-devtools-mcp/chrome-profile" | head -1)

# Print the window ids of the app, one per line, or nothing if there are none (yet)
app_windows() {
    aerospace list-windows --all --format '%{window-id}|%{app-bundle-id}|%{app-pid}' |
        awk -F'|' -v b="$bundle" -v d="${dev_pid:-0}" \
            '{ gsub(/^ +| +$/, "", $2) } $2 == b && $3 + 0 != d + 0 { print $1 + 0 }'
}

wins=$(app_windows)
if [ -n "$wins" ]; then
    # Already running: bring every window home, then go to the first one
    for win in $wins; do
        aerospace move-node-to-workspace --window-id "$win" "$workspace"
    done
    aerospace focus --window-id "${wins%%
*}"
    exit 0
fi

# Not running (or it has no window yet): open it in its workspace
aerospace workspace "$workspace"
open -b "$bundle"

# Wait (up to ~5s) for the new window to show up, then make it AeroSpace-fullscreen
i=0
while [ "$i" -lt 50 ]; do
    wins=$(app_windows)
    if [ -n "$wins" ]; then
        aerospace fullscreen on --no-outer-gaps --window-id "${wins%%
*}"
        exit 0
    fi
    sleep 0.1
    i=$((i + 1))
done
