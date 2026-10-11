#!/bin/sh
# Jump to the dev browser in workspace D: launch it there (fullscreen) if it
# isn't running yet, or move it back there if it has strayed elsewhere.
#
# The dev browser (~/.local/bin/dev-browser) is a second Brave Origin instance
# with its own profile and a DevTools port, so it shares Brave's bundle id. Its
# windows are told apart by the pid of that instance's main process.
#
# Bound to alt-d in aerospace.toml.

DEV_BROWSER="$HOME/.local/bin/dev-browser"
PROFILE="$HOME/.cache/chrome-devtools-mcp/chrome-profile"
WORKSPACE=D

# Print the window ids of the dev browser, one per line, or nothing if there are none (yet)
dev_windows() {
    pid=$(pgrep -f "MacOS/Brave Origin --user-data-dir=$PROFILE" | head -1)
    [ -n "$pid" ] || return 0
    aerospace list-windows --all --format '%{window-id}|%{app-pid}' |
        awk -F'|' -v p="$pid" '$2 + 0 == p { print $1 + 0 }'
}

wins=$(dev_windows)
if [ -n "$wins" ]; then
    # Already running: bring every window home to workspace D, then go to the first one
    for win in $wins; do
        aerospace move-node-to-workspace --window-id "$win" "$WORKSPACE"
    done
    aerospace focus --window-id "${wins%%
*}"
    exit 0
fi

# Not running (or it has no window yet): open it in workspace D
aerospace workspace "$WORKSPACE"
nohup "$DEV_BROWSER" >/dev/null 2>&1 &

# Wait (up to ~5s) for the new window to show up, then make it AeroSpace-fullscreen
i=0
while [ "$i" -lt 50 ]; do
    wins=$(dev_windows)
    if [ -n "$wins" ]; then
        aerospace fullscreen on --no-outer-gaps --window-id "${wins%%
*}"
        exit 0
    fi
    sleep 0.1
    i=$((i + 1))
done
