# dotfiles

Personal configuration synced across machines. Clone, then run `./install.sh`
to symlink everything into place. Re-run after adding new entries.

## herdr

- `herdr/config.toml` — keybindings, UI settings, custom commands.
- `herdr/scripts/space-picker.py` — fuzzy project picker bound to `prefix+t`.
  Lists directories under `~/Documents/code/alkait` by most recently used,
  focuses the workspace if open, creates it otherwise.

Requirements on a new machine: `herdr` installed, `python3` on PATH.
On macOS, make sure the terminal sends Option as Alt for the `alt+…` bindings.
