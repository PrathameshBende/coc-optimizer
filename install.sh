#!/usr/bin/env bash
set -e

EXT_ID="coc-tracker@zorro"
TARGET="$(cd "$(dirname "$0")" && pwd)"
LINK="$HOME/.local/share/gnome-shell/extensions/$EXT_ID"

echo "Installing $EXT_ID as a symlink to $TARGET..."
mkdir -p "$(dirname "$LINK")"

if [ -L "$LINK" ] || [ -d "$LINK" ]; then
    rm -rf "$LINK"
fi

ln -sf "$TARGET" "$LINK"
echo "Symlink created: $LINK -> $TARGET"

echo "Enabling extension..."
gnome-extensions enable "$EXT_ID" 2>/dev/null || true

echo ""
echo "Done. Reload GNOME Shell (Alt+F2 → r → Enter, or log out/in on Wayland)."
echo ""
echo "To generate your upgrade schedule:"
echo "  python3 \"$TARGET/run_pipeline.py\" \"$TARGET/village_export.json\""
echo ""
echo "To customize paths:"
echo "  nano \"$TARGET/config.json\""
