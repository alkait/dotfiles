#!/bin/sh
# Symlink configs from this repo into place. Safe to re-run.
# Usage: ./install.sh
set -eu
REPO="$(cd "$(dirname "$0")" && pwd)"

link() {  # link <repo-relative source> <absolute target>
    src="$REPO/$1"; dst="$2"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        echo "backing up $dst -> $dst.bak"
        mv "$dst" "$dst.bak"
    fi
    ln -sfn "$src" "$dst"
    echo "linked $dst -> $src"
}

# herdr (same path on Linux and macOS)
link herdr/config.toml "$HOME/.config/herdr/config.toml"
link herdr/scripts     "$HOME/.config/herdr/scripts"

# ghostty (XDG path, read on Linux and macOS)
link ghostty/config    "$HOME/.config/ghostty/config"

if command -v herdr >/dev/null 2>&1; then
    herdr server reload-config >/dev/null 2>&1 && echo "herdr config reloaded" || true
    # Plugins are registered by path, straight from this repo.
    herdr plugin link "$REPO/herdr/plugins/remote-watch" >/dev/null 2>&1 && echo "herdr plugin remote-watch linked" || true
fi
