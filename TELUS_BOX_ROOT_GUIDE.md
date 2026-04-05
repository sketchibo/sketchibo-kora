# Telus TV Box (TELUSTV-24S) Root + Xbox Cloud Guide

## Device Info
- **Model**: TELUSTV-24S  
- **Android**: 12 (API 31)
- **Kernel**: 5.4.289 (June 2025)
- **Arch**: ARMv8 (64-bit)
- **ADB**: 192.168.1.211:5555

## Root Status: NOT ROOTED
Kernel is patched (5.4.289 from June 2025). Modern exploits won't work.

## Part 1: ROOTING OPTIONS

### Option A: Magisk Patch (Recommended)
Requires:
1. Stock firmware dump (boot.img)
2. Magisk app on phone
3. Patch boot.img with Magisk
4. Flash via fastboot

**Steps:**
```bash
# 1. Dump current boot partition
adb shell su -c "dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/boot.img"
adb pull /sdcard/boot.img ~/telus_boot.img

# 2. Patch with Magisk on phone
# Install Magisk app, select "Install > Select and Patch a File"
# Choose ~/telus_boot.img

# 3. Flash patched boot.img
adb reboot bootloader
fastboot flash boot ~/magisk_patched_xxxxx.img
fastboot reboot
```

### Option B: Kernel Exploit (Low Success Rate)
- CVE-2022-0847 (DirtyPipe): Kernel 5.4 is patched
- CVE-2023-XXXX: Unknown, unlikely on June 2025 kernel

### Option C: Developer Build
Contact Telus for developer firmware (unlikely)

## Part 2: XBOX CLOUD GAMING (No Root Required)

### Method: Sideload Xbox Game Pass APK

**Step 1: Download Xbox APK**
On your phone:
1. Go to https://www.xbox.com/play
2. Or https://apkpure.com/xbox-game-pass/com.microsoft.xboxbeta
3. Download APK (~50-80MB)
4. Transfer to Downloads folder

**Step 2: Install**
```bash
adb connect 192.168.1.211:5555
adb install ~/Downloads/xbox_gamepass.apk
```

**Step 3: Launch**
```bash
adb shell am start -n com.microsoft.xboxbeta/com.microsoft.xbox.MainActivity
```

**Step 4: Sign In**
- Requires Xbox Game Pass Ultimate ($14.99/month)
- Sign in with Microsoft account
- Pair controller via Bluetooth

## Part 3: OPTIMIZATIONS (No Root)

```bash
# Reduce animations
adb shell settings put global window_animation_scale 0.5
adb shell settings put global transition_animation_scale 0.5

# Disable background apps
adb shell pm disable-user com.android.tv.launcher
adb shell pm disable-user com.google.android.tvlauncher

# WiFi optimization
adb shell settings put global wifi_scan_throttle_enabled 0

# Set performance mode (if available)
adb shell settings put global game_mode 1
```

## Part 4: ROOT ALTERNATIVE (Advanced)

If you can't root but need system-level changes:

### ADB Shell as System User
```bash
# Some boxes allow system-level ADB
adb shell
# Then: pm grant com.microsoft.xboxbeta android.permission.WRITE_SECURE_SETTINGS
```

### Accessibility Service Method
Apps can use accessibility services for system-level control without root.

## Current Assessment

**Root Difficulty**: HIGH
- Kernel is fully patched
- No known exploits for 5.4.289
- Would need firmware dump + Magisk patch

**Xbox Cloud without Root**: POSSIBLE
- Just sideload APK
- No system modifications needed
- Works with Game Pass Ultimate subscription

## Recommendation

1. **Don't root** - Not worth the effort/risk for Xbox Cloud
2. **Sideload Xbox app** - Takes 5 minutes, works perfectly
3. **Use Ethernet** - Better latency for cloud gaming
4. **Get Game Pass Ultimate** - Required for streaming

## Quick Commands

```bash
# Connect
adb connect 192.168.1.211:5555

# Install Xbox
adb install ~/Downloads/xbox.apk

# Launch Xbox
adb shell am start -n com.microsoft.xboxbeta/com.microsoft.xbox.MainActivity

# Screenshot
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png ~/xbox_screen.png
```

## Files Created
- `telus_root_xbox.py` - Automated root attempt (unlikely to work)
- `xbox_cloud_setup.sh` - Setup script
- This guide

## Status
⚠️ Root: Not feasible with current kernel
✅ Xbox Cloud: Ready to sideload
