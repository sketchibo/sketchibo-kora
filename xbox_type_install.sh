#!/bin/bash
# Install Xbox using text input method

BOX_IP="192.168.1.211:5555"

echo "========================================"
echo "XBOX INSTALL - TYPE METHOD"
echo "========================================"

adb connect $BOX_IP 2>/dev/null

# Method: Open Play Store and search
echo "[1/5] Opening Google Play Store..."
adb -s $BOX_IP shell am start -a android.intent.action.VIEW -d "market://details?id=com.microsoft.xboxbeta" 2>/dev/null || \
adb -s $BOX_IP shell am start -a android.intent.action.VIEW -d "https://play.google.com/store/apps/details?id=com.microsoft.xboxbeta" 2>/dev/null
echo "    Play Store opened"
sleep 4

echo ""
echo "[2/5] Taking screenshot..."
adb -s $BOX_IP shell screencap -p /sdcard/ps.png 2>/dev/null
adb -s $BOX_IP pull /sdcard/ps.png ~/Downloads/playstore_xbox.png 2>/dev/null
echo "    Screenshot: ~/Downloads/playstore_xbox.png"

echo ""
echo "[3/5] Navigating to Install button..."
# Navigate to Install (usually down then center)
adb -s $BOX_IP shell input keyevent 20  # DOWN
sleep 1
adb -s $BOX_IP shell input keyevent 20  # DOWN
sleep 1
adb -s $BOX_IP shell input keyevent 20  # DOWN
sleep 1
adb -s $BOX_IP shell input keyevent 23  # CENTER/ENTER
echo "    Install clicked"
sleep 5

echo ""
echo "[4/5] Confirming install..."
# Accept permissions (if prompted)
adb -s $BOX_IP shell input keyevent 22  # RIGHT
sleep 1
adb -s $BOX_IP shell input keyevent 23  # CENTER
echo "    Permissions accepted"
sleep 2

echo ""
echo "[5/5] Waiting for install..."
sleep 30  # Wait for download/install

echo ""
echo "Checking if installed..."
adb -s $BOX_IP shell pm list packages | grep xbox | grep -v "grep"

echo ""
echo "========================================"
echo "If Xbox shows in list above, launch with:"
echo "adb -s $BOX_IP shell am start -n com.microsoft.xboxbeta/com.microsoft.xbox.MainActivity"
echo "========================================"
