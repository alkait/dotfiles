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
- The `alt+…` bindings in `config.toml` reach Herdr, meaning the terminal sends
  Option/Alt as Alt.

`install.sh` produces the symlinks and the plugin link, and is safe to re-run.

## Prerequisites

- `herdr` installed and on PATH (https://herdr.dev/docs/install/).
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
