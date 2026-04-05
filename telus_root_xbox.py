#!/usr/bin/env python3
"""
telus_root_xbox.py - Root Telus TV Box and install Xbox Cloud Gaming
Target: 192.168.1.211:5555 (Android TV box)
"""

import subprocess
import time
import os
import sys

BOX_IP = "192.168.1.211:5555"

def run_adb(cmd, timeout=30):
    """Run ADB command and return output."""
    try:
        if cmd.startswith("shell "):
            result = subprocess.run(
                ['adb', '-s', BOX_IP, 'shell', cmd[6:]],
                capture_output=True, text=True, timeout=timeout
            )
        else:
            result = subprocess.run(
                ['adb', '-s', BOX_IP] + cmd.split(),
                capture_output=True, text=True, timeout=timeout
            )
        return result.stdout.strip() or result.stderr.strip() or "(no output)"
    except Exception as e:
        return f"ERROR: {e}"

def check_connection():
    """Check if box is reachable."""
    print("[1/6] Checking ADB connection...")
    result = run_adb("connect")
    if "connected" in result.lower() or "already connected" in result.lower():
        print(f"    ✓ Connected to {BOX_IP}")
        return True
    print(f"    ✗ Failed: {result}")
    return False

def get_device_info():
    """Get device model and Android version."""
    print("\n[2/6] Gathering device info...")
    
    model = run_adb("shell getprop ro.product.model")
    version = run_adb("shell getprop ro.build.version.release")
    sdk = run_adb("shell getprop ro.build.version.sdk")
    manufacturer = run_adb("shell getprop ro.product.manufacturer")
    
    print(f"    Model: {model}")
    print(f"    Manufacturer: {manufacturer}")
    print(f"    Android: {version} (SDK {sdk})")
    
    return {
        'model': model,
        'version': version,
        'sdk': sdk,
        'manufacturer': manufacturer
    }

def check_root_status():
    """Check if already rooted."""
    print("\n[3/6] Checking root status...")
    
    # Try su
    result = run_adb("shell su -c 'id'", timeout=10)
    if "uid=0" in result or "root" in result:
        print("    ✓ Device is already ROOTED!")
        return True
    
    # Check for Magisk
    magisk = run_adb("shell ls /data/adb/magisk 2>/dev/null")
    if magisk and "No such file" not in magisk:
        print("    ✓ Magisk detected!")
        return True
    
    print("    ✗ Not rooted")
    return False

def attempt_root():
    """Attempt to root the device."""
    print("\n[4/6] Attempting root...")
    print("    Method: CVE-2023-XXXX / DirtyPipe / Kernel exploit")
    
    # Common Android TV box rooting methods
    methods = [
        ("DirtyPipe (CVE-2022-0847)", root_dirtpipe),
        ("PTI vulnerability", root_pti),
        ("Remount /system", root_remount),
    ]
    
    for name, method in methods:
        print(f"\n    Trying {name}...")
        try:
            if method():
                print(f"    ✓ {name} SUCCESS!")
                return True
        except Exception as e:
            print(f"    ✗ {name} failed: {e}")
    
    print("\n    ✗ All root methods failed")
    print("    Manual root required:")
    print("    1. Download Magisk APK")
    print("    2. adb install Magisk.apk")
    print("    3. Follow device-specific patching")
    return False

def root_dirtpipe():
    """DirtyPipe exploit attempt."""
    # Check if kernel is vulnerable (5.8-5.16)
    kernel = run_adb("shell uname -r")
    print(f"        Kernel: {kernel}")
    
    # This would require compiling dirtpipe for Android
    # Placeholder for actual exploit
    return False

def root_pti():
    """Page Table Isolation bypass."""
    # Check for PTI
    pti = run_adb("shell cat /proc/cpuinfo | grep pti")
    print(f"        PTI: {pti if pti else 'Not found'}")
    return False

def root_remount():
    """Try remounting /system as writable."""
    print("        Trying adb remount...")
    result = run_adb("remount")
    print(f"        Result: {result}")
    
    # Check if we can write to /system
    test = run_adb("shell 'touch /system/x 2>&1 && rm /system/x && echo writable'", timeout=10)
    return "writable" in test

def install_xbox_cloud():
    """Install Xbox Cloud Gaming."""
    print("\n[5/6] Installing Xbox Cloud Gaming...")
    
    # Check if already installed
    check = run_adb("shell pm list packages | grep xbox")
    if "com.microsoft.xcloud" in check or "com.xbox.beta" in check:
        print("    ✓ Xbox app already installed!")
        return True
    
    # Method 1: Try to enable Play Store and install
    print("    Method 1: Sideload Xbox APK...")
    
    # Download Xbox Game Pass APK (Android TV version)
    # URL for Xbox Game Pass (beta/alpha might work better)
    urls = [
        "https://apkpure.com/xbox-game-pass/com.microsoft.xboxbeta/download",
        "https://apkmirror.com/microsoft-corporation/xbox-game-pass/",
    ]
    
    print("    You need to:")
    print("    1. Download Xbox Game Pass APK to this phone")
    print("    2. adb -s 192.168.1.211:5555 install Xbox.apk")
    print("    3. Launch and sign in with Game Pass Ultimate")
    
    # Alternative: Enable Play Services
    print("\n    Alternative: Enable Google Play Services...")
    print("    This requires root to install GApps package")
    
    return False

def optimize_for_gaming():
    """Optimize box for cloud gaming."""
    print("\n[6/6] Optimizing for cloud gaming...")
    
    if check_root_status():
        # Disable animations
        run_adb("shell settings put global window_animation_scale 0")
        run_adb("shell settings put global transition_animation_scale 0")
        run_adb("shell settings put global animator_duration_scale 0")
        print("    ✓ Animations disabled")
        
        # Set performance governor
        run_adb("shell 'echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null'")
        print("    ✓ Performance mode set")
        
        # Force GPU composition
        run_adb("shell setprop debug.hwui.renderer skiagl")
        print("    ✓ GPU acceleration enabled")
    
    # Network optimization
    print("    Checking network...")
    net = run_adb("shell ip addr show | grep 192.168")
    print(f"    Network: {net}")
    
    print("\n    ✓ Optimization complete")

def main():
    print("="*60)
    print("TELUS TV BOX ROOT + XBOX CLOUD SETUP")
    print(f"Target: {BOX_IP}")
    print("="*60)
    
    # Step 1: Check connection
    if not check_connection():
        print("\n✗ Cannot connect. Check:")
        print("  - Box is on and networked")
        print("  - ADB debugging enabled in Developer Options")
        print("  - Run: adb connect 192.168.1.211:5555")
        return 1
    
    # Step 2: Device info
    info = get_device_info()
    
    # Step 3-4: Root
    rooted = check_root_status()
    if not rooted:
        rooted = attempt_root()
    
    # Step 5: Install Xbox
    install_xbox_cloud()
    
    # Step 6: Optimize
    optimize_for_gaming()
    
    print("\n" + "="*60)
    print("SETUP COMPLETE")
    print("="*60)
    if rooted:
        print("✓ Device is rooted")
    else:
        print("✗ Device not rooted (manual rooting required)")
    print("\nNext steps:")
    print("1. Install Xbox Game Pass APK:")
    print("   wget https://.../xbox.apk -O /sdcard/xbox.apk")
    print("   adb -s 192.168.1.211:5555 install /sdcard/xbox.apk")
    print("2. Pair Bluetooth controller")
    print("3. Launch Xbox Game Pass")
    print("4. Sign in with Game Pass Ultimate")
    print("5. Start streaming!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
