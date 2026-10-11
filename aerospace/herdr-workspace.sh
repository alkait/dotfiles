#!/bin/sh
# Jump to Herdr in workspace A: launch it there (fullscreen) if it isn't running
# yet, or move it back there if it has strayed elsewhere.
#
# Herdr has no bundle id of its own: Herdr.app is a launcher applet that starts
# a separate Ghostty instance running ~/.local/bin/herdr. So the Herdr window is
# told apart from ordinary Ghostty windows by the pid of that Ghostty process.
#
# Bound to alt-a in aerospace.toml.

HERDR_BIN="$HOME/.local/bin/herdr"
WORKSPACE=A

# Print the window id of the running Herdr, or nothing if there is none (yet)
herdr_window() {
    pid=$(pgrep -f "ghostty -e $HERDR_BIN" | head -1)
    [ -n "$pid" ] || return 0
    aerospace list-windows --all --format '%{window-id}|%{app-pid}' |
        awk -F'|' -v p="$pid" '$2 + 0 == p { print $1 + 0; exit }'
}

win=$(herdr_window)
if [ -n "$win" ]; then
    # Already running: bring it home to workspace A, then go to it
    aerospace move-node-to-workspace --window-id "$win" "$WORKSPACE"
    aerospace focus --window-id "$win"
    exit 0
fi

# Not running (or it has no window yet): open it in workspace A
aerospace workspace "$WORKSPACE"
open -na Ghostty --args -e "$HERDR_BIN"

# Wait (up to ~5s) for the new window to show up, then make it AeroSpace-fullscreen
i=0
while [ "$i" -lt 50 ]; do
    win=$(herdr_window)
    if [ -n "$win" ]; then
        aerospace fullscreen on --no-outer-gaps --window-id "$win"
        exit 0
    fi
    sleep 0.1
    i=$((i + 1))
done
