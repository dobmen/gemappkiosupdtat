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

echo "[1/8] Configuring passwordless sudo for system power & update commands..."
SUDOERS_FILE="/etc/sudoers.d/kiosk_nopasswd"
cat <<EOF > "$SUDOERS_FILE"
# Allow Kiosk OS user to reboot, shut down, and manage services without a password
$REAL_USER ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown, /usr/sbin/reboot, /usr/sbin/shutdown, /bin/reboot, /bin/shutdown, /usr/bin/systemctl
EOF
chmod 0440 "$SUDOERS_FILE"
echo " -> Passwordless sudo configured successfully."

echo "[2/8] Updating system and installing Linux audio/display/window manager dependencies..."
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
    lightdm \
    openbox \
    git \
    curl

echo "[3/8] Configuring LightDM Auto-Login for user: $REAL_USER..."
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"
if [ -f "$LIGHTDM_CONF" ]; then
    # Uncomment or set auto-login fields in lightdm.conf
    sed -i "s/#autologin-user=/autologin-user=$REAL_USER/" "$LIGHTDM_CONF"
    sed -i "s/#autologin-user-timeout=0/autologin-user-timeout=0/" "$LIGHTDM_CONF"
    
    # If lines don't exist under [Seat:*], ensure they are added
    if ! grep -q "autologin-user=$REAL_USER" "$LIGHTDM_CONF"; then
        sed -i "/\[Seat:\*\]/a autologin-user=$REAL_USER\nautologin-user-timeout=0" "$LIGHTDM_CONF"
    fi
    echo " -> Auto-login enabled via LightDM."
else
    echo " ⚠ LightDM config not found. Skipping auto-login configuration."
fi

echo "[4/8] Pulling fresh Kiosk OS directly from GitHub (main branch)..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo " -> Existing Git repo found at $INSTALL_DIR. Pulling latest changes..."
    sudo -u $REAL_USER git -C "$INSTALL_DIR" fetch origin
    sudo -u $REAL_USER git -C "$INSTALL_DIR" checkout -B main origin/main
else
    echo " -> Cloning fresh Kiosk OS repository into $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
    sudo -u $REAL_USER git clone -b main "$GITHUB_REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo "[5/8] Creating Python virtual environment..."
sudo -u $REAL_USER python3 -m venv venv
source venv/bin/activate

echo "[6/8] Installing Python libraries..."
pip install --upgrade pip --quiet
pip install --quiet \
    PyQt6 \
    PyQt6-WebEngine \
    speechrecognition \
    pyaudio \
    spotipy \
    requests

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
    echo " -> Created fresh config.json."
fi

# Make launcher executable and fix recursive file ownership
chmod +x "$INSTALL_DIR/launch.sh"
chown -R $REAL_USER:$REAL_USER "$INSTALL_DIR"

echo "[8/8] Configuring Openbox session to auto-launch Kiosk OS..."
# Create an XDG autostart entry for openbox so it runs launch.sh right when the GUI boots
AUTOSTART_DIR="$REAL_HOME/.config/openbox"
sudo -u $REAL_USER mkdir -p "$AUTOSTART_DIR"

cat <<EOF > "$AUTOSTART_DIR/autostart"
# Launch Kiosk OS automatically inside the lightweight Openbox session
$INSTALL_DIR/launch.sh &
EOF
chown -R $REAL_USER:$REAL_USER "$REAL_HOME/.config"

# Ensure LightDM starts on boot
systemctl enable lightdm.service

echo "================================================="
echo "   INSTALLATION & KIOSK ENVIRONMENT COMPLETE!    "
echo "================================================="
echo "Kiosk OS has been installed to: $INSTALL_DIR"
echo ""
echo "When you reboot, Debian 13 will auto-login into LightDM,"
echo "spawn Openbox, and launch your Kiosk application full-screen."
echo "   sudo reboot"
echo "================================================="