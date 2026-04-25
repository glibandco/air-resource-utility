#!/usr/bin/env python3
"""
MacBook Air Resource Monitor
Live dashboard for CPU, RAM, battery, thermals and per-app usage.

Run:
    python3 monitor.py

Then open http://localhost:8765 (a browser tab opens automatically).
Press Ctrl+C in the terminal to stop.
"""

import json
import subprocess
import sys
import threading
import time
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Dependency bootstrap -----------------------------------------------------
try:
    import psutil
except ImportError:
    print("Installing psutil (one-time setup)...")
    for args in (
        [sys.executable, "-m", "pip", "install", "--user", "--break-system-packages", "psutil"],
        [sys.executable, "-m", "pip", "install", "--user", "psutil"],
    ):
        try:
            subprocess.check_call(args)
            break
        except Exception:
            continue
    import psutil  # noqa: E402

PORT = 8765

# Prime cpu_percent so the first reading isn't 0.
psutil.cpu_percent(interval=None)
for _p in psutil.process_iter():
    try:
        _p.cpu_percent(None)
    except Exception:
        pass

# Apps we want to highlight with a colored dot in the table.
PRIORITY_APPS = {
    "claude": "#d97757",
    "comet": "#9b59f6",
    "chrome": "#4285f4",
    "google chrome": "#4285f4",
    "safari": "#1e88e5",
    "code": "#007acc",
    "cursor": "#7c5cff",
    "slack": "#4a154b",
    "arc": "#ff6b6b",
    "firefox": "#ff7139",
    "xcode": "#147efb",
    "terminal": "#1d9bf0",
    "iterm": "#1d9bf0",
    "spotify": "#1db954",
    "notion": "#e8e8ea",
    "figma": "#a259ff",
    "discord": "#5865f2",
    "zoom": "#2d8cff",
    "whatsapp": "#25d366",
}

# Process names that share a common prefix (e.g. "Google Chrome Helper (Renderer)")
# get rolled up under one app row.
GROUP_PREFIXES = [
    "Claude", "Comet", "Google Chrome", "Chrome", "Safari", "Slack",
    "Cursor", "Code", "Arc", "Firefox", "Xcode", "Spotify", "Notion",
    "Figma", "Discord", "WhatsApp", "Zoom", "Microsoft", "Adobe",
]


def get_thermal():
    """Read `pmset -g therm` to detect thermal throttling on macOS."""
    try:
        out = subprocess.check_output(
            ["pmset", "-g", "therm"], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        for line in out.splitlines():
            if "CPU_Scheduler_Limit" in line:
                val = int(line.split("=")[-1].strip())
                if val >= 100:
                    return {"state": "Nominal", "level": val}
                if val >= 75:
                    return {"state": "Mild throttle", "level": val}
                return {"state": "Throttling", "level": val}
        return {"state": "Nominal", "level": 100}
    except Exception:
        return {"state": "Unknown", "level": None}


def aggregate_processes():
    agg = defaultdict(lambda: {"cpu": 0.0, "mem": 0, "count": 0})
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            name = p.info["name"] or ""
            key = name
            low = name.lower()
            for prefix in GROUP_PREFIXES:
                if low.startswith(prefix.lower()):
                    key = prefix
                    break
            cpu = p.info["cpu_percent"] or 0
            mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
            agg[key]["cpu"] += cpu
            agg[key]["mem"] += mem
            agg[key]["count"] += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # CPU% is per-core, normalize to whole-machine percent.
    cpu_count = psutil.cpu_count(logical=True) or 1
    procs = []
    for name, s in agg.items():
        norm_cpu = s["cpu"] / cpu_count
        color = next(
            (PRIORITY_APPS[k] for k in PRIORITY_APPS if k in name.lower()),
            None,
        )
        procs.append({
            "name": name,
            "cpu": round(norm_cpu, 1),
            "mem": s["mem"],
            "count": s["count"],
            "color": color,
        })
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:15]


