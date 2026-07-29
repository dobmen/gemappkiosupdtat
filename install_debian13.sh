#!/bin/bash
set -e

echo "===================================================="
echo " Kiosk OS (Debian 13) Dependencies Installer"
echo "===================================================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./install_debian13.sh)"
  exit 1
fi

echo "[1/2] Updating package repositories..."
apt-get update

echo "[2/2] Installing C++ Qt6 Wayland Compositor dependencies..."
apt-get install -y \
    build-essential \
    cmake \
    qt6-base-dev \
    qt6-declarative-dev \
    qt6-wayland-dev \
    libqt6waylandcompositor6-dev \
    qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts \
    qml6-module-qtquick-window \
    qml6-module-qtwayland-compositor \
    qt6-wayland

echo "===================================================="
echo " Dependencies Installed Successfully!"
echo " Next Steps:"
echo " 1. cd os_compositor"
echo " 2. mkdir build && cd build"
echo " 3. cmake .."
echo " 4. make"
echo " 5. ./kiosk_os"
echo "===================================================="
