#!/bin/bash
# Double-click to launch the menu bar Resource Monitor.
# (First run: right-click -> Open, since macOS may block .command files.)
set -u
cd "$(dirname "$0")"

PY=$(command -v python3)
echo "Using Python: $PY"
echo

# Pin pyobjc to <11 — pyobjc 12.x dropped Python 3.9 support (yanked release)
# and would compile from source forever and still fail.
DEPS=(psutil "pyobjc-core<11" "pyobjc-framework-Cocoa<11" rumps)

echo "Checking dependencies (one-time)..."
# Try plain --user (works on macOS system Python 3.9). If that fails, retry
# with --break-system-packages (required on Python 3.12+).
"$PY" -m pip install --user --upgrade --quiet "${DEPS[@]}" 2>/dev/null \
  || "$PY" -m pip install --user --upgrade --quiet --break-system-packages "${DEPS[@]}" 2>/dev/null \
  || "$PY" -m pip install --user --upgrade "${DEPS[@]}"

echo
echo "Launching menu bar app... (look at the top-right of your screen for 'CPU --%')"
echo "Close this Terminal window or press Ctrl+C to quit."
echo
exec "$PY" menubar.py
