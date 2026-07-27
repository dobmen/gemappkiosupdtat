#!/usr/bin/env bash
# =================================================================
# KIOSK OS - AUTO-DETECTING HARDWARE LAUNCHER (WAYLAND)
# =================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Enable logging for debugging Wayland boot issues
exec > >(tee -a /tmp/kiosk_boot.log) 2>&1
set -x

export QT_QPA_PLATFORM=wayland
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export PYGAME_HIDE_SUPPORT_PROMPT=1

# Check if we are already inside Wayland
if [ "$XDG_SESSION_TYPE" == "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    echo "[Hardware Detect] Checking connected display resolution..."
    
    # Try reading resolution from wlr-randr
    if command -v wlr-randr &> /dev/null; then
        RES=$(wlr-randr | grep "current" | awk '{print $1}')
        OUTPUT=$(wlr-randr | grep -m 1 "^[a-zA-Z0-9-]" | awk '{print $1}')
        
        # Classify the connected display hardware
        if [[ "$RES" == *"1200x1920"* ]]; then
            echo "[Hardware Detect] ⟳ Portrait Display Detected ($RES) on $OUTPUT. Rotating to Landscape..."
            wlr-randr --output $OUTPUT --rotate right
            export KIOSK_DISPLAY_MODE="WIDESCREEN_1200P"
        elif [[ "$RES" == *"1920x1200"* ]] || [[ "$RES" == *"1920x1080"* ]]; then
            export KIOSK_DISPLAY_MODE="WIDESCREEN_1200P"
            echo "[Hardware Detect] ✔ Identified Display: Pro Widescreen ($RES)"
        elif [[ "$RES" == *"1024x600"* ]] || [[ "$RES" == *"1024x768"* ]]; then
            export KIOSK_DISPLAY_MODE="COMPACT_600P"
            echo "[Hardware Detect] ✔ Identified Display: Compact Touchscreen ($RES)"
        else
            export KIOSK_DISPLAY_MODE="CUSTOM"
            echo "[Hardware Detect] ⚠ Custom/Unknown Display Detected ($RES) - Using dynamic scaling."
        fi
    else
        export KIOSK_DISPLAY_MODE="CUSTOM"
    fi

    # Activate virtual environment and boot OS
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    echo "[Kiosk OS] Starting system..."
    python3 main.py
else
    # We are NOT in Wayland yet. Launch labwc!
    echo "[Kiosk OS] Starting Wayland Compositor (labwc)..."
    
    mkdir -p ~/.config/labwc
    
    # Configure Labwc autostart to run this script again inside Wayland
    cat <<EOF > ~/.config/labwc/autostart
bash "$DIR/launch.sh"
EOF

    # Configure Labwc environment rules
    cat <<EOF > ~/.config/labwc/environment
XCURSOR_SIZE=24
EOF

    # Configure Labwc basic XML (remove window decorations and borders)
    cat <<EOF > ~/.config/labwc/rc.xml
<?xml version="1.0"?>
<labwc_config>
  <core>
    <gap>0</gap>
  </core>
  <theme>
    <name>default</name>
    <cornerRadius>0</cornerRadius>
    <borderWidth>0</borderWidth>
  </theme>
  <keyboard>
    <default>
      <keybind key="W-q"><action name="Exit"/></keybind>
    </default>
  </keyboard>
</labwc_config>
EOF

    exec labwc
fi