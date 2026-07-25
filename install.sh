#!/usr/bin/env bash
# =================================================================
# KIOSK OS - STANDALONE BOOTSTRAP HARDWARE INSTALLER
# =================================================================

set -e

echo "================================================="
echo "   STARTING KIOSK OS HARDWARE DEPLOYMENT         "
echo "   Target Resolution : Auto-Detecting            "
echo "   Installation Path : ~/kiosk_os                "
echo "================================================="

# 1. Check for root/sudo privileges for system packages
if [ "$EUID" -ne 0 ]; then
    echo "Please run this installer with sudo: sudo ./install.sh"
    exit 1
fi

# Get the actual user who invoked sudo and define the installation path
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)
INSTALL_DIR="$REAL_HOME/kiosk_os"

# The GitHub repository to clone the entire Kiosk OS system from
GITHUB_REPO_URL="https://github.com/dobmen/gemappkiosupdtat.git"

echo "[1/7] Configuring passwordless sudo for system power & update commands..."
SUDOERS_FILE="/etc/sudoers.d/kiosk_nopasswd"
cat <<EOF > "$SUDOERS_FILE"
# Allow Kiosk OS user to reboot, shut down, and manage services without a password
$REAL_USER ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown, /usr/sbin/reboot, /usr/sbin/shutdown, /bin/reboot, /bin/shutdown, /usr/bin/systemctl
EOF
chmod 0440 "$SUDOERS_FILE"
echo " -> Passwordless sudo configured successfully."

echo "[2/7] Updating system and installing Linux audio/display/git dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libasound2-dev \
    portaudio19-dev \
    libjack-jackd2-dev \
    libgl1 \
    libglx-mesa0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    x11-xserver-utils \
    git \
    curl

echo "[3/7] Pulling fresh Kiosk OS directly from GitHub (main branch)..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo " -> Existing Git repo found at $INSTALL_DIR. Pulling latest changes..."
    sudo -u $REAL_USER git -C "$INSTALL_DIR" fetch origin
    sudo -u $REAL_USER git -C "$INSTALL_DIR" checkout -B main origin/main
else
    echo " -> Cloning fresh Kiosk OS repository into $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
    sudo -u $REAL_USER git clone -b main "$GITHUB_REPO_URL" "$INSTALL_DIR"
fi

# Move into the newly cloned installation directory for all subsequent steps
cd "$INSTALL_DIR"

echo "[4/7] Creating Python virtual environment..."
sudo -u $REAL_USER python3 -m venv venv
source venv/bin/activate

echo "[5/7] Installing Python libraries..."
pip install --upgrade pip --quiet
pip install --quiet \
    PyQt6 \
    PyQt6-WebEngine \
    speechrecognition \
    pyaudio \
    spotipy \
    requests

echo "[6/7] Creating runtime directories & generating default config..."
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
    echo " -> Created fresh config.json."
else
    echo " -> Existing config.json preserved."
fi

# Make launcher executable and fix recursive file ownership
chmod +x "$INSTALL_DIR/launch.sh"
chown -R $REAL_USER:$REAL_USER "$INSTALL_DIR"

echo "[7/7] Registering Kiosk OS as an automatic startup service..."
SERVICE_FILE="/etc/systemd/system/kiosk.service"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Kiosk OS Touchscreen Interface
After=network.target graphical.target systemd-user-sessions.service

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/launch.sh
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=$REAL_HOME/.Xauthority

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable kiosk.service

echo "================================================="
echo "   INSTALLATION & CLONING COMPLETE!              "
echo "================================================="
echo "Kiosk OS has been installed to: $INSTALL_DIR"
echo ""
echo "You can now reboot the device. It will boot directly"
echo "into Kiosk OS with auto-detected hardware scaling:"
echo "   sudo reboot"
echo "================================================="