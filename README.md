# Air Resource Utility

A small live resource monitor for MacBook Air — useful for keeping an eye on CPU,
memory, battery, and thermal throttling while running heavy apps like Claude,
Comet, Chrome, and friends.

Two ways to view it:

- **Menu bar app** (`menubar.py`) — live `CPU NN%` sits in the menu bar, click for
  RAM / battery / thermal status and the top apps by CPU.
- **Web dashboard** (`monitor.py`) — a fuller browser view at
  `http://localhost:8765` with per-core bars and a top-15 process table.

The menu bar app has an "Open dashboard" item that launches the web view.

## Quick start

Double-click `start.command`. First run installs dependencies (`psutil`, `rumps`,
and a pinned older `pyobjc`); subsequent runs are instant. After it boots, look
at the top-right of your screen for `CPU --%`.

> First time only: macOS may block the script. Right-click `start.command`
> -> Open -> Open.

## Run from the command line

```bash
cd "Air Resource Utility"
python3 menubar.py     # menu bar app
python3 monitor.py     # web dashboard at http://localhost:8765
```

## Why pinned pyobjc

`pyobjc` 12.x dropped support for Python 3.9 (and the wheel was yanked), which
is the version macOS ships at `/Library/Developer/CommandLineTools/usr/bin/python3`.
The launcher pins `pyobjc-core<11` and `pyobjc-framework-Cocoa<11` — those have
proper binary wheels for system Python, so install finishes in seconds instead
of compiling from source.

## What it tracks

System: total CPU% and per-core usage, memory (used / total GB), battery
(percent + time-left or charging state), and thermal throttling state read from
`pmset -g therm`.

Apps: per-app CPU and memory, with helper processes rolled up under their parent
(so all the `Google Chrome Helper (Renderer)` workers show as one `Google Chrome`
row). Highlighted apps include Claude, Comet, Chrome, Safari, Slack, Cursor,
VS Code, Arc, Firefox, Xcode, Spotify, Notion, Figma, Discord, WhatsApp, Zoom.

## Files

| File | What it is |
|------|------------|
| `menubar.py` | Menu bar app (rumps + pyobjc) |
| `monitor.py` | Standalone web dashboard (stdlib HTTP server + psutil) |
| `start.command` | Double-click launcher; installs deps, runs the menu bar app |

## Requirements

- macOS (uses `pmset` and AppKit)
- Python 3.9+ — the system Python at `/usr/bin/python3` is fine
