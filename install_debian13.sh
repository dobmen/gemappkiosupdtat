#!/bin/bash
set -e

echo "===================================================="
echo " Kiosk OS (Debian 13) Dependencies Installer"
echo "===================================================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (su -)"
  exit 1
fi

# Detect the user who owns the current directory (the one who cloned the repo)
TARGET_USER=$(stat -c '%U' .)

echo "[1/5] Updating package repositories & installing sudo..."
apt-get update
apt-get install -y sudo

echo "[2/5] Adding $TARGET_USER to sudo group..."
usermod -aG sudo $TARGET_USER

echo "[3/5] Installing C++ Qt6 Wayland Compositor dependencies & greetd..."
apt-get install -y \
    build-essential \
    cmake \
    qt6-base-dev \
    qt6-declarative-dev \
    qt6-wayland-dev \
    qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts \
    qml6-module-qtquick-window \
    qml6-module-qtwayland-compositor \
    qt6-wayland \
    qt6-shadertools-dev \
    libxkbcommon-dev \
    greetd

echo "[4/5] Building the C++ Wayland Compositor..."
cd "$(dirname "$0")/os_compositor"
mkdir -p build
cd build
cmake ..
make -j$(nproc)
COMPOSITOR_PATH=$(realpath ./kiosk_os)

echo "[5/5] Purging GNOME & Configuring Kiosk Auto-Boot..."
# Remove the standard desktop environment
apt-get purge -y gdm3 gnome-shell task-gnome-desktop
apt-get autoremove -y

# Configure greetd for auto-login
cat <<EOF > /etc/greetd/config.toml
[terminal]
vt = 1

[default_session]
# Launch the compositor directly on DRM/KMS hardware
command = "QT_QPA_PLATFORM=eglfs $COMPOSITOR_PATH"
user = "$TARGET_USER"
EOF

systemctl enable greetd.service

echo "===================================================="
echo " Installation and System Configuration Complete!"
echo " GNOME has been removed. The system is now a Kiosk."
echo " Please type 'reboot' to restart your VM."
echo " Upon restart, it will instantly boot into your OS!"
echo "===================================================="
