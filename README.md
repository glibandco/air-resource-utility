# Resource Monitor

Live CPU%, RAM, battery, and thermal status in your macOS menu bar.

## Install

1. Download **Resource Monitor.dmg**
2. Open it and drag **Resource Monitor.app** into **Applications**
3. Launch it — look for `CPU --%` in the top-right of your menu bar

> First launch: macOS may block it. Right-click → Open → Open to allow it.
> Dependencies install automatically on first run (~30–60 seconds, once only).

## What it shows

- **Menu bar:** live CPU% — click to expand
- **Expanded:** RAM, battery (% + time remaining), thermal state, top apps by CPU
- **Dashboard:** full per-core bars + top-15 process table at `http://localhost:8765` (open via "Open dashboard" in the menu)

## Requirements

- macOS 10.15 or later
- Python 3.9+ (the system Python at `/usr/bin/python3` is fine)
