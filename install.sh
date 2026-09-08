#!/bin/bash

# Exit on error
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run the installer with sudo: sudo ./install.sh"
  exit 1
fi

if [ -z "$SUDO_USER" ]; then
    echo "Warning: Not run via sudo, using root as the user."
    REAL_USER="root"
    REAL_UID=0
else
    REAL_USER="$SUDO_USER"
    REAL_UID=$(id -u "$REAL_USER")
fi

APP_DIR=$(dirname $(readlink -f "$0"))

INSTALL_TAILSCALE=0
PORT=5000

while [[ $# -gt 0 ]]; do
  case $1 in
    tailscale)
      INSTALL_TAILSCALE=1
      shift
      ;;
    -p|--port)
      PORT="$2"
      shift 2
      ;;
    port=*)
      PORT="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: sudo ./install.sh [tailscale] [--port 8080]"
      exit 1
      ;;
  esac
done

echo "Installing picture..."
echo "User: $REAL_USER"
echo "Directory: $APP_DIR"
echo "Web UI Port: $PORT"

# Install dependencies
apt update
apt install -y python3-pygame python3-flask python3-werkzeug python3-pip libgbm1 libegl1 libgles2 cage

# Create the service file from template
sed -e "s|CURRENT_USER|$REAL_USER|g" \
    -e "s|CURRENT_UID|$REAL_UID|g" \
    -e "s|APP_DIR|$APP_DIR|g" \
    -e "s|PICTURE_PORT_VALUE|$PORT|g" \
    "$APP_DIR/picture.service.template" > /etc/systemd/system/picture.service

systemctl daemon-reload
systemctl enable picture.service
systemctl restart picture.service

# Configure display resolution for official DSI display
CMDLINE_FILE=""
if [ -f "/boot/firmware/cmdline.txt" ]; then
    CMDLINE_FILE="/boot/firmware/cmdline.txt"
elif [ -f "/boot/cmdline.txt" ]; then
    CMDLINE_FILE="/boot/cmdline.txt"
fi

if [ -n "$CMDLINE_FILE" ]; then
    # Hide boot text and blinking cursor
    echo "Configuring cmdline.txt to hide boot text..."
    sed -i 's/console=tty1/console=tty3/g' "$CMDLINE_FILE"
    for param in quiet splash loglevel=3 logo.nologo vt.global_cursor_default=0; do
        if ! grep -q "$param" "$CMDLINE_FILE"; then
            sed -i "1s/$/ $param/" "$CMDLINE_FILE"
        fi
    done
else
    echo "Warning: cmdline.txt not found, could not hide boot text."
fi

# Hide the rainbow screen and enable DSI overlay
CONFIG_FILE=""
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

if [ -n "$CONFIG_FILE" ]; then
    if ! grep -q "disable_splash=1" "$CONFIG_FILE"; then
        echo "disable_splash=1" >> "$CONFIG_FILE"
    fi
    if ! grep -q "dtoverlay=vc4-kms-dsi-7inch" "$CONFIG_FILE"; then
        sed -i '/dtoverlay=vc4-kms-v3d/a dtoverlay=vc4-kms-dsi-7inch' "$CONFIG_FILE"
    fi
fi

# Optional: Install Tailscale for remote uploading
if [ "$INSTALL_TAILSCALE" -eq 1 ]; then
    if ! command -v tailscale &> /dev/null; then
        echo "Installing Tailscale for remote web UI access..."
        curl -fsSL https://tailscale.com/install.sh | sh
        echo ""
        echo "=================================================================="
        echo "Tailscale has been installed! To enable remote access from anywhere:"
        echo "1. Click the authentication link that appears below."
        echo "2. Once authenticated, use your phone's browser from anywhere in the world!"
        echo "   (e.g., http://piframe:$PORT)"
        echo "=================================================================="
        
        # Authenticate tailscale
        tailscale up
    fi
else
    echo "Skipping Tailscale installation. If you want secure remote access from anywhere, run: sudo ./install.sh tailscale"
fi

echo "Installation complete!"