def collect_stats():
    cpu_pct = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    ram = psutil.virtual_memory()
    bat = psutil.sensors_battery()

    return {
        "cpu": {
            "percent": cpu_pct,
            "cores": cpu_count,
            "per_core": cpu_per_core,
        },
        "ram": {
            "percent": ram.percent,
            "used_gb": round(ram.used / 1e9, 2),
            "total_gb": round(ram.total / 1e9, 2),
        },
        "battery": {
            "percent": bat.percent if bat else None,
            "charging": bat.power_plugged if bat else None,
            "time_left_min": (bat.secsleft // 60)
            if bat and bat.secsleft and bat.secsleft > 0
            else None,
        },
        "thermal": get_thermal(),
        "processes": aggregate_processes(),
        "timestamp": time.time(),
    }


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Resource Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #0f0f12;
    --panel: #1a1a20;
    --panel2: #22222a;
    --border: #2a2a32;
    --text: #e8e8ea;
    --muted: #7a7a85;
    --accent: #d97757;
    --green: #4ade80;
    --yellow: #fbbf24;
    --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { background: var(--bg); color: var(--text); }
  body {
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
    padding: 28px 24px 40px;
    max-width: 880px;
    margin: 0 auto;
  }
  h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.01em; }
  .sub { color: var(--muted); margin: 4px 0 22px; font-size: 13px; }
  .panel {
    background: var(--panel);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 16px;
  }
  .panel h2 { font-size: 13px; font-weight: 600; margin-bottom: 14px; color: var(--text);
    text-transform: uppercase; letter-spacing: 0.06em; }
  .row { display: flex; align-items: center; gap: 12px; margin: 10px 0; }
  .row .name { width: 80px; color: var(--text); font-size: 13px; }
  .row .val { color: var(--text); font-size: 13px; min-width: 220px;
    font-variant-numeric: tabular-nums; }
  .bar {
    flex: 1;
    height: 10px;
    background: var(--panel2);
    border-radius: 5px;
    overflow: hidden;
    min-width: 160px;
  }
  .bar > div {
    height: 100%;
    transition: width 0.45s ease, background 0.2s ease;
    border-radius: 5px;
  }
  .therm {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    margin-top: 10px;
  }
  table { width: 100%; border-collapse: collapse; }
  th, td {
    text-align: left; padding: 9px 6px; font-size: 13px;
    border-bottom: 1px solid var(--border);
  }
  tr:last-child td { border-bottom: none; }
  th { color: var(--muted); font-weight: 500; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.06em; }
  td.num { font-variant-numeric: tabular-nums; text-align: right; padding-right: 14px; }
  th.num { text-align: right; padding-right: 14px; }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 8px; vertical-align: middle; }
  .cores { display: grid; grid-template-columns: repeat(auto-fit, minmax(54px, 1fr));
    gap: 6px; margin-top: 14px; }
  .core { height: 28px; background: var(--panel2); border-radius: 5px;
    position: relative; overflow: hidden; }
  .core > div { position: absolute; bottom: 0; left: 0; right: 0;
    transition: height 0.4s, background 0.2s; }
  .core span { position: absolute; inset: 0; display: grid; place-items: center;
    font-size: 10px; color: var(--text); font-variant-numeric: tabular-nums;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5); }
  .footer { color: var(--muted); font-size: 11px; text-align: center; margin-top: 18px; }
</style>
</head>
<body>
  <h1>Resource Monitor</h1>
  <div class="sub" id="sub">MacBook Air &middot; live</div>

  <div class="panel">
    <h2>System</h2>
    <div class="row"><div class="name">CPU</div>
      <div class="bar"><div id="cpu-bar"></div></div>
      <div class="val" id="cpu-val">&mdash;</div></div>
    <div class="row"><div class="name">Memory</div>
      <div class="bar"><div id="ram-bar"></div></div>
      <div class="val" id="ram-val">&mdash;</div></div>
    <div class="row"><div class="name">Battery</div>
      <div class="bar"><div id="bat-bar"></div></div>
      <div class="val" id="bat-val">&mdash;</div></div>
    <div class="therm" id="therm">Thermal: &mdash;</div>
    <div class="cores" id="cores"></div>
  </div>

  <div class="panel">
    <h2>Top apps by CPU</h2>
    <table>
      <thead>
        <tr><th>App</th><th class="num">CPU</th><th class="num">Memory</th><th class="num">Procs</th></tr>
      </thead>
      <tbody id="proc-body"></tbody>
    </table>
  </div>

  <div class="footer">Refreshes every 2s &middot; stop with Ctrl+C in the terminal</div>

