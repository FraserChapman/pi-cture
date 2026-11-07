#!/bin/bash

# Exit on error
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run the uninstaller with sudo: sudo ./uninstall.sh"
  exit 1
fi

APP_DIR=$(dirname $(readlink -f "$0"))

REMOVE_PACKAGES=0
REMOVE_TAILSCALE=0

while [[ $# -gt 0 ]]; do
  case $1 in
    packages)
      REMOVE_PACKAGES=1
      shift
      ;;
    tailscale)
      REMOVE_TAILSCALE=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: sudo ./uninstall.sh [packages] [tailscale]"
      exit 1
      ;;
  esac
done

echo "Uninstalling picture..."

# Stop and remove the service
SERVICE_FILE="/etc/systemd/system/picture.service"
if [ -f "$SERVICE_FILE" ]; then
    systemctl stop picture.service || true
    systemctl disable picture.service || true
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    # The service took over tty1, so give the login prompt back
    systemctl start getty@tty1.service || true
else
    echo "Service not installed, skipping."
fi

# Restore boot text and cursor
CMDLINE_FILE=""
if [ -f "/boot/firmware/cmdline.txt" ]; then
    CMDLINE_FILE="/boot/firmware/cmdline.txt"
elif [ -f "/boot/cmdline.txt" ]; then
    CMDLINE_FILE="/boot/cmdline.txt"
fi

if [ -n "$CMDLINE_FILE" ]; then
    echo "Restoring cmdline.txt boot text..."
    sed -i 's/console=tty3/console=tty1/g' "$CMDLINE_FILE"
    # Remove exactly the parameters install.sh added (whole tokens only)
    awk -v remove="quiet splash loglevel=3 logo.nologo vt.global_cursor_default=0" '
        BEGIN { n = split(remove, list, " "); for (i = 1; i <= n; i++) skip[list[i]] = 1 }
        NR == 1 {
            out = ""
            for (i = 1; i <= NF; i++) if (!($i in skip)) out = out (out == "" ? "" : " ") $i
            print out
            next
        }
        { print }
    ' "$CMDLINE_FILE" > "$CMDLINE_FILE.tmp"
    cat "$CMDLINE_FILE.tmp" > "$CMDLINE_FILE"
    rm -f "$CMDLINE_FILE.tmp"
fi

# Restore the rainbow screen and remove the DSI overlay
CONFIG_FILE=""
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

if [ -n "$CONFIG_FILE" ]; then
    echo "Restoring config.txt..."
    sed -i -e '/^disable_splash=1$/d' -e '/^dtoverlay=vc4-kms-dsi-7inch$/d' "$CONFIG_FILE"
fi

# Optional: Remove the packages only picture needs. Shared libraries
# (libgbm1, libegl1, libgles2) and python3-pip are left alone as other
# software is likely to depend on them.
if [ "$REMOVE_PACKAGES" -eq 1 ]; then
    echo "Removing packages..."
    apt remove -y cage python3-pygame python3-flask python3-werkzeug
else
    echo "Leaving installed packages. To remove them too, run: sudo ./uninstall.sh packages"
fi

# Optional: Remove Tailscale
if [ "$REMOVE_TAILSCALE" -eq 1 ]; then
    if command -v tailscale &> /dev/null; then
        echo "Removing Tailscale..."
        tailscale logout || true
        apt remove -y tailscale
        rm -f /etc/apt/sources.list.d/tailscale.list /usr/share/keyrings/tailscale-archive-keyring.gpg
    else
        echo "Tailscale not installed, skipping."
    fi
fi

echo ""
echo "Uninstall complete! Reboot for the boot changes to take effect: sudo reboot"
echo "Your photos and settings have been kept in $APP_DIR."
echo "Delete that directory if you no longer need them."
