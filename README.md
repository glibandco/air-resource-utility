# Air Resource Utility

A small live resource monitor for MacBook Air — useful for keeping an eye on CPU,
memory, battery, and thermal throttling while running heavy apps like Claude,
Comet, Chrome, and friends.

Two ways to view it:

- **Menu bar app** — live `CPU NN%` sits in the menu bar, click for RAM /
  battery / thermal status and the top apps by CPU.
- **Web dashboard** (`monitor.py`) — fuller browser view at
  `http://localhost:8765` with per-core bars and a top-15 process table. The
  menu bar app has an "Open dashboard" item that launches it.

## Install (no Terminal)

1. Double-click `Resource Monitor.app`. The first launch will be blocked by
   macOS Gatekeeper — **right-click `Resource Monitor.app` → Open → Open**
   to allow it.
2. On first launch the app silently installs its Python dependencies (a
   notification appears while it does — takes ~30–60 seconds, only happens
   once).
3. Look at the top-right of your screen for `CPU --%`. Click it to expand.

To put it in `/Applications`, drag `Resource Monitor.app` over there. The
bundle is self-contained — `menubar.py` and `monitor.py` live inside it.

### Launch on login

System Settings → General → Login Items → "+" → pick `Resource Monitor.app`.
You'll never have to think about it again.

### Uninstall

Drag `Resource Monitor.app` to the Trash. Delete `~/Library/Logs/ResourceMonitor.log`
if you want to be thorough.

## Run from the command line (for development)

```bash
cd "Air Resource Utility"
python3 menubar.py     # menu bar app
python3 monitor.py     # web dashboard at http://localhost:8765
```

`start.command` does the same plus auto-installs deps in a Terminal window —
handy when something goes wrong and you want to see error output.

## What it tracks

System: total CPU% and per-core usage, memory (used / total GB), battery
(percent + time-left or charging state), and thermal throttling state read
from `pmset -g therm`.

Apps: per-app CPU and memory, with helper processes rolled up under their
parent (so all the `Google Chrome Helper (Renderer)` workers show as one
`Google Chrome` row). Highlighted apps include Claude, Comet, Chrome, Safari,
Slack, Cursor, VS Code, Arc, Firefox, Xcode, Spotify, Notion, Figma, Discord,
WhatsApp, Zoom.

## Files

| File | What it is |
|------|------------|
| `Resource Monitor.app` | Double-clickable Mac app — the main install path |
| `menubar.py` | Menu bar app source (rumps + pyobjc) |
| `monitor.py` | Web dashboard source (stdlib HTTP server + psutil) |
| `start.command` | Terminal launcher with verbose output (for debugging) |
| `rebuild-app.command` | Re-sync source `.py` files into the .app after edits |
| `publish-to-github.command` | One-click `git init` + `gh repo create` + push |
| `setup-git.command` | Local-only `git init` and first commit |

## Why pinned pyobjc

`pyobjc` 12.x dropped support for Python 3.9 (the wheel was yanked) — that's
the version macOS ships at `/Library/Developer/CommandLineTools/usr/bin/python3`.
The launcher pins `pyobjc-core<11` and `pyobjc-framework-Cocoa<11` — those
have proper binary wheels for system Python, so install finishes in seconds
instead of compiling from source forever.

## Debugging

If the menu bar item doesn't appear after launching `Resource Monitor.app`,
check the log:

```bash
tail -f ~/Library/Logs/ResourceMonitor.log
```

Or run from Terminal to see live output: `bash start.command`.

## Requirements

- macOS 10.15 or later (uses `pmset` and AppKit)
- Python 3.9+ — the system Python at `/usr/bin/python3` is fine. If `python3`
  is missing, the app prompts you to run `xcode-select --install`.