<script>
function colorFor(pct) {
  if (pct < 60) return 'var(--green)';
  if (pct < 85) return 'var(--yellow)';
  return 'var(--red)';
}
function setBar(id, pct, c) {
  const el = document.getElementById(id);
  el.style.width = Math.min(100, Math.max(0, pct)) + '%';
  el.style.background = c || colorFor(pct);
}
function fmtMem(bytes) {
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(2) + ' GB';
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(0) + ' MB';
  return (bytes / 1e3).toFixed(0) + ' KB';
}

async function tick() {
  try {
    const r = await fetch('/stats');
    const d = await r.json();

    setBar('cpu-bar', d.cpu.percent);
    document.getElementById('cpu-val').textContent =
      d.cpu.percent.toFixed(0) + '%  \u00b7  ' + d.cpu.cores + ' cores';

    setBar('ram-bar', d.ram.percent);
    document.getElementById('ram-val').textContent =
      d.ram.percent.toFixed(0) + '%  \u00b7  ' + d.ram.used_gb + ' / ' + d.ram.total_gb + ' GB';

    if (d.battery.percent !== null) {
      const bc = d.battery.percent > 30 ? 'var(--green)'
        : (d.battery.percent > 15 ? 'var(--yellow)' : 'var(--red)');
      setBar('bat-bar', d.battery.percent, bc);
      let txt = d.battery.percent.toFixed(0) + '%';
      if (d.battery.charging) txt += ' \u00b7 charging';
      else if (d.battery.time_left_min)
        txt += ' \u00b7 ' + Math.floor(d.battery.time_left_min/60) +
               'h ' + (d.battery.time_left_min%60) + 'm left';
      document.getElementById('bat-val').textContent = txt;
    } else {
      setBar('bat-bar', 0, 'var(--muted)');
      document.getElementById('bat-val').textContent = 'N/A';
    }

    const therm = document.getElementById('therm');
    const t = d.thermal;
    therm.textContent = 'Thermal: ' + t.state +
      (t.level !== null && t.level !== undefined ? '  \u00b7  ' + t.level + '%' : '');
    let tbg = 'rgba(122,122,133,0.15)', tfg = 'var(--muted)';
    if (t.state === 'Nominal') { tbg = 'rgba(74,222,128,0.15)'; tfg = 'var(--green)'; }
    else if (t.state === 'Mild throttle') { tbg = 'rgba(251,191,36,0.15)'; tfg = 'var(--yellow)'; }
    else if (t.state === 'Throttling') { tbg = 'rgba(239,68,68,0.15)'; tfg = 'var(--red)'; }
    therm.style.background = tbg;
    therm.style.color = tfg;

    const cores = document.getElementById('cores');
    cores.innerHTML = d.cpu.per_core.map(c =>
      `<div class="core"><div style="height:${c}%;background:${
        c<60?'var(--green)':c<85?'var(--yellow)':'var(--red)'
      }"></div><span>${c.toFixed(0)}</span></div>`
    ).join('');

    const body = document.getElementById('proc-body');
    body.innerHTML = d.processes.map(p => `
      <tr>
        <td>${p.color ? `<span class="dot" style="background:${p.color}"></span>` : '<span class="dot" style="background:#3a3a44"></span>'}${p.name}${p.count > 1 ? ` <span style="color:var(--muted);font-size:11px">\u00d7${p.count}</span>` : ''}</td>
        <td class="num">${p.cpu.toFixed(1)}%</td>
        <td class="num">${fmtMem(p.mem)}</td>
        <td class="num" style="color:var(--muted)">${p.count}</td>
      </tr>
    `).join('');

    document.getElementById('sub').textContent =
      'MacBook Air \u00b7 live \u00b7 last update ' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error(e);
    document.getElementById('sub').textContent =
      'Lost connection to monitor.py (is it still running?)';
  }
}
tick();
setInterval(tick, 2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        return  # silence stdout

    def do_GET(self):
        if self.path == "/stats":
            try:
                data = json.dumps(collect_stats()).encode()
            except Exception as e:
                data = json.dumps({"error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            data = INDEX_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\n  Resource Monitor running at {url}")
    print(f"  Press Ctrl+C to stop.\n")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
