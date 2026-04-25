#!/bin/bash
# Re-sync the source .py files into Resource Monitor.app/Contents/Resources/.
# Run after editing menubar.py or monitor.py if you also want the .app to pick
# up the changes (the .app contains its own copies for portability).
set -eu
cd "$(dirname "$0")"

APP="Resource Monitor.app"
if [ ! -d "$APP" ]; then
    echo "Resource Monitor.app not found. Nothing to rebuild."
    exit 1
fi

cp menubar.py "$APP/Contents/Resources/menubar.py"
cp monitor.py "$APP/Contents/Resources/monitor.py"
chmod +x "$APP/Contents/MacOS/launcher"

# Rebuild .icns from the iconset if iconutil is available and the iconset
# is present (lets you tweak the PNGs and re-pack without needing Pillow).
if [ -d AppIcon.iconset ] && command -v iconutil >/dev/null 2>&1; then
    iconutil -c icns AppIcon.iconset -o "$APP/Contents/Resources/AppIcon.icns"
    echo "Rebuilt AppIcon.icns from AppIcon.iconset."
fi

# Force macOS to re-read the bundle metadata and clear icon cache.
touch "$APP"
rm -rf "$HOME/Library/Caches/com.apple.iconservices.store" 2>/dev/null || true

echo "Resynced menubar.py and monitor.py into '$APP'."
echo "Done."
