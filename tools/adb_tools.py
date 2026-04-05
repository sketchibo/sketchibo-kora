import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BOX_IP = "192.168.1.211:5555"

def adb(command):
    try:
        if command.strip().startswith('shell '):
            shell_cmd = command.strip()[6:]
            result = subprocess.run(['adb','-s',BOX_IP,'shell',shell_cmd],capture_output=True,text=True,timeout=15)
        else:
            result = subprocess.run(f"adb -s {BOX_IP} {command}",shell=True,capture_output=True,text=True,timeout=15)
        return result.stdout.strip() or result.stderr.strip() or '(ok)'
    except Exception as e:
        return f"ADB ERROR: {e}"

def tv_screenshot():
    try:
        subprocess.run(f"adb -s {BOX_IP} shell screencap -p /sdcard/kora_screen.png",shell=True,timeout=10)
        out = BASE_DIR / 'vision'
        out.mkdir(exist_ok=True)
        subprocess.run(f"adb -s {BOX_IP} pull /sdcard/kora_screen.png {out}/tv_latest.png",shell=True,timeout=10)
        return f"Screenshot saved to {out}/tv_latest.png"
    except Exception as e:
        return f"ERROR: {e}"
