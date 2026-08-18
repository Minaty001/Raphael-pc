#!/usr/bin/env bash
# install_runtime.sh — desktop integration for Raphael v3 Always-Alive Runtime
# (Sections 5-6, 73). No root required for normal operation.
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_SRC="$REPO_DIR/scripts/raphael-runtime.service"
SERVICE_DST="$HOME/.config/systemd/user/raphael-runtime.service"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/raphael-runtime.desktop"

echo "Raphael v3 — installing always-alive runtime integration"
echo "Repo: $REPO_DIR"

# 1) systemd --user unit (Linux Mint / systemd desktops)
mkdir -p "$(dirname "$SERVICE_DST")"
sed "s|%h|$HOME|g" "$SERVICE_SRC" > "$SERVICE_DST"
echo "  -> installed $SERVICE_DST"

systemctl --user daemon-reload 2>/dev/null || true

# 2) Desktop autostart entry (start minimized on login; Section 73 startup_mode)
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Raphael Runtime
Comment=Raphael v3 Always-Alive Assistant Runtime
Exec=$REPO_DIR/venv/bin/python $REPO_DIR/raphael/runtime_launcher.py
Hidden=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=10
EOF
echo "  -> installed $AUTOSTART_FILE"

echo ""
echo "Enable on next login (background, no window)? Run:"
echo "  systemctl --user enable raphael-runtime.service"
echo ""
echo "Start now?"
read -r -p "  [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  systemctl --user start raphael-runtime.service
  echo "  -> started. Check: systemctl --user status raphael-runtime.service"
fi
echo "Done."
