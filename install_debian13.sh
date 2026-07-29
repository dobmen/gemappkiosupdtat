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
    qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts \
    qml6-module-qtquick-window \
    qml6-module-qtwayland-compositor \
    qt6-wayland

echo "[3/3] Building the C++ Wayland Compositor..."
cd "$(dirname "$0")/os_compositor"
mkdir -p build
cd build
cmake ..
make -j$(nproc)

echo "===================================================="
echo " Installation and Build Complete!"
echo " The OS is ready. To launch it, run:"
echo " cd os_compositor/build && ./kiosk_os"
echo "===================================================="
