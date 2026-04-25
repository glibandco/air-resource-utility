#!/bin/bash
# Build a distributable DMG for Resource Monitor.app.
# Double-click to run, or: bash build-dmg.command
set -eu
cd "$(dirname "$0")"

APP="Resource Monitor.app"
DMG="Resource Monitor.dmg"
STAGING="$(mktemp -d)/dmg-staging"

if [ ! -d "$APP" ]; then
    echo "ERROR: $APP not found. Run rebuild-app.command first."
    exit 1
fi

echo "Building $DMG..."

# Stage: app + Applications symlink
mkdir -p "$STAGING"
cp -r "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# Create a writable image from the staging folder
hdiutil create \
    -volname "Resource Monitor" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDZO \
    -o "$DMG"

rm -rf "$(dirname "$STAGING")"

echo ""
echo "Done: $DMG"
echo "Drag Resource Monitor.app onto the Applications folder inside the DMG to install."
