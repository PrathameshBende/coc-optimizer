#!/usr/bin/env bash
set -e

EXT_ID="coc-tracker@zorro"
LINK="$HOME/.local/share/gnome-shell/extensions/$EXT_ID"

echo "Disabling extension $EXT_ID..."
gnome-extensions disable "$EXT_ID" 2>/dev/null || true

if [ -L "$LINK" ] || [ -d "$LINK" ]; then
    TARGET="$(readlink -f "$LINK" 2>/dev/null || echo "$LINK")"
    echo "Removing extension symlink: $LINK"
    rm -rf "$LINK"
    echo "Extension link removed."
else
    echo "Extension not found at $LINK"
fi

# Clean up runtime state files if the repo is still accessible
RUNTIME_FILES=("state.json" "overrides.json" "pos.json" "cache")
if [ -n "$TARGET" ] && [ -d "$TARGET" ]; then
    for f in "${RUNTIME_FILES[@]}"; do
        if [ -e "$TARGET/$f" ]; then
            rm -rf "$TARGET/$f"
            echo "Removed: $TARGET/$f"
        fi
    done
fi

# Clean up per-user state stored elsewhere
for dir in "$HOME/.local/share/gnome-shell/extensions/$EXT_ID" \
           "$HOME/.cache/gnome-shell/extensions/$EXT_ID"; do
    if [ -e "$dir" ]; then
        rm -rf "$dir"
        echo "Removed: $dir"
    fi
done

echo ""
echo "Uninstall complete. Reload GNOME Shell (Alt+F2 → r → Enter)."
