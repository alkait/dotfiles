#!/usr/bin/env python3
"""Herdr space picker: fuzzy-pick a project directory and open/focus it as a workspace.

Runs inside a Herdr popup (type = "popup" custom command). Lists the
subdirectories of ROOT sorted by most recently used, filters as you type,
Up/Down to move, Enter to open (focus if already open, create otherwise),
Esc to cancel.

Debug outside the TUI:
  space-picker.py --list            print entries in current order
  space-picker.py --query foo       print scored matches for a query
"""
import curses
import json
import os
import subprocess
import sys
import time

ROOT = os.path.expanduser(os.environ.get("HERDR_SPACE_ROOT", "~/Documents/code/alkait"))
MRU_FILE = os.path.expanduser("~/.local/state/herdr/space-picker-mru.json")
HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")


# ---------- data ----------

def load_mru():
    try:
        with open(MRU_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_mru(mru):
    os.makedirs(os.path.dirname(MRU_FILE), exist_ok=True)
    tmp = MRU_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(mru, f)
    os.replace(tmp, MRU_FILE)


def herdr_json(*args):
    try:
        out = subprocess.run([HERDR, *args], capture_output=True, text=True, timeout=5)
        return json.loads(out.stdout) if out.stdout.strip() else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def open_workspaces():
    """Map directory path -> workspace_id for every open workspace, via pane cwds."""
    snap = herdr_json("api", "snapshot").get("result", {}).get("snapshot", {})
    by_path = {}
    labels = {w["workspace_id"]: w.get("label", "") for w in snap.get("workspaces", [])}
    for pane in snap.get("panes", []):
        cwd = pane.get("cwd") or ""
        wid = pane.get("workspace_id")
        if cwd and wid and cwd not in by_path:
            by_path[cwd] = wid
    return by_path, labels, snap.get("focused_workspace_id")


def entries():
    mru = load_mru()
    by_path, labels, focused = open_workspaces()
    items = []
    try:
        names = sorted(os.listdir(ROOT))
    except OSError:
        names = []
    for name in names:
        if name.startswith("."):
            continue
        path = os.path.join(ROOT, name)
        if not os.path.isdir(path):
            continue
        # Open if any pane sits in this dir or below it; prefer the exact match.
        wid = by_path.get(path)
        if wid is None:
            for cwd, w in by_path.items():
                if cwd.startswith(path + os.sep):
                    wid = w
                    break
        if wid is None:
            for w, label in labels.items():
                if label == name:
                    wid = w
                    break
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            mtime = 0
        items.append({
            "name": name,
            "path": path,
            "workspace_id": wid,
            "focused": wid is not None and wid == focused,
            "used": mru.get(path, 0),
            "mtime": mtime,
        })
    # Most recently used first; never-used dirs fall back to mtime.
    items.sort(key=lambda e: (e["used"], e["mtime"]), reverse=True)
    return items


# ---------- fuzzy ----------

def score(query, text):
    """Return a score (higher is better) or None if query does not match.

    Every space-separated word must match. A word matches as a substring
    (strong) or as an in-order subsequence (weaker, penalised by gaps).
    """
    text_l = text.lower()
    total = 0
    for word in query.lower().split():
        idx = text_l.find(word)
        if idx >= 0:
            total += 1000 - idx * 10 + (200 if idx == 0 else 0)
            continue
        pos, gaps, first = -1, 0, None
        for ch in word:
            nxt = text_l.find(ch, pos + 1)
            if nxt < 0:
                return None
            if pos >= 0:
                gaps += nxt - pos - 1
            else:
                first = nxt
            pos = nxt
        total += 500 - gaps * 5 - first * 2
    return total


def filtered(items, query):
    if not query.strip():
        return list(items)
    scored = []
    for rank, e in enumerate(items):
        s = score(query, e["name"])
        if s is not None:
            scored.append((s, -rank, e))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [e for _, _, e in scored]


# ---------- actions ----------

def open_entry(e):
    mru = load_mru()
    mru[e["path"]] = time.time()
    save_mru(mru)
    if e["workspace_id"]:
        r = herdr_json("workspace", "focus", e["workspace_id"])
    else:
        r = herdr_json("workspace", "create", "--cwd", e["path"], "--label", e["name"], "--focus")
    if "error" in r:
        sys.stderr.write(json.dumps(r) + "\n")
        return 1
    return 0


# ---------- ui ----------

def run_ui(stdscr, items):
    try:
        curses.set_escdelay(25)
    except AttributeError:
        pass
    curses.curs_set(1)
    curses.use_default_colors()
    has_color = curses.has_colors()
    if has_color:
        curses.init_pair(1, curses.COLOR_CYAN, -1)   # accent
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # open marker
        curses.init_pair(3, -1, -1)
    accent = curses.color_pair(1) | curses.A_BOLD if has_color else curses.A_BOLD
    green = curses.color_pair(2) if has_color else curses.A_NORMAL
    dim = curses.A_DIM

    query, cursor, top = "", 0, 0
    while True:
        h, w = stdscr.getmaxyx()
        matches = filtered(items, query)
        cursor = max(0, min(cursor, len(matches) - 1))
        list_h = max(1, h - 3)
        if cursor < top:
            top = cursor
        elif cursor >= top + list_h:
            top = cursor - list_h + 1

        stdscr.erase()
        prompt = "❯ "
        stdscr.addnstr(0, 0, prompt, w - 1, accent)
        stdscr.addnstr(0, len(prompt), query, max(0, w - len(prompt) - 1))
        stdscr.addnstr(1, 0, "─" * (w - 1), w - 1, dim)

        for row, e in enumerate(matches[top:top + list_h]):
            y = 2 + row
            selected = (top + row) == cursor
            marker = "●" if e["workspace_id"] else " "
            tag = "focused" if e["focused"] else ("open" if e["workspace_id"] else "")
            name_w = max(1, w - 4 - len(tag) - 2)
            line = f" {marker} {e['name'][:name_w]:<{name_w}} {tag} "
            attr = curses.A_REVERSE if selected else curses.A_NORMAL
            stdscr.addnstr(y, 0, line, w - 1, attr)
            if e["workspace_id"] and not selected:
                stdscr.addnstr(y, 1, marker, 1, green)

        if not matches:
            stdscr.addnstr(2, 1, "no match", w - 2, dim)
        footer = f"{len(matches)}/{len(items)}  ↑↓ move · enter open · esc cancel"
        stdscr.addnstr(h - 1, 0, footer[:w - 1], w - 1, dim)
        stdscr.move(0, min(len(prompt) + len(query), w - 1))
        stdscr.refresh()

        try:
            key = stdscr.get_wch()
        except curses.error:
            continue

        if key in (27, "\x1b", "\x03", "\x07"):            # esc, ctrl+c, ctrl+g
            return None
        if key in ("\n", "\r", curses.KEY_ENTER):
            return matches[cursor] if matches else None
        if key in (curses.KEY_UP, "\x10"):                # up, ctrl+p
            cursor -= 1
        elif key in (curses.KEY_DOWN, "\x0e"):            # down, ctrl+n
            cursor += 1
        elif key == curses.KEY_PPAGE:
            cursor -= list_h
        elif key == curses.KEY_NPAGE:
            cursor += list_h
        elif key == curses.KEY_HOME:
            cursor = 0
        elif key == curses.KEY_END:
            cursor = len(matches) - 1
        elif key in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
            query = query[:-1]
            cursor = 0
        elif key == "\x15":                               # ctrl+u
            query, cursor = "", 0
        elif key == "\x17":                               # ctrl+w
            query = query.rstrip().rsplit(" ", 1)[0] if " " in query.rstrip() else ""
            cursor = 0
        elif key == curses.KEY_RESIZE:
            pass
        elif isinstance(key, str) and key.isprintable():
            query += key
            cursor = 0


def main(argv):
    items = entries()
    if "--list" in argv:
        for e in items:
            print(("● " if e["workspace_id"] else "  ") + e["name"], e["workspace_id"] or "", sep="\t")
        return 0
    if "--query" in argv:
        q = argv[argv.index("--query") + 1]
        for e in filtered(items, q):
            print(score(q, e["name"]), e["name"], sep="\t")
        return 0
    os.environ.setdefault("ESCDELAY", "25")
    choice = curses.wrapper(run_ui, items)
    if choice is None:
        return 0
    return open_entry(choice)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
