#!/usr/bin/env bash
# =================================================================
# KIOSK OS - AUTO-DETECTING HARDWARE LAUNCHER
# =================================================================

# Resolve exact script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Enable Qt hardware acceleration and touchscreen optimization
export QT_QPA_PLATFORM=xcb
export QT_QPA_GENERIC_PLUGINS=evdevtouch
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export PYGAME_HIDE_SUPPORT_PROMPT=1

# Prevent screen blanking or power saving during runtime
xset s noblank 2>/dev/null
xset s off 2>/dev/null
xset -dpms 2>/dev/null

# -------------------------------------------------------------
# HARDWARE DISPLAY AUTO-DETECTION
# -------------------------------------------------------------
echo "[Hardware Detect] Checking connected display resolution..."

# Try reading resolution from X11 server, fallback to framebuffer
RES=$(xdpyinfo 2>/dev/null | grep 'dimensions:' | awk '{print $2}')
if [ -z "$RES" ]; then
    RES=$(cat /sys/class/graphics/fb0/modes 2>/dev/null | head -n 1 | cut -d':' -f2 | cut -d'-' -f1)
fi

# Classify the connected display hardware
if [[ "$RES" == *"1200x1920"* ]]; then
    OUTPUT=$(xrandr | grep " connected" | awk '{print $1}' | head -n 1)
    echo "[Hardware Detect] ⟳ Portrait Display Detected ($RES) on $OUTPUT. Rotating to Landscape..."
    if [ -n "$OUTPUT" ]; then
        xrandr --output $OUTPUT --rotate right
        
        # When X11 rotates the screen, touch coordinates don't rotate automatically.
        # Apply the 90-degree clockwise (right) Transformation Matrix to all pointers.
        for device in $(xinput list | grep "pointer" | grep -v "master" | grep -v "Virtual" | sed -n 's/.*id=\([0-9]*\).*/\1/p'); do
            xinput set-prop "$device" "Coordinate Transformation Matrix" 0 1 0 -1 0 1 0 0 1 2>/dev/null || true
        done
    fi
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

# Activate virtual environment and boot OS
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "[Kiosk OS] Starting X11 Compositor (picom)..."
picom -b --vsync 2>/dev/null || true

echo "[Kiosk OS] Starting system..."
python3 main.py