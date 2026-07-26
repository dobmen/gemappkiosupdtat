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
SUDOERS_FILE="/etc/sudoers.d/010_kiosk_nopasswd"
cat <<EOF > "$SUDOERS_FILE"
# Allow Kiosk OS user to perform all sudo commands without a password for seamless updates
$REAL_USER ALL=(ALL) NOPASSWD: ALL
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
    libxcb-cursor0 \
    x11-xserver-utils \
    lightdm \
    openbox \
    git \
    curl

echo "[3/8] Configuring LightDM Auto-Login for user: $REAL_USER..."
# Ensure lightdm is the default display manager instead of gdm3
echo "/usr/sbin/lightdm" > /etc/X11/default-display-manager
DEBIAN_FRONTEND=noninteractive dpkg-reconfigure lightdm 2>/dev/null || true
systemctl disable gdm3 2>/dev/null || true

# Add user to autologin groups to ensure PAM allows passwordless boot
groupadd -f autologin
gpasswd -a $REAL_USER autologin
groupadd -f nopasswdlogin
gpasswd -a $REAL_USER nopasswdlogin

LIGHTDM_CONF_DIR="/etc/lightdm/lightdm.conf.d"
if [ -d "/etc/lightdm" ]; then
    mkdir -p "$LIGHTDM_CONF_DIR"
    cat <<EOF > "$LIGHTDM_CONF_DIR/50-kiosk-autologin.conf"
[Seat:*]
autologin-guest=false
autologin-user=$REAL_USER
autologin-user-timeout=0
user-session=openbox
EOF
    echo " -> Auto-login enabled via LightDM drop-in config (Session: Openbox)."
else
    echo " ⚠ LightDM config directory not found. Skipping auto-login configuration."
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

# Ensure LightDM starts on boot (and GDM3 is disabled)
systemctl disable gdm3 2>/dev/null || true
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