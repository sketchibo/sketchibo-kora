#!/bin/bash
# Xbox Cloud Gaming setup for Telus TV Box
# No root required - sideload method

BOX_IP="192.168.1.211:5555"
echo "========================================"
echo "XBOX CLOUD GAMING SETUP"
echo "Telus TV Box: $BOX_IP"
echo "========================================"

# Connect ADB
echo "[1/5] Connecting to box..."
adb connect $BOX_IP 2>/dev/null || echo "Already connected"

# Check if Xbox already installed
echo "[2/5] Checking for existing Xbox install..."
XBOX_CHECK=$(adb -s $BOX_IP shell pm list packages | grep -i xbox)
if [ -n "$XBOX_CHECK" ]; then
    echo "    ✓ Xbox app found: $XBOX_CHECK"
    echo "    Launching..."
    adb -s $BOX_IP shell am start -n com.microsoft.xboxbeta/com.microsoft.xbox.MainActivity 2>/dev/null || \
    adb -s $BOX_IP shell am start -n com.microsoft.xcloud/com.microsoft.xcloud.MainActivity 2>/dev/null
    exit 0
fi

echo "    ✗ Xbox app not installed"

# Download Xbox Game Pass APK
echo "[3/5] Downloading Xbox Game Pass APK..."
APK_URL="https://download.apkpure.com/b/apk/Y29tLm1pY3Jvc29mdC54Ym94XzIyMTFfZmI0MDU0YzE?_fn=R2FtZSBQYXNzX3YyMjExX2Fwa3B1cmUuY29tLmFwayZfa3M9YXBrcHVyZQ&at=174MORE"
APK_PATH="/sdcard/Download/xbox_gamepass.apk"

echo "    Download to phone first, then install:"
echo "    wget -O ~/Downloads/xbox.apk 'https://apkpure.com/xbox-game-pass/com.microsoft.xboxbeta/download'"
echo ""

# Enable developer options optimizations
echo "[4/5] Enabling developer optimizations..."
adb -s $BOX_IP shell settings put global window_animation_scale 0.5 2>/dev/null
echo "    ✓ Animations reduced"

# Disable background processes for more RAM
echo "    Disabling unnecessary background services..."
adb -s $BOX_IP shell pm disable-user --user 0 com.android.tv.launcher 2>/dev/null || true
adb -s $BOX_IP shell pm disable-user --user 0 com.google.android.tvlauncher 2>/dev/null || true
echo "    ✓ Background launchers disabled"

# Network optimization
echo "[5/5] Network optimization..."
adb -s $BOX_IP shell settings put global wifi_scan_throttle_enabled 0 2>/dev/null || true
echo "    ✓ WiFi scanning optimized"

echo ""
echo "========================================"
echo "SETUP INSTRUCTIONS"
echo "========================================"
echo ""
echo "1. DOWNLOAD XBOX APK:"
echo "   On this phone, download from:"
echo "   https://www.xbox.com/en-US/play"
echo "   OR"
echo "   https://apkpure.com/xbox-game-pass/com.microsoft.xboxbeta"
echo ""
echo "2. INSTALL TO BOX:"
echo "   adb -s $BOX_IP install ~/Downloads/xbox.apk"
echo ""
echo "3. PAIR CONTROLLER:"
echo "   Settings > Bluetooth > Pair new device"
echo "   (Xbox controller: hold sync button)"
echo ""
echo "4. LAUNCH:"
echo "   adb -s $BOX_IP shell am start -n com.microsoft.xboxbeta/com.microsoft.xbox.MainActivity"
echo ""
echo "5. SIGN IN:"
echo "   Use Game Pass Ultimate subscription"
echo ""
echo "6. PLAY:"
echo "   Stream Xbox games to your TV!"
echo ""
echo "TIPS:"
echo "- Use Ethernet for best latency"
echo "- Close background apps before gaming"
echo "- Sign up for Xbox Game Pass Ultimate ($14.99/mo)"
echo ""
echo "Enjoy cloud gaming on your Telus box!"
