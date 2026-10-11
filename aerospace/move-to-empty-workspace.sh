#!/bin/bash
# Move a window to the lowest-numbered empty workspace on the focused monitor.
# Intended for AeroSpace on-window-detected callbacks, where AEROSPACE_WINDOW_ID is set.
# Usage: move-to-empty-workspace.sh [window-id]

win="${1:-$AEROSPACE_WINDOW_ID}"
[ -n "$win" ] || exit 0

# Already alone in its workspace? Nothing to do.
focused_ws=$(aerospace list-workspaces --focused)
if [ "$(aerospace list-windows --workspace "$focused_ws" --count)" = "1" ]; then
    exit 0
fi

target=$(aerospace list-workspaces --monitor focused --empty | grep -E '^[0-9]+$' | sort -n | head -1)

# Every known numeric workspace is occupied — mint a fresh one.
if [ -z "$target" ]; then
    existing=$(aerospace list-workspaces --all)
    target=1
    while grep -qx "$target" <<<"$existing"; do
        target=$((target + 1))
    done
fi

aerospace move-node-to-workspace --window-id "$win" --focus-follows-window "$target"
