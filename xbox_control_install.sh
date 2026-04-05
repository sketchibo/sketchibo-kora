#!/bin/bash
# Install Xbox Cloud Gaming using on-screen controls via ADB
# Navigates browser and installs without sideloading APK

BOX_IP="192.168.1.211:5555"

echo "========================================"
echo "XBOX CLOUD - CONTROL METHOD"
echo "Using on-screen navigation"
echo "========================================"

# Keycodes for Android TV
KEY_ENTER=66
KEY_DPAD_UP=19
KEY_DPAD_DOWN=20
KEY_DPAD_LEFT=21
KEY_DPAD_RIGHT=22
KEY_DPAD_CENTER=23
KEY_BACK=4
KEY_HOME=3
KEY_MENU=82

echo "[1/8] Connecting to box..."
adb connect $BOX_IP 2>/dev/null

echo "[2/8] Taking screenshot to see current state..."
adb -s $BOX_IP shell screencap -p /sdcard/screen.png 2>/dev/null
adb -s $BOX_IP pull /sdcard/screen.png ~/Downloads/tv_current.png 2>/dev/null
echo "    Screenshot saved to ~/Downloads/tv_current.png"

echo ""
echo "[3/8] Launching Chrome browser..."
adb -s $BOX_IP shell am start -n com.android.chrome/com.google.android.apps.chrome.Main 2>/dev/null || \
adb -s $BOX_IP shell am start -a android.intent.action.VIEW -d "https://www.xbox.com/en-US/play" 2>/dev/null
echo "    Browser launched"
sleep 3

echo ""
echo "[4/8] Typing Xbox URL..."
# Clear any existing text and type URL
adb -s $BOX_IP shell input text "xbox.com/play" 2>/dev/null
echo "    URL typed"
sleep 2

echo ""
echo "[5/8] Pressing Enter..."
adb -s $BOX_IP shell input keyevent $KEY_ENTER
echo "    Loading xbox.com/play..."
sleep 5

echo ""
echo "[6/8] Navigating to install..."
echo "    Sending navigation commands..."
# Navigate down to "Play" or "Install" button
adb -s $BOX_IP shell input keyevent $KEY_DPAD_DOWN
sleep 1
adb -s $BOX_IP shell input keyevent $KEY_DPAD_DOWN
sleep 1
adb -s $BOX_IP shell input keyevent $KEY_DPAD_CENTER
echo "    Selection made"
sleep 3

echo ""
echo "[7/8] Confirming download/install..."
# Handle any install prompts
adb -s $BOX_IP shell input keyevent $KEY_DPAD_RIGHT
sleep 1
adb -s $BOX_IP shell input keyevent $KEY_DPAD_CENTER
echo "    Install confirmed"
sleep 2

echo ""
echo "[8/8] Final screenshot..."
adb -s $BOX_IP shell screencap -p /sdcard/screen.png 2>/dev/null
adb -s $BOX_IP pull /sdcard/screen.png ~/Downloads/tv_after_install.png 2>/dev/null
echo "    Screenshot saved"

echo ""
echo "========================================"
echo "CONTROL SEQUENCE COMPLETE"
echo "========================================"
echo ""
echo "Check screenshots in ~/Downloads/"
echo ""
echo "If install didn't complete automatically:"
echo "1. Use TV remote to navigate"
echo "2. Look for 'Get the app' or 'Install' button"
echo "3. Accept permissions"
echo "4. Wait for download"
echo ""
echo "Alternative: Use voice remote and say"
echo "'Xbox Game Pass' to search"
