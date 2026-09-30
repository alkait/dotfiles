#!/usr/bin/env python3
"""Herdr remote watch: fetch a space's git remote when you enter it.

Runs as a Herdr plugin hook (startup + workspace/agent events). For the space
the event belongs to, it fetches the repo's remote in the background. The
sidebar's built-in git_status then shows the ahead/behind counts, and a toast
appears once per new remote head when the space is behind its upstream.

It only ever fetches. It never pulls, merges or touches the working tree.

Debug outside a hook:
  remote_watch.py --all             check every open space now, ignoring the throttle
  remote_watch.py --cwd PATH        check one directory now, ignoring the throttle
"""
import fcntl
import json
import os
import subprocess
import sys
import time

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
STATE_DIR = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.path.expanduser(
    "~/.local/state/herdr/plugins/alkait.remote-watch")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
# Fetch a given repo at most this often, however many events fire.
MIN_INTERVAL = int(os.environ.get("REMOTE_WATCH_INTERVAL", "300"))
RETRY_AFTER_FAILURE = 60
FETCH_TIMEOUT = 30


# ---------- herdr ----------

def herdr(*args):
    try:
        out = subprocess.run([HERDR, *args], capture_output=True, text=True, timeout=5)
        return json.loads(out.stdout) if out.stdout.strip() else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def all_spaces():
    """(label, cwd) for every open workspace, taken from its first pane."""
    snap = herdr("api", "snapshot").get("result", {}).get("snapshot", {})
    labels = {w["workspace_id"]: w.get("label", "") for w in snap.get("workspaces", [])}
    seen, spaces = set(), []
    for pane in snap.get("panes", []):
        wid, cwd = pane.get("workspace_id"), pane.get("cwd")
        if wid and cwd and wid not in seen:
            seen.add(wid)
            spaces.append((labels.get(wid, ""), cwd))
    return spaces


def event_space():
    """(label, cwd) of the workspace the triggering event belongs to."""
    try:
        ctx = json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON", "{}"))
    except ValueError:
        return None
    cwd = ctx.get("workspace_cwd") or ctx.get("focused_pane_cwd")
    return (ctx.get("workspace_label", ""), cwd) if cwd else None


# ---------- git ----------

def git(repo, *args, timeout=10, env=None):
    try:
        out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                             timeout=timeout, env=env, stdin=subprocess.DEVNULL)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def fetch(repo, remote):
    # Never block on a passphrase or credential prompt: this runs unattended.
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    ssh = env.get("GIT_SSH_COMMAND") or git(repo, "config", "core.sshCommand") or "ssh"
    env["GIT_SSH_COMMAND"] = ssh + " -o BatchMode=yes -o ConnectTimeout=5"
    return git(repo, "fetch", "--quiet", remote, timeout=FETCH_TIMEOUT, env=env) is not None


# ---------- state ----------

class State:
    """state.json under an exclusive lock, so concurrent hooks don't double-fetch."""

    def __enter__(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        self.f = open(STATE_FILE, "a+")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        self.f.seek(0)
        try:
            self.data = json.load(self.f)
        except ValueError:
            self.data = {}
        return self.data

    def __exit__(self, *exc):
        self.f.seek(0)
        self.f.truncate()
        json.dump(self.data, self.f)
        self.f.close()


# ---------- check ----------

def check(label, cwd, force=False):
    repo = git(cwd, "rev-parse", "--show-toplevel")
    if not repo:
        return
    branch = git(repo, "symbolic-ref", "-q", "HEAD")
    if not branch:   # detached HEAD
        return
    tracking = git(repo, "for-each-ref", "--format=%(upstream:short) %(upstream:remotename)", branch)
    if not tracking or len(tracking.split()) != 2:   # no upstream, or it tracks a local branch
        return
    upstream, remote = tracking.split()   # e.g. origin/main, origin

    # Claim the fetch slot before fetching so hooks firing together skip.
    now = time.time()
    with State() as state:
        entry = state.setdefault(repo, {})
        if not force and now - entry.get("fetched", 0) < MIN_INTERVAL:
            return
        entry["fetched"] = now

    if not fetch(repo, remote):
        with State() as state:   # offline or auth failure: stay quiet, retry soon
            state.setdefault(repo, {})["fetched"] = now - MIN_INTERVAL + RETRY_AFTER_FAILURE
        return

    counts = git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    head = git(repo, "rev-parse", "@{u}")
    if not counts or not head:
        return
    ahead, behind = (int(n) for n in counts.split())
    if behind == 0:
        return

    # One toast per new remote head; the sidebar keeps showing the count after that.
    with State() as state:
        entry = state.setdefault(repo, {})
        if entry.get("notified") == head and not force:
            return
        entry["notified"] = head

    name = label or os.path.basename(repo)
    commits = "commit" if behind == 1 else "commits"
    title = f"{name}: {behind} new {commits} on {upstream}"
    body = git(repo, "log", "-1", "--format=%s (%an, %cr)", "@{u}") or ""
    if ahead:
        body += f" · diverged, {ahead} local {'commit' if ahead == 1 else 'commits'} unpushed"
    herdr("notification", "show", title, "--body", body)


def main(argv):
    if "--cwd" in argv:
        check("", os.path.abspath(argv[argv.index("--cwd") + 1]), force=True)
        return 0
    if "--all" in argv or os.environ.get("HERDR_PLUGIN_EVENT") == "startup":
        seen = set()
        for label, cwd in all_spaces():
            if cwd not in seen:
                seen.add(cwd)
                check(label, cwd, force="--all" in argv)
        return 0
    space = event_space()
    if space:
        check(*space)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
