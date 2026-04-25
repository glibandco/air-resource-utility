#!/usr/bin/env python3
"""
MacBook Air Resource Monitor — menu bar app
Live CPU% in your menu bar. Click for RAM, battery, thermals, and top apps.

Run:
    python3 menubar.py

Click "Open dashboard" in the menu to also launch the full web view (monitor.py).
"""

import os
import subprocess
import sys
import threading
import webbrowser
from collections import defaultdict


# --- Dependency bootstrap -----------------------------------------------------
# pyobjc 12.x dropped Python 3.9 support (and the wheel was yanked), so we pin
# to <11 — those releases ship binary wheels for macOS system Python 3.9.
def _pip_install(*pkgs):
    """pip install --user, falling back to --break-system-packages on newer pythons."""
    base = [sys.executable, "-m", "pip", "install", "--user", "--upgrade", "--quiet"]
    # Older pip (Py3.9) doesn't accept --break-system-packages; try plain first.
    for extra in ([], ["--break-system-packages"]):
        try:
            r = subprocess.run(base + extra + list(pkgs), capture_output=True, text=True)
            if r.returncode == 0:
                return
        except Exception:
            continue
    # Last resort: run loudly so the user sees the error.
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--user", "--upgrade"] + list(pkgs)
    )


try:
    import psutil  # noqa: E402
except ImportError:
    print("Installing psutil (one-time)...")
    _pip_install("psutil")
    import psutil  # noqa: E402

try:
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory  # noqa: E402
except ImportError:
    print("Installing pyobjc (one-time, this may take a moment)...")
    _pip_install("pyobjc-core<11", "pyobjc-framework-Cocoa<11")
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory  # noqa: E402

try:
    import rumps  # noqa: E402
except ImportError:
    print("Installing rumps (one-time)...")
    _pip_install("rumps")
    import rumps  # noqa: E402

# Hide the dock icon — this is a menu-bar-only app.
NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)

# Prime cpu_percent so the first reading isn't 0.
psutil.cpu_percent(interval=None)
for _p in psutil.process_iter():
    try:
        _p.cpu_percent(None)
    except Exception:
        pass

# Process names that share a common prefix (e.g. "Google Chrome Helper")
# are rolled up under one app row.
GROUP_PREFIXES = [
    "Claude", "Comet", "Google Chrome", "Chrome", "Safari", "Slack",
    "Cursor", "Code", "Arc", "Firefox", "Xcode", "Spotify", "Notion",
    "Figma", "Discord", "WhatsApp", "Zoom", "Microsoft", "Adobe",
]

DASHBOARD_PORT = 8765
TOP_N = 6


def get_thermal_state():
    """Returns (state_label, percent) by reading `pmset -g therm`."""
    try:
        out = subprocess.check_output(
            ["pmset", "-g", "therm"], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        for line in out.splitlines():
            if "CPU_Scheduler_Limit" in line:
                v = int(line.split("=")[-1].strip())
                if v >= 100:
                    return "Nominal", v
                if v >= 75:
                    return "Mild throttle", v
                return "Throttling", v
        return "Nominal", 100
    except Exception:
        return "Unknown", None


def aggregate_top():
    agg = defaultdict(lambda: [0.0, 0])
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            name = p.info["name"] or ""
            key = name
            low = name.lower()
            for prefix in GROUP_PREFIXES:
                if low.startswith(prefix.lower()):
                    key = prefix
                    break
            agg[key][0] += p.info["cpu_percent"] or 0
            agg[key][1] += p.info["memory_info"].rss if p.info["memory_info"] else 0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    cpu_count = psutil.cpu_count(logical=True) or 1
    return sorted(
        [(name, cpu / cpu_count, mem) for name, (cpu, mem) in agg.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:TOP_N]


class MonitorApp(rumps.App):
    def __init__(self):
        super().__init__("CPU --", quit_button=None)

        # Menu items we'll mutate on each refresh.
        self.cpu_item = rumps.MenuItem("CPU: ...")
        self.ram_item = rumps.MenuItem("Memory: ...")
        self.bat_item = rumps.MenuItem("Battery: ...")
        self.therm_item = rumps.MenuItem("Thermal: ...")
        self.app_items = [rumps.MenuItem(f"app_{i}") for i in range(TOP_N)]

        # rumps treats plain strings as disabled (section-header) items.
        self.menu = [
            self.cpu_item,
            self.ram_item,
            self.bat_item,
            self.therm_item,
            None,  # separator
            "Top apps",
            *self.app_items,
            None,
            rumps.MenuItem("Open dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Refresh now", callback=self.manual_refresh),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self._dashboard_proc = None

    # Title of the menu bar item.
    def _set_title(self, cpu_pct, therm_state):
        prefix = ""
        if therm_state == "Throttling":
            prefix = "! "
        elif cpu_pct >= 85:
            prefix = "! "
        self.title = f"{prefix}CPU {cpu_pct:.0f}%"

    @rumps.timer(2)
    def refresh(self, _sender):
        cpu_pct = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        bat = psutil.sensors_battery()
        therm_state, therm_level = get_thermal_state()

        self._set_title(cpu_pct, therm_state)

        cores = psutil.cpu_count(logical=True)
        self.cpu_item.title = f"CPU:  {cpu_pct:.0f}%   ({cores} cores)"
        self.ram_item.title = (
            f"Memory:  {ram.percent:.0f}%   "
            f"{ram.used / 1e9:.1f} / {ram.total / 1e9:.1f} GB"
        )

        if bat:
            txt = f"Battery:  {bat.percent:.0f}%"
            if bat.power_plugged:
                txt += "   charging"
            elif bat.secsleft and bat.secsleft > 0:
                m = bat.secsleft // 60
                txt += f"   {m // 60}h {m % 60}m left"
            self.bat_item.title = txt
        else:
            self.bat_item.title = "Battery:  N/A"

        if therm_level is not None and therm_state != "Unknown":
            self.therm_item.title = f"Thermal:  {therm_state}  ({therm_level}%)"
        else:
            self.therm_item.title = f"Thermal:  {therm_state}"

        top = aggregate_top()
        for i, item in enumerate(self.app_items):
            if i < len(top):
                name, c, m = top[i]
                short = name if len(name) <= 24 else name[:23] + "..."
                item.title = f"{short:<25}  {c:5.1f}%   {m / 1e9:5.2f} GB"
            else:
                item.title = " "

    def manual_refresh(self, _sender):
        self.refresh(None)

    def open_dashboard(self, _sender):
        url = f"http://localhost:{DASHBOARD_PORT}"
        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "monitor.py")

        if not os.path.exists(script):
            rumps.notification(
                "Resource Monitor",
                "monitor.py not found",
                "Keep monitor.py next to menubar.py to use the dashboard.",
            )
            return

        already_running = self._dashboard_proc and self._dashboard_proc.poll() is None
        if not already_running:
            self._dashboard_proc = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        else:
            webbrowser.open(url)


if __name__ == "__main__":
    MonitorApp().run()
