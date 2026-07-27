#!/usr/bin/env bash
# =================================================================
# KIOSK OS - STANDALONE BOOTSTRAP HARDWARE INSTALLER (DEBIAN 13)
# =================================================================

set -e

echo "================================================="
echo "   STARTING KIOSK OS HARDWARE DEPLOYMENT         "
echo "   Target Resolution : Auto-Detecting            "
echo "   Installation Path : ~/kiosk_os                "
echo "================================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run this installer with sudo: sudo bash install.sh"
    exit 1
fi

REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)
INSTALL_DIR="$REAL_HOME/kiosk_os"
GITHUB_REPO_URL="https://github.com/dobmen/gemappkiosupdtat.git"

echo "[1/8] Configuring passwordless sudo for system power & update commands..."
SUDOERS_FILE="/etc/sudoers.d/010_kiosk_nopasswd"
cat <<EOF > "$SUDOERS_FILE"
$REAL_USER ALL=(ALL) NOPASSWD: ALL
EOF
chmod 0440 "$SUDOERS_FILE"

echo "[2/8] Updating system and installing Linux audio/Wayland dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3-pip python3-venv python3-dev build-essential \
    libasound2-dev portaudio19-dev libjack-jackd2-dev \
    libgl1 libglx-mesa0 libgbm1 libdrm2 \
    labwc wlr-randr wayland-protocols \
    python3-pyqt6 python3-pyqt6.qtwebengine python3-pyqt6.qtquick \
    qml6-module-qtquick-controls qml6-module-qtquick-layouts qml6-module-qtquick-templates2 qml6-module-qtquick-effects \
    qt6-wayland \
    libqt6webenginecore6 libqt6webenginewidgets6 \
    alsa-utils network-manager bluez \
    libnss3 git curl unzip wget openssh-server \
    polkitd seatd dbus-x11

echo "[3/8] Removing legacy LightDM & Openbox to ensure pure Wayland boot..."
systemctl disable lightdm 2>/dev/null || true
systemctl disable gdm3 2>/dev/null || true

echo "[3.5/8] Granting hardware permissions to user..."
getent group seat || groupadd seat
usermod -a -G seat,video,render,input $REAL_USER
systemctl enable seatd

echo "[3.8/8] Applying global touchscreen calibration matrix..."
cat << 'EOF' | tee /etc/udev/rules.d/99-touchscreen.rules > /dev/null
ACTION=="add|change", SUBSYSTEM=="input", ATTRS{name}=="Wacom HID 4808 Finger", ENV{LIBINPUT_CALIBRATION_MATRIX}="0 1 0 -1 0 1"
ACTION=="add|change", SUBSYSTEM=="input", ATTRS{name}=="Wacom HID 4808 Pen", ENV{LIBINPUT_CALIBRATION_MATRIX}="0 1 0 -1 0 1"
EOF
udevadm control --reload-rules && udevadm trigger

echo "[4/8] Pulling fresh Kiosk OS directly from GitHub (main branch)..."
if [ -d "$INSTALL_DIR/.git" ]; then
    sudo -u $REAL_USER git -C "$INSTALL_DIR" fetch origin
    sudo -u $REAL_USER git -C "$INSTALL_DIR" reset --hard origin/main
    sudo -u $REAL_USER git -C "$INSTALL_DIR" checkout -B main origin/main
else
    rm -rf "$INSTALL_DIR"
    sudo -u $REAL_USER git clone -b main "$GITHUB_REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

echo "[5/8] Creating Python virtual environment..."
sudo -u $REAL_USER python3 -m venv venv

echo "[6/8] Installing Python libraries..."
sudo -u $REAL_USER venv/bin/pip install --upgrade pip --quiet
sudo -u $REAL_USER venv/bin/pip install --quiet -r requirements.txt

echo "[7/8] Creating runtime directories & generating default config..."
sudo -u $REAL_USER mkdir -p apps clockfaces photos screenshots videos browser_data web_app_data icons fonts

CONFIG_FILE="$INSTALL_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    sudo -u $REAL_USER cat <<EOF > "$CONFIG_FILE"
{
    "clockface_index": 0,
    "classic_color": "#FFFFFF",
    "classic_bg": "#0C0C0E",
    "stacked_hour": "#FFFFFF",
    "stacked_min": "#5A8DEF",
    "stacked_bg": "#0C0C0E",
    "analog_theme": "dark",
    "neon_digital_color": "#1ED760",
    "neon_digital_bg": "#0C0C0E",
    "app_drawer_scale": 100,
    "app_drawer_layout": "grid",
    "system_volume": 80,
    "brightness": 85,
    "silent_mode": false,
    "dnd_mode": false,
    "update_channel": "main",
    "os_version": "0.1.0"
}
EOF
fi

chmod +x "$INSTALL_DIR/launch.sh"
chown -R $REAL_USER:$REAL_USER "$INSTALL_DIR"

echo "[8/8] Configuring systemd for direct Wayland boot (tty1)..."
SERVICE_FILE="/etc/systemd/system/kiosk-wayland.service"
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Labwc Kiosk Wayland Session
After=systemd-user-sessions.service network.target sound.target seatd.service
Wants=seatd.service
Conflicts=getty@tty1.service

[Service]
User=$REAL_USER
PAMName=login
WorkingDirectory=$INSTALL_DIR
StandardInput=tty
StandardOutput=journal
StandardError=journal
TTYPath=/dev/tty1
Environment=XDG_SESSION_TYPE=wayland
Environment=XDG_CURRENT_DESKTOP=labwc
Environment=QT_QPA_PLATFORM=wayland
ExecStart=/bin/bash $INSTALL_DIR/launch.sh
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable kiosk-wayland.service

echo "================================================="
echo "   INSTALLATION & KIOSK ENVIRONMENT COMPLETE!    "
echo "================================================="
echo "Kiosk OS has been installed to: $INSTALL_DIR"
echo ""
echo "When you reboot, Debian 13 will bypass LightDM,"
echo "and boot directly into a pure hardware-accelerated"
echo "Wayland (labwc) session on tty1 at 60 FPS."
echo "   sudo reboot"
echo "================================================="