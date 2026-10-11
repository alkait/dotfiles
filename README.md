# dotfiles

Personal configuration synced across machines (Linux and macOS). The repo is
the source of truth; the live config locations are symlinks into it.

## End state

- `~/.config/herdr/config.toml` is a symlink to `herdr/config.toml` in this repo.
- `~/.config/herdr/scripts` is a symlink to `herdr/scripts` in this repo.
- The running Herdr server has loaded this config (`herdr config check` passes,
  `herdr server reload-config` applied).
- `prefix+t` in Herdr opens the space picker: a fuzzy list of the directories
  under `~/Documents/code/alkait`, sorted by most recently used. Enter focuses
  the workspace if open, otherwise creates it.
- The `remote-watch` plugin in `herdr/plugins/remote-watch` is linked
  (`herdr plugin list` shows `alkait.remote-watch`). Entering a space fetches
  its git remote in the background, at most once every 5 minutes per repo, so
  the sidebar's `↑n ↓n` counts are current. It only fetches; it never pulls.
  With `[ui.toast] delivery = "herdr"` in `config.toml` it also shows a toast
  once per new remote head when the space is behind.
- `~/.config/ghostty/config` is a symlink to `ghostty/config` in this repo.
- The `alt+…` bindings in `config.toml` reach Herdr: Ghostty sends Option as
  Alt, and its default Option+Left/Right word-jump bindings (`esc:b` / `esc:f`)
  are unbound so those arrows reach Herdr as `alt+left` / `alt+right`.
- macOS only: `~/.config/aerospace` is a symlink to `aerospace/` in this repo
  (config plus the scripts its bindings run), and the running AeroSpace has
  reloaded it. `alt+<letter>` brings an app to its home workspace and focuses
  it, launching it there if it isn't running: Herdr `A`, Brave `B`, the dev
  browser `D`, WhatsApp `W`, X `X`, YouTube `Y`. Windows opened any other way
  stay where they open, and `alt+shift+<n>` moves them freely.

`install.sh` produces the symlinks and the plugin link, and is safe to re-run.

## Prerequisites

- `herdr` installed and on PATH (https://herdr.dev/docs/install/).
- macOS: AeroSpace installed (https://nikitabobko.github.io/AeroSpace/guide#installation).
- `python3` on PATH with the standard `curses` module (macOS: Xcode command
  line tools provide it).
- Projects live under `~/Documents/code/alkait`. If they live elsewhere on this
  machine, set `HERDR_SPACE_ROOT` in the picker's `[[keys.command]]` entry.
- Repo cloned to `~/Documents/code/alkait/dotfiles` so the picker lists it too.

## Not part of the sync

`session.json`, logs, sockets and `.plugins.lock` in `~/.config/herdr` are
per-machine runtime state and stay out of the repo. The picker's usage history
in `~/.local/state/herdr` rebuilds itself, as does the plugin's fetch throttle
state in `~/.local/state/herdr/plugins`.
